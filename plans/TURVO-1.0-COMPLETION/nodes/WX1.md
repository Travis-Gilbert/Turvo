# WX1: Restore Windows native and packaging acceptance

Canonical SHA-256: `7af2ed578ba07b057f27605aed5bdde4ea3d90548539e7e329bc17fef3e8b380`

- Status: `parked`
- Controller: `agent`
- Type: `work.implementation`
- Depends on: `V07`
- Obligations: `O13`
- Oracle class: Windows native security and packaged behavior
- Evidence class: exact-commit Windows native and bundle receipts
- Implementation mode: `real`
- Live oracle required: `true`
- Substitution allowed: `false`

## Gist

Retain the deferred Windows acceptance work outside the active Unix development path.

## Park and resume condition

Windows is explicitly deferred by the user in F26. Previous cross-origin asset and CSP failures remain unresolved, not passed.

Resume: Windows returns to active project scope; restore its CI target and fix the unchanged native and clean-machine packaging oracles.

## Scope

- Windows-only native integration, ANGLE packaging, and restored Windows CI target

## Consumes

- V07 Linux/macOS implementation
- F19/F25 failed Windows receipts

## Produces

- Windows implementation and restored native CI

## Blueprint

- Restore the Windows target and reuse the same security assertions, including remote-asset and CSP handler canaries.
- Verify ANGLE libraries and clean-machine bundles before claiming Windows support.

## Proof commands

- `Windows native security and packaged smoke suite`

## Discharge evidence

Not yet discharged.

## Non-conclusions

None.

## Retraction path

Return Windows to deferred status with the exact failed receipt; do not claim three-platform acceptance.
