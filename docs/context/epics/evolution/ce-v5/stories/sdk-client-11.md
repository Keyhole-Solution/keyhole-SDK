# SDK-CLIENT-11 — Alignment Guidance

**Status:** DRAFT  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (design + validation), Prod (governed promotion only; no uncontrolled canonical mutation)  
**Surface:** Client  
**Zipper Pair:** `sdk-server-11.md`  
**Purpose:** Define the client-side alignment-guidance contract that renders deterministic remediation suggestions, next-best actions, and inferred-vs-verified governance gaps from governed ingestion and gap-analysis results without mutating the repository silently.

---

## 1. Story Purpose

SDK-CLIENT-11 turns ingestion and validation output into **actionable builder guidance**.

By the time this story runs, the builder should already be able to:

- authenticate,
- initialize a governed repo,
- validate local declarations,
- generate a capability passport,
- register the repo,
- ingest a repo for graphing and inference.

What is still missing at that point is a clear answer to:

```text
what should I do next to bring this repo into stronger governance alignment?
```

This story exists to provide that answer.

It defines how the client:

- consumes gap-analysis output,
- distinguishes inferred state from verified state,
- renders remediation suggestions,
- ranks next-best actions,
- groups guidance by severity and confidence,
- preserves non-mutating behavior,
- and emits proof artifacts that explain what the platform recommended and why.

This is not a mutation story.
It is a **deterministic guidance story**.

---

## 2. Why This Story Exists

A governed platform that can only say “invalid” is not usable at scale.

Builders need the platform to do more than detect gaps.
They need it to tell them:

- what the gap means,
- how serious it is,
- what concrete action would improve alignment,
- what should happen first,
- what remains only inferred versus fully verified,
- and how to move forward without guessing.

SDK-CLIENT-10 already gives the client the ability to inspect a repository and package it for governed analysis. SDK-CLIENT-11 converts that analysis into a builder-facing remediation surface.

Without this story:

- ingestion yields opaque diagnostics,
- builders cannot prioritize fixes,
- inferred findings can be mistaken for authoritative truth,
- the platform feels like a scanner rather than a governed assistant,
- adoption becomes friction-heavy.

This story ensures the SDK behaves like a serious governed guidance tool rather than a bare inspection shell.

---

## 3. Story Goals

The client must:

- render remediation suggestions clearly,
- render next-best actions deterministically,
- preserve the distinction between inferred and verified findings,
- group, rank, and summarize alignment gaps,
- avoid silently mutating the repository,
- emit replayable proof artifacts describing what guidance was shown,
- remain consistent across repeated runs on the same analysis input.

This story must make the following true:

```text
same gap analysis input
→ same rendered guidance ordering and semantics
```

unless the server analysis output itself changes.

---

## 4. Scope

### Included

- client-side rendering of remediation suggestions
- client-side rendering of next-best actions
- deterministic ordering/grouping of guidance
- inferred-vs-verified state labeling
- local summary generation
- human-readable and machine-readable alignment guidance artifacts
- forward-compatible integration into proof bundles
- zipper expectations against `sdk-server-11.md`

### Excluded

- automatic repo mutation
- automatic contract rewriting
- automatic capability registration
- final explainability/support-bundle UX across all run types
- broader execution retry/idempotency work
- generic memory explainability surfaces

---

## 5. Command / UX Contract

SDK-CLIENT-11 may be surfaced through one or more of the following patterns:

```text
keyhole ingest .
keyhole ingest . --shadow
keyhole validate --suggest
keyhole align
keyhole align --from <analysis-artifact>
```

The exact command surface may evolve, but the client must provide a canonical builder-facing way to:

- display alignment guidance,
- display next-best actions,
- persist guidance artifacts,
- and replay the same guidance deterministically from stored analysis results.

This story does **not** require a brand-new top-level command if alignment guidance is rendered as part of `keyhole ingest` or `keyhole validate`, but the behavior must still be explicitly defined and testable.

---

## 6. Input Sources

The client may render alignment guidance from one or more of the following sources:

- server gap-analysis response,
- local ingestion result package,
- local validation result package,
- saved alignment artifact from a previous run,
- combined local + remote analysis results when the contract permits it.

The client must preserve provenance of each recommendation source.

It must not blur:

- server-verified findings,
- client-local validation findings,
- inferred capability suggestions,
- user-authored declarations.

---

## 7. Guidance Model

### 7.1 Guidance object types

The client must support at minimum the following categories:

- **gap** — a missing or noncompliant governed condition
- **warning** — a weaker but notable risk or ambiguity
- **suggestion** — a recommended improvement not yet required
- **next_best_action** — the top-ranked concrete action the builder should take next
- **inference** — a proposed capability / dependency / structural interpretation not yet verified

### 7.2 Required fields

A rendered guidance item should support fields such as:

```json
{
  "id": "gap.contract.missing_provider_pin",
  "class": "gap",
  "severity": "high",
  "confidence": 0.98,
  "state": "verified",
  "title": "Provider pin missing",
  "detail": "Dependency payment.stripe.integration.v1 has no provider pin.",
  "repair": [
    "Pin the provider in dependencies.yaml.",
    "Run keyhole search payment.stripe.integration.v1 to select a provider."
  ],
  "source": "server_gap_analysis",
  "artifact_ref": "..."
}
```

### 7.3 Verified vs inferred distinction

This story requires an explicit distinction between:

- **verified** findings — grounded in schema checks, server analysis, or deterministic evidence
- **inferred** findings — plausible suggestions derived from graphing, heuristics, or confidence-scored capability inference

The client must never render inferred findings as though they are already verified truth.

---

## 8. Deterministic Ordering Rules

The client must render suggestions in a stable, predictable order.

Recommended precedence:

1. blocking verified gaps
2. high-severity verified warnings
3. medium/low verified issues
4. inferred but high-confidence suggestions
5. lower-confidence optional improvements

Within a class, ordering should be deterministic based on a stable sort key, such as:

- severity,
- confidence,
- canonical gap id,
- artifact path,
- title.

The client must not present the same analysis in random order across repeated invocations.

---

## 9. Rendering Requirements

### 9.1 Terminal rendering

The CLI must show:

- total gap count,
- verified vs inferred counts,
- top next-best action,
- a clearly grouped list of issues,
- repair suggestions for each actionable item,
- a summary of what was **not** changed automatically.

### 9.2 Machine-readable output

The client must also materialize a machine-readable artifact for the same guidance set.

Recommended shape:

```text
proof_bundle/alignment/gap_analysis.json
proof_bundle/alignment/summary.md
proof_bundle/alignment/next_actions.json
```

### 9.3 Human-readable summary

The client must generate a concise summary explaining:

- current alignment status,
- the highest-priority remediation steps,
- what remains inferred,
- and whether the repo is ready for the next step (register, run, or remain in shadow).

---

## 10. No Silent Repo Mutation Rule

This story must preserve a hard platform law:

```text
guidance may suggest
but it may not silently mutate
```

The client must not:

- rewrite contracts automatically,
- add dependencies automatically,
- register inferred capabilities automatically,
- rename or delete files automatically,
- treat a suggestion as applied unless the builder explicitly applies it.

If future stories add assisted patch generation, that must still remain explicit and reviewable.

---

## 11. Next-Best Action Contract

The client must compute and display a **next-best action** when possible.

A next-best action must be:

- concrete,
- local to the builder’s current state,
- consistent with deterministic ordering,
- and non-ambiguous.

Examples:

- `Run keyhole validate after fixing governance_contract.yaml.`
- `Pin a provider for payment.stripe.integration.v1 in dependencies.yaml.`
- `Review inferred capability workorder.assignment.engine.v1 before registration.`
- `Use --shadow until unresolved high-severity gaps are fixed.`

If multiple actions are equally valid, the client must either:

- rank them deterministically, or
- present a clearly labeled ordered shortlist.

---

## 12. Confidence and Severity Semantics

The client must preserve both:

- **severity** — how important the issue is to governance correctness
- **confidence** — how certain the platform is that the finding is accurate

These are not interchangeable.

Examples:

- a high-severity missing provider pin with verified evidence,
- a medium-severity inferred capability with 0.72 confidence,
- a low-severity optional trust metadata suggestion.

The renderer must show enough of both to support sane builder judgment.

---

## 13. Local Artifact Contract

SDK-CLIENT-11 must emit local artifacts that preserve the guidance surface.

### Minimum recommended outputs

```text
proof_bundle/
  alignment/
    gap_analysis.json
    next_actions.json
    summary.md
    correlation.json
```

### Required semantics

- artifacts must be generated for both success and partial-failure cases where analysis results exist,
- inferred vs verified state must remain explicit in stored artifacts,
- summary text must not overclaim certainty,
- local artifacts must be deterministic enough for golden-file style tests.

---

## 14. Error Handling and Repair Guidance

If alignment guidance cannot be rendered cleanly, the client must explain why.

Possible failure classes include:

- no analysis artifact present,
- malformed server response,
- corrupted saved artifact,
- unsupported schema version,
- missing repo context,
- local render failure.

In all such cases, the client must provide repair guidance such as:

- rerun `keyhole ingest .`,
- rerun `keyhole validate`,
- update the CLI version,
- inspect the saved analysis artifact,
- use `--shadow` if appropriate.

---

## 15. Proof / Test Strategy

### 15.1 Local client tests

The client must support tests for:

- deterministic rendering order,
- verified vs inferred labeling,
- next-best-action selection,
- summary generation,
- machine-readable artifact creation,
- no silent repo mutation,
- repair guidance on malformed or missing analysis input.

### 15.2 Zipper / boundary tests

The paired server story must prove:

- gaps identified deterministically,
- suggestions reproducible,
- inferred vs verified state clearly distinguished,
- event `GAP_ANALYSIS_COMPLETE` emitted.

The client proof must demonstrate that those server outputs are rendered faithfully and deterministically.

### 15.3 Negative tests

The client must reject or clearly surface:

- ambiguous guidance records,
- missing required fields,
- inferred items incorrectly marked verified,
- non-deterministic ordering,
- any attempted auto-apply behavior.

---

## 16. Acceptance Criteria

This story is complete only when all of the following are true:

1. remediation suggestions render clearly in the client
2. next-best actions are produced deterministically when possible
3. inferred vs verified state is explicitly distinguished in terminal and artifact output
4. the same guidance input yields the same rendered ordering and semantics
5. local alignment artifacts are materialized
6. no silent repo mutation occurs
7. repair guidance is provided when rendering fails or inputs are invalid
8. zipper proof shows deterministic server gap analysis and reproducible suggestion generation
9. the client faithfully renders `GAP_ANALYSIS_COMPLETE`-backed analysis output
10. the builder can tell what to do next without guessing

---

## 17. Zipper Expectations Against `sdk-server-11.md`

The paired server story must provide:

- a deterministic gap analysis engine,
- deterministic suggestion generation,
- explicit inferred vs verified distinctions,
- event emission for `GAP_ANALYSIS_COMPLETE`,
- a stable analysis payload shape.

SDK-CLIENT-11 closes only when the paired zipper proves:

- gaps identified deterministically,
- suggestions reproducible,
- inferred vs verified state clearly distinguished,
- `GAP_ANALYSIS_COMPLETE` event emitted.

---

## 18. Forward-Compatibility Notes

This story must be implemented so it remains compatible with later stories for:

- explainability and support bundles,
- async run inspection,
- budget visibility,
- trust enforcement,
- deeper context-bound remediation surfaces.

The implementation must avoid assumptions such as:

- all findings are server-verified,
- all suggestions are immediately actionable,
- one analysis artifact always covers every future surface,
- mutation helpers already exist.

---

## 19. Non-Goals

SDK-CLIENT-11 does **not**:

- auto-fix the repo,
- modify contracts silently,
- register capabilities automatically,
- replace local validation,
- replace ingestion,
- expose full support-bundle functionality,
- overstate inferred analysis as canonical truth.

---

## 20. Story Closure Statement

SDK-CLIENT-11 is the story that makes the platform useful after it has inspected a repo.

When this story closes, a builder must be able to:

```text
run analysis
see what is wrong
see what is inferred
see what is verified
know what to do next
and keep full control of the repo
```

That is the minimum bar for governed alignment guidance.
