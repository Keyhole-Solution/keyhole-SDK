# Keyhole Developer Kit

## Overview

**Keyhole** is a governance platform that manages how software changes are realized across environments. It enforces policy, audit, and identity requirements before any change is applied.

This repository exposes the **public developer interface** for Keyhole:

- Language SDKs (starting with Python)
- Public JSON schemas and OpenAPI contracts
- A **local test runtime** that developers can run to validate realization behavior without connecting to a production Keyhole deployment
- Bridge examples and integration smoke tests
- Deployment templates for running the public runtime on third-party infrastructure

> This repository does **not** contain Keyhole’s private governance engine, promotion kernel internals, production secrets, or protected control-plane logic.

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

### 1. Start the test runtime

```bash
docker compose up
2. Verify the runtime is up
curl http://localhost:8080/healthz
curl http://localhost:8080/identity

Example identity response:

{
  "runtime_id": "keyhole-test-runtime",
  "runtime_name": "Keyhole Test Runtime",
  "runtime_version": "0.1.0",
  "environment": "production",
  "capabilities": ["realize", "state", "health"]
}
3. Inspect runtime state
curl http://localhost:8080/state

Example initial response:

{
  "current_digest": null,
  "realized_digests": [],
  "updated_at": "2026-03-06T12:00:00+00:00"
}
4. Submit a realization request
curl -X POST http://localhost:8080/realize \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_digest": "sha256:abc123",
    "payload": {}
  }'

Example first response:

{
  "digest": "sha256:abc123",
  "status": "ACCEPT",
  "message": "Digest realized successfully.",
  "realized_at": "2026-03-06T12:01:00+00:00"
}
5. Replay the same request safely
curl -X POST http://localhost:8080/realize \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_digest": "sha256:abc123",
    "payload": {}
  }'

Example replay response:

{
  "digest": "sha256:abc123",
  "status": "ALREADY_REALIZED",
  "message": "Digest has already been realized. No state mutation performed.",
  "realized_at": "2026-03-06T12:02:00+00:00"
}
SDK Usage
Python

Install the SDK:

pip install -e ./packages/python

Invoke the test runtime from Python:

from keyhole_sdk.client import KeyholeClient

client = KeyholeClient(base_url="http://localhost:8080")

# Check runtime identity
identity = client.get("/identity")
print(identity)

# Inspect state
state = client.get("/state")
print(state)

# Submit a realization request
receipt = client.post(
    "/realize",
    json={
        "candidate_digest": "sha256:abc123",
        "payload": {}
    }
)
print(receipt)

# Replay the same digest safely
replay = client.post(
    "/realize",
    json={
        "candidate_digest": "sha256:abc123",
        "payload": {}
    }
)
print(replay)
Public Runtime Surface

The public test runtime currently exposes:

GET /healthz — liveness check

GET /identity — runtime identity and declared capabilities

GET /state — current local runtime state

POST /realize — bounded realization endpoint with digest-based idempotent replay behavior

This runtime is intentionally narrow in scope.

It is:

a real HTTP-addressable target for SDK and bridge validation,

a deterministic local/public runtime for integration testing,

a deployable container image for external builders.

It is not:

the Keyhole MCP server,

the full Keyhole platform,

a governance engine,

a production persistence layer.

Repository Structure
.
├── .github/
│   └── workflows/
├── deploy/
│   └── compose.server.yml
├── docs/
│   ├── architecture.md
│   ├── bridge-contract.md
│   ├── quickstart.md
│   ├── test-runtime.md
│   └── traefik-deploy.md
├── examples/
├── services/
│   └── test-runtime/
├── docker-compose.yml
├── Makefile
└── README.md
Container Image

The public test runtime container is published to GHCR:

ghcr.io/keyhole-solution/keyhole-test-runtime:latest
Intended Use Cases

This repository is designed for:

external builders deploying a real runtime target,

SDK and CLI integration testing,

bridge smoke tests,

contract validation against a stable public surface,

local and remote replay-safe realization testing.

Boundary Discipline

This repository is the public builder-facing surface of the Keyhole ecosystem.

It is meant to expose:

public contracts,

public runtime behavior,

examples,

SDK-facing integration patterns,

deployable public artifacts.

It is not meant to expose private governance internals.

That separation is intentional and load-bearing.

Status

This repository is the first public Keyhole developer kit surface and will expand over time.

Planned growth includes:

additional language SDKs,

richer public schemas,

stronger bridge examples,

broader smoke-test coverage,

improved deployment templates.

The core principle will remain the same:

public developer capability expands, while private governance internals remain outside the boundary.