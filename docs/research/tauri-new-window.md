# Runtime-neutral `window.open` seam

## Finding and proposal

At Tauri `tauri-v2.11.5` / commit
`7cd71369c00978a3783b6ae3e9972358abbe4ae6`, `NewWindowFeatures::new` requires
`NewWindowOpener`, whose desktop fields contain real WebKit or WebView2 objects.
Servo cannot construct these legitimately. The existing callback is otherwise
runtime-generic, including its create/allow/deny response.

The versioned proposal in `patches/tauri` adds:

- `RuntimeNewWindowOpener`, an opaque `Arc<dyn Any + Send + Sync>` token with
  typed access and content-free debug output;
- `NewWindowFeatures::new_for_runtime` plus optional native/runtime accessors;
- a default-rejecting `WindowBuilder::with_runtime_new_window_opener` method;
- private storage in the core webview-window builder, which forwards the token
  before window creation and propagates rejection.

The runtime stores a thread-safe request identity in the token. Its engine-owned
registry retains the actual, possibly thread-affine request. A matching Rust
type is not authorization: the runtime must still check engine ownership,
request lifetime, and one-shot consumption. Cloning a token is not permission
to create a second child. Dropped, denied, expired, or foreign requests must not
leave a child or an unresolved engine response.

## Compatibility boundary

The existing native constructor and `opener()` signature are unchanged. Wry's
native opener creation and WebKit/WebView2 configuration remain unchanged. The
new hook has a default implementation, so existing runtime implementors need
not add a method. No field is added to the public, exhaustive
`WebviewAttributes` or `PendingWindow` structs.

There is one explicit API tradeoff: calling the legacy native-only `opener()`
on a newly introduced runtime-owned feature value panics. A safe native object
cannot be returned for Servo while retaining the old non-optional return type.
Runtime-neutral consumers must use the new optional accessors; the core
`window_features` method does so. Existing Wry-originated values retain their
old behavior. This tradeoff needs upstream API review before integration.

## Tests and evidence

Four runtime unit tests cover geometry/type preservation, shared token identity
across threads, redacted debug formatting, and the documented legacy-accessor
failure. Compile-time signature checks retain the native constructor/accessor
contract. Two core integration tests use Tauri's real `MockRuntime`: ordinary
window creation still succeeds, and a runtime-owned opener is rejected before
a child is created when the runtime has not opted in.

The mock tests run with Tauri's default test dependencies, which themselves
enable Wry. They exercise a **mock runtime**, not a Wry-free test binary. A
separate `cargo check -p tauri --no-default-features --lib --locked` checks the
no-Wry library configuration. Neither check proves Servo child-window behavior.

Local formatting and patch whitespace checks pass. At `bc49469`,
[run 33336218434](https://github.com/Travis-Gilbert/Turvo/actions/runs/33336218434)
passed all three platforms. Each ran the four token tests, no-Wry core
compilation, and two MockRuntime contract tests. Existing Tauri core tests
passed 55 on Linux, 56 on macOS, and 57 on Windows. Jobs are 99323466184,
99323466208, and 99323466234 respectively.

The first Windows attempt in run 33335848522 stopped at formatting because its
checkout converted upstream files to CRLF. Preserving LF before checkout fixed
that environment defect without changing the patch. MSRV/mobile coverage,
positive Servo opener consumption, opener navigation/close races, and
visual/native child-window behavior are not discharged by these tests.

## Integration and external gate

The exact Servo `0.5.0` source adds another integration constraint:
`CreateNewWebViewRequest` contains an engine handle and a one-shot responder,
and its public method is `builder(rendering_context)`. It does **not** expose
the requested target URL, position, or size. The token can retain that real
creation request on the engine thread, but it cannot manufacture missing
callback metadata. Full compatibility with Tauri's URL-bearing
`on_new_window` callback needs a validated engine design or an accepted public
metadata API. Passing the parent URL or an invented `about:blank` value is
not a verified substitute. This source finding is not proof that a particular
future two-phase or navigation-based design cannot work.

Turvo must not create fake native handles or silently treat `window.open` as a
fresh unrelated webview. Once a public revision is approved, its adapter must
map Servo's actual new-window request to the token, retain the engine response,
create the child in the same engine context, and settle create/deny exactly once.
That implementation and its native tests belong to W04/V04.

Tauri's pinned contribution guide requires review and testing of AI-generated
content before submission and prohibits AI-written review replies except
translations. This run therefore prepares a reviewable patch and tests it in
Turvo's public CI; it does not impersonate human review or submit an upstream PR.
E01 still requires an accepted release or explicitly approved public revision.
W03 remains parked, with these partial receipts retained, until the complete
Servo-sufficiency review can pass. A separate read-only source pass found the
metadata gap above; this is not an independent-agent or maintainer approval.

Source anchors:

- [Servo 0.5.0 creation request and delegate](https://docs.rs/crate/servo/0.5.0/source/webview_delegate.rs)
- [Servo 0.5.0 responder-backed webview builder](https://docs.rs/crate/servo/0.5.0/source/webview.rs)
- [Pinned Tauri native opener contract](https://github.com/tauri-apps/tauri/blob/7cd71369c00978a3783b6ae3e9972358abbe4ae6/crates/tauri-runtime/src/webview.rs)
