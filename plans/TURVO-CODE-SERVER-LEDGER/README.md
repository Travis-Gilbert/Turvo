# Turvo code-server ledger plan

This portable plan is generated from the native Turvo compatibility ledger at
`docs/ledgers/vscode/0002-turvo.md`.

The ledger is the only authority for observed `VSC-NNN` classes. If the native
capture is missing or explicitly pending, the board contains a parked capture
node and no failure-class nodes. This is intentional: ServoShell evidence and
source inspection cannot create a Turvo-native observation.

## Refresh

```sh
python3 plans/TURVO-CODE-SERVER-LEDGER/import_ledger.py
python3 plans/TURVO-CODE-SERVER-LEDGER/render_board.py
python3 plans/TURVO-CODE-SERVER-LEDGER/import_ledger.py --check
python3 plans/TURVO-CODE-SERVER-LEDGER/render_board.py --check
python3 -m unittest discover -s plans/TURVO-CODE-SERVER-LEDGER -p 'test_*.py'
```

## Ownership

`ownership.json` routes a class to `servo-fork`, `turvo`, or
`code-server-fork`. Untriaged symptoms default to the Turvo integration owner.
That default assigns responsibility for diagnosis; it does not claim that
Turvo is the root cause.

An override must include the current class fingerprint. This prevents a reused
`VSC-NNN` label or changed source/message pair from silently inheriting stale
ownership. Optional `depends_on` class ids create explicit repair ordering.

## Proof boundary

Each work node and verifier declares an absence command for its exact class.
The command passes only against a completed native capture where that class id
is absent. The terminal command requires a completed native ledger with an
explicit classifier count of zero.
