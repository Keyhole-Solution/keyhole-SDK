# sdk-client-03.md

# SDK-CLIENT-03 — Capability Namespace Enforcement

**Status:** DRAFT — FULLY EXPANDED CLIENT STORY  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (implementation + validation), Prod (promotion only)  
**Surface:** Client (CLI + SDK local generation and validation)  
**Epic:** SDK-CLIENT — Governed Developer SDK, Onboarding, Repository Ingestion, and Scale-Safe Runtime UX  
**Paired Server Story:** `sdk-server-03.md`  
**Purpose:** Ensure every capability name created, edited, inferred, or submitted by the client is shaped according to the canonical Keyhole namespace contract before it reaches registration-time validation at the MCP boundary.

---

## 1. Story Goal

Implement a **client-side capability creation helper** and **namespace validator** so builders can only create capability identifiers that conform to the canonical Keyhole naming contract, with deterministic local feedback before server registration.

This story exists to make capability naming:

- predictable,
- portable,
- globally legible,
- validation-friendly,
- version-aware,
- and consistent across greenfield and ingested repositories.

The client must help the builder generate correct names, reject malformed names early, and normalize the most common mistakes before the server ever sees the artifact.

---

## 2. Why This Story Exists

The revised `sdk-client-INDEX` makes capability naming and versioning a first-class governance rule. It explicitly states that capability names must be globally legible, use hierarchical namespace rules, and carry explicit major-version semantics. It also treats repo shape and declaration artifacts as governance primitives rather than casual metadata. fileciteturn0file0

Without this story:

- builders will invent inconsistent names,
- the same capability will appear under multiple spellings,
- version semantics will drift,
- dependency resolution will become noisy and ambiguous,
- ingestion inference will produce low-trust suggestions,
- registration-time server rejection will become a frustrating first-touch builder experience.

This story prevents that by making the correct path the easy path.

---

## 3. Strategic Role

This is one of the earliest local-governance stories in the client roadmap.

It sits directly after scaffold generation because as soon as a repo exists, the builder must be able to create or declare capabilities correctly. It sits before broader validation, passport generation, dependency resolution, and registration because all of those depend on stable naming. The index already frames capability naming, versioning, and compatibility as canonical design principles for the client epic. fileciteturn0file0

### Position in the client flow

```text
login
  ↓
init vertical
  ↓
create capability / validate capability namespace   ← this story
  ↓
validate contracts
  ↓
generate passport
  ↓
register with MCP
```

This is a local-first story. It can be implemented and proven offline because the client owns capability generation UX and first-pass validation, even though the server remains the final boundary authority.

---

## 4. Core Principle

Capability names are not labels.

They are **governed identifiers**.

A capability identifier must be stable enough to support:

- declaration,
- dependency resolution,
- provider pinning,
- compatibility review,
- proof and passport binding,
- ingestion inference,
- registration-time validation,
- and long-term ecosystem reuse.

Therefore the client must never treat capability names as arbitrary strings.

---

## 5. Canonical Naming Contract

The canonical capability name format is:

```text
<domain>.<category>.<capability>.v<major>
```

Examples of valid names include:

- `payment.stripe.integration.v1`
- `crm.salesforce.sync.v1`
- `workorder.assignment.engine.v1`
- `identity.oidc.discovery.v2`

Examples of invalid names include:

- `StripeIntegration`
- `payment/stripe/integration`
- `payment.stripe.integration`
- `payment.stripe.integration.v01`
- `payment..integration.v1`
- `payment.stripe.integration.V1`

The client must treat this format as canonical and non-optional. The index explicitly defines hierarchical namespace rules and major-version semantics as part of the SDK contract. fileciteturn0file0

---

## 6. Client Deliverables

This story delivers two primary client capabilities.

### 6.1 Capability Creation Helper

A CLI and SDK helper that assists the builder in generating a valid capability name from structured input.

Example CLI surface:

```text
keyhole capability create
```

Possible interactive prompts:

- domain
- category
- capability name
- major version

Example non-interactive surface:

```text
keyhole capability create --domain payment --category stripe --name integration --major 1
```

Output behavior:

- validates parts,
- normalizes safe casing,
- assembles canonical name,
- writes or inserts into the correct declaration artifact,
- refuses to create malformed identifiers.

### 6.2 Namespace Validator

A reusable validation module that can be invoked by:

- `keyhole validate`
- scaffold post-generation checks
- capability creation flows
- dependency declaration validation
- ingestion suggestion filtering
- passport generation prechecks

The validator must:

- accept canonical names,
- reject malformed names,
- explain what failed,
- suggest the correct shape when possible,
- enforce major-version suffix semantics.

---

## 7. Command Surfaces

### 7.1 Required CLI surface

At minimum, the client must support one of the following patterns:

```text
keyhole capability create
```

or

```text
keyhole capability add
```

The exact verb can be finalized during implementation, but the behavior must include:

- canonical name generation,
- local validation,
- artifact update,
- diff preview or confirmation,
- deterministic failure when invalid.

### 7.2 SDK surface

At minimum, the SDK should expose helper functions conceptually equivalent to:

```python
create_capability_name(domain: str, category: str, capability: str, major: int) -> str
validate_capability_name(name: str) -> ValidationResult
```

The validator result should be structured enough to support:

- CLI-friendly error messages,
- test assertions,
- future LSP/editor integration,
- remediation suggestions.

---

## 8. Validation Rules

The client validator must enforce the following minimum rules.

### 8.1 Segment count

A capability identifier must contain exactly four segments when split by `.`:

1. domain
2. category
3. capability
4. version segment

### 8.2 Character rules

The first three segments must:

- be lowercase,
- use alphanumeric characters and hyphens only if explicitly allowed by final implementation policy,
- contain no whitespace,
- contain no empty segments.

Default-safe rule:

- lowercase letters `a-z`
- digits `0-9`
- optional internal hyphen `-`

### 8.3 Version segment rules

The last segment must match:

```text
v<major>
```

Where:

- `v` is lowercase,
- `<major>` is a positive integer,
- no leading zero formatting is used unless the value is literally zero and zero is allowed (default recommendation: require `v1+`).

Examples:

- valid: `v1`, `v2`, `v10`
- invalid: `V1`, `1`, `version1`, `v01`

### 8.4 No inferred silent repair on destructive ambiguity

The client may safely normalize:

- trimming leading/trailing whitespace,
- lowering case when builder intent is obvious,
- replacing spaces during guided input before final confirmation.

The client must **not silently rewrite** already-declared malformed names in-place without explicit builder confirmation.

### 8.5 Deterministic reasons for rejection

Every invalid name must produce a deterministic reject reason such as:

- `invalid_segment_count`
- `invalid_version_suffix`
- `uppercase_not_allowed`
- `empty_namespace_segment`
- `illegal_character`

---

## 9. Artifact Integration

The capability creation helper must integrate with the governed repo scaffold and declaration artifacts created by earlier client stories.

Likely insertion points include:

- `capability_passport.yaml`
- `governance_contract.yaml`
- `keyhole.yaml`
- future capability registry or declaration file under `capabilities/`

The client must update artifacts deterministically.

### 9.1 Required behavior

- insert new capability in the correct location,
- preserve stable ordering where the file contract expects it,
- avoid duplicate insertion,
- show the builder what changed,
- fail safely if the target artifact is missing or malformed.

### 9.2 Duplicate local declaration handling

If the capability already exists in the target artifact:

- do not insert a duplicate,
- surface a deterministic local warning or reject outcome,
- allow builder override only if explicit behavior is defined.

---

## 10. UX Requirements

### 10.1 Guided creation must feel easy

The whole point of this story is to make correct names easy and incorrect names hard.

A builder should not need to memorize the full naming grammar on day one.

### 10.2 Validation messages must teach the rule

Bad:

```text
invalid capability
```

Good:

```text
Invalid capability namespace.
Expected: <domain>.<category>.<capability>.v<major>
Example: payment.stripe.integration.v1
```

### 10.3 Repair suggestions must be actionable

If possible, the client should suggest a corrected form:

```text
Did you mean: payment.stripe.integration.v1 ?
```

### 10.4 No governance jargon overload

Early CLI output should explain what happened in simple terms and only expose deeper governance context when needed.

---

## 11. Interaction with Server Story

The client is responsible for:

- capability generation UX,
- local namespace validation,
- artifact updates,
- deterministic local errors,
- preventing obviously malformed capabilities from ever reaching MCP.

The server is responsible for:

- final registration-time namespace validation,
- rejecting malformed or conflicting capability identifiers at the boundary,
- ensuring client and server rules remain aligned.

This zipper must prove:

- invalid names are rejected consistently on both sides,
- valid names are accepted consistently on both sides,
- version suffix rules do not drift between client and server.

---

## 12. Proof / Tests

This story is not complete until it has both deterministic local proof and zipper-aligned server proof.

### 12.1 Required local unit tests

At minimum, test:

- valid canonical names are accepted,
- malformed names are rejected,
- version suffix is required,
- uppercase forms are rejected or normalized only where explicitly allowed,
- duplicate insertion is blocked,
- artifact update is deterministic,
- interactive helper output matches expected normalized form.

### 12.2 Required fixture tests

Use fixture repos to verify:

- scaffolded repos accept valid capability insertion,
- malformed declaration files fail safely,
- validation output remains stable across reruns.

### 12.3 Zipper proof requirements

The paired server/client proof must demonstrate:

- invalid names rejected client + server,
- valid names accepted consistently,
- version suffix enforcement works.

This exact proof contract is already called out in the story index. fileciteturn0file0

---

## 13. Acceptance Criteria

This story is complete only when all of the following are true:

1. The client provides a capability creation helper.
2. The client provides a reusable namespace validator.
3. The canonical namespace format `<domain>.<category>.<capability>.v<major>` is enforced locally.
4. Invalid names are rejected deterministically.
5. Valid names are accepted consistently.
6. Version suffix enforcement works locally.
7. Capability insertion into governed repo artifacts is deterministic.
8. Duplicate local insertion is prevented or surfaced deterministically.
9. Validation messages include clear repair guidance.
10. Client behavior aligns with registration-time server validation semantics.
11. Proof demonstrates invalid names rejected client + server, valid names accepted consistently, and version suffix enforcement works.

---

## 14. Non-Goals

This story does **not**:

- implement full remote capability registry discovery,
- solve dependency resolution,
- decide final provider resolution semantics,
- infer capabilities from arbitrary repo code,
- define long-term compatibility policy in full,
- auto-register capabilities with MCP.

Those concerns belong to later stories.

This story only establishes **correct capability naming and local creation discipline**.

---

## 15. Failure Modes This Story Prevents

Without this story, the platform would drift into:

- multiple spellings for the same capability,
- missing version suffixes,
- broken dependency references,
- low-trust ingestion inference,
- late server-side rejection of obviously malformed declarations,
- hard-to-clean ecosystem naming entropy.

This story prevents that drift before it spreads.

---

## 16. Implementation Notes

### 16.1 Recommended validation implementation

Use one central validator module and reuse it everywhere.

Do **not** duplicate regex fragments across:

- CLI commands,
- validation pipeline,
- scaffold utilities,
- passport generation.

### 16.2 Recommended normalization policy

Safe normalization may happen only before final confirmation and only where builder intent is clear.

The validator should not act like a silent rewrite engine.

### 16.3 Recommended file update behavior

All writes to declaration artifacts should be:

- stable,
- diffable,
- deterministic,
- testable via golden files.

---

## 17. Evidence Requirements

The client story should emit or materialize evidence for:

- namespace validation pass/fail,
- artifact mutation preview or diff,
- created capability identifier,
- duplicate suppression behavior,
- local proof bundle summary for the story test run.

At minimum, the completion evidence should include:

- unit test results,
- fixture test results,
- example accepted names,
- example rejected names,
- zipper proof summary referencing the paired server validation.

---

## 18. Completion Statement

SDK-CLIENT-03 is complete when the builder can create a capability the right way on the first try, the client rejects malformed namespace strings before registration, and the server agrees with the client about what is valid.

This story seals the first real ecosystem naming law for the client boundary.

---

## 19. One-Line Summary

Make capability identifiers deterministic, canonical, and impossible to get casually wrong before they ever reach the MCP boundary.
