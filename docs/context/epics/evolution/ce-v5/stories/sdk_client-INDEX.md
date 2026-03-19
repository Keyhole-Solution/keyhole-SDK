# dev-sdk-INDEX.md

# DEV-SDK — Governed Developer SDK, Onboarding, and Repository Ingestion

**Status:** MASTER GUIDANCE — FINAL  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (design + validation), Prod (promotion only)  
**Purpose:** Define the canonical SDK, CLI, onboarding flow, declaration artifacts, capability passport model, governance contract model, dependency model, repository ingestion flow, proof bundle contract, event model, trust-readiness model, and zipped server/client story outline for external builders and vertical repos connecting to the Keyhole MCP surface.

---

## 1. Mission

DEV-SDK establishes the **official builder entry point** into the Keyhole ecosystem.

This epic defines how a developer or organization:

1. discovers Keyhole,
2. creates an account,
3. authenticates through the governed boundary,
4. scaffolds a governed repository,
5. declares or infers capabilities and dependencies,
6. validates local contracts,
7. registers with the MCP server,
8. runs governed workflows,
9. emits events into the Event Spine,
10. produces replayable proof bundles,
11. ingests and graphs existing repositories,
12. receives deterministic remediation guidance,
13. gradually aligns legacy systems into Keyhole governance.

The SDK is **not** an alternate control plane.  
It is a **governed bridge** to the MCP spine.

---

## 2. Why This Epic Exists

The SDK is the first public builder surface that translates Keyhole doctrine into usable developer workflow.

It exists to make the following simultaneously true:

- the first builder experience is simple,
- the developer boundary remains governed,
- capabilities become reusable and discoverable,
- existing repositories can be brought under governance gradually,
- all participation remains attributable, replayable, and auditable,
- the platform accumulates capability knowledge and institutional intelligence rather than scattered tooling.

This epic is therefore not merely a packaging effort. It is the formal definition of how external builders enter the Keyhole ecosystem.

---

## 3. Constitutional Anchors

DEV-SDK must preserve the following architectural truths:

- **Event Spine is canonical truth.**
- **Promotion is the sole canonical mutation path.**
- **The MCP boundary is the only approved public participation surface.**
- **Builders declare intent through artifacts; they do not directly mutate the platform.**
- **All governed participation must trace back to tenant, org, user, cohort, worker, repo, workspace, and purpose.**
- **A zipper is not closed until it produces a replayable proof bundle.**
- **Trust metadata must be representable now, even if enforcement is phased.**

---

## 4. Strategic Outcome

When this epic is complete, a builder must be able to do one of two things quickly and safely.

### 4.1 Greenfield path

```text
pip install keyhole-cli
keyhole login
keyhole init vertical
keyhole validate
keyhole register
keyhole run
```

### 4.2 Existing repo path

```text
pip install keyhole-cli
keyhole login
keyhole ingest .
```

In both paths, the builder must receive immediate value and produce attributable, replayable, governed outcomes.

---

## 5. Final Epic Success Criteria

DEV-SDK is complete only when all of the following are true:

- a new developer can authenticate without manual `.env` creation,
- the CLI owns credential bootstrap and the SDK consumes local credentials rather than demanding preconfiguration,
- a governed repository scaffold is generated automatically,
- declaration artifacts are standardized and tool-managed,
- capability naming, versioning, and dependency declaration rules are enforced,
- dependency resolution is deterministic and explainable,
- registration with MCP is deterministic, attributable, and auditable,
- a governed run can execute end-to-end,
- every zipper emits a replayable proof bundle,
- repository ingestion can graph a repo and produce confidence-scored governance gap suggestions,
- identity context is present across registration, run, event, and proof flows,
- emitted events are classified and routed with retention hints,
- proof bundles are split into hot replay core and cold extended evidence,
- trust metadata hooks exist in passports and proof bundles,
- the first useful output appears within the first 10 minutes for a new builder,
- the platform remains adoption-friendly through progressive disclosure rather than exposing all governance complexity up front.

---

## 6. Non-Goals

DEV-SDK does **not**:

- expose cluster credentials,
- embed promotion kernel logic,
- allow direct canonical mutation,
- bypass the MCP boundary,
- silently rewrite builder repositories,
- auto-promote capabilities into canon,
- replace the governance kernel,
- implement final marketplace economics or royalty settlement in this epic,
- require every builder workflow to hard-gate on full SBOM / attestation / transparency verification on day one.

---

## 7. Design Principles

### 7.1 SDK is not the control plane

The SDK is a governed client. The MCP server remains the sole public control boundary.

### 7.2 Authentication belongs to the CLI layer

The SDK must not require a pre-existing `.env` for first connection. Authentication is handled by the CLI through approved auth flows.

### 7.3 Declarative participation only

Builders participate by editing or generating declaration artifacts, not by imperative platform mutation.

### 7.4 Repo shape is a governance primitive

Every governed repo must share a predictable file structure.

### 7.5 Capability naming and versioning must be globally legible

Capabilities must follow hierarchical namespace rules and explicit major-version semantics.

### 7.6 Capability proofs are portable

Descendants inherit upstream governance requirements, but proof satisfaction may be delegated via capability passports.

### 7.7 Existing repos must enter gradually

The system must support governance alignment by ingestion, graphing, and remediation guidance, not only greenfield scaffolds.

### 7.8 No floating execution

Every command, run, event, registration, and proof bundle must include deterministic identity context.

### 7.9 Version labels are insufficient by themselves

Capability safety requires version + provider + digest + compatibility semantics + deterministic resolution.

### 7.10 Not all evidence deserves equal weight

Replay-critical truth belongs on the hot path. Large auxiliary evidence belongs in referenced extended storage.

### 7.11 Progressive disclosure is mandatory

The SDK must feel easy first and reveal governance depth gradually. Builders should see value before complexity.

### 7.12 Failure must produce repair guidance

Every rejection path should surface deterministic reasons and next-best actions rather than dead ends.

---

## 8. Adoption-First Builder Experience

The architecture is strong enough to become adoption-hostile if exposed too bluntly. Therefore the SDK must be designed around progressive disclosure.

### 8.1 The first 10-minute rule

A new builder must be able to go from zero to first useful output in under 10 minutes.

### 8.2 The first wow moment

At least one of the following must appear quickly:

- a valid governed run result,
- an architecture graph of the current repository,
- confidence-scored inferred capabilities,
- deterministic remediation suggestions,
- a visible proof bundle summary.

### 8.3 Progressive disclosure levels

```text
Level 0: install + login + run or ingest
Level 1: see generated artifacts and summaries
Level 2: validate and register explicitly
Level 3: edit contracts and capability declarations
Level 4: advanced dependency, trust, and governance tuning
```

### 8.4 Shadow mode

The SDK must support shadow participation for low-risk onboarding.

Examples:

```text
keyhole run --shadow
keyhole ingest --shadow
```

Shadow mode may:

- simulate MCP participation,
- generate proof bundles,
- validate local behavior,
- avoid irreversible registration or production-side effect.

This allows builders to experience the platform before committing real state.

---

## 9. Identity, Binding, and Visibility

The identity model is only useful if builders can see it and the system can prove it.

### 9.1 Required identity context

Every registration, run, event, and proof bundle must carry:

```json
{
  "tenant_id": "...",
  "org_id": "...",
  "user_id": "...",
  "cohort_id": "...",
  "worker_id": "...",
  "repo_id": "...",
  "workspace_id": "...",
  "origin": "...",
  "purpose": "..."
}
```

### 9.2 Identity UX

The SDK must expose a clear identity inspection surface.

Example:

```text
keyhole whoami
```

This must return enough information for a builder to understand:

- who they are acting as,
- what tenant/org they are in,
- what cohort/worker is active,
- what workspace they are using,
- whether they are in shadow, dev, or real governed mode.

### 9.3 Principle

No floating execution. Ever.

---

## 10. Standard Repo Shape

Every governed repo created by the SDK must include a predictable structure.

```text
repo/
 ├── keyhole.yaml
 ├── governance_contract.yaml
 ├── capability_passport.yaml
 ├── dependencies.yaml
 ├── capabilities/
 ├── src/
 ├── tests/
 └── docs/
```

### 10.1 Required files

- `keyhole.yaml` — repo-level Keyhole identity and metadata
- `governance_contract.yaml` — local governance requirements and gates
- `capability_passport.yaml` — current declared/proven capability surface
- `dependencies.yaml` — consumed capabilities and versions/providers

### 10.2 Rule

These files are canonical and tool-managed where possible. Builders may inspect and edit them, but the CLI is responsible for generating and validating them.

---

## 11. Capability Naming, Versioning, and Compatibility

### 11.1 Canonical capability shape

```text
<domain>.<category>.<capability>.v<major>
```

### 11.2 Examples

- `payment.stripe.integration.v1`
- `crm.salesforce.sync.v1`
- `robotics.lidar.calibration.v2`
- `workorder.assignment.engine.v1`

### 11.3 Enforcement

The CLI must reject invalid names during creation and validation.

### 11.4 Versioning rule

- breaking changes require a new major version,
- a published major line must not silently change declared behavior,
- compatibility and deprecation semantics must be explicit,
- builder-facing tools must make upgrade boundaries obvious.

### 11.5 Compatibility contract requirement

Each capability line must support compatibility metadata sufficient to explain:

- what stays stable,
- what changed,
- what is deprecated,
- what upgrade path exists.

### 11.6 Capabilities are APIs

Treat capabilities the way serious platforms treat API surfaces: stability must be explicit, upgrade behavior must be intentional, and breaking changes must be named rather than hidden.

---

## 12. Dependency Declaration and Deterministic Resolution

Version labels alone are not enough.

### 12.1 Dependency declaration shape

```yaml
dependencies:
  - capability: payment.stripe.integration.v1
    provider: workorder-platform
    digest: sha256:...
  - capability: crm.salesforce.sync.v2
    provider: crm-platform
```

### 12.2 Deterministic resolution requirements

Each dependency must be resolvable by:

- capability name,
- major version,
- provider,
- immutable digest where pinned,
- compatibility/deprecation contract.

### 12.3 Resolver behavior

Production-safe resolution must be deterministic and fail-closed.

Priority order:

1. explicitly pinned provider + version,
2. tenant policy override,
3. org policy override,
4. platform default provider,
5. otherwise fail.

### 12.4 Resolution proof

Every resolution decision must be materializable and explainable.

Example resolution record:

```json
{
  "requested": "payment.stripe.integration.v1",
  "resolved_to": "repo://workorder-platform@sha256:abc...",
  "reason": "pinned provider + version"
}
```

### 12.5 Rule

No implicit capability dependency should be trusted for governed reuse unless it is declared or inferred and then explicitly accepted.

---

## 13. Capability Passport Model

Capability passports are the portable proof objects that let downstream repos inherit proven behavior without re-running every ancestor gate.

### 13.1 Passport responsibilities

A capability passport must declare:

- capability name,
- version,
- owner repo,
- visibility,
- proof references,
- delegated capabilities,
- parent lineage,
- signature / digest anchor,
- optional trust metadata references.

### 13.2 Draft shape

```yaml
capability: payment.stripe.integration.v1
owner_repo: workorder-platform
visibility: public
proofs:
  - event_ref: evt_12345
delegated_capabilities:
  - identity.auth.v1
parent_repo: keyhole-platform
signature: sha256:...
trust:
  sbom_digest: null
  attestation_digest: null
  rekor_entry_uuid: null
```

### 13.3 Design constraint

A passport is **not** a secret-bearing token. It is a transport-safe governance object.

---

## 14. Governance Contract Model

Governance contracts express what the repo promises locally beyond inherited platform invariants.

### 14.1 Governance contract responsibilities

A governance contract must declare:

- repo identity,
- parent repo / lineage,
- local capabilities produced,
- required tests,
- integration contracts,
- local invariants,
- deprecation or compatibility rules where applicable.

### 14.2 Draft shape

```yaml
repo: workorder-platform
parent_repo: keyhole-platform
produces:
  - payment.stripe.integration.v1
  - workorder.assignment.engine.v1
required_tests:
  - stripe_webhook_validation
  - apex_schema_consistency
local_invariants:
  - no_unversioned_dependencies
compatibility_contracts:
  - payment.stripe.integration.contract.v1
```

---

## 15. Repository Ingestion and Governance Alignment

The platform must meet builders where they already are.

### 15.1 Command

```text
keyhole ingest <path-or-url>
```

### 15.2 Responsibilities

The ingestion flow must:

1. scan repo structure,
2. inspect dependency manifests,
3. infer capabilities,
4. build an architecture/capability graph,
5. identify governance gaps,
6. write graph artifacts to the platform,
7. return suggested remediation/alignment actions.

### 15.3 Important constraints

The SDK must **not silently mutate the repo** during ingestion.

It may generate artifacts and suggestions, but builder-visible adoption of changes must remain explicit.

Inference must carry confidence and must not auto-register new capabilities without builder approval.

### 15.4 Example outputs

- inferred capabilities,
- inference confidence,
- architecture graph,
- missing tests,
- candidate governance contract,
- suggested capability substitutions,
- dependency versioning issues.

### 15.5 Ingestion safety principle

Suggest. Never assume.

---

## 16. Failure and Repair UX

A governed system that only says “no” will fail adoption.

### 16.1 Every reject path must include

- reject class,
- deterministic reason,
- affected artifact or dependency,
- next-best repair suggestions.

### 16.2 Example

```json
{
  "status": "REJECT",
  "reason": "missing dependency provider pin",
  "repair": [
    "pin payment.stripe.integration.v1 provider",
    "run keyhole search stripe"
  ]
}
```

### 16.3 Principle

Failure must produce repair guidance, not a dead end.

---

## 17. Event Classification, Retention, and Enforcement

Event growth must be handled as a design primitive, not a future optimization.

### 17.1 Every emitted event must include

- `event_class`
- `importance`
- `retention_hint`
- `correlation_id`
- identity context

### 17.2 Minimum classes

- `critical` — auth, gates, promotion, security, ACCEPT/REJECT
- `operational` — runs, registration, validation, ingestion summaries
- `noise` — heartbeat, debug, high-frequency progress telemetry

### 17.3 Routing principle

- truth events belong in long-retention governed streams,
- operational events belong in medium-retention streams,
- noise events belong in short-retention / sampled / aggressively expired paths.

### 17.4 Server enforcement requirements

The server must not trust SDK-provided classification blindly.

Required enforcement classes include:

- event class validation,
- event rate limiting,
- event size limits,
- rejection or deterministic defaulting when fields are missing.

### 17.5 Principle

Event classification is declarative at the edge and enforced at the spine.

---

## 18. Proof Bundle Contract

Proof bundles are table stakes for this epic.

### 18.1 Minimum proof bundle shape

```text
proof_bundle/
  ├── core.json
  ├── request.json
  ├── response.json
  ├── event_chain.json
  ├── passport.json
  ├── verification_result.json
  ├── identity_context.json
  ├── correlation.json
  ├── summary.md
  ├── diff.json
  ├── digest.txt
  └── extended/
```

### 18.2 Required semantics

- `core.json` contains replay-critical truth,
- `summary.md` is human-readable proof summary,
- `diff.json` explains what changed vs prior comparable execution when applicable,
- `extended/*` contains non-essential large artifacts.

### 18.3 Replay requirement

A zipper is replayable if the hot proof core contains enough information to reconstruct and verify the execution without requiring large extended artifacts.

### 18.4 Storage principle

- `core.json` → hot, replay-required, queryable
- `extended/*` → referenced, optional, cold-capable evidence

### 18.5 Principle

Not all evidence deserves equal weight.

---

## 19. Trust Readiness (SBOM / Attestation / Transparency)

Trust hardening must be schema-complete now, even if enforcement is phased.

### 19.1 This epic requires

- reserved SBOM fields,
- reserved attestation fields,
- reserved transparency-log / Rekor fields,
- digest-addressable references in passports and proof bundles.

### 19.2 This epic does not yet require

- universal builder-facing hard gates on trust verification,
- full launch-blocking submission workflows for every builder action.

### 19.3 Principle

Trust metadata must be schema-complete in this epic. Trust enforcement can be phased.

---

## 20. MCP Surface Expectations / Dependencies

DEV-SDK assumes the MCP surface supports the minimum necessary builder flow.

### 20.1 Required existing or parallel capabilities

- identity / whoami,
- capability disclosure,
- governed run dispatch,
- memory write/query where used for graph storage,
- event emission/query where used for provenance and analysis.

### 20.2 Strongly recommended parallel or near-term surface additions

- capability registry listing / discovery,
- dependency resolution / capability resolution,
- capability registration endpoint or equivalent governed run type,
- event emit completion if currently incomplete,
- cohort self-introspection if needed for local runtime context.

This epic may depend on one or more adjacent MCP stories if the SDK builder journey cannot be completed without them.

---

## 21. Zippered Delivery Model

This epic is executed as **paired stories** across:

- **Server (Keyhole Platform / MCP boundary)**
- **Client (SDK / CLI / Repo)**

Each story pair must close a functional loop and produce proof artifacts demonstrating:

- end-to-end execution,
- attribution (tenant/org/user/cohort/worker/repo/workspace),
- event emission,
- deterministic behavior,
- replayable proof core,
- failure → repair guidance where applicable.

A story is **not complete** unless both sides pass and emit proof.

---

## 22. Zippered Story Outline

### DEV-SDK-01 — Authentication Bootstrap

**Client (sdk-client-01.md)**

- implement `keyhole login`
- PKCE / device flow support
- secure local credential store
- `keyhole whoami`

**Server (sdk-server-01.md)**

- auth endpoints
- `/whoami` identity surface
- identity context issuance

**Proof / Tests**

- login → token issued
- `whoami` returns correct identity context
- token usable across endpoints
- shadow vs real mode visible
- event: `AUTH_SUCCESS`

---

### DEV-SDK-02 — Governed Repo Scaffold

**Client (sdk-client-02.md)**

- `keyhole init vertical`
- generate canonical repo structure + files

**Server (sdk-server-02.md)**

- publish canonical schema definitions
- optional remote scaffold validation

**Proof / Tests**

- scaffold passes schema validation
- deterministic generation
- trust-ready placeholders included

---

### DEV-SDK-03 — Capability Namespace Enforcement

**Client (sdk-client-03.md)**

- capability creation helper
- namespace validator

**Server (sdk-server-03.md)**

- registration-time namespace validation

**Proof / Tests**

- invalid names rejected client + server
- valid names accepted consistently
- version suffix enforcement works

---

### DEV-SDK-04 — Governance Contract + Dependency Schema

**Client (sdk-client-04.md)**

- local schema validation via `keyhole validate`

**Server (sdk-server-04.md)**

- contract ingestion + validation
- dependency normalization

**Proof / Tests**

- malformed contracts rejected
- valid contracts accepted and stored
- dependency/provider fields normalized
- event: `CONTRACT_REGISTERED`

---

### DEV-SDK-05 — Capability Passport Generation

**Client (sdk-client-05.md)**

- passport generation from repo

**Server (sdk-server-05.md)**

- passport verification + storage
- lineage linking

**Proof / Tests**

- passport deterministic for same input
- lineage correctly linked
- transport-safe shape enforced
- event: `PASSPORT_ACCEPTED`

---

### DEV-SDK-06 — Local Validation Pipeline

**Client (sdk-client-06.md)**

- `keyhole validate`
- schema + dependency + namespace + compatibility checks

**Server (sdk-server-06.md)**

- optional remote validation
- invariant enforcement hooks

**Proof / Tests**

- failing repo blocked
- passing repo emits validation success artifact
- compatibility violations rejected with repair suggestions

---

### DEV-SDK-07 — Registration with MCP

**Client (sdk-client-07.md)**

- `keyhole register`
- send contracts + passport + metadata

**Server (sdk-server-07.md)**

- registration endpoint
- identity binding (tenant/org/cohort/worker/repo/workspace)

**Proof / Tests**

- repo appears in registry
- identity bound correctly
- registration is idempotent
- event: `REPO_REGISTERED`

---

### DEV-SDK-08 — Capability Discovery and Resolution

**Client (sdk-client-08.md)**

- `keyhole search`
- dependency resolution helper

**Server (sdk-server-08.md)**

- capability registry endpoint
- deterministic resolver

**Proof / Tests**

- search returns correct capabilities
- resolution maps to valid providers deterministically
- ambiguous cases fail closed
- resolution record materialized
- event: `CAPABILITY_QUERY`

---

### DEV-SDK-09 — Governed Runtime Execution

**Client (sdk-client-09.md)**

- `keyhole run`
- `keyhole run --shadow`

**Server (sdk-server-09.md)**

- run dispatch
- traceable event emission

**Proof / Tests**

- run executes end-to-end
- correlation_id present across events
- event classification metadata stamped
- event chain verifiable
- failure paths emit repair guidance

---

### DEV-SDK-10 — Repository Ingestion and Graph

**Client (sdk-client-10.md)**

- `keyhole ingest`
- `keyhole ingest --shadow`
- local scan + packaging

**Server (sdk-server-10.md)**

- ingestion endpoint
- graph builder
- capability inference

**Proof / Tests**

- repo graph created
- inferred capabilities stored with confidence scores
- no silent repo mutation
- event: `INGEST_COMPLETE`

---

### DEV-SDK-11 — Alignment Guidance

**Client (sdk-client-11.md)**

- render remediation suggestions and next-best actions

**Server (sdk-server-11.md)**

- gap analysis engine
- suggestion generation

**Proof / Tests**

- gaps identified deterministically
- suggestions reproducible
- inferred vs verified state clearly distinguished
- event: `GAP_ANALYSIS_COMPLETE`

---

### DEV-SDK-12 — Event Classification and Retention Routing

**Client (sdk-client-12.md)**

- emit classification metadata on SDK-originated events

**Server (sdk-server-12.md)**

- route events by class / retention policy
- enforce event envelope requirements

**Proof / Tests**

- events land in correct streams
- missing classification fields rejected or defaulted deterministically
- rate/size validation works

---

### DEV-SDK-13 — Proof Bundle Hot/Cold Split

**Client (sdk-client-13.md)**

- generate `core.json`, `summary.md`, `diff.json`, and `extended/*`

**Server (sdk-server-13.md)**

- store proof core hot
- store extended evidence by reference

**Proof / Tests**

- replay succeeds from core bundle only
- extended artifacts are addressable by digest
- large evidence does not block hot query path

---

### DEV-SDK-14 — Trust-Ready Metadata Hooks

**Client (sdk-client-14.md)**

- generate optional SBOM / attestation / transparency placeholders

**Server (sdk-server-14.md)**

- accept and persist trust metadata references

**Proof / Tests**

- trust-ready fields validate when present
- fields remain optional for first-run success
- digests / references preserved in passports and proof bundles

---

## 23. Epic Closure Criteria

DEV-SDK is CLOSED only when:

- every story pair passes independently,
- every story pair produces verifiable events,
- every story pair produces a replayable proof bundle,
- the full loop works:

```text
login → init → validate → register → run → ingest → analyze
```

- all artifacts are:
  - attributable,
  - replayable,
  - queryable from the Event Spine,
  - identifiable by deterministic digest.

---

## 24. Proof Doctrine for This Epic

Each zipper must emit:

- correlation_id,
- tenant/org/user/cohort/worker/repo/workspace binding,
- ACCEPT/REJECT artifact,
- persisted event chain,
- proof bundle core,
- human-readable proof summary,
- failure repair guidance where relevant.

The epic is not complete without:

- replay validation,
- lineage validation,
- capability reuse validation,
- identity attribution validation,
- event class / retention validation,
- hot/cold proof storage validation,
- shadow-mode validation.

---

## 25. Final Summary

DEV-SDK is the master guidance for the governed builder boundary.

It defines a developer experience that must feel simple while remaining structurally correct.

It exists to ensure that every external builder-facing feature:

- begins at the developer,
- passes through the MCP boundary,
- resolves inside the governed platform,
- emits attributable events,
- produces replayable proof,
- returns deterministic outcomes,
- remains safe to adopt incrementally.

No half-features.  
No one-sided implementations.  
No floating execution.  
No replayless closure.

Only zipper-closed capabilities that preserve identity, proof, governance, and adoption quality at the same time.

