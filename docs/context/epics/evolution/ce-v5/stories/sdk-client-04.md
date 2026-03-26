# sdk-client-04.md

# SDK-CLIENT-04 — Governance Contract + Dependency Schema

**Status:** DRAFT — FULLY EXPANDED CLIENT STORY  
**Epic:** SDK-CLIENT — Governed Developer SDK, Onboarding, Repository Ingestion, and Scale-Safe Runtime UX  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (implementation + validation), Prod (promotion only)  
**Story Type:** Client-side zipper story  
**Depends-On:** SDK-CLIENT-02 — Governed Repo Scaffold; SDK-CLIENT-03 — Capability Namespace Enforcement  
**Server Pair:** `sdk-server-04.md`  
**Primary Client Surface:** `keyhole validate`  
**Last Updated:** 2026-03-26

---

## 1. Purpose

SDK-CLIENT-04 establishes the **local governance contract and dependency schema validation layer** for governed repositories.

This story ensures that a builder can validate the repository’s declared governance shape **before** attempting registration with the MCP boundary.

The client must be able to inspect, parse, validate, and explain the repo’s core governance artifacts locally, so malformed declarations are caught early, deterministically, and with repair guidance.

This story exists to make the SDK responsible for first-pass structural correctness rather than delegating all contract failure to server-side ingestion.

---

## 2. Goal

Implement local schema validation via:

```text
keyhole validate
```

and ensure the client can verify that:

- governance contract files are present where required,
- YAML/JSON structure is valid,
- required keys exist,
- field types are correct,
- capability and dependency declarations conform to canonical schema,
- dependency/provider declarations are normalizable and explainable,
- malformed contracts are rejected locally before MCP registration.

---

## 3. Why This Story Exists

The scaffold story creates the repo shape.
The namespace story ensures capability identifiers are well-formed.

This story turns those files and names into a **coherent, governed contract surface**.

Without SDK-CLIENT-04:

- builders can generate valid-looking repos that still contain invalid governance declarations,
- malformed dependencies are only discovered after server submission,
- provider ambiguity leaks into registration,
- repair becomes reactive rather than immediate,
- the SDK feels brittle and server-dependent instead of disciplined and helpful.

This story therefore makes `keyhole validate` the first real **governance gate** in the client experience.

---

## 4. Scope

This client story covers:

- local schema validation for governance files,
- dependency declaration parsing and normalization preview,
- deterministic validation output,
- repair-oriented error reporting,
- validation summaries suitable for proof bundles,
- preflight readiness for later registration.

This story does **not** cover:

- server-side contract storage,
- final server-side normalization authority,
- remote policy checks,
- actual repo registration,
- run execution,
- context compilation,
- proof bundle storage on the server.

Those belong to later zipper stories or the paired server story.

---

## 5. Primary Client Deliverable

The client must implement:

```text
keyhole validate
```

This command validates the canonical governed repo files, beginning with:

- `keyhole.yaml`
- `governance_contract.yaml`
- `capability_passport.yaml`
- `dependencies.yaml`

It must produce a deterministic result with:

- pass/fail summary,
- file-by-file validation status,
- error list,
- repair guidance,
- normalization preview where applicable.

---

## 6. Client Responsibilities

The client implementation must provide the following capabilities.

### 6.1 File discovery

Locate the canonical governance files in the repo root.

Required behavior:

- detect missing required files,
- distinguish missing vs malformed vs empty,
- support explicit path override if later added,
- fail deterministically when the repo is not scaffold-compliant.

### 6.2 Schema parsing

Parse YAML safely and deterministically.

Required behavior:

- reject invalid YAML/JSON,
- reject duplicate/conflicting structures where parser exposes them,
- report precise file and field path where parsing or schema validation fails.

### 6.3 Governance contract validation

Validate `governance_contract.yaml` for:

- required top-level keys,
- supported field types,
- valid local invariant list shape,
- valid required tests shape,
- valid produced capability declarations,
- valid compatibility contract declarations.

### 6.4 Dependency schema validation

Validate `dependencies.yaml` for:

- required dependency fields,
- canonical capability identifier format,
- provider field shape,
- optional digest shape,
- duplicate dependency handling,
- unsupported or ambiguous field combinations.

### 6.5 Passport file validation

Validate `capability_passport.yaml` for local structural correctness only.

This story does not finalize trust or server lineage validation, but it must ensure that the file is structurally usable.

### 6.6 Normalization preview

The client must be able to show the builder how dependency/provider information will be normalized before server submission.

This is especially important for:

- capability names,
- provider references,
- digest pinning,
- version/provider combinations.

### 6.7 Repair-oriented output

Every validation failure must produce deterministic repair guidance.

Bad example:

```text
Validation failed.
```

Required example shape:

```json
{
  "status": "REJECT",
  "file": "dependencies.yaml",
  "field": "dependencies[1].provider",
  "reason": "provider field missing",
  "repair": [
    "Add a provider for crm.salesforce.sync.v2",
    "Run keyhole search crm.salesforce.sync.v2 to discover eligible providers"
  ]
}
```

---

## 7. Canonical Files Covered

### 7.1 `keyhole.yaml`

Validate minimal repo identity and SDK-managed metadata structure.

Expected client checks include:

- repo name presence,
- schema version presence,
- owner / namespace fields where required,
- file shape compliance.

### 7.2 `governance_contract.yaml`

Validate:

- `repo`
- `parent_repo`
- `produces`
- `required_tests`
- `local_invariants`
- `compatibility_contracts`

as applicable to the declared contract schema.

### 7.3 `capability_passport.yaml`

Validate:

- capability identifier,
- owner repo,
- visibility,
- proof structure,
- delegated capability list shape,
- trust metadata placeholder structure.

### 7.4 `dependencies.yaml`

Validate:

- dependency list shape,
- capability identifiers,
- provider presence/optionality rules,
- digest formatting,
- deterministic field naming.

---

## 8. Command UX

### 8.1 Basic usage

```text
keyhole validate
```

### 8.2 Expected output classes

The command must support at least:

- `PASS`
- `WARN`
- `REJECT`

### 8.3 Human-readable summary

Example:

```text
✔ keyhole.yaml valid
✔ governance_contract.yaml valid
⚠ capability_passport.yaml missing optional trust metadata digests
✖ dependencies.yaml invalid: dependencies[0].provider missing
```

### 8.4 Machine-readable mode

The command should support a JSON output mode or an internal structured result object suitable for:

- CI,
- later proof bundle embedding,
- local test assertions.

### 8.5 Exit codes

Recommended behavior:

- `0` → validation pass
- `1` → validation reject
- `2` → internal CLI/runtime failure

---

## 9. Validation Semantics

### 9.1 Deterministic

The same repo contents must produce the same validation result.

### 9.2 Local-first

The client must not require a live MCP server for baseline schema validation.

### 9.3 Fail-closed

Malformed or ambiguous contract data must not be silently corrected and treated as valid.

### 9.4 Preview, not authority

The client may show normalization preview, but the server remains the final normalization authority during ingestion.

---

## 10. Relationship to Server Pair (`sdk-server-04.md`)

This story is the client half of the zipper.

### Client role

- validate locally,
- catch malformed declarations early,
- preview normalized shapes,
- prepare clean contract payloads.

### Server role

- ingest contracts,
- validate again at boundary,
- normalize dependency/provider fields,
- persist accepted contracts,
- emit authoritative registration events.

### Closure rule

This story is **client-complete** when local validation is correct and replayable.
It is **zipper-complete** only when paired with `sdk-server-04.md` and proven end-to-end.

---

## 11. Acceptance Criteria

This story is complete only when all of the following are true:

1. `keyhole validate` parses the canonical repo governance files locally.
2. Malformed contracts are rejected locally with deterministic reasons.
3. Valid contracts pass local validation.
4. Dependency/provider fields are parsed and presented in a normalization-friendly shape.
5. Capability identifiers inside contract files are validated using canonical namespace rules.
6. The client surfaces repair guidance for every contract rejection class.
7. Validation output is deterministic and testable.
8. The command can run fully without a live MCP server.
9. Validation results are available in a structured format suitable for proof generation.
10. The client is ready to hand validated contracts to the paired server ingestion story.

---

## 12. Proof / Tests

### 12.1 Local proof requirements

The client must produce evidence demonstrating:

- malformed contracts rejected,
- valid contracts accepted,
- dependency/provider fields normalized into a preview structure,
- deterministic validation output across repeated runs.

### 12.2 Required test classes

#### A. Positive tests

- valid `keyhole.yaml` passes
- valid `governance_contract.yaml` passes
- valid `capability_passport.yaml` passes structural validation
- valid `dependencies.yaml` passes
- complete scaffolded repo passes baseline validation

#### B. Negative tests

- missing required file rejected
- invalid YAML rejected
- missing required top-level field rejected
- invalid capability identifier rejected
- invalid dependency/provider combination rejected
- invalid digest shape rejected

#### C. Determinism tests

- repeated validation of the same repo returns the same structured result
- validation summary ordering is stable

#### D. Proof-shape tests

- structured validation result serializes cleanly
- validation result can be embedded into a proof bundle section later

### 12.3 Zipper proof expectations (paired with server)

When paired later with `sdk-server-04.md`, the combined zipper must prove:

- malformed contracts rejected,
- valid contracts accepted and stored,
- dependency/provider fields normalized,
- event: `CONTRACT_REGISTERED`.

---

## 13. Suggested Structured Output Shape

Example result object:

```json
{
  "status": "REJECT",
  "repo": "workorder-platform",
  "files": {
    "keyhole.yaml": "PASS",
    "governance_contract.yaml": "PASS",
    "capability_passport.yaml": "WARN",
    "dependencies.yaml": "REJECT"
  },
  "issues": [
    {
      "file": "dependencies.yaml",
      "field": "dependencies[0].provider",
      "reason": "provider field missing",
      "repair": [
        "Add a provider for payment.stripe.integration.v1"
      ]
    }
  ],
  "normalization_preview": {
    "dependencies": []
  }
}
```

---

## 14. Local Artifact Expectations

This story should support emitting or preparing:

- validation summary markdown,
- structured validation JSON,
- optional normalization preview JSON,
- future-ready proof core section references.

Suggested local output location:

```text
proof_bundle/
  validation_result.json
  validation_summary.md
```

These may be produced directly now or prepared as internal structures for SDK-CLIENT-13.

---

## 15. Non-Goals

This story does **not**:

- perform server registration,
- persist contracts remotely,
- finalize provider resolution against the live registry,
- enforce trust metadata hard gates,
- compile governed context,
- execute governed runs,
- replace server-side validation.

---

## 16. Implementation Notes

### 16.1 Preferred validation order

1. repo root detection
2. required file presence
3. YAML parse
4. schema validation
5. namespace validation
6. dependency/provider normalization preview
7. summary + result emission

### 16.2 Failure design principle

Always fail with:

- exact file,
- exact field,
- deterministic reason,
- next-best repair.

### 16.3 Builder experience principle

`keyhole validate` should feel like a trustworthy preflight, not like a server echo.

---

## 17. Completion Signal

SDK-CLIENT-04 is client-complete when a builder can run:

```text
keyhole validate
```

against a scaffolded repo and receive a deterministic, repair-oriented answer that correctly distinguishes:

- malformed contract,
- missing field,
- invalid namespace,
- bad dependency/provider shape,
- and valid governed contract state.

It becomes zipper-complete when paired server ingestion proves:

- malformed contracts rejected,
- valid contracts accepted and stored,
- dependency/provider fields normalized,
- event: `CONTRACT_REGISTERED`.

---

## 18. One-Line Summary

Implement `keyhole validate` so builders can catch malformed governance and dependency contracts locally, get deterministic repair guidance, and hand clean, normalization-ready declarations to the server ingestion boundary.
