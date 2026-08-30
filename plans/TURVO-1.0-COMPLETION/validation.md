# Board validation

Canonical SHA-256: `12804b7efa144e33e238652cbb92d64128f23fc954164a91c3de0af49a7fc9e4`

- Canonical JSON parses.
- Required fields, palettes, controllers, and statuses validate.
- Dependency graph is acyclic and every task feeds the terminal node.
- Portable binding has at most one active frontier and its dependencies are complete.
- 11 work nodes have verifier siblings.
- 11 verifier nodes are independently controlled.
- 12 obligations have work and verifier coverage.
- Completed nodes carry discharge evidence and live oracles forbid substitution.
- Parallel work nodes have no exact declared-scope collision.
