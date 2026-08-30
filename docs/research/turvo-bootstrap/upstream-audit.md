# Turvo upstream audit

Date: 2026-08-30

## Question

What should Turvo reuse, and which parts of the handoff are already proven or
blocked by current Tauri and Servo APIs?

## Findings

1. The current published engine/runtime set is Servo 0.5.0,
   `tauri-runtime` 2.11.3, and Tauri 2.11.5. The `turvo` crate name is not
   present in the crates.io index as of this audit.
2. [`copse-dev/tauri-runtime-servo`](https://github.com/copse-dev/tauri-runtime-servo)
   already implements the bulk of the required in-process runtime: Tao event
   integration, Tauri runtime traits, per-window Servo rendering contexts,
   input forwarding, custom protocols, and a postMessage IPC bridge. Rewriting
   those layers independently would add risk without adding product value.
3. Upstream CI run
   [`32959507850`](https://github.com/copse-dev/tauri-runtime-servo/actions/runs/32959507850)
   passed tests, Clippy, and a hello-world build for Linux, Windows, and macOS
   at commit `b9d4ef11`. Those jobs compile the example; they do not launch a
   native window or prove asset loading, IPC, origins, or input behavior.
4. The published runtime leaves Tauri's `new_window_handler` unused. More
   importantly, `tauri-runtime` 2.11.3 defines `NewWindowOpener` in terms of
   WebKitGTK, WebView2, and WKWebView native objects. A Servo runtime cannot
   safely construct those values. `window.open` therefore needs an upstream
   runtime-trait generalization or an explicitly accepted Tauri patch; an
   unsafe placeholder is not viable.
5. Servo 0.5.0 exposes `WebView::rendering_context`, `ProtocolRegistry`, HTTP
   request interception through `WebResourceLoad`, and a Firefox-compatible
   devtools server. Turvo can use those public APIs directly.
6. Tauri maps bundled assets to `tauri://localhost` on Linux/macOS but to
   `http://tauri.localhost` on Windows. The imported runtime registers a
   `tauri` custom protocol, while Servo request interception is the available
   API for HTTP(S). The Windows build is green, but the source-level mapping
   still needs a native runtime test before local/remote origin behavior can be
   claimed.
7. The imported IPC bridge derives the invoke URL from the page's current URL
   instead of hardcoding an `Origin`. That is the right security direction:
   Tauri's capability resolver classifies the request URL as local or remote.
   Turvo now has source-level tests that preserve local and remote origins in
   the IPC request. It still needs capability-denial tests and native receipts
   on all three platforms.
8. The successful Windows job compiled `mozjs_sys` and `mozangle` and built the
   example without a separate Verso binary. This proves build graph coverage,
   not that every required runtime library is correctly bundled on a clean
   machine.
9. Servo validates its generated DevTools token before sending
   `RequestDevtoolsConnection` to the embedder. That callback represents a
   missing or invalid token and must default to deny. Servo 0.5 also reports
   the configured address port instead of the bound listener port, so port `0`
   cannot currently produce a discoverable endpoint.

## Decision

Import `copse-dev/tauri-runtime-servo@b9d4ef11` with attribution and preserve
its dual-license headers. Turvo owns the imported runtime source so its `next`
branch can absorb Servo churn. A thin facade dependency was rejected because
it could not repair upstream API changes or close Turvo's protocol, devtools,
and new-window gates.

## Immediate consequences

- Keep the proven implementation layout initially; split the large runtime
  module only when tests protect the extraction.
- Pin Servo and Tauri versions exactly in Turvo releases.
- Treat upstream cross-platform builds as inherited evidence only for the
  imported commit. Turvo changes require Turvo CI.
- Track `window.open` as an upstream prerequisite, not as implemented work.
- Do not publish performance or size claims before the benchmark record exists.

## Primary sources

- [Servo 0.5.0 crate documentation](https://docs.rs/servo/0.5.0/servo/)
- [Tauri runtime 2.11.3 traits](https://docs.rs/tauri-runtime/2.11.3/tauri_runtime/)
- [Tauri 2.11.5 crate documentation](https://docs.rs/tauri/2.11.5/tauri/)
- [Imported runtime source](https://github.com/copse-dev/tauri-runtime-servo/tree/b9d4ef11a5493b730172dca2dcba927987b93d1f)
- [Archived Verso runtime](https://github.com/versotile-org/tauri-runtime-verso)
