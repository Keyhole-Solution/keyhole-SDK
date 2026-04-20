# SDK-SERVER-01-C — Server Agent Handoff

**From:** SDK-CLIENT-01-C (client-side implementation, `keyhole-SDK` repo)  
**To:** SDK-SERVER-01-C (server-side implementation, `keyhole_platform` repo)  
**Date:** 2026-04-17  
**Prepared by:** Client-side implementation agent post north-south traffic proof  
**Paired Story:** `SDK-CLIENT-01-C — MCP Host Identity Reconciliation, Doctor Discovery, and Connection Binding UX`

---

## 1. Why This Handoff Exists

The client-side story (SDK-CLIENT-01-C) is fully implemented and all 148 unit
tests pass.  A live north-south traffic proof was run against
`https://mcp.keyholesolution.com` on 2026-04-17.

**The proof confirmed:**

- Transport: working (auth, capabilities discovery, whoami all succeed)
- Dispatch pipeline: working (`context.compile` round-trips successfully)
- Connection feature flags: all enabled on the live server
- Connection run types: **not yet registered in the server scope mapping**

Every SDK request for a connection run type reaches the server and returns
`UNKNOWN_RUN_TYPE` — not a transport failure.  The client is ready and
waiting.  The server work is the blocker.

---

## 2. Current Server State (verified 2026-04-17)

### 2.1 Feature flags (capabilities response, `data.feature_flags`)

| Flag | Value |
|------|-------|
| `connection_identity_truth` | `true` |
| `connection_rebind` | `true` |
| `connection_lineage` | `true` |
| `stale_connection_detection` | `true` |

All four flags are **already live in production**.  They signal the intended
surface but the run-type handlers are not wired.

### 2.2 Scope mapping (confirmed by dispatch)

None of the six connection run types appear in the server's scope mapping.
Every dispatch attempt returns:

```json
{
  "ok": false,
  "data": {
    "status": "blocked",
    "message": "Unknown run_type: connection.identity.inspect (not in scope mapping)"
  },
  "error": {
    "code": "UNKNOWN_RUN_TYPE"
  }
}
```

### 2.3 Operations counts (capabilities)

| Field | Value |
|-------|-------|
| `operations_declared` | 30 |
| `operations_implemented` | 12 |
| `unimplemented_ops` | 18 (none are connection ops — they are not even declared) |

The connection run types are absent from **both** declared and implemented counts.
They do not appear anywhere in capabilities — only the feature flags hint at them.

### 2.4 Evidence event

A proof event was emitted to the Event Spine during the north-south proof:

```
event_id: 26bd9e85-6251-46cf-aa0f-d8983ed8cf4e
correlation_id: 85cf4049-e603-4bd7-ad7b-d974f9a4e03f
type: sdk.client.01c.north_south_proof
subject: ev.ops.customgpt
published_at: 2026-04-17T11:15:48Z
```

---

## 3. What the Server Must Implement

### 3.1 Run types required

Six run types must be registered in the server scope mapping and implemented:

| Run Type | Kind | Auth Required | Write-Bearing |
|----------|------|--------------|---------------|
| `connection.list.inspect` | read | yes | no |
| `connection.identity.inspect` | read | yes | no |
| `connection.status.inspect` | read | yes | no |
| `connection.lineage.inspect` | read | yes | no |
| `connection.rebind` | write | yes | yes |
| `connection.invalidate` | write | yes | yes |

All six must appear in `GET /mcp/v1/capabilities` under `operations_declared`
(and `operations_implemented` once wired) so the SDK's surface-negotiation
check (`check_connection_surfaces_available()`) passes.

### 3.2 Read-only run types (inspect surface)

#### `connection.identity.inspect`

Returns the active governed principal currently bound to a connection or
resolved from the requesting session.

**Request shape:**
```json
{
  "run_type": "connection.identity.inspect",
  "parameters": {
    "connection_id": "<optional — if omitted, use session-resolved connection>",
    "host_hint": "<optional — e.g. 'vscode', 'jetbrains'>",
    "correlation_id": "<optional>"
  }
}
```

**Response shape (inside `data`):**
```json
{
  "run_id": "run_...",
  "status": "ok",
  "connection_id": "conn_...",
  "principal": {
    "user_id": "usr_...",
    "username": "nathan@example.com",
    "tenant_id": "acme",
    "display_label": "nathan"
  },
  "authority": "session_bound",
  "bound_at": "2026-04-17T10:00:00Z",
  "session_lineage_id": "lin_...",
  "purpose": "mcp_host",
  "origin": {
    "host_hint": "vscode",
    "surface_id": "vscode-copilot"
  },
  "staleness": {
    "state": "fresh",
    "stale_since": null,
    "last_verified_at": "2026-04-17T10:00:00Z"
  },
  "rebind_supported": true,
  "invalidate_supported": true
}
```

**Error cases:**
- `CONNECTION_NOT_FOUND` — no connection matches the given id or session
- `AMBIGUOUS_CONNECTION` — multiple unresolvable connections for session
- `CONNECTION_IDENTITY_UNAVAILABLE` — connection exists but identity cannot be resolved

---

#### `connection.list.inspect`

Returns all connections currently visible to the acting principal (or tenant,
depending on authority level).

**Request shape:**
```json
{
  "run_type": "connection.list.inspect",
  "parameters": {
    "host_hint": "<optional filter>",
    "include_stale": true,
    "page_size": 50,
    "page_token": "<optional>"
  }
}
```

**Response shape (inside `data`):**
```json
{
  "run_id": "run_...",
  "status": "ok",
  "connections": [
    {
      "connection_id": "conn_...",
      "host_hint": "vscode",
      "principal": {
        "user_id": "usr_...",
        "display_label": "nathan"
      },
      "authority": "session_bound",
      "bound_at": "2026-04-17T09:00:00Z",
      "staleness_state": "fresh",
      "rebind_supported": true,
      "invalidate_supported": true,
      "purpose": "mcp_host"
    }
  ],
  "total": 1,
  "page_token": null
}
```

---

#### `connection.status.inspect`

Returns a lightweight liveness/health summary for a connection without full
identity detail.

**Request shape:**
```json
{
  "run_type": "connection.status.inspect",
  "parameters": {
    "connection_id": "<required>",
    "correlation_id": "<optional>"
  }
}
```

**Response shape (inside `data`):**
```json
{
  "run_id": "run_...",
  "status": "ok",
  "connection_id": "conn_...",
  "alive": true,
  "staleness_state": "fresh",
  "last_seen_at": "2026-04-17T10:00:00Z",
  "principal_visible": true,
  "rebind_supported": true
}
```

---

#### `connection.lineage.inspect`

Returns the causal history of how the current connection's identity came to be
— auth events, rebinds, logins, profile switches that affected this
connection.

**Request shape:**
```json
{
  "run_type": "connection.lineage.inspect",
  "parameters": {
    "connection_id": "<optional — session-resolved if omitted>",
    "host_hint": "<optional>",
    "limit": 20,
    "correlation_id": "<optional>"
  }
}
```

**Response shape (inside `data`):**
```json
{
  "run_id": "run_...",
  "status": "ok",
  "connection_id": "conn_...",
  "lineage": [
    {
      "event_type": "connection.bound",
      "occurred_at": "2026-04-17T08:00:00Z",
      "principal_at_event": "nathan",
      "correlation_id": "corr_...",
      "source": "login_flow"
    },
    {
      "event_type": "connection.rebind_accepted",
      "occurred_at": "2026-04-17T09:30:00Z",
      "principal_at_event": "paul",
      "correlation_id": "corr_...",
      "source": "keyhole_cli"
    }
  ],
  "total_events": 2
}
```

**Sources:** The Event Spine is the authoritative source for lineage.
This run type must query the event spine for connection-scoped events.
If the Event Spine shows no lineage, return an empty `lineage` array —
do not fabricate entries.

---

### 3.3 Write-bearing run types

Both write-bearing run types are idempotent.  The server must honor
`X-Idempotency-Key` and `X-Request-Id` and replay prior outcomes for
duplicate keys rather than double-executing.

#### `connection.rebind`

Moves a live connection from its current principal to a target principal
specified by the caller.

**Request shape:**
```json
{
  "run_type": "connection.rebind",
  "parameters": {
    "connection_id": "<required>",
    "target_user_id": "<required — new principal>",
    "target_profile_label": "<optional — human-readable label>",
    "reason": "<optional — caller note for audit>",
    "correlation_id": "<optional>"
  }
}
```

**Response shape (inside `data`):**
```json
{
  "run_id": "run_...",
  "status": "rebound",
  "connection_id": "conn_...",
  "old_principal": {
    "user_id": "usr_nathan",
    "display_label": "nathan"
  },
  "new_principal": {
    "user_id": "usr_paul",
    "display_label": "paul"
  },
  "rebound_at": "2026-04-17T10:00:00Z",
  "idempotency_key": "<echo of X-Idempotency-Key>",
  "replay": false
}
```

**Terminal statuses the client must handle:**

| Status | Meaning |
|--------|---------|
| `rebound` | Synchronous success, principal changed |
| `accepted` | Async accepted, not yet applied — poll for result |
| `replayed` | Identical idempotency key, outcome replayed from prior run |
| `rejected` | Server refused: target principal not valid, access denied, etc. |
| `deferred` | Execution queued — connection not currently live |

**Error codes:**
- `CONNECTION_NOT_FOUND` — no connection for given id
- `REBIND_FORBIDDEN` — caller lacks authority to rebind this connection
- `TARGET_PRINCIPAL_INVALID` — target user does not exist or is not eligible
- `REBIND_UNSUPPORTED` — this connection type does not support rebind

**Authority requirement:** The caller must have authority over the connection
(own it, or have operator/tenant-admin authority).  Worker/service-account
principals must not be allowed to rebind human-owned connections unless
explicitly granted.

**Event spine:** Emit a `connection.rebind_accepted` (or `connection.rebind_rejected`)
event to the event spine for every non-replayed dispatch.

---

#### `connection.invalidate`

Terminates a connection's authority, forcing the host to reconnect from
scratch.  Does not switch the principal in place — kills the existing
connection context.

**Request shape:**
```json
{
  "run_type": "connection.invalidate",
  "parameters": {
    "connection_id": "<required>",
    "reason": "<optional — audit note: 'stale', 'wrong_principal', etc.>",
    "correlation_id": "<optional>"
  }
}
```

**Response shape (inside `data`):**
```json
{
  "run_id": "run_...",
  "status": "invalidated",
  "connection_id": "conn_...",
  "invalidated_at": "2026-04-17T10:00:00Z",
  "idempotency_key": "<echo>",
  "replay": false,
  "reconnect_required": true
}
```

**Terminal statuses the client must handle:**

| Status | Meaning |
|--------|---------|
| `invalidated` | Connection killed, host must reconnect |
| `accepted` | Async accepted, not yet applied |
| `replayed` | Prior idempotency key, outcome echoed |
| `rejected` | Server refused (already invalidated, access denied) |
| `already_invalidated` | Connection was not live at dispatch time |

**Event spine:** Emit `connection.invalidated` event for every non-replayed
dispatch.

---

## 4. Scope Mapping Registration

The server must register all six run types in its scope mapping so they are
returned in the `UNKNOWN_RUN_TYPE` valid-run-types list and appear in
`GET /mcp/v1/capabilities` operations.

The capabilities response must show them as `implemented: true` once wired.
The client uses `check_connection_surfaces_available()` which checks that the
server's operations list includes `connection.identity.inspect`.  Until that
check passes, `doctor` will report `surface_unavailable` for all hosts.

Minimum capabilities entry per run type:
```json
{
  "run_type": "connection.identity.inspect",
  "implemented": true,
  "read_only": true,
  "tenant_scoped": true,
  "auth_required": true
}
```

---

## 5. What the Client Already Does (do not duplicate)

The SDK client is fully implemented.  The server should not re-implement any
of this:

| Client module | What it does |
|---------------|-------------|
| `keyhole_sdk/connection_identity/client.py` | Dispatches all 6 run types via `POST /mcp/v1/runs/start` with idempotency headers |
| `keyhole_sdk/connection_identity/render.py` | Parses and renders server responses for CLI output |
| `keyhole_sdk/connection_identity/repair.py` | Builds repair guidance from server error codes |
| `keyhole_sdk/connection_identity/models.py` | Typed Pydantic models for all response shapes |
| `keyhole_sdk/doctor/reconciliation.py` | Run type constants, surface availability check, reconciliation logic |
| `keyhole_cli/commands/connection_inspect.py` | `keyhole connection inspect` CLI command |
| `keyhole_cli/commands/connection_lineage.py` | `keyhole connection lineage` CLI command |
| `keyhole_cli/commands/connection_rebind.py` | `keyhole connection rebind` CLI command |
| `keyhole_cli/commands/connection_invalidate.py` | `keyhole connection invalidate` CLI command |
| `keyhole_cli/commands/connections_list.py` | `keyhole connections list` CLI command |

**SDK constants** (must match server exactly):

```python
CONNECTION_LIST_RUN_TYPE      = "connection.list.inspect"
CONNECTION_INSPECT_RUN_TYPE   = "connection.identity.inspect"
CONNECTION_STATUS_RUN_TYPE    = "connection.status.inspect"
CONNECTION_LINEAGE_RUN_TYPE   = "connection.lineage.inspect"
CONNECTION_REBIND_RUN_TYPE    = "connection.rebind"
CONNECTION_INVALIDATE_RUN_TYPE = "connection.invalidate"
```

---

## 6. Required Error Code Contract

The client's `repair.py` module maps the following server error codes to
repair guidance.  These must be exact — any deviation breaks repair UX:

| Error code | Client interpretation |
|------------|----------------------|
| `CONNECTION_NOT_FOUND` | Connection is not visible or not owned |
| `AMBIGUOUS_CONNECTION` | Session maps to multiple connections — needs explicit `connection_id` |
| `CONNECTION_IDENTITY_UNAVAILABLE` | Connection exists but identity lookup failed |
| `SURFACE_UNAVAILABLE` | Run type not implemented on this server |
| `REBIND_FORBIDDEN` | Caller cannot rebind this connection |
| `REBIND_UNSUPPORTED` | Connection type does not allow rebind |
| `TARGET_PRINCIPAL_INVALID` | Requested rebind target does not exist or is not eligible |
| `INVALIDATE_FORBIDDEN` | Caller cannot invalidate this connection |
| `VERIFICATION_FAILED` | Post-fix inspection returned unexpected principal |

---

## 7. Idempotency Contract (mandatory for write-bearing runs)

The client attaches two headers to every request:

```
X-Idempotency-Key: <uuid — generated once per logical operation, reused across retries>
X-Request-Id:      <uuid — per physical HTTP request>
```

For `connection.rebind` and `connection.invalidate`, the server must:

1. On first receipt: execute and store outcome keyed by `X-Idempotency-Key`
2. On duplicate receipt (same key): return stored outcome with `"replay": true`
3. Never re-execute a completed write-bearing ran with the same idempotency key

This is enforced by INV-SDK-CLIENT-01-C-006 on the client side.

---

## 8. Async Execution Contract

The client correctly handles both synchronous and asynchronous outcomes.
`connection.rebind` and `connection.invalidate` may return `"accepted"` for
deferred execution.  The client surfaces this to the builder:

```text
→ ACCEPTED (run_id=run_abc123)
  Use 'keyhole run status run_abc123' to check progress.
```

The server must:
- return `run_id` in every response
- support status polling via the existing runs infrastructure
- not pretend async operations are synchronous

---

## 9. Connection Identity Authority Model

For the server implementation, the authority model must address:

### 9.1 Who can read connection identity?

- The authenticated principal owning the connection (always allowed)
- Tenant admins for connections in their tenant
- Service accounts with `connections:inspect` scope

### 9.2 Who can rebind?

- The human owner of the connection (requires human auth, not worker token)
- Tenant admins
- **Not** arbitrary service accounts or workers without explicit grant

### 9.3 Who can invalidate?

- Same as rebind authority — but note that invalidation is less sensitive
  (it does not transfer authority, it terminates it)
- Consider allowing self-invalidation more broadly than rebind

### 9.4 How is connection_id resolved?

If no `connection_id` is given in the request parameters, the server resolves
it from the authenticated session:

1. Look up the connection associated with the bearer token's session
2. If exactly one connection → use it
3. If zero → `CONNECTION_NOT_FOUND`
4. If multiple and unresolvable → `AMBIGUOUS_CONNECTION`

---

## 10. Relationship to Existing Platform Surfaces

These run types are extensions of the existing auth/identity model, not
replacements.

- `GET /mcp/v1/whoami` — reports identity of the **bearer token** caller, not
  the **connection** principal.  These are the same only when the IDE has
  reauthenticated.  The new run types expose the **connection-bound**
  principal, which may differ.

- `bindings.cohort.get` / `bindings.cohort.upsert` — cohort binding is
  distinct from connection identity.  These run types are not related.

- `auth.status` — reports token lifecycle state, not connection binding.

The key insight: a builder may log in fresh (new token), but the IDE's live
MCP connection still executes under the old session's principal.  Only the
connection run types can surface that split.

---

## 11. Priority Order for Implementation

Implement in this order to make the client testable incrementally:

1. **`connection.identity.inspect`** — highest value; unlocks `keyhole connection inspect` and all `doctor` check flows.  Without this, all doctor checks report `surface_unavailable`.

2. **`connection.list.inspect`** — unlocks `keyhole connections list`.

3. **`connection.rebind`** — unlocks the write-bearing reconciliation flow.

4. **`connection.invalidate`** — paired with rebind, lower-risk write operation.

5. **`connection.lineage.inspect`** — event-spine-backed, can be added after the core surface stabilises.

6. **`connection.status.inspect`** — lowest priority; lightweight companion to inspect, useful for polling but not required for first-run success.

Register each in the scope mapping as it lands.  The SDK's surface check only
requires `connection.identity.inspect` to be present to pass.

---

## 12. Validation Steps After Server Implements

Once the server wires the run types, the following must be true:

### 12.1 Capabilities check passes

```http
GET /mcp/v1/capabilities
```

`data.operations` (or equivalent) must include `connection.identity.inspect`
with `implemented: true`.

### 12.2 SDK surface check passes

```python
from keyhole_sdk.doctor.reconciliation import check_connection_surfaces_available
from keyhole_sdk.capabilities.client import CapabilitiesClient

caps = CapabilitiesClient().fetch()
result = check_connection_surfaces_available(caps.operations)
assert result.available == True
```

### 12.3 Live round-trip succeeds

```http
POST /mcp/v1/runs/start
Authorization: Bearer <token>
X-Idempotency-Key: <uuid>
X-Request-Id: <uuid>
Content-Type: application/json

{
  "run_type": "connection.identity.inspect",
  "parameters": {}
}
```

Expected: `200 OK`, `ok: true`, `data.status: "ok"`, `data.connection_id` present.

### 12.4 CLI round-trip succeeds

```bash
keyhole connection inspect
# → displays connection principal, authority, bound_at, staleness
```

### 12.5 Rebind round-trip succeeds with ACCEPTED or rebound

```bash
keyhole connection rebind --connection-id conn_xxx --profile paul --yes
# → status: rebound | accepted
```

### 12.6 Doctor reports aligned or split_identity (not surface_unavailable)

```bash
keyhole doctor
# → no longer shows "surface_unavailable" for connection identity
```

---

## 13. Acceptance Criteria Reference (from SDK-CLIENT-01-C §18)

These criteria close when both sides are implemented:

| # | Criterion | Client | Server |
|---|-----------|--------|--------|
| 18.1 | Host inventory | ✅ | n/a |
| 18.2 | Split identity visible | ✅ | needs `connection.identity.inspect` |
| 18.3 | No false convergence claim | ✅ | n/a |
| 18.4 | Surface-aware degradation | ✅ | needs ops in capabilities |
| 18.5 | Explicit rebind | ✅ (dispatches) | needs `connection.rebind` handler |
| 18.6 | Verification after fix | ✅ | needs `connection.identity.inspect` |
| 18.7 | Safe non-interactive mode | ✅ | n/a |
| 18.8 | Repo neutrality | ✅ | n/a |
| 18.9 | Surface discipline | ✅ | needs run types in scope mapping |

---

## 14. Invariants the Server Must Honor

From `SDK-CLIENT-01-C §20`:

| Invariant | Server obligation |
|-----------|------------------|
| INV-001 — Split identity is visible | `connection.identity.inspect` must return the actual bound principal, not the caller's token principal |
| INV-002 — Login is not rebind | Do not automatically rebind connections on `auth.login_complete` — keep them separate operations |
| INV-004 — Reconciliation is server-verified | `connection.identity.inspect` must reflect actual post-rebind state when polled after a rebind |
| INV-006 — Rebind/invalidate are idempotent | Honor `X-Idempotency-Key`; return `replay: true` on duplicate keys |

---

## 15. Summary

| Aspect | State |
|--------|-------|
| Client implementation | Complete (148 tests passing) |
| Feature flags on server | All enabled (`connection_identity_truth`, `connection_rebind`, `connection_lineage`, `stale_connection_detection`) |
| Transport / auth / dispatch | Proven working against live production boundary |
| Connection run types registered | **Not yet** — `UNKNOWN_RUN_TYPE` on all six |
| Blocker for full closure | Server must register and implement all six run types |
| First priority | `connection.identity.inspect` — unlocks the most client flows |

The client will work without modification once the server registers the run
types.  Nothing on the SDK side needs to change.
