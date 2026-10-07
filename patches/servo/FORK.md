# Unified Theorem/Turvo Servo fork

Turvo and Theorem are independent consumers of this shared downstream Servo
fork. Each owns its embedding, exact consumer pin, validation and releases.
Theorem's GPUI product owns its native window and chrome. This directory records
Turvo's selected revision and the shared patch history; it does not require
Theorem to consume Turvo or select the same revision. See
[Record 004](../../docs/records/004-independent-servo-consumers.md).

## Lineage

| Fact | Value |
|---|---|
| Upstream tag | `refs/tags/v0.5.0` = `1d44e5dd6a8b64c02f9dbf7fcbdf4ebdd0740019` |
| Previous-release merge base | `b5675b1bc38498a26530b27e578122a8068af3b6` |
| Fork branch | `Travis-Gilbert/servo:theorem/v0.5.0` |
| Turvo consumer pin | `e92cdaa790797479c1821c33470c64e0d166feb2` |
| Relationship | `ahead_by=56`, `behind_by=0` against upstream `v0.5.0` |
| Rust channel | `1.95.0`, identical to upstream `v0.5.0` and Turvo's `rust-toolchain.toml` |
| Recorded in | `integration.json` and `upstream-base` |
| Enforced by | `.github/workflows/servo-integration.yml` |

The old `v0.4.0` release branch is not an ancestor of `v0.5.0`; both descend
from the recorded merge base. ADDENDUM-1 deliberately invokes the former
Theorem fork ledger's rebase escape clause: update the base record in the same
change, replay every surviving fork commit onto the named release tag, and
invalidate receipts bound to the old SHA.

## Carried engine work

| Commit | Purpose | Disposition |
|---|---|---|
| `5cd7e545ab` | Document layout snapshot and hit-test series | Local embedder read seam |
| `5585210c17` | Preserve parent profiler identity | Local multiprocess fix |
| `4a965593cb` | Trace content-process startup | Local diagnostic |
| `b491fb1e61` | Forward the content diagnostic gate | Local diagnostic |
| `a8854be8df` | Signal random pipeline closures | Local multiprocess fix |
| `047688d947` | Own the selected pipeline identifier | Local multiprocess fix |
| `42ce5917ce` | Preserve fetch policy for intercepted HTTP responses | Local transport seam |
| `6832eaa774` | Lock the cancellation-token feature dependency | Local dependency fix |
| `25eceaf39a` | Reuse the shared asynchronous network test runtime | Local test fix |
| `38a205376b` | Identify window-backed requests | Local origin-security fix |
| `8ae21c0bbc` | Add embeddable storage-engine factories | Local engine seam |
| `a9204f3535` | Align the external engine allocator graph | Local dependency fix |
| `e2a2d5e575` | Make web-resource responders sendable | Local embedder seam |
| `65d71b0bfe` | Escape keyword-named Promise wrapper methods | Candidate upstream generator fix |
| `4182b51681` through `b70d4e64c0` | Repair and verify the v0.5 carry against current module, media, sandbox, and lifecycle APIs | Rebase adaptation |
| `b5fead2675` through `6ed6091e4e` | IndexedDB index records, cursor iteration, the getAll family, `IDBRecord`, transaction rollback, and reported backend failures in place of panics | Local engine work, accepted independently at `6ed6091e4e` against the IndexedDB web-platform suite |
| `fec9c84f8f` through `e92cdaa790` | Web Locks, shared-worker teardown, and named browsing-context lookup through the constellation | Local engine work, accepted independently at `e92cdaa790` against the Web Locks and window-proxy suites |

The versioned patch files retain Turvo's seven original engine commits plus
one squashed file per independently verified slice, nine in all, for digest
and reverse-application checks. Reversing the nine in order at the current pin
reconstructs the same tree reversing the seven produced at the previous pin,
which is what makes the two additions a decomposition rather than a rewrite. The branch is authoritative when those
patch artifacts and the exact pin disagree.

## Rules

1. Every engine change receives a row here and an executable regression oracle.
2. Grow `theorem/v0.5.0` by commits; do not silently rebase or retarget it.
3. Adopting another upstream release requires updating `upstream-base`, this
   ledger, `integration.json`, the Rust channel, and all invalidated receipts in
   one reviewed change.
4. Each consumer enforces one exact engine family within its workspace. A
   consumer upgrade does not change another consumer's pin or acceptance state.
5. No generated or AI-authored change is submitted upstream; upstream
   contribution policy remains binding.

## Patch queue maintenance

Preserve the nine-patch baseline and its digests while separating storage
injection from the generally useful compatibility changes. Patch 0008 extends
contracts introduced by 0005; reversing 0005 alone removes more than injection
and breaks the conformance slice. A cleanup must be a separately verified
candidate, not a deletion of that baseline or its historical branches.

For each new or revised patch, record its narrow purpose, exact upstream base,
dependency order, regression command and reason it remains necessary. Before
adopting a later upstream release, check equivalent upstream behavior. Drop a
patch only after the same regression demonstrates equivalence; otherwise adapt
it and rerun the relevant tests. Keep this migration on v0.5.0; a Servo 0.7
upgrade is separate work. Historical verification in the table is not fresh
evidence for a changed candidate. Record 004 names the current cleanup blockers.
