# Record 004: Independent Servo consumers

Date: 2026-10-07

Status: Ownership decision approved by the user's execution request. Migration,
engine cleanup, benchmarks and native acceptance remain separate obligations.

## Decision and supersession

Theorem owns its GPUI product, in-repository Servo embedding, exact consumer
pin, hosted validation and native application packaging. Turvo remains an
independent OSS Servo application runtime and SDK with its own embedding, pin,
packaging, benchmarks and releases. The projects may share the downstream
Servo fork without synchronizing their integration code or release schedules.

This explicitly supersedes Record 003's sole Theorem integration owner, shared
consumer pin and mandatory Turvo dependency clauses. It also supersedes those
ownership clauses of `SPEC-THEOREM-DESKTOP-SHELL-SERVO-RR-1.0-ADDENDUM-1` and the
prohibition on Theorem-owned bundling/workflows. The original record calls the
addendum accepted while its header says Proposed; the ownership decision does
not retroactively resolve that discrepancy or accept its remaining work.

Theorem's corresponding source audit and execution record is
`docs/records/2026-10-07-theorem-turvo-independent-servo-consumer.md` in its
repository. Theorem retains its separate Cargo workspace and toolchain
attachment boundary. No Turvo release is a prerequisite for Theorem product
changes. Each consumer still verifies a consistent exact Servo crate family
inside its own workspace.

Turvo's existing public Tauri runtime remains supported. Retiring it requires
a separate deliberate migration of needed native capabilities and public API
compatibility. Origin-boundary negative tests, arbitrary third-party page/frame
support, macOS/Linux native proof and registry publication gates survive.
Windows/mobile deferrals remain explicit; they are not passing evidence.

## Frozen baseline and storage findings

- Turvo baseline: `next`, `90cc0003dff3800ad01fabe571a75ad80491cd5b`.
- Turvo Servo pin: `e92cdaa790797479c1821c33470c64e0d166feb2`, upstream v0.5.0
  base `1d44e5dd6a8b64c02f9dbf7fcbdf4ebdd0740019`.
- Existing nine-patch artifacts, digests and upstream lineage are preserved.
- Theorem currently pins `f0cc9e54a0db1b50d1603473439ae28bdf292121`; this change
  does not repin either consumer.
- Turvo exposes `with_storage_engines` and wires it to `ServoBuilder`; its
  only in-tree configured-factory caller is a unit test. This does not prove
  the absence of external public API consumers.
- Historical Theorem branch `Codex/turvo-rustyred-storage-1.0` at
  `10fe60c1d8e867dc28e5ffc1974c185f10f01c4c` contains `rustyred-web-storage`
  implementing all four factories, with no product host caller found. Preserve
  that branch/pin as compatibility history. Reusable OrderedMap and RustyRed
  storage substrate are outside obsolete integration cleanup.
- Patch 0008 depends on factory contracts and refactoring from 0005. Patch
  0005 also changes web compatibility defaults and operation context; deleting
  it wholesale would discard useful behavior.
- At the Turvo pin, built-in CacheStorage uses `DummyCacheStorageEngine` and
  `has_cache` returns false. Functional SQLite CacheStorage is not established
  baseline behavior. Preserve this limitation in acceptance reporting.

Storage cleanup must be a forward candidate retaining default SQLite IndexedDB,
registry and localStorage paths/schema, in-memory sessionStorage, origin
boundaries, conformance/error handling and profile restart behavior. Preserve
all applicable regression tests. Default-backend round-trip and isolation
proof must replace retired injection-only proofs. Do not combine this with an
upstream version upgrade, delete historical branches, or repin before required
candidate validation.

## Development and validation changes

The hosted Servo policy retains its macOS/Linux matrix, exact SHA/lineage,
patch-stack, networking, library-storage and request-origin checks. It now also
declares `cargo +1.95.0 test -p servo-storage --test main --locked` and retains
its log. The storage package disables automatic test discovery and declares
that integration target explicitly, so `--lib` alone misses registry,
Web Storage and storage-factory regressions.

The integration policy checker validates this repository's manifest/lockfile
families and patch digests; it does not compare Theorem pins or enforce sole
consumer authority. It remains unchanged.

The root `incremental = false` remains pending measurement. CI already sets
`CARGO_PROFILE_DEV_INCREMENTAL=false` for hosted disk pressure, but that does
not establish the best local application setting. Compare repeat-edit compile
time and target disk use in separate stable private targets before changing
local policy. This candidate makes no benchmark or speedup claim.

Implementation notes: considered deleting the storage-factory patch versus a
forward cleanup; selected the forward candidate because 0008 and the historical
RustyRed adapter depend on its contracts. Considered removing global
incremental disabling immediately versus measuring; retained it pending the
required local evidence while keeping Theorem's independent preview lane free
to proceed.

## Evidence and remaining obligations

This change updates ownership and the declared hosted storage gate. It does not
establish a new engine, embedding, packaging or security runtime pass. Fresh
candidate CI, selected equal-roster WPT comparisons, profile restart/isolation,
macOS/Linux embedding and a real interactive GPUI Servo page remain required
before a product repin or acceptance. Existing historical receipts remain bound
to their original candidates; preserve them without reclassifying them.

Local candidate checks on 2026-10-07:

- `python3 -B -m unittest discover -s scripts -p 'test_*.py'`: passed 15
  tests, including six exact-family integration policy tests.
- `python3 -B scripts/check_integration.py`: source pins, patch digests and
  lockfile families verified.
- PyYAML parsed `.github/workflows/servo-integration.yml`; readback confirmed
  both storage target commands and the integration log artifact.
- `git diff --check`: passed. `actionlint` is unavailable locally; no
  actionlint or hosted workflow execution is claimed.
- No Cargo build, engine regression suite, benchmark or native runtime was
  executed for this documentation/workflow candidate.
