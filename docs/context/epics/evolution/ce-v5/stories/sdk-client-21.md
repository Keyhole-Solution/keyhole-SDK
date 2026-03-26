# SDK-CLIENT-21 — Surface Negotiation & Compatibility Guardrails

**Status:** DRAFT  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (design + validation), Prod (governed promotion only; no uncontrolled canonical mutation)  
**Surface:** Client  
**Zipper Pair:** `sdk-server-21.md`  
**Purpose:** Define the client-side startup and first-call compatibility contract for negotiating real MCP boundary posture before executing governed work. This story ensures the SDK does not blindly assume async execution, context enforcement, idempotency guarantees, explainability surfaces, or other runtime capabilities exist everywhere.

---

## 1. Story Purpose

SDK-CLIENT-21 establishes the client-side discipline for **surface negotiation**.

Its job is to ensure that the SDK behaves like a governed client rather than a hopeful API wrapper.

That means the client must:

- discover what the live server actually supports,
- distinguish **required** surfaces from **optional** ones,
- fail closed when required safety guarantees are absent,
- degrade gracefully when optional convenience surfaces are absent,
- expose the negotiated result to the builder clearly,
- carry that result forward into later commands rather than re-assuming unsupported behavior.

This story exists because the client roadmap now depends on surfaces that may arrive at different times:

- accepted async execution,
- context-bound governed runs,
- idempotency enforcement,
- explainability and support bundle lookup,
- budget/limit inspection,
- stream/tail capability,
- memory boundary enforcement.

The client must not guess.

---

## 2. Why This Story Exists

Without compatibility guardrails, the SDK will drift into a dangerous pattern:

```text
client assumes the platform is more complete than it is
```

That creates three classes of failure:

1. **False safety**
   - client assumes idempotent writes but the server does not enforce them yet
   - client assumes governed runs require context when they do not
   - client assumes async acceptance semantics exist when the boundary still returns inline results only

2. **False breakage**
   - optional surfaces such as explainability or stream/tail are missing
   - the client treats the absence as fatal even when core governed participation is still possible

3. **Opaque mismatch**
   - builder sees strange behavior with no explanation
   - same SDK behaves differently across environments
   - support and debugging become narrative-based instead of contract-based

SDK-CLIENT-21 prevents those failures by forcing the client to negotiate reality at startup or first authenticated call.

---

## 3. Story Goals

The client must implement:

- feature / capability negotiation at startup or first authenticated call
- version / surface compatibility checks against live server posture
- fail-closed behavior for unsupported **required** features
- graceful degraded UX for unsupported **optional** features
- clear builder-facing messaging when a required surface is unavailable
- a local, inspectable record of the negotiated result

This story is not about inventing new platform features.
It is about ensuring the client speaks truthfully about what the platform can do **right now**.

---

## 4. Scope

### Included

- negotiation against `GET /mcp/v1/capabilities` or equivalent declared surface
- startup or lazy-first-auth negotiation behavior
- compatibility evaluation rules
- required vs optional feature classification
- deterministic local handling of missing required features
- deterministic degraded UX for missing optional features
- local artifact or cache of negotiation result
- builder-facing inspection and explanation of negotiation posture
- zipper expectations against `sdk-server-21.md`

### Excluded

- implementation of async execution itself
- implementation of idempotency itself
- implementation of context enforcement itself
- implementation of explainability itself
- long-term version migration policy across all future SDK majors

This story consumes those declarations. It does not create them.

---

## 5. Negotiation Principles

### 5.1 Truth before convenience

The client must prefer accurate capability detection over optimistic fallback.

### 5.2 Required vs optional must be explicit

The client must classify capabilities into at least two classes:

- **required** — absence blocks specific commands or all governed participation
- **optional** — absence degrades UX or observability but does not necessarily block operation

### 5.3 No silent assumption

The client must never silently assume:

- accepted async execution exists,
- context enforcement exists,
- idempotency enforcement exists,
- explainability exists,
- stream/tail exists,
- budget visibility exists.

### 5.4 Stable messaging

A builder should be able to run one inspection command and understand:

- what the server supports,
- what the client expected,
- what is blocked,
- what is degraded,
- what the next repair step is.

---

## 6. Capability Classes

The client must maintain a compatibility model with at least the following categories.

### 6.1 Required surfaces

These are features whose absence must cause fail-closed behavior for relevant commands.

Examples:

- authenticated identity surface
- capabilities declaration surface
- repo registration surface when using `repo register`
- idempotency enforcement for write-bearing commands once the client declares it mandatory
- governed context requirement / context compile support for commands that require context binding
- stable run dispatch contract for governed runtime participation

### 6.2 Optional surfaces

These are features whose absence should degrade gracefully but not necessarily block the builder.

Examples:

- explainability surface
- support-bundle retrieval
- stream/tail event follow
- budget / limit inspection
- advanced capability-discovery enrichment
- optional trust metadata verification endpoints

### 6.3 Environment-declared transitional surfaces

The client may also recognize surfaces that are present but marked transitional, preview, or degraded.

This is especially important while the platform is moving from synchronous to accepted-async execution.

---

## 7. Negotiation Trigger

The client may negotiate in one of two patterns.

### 7.1 Startup negotiation

At CLI startup or session bootstrap:

- fetch server posture,
- evaluate required/optional features,
- cache result for the current profile/session.

### 7.2 First authenticated call negotiation

If startup negotiation is too early or expensive, the client may negotiate on the first authenticated command that requires server posture.

In both cases, the user must not be left unaware that negotiation happened.

---

## 8. Canonical Server Source

The canonical source for negotiation is:

```text
GET /mcp/v1/capabilities
```

or an explicitly equivalent server-declared surface.

The server response must provide enough information for the client to determine support for:

- async run contract
- context compile / get support
- governed context enforcement on runs
- idempotency expectations
- explainability surfaces
- support-bundle surfaces
- stream/tail support
- budget / limit visibility
- version compatibility / feature flags / operation disclosure

The client must not require hidden endpoints to infer these.

---

## 9. Client Negotiation Model

The client must normalize the server response into a local compatibility object.

### 9.1 Minimum local model

```json
{
  "server_version": "…",
  "surface_fingerprint": "…",
  "operations": ["…"],
  "features": {
    "run_async_accept": true,
    "context_compile": true,
    "context_required_for_runs": false,
    "idempotency_required": false,
    "explainability": false,
    "support_bundle": false,
    "run_tail": false,
    "budget_visibility": false
  },
  "compatibility": {
    "status": "ok | degraded | blocked",
    "required_missing": [],
    "optional_missing": []
  }
}
```

### 9.2 Local artifact

The normalized negotiation result must be cached locally for the active profile/session and be inspectable.

### 9.3 Freshness

The client may cache negotiation results briefly, but it must be able to refresh them deterministically.

---

## 10. Command UX

The client should provide at least one explicit inspection surface such as:

```text
keyhole surfaces
```

or equivalent.

This command should display:

- server identity / version if available
- active negotiated surface set
- required missing features
- optional missing features
- whether the client is in:
  - `compatible`
  - `degraded`
  - `blocked`
  posture

It may also show recommended repair steps.

---

## 11. Fail-Closed Rules

If a **required** surface is missing, the client must fail closed for the affected workflow.

### 11.1 Examples

If write-bearing commands require idempotency enforcement but the server posture does not declare it, the client must not proceed with those commands.

If governed runtime execution requires context enforcement but the server posture does not provide the required context surfaces, the client must block the context-bound run workflow rather than silently weaken it.

If repo registration requires a registration endpoint that is missing or version-incompatible, `keyhole repo register` must fail closed.

### 11.2 UX requirement

Fail-closed messaging must explain:

- what surface is missing,
- why it is required,
- which command is blocked,
- how the builder may recover (upgrade server, switch environment, use shadow mode, etc.).

---

## 12. Graceful Degradation Rules

If an **optional** surface is missing, the client must degrade gracefully.

### 12.1 Examples

If explainability is missing:
- `keyhole explain run` may return a deterministic “surface unavailable” message
- core runtime commands remain available if otherwise compatible

If support-bundle retrieval is missing:
- local proof artifacts may still be generated
- server-enriched support-bundle functionality may be unavailable

If stream/tail is missing:
- `keyhole runs tail` may degrade to polling or become unavailable with a clear message

### 12.2 UX requirement

Degraded mode must not feel like random failure.
It must be explicit and bounded.

---

## 13. Compatibility Evaluation Rules

The client must define deterministic rules for deciding whether a command is allowed.

Example evaluation flow:

1. determine command requirements
2. compare against negotiated surface posture
3. if any required feature missing:
   - block
4. if only optional features missing:
   - degrade
5. otherwise:
   - proceed

This evaluation must be transparent enough to support local tests and user-facing explanation.

---

## 14. Integration with Other SDK Stories

SDK-CLIENT-21 is cross-cutting and must interoperate with:

- **SDK-CLIENT-15** — idempotent transport, retry, and request identity
- **SDK-CLIENT-16** — context lifecycle and governed run binding
- **SDK-CLIENT-17** — async run tracking and stream-safe UX
- **SDK-CLIENT-19** — budget / limit / overload visibility
- **SDK-CLIENT-20** — governance explainability and support bundles

This story ensures the client only attempts to use those surfaces when the server posture says they really exist.

---

## 15. Local Artifacts

The client must materialize a local negotiation artifact suitable for proof and support.

Recommended minimum:

```text
proof_bundle/
  compatibility/
    capabilities_raw.json
    negotiation_result.json
    summary.md
```

### Required semantics

- `capabilities_raw.json` preserves the raw server response
- `negotiation_result.json` preserves normalized client interpretation
- `summary.md` explains the resulting posture in builder-readable form

---

## 16. Proof Contract

Every negotiation cycle must be able to prove:

- what the server declared,
- how the client interpreted it,
- which required surfaces were missing, if any,
- which optional surfaces were missing, if any,
- why a command was blocked or degraded.

The proof must support later questions such as:

- why did this client refuse to run?
- why did this client hide or degrade a feature?
- what did the server say it supported at the time?

---

## 17. Local Test Strategy

### 17.1 Positive tests

- capabilities response parsed successfully
- normalized negotiation object created deterministically
- fully compatible server posture yields `compatible`
- missing optional feature yields `degraded`
- missing required feature yields `blocked`

### 17.2 Negative tests

- malformed capabilities response rejected deterministically
- unknown version/feature shape handled safely
- client does not silently assume unavailable features
- stale cached negotiation can be refreshed correctly

### 17.3 Command-level tests

- blocked command fails closed with repair guidance
- degraded command surfaces graceful reduced UX
- inspection command shows current negotiation posture
- negotiation artifact written locally

### 17.4 Zipper tests

- client detects missing required surface and fails closed with repair guidance
- client detects missing optional surface and degrades gracefully
- client does not assume accepted async, context enforcement, or explainability exist everywhere
- surface negotiation result is visible and inspectable

---

## 18. Acceptance Criteria

This story is complete only when all of the following are true:

1. the client negotiates live server posture at startup or first authenticated call
2. the client normalizes server capability/surface declarations deterministically
3. required feature absence causes fail-closed behavior
4. optional feature absence causes graceful degraded behavior
5. builder-facing messaging explains why a feature is blocked or degraded
6. the client does not assume accepted async, context enforcement, idempotency enforcement, or explainability exist everywhere
7. surface negotiation results are visible and inspectable
8. negotiation artifacts are written locally for proof/support use
9. command-level compatibility checks are deterministic
10. zipper proof demonstrates truthful compatibility behavior against the paired server story

---

## 19. Non-Goals

SDK-CLIENT-21 does **not**:

- replace full version negotiation across all future SDK majors
- hide real incompatibility behind best-effort guesses
- invent missing server features
- make optional features mandatory prematurely
- downgrade required safety guarantees for convenience

---

## 20. Zipper Expectations Against `sdk-server-21.md`

The paired server story must provide:

- capability / surface declaration via `GET /mcp/v1/capabilities` or equivalent
- versioned feature flags or operation disclosure
- explicit async / context / idempotency / explainability support disclosure

SDK-CLIENT-21 closes only when paired proof shows:

- client detects missing required surface and fails closed with repair guidance
- client detects missing optional surface and degrades gracefully
- client does not assume accepted async, context enforcement, or explainability exist everywhere
- negotiation result is visible and inspectable on both sides of the zipper

---

## 21. Story Closure Statement

SDK-CLIENT-21 is the story that stops the SDK from confusing **wishful architecture** with **live boundary truth**.

When this story closes, the client must be able to say:

```text
this is what the server actually supports
this is what I require
this is what I can still do safely
and this is why
```

That is the minimum honest posture required before broad externalization.
