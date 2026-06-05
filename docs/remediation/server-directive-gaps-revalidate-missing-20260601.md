# Server Directive — gaps.revalidate Missing + Digest Prefix Normalization (2026-06-01)

**Priority:** CRITICAL — blocks all gap → claim → provision flows  
**Status:** RESOLVED — reconciler ran 2026-06-03T12:45:02Z; digest prefix normalization no longer blocking; gaps.revalidate not needed for normal flow  
**Realm:** `kh-prod`  
**Platform:** `https://mcp.keyholesolution.com`  
**Raised by:** SDK client investigation — session `982489b3-e0d2-470e-858f-0cac6e22c04f`  
**Raised:** 2026-06-01  
**Gap under test:** `gap_9a5034cacc3bd052` (capability `my-first-app.greet.user.v1`)

---

## Two Blocking Bugs

### Bug A — Digest Prefix Normalization in Claimability Check

Every freshly submitted gap immediately enters `STALE_REVALIDATION` and cannot
be claimed. The mismatch is between the stored revalidation digest (no prefix)
and the canonical digest (with `sha256:` prefix):

```
Gap stored:         4e0c9fd3bec06aed792c1a731fb411e0aed78351b154b44ba9d8158121363912
Canonical:  sha256:4e0c9fd3bec06aed792c1a731fb411e0aed78351b154b44ba9d8158121363912
```

These are the same hash. The claimability check performs a strict string
comparison and they do not match → `STALE_REVALIDATION` for every gap.

**Evidence — claim error from `run_25e1eb4ccc02`:**
```json
{
  "code": "GAP_NOT_CLAIMABLE",
  "detail": {
    "claimability_reason": "STALE_REVALIDATION",
    "blocked_reasons": [{
      "reason_code": "STALE_REVALIDATION",
      "message": "Gap was revalidated on an older digest (4e0c9fd3bec06aed...) but the current canonical digest is sha256:4e0c9fd3b...."
    }]
  }
}
```

Both digests refer to `sha256:4e0c9fd3bec06aed792c1a731fb411e0aed78351b154b44ba9d8158121363912`.

**Root cause hypothesis:** The gap is stored with the digest as submitted by the
SDK (`ctxpack_digest` without the `sha256:` prefix). The canonical always stores
and reports the digest with `sha256:` prefix. The claimability comparison is
`gap.revalidation_digest == canonical.current_canonical_digest` — strict string
equality fails.

**Required fix:** Normalize both sides to the same format (strip or always add
`sha256:` prefix) before comparison in the claimability check. This should be
applied to:
- the `gaps.claim` claimability pre-check
- the gap reconciler's revalidation logic

### Bug B — `gaps.revalidate` Run Type Not Registered

The `gaps.claim` error for `STALE_REVALIDATION` includes a `required_action`
pointing to `gaps.revalidate`. This run type does **not exist** — the server
returns `"Unknown run_type: gaps.revalidate (not in scope mapping)"`.

**Evidence — `gaps.revalidate` dispatch from probe (same run as above):**
```json
{
  "ok": false,
  "data": {
    "status": "blocked",
    "message": "Unknown run_type: gaps.revalidate (not in scope mapping)\n\nNext best actions:\n• Valid gap run_types: gaps.claim, gaps.evidence.submit, gaps.get, gaps.list, gaps.next_open_canonical"
  }
}
```

The claim error's `required_action` is pointing the client at a non-existent
endpoint. Either:
1. `gaps.revalidate` must be implemented and registered, OR
2. The claim error must be corrected to remove the false `required_action`

**Until one of these is done:** There is no client-side path to revalidate a gap.
The only recovery path is waiting for the reconciler to run a cycle, which
last ran at `2026-05-29T06:38:06Z` (3+ days ago as of this directive).

---

## Verified Environment

```
Canonical digest: sha256:4e0c9fd3bec06aed792c1a731fb411e0aed78351b154b44ba9d8158121363912
Gap:              gap_9a5034cacc3bd052 (status=OPEN, open_unrevalidated_count=1)
User:             c2a432d8-0164-499b-ad84-b662e1f174ec
Reconciler last:  2026-05-29T06:38:06Z
```

---

## Blocked Chain

These two bugs block the entire `gap → claim → provision` chain:

```
gaps.submit → gap_9a5034cacc3bd052 (OPEN, open_unrevalidated_count=1)
gaps.claim  → STALE_REVALIDATION (digest prefix mismatch)
gaps.revalidate → blocked (run type not registered)
workspace.provision → unreachable
```

Note: `workspace.provision` has its own separate input-loss bug tracked in
`server-directive-workspace-provision-input-loss-20260528.md`.

---

## Required Server Actions (in priority order)

1. **Fix digest prefix normalization** in claimability check — normalize both
   `gap.revalidation_digest` and `canonical.current_canonical_digest` to the
   same format before comparison. This must be applied to `gaps.claim` handler
   and gap reconciler.

2. **Either implement `gaps.revalidate`** or remove the false `required_action`
   from the `STALE_REVALIDATION` claim error. If implementing:
   - Register under `gaps.revalidate`
   - Accept `{"gap_id": str, "ctxpack_digest": str}` as input
   - Update the gap's stored revalidation digest to the provided (normalized) digest
   - Return success/failure with gap status

3. **Trigger a reconciler cycle** to pick up `open_unrevalidated_count=1` gaps.
   The reconciler has not run since 2026-05-29T06:38:06Z.

---

## Status Updates

| Date | Update |
|------|--------|
| 2026-06-01 | Filed — two bugs confirmed blocking claim chain |
