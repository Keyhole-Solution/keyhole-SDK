# Recursive Demo Readiness Pack

**Story:** CE-V5-S42-09  
**Status:** Ready for demonstration  
**Last Updated:** 2026-03-14

---

## What the Recursive Demo Is Proving

The recursive governance demonstration proves that an **external participant
repository** can undergo a governed change lifecycle across a real repo
boundary:

1. A story exists in the governance spine
2. The external repo retrieves governed truth before acting
3. The external repo applies a small, safe change
4. Verification artifacts are produced locally
5. A proof-bearing handoff occurs to the platform side
6. The platform evaluates, returns verdicts, and promotes or rejects
7. Evidence appears in the expected places
8. Humans (and agents) can see the whole loop

This is not a synthetic exercise. It is the first real cross-boundary
governed change using the developer kit as the external participant.

---

## Demo-Safe Change Path

### Selected Change: `keyhole version --governance` subcommand flag

**Affected surface:** `keyhole-cli` — adds a `--governance` flag to the
existing `keyhole version` command that displays the participant's
governance posture alongside the version.

**What it does:**

```
$ keyhole version --governance
keyhole-cli 0.3.0
SDK: keyhole-sdk 0.3.0
Participant: keyhole-developer-kit
Posture: boundary-consuming
Support: scaffolded (proof-ready)
Environment: local-only
```

**Why this change is safe:**

- Read-only output — no mutation of any state
- Low blast radius — a single flag on an existing command
- Does not touch platform surfaces or boundary logic
- Uses only local participant contract placeholder data
- Easy to verify: run the command, observe the output

**How it will be verified:**

- Unit test: `keyhole version --governance` produces expected fields
- Contract surface test: output fields match `ParticipantContractPlaceholder` shape
- Boundary smoke test: existing read-only smoke path still passes

**Why it is meaningful:**

- Proves governance across a repo boundary (not trivial formatting)
- Shows the participant declaring its posture through boundary-consumed truth
- The change itself is the kind of thing a governed participant would submit
- Verification outputs naturally feed into proof-bundle assembly

---

## Candidate Demo Workflow

### Prerequisites

| Check | How to verify | Status |
|-------|--------------|--------|
| MCP boundary reachable | `curl $MCP_URL/mcp/v1/capabilities` returns 200 | Executable now |
| Auth token available | OIDC/PKCE token for realm `keyhole-mcp` | Executable now |
| Developer kit repo cloned | Working copy with demo branch | Executable now |
| SDK installed | `pip install -e packages/python/keyhole-sdk` | Executable now |
| CLI installed | `pip install -e packages/python/keyhole-cli` | Executable now |

### Step-by-Step Flow

#### Phase 1: Discover (executable now)

```bash
# Retrieve live boundary capabilities
python -c "
from keyhole_sdk import CapabilitiesClient
with CapabilitiesClient('$MCP_URL') as client:
    caps = client.fetch()
    print(f'Contract: {caps.get_contract_version()}')
    print(f'Auth: {caps.get_auth_flow()}')
    print(f'Surfaces: {caps.get_implemented_context_surfaces()}')
"
```

**Expected output:** Contract version, auth posture, implemented surfaces.

#### Phase 2: Retrieve Governed Context (executable now)

```bash
# Retrieve governed context before acting
python -c "
from keyhole_sdk import ContextClient
with ContextClient('$MCP_URL', token='$TOKEN') as ctx:
    snapshot = ctx.compile_context()
    print(f'Platform: {snapshot.get_platform_name()}')
    print(f'Model: {snapshot.get_governance_model()}')
    print(f'Contract: {snapshot.get_mcp_contract()}')
"
```

**Expected output:** Platform name, governance model, MCP contract version.

#### Phase 3: Confirm Participant Posture (executable now)

```bash
# Confirm participant identity and readiness
python -c "
from keyhole_sdk.proof import ParticipantContractPlaceholder, SupportStatus
contract = ParticipantContractPlaceholder()
print(f'Participant: {contract.participant_name}')
print(f'Type: {contract.participant_type}')
print(f'Posture: {contract.compatibility_posture}')
print(f'Status: {contract.support_status.value}')
print(f'Verification classes: {contract.verification_classes}')
"
```

**Expected output:** Participant identity, boundary-consuming posture, scaffolded status.

#### Phase 4: Apply Demo-Safe Change (executable now)

```bash
# Create the demo branch and apply the change
git checkout -b demo/governance-posture-flag
# (Apply the --governance flag to keyhole version command)
# (See demo change definition above)
git add -A && git commit -m "feat: add --governance flag to keyhole version"
```

**Expected output:** Clean commit on demo branch.

#### Phase 5: Run Local Verification (executable now)

```bash
# Run verification runner with demo collectors
python -c "
from keyhole_sdk.proof import VerificationRunner, VerificationOutput
from keyhole_sdk.demo import DemoFlowRunner

demo = DemoFlowRunner(
    base_url='$MCP_URL',
    token='$TOKEN',
)
result = demo.run_verification()
print(f'All passed: {result.all_passed}')
print(f'Summary: {result.verification_summary}')
"
```

**Expected output:** Verification summary with pass/fail per class.

#### Phase 6: Assemble Proof-Ready Artifacts (executable now)

```bash
# Assemble proof bundle from verification outputs
python -c "
from keyhole_sdk.demo import DemoFlowRunner

demo = DemoFlowRunner(
    base_url='$MCP_URL',
    token='$TOKEN',
)
bundle = demo.assemble_proof_bundle()
print(f'Participant: {bundle.participant_name}')
print(f'Commit: {bundle.source_commit}')
print(f'Ref: {bundle.source_ref}')
print(f'Verifications: {bundle.verification_summary}')
print(f'Status: {bundle.support_status.value}')
"
```

**Expected output:** Proof bundle with participant metadata, provenance, and verification results.

#### Phase 7: Handoff to Platform (requires DEV-UX)

> **Status: SCAFFOLDED — awaiting DEV-UX surface stabilization.**

```bash
# When DEV-UX-03/04 surfaces stabilize:
python -c "
from keyhole_sdk.demo import DemoFlowRunner

demo = DemoFlowRunner(base_url='$MCP_URL', token='$TOKEN')
result = demo.submit_proof()  # → AdapterResult(supported=False)
print(f'Supported: {result.supported}')
print(f'Reason: {result.reason}')
"
```

**Expected output (today):** `supported=False` with clear explanation.  
**Expected output (after DEV-UX):** Submission acknowledgement with reference ID.

#### Phase 8: Observe Platform Evidence (requires DEV-UX)

> **Status: NOT YET AVAILABLE — requires DEV-UX-06/08/09.**

Expected observations when platform side is ready:
- Contract registered in participant registry
- Proof bundle accepted by submission pipeline
- Verification graph resolves blast radius
- Verdict artifact generated (pass/fail)
- Evidence visible in governance console

---

## Ownership Boundary

### Developer Kit Side Owns

| Responsibility | Status |
|---------------|--------|
| Capabilities discovery | **Executable now** |
| Context retrieval before acting | **Executable now** |
| Participant posture confirmation | **Executable now** |
| Demo-safe change application | **Executable now** |
| Local verification execution | **Executable now** |
| Proof-ready bundle assembly | **Executable now** |
| Handoff to platform adapters | **Scaffolded** |

### Platform DEV-UX Side Owns

| Responsibility | Status |
|---------------|--------|
| Contract/proof intake (DEV-UX-03/04) | **Planned** |
| Verification graph resolution (DEV-UX-05) | **Planned** |
| Verdict generation (DEV-UX-06) | **Planned** |
| Repair guidance (DEV-UX-06) | **Planned** |
| Promotion logic | **Planned** |
| Console visibility (DEV-UX-08) | **Planned** |
| Full recursive demonstration (DEV-UX-09) | **Planned** |

---

## Related Stories

| Story | Title | Relationship |
|-------|-------|-------------|
| CE-V5-S42-01 through S42-07 | Foundation stories | Composed into demo flow |
| CE-V5-S42-08 | Proof-Ready Scaffolding | Proof models & adapters used |
| **CE-V5-S42-09** | **Recursive Demo Readiness Pack** | **This story** |
| CE-V5-S42-10 | Launch Readiness Seal | Consumes this readiness pack |
| DEV-UX-03 | Participant Contract Registry | Future handoff target |
| DEV-UX-04 | Proof Submission Pipeline | Future handoff target |
| DEV-UX-09 | Recursive Story Demonstration | Consumes this readiness pack |

---

## Common Failure Modes

See [recursive-demo-operator-notes.md](recursive-demo-operator-notes.md)
for the full troubleshooting guide.
