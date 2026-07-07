# Server Directive: Governed Repo Product Envelope Surfaces

**Date:** 2026-07-06
**Status:** PRODUCT ENVELOPE ADVERTISED / FRESH GOVERNED RUN BLOCKED BY GAP CLAIMABILITY
**Closure:** NOT REQUIRED FOR PUBLIC TECHNICAL PREVIEW
**Promotion:** REQUIRED BEFORE "COMPLETE GOVERNED REPO PRODUCT" MARKETING
**Realm:** `kh-prod`
**MCP URL:** `https://mcp.keyholesolution.com`
**Client repo:** Keyhole public SDK/developer kit

## Executive Summary

The core governed repo path is live and working.

Verified on 2026-07-06:

- `keyhole whoami --json` succeeds in `mode=real`.
- `keyhole surfaces --json --refresh` succeeds.
- `keyhole doctor launch --repo-dir examples/second-governed-app --json` succeeds.
- `keyhole validate examples/second-governed-app --json` succeeds.
- `keyhole validate my-first-app --json` succeeds.
- `keyhole governed status --repo-dir examples/second-governed-app --last --json` loads live-confirmed terminal state.
- `keyhole governed receipt --repo-dir examples/second-governed-app --last --json` returns a governed receipt.
- The governed receipt contains `governed=true`, `event_spine_evidence=true`, `governance_verdict=ACCEPT`, `drift_state=non_drifted`, `governance_context_id`, `mcp_event_id`, `proof_id`, and `receipt_id`.
- `keyhole gaps list --repo-dir examples/second-governed-app --json` returns claimable gap `gap_8488f30fb4e1ef82`.
- `keyhole context compile --repo-dir examples/second-governed-app --purpose release_proof --json` succeeds.
- `keyhole governed run --repo-dir examples/second-governed-app --dry-run --explain --json` succeeds and shows the planned MCP operation chain.

After the 2026-07-07 promoted digest, live surface negotiation is compatible.
The remaining complete-product blocker moved from capability advertisement to
fresh governed execution: the only visible matching gap for
`examples/second-governed-app` is currently `STALE`, `claimable=false`, and
rejected by `gaps.claim`.

Required surfaces that are advertised and mostly working:

```text
authenticated_identity=true
run_dispatch=true
context_compile=true
repo.register advertised
context.compile advertised
governed.realize advertised
gaps.list path working
gaps.claim advertised, but fresh run currently blocked by stale non-claimable gap
```

Do not roll back the working core path. This directive now tracks two things:
preserving the advertised product envelope and restoring a fresh claimable gap
so the SDK can prove async lifecycle, explainability, support bundle, run tail,
budget visibility, and explicit enforcement guarantees against a new live run.

## Latest Recheck: 2026-07-07 Post-Promoted Digest

Backend reported that `kh-prod` was promoted to digest
`sha256:3092eacb6d5983d3023021276374d1c5ea739376c596947836e2429cb5644df7`
and that `main` is source-aligned.

The public SDK repo rechecked the live boundary from the public CLI path.

Commands run:

```powershell
python -m keyhole_cli.cli whoami --json
python -m keyhole_cli.cli surfaces --json --refresh
python -m keyhole_cli.cli doctor launch --repo-dir examples\second-governed-app --json
python -m keyhole_cli.cli governed status --repo-dir examples\second-governed-app --last --json
python -m keyhole_cli.cli governed receipt --repo-dir examples\second-governed-app --last --json
python -m keyhole_cli.cli explain run bdeeab31-a217-458f-aabc-2c4905ab8b7b --repo-dir examples\second-governed-app --json
python -m keyhole_cli.cli inspect bdeeab31-a217-458f-aabc-2c4905ab8b7b --repo-dir examples\second-governed-app --json
python -m keyhole_cli.cli support-bundle bdeeab31-a217-458f-aabc-2c4905ab8b7b --repo-dir examples\second-governed-app --json
python -m keyhole_cli.cli runs budget bdeeab31-a217-458f-aabc-2c4905ab8b7b --repo-dir examples\second-governed-app --json
python -m keyhole_cli.cli governed run --repo-dir examples\second-governed-app --json
python -m keyhole_cli.cli gaps list --repo-dir examples\second-governed-app --json
```

Observed improvements:

```text
whoami success=true
whoami mode=real
surfaces success=true
surfaces compatibility.status=compatible
surfaces required_missing=[]
surfaces optional_missing=[]
authenticated_identity=true
run_dispatch=true
run_async_accept=true
context_compile=true
context_required_for_runs=true
idempotency_required=true
explainability=true
support_bundle=true
run_tail=true
budget_visibility=true
```

That means the original capability-advertisement blocker is closed.

Remaining blocker:

```text
keyhole governed run --repo-dir examples\second-governed-app --json
success=false
error_class=GovernedDemoError
summary=gap claim failed with HTTP 422
```

The follow-up `gaps list` response showed the selected gap is not claimable:

```text
gap_id=gap_8488f30fb4e1ef82
status=STALE
claimable=false
blocked=true
blocked_reasons=STATUS_NOT_CLAIMABLE
message=Gap status 'STALE' does not permit claiming.
revalidated_on_digest=sha256:3092eacb6d5983d3023021276374d1c5ea739376c596947836e2429cb5644df7
explained_on_digest=sha256:3092eacb6d5983d3023021276374d1c5ea739376c596947836e2429cb5644df7
```

The SDK also found a client-side false positive: `doctor launch` and governed
gap resolution treated any matching `gap_id` as actionable even when the
server explicitly returned `claimable=false`. The SDK has been hardened to fail
early with `NO_CLAIMABLE_GAP` and to mark `claimable_gap_availability=false`.
The SDK also added a bounded retry from story-id-filtered gap discovery to the
storyless discovery shape after one live run returned `NEON_QUERY_FAILED` from
the filtered discovery query while direct `keyhole gaps list` still succeeded.

Optional product surface proof is still incomplete:

```text
explain run <old correlation_id>   -> success=true, fallback outcome_class=unknown
inspect <old correlation_id>       -> success=true, fallback outcome_class=unknown
support-bundle <old correlation_id> -> success=true, missing context/events/proof_refs
runs budget <old correlation_id>   -> success=true, limit_outcome=no_pressure_data
runs status <old correlation_id>   -> success=true, status=unknown
```

This may be because the old accepted receipt did not preserve a usable
`run_id` or request id. A fresh governed run is needed to prove the optional
surfaces, but the fresh run is blocked before claim by the stale gap.

### 2026-07-07 Current Verdict

The SDK is partially unblocked.

Closed:

- Live identity works.
- Capability negotiation is compatible.
- Product-envelope flags are visible to the public device-login identity.
- The prior surfaces stale/misaligned report is closed.

Still open:

- Fresh blessed public governed run cannot complete because the only visible
  matching gap is `STALE`, `claimable=false`, and rejected by `gaps.claim`.
- The optional product read surfaces are advertised but not yet proven against
  a fresh server-backed governed run id/request id.
- `gaps.claim` returned HTTP 422 without enough structured JSON detail in the
  CLI summary to make the repair deterministic from the failing command alone.

### Immediate Backend Remediation For Current Blocker

Backend must do all of the following before asking the SDK repo to reverify the
complete product path:

1. Materialize or reopen a current `OPEN`/claimable gap for
   `examples/second-governed-app` at the current public SDK commit and
   capability `second-governed-app.echo.user.v1`.
2. Ensure `gaps.list` actionable ordering does not return a stale,
   non-claimable gap as the only actionable candidate without a clear current
   claimable alternative.
3. Ensure `gaps.claim` rejects non-claimable gaps with structured JSON:
   `code=STATUS_NOT_CLAIMABLE`, `gap_id`, `status`, `claimable=false`,
   `blocked_reasons`, `required_action`, `request_id`, and `correlation_id`.
4. Fix the story-id-filtered `gaps.list` query path so it never returns
   `NEON_QUERY_FAILED` for a normal public SDK discovery request.
5. Ensure a successful governed run returns or persists a stable `run_id` and
   request id/correlation id that can bind `run.explain`, `request.inspect`,
   `support.bundle`, `run.tail`, and `run.budget`.
6. Re-run the public SDK blessed path from a fresh state and prove:
   `governed run` reaches `ACCEPT`, then optional product surfaces return
   server-backed truth for the same fresh run/request identifier.

## First 2026-07-07 Recheck

Backend reported that the product-envelope changes had landed. The public SDK
repo rechecked the live `kh-prod` boundary from the public CLI path.

Commands run:

```powershell
python -m keyhole_cli.cli whoami --json
python -m keyhole_cli.cli surfaces --json --refresh
curl.exe -s https://mcp.keyholesolution.com/mcp/v1/capabilities
```

Observed result:

```text
whoami success=true
whoami mode=real
surfaces success=true
surfaces compatibility.status=degraded
surfaces required_missing=[]
surfaces optional_missing=[
  run_async_accept,
  explainability,
  support_bundle,
  run_tail,
  budget_visibility
]
surfaces transitional=[
  context_required_for_runs,
  idempotency_required
]
```

The raw capabilities response also did not advertise the required
product-envelope feature flags:

```text
run_async_accept
explainability
support_bundle
run_tail
budget_visibility
context_required_for_runs
idempotency_required
```

The raw capabilities response did not advertise these product-envelope
operations either:

```text
run.budget
run.explain
request.inspect
support.bundle
run.tail
```

The raw response did advertise other unrelated flags and surfaces such as
`runs_cancel_enabled`, `events_replay_enabled`, connection surfaces, and
governance self-inspection run types. Those do not satisfy this directive.

### 2026-07-07 Verdict

The claimed server-side landing is not visible to the public MCP boundary.

From the public SDK perspective, the work is still open unless one of these is
true and then corrected:

1. The changes were not deployed to `kh-prod`.
2. The changes deployed but were not wired into `GET /mcp/v1/capabilities`.
3. The changes deployed under private or different names that the SDK cannot
   discover without guessing.
4. The changes are behind tenant/cohort/identity gating and the public CLI
   identity does not receive the advertised flags.

### Immediate Backend Remediation

Backend must do all of the following before asking the SDK repo to reverify:

1. Confirm the target environment is `kh-prod` at
   `https://mcp.keyholesolution.com`.
2. Confirm the public device-login identity class can see the same capabilities
   that backend expects external builders to see.
3. Add the missing feature flags to the public capabilities payload, or provide
   exact documented aliases and update the SDK parser in the public repo.
4. Add the missing operation/run-type declarations, or provide exact documented
   canonical names and paths.
5. Re-run `keyhole surfaces --json --refresh` from a public SDK checkout and
   confirm `optional_missing=[]` before declaring complete-product landing.
6. Keep the current core governed path intact: `repo.register`,
   `context.compile`, `gaps.claim`, `governed.realize`, Event Spine evidence,
   proof id, and receipt id must continue to work.

## Capability Advertisement Contract

`GET /mcp/v1/capabilities` must advertise truth, not aspirations.

The SDK currently reads product-envelope feature presence from capability
feature flags and operation/run-type discovery. The simplest server contract is:

```json
{
  "features": {
    "flags": {
      "run_async_accept": true,
      "explainability": true,
      "support_bundle": true,
      "run_tail": true,
      "budget_visibility": true,
      "context_required_for_runs": true,
      "idempotency_required": true
    }
  },
  "operations": [
    "run.status",
    "run.budget",
    "run.explain",
    "request.inspect",
    "support.bundle",
    "run.tail"
  ]
}
```

If backend chooses different canonical operation names, advertise aliases or
publish a precise mapping. The client can add a non-bypassing compatibility
mapper, but it must not guess from private platform internals.

Do not set a feature flag to `true` until the corresponding live operation is
implemented for the production realm and the device-login identity class used
by the public CLI.

## Directive 1: Accepted/Deferred Async Run Semantics

### Surface

```text
feature flag: run_async_accept
minimum operations: /mcp/v1/runs/start plus durable run.status lookup
affected commands: keyhole run, keyhole governed run, keyhole runs wait, keyhole runs resume
```

### Why It Is Needed

The current blessed path can complete synchronously and return terminal state,
which is enough for public technical preview. A complete product must also
handle long-running governed work without making the operator wait blindly or
lose state when a terminal result is delayed.

### Required Server Semantics

For write-bearing governed runs that cannot complete inline, `/mcp/v1/runs/start`
must be able to return an accepted/deferred response with:

```text
accepted=true or status=accepted/deferred
run_id=<stable server id>
request_id=<stable request id>
correlation_id=<stable correlation id>
poll_url or status operation hint
retry_after optional
created_at
expires_at optional
```

The server must persist the run enough for later observation by:

```text
run.status by run_id
run.status by request_id or documented request lookup
resume/reconnect by run_id after local client state loss
terminal result retrieval after completion
```

The terminal status response must preserve the same causal chain:

```text
run_id
request_id
correlation_id
run_type
status
created_at
updated_at
terminal=true when complete
governance_context_id when relevant
receipt_id/proof_id/event id when relevant
```

### Required Failure Semantics

Return structured failures for:

```text
RUN_NOT_FOUND
RUN_EXPIRED
RUN_NOT_READY
EXECUTION_SCOPE_NOT_GRANTED
INVALID_RUN_TYPE
INVALID_PARAMETERS
ASYNC_NOT_SUPPORTED
```

Do not collapse these into generic `INTERNAL_ERROR`.

### Acceptance Criteria

- `keyhole surfaces --json --refresh` reports `run_async_accept=true`.
- A safe long-running governed fixture or existing slow governed operation can return accepted/deferred state.
- `keyhole runs status <run-id> --json` returns the same run identity and reaches a terminal state.
- `keyhole runs wait <run-id> --json` exits successfully when the run becomes terminal.
- `keyhole runs resume <run-id> --json` works without relying only on local `.keyhole` state.
- Replaying the same idempotent request does not create duplicate governed work.

## Directive 2: Governance Explainability

### Surface

```text
feature flag: explainability
minimum operations: run.explain, request.inspect
affected commands: keyhole explain run, keyhole inspect
```

### Why It Is Needed

Operators need to understand why a run was accepted, rejected, deferred,
degraded, or blocked. A complete product cannot leave users with only a final
status and a correlation id.

### Required `run.explain` Request

Preferred run-invoked shape:

```json
{
  "run_type": "run.explain",
  "params": {
    "run_id": "<run id>"
  }
}
```

Accept a request id as an alternative when the run id is not known:

```json
{
  "run_type": "run.explain",
  "params": {
    "request_id": "<request id>"
  }
}
```

### Required `run.explain` Response

The response must keep layers distinct:

```json
{
  "run_id": "run_...",
  "request_id": "req_...",
  "correlation_id": "...",
  "status": "succeeded | failed | blocked | deferred | accepted",
  "summary": "Human-readable one-line summary.",
  "request": {
    "run_type": "governed.realize",
    "idempotency_key_fingerprint": "sha256:...",
    "submitted_at": "..."
  },
  "run": {
    "created_at": "...",
    "updated_at": "...",
    "terminal": true,
    "terminal_status": "succeeded"
  },
  "context": {
    "governance_context_id": "gctx_...",
    "ctxpack_digest": "..."
  },
  "decision": {
    "governance_verdict": "ACCEPT",
    "drift_state": "non_drifted",
    "policy_ids": [],
    "invariant_ids": []
  },
  "event": {
    "event_spine_evidence": true,
    "mcp_event_id": "..."
  },
  "proof": {
    "proof_id": "...",
    "receipt_id": "..."
  },
  "root_cause": {
    "class": "none | policy | auth | schema | budget | server | unknown",
    "detail": ""
  },
  "repair_guidance": []
}
```

If a section is unavailable, include it in `missing_sections[]` with a reason.
Do not fabricate policy, event, or proof data.

### Required `request.inspect` Semantics

`request.inspect` must answer whether a request was:

```text
never_seen
accepted
deduped
replayed
deferred
running
terminal
expired
rejected
```

The response must include `request_id`, `correlation_id`, and any linked
`run_id`.

### Acceptance Criteria

- `keyhole surfaces --json --refresh` reports `explainability=true`.
- `keyhole explain run <run-id> --json` returns a layered explanation for a successful governed receipt.
- A rejected or intentionally invalid request returns structured root cause and repair guidance.
- `keyhole inspect <request-id> --json` can recover request state and linked run id.
- Explanations never include bearer tokens, refresh tokens, Authorization headers, or credential contents.

## Directive 3: Server-Enriched Support Bundle

### Surface

```text
feature flag: support_bundle
minimum operation: support.bundle
affected command: keyhole support-bundle
```

### Why It Is Needed

Public support needs a deterministic, redacted artifact that lets support staff
debug a governed run without asking users to paste raw logs, credentials, or
local proof directories.

### Required Request

Preferred run-invoked shape:

```json
{
  "run_type": "support.bundle",
  "params": {
    "run_id": "<run id>",
    "request_id": "<optional request id>",
    "include": [
      "summary",
      "request",
      "run",
      "context",
      "events",
      "proof_refs",
      "surface_posture",
      "budget",
      "repair"
    ]
  }
}
```

### Required Response

Return a JSON bundle or a server-side bundle reference with a manifest:

```json
{
  "bundle_id": "sb_...",
  "run_id": "run_...",
  "request_id": "req_...",
  "correlation_id": "...",
  "created_at": "...",
  "redacted": true,
  "manifest": [
    "summary.json",
    "request.json",
    "run.json",
    "context.json",
    "events.json",
    "proof_refs.json",
    "surface_posture.json",
    "budget.json",
    "repair.json",
    "redaction_report.json"
  ],
  "missing_sections": [],
  "omission_notes": [],
  "redaction_report": {
    "tokens_removed": true,
    "authorization_headers_removed": true,
    "credential_paths_removed": true,
    "local_paths_redacted": true
  }
}
```

### Security Requirements

Support bundles must not include:

```text
access tokens
refresh tokens
Authorization headers
credential file contents
private keys
unredacted local absolute paths
unredacted environment variables that can contain secrets
```

### Acceptance Criteria

- `keyhole surfaces --json --refresh` reports `support_bundle=true`.
- `keyhole support-bundle <run-id> --json` returns `bundle_id` or writes a bundle with a manifest.
- Bundle manifest includes request, run, context, event/proof refs, surface posture, budget when available, repair guidance, and redaction report.
- Automated redaction scan finds no tokens, refresh tokens, Authorization headers, or credential contents.
- Missing optional sections are represented in `missing_sections[]`, not silently omitted.

## Directive 4: Server-Backed Run Tail

### Surface

```text
feature flag: run_tail
minimum operation: run.tail or documented observation stream
affected command: keyhole runs tail
```

### Why It Is Needed

Current client behavior can poll status and honestly label the observation
method as `status_poll`. That is useful fallback behavior. It is not a complete
run-tail product surface.

A complete product needs chronological server observations for running work.

### Required Semantics

The server must expose a read-only observation surface for a run:

```json
{
  "run_type": "run.tail",
  "params": {
    "run_id": "<run id>",
    "after_sequence": "<optional cursor>",
    "limit": 100
  }
}
```

Equivalent REST, long-poll, or event-stream contracts are acceptable if
advertised in capabilities with exact client guidance.

Each observation entry must include:

```text
sequence
timestamp
status
message
source
correlation_id
event_id optional
terminal optional
```

The surface must preserve ordering and provide a cursor for resume.

### Required Failure Semantics

Return structured failures for:

```text
RUN_NOT_FOUND
RUN_EXPIRED
TAIL_NOT_AVAILABLE
CURSOR_EXPIRED
EXECUTION_SCOPE_NOT_GRANTED
```

### Acceptance Criteria

- `keyhole surfaces --json --refresh` reports `run_tail=true`.
- `keyhole runs tail <run-id> --json` reports a server-backed observation method, not only `status_poll`.
- Tail output includes monotonic sequence or cursor data.
- Tail can resume from a cursor without duplicating entries.
- Terminal observations match `run.status` and governed receipt state.

## Directive 5: Budget and Runtime Pressure Visibility

### Surface

```text
feature flag: budget_visibility
minimum operation: run.budget or budget fields in run.status
affected command: keyhole runs budget
```

### Why It Is Needed

`whoami` can report account-level limits, but complete-product UX needs
run-level budget and pressure truth. Operators must be able to tell whether a
run succeeded with normal budget posture, was deferred by load, was rate or
concurrency limited, or exhausted a runtime budget after partial execution.

### Required Response Shape

`run.budget` preferred request:

```json
{
  "run_type": "run.budget",
  "params": {
    "run_id": "<run id>"
  }
}
```

Required response fields:

```json
{
  "run_id": "run_...",
  "request_id": "req_...",
  "correlation_id": "...",
  "status": "succeeded | deferred | rate_limited | budget_exhausted",
  "limit_outcome": "success_with_budget_visibility | deferred | rate_limited | concurrency_limited | budget_exhausted | no_pressure_data",
  "limit_class": "wall_time | event | byte | storage | concurrency_slot | operation_rate | none",
  "budget_snapshots": [
    {
      "budget_class": "operation_rate",
      "budget_used": 12,
      "budget_remaining": 988,
      "budget_unit": "operations",
      "near_limit": false,
      "retry_after": null
    }
  ],
  "partial_execution": false,
  "is_terminal": true,
  "retry_after": null,
  "retry_safe": false,
  "repair_guidance": []
}
```

It is acceptable for successful runs to report `no_pressure_data` only if the
server explicitly declares that no run-level budget data exists for that run.
When `budget_visibility=true`, at least one supported run class must expose
real budget posture so the feature is not a hollow flag.

### Required Pressure Categories

At minimum, distinguish:

```text
success_with_budget_visibility
deferred
rate_limited
concurrency_limited
budget_exhausted
no_pressure_data
unknown_pressure
```

Do not report network failures as budget outcomes.

### Acceptance Criteria

- `keyhole surfaces --json --refresh` reports `budget_visibility=true`.
- `keyhole runs budget <run-id> --json` returns structured budget posture.
- A success case can show budget visibility.
- At least one pressure fixture or controlled test can show deferred, rate limited, concurrency limited, or budget exhausted semantics.
- `retry_after` and `retry_safe` are present when retry guidance is meaningful.

## Directive 6: Context Binding Enforcement

### Surface

```text
feature flag: context_required_for_runs
class: transitional until fully enforced
affected commands: governed write-bearing run dispatch
```

### Why It Is Needed

The client can compile and pass context today. A complete product must make the
server guarantee explicit: either context binding is required and enforced, or
it is not. The client must not have to infer this from convention.

### Required Server Semantics

When `context_required_for_runs=true`:

- Governed write-bearing operations must reject missing context.
- The rejection must be structured and repair-oriented.
- Valid `governance_context_id` or `ctxpack_digest` must bind the run to the context.
- The terminal receipt or run status must echo the context id/digest used.

Structured rejection:

```json
{
  "ok": false,
  "error": {
    "code": "CONTEXT_REQUIRED",
    "message": "This run type requires a governed context.",
    "repair": [
      "Run keyhole context compile for this repo.",
      "Retry with governance_context_id or ctxpack_digest."
    ]
  }
}
```

### Acceptance Criteria

- `keyhole surfaces --json --refresh` reports `context_required_for_runs=true` only after enforcement is live.
- A governed write without context fails with `CONTEXT_REQUIRED`.
- The same governed write with a valid context succeeds or reaches normal policy evaluation.
- Receipts and status records echo the context id/digest.

## Directive 7: Idempotency Enforcement

### Surface

```text
feature flag: idempotency_required
class: transitional until fully enforced
affected commands: write-bearing runs, repo registration, gap claim, governed realization
```

### Why It Is Needed

The SDK treats write-bearing operations as idempotency-sensitive. A complete
product must make server behavior explicit so retries, resumes, and duplicate
submissions are safe.

### Required Server Semantics

When `idempotency_required=true`:

- Write-bearing operations require an idempotency key or documented equivalent.
- Repeating the same key with the same payload returns the original result or a deterministic replay response.
- Repeating the same key with a materially different payload returns conflict.
- The response includes `idempotency_key_fingerprint` or equivalent non-secret proof.

Structured conflict:

```json
{
  "ok": false,
  "error": {
    "code": "IDEMPOTENCY_CONFLICT",
    "message": "The idempotency key was previously used with a different payload.",
    "request_id": "req_...",
    "correlation_id": "..."
  }
}
```

### Acceptance Criteria

- `keyhole surfaces --json --refresh` reports `idempotency_required=true` only after enforcement is live.
- Write-bearing request without idempotency fails with `IDEMPOTENCY_REQUIRED`.
- Same idempotency key plus same payload dedupes to the same result.
- Same idempotency key plus different payload fails with `IDEMPOTENCY_CONFLICT`.
- Event/proof records preserve one causal chain instead of duplicate writes.

## Cross-Cutting Requirements

### Capabilities Must Match Implementation

For every feature flag:

```text
false = unavailable or fallback-only
true = server-backed semantics implemented and live in kh-prod
```

Client fallback behavior is not sufficient reason to set a server feature flag.
For example, status polling is not `run_tail=true`; local bundle assembly is
not `support_bundle=true`; plan limits in `whoami` are not
`budget_visibility=true`.

### Read-Only Versus Write-Bearing Classification

These surfaces must be read-only:

```text
run.status
run.tail
run.budget
run.explain
request.inspect
support.bundle
```

These surfaces remain write-bearing and must preserve idempotency/proof:

```text
repo.register
gaps.claim
governance.context.create
context.compile when it materializes a context
governed.realize
```

### Security Requirements

- Do not require users to paste bearer tokens into docs or support bundles.
- Do not return access tokens, refresh tokens, Authorization headers, or credential contents.
- Redact local absolute paths in portable support artifacts.
- Return structured authorization failures with required scope/entitlement guidance.
- Preserve tenant/org/cohort/workspace attribution in server-side records.

### Event and Proof Requirements

When a surface references a governed run, it must preserve:

```text
run_id
request_id
correlation_id
governance_context_id when relevant
mcp_event_id when relevant
proof_id when relevant
receipt_id when relevant
```

No client should need to manually mutate Event Spine, proof stores, or local
receipts to satisfy these requirements.

## Backend Acceptance Checklist

The complete product-envelope server work is accepted when:

```text
keyhole surfaces reports status=compatible
required_missing is empty
optional_missing is empty
run_async_accept=true
explainability=true
support_bundle=true
run_tail=true
budget_visibility=true
context_required_for_runs=true or documented false with reason
idempotency_required=true or documented false with reason
run.status can retrieve durable run state by run_id
run.explain returns layered decision/execution explanation
request.inspect returns request/run linkage
support.bundle returns redacted manifest-backed support artifact
run.tail returns server-backed chronological observations
run.budget returns structured run-level budget/pressure posture
context enforcement behavior matches context_required_for_runs
idempotency behavior matches idempotency_required
core governed receipt path still returns governed Event Spine/proof evidence
```

## Required Retest Commands

Use the public SDK repo, not private platform source.

```powershell
python -m keyhole_cli.cli login --flow device --force
python -m keyhole_cli.cli whoami --json
python -m keyhole_cli.cli surfaces --json --refresh
python -m keyhole_cli.cli validate examples\second-governed-app --json
python -m keyhole_cli.cli doctor launch --repo-dir examples\second-governed-app --json
python -m keyhole_cli.cli governed run --repo-dir examples\second-governed-app --json
python -m keyhole_cli.cli governed status --repo-dir examples\second-governed-app --last --json
python -m keyhole_cli.cli governed receipt --repo-dir examples\second-governed-app --last --json
```

Then retest optional product surfaces against the run id or request id returned
by the governed run/status response:

```powershell
python -m keyhole_cli.cli explain run <run-id> --json
python -m keyhole_cli.cli inspect <request-id> --json
python -m keyhole_cli.cli support-bundle <run-id> --json
python -m keyhole_cli.cli runs tail <run-id> --json
python -m keyhole_cli.cli runs budget <run-id> --json
```

Finally rerun the public release gate:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\public-release-gate.ps1 -IncludeLiveProof
python -m pytest tests/unit -q --basetemp .pytest-tmp
git diff --check
```

Publishing remains blocked if generated `.keyhole/` or `proof_bundle/` state is
tracked by Git.

## Current Closure Posture

The Keyhole SDK can be marketed as a public technical preview / early-access
governed repo SDK after clean-clone proof and CI verification.

It should not be marketed as a complete governed repo product until the server
implements or explicitly resolves the product-envelope surfaces in this
directive. Core governance is real; product completeness requires observability,
explainability, supportability, async lifecycle safety, budget visibility, and
explicit enforcement guarantees.
