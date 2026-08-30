# Turvo

Turvo is an experimental Tauri desktop runtime backed by Servo. It embeds one
version of the renderer in the application so Linux, Windows, and macOS do not
silently select different system webviews.

The project is aiming for an Electron-class application shell without bundling
Chromium. Performance, memory, startup-time, and binary-size claims are
deliberately deferred until Turvo has a reproducible benchmark suite.

## Current status

Turvo is pre-release software. The repository currently contains:

- an in-process Servo 0.5.0 runtime over Tao and `tauri-runtime` 2.11.3;
- Tauri `Runtime`, `RuntimeHandle`, window, and webview dispatcher
  implementations;
- bundled-asset/custom-protocol plumbing and a Servo-compatible Tauri IPC
  bridge;
- a `turvo::builder()` entry point;
- opt-in Firefox remote devtools via `builder_with_options`;
- a minimal bundled-HTML example;
- an API probe for invoke, events, and runtime-managed windows; and
- compile/test CI definitions for Linux, Windows, and macOS.

Cross-platform compilation is not the same as cross-platform runtime proof.
The native IPC/security fixture passes on Linux and macOS. Windows boots with
ANGLE and reaches IPC, but its mapped-asset path fails cross-origin and CSP
checks. Ordinary app `fetch()` and module compatibility also remain unresolved.
Do not use this bootstrap in production or load untrusted remote pages/frames.
The [protocol audit](https://github.com/Travis-Gilbert/Turvo/blob/main/docs/research/protocol-origin-boundary.md)
records the engine API limitations and required negative tests.

The acceptance matrix in
[Record 001](https://github.com/Travis-Gilbert/Turvo/blob/main/docs/records/001-turvo-bootstrap.md)
tracks which behaviors are wired, compiled, and actually observed.

## Quickstart

Turvo 0.1.0 is not published yet. The two edits below describe the release
interface; until publication, use the checked-out examples in this repository.

Disable Tauri's default Wry runtime and add Turvo:

```toml
[dependencies]
tauri = { version = "=2.11.5", default-features = false, features = [
  "common-controls-v6",
] }
turvo = "0.1.0"
```

Then change the application builder:

```rust
fn main() {
  turvo::builder()
    .run(tauri::generate_context!())
    .expect("failed to run the application");
}
```

For Firefox remote debugging, configure a non-zero loopback port before the
first webview starts.

```rust
fn main() {
  let options = turvo::TurvoOptions::default()
    .try_with_devtools_port(7000)
    .expect("the DevTools port must be non-zero")
    // Servo calls this only when a client did not present its generated token.
    // Replace this development-only approval with an application prompt.
    .with_devtools_connection_handler(|| cfg!(debug_assertions));

  turvo::builder_with_options(options)
  .expect("Turvo options were configured too late")
  .run(tauri::generate_context!())
  .expect("failed to run the application");
}
```

Connect from Firefox's `about:debugging` page. Turvo binds the server to
`127.0.0.1`. Tokenless clients are denied unless the application-supplied
connection handler approves them. A `with_devtools_server_handler` callback is
available for clients that can use Servo's generated authentication token;
Turvo redacts that token from debug output and never logs it.

Turvo 0.1 attaches a fixed DevTools port to the first Servo engine only. Port
`0` is rejected because Servo 0.5 does not report its actual ephemeral port to
the embedder.

## Example

```sh
cargo run -p helloworld
cargo run -p turvo-api
```

The first Servo build is large. Keep `MOZJS_FROM_SOURCE` unset so `mozjs_sys`
can use a prebuilt SpiderMonkey artifact where one is available. Do not start a
local build without ample free disk space; hosted CI is the authoritative
three-platform compile lane for this repository.

## Engine policy

- `main` pins the current Servo LTS release exactly.
- `next` is the monthly migration lane. Its scheduled workflow asks a coding
  agent to update Servo and repair API churn. The agent receives prefetched
  dependencies but no GitHub token or shell network access; fresh jobs validate
  its scoped patch and open a draft PR against `next`.
- A failing `next` migration does not block `main`; it is an early warning for
  the next LTS update.

The scheduled agent workflow expects an `OPENAI_API_KEY` Actions secret. Its
default model is GPT-5.3 Codex Spark and can be overridden with the
`TURVO_MIGRATION_MODEL` repository variable.

## Scope

Turvo is an application shell for content the application ships. Compatibility
with arbitrary third-party websites is not a project goal. Mobile targets keep
Tauri's Wry runtime; Turvo is desktop-only.

For an application that also ships on mobile, make the runtime dependency
target-specific so the desktop graph does not enable Wry and the mobile graph
does not compile Turvo:

```toml
[target.'cfg(not(any(target_os = "android", target_os = "ios")))'.dependencies]
tauri = { version = "=2.11.5", default-features = false, features = [
  "common-controls-v6",
] }
turvo = "0.1.0"

[target.'cfg(any(target_os = "android", target_os = "ios"))'.dependencies]
tauri = { version = "=2.11.5" }
```

Select `turvo::builder()` in the desktop entry point and
`tauri::Builder::default()` in the mobile entry point. Keep application setup
behind a shared function so runtime selection is the only platform-specific
branch.

## Provenance

The runtime began from the dual-licensed implementation in
[`copse-dev/tauri-runtime-servo`](https://github.com/copse-dev/tauri-runtime-servo)
at commit
[`b9d4ef11`](https://github.com/copse-dev/tauri-runtime-servo/commit/b9d4ef11a5493b730172dca2dcba927987b93d1f).
Original copyright and SPDX headers are preserved. Turvo's changes include the
public builder API, exact engine policy, devtools configuration, acceptance
tracking, and the maintenance workflows.

## License

Licensed under either [MIT](LICENSE-MIT) or
[Apache-2.0](LICENSE-APACHE-2.0), at your option. Servo remains MPL-2.0 as a
dependency.
