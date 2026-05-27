# Operator Escalation: Gap STALE_REVALIDATION Blocker

**Date**: 2026-05-27  
**Reporter**: SDK client — cohort-0, tenant-6f4f45b96f64  
**Severity**: CRITICAL — blocks entire governance chain  
**Status**: Requires operator action  

---

## Summary

All gap submissions immediately enter `STALE_REVALIDATION` state. The required
action (`gaps.revalidate`) does not exist as a valid run type. There is no
client-side path to resolve this. The governance chain is fully blocked.

---

## Root Cause Analysis

### 1. Gap Reconciler Degraded

The gap reconciler is in **degraded** state due to `readiness_cache_mismatch`.
Evidence from `gaps.status`:

```json
{
  "canonical": {
    "current_canonical_digest": "sha256:6bbb6f5727a7f76ea26d875ce8780439abfd71d4f45838ca3f2a2e57f77b25bc",
    "last_reconcile_result": "degraded",
    "last_reconcile_reason": "readiness_cache_mismatch",
    "last_readiness_source": "cache",
    "last_readiness_source_reason": "readiness_cache_mismatch",
    "open_unrevalidated_count": 1,
    "stale_count": 11,
    "canonical_queue_open_count": 0
  }
}
```

### 2. Four Failing Keycloak Constitutional Invariants

Evidence from `readiness.explain` (run at 2026-05-27T07:09:00Z):

```json
{
  "constitutional": {
    "failed": [
      "INV-SDK-SERVER-01D-KEYCLOAK-DIGEST-PINNED",
      "INV-SDK-SERVER-01D-KEYCLOAK-PROVIDERS-PRESENT",
      "INV-SDK-SERVER-01D-KEYCLOAK-BROWSER-FLOW-CANONICAL",
      "INV-SDK-SERVER-01D-KEYCLOAK-FLOW-EXECUTIONS-REQUIRED"
    ]
  }
}
```

Out of 472 total invariants: 188 passing, **4 failing**, 280 skipped.

### 3. Probable Causal Chain

On **2026-05-20**, the Keycloak `kh-prod` realm was reconfigured (by platform
operator) to fix client token TTL issues:
- Access token TTL: changed to 900s  
- SSO Session Max: changed to 7 days  
- Refresh token rotation: enabled  

These changes invalidated the pinned Keycloak configuration that the 4
constitutional invariants validate against (`INV-SDK-SERVER-01D-KEYCLOAK-DIGEST-PINNED`
+ 3 derived checks). The constitutional digest changed, the reconciler
recomputed the canonical gap digest, and all existing and new gaps now fail
`STALE_REVALIDATION` because they reference the pre-change canonical.

### 4. Missing Run Type

The server returns `required_action.run_type: "gaps.revalidate"` in
`STALE_REVALIDATION` error messages. However, this run type does **not** exist
in the server's operation registry. Calling it returns:

```
UNKNOWN_RUN_TYPE: "gaps.revalidate"
```

The client scope list from `gaps:*` operations shows:
```
['connection:read', 'context:compile', 'gaps:claim', 'gaps:evidence',
 'gaps:read', 'gaps:submit', 'intent:submit', 'workspace:provision',
 'workspace:close']
```

`gaps:resolve` and `gaps:revalidate` are not in our allowed scopes.

---

## Evidence

| Item | Value |
|------|-------|
| Workspace | `ws:tenant-6f4f45b96f64:cohort-0:default` |
| Canonical digest | `sha256:6bbb6f5727a7f76ea26d875ce8780439abfd71d4f45838ca3f2a2e57f77b25bc` |
| Gap ID (stale) | `gap_7cde6c0a3a116eb3` |
| Reconciler state | degraded / readiness_cache_mismatch |
| Event Spine pending | 4,130 events |
| Constitutional evidence ref | `/opt/keyhole_evidence/runtime/system/constitutional/prod/unknown/constitutional_45fc816d2bf409f4.json` |
| Readiness explain run | `c5b835b8-3269-4227-a24f-33302e0efb72` |
| Gaps status run | `b0df7b50-ee71-42d0-8786-6bf7804adf1a` |

---

## Blocked Operations

| Operation | Scope | Result |
|-----------|-------|--------|
| `gaps.submit` | `gaps:submit` ✓ | Accepted but immediately STALE_REVALIDATION |
| `gaps.claim` | `gaps:claim` ✓ | ACCEPTED (run_id: null, no claim_token) |
| `gaps.revalidate` | N/A | UNKNOWN_RUN_TYPE — doesn't exist |
| `gaps.resolve` | `gaps:resolve` ✗ | SCOPE_DENIED |
| `convergence.status` | `runs:convergence` ✗ | SCOPE_DENIED |
| `workspace.provision` | `workspace:provision` ✓ | Blocked upstream (no claim_token) |

---

## Required Operator Actions

### Option A — Fix Keycloak Constitutional Invariants (Recommended)

The root cause is that 4 constitutional invariants are failing due to the May
20 Keycloak changes. The operator should:

1. Update the pinned Keycloak digest in `INV-SDK-SERVER-01D-KEYCLOAK-DIGEST-PINNED`
   to reflect the current Keycloak configuration state.
2. Verify that `INV-SDK-SERVER-01D-KEYCLOAK-PROVIDERS-PRESENT`,
   `INV-SDK-SERVER-01D-KEYCLOAK-BROWSER-FLOW-CANONICAL`, and
   `INV-SDK-SERVER-01D-KEYCLOAK-FLOW-EXECUTIONS-REQUIRED` pass after the
   digest is updated.
3. Once invariants pass, the readiness cache will stabilize, the reconciler
   will exit degraded state, and gaps submitted with the new canonical will
   be claimable.

### Option B — Implement `gaps.revalidate` Run Type

Implement the `gaps.revalidate` run type (referenced in STALE_REVALIDATION
error messages but absent from the server). The run type should:
- Accept `{gap_id: string, ctxpack_digest: string}` as input
- Update the gap's `revalidated_on_digest` to the provided digest
- Re-check claimability after revalidation
- Required scope: `gaps:claim` (already granted to our cohort)

### Option C — Grant `gaps:resolve` Scope (Partial Workaround)

Add `gaps:resolve` to cohort-0's binding scope list. This would allow the
client to close stale gaps. The client could then resubmit gaps once the
reconciler exits degraded state. This does NOT fix the reconciler degradation
but provides a cleanup path.

### Option D — Manual Advance

Operator manually sets gap `gap_7cde6c0a3a116eb3` to CLAIMED state with a
`claim_token` and returns the token out-of-band. This is a one-time workaround
while the structural fix is applied.

---

## Secondary Issue: `run_id: null` on ACCEPTED Responses

All ACCEPTED responses from `gaps.claim` return `run_id: null`. The client
cannot poll for the async result (claim_token). Even if the STALE_REVALIDATION
issue were resolved, the client would not be able to retrieve the `claim_token`
from an async claim operation.

**Required fix**: The `gaps.claim` run type must return a stable `run_id`
in its ACCEPTED response so the client can poll `/mcp/v1/runs/{run_id}` for
the claim_token.

Alternatively, make `gaps.claim` a synchronous operation that returns the
`claim_token` directly in the 200 response body.

---

## Client SDK Boundary Posture

Per the SDK boundary constitution, the client is NOT attempting to:
- Bypass the MCP boundary
- Simulate governance locally
- Cache decisions as authoritative

The client is correctly using governed run types through the MCP boundary.
The blocker is server-side. All discovery and identity checks were performed
in the correct order.
