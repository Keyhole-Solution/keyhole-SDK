STORY DEVKIT-01-01
README.md

README must contain:

Overview

Explain:

Keyhole is a governance platform

this repository exposes the public developer interface

the repo contains a test runtime

Quickstart
docker compose up

Then:

curl http://localhost:8080/identity
Example realization
POST /realize
SDK usage

Python example invoking the runtime.

STORY DEVKIT-01-02
Docker Compose Environment

File:

docker-compose.yml

Purpose:

Launch test runtime and expose it via Traefik.

Compose configuration
version: "3.9"

services:

  test-runtime:
    build: ./services/test-runtime
    container_name: keyhole-test-runtime
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.keyhole-test.rule=Host(`test.keyhole.local`)"
      - "traefik.http.services.keyhole-test.loadbalancer.server.port=8080"
    networks:
      - keyhole-net

networks:
  keyhole-net:
    external: false