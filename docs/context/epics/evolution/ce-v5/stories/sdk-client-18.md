# SDK-CLIENT-18 — Memory Boundary Enforcement

**Status:** DRAFT  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (design + validation), Prod (governed promotion only; no uncontrolled canonical mutation)  
**Surface:** Client  
**Zipper Pair:** `sdk-server-18.md`  
**Purpose:** Define the client-side memory boundary so the SDK does not expose direct canonical memory query/write as a public primitive, and instead routes all lawful memory interaction through governed context or governed run surfaces.

---

## 1. Story Purpose

SDK-CLIENT-18 hardens the client boundary around memory.

Its job is not to make memory more powerful.
Its job is to make the SDK **incapable of encouraging the wrong architecture**.

This story makes the following true:

- the public SDK does **not** expose direct canonical memory query/write methods,
- builders interact with memory only through governed context or governed run flows,
- client-side APIs and CLI commands reinforce that memory is a governed derivative layer, not a generic vector database,
- illegal direct-memory attempts fail early and clearly,
- the developer experience still remains usable through helper surfaces that preserve the boundary rather than bypass it.

This story is part of the client-side reflection of the S47 memory/context containment doctrine.

---

## 2. Why This Story Exists

The revised SDK-CLIENT epic explicitly states:

- governed execution must be context-bound,
- the client must not expose direct canonical memory access,
- memory interaction must occur through governed run/context surfaces. 

If the SDK were to expose a public shape like:

```python
client.memory.query(...)
client.memory.write(...)
```

then the client would immediately train builders to think of Keyhole memory as a normal application database or generic semantic store.

That would be architecturally wrong.

Keyhole memory is not the control plane.
It is not canonical truth.
It is not a free-form builder playground.
It is a governed, derived layer whose interaction must be mediated by:

- context,
- governed execution,
- Event Spine lineage,
- proof surfaces,
- and server-side policy.

So this story exists to ensure the client boundary itself cannot quietly undo the memory-governance work happening server-side.

---

## 3. Story Goals

The client must provide all of the following:

1. **No direct canonical memory query/write surface exposed publicly**
2. **Context- or run-mediated helper APIs only**
3. **Clear developer messaging about governed memory access**
4. **Deterministic local rejection when a caller attempts illegal memory access through unsupported routes**
5. **A migration-safe UX that still gives developers ways to achieve legitimate goals without teaching the wrong model**

This story is not anti-memory.
It is anti-bypass.

---

## 4. Scope

### Included

- public CLI and SDK surface design for memory-related behavior
- explicit prohibition of direct canonical memory query/write APIs in the public SDK
- context-mediated helper flows
- run-mediated helper flows
- error and repair messaging for illegal access attempts
- docs/help output that explains why memory is governed the way it is
- zipper expectations against `sdk-server-18.md`

### Excluded

- server-side context gating implementation
- server-side elimination of unsafe direct memory surfaces
- direct Qdrant hardening
- memory schema redesign
- traceability metadata design itself
- query deduplication and budgeting internals
- context compilation semantics

Those are handled in the server-side and S47 stories. This story ensures the client boundary does not undermine them.

---

## 5. Core Principle

The public SDK must not teach builders this mental model:

```text
my app talks directly to memory
```

It must instead teach this mental model:

```text
my app participates through governed context and governed runs
and memory is one derivative layer inside that system
```

That distinction is the entire purpose of this story.

---

## 6. Allowed Client Surfaces

The client may expose helper surfaces that are lawful because they are mediated through context or runs.

### 6.1 Context-mediated helpers

Examples of acceptable public shapes:

```python
client.context.compile(...)
client.context.get(...)
client.context.inspect(...)
```

These surfaces let builders work with governed context artifacts, not raw memory.

### 6.2 Run-mediated helpers

Examples of acceptable public shapes:

```python
client.run(...)
client.run_with_context(...)
```

or CLI equivalents:

```text
keyhole run --context <digest>
keyhole run --context auto
```

These surfaces allow memory-relevant activity only as part of a governed execution path.

### 6.3 Explainability / inspection helpers

Where appropriate, the client may expose read surfaces for:

- proof bundles
n- support bundles
- explainability artifacts
- run inspection
- context inspection

These are lawful because they are not raw canonical memory primitives.

---

## 7. Forbidden Client Surfaces

The client must not expose public APIs or commands that imply canonical memory is directly queryable or mutable by the builder.

### Forbidden examples

```python
client.memory.query(...)
client.memory.search(...)
client.memory.get(...)
client.memory.write(...)
client.memory.upsert(...)
client.memory.delete(...)
```

CLI equivalents are also forbidden as public builder commands:

```text
keyhole memory query
keyhole memory get
keyhole memory write
keyhole memory delete
```

unless a future story explicitly introduces a tightly governed inspection-only surface under a different contract and name.

This story assumes the answer is **no public direct canonical memory surface**.

---

## 8. Helper UX Requirements

The absence of direct memory APIs must not make the SDK confusing.

So the client must provide alternate paths that are:

- clear,
- discoverable,
- repair-oriented,
- governance-aligned.

### 8.1 If a developer wants "memory access"

The client should guide them toward:

- `keyhole context compile`
- `keyhole context inspect`
- `keyhole run --context ...`
- `keyhole explain run <id>`
- proof or support-bundle inspection

### 8.2 If a developer attempts illegal direct access

The client must respond with a deterministic, helpful message, for example:

```text
Direct canonical memory access is not exposed by the public SDK.
Use governed context or governed run surfaces instead.
Suggested next steps:
- keyhole context compile
- keyhole run --context <digest>
- keyhole explain run <id>
```

### 8.3 Message quality rule

The client must explain **what to do instead**, not only what is forbidden.

---

## 9. Client API Contract

### 9.1 Public API shape

Public SDK namespaces should be structured so that memory is not presented as a top-level builder primitive.

Preferred shape:

```python
client.auth.*
client.repo.*
client.context.*
client.run.*
client.proof.*
client.explain.*
```

Not preferred:

```python
client.memory.*
```

### 9.2 Internal client code

Internal plumbing may still talk about memory as an implementation concern where needed, but those internal details must not leak into the stable public SDK contract.

### 9.3 Documentation rule

Examples, tutorials, shell completion, and help text must never imply that builders should use raw canonical memory surfaces directly.

---

## 10. CLI Contract

### 10.1 No public direct memory commands

The CLI must not ship with direct canonical memory commands as first-class public builder commands.

### 10.2 Lawful alternatives

The CLI should steer users to:

```text
keyhole context compile
keyhole context inspect
keyhole run --context <digest>
keyhole explain run <id>
keyhole support-bundle <run-id|request-id>
```

### 10.3 Help / completion behavior

Autocomplete, help text, command docs, and examples must reinforce the same boundary.

---

## 11. Error and Repair Contract

Illegal direct memory attempts must fail:

- deterministically,
- early,
- with repair guidance,
- without ambiguity.

### Required fields in client-side error mapping

- error class
- short reason
- boundary explanation
- lawful alternatives
- link or hint to context/run/explain command

### Example SDK exception category

```text
DirectMemoryAccessNotAllowed
```

### Example CLI failure output

```text
REJECT — Direct canonical memory access is not exposed by the public SDK.
Why: memory is governed through context and run surfaces.
Try:
  keyhole context compile
  keyhole run --context <digest>
  keyhole explain run <id>
```

---

## 12. Relationship to Context and Runs

This story depends on the client exposing **better alternatives**.

### 12.1 Context lifecycle alignment

SDK-CLIENT-16 provides:

- `keyhole context compile`
- `keyhole context inspect`
- `keyhole run --context <digest>`

That means SDK-CLIENT-18 does not leave the builder stranded. It redirects them to the correct governance boundary.

### 12.2 Run execution alignment

SDK-CLIENT-09 and SDK-CLIENT-17 provide:

- governed runtime execution
- async-safe run tracking
- explainable run outcomes

That means the client can honestly say:

```text
use the run surface
not a direct memory surface
```

---

## 13. Proof Contract

This story must produce proof that the client boundary itself enforces the memory doctrine.

### Required local proof outputs

Recommended minimum:

```text
proof_bundle/
  memory_boundary/
    attempted_surface.json
    rejection.json
    summary.md
```

For positive proof paths, artifacts may show:

- lawful context-mediated call
- lawful run-mediated call
- absence of direct-memory surface from command or SDK discovery

### Proof must demonstrate

- direct canonical memory methods are not publicly exposed
- illegal direct attempts fail deterministically
- repair guidance is present
- lawful alternatives exist and are surfaced clearly

---

## 14. Local Test Strategy

### 14.1 Public API tests

- assert no public `client.memory.query` exists
- assert no public `client.memory.write` exists
- assert no public direct canonical memory namespace is exported

### 14.2 CLI tests

- assert no `keyhole memory query` public command exists
- assert no `keyhole memory write` public command exists
- assert help text points users to context/run alternatives

### 14.3 Negative tests

- attempted direct memory helper import fails or is absent
- attempted direct memory CLI command fails deterministically
- error output includes repair guidance

### 14.4 Positive path tests

- `keyhole context compile` remains available
- `keyhole context inspect` remains available
- `keyhole run --context <digest>` remains available
- explain/proof surfaces remain available

### 14.5 Zipper tests

In the paired server proof:

- illegal direct client memory paths are explicitly rejected
- client cannot reach canonical memory outside lawful context/run path
- no SDK canonical memory bypass remains

---

## 15. Acceptance Criteria

This story is complete only when all of the following are true:

1. the public SDK exposes **no direct canonical memory query/write surface**
2. the public CLI exposes **no direct canonical memory query/write command**
3. lawful alternatives exist through context or governed run surfaces
4. direct illegal attempts fail deterministically
5. direct illegal attempts include repair guidance
6. client help/docs/examples reinforce the governed memory model correctly
7. no public SDK canonical memory bypass remains
8. zipper proof shows server-side rejection of illegal client memory attempts
9. the client boundary aligns with S47 memory containment rather than weakening it

---

## 16. Zipper Expectations Against `sdk-server-18.md`

The paired server story must provide:

- context-gated memory access
- elimination of unsafe direct memory surfaces
- explicit rejection of illegal client memory paths

SDK-CLIENT-18 closes only when the paired server proof demonstrates:

- client cannot query canonical memory without lawful context/run path
- illegal direct memory attempts fail deterministically
- no direct SDK canonical memory bypass remains

---

## 17. Forward-Compatibility Notes

This story does **not** forbid future richer governed memory inspection tooling.

It does require that any future tooling:

- remain context-bound or inspection-bound,
- avoid presenting canonical memory as a generic builder database,
- preserve proof, context, event, and run lineage expectations.

If a future story adds memory inspection capabilities, it must do so under a stricter, explicitly governed contract rather than weakening this one.

---

## 18. Non-Goals

SDK-CLIENT-18 does **not**:

- redesign the memory system
- expose Qdrant directly
- provide generic semantic search over canonical memory as a public builder API
- replace context inspection or explainability surfaces
- prevent all internal platform code from referencing memory as an implementation concern
- eliminate server-side memory work by itself

It only defines the **public client boundary**.

---

## 19. Story Closure Statement

SDK-CLIENT-18 closes when the client can truthfully say:

```text
The SDK does not expose direct canonical memory access.
If you want memory-relevant behavior, you must come through governed context,
governed runs, or explainability/proof surfaces.
```

That is the client-side reflection of the memory containment doctrine.
