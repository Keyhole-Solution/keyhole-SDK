# SDK / Runtime Compatibility Contract

**Version:** 1.0.0  
**Story:** CE-V5-S41-03  
**Owner:** Keyhole Solution Foundation  
**Last Updated:** 2026-03-10

---

## 1) Purpose

This document describes the compatibility relationship between
`keyhole-sdk` and the Keyhole public runtime contract. It defines
what guarantees the SDK provides, what changes are compatible or
breaking, and how compatibility is validated.

---

## 2) SDK / Runtime Relationship

The SDK is the **programmatic embodiment of the public contract**.

```
Public Runtime → typed SDK models → stable client API → developer code
```

The SDK models **only** the public contract. It does not expose,
require, or infer private governance internals.

---

## 3) Typed Public Models

The SDK provides typed Pydantic models for every public endpoint:

| Model | Endpoint | Description |
|-------|----------|-------------|
| `RuntimeIdentity` | `GET /identity` | Runtime ID, name, version, environment, capabilities |
| `RuntimeHealth` | `GET /healthz` | Health status |
| `RuntimeState` | `GET /state` | Current digest, realized digests, updated timestamp |
| `RealizationRequest` | `POST /realize` (request) | Candidate digest + payload |
| `RealizationReceipt` | `POST /realize` (response) | Digest, status, message, timestamp |
| `CompatibilityResult` | SDK method | Compatibility check outcome |
| `PublicError` | Error responses | Structured error envelope |

### Required Fields

**RuntimeIdentity:** `runtime_id`, `runtime_name`, `runtime_version`,
`environment`, `capabilities`

**RealizationReceipt:** `digest`, `status`, `message` (may be empty),
`realized_at`

**RuntimeState:** `updated_at`

---

## 4) Public Client Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `get_identity()` | `RuntimeIdentity` | Typed runtime identity |
| `get_health()` | `RuntimeHealth` | Typed runtime health |
| `get_state()` | `RuntimeState` | Typed runtime state |
| `realize_typed(digest, payload)` | `RealizationReceipt` | Typed realization |
| `check_compatibility()` | `CompatibilityResult` | SDK/runtime compatibility |

Legacy dict-returning methods (`identity()`, `health()`, `state()`,
`realize()`) remain available for backward compatibility.

---

## 5) Compatibility Check

The `check_compatibility()` method validates:

1. `/identity` returns all required fields
2. Identity response parses into `RuntimeIdentity` model
3. `/healthz` is reachable
4. `/state` is reachable and parseable (warning-only)

### Outcome Classes

| Status | Meaning |
|--------|---------|
| `compatible` | All required surfaces present and parseable |
| `compatible_with_warnings` | Core surfaces work; optional surfaces have issues |
| `incompatible` | Required surfaces missing or unparseable |

### Result Shape

```json
{
  "sdk_version": "0.2.0",
  "runtime_name": "Keyhole Test Runtime",
  "runtime_version": "0.1.0",
  "compatibility_status": "compatible",
  "checked_contract_version": null,
  "failures": [],
  "warnings": [],
  "checked_at": "2026-03-10T12:00:00+00:00"
}
```

---

## 6) Error Handling

The SDK distinguishes five error classes:

| Exception | Cause | Example |
|-----------|-------|---------|
| `TransportError` | Network/DNS/timeout | Connection refused |
| `RuntimeUnavailableError` | Runtime returned 5xx | Internal server error |
| `PublicEndpointError` | Runtime returned 4xx | Not found, unauthorized |
| `SchemaError` | Response shape mismatch | Missing required fields |
| `CompatibilityError` | Contract-level incompatibility | SDK/runtime diverged |

All inherit from `KeyholeSDKError`.

---

## 7) Public / Private Boundary

### Forbidden Private Fields

The following fields are **never** exposed by the SDK:

- `pointer_state`
- `promotion_state`
- `canonical_digest`
- `cluster_topology`
- `internal_lane`
- `controller_state`
- `governance_verdict`
- `drift_state`

If the runtime returns these fields, the SDK strips them silently.
The SDK never requires them.

---

## 8) Release Compatibility Rules

### 8.1 Compatible Changes

A change is **compatible** if it:

- Adds optional public fields
- Adds non-breaking helper behavior
- Preserves all required semantics
- Does not break existing typed model / client usage

### 8.2 Conditionally Compatible Changes

A change is **compatible-with-warnings** if it:

- Adds new public capabilities not yet modeled
- Adds optional surface details the SDK can safely ignore
- Preserves all existing required behavior

### 8.3 Incompatible Changes

A change is **incompatible** if it:

- Removes required public fields
- Renames required public fields
- Changes required field meaning
- Changes receipt semantics
- Changes environment/mode meaning
- Introduces reliance on private/internal fields

### 8.4 Promotion Rule

Incompatible drift must produce **REJECT** unless explicitly
coordinated through governed versioning and accompanying
SDK / docs / example updates.

---

## 9) Mode / Environment Semantics

The SDK exposes `environment` from the identity endpoint as-is.

- `"dev"` — development / test environment
- `"prod"` — production environment
- `"unknown"` — environment could not be determined

The SDK **never** infers:

- Private lane state
- Governance mode
- Cluster posture
- Controller state

If the runtime environment is unavailable, the SDK reports
it as `"unknown"` rather than guessing.

---

## 10) Receipt Semantics

The SDK exposes realization receipt fields exactly as declared:

- `digest` — the candidate digest
- `status` — `"ACCEPT"`, `"ALREADY_REALIZED"`, etc.
- `message` — human-readable context (may be empty)
- `realized_at` — ISO-8601 timestamp

The SDK **never** exposes:

- Governance verdicts
- Pointer state
- Canonical promotion state
- Private result classifications

A local-only receipt proves local realization. It does **not**
prove governed approval or Event Spine attestation.

---

## 11) How to Run Compatibility Check

### From Python

```python
from keyhole_sdk import KeyholeClient

with KeyholeClient(base_url="http://localhost:8080") as client:
    result = client.check_compatibility()
    print(result.compatibility_status.value)
```

### From CLI (standalone)

```bash
python -m keyhole_sdk.compatibility http://localhost:8080
```

### From CI

```bash
python -m keyhole_sdk.compatibility $RUNTIME_URL || exit 1
```

---

## 12) Version Alignment

| Component | Current Version |
|-----------|----------------|
| `keyhole-sdk` | 0.2.0 |
| `keyhole-cli` | 0.2.0 |
| Runtime contract | 0.1.0 |

Exact version alignment is not required. Declared compatibility
ranges must be truthful.
