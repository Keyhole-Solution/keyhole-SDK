
SDK
# Keyhole Developer Kit

## Overview

**Keyhole** is a governance platform that manages how software changes are realized across environments. It enforces policy, audit, and identity requirements before any change is applied.

This repository exposes the **public developer interface** for Keyhole:

- Language SDKs (starting with Python)
- Public JSON schemas and OpenAPI contracts
- A **local test runtime** that developers can run to validate realization packages without connecting to a production Keyhole deployment
- Bridge examples and integration smoke tests

> This repository does **not** contain Keyhole's private governance engine, promotion kernel internals, production secrets, or protected control-plane logic.

---

## Quickstart

### 1. Start the test runtime

```bash
docker compose up
```

### 2. Verify the runtime is up

```bash
curl http://localhost:8080/identity
```

Expected response:

```json
{
  "runtime": "keyhole-test-runtime",
  "version": "0.1.0"
}
```

### 3. Send a realization package

```bash
curl -X POST http://localhost:8080/realize \
  -H "Content-Type: application/json" \
  -d '{
    "package_id": "pkg-001",
    "promotion_id": "promo-abc",
    "payload": {}
  }'
```

---

## SDK Usage

### Python

Install the SDK:

```bash
pip install -e ./packages/python
```

Invoke the test runtime from Python:

```python
from keyhole_sdk.client import KeyholeClient

client = KeyholeClient(base_url="http://localhost:8080")

# Check runtime identity
identity = client.get("/identity")
print(identity)

# Submit a realization package
receipt = client.post("/realize", json={
    "package_id": "pkg-001",
    "promotion_id": "promo-abc",
a local/public test runtime
