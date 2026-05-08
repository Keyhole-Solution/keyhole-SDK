# Remediation Handoff — Auth Realm Mismatch (CLI vs MCP Server)

**Date:** 2026-04-29  
**Raised by:** SDK-CLIENT team  
**Severity:** BLOCKER — CLI login is broken; no write-bearing CLI operations possible  
**Status:** Awaiting server-side remediation  

---

## 1. Executive Summary

The CLI (`keyhole login`) and the VS Code / MCP integration use **different Keycloak realms and different grant types**. Users are provisioned through the `kh-prod` realm via VS Code, then blocked from authenticating via the CLI because the CLI targets a separate `keyhole-mcp` realm where their accounts do not exist.

No write-bearing CLI operations (`intent.submit`, `gaps.claim`, `gaps.evidence`, `gaps.submit`) can succeed until this is resolved.

---

## 2. Observed Discrepancy

### MCP Server / VS Code integration (working)

```
GET https://auth.keyholesolution.com/realms/kh-prod/login-actions/authenticate
    ?execution=87dead2a-ce23-48c9-a176-ba257f5183b3
    &client_id=vscode-copilot-bridge
```

| Field | Value |
|---|---|
| Realm | `kh-prod` |
| Client ID | `vscode-copilot-bridge` |
| Flow | Passwordless — 6-digit code delivered to user email |
| User provisioning | Occurs in this realm via VS Code OIDC bridge |

### CLI — `keyhole login` (broken)

```
GET https://auth.keyholesolution.com/realms/keyhole-mcp/protocol/openid-connect/auth
    ?response_type=code
    &client_id=keyhole-cli
    &redirect_uri=http%3A%2F%2Flocalhost%3A9876%2Fcallback
    &scope=openid+profile+email
    &state=<random>
    &code_challenge=<S256>
    &code_challenge_method=S256
```

| Field | Value |
|---|---|
| Realm | `keyhole-mcp` |
| Client ID | `keyhole-cli` |
| Flow | PKCE Authorization Code — opens browser, redirects to `localhost:9876` |
| Grant type | `authorization_code` + `code_challenge_method=S256` |
| User accounts | **Do not exist here** — users were provisioned in `kh-prod` |

### Root Cause

Keycloak realms are fully isolated identity domains. A user account created in `kh-prod` cannot authenticate to `keyhole-mcp` without explicit identity federation. There is no federation configured between these two realms. The CLI therefore fails with "invalid credentials" or "user not found" for every user provisioned through VS Code.

Secondary issue: the CLI is using PKCE (browser redirect to `localhost:9876`), which is wrong for a developer CLI. The SDK already implements Device Authorization Grant (RFC 8628) in `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/device.py`. Device flow is the correct mechanism for the CLI — no browser, no localhost server needed.

---

## 3. Required Server-Side Changes

### Option A — RECOMMENDED: Enable `keyhole-cli` in the `kh-prod` realm with Device Authorization Grant

This is the minimal-change path. Users already live in `kh-prod`. Configure the CLI client there.

**Actions for the server team:**

1. **Create `keyhole-cli` client in the `kh-prod` realm**
   - Client ID: `keyhole-cli`
   - Client type: `public` (no client secret — matches current SDK posture)
   - Standard flow: enabled
   - Device authorization grant: **enabled**
   - Direct access grants: disabled (do not enable ROPC in production)
   - Implicit flow: disabled
   - Redirect URIs: none required for device flow; add `http://localhost:9876/callback` only if PKCE fallback is retained

2. **Configure allowed scopes for `keyhole-cli`**  
   The SDK requests `openid profile email`. The cohort binding currently grants:
   ```
   connection:read, context:compile, gaps:claim, gaps:evidence,
   gaps:read, gaps:submit, intent:submit
   ```
   Map these scopes on the `keyhole-cli` client in `kh-prod` so the issued token carries the same claims as the VS Code bridge token.

3. **Verify `device_authorization_endpoint` is present in the OIDC discovery document**
   ```
   GET https://auth.keyholesolution.com/realms/kh-prod/.well-known/openid-configuration
   ```
   The response must contain `device_authorization_endpoint`. The SDK's `DeviceFlow` class discovers it from this document.

4. **Verify `grant_types_supported` includes `urn:ietf:params:oauth:grant-type:device_code`**  
   The SDK submits exactly this grant type in the token exchange.

---

### Option B — ALTERNATIVE: Federate `keyhole-mcp` realm with `kh-prod` via Keycloak Identity Provider

If the `keyhole-mcp` realm must remain the target for CLI auth, add a Keycloak Identity Provider (IdP) broker:

- Add `kh-prod` as an OIDC Identity Provider inside `keyhole-mcp`
- Enable "first login" flow to auto-create federated accounts in `keyhole-mcp` on first CLI login
- Ensure the federated token carries the same `user_id`, `tenant_id`, `org_id` claims as the `kh-prod` token (the SDK validates these against the `whoami` response)

**Risk:** This adds a federation hop and increases token complexity. Option A is simpler and avoids cross-realm token translation.

---

## 4. Required SDK / CLI Changes (post server remediation)

Once the server team confirms which option is implemented, the SDK team will apply exactly one change:

### If Option A (recommended):

Update `packages/python/keyhole-sdk/keyhole_sdk/config.py`:

```python
# Before
DEFAULT_AUTH_SERVER: str = os.environ.get(
    "KEYHOLE_AUTH_SERVER", "https://auth.keyholesolution.com/realms/keyhole-mcp"
)
DEFAULT_REALM: str = os.environ.get("KEYHOLE_REALM", "keyhole-mcp")

# After
DEFAULT_AUTH_SERVER: str = os.environ.get(
    "KEYHOLE_AUTH_SERVER", "https://auth.keyholesolution.com/realms/kh-prod"
)
DEFAULT_REALM: str = os.environ.get("KEYHOLE_REALM", "kh-prod")
```

Update the default flow in `keyhole_cli/commands/login.py` from `"pkce"` to `"device"`:

```python
# Before
def run_login(*, flow: str = "pkce", ...):

# After
def run_login(*, flow: str = "device", ...):
```

No other SDK code changes are required. The Device Authorization Grant is fully implemented in `keyhole_sdk/auth_bootstrap/device.py` and wired through `AuthBootstrapClient`. It discovers endpoints via OIDC `.well-known` automatically — it will pick up the `kh-prod` endpoints as soon as the `DEFAULT_AUTH_SERVER` is updated.

### If Option B (federation):

No SDK changes needed. The realm URL and client ID remain as-is. The IdP broker handles federation transparently.

---

## 5. Verification Protocol

After server remediation, the SDK team will verify with:

```bash
# 1. Confirm OIDC discovery includes device_authorization_endpoint
curl https://auth.keyholesolution.com/realms/kh-prod/.well-known/openid-configuration \
  | python -m json.tool | grep device

# 2. Confirm CLI device flow initiates correctly
keyhole login --flow device --json

# Expected output:
# {
#   "verification_uri_complete": "https://auth.keyholesolution.com/...",
#   "user_code": "XXXX-XXXX",
#   ...
# }

# 3. Complete auth in browser at the verification_uri_complete URL

# 4. Confirm identity resolves correctly
keyhole whoami --json
# Expected: user_id, tenant_id, org_id matching MCP /mcp/v1/whoami

# 5. Confirm write-bearing run succeeds
keyhole run --run-type intent.submit --input context/requests/intent-declare-greet-v1.json
```

---

## 6. Impact While Blocked

The following CLI operations are **completely blocked** until this is resolved:

| Operation | CLI Command | Blocked Because |
|---|---|---|
| Intent submission | `keyhole run --run-type intent.submit` | Requires auth token; login fails |
| Gap claim | `keyhole run --run-type gaps.claim` | Same |
| Evidence submission | `keyhole run --run-type gaps.submit` | Same |
| Whoami verification | `keyhole whoami` | Returns "not authenticated" |

**MCP tool-based operations are unaffected** — VS Code MCP integration authenticates independently via `kh-prod` / `vscode-copilot-bridge` and is working correctly.

---

## 7. No SDK Workarounds Permitted

The SDK boundary posture prohibits:

- bypassing auth to submit write-bearing operations
- faking or stubbing identity for governed runs
- using a different user's cached credentials
- direct HTTP calls that skip `X-Idempotency-Key` injection

The CLI must authenticate as the governed participant before any write-bearing operation. There is no safe workaround while the realm mismatch exists.

---

## 8. Server Team Contact Points

**Action required from server team:**

1. Confirm which remediation option (A or B) will be implemented
2. Confirm timeline
3. Notify SDK team when `device_authorization_endpoint` is live in the target realm
4. Provide the correct `client_id` value to use if different from `keyhole-cli`

**SDK team point of contact for coordination:** SDK-CLIENT working group.

---

## 9. References

| Item | Location |
|---|---|
| SDK auth client | `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/client.py` |
| Device Authorization Grant impl | `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/device.py` |
| PKCE impl | `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/pkce.py` |
| SDK config defaults | `packages/python/keyhole-sdk/keyhole_sdk/config.py` |
| CLI login command | `packages/python/keyhole-cli/keyhole_cli/commands/login.py` |
| SDK-CLIENT-25 device flow | `packages/python/keyhole-sdk/keyhole_sdk/sdk_client_25/device_flow.py` |
| Auth bootstrap docs | `docs/auth-bootstrap.md` |
| Boundary constitution | `docs/boundary-constitution.md` |
