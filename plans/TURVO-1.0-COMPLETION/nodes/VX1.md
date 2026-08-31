# VX1: Verify restored Windows acceptance

Canonical SHA-256: `2823f8c5ed0356356367d36661bbc6c374a028fae198fa9b3013b1460f9c99af`

- Status: `pending`
- Controller: `verifier`
- Type: `verify.live`
- Depends on: `WX1`
- Obligations: `O13`
- Oracle class: independent Windows native verification
- Evidence class: Windows hosted and clean-machine artifacts
- Implementation mode: `independent_verification`
- Live oracle required: `true`
- Substitution allowed: `false`

## Gist

Only real Windows receipts discharge the deferred platform obligation.

## Scope

- read-only restored Windows CI, security and package receipts

## Consumes

- WX1 exact-revision artifacts

## Produces

- Windows verification receipt

## Blueprint

- Independently check the original negative security assertions, native window behavior, and ANGLE bundle launch.

## Proof commands

- `Windows native security and packaged smoke suite`

## Discharge evidence

Not yet discharged.

## Non-conclusions

None.

## Retraction path

Reopen WX1 on any failed or missing Windows receipt.
