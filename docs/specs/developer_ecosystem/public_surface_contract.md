# Public Developer Surface Contract

**Version:** 1.0.0
**Story:** CE-V5-S41-01
**Owner:** Keyhole Solution Foundation
**Last Updated:** 2026-03-10

---

## 1) Purpose

This document defines the canonical public developer boundary for the Keyhole
ecosystem. It specifies what the public developer surface is, what it may
contain, what it must not contain, and how it is governed to prevent silent
drift from the actual runtime and MCP contract surfaces.

---

## 2) Scope

The governed public developer surface comprises:

| Surface | Description |
|---------|-------------|
| **CLI** | `keyhole-cli` — public command-line entry point |
| **SDK** | `keyhole-sdk` — public programmatic client |
| **Runtime** | Keyhole Test Runtime — public HTTP runtime bridge |
| **OpenAPI** | OpenAPI spec for the public runtime |
| **Schemas** | JSON schemas for public request/receipt shapes |
| **Docs** | README, quickstart, architecture, bridge contract, runtime docs, deployment guides |
| **Examples** | Bridge smoke tests, Python client examples |
| **Publishing** | PyPI packages, GHCR images, changelog, release metadata |
| **Workspace** | Agent guidance files (`.github/copilot-instructions.md`, `docs/AGENT.md`) |

The canonical surface inventory is declared in
`docs/specs/developer_ecosystem/public_surface_inventory.yaml`.

---

## 3) Current Runtime Contract

The runtime contract is the source of truth. All other surfaces must agree
with it.

### 3.1 `/identity` — Runtime Identity

```json
{
  "runtime_id": "keyhole-test-runtime",
  "runtime_name": "Keyhole Test Runtime",
  "runtime_version": "0.1.0",
  "environment": "dev",
  "capabilities": ["realize", "state", "health"]
}
```

Fields: `runtime_id`, `runtime_name`, `runtime_version`, `environment`,
`capabilities`.

### 3.2 `/realize` — Realization Receipt

```json
{
  "digest": "sha256:abc123",
  "status": "ACCEPT",
  "message": "Digest realized successfully.",
  "realized_at": "2026-03-06T12:01:00+00:00"
}
```

Fields: `digest`, `status`, `message`, `realized_at`.

### 3.3 `/healthz` — Health

```json
{"status": "ok"}
```

### 3.4 `/state` — Runtime State

```json
{
  "current_digest": null,
  "realized_digests": [],
  "updated_at": "2026-03-06T12:00:00+00:00"
}
```

---

## 4) Public / Private Separation

### 4.1 Allowed in the public repo

- Public CLI, SDK, and runtime code
- Public schemas and OpenAPI
- Public docs, examples, deployment templates
- Public agent guidance
- Public release automation

### 4.2 Forbidden in the public repo

- Private cluster topology or namespace maps
- Production credentials or secrets
- Internal governance engine details
- Private promotion kernel internals
- Non-public control-plane APIs
- Internal causal surfaces
- Runtime evidence logs (belong in evidence storage)
- Build artifacts (belong in CI or registries)

### 4.3 Boundary description rule

Public docs may describe that a boundary exists (e.g., "the runtime connects
to MCP governance when configured"). Public docs must not reveal protected
internals behind that boundary.

---

## 5) Mode Truth Rules

### 5.1 Local-only mode (default)

- Runtime realizes locally without governance gating
- Replay behavior works
- No Event Spine evidence may be claimed
- No governed approval may be implied
- Useful for first-run development and contract validation

### 5.2 Governed mode

- Requires `KEYHOLE_MCP_URL` and `KEYHOLE_MCP_TOKEN` configuration
- Upstream governance interaction occurs
- Upstream verdicts affect local realization
- Event Spine evidence may be expected only if actually emitted

### 5.3 Implementation constraint

Docs, examples, SDK comments, CLI output, smoke tests, and schemas must not
invent mode fields or mode semantics that the current runtime does not
implement.

### 5.4 Local-only ≠ bridge-proof

A successful local-only run proves the local runtime works and the developer
loop works. It does not prove full governed bridge closure (S40-07) or
upstream evidence return.

---

## 6) S40-07 vs S41 Claim Boundary

### What S40-07 proves

- First real external Runtime Bridge law
- Real external runtime can be governed
- Approved change can be realized locally
- Attributable evidence can return
- One Mint remains sovereign

### What S41 proves

- Public developer ecosystem is governed
- Public surfaces are truthful and executable
- CLI / SDK / docs / runtime / publishing surfaces move together
- External builders can learn, install, run, and trust the ecosystem

### Forbidden conflation

The public surface must never imply:
- "local smoke test success = S40-07 closure"
- "working SDK = external bridge proven"
- "helpful ergonomics = constitutional proof"

---

## 7) Invariant Set

| ID | Name | Description |
|----|------|-------------|
| S41-01-INV-01 | PUBLIC-SURFACE-CONTRACT-CLOSED | Public surface exists as bounded, declared contract |
| S41-01-INV-02 | PUBLIC-SURFACE-PROMOTION-GATED | No public release advances without promotion verification |
| S41-01-INV-03 | CLI-SDK-RUNTIME-ALIGNED | CLI, SDK, and runtime agree on current contract |
| S41-01-INV-04 | DOCS-EXAMPLES-TRUTHFUL | All docs/examples match current runtime behavior |
| S41-01-INV-05 | MODE-TRUTHFULNESS | Local-only and governed behavior always distinguished |
| S41-01-INV-06 | PUBLIC-PRIVATE-BOUNDARY-CLOSED | Public repo contains no private platform leakage |
| S41-01-INV-07 | PUBLISH-COMPATIBILITY-CLOSED | Published packages/images/docs are version-aligned |

---

## 8) Promotion Controller Enforcement

### 8.1 Required promotion inputs

For any candidate changing the public developer surface:

- Public surface inventory manifest
- Runtime contract (OpenAPI / schema state)
- Runtime contract test results
- SDK compatibility test results
- CLI compatibility test results
- Docs/example truth test results
- Publish compatibility evidence

### 8.2 Required promotion checks

Before ACCEPT:

1. All changed public surface files are in the declared inventory
2. Runtime contract matches OpenAPI
3. SDK models match runtime contract
4. CLI expectations match runtime contract
5. Docs and examples match current runtime contract
6. Local-only vs governed wording is truthful
7. No forbidden private references introduced
8. No package/image/docs version skew

### 8.3 Promotion outcomes

- ACCEPT or REJECT
- Violated invariant(s) listed
- Attributable reason code(s)
- Evidence references
- Minimal repair hints when possible

---

## 9) Compatibility Evolution Rules

### 9.1 Contract changes must be coordinated

Any change to the runtime contract (new fields, removed fields, changed
semantics) must propagate to all surfaces before release:

`runtime → OpenAPI → schema → SDK → CLI → docs → examples`

### 9.2 Additive changes are preferred

New optional fields may be added without breaking existing clients.
Required field removal or rename requires a major version increment.

### 9.3 Version alignment

The SDK `pyproject.toml` version, CLI `pyproject.toml` version, and runtime
`RUNTIME_VERSION` env must be compatible. Exact alignment is not required,
but declared compatibility ranges must be truthful.
