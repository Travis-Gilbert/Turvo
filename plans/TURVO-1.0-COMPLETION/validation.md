# Board validation

Canonical SHA-256: `3acdebbd81396e7804d432127141c9890fbf3d665bc1d41e84f267e93a3b9f9a`

- Canonical JSON parses.
- Required fields, palettes, controllers, and statuses validate.
- Dependency graph is acyclic and every task feeds the terminal node.
- Portable binding has at most one active frontier and its dependencies are complete.
- 12 work nodes have verifier siblings.
- 12 verifier nodes are independently controlled.
- 12 obligations have work and verifier coverage.
- Completed nodes carry discharge evidence and live oracles forbid substitution.
- Parallel work nodes have no exact declared-scope collision.
