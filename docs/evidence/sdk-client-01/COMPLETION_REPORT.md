# SDK-CLIENT-01 — Authentication Bootstrap (Client): Completion Report

**Story ID:** SDK-CLIENT-01 / sdk-client-01  
**Epic:** SDK-CLIENT — Governed Developer SDK, Onboarding, and Repository Ingestion  
**Story Type:** Client-side zipper story  
**Status:** COMPLETE — all acceptance criteria satisfied  
**Test Result:** 85/85 passed (0.52s)

---

## 1. Implementation Summary

This story implements the client-side authentication bootstrap flow enabling a
new builder to authenticate into the Keyhole ecosystem, persist credentials
locally, inspect governed identity context, and proceed into further SDK
workflows without manual configuration.

### Modules Delivered

| Module | Location | Purpose |
|--------|----------|---------|
| `models.py` | `keyhole_sdk/auth_bootstrap/` | Typed Pydantic models: AuthFlowType, AuthMode, AuthSession, PKCEChallenge, DeviceCodeResponse, TokenResponse, WhoamiResponse, LoginResult |
| `errors.py` | `keyhole_sdk/auth_bootstrap/` | Error hierarchy with deterministic repair guidance for 8 failure classes |
| `credential_store.py` | `keyhole_sdk/auth_bootstrap/` | Secure local credential persistence (`~/.keyhole/credentials.json`, 0600) |
| `pkce.py` | `keyhole_sdk/auth_bootstrap/` | PKCE (S256) browser-based OIDC flow with local callback server |
| `device.py` | `keyhole_sdk/auth_bootstrap/` | Device/constrained flow with polling and backoff |
| `whoami.py` | `keyhole_sdk/auth_bootstrap/` | WhoamiClient calling `GET /mcp/v1/whoami` |
| `client.py` | `keyhole_sdk/auth_bootstrap/` | AuthBootstrapClient orchestrating full login lifecycle |
| `proof.py` | `keyhole_sdk/auth_bootstrap/` | AuthProofBundle generating all proof artifacts |
| `login.py` | `keyhole_cli/commands/` | `keyhole login` CLI command |
| `whoami.py` | `keyhole_cli/commands/` | `keyhole whoami` CLI command |
| `cli.py` | `keyhole_cli/` | Modified — registered login and whoami commands |

---

## 2. Acceptance Criteria Mapping

### §15 Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | `keyhole login` can initiate a valid auth flow | ✅ | `AuthBootstrapClient.login()` dispatches PKCE or device flow; CLI `login` command wraps it. Tests: `TestAuthBootstrapClient::test_login_pkce_success`, `TestCLILogin::test_login_command_success` |
| 2 | Client supports PKCE and constrained/device flow | ✅ | `PKCEFlow` (S256 challenge, browser launch, callback server, code exchange) and `DeviceFlow` (device code request, poll with backoff). Tests: `TestPKCEFlow` (9 tests), `TestDeviceFlow` (5 tests) |
| 3 | Client receives usable token/session | ✅ | `TokenResponse` → `AuthSession` with `is_expired` check; session stored with fingerprint. Tests: `TestModels::test_auth_session_*` |
| 4 | Credentials written to secure local store | ✅ | `CredentialStore` writes to `~/.keyhole/credentials.json` with atomic rename, 0600 perms, 0700 dir. Tests: `TestCredentialStore` (12 tests) |
| 5 | No manual `.env` setup required | ✅ | `CredentialStore` auto-creates directory structure; no env file dependency anywhere. Tests: `TestCredentialStore::test_save_creates_directory` |
| 6 | `keyhole whoami` returns and renders correct identity context | ✅ | `WhoamiClient.verify()` calls `GET /mcp/v1/whoami`; CLI renders user_id, tenant, org, cohort, worker, workspace, plan, mode, limits. Tests: `TestWhoamiClient` (6 tests), `TestCLIWhoami` (5 tests) |
| 7 | `keyhole whoami` makes shadow vs real mode visible | ✅ | `AuthMode` enum (`shadow`/`real`) rendered explicitly in whoami output and proof. Tests: `TestModels::test_auth_mode_enum`, `TestCLIWhoami::test_whoami_shows_shadow_mode`, `TestIntegrationScenarios::test_shadow_mode_*` |
| 8 | Stored credentials usable for subsequent commands | ✅ | `CredentialStore.load()` returns `AuthSession` usable by any command; `is_authenticated()` gate. Tests: `TestCredentialStore::test_load_returns_session`, `TestIntegrationScenarios::test_credentials_usable_across_commands` |
| 9 | Client contributes proof artifacts sufficient for zipper | ✅ | `AuthProofBundle` generates core.json, request.json, response.json, event_chain.json, identity_context.json, verification_result.json, correlation.json, summary.md, digest.txt, extended/. Tests: `TestProofBundle` (12 tests) |
| 10 | Failure paths produce deterministic repair guidance | ✅ | 7 error classes each with `error_class`, `reason`, `repair_suggestions[]`. Tests: `TestErrors` (8 tests) |

---

## 3. Test Plan Coverage (§16)

### Positive Tests

| Test | Description | Test Functions |
|------|-------------|----------------|
| **A** — PKCE login success | Full browser flow → session → credential → whoami | `test_login_pkce_success`, `test_pkce_generate_challenge`, `test_pkce_exchange_code` |
| **B** — Device flow success | Constrained flow → poll → session → credential | `test_login_device_success`, `test_request_device_code`, `test_poll_for_token_success` |
| **C** — Token usable across commands | Auth → whoami → credential reuse | `test_credentials_usable_across_commands` |
| **D** — Shadow mode visible | Shadow mode rendered in whoami + proof | `test_shadow_mode_visible_in_whoami_and_proof`, `test_whoami_shows_shadow_mode` |
| **E** — Real mode visible | Real mode rendered in whoami + proof | `test_real_mode_visible`, `test_auth_mode_enum` |

### Negative Tests

| Test | Description | Test Functions |
|------|-------------|----------------|
| **F** — Browser cannot open | BrowserLaunchError with repair guidance | `test_browser_launch_error`, `test_pkce_browser_launch_failure` |
| **G** — Invalid completion artifact | InvalidTokenError, no false success | `test_invalid_token_error`, `test_pkce_exchange_code_failure` |
| **H** — Credential store write failure | CredentialStoreError with clear error | `test_credential_store_error`, `test_save_permission_error` |
| **I** — Whoami fails after login | WhoamiVerificationError, no partial success | `test_whoami_verification_error`, `test_verify_401`, `test_verify_403` |
| **J** — Missing/expired session | Clean failure with `keyhole login` suggestion | `test_whoami_no_session`, `test_whoami_expired_session`, `test_is_expired` |

### Proof Tests

| Test | Description | Test Functions |
|------|-------------|----------------|
| **K** — Proof bundle sufficiency | All required fields and files present | `test_generate_returns_complete_bundle`, `test_write_creates_all_files`, `test_event_chain_recorded` |
| **L** — No secret leakage | Tokens excluded from proof, `repr=False` on secrets | `test_no_secret_leakage_in_proof`, `test_token_not_in_repr`, `test_auth_session_safe_summary` |

---

## 4. Test Results

```
85 passed in 0.52s
```

| Test Class | Count | Status |
|------------|-------|--------|
| TestModels | 13 | ✅ All pass |
| TestCredentialStore | 12 | ✅ All pass |
| TestPKCEFlow | 9 | ✅ All pass |
| TestDeviceFlow | 5 | ✅ All pass |
| TestWhoamiClient | 6 | ✅ All pass |
| TestErrors | 8 | ✅ All pass |
| TestAuthBootstrapClient | 8 | ✅ All pass |
| TestCLILogin | 3 | ✅ All pass |
| TestCLIWhoami | 5 | ✅ All pass |
| TestProofBundle | 12 | ✅ All pass |
| TestIntegrationScenarios | 3 | ✅ All pass |

---

## 5. Proof Artifacts

Generated to `docs/evidence/sdk-client-01/proof_bundle/`:

```
proof_bundle/
├── core.json                  # Story ID, correlation, flow type, mode, result
├── request.json               # Login initiation metadata
├── response.json              # Completion state
├── event_chain.json           # 8 lifecycle events with timestamps
├── identity_context.json      # Whoami identity snapshot
├── verification_result.json   # Final verification state
├── correlation.json           # Correlation ID and session linkage
├── summary.md                 # Human-readable proof summary
├── digest.txt                 # SHA-256 digest of core.json
└── extended/                  # Reserved for additional proof material
```

**Digest:** `sha256:14cd59c27a1dcf7effe76f10237ad70358245e494fa71473c1782d7db0392539`

---

## 6. Security Properties

| Property | Implementation |
|----------|---------------|
| Token secrecy in models | `Field(repr=False)` on `access_token`, `refresh_token`, `id_token` |
| Token secrecy in proof | Tokens explicitly excluded from all proof artifacts |
| Credential file permissions | 0600 (owner read/write only) |
| Credential directory permissions | 0700 (owner only) |
| Atomic writes | Write to `.tmp` then `os.replace()` to prevent partial state |
| Safe summary | `AuthSession.safe_summary()` returns fingerprint, not token |
| No `.env` dependency | Credentials auto-managed in `~/.keyhole/credentials.json` |

---

## 7. Error Hierarchy and Repair Guidance

| Error Class | Trigger | Repair Suggestions |
|-------------|---------|-------------------|
| `NetworkError` | Connection/timeout failure | Check connectivity, retry, verify auth server URL |
| `BrowserLaunchError` | Browser cannot open | Use `--flow device`, open URL manually |
| `ExpiredChallengeError` | Auth challenge timeout | Retry login, check network |
| `InvalidTokenError` | Bad completion code/token | Retry login, clear credentials |
| `LoginDeniedError` | Access denied by IdP | Check account permissions, contact org admin |
| `CredentialStoreError` | Local store write failure | Check file permissions, disk space, directory ownership |
| `WhoamiVerificationError` | Whoami 401/403/error | Re-login, check token validity |

All errors inherit from `AuthBootstrapError` → `KeyholeSDKError` and carry `error_class`, `reason`, and `repair_suggestions[]`.

---

## 8. Constitutional Compliance

| Principle | How Satisfied |
|-----------|---------------|
| SDK is not the control plane | Client delegates auth to boundary server; no local token minting |
| All participation through MCP/auth boundary | PKCE/device flows target OIDC boundary; whoami calls `/mcp/v1/whoami` |
| No floating execution | Login validates via whoami before reporting success |
| Identity visible and attributable | Whoami renders user, tenant, org, cohort, worker, workspace, plan, mode |
| Zipper produces replayable proof | 10-file proof bundle with event chain and SHA-256 digest |
| Failure produces repair guidance | 7 error classes with deterministic repair suggestions |
| Onboarding feels easy | `keyhole login` → guided flow → credential stored → identity shown |

---

## 9. Files Changed

### New Files (11)

- `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/__init__.py`
- `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/models.py`
- `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/errors.py`
- `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/credential_store.py`
- `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/pkce.py`
- `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/device.py`
- `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/whoami.py`
- `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/client.py`
- `packages/python/keyhole-sdk/keyhole_sdk/auth_bootstrap/proof.py`
- `packages/python/keyhole-cli/keyhole_cli/commands/login.py`
- `packages/python/keyhole-cli/keyhole_cli/commands/whoami.py`

### Modified Files (1)

- `packages/python/keyhole-cli/keyhole_cli/cli.py` — registered `login` and `whoami` commands

### Test Files (1)

- `tests/unit/test_sdk_client_01_auth_bootstrap.py` — 85 tests

### Evidence Files

- `docs/evidence/sdk-client-01/proof_bundle/` — full proof bundle (10 files + extended/)

---

## 10. Zipper Status

The client half of the first SDK zipper is **closed**.

```
keyhole login
→ auth flow initiated (PKCE or device)
→ builder completes auth
→ client receives token/session
→ local credential store written (secure, atomic, 0600)
→ client calls whoami
→ identity rendered (user, tenant, org, mode)
→ proof bundle closed (10 artifacts + digest)
```

**Paired server story:** `sdk-server-01.md` — required to close the full zipper.
