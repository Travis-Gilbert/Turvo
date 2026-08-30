# Lessons and constraints

Canonical SHA-256: `c59f59c06fe9833be173f484504acd20e115bb05a9dd24fd761801df446001a3`

## Current facts

- `F01`: Bootstrap tip a54063aed480922cc0b636371d041a674d158fc4 is public on Travis-Gilbert/Turvo main; CI run 33326854324 proved Linux and macOS runtime tests and lint, then exposed missing example icons plus Tauri's known Windows test-manifest entry-point failure.
- `F02`: The active Turvo dependency tree exact-pins Servo 0.5.0, Tauri 2.11.5, tauri-runtime 2.11.3, and Tao 0.37.0 without tauri-runtime-wry.
- `F03`: Tauri 2.11.5 generates http://tauri.localhost for Windows app assets, while Turvo currently registers only the tauri custom protocol and does not implement Servo HTTP resource interception.
- `F04`: Turvo currently discards pending.new_window_handler; tauri-runtime 2.11.3 NewWindowOpener embeds Wry-native WebKitGTK, WebView2, or WKWebView objects.
- `F05`: The configured Cargo target volume was 99 percent utilized with approximately 9 GiB free at charting, so hosted CI outranks a fresh local Servo build until storage is made safe.
- `F06`: CI run 33327853233 made format/package plus complete Ubuntu and macOS jobs green; Windows passed all 24 Turvo unit tests but the downstream public_api test still lacked the Common Controls v6 manifest, proving the fix must be emitted by Turvo's own build script.
- `F07`: CI run 33328684442 confirmed the Turvo-owned manifest fix: Windows runtime unit tests, public_api integration tests, and Clippy all passed. Its hello-world build then exposed the separate missing ICO requirement in tauri-build; Ubuntu and macOS remained fully green.
- `F08`: Pinned-source audit found that the bootstrap console IPC callback substitutes the top-level WebView URL for the unknown sending frame, and ignores initialization-script main-frame flags. Servo 0.5.0 WebResourceRequest exposes neither request origin nor body and interception precedes HTTP Origin-header insertion. Asset routing tests cannot discharge the IPC source-authentication obligation; W02I and V02I now own that separate gate. This is source evidence, not a reproduced native exploit.
- `F09`: Commit 750d6422f7781f408bcc2f7759b942d0f57b2d1c passed CI run 33329627108: format/package job 99305763884, macOS 99305763947, Linux 99305763979, Windows 99305763986. Every desktop job passed runtime tests, Clippy, hello-world, and API-example builds. Tracked next was created from that verified commit. Native application behavior remains unverified.
- `F10`: Commit 7813baa3529e6db53113e30adfc4242de65ee276 passed run 33330884047: jobs 99309104737, 99309104910, 99309104920, 99309104928. All desktop targets passed 31 unit tests (including seven new protocol tests), two public API tests, Clippy, and both examples. Next independently passed its baseline run 33330599055.
- `F11`: Servo 0.5.0 navigation.rs sets each document request's pipeline_id from the new engine pipeline; fetch.rs assigns fetches the calling global's pipeline_id and client. The lower-level published protocol Request also has the actual Origin and a body stream. This is a candidate source-authenticated IPC path, not a native security receipt; opaque and sandboxed documents and consumer fork type coherence require explicit tests.
- `F12`: Run 33332319128 at 51237b74cf85108ec78600527ff735cc81630a49 passed format/package and five Node transport tests. All Rust targets stopped at an unresolved servo_net_traits import before runtime tests. Pinned manifests declare library names net_traits and servo_base for packages servo-net-traits and servo-base respectively; imports were corrected from those exact declarations. Native proof is still pending.
- `F13`: Pinned Tauri protocol/tauri.rs strips tauri://localhost to derive asset paths; Wry reverses the Windows HTTP mapping only for the handler-facing URI. The adapter now follows that lookup contract without changing the browser response URL or Origin. Servo fetch/methods.rs also treats fetchable custom protocols as basic responses before the normal CORS path, so a real cross-origin asset canary was added to the native security fixture. This is an open policy-risk probe, not yet a native receipt.
- `F14`: Commit aa639664be21a94d7a30da9525921f36c94817a8 passed all jobs in run 33332869372 (99314527731, 99314527798, 99314527824, 99314527916). Every desktop passed 47 unit tests, two public API tests, Clippy, and both examples; five Node transport tests also passed. Real request-body streaming, cancellation, caller-provenance logic, and main-frame script handling are compile/unit verified. W02I remains working until the new native adversarial fixture passes.

## Explicit exclusions

- No arbitrary third-party web compatibility commitment.
- No offscreen GPUI compositor implementation in the 0.1.0 windowed release; only its follow-on plan is required.
- No performance, memory, startup, or binary-size claim before a reproducible benchmark receipt.
- No unsafe fabrication of Tauri NewWindowOpener platform objects.
- No force-push, history rewrite, credential disclosure, or unrelated dirty-worktree cleanup.
