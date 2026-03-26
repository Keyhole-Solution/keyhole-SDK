# SDK-CLIENT-10 — Repository Ingestion and Graph

**Status:** DRAFT  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (design + validation), Prod (governed promotion only; no uncontrolled canonical mutation)  
**Surface:** Client  
**Zipper Pair:** `sdk-server-10.md`  
**Purpose:** Define the client-side governed repository ingestion contract for `keyhole ingest` and `keyhole ingest --shadow`, including local repository scan, deterministic packaging, privacy-safe upload shaping, graph-ready artifact generation, confidence-aware inference boundaries, proof emission, and strict no-silent-mutation behavior.

---

## 1. Story Purpose

SDK-CLIENT-10 defines how an existing repository enters the Keyhole ecosystem **without requiring a greenfield scaffold first**.

This story must make the following true:

- a builder can point the SDK at an existing repo,
- the client can inspect it locally and package a governed ingestion request,
- shadow mode exists for low-risk first contact,
- the ingestion flow can produce architecture and capability graph outputs,
- inferred capabilities are clearly marked as inferred rather than declared truth,
- repo analysis remains attributable and proof-bearing,
- no silent mutation occurs to the builder’s working tree.

This story is the bridge between:

```text
legacy repo reality
```

and:

```text
governed Keyhole participation
```

It is not a direct rewrite path.  
It is an **observation, packaging, and guided alignment path**.

---

## 2. Why This Story Exists

Not every builder will begin from `keyhole init vertical`.

Many of the most valuable future builders will arrive with:

- existing repositories,
- inconsistent project structures,
- mixed dependency systems,
- partial tests,
- implicit capabilities,
- unclear architecture boundaries,
- and little or no existing governance metadata.

If the SDK only supports greenfield scaffolds, it forces adoption through replacement rather than alignment.

SDK-CLIENT-10 exists so the platform can say:

```text
bring what you already have
and we will help you understand it first
```

This story is also strategically important because ingestion is the first place the platform can create the “wow moment” for existing builders:

- repo graph,
- inferred capabilities,
- confidence scores,
- remediation suggestions,
- proof that the system understood something real.

That is the adoption wedge for non-greenfield users.

---

## 3. Story Goals

The client must provide:

- `keyhole ingest`
- `keyhole ingest --shadow`
- deterministic local repository scan
- deterministic packaging of ingestion inputs
- explicit control of what gets included or excluded
- no silent repo mutation
- clear distinction between:
  - observed facts,
  - inferred capabilities,
  - confidence-scored suggestions,
  - declared governed truth
- proof artifacts for the ingestion attempt
- forward compatibility with later repair and alignment stories

---

## 4. Scope

### Included

- client-side command contract for `keyhole ingest`
- client-side command contract for `keyhole ingest --shadow`
- local repository scan
- artifact packaging for upload / submit
- packaging of metadata needed by the server graph builder
- proof bundle emission
- shadow-mode UX
- repo safety rules
- zipper expectations for graph creation, inferred capabilities, and `INGEST_COMPLETE`

### Excluded

- silent modification of the repo
- automatic acceptance of inferred capabilities as declared truth
- automatic promotion of inferred dependencies into contracts
- final alignment/remediation edits to the repo
- direct mutation of canonical memory from the client
- full explainability/support-bundle contract (later stories)

---

## 5. Command Contract

## 5.1 Primary command

```text
keyhole ingest
```

The command scans the current repo (or a provided path), packages governed ingestion inputs, submits them to the server ingestion surface, and returns a governed ingestion outcome.

## 5.2 Shadow command

```text
keyhole ingest --shadow
```

This command performs the same local scan and packaging but explicitly marks the request as shadow / low-risk participation.

Shadow mode must be visible in:

- request metadata,
- terminal output,
- proof summary,
- any local generated artifact metadata.

## 5.3 Path contract

The command should support at least:

```text
keyhole ingest .
keyhole ingest <path>
```

Optional future extensions may support URLs or remote repos, but this story only requires local path ingestion.

---

## 6. Repo Safety Contract

The client must not silently rewrite the repository.

This is a hard rule.

### Forbidden behavior

- editing source files without explicit builder action,
- generating contracts directly into the repo without opt-in,
- renaming files,
- deleting files,
- inserting hidden markers,
- auto-committing inferred changes,
- mutating dependency manifests implicitly.

### Allowed behavior

- reading repo files,
- classifying files,
- generating out-of-tree artifacts,
- generating proof artifacts,
- presenting suggested changes,
- writing temporary packaging artifacts outside the repo or under an explicit tool-owned safe path.

The builder must always be able to trust:

```text
ingestion observes first
it does not rewrite first
```

---

## 7. Local Scan Responsibilities

Before submission, the client must inspect the repository locally.

### Minimum scan responsibilities

- identify repo root,
- identify common project manifests,
- identify likely source directories,
- identify test directories,
- identify documentation directories,
- identify dependency files,
- identify CI / build files when relevant,
- enumerate files to include or exclude in the ingestion package,
- detect obvious repo-level language / framework signals,
- gather enough local evidence to support graphing and capability inference.

### Examples of scan signals

- `pyproject.toml`, `requirements.txt`, `package.json`, `pom.xml`, `go.mod`
- `src/`, `app/`, `lib/`, `tests/`, `docs/`
- Docker / compose / infra manifests
- README / design docs
- build scripts
- existing governance-like files if present

The scan result must be deterministic enough for stable tests.

---

## 8. Packaging Contract

The client must transform local scan results into a deterministic ingestion package.

### The package must include, at minimum:

- repo identity metadata,
- local path context,
- language/framework signals,
- included file manifest,
- excluded file manifest or exclusion rules,
- dependency manifest snapshots or summaries,
- scan summary,
- shadow mode flag,
- proof correlation metadata,
- any builder-supplied hints.

### The package must not include by default:

- arbitrary secret files,
- credential stores,
- local environment files,
- Git internals,
- hidden system junk,
- oversized binary blobs unless explicitly allowed.

### Packaging principle

Package only what is necessary to support governed graphing and inference.

No indiscriminate “upload the whole machine” behavior.

---

## 9. Include / Exclude Rules

The client must implement deterministic include/exclude rules.

### Exclude by default

- `.git/`
- virtual environments
- `node_modules/`
- build output directories
- cache directories
- binary artifacts not required for structural analysis
- `.env` and secret-bearing local config files
- OS junk / editor temp files

### Include by default

- source files
- test files
- docs and READMEs
- dependency manifests
- build/config manifests relevant to topology inference

The client should surface the package summary clearly before or during submission when helpful.

---

## 10. Shadow Mode Contract

In shadow mode, the client must:

- package and submit the ingestion request with explicit shadow intent,
- mark proof artifacts as shadow,
- avoid implying that inferred capabilities are now registered or canonical,
- render the outcome as exploratory / diagnostic rather than committed participation.

Shadow mode exists specifically to make first ingestion safe for skeptical builders.

---

## 11. Server-Facing Expectations

The paired server story (`sdk-server-10.md`) is responsible for:

- ingestion endpoint,
- graph builder,
- capability inference,
- confidence scoring,
- persistence / registry behavior,
- event emission.

The client must therefore shape requests in a way that supports those outputs without assuming the client itself is the graph engine.

The client should expect, at minimum, that the server can return:

- graph summary,
- inferred capability list,
- confidence scores,
- warnings / caveats,
- ingestion identifiers or references,
- event/proof correlation data.

---

## 12. Output Contract

The client must render ingestion outcomes clearly.

### Minimum success output

- repo path or identity
- mode (`shadow` / normal)
- ingestion summary
- graph creation status
- count of inferred capabilities
- confidence summary
- proof artifact location
- next-step suggestion

### Minimum failure output

- failure class
- local vs server failure distinction where possible
- deterministic reason
- repair guidance
- proof artifact location if generated

### Important rule

Inference results must never be presented as declared truth.

The client must visually distinguish:

- observed repo facts
- inferred capabilities
- suggested remediations
- accepted governed registrations (which this story does not itself finalize)

---

## 13. Graph and Inference Semantics

The client must support a server response model where:

- a repo graph is created,
- inferred capabilities are returned,
- each inferred capability includes a confidence score,
- the client presents those scores clearly,
- low-confidence inference does not masquerade as reliable truth.

### Required UX distinction

Use clear language such as:

- `observed`
- `inferred`
- `confidence: high|medium|low`
- `suggested next step`

This prevents the builder from mistaking ingestion for automatic governance acceptance.

---

## 14. Local Proof Contract

Every ingestion attempt must produce local proof artifacts sufficient to explain:

- what was scanned,
- what path was targeted,
- what mode was used,
- what package summary was submitted,
- what the server returned,
- what graph / inference outcomes were observed,
- what repair guidance was shown if the attempt failed.

### Minimum recommended structure

```text
proof_bundle/
  ingest/
    request.json
    package_manifest.json
    response.json
    summary.md
    correlation.json
```

If the client already uses a broader proof bundle layout, the ingestion proof may live under that existing structure.

### Required semantics

- proof artifacts must exist for success and failure
- shadow mode must be visible
- package manifest must be inspectable
- no silent mutation claim must be supportable from proof

---

## 15. Local Tests

SDK-CLIENT-10 must support the following local and integration-style tests.

### 15.1 Local client tests

- `keyhole ingest` command parsing
- `keyhole ingest --shadow` command parsing
- repo root detection
- include/exclude filtering correctness
- secret-bearing files excluded by default
- deterministic package manifest generation
- no repo mutation during ingestion
- proof artifacts generated on success
- proof artifacts generated on failure
- clear output rendering for inferred capabilities and confidence

### 15.2 Zipper / boundary tests

- repo graph created
- inferred capabilities stored with confidence scores
- no silent repo mutation
- event: `INGEST_COMPLETE`

### 15.3 Negative tests

- invalid or missing repo path rejected locally
- unreadable repo state fails clearly
- unsupported packaging state surfaces repair guidance
- client does not claim successful inference when the server rejected ingestion

---

## 16. Acceptance Criteria

This story is complete only when all of the following are true:

1. the client exposes `keyhole ingest`
2. the client exposes `keyhole ingest --shadow`
3. local repo scan executes deterministically
4. packaging excludes obviously unsafe secret-bearing or irrelevant directories by default
5. packaging is deterministic for the same repo state
6. shadow mode is visible in request, output, and proof
7. no silent repo mutation occurs
8. proof artifacts are emitted for both success and failure
9. the client renders inferred capabilities with confidence scores clearly
10. the client distinguishes observed facts from inferred capabilities
11. zipper proof shows repo graph creation end-to-end
12. zipper proof shows `INGEST_COMPLETE` event emission

---

## 17. Zipper Expectations Against `sdk-server-10.md`

The paired server story must provide:

- ingestion endpoint
- graph builder
- capability inference
- confidence scoring
- event emission (`INGEST_COMPLETE`)

SDK-CLIENT-10 closes only when the paired server proof demonstrates:

- repo graph created
- inferred capabilities stored with confidence scores
- no silent repo mutation
- event: `INGEST_COMPLETE`

---

## 18. Forward-Compatibility Notes

This story must be implemented in a way that supports later stories for:

- alignment guidance
- explainability/support bundles
- trust metadata enrichment
- context-required runtime binding for inferred follow-up actions
- registration or acceptance of inferred capabilities only after explicit builder action

The client must not assume ingestion itself equals registration.

---

## 19. Non-Goals

SDK-CLIENT-10 does **not**:

- auto-register inferred capabilities
- auto-edit repo contracts
- rewrite source files
- expose direct canonical memory access
- finalize capability acceptance on behalf of the builder
- guarantee all inference is high confidence
- replace later remediation or alignment stories

---

## 20. Story Closure Statement

SDK-CLIENT-10 is the story that lets an existing repository meet Keyhole safely.

When this story closes, a builder must be able to:

```text
point the SDK at a repo
observe a governed ingestion result
see a graph
see inferred capabilities with confidence
receive proof artifacts
and trust that the SDK did not silently mutate their codebase
```

That is the adoption-safe ingestion boundary this epic requires.
