# TURVO-1.0-COMPLETION completion board

Canonical SHA-256: `c59f59c06fe9833be173f484504acd20e115bb05a9dd24fd761801df446001a3`

## Destination

Ship Turvo 0.1.0 as a public, deterministic, desktop-only Tauri runtime backed by an in-process pinned Servo engine, with native Linux, Windows, and macOS proof, secure local-versus-remote capability behavior, Firefox DevTools, runtime-managed window.open, automated Servo migration, a published two-edit consumer path, and an exact-revision Theorem consumer receipt.

## Fixpoint

O01-O12 each carry their declared evidence. GitHub main and next exist; the exact source tip passes compile, lint, package, native smoke, DevTools, origin, IPC, events, plugin, tray, multi-window, and window.open gates on the required platforms; servo-next has opened a real migration PR; turvo 0.1.0 is published and consumed in a clean app; Theorem boots with its consumer-owned Servo patch; no benchmark claim appears without a benchmark receipt; no rewrite remains applicable.

## Hard prerequisite

Never substitute source inspection, inherited upstream CI, metadata, or package listing for current-tip compilation or native behavior. Preserve unrelated repositories and credentials. The crates.io publish node is irreversible and remains held until every prerequisite obligation has a replayable receipt.

## Authority

Gate: `granted_by_user_request_2026-08-30`

The user explicitly requested the bootstrap push, graph computation, and execution to completion in one instruction. This grants the bounded authority below; no additional scheduled human stop is charted.

## Opening move

- 1. `W02I`: Asset routing is verified at its declared test level. F08's caller-identity gap now has a published low-level API candidate in F11 that must be proven before native API parity or release.

## Task board

| Node | Status | Controller | Type | Depends on | Obligations |
|---|---|---|---|---|---|
| [P00](nodes/P00.md) | completed | agent | probe.research | root | O01, O02, O03, O04, O05, O06, O07, O08, O09, O10, O11, O12 |
| [D00](nodes/D00.md) | completed | agent | decision.architecture | P00 | O01, O10, O11, O12 |
| [P01](nodes/P01.md) | completed | agent | probe.research | D00 | O03, O05, O06, O08 |
| [D01](nodes/D01.md) | completed | agent | decision.architecture | P01 | O03, O06, O08 |
| [W01](nodes/W01.md) | completed | agent | work.implementation | D01 | O01, O02, O12 |
| [V01](nodes/V01.md) | completed | verifier | verify.live | W01 | O01, O02, O12 |
| [W02](nodes/W02.md) | completed | agent | work.implementation | V01 | O03, O04 |
| [V02](nodes/V02.md) | completed | verifier | verify.local | W02 | O03, O04 |
| [W02I](nodes/W02I.md) | working | agent | work.implementation | V02 | O03, O04 |
| [V02I](nodes/V02I.md) | pending | verifier | verify.live | W02I | O03, O04 |
| [W03](nodes/W03.md) | pending | agent | work.external | V02 | O06 |
| [V03](nodes/V03.md) | pending | verifier | verify.live | W03 | O06 |
| [E01](nodes/E01.md) | pending | world | weather | V03 | O06 |
| [W04](nodes/W04.md) | pending | agent | work.implementation | E01 | O06 |
| [V04](nodes/V04.md) | pending | verifier | verify.live | W04 | O06 |
| [W05](nodes/W05.md) | pending | agent | work.implementation | V02I | O03, O04, O06, O07, O12 |
| [V05](nodes/V05.md) | pending | verifier | verify.live | W05 | O03, O04, O06, O07, O12 |
| [W06](nodes/W06.md) | pending | agent | work.implementation | V04, V05 | O08, O12 |
| [V06](nodes/V06.md) | pending | verifier | verify.local | W06 | O08, O12 |
| [W07](nodes/W07.md) | pending | agent | work.implementation | V06 | O01, O03, O04, O05, O06, O07, O08, O09 |
| [V07](nodes/V07.md) | pending | verifier | verify.live | W07 | O01, O03, O04, O05, O06, O07, O08, O09 |
| [W08](nodes/W08.md) | pending | agent | work.implementation | V07 | O09 |
| [V08](nodes/V08.md) | pending | verifier | verify.live | W08 | O09 |
| [W09](nodes/W09.md) | pending | agent | work.release | V08 | O10, O12 |
| [V09](nodes/V09.md) | pending | verifier | verify.live | W09 | O10, O12 |
| [W10](nodes/W10.md) | pending | agent | work.external | V09 | O11 |
| [V10](nodes/V10.md) | pending | verifier | verify.live | W10 | O11 |
| [W11](nodes/W11.md) | pending | agent | work.implementation | V10 | O12 |
| [V11](nodes/V11.md) | pending | verifier | verify.live | W11 | O12 |

## Projections

- [Dependency graph](projection.md)
- [Edges](edges.md)
- [Continuity](CONTINUITY.md)
- [Decisions and disagreements](disagreements.md)
- [Lessons](lessons.md)
- [Replay](replay.md)
- [Validation](validation.md)
