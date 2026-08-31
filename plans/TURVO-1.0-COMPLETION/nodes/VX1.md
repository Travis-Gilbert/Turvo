# VX1: Verify restored Windows acceptance

Canonical SHA-256: `91235407bdc29086e28edf393c79e56da60be8122b5192cdd9578dc6bb3a2660`

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
