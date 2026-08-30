# Board validation

Canonical SHA-256: `13e1eb23cc113380065dc2a0f29957978d859bb8dac12bac2f301935b2b65e1d`

- Canonical JSON parses.
- Required fields, palettes, controllers, and statuses validate.
- Dependency graph is acyclic and every task feeds the terminal node.
- Portable binding has at most one active frontier and its dependencies are complete.
- 11 work nodes have verifier siblings.
- 11 verifier nodes are independently controlled.
- 12 obligations have work and verifier coverage.
- Completed nodes carry discharge evidence and live oracles forbid substitution.
- Parallel work nodes have no exact declared-scope collision.
