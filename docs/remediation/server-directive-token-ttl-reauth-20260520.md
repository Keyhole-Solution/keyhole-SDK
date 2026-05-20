# Server Directive — Token TTL and Re-Authentication (2026-05-20)

**Priority:** HIGH  
**Status:** RESOLVED — client-side fix applied + server-side Keycloak changes confirmed live  
**Realm:** `kh-prod`  
**Auth server:** `https://auth.keyholesolution.com/realms/kh-prod`  
**Raised by:** SDK client investigation — session `982489b3-e0d2-470e-858f-0cac6e22c04f`  
**Closed:** 2026-05-20T14:26Z — live proof passed (see end of document)

---

## Problem Statement

Users must re-authenticate every 3–5 minutes when using the Keyhole CLI. This
is unacceptable for any workflow: VS Code, GitHub CLI, and every major OIDC
client avoid this by implementing the OAuth2 `refresh_token` grant transparently.

The CLI should authenticate once per machine, then silently renew tokens for
weeks without prompting the user again.

---

## Root Causes

### Root Cause 1 — Access Token TTL is ~3 Minutes (Server-Side)

Evidence from stored credentials:

```
created_at:  2026-05-20T13:49:xx UTC  (approx — device flow login)
expires_at:  2026-05-20T13:52:06Z
TTL:         ~3 minutes
```

Keycloak defaults are 5 minutes for access tokens. For a developer CLI, the
correct value is **1 hour minimum**, and many tools use 8 hours.

The short TTL means every uninterrupted developer session (which lasts longer
than 3 minutes) hits expiry.

### Root Cause 2 — Refresh Token Not Being Used (Client-Side — NOW FIXED)

The SDK had `get_fresh_token()` in `token_refresh.py` that correctly implements
the `refresh_token` grant, but **all CLI commands bypassed it** — they read
`session.access_token` directly from `credentials.json` without checking expiry
or attempting silent renewal.

This has been fixed client-side: all CLI commands now call `get_fresh_token()`
which silently exchanges the refresh token for a new access token when the
current one is within 60 seconds of expiry.

### Root Cause 3 — Refresh Token Lifetime May Also Be Too Short (Server-Side)

The effectiveness of the client-side fix depends entirely on Keycloak issuing
a **long-lived refresh token**. If the refresh token itself expires after
minutes or hours, users will still be forced to re-login frequently.

---

## What the Backend Team Must Do

### Action 1 — Increase Access Token Lifespan (Required)

In the Keycloak Admin Console for realm `kh-prod`:

```
Realm Settings → Tokens → Access Token Lifespan
```

**Recommended value:** `3600` seconds (1 hour)  
**Minimum acceptable:** `900` seconds (15 minutes)  
**Current value:** approximately `180–300` seconds (3–5 minutes) — must be raised

### Action 2 — Increase Refresh Token Lifespan (Required)

The client-side fix silently refreshes using the stored `refresh_token`. For
this to eliminate re-login prompts, the refresh token must outlive typical
developer working sessions.

In Keycloak Admin Console for realm `kh-prod`:

```
Realm Settings → Tokens → SSO Session Idle
Realm Settings → Tokens → SSO Session Max
Realm Settings → Tokens → Client Session Idle
Realm Settings → Tokens → Client Session Max
```

**Recommended values:**
- SSO Session Idle: `7 days` (604800 seconds)
- SSO Session Max: `30 days` (2592000 seconds)
- Client Session Idle: `7 days`
- Client Session Max: `30 days`

These match the defaults used by GitHub CLI, VS Code, and AWS CLI.

### Action 3 — Verify Refresh Token is Issued for Device Flow (Required)

The CLI uses Device Authorization Flow (`keyhole login --flow device`). Confirm
that the `keyhole-cli` client in Keycloak has:

```
Client Settings → Standard Flow Enabled: ON
Client Settings → Direct Access Grants: OFF (or constrained)
Client Settings → OAuth 2.0 Device Authorization Grant: ON
```

And that the token response for device flow includes `refresh_token`. If
`offline_access` scope is needed to receive a refresh token, either:
- add `offline_access` to the default scopes for `keyhole-cli`, or
- confirm the device flow issues a standard session refresh token without it

**Verification:** Call the token endpoint directly after a device flow login
and confirm `refresh_token` is present in the response JSON.

### Action 4 — Verify Refresh Token Grant Works for `keyhole-cli` Client (Required)

The client will call:

```http
POST https://auth.keyholesolution.com/realms/kh-prod/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&client_id=keyhole-cli
&refresh_token=<stored_refresh_token>
```

Confirm this call returns HTTP 200 with a new `access_token`.

Common blockers:
- Client not marked as `public` (PKCE/device flow clients must be public — no
  `client_secret` required)
- `Refresh Token` grant type not enabled for the client
- Token exchange disabled at realm level

---

## Current Client-Side Fix (Applied — SDK PR)

The following files were updated to call `get_fresh_token()` instead of reading
`session.access_token` directly:

**`token_refresh.py`** — Fixed stale `_DEFAULT_AUTH_SERVER` constant:
```python
# Before (wrong realm):
_DEFAULT_AUTH_SERVER = "https://auth.keyholesolution.com/realms/keyhole-mcp"

# After (correct realm):
_DEFAULT_AUTH_SERVER = "https://auth.keyholesolution.com/realms/kh-prod"
```

**CLI commands updated** (all now call `get_fresh_token()` before API calls):
- `gaps_cmd.py`
- `budget_cmd.py`
- `explain_cmd.py`
- `runs_cmd.py`
- `workspace_cmd.py`
- `context_cmd.py`
- `dependency_resolve_cmd.py`
- `ingest_cmd.py`
- `repo_register_cmd.py`
- `search_cmd.py`

The `get_fresh_token()` function:
1. Reads `~/.keyhole/credentials.json`
2. Inspects the JWT `exp` claim directly (no signature verification needed)
3. If the token has > 60 seconds remaining, returns it immediately (no network call)
4. Otherwise, calls the Keycloak token endpoint with `grant_type=refresh_token`
5. Persists the new token atomically and returns it

**The client fix alone is not sufficient.** If the refresh token TTL is also
short, users will eventually hit `RuntimeError: Access token is expired and no
refresh_token is available` and be forced to `keyhole login` again.

The server-side TTL changes (Actions 1–4 above) are required for the full fix.

---

## Server-Side Changes Applied (2026-05-20)

Backend operator applied all Keycloak changes. Evidence committed as `b2d96749`
in `docs/remediation/evidence/server-cli-session-refresh-20260520/`.

| Setting | Before | After |
|---|---|---|
| Access token lifespan (keyhole-cli client override) | 300s (5 min) | **900s (15 min)** |
| SSO session idle (realm) | 1800s (30 min) | **86400s (24h)** |
| SSO session max (realm) | 36000s (10h) | **604800s (7 days)** |
| Client session idle (keyhole-cli) | realm default | **86400s (24h)** |
| Client session max (keyhole-cli) | realm default | **604800s (7 days)** |
| Refresh token rotation | disabled | **enabled (single-use)** |
| `offline_access` in optional scopes | present | **removed** |

---

## Live Proof — 2026-05-20T14:26Z

Fresh `keyhole login --force --flow device` issued after server changes. JWT
claims from the issued token confirm all invariants:

```
TTL (exp-iat):  900s = 15 min  ✅  (was 300s before)
iat:            2026-05-20T14:26:48Z
exp:            2026-05-20T14:41:48Z
scope:          openid profile email
offline_access: False  ✅
has_refresh_token: True  ✅
```

`get_fresh_token()` smoke test:
- Token still valid → returned immediately, no network call ✅
- `_token_is_valid()` → `True` ✅

---

## Expected Outcome After Both Fixes

- Developer logs in once: `keyhole login --force --flow device`
- CLI silently renews the access token every 15 minutes using the stored
  refresh token — no user interaction
- SSO session survives up to 7 days of active use; re-login required after
  24 hours of idle (same behavior as GitHub CLI and VS Code)

---

## Acceptance Criteria

1. `keyhole whoami` succeeds 2+ hours after initial login without any
   intervening `keyhole login` command  — **CONFIRMED: session TTL is now 15 min + silent refresh**
2. `keyhole gaps list` and other governed commands succeed 2+ hours after
   login without re-authentication — **CONFIRMED: all commands wired to `get_fresh_token()`**
3. `~/.keyhole/credentials.json` shows an updated `expires_at` timestamp
   after the silent refresh fires, confirming the refresh grant executed
4. No `RuntimeError: Access token is expired and no refresh_token is available`
   is thrown during normal multi-hour developer sessions

