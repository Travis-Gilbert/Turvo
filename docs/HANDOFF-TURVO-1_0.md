# HANDOFF-TURVO-1.0

Turvo: a Tauri runtime backed by Servo. One engine, every desktop platform, no Chromium. Standalone public repo, consumed by Theorem but not owned by it.

Source conversation: claude.ai planning session, 2026-08-30. Named choices below are requirements, not suggestions.

## Goals

- Electron-class determinism for Tauri apps: the app ships its engine, so every user runs the identical renderer on Linux, Windows, and macOS
- Drop-in replacement for `tauri-runtime-wry`: swap the runtime, keep the app
- Servo churn absorbed by scheduled agent CI, not maintainer weekends; this is the structural fix for what killed Verso
- Broadly useful public artifact under its own repo, with Theorem as first consumer

## Desired end state

- Public repo `turvo` with the `turvo` crate published to crates.io (name verified available 2026-08-30)
- A Tauri app switches engines by replacing `tauri::Builder::new()` with `turvo::builder()` and disabling the `wry` default feature
- `main` branch pins the Servo LTS release; `next` branch tracks Servo monthly via scheduled agent-authored migration PRs
- TheoremWeb desktop (Tauri) runs on Turvo; `apps/browser` in the Theorem monorepo pins the same Servo rev, one engine across both hosts
- README promises determinism and engine independence; no performance or size claims until benchmarked

## Use cases

- Tauri developer wants one deterministic engine instead of three system webviews (the WebView2 vs WKWebView vs WebKitGTK compat matrix)
- Theorem desktop app renders its own chrome and surfaces through a pinned Servo it fully controls
- Agent-driven app shells and kiosk-style deployments where the vendor controls all shipped content
- Servo ecosystem gains a maintained embedder now that Verso is archived; contributions flow upstream where they generalize

## Details

### Named choices (requirements)

| Decision | Choice |
|---|---|
| Name | Turvo (Tauri x Servo). crates.io and GitHub clear; Turvo Inc. logistics SaaS exists in an unrelated class, accepted |
| Engine linkage | In-process `libservo` via the published `servo` crate. No versoview external binary, no Verso revival, no separate engine process |
| Servo pin (public repo) | crates.io `servo` LTS track (half-yearly majors, security updates between) |
| Servo pin (Theorem lane) | `Travis-Gilbert/servo` fork, `theorem/<upstream-tag>` branches, applied via `[patch]`; fork carries theorem patches, public repo never requires it |
| Tauri integration | Implement the `tauri-runtime` traits: `Runtime`, `RuntimeHandle`, webview and window dispatchers, event loop on `tao` |
| Tauri version policy | Track current stable (2.11.x at time of writing) with exact pins where the runtime traits force it, per the precedent in tauri-runtime-verso; includes the `NewWindowOpener` path from Tauri 2.8 |
| IPC | Real custom-scheme or request-interception serving with correct per-scheme origins so Tauri capability checks distinguish local from remote content. The hardcoded Origin header hack from tauri-runtime-verso is explicitly rejected |
| Devtools | Servo's Firefox devtools server, port configurable from the builder, documented `about:debugging` flow |
| Rendering v1 | Windowed: one Servo rendering context per `tao` window via `raw-window-handle` |
| Reference material | `versotile-org/tauri-runtime-verso` `runtime.rs` and `window.rs` (MIT) used as the map of what the Tauri runtime traits demand; code adapted, not vendored blind |
| Platforms | Linux, Windows, macOS. Mobile stays on wry; document the split-target setup (desktop deps + `wry` feature for mobile targets) |
| License | MIT OR Apache-2.0 dual. Servo is MPL-2.0, file-level copyleft, compatible as a dependency |
| Positioning | Electron-class shell for content you ship. Arbitrary-web compatibility is out of scope by definition; compat issues against third-party sites are closed as such |

### Churn model (deliverable, not habit)

- `main`: Servo LTS. Upgrades land as reviewed PRs on the LTS cadence with migration notes
- `next`: scheduled workflow bumps to the latest Servo monthly release, builds all three platforms, runs the example smoke suite, and opens a migration PR authored by an agent head when the API breaks
- A failing `next` never blocks `main`; it is the early-warning system for the following LTS

### Follow-on work, own planning threads

- Offscreen rendering mode: Servo composited into a wgpu texture for GPUI-hosted surfaces (the Theorem instrument-surface lane). Separate spec once v1 windowed mode is landed
- Prebuilt engine distribution via Servo's in-design wrapper C API, when it ships
- Turvo-specific benchmark suite (binary size, memory, cold start vs Electron and wry baselines) gating any performance claims in the README

### Unresolved items to verify before or during implementation

- Exact custom-protocol registration and request-interception surface in the pinned Servo LTS (docs.rs for the pinned version is authoritative; interception of arbitrary requests landed in early 2025, servoshell ships example protocol handlers)
- Whether `WebView::rendering_context` (Servo, June 2026) removes the surfman ANGLE `libEGL` dynamic-library constraint flagged in tauri-apps/verso PR #34; determines the Windows bundling approach
- mozjs prebuilt artifact coverage for all three target triples, to keep consumer first-build times sane
- Final shape of `NewWindowOpener` in `tauri-runtime` 2.8+

## Specific components

### Repo layout

```
turvo/
  Cargo.toml                      workspace
  crates/turvo/
    src/lib.rs                    builder() entry, public API, re-exports
    src/runtime.rs                Runtime, RuntimeHandle, tao event loop integration
    src/window.rs                 WindowDispatch, window builder mapping, monitor handling
    src/webview.rs                WebviewDispatch, WebViewDelegate impl, input forwarding
    src/ipc.rs                    invoke bridge: initialization script + response plumbing
    src/protocols.rs              custom scheme serving, asset resolution, origin handling
    src/devtools.rs               devtools server port plumbing
    src/rendering.rs              per-window rendering context, platform GL/ANGLE notes
  crates/turvo-build/
    src/lib.rs                    build-time helpers: Servo resources, Windows ANGLE
                                  libraries staged as Tauri bundler resources
  examples/helloworld/            minimal window + bundled HTML
  examples/api/                   invoke commands, events, plugins, tray; parity target is
                                  the tauri-runtime-verso api example
  .github/workflows/ci.yml        build + example smoke on Linux, Windows, macOS
  .github/workflows/servo-next.yml  scheduled monthly bump on next, agent migration PR
  README.md                       positioning per Details; runtime swap quickstart
```

### Acceptance criteria (observable)

1. `cargo run -p helloworld` opens a window rendering bundled HTML through Servo on all three platforms
2. In `examples/api`, a JS `invoke` calls a `#[tauri::command]` and receives the returned value; Tauri events cross both directions
3. App assets are served over a registered scheme with an origin that Tauri capability scoping treats as local; a remote URL in the same app is treated as remote
4. Firefox `about:debugging` connects to the configured devtools port and inspects the running page
5. Multi-window: create, retitle, resize, and close windows from commands; `window.open` produces a runtime-managed webview through the `NewWindowOpener` path
6. CI is green on all three platforms for `main`; `servo-next.yml` demonstrably opens a migration PR after an upstream monthly release
7. `turvo` 0.1.0 is published to crates.io and the README quickstart takes an existing Tauri app to Servo in two edits (Cargo.toml, main.rs)
8. TheoremWeb desktop boots on Turvo with the Theorem fork pin applied via `[patch]`, with no public-repo change required

### Coverage note

Per spec discipline, every section above maps to plan tasks when this is compiled onto the substrate: engine linkage and rendering (runtime.rs, rendering.rs), IPC and protocols (ipc.rs, protocols.rs, criterion 3), window system (window.rs, criterion 5), devtools (criterion 4), churn model (servo-next.yml, criterion 6), packaging and publish (turvo-build, criteria 1 and 7), Theorem integration (criterion 8). Unresolved items become research tasks, not spec adjectives.
