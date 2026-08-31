# Board validation

Canonical SHA-256: `91235407bdc29086e28edf393c79e56da60be8122b5192cdd9578dc6bb3a2660`

- Canonical JSON parses.
- Required fields, palettes, controllers, and statuses validate.
- Dependency graph is acyclic and every task feeds the terminal node.
- Portable binding has at most one active frontier and its dependencies are complete.
- 13 work nodes have verifier siblings.
- 13 verifier nodes are independently controlled.
- 13 obligations have work and verifier coverage.
- Completed nodes carry discharge evidence and live oracles forbid substitution.
- Parallel work nodes have no exact declared-scope collision.
