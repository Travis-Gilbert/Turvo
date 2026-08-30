// Copyright 2020-2026 Tauri Programme within The Commons Conservancy
// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

use std::{borrow::Cow, collections::HashMap, sync::Arc};

use servo::{
  protocol_handler::{
    DoneChannel, FetchContext, HttpStatus, NetworkError, ProtocolHandler, ProtocolRegistry,
    Request as ServoRequest, ResourceFetchTiming, Response as ServoResponse, ResponseBody,
  },
  WebResourceLoad, WebResourceResponse,
};
use url::Url;

use crate::{RequestAsyncResponder, ServoError, ServoResult, WebViewId};

pub(super) type CustomProtocolHandler =
  Box<dyn Fn(WebViewId, http::Request<Vec<u8>>, RequestAsyncResponder) + Send + Sync>;

/// One immutable handler set shared by the engine and webview delegates.
pub(super) struct ProtocolRouter {
  webview_id: String,
  handlers: HashMap<String, CustomProtocolHandler>,
}

impl ProtocolRouter {
  pub fn new(webview_id: String, handlers: HashMap<String, CustomProtocolHandler>) -> Self {
    Self {
      webview_id,
      handlers,
    }
  }

  pub fn registry(self: &Arc<Self>) -> ServoResult<ProtocolRegistry> {
    let mut registry = ProtocolRegistry::default();
    for scheme in self.handlers.keys() {
      registry
        .register(
          scheme,
          CustomProtocol {
            router: self.clone(),
            scheme: scheme.clone(),
          },
        )
        .map_err(|error| {
          ServoError::Servo(format!(
            "failed to register custom protocol {scheme}: {error:?}"
          ))
        })?;
    }
    Ok(registry)
  }

  fn mapped_handler(&self, url: &Url) -> Result<Option<&CustomProtocolHandler>, http::StatusCode> {
    if !matches!(url.scheme(), "http" | "https") {
      return Ok(None);
    }
    let Some(scheme) = url
      .domain()
      .and_then(|host| host.strip_suffix(".localhost"))
    else {
      return Ok(None);
    };
    let Some(handler) = self.handlers.get(scheme) else {
      return Ok(None);
    };

    // A registered localhost name must never fall through to an actual server
    // just because credentials or a nonstandard port were added to its URL.
    // Url normalizes explicit default ports to None.
    if !url.username().is_empty() || url.password().is_some() || url.port().is_some() {
      return Err(http::StatusCode::FORBIDDEN);
    }
    Ok(Some(handler))
  }

  pub fn load_web_resource(&self, load: WebResourceLoad) {
    let handler = match self.mapped_handler(&load.request().url) {
      Ok(Some(handler)) => handler,
      Ok(None) => return, // Dropping an unclaimed load resumes normal fetching.
      Err(status) => {
        complete_load(load, status_response(status));
        return;
      }
    };
    let request = load.request();
    let request = protocol_request(
      &request.url,
      request.method.clone(),
      request.headers.clone(),
    );
    let Ok(request) = request else {
      complete_load(load, status_response(http::StatusCode::BAD_REQUEST));
      return;
    };

    // Once a registered URL has been claimed, a dropped asynchronous response
    // must fail closed rather than accidentally contacting a loopback server.
    let pending = PendingResourceLoad(Some(load));
    handler(
      &self.webview_id,
      request,
      RequestAsyncResponder {
        responder: Box::new(move |response| pending.respond(response)),
      },
    );
  }
}

fn protocol_request(
  url: &Url,
  method: http::Method,
  headers: http::HeaderMap,
) -> http::Result<http::Request<Vec<u8>>> {
  // Servo 0.5's interception API supplies metadata, not request bodies. This
  // serves assets; it does not establish the source-authenticated IPC path.
  // In particular, neither the target URL nor a referrer is an Origin header.
  let mut request = http::Request::builder()
    .method(method)
    .uri(url.as_str())
    .body(Vec::new())?;
  *request.headers_mut() = headers;
  Ok(request)
}

fn resource_response(
  url: Url,
  response: http::Response<Cow<'static, [u8]>>,
) -> (WebResourceResponse, Cow<'static, [u8]>) {
  let (parts, body) = response.into_parts();
  let response = WebResourceResponse::new(url)
    .status_code(parts.status)
    .status_message(
      parts
        .status
        .canonical_reason()
        .unwrap_or_default()
        .as_bytes()
        .to_vec(),
    )
    .headers(parts.headers);
  (response, body)
}

fn status_response(status: http::StatusCode) -> http::Response<Cow<'static, [u8]>> {
  let mut response = http::Response::new(Cow::Borrowed(&[] as &[u8]));
  *response.status_mut() = status;
  response
}

fn complete_load(load: WebResourceLoad, response: http::Response<Cow<'static, [u8]>>) {
  let (response, body) = resource_response(load.request().url.clone(), response);
  let mut intercepted = load.intercept(response);
  // Send even an empty chunk so Servo finalizes the body as Done(empty).
  intercepted.send_body_data(body.into_owned());
  intercepted.finish();
}

struct PendingResourceLoad(Option<WebResourceLoad>);

impl PendingResourceLoad {
  fn respond(mut self, response: http::Response<Cow<'static, [u8]>>) {
    if let Some(load) = self.0.take() {
      complete_load(load, response);
    }
  }
}

impl Drop for PendingResourceLoad {
  fn drop(&mut self) {
    if let Some(load) = self.0.take() {
      complete_load(
        load,
        status_response(http::StatusCode::INTERNAL_SERVER_ERROR),
      );
    }
  }
}

struct CustomProtocol {
  router: Arc<ProtocolRouter>,
  scheme: String,
}

impl ProtocolHandler for CustomProtocol {
  fn load<'a>(
    &'a self,
    request: &'a mut ServoRequest,
    _done_chan: &mut DoneChannel,
    _context: &FetchContext,
  ) -> std::pin::Pin<Box<dyn std::future::Future<Output = ServoResponse> + Send + 'a>> {
    let url = request.current_url();
    let timing_type = request.timing_type();
    let request = protocol_request(
      url.as_url(),
      request.method.clone(),
      request.headers.clone(),
    );
    let Ok(request) = request else {
      return Box::pin(std::future::ready(ServoResponse::network_error(
        NetworkError::ResourceLoadError(format!("invalid custom protocol URL: {url}")),
      )));
    };

    let (sender, receiver) = futures_channel::oneshot::channel();
    (self.router.handlers[&self.scheme])(
      &self.router.webview_id,
      request,
      RequestAsyncResponder {
        responder: Box::new(move |response| {
          let _ = sender.send(response);
        }),
      },
    );

    Box::pin(async move {
      match receiver.await {
        Ok(response) => {
          let (parts, body) = response.into_parts();
          let mut response = ServoResponse::new(url, ResourceFetchTiming::new(timing_type));
          response.status = HttpStatus::new_raw(
            parts.status.as_u16(),
            parts
              .status
              .canonical_reason()
              .unwrap_or_default()
              .as_bytes()
              .to_vec(),
          );
          response.headers = parts.headers;
          *response.body.lock() = ResponseBody::Done(body.into_owned());
          response
        }
        Err(_) => ServoResponse::network_error(NetworkError::ResourceLoadError(
          "custom protocol response channel closed".into(),
        )),
      }
    })
  }

  fn is_fetchable(&self) -> bool {
    true
  }

  fn is_secure(&self) -> bool {
    true
  }
}

#[cfg(test)]
mod tests {
  use super::*;

  fn router() -> ProtocolRouter {
    let mut handlers: HashMap<String, CustomProtocolHandler> = HashMap::new();
    handlers.insert("tauri".into(), Box::new(|_, _, _| {}));
    handlers.insert("app-assets".into(), Box::new(|_, _, _| {}));
    ProtocolRouter::new("main".into(), handlers)
  }

  #[test]
  fn maps_only_registered_localhost_names() {
    let router = router();
    for url in [
      "http://tauri.localhost/index.html",
      "https://tauri.localhost/index.html?mode=test",
      "http://tauri.localhost:80/",
      "https://tauri.localhost:443/",
      "https://TAURI.localhost/",
      "http://app-assets.localhost/image.png",
    ] {
      assert!(
        router
          .mapped_handler(&Url::parse(url).unwrap())
          .unwrap()
          .is_some(),
        "{url}"
      );
    }
  }

  #[test]
  fn leaves_unregistered_and_unrelated_urls_to_servo() {
    let router = router();
    for url in [
      "tauri://localhost/index.html",
      "https://example.com/",
      "http://tauri.localhost.example.com/",
      "http://nested.tauri.localhost/",
      "http://unknown.localhost/",
      "http://localhost/",
      "http://127.0.0.1/",
      "http://[::1]/",
      "http://tauri.localhost./",
    ] {
      assert!(
        router
          .mapped_handler(&Url::parse(url).unwrap())
          .unwrap()
          .is_none(),
        "{url}"
      );
    }
  }

  #[test]
  fn rejects_ambiguous_registered_authorities_instead_of_using_the_network() {
    let router = router();
    for url in [
      "http://tauri.localhost:8080/",
      "https://tauri.localhost:80/",
      "http://user@tauri.localhost/",
      "http://user:password@tauri.localhost/",
      "https://:password@app-assets.localhost/",
    ] {
      assert!(
        matches!(
          router.mapped_handler(&Url::parse(url).unwrap()),
          Err(http::StatusCode::FORBIDDEN)
        ),
        "{url}"
      );
    }
  }

  #[test]
  fn preserves_request_url_method_and_headers_without_rewriting_origin() {
    let url = Url::parse("https://tauri.localhost/image.png?size=2").unwrap();
    let mut headers = http::HeaderMap::new();
    headers.insert(
      http::header::ORIGIN,
      "https://remote.example".parse().unwrap(),
    );
    headers.insert(http::header::RANGE, "bytes=0-3".parse().unwrap());
    let request = protocol_request(&url, http::Method::HEAD, headers.clone()).unwrap();

    assert_eq!(request.uri().to_string(), url.as_str());
    assert_eq!(request.method(), http::Method::HEAD);
    assert_eq!(request.headers(), &headers);
    assert!(request.body().is_empty());
  }

  #[test]
  fn never_invents_a_missing_origin_header() {
    let request = protocol_request(
      &Url::parse("http://tauri.localhost/").unwrap(),
      http::Method::GET,
      http::HeaderMap::new(),
    )
    .unwrap();
    assert!(!request.headers().contains_key(http::header::ORIGIN));
  }

  #[test]
  fn preserves_response_url_status_headers_and_binary_body() {
    let url = Url::parse("http://tauri.localhost/image.png").unwrap();
    let body = vec![0, 255, 0, 99];
    let response = http::Response::builder()
      .status(http::StatusCode::PARTIAL_CONTENT)
      .header(http::header::CONTENT_TYPE, "image/png")
      .header(http::header::CONTENT_RANGE, "bytes 0-3/20")
      .body(Cow::Owned(body.clone()))
      .unwrap();
    let (response, received_body) = resource_response(url.clone(), response);

    assert_eq!(response.url, url);
    assert_eq!(response.status_code, http::StatusCode::PARTIAL_CONTENT);
    assert_eq!(response.status_message, b"Partial Content");
    assert_eq!(response.headers[http::header::CONTENT_TYPE], "image/png");
    assert_eq!(
      response.headers[http::header::CONTENT_RANGE],
      "bytes 0-3/20"
    );
    assert_eq!(received_body.as_ref(), body);
  }

  #[test]
  fn keeps_the_custom_scheme_registry_for_non_windows_loading() {
    let router = Arc::new(router());
    let registry = router.registry().unwrap();
    assert!(registry.get("tauri").is_some());
    assert!(registry.get("app-assets").is_some());
    assert!(registry.get("http").is_none());
    assert!(registry.get("https").is_none());
  }
}
