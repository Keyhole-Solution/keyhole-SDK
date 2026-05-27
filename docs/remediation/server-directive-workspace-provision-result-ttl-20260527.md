# Server Directive — Two-Plane Run Result Persistence + Gap Stale Regression (2026-05-27)

**Priority:** CRITICAL  
**Status:** OPEN — blocking entire gap→workspace→proof chain  
**Realm:** `kh-prod`  
**Platform:** `https://mcp.keyholesolution.com`  
**Raised by:** SDK client investigation — session `982489b3-e0d2-470e-858f-0cac6e22c04f`  
**Raised:** 2026-05-27T12:15Z  
**Updated:** 2026-05-27T12:30Z — scope expanded: `gaps.claim` also affected; gap goes STALE immediately  
**Related directive:** `server-directive-gap-reconciler-degraded-20260527.md` (PR #341 deployed, but introduced this regression)

---

## Problem Statement

There are **two independent regressions** blocking the full gap→claim→workspace→proof chain, both introduced after the PR #341 deployment:

### Regression A — All two-plane run results have TTL ≈ 0

Any run dispatched with `dispatch_mode: "two_plane"` returns a `run_id` (202 ACCEPTED) but the result is **never stored** in the result backend. Polling `GET /mcp/v1/runs/<run_id>` returns `not_found` from 50ms through 8s+.

**Affected run types:**
- `gaps.claim`
- `workspace.provision`
- `gaps.submit` (unconfirmed but `keyhole runs wait` timed out for this too)

**Not affected (synchronous or single-plane):**
- `gaps.get`
- `gaps.list`
- `gaps.status`
- `context.compile`

### Regression B — Gaps transition to STALE immediately after creation

A newly submitted gap (`gap_810669d1c41e2041`) transitioned from OPEN to STALE **4 minutes** after creation, despite:
- The gap's `meta.ctxpack_digest` matching the current canonical digest exactly
- No competing gap for the same capability
- No evidence of revalidation failure

This means even if claim results were visible (Regression A fixed), the gap would be unclaim-able because it is STALE.

---

## Evidence

### Regression A — Two-plane run results not stored

#### Timeline of all affected run IDs (12:11–12:30 UTC, 2026-05-27)

| Run ID | Run type | Dispatch time | Result visible? |
|---|---|---|---|
| `run_8114deb49f4c` | `workspace.provision` | ~12:05 (pre-fix session) | ❌ never |
| `run_0fed14d9f80f` | `workspace.provision` | ~12:11 | ❌ never (200 polls, 635s) |
| `run_59696983dbcc` | `workspace.provision` | ~12:12 | ❌ never (50ms–8s) |
| `run_d117a3d0cad3` | `gaps.submit` | 12:19:29 | ❌ never (15 polls, 33s) |
| `run_cfc3943bb1ae` | `gaps.claim` | ~12:21 | ❌ unknown after 3s |
| `run_2a2a681674b7` | `gaps.claim` | ~12:22 | ❌ never (50ms–8s) |
| `run_2fb4811069f0` | `workspace.provision` | ~12:22 | ❌ never (50ms–8s) |
| `run_9ea37435f37f` | `gaps.claim` | 12:24:33 | ❌ never (10 polls, 22s) |
| `run_37435c5aeb76` | `gaps.claim` | ~12:26 | ❌ never (50ms–8s) |
| `run_0e8b05c5027c` | `workspace.provision` | ~12:26 | ❌ never (50ms–8s) |

All `dispatch_mode: "two_plane"` runs return `not_found` for all polling attempts.

#### Wire format from server response (confirmed `dispatch_mode: "two_plane"`)

```json
{
  "ok": true,
  "data": {
    "run_id": "run_37435c5aeb76",
    "correlation_id": "17b118b2-8272-4ae9-ae93-dc23fb7e8da",
    "status": "accepted",
    "poll_url": "/mcp/v1/runs/run_37435c5aeb76",
    "message": "Run gaps.claim accepted for background execution."
  },
  "meta": {
    "dispatch_mode": "two_plane",
    "run_type": "gaps.claim",
    "budget_envelope": {
      "max_wall_ms": 120000
    }
  }
}
```

#### gaps.claim side effects absent

After 6+ `gaps.claim` dispatches against `gap_810669d1c41e2041`:
```
gaps.status → CLAIMED: 0  (gap never transitions to CLAIMED)
gaps.get    → claimed_by: null, claim_expires_ts: null
```

### Regression B — Gap goes STALE immediately

Gap submission at **12:19:30**:
```json
{
  "gap_id": "gap_810669d1c41e2041",
  "status": "OPEN",
  "meta": {
    "ctxpack_digest": "6d8f24eac06e4547d0f73645ec1709a1763d742eb5eee62149b2269bcab5f818"
  }
}
```

Canonical digest from `gaps.status` at same time:
```
"current_canonical_digest": "sha256:6d8f24eac06e4547d0f73645ec1709a1763d742eb5eee62149b2269bcab5f818"
```

Digests are **identical** (modulo `sha256:` prefix which is a formatting difference).

After reconciler cycle at **12:23:52** (4 minutes later):
```
gaps.status → OPEN: 0, STALE: 12 (was 11)
gaps.get    → status: "STALE"
```

**The gap was moved to STALE despite having the current canonical digest.**

This is the same behavior that prompted the previous directive (`server-directive-gap-reconciler-degraded-20260527.md`). The PR #341 fix may not have fully resolved the reconciler's stale detection logic.

---

## Root Cause Hypotheses

### Regression A — Two-plane result storage

The `dispatch_mode: "two_plane"` executor **dispatches runs to a background plane** but does not write the result to the result store (`GET /mcp/v1/runs/<run_id>`) after completion.

Possible causes:
1. PR #341 changed the result-store write path for two-plane runs and broke the write (none of the results persist)
2. A result TTL of 0 was set during the PR #341 deployment, immediately expiring all results
3. The two-plane executor's result callback is misconfigured or silently erroring

Evidence for #1: before PR #341 deployment, `gaps.claim` results were accessible after ~1-2s. After deployment, they are not.

### Regression B — Gap stale detection

The reconciler is using the `sha256:` prefix as part of the digest comparison, causing a mismatch between:
- Gap's stored digest: `6d8f24eac06e4547d0f73645ec1709a1763d742eb5eee62149b2269bcab5f818` (no prefix)
- Canonical digest: `sha256:6d8f24eac06e4547d0f73645ec1709a1763d742eb5eee62149b2269bcab5f818` (with prefix)

If the reconciler does a string equality check without normalizing, this would cause all SDK-submitted gaps to immediately go STALE. This is likely the same root cause as the original gap-reconciler degraded issue (which the PR #341 was supposed to fix).

---

## Impact

Without these fixes, the full gap→claim→workspace→proof chain is **completely blocked**:

1. Gaps submitted with correct digest → immediately go STALE (Regression B)
2. Claims cannot succeed against STALE gaps
3. Even if somehow claimed, the claim result is invisible (Regression A)
4. `workspace.provision` results are also invisible (Regression A)
5. Identity never exits the neutral default workspace

The client-side changes from PR #341 are complete and correct. The only remaining blockers are server-side.

---

## What the Backend Team Must Do

### Action 1 (CRITICAL) — Fix two-plane result persistence

The `dispatch_mode: "two_plane"` result store write must be repaired. For every run that accepts a `two_plane` dispatch, the result must be written to the result backend and accessible via:

```
GET /mcp/v1/runs/<run_id>
```

For at least **120 seconds** after the 202 response (matching the `max_wall_ms: 120000` budget envelope).

This is likely a regression from PR #341 (`78bb1cf1`, `sdk-server-workspace-provision-repair`). Check what the PR changed in the two-plane executor's result callback.

### Action 2 (CRITICAL) — Fix reconciler digest normalization

The reconciler must normalize digests before comparison. Both:
- `6d8f24eac06e4547d0f73645ec1709a1763d742eb5eee62149b2269bcab5f818`
- `sha256:6d8f24eac06e4547d0f73645ec1709a1763d742eb5eee62149b2269bcab5f818`

must be treated as equivalent.

Additionally, a gap submitted with the **current canonical digest** must remain OPEN (not transition to STALE) until:
- It is claimed, provisioned, or manually closed
- The canonical digest advances and the gap's digest is no longer current

### Action 3 (REQUIRED) — Revalidate or reset gap_810669d1c41e2041

The gap `gap_810669d1c41e2041` (capability `my-first-app.greet.user.v1`) is currently STALE despite having a matching digest. It should be:

Option A: Moved back to OPEN by the operator  
Option B: Revalidated by the reconciler after Action 2 is deployed  

### Action 4 (NICE-TO-HAVE) — Return workspace_id in provision result

When `workspace.provision` succeeds (after Action 1 fixes result persistence), the result should contain:

```json
{
  "status": "ok",
  "workspace_id": "ws:tenant-...:cohort-0:my-first-app",
  "repo": "my-first-app",
  "gap_id": "gap_810669d1c41e2041"
}
```

---

## Acceptance Criteria

1. `GET /mcp/v1/runs/<run_id>` returns a non-null result within 30 seconds for `gaps.claim` and `workspace.provision`
2. After `gaps.claim` succeeds: `gaps.get` shows `status: "CLAIMED"` and `claimed_by: <user_id>`
3. A gap submitted with the current canonical digest remains OPEN through at least one reconciler cycle
4. `keyhole gaps claim --gap-id <id>` followed by `keyhole workspace provision --repo my-first-app --gap-id <id>` completes the full chain within 60s
5. After successful provision: `keyhole whoami` shows a non-neutral workspace_id

---

## Reproduction Steps

```bash
# 1. Submit a new gap
keyhole gaps create --capability my-first-app.greet.user.v1 --repo-dir my-first-app --json
# → ACCEPTED run_id=<submit_run_id>

# 2. Wait for gap to appear (gaps.status will show OPEN: 1)
# But: after ~4 min reconciler cycle → STALE (Regression B)

# 3. Attempt to claim
keyhole gaps claim --gap-id <gap_id> --json
# → ACCEPTED run_id=<claim_run_id>

# 4. Check claim result — always not_found (Regression A)
keyhole runs wait <claim_run_id> --max-polls 10
# → wait_timeout: "Run did not reach terminal state after 10 polls"

# 5. Check gap state — still OPEN/STALE, never CLAIMED
gaps.get {gap_id} → status: "OPEN" or "STALE", claimed_by: null
```

---

## Client-Side Status

The SDK/CLI client side is **complete and correct**:
- `--claim-token` is now Optional (merged this session)
- New error handlers for `GAP_NOT_FOUND`, `GAP_NOT_CLAIMED`, `CLAIM_EXPIRED`, `CLAIM_OWNER_MISMATCH`
- `keyhole runs wait` uses correct polling pattern
- Wire format (`"repo"`, `"input"`, `"ctxpack_digest"`) confirmed correct via raw HTTP probes

**No further client changes are needed.** Only server-side fixes (Actions 1–3) are blocking.
