# sdk-client-01-e.md

## SDK-CLIENT-01-E — Auto-Detection, MCP Boundary Probing, and Governed Mode Auto-Promotion

**Status:** COMPLETE
**Owner / Author:** Keyhole Solution Foundation
**Lane:** Dev
**Depends on:** SDK-CLIENT-01, SDK-CLIENT-01-A, SDK-CLIENT-01-C, SDK-CLIENT-01-D
**Evidence:** `tests/unit/test_sdk_client_01e_auto_detection.py` — 24/24 tests (commit `57bc996`)
**Purpose:** Add an `AUTO` operating mode that probes the MCP boundary at startup and automatically promotes the client to governed mode when the boundary is reachable and a valid MCP config is present, while preserving full backward compatibility for existing `local_only` and `governed` consumers.

---

## 1. Goal

Remove the manual burden of explicitly declaring `--mode governed` when the boundary is reachable. After this story:

- The client detects whether the MCP boundary is live by probing `https://mcp.keyholesolution.com` at startup
- If reachable + config present → the client self-promotes to governed mode transparently
- If unreachable → the client falls back to `local_only` and surfaces repair guidance
- `doctor` shows correct next-step guidance in AUTO mode
- Existing `local_only` and `governed` callers are unaffected

---

## 2. Problem Statement

Before this story, `OperatingMode` only had `local_only` and `governed`. Users had to know which mode applied and pass it explicitly. This created friction for first-run onboarding and any environment where connectivity varies.

Adding `AUTO` mode makes the client environment-aware without requiring the user to understand the operating mode concept at all. It matches the "first 10-minute rule": a user should receive a first governed interaction within 10 minutes of setup without configuring anything beyond installing the CLI.

---

## 3. Scope

### 3.1 In scope

- `OperatingMode.AUTO` added to the `OperatingMode` enum
- MCP boundary probe: `GET https://mcp.keyholesolution.com/mcp/v1/capabilities` with short timeout
- Auto-promotion logic: `local_only → governed` when probe succeeds and MCP config is present
- Runtime checks skip when boundary is live (no false-positive failure reports in governed mode)
- Expanded MCP config search to include VS Code host paths (`.vscode/mcp.json`, `~/.config/Code/User/mcp.json`, etc.)
- `doctor` command surfaces appropriate `next_steps` when in AUTO mode (connect, login, whoami)
- `EnvironmentFacts` extended with new fields: `mcp_boundary_reachable`, `mcp_config_paths_found`
- Backward compatibility: `local_only` and `governed` modes behave identically to before

### 3.2 Out of scope

- Automatic token acquisition (auth still requires explicit `keyhole login`)
- Auto-mode behavior for write-bearing dispatch (still requires explicit context)

---

## 4. Sections Covered by Tests

| § | Test class / description |
|---|--------------------------|
| §1 | `OperatingMode.AUTO` present and distinguishable from `local_only` and `governed` |
| §2 | MCP boundary probe fires during fact collection; reachable and unreachable paths both handled |
| §3 | Auto-promotion: reachable + config → governed; unreachable → local_only |
| §4 | Runtime checks (test-runtime availability) skip when MCP boundary is live |
| §5 | VS Code host config paths included in MCP config search |
| §6 | `doctor` next-steps surface correct guidance in AUTO mode |
| §7 | Backward compat: existing `local_only`-mode callers unaffected |
| §8 | New `EnvironmentFacts` fields (`mcp_boundary_reachable`, `mcp_config_paths_found`) default safely |

---

## 5. Implementation Files

| File | Change |
|------|--------|
| `packages/python/keyhole-sdk/keyhole_sdk/doctor/models.py` | Added `mcp_boundary_reachable: bool`, `mcp_config_paths_found: list[str]` to `EnvironmentFacts` |
| `packages/python/keyhole-sdk/keyhole_sdk/doctor/diagnostics.py` | Added auto-promotion logic, boundary-probe result consumption, runtime-check skip logic |
| `packages/python/keyhole-cli/keyhole_cli/doctor/facts.py` | Added MCP boundary probe, expanded config path search |
| `packages/python/keyhole-cli/keyhole_cli/doctor/handler.py` | Added AUTO mode next-steps surfacing |

---

## 6. Invariants

| ID | Invariant |
|----|-----------|
| INV-SDK-CLIENT-01-E-001 | AUTO mode must never claim governed status without a successful live boundary probe. |
| INV-SDK-CLIENT-01-E-002 | Probe failure must not crash the client — fall back to `local_only` silently with guidance. |
| INV-SDK-CLIENT-01-E-003 | AUTO-mode promotion is diagnostic only — it does not bypass the auth requirement. |
| INV-SDK-CLIENT-01-E-004 | `local_only` and `governed` modes must not be affected by the presence of AUTO mode. |
| INV-SDK-CLIENT-01-E-005 | New `EnvironmentFacts` fields must be backward-compatible — consumers that ignore them must not break. |

---

## 7. Evidence

**Test file:** `tests/unit/test_sdk_client_01e_auto_detection.py`
**Test count:** 24/24
**Commit:** `57bc996` — "Add unit tests for SDK-CLIENT-01-E: Auto-detection and MCP boundary probing"

All 24 tests pass as of commit `57bc996`.

---

## 8. Dependencies

### Depends on
- SDK-CLIENT-01 — login baseline
- SDK-CLIENT-01-A — hardened identity conformance
- SDK-CLIENT-01-C — doctor/reconciliation surface
- SDK-CLIENT-01-D — host inventory and credential installation

### Unlocks
- First-run onboarding with zero configuration (auto-detect + auto-promote)
- CI/CD environments where the boundary may or may not be reachable without requiring explicit mode flags
