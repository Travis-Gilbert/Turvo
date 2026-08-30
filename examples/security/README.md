# Native IPC security probe

This is a test-only application. It deliberately shares its ephemeral invoke
key with adversarial fixture pages through an in-process, loopback-only HTTP
server. Never reuse that server or its configuration endpoint in a product.

Build with `cargo build -p turvo-security --locked`, then launch the resulting
binary with `python scripts/run-native-smoke.py <binary-path>`. Linux requires
`dbus-run-session` and `xvfb-run`; CI supplies a software OpenGL display.
Windows uses Servo's published ANGLE backend. CI first builds the tests with
`scripts/build_windows.py`, which stages `libEGL.dll` and `libGLESv2.dll` from
the exact Cargo-reported mozangle output beside binaries and test executables.
It fails on missing or ambiguous outputs instead of searching stale artifacts.
Clean-machine bundle packaging and hardware performance remain separate gates.

The application has a 120-second deadline and the runner has an independent
180-second deadline. A successful receipt requires:

- real JSON, raw-protocol, binary, and large-channel round trips;
- Tauri events in both directions;
- local document layout and CSP-blocked network and bundled image requests;
- rejected commands from remote, local-child, sandboxed, and opaque frames;
- rejection of cross-origin bundled-asset reads;
- rejected remote, sandboxed-local, and opaque top-level callers; and
- restored local IPC with no extra native calls from the old document's
  queued requests during navigation.

The navigation stress case complements the deterministic generation-revocation
unit tests; it does not claim exhaustive coverage of every possible scheduling
interleaving. Layout and animation callbacks are not pixel/screenshot proof.
Native smoke receipts and visual-rendering receipts remain separate gates.

Servo 0.5.0 treats `tauri://` origins as opaque, so this fixture explicitly
allows `tauri:` scripts and frames. A passing IPC receipt therefore does not
prove that an existing Tauri application's `'self'` policy works unchanged.
That compatibility gap remains a release blocker, not a recommended product
CSP adjustment. The `img-src 'none'` canaries must still block both network
and intercepted bundled assets before their handlers are reached.
Ordinary custom protocols are intentionally not marked fetchable: Servo's
flag bypasses CORS rather than enabling a same-origin policy. Local `fetch()`
and module-script compatibility consequently need an engine-level solution;
the authenticated IPC protocols are the only callers of that exemption.

All negative calls carry the same valid test key used by a successful local
positive control. The test checks actual Rust handler counts independently of
the JavaScript responses. Missing/duplicate reports and unexpected native
calls fail the receipt. The runner retains sanitized logs under `.reports/`.

The fixture reuses [tiny_http](https://docs.rs/tiny_http/0.12.0/tiny_http/)
for HTTP parsing and Tauri's [application command permissions](https://v2.tauri.app/security/capabilities/)
for its local-only capability manifest.
