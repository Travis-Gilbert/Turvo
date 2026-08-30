# Continuity

Canonical SHA-256: `fc87252da42bb7f283798fafd9ba3359b7f1e3be1a4f5eb6ea6e718793057eab`

Generation: `2`

## Resume here

- `W02` (working): Route only Tauri-owned Windows localhost traffic to the registered asset protocol while preserving local and remote origins.

## Completed receipts

- `P00`: Bootstrap a54063aed480922cc0b636371d041a674d158fc4 pushed to https://github.com/Travis-Gilbert/Turvo; CI run 33326854324 started.
- `D00`: Authority and protected state recorded in canonical board.
- `P01`: F03-F04 established from exact pinned source; Record 001 and upstream audit preserve the findings.
- `D01`: ADR01-ADR03 sealed in canonical board.
- `W01`: 750d6422f7781f408bcc2f7759b942d0f57b2d1c passed all four jobs in https://github.com/Travis-Gilbert/Turvo/actions/runs/33329627108. Windows runtime tests, Clippy, and both examples passed after manifest and native icon repairs.
- `V01`: Separate read-only audit confirmed success for jobs 99305763884, 99305763947, 99305763979, and 99305763986 at exact public SHA 750d6422f7781f408bcc2f7759b942d0f57b2d1c; tracked next was created from the same SHA.; Local fmt, locked metadata, and three target-specific normal dependency trees passed; no active tauri-runtime-wry, wry, or versoview appeared. Locked offline cargo package --no-verify produced 27 files including both licenses, public source, tests, and the Windows manifest. These are compile/package receipts, not native behavior or published-crate proof.

## Parked work

None.

## Invariants

- Only one mutating actor owns an exact declared scope at a time. Verification scopes are read-only. Parallel work nodes have disjoint scopes; any newly discovered overlap serializes through a plan rewrite before editing.
- Never substitute source inspection, inherited upstream CI, metadata, or package listing for current-tip compilation or native behavior. Preserve unrelated repositories and credentials. The crates.io publish node is irreversible and remains held until every prerequisite obligation has a replayable receipt.
- Update the canonical JSON, render, and pass check mode before committing a transition.
