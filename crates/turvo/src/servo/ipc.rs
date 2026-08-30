// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

use std::sync::{mpsc, Mutex};

use content_security_policy::PolicyDisposition;
use futures_util::StreamExt;
use ipc_channel::ipc;
use net_traits::request::{
  BodyChunkRequest, BodyChunkResponse, Origin, Request, RequestBody, RequestMode,
};
use servo::{protocol_handler::NetworkError, WebResourceRequest};
use url::Url;

pub(super) const BRIDGE_SCHEME: &str = "turvo-ipc";
pub(super) const MAX_REQUEST_BODY_BYTES: usize = 16 * 1024 * 1024;

pub(super) struct BridgeMessage {
  pub source: AuthenticatedSource,
  pub body: String,
}

pub(super) struct BridgeSink {
  pub sender: mpsc::Sender<BridgeMessage>,
  pub wake: Box<dyn Fn() + Send + Sync>,
}

#[derive(Clone)]
pub(super) struct AuthenticatedSource {
  pub url: Url,
  epoch: u64,
}

#[derive(Default)]
struct DocumentState {
  epoch: u64,
  top_url: Option<Url>,
  local_document: Option<(u64, Url)>,
}

#[derive(Default)]
pub(super) struct SourceTracker(Mutex<DocumentState>);

impl SourceTracker {
  pub fn observe_load(&self, request: &WebResourceRequest) {
    if request.is_for_main_frame {
      if let Ok(mut state) = self.0.lock() {
        state.epoch = state.epoch.wrapping_add(1);
        state.top_url = Some(request.url.clone());
        state.local_document = None;
      }
    }
  }

  pub fn observe_url(&self, url: &Url) {
    if let Ok(mut state) = self.0.lock() {
      // Same-document URL changes retain the document's identity. Changes
      // without a fetch, such as navigation to a data URL, revoke it.
      let same_authority = state.top_url.as_ref().is_some_and(|previous| {
        url.has_host()
          && previous.scheme() == url.scheme()
          && previous.host_str() == url.host_str()
          && previous.port() == url.port()
      });
      if !same_authority {
        state.epoch = state.epoch.wrapping_add(1);
        state.local_document = None;
      }
      state.top_url = Some(url.clone());
    }
  }

  pub fn epoch(&self) -> Option<u64> {
    self.0.lock().ok().map(|state| state.epoch)
  }

  pub fn is_current(&self, source: &AuthenticatedSource) -> bool {
    self.epoch() == Some(source.epoch)
  }

  pub fn document_candidate(&self, request: &Request) -> Option<(u64, u64, Url)> {
    let client = request.client.as_ref()?;
    if request.mode != RequestMode::Navigate || client.is_nested_browsing_context {
      return None;
    }
    Some((
      self.epoch()?,
      u64::from(request.pipeline_id?),
      request.current_url().into_url(),
    ))
  }

  pub fn accept_document(&self, candidate: Option<(u64, u64, Url)>) {
    if let Some((epoch, pipeline, url)) = candidate {
      if let Ok(mut state) = self.0.lock() {
        // A late response for a superseded navigation cannot register an
        // identity for the replacement document.
        if state.epoch == epoch {
          state.local_document = Some((pipeline, url));
        }
      }
    }
  }

  pub fn authenticate(&self, request: &Request) -> Result<AuthenticatedSource, http::StatusCode> {
    let denied = http::StatusCode::FORBIDDEN;
    let client = request.client.as_ref().ok_or(denied)?;
    let sandboxed = client
      .policy_container
      .csp_list
      .as_ref()
      .is_some_and(|list| {
        list.0.iter().any(|policy| {
          policy.disposition == PolicyDisposition::Enforce
            && policy
              .directive_set
              .iter()
              .any(|directive| directive.name == "sandbox")
        })
      });
    if client.is_nested_browsing_context || sandboxed {
      return Err(denied);
    }
    let Origin::Origin(origin) = &request.origin else {
      return Err(denied);
    };
    let state = self.0.lock().map_err(|_| denied)?;
    let url = if origin.is_tuple() {
      // This value comes from Servo's request origin, never from JavaScript,
      // the request target, a referrer, or the webview's latest URL.
      let serialized = origin.ascii_serialization();
      let current = state.top_url.as_ref().ok_or(denied)?;
      if current.origin().ascii_serialization() != serialized {
        return Err(denied);
      }
      Url::parse(&serialized).map_err(|_| denied)?
    } else {
      // Custom app schemes have opaque origins in Servo. Only the exact
      // engine pipeline that received our main-document response can use
      // that local URL. Remote, sandboxed, and data documents cannot borrow it.
      let pipeline = request.pipeline_id.map(u64::from).ok_or(denied)?;
      let (known_pipeline, local_url) = state.local_document.as_ref().ok_or(denied)?;
      if pipeline != *known_pipeline {
        return Err(denied);
      }
      local_url.clone()
    };
    Ok(AuthenticatedSource {
      url,
      epoch: state.epoch,
    })
  }
}

fn body_error(message: &str) -> NetworkError {
  NetworkError::ResourceLoadError(message.into())
}

struct BodyLease(RequestBody);

impl BodyLease {
  fn send(&self, message: BodyChunkRequest) -> Result<(), NetworkError> {
    let stream = self.0.clone_stream();
    let stream = stream.lock();
    stream
      .as_ref()
      .ok_or_else(|| body_error("request body stream is closed"))?
      .send(message)
      .map_err(|_| body_error("request body stream disconnected"))
  }
}

impl Drop for BodyLease {
  fn drop(&mut self) {
    self.0.close_stream();
  }
}

pub(super) async fn read_request_body(
  body: Option<RequestBody>,
  limit: usize,
) -> Result<Vec<u8>, NetworkError> {
  let Some(body) = body else {
    return Ok(Vec::new());
  };
  let body = BodyLease(body);
  if body.0.len().is_some_and(|length| length > limit) {
    return Err(body_error("request body exceeds the configured byte limit"));
  }
  let (sender, receiver) =
    ipc::channel().map_err(|_| body_error("failed to create request body channel"))?;
  let mut stream = receiver.to_stream();
  body.send(BodyChunkRequest::Connect(sender))?;
  let mut bytes = Vec::with_capacity(body.0.len().unwrap_or(0));

  loop {
    body.send(BodyChunkRequest::Chunk)?;
    match stream.next().await {
      Some(Ok(BodyChunkResponse::Chunk(chunk))) => {
        if chunk.len() > limit.saturating_sub(bytes.len()) {
          return Err(body_error("request body exceeds the configured byte limit"));
        }
        bytes.extend_from_slice(&chunk);
      }
      Some(Ok(BodyChunkResponse::Done)) => return Ok(bytes),
      Some(Ok(BodyChunkResponse::Error)) => return Err(body_error("request body stream failed")),
      Some(Err(_)) | None => return Err(body_error("request body stream disconnected")),
    }
  }
}

#[cfg(test)]
mod tests {
  use super::*;
  use content_security_policy::{CspList, PolicySource};
  use net_traits::{
    blob_url_store::UrlWithBlobClaim,
    policy_container::PolicyContainer,
    request::{
      BodySource, InsecureRequestsPolicy, PreloadedResources, Referrer, RequestBuilder,
      RequestClient,
    },
  };
  use servo::ServoUrl;
  use servo_base::{
    generic_channel::GenericSharedMemory,
    id::{PipelineId, PipelineNamespace, PipelineNamespaceId},
  };

  fn request(origin: &str, nested: bool) -> Request {
    let origin = ServoUrl::parse(origin).unwrap().origin();
    let client = RequestClient {
      preloaded_resources: PreloadedResources::default(),
      policy_container: PolicyContainer::default(),
      origin: Origin::Origin(origin.clone()),
      is_nested_browsing_context: nested,
      insecure_requests_policy: InsecureRequestsPolicy::DoNotUpgrade,
      has_trustworthy_ancestor_origin: false,
    };
    RequestBuilder::new(
      None,
      UrlWithBlobClaim::from_url_without_having_claimed_blob(
        ServoUrl::parse("ipc://localhost/test").unwrap(),
      ),
      Referrer::NoReferrer,
    )
    .origin(origin)
    .client(client)
    .build()
  }

  fn pipeline() -> PipelineId {
    PipelineNamespace::install(PipelineNamespaceId(73));
    PipelineId::new()
  }

  #[test]
  fn remote_origin_is_not_replaced_by_the_local_document_url() {
    let tracker = SourceTracker::default();
    tracker.observe_url(&Url::parse("https://remote.example/page").unwrap());
    tracker.accept_document(Some((1, 7, Url::parse("tauri://localhost/").unwrap())));
    let source = tracker
      .authenticate(&request("https://remote.example/page", false))
      .unwrap();
    assert_eq!(source.url.as_str(), "https://remote.example/");
  }

  #[test]
  fn opaque_app_origin_requires_the_exact_served_pipeline() {
    let tracker = SourceTracker::default();
    let mut request = request("tauri://localhost/", false);
    let pipeline = pipeline();
    request.pipeline_id = Some(pipeline);
    assert!(tracker.authenticate(&request).is_err());
    tracker.accept_document(Some((
      0,
      u64::from(pipeline),
      Url::parse("tauri://localhost/").unwrap(),
    )));
    assert_eq!(
      tracker.authenticate(&request).unwrap().url.as_str(),
      "tauri://localhost/"
    );
    request.pipeline_id = Some(PipelineId::new());
    assert!(tracker.authenticate(&request).is_err());
  }

  #[test]
  fn opaque_data_documents_have_no_local_identity() {
    let tracker = SourceTracker::default();
    assert!(tracker
      .authenticate(&request("data:text/html,remote", false))
      .is_err());
  }

  #[test]
  fn rejects_frames_even_with_an_app_origin() {
    let tracker = SourceTracker::default();
    assert!(tracker
      .authenticate(&request("http://tauri.localhost/", true))
      .is_err());
    assert!(tracker
      .authenticate(&request("https://remote.example/", true))
      .is_err());
  }

  #[test]
  fn rejects_enforced_sandbox_but_not_report_only_policy() {
    let tracker = SourceTracker::default();
    tracker.observe_url(&Url::parse("http://tauri.localhost/").unwrap());
    let mut request = request("http://tauri.localhost/", false);
    request.client.as_mut().unwrap().policy_container.csp_list = Some(CspList::parse(
      "sandbox allow-scripts",
      PolicySource::Header,
      PolicyDisposition::Enforce,
    ));
    assert!(tracker.authenticate(&request).is_err());
    request.client.as_mut().unwrap().policy_container.csp_list = Some(CspList::parse(
      "sandbox allow-scripts",
      PolicySource::Header,
      PolicyDisposition::Report,
    ));
    assert!(tracker.authenticate(&request).is_ok());
  }

  #[test]
  fn rejects_missing_client_and_unresolved_origin() {
    let tracker = SourceTracker::default();
    let mut request = request("http://tauri.localhost/", false);
    request.client = None;
    assert!(tracker.authenticate(&request).is_err());
    let mut request = self::request("http://tauri.localhost/", false);
    request.origin = Origin::Client;
    assert!(tracker.authenticate(&request).is_err());
  }

  #[test]
  fn navigation_revokes_queued_calls_and_late_document_responses() {
    let tracker = SourceTracker::default();
    tracker.observe_url(&Url::parse("https://remote.example/").unwrap());
    let source = tracker
      .authenticate(&request("https://remote.example/", false))
      .unwrap();
    tracker.observe_url(&Url::parse("tauri://localhost/").unwrap());
    assert!(!tracker.is_current(&source));
    tracker.accept_document(Some((
      source.epoch,
      7,
      Url::parse("tauri://localhost/").unwrap(),
    )));
    assert!(tracker.0.lock().unwrap().local_document.is_none());
  }

  #[test]
  fn old_tuple_origin_cannot_join_a_replacement_documents_epoch() {
    let tracker = SourceTracker::default();
    tracker.observe_url(&Url::parse("http://tauri.localhost/").unwrap());
    let old_request = request("http://tauri.localhost/", false);
    assert!(tracker.authenticate(&old_request).is_ok());
    tracker.observe_url(&Url::parse("https://remote.example/").unwrap());
    assert!(tracker.authenticate(&old_request).is_err());
    assert!(tracker
      .authenticate(&request("https://remote.example/", false))
      .is_ok());
  }

  #[test]
  fn data_navigation_revokes_an_opaque_app_documents_identity() {
    let tracker = SourceTracker::default();
    let mut request = request("tauri://localhost/", false);
    request.pipeline_id = Some(pipeline());
    tracker.observe_url(&Url::parse("tauri://localhost/").unwrap());
    tracker.accept_document(Some((
      tracker.epoch().unwrap(),
      u64::from(request.pipeline_id.unwrap()),
      Url::parse("tauri://localhost/").unwrap(),
    )));
    assert!(tracker.authenticate(&request).is_ok());
    tracker.observe_url(&Url::parse("data:text/html,replacement").unwrap());
    assert!(tracker.authenticate(&request).is_err());
  }

  #[test]
  fn nested_navigation_cannot_register_a_local_document() {
    let tracker = SourceTracker::default();
    let mut request = request("tauri://localhost/", true);
    request.mode = RequestMode::Navigate;
    request.pipeline_id = Some(pipeline());
    assert!(tracker.document_candidate(&request).is_none());
  }

  fn body_stream(chunks: Vec<Vec<u8>>, advertised: Option<usize>, fail: bool) -> RequestBody {
    let (sender, receiver) = ipc::channel().unwrap();
    std::thread::spawn(move || {
      let Ok(BodyChunkRequest::Connect(sender)) = receiver.recv() else {
        return;
      };
      for chunk in chunks {
        if !matches!(receiver.recv(), Ok(BodyChunkRequest::Chunk)) {
          return;
        }
        if sender
          .send(BodyChunkResponse::Chunk(GenericSharedMemory::from_bytes(
            &chunk,
          )))
          .is_err()
        {
          return;
        }
      }
      if matches!(receiver.recv(), Ok(BodyChunkRequest::Chunk)) {
        let _ = sender.send(if fail {
          BodyChunkResponse::Error
        } else {
          BodyChunkResponse::Done
        });
      }
    });
    RequestBody::new(sender, BodySource::Object, advertised)
  }

  #[test]
  fn reads_real_binary_body_chunks_and_closes_the_stream() {
    let body = body_stream(vec![vec![0, 255], vec![10, 0]], Some(4), false);
    let bytes = tauri::async_runtime::block_on(read_request_body(Some(body.clone()), 4)).unwrap();
    assert_eq!(bytes, [0, 255, 10, 0]);
    assert!(body.clone_stream().lock().is_none());
  }

  #[test]
  fn rejects_advertised_and_streamed_body_overflows() {
    for advertised in [Some(5), None] {
      let body = body_stream(vec![vec![1, 2, 3, 4, 5]], advertised, false);
      assert!(tauri::async_runtime::block_on(read_request_body(Some(body.clone()), 4)).is_err());
      assert!(body.clone_stream().lock().is_none());
    }
  }

  #[test]
  fn rejects_stream_errors_and_disconnects() {
    let body = body_stream(Vec::new(), None, true);
    assert!(tauri::async_runtime::block_on(read_request_body(Some(body), 4)).is_err());
    let (sender, receiver) = ipc::channel::<BodyChunkRequest>().unwrap();
    drop(receiver);
    let body = RequestBody::new(sender, BodySource::Object, None);
    assert!(tauri::async_runtime::block_on(read_request_body(Some(body), 4)).is_err());
  }

  #[test]
  fn accepts_missing_and_empty_bodies() {
    assert!(tauri::async_runtime::block_on(read_request_body(None, 4))
      .unwrap()
      .is_empty());
    let body = body_stream(Vec::new(), Some(0), false);
    assert!(
      tauri::async_runtime::block_on(read_request_body(Some(body), 4))
        .unwrap()
        .is_empty()
    );
  }

  #[test]
  fn cancelling_a_pending_body_read_closes_its_control_stream() {
    use futures_util::FutureExt;

    let (sender, receiver) = ipc::channel::<BodyChunkRequest>().unwrap();
    let body = RequestBody::new(sender, BodySource::Object, None);
    assert!(read_request_body(Some(body.clone()), 4)
      .now_or_never()
      .is_none());
    assert!(body.clone_stream().lock().is_none());
    drop(receiver);
  }
}
