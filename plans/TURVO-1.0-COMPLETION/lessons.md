# Lessons and constraints

Canonical SHA-256: `12804b7efa144e33e238652cbb92d64128f23fc954164a91c3de0af49a7fc9e4`

## Current facts

- `F01`: Bootstrap tip a54063aed480922cc0b636371d041a674d158fc4 is public on Travis-Gilbert/Turvo main; CI run 33326854324 proved Linux and macOS runtime tests and lint, then exposed missing example icons plus Tauri's known Windows test-manifest entry-point failure.
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
