# SDK-CLIENT-01 Smoke Tests

Official smoke tests for the Keyhole SDK auth bootstrap lifecycle.

## Overview

These tests validate the SDK + CLI against the live MCP server, proving:
- Real auth flow (OIDC device flow)
- Real token acquisition and storage
- Real `/whoami` identity verification
- Real proof bundle generation
- Optional event emission to Event Spine

**Note:** This is an operator-assisted smoke test. Device flow may require
user interaction and is not assumed to be unattended CI.

## Test Structure

### Layers

| Layer | Name | Purpose |
|-------|------|---------|
| 0 | Prerequisites | Check required tools (curl, jq, keyhole, python3) |
| (opt) | Local Runtime | Probe local runtime if CHECK_LOCAL_RUNTIME=true |
| 1 | CLI Login | Execute `keyhole login --flow device --json` |
| 2 | Token Capture | Extract and validate token from credentials file |
| 3 | Whoami CLI | Verify identity via `keyhole whoami --json` |
| 4 | Direct MCP | Call `/mcp/v1/whoami` directly with token |
| 5 | Secondary | Test token on secondary authenticated endpoint |
| 6 | Event Spine | Check for AUTH_SUCCESS event (optional) |
| 7 | Proof Bundle | Verify proof artifacts |

## Files

- `sdk_client_01_auth_bootstrap.sh` - Interactive bash smoke test
- `test_sdk_client_01_auth_bootstrap.py` - Pytest CI companion

## Running the Tests

### Bash Script (Interactive)

```bash
# Full test against live MCP (default)
./tests/smoke/sdk_client_01_auth_bootstrap.sh

# Check local runtime as well
CHECK_LOCAL_RUNTIME=true ./tests/smoke/sdk_client_01_auth_bootstrap.sh

# Skip event check (if event spine not yet wired)
SKIP_EVENT_CHECK=true ./tests/smoke/sdk_client_01_auth_bootstrap.sh

# Require event check to pass (fail if events unavailable)
EVENT_CHECK_REQUIRED=true ./tests/smoke/sdk_client_01_auth_bootstrap.sh

# Debug mode
DEBUG=true ./tests/smoke/sdk_client_01_auth_bootstrap.sh
```

### Pytest (CI)

```bash
# Run with MCP access
MCP_AVAILABLE=true pytest tests/smoke/test_sdk_client_01_auth_bootstrap.py -v

# Run without MCP (skips network-dependent tests)
pytest tests/smoke/test_sdk_client_01_auth_bootstrap.py -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_BASE_URL` | `https://mcp.keyholesolution.com` | MCP server URL |
| `KEYHOLE_HOME` | `~/.keyhole` | Keyhole config directory |
| `CHECK_LOCAL_RUNTIME` | `false` | Probe local runtime before tests |
| `LOCAL_RUNTIME_URL` | `http://localhost:8080` | Local test runtime URL |
| `SKIP_EVENT_CHECK` | `false` | Skip event spine verification |
| `EVENT_CHECK_REQUIRED` | `false` | Fail if event check fails |
| `SECONDARY_AUTH_URL` | `$MCP_BASE_URL/mcp/v1/memory/search` | Secondary endpoint URL |
| `SECONDARY_AUTH_PAYLOAD` | `{"query":"smoke test identity","limit":1}` | Secondary endpoint payload |
| `PROOF_DIR` | (auto-detected) | Force specific proof directory |
| `MCP_AVAILABLE` | not set | Set to `true` for pytest MCP tests |
| `DEBUG` | `false` | Enable debug output |

## Expected Proof Bundle

After successful auth bootstrap, the proof bundle should contain:

### Required Files
- `core.json` - Core proof metadata (proof_type=auth_bootstrap)
- `event_chain.json` - Event chain with correlation_id
- `identity_context.json` - Server-sourced identity (source=server/whoami)
- `verification_result.json` - Verification confirmation

### Optional Files
- `request.json` - Original auth request
- `response.json` - Auth response
- `correlation.json` - Correlation tracking
- `summary.md` - Human-readable summary
- `digest.txt` - Content digest

## Security Checks

The tests verify:
- Credentials file has 600 permissions
- No token leakage in proof bundle
- Consistent correlation_id across artifacts

## Exit Codes

- `0` - All checks passed
- `1` - One or more checks failed

### Proof
- [ ] Proof bundle directory exists
- [ ] Required files exist
- [ ] No secret leakage
- [ ] `identity_context.source == "server/whoami"`

## CI Integration

The pytest version is designed for CI:

```yaml
# Example GitHub Actions
- name: Run SDK Smoke Test
  run: |
    pytest tests/smoke/test_sdk_client_01_auth_bootstrap.py -v --tb=short
  env:
    MCP_BASE_URL: ${{ secrets.MCP_BASE_URL }}
    SKIP_DOCKER: "true"  # Use external runtime
```

## Troubleshooting

### "keyhole CLI not found"
Install the CLI: `pip install -e packages/python/keyhole-cli`

### "Login failed: device flow timeout"
Device flow requires user interaction. For automated testing, pre-authenticate or use a service account.

### "MCP /whoami returned 401"
Token may be expired or invalid. Re-run login.

### "Proof bundle not found"
Ensure the CLI version supports proof generation (SDK-CLIENT-01+).

## Related

- [HARDENING_REPORT.md](../../docs/evidence/sdk-client-01/HARDENING_REPORT.md) — Client hardening details
- [auth-bootstrap.md](../../docs/auth-bootstrap.md) — Auth bootstrap specification
- [bridge-smoke-test](../../examples/bridge-smoke-test/) — Bridge smoke test example
