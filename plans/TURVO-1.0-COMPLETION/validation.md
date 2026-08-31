# Board validation

Canonical SHA-256: `2823f8c5ed0356356367d36661bbc6c374a028fae198fa9b3013b1460f9c99af`

- Canonical JSON parses.
- Required fields, palettes, controllers, and statuses validate.
- Dependency graph is acyclic and every task feeds the terminal node.
- Portable binding has at most one active frontier and its dependencies are complete.
- 13 work nodes have verifier siblings.
- 13 verifier nodes are independently controlled.
- 13 obligations have work and verifier coverage.
- Completed nodes carry discharge evidence and live oracles forbid substitution.
- Parallel work nodes have no exact declared-scope collision.
