# keyhole-sdk

Python SDK for interacting with the Keyhole test runtime.

## Install

```bash
pip install -e .
```

## Usage

```python
from keyhole_sdk.client import RuntimeBridgeClient

client = RuntimeBridgeClient("http://localhost:8080")
print(client.identity())
```
