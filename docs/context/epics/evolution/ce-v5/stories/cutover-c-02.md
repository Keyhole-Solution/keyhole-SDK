# CE-V5-S51-CUTOVER-C-02 — Pin Base Image Digest

**Status:** ACCEPTED — base pin effective; upper-layer timestamps remain non-deterministic; C-03 opened  
**Story Stream:** CUTOVER-C (Track C — Reproducible Build Identity)  
**Owner:** Keyhole Solution Foundation  
**Author:** Keyhole Solution Foundation  
**Track:** C — Reproducible Build Identity  
**Depends On:** CE-V5-S51-CUTOVER-C-01 (ACCEPTED — NON_DETERMINISTIC verdict confirmed)  
**Gap:** `gap_6cdc80fdf3d55995` — `keyhole-SDK.cutover.pin-base-image-digest.v1`  
**Constitutional Layer:** Build identity / base image provenance  
**Risk Level:** MEDIUM  
**Primary Surface:** `services/test-runtime/Dockerfile` — FROM instruction  
**Canonical Pointer:** `sha256:a9af9cc5` (unchanged — no build mechanics changed in C-01)  
**Opened:** 2026-06-05  

---

## 1. Why this story exists

CE-V5-S51-CUTOVER-C-01 measured the reproducibility baseline and confirmed:

```
VERDICT: NON_DETERMINISTIC
Primary cause: base_image_mutable_tag
  python:3.11-slim resolved to sha256:a3ab0b966bc4e91546a... today
  The prior local build (2 months old) used entirely different base layers
  The original base digest used to produce sha256:a9af9cc5 cannot be recovered
  from image metadata alone — it is not stored in the image config
```

C-02 fixes the primary cause only: the mutable base image tag.

### What C-02 is and is not

**C-02 IS:**  
Elimination of mutable base tag drift from today's build point forward.  
Pinning `python:3.11-slim` to its currently resolved digest establishes  
a stable, verifiable build baseline for all future builds.

**C-02 IS NOT:**  
Reproduction of `sha256:a9af9cc5`. That would require the exact base image  
digest used at the platform's original build time, which cannot be recovered.  
C-02 makes no claim to reproduce the prior canonical digest.

**Explicit proof statement:**
```
Prior canonical base image digest: NOT RECOVERABLE
C-02 pins the current observed base digest (sha256:a3ab0b96...) and
establishes a new reproducible baseline from this point forward.
The prior canonical digest sha256:a9af9cc5 is not reproduced by C-02.
```

---

## 2. Problem

Current Dockerfile line 1:

```dockerfile
FROM python:3.11-slim
```

`python:3.11-slim` is a mutable tag. Its resolved digest changes when:
- The upstream Python maintainers patch the slim image (security updates, OS base bumps)
- A different build host pulls the tag at a different calendar date

The C-01 probe recorded today's resolved digest:
```
python@sha256:a3ab0b966bc4e91546a033e22093cb840908979487a9fc0e6e38295747e49ac0
```

This is not the digest that produced `sha256:a9af9cc5...` on the platform. Without pinning, every new build uses whatever `python:3.11-slim` resolves to on that day.

---

## 3. Change

Pin the base image to its current resolved digest:

```dockerfile
FROM python:3.11-slim@sha256:a3ab0b966bc4e91546a033e22093cb840908979487a9fc0e6e38295747e49ac0
```

This is a single-line Dockerfile change. No other build mechanics are altered.

### Constraints

- Do not change the Python version (3.11)
- Do not change the slim variant
- Do not add any other Dockerfile instructions
- Do not change `requirements.txt`, `pip` behavior, or app source
- The pinned digest is the C-01 recorded resolved digest — the current production-safe value

---

## 4. Acceptance criterion

C-02 is accepted when ALL of the following are true:

1. `FROM python:3.11-slim@sha256:<digest>` is the Dockerfile's only FROM line
2. Pinned digest is recorded in evidence
3. Build platform is recorded
4. `docker build --no-cache services/test-runtime` succeeds (first rebuild)
5. A second `docker build --no-cache` from identical inputs produces the same digest OR emits the next non-determinism delta
6. No pip/hash/platform remediation is included — those belong to C-03 and C-04
7. Follow-up gap opens only for the next observed non-deterministic factor

### What C-02 explicitly does NOT achieve

- Reproduction of `sha256:a9af9cc5` — prior base digest is not recoverable
- Full supply-chain verification — pip hash verification belongs to C-03
- Bit-identical builds — pip version and metadata are still non-deterministic until C-03/C-04

### The gap between today's pin and the prior canonical

C-01 layer comparison proved:
```
Prior local image base layers (sha256:a257f20c...):  NOT identical to today
Today's resolved base layers (sha256:219a998c...):   different set entirely
```
The prior base image digest is irrecoverable. C-02 pins today's observed digest only.

---

## 5. Evidence trail

All C-02 evidence lives under `docs/evidence/cutover-c-02/` and is mirrored to
`docs/context/epics/evolution/ce-v5/evidence/cutover-c-02/`.

Evidence required for acceptance:
- `dockerfile_diff.txt` — before/after FROM line
- `build_result.json` — new Docker build output and image digest
- `PROOF.md`
