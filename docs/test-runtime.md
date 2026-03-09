# Keyhole Test Runtime

The **Keyhole Test Runtime** is the first public runtime container in the Keyhole developer ecosystem.

It provides a real, HTTP-addressable, health-checkable, deterministic runtime target that external builders can run locally or deploy remotely to validate SDK behavior, bridge integrations, and replay-safe realization flows without requiring access to a private Keyhole deployment.

---

## Purpose

The test runtime exists to give builders a **real public execution target**.

It is designed to let external developers:

- verify runtime liveness,
- inspect runtime identity,
- observe runtime-local state,
- submit bounded realization requests,
- validate deterministic replay behavior.

This runtime is intentionally narrow in scope and public-facing by design.

---

## What It Is

- A small FastAPI application packaged in a public container image
- The public Runtime Bridge entry point into Keyhole governance
- A stable runtime target for SDK and CLI examples
- A surface for governance-gated, idempotent realization testing
- A Traefik-compatible service deployable on third-party infrastructure
- A public validation target for builder integrations

When `KEYHOLE_MCP_URL` and `KEYHOLE_MCP_TOKEN` are configured, every `POST /realize`
is evaluated against the Keyhole MCP governance controller before any local mutation
is applied. The runtime returns the governance verdict (`ACCEPT`, `REJECT`) alongside
the realization receipt so callers know whether a real governance decision was made.

## What It Is Not

- Not the Keyhole MCP server (it calls the MCP server; it does not replace it)
- Not a production-grade persistence layer
- Not a private control-plane surface
- Not a canonical system of record

---

## Public Runtime Surface

The runtime exposes four public endpoints:

- `GET /healthz`
- `GET /identity`
- `GET /state`
- `POST /realize`

These endpoints define the current public runtime contract for the test runtime.

---

## Endpoints

### `GET /healthz`

Returns runtime health status.

#### Request

```http
GET /healthz
Response
{
  "status": "ok"
}

This endpoint confirms the runtime is alive and reachable.

GET /identity

Returns runtime identity and declared capabilities.

Request
GET /identity
Response
{
  "runtime_id": "keyhole-test-runtime",
  "runtime_name": "Keyhole Test Runtime",
  "runtime_version": "0.1.0",
  "environment": "production",
  "capabilities": ["realize", "state", "health"]
}

Use this endpoint to verify:

which runtime you are talking to,

which version it reports,

which public capabilities it declares.

Clients should not assume capabilities that are not explicitly declared.

GET /state

Returns the current runtime-local state view.

Request
GET /state
Response (initial)
{
  "current_digest": null,
  "realized_digests": [],
  "updated_at": "2026-03-06T12:00:00+00:00"
}

This endpoint is intended for:

integration testing,

replay validation,

runtime inspection,

smoke tests.

It should be treated as a runtime-local state representation, not as a platform ledger or private governance record.

POST /realize

Accepts a bounded realization request and mutates local state if the digest has not been realized before.

Request
POST /realize
Content-Type: application/json
Request body
{
  "candidate_digest": "sha256:abc123",
  "payload": {}
}
Required field

candidate_digest

A stable digest identifying the candidate being realized. This field is the basis for replay detection and idempotent behavior.

Optional field

payload

An optional JSON object containing bounded input associated with the realization request.

Response (first application)
{
  "digest": "sha256:abc123",
  "status": "ACCEPT",
  "message": "Digest realized successfully.",
  "realized_at": "2026-03-06T12:01:00+00:00"
}
Response (replay — same digest posted again)
{
  "digest": "sha256:abc123",
  "status": "ALREADY_REALIZED",
  "message": "Digest has already been realized. No state mutation performed.",
  "realized_at": "2026-03-06T12:02:00+00:00"
}
Replay Behavior

The runtime enforces strict idempotent replay discipline:

The first POST /realize with a given candidate_digest mutates state and returns ACCEPT.

Any subsequent POST /realize with the same digest returns ALREADY_REALIZED without mutating state.

GET /state after a replay attempt reflects only the original mutation.

This makes the runtime safe for retries, repeated local testing, CI reruns, and bridge smoke tests.

Error Expectations

The public runtime contract should remain simple and explicit.

Invalid request body

Malformed JSON or missing required fields should return a client error such as:

400 Bad Request

or

422 Unprocessable Entity
Unknown route

Unsupported routes should return:

404 Not Found
Internal runtime failure

Unexpected server-side failures should return:

500 Internal Server Error

Clients should only treat a realization as successful when the runtime returns a successful response.

Container Image
ghcr.io/keyhole-solution/keyhole-test-runtime:latest
Intended Use Cases

External builders deploying a real runtime target

SDK and CLI integration testing

Bridge smoke tests against a live runtime

Idempotent realization validation

Traefik-compatible deployment examples

Local and remote contract verification

Quick Start (Local)

Run the published container image:

docker run --rm -p 8080:8080 ghcr.io/keyhole-solution/keyhole-test-runtime:latest

Verify the runtime:

curl http://localhost:8080/healthz
curl http://localhost:8080/identity
curl http://localhost:8080/state

Submit a realization request:

curl -X POST http://localhost:8080/realize \
  -H "Content-Type: application/json" \
  -d '{"candidate_digest":"sha256:abc123","payload":{}}'

Replay the same digest safely:

curl -X POST http://localhost:8080/realize \
  -H "Content-Type: application/json" \
  -d '{"candidate_digest":"sha256:abc123","payload":{}}'
Boundary Reminder

The Keyhole Test Runtime is part of the public builder-facing surface of the Keyhole ecosystem.

It exists to expose:

a stable runtime contract,

deterministic runtime behavior,

replay-safe testing semantics,

a deployable validation target.

It does not expose private governance internals, private policy machinery, or protected control-plane logic.

That boundary is intentional and load-bearing.

Summary

The Keyhole Test Runtime is a small, deterministic public runtime target.

It gives external builders a clean way to:

validate liveness,

inspect identity and capabilities,

observe runtime-local state,

test replay-safe realization behavior,

build against a stable public HTTP surface.

It serves as the executable integration target for the Keyhole Developer Kit while keeping private governance internals outside the public repository.