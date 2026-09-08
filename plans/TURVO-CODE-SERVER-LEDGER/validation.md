# Board validation

Canonical SHA-256: `ab206455c67a6dcc18d7d9af4ac802cf14b2465caf626cc5d64e7e3f88b0dcc2`

- Canonical JSON parses and matches the native ledger import.
- Task ids are unique and dependency edges are acyclic.
- 0 observed classes produce 0 work nodes and 0 verifier nodes.
- Every class node has an allowed routing owner and a fingerprint absence proof command.
- Capture-pending state produces no observed class node.
- The terminal node depends on every class verifier.
