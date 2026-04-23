# sdk-client-01-c.md

## SDK-CLIENT-01-C — MCP Host Identity Reconciliation, Doctor Discovery, and Connection Binding UX

**Status:** COMPLETE
**Owner / Author:** Keyhole Solution Foundation
**Lane:** Dev (design + validation), Prod (promotion only)
**Depends on:** SDK-CLIENT-01, SDK-CLIENT-01-B, SDK-CLIENT-15, SDK-CLIENT-20, SDK-CLIENT-21
**Paired With:** SDK-SERVER-01-C — Connection-Scoped Identity Authority, Rebind, and Stale-Connection Truth via Governed Runs
**Purpose:** Define the client-side UX, discovery, diagnostics, and governed reconciliation flow for installed MCP hosts and other long-lived local clients so builders can detect split identity, inspect the true active connection principal, and explicitly rebind or invalidate stale host connections without unsafe hidden mutation.

---

## 1. Goal

Close the builder-side gap exposed by installed IDE MCP servers and other long-lived local hosts that continue executing under a stale or different principal after the builder logs in, switches profiles, or rotates credentials elsewhere.

This story makes the following true:

* the builder can inventory local Keyhole-relevant host environments,
* the builder can see which installed MCP hosts are present,
* the builder can compare:

  * current CLI profile,
  * current SDK credential context,
  * active server-reported connection identity for each host,
* split identity becomes visible and explainable,
* host identity reconciliation is explicit and governed,
* `doctor` can detect, propose, optionally apply, and verify a safe fix,
* the CLI never claims a host has switched identity unless the server confirms the connection has actually rebound.

---

## 2. Problem Statement

Current client stories correctly cover:

* account creation and verification,
* login bootstrap,
* passwordless login,
* surface negotiation,
* and planned logout/profile switching. 

But they do not define what the client should do when an installed MCP host has:

* already authenticated as one principal,
* is holding a long-lived connection,
* and the user later logs in or switches profiles elsewhere.

That produces a real builder failure mode:

* `keyhole login` succeeds as Paul,
* the IDE-hosted Keyhole MCP connection still executes as Nathan,
* the builder assumes the system switched globally,
* but the server continues to honor the already-bound connection identity.

This is not a login failure. It is a host reconciliation and connection-binding UX gap.

---

## 3. Why This Story Exists

The SDK epic already requires:

* CLI-owned credential bootstrap,
* identity visibility,
* deterministic repair guidance,
* explainability,
* and surface negotiation against live server posture. 

This story exists because those guarantees are incomplete on a real workstation unless the builder can also answer:

* Which Keyhole-capable hosts are installed here?
* Which one is actually calling the MCP boundary?
* Under which principal?
* Is that principal stale relative to the selected active profile?
* Can I keep it, switch it, or invalidate it safely?

---

## 4. Scope

This story governs:

* local environment inventory for Keyhole-relevant hosts,
* installed MCP host discovery,
* CLI UX for identity mismatch detection,
* server-backed connection introspection through governed run types,
* guided host reconciliation and explicit rebind/invalidate flows,
* post-fix verification and proof emission.

This story does **not** define:

* the server-side authority model,
* raw auth token issuance,
* the profile store format itself,
* generic logout/refresh semantics already owned by SDK-CLIENT-01-B,
* direct mutation of arbitrary third-party IDE configuration without user intent.

---

## 5. Strategic Outcome

After this story, a builder can do:

```text
keyhole doctor
keyhole connections list
keyhole connection inspect --host vscode
keyhole profiles use paul
keyhole connection rebind --host vscode --profile paul
```

And receive truthful output such as:

```text
Host: vscode
MCP server: keyhole
Server URL: https://mcp.keyholesolution.com/sse

CLI active profile: paul
Connection active principal: nathan
Connection authority: session_bound
State: stale_confirmed

Suggested repairs:
  1. keep current IDE identity
  2. rebind IDE connection to paul
  3. invalidate IDE connection and reconnect
```

---

## 6. Design Principles

### 6.1 Detect first, mutate second

The client must inventory and explain before applying changes.

### 6.2 No silent IDE mutation

The CLI must not rewrite or clear host configuration or credentials without explicit builder intent.

### 6.3 Local assumptions are never enough

The client must not infer host execution identity from local files alone when the server can provide connection truth.

### 6.4 CLI login is not host rebind

A successful local login does not imply any long-lived host connection has changed identity.

### 6.5 One connection, one truth

Each live host connection must resolve to one server-confirmed principal or fail closed.

### 6.6 Repair must be concrete

When split identity is detected, the builder must be given lawful next-best actions.

### 6.7 Doctor is advisory by default

`keyhole doctor` inventories, explains, proposes, and optionally fixes only with explicit intent.

### 6.8 Surface negotiation still applies

The client must verify the server supports connection identity run types before attempting them.

### 6.9 Executables stay governed

All server-affecting host actions must go through `POST /mcp/v1/runs/start`, not ad hoc direct routes.

---

## 7. Non-Goals

This story does **not**:

* replace `keyhole login`,
* replace `keyhole profiles use`,
* replace generic `whoami`,
* guarantee every IDE vendor exposes writable config in the same way,
* promise automatic rewiring of every external host,
* merge human and worker identities,
* bypass server truth with local guesses,
* silently delete stored host credentials.

---

## 8. Terms

### 8.1 Host

A local application or integration capable of maintaining a Keyhole MCP connection.

### 8.2 Host inventory

The client-side discovery result showing installed hosts, their candidate Keyhole MCP entries, and whether they appear active.

### 8.3 Connection reconciliation

The governed process of comparing local expected profile identity against server-reported active connection identity for a host.

### 8.4 Rebind

An explicit governed request to move an already-open host connection from one principal to another.

### 8.5 Host drift

A condition in which the host’s live executing principal differs from the builder’s intended active profile context.

---

## 9. Required CLI Surfaces

### 9.1 `keyhole doctor`

Primary diagnostic surface.

Responsibilities:

* inventory local environment,
* detect known Keyhole-capable hosts,
* detect local active profile,
* negotiate server capabilities,
* invoke server-backed connection identity/status inspection run types where possible,
* detect mismatch,
* render advisory or machine-readable diagnosis,
* optionally apply approved repair,
* verify post-fix outcome.

Example usage:

```text
keyhole doctor
keyhole doctor --json
keyhole doctor --fix
keyhole doctor --fix --host vscode --profile paul
keyhole doctor --non-interactive --fix --host vscode --profile paul
```

Output responsibilities:

* show active CLI profile,
* list detected Keyhole hosts,
* show whether each host appears connected,
* show server-reported active principal per connection when available,
* classify status:

  * `aligned`
  * `split_identity`
  * `stale_connection`
  * `unsupported_host`
  * `surface_unavailable`
  * `ambiguous_connection`
* offer deterministic repair guidance.

---

### 9.2 `keyhole connections list`

Purpose: list live or recently observed Keyhole MCP connections visible through governed run inspection.

Underlying run type:

* `connection.list.inspect`

Example:

```text
keyhole connections list
keyhole connections list --json
```

Output fields:

* host hint / label if known,
* connection_id,
* principal,
* authority state,
* purpose/origin,
* bound_at,
* staleness state,
* rebind support.

---

### 9.3 `keyhole connection inspect`

Purpose: inspect the active identity for a specific connection or host using server-backed connection-truth inspection.

Underlying run types:

* `connection.identity.inspect`
* optionally `connection.status.inspect`

Example:

```text
keyhole connection inspect --host vscode
keyhole connection inspect --connection-id conn_123
keyhole connection inspect --json
```

Must display:

* connection principal,
* identity authority,
* session lineage id,
* purpose/origin,
* staleness state,
* repair guidance if mismatched.

---

### 9.4 `keyhole connection lineage`

Purpose: explain how the current connection identity came to be.

Underlying run type:

* `connection.lineage.inspect`

Example:

```text
keyhole connection lineage --host vscode
keyhole connection lineage --connection-id conn_123 --json
```

---

### 9.5 `keyhole connection rebind`

Purpose: explicitly request rebinding of a live host connection to a selected profile/principal.

Underlying run type:

* `connection.rebind`

Example:

```text
keyhole connection rebind --host vscode --profile paul
keyhole connection rebind --connection-id conn_123 --profile paul
keyhole connection rebind --host vscode --profile paul --yes
```

Requirements:

* confirm identity-changing action unless `--yes`,
* validate target profile exists locally,
* verify capability support first,
* dispatch as a governed write-bearing run,
* include request identity / idempotency identity,
* honestly render:

  * accepted,
  * rebound,
  * deferred,
  * replayed,
  * rejected.

---

### 9.6 `keyhole connection invalidate`

Purpose: explicitly invalidate a stale or wrong-principal host connection.

Underlying run type:

* `connection.invalidate`

Example:

```text
keyhole connection invalidate --host vscode
keyhole connection invalidate --connection-id conn_123 --yes
```

Use when the builder wants the host to reconnect cleanly rather than switch in place.

---

## 10. Doctor Discovery Model

### 10.1 DoctorHostRecord

```json
{
  "host_id": "vscode",
  "host_type": "ide_mcp_client",
  "display_name": "Visual Studio Code",
  "detected": true,
  "config_detected": true,
  "keyhole_server_entry_detected": true,
  "server_url": "https://mcp.keyholesolution.com/sse",
  "local_auth_hints_present": true,
  "connection_visible_from_server": true,
  "connection_id": "conn_...",
  "server_principal_user_id": "usr_...",
  "server_principal_label": "nathan",
  "staleness_state": "stale_confirmed",
  "supports_rebind": true,
  "supports_invalidate": true,
  "diagnosis": "split_identity"
}
```

### 10.2 DoctorReport

```json
{
  "cli_active_profile": "paul",
  "cli_user_id": "usr_paul",
  "hosts": [
    {
      "host_id": "vscode",
      "diagnosis": "split_identity",
      "current_connection_principal": "nathan",
      "recommended_actions": [
        "rebind",
        "invalidate_reconnect",
        "keep_as_is"
      ]
    }
  ],
  "summary_status": "attention_required"
}
```

---

## 11. Host Detection Responsibilities

The client must support a pluggable host-discovery model.

### 11.1 Minimum initial host targets

* installed IDE MCP client environments,
* local Keyhole SDK runtime context,
* known host configuration stores where the Keyhole MCP server entry may exist.

### 11.2 Detection principles

* detection may use file/config heuristics,
* all such heuristics are advisory,
* server truth outranks local hints for active connection identity,
* unsupported/unreadable hosts must be reported honestly.

### 11.3 No hard failure on unknown hosts

If unrecognized MCP hosts exist, `doctor` reports:

* unknown host,
* unreadable config,
* or unsupported integration,
  without failing the entire scan.

---

## 12. Reconciliation Flow

### 12.1 Default flow

1. determine CLI active profile,
2. inventory local hosts,
3. negotiate server capabilities,
4. invoke `connection.list.inspect` and `connection.identity.inspect` for visible hosts,
5. compare local intended identity vs connection identity,
6. classify mismatch if any,
7. render repair options,
8. optionally apply selected action via governed write-bearing runs,
9. verify result using read-only inspection run types,
10. emit proof/support artifacts.

### 12.2 Important rule

The client must not treat local profile switch as sufficient evidence that a host has changed identity.

### 12.3 Post-fix verification

After any rebind/invalidate action, the client must re-run connection inspection and report the actual result.

---

## 13. Required Client Behaviors

### 13.1 Split identity detection

If CLI profile user != server-reported host connection principal:

* classify `split_identity`,
* show both principals,
* do not claim automatic convergence.

### 13.2 Aligned state

If CLI profile and connection principal match:

* classify `aligned`,
* report no action required.

### 13.3 Surface unavailable

If the server lacks required connection identity run types:

* `doctor` reports `surface_unavailable`,
* gives repair guidance:

  * upgrade server,
  * use generic `whoami`,
  * avoid claiming host alignment.

### 13.4 Unsupported host

If the host is detected locally but not readable or not writable:

* classify `unsupported_host`,
* show what was and was not verified.

### 13.5 Rebind result rendering

`keyhole connection rebind` must render:

* old principal,
* target principal,
* connection_id,
* server verdict,
* next step,
* follow-up run status guidance when async.

### 13.6 Invalidate result rendering

`keyhole connection invalidate` must render:

* invalidated / accepted / rejected,
* whether reconnect is required,
* how to verify afterward.

### 13.7 No false convergence claim

A successful CLI login must never be presented as proof that installed hosts are now aligned.

---

## 14. Integration with Existing Stories

### 14.1 SDK-CLIENT-01

Still owns login and generic `whoami`. This story does not replace them.

### 14.2 SDK-CLIENT-01-B

Still owns logout, profile listing, profile switching, and token lifecycle. This story consumes the selected profile and applies it to long-lived hosts explicitly.

### 14.3 SDK-CLIENT-15

All write-bearing rebind/invalidate actions must use request identity and idempotency identity. `doctor --fix` must not bypass that discipline.

### 14.4 SDK-CLIENT-20

Mismatch diagnosis and connection reconciliation must be explainable and support-bundle-friendly.

### 14.5 SDK-CLIENT-21

Before using connection identity run types, the client must negotiate whether the server supports them.

### 14.6 SDK-CLIENT-22

Passwordless login is a valid way to establish the current CLI profile, but it does not itself rebind existing hosts.

---

## 15. Required Local Artifacts

All doctor/reconciliation actions must write tool-owned artifacts outside any repo.

### 15.1 Path

```text
<tool-owned-state>/
  doctor/
    <correlation-or-request-id>/
```

### 15.2 Minimum files

```text
doctor/
  <id>/
    report.json
    local_profile_snapshot.json
    host_inventory.json
    connection_truth.json
    negotiation.json
    requested_fix.json
    response.json
    verification.json
    repair.json
    summary.md
```

### 15.3 Repo neutrality

These artifacts are diagnostic and host-scoped, not repo-scoped.

---

## 16. Error Semantics and Repair Guidance

### 16.1 `HOST_NOT_DETECTED`

Repair:

* verify host is installed,
* rerun doctor,
* or specify host explicitly.

### 16.2 `HOST_KEYHOLE_ENTRY_NOT_FOUND`

Repair:

* install/add Keyhole MCP host entry,
* rerun doctor.

### 16.3 `HOST_CONNECTION_NOT_VISIBLE`

Repair:

* ensure host has opened a Keyhole connection,
* refresh host,
* rerun `keyhole connections list`.

### 16.4 `HOST_SPLIT_IDENTITY`

Repair:

* keep as is,
* rebind to active profile,
* invalidate and reconnect.

### 16.5 `HOST_REBIND_UNSUPPORTED`

Repair:

* invalidate connection and reconnect under desired profile,
* or upgrade server/client.

### 16.6 `HOST_REBIND_REJECTED`

Repair:

* inspect server reason,
* verify target profile/session,
* retry with lawful identity.

### 16.7 `HOST_VERIFICATION_FAILED`

Repair:

* rerun `keyhole connection inspect`,
* inspect lineage / support bundle,
* avoid assuming the fix applied.

---

## 17. Proof / Support Bundle Contract

### 17.1 Required proof content

Every doctor scan and every fix flow must include:

* active CLI profile,
* detected hosts,
* server-reported connection truth,
* selected repair action if any,
* final verification state,
* correlation ids and request ids where applicable.

### 17.2 Summary expectations

`summary.md` must explain:

* what mismatch was found,
* what action was chosen,
* what the server ultimately confirmed.

### 17.3 Support-bundle compatibility

These artifacts must be ingestible into existing explainability/support-bundle surfaces.

---

## 18. Acceptance Criteria

### 18.1 Environment inventory

Given a machine with one or more supported hosts, `keyhole doctor` detects Keyhole-relevant hosts and renders a structured host inventory.

### 18.2 Split identity visibility

Given the CLI is logged in as user A and a host connection is executing as user B, `keyhole doctor` reports `split_identity` and shows both principals.

### 18.3 No false convergence claim

Given a successful `keyhole login`, the client does not claim a host has switched identity unless server-backed connection inspection confirms it.

### 18.4 Surface-aware behavior

Given the server does not support required connection identity run types, the client detects that via negotiation and degrades honestly.

### 18.5 Explicit rebind

Given a supported host and a valid target profile, `keyhole connection rebind` submits a governed rebind request and renders the server’s actual verdict.

### 18.6 Verification after fix

Given a rebind or invalidate succeeds, the client re-runs connection inspection and reports the post-fix principal.

### 18.7 Safe non-interactive mode

Given `--fix --non-interactive --host X --profile Y`, the client applies only the explicitly requested fix and still verifies afterward.

### 18.8 Repo neutrality

Doctor and host reconciliation produce proof/support artifacts outside any working repo.

### 18.9 Surface discipline

The client assumes no new direct executable connection routes; all executable reconciliation actions are governed runs.

---

## 19. Tests

### Unit

* host inventory with zero hosts,
* host inventory with known supported host,
* split identity classifier,
* aligned classifier,
* unsupported host classifier,
* surface negotiation fail/warn/pass handling,
* no-false-convergence behavior after login,
* rebind request shaping,
* invalidate request shaping,
* proof artifact emission.

### Integration

* CLI profile = Paul,
* live connection principal = Nathan,
* `doctor` reports mismatch,
* `connection inspect` returns Nathan,
* `connection rebind --profile paul` returns accepted/rebound,
* post-fix verification returns Paul.

### Negative

* host not detected,
* connection not visible,
* required run types unavailable,
* rebind forbidden,
* ambiguous connection truth,
* verification mismatch after attempted fix.

---

## 20. Invariants

* **INV-SDK-CLIENT-01-C-001 — Split identity is visible**
  If local active profile and server-reported connection principal differ, the client must surface that mismatch explicitly.

* **INV-SDK-CLIENT-01-C-002 — Login is not rebind**
  The client may not claim a host connection changed identity solely because local CLI authentication changed.

* **INV-SDK-CLIENT-01-C-003 — Doctor is advisory by default**
  `keyhole doctor` must not silently mutate host auth/config state without explicit fix intent.

* **INV-SDK-CLIENT-01-C-004 — Reconciliation is server-verified**
  The client must verify post-fix identity against server-backed connection inspection before reporting success.

* **INV-SDK-CLIENT-01-C-005 — Unsupported surfaces degrade honestly**
  If required run types are unavailable, the client must not fabricate alignment results.

* **INV-SDK-CLIENT-01-C-006 — Rebind/invalidate are idempotent**
  All write-bearing host reconciliation actions honor request-id/idempotency semantics.

* **INV-SDK-CLIENT-01-C-007 — Doctor artifacts are repo-neutral**
  Host/identity reconciliation artifacts must be stored in tool-owned state, not inside builder repos.

* **INV-SDK-CLIENT-01-C-008 — Surface remains governed**
  The client uses governed run types for executable connection actions and does not depend on a new top-level connection route family.

---

## 21. Suggested Client Modules

```text
keyhole_sdk/doctor/__init__.py
keyhole_sdk/doctor/models.py
keyhole_sdk/doctor/host_inventory.py
keyhole_sdk/doctor/diagnostics.py
keyhole_sdk/doctor/reconciliation.py
keyhole_sdk/doctor/proof.py

keyhole_sdk/connection_identity/__init__.py
keyhole_sdk/connection_identity/client.py
keyhole_sdk/connection_identity/models.py
keyhole_sdk/connection_identity/render.py
keyhole_sdk/connection_identity/repair.py
```

Suggested CLI commands:

```text
keyhole_cli/commands/doctor.py
keyhole_cli/commands/connections_list.py
keyhole_cli/commands/connection_inspect.py
keyhole_cli/commands/connection_lineage.py
keyhole_cli/commands/connection_rebind.py
keyhole_cli/commands/connection_invalidate.py
```

Implementation pattern:

* read-only commands call the corresponding read-only run types,
* write-bearing commands dispatch through governed transport with idempotency,
* follow async outcomes through existing run status / explainability tooling.

---

## 22. Dependencies / Unlocks

### Depends on

* SDK-CLIENT-01
* SDK-CLIENT-01-B
* SDK-CLIENT-15
* SDK-CLIENT-20
* SDK-CLIENT-21
* SDK-SERVER-01-C

### Unlocks

* trustworthy `keyhole doctor`,
* safe profile switching across CLI + installed hosts,
* explicit IDE MCP rebinding,
* reduced builder confusion in multi-profile environments,
* honest onboarding on real workstations.

---

## 23. Closure Criteria

This story is complete only when:

* a builder can inventory local Keyhole-relevant hosts,
* the client can query server-backed connection truth through governed run types,
* split identity becomes visible and explainable,
* explicit host rebind/invalidate flows work end-to-end with idempotent semantics,
* the client never reports a fix without server verification,
* doctor and connection reconciliation emit repo-neutral proof/support artifacts,
* the client remains compliant with the sealed MCP surface,
* the paired server story closes the authority model underneath.

---

## 24. Agent Handoff

Implement this as a narrow, high-confidence extension to auth/profile UX, not as an invasive environment manager.

Sequence:

1. add host inventory abstraction,
2. implement `doctor` advisory scan,
3. wire negotiation for connection identity run-type support,
4. add `connections list` and `connection inspect`,
5. add `connection lineage`,
6. add explicit `connection rebind` and `connection invalidate`,
7. add post-fix verification,
8. emit doctor/reconciliation artifacts,
9. integrate repair guidance and support-bundle compatibility,
10. validate against a real IDE-hosted Keyhole MCP setup with split identity,
11. only then consider optional auto-fix ergonomics.

