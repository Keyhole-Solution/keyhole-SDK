# my-first-app

This repository was scaffolded by `keyhole init vertical`.

## Generated Declaration Files

| File | Purpose |
|------|---------|
| `keyhole.yaml` | Local repo identity, scaffold metadata, and future registration anchor |
| `governance_contract.yaml` | Local governance rules, produced capabilities, required tests, and invariants |
| `capability_passport.yaml` | Future portable capability / proof identity placeholder |
| `dependencies.yaml` | Declared upstream capability dependencies |

## Important

This scaffold is **local only**. Generating it does not register this
repository with the MCP boundary, does not create governed proof, and
does not imply live platform participation.

## Next Steps

1. `keyhole validate` — validate local declaration files
2. Edit `governance_contract.yaml` — declare capabilities and invariants
3. Edit `capability_passport.yaml` — declare capabilities
4. `keyhole repo register` — register with the MCP boundary (later)
5. `keyhole context compile` — compile governed context (later)
6. `keyhole run --context auto` — execute a governed run (later)
