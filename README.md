# Keyhole Developer Kit

## Overview

**Keyhole** is a governance platform that manages how software changes are realized across environments. It enforces policy, audit, and identity requirements before any change is applied.

This repository exposes the **public developer interface** for Keyhole:

- Language SDKs (starting with Python)
- Public JSON schemas and OpenAPI contracts
- A **local test runtime** that developers can run to validate realization behavior without connecting to a production Keyhole deployment
- Bridge examples and integration smoke tests
- Deployment templates for running the public runtime on third-party infrastructure

> This repository does **not** contain Keyhole's private governance engine, promotion kernel internals, production secrets, or protected control-plane logic.

---

## What This Repository Is For

The Keyhole Developer Kit exists to let external builders:

- understand the public Keyhole integration model,
- develop against stable public contracts,
- run a real local runtime target,
- validate SDK, bridge, and realization behavior without requiring access to a private Keyhole deployment.

The goal is to provide a **real, executable public developer surface** while keeping protected Keyhole internals outside the repository.

---

## Quickstart

### 1. Install the SDK

```bash
pip install keyhole-sdk
```

### 2. Start the test runtime

```bash
docker compose up
```

### 3. Verify the runtime is up

```bash
curl http://localhost:8080/healthz
curl http://localhost:8080/identity
```

Example identity response:

```json
{
  "runtime_id": "keyhole-test-runtime",
  "runtime_name": "Keyhole Test Runtime",
  "runtime_version": "0.1.0",
  "environment": "production",
  "capabilities": ["realize", "state", "health"]
}
```

### 4. Inspect runtime state

```bash
curl http://localhost:8080/state
```

Example initial response:

```json
{
  "current_digest": null,
  "realized_digests": [],
  "updated_at": "2026-03-06T12:00:00+00:00"
}
```

### 5. Submit a realization request

```bash
curl -X POST http://localhost:8080/realize \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_digest": "sha256:abc123",
    "payload": {}
  }'
```

Example first response:

```json
{
  "digest": "sha256:abc123",
  "status": "ACCEPT",
  "message": "Digest realized successfully.",
  "realized_at": "2026-03-06T12:01:00+00:00"
}
```

### 6. Replay the same request safely

```bash
curl -X POST http://localhost:8080/realize \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_digest": "sha256:abc123",
    "payload": {}
  }'
```

Example replay response:

```json
{
  "digest": "sha256:abc123",
  "status": "ALREADY_REALIZED",
  "message": "Digest has already been realized. No state mutation performed.",
  "realized_at": "2026-03-06T12:02:00+00:00"
}
```

---

## SDK Usage

### Python

Install from PyPI:

```bash
pip install keyhole-sdk
```

Use the SDK client:

```python
from keyhole_sdk import KeyholeClient

client = KeyholeClient(base_url="http://localhost:8080")

# Check health
print(client.health())

# Runtime identity
print(client.identity())

# Runtime state
print(client.state())

# Submit a realization request
receipt = client.realize(
    candidate_digest="sha256:abc123",
    payload={},
)
print(receipt)

# Replay the same digest safely
replay = client.realize(
    candidate_digest="sha256:abc123",
    payload={},
)
print(replay)

client.close()
```

### CLI

Install the CLI:

```bash
pip install keyhole-cli
```

```bash
keyhole runtime health
keyhole runtime identity
keyhole runtime state
keyhole runtime realize sha256:abc123
```

The CLI reads `KEYHOLE_RUNTIME_URL` from the environment (default: `http://localhost:8080`).

---

## Public Runtime Surface

The public test runtime currently exposes:

- `GET /healthz` — liveness check
- `GET /identity` — runtime identity and declared capabilities
- `GET /state` — current runtime-local state
- `POST /realize` — bounded realization endpoint with digest-based idempotent replay behavior

This runtime is intentionally narrow in scope.

It is:

- a real HTTP-addressable target for SDK and bridge validation,
- a deterministic local/public runtime for integration testing,
- a deployable container image for external builders.

It is **not**:

- the Keyhole MCP server,
- the full Keyhole platform,
- a governance engine,
- a production persistence layer.

---

## Repository Structure

```text
.
├── deploy/
│   └── compose.server.yml
├── docs/
│   ├── architecture.md
│   ├── bridge-contract.md
│   ├── quickstart.md
│   ├── test-runtime.md
│   └── traefik-deploy.md
├── examples/
│   ├── bridge-smoke-test/
│   └── python-client/
├── openapi/
│   └── test-runtime.openapi.yaml
├── packages/
│   └── python/
│       ├── keyhole-sdk/
│       └── keyhole-cli/
├── schemas/
│   ├── realization_request.v1.schema.json
│   └── runtime_realization_receipt.v1.schema.json
├── services/
│   └── test-runtime/
├── docker-compose.yml
└── README.md
```

---

## PyPI Packages

| Package | Description |
|---------|-------------|
| [`keyhole-sdk`](https://pypi.org/project/keyhole-sdk/) | Python SDK for interacting with Keyhole-compatible runtimes |
| [`keyhole-cli`](https://pypi.org/project/keyhole-cli/) | CLI for interacting with Keyhole-compatible runtimes |

---

## Container Image

The public test runtime container is published to GHCR:

```text
ghcr.io/keyhole-solution/keyhole-test-runtime:latest
```

---

## Intended Use Cases

This repository is designed for:

- external builders deploying a real runtime target,
- SDK and CLI integration testing,
- bridge smoke tests,
- contract validation against a stable public surface,
- local and remote replay-safe realization testing.

---

## Boundary Discipline

This repository is the public builder-facing surface of the Keyhole ecosystem.

It exposes public contracts, runtime behavior, examples, SDK integration patterns, and deployable public artifacts.

It does **not** expose private governance internals. That separation is intentional and load-bearing.
