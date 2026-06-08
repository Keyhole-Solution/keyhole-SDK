# CE-V5-S51-CUTOVER-C-03 — Deterministic Layer Timestamps via SOURCE_DATE_EPOCH

**Status:** ACCEPTED — SOURCE_DATE_EPOCH partially effective; COPY and RUN layer timestamps unresolved; C-04 opened  
**Story Stream:** CUTOVER-C (Track C — Reproducible Build Identity)  
**Owner:** Keyhole Solution Foundation  
**Author:** Keyhole Solution Foundation  
**Track:** C — Reproducible Build Identity  
**Depends On:** CE-V5-S51-CUTOVER-C-02 (ACCEPTED — base pin effective)  
**Gap:** `gap_ded81481879df255` — `keyhole-SDK.cutover.source-date-epoch-layer-timestamps.v1`  
**Constitutional Layer:** Build identity / layer provenance / timestamp determinism  
**Risk Level:** LOW  
**Primary Surface:** `services/test-runtime/Dockerfile` — build environment  
**Opened:** 2026-06-05  

---

## 1. Why this story exists

CE-V5-S51-CUTOVER-C-02 confirmed:

```
Base image pin: EFFECTIVE — layers 1–5 identical across builds
Upper layer pin: FAILED — layers 6–9 differ between identical builds

Cause identified:
  BuildKit embeds wall-clock timestamps in layer tar entries.
  Without SOURCE_DATE_EPOCH, every build produces different
  layer hashes for pip install and COPY steps, even when
  file content is bit-identical.

Build 1 digest: sha256:d7dc9196f7dc3c2fd6eee6b004e017188be20b0811bbab14a8abe4c328b06b34
Build 2 digest: sha256:1977a8e186ead51bcbbc1f8dde63a743ff5accd508cf17df0ad2e63aace8c04c
Layers 1–5: IDENTICAL (base pin working)
Layers 6–9: DIFFERENT (timestamps)
```

---

## 2. The mechanism

Docker BuildKit respects the `SOURCE_DATE_EPOCH` environment variable, defined by the
[reproducible-builds.org spec](https://reproducible-builds.org/docs/source-date-epoch/).

When `SOURCE_DATE_EPOCH` is set:
- All file modification times inside new layers are clamped to the epoch value
- Layer tar entries become deterministic across builds
- The layer hash (SHA-256 of tar content) is identical for identical file content

Without it:
- Each file's mtime in the layer tar is set to the actual wall-clock time at build
- Two builds 14 seconds apart produce different mtimes → different layer hashes → different image IDs

---

## 3. Change

Set `SOURCE_DATE_EPOCH` in the build environment. The canonical value is the
Unix timestamp of the commit being built.

### Option A — CI environment variable (preferred)

In the build workflow:
```bash
export SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
docker build --no-cache -t ... services/test-runtime
```

This ties the epoch to the commit timestamp, making the image digest a deterministic
function of source content and commit time.

### Option B — Fixed epoch (simpler, less informative)

```bash
export SOURCE_DATE_EPOCH=0
docker build --no-cache -t ... services/test-runtime
```

Uses Unix epoch 0. Maximally reproducible but loses commit-time provenance.

### Constraints

- Do not change `requirements.txt`, Dockerfile instructions, or app source
- Do not combine with pip hash verification — that belongs to C-04
- Record which option (A or B) was used and why

---

## 4. Acceptance criterion

C-03 is accepted when ALL of the following are true:

1. `SOURCE_DATE_EPOCH` is set during both builds
2. Two `--no-cache` builds from identical inputs produce **identical digests**
3. The matching digest is recorded as the new reproducible baseline
4. The `SOURCE_DATE_EPOCH` value and method are recorded in evidence
5. No pip/requirements changes in this story
6. No platform changes
7. Follow-up gap (C-04) opened only if pip layer still varies

### Measured result (2026-06-05)

```
SOURCE_DATE_EPOCH=1780644503 (commit timestamp)
Build 3: sha256:6ed2f539...
Build 4: sha256:b91e02e0...
Match: NO
```

### What SOURCE_DATE_EPOCH does and does not fix

| Layer | Instruction | Source of non-determinism | SOURCE_DATE_EPOCH fixes it? |
|-------|------------|--------------------------|----------------------------|
| 1-4 | Base image | N/A (pinned by C-02) | N/A |
| 5 | WORKDIR /app | Directory creation timestamp | YES — clamped to epoch |
| 6 | COPY requirements.txt | Host file mtime in tar entry | NO |
| 7 | RUN pip install | Container-side .dist-info, __pycache__ timestamps | NO (epoch not passed into container) |
| 8 | COPY app/ | Host file mtimes in tar entry | NO |
| 9 | RUN addgroup/adduser | /etc/passwd, /etc/shadow mtimes | NO (epoch not passed into container) |

### Two separate fixes required for C-04

1. **COPY layers** — normalize source file mtimes before build context is sent:
   ```bash
   # Linux: normalize all tracked file mtimes to commit timestamp
   git ls-files -z | xargs -0 touch -d @$SOURCE_DATE_EPOCH
   docker build ...
   ```

2. **RUN layers** — pass `SOURCE_DATE_EPOCH` into the container via Dockerfile:
   ```dockerfile
   ARG SOURCE_DATE_EPOCH
   ENV SOURCE_DATE_EPOCH=$SOURCE_DATE_EPOCH
   RUN pip install ...
   ```
   Then build with: `docker build --build-arg SOURCE_DATE_EPOCH=$SOURCE_DATE_EPOCH ...`

Both are required together to fully stabilize layers 6-9.

---

## 5. Evidence trail

Evidence under `docs/evidence/cutover-c-03/` and mirrored to
`docs/context/epics/evolution/ce-v5/evidence/cutover-c-03/`.

Required:
- `build_result.json` — both build digests, SOURCE_DATE_EPOCH value, layer comparison
- `determinism_verdict.json` — DETERMINISTIC or NEXT_DELTA_IDENTIFIED
