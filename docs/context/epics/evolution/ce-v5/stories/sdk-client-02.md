# sdk-client-02.md

# SDK-CLIENT-02 — Governed Repo Scaffold

**Status:** DRAFT — READY FOR IMPLEMENTATION  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (implementation + validation), Prod (promotion only)  
**Surface:** Client / CLI / Local Repository Workspace  
**Epic:** SDK-CLIENT — Governed Developer SDK, Onboarding, Repository Ingestion, and Scale-Safe Runtime UX  
**Story Type:** Client-only, offline-safe scaffold story  
**Depends-On:**
- SDK-CLIENT-00 — Identity Creation & Verification (already complete)
- SDK-CLIENT-01 — Authentication Bootstrap (already complete / integrated)
- SDK-CLIENT-01-A — Auth hardening (already complete)

---

## 1. Goal

Implement:

```text
keyhole init vertical
```

so that a builder can generate a **canonical governed repository scaffold** with the correct file structure, declaration artifacts, and context/proof-ready placeholders required for future Keyhole participation.

This story exists to make the repo itself a governance primitive rather than an ad hoc starting point.

The scaffold must:

- generate the canonical repo structure,
- create required declaration files,
- create proof-ready directories and placeholders,
- create context-ready directories and placeholders,
- be deterministic and repeatable,
- remain useful before a live MCP server is required.

---

## 2. Why This Story Exists

The SDK cannot become a governed builder boundary if every repo begins from a different shape and every user invents their own local contract layout.

The scaffold is the first durable client-side act after authentication. It is the point where Keyhole stops being a login flow and becomes a builder operating model.

Without this story:

- local repos will drift structurally,
- later stories will need to compensate for arbitrary file layouts,
- validation will become more complex,
- contract generation will become inconsistent,
- proof generation will feel bolted on,
- context-aware execution will have nowhere canonical to attach local state.

This story therefore establishes the canonical local workspace shape for all later client-side stories.

---

## 3. Story Thesis

A governed repo should not begin as an empty folder plus good intentions.

It should begin as a **declared, repeatable, inspectable workspace** with:

- known file locations,
- known contract entry points,
- known proof paths,
- known context placeholders,
- and a deterministic initialization story.

This story turns:

```text
mkdir repo
```

into:

```text
keyhole init vertical
```

where the result is not just a folder tree, but a **future-governable repo**.

---

## 4. Scope

This story covers:

- the `keyhole init vertical` CLI command,
- local generation of the canonical repo structure,
- creation of declaration artifacts,
- creation of proof-ready and context-ready placeholders,
- deterministic file content generation,
- re-run safety behavior,
- local evidence that the scaffold was generated correctly.

This story does **not** cover:

- server-side repo registration,
- remote validation,
- capability registration,
- governed run submission,
- context compilation itself,
- proof bundle population from live runs,
- ingestion of existing repos,
- any direct MCP mutation.

This is a **local scaffold story only**.

---

## 5. User-Facing Command Contract

### Primary command

```text
keyhole init vertical
```

### Supported intent

The command creates a new governed vertical/project scaffold in the current directory or a named target directory.

### Recommended flags

At minimum, the implementation should support some or all of the following:

```text
keyhole init vertical [name]
keyhole init vertical --path <dir>
keyhole init vertical --force
keyhole init vertical --dry-run
keyhole init vertical --template default
keyhole init vertical --non-interactive
```

### Behavioral rules

- Default behavior should be interactive when useful.
- `--non-interactive` must be deterministic.
- `--dry-run` must show exactly what would be created.
- `--force` must be required before overwriting existing managed files.
- The command must never silently destroy user content.

---

## 6. Canonical Scaffold Output

The generated repository must include a predictable governed shape.

### Minimum repo tree

```text
repo/
├── keyhole.yaml
├── governance_contract.yaml
├── capability_passport.yaml
├── dependencies.yaml
├── capabilities/
│   └── .gitkeep
├── src/
│   └── .gitkeep
├── tests/
│   └── .gitkeep
├── docs/
│   ├── README.md
│   └── context/
│       └── .gitkeep
├── proof_bundle/
│   ├── core/
│   │   └── .gitkeep
│   ├── extended/
│   │   └── .gitkeep
│   └── README.md
├── context/
│   ├── requests/
│   │   └── .gitkeep
│   ├── resolved/
│   │   └── .gitkeep
│   └── README.md
└── .keyhole/
    ├── state/
    │   └── .gitkeep
    ├── cache/
    │   └── .gitkeep
    └── README.md
```

The exact tree may evolve slightly, but the story must preserve these ideas:

- root declarations,
- capabilities directory,
- implementation directory,
- tests directory,
- docs directory,
- proof-ready structure,
- context-ready structure,
- internal tool state/cache location.

---

## 7. Required Generated Files

### 7.1 `keyhole.yaml`

Purpose:
- repo identity,
- local metadata,
- declared project type,
- future registration anchor.

Minimum placeholder shape:

```yaml
schema_version: v0.1
repo:
  name: <repo-name>
  kind: vertical
  owner: Keyhole Solution Foundation
  visibility: private
sdk:
  initialized_by: keyhole init vertical
  initialized_at: <timestamp>
  template: default
context:
  mode: explicit
proof:
  enabled: true
```

### 7.2 `governance_contract.yaml`

Purpose:
- local governance contract,
- required tests,
- local invariants,
- produced capabilities.

Minimum placeholder shape:

```yaml
schema_version: v0.1
repo: <repo-name>
parent_repo: null
produces: []
required_tests: []
local_invariants: []
compatibility_contracts: []
```

### 7.3 `capability_passport.yaml`

Purpose:
- future portable proof / capability identity object.

Minimum placeholder shape:

```yaml
schema_version: v0.1
capabilities: []
owner_repo: <repo-name>
visibility: private
proofs: []
trust:
  sbom_digest: null
  attestation_digest: null
  transparency_ref: null
```

### 7.4 `dependencies.yaml`

Purpose:
- declared upstream capability dependencies.

Minimum placeholder shape:

```yaml
schema_version: v0.1
dependencies: []
```

### 7.5 `docs/README.md`

Purpose:
- human-readable explanation of the scaffold and next steps.

Must include:
- what files were generated,
- what each root declaration means,
- suggested next commands (`validate`, later `register`, later `context`, later `run`),
- explicit note that the scaffold is local and not yet registered with MCP.

### 7.6 `proof_bundle/README.md`

Purpose:
- explain hot vs extended proof layout,
- establish proof-ready structure before live runs exist.

### 7.7 `context/README.md`

Purpose:
- explain local context request / resolved artifact placeholders,
- establish that governed execution will eventually bind to explicit context.

### 7.8 `.keyhole/README.md`

Purpose:
- explain local tool-managed state and cache area,
- clarify that users should not treat this as the source of truth.

---

## 8. Context-Ready Placeholder Requirements

This story must include **context-ready placeholders** even though live context compilation is implemented later.

The scaffold must make room for:

- local context requests,
- resolved context artifacts,
- context references used by later run workflows.

### Required directories

```text
context/requests/
context/resolved/
```

### Required semantics

- `context/requests/` is the local human/tool staging area for input specifications that may later become ContextCards or equivalent request artifacts.
- `context/resolved/` is the local repository-visible place where resolved context references or summaries may be materialized when appropriate.
- The scaffold must not pretend context is optional for the long-term client roadmap.

### Important rule

The placeholders must prepare the repo for explicit governed context without faking a live compile or pretending that context can be inferred invisibly.

---

## 9. Proof-Ready Placeholder Requirements

The scaffold must include **proof-ready placeholders** from day one.

### Required directories

```text
proof_bundle/core/
proof_bundle/extended/
```

### Required semantics

- `proof_bundle/core/` is reserved for replay-critical proof artifacts.
- `proof_bundle/extended/` is reserved for non-essential or bulky evidence.
- The scaffold must make the future proof split visible before the first run exists.

### Required explanation

The generated README must explain:

- hot core vs extended evidence,
- why this split exists,
- that later stories populate these areas from real events/runs.

---

## 10. Determinism Requirements

This story is not complete unless scaffold generation is deterministic.

### Determinism means

For the same:
- repo name,
- template,
- flags,
- story version,

the command must generate the same structure and the same normalized file content except for allowed volatile fields like timestamps.

### Allowed volatility

Only explicitly allowed metadata may differ between runs, such as:
- initialization timestamp,
- generated correlation/request id if shown in the console only.

### Forbidden nondeterminism

- random placeholder content,
- unstable ordering in YAML lists/maps,
- inconsistent README text,
- different tree shape from one run to another.

---

## 11. Re-Run / Existing Directory Rules

This story must define safe rerun behavior.

### Case A — empty target directory

Expected outcome:
- scaffold succeeds
- files created normally

### Case B — existing governed repo already initialized

Expected outcome:
- command detects existing scaffold
- exits safely with clear explanation
- suggests `--force` or a future `upgrade` command if appropriate

### Case C — partially initialized or conflicting directory

Expected outcome:
- command refuses to overwrite managed files silently
- reports exact conflicts
- supports `--dry-run` to inspect what would happen

### Case D — `--force`

Expected outcome:
- only managed scaffold files may be overwritten
- user content must not be silently deleted
- behavior must be explicit and logged in proof/evidence

---

## 12. UX Requirements

### 12.1 Success output

A successful init should show:

- repo path
- files created
- next steps
- whether scaffold was created fresh or updated

Example:

```text
✔ Governed repo scaffold created
Path: ./my-vertical
Files: keyhole.yaml, governance_contract.yaml, capability_passport.yaml, dependencies.yaml
Next:
  1. keyhole validate
  2. edit governance_contract.yaml
  3. edit capability_passport.yaml
  4. later: keyhole register
```

### 12.2 Dry-run output

Must show the exact file tree and managed files that would be created.

### 12.3 Error UX

Must clearly distinguish:
- invalid target path,
- existing initialized repo,
- conflicting unmanaged files,
- permission errors.

### 12.4 Progressive disclosure

The command must feel simple for a first-time builder, while the generated files make the deeper governance model visible for advanced use.

---

## 13. Local Evidence / Proof Requirements

Even though this is an offline-safe client story, it still needs replayable local evidence.

### Minimum local artifact expectations

The implementation should produce or be testable against:

- file tree snapshot,
- generated file contents,
- normalized digest(s) for managed scaffold content,
- summary of generated artifacts,
- deterministic test fixtures.

### Optional local proof artifact

A local init summary artifact may be emitted into `.keyhole/state/` or an equivalent test artifact directory, but this story does not require a full server-backed proof bundle.

### Rule

This story must be provable locally through deterministic scaffold outputs.

---

## 14. Acceptance Criteria

This story is complete only when all of the following are true:

1. `keyhole init vertical` creates the canonical governed repo structure.
2. The required root declaration files are generated.
3. Context-ready placeholders are present.
4. Proof-ready placeholders are present.
5. The scaffold is deterministic for the same inputs.
6. Dry-run mode shows exact intended changes.
7. Existing initialized repos are detected safely.
8. Unmanaged conflicting files are not silently overwritten.
9. Success output clearly explains next steps.
10. The scaffold is usable without a live MCP server.

---

## 15. Test Plan

### 15.1 Unit tests

- command argument parsing
- target path resolution
- deterministic file content generation
- YAML serialization stability
- dry-run output correctness
- existing-repo detection
- conflict detection

### 15.2 Golden-file tests

- generated `keyhole.yaml`
- generated `governance_contract.yaml`
- generated `capability_passport.yaml`
- generated `dependencies.yaml`
- generated README files
- generated tree snapshot

### 15.3 Integration-style local tests

- initialize into empty temp dir
- rerun against initialized dir
- initialize with `--force`
- initialize with `--dry-run`
- initialize nested path

### 15.4 Negative tests

- invalid path
- permission denied
- conflicting unmanaged file
- malformed template selection

---

## 16. Recommended Generated Tree (Reference Form)

```text
<repo-name>/
├── keyhole.yaml
├── governance_contract.yaml
├── capability_passport.yaml
├── dependencies.yaml
├── capabilities/
│   └── .gitkeep
├── src/
│   └── .gitkeep
├── tests/
│   └── .gitkeep
├── docs/
│   ├── README.md
│   └── context/
│       └── .gitkeep
├── proof_bundle/
│   ├── core/
│   │   └── .gitkeep
│   ├── extended/
│   │   └── .gitkeep
│   └── README.md
├── context/
│   ├── requests/
│   │   └── .gitkeep
│   ├── resolved/
│   │   └── .gitkeep
│   └── README.md
└── .keyhole/
    ├── state/
    │   └── .gitkeep
    ├── cache/
    │   └── .gitkeep
    └── README.md
```

This reference tree is part of the story contract.

---

## 17. Future Compatibility Hooks

This scaffold must prepare for later client stories without pre-implementing them.

### Must be compatible with future:
- local validation pipeline (`sdk-client-06`)
- capability passport workflows (`sdk-client-05`)
- repo registration (`sdk-client-07`)
- governed context lifecycle (`sdk-client-16`)
- proof hot/cold split (`sdk-client-13`)
- governance explainability surfaces (`sdk-client-20`)

### Important principle

The scaffold should not need structural redesign when those stories land.

---

## 18. Non-Goals

This story does **not**:

- register the repo with MCP
- contact the network by default
- generate live contexts
- execute governed runs
- ingest existing repos
- produce full runtime proof bundles
- declare final trust metadata values
- infer capabilities automatically

It only creates the **correct governed starting shape**.

---

## 19. Completion Signal

This story is complete when a new builder can run:

```text
keyhole init vertical my-vertical
```

and get a local repo that is:

- canonically shaped,
- declaration-ready,
- context-ready,
- proof-ready,
- deterministic,
- safe to rerun,
- and usable before any live MCP dependency exists.

---

## 20. One-Line Summary

Generate a deterministic governed repo scaffold with canonical declarations, context-ready placeholders, and proof-ready structure so every future Keyhole vertical starts from the same lawful local shape.
