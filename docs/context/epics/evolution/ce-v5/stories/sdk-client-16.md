# SDK-CLIENT-16 — Context Lifecycle and Governed Run Binding

**Status:** DRAFT  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (design + validation), Prod (governed promotion only; no uncontrolled canonical mutation)  
**Surface:** Client  
**Zipper Pair:** `sdk-server-16.md`  
**Purpose:** Define the client-side contract for governed context lifecycle management and explicit run binding, including `keyhole context compile`, `keyhole context inspect`, `keyhole run --context <digest>`, optional `--context auto` helper UX, durable context-to-run linkage expectations, and repair-oriented handling when context is missing, invalid, stale, or incompatible.

---

## 1. Story Purpose

SDK-CLIENT-16 is the story that turns context from a background platform concept into a **first-class builder-visible runtime boundary**.

By the time a builder reaches this story, the client already knows how to:

- authenticate,
- scaffold a governed repo,
- validate local artifacts,
- generate a capability passport,
- register a repo,
- discover capabilities,
- and invoke governed runtime work.

What is still missing at that stage is the single most important execution discipline for the external platform:

```text
no governed run may float without explicit governed context
```

This story therefore introduces the client-side UX and contract for:

- compiling governed context,
- inspecting governed context,
- binding runs to a specific `ctxpack_digest`,
- making context visible rather than implicit,
- preserving context lineage in proof and inspection artifacts,
- rejecting contextless governed execution early when possible,
- and remaining forward-compatible with later async, idempotency, explainability, and budget-enforcement stories.

This story is not just a new CLI command set.
It is the first story where the SDK teaches the builder that:

```text
execution happens against a declared state-of-truth
not a vague current environment
```

---

## 2. Why This Story Exists

The current platform work already established that context is becoming the lawful execution boundary for governed work, and that memory and execution must not drift into contextless behavior. The revised `sdk-client-INDEX` explicitly hardens this principle by requiring that the client not permit governed runs to float without explicit governed context, while still allowing helper UX so long as the helper does not hide the boundary. fileciteturn0file0

This story exists because without explicit client-side context lifecycle support, builders will naturally fall into one of four bad patterns:

1. **Context omission**  
   Builders run governed work without understanding that context is required.

2. **Context invisibility**  
   The client may compile or infer context behind the scenes, but the builder cannot see which state-of-truth artifact actually governed execution.

3. **Context recomputation confusion**  
   Builders repeatedly compile context without understanding reuse, digest identity, or when context has changed.

4. **Weak proof / replay semantics**  
   A run result exists, but it is unclear which context artifact governed it.

Those patterns are unacceptable for Keyhole standards because they weaken:

- deterministic execution,
- explainability,
- repair guidance,
- proof lineage,
- memory containment,
- and future SDK-scale runtime safety.

SDK-CLIENT-16 closes that seam by making context a first-class, inspectable, explicit client artifact.

---

## 3. Story Goals

The client must provide:

- `keyhole context compile`
- `keyhole context inspect`
- `keyhole run --context <digest>`
- optional helper UX such as `--context auto`, while preserving explicit visibility
- durable recording of context identity in local proof artifacts
- clear repair guidance when context is missing, invalid, incompatible, or stale
- forward compatibility with server-side context admission enforcement and later run-tracking stories

The client must **not**:

- silently substitute hidden context and pretend execution was explicit,
- allow governed runs to appear contextless,
- turn `--context auto` into an invisible magic shortcut with no digest visibility,
- expose direct canonical memory access as a substitute for context.

---

## 4. Scope

### Included

- CLI command contract for `keyhole context compile`
- CLI command contract for `keyhole context inspect`
- CLI contract for `keyhole run --context <digest>`
- helper UX for context auto-resolution / auto-compilation
- local artifact handling for context summaries and proof references
- client-side validation for context argument presence and basic shape
- request shaping to server-side context compile/get and governed run admission surfaces
- explicit context-to-run lineage recording in local proof artifacts
- zipper expectations against `sdk-server-16.md`

### Excluded

- final context cache implementation internals on the server
- final async run tracking UX (`accepted + run_id`, polling, tailing)
- final idempotent write-bearing retry logic
- budget/limit visibility
- final explainability and support bundle tooling
- memory query surfaces

Those are tightened further by later stories, especially SDK-CLIENT-17 through SDK-CLIENT-20.

---

## 5. Command Contract

### 5.1 `keyhole context compile`

Primary purpose:

- compile or resolve a governed context artifact for the current repo and active identity context.

Expected behavior:

- gather the required local inputs,
- call the context compile surface,
- receive a deterministic context result,
- surface `ctxpack_digest` clearly,
- write local summary/proof references,
- optionally persist a local pointer to the active or most-recent context artifact reference.

The command must not pretend context is merely a debug artifact. It is a runtime boundary artifact.

### 5.2 `keyhole context inspect`

Primary purpose:

- inspect a specific `ctxpack_digest` or the most recent locally known context artifact.

Expected behavior:

- render digest,
- show high-level summary of what the context represents,
- show lens/lane if available,
- show evidence or artifact reference if available,
- show whether the context is appropriate for governed run binding,
- help the builder understand what they are actually binding their run to.

### 5.3 `keyhole run --context <digest>`

Primary purpose:

- execute a governed run under an explicit, builder-chosen governed context artifact.

Expected behavior:

- require a digest value,
- include that digest in the run request,
- surface that context binding in local proof,
- fail clearly if the digest is missing, malformed, rejected, or incompatible.

### 5.4 Optional helper UX: `--context auto`

This story may support helper UX such as:

```text
keyhole run --context auto
```

This is allowed **only if explicit visibility is preserved**.

That means the client may:

- compile context automatically,
- resolve the resulting digest,
- then proceed to run under that digest,

but it must still show the builder:

- which context digest was produced or selected,
- that the run is bound to that digest,
- and where that context artifact can be inspected.

The helper must never reduce to:

```text
just trust us, we figured it out
```

That would violate the explicit-boundary rule.

---

## 6. Preconditions

Before compiling or binding context, the client must verify as applicable:

1. the user is authenticated,
2. required local credentials exist,
3. the repo contains the canonical scaffold,
4. local declaration artifacts exist in a minimally valid form,
5. the repo is in a state suitable for context compilation,
6. the requested digest argument is present when `--context <digest>` is used,
7. `--context auto` is not combined with incompatible manual options.

The client must fail locally when a problem is obvious locally.

Examples:

- no authenticated profile,
- missing repo root markers,
- malformed digest string,
- mutually exclusive CLI flags.

Do not send obviously-invalid requests to the boundary just to learn what the client already knows.

---

## 7. Local Input Sources

The client may use the following local sources to shape context-related requests:

- `keyhole.yaml`
- `governance_contract.yaml`
- `capability_passport.yaml`
- `dependencies.yaml`
- active local credential / identity context
- current repo metadata
- prior local validation artifacts
- the most recent locally recorded context reference, when explicitly requested

The client must not fabricate missing repo truth or silently assume a digest.

---

## 8. Context Compile Request Construction

When the builder runs `keyhole context compile`, the client must construct a deterministic compile request from:

- active identity context,
- repo identity,
- requested mode or defaults,
- local repo metadata,
- declared purpose/origin where required,
- correlation metadata,
- proof-bundle seed metadata.

The compile request must be:

- deterministic for the same local state,
- attributable to the current builder and repo,
- suitable for inspection in local proof output,
- forward-compatible with later context caching and replay stories.

The client must preserve enough local request metadata to later explain:

- which repo state was used,
- which identity context was used,
- which command initiated the compile,
- and what digest the compiler returned.

---

## 9. Context Inspect UX

`keyhole context inspect` must make context intelligible to a builder.

At minimum, inspection should surface:

- `ctxpack_digest`
- summary / display header
- repo identity
- tenant/org/workspace context where available
- lens / lane if surfaced by the server
- evidence / artifact reference if available
- time of creation / local observation timestamp
- whether the context is the one most recently used for a run

The purpose is not to dump raw JSON only.
The purpose is to let a builder understand:

```text
what state-of-truth this digest actually represents
```

Raw output modes may still exist for automation.

---

## 10. Governed Run Binding Contract

When the builder executes:

```text
keyhole run --context <digest>
```

The client must:

1. validate that a digest string is present,
2. include that digest in the governed run request,
3. preserve the digest in local proof artifacts,
4. render the bound digest clearly in terminal output,
5. distinguish between local-preflight errors and server-admission rejections.

This story does **not** require the client to fully validate whether the digest exists remotely before submission if that validation belongs to the server.

But it does require the client to:

- treat context binding as mandatory for governed runs under this story line,
- preserve explicitness,
- never silently drop the digest.

---

## 11. Auto Context UX Contract

If `--context auto` is supported, the client must follow this contract:

### 11.1 Allowed behavior

- compile context automatically,
- show the resulting digest,
- bind the run to that digest,
- optionally persist a local “most recent context” reference.

### 11.2 Forbidden behavior

- hide the resulting digest,
- run without showing the builder what context was chosen,
- silently choose a different digest later,
- silently fall back to contextless execution if compile fails.

### 11.3 Required output example

The builder must see something like:

```text
Compiled context: ff5264504e88...
Binding governed run to context ff5264504e88...
```

Not just:

```text
Running...
```

Explicit visibility is the entire point.

---

## 12. Result Rendering

### 12.1 Successful context compile

Must show at minimum:

- success status,
- `ctxpack_digest`,
- repo identity,
- context artifact/proof location,
- next suggested action (for example: run with this context).

### 12.2 Successful context inspect

Must show:

- digest,
- summary,
- evidence or artifact reference,
- whether the context is currently active / recent / run-bound if known.

### 12.3 Successful run with context

Must show:

- run outcome,
- bound `ctxpack_digest`,
- correlation id,
- proof artifact location,
- shadow mode if applicable.

### 12.4 Failures

Must show:

- missing context
- invalid digest shape
- context not found
- context incompatible
- stale/invalid context (if server says so)
- clear repair suggestions

A failure must never collapse into an opaque “bad request.”

---

## 13. Repair Guidance Contract

The client must surface specific next-best actions when context-related commands fail.

Examples include:

- run `keyhole context compile` first
- run `keyhole context inspect <digest>` to verify the selected digest
- rerun with `--context auto`
- ensure repo validation passes before context compile
- refresh authentication if context compile was rejected due to auth scope
- choose a valid digest from the local recent-context list

Repair guidance must distinguish:

- local misuse,
- remote rejection,
- stale or missing context,
- incompatible run/context combination.

---

## 14. Local Artifact and Proof Contract

The client must generate or update local proof artifacts for context lifecycle activity.

Recommended minimum outputs:

```text
proof_bundle/
  context/
    compile-request.json
    compile-response.json
    inspect-output.json
    summary.md
    recent-contexts.json
  run/
    request.json
    response.json
    context-binding.json
```

### Required semantics

- context compile emits proof even when it fails,
- inspect output may be materialized for reproducibility,
- run proof must include the bound `ctxpack_digest`,
- auto-context mode must record the compile → bind transition,
- later stories must be able to reuse these local artifacts for explainability/support bundles.

---

## 15. Local Test Strategy

SDK-CLIENT-16 must support the following tests.

### 15.1 Local client tests

- command parsing for `keyhole context compile`
- command parsing for `keyhole context inspect`
- command parsing for `keyhole run --context <digest>`
- parsing and mutual-exclusion behavior for `--context auto`
- malformed digest rejected locally
- missing digest rejected locally when explicit digest required
- deterministic compile request shaping
- proof artifact generation for compile
- proof artifact generation for inspect
- proof artifact generation for context-bound run
- auto-context flow preserves explicit digest visibility

### 15.2 Zipper / boundary tests

- governed run without context rejected
- valid context visible and inspectable
- context → run linkage durable and queryable
- repair guidance emitted for missing/invalid context

### 15.3 Negative tests

- hidden fallback from missing context to contextless run does not occur
- auto mode does not hide the resulting digest
- invalid or unknown digest produces clear failure UX
- inspect on unknown digest produces deterministic repair guidance

---

## 16. Acceptance Criteria

This story is complete only when all of the following are true:

1. the client exposes `keyhole context compile`
2. the client exposes `keyhole context inspect`
3. the client supports `keyhole run --context <digest>`
4. optional helper UX such as `--context auto` preserves explicit digest visibility
5. governed run without context is rejected at the appropriate layer
6. valid context is visible and inspectable to the builder
7. local proof artifacts preserve context compile and context-bound run lineage
8. context → run linkage is durable and queryable through paired proof/server surfaces
9. repair guidance exists for missing, invalid, incompatible, or stale context
10. the story remains forward-compatible with later async/idempotency/explainability hardening

---

## 17. Zipper Expectations Against `sdk-server-16.md`

The paired server story must provide:

- context compile / get surfaces
- governed run admission requiring `ctxpack_digest`
- deterministic context validation
- durable context → run linkage

SDK-CLIENT-16 closes only when the paired server proof demonstrates:

- governed run without context rejected
- valid context visible and inspectable
- context → run linkage durable and queryable
- repair guidance for missing / invalid context

---

## 18. Forward-Compatibility Notes

This story must be implemented in a way that does **not** block later hardening.

Later stories extend this surface for:

- async run tracking and accepted execution
- request identity and idempotent retry
- budget and limit visibility
- explainability and support-bundle lookup
- stricter memory/context traceability

Therefore SDK-CLIENT-16 must avoid assumptions such as:

- every run still returns a final result inline forever,
- context auto-mode can stay implicit,
- context inspection never needs richer lineage,
- proof bundles do not need to carry digest-level lineage later.

---

## 19. Non-Goals

SDK-CLIENT-16 does **not**:

- implement the full server-side context cache
- provide final async run waiting/tailing UX
- expose direct canonical memory query/write APIs
- replace registration or validation
- implement final budget/overload visibility
- hide context from the builder in the name of convenience

---

## 20. Story Closure Statement

SDK-CLIENT-16 is the story that makes governed context visible and real at the client boundary.

When this story closes, a builder must be able to:

```text
compile a governed context
inspect that context
run against that context explicitly
and prove afterward which context governed execution
```

without needing to guess what state-of-truth the platform was actually using.
