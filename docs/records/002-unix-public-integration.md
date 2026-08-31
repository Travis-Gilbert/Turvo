# Public Servo/Tauri integration, Linux and macOS first

## Authority and scope

On 2026-08-30 the user authorized the proposed public, version-pinned patched
Servo/Tauri integration branch and explicitly said to skip Windows for now.
Reversible implementation choices within this scope do not need another
confirmation. This supersedes the prior development-only park, not the original
published-engine or two-edit release requirements.

Turvo development continues on `integration/servo-0.5-unix`. Servo patches start
from published 0.5.0's recorded commit
`77fccacc1f1fdce10498d50173aafaa09d02879e`; Tauri patches start from
`7cd71369c00978a3783b6ae3e9972358abbe4ae6`. Public fork branches must use new
Turvo-specific names. Theorem-owned Servo branches and Turvo `main`/`next` are
not rewritten or repinned by this authorization.

## Acceptance

- Linux/macOS build, lint, and native checks remain required.
- Keep all existing IPC, remote/opaque/sandboxed caller, navigation-race, and
  CSP canary assertions. Add ordinary same-origin fetch and module success.
- Use actual engine popup URL/geometry and one-shot creation requests; no fake
  native handles or invented callback metadata.
- Windows native failures remain open under O13/WX1/VX1. Removing it from the
  active CI matrix is a user-directed deferral, not a successful test.
- E02 blocks registry release until published dependencies and the clean
  two-edit consumer satisfy the original contract.
- Performance and size advantages remain hypotheses until benchmarked.

## Implementation direction

Considered generic custom-origin registration versus a standard HTTP app URL
with an in-process response provider. The source review found that Servo and
the CSP library independently derive unknown-scheme opaque origins. Extending
only Servo's origin type would not fix ordinary CSP `'self'` behavior.

Prefer a runtime-neutral Tauri app-URL choice plus a policy-preserving Servo
HTTP transport hook. No network listener is needed: Servo retains its existing
origin, CSP, CORS, redirect, and response filtering machinery while Turvo
provides bundled bytes. This is a design choice to validate, not native proof.

The canonical graph records implementation, verification, deferred Windows,
and the published-release gate separately. Update its JSON and regenerate its
projections; do not hand-edit generated status pages.
