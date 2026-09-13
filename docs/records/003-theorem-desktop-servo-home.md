# Record 003: Theorem desktop Servo ownership

Date: 2026-09-13

Status: Accepted by `SPEC-THEOREM-DESKTOP-SHELL-SERVO-RR-1.0-ADDENDUM-1`.

## Decision

Turvo is the sole home of Theorem's Servo integration, exact engine pin,
migration lane, hosted engine validation, and desktop bundling path. Theorem
consumes Turvo. GPUI owns native application windows and chrome; Turvo's Tauri
runtime traits remain a supported consumer of the Servo embedding rather than
the repository's defining product boundary.

The supported scope includes arbitrary third-party pages and frames. The
origin-boundary audit's remote, nested, opaque, sandboxed, and navigation-race
negative tests are required CI gates rather than advisory future work.

## Migration

The migration starts on Turvo's `next` branch. It pins
`Travis-Gilbert/servo:theorem/v0.5.0` at an exact revision descended from
upstream Servo `v0.5.0`, records the deliberate rebase in `patches/servo/FORK.md`
and `patches/servo/upstream-base`, and requires Linux and macOS CI before
promotion to `main`.

The older `TURVO-1.0-COMPLETION` graph retains useful historical receipts and
the remaining runtime backlog. Any statement there that assigns the Servo pin
to Theorem, excludes third-party compatibility, or directs new work to
`integration/servo-0.5-unix` is superseded by this record.

## Consequences

- Exactly one repository declares the product Servo pin: Turvo.
- Theorem must remove its duplicate pin and fork ledger when it consumes Turvo.
- Linux and macOS hosted CI are release evidence; local builds are development
  checks only.
- Windows and mobile remain outside this migration milestone; their existing
  deferred obligations are not converted into passing receipts.
