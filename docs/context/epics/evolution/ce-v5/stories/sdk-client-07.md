# sdk-client-07.md

# SDK-CLIENT-07 — Repository Registration with MCP

**Status:** DRAFT — FULLY EXPANDED CLIENT STORY  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (implementation + validation), Prod (governed promotion only)  
**Surface:** Client / CLI / SDK  
**Zipper Pair:** `sdk-server-07.md`  
**Depends-On:**
- `sdk-client-00.md` — Identity Creation & Verification
- `sdk-client-01.md` — Authentication Bootstrap
- `sdk-client-01-a.md` — Auth Hardening
- `sdk-client-02.md` — Governed Repo Scaffold
- `sdk-client-04.md` — Governance Contract + Dependency Schema
- `sdk-client-05.md` — Capability Passport Generation
- `sdk-client-06.md` — Local Validation Pipeline
- `sdk-client-15.md` — Idempotent Transport, Retry, and Request Identity (for final production-grade sealing)

---

## 1. Purpose

This story defines the client-side contract for **repository registration with the MCP boundary**.

Its purpose is to let a builder take a locally scaffolded and locally validated governed repository and formally bind it to the Keyhole platform through a governed registration flow.

This story exists to answer the question:

```text
How does a repo stop being “just a local folder with declarations”
and become a known governed participant in the Keyhole ecosystem?
```

The client must be able to:

- collect the repo’s governed identity and declaration artifacts,
- shape a deterministic registration payload,
- send contracts + passport + metadata to MCP,
- preserve request identity and eventual idempotency semantics,
- surface identity binding clearly to the builder,
- emit replayable local proof that registration was attempted, accepted, replayed, or rejected.

This story is **not** the final server enforcement story. That belongs to `sdk-server-07.md`.

This is the **client-half** of the zipper: the local command, payload shaping, UX, local proof, repair guidance, and deterministic behavior expected before and after the boundary call.

---

## 2. Strategic Role

`SDK-CLIENT-07` is the bridge between:

- **local governed repo state**, and
- **platform-recognized governed participation**.

It sits after scaffold, schema, passport, and validation because the client must not attempt registration from an undefined repo state.

### Flow placement

```text
login
  ↓
init vertical
  ↓
validate
  ↓
generate passport
  ↓
repo register   ← THIS STORY
  ↓
context / run / ingest / explain
```

Without this story, the builder can prepare a governed repo locally but cannot bind it into the MCP ecosystem as an attributable participant.

With this story complete, the builder can move from:

```text
local declaration
```

to:

```text
governed platform participation
```

---

## 3. Why This Story Exists

The platform requires a governed boundary for all external participation.

A repo is not considered part of the ecosystem merely because it contains:

- `keyhole.yaml`
- `governance_contract.yaml`
- `capability_passport.yaml`
- `dependencies.yaml`

Those files define **local governed intent**, but they do not yet establish:

- tenant / org / cohort / worker binding,
- server-recognized repo identity,
- server-side lineage and registry presence,
- canonical boundary admission,
- event emission for platform observability,
- supportable proof that the platform accepted the repo.

This story exists to make repo participation:

- explicit,
- attributable,
- idempotent in intent,
- and inspectable.

It also prevents an anti-pattern:

```text
builders assuming a repo is “registered”
because local files exist
```

Registration must be a governed act, not an assumption.

---

## 4. Client Responsibilities

The client is responsible for:

1. determining whether the current directory is a governed repo,
2. verifying local prerequisites before registration is attempted,
3. loading required declaration artifacts,
4. constructing the registration payload deterministically,
5. attaching identity and request metadata,
6. sending the payload to the MCP registration endpoint,
7. rendering a clear registration result,
8. persisting replayable local proof of the registration attempt,
9. surfacing repair guidance on rejection.

The client is **not** responsible for:

- assigning canonical tenant/org binding on its own,
- mutating server-side registry state directly,
- deciding whether the repo is accepted into canonical participation,
- bypassing the MCP boundary,
- silently inventing missing contract fields.

---

## 5. Command Contract

### Primary command

```text
keyhole repo register
```

### Optional examples

```text
keyhole repo register
keyhole repo register --shadow
keyhole repo register --json
keyhole repo register --path ./my-repo
keyhole repo register --non-interactive
keyhole repo register --force-proof
```

### Minimum expectations

The command must:

- locate the repo root,
- verify required files exist,
- ensure validation has either succeeded or is executed as part of the flow,
- load the latest local passport,
- construct the registration payload,
- call the MCP registration endpoint,
- emit a replayable local proof bundle,
- show the builder whether registration:
  - succeeded,
  - replayed,
  - was deferred,
  - or was rejected.

---

## 6. Precondition Contract

Before the client sends a registration request, it must verify all of the following locally.

### 6.1 Required files exist

At minimum:

- `keyhole.yaml`
- `governance_contract.yaml`
- `capability_passport.yaml`
- `dependencies.yaml` (when required by repo type)

### 6.2 Repo shape is valid

The repo must satisfy the canonical governed scaffold expectations from `sdk-client-02.md`.

### 6.3 Namespace and schema are valid

All relevant declarations must pass local checks from:

- `sdk-client-03.md`
- `sdk-client-04.md`
- `sdk-client-06.md`

### 6.4 A local passport exists or can be generated deterministically

If the passport is missing but the repo is valid, the client may generate it before registration.

### 6.5 Auth context exists

The user must be logged in through the CLI bootstrap flow.

### 6.6 Local validation state is known

The client must not register a repo with known-failing local validation unless an explicitly governed override mode exists later. For this story, the default is fail-closed.

---

## 7. Payload Construction

The client must construct a deterministic registration payload from the repo state.

### 7.1 Required payload sections

At minimum, the payload should include:

- repo identity metadata
- governance contract
- capability passport
- dependencies
- local validation summary
- local proof correlation metadata
- client version / command metadata

### 7.2 Suggested payload shape

```json
{
  "repo": {
    "name": "workorder-platform",
    "path_digest": "sha256:...",
    "repo_digest": "sha256:...",
    "workspace_hint": "local"
  },
  "artifacts": {
    "keyhole": {...},
    "governance_contract": {...},
    "capability_passport": {...},
    "dependencies": {...}
  },
  "validation": {
    "status": "PASS",
    "artifact_ref": "proof_bundle/validation_success.json"
  },
  "client": {
    "command": "keyhole repo register",
    "cli_version": "0.x.y"
  }
}
```

The exact wire shape may evolve with the server zipper pair, but the client must ensure deterministic ordering and stable serialization for proof and replay.

---

## 8. Identity Context Requirements

This story must preserve the “no floating execution” rule.

Every registration attempt must carry deterministic identity context.

### 8.1 Required identity fields (resolved from authenticated session and local repo state)

The client must be ready to bind or receive binding for:

- `tenant_id`
- `org_id`
- `user_id`
- `cohort_id`
- `worker_id`
- `repo_id`
- `workspace_id`
- `origin`
- `purpose`

### 8.2 Client role

The client may not invent authoritative tenant or org truth, but it must:

- send the information it knows,
- include repo-local identity,
- preserve returned server binding in local proof and UX,
- display the resolved registration context clearly.

---

## 9. Idempotency and Request Identity

This story is one of the first client stories where real write-bearing semantics matter.

Even if full platform-wide idempotency lands formally in `sdk-client-15.md`, this story must already be shaped so it can adopt that contract cleanly.

### 9.1 Required client behavior

The registration request should carry:

- `X-Request-Id`
- `X-Idempotency-Key` (when implemented / enabled)

### 9.2 Design expectation

Registration must be treated as:

```text
same repo + same payload + same attempt
→ same registration outcome
```

The client must not shape repo registration as a blind write with no replay semantics.

### 9.3 Current compatibility note

If the server-side idempotency posture is not yet fully sealed on the registration route, the client story must still:

- preserve the right transport structure,
- persist request identity locally,
- and emit proof so the registration attempt can be understood and replayed safely later.

---

## 10. UX Contract

### 10.1 Success output

On success, the client must display:

- repo name
- registration state
- bound identity context (at least the fields returned by the server)
- whether the result was fresh or replayed
- proof bundle location

Example:

```text
✔ Repository registered
  repo: workorder-platform
  tenant: tenant-123
  org: org-456
  cohort: builder-default
  worker: worker-abc
  repo_id: repo-789
  proof: ./proof_bundle/repo_register/...
```

### 10.2 Replayed / already-registered semantics

If the same registration attempt replays safely, the client must treat that as a stable governed outcome, not as a confusing partial failure.

### 10.3 Failure output

On rejection, the client must surface:

- reject reason
- affected artifact
- next-best repair guidance
- local proof location

Example:

```json
{
  "status": "REJECT",
  "reason": "governance_contract invalid",
  "repair": [
    "run keyhole validate",
    "fix missing capability owner field",
    "re-run keyhole repo register"
  ]
}
```

### 10.4 Non-interactive mode

A CI-safe / machine-readable mode must exist.

Example:

```text
keyhole repo register --json
```

---

## 11. Local Proof Contract

Every registration attempt must emit a replayable client-side proof bundle, even if the server rejects the repo.

### 11.1 Minimum proof contents

Suggested local proof bundle structure:

```text
proof_bundle/
  repo_register/
    core.json
    request.json
    response.json
    identity_context.json
    artifacts_snapshot.json
    summary.md
    digest.txt
```

### 11.2 Required semantics

The proof must capture:

- repo path / digest
- registration command invocation
- local artifact digests
- request identity
- server response
- resolved identity binding (if returned)
- whether the registration was accepted, replayed, deferred, or rejected
- repair guidance if applicable

### 11.3 Replayability

The proof core must be sufficient to explain the registration attempt later without re-reading the entire repo.

---

## 12. Local Artifact Snapshot Rules

The client must capture a deterministic snapshot of the artifacts used for registration.

### Required snapshot sources

- `keyhole.yaml`
- `governance_contract.yaml`
- `capability_passport.yaml`
- `dependencies.yaml`
- validation result artifact

This ensures that repo registration proof is tied to the exact declaration set that was presented to the MCP boundary.

---

## 13. Server Zipper Expectations (`sdk-server-07.md`)

This client story assumes the paired server story provides:

- registration endpoint,
- identity binding resolution,
- repo registry presence,
- deterministic acceptance / rejection,
- event emission (`REPO_REGISTERED`),
- replay-safe behavior,
- returned bound fields sufficient for client proof and display.

### Client-side expectation of returned data

At minimum, the server should return:

- registration status
- repo_id
- resolved tenant/org/cohort/worker/workspace binding
- correlation or request reference
- whether the result was created or replayed

The client must preserve all of that in proof and UX.

---

## 14. Event Expectations

The primary authoritative event belongs to the server zipper story:

```text
REPO_REGISTERED
```

The client must still be structured to capture and preserve any event references returned by the server so the builder can correlate:

```text
local proof ↔ registration response ↔ event spine reference
```

---

## 15. Determinism Requirements

The client-side registration flow must be deterministic in all the places it controls.

### 15.1 Deterministic behaviors required

- payload shaping from the same repo state is stable
- artifact snapshot hashing is stable
- local proof bundle layout is stable
- command output modes (`human` vs `json`) are stable
- failure categories and repair formatting are stable

### 15.2 Non-deterministic behavior forbidden

- silently skipping missing artifact fields
- mutating repo declarations during registration without explicit builder action
- producing non-repeatable proof structure for the same outcome

---

## 16. Shadow Mode Considerations

Repo registration may eventually support:

```text
keyhole repo register --shadow
```

For this story, the client must be structured so shadow registration can be added without changing the command model dramatically.

That means separating:

- payload building,
- request sending,
- proof generation,
- output rendering.

Even if full shadow registration is paired later, the current client shape should not block it.

---

## 17. Acceptance Criteria

This story is complete only when all of the following are true:

1. `keyhole repo register` exists and targets the current repo (or explicit `--path`).
2. The client refuses registration if required governed repo artifacts are missing.
3. The client refuses registration if local validation fails.
4. The client can assemble contracts + passport + metadata into a deterministic payload.
5. The client includes request identity metadata for the registration attempt.
6. The client can render accepted, replayed, deferred, and rejected outcomes clearly.
7. The client emits a replayable local proof bundle for every registration attempt.
8. The proof bundle captures the exact artifact snapshot used for registration.
9. The client preserves server-returned identity binding in proof and UX.
10. The client is structurally ready for full idempotent transport semantics.

---

## 18. Proof / Tests

### 18.1 Local deterministic tests

- same repo state → same payload shape
- same repo state → same local artifact snapshot digest
- missing required files → deterministic client-side reject
- failed validation → deterministic client-side block
- successful response → proof bundle emitted with expected fields

### 18.2 Zipper tests (when paired with server)

- repo appears in registry
- identity bound correctly
- registration is idempotent
- event: `REPO_REGISTERED`

### 18.3 Negative tests

- malformed governance contract blocks before network call
- missing passport blocks or triggers deterministic generation before send
- invalid local dependency schema blocks with repair guidance
- rejected registration still emits local proof artifact

---

## 19. Repair Guidance Rules

The client must always offer the next-best repair action.

### Examples

If validation failed:

```text
Run: keyhole validate
Fix the listed contract or dependency errors
Then re-run: keyhole repo register
```

If auth is missing:

```text
Run: keyhole login
Then re-run: keyhole repo register
```

If the passport is missing:

```text
Run: keyhole passport generate
Or re-run registration with auto-generation enabled
```

---

## 20. Non-Goals

This story does **not**:

- define remote capability resolution,
- define governed runtime execution,
- define context lifecycle,
- expose direct canonical mutation,
- rewrite repo artifacts silently,
- replace later idempotency hardening work,
- solve async run tracking.

This story is specifically about:

```text
taking a governed local repo
and binding it lawfully to MCP
```

---

## 21. Relationship to Neighboring Stories

- `sdk-client-02.md` creates the repo shape.
- `sdk-client-03.md` enforces capability namespace correctness.
- `sdk-client-04.md` validates governance/dependency schema.
- `sdk-client-05.md` generates the passport.
- `sdk-client-06.md` validates the local repo.
- `sdk-client-07.md` sends that governed state to MCP and captures the result.
- later stories build on the registered repo for:
  - discovery,
  - runs,
  - context,
  - explainability,
  - proof deepening.

---

## 22. One-Line Summary

`SDK-CLIENT-07` turns a locally valid governed repository into a formally registered MCP participant by sending contracts, passport, and repo metadata through a deterministic, identity-aware, proof-emitting registration flow.
