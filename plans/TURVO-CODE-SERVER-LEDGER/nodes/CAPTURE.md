# CAPTURE: Capture the Turvo code-server console ledger

Canonical SHA-256: `ab206455c67a6dcc18d7d9af4ac802cf14b2465caf626cc5d64e7e3f88b0dcc2`

- Status: `parked`
- Owner: `turvo`
- Type: `weather`
- Controller: `world`
- Depends on: root
- Obligations: `CAPTURE`

## Gist

Make the native Turvo console export authoritative before creating failure work.

## Park and resume condition

the ledger explicitly records capture pending

Resume: 0002-turvo.md records a completed classifier capture with an explicit class count.

## Scope

- docs/ledgers/vscode/0002-turvo.md

## Consumes

- running examples/code-server workbench
- Firefox DevTools console export

## Produces

- docs/ledgers/vscode/0002-turvo.md

## Blueprint

- Launch code-server in Turvo, exercise the workbench, and export the console.
- Classify the export into stable VSC-NNN source and first-message fingerprints.

## Proof commands

- `python3 scripts/vscode-ledger-classify.py --output docs/ledgers/vscode/0002-turvo.md docs/ledgers/vscode/0002-turvo-console.json`
- `python3 plans/TURVO-CODE-SERVER-LEDGER/import_ledger.py --check`

## Discharge evidence

Not yet discharged.

## Non-conclusions

- A pending file, source audit, ServoShell ledger, or screenshot alone does not identify a Turvo failure class.

## Retraction path

Mark the capture pending and regenerate if the native artifact is invalidated.
