# Recursive Demo — Evidence Map

**Story:** CE-V5-S42-09  
**Purpose:** Maps each participant-side action to the platform-side evidence
it should eventually produce.

---

## Evidence Map Overview

```
Participant Action          →  Expected Evidence / Observation
─────────────────────────── ─  ─────────────────────────────────────────
1. Discovery                →  Capabilities receipt (local + boundary log)
2. Identity                 →  Authenticated participant record
3. Context retrieval        →  Context compile response snapshot
4. Posture declaration      →  Participant contract shape
5. Change commit            →  Source commit SHA + ref provenance
6. Local verification       →  Verification output per collector
7. Proof bundle assembly    →  Bundle artifact with full metadata
8. Handoff attempt          →  Adapter result (scaffolded until DEV-UX)
```

---

## Detailed Evidence Mapping

### 1. Discovery → Capabilities Receipt

| Aspect | Detail |
|--------|--------|
| **Action** | `GET /mcp/v1/capabilities` via `CapabilitiesClient` |
| **Evidence produced** | `CapabilitiesResult` with contract version, auth flow, transport |
| **Participant-side observable** | Contract version string, operations list |
| **Platform-side observable** | Access log entry (unauthenticated discovery) |
| **Status** | Executable now |
| **Fields captured** | `contract`, `auth_flow`, `transport`, `min_sdk_version`, `operations` |

### 2. Identity → Authenticated Participant Record

| Aspect | Detail |
|--------|--------|
| **Action** | `GET /mcp/v1/whoami` with Bearer token |
| **Evidence produced** | Participant identity JSON |
| **Participant-side observable** | HTTP 200 with identity payload |
| **Platform-side observable** | Authenticated access log, participant token validation |
| **Status** | Executable now |
| **Fields captured** | Participant name, type, realm, authority claims |

### 3. Context Retrieval → Context Compile Snapshot

| Aspect | Detail |
|--------|--------|
| **Action** | `POST /mcp/v1/runs/start` with `context.compile` via `ContextClient` |
| **Evidence produced** | `ContextSnapshot` with platform truth |
| **Participant-side observable** | Platform name, governance model, implemented surfaces |
| **Platform-side observable** | Run dispatch log for `context.compile` |
| **Status** | Executable now |
| **Fields captured** | `platform_name`, `governance_model`, `mcp_contract`, `implemented_surfaces` |

### 4. Posture Declaration → Participant Contract Shape

| Aspect | Detail |
|--------|--------|
| **Action** | Instantiate `ParticipantContractPlaceholder` |
| **Evidence produced** | Contract metadata object |
| **Participant-side observable** | Participant name, type, posture, verification classes |
| **Platform-side observable** | None until contract registration adapter is supported |
| **Status** | Scaffolded (participant-side only) |
| **Fields captured** | `participant_name`, `participant_type`, `compatibility_posture`, `support_status`, `verification_classes` |

### 5. Change Commit → Source Provenance

| Aspect | Detail |
|--------|--------|
| **Action** | `git commit` on demo branch |
| **Evidence produced** | Git commit SHA, branch ref, commit message |
| **Participant-side observable** | `source_commit`, `source_ref` in proof bundle |
| **Platform-side observable** | None (local git only) until proof submission |
| **Status** | Executable now (local git) |
| **Fields captured** | `source_commit`, `source_ref`, commit timestamp |

### 6. Local Verification → Verification Outputs

| Aspect | Detail |
|--------|--------|
| **Action** | `VerificationRunner.run()` with registered collectors |
| **Evidence produced** | `VerificationOutput` per collector |
| **Participant-side observable** | Pass/fail per verification class, test counts, error summaries |
| **Platform-side observable** | None until proof submission |
| **Status** | Executable now |
| **Fields captured** | `verification_class`, `passed`, `passed_tests`, `total_tests`, `error_summary` |

### 7. Proof Bundle Assembly → Bundle Artifact

| Aspect | Detail |
|--------|--------|
| **Action** | `ProofBundlePlaceholder` with verification outputs |
| **Evidence produced** | Complete proof bundle with metadata |
| **Participant-side observable** | Participant identity, source provenance, environment, SDK version, verification summary |
| **Platform-side observable** | None until proof submission |
| **Status** | Executable now (assembly only) |
| **Fields captured** | All participant fields + `assembled_at`, `verification_summary`, `verifications` |

### 8. Handoff Attempt → Adapter Result

| Aspect | Detail |
|--------|--------|
| **Action** | `ProofSubmissionAdapter.submit_proof()` |
| **Evidence produced** | `AdapterResult` with supported=False |
| **Participant-side observable** | `supported=False`, reason explaining DEV-UX dependency |
| **Platform-side observable** | None (adapter is local-only stub) |
| **Status** | Scaffolded — awaits DEV-UX surface stabilization |
| **Fields captured** | `supported`, `success`, `reason`, `data` |

---

## Evidence Status Summary

| Phase | Category | Participant Evidence | Platform Evidence |
|-------|----------|---------------------|-------------------|
| Discovery | Live boundary | Available now | Access log |
| Identity | Authenticated | Available now | Auth log |
| Context | Governed read | Available now | Run log |
| Posture | Local scaffold | Available now | Awaits DEV-UX |
| Change | Local git | Available now | Awaits submission |
| Verification | Local test | Available now | Awaits submission |
| Bundle | Local assembly | Available now | Awaits submission |
| Handoff | Scaffolded stub | Stub result now | Awaits DEV-UX |

---

## Boundary Between Now and Later

**Executable now (participant-side):**
- Steps 1–7 produce real, observable evidence on the participant side
- All outputs are deterministic and scriptable
- No platform write operations occur

**Scaffolded for later (platform-side):**
- Step 8 handoff returns a stub result
- Contract registration, proof intake, verification graph construction,
  verdict computation, and promotion are all awaiting DEV-UX surfaces
- When those surfaces stabilize, the same participant workflow will
  produce platform-side evidence without structural changes

---

## Verification Classes

The demo uses these verification classes for the proof bundle:

| Class | Description | Coverage |
|-------|-------------|----------|
| `sdk-compatibility` | SDK version and boundary contract match | Discovery + context |
| `runtime-bridge` | Test runtime identity and realize endpoints | Runtime shape |
| `proof-scaffolding` | Proof models and adapter seam boundaries | S42-08 deliverables |
| `demo-readiness` | Demo flow completeness and scriptability | S42-09 deliverables |

Each verification class maps to a collector registered with
`VerificationRunner`.
