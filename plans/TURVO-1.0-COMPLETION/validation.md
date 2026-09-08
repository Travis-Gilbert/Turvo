# Board validation

Canonical SHA-256: `e6805a0db8f36fc01c742435d134de3216bccc5ae26e7a53634283614f91c765`

- Canonical JSON parses.
- Required fields, palettes, controllers, and statuses validate.
- Dependency graph is acyclic and every task feeds the terminal node.
- Portable binding has at most one active frontier and its dependencies are complete.
- 13 work nodes have verifier siblings.
- 13 verifier nodes are independently controlled.
- 13 obligations have work and verifier coverage.
- Completed nodes carry discharge evidence and live oracles forbid substitution.
- Parallel work nodes have no exact declared-scope collision.
