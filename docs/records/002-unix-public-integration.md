# Public Servo/Tauri integration, Linux and macOS first

## Authority and scope

On 2026-08-30 the user authorized the proposed public, version-pinned patched
Servo/Tauri integration branch and explicitly said to skip Windows for now.
Reversible implementation choices within this scope do not need another
confirmation. This supersedes the prior development-only park, not the original
published-engine or two-edit release requirements.

Turvo development continues on `integration/servo-0.5-unix`. Servo patches start
from published 0.5.0's recorded commit
`77fccacc1f1fdce10498d50173aafaa09d02879e`; Tauri patches start from
`7cd71369c00978a3783b6ae3e9972358abbe4ae6`. Public fork branches must use new
Turvo-specific names. Theorem-owned Servo branches and Turvo `main`/`next` are
not rewritten or repinned by this authorization.

## Acceptance

- Linux/macOS build, lint, and native checks remain required.
- Keep all existing IPC, remote/opaque/sandboxed caller, navigation-race, and
  CSP canary assertions. Add ordinary same-origin fetch and module success.
- Use actual engine popup URL/geometry and one-shot creation requests; no fake
  native handles or invented callback metadata.
- Windows native failures remain open under O13/WX1/VX1. Removing it from the
  active CI matrix is a user-directed deferral, not a successful test.
- E02 blocks registry release until published dependencies and the clean
  two-edit consumer satisfy the original contract.
- Performance and size advantages remain hypotheses until benchmarked.

## Implementation direction

Considered generic custom-origin registration versus a standard HTTP app URL
with an in-process response provider. The source review found that Servo and
the CSP library independently derive unknown-scheme opaque origins. Extending
only Servo's origin type would not fix ordinary CSP `'self'` behavior.

Prefer a runtime-neutral Tauri app-URL choice plus a policy-preserving Servo
HTTP transport hook. No network listener is needed: Servo retains its existing
origin, CSP, CORS, redirect, and response filtering machinery while Turvo
provides bundled bytes. This is a design choice to validate, not native proof.

The canonical graph records implementation, verification, deferred Windows,
and the published-release gate separately. Update its JSON and regenerate its
projections; do not hand-edit generated status pages.

## Implemented integration and proof boundaries

- Public Tauri revision `e84733018d84c8004645e04cbc8fea8511ae36b1` adds the
  runtime HTTP-origin opt-in and retains the versioned runtime-opener seam.
  Run [33357076684](https://github.com/Travis-Gilbert/Turvo/actions/runs/33357076684)
  passed Linux/macOS formatting, JavaScript mapping, runtime/core tests,
  no-Wry compilation, default Wry compatibility, and isolation-mode tests.
- Public Servo revision `8d45326e4a414afb3fe8b7afba98492e320d42f6` moves
  interception into HTTP transport, adds cancellable bounded accumulation and
  framing validation, and reports upload presence before application dispatch.
  All forty-two new networking tests passed Linux/macOS in run 33358290552.
  Follow-up `1dfbf13a15b2b37d93b6740024a6892b7ed5e96f` adds the missing
  `tokio-util -> futures-util` lockfile edge. The full run had 431 successes and
  one existing file-manager test failure: that test tried to initialize a
  second process-wide runtime. Test-only follow-up
  `c9f01133e338ceabc6657a5f7ae9b1c772bbb21d` reuses the shared helper and is
  the current engine pin. Both isolated and full-suite reruns remain required.
- A separate source reviewer found a completion-channel cancellation race and
  incomplete HTTP framing validation. Both were corrected and re-reviewed.
  This is a source review receipt, not native or exhaustive concurrency proof.
- Turvo maps app URLs on Linux/macOS, rejects ambiguous authorities, preserves
  handler-facing custom URLs, suppresses HEAD/null-status bodies, and rejects
  uploads before invoking mapped asset handlers. IPC retains its real body stream.
- Native coverage now requires normal CSP `'self'`, same-origin fetch and HEAD,
  static and dynamic modules, no-CORS opacity, and zero upload-handler dispatch.
  All prior negative capability/CSP/navigation assertions remain required.

The lockfile candidate job has read-only GitHub permissions and never commits.
Its output must be reviewed, committed, and rerun with `--locked`. No cold build
is attempted on the nearly full workstation. Engine and native hosted receipts
remain open until their exact pinned revisions pass.

Lockfile candidate run
[33357839687](https://github.com/Travis-Gilbert/Turvo/actions/runs/33357839687)
succeeded. Review confirmed the same 996 packages and no package-version changes;
63 packages changed to the intended public Git source families. The imported
candidate advances the engine source ID through the lockfile-only follow-up.
The initial engine test run stopped at `--locked` before compilation; its missing
feature edge was fixed, not bypassed by dropping the locked requirement.

Run [33358290540](https://github.com/Travis-Gilbert/Turvo/actions/runs/33358290540)
at Turvo `918ad410cbf182a7b9ef88d99786b75fcc77071a` passed 53 runtime tests,
two API tests, Clippy, example builds, and source-package checks on Linux/macOS.
Both native runs passed ordinary app assets/modules, local IPC/events and all
four hostile-frame cases, then timed out at the sandboxed top-level document:
CSP correctly blocked its relative script because its origin was opaque.
The fixture now loads that script from its already-allowed generated loopback
source while retaining the sandbox header, app CSP, mandatory reports and
negative Rust-call counters. A separate source reviewer checked this correction.
It is not full native acceptance until the repaired exact-tip rerun passes.

Exact-tip Servo run
[33359241838](https://github.com/Travis-Gilbert/Turvo/actions/runs/33359241838)
at Turvo `54e7765f47792c5568e55baf4f47e06cd0337c86` and public Servo
`c9f01133e338ceabc6657a5f7ae9b1c772bbb21d` passed the isolated file-manager
case and all 432 networking tests on Linux and macOS, including all forty-two
interception tests. That is complete engine-suite evidence, not native IPC
caller-isolation evidence.

Root run
[33359241859](https://github.com/Travis-Gilbert/Turvo/actions/runs/33359241859)
passed the original ten-case native suite on Linux. macOS passed compile,
tests, lint and example builds, then its native probe stopped after five
frame/module reports and one status poll without reaching a protected handler.
The fixture now immediately issues the next status request while retaining its
deadline and required-report oracle; this liveness change still needs a native
rerun.

Source review also identified a distinct caller-provenance candidate: Servo
workers inherit their owner origin, webview and pipeline, but are represented as
non-nested request clients. Turvo currently validates tuple origin and nested
state without proving that the caller is a Window. The native suite therefore
adds a same-origin child-frame worker case before changing the production guard.
Until that fixture first reproduces and then rejects the path on Linux/macOS,
W02I/V02I remain open.

The encoded-response cap does not bound the embedder queue, decoded body, or
renderer memory. Cache hits skip per-webview interception; dynamic handlers need
appropriate cache policy. Synthetic transport does not fabricate TLS handshakes
or network timings. Tauri's initial-window-origin asset ACAO behavior is retained,
including the documented remote-first-window caveat.

Servo's upstream policy prohibits AI-generated submissions, so no upstream
issue, comment, or PR is submitted. The authorized public fork does not discharge
the separately tracked published-engine release requirement.
