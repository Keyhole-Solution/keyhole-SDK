# PROOF — CE-V5-S51-CUTOVER-C-01: Reproducible Build Identity Baseline

**Story:** CE-V5-S51-CUTOVER-C-01  
**Gap:** `gap_b4bcf14ab2e95b1b`  
**Capability:** `keyhole-SDK.cutover.reproducible-build-identity.v1`  
**Probe date:** 2026-06-05  
**Phase 1 status:** COMPLETE — `NON_DETERMINISTIC_INPUTS_IDENTIFIED`  
**Phase 2 status:** COMPLETE — `NON_DETERMINISTIC` (Docker build measured 2026-06-05)  

---

## Canonical pointer

| Field | Value |
|-------|-------|
| Production digest | `sha256:a9af9cc5` |
| Platform alignment | dev v304 / staging v299 / prod v304 |
| Flightcheck | 473/473 PASS |
| Production verification | 5/5 PASS |
| Track A | CLOSED (INV-CONTROLLER-EGRESS-ENFORCED bilateral confirmed) |

---

## Source state at baseline capture

| Field | Value |
|-------|-------|
| Repo | `Keyhole-Solution/keyhole-SDK` |
| Branch | `main` |
| Commit SHA | `58c79c3259712abc32e2ae033c0cd82c2d0f7b19` |
| Dirty worktree | Yes (SDK-CLIENT-30 files modified — not part of runtime build context) |
| Captured at | 2026-06-05 UTC |

---

## Build input hashes

| Input | SHA-256 |
|-------|---------|
| `services/test-runtime/Dockerfile` | `065418E2B0A7D9087666032CD25289460EF478DC64B5EC5106A36F8F7D5FB7D8` |
| `services/test-runtime/requirements.txt` | `E6094860EF4BF73DA44F42FAB61687102E04B38F6C1184565716BC4E002ACA69` |

### requirements.txt content (pinned)

```
fastapi==0.115.6
uvicorn==0.34.0
pydantic==2.10.4
httpx==0.27.2
```

### App source manifest (`services/test-runtime/app/`)

| File | SHA-256 |
|------|---------|
| `bridge.py` | `E193793D45445E8E9195310120CEE397DE0A38B02E878A74B3F4DE107F0CD9CE` |
| `contract.py` | `E1BDF36F18870D949FB3D08CA4C8D9AA74F557C23F3C44E548E1692650C4D752` |
| `main.py` | `6DDDAE0B4C45050BFBAB558ED7E0A258ED6924ED832096C78CB1A9553309E95B` |
| `mode.py` | `72B7784F4CD976938C8A219853BEC05CD060FEB5E8C17853465248FECC1F800D` |
| `models.py` | `78D08474D352794B6EE4AA40704FDBD1F27DF94BCCCA1BE08EC2579318386921` |
| `routes.py` | `96E67F898DCA3306BCD55194DAA14AE61A2A9BFA8C604DB80269499BC60ADC3B` |
| `state.py` | `A67819012D8CF7B3E306161A0E5FDE19CB47383BF23ED8FC0929C3CED2967AAB` |
| `__init__.py` | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` (empty) |

---

## Static non-determinism analysis — Phase 1 verdict

**Verdict: `NON_DETERMINISTIC_INPUTS_IDENTIFIED`**  
4 of 5 checked factors are non-deterministic.

| Factor | Deterministic | Issue |
|--------|--------------|-------|
| `base_image` | NO | `python:3.11-slim` is a mutable tag — not pinned to digest |
| `pip_install` | NO | `--require-hashes` not used — wheel content unverified |
| `pip_version` | NO | pip version not pinned — inherits from base image |
| `build_platform` | NO | Build platform undeclared — amd64 vs arm64 produce different digests |
| `embedded_timestamps` | YES | No explicit timestamps in image layers |

### Non-determinism priority

1. **Base image** (`python:3.11-slim`) — highest impact. Mutable tag resolves to different
   content on different pull dates. This alone prevents bit-identical reproduction.

2. **Build platform** — undeclared platform produces architecturally different binaries.
   If `sha256:a9af9cc5` was built for `linux/amd64`, an `arm64` build can never match.

3. **pip version** — transitively non-deterministic via base image. Different pip versions
   may produce different metadata ordering in wheel installation.

4. **pip install hash verification** — lowest severity. Package versions are pinned; wheels
   from PyPI are stable. Risk is theoretical (PyPI wheel mutation), not demonstrated.

---

## Phase 2 — Docker build verdict

**Status: COMPLETE**  
**Verdict: `NON_DETERMINISTIC`**  
**Measured: 2026-06-05 — Docker Desktop 28.4.0, linux/amd64**

### Digest comparison

| Field | Value |
|-------|-------|
| Canonical pointer digest | `sha256:a9af9cc50cd83d0c857d0e59792a5ccd824162d3d49d98feec44060e8970abf1` |
| Source of canonical digest | `gap.revalidated_on_digest` — platform ctxpack pointer at gap creation |
| Rebuilt Docker digest | `sha256:9cdaa826c10f193151e60e886f83d1c08a7b211aa429dab87859e2cc56b0e15f` |
| Match | **NO** |

### Build inputs recorded

| Input | Value |
|-------|-------|
| Base image declared | `python:3.11-slim` (mutable tag) |
| Base image resolved today | `python@sha256:a3ab0b966bc4e91546a033e22093cb840908979487a9fc0e6e38295747e49ac0` |
| pip version | `pip 24.0` |
| Build platform | `linux/amd64` |
| Commit SHA | `58c79c3259712abc32e2ae033c0cd82c2d0f7b19` |

### Primary cause of non-determinism

`python:3.11-slim` is a mutable tag. When resolved today it is:
```
python@sha256:a3ab0b966bc4e91546a033e22093cb840908979487a9fc0e6e38295747e49ac0
```
The production build used a different base image digest at its build time. This alone
renders bit-identical reproduction impossible without pinning to the original base digest.

### Artifact type note

The canonical pointer digest (`sha256:a9af9cc5...`) is the platform's context-pack state
hash (`ctxpack_digest` / `revalidated_on_digest` from the governance boundary). The rebuilt
digest is the Docker image content hash. These measure different artifact types. The Docker
build is internally non-deterministic regardless of which canonical pointer is used as reference.

---

## Evidence files

| File | Contents |
|------|----------|
| `build_identity_baseline.json` | Complete Phase 1 baseline capture |
| `static_nondet_analysis.json` | Detailed non-determinism factor analysis |
| `delta_report.json` | Phase 2 Docker build comparison — NON_DETERMINISTIC ✅ |

---

## Track C continuation

This story's Phase 1 verdict is `NON_DETERMINISTIC_INPUTS_IDENTIFIED`.

Conditional next stories (must not open until Phase 2 completes):

| Priority | Story | Repair |
|----------|-------|--------|
| 1 | CUTOVER-C-02 | Pin base image: `FROM python:3.11-slim@sha256:<digest>` |
| 2 | CUTOVER-C-04 | Declare build platform in CI workflow |
| 3 | CUTOVER-C-03 | Add pip hash verification via `--require-hashes` |

Phase 2 verdict confirmed as NON_DETERMINISTIC (2026-06-05). CUTOVER-C-02 may now be opened.
