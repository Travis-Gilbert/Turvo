# Record 001: Turvo bootstrap and proof plan

Status: In progress

## Destination

Ship an independently maintained, desktop-only Tauri runtime that embeds a
pinned Servo release in process, exposes `turvo::builder()`, and is honest
about the difference between compile coverage and observed application
behavior.

## Architecture decision

Turvo imports and evolves the dual-licensed runtime from
`copse-dev/tauri-runtime-servo@b9d4ef11`. This is preferable to either a fresh
trait implementation or a thin dependency facade:

- the existing code already carries the low-level Tao and Servo integration;
- owning the source lets Turvo repair monthly Servo churn on `next`; and
- exact engine pins remain under Turvo's control.

The imported module layout remains intact for the bootstrap. Splitting the
5,000-line runtime into `runtime`, `ipc`, `protocols`, `devtools`, and
`rendering` modules is a refactor after behavior tests exist, not a prerequisite
for the first working window.

## Acceptance matrix

| ID | Observable requirement | Current state | Required proof |
|---|---|---|---|
| A1 | Bundled hello-world renders through Servo on Linux, Windows, macOS | Wired; inherited compile evidence only | Launch and capture on each native platform |
| A2 | JS invoke returns a Rust command result; events cross both directions | API probe wired; unrun | Native smoke receipts plus repeatable automation |
| A3 | Local scheme is local and remote content is remote for Tauri capabilities | IPC origin preservation tested in source; capability and Windows mapping unresolved | Positive local and negative remote capability tests per platform |
| A4 | Firefox connects to a configured devtools port | Secure token/approval API implemented; unrun | Native connection receipt and inspected page |
| A5 | Create/retitle/resize/close multi-window; `window.open` is runtime-managed | Command path wired; `window.open` blocked by Tauri opener types | Native command test plus Tauri upstream change or approved patch |
| A6 | `main` CI green on three platforms; monthly `next` migration PR opens | Workflows present locally; no remote run | Public-repo Actions receipts and one demonstrated migration PR |
| A7 | `turvo` 0.1.0 is published; existing app swaps in two edits | API and docs wired; unpublished | crates.io release and clean consumer smoke |
| A8 | TheoremWeb desktop boots with its Servo fork via consumer `[patch]` | Out of this repository's bootstrap scope | Exact-revision Theorem build and native boot receipt |

## Implementation slices

1. Bootstrap the imported runtime, exact pins, builder API, devtools options,
   hello-world example, documentation, and CI definitions.
2. Add the API parity example and focused tests for invoke, events, window
   commands, and protocol origin classification.
3. Resolve the Windows bundled-asset interception path and run native smoke on
   all three platforms.
4. Resolve the Tauri `NewWindowOpener` boundary upstream or record an approved
   temporary patch strategy.
5. Demonstrate the `next` migration workflow, then publish 0.1.0.
6. Integrate Theorem through consumer-owned `[patch]` entries without adding a
   private fork requirement to Turvo.

## Implementation notes

- Considered: a fresh runtime, a facade over `tauri-runtime-servo`, and an
  attributed source import.
- Chose: attributed source import because it reuses proven code while keeping
  Servo migration ownership inside Turvo.
- Deferred: `turvo-build`; Servo 0.5.0 bakes resources into the crate and the
  current Windows graph compiles without a separate Verso binary. Add build
  helpers only when a clean-machine bundle test demonstrates a resource gap.
- Isolated: the monthly coding agent receives a static prompt, prefetched
  dependencies, workspace writes, and no GitHub token or shell network. It
  emits a scope-checked patch; a secret-free job validates it before a separate
  clean job can open a draft PR.
- Reviewed: CodeRabbit's final isolated-delta pass reported zero findings after
  DevTools authentication, immutable action pins, and engine-state timing were
  corrected.

## Local verification

Completed on 2026-08-30:

- `cargo fmt --all --check`
- `cargo metadata --no-deps --locked --format-version 1`
- `cargo tree -p turvo --depth 1 --locked` (exact Servo 0.5.0, Tao 0.37.0,
  Tauri 2.11.5, and `tauri-runtime` 2.11.3)
- inverse dependency check showing `tauri-runtime-wry` absent from Turvo's
  active desktop graph
- `cargo package -p turvo --locked --allow-dirty --no-verify` (25 files;
  package contains both licenses, README, public source, and API test)
- JavaScript syntax, Tauri JSON, workflow YAML, embedded Bash syntax, immutable
  40-character action references, and Git whitespace checks
- CodeRabbit isolated-delta review: zero findings on the final pass

Not run locally: Rust tests, Clippy, example builds, native window launches, or
Firefox attachment. A cold Servo build was unsafe with 4.6 GiB free on the
internal data volume and 9.0 GiB free on the already 99%-used SSD. Those remain
CI/native proof gates, not inferred passes.
