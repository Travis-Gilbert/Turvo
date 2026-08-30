# Continuity

Canonical SHA-256: `12804b7efa144e33e238652cbb92d64128f23fc954164a91c3de0af49a7fc9e4`

Generation: `1`

## Resume here

- `W01` (working): Drive the exact public bootstrap tip to green tests, Clippy, packages, and example builds on all three operating systems.

## Completed receipts

- `P00`: Bootstrap a54063aed480922cc0b636371d041a674d158fc4 pushed to https://github.com/Travis-Gilbert/Turvo; CI run 33326854324 started.
- `D00`: Authority and protected state recorded in canonical board.
- `P01`: F03-F04 established from exact pinned source; Record 001 and upstream audit preserve the findings.
- `D01`: ADR01-ADR03 sealed in canonical board.

## Parked work

None.

## Invariants

- Only one mutating actor owns an exact declared scope at a time. Verification scopes are read-only. Parallel work nodes have disjoint scopes; any newly discovered overlap serializes through a plan rewrite before editing.
- Never substitute source inspection, inherited upstream CI, metadata, or package listing for current-tip compilation or native behavior. Preserve unrelated repositories and credentials. The crates.io publish node is irreversible and remains held until every prerequisite obligation has a replayable receipt.
- Update the canonical JSON, render, and pass check mode before committing a transition.
