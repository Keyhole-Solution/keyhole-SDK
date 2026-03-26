# sdk-client-05.md

# SDK-CLIENT-05 — Capability Passport Generation

**Status:** DRAFT — CLIENT STORY  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (implementation + validation), Prod (promotion only)  
**Surface:** Client (CLI / SDK / local repo artifact generation)  
**Zipper Pair:** `sdk-server-05.md`  
**Purpose:** Define the client-side contract for deterministic capability passport generation from a governed repository, producing a transport-safe artifact that can be verified, stored, lineage-linked, and later reused by the MCP boundary.

---

## 1. Goal

Implement deterministic **capability passport generation from repo state**.

The client must be able to inspect a governed repository, resolve the local capability declarations and supporting metadata, and generate a **capability passport** that is:

- deterministic for the same effective repo inputs,
- transport-safe for submission to MCP,
- lineage-ready for server-side verification and linking,
- suitable for proof bundle inclusion,
- stable enough to support downstream dependency resolution and capability reuse.

This story is the first point where a governed repo stops being only a folder with declarations and begins to emit a **portable, attestable capability object**.

---

## 2. Why This Story Exists

The scaffold, namespace, and contract work from earlier stories create the ingredients of governed participation, but they do not yet produce the artifact that downstream repos and the MCP boundary need in order to reason about a repo’s declared capabilities.

Without this story:

- capabilities remain trapped inside local YAML files,
- there is no deterministic transport object for server verification,
- lineage between repo, capability, and proof is not formalized,
- downstream dependency resolution remains weaker and more ad hoc,
- builder repos cannot safely export reusable governed capability identity.

This story exists to define the **portable governance artifact** that turns local declarations into server-verifiable, lineage-linkable capability truth.

---

## 3. Scope

### In Scope

Client-side implementation of:

- repository inspection for passport inputs,
- deterministic passport generation,
- canonical transport-safe passport shape,
- stable digest / fingerprint generation for the passport payload,
- lineage-ready metadata fields,
- local validation before submission,
- inclusion of the generated passport in local proof outputs.

### Out of Scope

This story does **not** include:

- server verification logic,
- server storage logic,
- registry publication,
- dependency resolution,
- promotion or canonical minting,
- server-side signature authority,
- full marketplace visibility behavior.

Those belong to the zipper partner `sdk-server-05.md` or later stories.

---

## 4. Strategic Role

This story sits after:

- **SDK-CLIENT-02** — repo scaffold,
- **SDK-CLIENT-03** — capability namespace enforcement,
- **SDK-CLIENT-04** — governance contract + dependency schema validation.

It prepares for:

- registration with MCP,
- capability verification and storage,
- lineage binding,
- dependency resolution,
- downstream capability reuse.

In practical terms:

```text
repo scaffold
  → validated declarations
  → capability passport generation
  → passport verification + storage
  → lineage linking
  → governed reuse
```

---

## 5. Core Principle

A capability passport is a **portable governance artifact**, not a secret, not a token, and not a human-authored freeform document.

It must be:

- generated from repo truth,
- deterministic,
- explicit in scope,
- minimally sufficient for safe transport,
- suitable for server-side re-verification.

The client must not allow “casual” passport generation that depends on hidden local state, machine-specific randomness, or unstable ordering.

---

## 6. Functional Requirements

### 6.1 Command Surface

The client must expose capability passport generation through a deterministic command/API surface.

Recommended CLI shape:

```text
keyhole passport generate
```

Optional extensions:

```text
keyhole passport generate --output capability_passport.generated.yaml
keyhole passport show
keyhole passport validate
```

The story does not require final CLI naming lock, but generation must be explicit and inspectable.

### 6.2 Source Inputs

Passport generation must read from governed repo artifacts, including at minimum:

- `keyhole.yaml`
- `governance_contract.yaml`
- declared capabilities in canonical repo files
- dependency declarations where needed for lineage context
- local proof-ready metadata already present in scaffolded repo structure

### 6.3 Capability Discovery Rules

The client must determine which capabilities belong in the passport from repo declarations, not from fuzzy inference.

Rules:

- declared capabilities are authoritative,
- invalid capability names are rejected before passport generation,
- undeclared inferred capabilities are not silently inserted into the passport,
- ordering must be deterministic.

### 6.4 Passport Output Shape

The generated artifact must follow the canonical transport-safe shape defined by the epic.

Minimum fields expected in the generated passport:

```yaml
schema_version: v1
artifact_kind: capability_passport
repo:
  repo_name: <name>
  repo_id: <id-or-null>
  owner: <owner>
identity:
  tenant_id: <optional-local-known>
  org_id: <optional-local-known>
capabilities:
  - name: payment.stripe.integration.v1
    visibility: private
    status: declared
lineage:
  parent_repo: <optional>
  parent_passport_digest: <optional>
proof:
  local_proof_ref: <optional>
transport:
  generated_at: <timestamp>
  digest: sha256:...
```

The exact final schema can tighten during zipper closure, but the client must emit a stable transport-safe object with these conceptual sections.

### 6.5 Deterministic Serialization

The client must serialize passport output deterministically.

Requirements:

- stable field ordering,
- stable ordering of capabilities,
- stable digest generation,
- no nondeterministic timestamps included in the digest basis unless intentionally excluded,
- no machine-specific absolute paths in the digest basis.

### 6.6 Transport Safety

The passport must be safe to transmit to MCP without carrying secrets or local environmental leakage.

Forbidden content:

- access tokens,
- raw API keys,
- private local filesystem paths when not explicitly allowed,
- hostnames / usernames unrelated to governance identity,
- ephemeral machine-specific debugging data.

### 6.7 Local Persistence

The client must write the generated passport into the governed repo in a predictable location.

Recommended default:

```text
capability_passport.yaml
```

or tool-generated equivalent.

The client must also support writing the artifact into a proof bundle or export path when requested.

---

## 7. Lineage Requirements

The client side does not perform final lineage linking, but it **must emit enough lineage material** for the server to do so.

At minimum, the passport must carry or support:

- repo identity,
- declared capability names,
- parent repo reference if declared,
- parent capability or upstream lineage hints if declared,
- local proof references where available,
- deterministic passport digest.

The client must not pretend lineage is final at this stage. It must prepare the artifact so the server can verify and link lineage later.

---

## 8. Determinism Contract

The most important property of this story is determinism.

### 8.1 Same input, same passport

For the same effective repo state, the generated passport must be byte-stable or semantically stable such that the same digest is produced.

### 8.2 Allowed changes that must change the passport

The passport must change when:

- capability declarations change,
- repo identity metadata changes,
- lineage hints change,
- proof reference inputs included in digest basis change,
- schema version changes.

### 8.3 Allowed changes that must not break determinism

The passport must remain stable across:

- reruns on the same repo,
- different machines with the same repo content,
- local timestamp variation if timestamps are excluded from digest basis,
- repeated generation after `keyhole validate` with no declared changes.

---

## 9. Client UX Requirements

### 9.1 Success UX

On success, the client must tell the user:

- passport was generated,
- file path written,
- digest produced,
- number of capabilities included,
- whether the artifact is ready for server verification.

Example:

```text
Capability passport generated.
Path: capability_passport.yaml
Capabilities: 3
Digest: sha256:...
Next step: keyhole register repo
```

### 9.2 Failure UX

When generation fails, the client must provide deterministic repair guidance.

Example failure classes:

- invalid capability name,
- missing repo identity metadata,
- malformed governance contract,
- unsupported schema version,
- duplicate capability declaration,
- non-transport-safe field contamination.

Each failure must include:

- reason,
- affected file/field when possible,
- next-best repair action.

### 9.3 No silent mutation

The client may update or generate the passport artifact, but it must not silently rewrite unrelated governance files as a side effect.

---

## 10. File and Artifact Expectations

### 10.1 Generated Repo Artifact

The client must generate:

```text
capability_passport.yaml
```

or canonical equivalent.

### 10.2 Optional Proof Inclusion

The client should include the passport in the local proof-ready structure, for example:

```text
proof_bundle/
  passport.json
  summary.md
  digest.txt
```

### 10.3 Suggested Proof Metadata

Include at minimum:

- passport digest,
- source files used,
- capability count,
- generation command,
- generation result.

---

## 11. Validation Requirements

Before writing the passport, the client must validate:

- repo is scaffolded or recognized as governed,
- required schema files exist,
- capability names are valid,
- duplicates are rejected,
- transport-safe shape is satisfied,
- required fields are present.

The client may reuse `keyhole validate` internals from SDK-CLIENT-04 rather than duplicating logic.

---

## 12. Relationship to Server Zipper Story

The client story ends at **deterministic generation of a transport-safe passport artifact**.

The server zipper partner `sdk-server-05.md` is responsible for:

- passport verification,
- persistence,
- lineage linking,
- acceptance or rejection,
- event emission (`PASSPORT_ACCEPTED` or equivalent failure path).

The client story must therefore guarantee that the server receives an artifact that is:

- predictable,
- verifiable,
- complete enough for lineage linking,
- free of local contamination.

---

## 13. Proof / Tests

### 13.1 Required Proof Outcomes

The following must be provable:

- passport deterministic for same input,
- transport-safe shape enforced,
- invalid repo state rejected before generation,
- generated artifact includes expected capabilities,
- artifact ready for server verification.

### 13.2 Client Test Matrix

#### Test A — Happy path scaffolded repo

- start from valid governed scaffold
- declare one or more valid capabilities
- generate passport
- assert file created
- assert digest created
- assert stable shape

#### Test B — Determinism on repeated runs

- generate passport twice from identical repo state
- assert identical digest
- assert stable serialized content

#### Test C — Capability ordering stability

- reorder declarations in source files where order should not matter
- assert passport output ordering remains canonical

#### Test D — Invalid capability name rejected

- declare malformed capability name
- run generation
- assert deterministic failure
- assert repair guidance returned

#### Test E — Missing required repo metadata rejected

- remove required repo identity field
- assert generation fails with clear error

#### Test F — Duplicate capability declaration rejected

- declare same capability twice
- assert deterministic failure

#### Test G — Transport safety enforcement

- inject forbidden secret-like field or illegal leakage into source metadata
- assert generation rejects or strips according to contract
- assert final passport does not contain unsafe data

#### Test H — Proof artifact generation

- generate passport with proof output enabled
- assert proof references include digest and source summary

### 13.3 Zipper Proof Expectations

When paired with `sdk-server-05.md`, the zipper must prove:

- client-generated passport accepted by server,
- server verifies deterministically,
- lineage linked correctly,
- event `PASSPORT_ACCEPTED` emitted,
- same input → same acceptance semantics.

---

## 14. Acceptance Criteria

This story is complete only when all of the following are true:

1. The client can generate a capability passport from a governed repo.
2. The generated passport is deterministic for the same effective input.
3. The passport has a transport-safe shape.
4. Invalid capability declarations are rejected before passport generation.
5. Missing required repo/governance metadata is rejected deterministically.
6. Duplicate capability declarations are rejected.
7. The passport artifact is written to a predictable local path.
8. The passport includes sufficient identity and lineage-ready metadata for server verification.
9. The client emits clear repair guidance on failure.
10. Local proof artifacts can include the generated passport and digest.

---

## 15. Non-Goals

This story does not:

- publish capabilities into a shared registry,
- decide final visibility policy beyond local declaration fields,
- verify signatures server-side,
- grant trust or authority by generation alone,
- allow manual freeform passport authoring as a first-class path,
- replace local validation from SDK-CLIENT-04.

---

## 16. Closure Standard

SDK-CLIENT-05 is closed when the client can take a valid governed repo and deterministically emit a **portable capability passport** that the server can later verify, store, and lineage-link without ambiguity.

This story is not about making the repo merely “describe itself.”
It is about making the repo emit a **governed reusable capability artifact**.

