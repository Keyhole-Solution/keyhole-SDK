# sdk-client-08.md

# SDK-CLIENT-08 — Capability Discovery and Resolution

**Status:** DRAFT — FULLY EXPANDED CLIENT STORY  
**Owner / Author:** Keyhole Solution Foundation  
**Surface:** Client  
**Applies To:** CLI, SDK resolver layer, local dependency helper UX, proof bundle generation, MCP capability discovery client behavior  
**Last Updated:** 2026-03-26

---

## 1. Purpose

This story defines the client-side behavior for **governed capability discovery and deterministic dependency resolution**.

Its purpose is to let a builder:

- search the Keyhole ecosystem for existing capabilities,
- inspect candidate providers,
- resolve a dependency request into a deterministic provider selection,
- materialize that selection into local repo artifacts and proof,
- fail safely when ambiguity or incompatibility exists,
- avoid ad hoc or hidden dependency selection.

This story is the point where the SDK stops being only a local declaration tool and becomes a **governed reuse tool**.

The client-side responsibility is not to invent resolution truth. The client’s job is to:

- shape discovery and resolution requests correctly,
- present results clearly,
- preserve enough context for deterministic reuse,
- materialize the chosen result into local governed artifacts,
- and fail closed when the boundary cannot produce a lawful answer.

---

## 2. Why This Story Exists

A governed platform is only useful as an ecosystem if builders can find and reuse existing capabilities safely.

Without this story, the builder experience degrades into:

- manual guessing of capability names,
- ad hoc provider selection,
- copy/paste of dependency identifiers,
- local repo drift from platform truth,
- and no portable explanation of why a dependency resolved the way it did.

This story exists to ensure that dependency reuse behaves like a governed capability market rather than a string lookup.

The client must be able to answer questions like:

- “What providers implement `payment.stripe.integration.v1`?”
- “Which one would be selected under current pins and policy?”
- “Why did this provider win?”
- “Why did this fail?”
- “What record should be written into local repo governance files?”

The client must also protect the platform from unsafe assumptions:

- ambiguous matches must not silently succeed,
- invalid or stale local dependency entries must not remain unexplained,
- non-deterministic resolution must not be presented as lawful.

---

## 3. Story Goal

Enable builders to discover capabilities and resolve dependencies through a deterministic, explainable, fail-closed client flow.

The core client responsibilities are:

- provide `keyhole search` for governed capability discovery,
- provide a dependency resolution helper for local workflow and artifact updates,
- materialize resolution records locally,
- expose deterministic reasons for acceptance or rejection,
- align local files with the server’s capability registry and resolver contract.

---

## 4. Strategic Role

SDK-CLIENT-08 sits after:

- repo scaffold exists,
- naming rules exist,
- governance/dependency schema exists,
- capability passports exist,
- local validation exists,
- repo registration exists.

It is the first story where the builder begins interacting with the broader ecosystem as a consumer of platform capabilities instead of only declaring local repo state.

### Layering

```text
sdk-client-02  → repo exists
sdk-client-03  → capability names are lawful
sdk-client-04  → dependency schema exists
sdk-client-05  → passport model exists
sdk-client-06  → local validation exists
sdk-client-07  → repo is registered
sdk-client-08  → repo can discover and resolve ecosystem capabilities
```

---

## 5. Scope

This client story covers:

- the `keyhole search` command,
- SDK helper methods for capability search and selection,
- dependency resolution request shaping,
- deterministic local handling of resolution responses,
- fail-closed ambiguity behavior,
- local materialization of a resolution record,
- proof artifacts for search and resolution actions,
- CLI output and repair guidance.

This story does **not** define:

- the server-side registry implementation,
- the server-side resolver algorithm,
- marketplace ranking or economics,
- automatic code installation or repository mutation beyond declared artifact updates,
- opaque recommendation systems,
- direct memory-backed semantic search outside the governed capability registry surface.

---

## 6. Constitutional Anchors

This story must preserve all of the following truths:

- The SDK is not the control plane.
- The MCP boundary is the sole public authority for capability registry truth.
- Builders declare and consume artifacts; they do not mutate platform truth directly.
- Dependency resolution must be deterministic and explainable.
- Ambiguous cases must fail closed.
- Capability selection must be attributable and replayable.
- No direct canonical memory access may be introduced through discovery UX.
- A zipper is not closed until a proof bundle exists.

---

## 7. Client Responsibilities

The client must do the following:

### 7.1 Search

Provide a builder-friendly search surface:

```text
keyhole search <query>
```

This command must support at minimum:

- exact capability search,
- namespace-prefix search,
- provider-filtered search,
- version-aware query shaping,
- optional local output formatting modes.

### 7.2 Resolution helper

Provide a deterministic resolution helper for local dependency workflows.

This may be exposed as:

- `keyhole resolve <capability>`
- `keyhole dependency resolve <capability>`
- or an SDK method used by higher-level commands.

The helper must:

- accept a capability request,
- gather local repo dependency context,
- send a lawful resolution request to the server,
- render the result clearly,
- optionally materialize the result into repo files.

### 7.3 Fail closed

If multiple valid providers exist and no lawful tie-breaker is available, the client must not silently pick one.

It must return a deterministic failure that includes:

- what was ambiguous,
- what local pin or policy is missing,
- what the user can do next.

### 7.4 Materialize the resolution record

When resolution succeeds, the client must materialize the chosen result into a local, replayable form.

At minimum that means:

- a record in `dependencies.yaml`,
- a resolution record artifact in proof output,
- optional local summary output.

### 7.5 Preserve proof

Both discovery and resolution flows must be proof-producing. Search may be lightweight; resolution must be replayable.

---

## 8. Canonical Commands

### 8.1 Search

```text
keyhole search <query>
```

#### Examples

```text
keyhole search payment.stripe.integration.v1
keyhole search payment.stripe
keyhole search --provider workorder-platform payment.stripe.integration.v1
keyhole search --json payment.stripe.integration.v1
```

### 8.2 Resolve

Preferred canonical form:

```text
keyhole dependency resolve <capability>
```

Acceptable alias if adopted:

```text
keyhole resolve <capability>
```

#### Examples

```text
keyhole dependency resolve payment.stripe.integration.v1
keyhole dependency resolve crm.salesforce.sync.v2 --provider crm-platform
keyhole dependency resolve payment.stripe.integration.v1 --write
```

### 8.3 Optional repo-aware dependency fixup

This story may also allow the client to suggest or perform a controlled dependency pin update when resolution succeeds.

Example:

```text
keyhole dependency resolve payment.stripe.integration.v1 --write
```

If implemented, file mutation must be explicit, reviewable, and deterministic.

---

## 9. Local Inputs

The client may use the following local inputs when shaping a resolution request:

- `keyhole.yaml`
- `dependencies.yaml`
- `governance_contract.yaml`
- `capability_passport.yaml`
- current repo identity
- current builder identity / tenant context from credential store
- optional command flags (`--provider`, `--version`, `--json`, `--write`, etc.)

The client must not invent hidden provider pins or hidden repo policy.

---

## 10. Search UX Requirements

### 10.1 Output shape

For human-readable output, search results should present:

- capability name,
- provider,
- version,
- visibility,
- optional short summary,
- optional trust / proof availability signals,
- whether the result appears already pinned locally.

### 10.2 Empty results

If search returns no results, the client must say so explicitly and suggest likely next actions.

Example:

- check namespace spelling,
- remove excess provider/version filters,
- create a new capability instead,
- inspect local declarations.

### 10.3 Partial/ambiguous results

If search returns multiple close matches, the client may rank or group them for readability, but it must not imply a deterministic resolver choice unless one actually exists.

---

## 11. Resolution UX Requirements

### 11.1 Successful resolution

A successful resolution must show:

- requested capability,
- resolved provider,
- resolved version,
- immutable digest if pinned/returned,
- reason for resolution,
- whether local files were updated.

Example:

```json
{
  "requested": "payment.stripe.integration.v1",
  "resolved_to": {
    "provider": "workorder-platform",
    "capability": "payment.stripe.integration.v1",
    "digest": "sha256:..."
  },
  "reason": "pinned provider + compatible version"
}
```

### 11.2 Ambiguity failure

If ambiguity remains unresolved, the client must fail closed with repair guidance.

Example guidance:

- add `--provider <name>`
- pin provider in `dependencies.yaml`
- update governance policy
- inspect available providers with `keyhole search`

### 11.3 Incompatibility failure

If no provider is compatible, the client must surface:

- requested capability,
- incompatible candidates if safe to show,
- reason code,
- next steps.

---

## 12. Local Artifact Effects

When used in write mode, resolution may update:

### 12.1 `dependencies.yaml`

The dependency entry should include at minimum:

- capability,
- provider,
- optional digest,
- optional resolution metadata.

### 12.2 Proof bundle / resolution record

A resolution artifact must be written into the local proof area, such as:

```text
proof_bundle/
  resolution/
    <timestamp-or-digest>.json
```

The artifact must include:

- requested capability,
- local inputs used,
- resolved result,
- resolution reason,
- write/no-write mode,
- correlation/request identity if available,
- timestamp,
- local repo identity.

### 12.3 No silent mutation

If `--write` is not provided, the client must not silently mutate dependency files.

---

## 13. Transport and Contract Expectations

The client must shape discovery and resolution requests in a way that matches the governed boundary, but must remain robust if the server evolves.

### 13.1 Search contract expectation

The server should provide a capability registry endpoint or equivalent governed search surface.

### 13.2 Resolver contract expectation

The server should provide a deterministic resolver surface and return enough information for the client to materialize the result safely.

### 13.3 Identity context

Requests must carry the active identity context through normal auth/credential behavior.

### 13.4 Future-proofing

The client should preserve room for:

- request identity,
- idempotency identity for write-bearing resolution actions,
- correlation IDs,
- proof references.

---

## 14. Determinism Requirements

This story must preserve the following deterministic properties:

### 14.1 Same query, same result set contract

If the same query is issued against the same registry state and identity/policy context, the client must present the same search result set ordering/shape unless the server contract explicitly says ordering is undefined.

### 14.2 Same request, same resolution contract

If the same dependency resolution request is issued against the same repo state, same registry state, and same policy context, the client must produce the same resolved result or same fail-closed ambiguity outcome.

### 14.3 Materialized record determinism

A resolution record for the same successful result must be structurally equivalent across runs except for approved volatility fields (timestamps, request IDs, etc.).

---

## 15. Failure Model

The client must handle the following failure classes explicitly.

### 15.1 Empty search

No matches.

### 15.2 Ambiguous search / ambiguous resolution

Multiple candidates and no lawful tie-break.

### 15.3 Incompatible provider

Capability exists but candidate providers do not satisfy requested version/provider/compatibility constraints.

### 15.4 Registry unreachable

Server not reachable or contract unavailable.

### 15.5 Invalid local dependency state

The local repo’s dependency declarations are malformed and must be repaired before resolution.

### 15.6 Server reject

The server explicitly rejects the request due to governance or schema constraints.

Each class must produce deterministic repair guidance.

---

## 16. Repair Guidance Requirements

Every client-visible failure must include actionable next steps.

Examples:

- “Pin a provider in `dependencies.yaml`.”
- “Use `keyhole search <capability>` to inspect available providers.”
- “Run `keyhole validate` to fix malformed dependency declarations.”
- “Add a major version suffix, e.g. `.v1`.”
- “Specify `--provider` because multiple lawful providers exist.”

The client must not return opaque errors for routine resolution failure.

---

## 17. Proof / Tests

This story is complete only when the following are proven.

### 17.1 Search returns correct capabilities

- search with an exact capability query returns expected candidates
- namespace-prefix search returns grouped/ordered candidates
- empty search results are handled deterministically

### 17.2 Resolution maps to valid providers deterministically

- same request resolves to the same provider
- provider pinning is honored
- digest pinning is preserved when provided
- result materialization is deterministic

### 17.3 Ambiguous cases fail closed

- no silent winner selection when ambiguity remains
- repair guidance points to lawful next steps

### 17.4 Resolution record materialized

- successful resolution produces a local artifact
- optional file mutation occurs only in explicit write mode
- proof bundle contains replayable resolution context

### 17.5 Event expectation

The zipper expects the server side to emit:

```text
CAPABILITY_QUERY
```

The client side must preserve enough correlation/proof context to support that event lineage once the zipper closes.

---

## 18. Local Test Matrix

### 18.1 Unit tests

- parse and validate search command arguments
- parse and validate resolve command arguments
- verify output formatting for empty / single / multi results
- verify deterministic file update behavior
- verify fail-closed ambiguity handling

### 18.2 Fixture tests

- registry fixture with one candidate
- registry fixture with multiple compatible candidates
- registry fixture with incompatible candidates
- malformed local dependency file fixture

### 18.3 Artifact tests

- resolution artifact written correctly
- no-write mode produces proof artifact without mutating dependency files
- write mode updates dependency file deterministically

### 18.4 Replay tests

- same fixture inputs produce same local resolution record semantics

---

## 19. Proof Bundle Requirements

A replayable proof bundle for resolution should include at minimum:

- command invoked,
- local repo identity,
- input capability request,
- effective local dependency state,
- server response summary,
- final resolution decision,
- write/no-write mode,
- resulting file diff or no-diff statement,
- deterministic summary.

Suggested file layout:

```text
proof_bundle/
  resolution/
    core.json
    summary.md
    response.json
    diff.json
```

---

## 20. Zipper Expectations with sdk-server-08.md

This client story zippers with `sdk-server-08.md`.

### Client responsibility

- shape search and resolution requests correctly,
- fail closed locally when ambiguity remains,
- materialize the result into repo artifacts and proof,
- preserve deterministic local behavior.

### Server responsibility

- expose a capability registry endpoint,
- provide deterministic resolver behavior,
- reject unsafe or ambiguous resolution without hidden heuristics,
- emit attributable query/resolution events.

### Zipper completion condition

This zipper is closed only when:

- search returns correct capabilities end-to-end,
- resolution deterministically maps to valid providers,
- ambiguous cases fail closed,
- resolution record is materialized locally,
- server emits `CAPABILITY_QUERY` with attributable correlation.

---

## 21. Closure Criteria

SDK-CLIENT-08 is closed when all of the following are true:

1. `keyhole search` exists and returns deterministic results under fixture and live-compatible conditions.
2. A dependency resolution helper exists and behaves deterministically.
3. Ambiguous cases fail closed.
4. Successful resolutions can be materialized into local repo artifacts.
5. Resolution proofs are replayable.
6. The client half zippers cleanly with `sdk-server-08.md`.

---

## 22. One-Line Summary

`SDK-CLIENT-08` gives builders a governed way to find reusable capabilities and deterministically resolve dependencies into replayable local artifacts without hidden provider selection or unsafe ambiguity.
