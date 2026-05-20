# SDK-CLIENT-29 — Consume MCP Actor Envelope and Prove Client Auth Parity

**Status:** Implemented (client repo only — `keyhole-SDK`).
**Branch:** `sdk-client-29-actor-envelope-consumption`
**Scope:** SDK + CLI changes. **No** server, Keycloak, or Event Spine changes.

---

## What was implemented

1. **Actor envelope DTOs** (`keyhole_sdk.auth_bootstrap.actor_envelope`)
   - `HumanPrincipal`, `ActingPrincipal`, `Delegation`, `Authorization`,
     `ActorEnvelope`. All Pydantic v2 with `extra="allow"` for
     forward-compatibility. DTOs only — no authorization logic.

2. **`WhoamiResponse.actor_envelope`** (Optional)
   - Backward-compatible: pre-SDK-SERVER-29 servers (no envelope) parse
     without error.

3. **Envelope unwrapping** (`keyhole_sdk.envelope.unwrap_identity`)
   - Propagates `actor_envelope` from nested whoami payloads through to
     the flat dict consumed by `WhoamiResponse.model_validate()`.

4. **`keyhole whoami --show-envelope`**
   - Renders the server-resolved envelope (Human Principal / Acting
     Principal / Delegation / Authorization). Adds the
     `actor_envelope_present` flag to JSON output. Warns when the server
     returns no envelope.

5. **`keyhole login` post-login verification**
   - `LoginResult.whoami` is checked for `actor_envelope`. Success result
     surfaces `actor_envelope_present` and emits a `actor_envelope_missing`
     warning when the server has not yet been promoted to SDK-SERVER-29.

6. **`keyhole auth doctor`** (new)
   - Runs the eleven checks specified in the story (credential file,
     token-not-expired, JWT-issuer-realm, JWT-azp, no-direct-kh-prod
     token, whoami reachable, envelope present, human realm == kh-prod,
     acting realm == keyhole-mcp, acting client_id == keyhole-cli,
     write-idempotency-headers registered).
   - JWT inspection is **diagnostic only**. Server `/whoami` is the sole
     authority for actor truth.

7. **Write idempotency headers (carry-over)**
   - SDK-CLIENT-15 transport behavior verified intact: every
     `WRITE_IDEMPOTENT_REQUIRED` operation auto-injects `X-Request-Id`
     and `X-Idempotency-Key` via `GovernedTransport.execute()`. No
     regression.

## Constraints observed

- SDK auth defaults were already correct (`keyhole-mcp` realm, `keyhole-cli`
  client, `https://auth.keyholesolution.com/realms/keyhole-mcp` issuer).
  **No realm change made.**
- No JWT decoding is used as authority. JWT inspection is diagnostic only.
- Client never fabricates actor identity — the envelope is only ever
  populated from server responses.
- No server-side, Keycloak, or Event Spine changes.

## Evidence files

| File | Purpose |
|------|---------|
| `unit_test_report.txt` | pytest output: 19/19 passed |
| `whoami_actor_envelope.json` | Sample whoami response shape (redacted) |
| `login_device_flow_result.json` | Sample login success result (redacted) |
| `auth_doctor_output.txt` | Sample `keyhole auth doctor` human output |
| `idempotency_header_test.json` | Carry-over verification of SDK-CLIENT-15 |
| `redaction_check.json` | Confirms no token leaks in CLI output |

## Test results

```
tests/unit/test_sdk_client_29_actor_envelope.py ........... 19 passed in 0.93s
```

Pre-existing failures in `test_sdk_client_01_auth_bootstrap.py` (Windows
file-permission tests, PKCE challenge edge case) are **unchanged** by
SDK-CLIENT-29 — confirmed via `git stash` baseline run.

## Files changed

- `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/actor_envelope.py` (new)
- `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/__init__.py`
- `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/models.py`
- `packages/python/keyhole-sdk/keyhole_sdk/envelope.py`
- `packages/python/keyhole-cli/keyhole_cli/commands/whoami.py`
- `packages/python/keyhole-cli/keyhole_cli/commands/login.py`
- `packages/python/keyhole-cli/keyhole_cli/commands/auth_doctor.py` (new)
- `packages/python/keyhole-cli/keyhole_cli/cli.py`
- `tests/unit/test_sdk_client_29_actor_envelope.py` (new)
