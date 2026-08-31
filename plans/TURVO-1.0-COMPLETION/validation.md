# Board validation

Canonical SHA-256: `7af2ed578ba07b057f27605aed5bdde4ea3d90548539e7e329bc17fef3e8b380`

- Canonical JSON parses.
- Required fields, palettes, controllers, and statuses validate.
- Dependency graph is acyclic and every task feeds the terminal node.
- Portable binding has at most one active frontier and its dependencies are complete.
- 13 work nodes have verifier siblings.
- 13 verifier nodes are independently controlled.
- 13 obligations have work and verifier coverage.
- Completed nodes carry discharge evidence and live oracles forbid substitution.
- Parallel work nodes have no exact declared-scope collision.
