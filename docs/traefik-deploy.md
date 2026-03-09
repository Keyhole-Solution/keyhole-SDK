# Deploying the Keyhole Test Runtime Behind Traefik

This guide explains how to deploy the **Keyhole Test Runtime** behind a Traefik reverse proxy using Docker Compose.

It is intended for third parties who want to expose the public runtime over HTTPS on their own infrastructure.

---

## What This Deploys

This guide deploys the public runtime container:

- behind Traefik,
- on a shared external Docker network,
- with hostname-based routing,
- with HTTPS termination handled by Traefik.

This is a deployment pattern for the **public builder-facing runtime**, not for private Keyhole control-plane components.

---

## Prerequisites

Before you begin, make sure you have:

- Docker Engine and Docker Compose installed
- A running Traefik instance on the same Docker host
- A shared external Docker network that Traefik is already attached to
- A DNS record pointing your chosen hostname to the server running Traefik
- A working TLS certificate resolver configured in Traefik if you want automatic HTTPS certificates

This guide assumes the shared Docker network is named `proxy`, but you can use a different name if needed.

---

## Deployment File

Use the deployment template in:

```text
deploy/compose.server.yml

A reusable version of that file should look like this:

services:
  keyhole-test-runtime:
    image: ${KEYHOLE_RUNTIME_IMAGE:-ghcr.io/keyhole-solution/keyhole-test-runtime}:${KEYHOLE_RUNTIME_TAG:-latest}
    restart: unless-stopped
    pull_policy: always
    networks:
      - proxy
    labels:
      - traefik.enable=true
      - traefik.docker.network=${TRAEFIK_PROXY_NETWORK:-proxy}
      - traefik.http.routers.keyhole-test-runtime.rule=Host(`${KEYHOLE_RUNTIME_HOST:-runtime.example.yourdomain.com}`)
      - traefik.http.routers.keyhole-test-runtime.entrypoints=${TRAEFIK_ENTRYPOINTS:-websecure}
      - traefik.http.routers.keyhole-test-runtime.tls=true
      - traefik.http.routers.keyhole-test-runtime.tls.certresolver=${TRAEFIK_CERTRESOLVER:-letsencrypt}
      - traefik.http.services.keyhole-test-runtime.loadbalancer.server.port=8080

networks:
  proxy:
    external: true
    name: ${TRAEFIK_PROXY_NETWORK:-proxy}

This keeps the deployment template reusable while still working out of the box for common defaults.

Configuration

Set the values you want either in your shell environment or in a .env file beside the compose file.

Minimum required value

You should set at least:

KEYHOLE_RUNTIME_HOST=runtime.example.yourdomain.com
Common optional values
KEYHOLE_RUNTIME_IMAGE=ghcr.io/keyhole-solution/keyhole-test-runtime
KEYHOLE_RUNTIME_TAG=latest
TRAEFIK_PROXY_NETWORK=proxy
TRAEFIK_ENTRYPOINTS=websecure
TRAEFIK_CERTRESOLVER=letsencrypt
What these values mean

KEYHOLE_RUNTIME_HOST — the hostname Traefik should route to this runtime

KEYHOLE_RUNTIME_IMAGE — the container image repository

KEYHOLE_RUNTIME_TAG — the container image tag to deploy

TRAEFIK_PROXY_NETWORK — the shared Docker network Traefik uses

TRAEFIK_ENTRYPOINTS — the Traefik entrypoint, usually websecure

TRAEFIK_CERTRESOLVER — the Traefik certificate resolver name

Network Requirements

The runtime container must share a Docker network with Traefik.

That shared network is how Traefik reaches the container after matching the incoming hostname.

This guide assumes the external network is named proxy.

If your Traefik network uses a different name, set:

TRAEFIK_PROXY_NETWORK=your-network-name

Create the network if it does not already exist:

docker network create proxy

If Traefik is already deployed, make sure Traefik is also attached to that same external network.

Deploy

From the directory containing your compose file, run:

docker compose -f compose.server.yml up -d

If you are using the repo-provided file directly:

docker compose -f deploy/compose.server.yml up -d
Verify Deployment

Once the container is up and Traefik has loaded the route, verify the deployment using your real hostname.

In the examples below, replace:

runtime.example.yourdomain.com

with your actual hostname.

Health check
curl https://runtime.example.yourdomain.com/healthz

Expected response:

{
  "status": "ok"
}
Identity
curl https://runtime.example.yourdomain.com/identity

Example response:

{
  "runtime_id": "keyhole-test-runtime",
  "runtime_name": "Keyhole Test Runtime",
  "runtime_version": "0.1.0",
  "environment": "dev",
  "capabilities": ["realize", "state", "health"]
}
State
curl https://runtime.example.yourdomain.com/state

Example initial response:

{
  "current_digest": null,
  "realized_digests": [],
  "updated_at": "2026-03-06T12:00:00+00:00"
}
Realization
curl -X POST https://runtime.example.yourdomain.com/realize \
  -H "Content-Type: application/json" \
  -d '{"candidate_digest":"sha256:abc123","payload":{}}'

Example response on first submission:

{
  "digest": "sha256:abc123",
  "status": "ACCEPT",
  "message": "Digest realized successfully.",
  "realized_at": "2026-03-06T12:01:00+00:00"
}

Replay the same request safely:

curl -X POST https://runtime.example.yourdomain.com/realize \
  -H "Content-Type: application/json" \
  -d '{"candidate_digest":"sha256:abc123","payload":{}}'

Example replay response:

{
  "digest": "sha256:abc123",
  "status": "ALREADY_REALIZED",
  "message": "Digest has already been realized. No state mutation performed.",
  "realized_at": "2026-03-06T12:02:00+00:00"
}
Traefik Label Reference
Label	Purpose
traefik.enable=true	Tells Traefik to discover this container
traefik.docker.network=...	Tells Traefik which Docker network to use to reach the container
traefik.http.routers.keyhole-test-runtime.rule=Host(...)	Routes requests for the specified hostname
traefik.http.routers.keyhole-test-runtime.entrypoints=...	Binds the router to the chosen Traefik entrypoint
traefik.http.routers.keyhole-test-runtime.tls=true	Enables TLS for the router
traefik.http.routers.keyhole-test-runtime.tls.certresolver=...	Uses the named certificate resolver
traefik.http.services.keyhole-test-runtime.loadbalancer.server.port=8080	Tells Traefik the application listens on port 8080 inside the container
Operational Notes
Use a pinned image tag when stability matters

latest is fine for quick tests, but for repeatable deployments you should pin a specific tag.

Example:

KEYHOLE_RUNTIME_TAG=sha-abcdef123456

or a release tag:

KEYHOLE_RUNTIME_TAG=v1.0.0
Keep the runtime and Traefik on the same host unless you know your networking model

This guide assumes Docker-network-based service discovery on the same machine.

The runtime itself does not terminate TLS

Traefik handles TLS termination. The application continues to listen on port 8080 inside the container.

Troubleshooting
Container not discovered by Traefik

Make sure:

Traefik is running,

Traefik’s Docker provider is enabled,

the runtime container and Traefik share the same external Docker network,

traefik.enable=true is present.

404 from Traefik

Make sure the hostname in your DNS record matches the hostname in:

KEYHOLE_RUNTIME_HOST

and the router rule.

502 Bad Gateway

Make sure:

the container is actually running,

the application is listening on port 8080,

the label traefik.http.services.keyhole-test-runtime.loadbalancer.server.port=8080 is correct,

traefik.docker.network matches the real shared network.

TLS errors

Make sure:

your DNS record resolves to the Traefik host,

the Traefik entrypoint is correct,

the certificate resolver is configured in Traefik,

ports 80 and 443 are reachable if your resolver needs them.

Health check fails

Inspect the runtime logs:

docker logs keyhole-test-runtime

You can also verify the container directly on the Docker host if needed.

Summary

Deploying the Keyhole Test Runtime behind Traefik gives you:

a real HTTPS-addressable runtime target,

hostname-based routing,

a clean public validation surface,

a deployable environment for SDK, bridge, and replay-safe realization testing.

This is the recommended public-facing deployment pattern for the Keyhole Test Runtime on third-party infrastructure.