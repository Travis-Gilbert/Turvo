# Native IPC security probe

This is a test-only application. It deliberately shares its ephemeral invoke
key with adversarial fixture pages through an in-process, loopback-only HTTP
server. Never reuse that server or its configuration endpoint in a product.

Build with `cargo build -p turvo-security --locked`, then launch the resulting
binary with `python scripts/run-native-smoke.py <binary-path>`. Linux requires
`dbus-run-session` and `xvfb-run`; CI supplies a software OpenGL display.

The application has a 120-second deadline and the runner has an independent
180-second deadline. A successful receipt requires:

- real JSON, raw-protocol, binary, and large-channel round trips;
- Tauri events in both directions;
- local document layout and a CSP-blocked image request;
- rejected commands from remote, local-child, sandboxed, and opaque frames;
- rejection of cross-origin bundled-asset reads;
- rejected remote, sandboxed-local, and opaque top-level callers; and
- restored local IPC with no extra native calls from the old document's
  queued requests during navigation.

The navigation stress case complements the deterministic generation-revocation
unit tests; it does not claim exhaustive coverage of every possible scheduling
interleaving. Layout and animation callbacks are not pixel/screenshot proof.
Native smoke receipts and visual-rendering receipts remain separate gates.

All negative calls carry the same valid test key used by a successful local
positive control. The test checks actual Rust handler counts independently of
the JavaScript responses. Missing/duplicate reports and unexpected native
calls fail the receipt. The runner retains sanitized logs under `.reports/`.

The fixture reuses [tiny_http](https://docs.rs/tiny_http/0.12.0/tiny_http/)
for HTTP parsing and Tauri's [application command permissions](https://v2.tauri.app/security/capabilities/)
for its local-only capability manifest.
