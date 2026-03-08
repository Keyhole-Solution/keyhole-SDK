# Keyhole Test Runtime

The **Keyhole Test Runtime** is the first public runtime container in the Keyhole developer ecosystem. It provides a real, HTTP-addressable, health-checkable, deterministic runtime target that external builders can deploy, test, and verify against.

## What It Is

- A small FastAPI application packaged in a public container image
- A stable deployment target for SDK and CLI examples
- A surface for idempotent realization testing
- A Traefik-compatible service deployable on third-party infrastructure

## What It Is Not

- Not the Keyhole MCP server
- Not the full Keyhole platform
- Not a governance engine
- Not a production-grade persistence layer

---

## Endpoints

### `GET /healthz`

Returns runtime health status.

**Response:**

```json
{
  "status": "ok"
}
```

### `GET /identity`

Returns runtime identity and declared capabilities.

**Response:**

```json
{
  "runtime_id": "keyhole-test-runtime",
  "runtime_name": "Keyhole Test Runtime",
  "runtime_version": "0.1.0",
  "environment": "production",
  "capabilities": ["realize", "state", "health"]
}
```

### `GET /state`

Returns the current local runtime state.

**Response (initial):**

```json
{
  "current_digest": null,
  "realized_digests": [],
  "updated_at": "2026-03-06T12:00:00+00:00"
}
```

### `POST /realize`

Accepts a bounded realization request and mutates local state if the digest has not been realized before.

**Request:**

```json
{
  "candidate_digest": "sha256:abc123",
  "payload": {}
}
```

**Response (first application):**

```json
{
  "digest": "sha256:abc123",
  "status": "ACCEPT",
  "message": "Digest realized successfully.",
  "realized_at": "2026-03-06T12:01:00+00:00"
}
```

**Response (replay — same digest posted again):**

```json
{
  "digest": "sha256:abc123",
  "status": "ALREADY_REALIZED",
  "message": "Digest has already been realized. No state mutation performed.",
  "realized_at": "2026-03-06T12:02:00+00:00"
}
```

---

## Replay Behavior

The runtime enforces strict idempotent replay discipline:

1. The first `POST /realize` with a given `candidate_digest` mutates state and returns `ACCEPT`.
2. Any subsequent `POST /realize` with the same digest returns `ALREADY_REALIZED` without mutating state.
3. `GET /state` after a replay attempt reflects only the original mutation.

---

## Container Image

```text
ghcr.io/keyhole-solution/keyhole-test-runtime:latest
```

## Intended Use Cases

- External builders deploying a real runtime target
- SDK and CLI integration testing
- Bridge smoke tests against a live runtime
- Idempotent realization validation
- Traefik-compatible deployment examples

## Quick Start (Local)

```bash
docker run -p 8080:8080 ghcr.io/keyhole-solution/keyhole-test-runtime:latest
curl http://localhost:8080/healthz
curl http://localhost:8080/identity
curl http://localhost:8080/state
curl -X POST http://localhost:8080/realize \
  -H "Content-Type: application/json" \
  -d '{"candidate_digest": "sha256:abc123"}'
```
