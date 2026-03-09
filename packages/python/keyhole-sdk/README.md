# keyhole-sdk

Python SDK for interacting with [Keyhole](https://github.com/Keyhole-Solution/keyhole-developer-kit)-compatible runtimes.

## Install

```bash
pip install keyhole-sdk
```

## Quickstart

```python
from keyhole_sdk import KeyholeClient

client = KeyholeClient(base_url="http://localhost:8080")

# Health check
print(client.health())

# Runtime identity and capabilities (includes governance_mode)
identity = client.identity()
print(identity)  # governance_mode: "local-only" or "governed"

# Current runtime state
print(client.state())

# Submit a realization request
receipt = client.realize(
    candidate_digest="sha256:abc123",
    payload={},
)
print(receipt)  # includes governance_verdict, version, pointer

# Replay the same digest safely
replay = client.realize(
    candidate_digest="sha256:abc123",
    payload={},
)
print(replay)

client.close()
```

> **Note:** By default the test runtime runs in local-only mode
> (`governance_verdict: "LOCAL_ONLY"`). Set `KEYHOLE_MCP_URL` and
> `KEYHOLE_MCP_TOKEN` on the runtime to enable governed mode.

## API

| Method | Description |
|--------|-------------|
| `health()` | `GET /healthz` — runtime liveness |
| `identity()` | `GET /identity` — runtime identity and capabilities |
| `state()` | `GET /state` — current runtime-local state |
| `realize(candidate_digest, payload)` | `POST /realize` — bounded realization request |
| `close()` | Close the underlying HTTP session |

## Models

Pydantic models are available in `keyhole_sdk.models`:

- `RuntimeIdentity`
- `RuntimeState`
- `RealizationRequest`
- `RealizationReceipt`

## Configuration

```python
client = KeyholeClient(
    base_url="http://localhost:8080",
    timeout=10.0,  # default
)
```

You can also pass a custom `requests.Session` for advanced use cases.

## Compatibility

`RuntimeBridgeClient` is available as a backward-compatible alias for `KeyholeClient`.

## License

Apache 2.0 — see [LICENSE](https://github.com/Keyhole-Solution/keyhole-developer-kit/blob/main/LICENSE).
