# sdk-client-01-b.md

## SDK-CLIENT-01-B — Logout, Profile Listing, Profile Switching, and Token Lifecycle

**Status:** NOT STARTED
**Owner / Author:** Keyhole Solution Foundation
**Lane:** Dev (design + validation), Prod (promotion only)
**Depends on:** SDK-CLIENT-01, SDK-CLIENT-01-A
**Required by:** SDK-CLIENT-01-C (MCP Host Identity Reconciliation)
**Purpose:** Define the client-side lifecycle for session termination, profile inventory, profile switching, and token management so that a builder can safely transition between identities, environments, and realms without leaving stale credentials in host environments or breaking governed continuity.

---

## 1. Goal

Close the identity lifecycle gap between initial login (SDK-CLIENT-01) and long-lived host reconciliation (SDK-CLIENT-01-C).

After this story:

- `keyhole logout` terminates the active session cleanly and revokes the refresh token at the server boundary
- `keyhole profile list` shows all stored credential profiles on the local machine
- `keyhole profile switch` changes the active profile and signals affected hosts to reconcile
- token expiry is handled transparently (silent refresh) or surfaced clearly (hard expiry requiring re-login)
- stale tokens are never silently reused — the client detects expiry and either refreshes or prompts

---

## 2. Problem Statement

SDK-CLIENT-01 establishes login. SDK-CLIENT-01-A hardens it.

Neither story covers:

- what happens when the user explicitly terminates their session
- how to manage multiple profiles (e.g. paul@keyholesolution.com vs a CI service account)
- how to switch the active profile safely
- how token expiry and refresh interact with the credential store
- what signals should be sent to installed MCP hosts when the active identity changes

Without this story, SDK-CLIENT-01-C's host reconciliation has no clean profile source to compare against. Hosts may continue operating under a stale or different identity after the user logs out or switches profile.

---

## 3. Scope

### 3.1 In scope

- `keyhole logout` command: local credential removal + server-side token revocation
- `keyhole profile list` command: show all locally stored credential profiles
- `keyhole profile switch --profile <name>` command: change active profile
- Silent token refresh via stored `refresh_token` (reuse `token_refresh.get_fresh_token()` from SDK)
- Hard expiry path: detect expired token with no valid refresh token → prompt to re-login
- Credential store multi-profile format (`~/.keyhole/credentials.json` extended or `~/.keyhole/profiles/`)
- Post-switch host notification signal (consumed by SDK-CLIENT-01-C)

### 3.2 Out of scope

- MCP host rebind (owned by SDK-CLIENT-01-C)
- Server-side session management (owned by SDK-SERVER-01-B)
- SSO / federated identity (future)

---

## 4. CLI Surface

```text
keyhole logout                         # revoke token, clear local credentials
keyhole logout --all                   # clear all profiles

keyhole profile list                   # show all stored profiles
keyhole profile switch --profile paul  # switch active profile
keyhole profile current                # show current active profile
```

---

## 5. Invariants

| ID | Invariant |
|----|-----------|
| INV-SDK-CLIENT-01-B-001 | `keyhole logout` must revoke the refresh token at the server boundary before clearing local credentials. Local-only clearing is not a valid logout. |
| INV-SDK-CLIENT-01-B-002 | Profile switch must not silently carry the old token into the new context. Token refresh uses only the credentials of the selected profile. |
| INV-SDK-CLIENT-01-B-003 | Hard expiry (no valid refresh token) must surface clearly and direct the user to `keyhole login`. Silent failure is not acceptable. |
| INV-SDK-CLIENT-01-B-004 | Multiple profiles must never cross-contaminate. Active profile context is explicit, not inferred. |
| INV-SDK-CLIENT-01-B-005 | The `profile switch` command must emit a local signal that host reconciliation (SDK-CLIENT-01-C) can detect. |

---

## 6. Evidence Requirements

- Unit tests: `tests/unit/test_sdk_client_01b_session_lifecycle.py`
- Coverage: logout flow, profile list, profile switch, token expiry handling, multi-profile isolation
- Smoke test: `keyhole logout` → `keyhole whoami` → returns "not authenticated" → `keyhole login` restores session

---

## 7. Dependencies

### Depends on
- SDK-CLIENT-01 — login bootstrap
- SDK-CLIENT-01-A — hardened identity conformance

### Required by
- SDK-CLIENT-01-C — host identity reconciliation uses profile switch signals
- SDK-CLIENT-01-D — host credential installation checks active profile
