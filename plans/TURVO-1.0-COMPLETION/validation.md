# Board validation

Canonical SHA-256: `4b0fab440e0626d6a2ce176f1c0eba11106ce018b17c4f50f45482adbef649e4`

- Canonical JSON parses.
- Required fields, palettes, controllers, and statuses validate.
- Dependency graph is acyclic and every task feeds the terminal node.
- Portable binding has at most one active frontier and its dependencies are complete.
- 12 work nodes have verifier siblings.
- 12 verifier nodes are independently controlled.
- 12 obligations have work and verifier coverage.
- Completed nodes carry discharge evidence and live oracles forbid substitution.
- Parallel work nodes have no exact declared-scope collision.
