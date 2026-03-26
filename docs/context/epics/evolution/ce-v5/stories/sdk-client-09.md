# SDK-CLIENT-09 — Governed Runtime Execution

**Status:** DRAFT  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (design + validation), Prod (governed promotion only; no uncontrolled canonical mutation)  
**Surface:** Client  
**Zipper Pair:** `sdk-server-09.md`  
**Purpose:** Define the client-side governed runtime execution contract for `keyhole run` and `keyhole run --shadow`, including local preflight validation, request shaping, identity/context propagation, outcome handling under the current runtime contract, traceable proof generation, and repair-oriented failure UX.

---

## 1. Story Purpose

SDK-CLIENT-09 is the first builder-facing execution story.

It defines how a builder takes an already-authenticated, already-scaffolded, already-validated repo and asks Keyhole to **do governed work**.

This story must make the following true:

- the client can invoke governed execution through a canonical CLI entrypoint,
- the request is shaped lawfully and predictably,
- identity and repo context are carried into the request,
- shadow mode is first-class and explicit,
- outcomes are readable and attributable,
- proof and event expectations are visible to the user,
- failure paths produce repair guidance rather than dead ends.

This story intentionally reflects the **current execution contract**, not the final fully externalized long-running async-safe contract. Broader write-bearing, idempotent, context-required, and accepted-async execution hardening is tightened later by SDK-CLIENT-15 through SDK-CLIENT-20.

---

## 2. Why This Story Exists

Without a clean governed run surface, the SDK is only a scaffolding and registration tool.

Builders need a canonical action that says:

```text
 take this governed repo context
 and ask the platform to execute something lawful
```

This story creates that first runtime bridge.

It is also the place where the client starts teaching the builder the shape of Keyhole execution:

- runs are governed, not arbitrary,
- outcomes are attributable,
- proof matters,
- event lineage matters,
- shadow execution is a real mode,
- failure must be explained.

SDK-CLIENT-09 therefore exists to convert the SDK from “artifact management” into “governed participation.”

---

## 3. Story Goals

The client must provide:

- `keyhole run`
- `keyhole run --shadow`
- deterministic request construction from local repo truth
- clear runtime-mode visibility
- human-readable terminal outcome handling under the current server contract
- proof-ready local artifacts
- correlation-aware traceability expectations
- deterministic repair guidance on failure

This story does **not** assume the final accepted-async run contract is already live everywhere.

It must work cleanly against the current boundary while staying forward-compatible with:

- async run IDs
- context-required execution
- idempotent write-bearing run semantics
- budget/limit visibility
- run inspection / explain surfaces

---

## 4. Scope

### Included

- client-side command contract for `keyhole run`
- client-side command contract for `keyhole run --shadow`
- local preflight checks before dispatch
- request payload shaping
- shadow mode signaling
- correlation and proof metadata generation
- result rendering for current synchronous server contract
- failure/repair UX
- zipper expectations against `sdk-server-09.md`

### Excluded

- final async polling / run tracking UX
- global client retry/idempotency enforcement
- mandatory context lifecycle enforcement
- budget visibility
- explainability/support bundle UX
- direct canonical memory access of any kind

Those are handled or tightened later by SDK-CLIENT-15 through SDK-CLIENT-20.

---

## 5. Command Contract

### 5.1 Primary command

```text
keyhole run
```

The command executes a governed runtime request using the current repo and active local credential context.

### 5.2 Shadow command

```text
keyhole run --shadow
```

The shadow command performs the same request shaping and governed submission posture, but explicitly marks the request as a shadow / low-risk participation mode.

Shadow mode must be visible in:

- request metadata
- local proof artifact
- terminal UX
- summary output

### 5.3 Optional argument classes

The client may support structured arguments such as:

- run type / action selector
- input artifact path
- target capability
- target repo scope
- local metadata overrides allowed by policy
- output location
- proof output mode

But all options must remain subordinate to the canonical governed runtime contract.

---

## 6. Preconditions

Before dispatching a governed run, the client must verify:

1. the user is authenticated
2. local credentials are present and valid enough to attempt runtime participation
3. the repo contains the minimum canonical scaffold
4. required declaration artifacts are present or the failure is explainable
5. current repo validation state is acceptable for the run class being attempted
6. shadow mode vs non-shadow mode is explicit

If preconditions fail, the client must **not** emit an ambiguous network request.

Instead it must fail locally with deterministic repair guidance.

---

## 7. Local Input Sources

The client may use the following local sources to shape the request:

- `keyhole.yaml`
- `governance_contract.yaml`
- `capability_passport.yaml`
- `dependencies.yaml`
- active local identity / credential context
- local repo metadata
- optional CLI-provided run input files
- optional local validation results

The client must not silently synthesize undeclared repo identity or capability state.

---

## 8. Request Construction

The client must construct a governed runtime request from:

- active identity context
- repo identity
- requested run action
- declared mode (`shadow` or regular)
- correlation metadata
- proof bundle seed metadata
- event classification hints when relevant
- request-scoped metadata required by the current boundary

At this story stage, request construction must be:

- deterministic for the same input set
- inspectable in local proof output
- forward-compatible with later idempotency/context hardening
- bounded to the current runtime contract

---

## 9. Current Contract Handling

The current server/runtime posture still supports a synchronous response pattern for this story line.

Therefore SDK-CLIENT-09 must support a clean “request → terminal result” UX under the current contract **without** pretending that the final long-running async model is already universally live.

This means the client must:

- submit the request
- wait for the current boundary response
- render terminal status clearly
- preserve correlation/proof metadata locally
- surface repair guidance on failure

The client must also be structured so that later stories can extend the same command surface to:

- accepted + run_id flows
- polling
- wait/follow/tail
- idempotent replay semantics

without breaking the public command shape.

---

## 10. Shadow Mode Contract

Shadow mode exists to lower adoption risk.

When `--shadow` is used, the client must:

- mark the request as shadow participation
- render shadow status clearly in terminal output
- stamp shadow mode into the local proof summary
- avoid implying irreversible platform-side canonical consequences unless the server explicitly says otherwise

The client must never hide whether a run was executed in shadow mode.

---

## 11. Outcome Rendering

The client must render outcomes clearly for builders.

### Success must show, at minimum:

- final status
- run type or action
- repo identity
- shadow vs non-shadow
- correlation identifier
- proof artifact location
- next-step suggestion where useful

### Failure must show, at minimum:

- failure class
- deterministic reason
- local vs remote failure distinction when possible
- repair guidance
- proof artifact location if generated
- whether retrying is likely to help

### Important rule

A failure message must never be a dead end if the system knows a likely repair path.

---

## 12. Event Traceability Expectations

Even though event querying and deeper explainability are expanded later, this story must establish that governed runtime participation expects:

- correlation_id continuity
- attributable event emission
- event classification metadata when applicable
- verifiable event chain expectations at the zipper level

The client must preserve enough local metadata so later inspection can correlate:

- request
- repo
- identity context
- shadow mode
- proof output
- server outcome

---

## 13. Proof Contract

Every `keyhole run` invocation must produce or update a local proof artifact set sufficient to explain:

- what command was run
- when it was run
- in what mode
- under what repo identity
- with what local inputs
- what the boundary returned
- what correlation id / references were observed
- where repair guidance was emitted if failed

### Minimum local proof outputs

Recommended minimum:

```text
proof_bundle/
  run/
    request.json
    response.json
    summary.md
    correlation.json
```

If the client already uses the broader proof bundle contract, it may integrate into that structure instead.

### Required semantics

- proof generation must not depend on success only
- failed runs still emit useful proof artifacts
- shadow mode must be visible in proof
- proof must be deterministic enough for test assertions

---

## 14. Repair Guidance Contract

If a run fails, the client must surface repair guidance from one or more of:

- local validation findings
- server-provided deterministic reason
- known client-side mapping of reject class → next action
- repo state inspection

Examples of acceptable repair guidance:

- run `keyhole validate`
- complete login again
- register the repo before running
- use `--shadow` for a low-risk first pass
- fix invalid contract field `X`
- choose a valid capability target

Repair guidance must be concrete.

---

## 15. Local Test Strategy

SDK-CLIENT-09 must support the following local and integration-style tests.

### 15.1 Local client tests

- command parsing for `keyhole run`
- command parsing for `keyhole run --shadow`
- local precondition failure when unauthenticated
- local precondition failure when repo scaffold is missing
- deterministic request construction
- deterministic shadow flag propagation
- local proof artifacts created on success
- local proof artifacts created on failure
- readable summary generation
- repair guidance mapping

### 15.2 Zipper / boundary tests

- run executes end-to-end
- `correlation_id` present across request and event chain
- event classification metadata stamped
- event chain verifiable
- failure paths emit repair guidance

### 15.3 Negative tests

- invalid repo state blocks before dispatch where appropriate
- server failure is rendered clearly
- shadow mode does not masquerade as non-shadow
- malformed runtime request never appears as success

---

## 16. Acceptance Criteria

This story is complete only when all of the following are true:

1. the client exposes `keyhole run`
2. the client exposes `keyhole run --shadow`
3. local preflight validation blocks obviously invalid run attempts
4. request shaping is deterministic for the same input state
5. shadow mode is explicit in request, output, and proof
6. terminal outcome is surfaced clearly under the current contract
7. proof artifacts are emitted for both success and failure
8. correlation metadata is preserved locally
9. failure paths emit deterministic repair guidance
10. zipper proof shows end-to-end governed run execution
11. event chain can be verified in the paired server proof
12. the story remains forward-compatible with SDK-CLIENT-15 through SDK-CLIENT-20

---

## 17. Zipper Expectations Against `sdk-server-09.md`

The paired server story must provide:

- governed run dispatch surface
- traceable event emission
- stable outcome envelope under the current contract
- correlation id continuity
- repair-oriented failure semantics

SDK-CLIENT-09 closes only when the paired server proof demonstrates:

- run executes end-to-end
- `correlation_id` is present across emitted artifacts
- event classification metadata is stamped
- event chain is verifiable
- failure paths emit repair guidance

---

## 18. Forward-Compatibility Notes

This story must be implemented in a way that does **not** block later hardening.

Later stories will extend or tighten this command surface for:

- client-side idempotency and retries
- context-required governed execution
- accepted async execution with `run_id`
- polling / wait / stream-safe run inspection
- budget and overload visibility
- explainability/support bundle lookup

Therefore SDK-CLIENT-09 must avoid assumptions such as:

- every run always returns final inline result forever
- context is always optional
- retries are raw resends
- memory access belongs here

---

## 19. Non-Goals

SDK-CLIENT-09 does **not**:

- implement final long-running execution UX
- expose direct canonical memory access
- replace local validation
- replace registration
- provide final budget or rate-limit introspection
- provide final support bundle tooling
- hide the difference between shadow and non-shadow execution

---

## 20. Story Closure Statement

SDK-CLIENT-09 is the first story where the SDK stops being only a configuration and artifact tool and becomes a governed runtime participant.

When this story closes, a builder must be able to:

```text
authenticate
validate a repo
invoke a governed run
see a clear outcome
inspect proof artifacts
and understand what to do next
```

without needing to understand all later scaling and runtime-hardening layers up front.
