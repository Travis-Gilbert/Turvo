# Board validation

Canonical SHA-256: `301c8d5c2c478ede9e60f9a3506cc7d0d94d1c9798e8436c6385a4f5fa0c9db6`

- Canonical JSON parses.
- Required fields, palettes, controllers, and statuses validate.
- Dependency graph is acyclic and every task feeds the terminal node.
- Portable binding has at most one active frontier and its dependencies are complete.
- 12 work nodes have verifier siblings.
- 12 verifier nodes are independently controlled.
- 12 obligations have work and verifier coverage.
- Completed nodes carry discharge evidence and live oracles forbid substitution.
- Parallel work nodes have no exact declared-scope collision.
