# SDK Client Auth Realm Drift — Evidence Package

**Title:** SDK Client Auth Realm Drift Evidence Pack  
**Owner:** Keyhole Solution Foundation  
**Date:** 2026-05-15  
**Scope:** keyhole-SDK client-side auth audit evidence for server-side auth convergence  
**Status:** Evidence collection only — no SDK mutation has been applied  
**Prepared by:** SDK Client Agent (GitHub Copilot / Claude Sonnet 4.6)

---

## Executive Summary

The SDK client currently has split auth behavior. The VS Code MCP integration
authenticates `paul@keyholesolution.com` correctly through `kh-prod` via the
`vscode-copilot-bridge` client. However, the SDK CLI PKCE and device flows
resolve their issuer through `DEFAULT_AUTH_SERVER`, which is currently
hardcoded to `https://auth.keyholesolution.com/realms/keyhole-mcp` — a realm
where user accounts do not exist.

This evidence package captures the full proof of the split and provides the
exact server-side requirements and client-side patch for convergence.

---

## Evidence Index

| File | Contents |
|---|---|
| `whoami-mcp.json` | Live MCP identity from VS Code surface (sanitized) |
| `sdk-config-current.txt` | Exact SDK defaults from config.py |
| `cli-login-current.txt` | CLI login command realm defaults |
| `auth-bootstrap-client-current.txt` | AuthBootstrapClient flow dispatch proof |
| `passwordless-current.txt` | Passwordless flow realm alignment proof |
| `auth-realm-mismatch-doc-excerpt.txt` | Prior remediation document excerpt |
| `env-keyhole-current.txt` | Environment variable state (all unset) |
| `oidc-keyhole-mcp.json` | Full OIDC discovery for keyhole-mcp realm |
| `oidc-kh-prod.json` | Full OIDC discovery for kh-prod realm |
| `pkce-device-repro-redacted.txt` | Issuer binding repro (no tokens) |
| `proposed-client-patch.diff` | Proposed SDK patch (NOT applied) |
| `MANIFEST.sha256` | SHA-256 hashes of all evidence files |

---

## Evidence 1 — Live MCP Identity

**Source:** `whoami-mcp.json`  
**Tool:** `mcp_keyhole_keyhole_whoami` via VS Code MCP SSE transport  
**Captured:** 2026-05-15  

| Field | Value |
|---|---|
| `active_user` | `paul@keyholesolution.com` |
| `auth_channel` | `mcp` |
| `surface` | `vscode-copilot` |
| `lane` | `prod` |
| `auth_class` | `authenticated` |
| `realm_inferred_or_documented` | `kh-prod` |
| `client_inferred_or_documented` | `vscode-copilot-bridge` |

**Conclusion:** Paul is the correct active user. VS Code initiated the
correct passwordless flow through `kh-prod`. There is no active-user
contamination issue. The MCP session is production-bound and authenticated.

---

## Evidence 2 — SDK Config Defaults

**Source:** `sdk-config-current.txt`  
**File:** `packages/python/keyhole-sdk/keyhole_sdk/config.py`

```python
DEFAULT_AUTH_SERVER: str = os.environ.get(
    "KEYHOLE_AUTH_SERVER", "https://auth.keyholesolution.com/realms/keyhole-mcp"
)
DEFAULT_REALM: str = os.environ.get("KEYHOLE_REALM", "keyhole-mcp")
DEFAULT_CLIENT_ID: str = os.environ.get("KEYHOLE_CLIENT_ID", "keyhole-cli")
```

**Conclusion:** The CLI PKCE/device base issuer is currently realm-bound through
`DEFAULT_AUTH_SERVER`. Even if `KEYHOLE_REALM=kh-prod` is set as an environment
variable, PKCE and device flows still resolve to `keyhole-mcp` unless
`KEYHOLE_AUTH_SERVER` itself is overridden. The two variables are independent.

---

## Evidence 3 — CLI Login Defaults

**Source:** `cli-login-current.txt`  
**Files:** `cli.py`, `commands/login.py`

```python
# cli.py — login option
realm: str = typer.Option("kh-prod", "--realm", envvar="KEYHOLE_REALM", ...)

# commands/login.py — run_login()
def run_login(*, ..., auth_server_url: str = DEFAULT_AUTH_SERVER, realm: str = "kh-prod", ...)
```

**Conclusion:** The CLI command surface intends `kh-prod`, but that intent
does not control PKCE/device issuer selection. Those flows use `auth_server_url`
directly and ignore the `realm` parameter at flow dispatch time.

---

## Evidence 4 — AuthBootstrapClient Flow Dispatch

**Source:** `auth-bootstrap-client-current.txt`  
**File:** `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/client.py`

```python
# Constructor — realm not used in PKCE/device construction
self._pkce_flow    = PKCEFlow(auth_server_url=auth_server_url, client_id=client_id, ...)
self._device_flow  = DeviceFlow(auth_server_url=auth_server_url, client_id=client_id, ...)
self._passwordless_flow = PasswordlessFlow(mcp_base_url=mcp_base_url)  # no auth_server_url

# login() dispatch — realm only forwarded to passwordless
if flow_type == AuthFlowType.PKCE:
    token_response = self._do_pkce_flow(...)           # realm NOT passed
elif flow_type == AuthFlowType.PASSWORDLESS:
    token_response = self._do_passwordless_flow(..., realm=realm, ...)  # realm passed
else:  # DEVICE
    token_response = self._do_device_flow(...)         # realm NOT passed
```

**Conclusion:** The realm parameter is flow-specific:
- **passwordless:** realm-aware — forwarded to MCP boundary
- **PKCE:** auth_server_url-bound — realm is ignored
- **device:** auth_server_url-bound — realm is ignored

---

## Evidence 5 — Passwordless Flow Alignment

**Source:** `passwordless-current.txt`  
**File:** `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/passwordless.py`

```python
def request_code(self, email: str, realm: str = "kh-prod", ...) -> PasswordlessLoginResponse:
    url = f"{self._base_url}/auth/login-request"
    payload = {"email": email, "realm": realm}   # realm sent in request body
```

**Conclusion:** Passwordless already sends the requested realm to the MCP
boundary and is aligned with `kh-prod` intent. The auth split is isolated
to PKCE/device issuer binding only.

---

## Evidence 6 — Prior Remediation Document

**Source:** `auth-realm-mismatch-doc-excerpt.txt`  
**File:** `docs/remediation/auth-realm-mismatch-2026-04-29.md`

- **Date of original report:** 2026-04-29
- **Severity:** BLOCKER
- **Status at time of report:** Awaiting server-side remediation
- **VS Code realm/client confirmed:** `kh-prod` / `vscode-copilot-bridge`
- **Recommended option:** Create `keyhole-cli` client in `kh-prod` with Device Authorization Grant

**Conclusion (2026-05-15 audit):** The current evidence collection confirms
the previously documented remediation path. No server-side or client-side
changes have been applied since 2026-04-29. Status remains open.

---

## Evidence 7 — Environment Variable State

**Source:** `env-keyhole-current.txt`

```
KEYHOLE_AUTH_SERVER= [not set]
KEYHOLE_REALM=       [not set]
KEYHOLE_MCP_URL=     [not set]
KEYHOLE_CLIENT_ID=   [not set]
KEYHOLE_HOME=        [not set]
```

**Conclusion:** No environment-level workaround is deployed. All PKCE and
device flows run against `keyhole-mcp` defaults. Setting `KEYHOLE_REALM=kh-prod`
alone would not fix the issue — `KEYHOLE_AUTH_SERVER` must also be set.

---

## Evidence 8 — OIDC Discovery (Both Realms)

**Sources:** `oidc-keyhole-mcp.json`, `oidc-kh-prod.json`  
**Captured:** 2026-05-15 (live fetch)

### keyhole-mcp

| Field | Value |
|---|---|
| `issuer` | `https://auth.keyholesolution.com/realms/keyhole-mcp` |
| `authorization_endpoint` | `.../keyhole-mcp/protocol/openid-connect/auth` |
| `token_endpoint` | `.../keyhole-mcp/protocol/openid-connect/token` |
| `device_authorization_endpoint` | `.../keyhole-mcp/protocol/openid-connect/auth/device` ✓ |
| `code_challenge_methods_supported` | `["plain", "S256"]` ✓ |
| `grant_types_supported` | includes `urn:ietf:params:oauth:grant-type:device_code` ✓ |
| `scopes_supported` | `openid, builder, offline_access, roles, cohort-worker-claims, service_account, profile, runtime:read, runtime:write, email` |

### kh-prod

| Field | Value |
|---|---|
| `issuer` | `https://auth.keyholesolution.com/realms/kh-prod` |
| `authorization_endpoint` | `.../kh-prod/protocol/openid-connect/auth` |
| `token_endpoint` | `.../kh-prod/protocol/openid-connect/token` |
| `device_authorization_endpoint` | `.../kh-prod/protocol/openid-connect/auth/device` ✓ |
| `code_challenge_methods_supported` | `["plain", "S256"]` ✓ |
| `grant_types_supported` | includes `urn:ietf:params:oauth:grant-type:device_code` ✓ |
| `scopes_supported` | `openid, service_account, microprofile-jwt, web-origins, email, roles, basic, address, profile, phone, organization, acr, offline_access` |

**Conclusion:** `kh-prod` exposes `device_authorization_endpoint` and supports
`urn:ietf:params:oauth:grant-type:device_code` at the realm level. PKCE S256 is
supported. However, per-client grant enablement (for `keyhole-cli`) must be
confirmed by the server backend. The realm-level support does not guarantee
that a specific Keycloak client has the grant enabled.

**Scope delta (action required):** `kh-prod` currently lacks: `builder`,
`cohort-worker-claims`, `runtime:read`, `runtime:write`. These scopes are
present in `keyhole-mcp`. The server backend must ensure the scopes required
by the CLI are available to `keyhole-cli` in `kh-prod`, even if via
client-level scope mapping rather than top-level realm scopes.

---

## Evidence 9 — PKCE/Device Repro (Redacted)

**Source:** `pkce-device-repro-redacted.txt`

| Field | Value |
|---|---|
| Command | `keyhole login` (default: `--flow pkce`) |
| Resolved `auth_server_url` | `https://auth.keyholesolution.com/realms/keyhole-mcp` |
| Resolved realm param | `kh-prod` (passed but ignored by PKCE/device) |
| Observed issuer/realm | `keyhole-mcp` |
| Expected future issuer | `https://auth.keyholesolution.com/realms/kh-prod` |
| Result | FAIL — user not found in keyhole-mcp |

No actual auth flow was initiated. No tokens appear in this evidence file.

---

## Evidence 10 — Proposed Client Patch (Not Applied)

**Source:** `proposed-client-patch.diff`

```diff
-    "KEYHOLE_AUTH_SERVER", "https://auth.keyholesolution.com/realms/keyhole-mcp"
+    "KEYHOLE_AUTH_SERVER", "https://auth.keyholesolution.com/realms/kh-prod"
 )
-DEFAULT_REALM: str = os.environ.get("KEYHOLE_REALM", "keyhole-mcp")
+DEFAULT_REALM: str = os.environ.get("KEYHOLE_REALM", "kh-prod")
```

**Status:** NOT APPLIED. Must not be applied until server backend returns proof
of `keyhole-cli` client existence and readiness in `kh-prod`.

---

## Server Backend Agent Handoff

**Finding:**  
The SDK client currently has split auth behavior. VS Code MCP is correctly
authenticated as `paul@keyholesolution.com` through `kh-prod`, but SDK CLI
PKCE/device flows still resolve their issuer through `DEFAULT_AUTH_SERVER`,
which is currently hardcoded to
`https://auth.keyholesolution.com/realms/keyhole-mcp`.

**Confirmed:**
- `paul@keyholesolution.com` is the correct active MCP user.
- VS Code initiated the correct passwordless Device Code flow.
- The active MCP surface is authenticated and production-bound.
- CLI login defaults intend `kh-prod`.
- Passwordless flow is `kh-prod`-aware through the `realm` parameter.
- PKCE/device flows ignore the `realm` parameter and depend on `auth_server_url`.
- Current `DEFAULT_AUTH_SERVER` embeds `keyhole-mcp`.
- Therefore PKCE/device remain on `keyhole-mcp` until server-side `kh-prod`
  support is proven and the SDK default is flipped.
- `kh-prod` realm exposes `device_authorization_endpoint` and `device_code` grant
  at the realm level — but per-client enablement for `keyhole-cli` is unconfirmed.
- `kh-prod` currently lacks `builder`, `cohort-worker-claims`, `runtime:read`,
  `runtime:write` scopes that `keyhole-mcp` exposes.

**Server-side remediation requested:**
1. Create or verify public client `keyhole-cli` in `kh-prod`.
2. Enable Authorization Code + PKCE S256 for `keyhole-cli` in `kh-prod`.
3. Enable Device Authorization Grant for `keyhole-cli` in `kh-prod`.
4. Map required scopes to `keyhole-cli` in `kh-prod`:
   `connection:read`, `context:compile`, `gaps:claim`, `gaps:evidence`,
   `gaps:read`, `gaps:submit`, `intent:submit` (mirror VS Code bridge grants).
5. Confirm `kh-prod` OIDC discovery exposes required endpoints (done — see above).
6. Confirm issuer is `https://auth.keyholesolution.com/realms/kh-prod`.
7. Confirm MCP `/mcp/v1/whoami` accepts `kh-prod` human tokens from `keyhole-cli`.
8. Confirm `whoami` resolves `paul@keyholesolution.com` to the correct
   `tenant_id`, `org_id`, cohort, and worker context.
9. Return proof artifacts authorizing the SDK client default flip.

**Client-side change to authorize only after server proof:**
- `DEFAULT_AUTH_SERVER` → `https://auth.keyholesolution.com/realms/kh-prod`
- `DEFAULT_REALM` → `kh-prod`

**No SDK mutation has been applied by this evidence package.**
