// Copyright 2020-2026 Tauri Programme within The Commons Conservancy
// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

use std::{borrow::Cow, collections::HashMap, sync::Arc, thread, time::Duration};

use percent_encoding::percent_decode_str;

use servo::{
  protocol_handler::{
    DoneChannel, FetchContext, HttpStatus, NetworkError, ProtocolHandler, ProtocolRegistry,
    Request as ServoRequest, ResourceFetchTiming, Response as ServoResponse, ResponseBody,
  },
  WebResourceLoad, WebResourceResponse,
};
use url::Url;

use crate::{RequestAsyncResponder, ServoError, ServoResult, WebViewId};

use super::ipc::{
  read_request_body, AuthenticatedSource, BridgeMessage, BridgeSink, SourceTracker, BRIDGE_SCHEME,
  MAX_REQUEST_BODY_BYTES,
};

const MAX_CODE_SERVER_RESOURCE_BYTES: u64 = 64 * 1024 * 1024;
const VSCODE_RESOURCE_SUFFIX: &str = ".vscode-resource.vscode-cdn.net";
const VSCODE_WEBVIEW_SUFFIX: &str = ".vscode-cdn.net";

#[derive(Clone)]
struct CodeServerProxy {
  base_url: Url,
  agent: ureq::Agent,
}

impl CodeServerProxy {
  fn new(base_url: Url) -> Self {
    let config = ureq::Agent::config_builder()
      .http_status_as_error(false)
      .proxy(None)
      .max_redirects(0)
      .timeout_global(Some(Duration::from_secs(30)))
      .build();
    Self {
      base_url,
      agent: config.into(),
    }
  }

  fn target(&self, source: &Url) -> Result<Option<Url>, http::StatusCode> {
    if !matches!(source.scheme(), "http" | "https") {
      return Ok(None);
    }
    let Some(host) = source.host_str() else {
      return Ok(None);
    };
    let is_remote_resource = host == "vscode-remote-resource"
      || host
        .strip_suffix(VSCODE_RESOURCE_SUFFIX)
        .is_some_and(|prefix| !prefix.is_empty());
    let is_webview_host = !is_remote_resource
      && host
        .strip_suffix(VSCODE_WEBVIEW_SUFFIX)
        .is_some_and(|prefix| !prefix.is_empty());
    if !is_remote_resource && !is_webview_host {
      return Ok(None);
    }
    if !source.username().is_empty() || source.password().is_some() || source.port().is_some() {
      return Err(http::StatusCode::FORBIDDEN);
    }

    if is_remote_resource {
      let path = percent_decode_str(source.path())
        .decode_utf8()
        .map_err(|_| http::StatusCode::BAD_REQUEST)?;
      if path.as_bytes().contains(&0) {
        return Err(http::StatusCode::BAD_REQUEST);
      }
      let mut target = self.endpoint("vscode-remote-resource");
      target.query_pairs_mut().append_pair("path", &path);
      return Ok(Some(target));
    }

    let path = percent_decode_str(source.path())
      .decode_utf8()
      .map_err(|_| http::StatusCode::BAD_REQUEST)?;
    if path
      .split('/')
      .any(|component| matches!(component, "." | ".."))
      || !matches!(path.rsplit('/').next(), Some("index.html" | "fake.html"))
    {
      return Err(http::StatusCode::NOT_FOUND);
    }
    let mut target = self.base_url.clone();
    target.set_path(&format!(
      "{}/{}",
      self.base_url.path().trim_end_matches('/'),
      path.trim_start_matches('/')
    ));
    target.set_query(source.query());
    Ok(Some(target))
  }

  fn endpoint(&self, name: &str) -> Url {
    let mut target = self.base_url.clone();
    target.set_path(&format!(
      "{}/{}",
      self.base_url.path().trim_end_matches('/'),
      name
    ));
    target.set_query(None);
    target.set_fragment(None);
    target
  }

  fn fetch(
    &self,
    method: http::Method,
    source_headers: &http::HeaderMap,
    source_url: &Url,
    target: Url,
  ) -> http::Response<Cow<'static, [u8]>> {
    let mut request = match http::Request::builder()
      .method(method.clone())
      .uri(target.as_str())
      .body(())
    {
      Ok(request) => request,
      Err(_) => return status_response(http::StatusCode::BAD_REQUEST),
    };
    for name in [
      http::header::ACCEPT,
      http::header::ACCEPT_ENCODING,
      http::header::IF_MATCH,
      http::header::IF_MODIFIED_SINCE,
      http::header::IF_NONE_MATCH,
      http::header::IF_UNMODIFIED_SINCE,
      http::header::RANGE,
    ] {
      if let Some(value) = source_headers.get(&name) {
        request.headers_mut().insert(name, value.clone());
      }
    }

    let mut upstream = match self.agent.run(request) {
      Ok(response) => response,
      Err(_) => return status_response(http::StatusCode::BAD_GATEWAY),
    };
    let status = upstream.status();
    let mut headers = upstream.headers().clone();
    for name in [
      "connection",
      "keep-alive",
      "proxy-authenticate",
      "proxy-authorization",
      "set-cookie",
      "te",
      "trailer",
      "transfer-encoding",
      "upgrade",
    ] {
      headers.remove(name);
    }
    headers.insert(
      http::header::HeaderName::from_static("cross-origin-resource-policy"),
      http::HeaderValue::from_static("cross-origin"),
    );
    apply_cross_origin_isolation_headers(source_url, &mut headers);

    let body = if method == http::Method::HEAD {
      Vec::new()
    } else {
      match upstream
        .body_mut()
        .with_config()
        .limit(MAX_CODE_SERVER_RESOURCE_BYTES)
        .read_to_vec()
      {
        Ok(body) => body,
        Err(_) => return status_response(http::StatusCode::BAD_GATEWAY),
      }
    };
    let mut response = http::Response::new(Cow::Owned(body));
    *response.status_mut() = status;
    *response.headers_mut() = headers;
    response
  }
}

fn apply_cross_origin_isolation_headers(url: &Url, headers: &mut http::HeaderMap) {
  let value = url
    .query_pairs()
    .find_map(|(name, value)| (name == "vscode-coi").then_some(value));
  if matches!(value.as_deref(), Some("1" | "3")) {
    headers.insert(
      http::header::HeaderName::from_static("cross-origin-opener-policy"),
      http::HeaderValue::from_static("same-origin"),
    );
  }
  if matches!(value.as_deref(), Some("2" | "3")) {
    headers.insert(
      http::header::HeaderName::from_static("cross-origin-embedder-policy"),
      http::HeaderValue::from_static("require-corp"),
    );
  }
}

pub(super) type CustomProtocolHandler =
  Box<dyn Fn(WebViewId, http::Request<Vec<u8>>, RequestAsyncResponder) + Send + Sync>;

/// One immutable handler set shared by the engine and webview delegates.
pub(super) struct ProtocolRouter {
  webview_id: String,
  handlers: HashMap<String, CustomProtocolHandler>,
  use_https_scheme: bool,
  pub sources: SourceTracker,
  bridge: Option<BridgeSink>,
  code_server: Option<CodeServerProxy>,
}

impl ProtocolRouter {
  pub fn new(
    webview_id: String,
    handlers: HashMap<String, CustomProtocolHandler>,
    bridge: Option<BridgeSink>,
    use_https_scheme: bool,
    code_server_url: Option<Url>,
  ) -> Self {
    Self {
      webview_id,
      handlers,
      use_https_scheme,
      sources: SourceTracker::default(),
      bridge,
      code_server: code_server_url.map(CodeServerProxy::new),
    }
  }

  /// Normalize runtime-owned navigation without changing the handler-facing URL contract.
  pub fn browser_url(&self, url: Url) -> ServoResult<Url> {
    if url.scheme() == "ipc" || url.scheme() == BRIDGE_SCHEME {
      return Err(ServoError::Servo(
        "IPC endpoints cannot be navigated".into(),
      ));
    }
    self
      .mapped_handler(&url)
      .map_err(|_| ServoError::Servo("invalid mapped application URL authority".into()))?;
    if !self.handlers.contains_key(url.scheme()) {
      return Ok(url);
    }
    if url.host_str() != Some("localhost")
      || !url.username().is_empty()
      || url.password().is_some()
      || url.port().is_some()
    {
      return Err(ServoError::Servo(
        "custom application URLs require an unqualified localhost authority".into(),
      ));
    }
    let transport = if self.use_https_scheme {
      "https"
    } else {
      "http"
    };
    Url::parse(&format!(
      "{transport}://{}.localhost{}",
      url.scheme(),
      &url[url::Position::BeforePath..]
    ))
    .map_err(|error| ServoError::Servo(format!("invalid mapped application URL: {error}")))
  }

  pub fn registry(self: &Arc<Self>) -> ServoResult<ProtocolRegistry> {
    let mut registry = ProtocolRegistry::default();
    let schemes = self
      .handlers
      .keys()
      .cloned()
      .chain(self.bridge.as_ref().map(|_| BRIDGE_SCHEME.to_owned()));
    for scheme in schemes {
      registry
        .register(
          &scheme,
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

  fn mapped_handler(
    &self,
    url: &Url,
  ) -> Result<Option<(&str, &CustomProtocolHandler)>, http::StatusCode> {
    if !matches!(url.scheme(), "http" | "https") {
      return Ok(None);
    }
    let Some(scheme) = url
      .domain()
      .and_then(|host| host.strip_suffix(".localhost"))
    else {
      return Ok(None);
    };
    let Some((registered_scheme, handler)) = self.handlers.get_key_value(scheme) else {
      return Ok(None);
    };
    // The mapped HTTP interface has no authenticated initiator metadata.
    // Privileged IPC uses the lower-level ipc custom protocol on every OS.
    if scheme == "ipc" || scheme == BRIDGE_SCHEME {
      return Err(http::StatusCode::FORBIDDEN);
    }

    // A registered localhost name must never fall through to an actual server
    // just because credentials or a nonstandard port were added to its URL.
    // Url normalizes explicit default ports to None.
    if !url.username().is_empty() || url.password().is_some() || url.port().is_some() {
      return Err(http::StatusCode::FORBIDDEN);
    }
    Ok(Some((registered_scheme.as_str(), handler)))
  }

  pub fn load_web_resource(&self, load: WebResourceLoad) {
    if let Some(proxy) = &self.code_server {
      match proxy.target(&load.request().url) {
        Ok(Some(target)) => {
          if load.request().has_body
            || !matches!(
              load.request().method,
              http::Method::GET | http::Method::HEAD
            )
          {
            complete_load(load, status_response(http::StatusCode::METHOD_NOT_ALLOWED));
            return;
          }
          let method = load.request().method.clone();
          let headers = load.request().headers.clone();
          let source_url = load.request().url.clone();
          let proxy = proxy.clone();
          let pending = PendingResourceLoad(Some(load));
          let _ = thread::Builder::new()
            .name("turvo-code-server-resource".into())
            .spawn(move || {
              pending.respond(proxy.fetch(method, &headers, &source_url, target));
            });
          return;
        }
        Ok(None) => {}
        Err(status) => {
          complete_load(load, status_response(status));
          return;
        }
      }
    }

    let (scheme, handler) = match self.mapped_handler(&load.request().url) {
      Ok(Some(handler)) => handler,
      Ok(None) => return, // Dropping an unclaimed load resumes normal fetching.
      Err(status) => {
        complete_load(load, status_response(status));
        return;
      }
    };
    let request = load.request();
    if request.has_body {
      // Asset interception has no upload stream. Reject before calling application code;
      // returning an error after dispatch cannot undo handler side effects.
      complete_load(load, status_response(http::StatusCode::METHOD_NOT_ALLOWED));
      return;
    }
    let Ok(handler_url) = mapped_protocol_url(scheme, &request.url) else {
      complete_load(load, status_response(http::StatusCode::BAD_REQUEST));
      return;
    };
    let request = protocol_request(
      &handler_url,
      request.method.clone(),
      request.headers.clone(),
      Vec::new(),
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

fn mapped_protocol_url(scheme: &str, url: &Url) -> Result<Url, url::ParseError> {
  // Match Wry's handler-facing contract while leaving the browser URL and
  // request Origin untouched. Tauri's asset resolver strips tauri://localhost
  // before looking up the path; a raw HTTP URL would select the root asset.
  Url::parse(&format!(
    "{scheme}://localhost{}",
    &url[url::Position::BeforePath..]
  ))
}

fn protocol_request(
  url: &Url,
  method: http::Method,
  headers: http::HeaderMap,
  body: Vec<u8>,
) -> http::Result<http::Request<Vec<u8>>> {
  // Copy headers as supplied. Only the authenticated custom-protocol IPC
  // adapter may add an engine-derived Origin after this conversion.
  let mut request = http::Request::builder()
    .method(method)
    .uri(url.as_str())
    .body(body)?;
  *request.headers_mut() = headers;
  Ok(request)
}

fn resource_response(
  method: &http::Method,
  url: Url,
  response: http::Response<Cow<'static, [u8]>>,
) -> (WebResourceResponse, Cow<'static, [u8]>) {
  let (parts, body) = response.into_parts();
  let body = if method == http::Method::HEAD
    || matches!(
      parts.status,
      http::StatusCode::NO_CONTENT
        | http::StatusCode::RESET_CONTENT
        | http::StatusCode::NOT_MODIFIED
    ) {
    Cow::Borrowed(&[] as &[u8])
  } else {
    body
  };
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
  let (response, body) =
    resource_response(&load.request().method, load.request().url.clone(), response);
  let mut intercepted = load.intercept(response);
  if !body.is_empty() {
    intercepted.send_body_data(body.into_owned());
  }
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

impl CustomProtocol {
  fn is_privileged(&self) -> bool {
    self.scheme == "ipc" || self.scheme == BRIDGE_SCHEME
  }
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
    let method = request.method.clone();
    let headers = request.headers.clone();
    let body = request.body.clone();
    let protected = self.is_privileged();
    let source = if protected {
      match self.router.sources.authenticate(request) {
        Ok(source) => Some(source),
        Err(_) => {
          return Box::pin(std::future::ready(ServoResponse::network_error(
            NetworkError::ResourceLoadError("IPC caller has no authenticated document".into()),
          )));
        }
      }
    } else {
      None
    };
    let document = if protected {
      None
    } else {
      self.router.sources.document_candidate(request)
    };

    Box::pin(async move {
      let body = match read_request_body(body, MAX_REQUEST_BODY_BYTES).await {
        Ok(body) => body,
        Err(error) => return ServoResponse::network_error(error),
      };
      let Ok(mut request) = protocol_request(url.as_url(), method, headers, body) else {
        return ServoResponse::network_error(NetworkError::ResourceLoadError(format!(
          "invalid custom protocol URL: {url}"
        )));
      };
      if let Some(source) = &source {
        if !self.router.sources.is_current(source) {
          return ServoResponse::network_error(NetworkError::ResourceLoadError(
            "IPC document was superseded during request delivery".into(),
          ));
        }
        let Ok(origin) = http::HeaderValue::from_str(source.url.as_str()) else {
          return ServoResponse::network_error(NetworkError::ResourceLoadError(
            "IPC document URL cannot be represented as an origin".into(),
          ));
        };
        request.headers_mut().insert(http::header::ORIGIN, origin);
      }
      let (sender, receiver) = futures_channel::oneshot::channel();
      if self.scheme == BRIDGE_SCHEME {
        let response = match (self.router.bridge.as_ref(), source) {
          (Some(bridge), Some(source)) => bridge_response(bridge, source, request.into_body()),
          _ => status_response(http::StatusCode::FORBIDDEN),
        };
        let _ = sender.send(response);
      } else {
        (self.router.handlers[&self.scheme])(
          &self.router.webview_id,
          request,
          RequestAsyncResponder {
            responder: Box::new(move |response| {
              let _ = sender.send(response);
            }),
          },
        );
      }
      match receiver.await {
        Ok(response) => {
          if response.status().is_success() {
            self.router.sources.accept_document(document);
          }
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
    // Servo's fetchable flag bypasses the normal CORS path. Only endpoints
    // that authenticate every caller may opt into that exemption. Ordinary
    // assets retain Servo's navigation/no-cors handling without exposing
    // readable responses to unrelated documents.
    self.is_privileged()
  }

  fn is_secure(&self) -> bool {
    true
  }
}

fn bridge_response(
  bridge: &BridgeSink,
  source: AuthenticatedSource,
  body: Vec<u8>,
) -> http::Response<Cow<'static, [u8]>> {
  let Ok(body) = String::from_utf8(body) else {
    return status_response(http::StatusCode::BAD_REQUEST);
  };
  if bridge.sender.send(BridgeMessage { source, body }).is_err() {
    return status_response(http::StatusCode::SERVICE_UNAVAILABLE);
  }
  (bridge.wake)();
  status_response(http::StatusCode::OK)
}

#[cfg(test)]
mod tests {
  use super::*;

  fn router() -> ProtocolRouter {
    let mut handlers: HashMap<String, CustomProtocolHandler> = HashMap::new();
    handlers.insert("tauri".into(), Box::new(|_, _, _| {}));
    handlers.insert("app-assets".into(), Box::new(|_, _, _| {}));
    ProtocolRouter::new("main".into(), handlers, None, false, None)
  }

  fn code_server_proxy() -> CodeServerProxy {
    CodeServerProxy::new(Url::parse("http://127.0.0.1:8080/base/").unwrap())
  }

  #[test]
  fn maps_vscode_remote_resources_to_the_code_server_endpoint() {
    let source =
      Url::parse("https://file+.vscode-resource.vscode-cdn.net/%2Fworkspace%2Fimage.png?ignored=1")
        .unwrap();
    let target = code_server_proxy().target(&source).unwrap().unwrap();

    assert_eq!(
      target.as_str(),
      "http://127.0.0.1:8080/base/vscode-remote-resource?path=%2Fworkspace%2Fimage.png"
    );
  }

  #[test]
  fn maps_only_the_static_vscode_webview_documents() {
    let proxy = code_server_proxy();
    for (source, expected) in [
      (
        "https://abc.vscode-cdn.net/stable/commit/out/vs/workbench/contrib/webview/browser/pre/index.html?vscode-coi=3",
        "http://127.0.0.1:8080/base/stable/commit/out/vs/workbench/contrib/webview/browser/pre/index.html?vscode-coi=3",
      ),
      (
        "https://abc.vscode-cdn.net/stable/commit/out/vs/workbench/contrib/webview/browser/pre/fake.html",
        "http://127.0.0.1:8080/base/stable/commit/out/vs/workbench/contrib/webview/browser/pre/fake.html",
      ),
    ] {
      assert_eq!(
        proxy
          .target(&Url::parse(source).unwrap())
          .unwrap()
          .unwrap()
          .as_str(),
        expected
      );
    }

    for source in [
      "https://abc.vscode-cdn.net/stable/pre/service-worker.js",
      "https://abc.vscode-cdn.net/stable/pre/%2e%2e/index.html",
      "https://abc.vscode-cdn.net:444/stable/pre/index.html",
      "https://user@abc.vscode-cdn.net/stable/pre/index.html",
    ] {
      assert!(
        proxy.target(&Url::parse(source).unwrap()).is_err(),
        "{source}"
      );
    }
    assert!(proxy
      .target(&Url::parse("https://example.com/index.html").unwrap())
      .unwrap()
      .is_none());
  }

  #[test]
  fn applies_the_same_cross_origin_headers_as_vscode() {
    let opener = http::header::HeaderName::from_static("cross-origin-opener-policy");
    let embedder = http::header::HeaderName::from_static("cross-origin-embedder-policy");
    for (value, has_opener, has_embedder) in [
      ("1", true, false),
      ("2", false, true),
      ("3", true, true),
      ("x", false, false),
    ] {
      let mut headers = http::HeaderMap::new();
      let url = Url::parse(&format!(
        "https://abc.vscode-cdn.net/index.html?vscode-coi={value}"
      ))
      .unwrap();
      apply_cross_origin_isolation_headers(&url, &mut headers);
      assert_eq!(headers.contains_key(&opener), has_opener, "{value}");
      assert_eq!(headers.contains_key(&embedder), has_embedder, "{value}");
    }
  }

  #[test]
  fn maps_custom_navigation_preserving_path_query_and_fragment() {
    let mut router = router();
    let url =
      Url::parse("tauri://localhost/app%20file.js?next=tauri://localhost/#section").unwrap();
    assert_eq!(
      router.browser_url(url.clone()).unwrap().as_str(),
      "http://tauri.localhost/app%20file.js?next=tauri://localhost/#section"
    );
    router.use_https_scheme = true;
    assert_eq!(
      router.browser_url(url).unwrap().as_str(),
      "https://tauri.localhost/app%20file.js?next=tauri://localhost/#section"
    );
  }

  #[test]
  fn rejects_ambiguous_custom_navigation_and_ipc() {
    let router = router();
    for url in [
      "tauri://remote.example/",
      "tauri://user@localhost/",
      "tauri://localhost:80/",
      "http://tauri.localhost:8080/",
      "https://user@tauri.localhost/",
      "ipc://localhost/action",
      "turvo-ipc://localhost/",
    ] {
      assert!(
        router.browser_url(Url::parse(url).unwrap()).is_err(),
        "{url}"
      );
    }
  }

  #[test]
  fn preserves_browser_urls_outside_custom_navigation() {
    let router = router();
    for url in [
      "http://tauri.localhost/",
      "https://example.com/",
      "about:blank",
      "data:text/html,hello",
    ] {
      assert_eq!(
        router
          .browser_url(Url::parse(url).unwrap())
          .unwrap()
          .as_str(),
        url
      );
    }
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
    let request = protocol_request(&url, http::Method::HEAD, headers.clone(), Vec::new()).unwrap();

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
      Vec::new(),
    )
    .unwrap();
    assert!(!request.headers().contains_key(http::header::ORIGIN));
  }

  #[test]
  fn mapped_asset_callback_gets_the_custom_scheme_and_complete_path() {
    let browser_url =
      Url::parse("https://tauri.localhost/nested/app%20file.js?next=http://tauri.localhost/")
        .unwrap();
    let handler_url = mapped_protocol_url("tauri", &browser_url).unwrap();
    assert_eq!(
      handler_url.as_str(),
      "tauri://localhost/nested/app%20file.js?next=http://tauri.localhost/"
    );
    assert_eq!(browser_url.scheme(), "https");
    assert_eq!(browser_url.host_str(), Some("tauri.localhost"));
    let mut headers = http::HeaderMap::new();
    headers.insert(
      http::header::ORIGIN,
      "https://remote.example".parse().unwrap(),
    );
    let request = protocol_request(&handler_url, http::Method::GET, headers, Vec::new()).unwrap();
    assert_eq!(
      request.headers()[http::header::ORIGIN],
      "https://remote.example"
    );
    assert_eq!(request.uri().path(), "/nested/app%20file.js");
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
    let (response, received_body) = resource_response(&http::Method::GET, url.clone(), response);

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
  fn suppresses_head_and_bodyless_payloads_without_changing_headers() {
    for (method, status) in [
      (http::Method::HEAD, http::StatusCode::OK),
      (http::Method::GET, http::StatusCode::NO_CONTENT),
      (http::Method::GET, http::StatusCode::RESET_CONTENT),
      (http::Method::GET, http::StatusCode::NOT_MODIFIED),
    ] {
      let response = http::Response::builder()
        .status(status)
        .header(http::header::CONTENT_TYPE, "text/plain")
        .body(Cow::Borrowed(&b"handler representation"[..]))
        .unwrap();
      let (response, body) = resource_response(
        &method,
        Url::parse("http://tauri.localhost/asset.txt").unwrap(),
        response,
      );
      assert_eq!(response.status_code, status);
      assert_eq!(response.headers[http::header::CONTENT_TYPE], "text/plain");
      assert!(body.is_empty());
    }
  }

  #[test]
  fn keeps_the_custom_scheme_registry_without_a_fetch_policy_exemption() {
    let router = Arc::new(router());
    let registry = router.registry().unwrap();
    assert!(registry.get("tauri").is_some());
    assert!(registry.get("app-assets").is_some());
    assert!(registry.get("http").is_none());
    assert!(registry.get("https").is_none());
    assert!(!registry.is_fetchable("tauri"));
    assert!(!registry.is_fetchable("app-assets"));
  }

  #[test]
  fn only_authenticated_protocols_bypass_the_normal_fetch_policy() {
    let router = Arc::new(router());
    for scheme in ["ipc", BRIDGE_SCHEME, "tauri", "app-assets"] {
      let protocol = CustomProtocol {
        router: router.clone(),
        scheme: scheme.into(),
      };
      assert_eq!(protocol.is_fetchable(), protocol.is_privileged());
      assert_eq!(
        protocol.is_fetchable(),
        matches!(scheme, "ipc" | BRIDGE_SCHEME)
      );
    }
  }

  #[test]
  fn mapped_http_ipc_cannot_bypass_source_authentication() {
    let mut router = router();
    router.handlers.insert("ipc".into(), Box::new(|_, _, _| {}));
    for url in ["http://ipc.localhost/test", "https://ipc.localhost/test"] {
      assert!(matches!(
        router.mapped_handler(&Url::parse(url).unwrap()),
        Err(http::StatusCode::FORBIDDEN)
      ));
    }
  }
}
