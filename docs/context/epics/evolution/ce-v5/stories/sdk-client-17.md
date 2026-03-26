# SDK-CLIENT-17 — Async Run Tracking, Polling, and Stream-Safe UX

**Status:** DRAFT  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (design + validation), Prod (governed promotion only; no uncontrolled canonical mutation)  
**Surface:** Client  
**Zipper Pair:** `sdk-server-17.md`  
**Purpose:** Define the client-side contract for accepted async governed execution, including `accepted + run_id` handling, run status inspection, wait/follow UX, safe resume semantics, and proof continuity from request to terminal outcome.

---

## 1. Story Purpose

SDK-CLIENT-17 is the story that makes long-running governed execution feel first-class rather than awkward.

Earlier client stories establish:

- authentication,
- repo scaffold,
- local validation,
- registration,
- governed runtime invocation,
- context-bound run admission.

This story extends that into the runtime model Keyhole actually needs at scale:

```text
POST → accepted + run_id
GET  → status / terminal result
SSE  → optional event streaming
```

The client must handle this model safely, clearly, and without transport ambiguity.

This story exists so builders can:

- start a governed run,
- see whether it was accepted or completed immediately,
- inspect current run state,
- wait for terminal completion,
- follow run events,
- resume from a request ID or run ID after interruption,
- and keep proof continuity intact across long-running execution.

---

## 2. Why This Story Exists

A governed system that only supports “send request, block, hope” is not ready for real runtime scale.

As the platform moves into:

- write-bearing runs,
- long-running convergence,
- ingestion,
- declaration submission,
- repair workflows,
- and bounded execution under load,

it must stop assuming every run completes inside one synchronous request-response cycle.

The client therefore needs a real accepted-async UX that teaches builders the correct execution model:

- the boundary may accept work before it completes,
- a durable `run_id` becomes the identity of execution,
- status and events are separate from admission,
- interruption is survivable,
- proof spans the full run lifecycle rather than just the submit call.

Without this story:

- long-running runs feel broken,
- users retry unnecessarily,
- transport failure is confused with execution failure,
- proof continuity breaks,
- and async server behavior looks like instability rather than design.

---

## 3. Story Goals

The client must provide:

- accepted async execution handling (`accepted + run_id`),
- `keyhole runs status <run-id>`,
- `keyhole runs wait <run-id>`,
- `keyhole runs tail <run-id>`,
- `keyhole runs resume <request-id|run-id>`,
- optional event/stream follow UX,
- graceful handling of mixed fast-path vs long-running runs,
- durable local proof linkage across request → run → events → outcome.

This story is about **UX and contract discipline**, not merely transport mechanics.

---

## 4. Scope

### Included

- accepted async response handling
- run identity capture and persistence
- run status inspection UX
- blocking wait UX for interactive users
- streaming/follow UX when the server supports it
- resume/reconnect behavior
- proof continuity across the run lifecycle
- deterministic terminal state rendering
- zipper expectations against `sdk-server-17.md`

### Excluded

- final explainability/support bundle UX (later story)
- full budget/limit UX (later story)
- idempotency design itself (tightened in SDK-CLIENT-15)
- context compilation behavior itself (tightened in SDK-CLIENT-16)
- direct canonical memory surfaces

---

## 5. Command Contract

### 5.1 Accepted async run handling

When the client submits a governed run and the boundary responds with accepted async execution, the client must recognize and preserve at minimum:

- `run_id`
- request correlation metadata
- current state (`accepted`, `running`, etc.)
- any immediate proof/event references returned by the boundary

The client must not misrepresent `accepted` as `completed`.

### 5.2 Status inspection

```text
keyhole runs status <run-id>
```

This command must:

- fetch the current known state of a governed run,
- render current status clearly,
- preserve raw machine-readable output where appropriate,
- remain safe for repeated polling.

### 5.3 Wait for terminal outcome

```text
keyhole runs wait <run-id>
```

This command must:

- poll or otherwise follow the run until terminal state,
- stop on terminal result,
- render success/failure/cancel/defer clearly,
- emit or update proof artifacts.

### 5.4 Tail / follow

```text
keyhole runs tail <run-id>
```

This command must:

- follow run events safely,
- degrade gracefully if stream/SSE is unavailable,
- avoid presenting missing streams as client failure,
- preserve chronology clearly for humans.

### 5.5 Resume

```text
keyhole runs resume <request-id|run-id>
```

This command must:

- recover a previously accepted run using known local or server-visible identity,
- reconnect the user to current run state,
- avoid starting a new execution accidentally,
- preserve proof continuity.

### 5.6 Mixed fast-path vs long-running handling

The client must support both:

- immediate terminal responses, and
- accepted async responses

without forcing the user to learn two totally different interaction models.

---

## 6. Current Model vs Target Model

### 6.1 Fast-path terminal response

```text
submit run
→ server completes quickly
→ terminal outcome returned inline
```

### 6.2 Accepted async response

```text
submit run
→ server returns accepted + run_id
→ client polls / tails / waits
→ terminal outcome resolved later
```

### 6.3 Client obligation

The client must normalize both into one governed runtime UX so the builder experiences:

```text
I started a run.
I can inspect it.
I can wait for it.
I can resume it.
I can prove what happened.
```

---

## 7. Preconditions

Before using accepted-async run handling, the client must verify:

1. the user is authenticated,
2. the target run was submitted lawfully,
3. run identity is present (`run_id` or recoverable request identity),
4. local proof output can be updated safely,
5. status/tail/wait commands are not asked to operate on impossible or malformed IDs.

If those preconditions fail, the client must fail locally and clearly.

---

## 8. Local Run Record Contract

The client should maintain a minimal local record for accepted async runs sufficient to preserve continuity.

Recommended fields:

```json
{
  "request_id": "...",
  "run_id": "...",
  "command": "keyhole run",
  "mode": "shadow|regular",
  "ctxpack_digest": "...",
  "submitted_at": "...",
  "last_known_status": "accepted",
  "proof_path": "..."
}
```

This local run record is not the source of truth.
It exists to support:

- resume,
- wait,
- tail,
- proof continuity,
- clean UX after interruption.

---

## 9. Accepted Response Handling

When the server returns accepted async execution, the client must:

1. capture `run_id`,
2. write or update the local run record,
3. emit a proof artifact showing accepted state,
4. present the user with next-step commands,
5. avoid blocking indefinitely unless explicitly asked via `wait`.

### Example terminal UX

```text
✔ Run accepted
run_id: run_abc123
mode: shadow
next:
  keyhole runs status run_abc123
  keyhole runs wait run_abc123
  keyhole runs tail run_abc123
```

---

## 10. Status UX Contract

`keyhole runs status <run-id>` must provide:

- run ID
- current status
- last update time where available
- mode (`shadow` / regular)
- repo identity if known
- context digest if known
- terminal summary if complete
- next-step hint when still in progress

It must never imply finality if the run is still active.

---

## 11. Wait UX Contract

`keyhole runs wait <run-id>` must:

- continue until terminal state or explicit client timeout/interruption,
- surface intermediate progress where useful,
- end cleanly on success, failure, cancel, or governed denial,
- write the terminal result into local proof artifacts.

### Important rule

Waiting is a client convenience operation.
It must never change the run itself.

---

## 12. Tail / Stream UX Contract

`keyhole runs tail <run-id>` must support the best available observation mode.

### Preferred behavior

- use stream/SSE when available,
- present events in causal order,
- show timestamps and event class where useful,
- allow graceful shutdown by the user.

### Required fallback behavior

If stream/SSE is unavailable, the client may degrade to:

- status polling,
- batched event retrieval,
- or an explicit unsupported message

but it must do so honestly.

The client must not pretend to stream if it is polling snapshots.

---

## 13. Resume UX Contract

`keyhole runs resume <request-id|run-id>` exists for interrupted workflows.

It must:

- locate the correct run using known local records and/or server query surfaces,
- reconnect the builder to the active or terminal run,
- preserve original proof lineage,
- avoid accidental duplicate execution.

### Important rule

Resume is not “run again.”
Resume is “reconnect to the same governed execution identity.”

---

## 14. Mixed Fast-Path vs Async UX

The client must make both models feel coherent.

### Fast-path outcome

```text
✔ Run completed
```

### Accepted async outcome

```text
✔ Run accepted
```

The difference must be obvious, but the surrounding UX must still feel like one system.

For example:

- both produce proof artifacts,
- both preserve correlation,
- both support later inspection,
- both use the same run-oriented terminology.

---

## 15. Proof Contract

Every governed run invocation under this story must preserve proof continuity across the full lifecycle.

### Minimum proof outputs

Recommended structure:

```text
proof_bundle/
  runs/
    <request-or-run-id>/
      request.json
      accepted.json      # when accepted async
      status.json        # latest known status
      outcome.json       # when terminal
      events.json        # when available
      summary.md
      correlation.json
```

### Required semantics

- accepted runs must produce proof, not only completed runs,
- later status/tail/wait commands must update or extend the same proof lineage,
- terminal resolution must not fork into a disconnected proof artifact,
- `request_id` and `run_id` must remain linked.

---

## 16. Event Traceability Expectations

This story assumes the paired server story provides traceable event emission.

The client must preserve enough local state to relate:

- request
- run
- context
- mode
- event stream
- terminal outcome
- proof path

This is essential so later explainability stories can reconstruct the lifecycle without ambiguity.

---

## 17. Failure Handling and Repair Guidance

The client must distinguish at least the following failure classes:

### 17.1 Submission failure
The run was not accepted.

### 17.2 Observation failure
The run may exist, but status/tail retrieval failed.

### 17.3 Terminal failure
The run completed with governed failure or denial.

### 17.4 Resume ambiguity
The client cannot confidently determine which run to resume.

Each class must provide deterministic next-best actions.

Examples:

- retry status lookup
- use `keyhole runs resume <request-id>`
- inspect local proof artifact
- re-run only if the previous request was not accepted
- use support/explain surfaces once those stories land

---

## 18. Local Test Strategy

### 18.1 Client-only tests

- accepted response is parsed correctly
- fast-path terminal response is parsed correctly
- local run record is written deterministically
- status command renders active and terminal states clearly
- wait command polls until terminal state
- tail command handles stream vs fallback honestly
- resume reconnects to existing run identity rather than creating a new one
- proof artifacts update across lifecycle stages

### 18.2 Boundary zipper tests

- long-running run returns accepted + run_id
- client tracks and resolves terminal state safely
- no transport ambiguity under accepted async execution
- proof bundles link request → run → events → outcome

### 18.3 Negative tests

- malformed run_id rejected locally
- missing run_id in accepted response treated as protocol error
- resume without matching local/server identity fails clearly
- interrupted wait can be resumed without losing continuity

---

## 19. Acceptance Criteria

This story is complete only when all of the following are true:

1. the client recognizes and handles `accepted + run_id` responses
2. `keyhole runs status <run-id>` works against the paired server contract
3. `keyhole runs wait <run-id>` resolves terminal state safely
4. `keyhole runs tail <run-id>` follows events or degrades honestly
5. `keyhole runs resume <request-id|run-id>` reconnects to prior execution rather than duplicating it
6. mixed fast-path and long-running behavior is handled gracefully
7. local proof lineage spans request → run → events → outcome
8. no transport ambiguity remains when the server accepts async execution
9. repair guidance is present for observation/resume failures
10. zipper proof demonstrates durable async execution handling end-to-end

---

## 20. Zipper Expectations Against `sdk-server-17.md`

The paired server story must provide:

- two-plane run dispatch
- accepted async response contract with `run_id`
- run status endpoint
- optional stream / SSE compatibility
- stable terminal outcome retrieval
- correlation continuity

SDK-CLIENT-17 closes only when the paired server proof demonstrates:

- long-running run returns accepted + run_id
- client tracks and resolves terminal outcome safely
- no transport ambiguity remains
- proof bundles link request → run → events → outcome

---

## 21. Forward-Compatibility Notes

This story must be implemented so later stories can extend it without breaking the public UX.

Later stories may add or tighten:

- global idempotent transport semantics
- budget / limit visibility
- explainability / support bundles
- richer event streaming
- stronger context enforcement coupling

SDK-CLIENT-17 must therefore avoid assumptions such as:

- every accepted run always has a stream
- resume is purely local
- run tracking never needs request identity
- inline outcome and accepted outcome can share identical wording

---

## 22. Non-Goals

SDK-CLIENT-17 does **not**:

- define idempotency policy itself
- define context compilation itself
- expose direct canonical memory access
- replace proof bundle design
- force SSE support everywhere
- provide final explainability UI

It defines the client-side async run lifecycle UX.

---

## 23. Story Closure Statement

SDK-CLIENT-17 is the story that teaches builders how governed execution behaves when it does not finish immediately.

When this story closes, a builder must be able to:

```text
start a governed run
receive a durable run identity
inspect it
wait for it
follow it
resume it after interruption
and preserve proof continuity the entire time
```

That is the minimum async UX required for real external runtime participation.
