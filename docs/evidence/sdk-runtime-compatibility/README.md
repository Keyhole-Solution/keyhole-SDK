# SDK / Runtime Compatibility Evidence Bundle

**Story:** CE-V5-S41-03  
**SDK Version:** 0.2.0  
**Date:** 2026-03-10

## Contents

| File | Description |
|------|-------------|
| `compatibility-check.json` | Expected compatible output from `check_compatibility()` |
| `identity-parse.json` | Canonical identity from public surface contract, parseable by `RuntimeIdentity` |
| `receipt-parse.json` | Canonical receipt from public surface contract, parseable by `RealizationReceipt` |

## Typed Model Coverage

| Model | Public Endpoint | Verified |
|-------|----------------|----------|
| `RuntimeIdentity` | `GET /identity` | Yes |
| `RuntimeHealth` | `GET /healthz` | Yes |
| `RuntimeState` | `GET /state` | Yes |
| `RealizationRequest` | `POST /realize` (request) | Yes |
| `RealizationReceipt` | `POST /realize` (response) | Yes |
| `CompatibilityResult` | SDK method | Yes |
| `PublicError` | Error envelope | Yes |

## Private Field Verification

The following private/governance fields are verified as **never** required or exposed:

- `pointer_state`
- `promotion_state`
- `canonical_digest`
- `cluster_topology`
- `internal_lane`
- `controller_state`
- `governance_verdict`
- `drift_state`

Models strip these fields on parse. No SDK model declares any of them as a field.

## Example Convergence

`examples/python-client/example_typed.py` uses the typed SDK surface:

- `from keyhole_sdk import KeyholeClient, RuntimeIdentity, ...`
- `client.get_identity()` instead of raw `requests.get()`
- `client.check_compatibility()` for pre-flight validation
- `client.realize_typed()` for typed receipt handling
- Structured error handling with `TransportError`, `SchemaError`, etc.

## Test Results

55/55 tests passing across 10 test classes covering all 9 invariants.

## Release Compatibility Rules

Defined in `keyhole_sdk.compatibility.COMPATIBILITY_RULES` and documented in
`docs/specs/developer_ecosystem/sdk_runtime_compatibility.md`.
