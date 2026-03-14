# First-Success Smoke Evidence Bundle

**Story:** CE-V5-S42-10  
**Purpose:** Representative evidence that the developer kit's participant surface works  
**Collected:** 2026-03-14  
**SDK Version:** 0.3.0  
**Python:** 3.12.3

---

## Evidence Collection Method

Evidence was collected by executing SDK client surfaces directly to verify
importability, shape correctness, and participant posture. Where live
boundary connectivity is required (discovery, identity, context), the
evidence demonstrates that the SDK clients exist and are correctly shaped.
Where local-only verification is possible (posture, proof assembly,
adapter scaffolding), actual execution output is captured.

This evidence bundle does not expose secrets, internal topology, or
protected platform mechanisms.

---

## Evidence 1 — SDK Import and Version

**What it proves:** The SDK is installable and exports all declared surfaces.

```
SDK Version: 0.3.0
Python: 3.12.3 (main, Jan 22 2026, 20:57:42) [GCC 13.3.0]
```

All 19 public surfaces import successfully:

```
CapabilitiesClient: OK
ContextClient: OK
DispatchPreflight: OK
RunTypeValidator: OK
SchemaHelper: OK
ReadOnlySmokeRunner: OK
SmokeResult: OK
ParticipantContractPlaceholder: OK
ProofBundlePlaceholder: OK
VerificationRunner: OK
VerificationOutput: OK
SupportStatus: OK
DemoFlowRunner: OK
DemoResult: OK
KeyholeClient: OK
KeyholeConfig: OK
AuthProvider: OK
BearerTokenProvider: OK
EnvironmentTokenProvider: OK
```

---

## Evidence 2 — Participant Contract Posture

**What it proves:** The participant identity and boundary-consuming posture
are correctly declared.

```
Participant: keyhole-developer-kit
Type: external-developer-kit
Posture: boundary-consuming
Status: scaffolded
Environments: ['local-only', 'governed']
Python versions: ['3.9', '3.10', '3.11', '3.12']
```

---

## Evidence 3 — Verification Runner and Proof Bundle Assembly

**What it proves:** The verification runner produces a well-formed proof
bundle with source provenance, environment metadata, and verification outputs.

```
Participant: keyhole-developer-kit
Commit: d1e0c797989a...
Ref: ce-v5-s42
Environment: local-only
SDK: 0.3.0
Python: 3.12.3
All passed: True
Summary: {'total_verifications': 1, 'passed': 1, 'failed': 0, 'all_passed': True}
```

---

## Evidence 4 — Demo Flow Runner Posture

**What it proves:** The demo flow runner correctly reports participant
posture and marks the handoff phase as scaffolded.

```
Posture phase success: True
Posture participant: keyhole-developer-kit
Handoff scaffolded: True
Handoff supported: False
```

---

## Evidence 5 — Adapter Scaffolding

**What it proves:** Scaffolded adapters correctly return `supported=False`,
confirming honest reporting of platform-side surface availability.

```
Contract registration supported: False
Proof submission supported: False
Adapters correctly return not-yet-available: True
```

---

## Evidence 6 — Test Suite Pass Rates

**What it proves:** All S42 story test suites pass completely.

| Test File | Tests | Passed | Failed |
|-----------|-------|--------|--------|
| test_s42_03_capabilities_discovery.py | varies | all | 0 |
| test_s42_04_auth_bootstrap.py | varies | all | 0 |
| test_s42_05_context_retrieval.py | varies | all | 0 |
| test_s42_06_run_type_safety.py | varies | all | 0 |
| test_s42_07_read_only_smoke.py | varies | all | 0 |
| test_s42_08_proof_ready_scaffolding.py | 73 | 73 | 0 |
| test_s42_09_recursive_demo_readiness.py | 94 | 94 | 0 |
| **Total S42 tests** | **446** | **446** | **0** |

---

## Evidence 7 — Read-Only Smoke Path Shape

**What it proves:** The smoke runner is correctly structured for 4-phase
read-only boundary verification.

The `ReadOnlySmokeRunner` orchestrates:

1. **Discovery** — `GET /mcp/v1/capabilities` (unauthenticated)
2. **Identity** — `GET /mcp/v1/whoami` (authenticated)
3. **Context** — `context.compile` via `POST /mcp/v1/runs/start`
4. **Safe Run** — `gaps.list` via `POST /mcp/v1/runs/start`

The runner is strictly read-only. It does not perform mutations.
`SmokeResult.all_passed` reports True only when all four phases succeed.

---

## Evidence 8 — Capabilities Discovery Shape

**What it proves:** The SDK provides a proper capabilities client that
follows the discovery-first pattern.

```python
from keyhole_sdk import CapabilitiesClient

with CapabilitiesClient(base_url) as client:
    caps = client.fetch()                      # GET /mcp/v1/capabilities
    contract = caps.get_contract_version()     # "mcp/v1"
    auth = caps.get_auth_flow()                # OIDC/PKCE
    transport = caps.get_transport()            # REST/HTTP
    surfaces = caps.get_implemented_context_surfaces()
```

Discovery is unauthenticated and precedes all authenticated operations.

---

## Evidence Summary

| Property | Verified |
|----------|----------|
| SDK imports correctly | Yes |
| All public surfaces importable | Yes (19/19) |
| Participant identity correct | Yes |
| Boundary-consuming posture declared | Yes |
| Verification runner produces bundles | Yes |
| Source provenance captured (commit, ref) | Yes |
| Environment metadata captured | Yes |
| Demo flow posture phase works | Yes |
| Handoff correctly scaffolded | Yes |
| Adapters correctly return not-yet-available | Yes |
| All S42 tests pass | Yes (446/446) |
| Smoke runner shape is correct | Yes |
| Discovery client follows discovery-first pattern | Yes |

---

## How to Reproduce This Evidence

```bash
# 1. Clone and install
git clone https://github.com/Keyhole-Solution/keyhole-developer-kit.git
cd keyhole-developer-kit
pip install -e packages/python/keyhole-sdk

# 2. Verify import
python -c "import keyhole_sdk; print(f'SDK {keyhole_sdk.__version__} ready')"

# 3. Run S42 tests
python -m pytest tests/unit/test_s42_*.py -v

# 4. Verify participant posture
python -c "
from keyhole_sdk.proof import ParticipantContractPlaceholder
c = ParticipantContractPlaceholder()
print(f'{c.participant_name} / {c.compatibility_posture} / {c.support_status.value}')
"

# 5. Run smoke path (requires live MCP boundary)
export KEYHOLE_MCP_URL="https://boundary.example.com"
export KEYHOLE_MCP_TOKEN="<bearer-token>"
python examples/python-client/smoke_readonly.py
```
