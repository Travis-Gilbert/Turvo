# Public Servo HTTP integration

The exact source and patch digest are in `integration.json`. The patch applies
to published Servo 0.5.0's recorded commit
`77fccacc1f1fdce10498d50173aafaa09d02879e` and is published on the isolated
`Travis-Gilbert/servo:turvo/integration-0.5.0` branch. Theorem branches are untouched.

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
race test is bounded stress coverage, not exhaustive scheduling proof. Run:

```sh
cargo +1.94.0 test -p servo-net --test main --locked
```

Hosted test and native application receipts are required before acceptance.
The source patch alone is not a security, performance, or registry-release claim.

Servo's [contribution policy](https://book.servo.org/contributing/getting-started)
prohibits AI-generated submissions. This work stays on the authorized public
fork; no upstream issue, comment, or PR has been submitted. A qualifying published
engine remains an external release gate, not an assumed upstream acceptance.
