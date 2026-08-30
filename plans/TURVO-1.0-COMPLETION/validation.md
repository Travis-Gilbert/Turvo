# Board validation

Canonical SHA-256: `629c52ad58e9ae256e3b8e10d7bf8f198dd6532b99d6684351c909854f07e690`

- Canonical JSON parses.
- Required fields, palettes, controllers, and statuses validate.
- Dependency graph is acyclic and every task feeds the terminal node.
- Portable binding has at most one active frontier and its dependencies are complete.
- 12 work nodes have verifier siblings.
- 12 verifier nodes are independently controlled.
- 12 obligations have work and verifier coverage.
- Completed nodes carry discharge evidence and live oracles forbid substitution.
- Parallel work nodes have no exact declared-scope collision.
