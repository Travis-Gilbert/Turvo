# Board validation

Canonical SHA-256: `a50970801815dc810521ac4a603c073dc6b59de7bf8053ba179f33a2c44767ec`

- Canonical JSON parses.
- Required fields, palettes, controllers, and statuses validate.
- Dependency graph is acyclic and every task feeds the terminal node.
- Portable binding has at most one active frontier and its dependencies are complete.
- 11 work nodes have verifier siblings.
- 11 verifier nodes are independently controlled.
- 12 obligations have work and verifier coverage.
- Completed nodes carry discharge evidence and live oracles forbid substitution.
- Parallel work nodes have no exact declared-scope collision.
