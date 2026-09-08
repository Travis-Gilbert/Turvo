# FIXPOINT: Verify the code-server compatibility fixpoint

Canonical SHA-256: `ab206455c67a6dcc18d7d9af4ac802cf14b2465caf626cc5d64e7e3f88b0dcc2`

- Status: `pending`
- Owner: `turvo`
- Type: `verify.live`
- Controller: `verifier`
- Depends on: `CAPTURE`
- Obligations: `FIXPOINT`

## Gist

Accept the board only when the completed native capture contains zero remaining classes.

## Scope

- read-only docs/ledgers/vscode/0002-turvo.md

## Consumes

- completed CAPTURE
- all class verifier receipts

## Produces

- compatibility ledger fixpoint receipt

## Blueprint

- Require an explicit native classifier count of zero.
- Reject a missing ledger, capture-pending marker, or lower-class substitute.

## Proof commands

- `python3 plans/TURVO-CODE-SERVER-LEDGER/import_ledger.py --assert-empty`

## Discharge evidence

Not yet discharged.

## Non-conclusions

- Zero classes in an unclassified or capture-pending document is not a fixpoint receipt.

## Retraction path

Regenerate the board when a later native capture reports a VSC class.
