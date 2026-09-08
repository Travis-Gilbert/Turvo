# Continuity

Canonical SHA-256: `e6805a0db8f36fc01c742435d134de3216bccc5ae26e7a53634283614f91c765`

Generation: `6`

## Resume here

- `W03` (frontier): Implement and propose an additive Tauri API that lets non-Wry runtimes process window.open safely.

## Completed receipts

- `P00`: Bootstrap a54063aed480922cc0b636371d041a674d158fc4 pushed to https://github.com/Travis-Gilbert/Turvo; CI run 33326854324 started.
- `D00`: Authority and protected state recorded in canonical board.
- `P01`: F03-F04 established from exact pinned source; Record 001 and upstream audit preserve the findings.
- `D01`: ADR01-ADR03 sealed in canonical board.
- `W01`: 750d6422f7781f408bcc2f7759b942d0f57b2d1c passed all four jobs in https://github.com/Travis-Gilbert/Turvo/actions/runs/33329627108. Windows runtime tests, Clippy, and both examples passed after manifest and native icon repairs.
- `V01`: Separate read-only audit confirmed success for jobs 99305763884, 99305763947, 99305763979, and 99305763986 at exact public SHA 750d6422f7781f408bcc2f7759b942d0f57b2d1c; tracked next was created from the same SHA.; Local fmt, locked metadata, and three target-specific normal dependency trees passed; no active tauri-runtime-wry, wry, or versoview appeared. Locked offline cargo package --no-verify produced 27 files including both licenses, public source, tests, and the Windows manifest. These are compile/package receipts, not native behavior or published-crate proof.
- `W02`: 7813baa3529e6db53113e30adfc4242de65ee276 passed all jobs in run 33330884047, including seven protocol routing/header/response tests on Linux, macOS, and Windows. The adapter is Windows-only, shares registered handlers, rejects ambiguous authorities, and fails closed on a dropped response. Native asset rendering and IPC authentication are not discharged here.
- `V02`: Read-only review and exact-commit logs confirmed 31 unit tests and two public API tests per target in run 33330884047 (jobs 99309104910, 99309104920, 99309104928), plus Clippy, examples, and package job 99309104737. Source audit confirmed original headers are forwarded without synthesized Origin and both Servo delegate paths share the router. W02I/V02I retain all native IPC, CSP, and caller-isolation obligations.
- `W02I`: Turvo be7bb189aaaff9b6e0ac79ae17d948d215d2c9bd pins public Servo 526e95cf47ba81485225660fe1a14dc000ffd4b7, requires Window-backed engine provenance for privileged IPC, and retains the full hostile-frame, navigation, CSP, asset, module, binary, channel, and event suite.; CI run 33567283891 passed runtime tests, Clippy, both examples, package checks, and the native security suite on Linux x86_64 and macOS arm64. Both native receipts include local-frame-worker as passed while their privileged-call lists contain only local-json, local-raw, and restored-local.; The engine-side RequestClient serde and builder tests passed 4/4 locally at the exact public revision; the root runtime test rejects workers even when they share document identity.
- `V02I`: Independent source review confirmed only Window globals set RequestClient.is_window=true; dedicated and service workers, worklets, synthetic navigation requests, and deserialized legacy clients remain false.; Exact-tip GitHub jobs 100053244582 and 100053244665 independently exercised the native worker exploit on Linux and macOS. Each reported native case passed: local-frame-worker and TURVO_NATIVE_SECURITY passed=true without any worker-originated Rust call.; Run 33567283891 is bound to Turvo be7bb189aaaff9b6e0ac79ae17d948d215d2c9bd and completed successfully on both required platforms.

## Parked work

- `WX1`: Windows is explicitly deferred by the user in F26. Previous cross-origin asset and CSP failures remain unresolved, not passed. Resume: Windows returns to active project scope; restore its CI target and fix the unchanged native and clean-machine packaging oracles.
- `E02`: The integration branch may use public Git revisions, but no published Servo/Tauri versions provide these new integration APIs yet. Resume: Published dependency versions contain the required APIs and the unpatched two-edit consumer passes the native acceptance suite.

## Invariants

- Only one mutating actor owns an exact declared scope at a time. Verification scopes are read-only. Parallel work nodes have disjoint scopes; any newly discovered overlap serializes through a plan rewrite before editing.
- Never substitute source inspection, inherited upstream CI, metadata, or package listing for current-tip compilation or native behavior. Preserve unrelated repositories and credentials. The crates.io publish node is irreversible and remains held until every prerequisite obligation has a replayable receipt.
- Update the canonical JSON, render, and pass check mode before committing a transition.
