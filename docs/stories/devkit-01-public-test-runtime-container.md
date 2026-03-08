<!--
Path: docs/stories/devkit-01-public-test-runtime-container.md
Owner: Keyhole Solution Foundation
Epic: DEVKIT-01 — Public Runtime Test Surface
Story: DEVKIT-01-01
Title: Package and Publish the First Public Keyhole Test Runtime Container
Status: READY
Created: 2026-03-06
Last Updated: 2026-03-06
Repo: keyhole-developer-kit
Purpose: Build, containerize, document, and publish the first public Keyhole test runtime as a deployable container image for external builders. This runtime must be real, routable, health-checkable, Traefik-compatible, and sufficient to close the missing end-to-end external runtime proof loop for CE-V5-S40-07.
Related:
  - CE-V5-S40-07 — Minimum Viable External Runtime Bridge
  - CE-V5-S40-11 — Developer Ecosystem Governance & Public Surface Readiness
  - CE-V5-S41 — Developer Ecosystem Governance & Dogfooding Academy
-->

# DEVKIT-01-01 — Package and Publish the First Public Keyhole Test Runtime Container

## 0) Story Intent

Build the **first public Keyhole runtime container** in the `keyhole-developer-kit` repository.

This runtime is **not** the Keyhole MCP server and **not** the full platform.

It is a deliberately small, public, reproducible runtime target that exists to:

- give external builders a real deployment target
- provide a stable runtime surface for SDK and CLI examples
- run behind Traefik on third-party infrastructure
- become the first public container surface of the Keyhole ecosystem
- help close the missing real-runtime proof loop for `CE-V5-S40-07`

The runtime must be:

- real
- HTTP-addressable
- health-checkable
- deterministic
- containerized
- publishable to a public container registry
- deployable by anyone with a small Compose file
- suitable for idempotent realization testing

---

## 1) Why This Story Exists

Right now, the missing truth gap is not the bridge implementation.

The missing truth gap is the lack of a **real external runtime target** that can be:

- deployed outside the Keyhole platform
- addressed by the existing HTTP bridge
- mutated through a bounded realization package
- verified via live state
- replay-tested for idempotent behavior

This story creates that runtime.

It also becomes the first public developer artifact that says:

> “Here is a real runtime surface you can deploy, touch, test, and verify.”

That matters both technically and strategically.

---

## 2) Scope

This story includes only the **public test runtime container surface** and the minimum required assets to build, publish, deploy, and document it.

### In scope

- runtime source code
- container Dockerfile
- service-local dependency file
- public image publishing workflow
- example server-side Docker Compose deployment
- Traefik-compatible labels/config
- runtime contract docs
- health/readiness surface
- basic smoke behavior documentation

### Out of scope

- public MCP server
- private platform internals
- full CLI orchestration
- full SDK rollout
- Academy expansion
- multi-language clients
- advanced authentication
- production-grade persistence
- internal promotion kernel logic
- private governance doctrine implementation details

This story is intentionally minimal.

---

## 3) Core Runtime Contract

The runtime must expose exactly these launch-grade endpoints:

### `GET /healthz`
Returns runtime health.

### `GET /identity`
Returns runtime identity and declared capabilities.

### `GET /state`
Returns current local runtime state.

### `POST /realize`
Accepts a bounded realization request and mutates local runtime state if the digest has not yet been realized.

The runtime must support:

- first application of a digest → `ACCEPT`
- repeated application of the same digest → deterministic `already_realized` / no-op style result

This runtime is a **test/runtime target**, not a governance engine.

---

## 4) Required Behavior

The runtime must behave as follows:

### 4.1 Identity
`/identity` must return a stable identifier and runtime metadata.

Minimum fields:

- runtime_id
- runtime_name
- runtime_version
- environment
- capabilities

### 4.2 State
`/state` must return current local runtime state.

Minimum fields:

- current candidate/version digest
- realized digest set or replay-detection state
- updated timestamp

### 4.3 Realization
`/realize` must:

- accept a bounded JSON payload
- extract the candidate digest
- detect replay of the same digest
- mutate local state only on first application
- return a structured receipt

### 4.4 Replay Discipline
If the same candidate digest is posted again, the runtime must:

- not mutate the state a second time
- return a deterministic already-realized/no-op style receipt
- preserve previous state

### 4.5 Health
`/healthz` must return success when the service is up and ready.

---

## 5) Deliverables

The repo agent must create all of the following.

### 5.1 Runtime source

```text
services/test-runtime/app/main.py
services/test-runtime/app/models.py
services/test-runtime/app/state.py
5.2 Dependencies and image
services/test-runtime/requirements.txt
services/test-runtime/Dockerfile
5.3 Deployment example
deploy/compose.server.yml
5.4 Publishing workflow
.github/workflows/publish-test-runtime.yml
5.5 Documentation
docs/test-runtime.md
docs/traefik-deploy.md
5.6 Optional but encouraged
services/test-runtime/README.md
openapi/test-runtime.openapi.yaml
6) File-by-File Requirements
6.1 services/test-runtime/app/main.py

Implement a small FastAPI application with the required endpoints:

GET /healthz

GET /identity

GET /state

POST /realize

Requirements:

listen on 0.0.0.0:8080

no hidden side effects outside service-local state

deterministic JSON responses

structured error responses for malformed payloads

no private Keyhole internals imported

This runtime must remain public-safe.

6.2 services/test-runtime/app/models.py

Define Pydantic models for:

identity response

state response

realization request

realization receipt

The models should be simple, explicit, and public-facing.

Do not mirror private internal schemas beyond what is needed for this runtime.

6.3 services/test-runtime/app/state.py

Implement an in-memory state store sufficient for launch.

Minimum state:

current_digest

realized_digests

updated_at

Provide helper functions to:

get current state

check whether a digest has been realized

apply a digest once

return deterministic already-realized behavior

This can be in-memory for now.
Do not introduce unnecessary persistence.

6.4 services/test-runtime/requirements.txt

Pin minimal runtime dependencies only.

Expected class of dependencies:

FastAPI

Uvicorn

Pydantic

Do not add dev/test-only dependencies here.

6.5 services/test-runtime/Dockerfile

The Dockerfile must:

use a small Python base image

set stable runtime environment variables

install service-local dependencies

copy only what is required

run as a non-root user

expose port 8080

include a HEALTHCHECK

include OCI labels, especially:

title

description

source repository

The source label must associate the image to the GitHub repository.

The final container must boot directly into the FastAPI/Uvicorn app.

6.6 deploy/compose.server.yml

This file is for external builders like.

It must:

reference the public image

set restart: unless-stopped

attach to an external Traefik/proxy network

expose Traefik labels for routing

route to internal service port 8080

Use a placeholder domain in the example such as:

runtime.example.yourdomain.com

Do not hardcode private internal domains.

6.7 .github/workflows/publish-test-runtime.yml

Add a GitHub Actions workflow that:

checks out the repo

logs into GHCR

builds the runtime image

pushes the image to GHCR

tags at minimum:

latest

sha-*

semver tags when available

Publish the image as:

ghcr.io/keyhole-solution/keyhole-test-runtime

The workflow must build from the runtime Dockerfile, not from the repo root blindly.

6.8 docs/test-runtime.md

Document:

what the test runtime is

what it is not

the four endpoints

example payloads

expected receipts

replay behavior

intended use cases

This doc should be readable by both humans and coding agents.

6.9 docs/traefik-deploy.md

Document exactly how a third party deploys the runtime behind Traefik.

Include:

Docker Compose usage

Traefik label meaning

required network assumptions

how to verify deployment

curl examples for /healthz and /identity

This document must be straightforward enough for anyone to follow without guessing.

7) Public Registry Policy

The image must be published publicly to GitHub Container Registry.

Canonical image name:

ghcr.io/keyhole-solution/keyhole-test-runtime

Required tag posture:

latest

semver release tags

immutable SHA tags

This runtime is intended to become the first public deployable container in the Keyhole ecosystem.

8) Traefik Compatibility Rules

The runtime must be deployable behind Traefik without code changes.

That means:

no hardcoded host assumptions

no self-generated base URLs

no assumption of direct port exposure to the public internet

health endpoint works through service-local port

service listens on 8080

all routing assumptions live in deployment config, not app code

9) Acceptance Criteria

This story is complete only if all of the following are true.

9.1 Runtime boots successfully in Docker

A local docker build and docker run succeeds.

9.2 Health endpoint works

GET /healthz returns success.

9.3 Identity endpoint works

GET /identity returns structured identity JSON.

9.4 State endpoint works

GET /state returns current local state.

9.5 Realization works

POST /realize with a new digest mutates state and returns ACCEPT.

9.6 Replay works

Posting the same digest a second time returns deterministic already-realized/no-op behavior without mutating state again.

9.7 Image publishes successfully

The GitHub Actions workflow can publish the image to GHCR.

9.8 anyone can deploy it behind Traefik

The provided deploy/compose.server.yml is sufficient for a third party to deploy the runtime behind Traefik.

9.9 Docs are truthful

The docs reflect actual container behavior and endpoints.

10) Non-Negotiable Guardrails

The repo agent must obey all of the following:

Do not expose private Keyhole platform logic

Do not publish MCP server code

Do not leak internal control-plane assumptions

Do not build a fake/mock-only runtime

Do not add unnecessary complexity

Do not add authentication unless explicitly requested later

Do not conflate this runtime with the real Keyhole governance server

Do not introduce speculative features unrelated to the four endpoint contract

This story is about a small truthful surface, not a grand platform clone.

11) Implementation Order

Follow this exact order.

Step 1

Implement runtime source (main.py, models.py, state.py).

Step 2

Add requirements.txt.

Step 3

Add the Dockerfile.

Step 4

Run a local build and verify the endpoints manually.

Step 5

Add deploy/compose.server.yml.

Step 6

Add docs (test-runtime.md, traefik-deploy.md).

Step 7

Add the GHCR publish workflow.

Step 8

Verify that the image can be built and published.

Step 9

Document the final public image reference and deployment steps.

12) Output Standard

At the end of implementation, the repo agent must be able to say truthfully:

The first public Keyhole test runtime container now exists, builds reproducibly, publishes to GHCR, exposes a real HTTP runtime contract, supports deterministic replay behavior, and can be deployed behind Traefik by an external builder.

If that sentence is not yet true, the story is not complete.

13) One-Sentence Standard

Build and publish the first real public Keyhole runtime container so external builders can deploy a truthful runtime target behind Traefik and use it to validate the bridge, SDK, and onboarding surface.