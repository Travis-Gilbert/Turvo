# Protocol routing and IPC identity

Status: Windows asset adapter verified at commit `7813baa`; request-based IPC
adapter implemented but not yet natively verified. Native security proof
remains a release blocker. This document records source findings, not a
reproduced native exploit or a completed security assessment.

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

The handler-facing Windows URI is translated back to its registered scheme,
matching Wry's existing custom-protocol contract. This is a lookup-only
translation: `http://tauri.localhost/nested/app.js` is delivered to the asset
handler as `tauri://localhost/nested/app.js`, but the browser-visible response
URL and incoming headers retain their original values. Passing the HTTP URI
directly would make Tauri's resolver fall back to the root document for nested
assets. The native fixture exercises separate JavaScript and text resources.

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

## Candidate request-based transport

The console bridge has been removed. Standard Tauri invokes now use
`ipc://localhost/` on every desktop platform. The lower-level protocol adapter
reads actual JSON or binary request-body chunks through `ipc-channel`'s async
stream support, then forwards the engine-authenticated source to Tauri's
existing capability checker. Transport failures reject the call; they do not
fall back to console or metadata-only HTTP IPC.

Tuple origins are kept unchanged and must match the observed current top-level
origin. For opaque custom-scheme origins, only the exact engine pipeline that
received the successful main-document response can use its local app URL.
Nested clients, missing metadata, unresolved origins, and enforced CSP sandbox
clients are denied. Navigation revokes queued source tokens and late document
registrations. These are implementation rules requiring native validation,
not a claim that every engine provenance assumption has been proven.

The optional low-level `window.ipc.postMessage` hook uses the separate
`turvo-ipc:` fetch endpoint and the same source checks. Its queue wakes the main
event loop and rechecks the document generation before dispatch. Main-frame
initialization flags are honored with a `window === window.top` guard. Scripts
that intentionally share globals should use explicit `window` properties.

The adapter currently limits each custom-protocol request body to 16 MiB,
checking both advertised and streamed length. Dropping a pending read closes
its body stream. Applications with a CSP must allow `ipc:` in `connect-src`;
add `turvo-ipc:` only when using the low-level hook. These allowances enable the
transport, not permission to execute a command.

`servo-net-traits` is pinned to the same published engine version as `servo`.
A consumer replacing Servo with a fork must patch both crates to one coherent
revision; patching `servo` alone would leave incompatible request types from
two source trees. Turvo's own tests also directly use `servo-base` from that
engine family. The public Turvo package still has no private-fork dependency.

Focused Rust provenance/body tests and the Node transport tests do not replace
the required native cases below.

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
- [Servo 0.5.0 request provenance and body types](https://docs.rs/crate/servo-net-traits/0.5.0/source/request.rs)
- [Servo 0.5.0 navigation pipeline assignment](https://docs.rs/crate/servo-script/0.5.0/source/navigation.rs)
- [Servo 0.5.0 calling-global fetch metadata](https://docs.rs/crate/servo-script/0.5.0/source/fetch.rs)
- [ipc-channel 0.22 asynchronous streams](https://docs.rs/ipc-channel/0.22.0/ipc_channel/ipc/struct.IpcReceiver.html#method.to_stream)
