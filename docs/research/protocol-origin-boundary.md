# Protocol routing and IPC identity

Status: Windows asset adapter implemented; source-authenticated IPC and native
security proof remain release blockers. This document records source findings,
not a reproduced native exploit or a completed security assessment.

## Verified dependency surface

The audit used published Servo `0.5.0`, Tauri `2.11.5`, and `tauri-runtime`
`2.11.3`, matching Turvo's exact pins. Current documentation was checked through
Context7 and the pinned crate sources were used for API details.

Tauri emits `http://tauri.localhost` or `https://tauri.localhost` on Windows.
Servo's protocol registry cannot register `http` or `https`, so the app's
registered `tauri` handler alone cannot serve those URLs. The runtime now shares
its immutable handler set with both `WebViewDelegate::load_web_resource` and
`ServoDelegate::load_web_resource`. The latter also receives loads not attached
to a webview, such as worker-originated loads.

On Windows, only exact registered `<scheme>.localhost` names are claimed.
Unrelated requests continue through Servo. Credentials and nondefault ports
on registered names are rejected instead of falling through to a loopback
server. A dropped response fails closed with an error. On other platforms the
existing custom-scheme registry remains the loading path.

## Why this is not IPC authentication

The bootstrap's `show_console_message` bridge supplies `webview.url()` as the
IPC request URI. Servo's callback carries the webview, log level, and message,
but no initiating frame or document identity. The bootstrap also forwards
every initialization script without honoring Tauri's main-frame-only flag.
Those source facts are insufficient to establish remote-frame isolation.

Servo `0.5.0` exposes different metadata on its two loading paths:

- `WebResourceRequest` includes URL, method, headers, destination, referrer,
  and main-frame/redirect indicators, but neither request origin nor body.
- The lower-level protocol `Request` has an origin, client, pipeline ID, and
  request-body stream. It still needs a correct adapter; the bootstrap only
  forwards an empty body and the received headers.
- `request_interceptor.rs` runs before the normal HTTP loader inserts an
  engine-derived `Origin` header. Preserving existing headers is correct;
  inventing a missing origin from the target URL or referrer is not.
- `servo-url` treats unknown schemes such as `tauri` as opaque origins. A
  string comparison against a top-level custom URL cannot identify a remote
  or sandboxed frame's actual initiating document.
- The interceptor executes before normal scheme/CORS processing. Native
  regression tests must also audit cross-origin resource access and CSP
  behavior; an intercepted response is not evidence those policies ran.

The W02I/V02I graph pair therefore owns a source-authenticated transport,
main-frame script scoping, and native positive/negative tests. It must either
reuse a sufficient published Servo API or record a public compatibility
proposal and explicit release blocker. No hardcoded origin or console-derived
identity fallback is acceptable.

## Required native cases

1. A bundled local page invokes an allowed command and receives its payload.
2. A remote top-level page cannot exercise the local capability.
3. A remote iframe cannot borrow its local parent's identity.
4. An opaque or sandboxed document is not promoted to the local app origin.
5. A call queued across navigation cannot inherit the new document's trust.
6. Channel fetches, binary payloads, and both event directions retain their
   semantics without broadening capability scope.
7. Intercepted assets do not silently bypass the intended cross-origin and
   content-security policies.

The adapter unit tests and compile matrix are deliberately narrower receipts.

## Source anchors

- [Tauri 2.11.5 app protocol URL selection](https://docs.rs/crate/tauri/2.11.5/source/src/manager/mod.rs)
- [Tauri 2.11.5 IPC parsing](https://docs.rs/crate/tauri/2.11.5/source/src/ipc/protocol.rs)
- [Servo 0.5.0 webview delegate](https://docs.rs/crate/servo/0.5.0/source/webview_delegate.rs)
- [Servo 0.5.0 request interception](https://docs.rs/crate/servo-net/0.5.0/source/request_interceptor.rs)
- [Servo 0.5.0 fetch ordering](https://docs.rs/crate/servo-net/0.5.0/source/fetch/methods.rs)
- [Servo 0.5.0 origin representation](https://docs.rs/crate/servo-url/0.5.0/source/origin.rs)
