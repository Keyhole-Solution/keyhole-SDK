# SDK-CLIENT-19 — Budget, Limit, and Overload Visibility

**Status:** DRAFT  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (design + validation), Prod (governed promotion only; no uncontrolled canonical mutation)  
**Surface:** Client  
**Zipper Pair:** `sdk-server-19.md`  
**Purpose:** Define the client-side contract for surfacing runtime budget posture, execution limits, and overload outcomes so governed execution remains understandable, supportable, and trustworthy under pressure.

---

## 1. Story Purpose

SDK-CLIENT-19 exists to make runtime pressure **visible and intelligible** to builders.

A governed platform cannot feel arbitrary under load. When a run is:

- budget exhausted,
- deferred,
- rate limited,
- throttled,
- partially admitted,
- rejected due to concurrency or resource posture,

…the client must not render that outcome as a vague failure or transport mystery.

This story ensures that builders can:

- inspect budget posture,
- understand limit outcomes,
- distinguish platform pressure from business-logic rejection,
- receive deterministic repair guidance,
- reason about what to do next.

This story is not about inventing new runtime budgets. It is about making the existing and future server-side budget/limit model **usable at the client boundary**.

---

## 2. Why This Story Exists

By the time SDK-CLIENT-19 matters, the platform already supports:

- governed runs,
- accepted async execution,
- idempotent transport,
- context-bound participation,
- memory/query budgeting,
- overload-aware runtime behavior,
- durable proof and event lineage.

But unless the client can surface those conditions clearly, builders experience overload as:

```text
random failure
```

instead of:

```text
governed backpressure with an explainable reason
```

This story exists because a platform that enforces budgets but cannot explain them will feel unstable even when it is behaving correctly.

SDK-CLIENT-19 turns limit behavior into part of the product experience.

---

## 3. Story Goals

The client must provide:

- budget posture visibility where available,
- deterministic UX for overload and limit outcomes,
- clear distinction between runtime pressure and user error,
- repair guidance for `budget_exhausted`, `deferred`, `rate_limited`, `concurrency_limited`, and similar outcomes,
- proof and summary artifacts that preserve budget/limit information,
- forward-compatible rendering for future budget categories without rewriting the UX model.

This story does **not** require the client to invent or simulate server limits. It must faithfully present what the server declares.

---

## 4. Scope

### Included

- budget posture display on runs where the server provides it
- deterministic CLI rendering for overload outcomes
- inspection-friendly summaries of limit state
- budget/limit metadata integration into local proof artifacts
- repair-oriented next actions
- zipper expectations against `sdk-server-19.md`

### Excluded

- creation of new server budget categories
- autonomous client-side rate prediction
- hidden retries that mask overload
- policy decisions about what the limits should be
- final explainability bundles beyond what this story needs

---

## 5. Command / UX Surface

SDK-CLIENT-19 does not require one single command, but it must affect the following UX surfaces.

### 5.1 Inline run outcomes

When a run completes, is deferred, or is rejected due to pressure, the client must surface:

- final status,
- overload or limit classification,
- concise explanation,
- next-best action,
- proof/reference location.

### 5.2 Run inspection

The client should support budget/limit visibility through one or more inspection surfaces such as:

```text
keyhole runs status <run-id>
keyhole runs inspect <run-id>
```

or equivalent integrated output in existing run commands.

### 5.3 Resume / wait / tail integration

Where async run tracking already exists, budget/limit outcomes must appear coherently in:

- `status`
- `wait`
- `tail`
- `resume`

The builder must not have to infer limit conditions from disconnected logs.

---

## 6. Core UX Contract

The client must make the following distinctions obvious.

### 6.1 Budget exhaustion

Example classes:

- wall-time budget exhausted
- event budget exhausted
- memory query budget exhausted
- byte/output budget exhausted

### 6.2 Admission defer

Example classes:

- queue saturation
- deliberate defer under load
- temporary resource holdoff

### 6.3 Rate limiting

Example classes:

- per-user rate limit
- per-tenant rate limit
- per-cohort or per-runtime concurrency cap
- burst protection

### 6.4 Hard rejection vs temporary pressure

The client must clearly distinguish:

- **hard reject** — retrying immediately will not help
- **temporary defer / rate limit** — retry later or follow `Retry-After`
- **budget exhausted in-run** — request was admitted but could not complete within allowed resource bounds

---

## 7. Outcome Rendering Requirements

### 7.1 Success with budget visibility

If the server returns budget posture on a successful run, the client should surface concise budget summary such as:

- budget used
- budget remaining
- any near-limit warnings

without overwhelming the builder.

### 7.2 `budget_exhausted`

The client must render:

- the budget class that was exhausted,
- whether the run partially executed,
- whether retrying as-is is likely to fail again,
- suggested repair actions.

### 7.3 `deferred`

The client must render:

- that the request was not arbitrarily rejected,
- that the platform deferred due to governed pressure handling,
- whether retry timing or follow-up action is recommended.

### 7.4 `rate_limited`

The client must render:

- what kind of rate limit applied,
- whether `Retry-After` was returned,
- when and how to retry,
- that the request did not fail for semantic or contract reasons.

### 7.5 Unknown or future limit outcomes

The client must support a generic fallback rendering contract so new server limit types remain intelligible without a CLI redesign.

---

## 8. Repair Guidance Contract

Every overload or limit outcome must map to one or more repair actions.

Examples:

- retry after the indicated interval
- narrow the run scope
- use `--shadow` for exploratory execution
- wait for current runs to complete
- reduce output volume or target set
- inspect context or dependency shape if runaway work is suspected
- contact admin / inspect tenant limits where appropriate

The client must not leave the user with only:

```text
Request failed
```

Repair guidance must be deterministic and concrete whenever the server exposes enough information.

---

## 9. Proof Contract

The client must preserve budget and overload information in local proof artifacts when present.

### Minimum proof fields

Recommended minimum additions to runtime proof material:

- `run_id`
- `status`
- `limit_outcome`
- `limit_class`
- `budget_snapshot`
- `retry_after` if present
- `repair_guidance`
- `correlation_id`

### Summary requirements

`summary.md` or equivalent human-readable proof output must explain:

- whether the run was accepted, deferred, limited, or budget exhausted,
- whether the platform remained lawful under pressure,
- what the builder should do next.

### Important rule

Budget/limit data must be preserved even on failure, defer, or partial execution.

---

## 10. Local Behavior and Client Responsibilities

The client must:

- parse machine-readable limit outcomes from the server,
- preserve them in proof,
- render them deterministically,
- avoid hiding them behind generic exception wrappers,
- respect retry guidance where applicable,
- keep terminology stable across commands.

The client must **not**:

- silently retry until the limit clears,
- collapse all overload into generic network failure,
- invent unsupported budget numbers,
- tell the builder a request “succeeded” when it was actually deferred or terminated by budget law.

---

## 11. Server Expectations (`sdk-server-19.md`)

The paired server story must provide:

- budget/limit inspection surface,
- overload-aware accepted/denied semantics,
- stable machine-readable outcome classes,
- optional `Retry-After` or equivalent retry guidance,
- durable run-linked limit metadata where relevant.

The client side closes only when those server signals are available and the UX is proven end-to-end.

---

## 12. Test Strategy

### 12.1 Client rendering tests

- `budget_exhausted` renders correctly
- `deferred` renders correctly
- `rate_limited` renders correctly
- unknown future limit code renders through generic fallback
- repair guidance appears consistently
- proof artifact stores limit metadata

### 12.2 Inspection tests

- budget posture visible in run inspection output
- budget warnings do not overwhelm successful output
- limit outcomes remain stable across `status`, `wait`, and `resume` surfaces

### 12.3 Zipper tests

- client can inspect or display budget posture from server response
- overload does not appear as arbitrary failure
- budget/limit outcomes include repair guidance
- proof bundle links request → run → budget/limit outcome

### 12.4 Negative tests

- malformed limit payload handled safely
- missing optional budget fields degrade gracefully
- generic transport failure not misclassified as overload

---

## 13. Acceptance Criteria

This story is complete only when all of the following are true:

1. the client can surface run budget usage when the server provides it
2. the client can surface limit posture in a stable, human-readable way
3. `budget_exhausted` outcomes render deterministically
4. `deferred` outcomes render deterministically
5. `rate_limited` outcomes render deterministically
6. overload outcomes do not appear as arbitrary or generic failure
7. budget/limit outcomes include repair guidance
8. budget/limit metadata is preserved in proof artifacts
9. inspection surfaces can display budget posture where available
10. zipper proof shows request → run → budget/limit outcome clearly

---

## 14. Forward-Compatibility Requirements

This story must be implemented so new budget categories can be added without redesigning the client model.

The client must therefore treat limit outcomes as:

- a stable top-level category,
- optional structured metadata,
- optional retry guidance,
- optional quantitative budget fields.

The rendering layer must be extensible rather than hard-coded to exactly three status names forever.

---

## 15. Non-Goals

SDK-CLIENT-19 does **not**:

- decide or tune runtime budgets itself
- replace server overload control
- provide final full support-bundle UX
- predict future platform capacity precisely
- override rate limits locally
- expose raw server internals that are not part of the governed client contract

---

## 16. Story Closure Statement

SDK-CLIENT-19 closes when runtime pressure becomes **understandable**.

At that point, a builder must be able to experience overload and limits as:

```text
lawful, inspectable platform behavior
```

rather than:

```text
mysterious failure
```

That is the client-side standard required before broad external SDK usage can feel trustworthy under real load.
