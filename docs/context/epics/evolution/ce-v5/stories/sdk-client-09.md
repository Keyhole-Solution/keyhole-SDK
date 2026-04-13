**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (implementation + validation), Prod (governed promotion only; no uncontrolled canonical mutation)  
**Surface:** Client / CLI / SDK Run Dispatch  
**Story Type:** Client-side zipper story  
**Paired Server Story:** `sdk-server-09.md`  
**Depends On:** `sdk-client-00.md`, `sdk-client-01.md`, `sdk-client-01-a.md`, `sdk-client-02.md`, `sdk-client-15.md`, SDK-CLIENT master guidance, official MCP ingress contract  
**Precedes:** `sdk-client-16.md`, `sdk-client-17.md`, richer explainability and inspection flows  
**Last Updated:** 2026-04-13

---

## 1. Purpose

SDK-CLIENT-09 defines the canonical client-side execution contract for:

```text
keyhole run
keyhole run --shadow

This is the first builder-facing story where the SDK stops being only an onboarding and scaffold surface and becomes a governed runtime participant.

The purpose of this story is to make the following true:

a builder can invoke governed execution through a canonical CLI entrypoint,
the request is shaped lawfully from local repo and identity truth,
transport behavior inherits the request identity and idempotency discipline of SDK-CLIENT-15,
shadow mode is first-class and explicit,
outcomes are rendered clearly and truthfully,
proof artifacts are emitted into the canonical scaffold created by SDK-CLIENT-02,
failure paths produce deterministic repair guidance instead of dead ends.

This story must support the real boundary as it exists now while remaining forward-compatible with:

explicit governed context enforcement,
accepted/deferred execution with run_id,
polling / follow / wait surfaces,
richer proof and explainability UX,
budget and overload visibility,
stricter support tooling.
2. Why This Story Exists

Without a governed run surface, the SDK remains only a login, scaffold, and metadata tool.

Builders need a canonical action that says:

take this governed repo
take my current identity
take this explicit execution mode
and ask the platform to perform lawful governed work

This story creates that first runtime bridge.

It is also where the CLI begins teaching the builder the real shape of Keyhole execution:

execution is governed, not arbitrary,
outcomes are attributable,
proof matters,
shadow mode is a real participation posture,
repair guidance matters,
transport safety is already part of the client contract.

SDK-CLIENT-09 is therefore the first story that turns the SDK from artifact preparation into governed participation.

3. Story Role

This story sits on top of the completed foundation:

sdk-client-00 / 01 / 01-a
  → identity, auth bootstrap, active participant context

sdk-client-02
  → canonical local governed repo scaffold

sdk-client-15
  → request identity, operation-class transport discipline,
    retry safety, replay-aware proof continuity

sdk-client-09
  → first governed run command surface

sdk-client-16+
  → explicit governed context lifecycle, accepted/deferred run UX,
    inspection, explainability, budget visibility

This story does not create a separate control plane in the client.

The server remains authoritative for execution outcomes.

The client is responsible for:

local preflight,
exact request shaping,
lawful transport classification,
honest rendering of returned outcomes,
proof and repair continuity.
4. Scope
Included
keyhole run
keyhole run --shadow
local preflight checks before dispatch
exact request construction from local repo + active identity + run intent
operation-class-aware transport through the SDK-CLIENT-15 layer
shadow mode signaling
proof artifact emission into canonical proof paths
terminal UX for inline results
terminal UX for accepted / deferred results
deterministic repair guidance
Excluded
full context lifecycle implementation
final polling / follow / tail / wait UX
final explainability and support-bundle UX
final budget and overload inspection UX
direct canonical memory access of any kind
server-side execution semantics beyond the paired zipper contract

Those belong to later stories.

5. Command Contract
5.1 Primary command
keyhole run

Executes a governed runtime request using:

the current repo,
the active local credential context,
the current live boundary posture,
the declared execution mode.
5.2 Shadow command
keyhole run --shadow

Performs the same command flow while explicitly marking the request as shadow participation.

Shadow mode must be visible in:

request payload / metadata where supported,
local proof artifacts,
terminal rendering,
summary output.
5.3 Suggested argument classes

The client may support bounded, structured arguments such as:

keyhole run --run-type <key>
keyhole run --context <path-or-ref>
keyhole run --context auto
keyhole run --input <file>
keyhole run --output <path>
keyhole run --proof <mode>
keyhole run --shadow

Rules:

the client must not invent undocumented run types,
run-type selection must remain exact and validated,
--context auto is allowed only as an explicit helper, not as a hidden bypass,
command options must remain subordinate to the canonical governed runtime contract.
6. Preconditions

Before dispatching a governed run, the client must verify:

the user is authenticated,
active credentials are present and usable,
the repo contains the canonical scaffold required by SDK-CLIENT-02,
required declaration artifacts are present,
the chosen run mode is explicit,
the requested run type is valid under current discovery/preflight rules,
any context required by the current boundary for that run class is present or resolvable explicitly,
the client can classify the operation correctly for transport handling.

If preconditions fail, the client must not emit an ambiguous network request.

It must fail locally with deterministic repair guidance.

7. Local Input Sources

The client may shape the request from these local sources:

keyhole.yaml
governance_contract.yaml
capability_passport.yaml
dependencies.yaml
active local identity / credential context
optional CLI-provided run input files
optional explicit context references
optional local validation state where applicable

The client must not silently invent undeclared repo identity, capability state, or proof state.

8. Request Construction

The client must construct a governed run request from:

active identity context,
repo identity,
requested run type / action,
explicit execution mode (shadow or governed),
explicit context reference where present,
correlation / proof seed metadata,
any boundary-required request metadata.

Request construction must be:

deterministic for the same local input state,
inspectable in proof output,
lawful under the live MCP boundary,
compatible with later stricter context and async flows.
Important rule

This story must use the transport discipline already defined by SDK-CLIENT-15.

That means:

every request gets X-Request-Id,
operations classified as WRITE_IDEMPOTENT_REQUIRED get X-Idempotency-Key,
retries of the same attempt preserve the same operation identity,
the client must not bypass the central transport layer.
9. Operation-Class and Transport Handling

keyhole run must not treat all runs the same.

The client must classify the specific run request using the SDK-CLIENT-15 operation model:

READ_ONLY
WRITE_IDEMPOTENT_REQUIRED
NATURALLY_CONVERGENT_EXEMPT
INTERNAL_ONLY_NOT_EXPOSED

Rules:

read-only runs may omit X-Idempotency-Key,
write-bearing runs must use X-Idempotency-Key,
exemptions must be explicit and not guessed,
operation-class choice must be centralized, not reimplemented per command branch.

This prevents run dispatch from drifting into unsafe ad hoc transport behavior.

10. Boundary Outcome Modes

This story must not hard-code one forever outcome style.

The client must be able to render both of these lawfully:

10.1 Inline terminal result

The boundary returns a terminal result in the original request/response cycle.

The client must:

render terminal status clearly,
preserve proof artifacts,
surface repair guidance on failure.
10.2 Accepted / deferred result

The boundary returns an accepted or deferred response rather than a final terminal result.

The client must:

render acceptance or deferred state clearly,
preserve correlation / run references,
preserve proof artifacts,
suggest the next available inspection step,
avoid pretending the final work already completed.
Critical rule

The CLI must never fake synchronous success when the boundary only returned accepted/deferred state.

11. Shadow Mode Contract

Shadow mode exists to reduce adoption risk and make low-risk participation explicit.

When --shadow is used, the client must:

mark the request as shadow participation,
label terminal output clearly as shadow,
stamp shadow status into proof output,
avoid implying irreversible canonical consequences unless the server explicitly says so.

The client must never hide whether a run was shadow or non-shadow.

12. Outcome Rendering

The client must render outcomes clearly.

Minimum success rendering
status
run type / action
repo identity
shadow vs non-shadow
correlation identifier and/or run reference
proof artifact location
useful next step when available
Minimum failure rendering
failure class
deterministic reason
local-vs-remote distinction when possible
repair guidance
proof artifact location if generated
whether retrying the same attempt is safe
Important rule

A failure message must not be a dead end when the system can suggest a concrete next action.

13. Proof Contract

Every keyhole run invocation must emit or update local proof artifacts sufficient to explain:

what command was run,
when it was run,
which repo identity it used,
which execution mode it used,
what local inputs shaped the request,
which request/correlation identifiers were observed,
what the boundary returned,
what repair guidance was surfaced if it failed.
Required location discipline

This story must build on the scaffold created by SDK-CLIENT-02.

It must use the canonical proof structure rooted at:

proof_bundle/core/
proof_bundle/extended/

It must not invent a parallel proof root that conflicts with the scaffold.

Recommended artifact pattern

A reasonable structure is:

proof_bundle/
  core/
    runs/
      <correlation-or-run-ref>/
        request.json
        response.json
        summary.md
        correlation.json
  extended/
    runs/
      <correlation-or-run-ref>/
        render.log
        debug.json

The exact per-run sublayout may vary, but:

proof must exist for both success and failure,
shadow mode must be visible,
proof must remain deterministic enough for tests,
replay-aware transport metadata from SDK-CLIENT-15 must be preserved where applicable.
14. Event and Traceability Expectations

Even before full explainability lands, this story must establish that governed run participation expects:

attributable execution,
correlation continuity,
verifiable event lineage at the zipper level,
proof references that later inspection can use.

The client must preserve enough local metadata to correlate:

request
repo
identity context
run mode
shadow mode
proof output
returned outcome references
15. Repair Guidance Contract

If a run fails, the client must surface repair guidance from one or more of:

local preflight findings,
server-provided reason,
known client-side mapping of reject/error class to next action,
repo state inspection.

Acceptable examples include:

run keyhole validate
log in again
add or fix missing scaffold file
choose a valid run type
supply explicit context
try --shadow for a low-risk first pass
fix invalid contract field <field-name>

Repair guidance must be concrete and action-oriented.

16. Local Test Strategy
16.1 Local client tests

Must cover:

command parsing for keyhole run
command parsing for keyhole run --shadow
preflight failure when unauthenticated
preflight failure when scaffold is missing
deterministic request construction
deterministic shadow flag propagation
correct operation-class selection
transport layer invocation goes through the centralized SDK-CLIENT-15 client
proof artifacts created on success
proof artifacts created on failure
readable summary generation
repair guidance mapping
16.2 Boundary / zipper tests

Must prove:

run executes end-to-end
request identity is present
idempotency is present when required
correlation metadata survives across artifacts
failure paths render repair guidance clearly
16.3 Negative tests

Must cover:

invalid repo state blocks before dispatch
shadow mode cannot masquerade as non-shadow
malformed boundary response never appears as success
accepted/deferred responses do not render as final success
direct raw transport bypass is not used
17. Acceptance Criteria

This story is complete only when all of the following are true:

the client exposes keyhole run
the client exposes keyhole run --shadow
local preflight blocks obviously invalid runs before dispatch
request shaping is deterministic for the same local input state
operation-class transport discipline from SDK-CLIENT-15 is inherited correctly
shadow mode is explicit in request, output, and proof
terminal outcomes are rendered clearly
accepted/deferred outcomes are rendered honestly without fake completion claims
proof artifacts are emitted for both success and failure
correlation metadata is preserved locally
failure paths emit deterministic repair guidance
zipper evidence shows end-to-end governed run participation
the story remains forward-compatible with stricter context and richer inspection stories
18. Zipper Expectations Against sdk-server-09.md

The paired server story must provide:

governed run dispatch surface,
stable result envelope,
attributable execution metadata,
correlation continuity,
repair-oriented failure semantics.

SDK-CLIENT-09 closes only when zipper proof demonstrates:

request reached the governed run surface,
correlation survives across artifacts,
execution mode is visible,
failure paths remain repair-oriented,
outcome rendering matches actual server truth.
19. Forward-Compatibility Notes

This story must not block later hardening.

Later stories will tighten or expand this command surface for:

stricter governed context requirements,
accepted/deferred inspection UX,
polling / wait / tail behavior,
explainability and support bundles,
budget and overload visibility.

Therefore SDK-CLIENT-09 must avoid assumptions such as:

every run always returns final inline result,
context is permanently optional,
retries are raw resends,
proof belongs outside the canonical scaffold,
direct memory access belongs here.
20. Non-Goals

SDK-CLIENT-09 does not:

implement full context lifecycle enforcement,
implement final polling / follow / tail UX,
expose direct canonical memory access,
replace repo registration,
replace validation,
provide final budget/rate-limit introspection,
provide final explainability tooling,
hide the difference between shadow and non-shadow execution.
21. Story Closure Statement

SDK-CLIENT-09 is the first story where the SDK becomes a governed runtime participant.

When this story closes, a builder must be able to:

authenticate
stand in a lawful scaffolded repo
invoke a governed run
see an honest outcome
inspect proof artifacts
and know what to do next

without needing the full later runtime-hardening stack to understand the experience.