# Continuity

Canonical SHA-256: `ab206455c67a6dcc18d7d9af4ac802cf14b2465caf626cc5d64e7e3f88b0dcc2`

Ledger status: `capture_pending`; classes: 0.

## Resume here

No active class repair.

## Parked work

- `CAPTURE`: the ledger explicitly records capture pending Resume: 0002-turvo.md records a completed classifier capture with an explicit class count.

## Invariants

- A class has one routing owner at a time. Fingerprint-locked ownership overrides are explicit, and dependency overrides may reference only classes present in the same ledger.
- The native ledger is the sole authority for observed failure classes. A missing or capture-pending ledger creates no class node, and source inspection or a ServoShell capture cannot substitute for the Turvo native capture.
- Run the importer, render projections, then check both before recording a transition.
