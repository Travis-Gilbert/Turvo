# Board validation

Canonical SHA-256: `e80beb1aa16e530ef2571a9a7f011f4363ceedeb98fbf15e0fe9d11e89fba7f2`

- Canonical JSON parses.
- Required fields, palettes, controllers, and statuses validate.
- Dependency graph is acyclic and every task feeds the terminal node.
- Portable binding has at most one active frontier and its dependencies are complete.
- 13 work nodes have verifier siblings.
- 13 verifier nodes are independently controlled.
- 13 obligations have work and verifier coverage.
- Completed nodes carry discharge evidence and live oracles forbid substitution.
- Parallel work nodes have no exact declared-scope collision.
