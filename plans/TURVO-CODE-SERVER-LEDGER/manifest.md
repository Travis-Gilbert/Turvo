# TURVO-CODE-SERVER-LEDGER board

Canonical SHA-256: `ab206455c67a6dcc18d7d9af4ac802cf14b2465caf626cc5d64e7e3f88b0dcc2`

## Native ledger authority

- Path: `docs/ledgers/vscode/0002-turvo.md`
- Status: `capture_pending`
- SHA-256: `bbdfec042fb2485d821c356db10baf61dd589a68e826a228db8e13ec84465d75`
- Remaining failure classes: 0

## Destination

Resolve every failure class observed by the native Turvo code-server console capture, with each class routed to exactly one owning fork and discharged by a recapture in which its stable fingerprint is absent.

## Fixpoint

The native Turvo capture is complete, no remaining VSC-NNN failure class is present in docs/ledgers/vscode/0002-turvo.md, and the generated board has no class work node or verifier node.

## Hard prerequisite

The native ledger is the sole authority for observed failure classes. A missing or capture-pending ledger creates no class node, and source inspection or a ServoShell capture cannot substitute for the Turvo native capture.

## Opening move

No active move.

## Task board

| Node | Status | Owner | Type | Depends on |
|---|---|---|---|---|
| [CAPTURE](nodes/CAPTURE.md) | parked | turvo | weather | root |
| [FIXPOINT](nodes/FIXPOINT.md) | pending | turvo | verify.live | CAPTURE |

## Projections

- [Dependency graph](projection.md)
- [Edges](edges.md)
- [Continuity](CONTINUITY.md)
- [Decisions and disagreements](disagreements.md)
- [Lessons and constraints](lessons.md)
- [Replay](replay.md)
- [Validation](validation.md)
