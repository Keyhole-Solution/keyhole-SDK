# Quickstart

This guide gets you from clone to a working **Keyhole Test Runtime** in a few minutes.

The Developer Kit is a **separate governed participant** in the Keyhole ecosystem. It gives you a real runtime target you can run locally, inspect over HTTP, and use to validate SDK, bridge, and realization behavior without needing access to a private Keyhole deployment.

> **Boundary note:** This repository learns platform truth through the MCP
> boundary — beginning with `GET /mcp/v1/capabilities` — not through private
> platform source. See [boundary-constitution.md](boundary-constitution.md)
> for the full posture.

---

## What You Will Start

The local quickstart uses the repository’s root Docker Compose configuration to build and run the test runtime from source.

When it is running, the runtime is available at:

```text
http://localhost:8080

The public runtime surface includes:

GET /healthz

GET /identity

GET /state

POST /realize

Prerequisites

Before you begin, make sure you have:

Git

Docker Desktop or a compatible Docker Engine with Compose support

A terminal capable of running docker and curl

You do not need access to a private Keyhole environment for this quickstart.

> **Mode note:** This quickstart runs the test runtime in **local-only** mode.
> Realization requests are executed immediately without MCP governance gating
> and no events are emitted to the Keyhole Event Spine.
> See [architecture.md](architecture.md) for the governed-mode path.

1. Clone the Repository
git clone https://github.com/Keyhole-Solution/keyhole-developer-kit.git
cd keyhole-developer-kit
2. Start the Test Runtime

Build and start the runtime:

docker compose up --build

What this does:

builds the local runtime from services/test-runtime,

starts the runtime container,

publishes port 8080 to your machine.

Once the runtime is up, leave that terminal open.

3. Verify the Runtime Is Alive

Open a second terminal and call the health endpoint:

curl http://localhost:8080/healthz

Expected response:

{
  "status": "ok"
}

If you get that response, the runtime is live and reachable.

4. Inspect Runtime Identity

Call the identity endpoint:

curl http://localhost:8080/identity

Example response:

{
  "runtime_id": "keyhole-test-runtime",
  "runtime_name": "Keyhole Test Runtime",
  "runtime_version": "0.1.0",
  "environment": "dev",
  "capabilities": ["realize", "state", "health"]
}

This confirms:

which runtime you are talking to,

which version it reports,

which public capabilities it declares.

5. Inspect Initial Runtime State

Call the state endpoint:

curl http://localhost:8080/state

Example initial response:

{
  "current_digest": null,
  "realized_digests": [],
  "updated_at": "2026-03-06T12:00:00+00:00"
}

At startup, no digest has been realized yet.

6. Submit a Realization Request

Send a realization request to the runtime:

curl -X POST http://localhost:8080/realize -H "Content-Type: application/json" -d "{\"candidate_digest\":\"sha256:abc123\",\"payload\":{}}"

Example response for the first submission:

{
  "digest": "sha256:abc123",
  "status": "ACCEPT",
  "message": "Digest realized successfully.",
  "realized_at": "2026-03-06T12:01:00+00:00"
}

This means the runtime accepted the digest and mutated its local state.

7. Confirm State Changed

Call the state endpoint again:

curl http://localhost:8080/state

Example response after realization:

{
  "current_digest": "sha256:abc123",
  "realized_digests": ["sha256:abc123"],
  "updated_at": "2026-03-06T12:01:00+00:00"
}

You should now see the digest reflected in runtime state.

8. Replay the Same Request Safely

Send the exact same digest again:

curl -X POST http://localhost:8080/realize -H "Content-Type: application/json" -d "{\"candidate_digest\":\"sha256:abc123\",\"payload\":{}}"

Example replay response:

{
  "digest": "sha256:abc123",
  "status": "ALREADY_REALIZED",
  "message": "Digest has already been realized. No state mutation performed.",
  "realized_at": "2026-03-06T12:02:00+00:00"
}

This is expected.

The runtime is designed to be replay-safe:

the first submission of a new digest mutates state,

a repeated submission of the same digest does not mutate state again,

the runtime explicitly reports that the digest was already realized.

This makes the runtime safe for retries, smoke tests, and repeated local validation.

9. Stop the Runtime

When you are done:

docker compose down

If you also want to remove intermediate containers and related state created by Compose, you can rerun with any cleanup options you prefer.

Optional: Run the Published Container Image Directly

The test runtime is also published as a public GHCR image.

Run it directly without building from source:

docker run --rm -p 8080:8080 ghcr.io/keyhole-solution/keyhole-test-runtime:latest

Then verify it the same way:

curl http://localhost:8080/healthz
curl http://localhost:8080/identity
curl http://localhost:8080/state

And submit a realization request:

curl -X POST http://localhost:8080/realize -H "Content-Type: application/json" -d "{\"candidate_digest\":\"sha256:abc123\",\"payload\":{}}"
What This Quickstart Proves

By completing this quickstart, you have verified that you can:

run the Keyhole Test Runtime locally in local-only mode,

call the public HTTP surface,

inspect identity and runtime state,

submit a bounded realization request,

observe deterministic replay-safe behavior.

> **What this does NOT prove:** governance gating, Event Spine emission,
> or MCP-surface integration. Those require governed mode (see
> [architecture.md](architecture.md)).

That is the foundation for everything else in this repository:

SDK validation,

bridge development,

smoke tests,

remote deployment experiments,

public contract integration work.

Where to Go Next

After this quickstart, the next best docs to read are:

docs/auth-bootstrap.md — authentication and identity bootstrap for governed usage

docs/boundary-constitution.md — boundary posture and platform relationship

docs/test-runtime.md — full runtime behavior and endpoint contract

docs/bridge-contract.md — public bridge interaction model

docs/architecture.md — public developer surface architecture

docs/traefik-deploy.md — remote deployment behind Traefik

> **Local-only vs governed:** This quickstart runs in **local-only** mode —
> no authentication or MCP boundary connection is needed. For connecting to
> the governed boundary with authentication and identity inspection, see
> [auth-bootstrap.md](auth-bootstrap.md).

Troubleshooting
docker compose up --build fails

Make sure Docker is running and that Compose is available from your terminal.

curl http://localhost:8080/healthz does not respond

Check that the runtime container is still running and that port 8080 is available on your machine.

POST /realize fails

Make sure:

you are sending Content-Type: application/json,

your request body is valid JSON,

candidate_digest is present.

Replay does not return ALREADY_REALIZED

If you changed the digest value, the runtime will treat it as a new realization request. Replay behavior only applies when the same candidate_digest is posted again.

Summary

The quickstart is intentionally simple:

start the runtime,

verify health,

inspect identity,

inspect state,

submit a realization request,

replay the same request safely.

That gives you a real, executable public Keyhole surface to build against without exposing private platform internals.