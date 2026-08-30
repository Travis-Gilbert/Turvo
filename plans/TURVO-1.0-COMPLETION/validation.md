# Board validation

Canonical SHA-256: `b7edbcb983fc7ddccf8c60d17ef7e3fe1ad6a6875c11811b6eb979ad67eb20df`

- Canonical JSON parses.
- Required fields, palettes, controllers, and statuses validate.
- Dependency graph is acyclic and every task feeds the terminal node.
- Portable binding has at most one active frontier and its dependencies are complete.
- 12 work nodes have verifier siblings.
- 12 verifier nodes are independently controlled.
- 12 obligations have work and verifier coverage.
- Completed nodes carry discharge evidence and live oracles forbid substitution.
- Parallel work nodes have no exact declared-scope collision.
