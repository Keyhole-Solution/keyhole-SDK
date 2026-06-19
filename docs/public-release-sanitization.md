# Public Release Sanitization

The Keyhole SDK intentionally targets the live Keyhole MCP boundary for public proof and discovery.

The live MCP endpoint is not a secret:

```text
https://mcp.keyholesolution.com
```

This repository does not include credentials, generated proof bundles, local governance state, historical receipts, or operator probe scripts.

Safe discovery and self-inspection may use the canonical MCP endpoint. Authenticated governed operations require explicit user login or token configuration.

Generated `.keyhole/` and `proof_bundle/` outputs are local runtime artifacts and must not be committed.

Public safety rules:

- Public live boundary: allowed.
- Public credentials: forbidden.
- Public generated operational state: forbidden.
- Public mutable live operations without explicit auth: forbidden.

Recommended public flow:

```powershell
keyhole validate
keyhole doctor
keyhole login --device
```

For live governed proof:

```powershell
$env:KEYHOLE_MCP_URL = "https://mcp.keyholesolution.com"
keyhole login --device
keyhole governed run --repo-dir .\my-first-app
```

Password/ROPC login is dev/test-only and disabled by default. To use it in a local development environment, set:

```powershell
$env:KEYHOLE_ENABLE_DEV_PASSWORD_LOGIN = "1"
```
