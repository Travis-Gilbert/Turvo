# Lessons and constraints

Canonical SHA-256: `13e1eb23cc113380065dc2a0f29957978d859bb8dac12bac2f301935b2b65e1d`

## Current facts

- `F01`: Bootstrap tip a54063aed480922cc0b636371d041a674d158fc4 is public on Travis-Gilbert/Turvo main; CI run 33326854324 started from that tip.
- `F02`: The active Turvo dependency tree exact-pins Servo 0.5.0, Tauri 2.11.5, tauri-runtime 2.11.3, and Tao 0.37.0 without tauri-runtime-wry.
- `F03`: Tauri 2.11.5 generates http://tauri.localhost for Windows app assets, while Turvo currently registers only the tauri custom protocol and does not implement Servo HTTP resource interception.
- `F04`: Turvo currently discards pending.new_window_handler; tauri-runtime 2.11.3 NewWindowOpener embeds Wry-native WebKitGTK, WebView2, or WKWebView objects.
- `F05`: The configured Cargo target volume was 99 percent utilized with approximately 9 GiB free at charting, so hosted CI outranks a fresh local Servo build until storage is made safe.

## Explicit exclusions

- No arbitrary third-party web compatibility commitment.
- No offscreen GPUI compositor implementation in the 0.1.0 windowed release; only its follow-on plan is required.
- No performance, memory, startup, or binary-size claim before a reproducible benchmark receipt.
- No unsafe fabrication of Tauri NewWindowOpener platform objects.
- No force-push, history rewrite, credential disclosure, or unrelated dirty-worktree cleanup.
