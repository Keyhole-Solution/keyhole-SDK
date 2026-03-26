# SDK-CLIENT-00 — Identity Creation & Verification (Client): Completion Report

**Story ID:** SDK-CLIENT-00 / sdk-client-00  
**Epic:** SDK-CLIENT — Governed Developer SDK, Onboarding, and Repository Ingestion  
**Story Type:** Client-side zipper story  
**Status:** COMPLETE — all acceptance criteria satisfied  
**Test Result:** 85/85 passed (45 unit + 40 smoke)

---

## 1. Implementation Summary

This story implements the client-side identity creation and verification flow
enabling a brand new builder to enter the Keyhole ecosystem through a governed
onboarding surface before authentication bootstrap begins.

The client can register a new identity, complete verification, inspect status,
generate a replayable proof bundle, and hand off a verified active identity
cleanly to SDK-CLIENT-01.

### Modules Delivered

| Module | Location | Purpose |
|--------|----------|---------|
| `models.py` | `keyhole_sdk/onboarding/` | Typed Pydantic models: `RegistrationRequest`, `VerificationRequest`, `StatusRequest`, `OnboardingState` enum, `OnboardingRealm` enum, registration/verification/status response models |
| `errors.py` | `keyhole_sdk/onboarding/` | Error hierarchy with deterministic repair guidance: `MissingClassificationError`, `DuplicateRegistrationError`, `VerificationExpiredError`, `VerificationFailedError`, `RegistrationRejectedError`, `NetworkError` |
| `client.py` | `keyhole_sdk/onboarding/` | `OnboardingClient` orchestrating registration, verification, and status inspection against the governed boundary |
| `proof.py` | `keyhole_sdk/onboarding/` | `OnboardingProofBundle` generating all proof artifacts with classification capture |
| `register.py` | `keyhole_cli/commands/` | `keyhole register` CLI command |
| `verify.py` | `keyhole_cli/commands/` | `keyhole verify` CLI command |
| `registration_status.py` | `keyhole_cli/commands/` | `keyhole registration-status` CLI command |
| `cli.py` | `keyhole_cli/` | Modified — registered register, verify, and registration-status commands |

---

## 2. Acceptance Criteria Mapping

### §18 Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | `keyhole register` can initiate a valid identity creation flow | ✅ | `OnboardingClient.register()` submits to governed boundary; CLI wraps it with `--email`, `--username`, `--display-name`, `--realm`, `--origin`, `--purpose`. Tests: `TestA::test_register_returns_pending_verification`, `TestCLIRegisterCommand::test_run_register_success` |
| 2 | Client can submit the required onboarding fields | ✅ | `RegistrationRequest` collects email, username, display_name, realm, origin, purpose. Tests: `TestA::test_register_sends_correct_payload`, `TestModelValidation::test_registration_request_validate_classification_complete` |
| 3 | Dev/test onboarding can explicitly target `kh-dev` | ✅ | `--realm kh-dev` default; `OnboardingRealm.KH_DEV` enum. Tests: `TestD::test_verify_with_token_works`, `TestModelValidation::test_onboarding_realm_enum_values` |
| 4 | Origin and purpose explicitly provided for `kh-dev` test users | ✅ | `MissingClassificationError` raised when origin/purpose absent for `kh-dev`. Tests: `TestF::test_missing_origin_raises`, `TestF::test_missing_purpose_raises`, `TestF::test_missing_both_raises` |
| 5 | Client clearly reports pending verification state | ✅ | Registration returns `OnboardingState.PENDING_VERIFICATION` with next-step guidance. Tests: `TestA::test_register_returns_pending_verification`, smoke `TestLayer1Register::test_register_state_is_pending` |
| 6 | Client can complete verification through an approved mechanism | ✅ | `keyhole verify --code` / `--token` submits verification artifact to boundary. Tests: `TestB::test_verify_returns_active_state`, smoke `TestLayer3Verify::test_verify_success` |
| 7 | Client can inspect or poll onboarding status deterministically | ✅ | `keyhole registration-status --registration-id` returns full lifecycle state. Tests: `TestC::test_status_returns_full_context`, `TestC::test_status_safe_summary`, smoke `TestLayer2PreVerifyStatus`, `TestLayer4PostVerifyStatus` |
| 8 | Client does not claim activation before server confirms it | ✅ | `OnboardingState` transitions only from server responses; no local state inflation. Tests: `TestG::test_bad_code_does_not_report_active`, `TestH::test_expired_raises_correct_error` |
| 9 | Client generates a replayable onboarding proof bundle | ✅ | `OnboardingProofBundle` generates core.json, request.json, response.json, event_chain.json, registration_context.json, verification_result.json, identity_context.json, correlation.json, summary.md, digest.txt, extended/. Tests: `TestK::test_hot_proof_core_is_sufficient`, smoke `TestLayer6ProofBundle` (7 tests) |
| 10 | Proof artifacts preserve realm, origin, and purpose classification | ✅ | Classification fields always captured in proof. Tests: `TestL::test_realm_origin_purpose_in_proof`, `TestL::test_classification_in_summary`, `TestA::test_register_proof_captures_classification` |
| 11 | Failure paths return deterministic reasons and repair guidance | ✅ | 6 error classes, each with `error_class`, `reason`, and `repair_suggestions[]`. Tests: `TestErrorHierarchy` (6 tests), `TestNetworkFailures` (3 tests) |
| 12 | Successful onboarding gives a clear next step into SDK-CLIENT-01 | ✅ | Active verification shows "next: keyhole login". Tests: `TestE::test_active_verification_shows_login_next_step`, smoke `TestLayer5Handoff::test_next_steps_mention_login_or_sdk01` |
| 13 | No auth credentials are persisted by this story | ✅ | No credential store, no session persistence. Auth belongs to SDK-CLIENT-01. Tests: smoke `TestLayer5Handoff::test_no_auth_credentials_in_output` |
| 14 | No secret-bearing verification material leaks into proof artifacts | ✅ | Tokens excluded from proof; `repr=False` on secrets; disk write is safe. Tests: `TestJ::test_proof_bundle_contains_no_secrets`, `TestJ::test_verification_request_model_hides_token`, `TestJ::test_proof_write_to_disk_is_secret_safe`, smoke `TestLayer6ProofBundle::test_no_secret_leakage_in_proof` |

---

## 3. Test Plan Coverage (§19)

### Positive Tests

| Test | Description | Test Functions |
|------|-------------|----------------|
| **A** — Dev/test registration succeeds | Register with explicit `kh-dev`, origin, purpose → accepted, pending, proof captures classification | `TestA::test_register_returns_pending_verification`, `TestA::test_register_sends_correct_payload`, `TestA::test_register_proof_captures_classification` |
| **B** — Verification completes successfully | Verify with valid artifact → active state, proof captures completion | `TestB::test_verify_returns_active_state`, `TestB::test_verify_proof_captures_completion` |
| **C** — Registration status works | Status returns full lifecycle context, realm, origin, purpose visible | `TestC::test_status_returns_full_context`, `TestC::test_status_safe_summary` |
| **D** — Dev verification path | Verify with token works for dev/test (Mailhog-compatible) | `TestD::test_verify_with_token_works` |
| **E** — Handoff to login is clear | Active verification shows "next: keyhole login" | `TestE::test_active_verification_shows_login_next_step` |

### Negative Tests

| Test | Description | Test Functions |
|------|-------------|----------------|
| **F** — Missing classification rejected for `kh-dev` | Missing origin/purpose → `MissingClassificationError` with repair guidance | `TestF::test_missing_origin_raises`, `TestF::test_missing_purpose_raises`, `TestF::test_missing_both_raises`, `TestF::test_non_dev_realm_no_classification_required` |
| **G** — Invalid verification artifact rejected | Bad code → `VerificationFailedError`, no false active state | `TestG::test_bad_code_raises_verification_failed`, `TestG::test_bad_code_does_not_report_active` |
| **H** — Expired verification rejected | Expired → `VerificationExpiredError` with repair guidance | `TestH::test_expired_raises_correct_error` |
| **I** — Duplicate registration rejected cleanly | Duplicate → `DuplicateRegistrationError`, no false success | `TestI::test_duplicate_raises_correct_error`, `TestI::test_duplicate_no_false_success` |
| **J** — No secret leakage in proof | Proof bundle, model repr, disk write all secret-safe | `TestJ::test_proof_bundle_contains_no_secrets`, `TestJ::test_verification_request_model_hides_token`, `TestJ::test_proof_write_to_disk_is_secret_safe` |

### Proof Tests

| Test | Description | Test Functions |
|------|-------------|----------------|
| **K** — Onboarding proof replay sufficiency | Hot proof core sufficient to reconstruct onboarding closure | `TestK::test_hot_proof_core_is_sufficient` |
| **L** — Classification proof correctness | Realm, origin, purpose present and accurate in proof | `TestL::test_realm_origin_purpose_in_proof`, `TestL::test_classification_in_summary` |

---

## 4. Test Results

### Unit Tests — 45/45 passed (0.28s)

| Test Class | Count | Status |
|------------|-------|--------|
| TestA_DevTestRegistrationSucceeds | 3 | ✅ All pass |
| TestB_VerificationCompletesSuccessfully | 2 | ✅ All pass |
| TestC_RegistrationStatusWorks | 2 | ✅ All pass |
| TestD_DevVerificationPath | 1 | ✅ All pass |
| TestE_HandoffToLoginIsClear | 1 | ✅ All pass |
| TestF_MissingClassificationRejected | 4 | ✅ All pass |
| TestG_InvalidVerificationRejected | 2 | ✅ All pass |
| TestH_ExpiredVerificationRejected | 1 | ✅ All pass |
| TestI_DuplicateRegistrationRejected | 2 | ✅ All pass |
| TestJ_NoSecretLeakageInProof | 3 | ✅ All pass |
| TestK_OnboardingProofReplaySufficiency | 1 | ✅ All pass |
| TestL_ClassificationProofCorrectness | 2 | ✅ All pass |
| TestModelValidation | 5 | ✅ All pass |
| TestErrorHierarchy | 6 | ✅ All pass |
| TestNetworkFailures | 3 | ✅ All pass |
| TestCLIRegisterCommand | 4 | ✅ All pass |
| TestCLIVerifyCommand | 2 | ✅ All pass |
| TestCLIRegistrationStatusCommand | 1 | ✅ All pass |

### Smoke Tests — 40/40 passed (1.99s)

| Test Layer | Count | Status |
|------------|-------|--------|
| TestLayer0Prerequisites | 4 | ✅ keyhole CLI available, curl available, register + status endpoints reachable |
| TestLayer1Register | 10 | ✅ Registration against live MCP boundary — state pending, realm kh-dev, origin/purpose set, verification hint, next steps |
| TestLayer2PreVerifyStatus | 6 | ✅ Status inspection before verification — pending state confirmed, realm/origin/purpose visible |
| TestLayer3Verify | 4 | ✅ Verification with valid artifact against live boundary — state active, ID matches |
| TestLayer4PostVerifyStatus | 5 | ✅ Status after verification — state verified/active, classification fields unchanged |
| TestLayer5Handoff | 3 | ✅ Next steps mention login/SDK-01, no auth credentials in output |
| TestLayer6ProofBundle | 8 | ✅ Proof directory created, core.json exists, hot core files present, digest format valid, no secret leakage, summary mentions onboarding closure, verification result has active state, event chain has verification event |

### Live Evidence

- **MCP boundary:** `https://mcp.keyholesolution.com`
- **Target realm:** `kh-dev`
- **Smoke tests ran against live server** — 40/40 passed
- **Event Spine:** `IDENTITY_CREATED` confirmed on `KH_GATE.dev.onboarding.identity_created` seq=573134 (PR #162)

---

## 5. Proof Artifacts

Generated to `docs/evidence/sdk-client-00/proof_bundle/` (during smoke runs):

```
proof_bundle/
├── core.json                  # Story ID, correlation, flow type, realm, result
├── request.json               # Registration request metadata
├── response.json              # Registration/verification response
├── event_chain.json           # Lifecycle events (IDENTITY_CREATED, IDENTITY_VERIFIED)
├── registration_context.json  # Realm, origin, purpose classification
├── verification_result.json   # Verification completion state
├── identity_context.json      # Server-sourced identity context
├── correlation.json           # Correlation ID and registration linkage
├── summary.md                 # Human-readable onboarding proof summary
├── digest.txt                 # SHA-256 digest of core.json
└── extended/                  # Reserved for additional proof material
```

---

## 6. Security Properties

| Property | Implementation |
|----------|---------------|
| No auth credential persistence | This story persists zero credentials — that belongs to SDK-CLIENT-01 |
| Token secrecy in models | `Field(repr=False)` on verification tokens and secret fields |
| Token secrecy in proof | Verification artifacts explicitly excluded from proof bundles |
| Classification enforcement | `MissingClassificationError` for `kh-dev` without origin/purpose |
| No false activation | Client never claims active until server confirms |
| Safe summary | Status responses hide secret material; safe_summary for display |
| Proof write safety | Disk-written proof inspected for zero secret leakage |

---

## 7. Error Hierarchy and Repair Guidance

| Error Class | Trigger | Repair Suggestions |
|-------------|---------|-------------------|
| `MissingClassificationError` | `kh-dev` registration without origin/purpose | Provide explicit `--origin` and `--purpose` flags |
| `DuplicateRegistrationError` | Identity already registered | Check existing registration with `keyhole registration-status` |
| `VerificationExpiredError` | Verification token/code expired | Re-register or request new verification |
| `VerificationFailedError` | Invalid verification artifact | Check code/token, retry with correct artifact |
| `RegistrationRejectedError` | Server rejected registration | Check error reason, correct input fields, retry |
| `NetworkError` | Connection/timeout failure | Check connectivity, retry, verify MCP boundary URL |

All errors inherit from `OnboardingError` → `KeyholeSDKError` and carry `error_class`, `reason`, and `repair_suggestions[]`.

---

## 8. Constitutional Compliance

| Principle | How Satisfied |
|-----------|---------------|
| SDK is not the control plane | Client delegates identity creation to the governed boundary server; no local identity minting |
| All participation through MCP boundary | Registration, verification, and status all target `https://mcp.keyholesolution.com` |
| No floating execution | Client does not claim activation before server confirmation |
| Event Spine is canonical truth | Client references `IDENTITY_CREATED` and `IDENTITY_VERIFIED` from server; does not invent events |
| Test/dev users explicitly identifiable | `kh-dev` requires explicit `origin` and `purpose`; `MissingClassificationError` enforced |
| Zipper produces replayable proof | 11-file proof bundle with event chain, classification, and SHA-256 digest |
| Failure produces repair guidance | 6 error classes with deterministic repair suggestions |
| Onboarding feels easy | `keyhole register` → guided flow → verification → status → "next: keyhole login" |

---

## 9. Realm-Aware Onboarding

| Realm | Purpose | Classification Required |
|-------|---------|----------------------|
| `kh-dev` | Test and dev users | Yes — `origin` and `purpose` enforced |
| `keyhole-mcp` | Machine users | Out of scope for this story |
| `kh-prod` | Human production users | No explicit classification required |

The client enforces `MissingClassificationError` when `kh-dev` is targeted without origin/purpose, preventing ambiguous test identities.

---

## 10. Files Changed

### New Files (5)

- `packages/python/keyhole-sdk/keyhole_sdk/onboarding/__init__.py`
- `packages/python/keyhole-sdk/keyhole_sdk/onboarding/models.py`
- `packages/python/keyhole-sdk/keyhole_sdk/onboarding/errors.py`
- `packages/python/keyhole-sdk/keyhole_sdk/onboarding/client.py`
- `packages/python/keyhole-sdk/keyhole_sdk/onboarding/proof.py`

### New CLI Commands (3)

- `packages/python/keyhole-cli/keyhole_cli/commands/register.py`
- `packages/python/keyhole-cli/keyhole_cli/commands/verify.py`
- `packages/python/keyhole-cli/keyhole_cli/commands/registration_status.py`

### Modified Files (1)

- `packages/python/keyhole-cli/keyhole_cli/cli.py` — registered register, verify, and registration-status commands

### Test Files (2)

- `tests/unit/test_sdk_client_00_onboarding.py` — 45 unit tests
- `tests/smoke/test_sdk_client_00_onboarding.py` — 40 smoke tests

---

## 11. Zipper Status

The client half of the pre-auth onboarding zipper is **closed**.

```
keyhole register
→ registration submitted to governed boundary
→ pending identity created
→ verification initiated
→ builder completes verification
→ identity activated (server-confirmed)
→ IDENTITY_CREATED emitted (seq=573134)
→ proof bundle generated (11 artifacts + digest)
→ next: keyhole login (SDK-CLIENT-01)
```

**Paired server story:** `sdk-server-00.md` — server-side identity creation and verification logic.  
**Next client story:** `sdk-client-01.md` — authentication bootstrap (login, whoami, credential persistence).
