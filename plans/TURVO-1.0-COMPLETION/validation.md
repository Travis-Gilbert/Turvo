# Board validation

Canonical SHA-256: `016761279bad1e3338f54061260553cc5cb9eef3ce0b1969d9013736a4c50ca2`

- Canonical JSON parses.
- Required fields, palettes, controllers, and statuses validate.
- Dependency graph is acyclic and every task feeds the terminal node.
- Portable binding has at most one active frontier and its dependencies are complete.
- 11 work nodes have verifier siblings.
- 11 verifier nodes are independently controlled.
- 12 obligations have work and verifier coverage.
- Completed nodes carry discharge evidence and live oracles forbid substitution.
- Parallel work nodes have no exact declared-scope collision.
