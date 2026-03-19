# DEV-SDK-01 — Client Hardening for Server-Aligned Identity Governance

**Story:** DEV-SDK-01 / sdk-client-01  
**Type:** Hardening pass — behavior tightening, proof alignment, contract compliance  
**Test Result:** 106/106 passed (0.35s) — 85 original + 21 new hardening tests  
**Regressions:** None (1108 tests passing across full suite; 26 pre-existing failures in unrelated module)

---

## What Changed

### 1. Credential Persistence Moved After /whoami (client.py)

**Before:** Credentials saved BEFORE calling /whoami. If /whoami failed, the store contained a session without governed identity confirmation.

**After:** Credentials are ONLY persisted after /whoami succeeds and identity is validated. If /whoami fails, the credential store remains empty. No provisional session reaches disk.

**Why:** Token receipt alone is not proof of governed identity. The server is the sole issuer of identity truth. Persisting before identity confirmation creates a state where the client has credentials but no server-confirmed identity — a floating execution risk.

### 2. Identity Completeness Validation (models.py, errors.py)

**Before:** `WhoamiResponse` accepted all-optional fields. No validation that the server returned the minimum required governed identity.

**After:** `WhoamiResponse.validate_required_identity()` checks that `user_id` and `mode` are present and non-empty. `IncompleteIdentityError` is raised with specific missing-field detail and repair guidance. Login fails deterministically when the server returns incomplete identity.

**Why:** The client must reject partial identity from the server rather than silently accepting an under-provisioned account.

### 3. Stable Correlation ID Through Lifecycle (client.py)

**Before:** No correlation_id parameter on `login()`. Correlation was only created at the CLI layer, disconnected from the client orchestrator.

**After:** `login()` accepts `correlation_id` (auto-generated if not provided). The same correlation_id is passed to /whoami as `X-Correlation-ID` header and returned in `LoginResult.correlation_id`. One ID anchors the entire auth lifecycle from initiation through proof closure.

**Why:** The zipper must prove all lifecycle steps belong to the same auth closure. Split correlation defeats replay and audit.

### 4. Identity Source Attribution (models.py, proof.py)

**Before:** Proof bundle did not indicate where identity came from. No explicit "this came from /whoami" marker.

**After:** `LoginResult.identity_source` is set to `"server/whoami"` on success. `identity_context.json` includes `"source": "server/whoami"`. `verification_result.json` includes `identity_source`, `governed_identity_confirmed`, `server_auth_event_confirmed`, and `mode_source`. Summary references "governed identity confirmed" instead of just "verification passed".

**Why:** Proof must be a trustworthy replay surface that makes provenance explicit. Anyone reading the proof should know identity came from the server, not from local inference.

### 5. Token Opacity Audit (all modules)

**Before/After:** No JWT decoding, claim extraction, or token content inspection was found anywhere in the codebase. Tokens are treated as opaque transport credentials throughout. No changes needed — a test was added to enforce this invariant going forward.

**Why:** The client must never derive identity, mode, or governance state from token internals. Tokens are transport credentials only.

---

## How the Client Now Aligns With Server Law

| Invariant | Implementation |
|-----------|---------------|
| Identity comes only from /whoami | `login()` calls `/mcp/v1/whoami` and uses server response as sole identity truth |
| Login success requires governed identity | Success returned ONLY when /whoami returns valid, complete identity |
| Tokens are opaque | No JWT decode, no claim extraction, no token parsing anywhere in auth_bootstrap |
| Mode is server-determined, client-read-only | `session.mode = whoami.mode` — always from server response |
| One lifecycle correlation ID | `correlation_id` parameter threaded from login() through /whoami and into LoginResult |
| Credentials persist only after identity | `credential_store.save()` moved AFTER /whoami + identity validation |
| Proof anchored in server truth | `identity_source`, `source`, `governed_identity_confirmed`, `mode_source` all from server |
| Failure after token exchange is real failure | /whoami failure → credential_persisted=False, success=False, store empty |

---

## Hardened Flow Ordering

```
keyhole login
→ auth challenge initiated
→ auth completed (PKCE or device)
→ provisional token/session received (NOT persisted)
→ /whoami called (with correlation_id header)
→ governed identity returned by server
→ identity validated (required fields present)
→ mode accepted from server (read-only)
→ credentials persisted (ONLY now)
→ proof bundle written from server truth
→ AUTH_SUCCESS confirmed in chain
→ login reported successful
```

If the chain breaks anywhere after token exchange, the user receives a deterministic failure with repair guidance, and the credential store remains empty.

---

## Tests Proving Alignment

### Hardening: Positive Behavior (5 tests)

| Test | What It Proves |
|------|---------------|
| `test_login_success_requires_whoami` | Login fails without /whoami; identity_source is "server/whoami" on success |
| `test_identity_matches_whoami_exactly` | Client identity fields match /whoami response exactly |
| `test_correlation_stable_through_lifecycle` | Single correlation_id passes from login() to /whoami header |
| `test_proof_uses_server_issued_identity_and_mode` | Proof bundle identity_context has source="server/whoami"; core.whoami_completed=True |
| `test_session_persistence_only_after_whoami` | Store is empty before login; filled only after /whoami success with server mode |

### Hardening: Negative Behavior (5 tests)

| Test | What It Proves |
|------|---------------|
| `test_token_success_whoami_fail_is_login_failure` | Token OK + /whoami fail → success=False, credential_persisted=False, store empty |
| `test_incomplete_identity_is_login_failure` | /whoami returns but missing user_id → error_class="incomplete_identity", not persisted |
| `test_session_not_persisted_when_whoami_fails` | Credential store confirmed empty after /whoami failure |
| `test_proof_not_marked_complete_without_server_confirmation` | governed_identity_confirmed=False, server_auth_event_confirmed=False when /whoami missing |
| `test_client_does_not_decode_token_for_identity` | Source code scan confirms no jwt/jose/decode anywhere in auth_bootstrap |

### Hardening: Security Behavior (3 tests)

| Test | What It Proves |
|------|---------------|
| `test_proof_still_excludes_secrets` | No token secrets in any proof artifact |
| `test_token_remains_opaque_in_session` | Token stored as raw opaque value, not decoded; safe_summary excludes it |
| `test_mode_shown_is_exactly_server_returned` | Mode in LoginResult, WhoamiResponse, and stored session all match server |

### Hardening: Correlation (3 tests)

| Test | What It Proves |
|------|---------------|
| `test_correlation_generated_if_not_provided` | Auto-generated when not supplied |
| `test_correlation_in_proof_matches_login` | Same ID in core.json, event_chain.json, correlation.json |
| `test_correlation_on_failure_still_present` | Present even when login fails |

### Hardening: Identity Validation (5 tests)

| Test | What It Proves |
|------|---------------|
| `test_validate_required_identity_complete` | Complete identity passes |
| `test_validate_required_identity_missing_user_id` | Missing user_id detected |
| `test_validate_required_identity_empty_user_id` | Whitespace-only user_id rejected |
| `test_incomplete_identity_error_has_repair` | Error carries repair guidance and missing field list |
| `test_incomplete_identity_inherits_from_base` | Proper error hierarchy maintained |

### Updated Original Test

| Test | Change |
|------|--------|
| `test_whoami_fails_after_login` | Changed assertion from `credential_persisted=True` to `credential_persisted=False`; added assertion that store is empty |

---

## Files Changed

| File | Change Type | Summary |
|------|------------|---------|
| `keyhole_sdk/auth_bootstrap/client.py` | **Modified** | Reordered: /whoami before save; added correlation_id, identity validation, identity_source |
| `keyhole_sdk/auth_bootstrap/models.py` | **Modified** | Added `validate_required_identity()`, `identity_source` and `correlation_id` on LoginResult |
| `keyhole_sdk/auth_bootstrap/errors.py` | **Modified** | Added `IncompleteIdentityError` with missing_fields detail |
| `keyhole_sdk/auth_bootstrap/whoami.py` | **Modified** | Added `correlation_id` parameter → `X-Correlation-ID` header |
| `keyhole_sdk/auth_bootstrap/proof.py` | **Modified** | Added source attribution, governed_identity_confirmed, server_auth_event_confirmed, mode_source |
| `keyhole_cli/commands/login.py` | **Modified** | Passes correlation_id to client.login(); updated docstring |
| `tests/unit/test_sdk_client_01_auth_bootstrap.py` | **Modified** | Fixed 1 test, added 21 new hardening tests across 5 new test classes |
