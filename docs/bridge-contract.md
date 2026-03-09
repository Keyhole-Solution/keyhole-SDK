# Bridge Contract

## Purpose

The **Bridge Contract** defines the public interaction model between external builder systems and a **Keyhole-compatible runtime surface**.

It exists to make integrations predictable.

A bridge is any external system, adapter, script, SDK client, CI job, or service that sends requests to a Keyhole runtime and interprets the results. This document defines the minimum stable contract those bridges should rely on.

This contract is intentionally **public, narrow, and runtime-focused**. It does not expose private governance internals, promotion kernel behavior, or protected control-plane logic.

---

## Scope

This contract applies to public runtime interactions in this repository, especially the **Keyhole Test Runtime**.

It covers:

- health checks,
- runtime identity discovery,
- runtime state inspection,
- bounded realization submission,
- replay and idempotency expectations,
- bridge-side responsibilities.

It does **not** cover:

- private Keyhole governance orchestration,
- internal promotion workflows,
- protected policy evaluation logic,
- private audit backplanes,
- hidden control-plane state mutation.

---

## Core Model

A bridge interacts with a runtime over HTTP.

The runtime exposes a small set of endpoints that allow a bridge to:

1. verify the runtime is alive,
2. verify which runtime it is talking to,
3. inspect current local runtime state,
4. submit a bounded realization request,
5. safely replay the same request without causing duplicate mutation.

This makes the public runtime contract deterministic, testable, and safe for integration development.

---

## Contract Principles

### 1. Explicit over implicit

The runtime must expose clear, documented request and response shapes.

### 2. Bounded mutation

The bridge may request realization, but only through the declared public endpoint and request format.

### 3. Deterministic replay

Submitting the same realization digest multiple times must not create repeated mutation.

### 4. Public/runtime boundary only

Bridges interact with the public runtime surface, not with private governance internals.

### 5. Compatibility-first evolution

The public contract should evolve carefully and remain stable for builder integrations.

---

## Transport

### Protocol

The bridge contract uses:

- HTTP/1.1 or HTTP/2
- JSON request and response bodies where applicable

### Content type

For request bodies, bridges should send:

```http
Content-Type: application/json
Base URL

A bridge targets a runtime base URL such as:

http://localhost:8080

or a deployed public address such as:

https://runtime.example.yourdomain.com
Endpoint Contract
GET /healthz
Purpose

Checks whether the runtime is alive and reachable.

Request
GET /healthz
Success response
{
  "status": "ok"
}
Bridge expectations

A bridge should treat a successful 200 OK response with "status": "ok" as proof that the runtime is reachable.

This endpoint is for liveness, not identity or realization readiness beyond the declared public surface.

GET /identity
Purpose

Returns runtime identity and declared capabilities.

Request
GET /identity
Success response
{
  "runtime_id": "keyhole-test-runtime",
  "runtime_name": "Keyhole Test Runtime",
  "runtime_version": "0.1.0",
  "environment": "production",
  "capabilities": ["realize", "state", "health"]
}
Bridge expectations

A bridge should use this endpoint to:

confirm it is talking to the intended runtime,

verify runtime version,

inspect declared capabilities before sending higher-order requests.

A bridge should not assume capabilities that are not explicitly declared.

GET /state
Purpose

Returns the runtime’s current local state representation.

Request
GET /state
Example response
{
  "current_digest": null,
  "realized_digests": [],
  "updated_at": "2026-03-06T12:00:00+00:00"
}
Bridge expectations

A bridge may use this endpoint to:

inspect whether a digest has already been realized,

confirm replay behavior,

validate local runtime mutation during integration tests.

A bridge should treat this as a runtime-local state view, not as a full platform or governance ledger.

POST /realize
Purpose

Submits a bounded realization request to the runtime.

Request
POST /realize
Content-Type: application/json
Request body
{
  "candidate_digest": "sha256:abc123",
  "payload": {}
}
Required fields
candidate_digest

A stable digest string that identifies the candidate being realized.

This field is the foundation for replay detection and idempotent behavior.

Optional fields
payload

An optional JSON object carrying bounded runtime input associated with the realization request.

The runtime may accept and process this as implementation-specific request data.

First successful response
{
  "digest": "sha256:abc123",
  "status": "ACCEPT",
  "message": "Digest realized successfully.",
  "realized_at": "2026-03-06T12:01:00+00:00"
}
Replay response for the same digest
{
  "digest": "sha256:abc123",
  "status": "ALREADY_REALIZED",
  "message": "Digest has already been realized. No state mutation performed.",
  "realized_at": "2026-03-06T12:02:00+00:00"
}
Idempotency and Replay Rules

Replay discipline is a core part of this contract.

Rule 1 — first submission mutates

The first valid submission of a new candidate_digest may mutate runtime state.

Rule 2 — repeated submission does not mutate again

If the same candidate_digest is submitted again, the runtime must not perform a second mutation for that digest.

Rule 3 — replay must be explicit in the response

The runtime should communicate replay clearly through a response such as:

{
  "status": "ALREADY_REALIZED"
}
Rule 4 — state must remain stable under replay

A replayed request must not create duplicate realization records or unexpected state drift.

This makes the contract safe for:

retries,

CI reruns,

bridge smoke tests,

network-failure recovery,

repeated local development calls.

Error Expectations

The public bridge contract should keep error behavior simple and explicit.

Invalid request body

If the request body is malformed or missing required fields, the runtime should return a client error such as:

400 Bad Request

or

422 Unprocessable Entity

with a JSON error body.

Unsupported route

Unknown routes should return:

404 Not Found
Internal error

Unexpected server-side failures should return:

500 Internal Server Error

with a JSON error response where possible.

Bridge behavior on errors

Bridges should:

treat 4xx errors as request or contract issues,

treat 5xx errors as runtime-side failures,

avoid assuming mutation succeeded unless the runtime returns a successful response.

Bridge Responsibilities

A compliant bridge should:

1. Verify liveness before higher-order operations

Call /healthz when appropriate before assuming the runtime is available.

2. Verify identity when runtime targeting matters

Call /identity to ensure the correct runtime is being addressed.

3. Use stable digests for realization

A bridge should send a deterministic candidate_digest whenever replay-safe behavior is desired.

4. Handle replay correctly

A bridge must treat ALREADY_REALIZED as a successful replay-safe outcome, not as a hard failure.

5. Avoid hidden assumptions

A bridge should only rely on fields and behaviors documented in the public contract.

6. Preserve public/private boundary discipline

A bridge must not assume access to hidden Keyhole control-plane surfaces.

Runtime Responsibilities

A runtime implementing this contract should:

1. Expose the declared endpoints

The public runtime surface must include the documented endpoints if it claims compatibility with this contract.

2. Return JSON responses consistently

Runtime responses should be machine-readable and stable.

3. Enforce replay discipline

Duplicate realization requests for the same digest must not cause duplicate mutation.

4. Keep public behavior explicit

The runtime should communicate status clearly and avoid hidden side effects.

5. Preserve contract stability

Changes to public request or response shape should be deliberate and version-aware.

Compatibility Guidance

This public bridge contract should be treated as a compatibility surface.

Non-breaking changes

These are usually safe:

adding new response fields,

adding new optional request fields,

adding new capabilities to /identity,

adding new documentation and examples.

Breaking changes

These should be avoided without a versioning strategy:

renaming required fields,

removing existing fields,

changing the meaning of status values,

changing replay semantics,

removing existing endpoints.

If the contract evolves materially, versioning should be introduced explicitly.

Security Boundary

This bridge contract is intentionally public.

That means:

it is safe to document publicly,

it is intended for builder consumption,

it must not include secrets,

it must not imply access to private governance machinery.

A bridge integrates with the public runtime surface only.

Any private orchestration, promotion, policy, or governance logic remains outside this contract.

Minimal Bridge Example
Health check
curl http://localhost:8080/healthz
Identity check
curl http://localhost:8080/identity
State check
curl http://localhost:8080/state
Realization request
curl -X POST http://localhost:8080/realize \
  -H "Content-Type: application/json" \
  -d '{"candidate_digest":"sha256:abc123","payload":{}}'
Replay of the same request
curl -X POST http://localhost:8080/realize \
  -H "Content-Type: application/json" \
  -d '{"candidate_digest":"sha256:abc123","payload":{}}'

The second call should be replay-safe and should not produce a second mutation.

Conformance Summary

A bridge can be considered aligned with this contract if it:

talks to the runtime over HTTP,

uses the documented endpoints,

sends JSON request bodies where required,

submits deterministic candidate_digest values for realization,

handles replay responses correctly,

does not assume private Keyhole internals.

A runtime can be considered aligned with this contract if it:

exposes the documented public endpoints,

returns stable JSON responses,

enforces digest-based idempotent realization behavior,

preserves the public/private architectural boundary.

Summary

The Bridge Contract exists to make public Keyhole runtime integration safe, simple, and deterministic.

It gives builders a stable public target for:

SDK usage,

bridge implementations,

local integration testing,

remote runtime validation,

replay-safe realization testing.

The contract is deliberately narrow:

public runtime interaction in, deterministic runtime behavior out.