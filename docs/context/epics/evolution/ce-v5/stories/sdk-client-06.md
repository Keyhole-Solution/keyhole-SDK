# sdk-client-06.md

# SDK-CLIENT-06 — Local Validation Pipeline

**Status:** DRAFT — FULLY EXPANDED CLIENT STORY  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (implementation + validation), Prod (promotion only)  
**Surface:** Client (CLI / SDK local validation boundary)  
**Zipper Pair:** `sdk-server-06.md`  
**Purpose:** Define the canonical client-side local validation pipeline for governed repositories before remote ingestion, registration, or governed run submission.

---

## 1. Goal

Establish `keyhole validate` as the **deterministic local enforcement gate** for governed repositories.

This story ensures the client can validate a repository locally before it attempts server registration, remote validation, governed run submission, or downstream proof generation.

The local validation pipeline must check:

- schema correctness,
- dependency declaration correctness,
- capability namespace correctness,
- compatibility contract correctness,
- repo-shape and artifact presence where required,
- deterministic policy violations that can be caught without a live MCP server.

The client must fail early, explain clearly, and produce repair guidance rather than letting malformed governance artifacts drift into the server boundary.

---

## 2. Why This Story Exists

The revised `sdk-client-INDEX` makes the client responsible for catching malformed governance declarations locally before they hit the MCP boundary, while preserving the server as the final authority for remote validation and invariant enforcement. fileciteturn0file0

That means the SDK must not behave like a thin transport wrapper that forwards broken repo state upstream and waits for the server to reject it.

Instead, the client must provide:

- a fast local validation pass,
- deterministic validation output,
- explicit reject reasons,
- repair suggestions,
- and a local proof artifact showing what was checked and why the result was PASS / FAIL.

Without this story:

- malformed contracts reach the boundary too late,
- builders get slower feedback,
- onboarding quality degrades,
- proof bundles begin too late in the lifecycle,
- and the server becomes the first place where obvious client-shape issues are discovered.

This story exists to make validation **local-first, deterministic, and repair-oriented**.

---

## 3. Strategic Role

SDK-CLIENT-06 is the local governance gate that sits after scaffold generation and before any meaningful remote participation.

### Layering

```text
sdk-client-02  → governed repo scaffold
sdk-client-03  → namespace enforcement
sdk-client-04  → governance contract + dependency schema
sdk-client-05  → capability passport generation
sdk-client-06  → local validation pipeline
sdk-client-07+ → registration / remote interaction / runs / ingestion
```

This story is where the client first says:

```text
this repo is structurally and declaratively fit
for governed participation
```

It does not replace remote validation. It establishes the local preflight discipline that every governed repo should pass before touching the server.

---

## 4. Scope

This client story covers:

- the `keyhole validate` command,
- local validation of canonical repo structure,
- local validation of required artifact files,
- schema validation for governance contract and dependency declarations,
- capability namespace validation,
- compatibility and version rule checks,
- deterministic error reporting,
- repair suggestion generation,
- validation success artifact generation,
- zipper alignment with optional remote validation hooks on the server side.

This story does **not** cover:

- remote server persistence,
- final invariant enforcement at the MCP boundary,
- capability registration,
- governed run execution,
- async execution behavior,
- context compilation,
- memory access,
- marketplace or billing features.

---

## 5. User-Facing Command Contract

### Canonical command

```bash
keyhole validate
```

### Supported forms

```bash
keyhole validate
keyhole validate <path>
keyhole validate --json
keyhole validate --strict
keyhole validate --proof
keyhole validate --quiet
```

### Command behavior

The command must:

1. locate the governed repo root,
2. load canonical Keyhole artifacts,
3. run deterministic local checks,
4. summarize all failures and warnings,
5. emit repair suggestions,
6. return a non-zero exit code on failure,
7. optionally emit a validation success artifact and proof metadata on pass.

### Exit codes

- `0` — validation passed
- `1` — validation failed
- `2` — repo root / required file resolution failure
- `3` — internal CLI/tooling error

---

## 6. Validation Domains

The local validation pipeline must cover four mandatory validation domains.

### 6.1 Schema validation

Validate canonical Keyhole files, including at minimum:

- `keyhole.yaml`
- `governance_contract.yaml`
- `dependencies.yaml`
- `capability_passport.yaml` (when present or required by repo state)

Checks include:

- valid file presence where required,
- parseable YAML/JSON,
- required fields present,
- required field types correct,
- unsupported fields flagged according to policy,
- canonical schema version handling.

### 6.2 Dependency validation

Validate declared dependencies, including:

- dependency object shape,
- capability field presence,
- provider field rules,
- version / major-line expectations,
- digest format when pinned,
- duplicate dependency conflicts,
- invalid provider or empty capability references.

### 6.3 Namespace validation

Validate capability names using the namespace rules established in `sdk-client-03.md`, including:

- `<domain>.<category>.<capability>.v<major>` shape,
- no illegal characters,
- version suffix required,
- deterministic rejection of malformed names.

### 6.4 Compatibility validation

Validate local compatibility rules and dependency compatibility posture, including:

- incompatible major-line references,
- missing compatibility metadata when required,
- deprecated or conflicting version combinations,
- invalid or contradictory compatibility declarations,
- declared capability / dependency mismatches.

---

## 7. Required Artifact Awareness

The validator must understand the governed scaffold and repo-shape rules introduced earlier in the epic.

At minimum it must verify:

- the repo appears to be a Keyhole-governed repo,
- expected governance files exist where required,
- missing required artifacts are surfaced as deterministic errors,
- optional artifacts are treated as optional unless a later story or repo state elevates them to required.

### Minimum expected scaffold awareness

```text
repo/
 ├── keyhole.yaml
 ├── governance_contract.yaml
 ├── capability_passport.yaml   (required in some flows, optional in others)
 ├── dependencies.yaml
 ├── capabilities/
 ├── src/
 ├── tests/
 ├── docs/
 └── proof_bundle/
```

The validator must not require every possible future artifact, but it must know enough to say when the repo is structurally incomplete for the current workflow.

---

## 8. Validation Result Model

The client must produce a deterministic result model.

### Result classes

- `PASS`
- `FAIL`
- `WARN`

### Recommended result shape

```json
{
  "status": "FAIL",
  "repo_root": "/path/to/repo",
  "checks": {
    "schema": "PASS",
    "dependencies": "FAIL",
    "namespace": "PASS",
    "compatibility": "WARN"
  },
  "errors": [
    {
      "code": "DEPENDENCY_PROVIDER_MISSING",
      "file": "dependencies.yaml",
      "path": "dependencies[1]",
      "message": "provider is required for this dependency class",
      "repair": [
        "add provider for crm.salesforce.sync.v2",
        "re-run keyhole validate"
      ]
    }
  ],
  "warnings": [],
  "proof_ref": null
}
```

The result model must be stable enough for:

- CLI human display,
- JSON output,
- future CI integration,
- proof bundle inclusion.

---

## 9. Repair Guidance Contract

Validation failures must not dead-end.

Every deterministic failure should, where possible, include:

- a short reason,
- the exact file and field path,
- a stable error code,
- a suggested next action,
- optional command-level follow-up guidance.

### Example

```json
{
  "code": "CAPABILITY_NAMESPACE_INVALID",
  "message": "Capability name must end in .v<major>",
  "repair": [
    "rename workorder.assignment.engine to workorder.assignment.engine.v1",
    "run keyhole validate again"
  ]
}
```

The platform doctrine already requires repair-oriented failure behavior. This story is the local validation embodiment of that rule. fileciteturn0file0

---

## 10. Strict vs Standard Validation

### Standard mode

Standard mode should fail on deterministic structural violations and surface warnings for softer issues.

### Strict mode

`--strict` elevates selected warnings into failures, for example:

- optional metadata that is missing but strongly recommended,
- unresolved compatibility hints,
- weak dependency declarations,
- proof bundle folder missing,
- trust-ready placeholders absent where policy expects them.

Strict mode must be deterministic and documented.

---

## 11. Proof / Artifact Output

On successful validation, the client must be able to emit a local validation artifact.

### Minimum deliverable

A validation success artifact containing:

- validation timestamp,
- repo root,
- checked files,
- normalized summary of checks,
- final PASS result,
- optional digest / correlation reference.

### Suggested artifact location

```text
proof_bundle/validation/
  validation_result.json
  summary.md
```

### Rule

A passing repo should produce an artifact that can later be included in proof bundles, zipped story evidence, or CI validation records.

---

## 12. Server Zipper Expectations (`sdk-server-06.md`)

This is the client-half of a zipper.

### Client responsibilities

- catch deterministic local issues before network calls,
- reject malformed repo state early,
- emit local validation artifact,
- normalize local output shape.

### Server responsibilities

- optional remote validation,
- invariant enforcement hooks,
- server-side final truth when remote participation occurs.

### Zipper closure principle

A repo that passes local validation must still be allowed to fail remote validation if the server enforces stronger or newer invariants.

The client must not claim final authority.

---

## 13. Acceptance Criteria

This story is complete only when all of the following are true:

1. `keyhole validate` exists and runs locally without a live MCP server.
2. Schema validation catches malformed governed files deterministically.
3. Dependency validation catches malformed dependency/provider declarations deterministically.
4. Namespace validation applies the canonical capability naming rules.
5. Compatibility checks detect invalid or contradictory compatibility posture.
6. A failing repo is blocked locally with a non-zero exit code.
7. A passing repo emits a validation success artifact.
8. Validation failures include deterministic repair guidance.
9. JSON output mode is stable and machine-readable.
10. The client story aligns cleanly with `sdk-server-06.md` for optional remote validation and invariant enforcement.

---

## 14. Proof / Tests

The following proof and test expectations must be satisfied.

### 14.1 Required proof outcomes

- failing repo blocked
- passing repo emits validation success artifact
- compatibility violations rejected with repair suggestions

### 14.2 Required local tests

#### Positive tests
- valid governed repo passes validation
- valid scaffold from `sdk-client-02` passes base checks
- valid namespace and dependencies pass consistently
- success artifact is written when requested or by default policy

#### Negative tests
- malformed `governance_contract.yaml` rejected
- malformed `dependencies.yaml` rejected
- invalid capability namespace rejected
- invalid compatibility declaration rejected
- missing required file rejected
- duplicate conflicting dependency declarations rejected

#### Output tests
- JSON output shape remains stable
- strict mode elevates selected warnings correctly
- repair suggestions appear for supported failure classes

#### Determinism tests
- same repo state → same validation outcome
- same repo state → same normalized result structure

---

## 15. Error Classes (Minimum)

Suggested stable error codes include:

- `REPO_ROOT_NOT_FOUND`
- `KEYHOLE_FILE_MISSING`
- `SCHEMA_PARSE_ERROR`
- `SCHEMA_REQUIRED_FIELD_MISSING`
- `DEPENDENCY_PROVIDER_MISSING`
- `DEPENDENCY_DUPLICATE_CONFLICT`
- `CAPABILITY_NAMESPACE_INVALID`
- `COMPATIBILITY_CONTRACT_INVALID`
- `STRICT_MODE_WARNING_ESCALATED`

These codes must be deterministic and suitable for future CI and explainability surfaces.

---

## 16. UX Requirements

The command output must be readable and useful.

### Human-readable mode

Should summarize:

- PASS / FAIL,
- counts of errors and warnings,
- first relevant failures,
- exact repair guidance.

### JSON mode

Must produce a structured envelope suitable for automation.

### Quiet mode

Should suppress success chatter while preserving non-zero failure behavior.

---

## 17. Non-Goals

This story does **not**:

- perform server registration,
- perform remote invariant enforcement,
- compile context,
- execute governed runs,
- query or mutate memory,
- verify live registry/provider existence,
- replace later trust enforcement stories.

This is a **local-first validation gate**.

---

## 18. Strategic Statement

SDK-CLIENT-06 is where the client stops being a scaffold generator and becomes a local governance tool.

It ensures the builder can answer, before touching the server:

```text
Is this repo structurally fit for governed participation?
```

That is the correct role of `keyhole validate`.

---

## 19. One-Line Summary

**Implement `keyhole validate` as a deterministic local governance gate that enforces schema, dependency, namespace, and compatibility rules, blocks malformed repos early, and emits a replayable local validation artifact on success.**
