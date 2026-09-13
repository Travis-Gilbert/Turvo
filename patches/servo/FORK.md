# Unified Theorem/Turvo Servo fork

Turvo owns the Servo integration, exact pin, migration policy, and hosted
verification for Theorem desktop. GPUI remains the native window and chrome
owner; this fork supplies the embeddable web engine and does not make Servo or
Tauri the application window system.

## Lineage

| Fact | Value |
|---|---|
| Upstream tag | `refs/tags/v0.5.0` = `1d44e5dd6a8b64c02f9dbf7fcbdf4ebdd0740019` |
| Previous-release merge base | `b5675b1bc38498a26530b27e578122a8068af3b6` |
| Fork branch | `Travis-Gilbert/servo:theorem/v0.5.0` |
| Current pin | `b70d4e64c0005d5dc2d5257c09f997dba235410a` |
| Relationship | `ahead_by=20`, `behind_by=0` against upstream `v0.5.0` |
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

The versioned patch files retain Turvo's seven original engine commits for
digest and reverse-application checks. The branch is authoritative when those
patch artifacts and the exact pin disagree.

## Rules

1. Every engine change receives a row here and an executable regression oracle.
2. Grow `theorem/v0.5.0` by commits; do not silently rebase or retarget it.
3. Adopting another upstream release requires updating `upstream-base`, this
   ledger, `integration.json`, the Rust channel, and all invalidated receipts in
   one reviewed change.
4. Theorem consumes Turvo and does not declare a duplicate Servo pin or fork
   ledger.
5. No generated or AI-authored change is submitted upstream; upstream
   contribution policy remains binding.
