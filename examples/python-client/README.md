# Python Client Example

This example shows how to use the **Keyhole Python SDK** against the **Keyhole Test Runtime**.

It is intended as the simplest end-to-end example of a Python client interacting with the public runtime surface.

---

## What This Example Covers

This example demonstrates how to:

- connect to a running Keyhole Test Runtime,
- inspect runtime identity,
- inspect runtime-local state,
- submit a realization request,
- replay the same request and observe the runtime response.

This example uses the SDK exactly as it currently exists in this repository.

---

## Prerequisites

Before running this example, make sure you have:

- Python 3.9+ installed
- the Keyhole Test Runtime running on `http://localhost:8080`

---

## Start the Runtime

From the repository root:

```bash
docker compose up
```

You can verify the runtime manually:

```bash
curl http://localhost:8080/healthz
curl http://localhost:8080/identity
```

## Install the SDK

```bash
pip install keyhole-sdk
```

Or from the repository root for local development:

```bash
pip install -e packages/python/keyhole-sdk
```

## Example Code

Create a file such as `example.py` with the following contents:

```python
from keyhole_sdk import KeyholeClient

client = KeyholeClient(base_url="http://localhost:8080")

print("== health ==")
print(client.health())

print()
print("== identity ==")
print(client.identity())

print()
print("== initial state ==")
print(client.state())

print()
print("== first realize ==")
first_receipt = client.realize(
    candidate_digest="sha256:python-client-example",
    payload={"source": "python-client-example"},
)
print(first_receipt)

print()
print("== replay realize ==")
replay_receipt = client.realize(
    candidate_digest="sha256:python-client-example",
    payload={"source": "python-client-example"},
)
print(replay_receipt)

print()
print("== final state ==")
print(client.state())

client.close()
```

Run it with:

```bash
python example.py
```

## Expected Behavior

When the runtime is working correctly:

- `health()` returns `{"status": "ok"}`.
- `identity()` returns the runtime identity, declared capabilities, and `governance_mode` (`"local-only"` by default).
- `state()` initially shows no realized digest for this example.
- The first `realize(...)` call is accepted and mutates runtime-local state. The receipt includes `governance_verdict` (`"LOCAL_ONLY"` in local-only mode), `version`, and `pointer`.
- The second `realize(...)` call with the same digest returns `ALREADY_REALIZED`.
- The final `state()` call shows the realized digest in runtime state.

> **Note:** By default the runtime operates in local-only mode — realization
> is not gated through MCP governance. See
> [docs/architecture.md](../../docs/architecture.md) for the governed-mode path.

## SDK Method to Endpoint Mapping

| Method | Endpoint |
|--------|----------|
| `client.health()` | `GET /healthz` |
| `client.identity()` | `GET /identity` |
| `client.state()` | `GET /state` |
| `client.realize(candidate_digest, payload)` | `POST /realize` |

## Related Files

- [packages/python/keyhole-sdk/README.md](../../packages/python/keyhole-sdk/README.md)
- [docs/test-runtime.md](../../docs/test-runtime.md)
- [docs/bridge-contract.md](../../docs/bridge-contract.md)
- [examples/bridge-smoke-test](../bridge-smoke-test/)