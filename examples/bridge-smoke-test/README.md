# Bridge Smoke Test

This example walks through a minimal **bridge smoke test** against the **Keyhole Test Runtime**.

Its purpose is to validate the public runtime contract end-to-end with the smallest possible set of calls:

1. confirm the runtime is reachable,
2. confirm the runtime identity,
3. inspect initial state,
4. submit a realization request,
5. replay the same request safely,
6. confirm state remains stable after replay.

This is a **manual smoke test** intended for builders, integrators, and CI validation of the public runtime surface.

---

## What This Example Verifies

This smoke test verifies that a bridge or client can successfully interact with the current public runtime surface:

- `GET /healthz`
- `GET /identity`
- `GET /state`
- `POST /realize`

It also verifies the runtime’s replay-safe behavior:

- the first submission of a new `candidate_digest` is accepted,
- a repeated submission of the same digest returns `ALREADY_REALIZED`,
- replay does not create a second state mutation.

---

## Prerequisites

Before running this smoke test, make sure you have:

- Docker and Docker Compose, or access to a running Keyhole Test Runtime
- `curl`
- a terminal

By default, this example assumes the runtime is available at:

```text
http://localhost:8080
Start the Runtime

From the root of the repository, start the test runtime:

docker compose up

If you prefer to run the published image directly:

docker run --rm -p 8080:8080 ghcr.io/keyhole-solution/keyhole-test-runtime:latest

Leave the runtime running while you perform the checks below.

Smoke Test Steps
1. Health Check

Verify the runtime is up:

curl http://localhost:8080/healthz

Expected response:

{
  "status": "ok"
}
2. Identity Check

Verify you are talking to the expected runtime:

curl http://localhost:8080/identity

Expected response:

{
  "runtime_id": "keyhole-test-runtime",
  "runtime_name": "Keyhole Test Runtime",
  "runtime_version": "0.1.0",
  "environment": "production",
  "capabilities": ["realize", "state", "health"]
}

This confirms the runtime identity and its declared public capabilities.

3. Inspect Initial State

Check the runtime-local state before any realization request:

curl http://localhost:8080/state

Example initial response:

{
  "current_digest": null,
  "realized_digests": [],
  "updated_at": "2026-03-06T12:00:00+00:00"
}

At this point, no digest should have been realized yet.

4. Submit a Realization Request

Send a bounded realization request:

curl -X POST http://localhost:8080/realize \
  -H "Content-Type: application/json" \
  -d '{"candidate_digest":"sha256:abc123","payload":{}}'

Expected response on first submission:

{
  "digest": "sha256:abc123",
  "status": "ACCEPT",
  "message": "Digest realized successfully.",
  "realized_at": "2026-03-06T12:01:00+00:00"
}

This confirms the runtime accepted the digest and mutated local state.

5. Confirm State Changed

Check state again:

curl http://localhost:8080/state

Expected shape:

{
  "current_digest": "sha256:abc123",
  "realized_digests": ["sha256:abc123"],
  "updated_at": "2026-03-06T12:01:00+00:00"
}

The exact timestamp may differ, but the digest should now appear in state.

6. Replay the Same Digest Safely

Send the exact same request again:

curl -X POST http://localhost:8080/realize \
  -H "Content-Type: application/json" \
  -d '{"candidate_digest":"sha256:abc123","payload":{}}'

Expected replay response:

{
  "digest": "sha256:abc123",
  "status": "ALREADY_REALIZED",
  "message": "Digest has already been realized. No state mutation performed.",
  "realized_at": "2026-03-06T12:02:00+00:00"
}

This is the key replay-safety check.

7. Confirm Replay Did Not Mutate State Again

Check state one more time:

curl http://localhost:8080/state

The digest list should still contain the same realized digest without duplication.

Expected shape:

{
  "current_digest": "sha256:abc123",
  "realized_digests": ["sha256:abc123"],
  "updated_at": "2026-03-06T12:01:00+00:00"
}

The runtime should remain stable after replay.

Pass / Fail Criteria

The smoke test passes if all of the following are true:

/healthz returns {"status":"ok"}

/identity returns the expected runtime identity and capabilities

/state initially shows no realized digest

the first POST /realize returns ACCEPT

the second POST /realize with the same digest returns ALREADY_REALIZED

/state reflects only a single realized mutation

The smoke test fails if any of these conditions are not met.

Minimal One-Screen Smoke Test

For quick manual validation, you can run:

curl http://localhost:8080/healthz
curl http://localhost:8080/identity
curl http://localhost:8080/state
curl -X POST http://localhost:8080/realize -H "Content-Type: application/json" -d '{"candidate_digest":"sha256:abc123","payload":{}}'
curl -X POST http://localhost:8080/realize -H "Content-Type: application/json" -d '{"candidate_digest":"sha256:abc123","payload":{}}'
curl http://localhost:8080/state
Optional Bash Script

If you want a single copy-paste shell script:

set -e

BASE_URL="http://localhost:8080"
DIGEST="sha256:abc123"

echo "== health =="
curl -s "$BASE_URL/healthz"
echo
echo

echo "== identity =="
curl -s "$BASE_URL/identity"
echo
echo

echo "== initial state =="
curl -s "$BASE_URL/state"
echo
echo

echo "== first realize =="
curl -s -X POST "$BASE_URL/realize" \
  -H "Content-Type: application/json" \
  -d "{\"candidate_digest\":\"$DIGEST\",\"payload\":{}}"
echo
echo

echo "== replay realize =="
curl -s -X POST "$BASE_URL/realize" \
  -H "Content-Type: application/json" \
  -d "{\"candidate_digest\":\"$DIGEST\",\"payload\":{}}"
echo
echo

echo "== final state =="
curl -s "$BASE_URL/state"
echo
Troubleshooting
The health check fails

Make sure the runtime is actually running and reachable on port 8080.

/identity does not match expectations

Confirm you are calling the intended runtime and not another local service.

POST /realize fails

Make sure:

the request uses Content-Type: application/json

the JSON is valid

candidate_digest is present

Replay does not return ALREADY_REALIZED

Make sure you sent the exact same candidate_digest both times.

Why This Example Exists

A bridge smoke test should be simple, fast, and deterministic.

This example gives builders the smallest useful contract-validation loop for the Keyhole Test Runtime:

reach the runtime,

verify identity,

test realization,

verify replay safety.

That makes it a good first validation step for local development, CI checks, and third-party integration work.