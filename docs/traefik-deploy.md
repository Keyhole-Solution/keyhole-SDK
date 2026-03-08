# Deploying the Keyhole Test Runtime Behind Traefik

This guide explains how a third party can deploy the Keyhole Test Runtime container behind a Traefik reverse proxy using Docker Compose.

---

## Prerequisites

- Docker and Docker Compose installed
- A running Traefik instance connected to an external Docker network named `proxy`
- A DNS record pointing your chosen domain to the server running Traefik

---

## Docker Compose Setup

Create a `compose.server.yml` file (or use the one provided in `deploy/compose.server.yml`):

```yaml
version: "3.8"

services:
  keyhole-test-runtime:
    image: ghcr.io/keyhole-solution/keyhole-test-runtime:latest
    restart: unless-stopped
    networks:
      - proxy
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.keyhole-test-runtime.rule=Host(`runtime.example.yourdomain.com`)"
      - "traefik.http.routers.keyhole-test-runtime.entrypoints=websecure"
      - "traefik.http.routers.keyhole-test-runtime.tls.certresolver=letsencrypt"
      - "traefik.http.services.keyhole-test-runtime.loadbalancer.server.port=8080"

networks:
  proxy:
    external: true
```

Replace `runtime.example.yourdomain.com` with your actual domain.

---

## Traefik Label Reference

| Label | Purpose |
|---|---|
| `traefik.enable=true` | Tells Traefik to discover and route to this service |
| `traefik.http.routers.*.rule=Host(...)` | Routes requests matching the specified hostname |
| `traefik.http.routers.*.entrypoints=websecure` | Uses the HTTPS entrypoint |
| `traefik.http.routers.*.tls.certresolver=letsencrypt` | Automatically provisions a TLS certificate |
| `traefik.http.services.*.loadbalancer.server.port=8080` | Tells Traefik the container listens on port 8080 |

---

## Network Requirements

The runtime container must share a Docker network with Traefik. This guide assumes an external network named `proxy`.

If your Traefik network has a different name, update the `networks` section accordingly.

Create the network if it does not already exist:

```bash
docker network create proxy
```

---

## Deploy

```bash
docker compose -f compose.server.yml up -d
```

---

## Verify Deployment

### Health check

```bash
curl https://runtime.example.yourdomain.com/healthz
```

Expected response:

```json
{"status": "ok"}
```

### Identity

```bash
curl https://runtime.example.yourdomain.com/identity
```

Expected response:

```json
{
  "runtime_id": "keyhole-test-runtime",
  "runtime_name": "Keyhole Test Runtime",
  "runtime_version": "0.1.0",
  "environment": "production",
  "capabilities": ["realize", "state", "health"]
}
```

### State

```bash
curl https://runtime.example.yourdomain.com/state
```

### Realization

```bash
curl -X POST https://runtime.example.yourdomain.com/realize \
  -H "Content-Type: application/json" \
  -d '{"candidate_digest": "sha256:abc123"}'
```

---

## Troubleshooting

- **Container not discovered by Traefik:** Ensure the container and Traefik share the same Docker network (`proxy`).
- **502 Bad Gateway:** Verify the `loadbalancer.server.port` label matches the container's listening port (8080).
- **TLS errors:** Confirm your DNS record resolves to the Traefik host and that the `certresolver` is configured in your Traefik static configuration.
- **Health check failing:** Run `docker logs keyhole-test-runtime` to verify the application started successfully.
