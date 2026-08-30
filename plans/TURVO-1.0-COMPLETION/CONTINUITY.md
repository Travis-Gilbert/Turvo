# Continuity

Canonical SHA-256: `3acdebbd81396e7804d432127141c9890fbf3d665bc1d41e84f267e93a3b9f9a`

Generation: `3`

## Resume here

The board has no active frontier; recompute before mutation.

## Completed receipts

- `P00`: Bootstrap a54063aed480922cc0b636371d041a674d158fc4 pushed to https://github.com/Travis-Gilbert/Turvo; CI run 33326854324 started.
- `D00`: Authority and protected state recorded in canonical board.
- `P01`: F03-F04 established from exact pinned source; Record 001 and upstream audit preserve the findings.
- `D01`: ADR01-ADR03 sealed in canonical board.
- `W01`: 750d6422f7781f408bcc2f7759b942d0f57b2d1c passed all four jobs in https://github.com/Travis-Gilbert/Turvo/actions/runs/33329627108. Windows runtime tests, Clippy, and both examples passed after manifest and native icon repairs.
- `V01`: Separate read-only audit confirmed success for jobs 99305763884, 99305763947, 99305763979, and 99305763986 at exact public SHA 750d6422f7781f408bcc2f7759b942d0f57b2d1c; tracked next was created from the same SHA.; Local fmt, locked metadata, and three target-specific normal dependency trees passed; no active tauri-runtime-wry, wry, or versoview appeared. Locked offline cargo package --no-verify produced 27 files including both licenses, public source, tests, and the Windows manifest. These are compile/package receipts, not native behavior or published-crate proof.
- `W02`: 7813baa3529e6db53113e30adfc4242de65ee276 passed all jobs in run 33330884047, including seven protocol routing/header/response tests on Linux, macOS, and Windows. The adapter is Windows-only, shares registered handlers, rejects ambiguous authorities, and fails closed on a dropped response. Native asset rendering and IPC authentication are not discharged here.
- `V02`: Read-only review and exact-commit logs confirmed 31 unit tests and two public API tests per target in run 33330884047 (jobs 99309104910, 99309104920, 99309104928), plus Clippy, examples, and package job 99309104737. Source audit confirmed original headers are forwarded without synthesized Origin and both Servo delegate paths share the router. W02I/V02I retain all native IPC, CSP, and caller-isolation obligations.

## Parked work

- `W02I`: Native Windows run 33334815996 reproduces mapped-asset cross-origin disclosure and CSP bypass. Published Servo 0.5.0 cannot provide both the required origin semantics and normal app fetch/modules through its documented embedding paths. No safe embedder-only repair has been established. Resume: A public Servo release or accepted public API revision supplies standards-preserving asset transport/origins, or the user explicitly changes the published-engine constraint to authorize an isolated patched-engine integration lane; rerun the unchanged native positive/negative suite before discharge.
- `W03`: The versioned Tauri proposal passed all three compatibility jobs (F24), but the complete V03 Servo-sufficiency gate is not established: the pinned engine request lacks target URL/geometry provenance (F23), and no accepted public integration revision or native Servo popup receipt exists. Partial API proof is retained without discharging O06. Resume: An accepted public engine API or validated design supplies the real popup metadata and responder lifecycle, or the user explicitly authorizes a patched-engine development lane. Re-enter V03 verification before adopting a public Tauri revision; do not invent popup metadata.

## Invariants

- Only one mutating actor owns an exact declared scope at a time. Verification scopes are read-only. Parallel work nodes have disjoint scopes; any newly discovered overlap serializes through a plan rewrite before editing.
- Never substitute source inspection, inherited upstream CI, metadata, or package listing for current-tip compilation or native behavior. Preserve unrelated repositories and credentials. The crates.io publish node is irreversible and remains held until every prerequisite obligation has a replayable receipt.
- Update the canonical JSON, render, and pass check mode before committing a transition.
