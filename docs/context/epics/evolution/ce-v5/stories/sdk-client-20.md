# SDK-CLIENT-20 — Governance Explainability and Support Bundles

**Status:** DRAFT  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (design + validation), Prod (governed promotion only; no uncontrolled canonical mutation)  
**Surface:** Client  
**Zipper Pair:** `sdk-server-20.md`  
**Purpose:** Define the client-side explainability and supportability contract for governed execution, including human-readable run/request inspection, lineage-oriented explanations, deterministic support-bundle generation, and replay-safe visibility into context, events, proof, and rejection reasons.

---

## 1. Story Purpose

SDK-CLIENT-20 closes the client-side externalization surface for **understanding what happened**.

By the time a builder reaches this story, the SDK already supports:

- authentication,
- repo scaffolding,
- declaration artifacts,
- validation,
- registration,
- governed runtime execution,
- context lifecycle,
- async run tracking,
- memory boundary enforcement,
- budget and overload visibility.

What is still missing is the final human-facing layer:

```text
why did the platform do what it did?
```

This story exists to make that answer:

- deterministic,
- inspectable,
- replayable,
- support-friendly,
- and builder-readable.

It defines the client-side contract for:

- `keyhole explain run <id>`
- `keyhole inspect <request-id>`
- `keyhole support-bundle <run-id|request-id>`
- human-readable explanation of context, event lineage, proof artifacts, and rejection/defer/replay reasons

This is not just a support convenience story.
It is the story that turns the governed platform from:

```text
powerful but opaque
```

into:

```text
powerful, governed, and legible
```

---

## 2. Why This Story Exists

A governed platform that cannot explain its behavior is indistinguishable from a black box under pressure.

By this stage of the SDK line, builders can already:

- issue governed runs,
- bind runs to context,
- track long-running execution,
- observe budgets and overload outcomes,
- produce proof bundles,
- and interact with a memory-safe client boundary.

But none of that is sufficient if the builder cannot answer:

- why was this run accepted?
- why was this run rejected?
- why was this request replayed instead of re-executed?
- why was this run deferred?
- what context did this run use?
- what event chain supports this outcome?
- where is the proof?
- what do I send to support or another engineer to reconstruct the case?

SDK-CLIENT-20 exists because the final developer experience for a governed platform must include **explanation and recovery**, not just execution.

Without this story:

- repair remains harder than it needs to be,
- support becomes log-diving,
- builders mistrust “deferred” or “replayed” outcomes,
- black-box behavior reappears at exactly the layer where trust matters most,
- downstream adoption suffers even if the platform is technically correct.

---

## 3. Story Goals

The client must provide all of the following:

- a run explanation command,
- a request inspection command,
- a support-bundle command,
- a stable human-readable explanation format,
- deterministic rendering of context, run, event, and proof relationships,
- explicit explanation for accepted / rejected / replayed / deferred outcomes,
- portable support artifacts that can be attached to tickets or passed across teams.

This story must not require builders to understand raw internal logs, raw database records, or internal server implementation details.

It must present governed truth in a form that is:

- accurate,
- bounded,
- attributable,
- and useful.

---

## 4. Scope

### Included

- `keyhole explain run <id>`
- `keyhole inspect <request-id>`
- `keyhole support-bundle <run-id|request-id>`
- human-readable explanation rendering
- lineage-oriented summary generation
- local support-bundle packaging
- deterministic command outputs for known outcome classes
- zipper expectations against `sdk-server-20.md`

### Excluded

- arbitrary free-form debugging consoles
- raw privileged log browsing
- direct database or Event Spine operator tooling
- internal-only root-cause analysis beyond builder-safe surfaces
- replacement of proof bundles from SDK-CLIENT-13
- replacement of async run tracking from SDK-CLIENT-17
- replacement of budget visibility from SDK-CLIENT-19

This story builds on those surfaces and makes them intelligible.

---

## 5. Command Contract

### 5.1 Explain a run

```text
keyhole explain run <run-id>
```

This command must retrieve or reconstruct a human-readable explanation of a governed run using the stable explainability / lineage contract exposed by the server.

At minimum, it must explain:

- run identity,
- run status,
- context used,
- shadow vs non-shadow mode,
- key events emitted,
- proof artifact references,
- final outcome,
- rejection/defer/replay reason when applicable,
- suggested next step when useful.

### 5.2 Inspect a request

```text
keyhole inspect <request-id>
```

This command must answer the question:

```text
what happened to this request?
```

It must be able to surface:

- request identity,
- whether the request executed, replayed, conflicted, deferred, or failed,
- whether a run was created,
- associated run_id if present,
- context linkage if present,
- proof references,
- repair guidance.

### 5.3 Generate a support bundle

```text
keyhole support-bundle <run-id|request-id>
```

This command must create a portable support artifact set that preserves enough governed truth for a human or another system to reconstruct the case without scraping raw logs manually.

---

## 6. Human-Readable Explanation Contract

The client must render explanations in language that is precise, bounded, and useful.

Each explanation should clearly distinguish between:

- **request** — what the client asked for,
- **run** — what governed execution object existed,
- **context** — what governed state-of-truth the run was bound to,
- **event chain** — what the Event Spine recorded,
- **proof** — what replayable artifacts were materialized,
- **verdict/outcome** — what happened and why.

### Required explanation sections

A compliant explanation should include sections equivalent to:

1. **Summary**
2. **Identity / Scope**
3. **Request / Run Mapping**
4. **Context Used**
5. **Key Events**
6. **Outcome**
7. **Reason / Repair Guidance**
8. **Proof References**

### Important rule

The client must not overstate certainty.

If the server says “deferred” or “pending,” the client must not render “failed.”
If the server says “replayed,” the client must not imply fresh execution.
If the lineage surface is incomplete, the client must say so explicitly rather than inventing explanation.

---

## 7. Outcome Classes the Client Must Explain

At minimum, the client must support deterministic explanation for these outcome classes:

### 7.1 Accepted / Succeeded

Explain:

- what was accepted,
- what run executed,
- what context was used,
- what proof exists,
- what terminal outcome was reached.

### 7.2 Rejected

Explain:

- what rule or validation condition caused rejection,
- whether rejection occurred pre-admission or post-admission,
- what the builder can do next.

### 7.3 Replayed

Explain:

- that the request did not create a new governed action,
- which prior attempt/result was reused,
- what idempotency/request linkage caused replay,
- where to inspect the original run/proof.

### 7.4 Deferred

Explain:

- why the platform deferred action,
- whether the defer is overload-related, budget-related, scheduling-related, or dependency-related,
- how to continue or wait safely.

### 7.5 Rate-limited / Budget exhausted

Explain:

- which limit was hit,
- whether the request can be retried,
- whether retry must use the same request identity,
- whether a wait window or repair action exists.

### 7.6 Failed / Terminal error

Explain:

- whether failure was local or remote,
- what governed artifacts still exist,
- what proof/support bundle was created,
- what next-best action is recommended.

---

## 8. Support Bundle Contract

The support bundle must be deterministic, portable, and safe to attach to support workflows.

### 8.1 Minimum support bundle contents

Recommended minimum structure:

```text
support_bundle/
  summary.md
  request.json
  run.json
  context.json
  events.json
  proof_refs.json
  outcome.json
  repair.json
  metadata.json
```

If some surfaces are unavailable, the bundle must include an explicit placeholder or omission note rather than silently dropping expected sections.

### 8.2 Required semantics

- `summary.md` — human-readable executive summary
- `request.json` — request identity and key request metadata
- `run.json` — run metadata and status if a run exists
- `context.json` — context reference or digest, if applicable
- `events.json` — key lineage events or server-provided event references
- `proof_refs.json` — pointers to proof artifacts / digests
- `outcome.json` — final machine-readable outcome classification
- `repair.json` — deterministic suggested next actions
- `metadata.json` — bundle generation details, timestamps, CLI version

### 8.3 Safety requirement

The support bundle must not include secrets, tokens, or privileged local credentials.

It may include:

- IDs,
- digests,
- references,
- non-secret payload summaries,
- proof locations or references,
- bounded lineage summaries.

---

## 9. Local Client Responsibilities

The client is responsible for:

- taking user-facing identifiers (`run-id`, `request-id`),
- resolving the correct inspection/explain flow,
- formatting explanation safely,
- creating support bundles locally from server-returned truth,
- preserving deterministic file structure,
- surfacing repair guidance clearly.

The client is **not** responsible for:

- inventing lineage,
- inferring server truth that is not returned,
- exposing internal-only or privileged server details,
- bypassing the explainability contract,
- directly querying canonical memory as a substitute for explain surfaces.

---

## 10. Explainability Rendering Rules

### 10.1 Readability first

Human-readable output must be concise but complete enough to answer the builder’s immediate question.

### 10.2 Stable section ordering

The same outcome class should render in the same section order every time.

### 10.3 Distinguish known from inferred

If some explanation content is inferred client-side from stable server-returned metadata, it must be labeled or structurally separated from authoritative server-provided reason fields.

### 10.4 Repair guidance mandatory on non-success

Every non-successful explanation must end with deterministic next-best-action guidance where possible.

---

## 11. Local Proof and Artifact Expectations

Each explain / inspect / support-bundle invocation should itself be attributable.

Recommended local artifact location:

```text
proof_bundle/
  explain/
  inspect/
  support_bundle/
```

Each invocation should preserve:

- command executed,
- target id,
- timestamp,
- response snapshot,
- rendered output reference,
- bundle location if generated.

This supports replay and regression testing of explainability UX.

---

## 12. Error Handling and Repair Guidance

The client must distinguish between the following classes of explainability failure:

### 12.1 Not found

- run or request does not exist,
- wrong tenant/profile/context,
- expired or unavailable target.

### 12.2 Incomplete lineage available

- some references exist, but not all required surfaces are available,
- explanation must render partial truth honestly.

### 12.3 Unauthorized or scope mismatch

- builder is not allowed to inspect the target,
- explanation must fail safely and clearly.

### 12.4 Server contract issue

- explainability surface returned malformed or incomplete data,
- client must fail clearly and preserve diagnostic artifacts.

### 12.5 Repair guidance examples

- switch to the correct profile
- verify the run_id or request_id
- wait and retry if lineage is still materializing
- run `keyhole whoami`
- generate a support bundle from the request instead of the run

---

## 13. Local Test Strategy

### 13.1 Command parsing tests

- `keyhole explain run <id>` parses correctly
- `keyhole inspect <request-id>` parses correctly
- `keyhole support-bundle <run-id|request-id>` parses correctly

### 13.2 Rendering tests

- accepted/succeeded renders correctly
- rejected renders correctly
- replayed renders correctly
- deferred renders correctly
- budget/rate-limited renders correctly
- partial lineage renders honestly

### 13.3 Support-bundle tests

- bundle files created deterministically
- required sections present
- secret material excluded
- missing sections represented explicitly

### 13.4 Negative tests

- unknown run id handled deterministically
- unknown request id handled deterministically
- malformed explain response fails clearly
- unauthorized inspection renders safe denial

### 13.5 Zipper / boundary tests

- users can recover why a run was accepted, rejected, replayed, or deferred
- support bundle contains request/run/context/event/proof linkage
- explainability is deterministic and replayable

---

## 14. Acceptance Criteria

This story is complete only when all of the following are true:

1. the client exposes `keyhole explain run <id>`
2. the client exposes `keyhole inspect <request-id>`
3. the client exposes `keyhole support-bundle <run-id|request-id>`
4. accepted, rejected, replayed, and deferred outcomes render deterministically
5. explanations distinguish request, run, context, events, proof, and final reason
6. support bundles are generated deterministically and safely
7. support bundles contain request/run/context/event/proof linkage when available
8. missing lineage is rendered honestly rather than invented
9. non-success outcomes include repair guidance
10. explainability output is replayable from stable server-returned truth
11. zipper proof demonstrates deterministic explainability against `sdk-server-20.md`

---

## 15. Zipper Expectations Against `sdk-server-20.md`

The paired server story must provide:

- explainability / lineage lookup surfaces
- support bundle generation or retrieval
- stable reason contract
- stable lineage contract
- recoverable request → run → context → event → proof mapping

SDK-CLIENT-20 closes only when the paired server proof demonstrates:

- users can recover why a run was accepted, rejected, replayed, or deferred
- support bundle contains request/run/context/event/proof linkage
- explainability is deterministic and replayable

---

## 16. Forward-Compatibility Notes

This story should be implemented in a way that composes cleanly with:

- SDK-CLIENT-15 idempotent transport,
- SDK-CLIENT-16 context lifecycle,
- SDK-CLIENT-17 async run tracking,
- SDK-CLIENT-18 memory boundary enforcement,
- SDK-CLIENT-19 budget and overload visibility.

That means the explanation renderer must be ready to include:

- request identity,
- idempotency/replay semantics,
- explicit context digest,
- accepted async run lifecycle,
- budget posture,
- and lawful absence of direct memory explanation bypass.

---

## 17. Non-Goals

SDK-CLIENT-20 does **not**:

- expose privileged server internals,
- replace raw operator/debug tooling,
- create arbitrary search across platform internals,
- bypass support policy,
- expose direct canonical memory debugging surfaces,
- invent reasons the server did not return.

---

## 18. Story Closure Statement

SDK-CLIENT-20 closes the final user-trust layer of the client roadmap.

When this story closes, a builder must be able to say:

```text
I know what happened
I know why it happened
I know what the system used
I know what proof exists
and I know what to do next
```

without needing privileged backend access or manual forensic work.
