# keyhole-sdk

Python SDK for client-side Keyhole integration.

The SDK can:

- Validate local governance declarations.
- Validate capability passports.
- Submit requests to a configured governed server.
- Parse and expose governance receipts returned by that server.
- Fail safely when no governed server is configured.

The SDK does not implement server-side governance authority.

```python
from keyhole_sdk import KeyholeClient, KeyholeConfig

config = KeyholeConfig(
    base_url="https://your-keyhole-server.example.com",
    token="replace_me",
)
client = KeyholeClient.from_config(config)
```
