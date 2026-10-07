# Public Servo HTTP integration

The exact source and patch digests are in `integration.json`. The unified fork
descends from the upstream Servo `v0.5.0` tag at
`1d44e5dd6a8b64c02f9dbf7fcbdf4ebdd0740019` and is published as
`Travis-Gilbert/servo:theorem/v0.5.0`. It carries both the prior Theorem
embedder work and Turvo's engine/security patches. Turvo and Theorem select
independent exact consumer pins; this directory records Turvo's selected
revision and the shared patch history. See `FORK.md`, `upstream-base` and
[Record 004](../../docs/records/004-independent-servo-consumers.md).
The second patch locks the added Tokio cancellation feature's existing
`futures-util` dependency. The third patch makes the file-manager test reuse
the networking suite's shared runtime instead of initializing and dropping its
own process-wide runtime. The fourth patch marks engine request clients by
global kind so workers cannot inherit a document's protected IPC privilege.
The fifth patch adds value-selected storage engine factories for IndexedDB,
the client storage registry, Web Storage, and Cache Storage while preserving
the existing built-ins when no factory is supplied. It also moves the Turvo
compatibility preferences to fork defaults.
The sixth patch aligns Servo's jemalloc dependency with the 0.5.4 native-link
owner already required by Theorem, allowing the public storage traits package
to resolve in that workspace without two crates claiming `links = "jemalloc"`.
The seventh patch makes the public web-resource response handle `Send`, so a
bounded Turvo interceptor can finish Servo-owned responses from its worker
thread without an unsafe wrapper or a duplicate response path.
The eighth patch is the IndexedDB conformance slice: index records and cursor
iteration, the getAll family and `IDBRecord`, transaction rollback, key
generation where the operation runs, and the removal of the backend's panics
in favour of reported failures. It squashes thirty-three commits and is the
exact range an independent verifier accepted at `6ed6091e4e`.
The ninth patch adds the Web Locks API, ends shared workers when their owner
set empties, and finds named browsing contexts through the constellation. It
squashes three commits and is the range the same verifier accepted at
`e92cdaa790`.
The current public revision is
`e92cdaa790797479c1821c33470c64e0d166feb2`, 56 commits ahead of and zero
commits behind upstream `v0.5.0`. The two newest patch files each cover one
independently verified slice, so the nine files still reverse-apply in order
to the same tree the seven produced at the previous pin.

The request interceptor replaces only HTTP transport, after request policy
selection and before normal response processing. CSP, CORS/preflight, redirects,
cookies, caching, decoding, nosniff and response filtering retain their existing
engine paths. Successful interception cannot overwrite an earlier policy error.
`has_body` allows embedders to reject unsupported uploads before handler dispatch.
Ordinary network uploads and body-aware custom-protocol IPC are unchanged.

An intercepted response must claim, supply valid headers/body, and finish.
Malformed order, mismatched response URLs or lengths, dropped claimed responses,
unsupported final 1xx responses, and cancellation fail closed. HEAD/304 preserve
representation-length semantics. Cancellation wakes stalled embedder waits.

The 64 MiB preference bounds accumulated encoded response bytes. It does not
bound the unbounded message queue, decompression output, or renderer memory.
Interception is buffered, not a streaming API. Cache hits skip handler dispatch;
dynamic handlers must use appropriate `Cache-Control` and `Vary`, and must not
treat per-request interception as their authorization boundary. Synthetic loads
do not fabricate TLS handshake metadata or network connection timing.

Forty-two focused tests cover policy, status/headers, cookies/cache, decoding,
framing, cancellation, upload rejection and fallback. The cancellation-completion
race test is bounded stress coverage, not exhaustive scheduling proof. Four
request-client tests cover caller-kind serialization, fail-closed compatibility,
and builder propagation. Run:

```sh
cargo +1.95.0 test -p servo-net --test main --locked
cargo +1.95.0 test -p servo-net-traits --test request_client --locked
cargo +1.95.0 test -p servo-storage --lib --locked
cargo +1.95.0 test -p servo-storage --test main --locked
```

Both storage targets are required: `--lib` exercises SQLite/backend units,
while `--test main` includes registry, Web Storage and factory-selection
regressions. Declaring these CI commands does not establish a candidate pass.

Hosted test and native application receipts are required before acceptance.
The source patch alone is not a security, performance, or registry-release claim.

Servo's [contribution policy](https://book.servo.org/contributing/getting-started)
prohibits AI-generated submissions. This work stays on the authorized public
fork; no upstream issue, comment, or PR has been submitted. A qualifying published
engine remains an external release gate, not an assumed upstream acceptance.
