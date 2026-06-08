# CE-V5-S51-CUTOVER-C-01 — Reproducible Build Identity Baseline

**Status:** ACCEPTED — Phase 1 + Phase 2 complete, verdict NON_DETERMINISTIC  
**Story Stream:** CUTOVER-C (Track C — Reproducible Build Identity)  
**Owner:** Keyhole Solution Foundation  
**Author:** Keyhole Solution Foundation  
**Track:** C — Reproducible Build Identity  
**Depends On:** Track A closure (CE-V5-S51-CUTOVER-A-01 through A-05) — SEALED  
**Related Evidence:** Track A evidence is closure evidence only. Track C creates its own trail.  
**Gap:** `gap_b4bcf14ab2e95b1b` — `keyhole-SDK.cutover.reproducible-build-identity.v1`  
**Constitutional Layer:** Build identity / image provenance / non-determinism audit  
**Risk Level:** HIGH  
**Primary Surface:** `services/test-runtime/` — Dockerfile, requirements.txt, app source  
**Canonical Pointer:** `sha256:a9af9cc5`  
**Probe Date:** 2026-06-05  

---

## 1. Summary

This is the opening story of **Track C: Reproducible Build Identity**.

Track C answers one question for the canonical production digest `sha256:a9af9cc5`:

> Given the canonical source state + manifest pointer + declared build environment,
> can the platform reproduce `sha256:a9af9cc5` exactly?
>
> If no: emit a signed delta report proving why reproducibility fails.

**Track C does not change build mechanics.** This story captures the measurement
baseline only. Build changes, if warranted, belong to later stories opened
against observed delta — not against assumed delta.

---

## 2. Opening Posture

### 2.1 Canonical pointer state at story open

| Field | Value |
|-------|-------|
| Production digest | `sha256:a9af9cc5` |
| Platform versions | dev v304 / staging v299 / prod v304 |
| Flightcheck | 473/473 PASS |
| Production verification | 5/5 PASS |
| Open gaps | 0 |
| Track A closure | INV-CONTROLLER-EGRESS-ENFORCED passed — bilateral enforcement confirmed |

### 2.2 Source state at Track C open

| Field | Value |
|-------|-------|
| Repo | `Keyhole-Solution/keyhole-SDK` |
| Branch | `main` |
| Commit SHA | `58c79c3259712abc32e2ae033c0cd82c2d0f7b19` |
| Dirty worktree | Yes (5 modified files — SDK-CLIENT-30 work in progress) |
| Story opened | 2026-06-05 |

---

## 3. Problem Statement

`sha256:a9af9cc5` was produced by a platform build process. The SDK repository
contains the `services/test-runtime/` source tree that composes the image. The
question is whether that source tree, built today, produces the same digest.

Docker image digests are content-addressed. They encode all layer content, layer
ordering, and image metadata. A digest match proves bit-identical reproduction.
A mismatch proves at least one non-deterministic input was present.

### 3.1 Known non-deterministic inputs — confirmed by Phase 2 measurement

| Input | Deterministic? | Phase 2 evidence |
|-------|---------------|---------|
| `FROM python:3.11-slim` (base image) | **NO** | Today resolves to `sha256:a3ab0b96...` — different from prod build |
| `pip install -r requirements.txt` (dependency resolution) | Partial | Versions pinned; pip 24.0 recorded |
| `pip` version used at build time | **NO** | pip 24.0 in today's build; original build value unknown |
| Build timestamp / layer metadata | **NO** | Baked into OCI metadata per build |
| Build platform (linux/amd64 vs arm64) | YES | Confirmed linux/amd64 in both local and production |
| Layer ordering | YES | Dockerfile instruction order is fixed |
| App source files | YES | Deterministic from git SHA |
| ENV var values | YES | Hardcoded in Dockerfile |

**Summary:** At minimum two inputs are structurally non-deterministic without
additional pinning: the base image tag and build platform. A third (pip version)
is transitively non-deterministic via the base image.

---

## 4. Acceptance Criterion

This story is accepted when exactly one of the following is true and signed:

### Option A — Reproducible

```
VERDICT: REPRODUCIBLE
Source: sha256:a9af9cc5 (canonical)
Rebuilt digest: sha256:a9af9cc5 (match)
Build inputs:
  base_image_digest: sha256:<pinned>
  pip_version: <recorded>
  platform: linux/amd64
  commit_sha: <recorded>
```

### Option B — Non-deterministic delta report

```
VERDICT: NON_DETERMINISTIC
Source: sha256:a9af9cc5 (canonical)
Rebuilt digest: sha256:<different> (mismatch)
Delta factors identified:
  - base image tag not pinned to digest
  - pip version unrecorded
  - build platform undeclared
Non-deterministic inputs: [list]
Repair candidates: [list, ordered by impact]
```

Both options are valid outcomes. Option B is not a failure — it is the measured
truth needed to decide whether to pursue bit-identical reproducibility or
content-verified reproducibility (same packages, different metadata).

---

## 5. Preflight Measurement Plan

### 5.1 Static inputs (SDK-side, no build required)

The following are captured by `tests/preflight/track_c_build_identity_baseline.py`:

- Git commit SHA and dirty state
- `Dockerfile` SHA-256 content hash
- `requirements.txt` SHA-256 content hash
- Per-file SHA-256 manifest of `services/test-runtime/app/`
- Static non-determinism analysis (base image pin status, hash verification mode)

These are build-independent. They establish what the source state IS,
regardless of what Docker produces.

### 5.2 Build-dependent inputs (requires Docker)

The following require an active Docker build environment:

- Pull the current `python:3.11-slim` tag and record its resolved digest
- Build from source: `docker build --no-cache -t preflight-check services/test-runtime`
- Inspect built image digest: `docker inspect --format '{{index .RepoDigests 0}}'`
- Compare to canonical `sha256:a9af9cc5`
- Record pip version from the built image: `docker run --rm preflight-check pip --version`
- Record build platform: `docker inspect --format '{{.Os}}/{{.Architecture}}'`

### 5.3 Verdict gate

```
if rebuilt_digest == "sha256:a9af9cc5":
    VERDICT = REPRODUCIBLE
else:
    VERDICT = NON_DETERMINISTIC
    delta = {
        "canonical": "sha256:a9af9cc5",
        "rebuilt": rebuilt_digest,
        "non_deterministic_inputs": [factors],
        "repair_candidates": [ordered_list],
    }
```

---

## 6. What Track C Must NOT Do

- Must not mutate Track A evidence.
- Must not change build mechanics before delta is measured and recorded.
- Must not assume the base image is already pinned.
- Must not fabricate a REPRODUCIBLE verdict without a confirmed digest match.
- Must not open repair stories until this baseline story is accepted.

---

## 7. Evidence Trail

All Track C evidence lives under `docs/evidence/cutover-c-01/`.

Track A evidence directories (`sdk-client-00/` through `sdk-client-01-c/`, `sdk-client-29/`)
are read-only reference. They may be cited but not amended.

---

## 8. Next Stories (conditional on this story's verdict)

| Condition | Story |
|-----------|-------|
| Verdict: NON_DETERMINISTIC, base image not pinned | CUTOVER-C-02: Pin base image to digest |
| Verdict: NON_DETERMINISTIC, pip not hash-verified | CUTOVER-C-03: Add pip hash verification |
| Verdict: NON_DETERMINISTIC, platform undeclared | CUTOVER-C-04: Declare build platform |
| Verdict: REPRODUCIBLE | CUTOVER-C-99: Track C closed — no build changes needed |

Stories CUTOVER-C-02 through CUTOVER-C-99 must not be opened until
this story emits its verdict.
