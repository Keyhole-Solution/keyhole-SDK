# sdk-client-15.md

# SDK-CLIENT-15 — Idempotent Transport, Retry, and Request Identity (Client)

**Story ID:** SDK-CLIENT-15 / sdk-client-15  
**Epic:** SDK-CLIENT — Governed Developer SDK, Onboarding, Repository Ingestion, and Scale-Safe Runtime UX  
**Status:** READY FOR IMPLEMENTATION  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (implementation + validation), Prod (governed usage only)  
**System:** Keyhole CLI / SDK / Builder Transport Layer  
**Story Type:** Client-side zipper story  
**Paired Server Story:** `sdk-server-15.md`  
**Precedes:** `sdk-client-16.md`  
**Applies To:** Python SDK, CLI commands, onboarding flows, auth bootstrap, governed run dispatch, repo registration and ingestion flows, proof bundle builders, support / inspection tooling  
**Depends On:** `sdk-client-00.md`, `sdk-client-01.md`, `sdk-server-15.md`, SDK-CLIENT master guidance, official ingress contract, Event Spine truth model  
**Last Updated:** 2026-03-26

---

## 1. Purpose

This document defines the canonical **client-side idempotency contract** for Keyhole’s external SDK era.

Its purpose is to ensure that SDK and CLI behavior remains lawful, deterministic, supportable, and pleasant when builders encounter:

- network flakes,
- retries,
- duplicate sends,
- CLI re-runs,
- agent loops,
- process restarts,
- rate limits,
- deferred execution,
- partial success followed by lost client visibility.

Keyhole is transitioning from internal system-building to external platform use at scale. In that phase, the SDK must not behave like a thin convenience wrapper that forwards requests blindly and leaves retry safety to luck.

The client must instead:

- generate stable operation-attempt identity for write-bearing requests,
- preserve that identity across retries of the same attempt,
- distinguish safe replay from intentionally new action,
- carry request identity for support and proof continuity,
- surface replay, defer, and conflict outcomes clearly,
- avoid accidental duplicate mutation pressure on the server,
- make the safe path the default path for users and agents.

This story turns idempotency from a server-only safety mechanism into a **full zipper discipline** across the SDK and CLI.

---

## 2. Why This Story Exists

SDK-CLIENT-00 and SDK-CLIENT-01 proved the first public builder flows are real:

- registration works,
- verification works,
- auth bootstrap works,
- `whoami` works,
- production Event Spine evidence is already emitted,
- proof bundles already exist,
- the CLI is no longer hypothetical.

That success changes the failure mode.

The question is no longer:

> can the client reach the boundary?

The question is now:

> can the client behave correctly when the world is imperfect?

Without this contract, the SDK is exposed to common external-platform failure classes:

- a successful registration that looks failed to the user because the response was lost,
- a write-bearing run retried with a new identity and unintentionally dispatched twice,
- a rate-limited or deferred response retried too aggressively,
- a second attempt accidentally treated as a replay because the client used payload hashing as operation identity,
- proof bundles that cannot explain whether a request executed, replayed, conflicted, or never left the client,
- route-by-route drift where new client commands forget safe retry behavior.

This story exists to prevent those classes of failure **before** SDK-CLIENT expands into repo registration, governed execution, ingestion, capability registration, and broader vertical scale.

---

## 3. Story Role

This story sits between the already-built client surfaces and the upcoming write-bearing expansion.

### Layering

```text
sdk-client-00 / sdk-client-01
  → register, verify, login, whoami, credential persistence
SDK-CLIENT-15
  → operation-attempt identity, retry discipline, replay handling, proof continuity
SDK-CLIENT-16+
  → context lifecycle, async run tracking, memory boundary, budget visibility, explainability
```

The role of this story is not to move duplicate protection into the client.

The server remains authoritative.

The role of this story is to ensure the client:

- always speaks the duplicate-protection protocol correctly,
- does not sabotage server guarantees through careless retries,
- makes replay-safe behavior automatic for builders,
- emits enough metadata to support proof and diagnosis,
- becomes safer as more write-capable flows are added.

This story therefore elevates idempotency from a **server subsystem the client happens to benefit from** into a **client discipline the platform can rely on**.

---

## 4. Core Thesis

Keyhole client surfaces must treat **retry as normal**, **request identity as first-class**, and **blind duplication as forbidden**.

For any write-capable operation:

- one operation attempt must have one operation idempotency identity,
- retries of that same attempt must reuse that same identity,
- distinct user actions must mint distinct identities even if their payloads are identical,
- proof bundles must preserve the distinction between:
  - executed,
  - replayed,
  - deferred,
  - conflicted,
  - not-sent / transport-failed.

The client is responsible for preserving the operation-attempt boundary.

The server is responsible for deciding whether that attempt replays, conflicts, or executes.

---

## 5. What This Story Is

This story implements:

- a **client-side retry discipline**,
- a **wire protocol contract** for `X-Request-Id` and `X-Idempotency-Key`,
- a **safe default policy** for write-bearing SDK/CLI operations,
- a **proof and support continuity contract** for replay-aware client artifacts,
- a **builder UX contract** that makes retries safe without exposing unnecessary complexity,
- a **migration path** from naturally-safe early flows to full write-bearing SDK behavior.

## What This Story Is Not

This story is **not**:

- a replacement for server-side duplicate protection,
- permission for the client to decide replay outcomes on its own,
- a claim that every command requires an idempotency key,
- a universal retry policy for every HTTP status,
- a substitute for domain-level natural keys,
- a memory contract,
- a promise that transport failures always imply no server-side execution,
- a mechanism for collapsing intentionally repeated user actions across long horizons.

---

## 6. Constitutional Anchors

This contract must preserve the following Keyhole truths:

- **The MCP boundary is the only approved public participation surface.** Idempotency discipline must be expressed through the governed boundary, not around it.
- **Event Spine is canonical truth.** The client must never infer duplicate safety from local assumptions; it must consume server truth.
- **Builders declare; the platform decides.** The client carries operation identity, but the server decides replay vs conflict vs execution.
- **No floating execution.** Every write-bearing attempt must remain attributable through tenant, org, user, cohort, workspace, origin, purpose, request id, and operation id.
- **A zipper is not closed until it emits replayable proof.** Client proof bundles must record replay-relevant metadata.
- **Progressive disclosure is mandatory.** Builders should benefit from duplicate protection without needing to understand the full protocol initially.
- **Failure must produce repair guidance.** Replay, conflict, missing-key, transport-failure, rate-limit, and deferred states must all guide the user safely.
- **The SDK is not the control plane.** The client may automate, but it must not silently mint independent outcome truth.

---

## 7. Story Context

### 7.1 What Already Exists and Is Strong

Several current client surfaces are already low-risk or naturally safe:

- **Read-only operations are naturally idempotent**
  - `GET /auth/registration-status`
  - `GET /mcp/v1/whoami`
  - `GET /mcp/v1/capabilities`
- **Device flow polling is protocol-safe**
  - repeated token-poll attempts are expected and lawful under OAuth device flow.
- **Login avoids duplicate work in the common case**
  - `force=False` avoids unnecessary re-auth when a valid local session already exists.
- **Registration is protected by server-side natural-key checks**
  - duplicate username/email does not mint duplicate identities.
- **`/realize` uses digest-based duplicate protection**
  - repeated realization requests for the same digest already converge safely.

### 7.2 What Is Not Yet Strong Enough

The current client still has important gaps:

#### Medium

- **`POST /mcp/v1/runs/start` does not yet automatically send idempotency identity**
  - duplicate sends can waste resources today,
  - and will become dangerous when write-bearing run types are added.

- **HTTP retry settings exist but are not wired**
  - network failure currently returns raw or lightly wrapped transport errors rather than safe replay-oriented behavior.

#### Low / Medium

- **Onboarding lacks replay-aware client semantics**
  - the server blocks duplicate identities,
  - but same-attempt retry does not yet replay prior success cleanly from the client’s perspective.

- **Verification does not yet carry operation-attempt identity**
  - naturally convergent today,
  - but not yet normalized under one client duplicate-protection model.

#### Future Risk

- **Upcoming write-bearing routes will inherit whatever client pattern exists at launch**
  - if the safe pattern is absent now, future stories will copy unsafe defaults.

---

## 8. Design Principles

### 8.1 Operation Attempt Identity Is Unique Per Attempt

The client must generate a unique idempotency key for a **single logical operation attempt**.

Examples:

- one `keyhole register` submit attempt,
- one `keyhole run` submit attempt,
- one repo registration attempt,
- one capability submission attempt.

The same key must be reused only when retrying **that same attempt**.

### 8.2 Payload Equality Does Not Define Attempt Identity

The client must **not** use `sha256(run_type + sorted(params))` or equivalent payload hashing as the idempotency key itself.

Why:

- a builder may intentionally perform the same action again later,
- two legitimate operations can have identical payloads,
- payload-equality collapse would silently destroy intended repeated action.

Payload hashing may still exist for local convenience or proof artifacts, but it must not replace a unique operation-attempt identifier.

### 8.3 Server Fingerprint Is Authoritative

The client may compute convenience digests, but the server’s canonical fingerprinting and duplicate resolution remain authoritative.

The client must never assume:

- “identical payload means replay,”
- “transport failure means nothing happened,”
- “409 means the write did not succeed.”

### 8.4 Request Identity and Operation Identity Are Distinct

The client must distinguish:

- **`X-Request-Id`** — one HTTP request / support / trace identity
- **`X-Idempotency-Key`** — one logical write attempt across one or more retries

One operation attempt may involve multiple transport-level requests.

### 8.5 Read Safety and Write Safety Differ

- `GET`, `HEAD`, and other naturally idempotent reads do not require an idempotency key.
- Write-capable operations must default to carrying one.
- Naturally convergent write exemptions must still be explicit and documented.

### 8.6 Safe Behavior Must Be Automatic

Builders should not need to:

- manually generate UUIDs,
- remember to reuse keys on retry,
- distinguish every retry-safe status code by hand.

The CLI and SDK should do that work.

### 8.7 Proof Continuity Matters

The client must record enough local metadata to explain:

- what operation was attempted,
- which request IDs were used,
- which idempotency key governed the attempt,
- whether the server executed or replayed,
- whether retries occurred,
- whether a final outcome remained unknown.

---

## 9. Client Roles and Responsibilities

The client is responsible for:

1. generating `X-Request-Id` for every request,
2. generating `X-Idempotency-Key` for every write-capable operation attempt,
3. reusing the same idempotency key for retries of the same attempt,
4. generating a new idempotency key for intentionally new attempts,
5. preserving keys across retry loops within the same client process,
6. optionally persisting attempt state long enough to support support/proof continuity where appropriate,
7. surfacing replay/conflict/defer semantics clearly,
8. never mutating local state as if success occurred before server truth confirms it.

The client is **not** responsible for:

- deciding replay outcomes,
- storing canonical duplicate-protection truth,
- trusting local natural-key collisions as equivalent to replay,
- inventing idempotency exemptions,
- emitting authoritative event truth.

---

## 10. Operation Classes

All SDK/CLI operations must belong to one of the following classes.

### 10.1 READ_ONLY

Examples:

- `whoami`
- `capabilities`
- `registration_status`
- `health`
- future query/list/search surfaces

Behavior:

- `X-Request-Id` required
- `X-Idempotency-Key` omitted or ignored
- retry allowed according to ordinary safe-read policy

### 10.2 WRITE_IDEMPOTENT_REQUIRED

Examples:

- `register`
- `run.start` for write-bearing run types
- future repo registration
- future contract submission
- future capability registration
- future ingestion submission
- future runtime execution submission

Behavior:

- `X-Request-Id` required
- `X-Idempotency-Key` required
- retry allowed only with same idempotency key

### 10.3 NATURALLY_CONVERGENT_EXEMPT

Examples:

- specific one-way verification transitions where the server guarantees convergence and duplicate safety by domain logic

Behavior:

- `X-Request-Id` required
- `X-Idempotency-Key` recommended where feasible
- if omitted, the route must be explicitly declared exempt in the server contract
- client must not assume all POST routes qualify

### 10.4 INTERNAL_ONLY_NOT_EXPOSED

Not for public SDK use.

The client must not expose operations that rely on hidden duplicate-protection assumptions.

---

## 11. Required Headers

### 11.1 `X-Request-Id`

Every SDK request must carry a request identifier.

Purpose:

- supportability,
- tracing,
- log correlation,
- proof continuity,
- post-failure inspection.

Properties:

- unique per HTTP request,
- opaque to the server other than correlation,
- generated client-side by default.

### 11.2 `X-Idempotency-Key`

Every write-capable public SDK operation must carry an operation-attempt idempotency identity unless explicitly exempt.

Purpose:

- safe retry,
- duplicate protection,
- same-attempt replay.

Properties:

- unique per logical operation attempt,
- stable across retries of that attempt,
- not reused for intentionally distinct operations,
- not derived solely from payload hashing.

### 11.3 Optional Supporting Headers

Where useful and safe, the client may also emit:

- `X-Keyhole-Command` — originating CLI/SDK command name
- `X-Keyhole-Attempt` — retry attempt counter for local diagnostics
- `X-Keyhole-SDK-Version` — client version
- `X-Keyhole-Repo-Id` — when the repo is already known / registered
- `X-Keyhole-Shadow-Mode` — when the operation is explicitly shadow / non-production

These do not replace the required headers.

---

## 12. Key Generation Rules

### 12.1 Request ID Generation

The client must generate a fresh request ID for every transport request.

Recommended shape:

- UUIDv4 or equivalent collision-resistant opaque identifier.

### 12.2 Idempotency Key Generation

The client must generate a fresh idempotency key at the **start of a write-capable logical operation attempt**.

Recommended shape:

- UUIDv4 or equivalent collision-resistant opaque identifier.

### 12.3 Scope

The client must scope operation keys so that they represent **one attempt**, not a user, not a session, and not a route forever.

### 12.4 Reuse Rule

The client may reuse an idempotency key **only** when:

- retrying the same logical operation attempt,
- resending after an unknown outcome,
- following redirect/retry/backoff logic for the same attempt,
- recovering from a transport failure where execution status is uncertain.

### 12.5 New-Key Rule

The client must mint a new key when:

- the user intentionally initiates a distinct operation,
- the builder changes intent after a conflict or validation correction,
- a previous attempt is known to be completed and a second real action is desired,
- a support workflow intentionally instructs a fresh attempt.

---

## 13. Retry Rules

### 13.1 Retry Is Not Blind Resend

The client must distinguish between:

- safe automatic retry,
- user-confirmed retry,
- unsafe retry requiring human review.

### 13.2 Safe Automatic Retry Conditions

Automatic retry may occur for the same operation attempt when:

- connection failed before response,
- TLS/session failure occurred mid-flight,
- gateway timeout or transient upstream failure occurred,
- server explicitly returned retryable / deferred semantics,
- rate limit response includes `Retry-After`.

Automatic retry must preserve the same idempotency key.

### 13.3 Unsafe Automatic Retry Conditions

Automatic retry should not blindly occur when:

- a deterministic validation failure occurred,
- the server returned an idempotency conflict,
- the user changed parameters,
- authorization failure requires user action,
- the operation is known to have failed permanently.

### 13.4 Retry Budget

The client must implement bounded retry behavior.

No unbounded retry loops.
No silent infinite agent churn.

### 13.5 Backoff

Retry behavior must use exponential backoff with jitter or equivalent anti-thundering-herd behavior.

### 13.6 Respect `Retry-After`

When the server supplies `Retry-After`, the client must respect it or surface it clearly.

---

## 14. Unknown-Outcome Handling

One of the most important client responsibilities is handling the state:

> “I do not know whether the server executed this.”

Examples:

- network connection drops after request send,
- CLI process is interrupted after transmit,
- timeout occurs before response body arrives.

In this state, the client must:

1. preserve the idempotency key,
2. preserve request metadata in proof / logs where feasible,
3. retry with the same idempotency key if safe,
4. never silently mint a new key for the same unknown operation,
5. surface the ambiguity honestly if the final state remains unknown.

This is where idempotency is most valuable.

---

## 15. Command-Level Requirements

### 15.1 `keyhole register`

Must behave as a write-bearing idempotent operation.

Requirements:

- mint operation id at submit start,
- reuse the same key if a retry occurs,
- surface replayed success as success,
- if the server returns prior success metadata, preserve it in proof.

### 15.2 `keyhole verify`

May initially operate as naturally convergent if the server contract declares it so, but the client should still be structured so explicit idempotency can be added without redesign.

### 15.3 `keyhole login`

The login/bootstrap path must preserve request identity and, where session creation is write-bearing, support operation-attempt duplicate safety without collapsing intentionally distinct sessions.

### 15.4 `keyhole run`

All future write-bearing run dispatch must be treated as `WRITE_IDEMPOTENT_REQUIRED`.

Read-only run types may remain safe without a key only if the route contract says so, but the client should be ready to supply one once run dispatch becomes mutation-capable.

### 15.5 `keyhole ingest`

Submission-style ingestion starts must be treated as write-bearing attempts even if downstream processing is async.

### 15.6 `keyhole register-repo`, `keyhole submit-contract`, `keyhole publish-capability`

These future commands must inherit the same discipline by default.

---

## 16. Client API Surface Requirements

### 16.1 SDK Base Client

The base HTTP client layer must own:

- request-id injection,
- idempotency-key injection for declared operation classes,
- retry behavior,
- replay/defer/conflict error normalization,
- support metadata capture.

### 16.2 Command-Specific Clients

Higher-level clients such as onboarding, auth, context, and future repo/contract clients must declare the operation class of each method instead of hand-rolling idempotency logic.

### 16.3 Central Registry of Operation Classes

The SDK should maintain one internal registry mapping client methods / routes to:

- operation class,
- idempotency requirement,
- retry policy,
- proof requirements.

This avoids route-by-route drift.

---

## 17. Proof Bundle Requirements

Client-side proof artifacts for write-bearing operations must include idempotency metadata.

### 17.1 Minimum Fields

- `request_id`
- `idempotency_key` when applicable
- `operation_class`
- `command_name`
- `attempt_count`
- `final_client_observation`
  - `executed`
  - `replayed`
  - `deferred`
  - `conflict`
  - `transport_unknown`
- `server_request_id` if returned
- `original_request_id` if replay metadata returns one
- timestamps for each attempt
- retry reason(s)

### 17.2 Proof Continuity

If the server returns replay metadata, the client proof bundle must not present the replay as a fresh mutation.

### 17.3 Hot vs Extended Evidence

Replay-critical metadata belongs in the proof hot core.
Verbose per-attempt logs may live in extended evidence.

---

## 18. Error and Outcome Handling

### 18.1 Missing Idempotency Key

If a write-capable route requires `X-Idempotency-Key` and the client did not send one, that is a client bug or noncompliant call path.

The SDK must raise a typed error and not hide it.

### 18.2 Idempotency Conflict

If the server returns conflict because the same idempotency key was used with materially different semantics, the client must:

- stop automatic retry,
- surface deterministic repair guidance,
- instruct the caller to mint a new operation attempt if the action is intentionally new.

### 18.3 Replay-In-Progress / Retry Later

If the server indicates the operation is still processing, the client must:

- preserve the same key,
- retry later with same key,
- surface defer semantics clearly if interactive.

### 18.4 Rate Limit / Overload

If the server returns rate-limit or overload semantics, the client must:

- avoid minting a new key,
- respect backoff / retry-after,
- avoid churn storms.

### 18.5 Transport Failure

Transport failure after send is not proof of non-execution.

The SDK must say so explicitly.

---

## 19. CLI UX Principles

The SDK should make duplicate protection feel **magical by default**, not burdensome.

Builders should almost never see raw idempotency protocol details unless something went wrong.

### 19.1 Default UX

The CLI should simply:

- retry safely when appropriate,
- preserve operation identity automatically,
- tell the builder what happened.

### 19.2 Honest UX

When the client does not know whether the server executed, it must say so honestly and safely.

### 19.3 Repair-Oriented UX

Failure messages should include:

- reject class,
- reason,
- whether retrying the same operation is safe,
- whether a new attempt is required,
- request and proof references where useful.

### 19.4 Inspection UX

Future support commands should make idempotency behavior inspectable.

Examples:

```text
keyhole inspect <request-id>
keyhole proof <operation-id>
keyhole doctor
```

---

## 20. Local State and Persistence

### 20.1 Minimum Persistence Requirement

The client must preserve operation-attempt identity at least for the lifetime of the active retry flow.

### 20.2 Optional Extended Persistence

For selected commands, especially interactive CLI commands, the client may persist pending operation metadata long enough to support:

- crash recovery,
- support inspection,
- user-friendly replay continuation.

### 20.3 What Must Not Happen

The client must not silently persist and reuse old idempotency keys across unrelated future user actions.

Persistence must preserve attempt continuity, not create hidden cross-run coupling.

---

## 21. Config Surface

The SDK config surface should explicitly support safe duplicate-protection behavior.

Recommended fields:

```yaml
request_id_enabled: true
idempotency_enabled: true
retry_enabled: true
max_retries: 3
retry_backoff_base_ms: 250
retry_backoff_max_ms: 5000
respect_retry_after: true
persist_pending_operations: false
```

### 21.1 Defaults

Defaults must favor safety for public SDK use.

### 21.2 User Overrides

Advanced users may tune retry behavior, but should not be able to accidentally disable essential duplicate protection on official write paths without explicit opt-out and warnings.

---

## 22. Interaction With Server Contract

The client must align with the server contract, not invent a parallel one.

### 22.1 Same Public Protocol

The client must speak the same headers and semantics described by `sdk-server-15.md`.

### 22.2 Server Is Final Authority

The client must treat server replay/conflict/defer results as authoritative.

### 22.3 REST / JSON-RPC Parity

Where equivalent public transports exist, the client should preserve duplicate-protection semantics consistently.

If the server has not yet reached parity, the client must document any gap rather than hiding it.

---

## 23. Implementation Scope

### P0 — Required for Story Closure

#### 23.1 Base-client request identity

Inject `X-Request-Id` on every request by default.

#### 23.2 Base-client idempotency identity

Inject `X-Idempotency-Key` on all `WRITE_IDEMPOTENT_REQUIRED` operations by default.

#### 23.3 Onboarding replay-safe wiring

Make `register` replay-friendly at the client layer so same-attempt retries preserve operation identity.

#### 23.4 Public protocol publication

Document for builders and future SDK contributors:

- when keys are sent,
- when they are reused,
- when a new attempt is required,
- how replay/conflict/defer are surfaced.

### P1 — Retry and Error Normalization

#### 23.5 Retry-with-backoff implementation

Wire actual retry logic into `_post()` / `_invoke()` style base methods.

#### 23.6 `Retry-After` support

Respect server-provided retry timing when present.

#### 23.7 Typed error normalization

Map problem-detail / server duplicate-protection failures into deterministic SDK errors.

### P2 — Proof and Support Hardening

#### 23.8 Replay metadata in proof bundles

Proof cores must include idempotency metadata for write-bearing operations.

#### 23.9 Inspection tooling

Add local and server-linked inspection commands / helpers.

#### 23.10 Crash-recovery continuity where justified

Optionally preserve pending operation metadata for selected commands.

### P3 — Ecosystem Discipline

#### 23.11 Operation-class registry enforcement

New write-bearing client methods must declare operation class or fail lint/test checks.

#### 23.12 Documentation and examples

Publish examples showing safe retry behavior for SDK users and agents.

---

## 24. Testing Requirements

### 24.1 Unit Tests

Must cover:

- request-id generation,
- idempotency-key generation,
- retry reuses same key,
- fresh user action gets new key,
- missing-key bugs are caught on required routes,
- conflict handling,
- defer handling,
- transport-unknown handling.

### 24.2 Integration / Smoke Tests

Must prove against live or governed test surfaces:

- same-attempt registration retry replays safely,
- repeated run-start retry reuses key,
- server conflict is surfaced correctly,
- retry-after is obeyed,
- proof bundle captures replay metadata.

### 24.3 Negative Tests

Must cover:

- client accidentally minting new key on retry,
- client accidentally reusing key across distinct operations,
- retry storm prevention,
- malformed server replay/conflict responses.

---

## 25. Metrics and Observability

The client layer should make the following measurable where feasible:

### 25.1 Retry Count by Command

How often are builders encountering transport or retry-worthy failure?

### 25.2 Replay Success Rate

How often do same-attempt retries resolve cleanly through replay?

### 25.3 Conflict Rate

How often is the same key being reused incorrectly?

### 25.4 Unknown Outcome Incidence

How often do clients end in `transport_unknown` state?

### 25.5 Route Coverage Drift

Are any write-bearing commands shipping without declared operation class / idempotency policy?

---

## 26. Invariants

### INV-SDK-CLIENT-REQUEST-ID-ALWAYS

Every SDK request must carry a request identifier.

### INV-SDK-CLIENT-WRITE-KEY-REQUIRED

Every public write-bearing operation classified as `WRITE_IDEMPOTENT_REQUIRED` must carry an idempotency key.

### INV-SDK-CLIENT-SAME-ATTEMPT-SAME-KEY

Retries of the same logical write attempt must reuse the same idempotency key.

### INV-SDK-CLIENT-DIFFERENT-ATTEMPT-DIFFERENT-KEY

Intentionally distinct write attempts must use distinct idempotency keys even when payloads are identical.

### INV-SDK-CLIENT-PAYLOAD-HASH-NOT-KEY

Payload hashing may not be used as the sole idempotency-key generation rule.

### INV-SDK-CLIENT-PROOF-CAPTURES-REPLAY

Replay-relevant metadata must be captured in proof cores for write-bearing operations.

### INV-SDK-CLIENT-NO-BLIND-RETRY-WRITES

Write retries must not occur without stable operation identity.

### INV-SDK-CLIENT-ERRORS-REPAIRABLE

Duplicate-protection failures must produce deterministic repair guidance.

---

## 27. Non-Goals

This contract does not attempt to:

- replace server duplicate protection,
- define every future command in full,
- guarantee exactly-once transport delivery,
- make reads carry unnecessary idempotency protocol,
- solve memory-view recomputation behavior,
- define full agent orchestration semantics,
- expose server fingerprint/HMAC secrets,
- collapse domain-level duplicate concepts into one client rule.

---

## 28. Story Closure Criteria

This story is closed only when:

1. every write-bearing public client command has declared operation class,
2. required write-bearing commands automatically send `X-Idempotency-Key`,
3. every request automatically sends `X-Request-Id`,
4. retry logic preserves operation-attempt identity,
5. proof bundles include replay metadata for write-bearing commands,
6. conflict/defer/missing-key states are normalized into typed SDK errors,
7. new client stories inherit duplicate protection by default.

---

## 29. Strategic Statement

SDK-CLIENT-00 and SDK-CLIENT-01 proved builders can reach Keyhole.

SDK-CLIENT-15 proves builders can interact with Keyhole safely when the network lies, retries happen, and the platform begins to scale.

It closes the gap between:

- “the client can call the platform”

and

- “the client can call the platform repeatedly, imperfectly, and still behave lawfully.”

That is the minimum client duplicate-protection posture required before Keyhole expands into repo registration, governed execution, ingestion, and broader external scale.

---

## 30. One-Line Summary

Turn Keyhole idempotency from a server strength the client happens to benefit from into a client-side discipline where every write attempt carries stable operation identity, retries are safe by default, proof remains replay-aware, and builders never have to guess whether “retry” will duplicate reality.
