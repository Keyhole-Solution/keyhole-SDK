# sdk-client-20.md

# SDK-CLIENT-20 — Governance Explainability and Support Bundles

**Story ID:** SDK-CLIENT-20 / sdk-client-20  
**Epic:** SDK-CLIENT — Governed Developer SDK, Onboarding, Repository Ingestion, and Scale-Safe Runtime UX  
**Status:** READY FOR IMPLEMENTATION  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (implementation + validation), Prod (governed usage only; no uncontrolled canonical mutation)  
**Surface:** Client / CLI / SDK Explainability and Supportability  
**Story Type:** Client-side zipper story  
**Paired Server Story:** `sdk-server-20.md`  
**Depends On:** `sdk-client-00.md`, `sdk-client-01.md`, `sdk-client-01-a.md`, `sdk-client-09.md`, `sdk-client-15.md`, `sdk-client-16.md`, `sdk-client-17.md`, `sdk-client-18.md`, `sdk-client-19.md`, SDK-CLIENT master guidance, official MCP ingress contract  
**Precedes:** optional higher-level support tooling, richer operator-safe diagnostics, and later ecosystem-facing trust/reporting surfaces  
**Last Updated:** 2026-04-13

---

## 1. Purpose

SDK-CLIENT-20 closes the client-side trust layer for governed execution.

Its purpose is to answer a builder’s final practical question:

```text
what happened, why did it happen, what did the platform use, and what should I do next?

By the time a builder reaches this story, the client already supports:

authenticated participation,
governed run submission,
explicit context binding,
accepted/deferred lifecycle handling,
replay-safe transport behavior,
memory-safe public boundaries,
budget and overload visibility.

What is still missing is a stable, bounded, builder-readable explanation surface.

This story defines the client-side contract for:

keyhole explain run <id>
keyhole inspect <request-id>
keyhole support-bundle <run-id|request-id>

It makes the platform:

not just governed and powerful
but governed, powerful, and legible
2. Why This Story Exists

A governed platform that cannot explain itself will eventually feel like a black box.

By this stage of the client line, builders can already:

start governed runs,
bind them to context,
survive accepted/deferred execution,
observe pressure and limit behavior,
and preserve proof continuity.

But that still does not answer:

why was this request accepted?
why was it rejected?
why was it replayed instead of re-executed?
why was it deferred?
what context governed the run?
what event or proof references support the outcome?
what do I send to support or another engineer to reconstruct the case?

SDK-CLIENT-20 exists because execution without explanation is only half a product.

Without this story:

repair remains harder than necessary,
support becomes forensic log-diving,
replay/defer/limit outcomes feel mysterious,
and builder trust erodes at exactly the point where clarity matters most.
3. Core Thesis

Explainability must preserve and present the lawful layers of governed truth without inventing new ones.

The client must distinguish clearly between:

Request truth
What the client asked for and under which request identity.
Run truth
Whether a governed run exists, what its identity is, and what state it reached.
Context truth
What explicit governed context artifact was bound to execution.
Event and proof truth
What the platform emitted or referenced as attributable lineage and replayable evidence.
Rendered explanation
A bounded human-readable explanation assembled from those lawful sources.

The client must never blur these layers or invent missing server truth.

4. Strategic Role

SDK-CLIENT-20 sits on top of the already-sealed governed lifecycle:

sdk-client-09
  → governed run entrypoint

sdk-client-15
  → request identity, idempotency, retry safety, replay-aware transport

sdk-client-16
  → explicit governed context lifecycle and no-floating-run enforcement

sdk-client-17
  → accepted/deferred run tracking, wait, tail, resume

sdk-client-18
  → no public direct-memory bypass

sdk-client-19
  → budget, limit, and overload visibility

sdk-client-20
  → explanation, inspection, and portable supportability

This story does not replace those surfaces.

It makes them understandable together.

5. Scope
Included
keyhole explain run <run-id>
keyhole inspect <request-id>
keyhole support-bundle <run-id|request-id>
stable human-readable explanation rendering
request → run → context → event/proof linkage rendering
portable support-bundle creation
deterministic command output for known outcome classes
partial-lineage honesty
zipper expectations against sdk-server-20.md
Excluded
arbitrary privileged debug consoles
raw operator log browsing
direct Event Spine operator tooling
direct database access
direct canonical memory inspection
replacement of run tracking
replacement of proof generation
replacement of budget visibility
invention of reasons the server did not return

Those belong elsewhere.

6. Supported Targets

This story must work regardless of whether the underlying run originated from:

a Keyhole-native repo,
a foreign repo that was ingested and partially aligned,
a shadow run,
or a normal governed run.

The explainability surface is about governed execution identity, not repo purity.

That means the client must not assume:

in-repo proof is always available,
the repo is Keyhole-native,
every run has complete lineage immediately,
or every explanation can rely on local repo artifacts.

Explainability must remain truthful even when the repo is foreign or only partially aligned.

7. Command Contract
7.1 Explain a run
keyhole explain run <run-id>

This command must retrieve or reconstruct a human-readable explanation of a governed run using the stable explainability and lineage contract exposed by the server.

At minimum, it must explain:

run identity,
run status,
request linkage if known,
context used,
shadow vs non-shadow mode,
key event/proof references,
final outcome,
replay / defer / reject / limit reason when applicable,
suggested next step when useful.
7.2 Inspect a request
keyhole inspect <request-id>

This command must answer:

what happened to this request?

It should be able to surface:

request identity,
whether the request executed, replayed, deferred, conflicted, or failed,
whether a run was created,
associated run_id if present,
context linkage if present,
proof references,
repair guidance.
7.3 Generate a support bundle
keyhole support-bundle <run-id|request-id>

This command must create a portable, bounded, support-safe artifact set that preserves enough governed truth for a human or another system to reconstruct the case without privileged backend access.

8. Human-Readable Explanation Contract

The client must render explanations in language that is:

precise,
bounded,
useful,
and honest about uncertainty or incompleteness.

Each explanation must clearly distinguish between:

request
run
context
event/proof references
outcome
reason
repair guidance
Required explanation sections

A compliant explanation should include sections equivalent to:

Summary
Identity / Scope
Request and Run Mapping
Context Used
Key Evidence
Outcome
Reason and Repair Guidance
Proof / Support References
Important rule

The client must not overstate certainty.

If the server says:

deferred → do not render failed
replayed → do not imply fresh execution
accepted → do not imply terminal completion

If lineage is incomplete, the client must say so explicitly instead of inventing explanation.

9. Outcome Classes the Client Must Explain

At minimum, the client must support deterministic explanation for:

9.1 Accepted / succeeded

Explain:

what was accepted,
what run executed,
what context was used,
what proof/evidence exists,
what terminal outcome was reached.
9.2 Rejected

Explain:

what rule or validation condition caused rejection,
whether rejection occurred pre-admission or post-admission,
what the builder can do next.
9.3 Replayed

Explain:

that the request did not create a new governed action,
which prior attempt or result was reused,
what request/idempotency linkage caused replay,
where to inspect the original run/proof.
9.4 Deferred

Explain:

why the platform deferred action,
whether defer appears overload-related, scheduling-related, or dependency-related,
how to continue safely.
9.5 Rate-limited / budget exhausted

Explain:

which limit was hit,
whether the request can be retried,
whether retry should preserve the same request identity,
whether a wait window or repair action exists.
9.6 Failed / terminal error

Explain:

whether failure was local observation failure or remote terminal failure,
what governed artifacts still exist,
what support artifact can be generated,
what next-best action is recommended.
10. Support Bundle Contract

The support bundle must be:

deterministic,
portable,
bounded,
safe to attach to support workflows,
and free of secrets and credentials.
Minimum bundle contents

Recommended minimum structure:

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

If some sections are unavailable, the bundle must include an explicit omission note rather than silently dropping expected content.

Required semantics
summary.md — concise human-readable explanation
request.json — request identity and key metadata
run.json — run metadata and state if a run exists
context.json — explicit context reference if applicable
events.json — key event/proof references or bounded lineage summary
proof_refs.json — pointers to proof artifacts/digests
outcome.json — machine-readable final classification
repair.json — deterministic next-best actions
metadata.json — bundle generation details, CLI version, timestamps
Safety requirement

The support bundle must not include:

secrets
tokens
local credential stores
raw privileged backend logs

It may include:

IDs
digests
bounded metadata
reference summaries
support-safe evidence pointers
11. Local Client Responsibilities

The client is responsible for:

taking user-facing identifiers (run-id, request-id),
resolving the correct explain/inspect/support flow,
formatting explanation safely,
generating support bundles locally from lawful server-returned truth and local proof references,
preserving deterministic file structure,
surfacing repair guidance clearly.

The client is not responsible for:

inventing lineage,
fabricating server truth,
exposing internal-only operator details,
bypassing explainability contracts,
directly querying canonical memory as a substitute for explainability.
12. Rendering Rules
12.1 Readability first

Human-readable output must be concise but complete enough to answer the builder’s immediate question.

12.2 Stable section ordering

The same outcome class should render in the same section order every time.

12.3 Distinguish known from inferred

If some explanation text is synthesized client-side from stable server-returned metadata, it must be labeled or structurally separated from authoritative server-provided fields.

12.4 Repair guidance mandatory on non-success

Every non-successful explanation must end with deterministic next-best-action guidance when possible.

12.5 Accepted/deferred honesty

If the run is still accepted/deferred/non-terminal, the explanation must say so clearly and suggest status, wait, resume, or other lawful next steps where appropriate.

13. Transport and Lifecycle Alignment

This story must inherit the already-sealed client posture.

13.1 Transport inheritance

Explain, inspect, and support-bundle requests must continue to use the centralized transport layer and preserve request identity.

13.2 Context inheritance

Explanations must preserve explicit context linkage when context exists.

13.3 Async lifecycle inheritance

Explanations must work cleanly with:

accepted/deferred runs,
resumed runs,
partially observed runs.
13.4 Memory boundary inheritance

Explainability must not become a hidden memory bypass.
Memory-derived behavior may be surfaced only through lawful governed artifacts, context references, run outcomes, proof, or bounded lineage summaries.

13.5 Budget visibility inheritance

When budget or overload metadata exists, explanations must include it in the outcome and reason sections without redefining the underlying budget story.

14. Artifact Placement

Because many repos may be foreign or only partially aligned, explain/inspect/support artifacts must not assume in-repo placement by default.

Default local artifacts should live in a tool-owned local state path.

If the repo is already Keyhole-native and the builder explicitly opts in, the client may additionally mirror explainability artifacts into canonical in-repo proof paths.

Reasonable local structure
<tool-owned-state>/
  explain/
    <run-id-or-request-id>/
      response.json
      rendered.md
  inspect/
    <request-id>/
      response.json
      rendered.md
  support_bundle/
    <run-id-or-request-id>/
      summary.md
      request.json
      run.json
      context.json
      events.json
      proof_refs.json
      outcome.json
      repair.json
      metadata.json

These artifacts are for replayability and support, not for silently mutating the target repo.

15. Error Handling and Repair Guidance

The client must distinguish at least these classes of explainability failure:

15.1 Not found
run or request does not exist,
wrong profile/tenant/scope,
expired or unavailable target.
15.2 Incomplete lineage
some references exist, but not all surfaces are available yet,
explanation must render partial truth honestly.
15.3 Unauthorized or scope mismatch
the builder is not allowed to inspect the target,
explanation must fail safely and clearly.
15.4 Server contract issue
malformed or incomplete explainability response,
client must fail clearly and preserve diagnostic artifacts.
15.5 Repair guidance examples
switch to the correct profile
verify the run_id or request_id
wait and retry if lineage is still materializing
run keyhole whoami
generate a support bundle from the request if run lookup is incomplete
16. Local Test Strategy
16.1 Command parsing tests

Must verify:

keyhole explain run <id> parses correctly
keyhole inspect <request-id> parses correctly
keyhole support-bundle <run-id|request-id> parses correctly
16.2 Rendering tests

Must verify:

accepted/succeeded renders correctly
rejected renders correctly
replayed renders correctly
deferred renders correctly
rate-limited / budget-exhausted renders correctly
partial lineage renders honestly
non-terminal runs do not render as completed
16.3 Support-bundle tests

Must verify:

bundle files are created deterministically
required sections are present
missing sections are represented explicitly
secrets are excluded
request/run/context/event/proof linkage is preserved when available
16.4 Negative tests

Must verify:

unknown run ID handled deterministically
unknown request ID handled deterministically
malformed explain response fails clearly
unauthorized inspection renders safe denial
client does not invent lineage that was not returned
16.5 Zipper / boundary tests

Must verify:

builders can recover why a run was accepted, rejected, replayed, deferred, or limited
support bundles contain request/run/context/event/proof linkage
explainability is deterministic and replayable
17. Acceptance Criteria

This story is complete only when all of the following are true:

the client exposes keyhole explain run <id>
the client exposes keyhole inspect <request-id>
the client exposes keyhole support-bundle <run-id|request-id>
accepted, rejected, replayed, deferred, and limited outcomes render deterministically
explanations distinguish request, run, context, evidence, proof, and final reason
support bundles are generated deterministically and safely
support bundles contain request/run/context/event/proof linkage when available
missing lineage is rendered honestly rather than invented
non-success outcomes include repair guidance
explainability output is replayable from stable server-returned truth
zipper proof demonstrates deterministic explainability against sdk-server-20.md
18. Zipper Expectations Against sdk-server-20.md

The paired server story must provide:

explainability/lineage lookup surfaces
stable reason contract
stable lineage contract
recoverable request → run → context → event/proof mapping
support-safe evidence references or bundle ingredients

SDK-CLIENT-20 closes only when paired proof demonstrates:

builders can recover why a run was accepted, rejected, replayed, deferred, or limited
support bundles contain request/run/context/event/proof linkage
explainability is deterministic and replayable
19. Forward-Compatibility Notes

This story must compose cleanly with:

idempotent transport
explicit context lifecycle
accepted/deferred async run tracking
memory boundary enforcement
budget and overload visibility

That means the renderer must remain ready to include:

request identity
idempotency/replay semantics
explicit context digest
accepted/deferred run state
budget posture
lawful absence of direct-memory explainability bypass

without redesigning the command model later.

20. Non-Goals

SDK-CLIENT-20 does not:

expose privileged server internals
replace operator/debug tooling
create arbitrary search across platform internals
bypass support policy
expose direct canonical memory debugging surfaces
invent reasons the server did not return
21. Story Closure Statement

SDK-CLIENT-20 closes the final trust layer of the client roadmap.

When this story closes, a builder must be able to say:

I know what happened
I know why it happened
I know what context and governed artifacts were involved
I know what proof exists
and I know what to do next