# SSE Transport Doctrine Regression — Server-Side Audit and Remediation Brief
**Classification:** Critical Doctrine Error — Server Contract and Story Layer  
**Date:** 2026-04-27  
**Severity:** CRITICAL  
**Audience:** Keyhole Platform Server Team  
**Reference:** `docs/evidence/sse-transport-regression-audit-2026-04-27.md` (client-side audit)  
**Status:** Requires server-side action — capabilities contract amendment + story addenda

---

## 1. Purpose

The client-side audit (`sse-transport-regression-audit-2026-04-27.md`) documents a
critical transport doctrine regression that propagated through seven files in the
developer-kit repository. All seven client-side corrections have been applied as of
2026-04-27.

However, the **root cause of the regression is server-side**: the upstream
capabilities contract exposed by `GET /mcp/v1/capabilities` does not distinguish
between the VS Code MCP SSE transport and the SDK/CLI REST API transport. A future
agent or story author reading only the capabilities response will reach the same
incorrect conclusion again.

Additionally, the story files that established "current boundary truth" for the S42
epic — files that live in the developer-kit repo but represent contracts with the
server — contain the contaminated doctrine and require server-acknowledged addenda.

This report specifies what the server team must address.

---

## 2. The Upstream Source — How the Capabilities Contract Caused This

### 2.1 What the capabilities contract currently returns

```json
{
  "contract": "mcp/v1",
  "transport": "rest-http",
  "auth_flow": "oidc-pkce",
  "auth_realm": "keyhole-mcp",
  "min_sdk_version": "0.1.0",
  "charter_required": true,
  "workspace_supported": true,
  ...
}
```

The field `"transport": "rest-http"` is accurate for the SDK/CLI REST API layer.
It is the correct description of how `keyhole-sdk` and `keyhole-cli` communicate with
`/mcp/v1/capabilities`, `/mcp/v1/whoami`, `/mcp/v1/runs/start`, etc.

The problem: **the capabilities response contains no field describing the VS Code MCP
SSE server endpoint.** The `/sse` endpoint and the VS Code Model Context Protocol
transport are completely absent from the contract.

### 2.2 How this poisoned the story layer

When story CE-V5-S42-01 and CE-V5-S42-02 were authored (2026-03-13), the authors
consumed the live capabilities contract as "current boundary truth." They read:

> `transport: rest-http`

And concluded, correctly for the SDK/CLI transport, that this was the canonical
connection path. They then made the additional (incorrect) inference that any OTHER
transport — specifically SSE — was therefore deprecated.

Story CE-V5-S42-02, Section F, encodes this as:

> **F) Legacy Transport Rule**
> Legacy SSE and JSON-RPC are tombstoned and must not be used.

This statement then became a functional requirement in FR-7:

> **FR-7 — Tombstoned Transport Awareness**
> The instructions must make clear that legacy SSE and JSON-RPC are not valid connection paths.

And it was encoded directly into the agent instruction files.

### 2.3 The fundamental contract gap

The capabilities contract describes the SDK/CLI API transport layer. It says nothing
about how VS Code connects to the MCP server. These are two distinct integration paths
that have no overlap:

| Path | Purpose | Transport | Who uses it |
|------|---------|-----------|-------------|
| `GET /mcp/v1/capabilities` | API discovery | REST/HTTP | `keyhole-sdk`, `keyhole-cli` |
| `GET /mcp/v1/whoami` | Identity | REST/HTTP | `keyhole-sdk`, `keyhole-cli` |
| `POST /mcp/v1/runs/start` | Governed dispatch | REST/HTTP | `keyhole-sdk`, `keyhole-cli` |
| `https://mcp.keyholesolution.com/sse` | VS Code MCP integration | SSE + JSON-RPC | VS Code, MCP clients |

Because the capabilities contract documents only the first group, any agent or author
reading it perceives only one transport tier. The second tier — the one that provides
the primary AI agent ↔ Keyhole integration path — is invisible.

---

## 3. What the Server Team Owns

The following are in the server team's domain and require action:

| Item | Location | Type of action |
|------|----------|----------------|
| Capabilities contract response shape | `GET /mcp/v1/capabilities` | Contract amendment |
| `/sse` endpoint continuity | MCP server | Confirmation + commitment |
| CE-V5-S42-01 story addendum | Developer-kit story file | Doctrine correction |
| CE-V5-S42-02 story addendum | Developer-kit story file | Doctrine correction |
| CE-V5-S42-INDEX posture block | Developer-kit story file | Posture update |
| Server-side docs (if any) with SSE tombstoning | Platform repo | Investigation + correction |
| Future story authorship guard | Process | Going-forward requirement |

---

## 4. Critical Remediation — Capabilities Contract Amendment

### 4.1 Required change

The capabilities response must be amended to explicitly expose the VS Code MCP server
transport tier as a distinct field. This field must make the two-tier transport model
unambiguous for any agent or author reading the contract.

**Proposed contract amendment — add `client_transports` block:**

```json
{
  "contract": "mcp/v1",
  "transport": "rest-http",
  "auth_flow": "oidc-pkce",
  "auth_realm": "keyhole-mcp",
  "min_sdk_version": "0.1.0",
  "charter_required": true,
  "workspace_supported": true,
  "client_transports": {
    "sdk_cli": {
      "transport": "rest-http",
      "base_path": "/mcp/v1/",
      "note": "Used by keyhole-sdk and keyhole-cli for governed API operations"
    },
    "vscode_mcp": {
      "transport": "sse",
      "endpoint": "/sse",
      "protocol": "model-context-protocol",
      "note": "Canonical VS Code and MCP client integration path. SSE + JSON-RPC per MCP standard."
    }
  }
}
```

### 4.2 Why this field is required

Without it, the `"transport": "rest-http"` top-level field will continue to be read
as a global statement about all Keyhole connectivity. Every future story author who
sources "current boundary truth" from the capabilities response will reach the same
incorrect conclusion.

The `client_transports.vscode_mcp` field is:
- The first place where the VS Code MCP integration path is formally declared
- The authoritative, discoverable record that `/sse` is canonical and intentional
- The guard that prevents future conflation of the SDK/CLI REST transport with the
  MCP server SSE transport

### 4.3 Backward compatibility

This is an additive change. Existing SDK and CLI code that reads `transport` from the
capabilities response is unaffected. No breaking change to existing clients.

The `client_transports` block becomes a new optional field that external participants
and agents can read to learn about the full transport posture.

### 4.4 SDK/CLI contract update required in parallel

Once the server adds `client_transports` to the capabilities response, the developer-kit
must:

1. Update `keyhole_sdk/models.py` — add `client_transports` as an optional field in
   `CapabilitiesResult`
2. Update the OpenAPI spec (`openapi/test-runtime.openapi.yaml`) to document the new field
3. Update `docs/specs/developer_ecosystem/public_surface_inventory.yaml` to declare the
   new field as a governed surface element

This SDK/CLI work depends on the server amendment landing first.

---

## 5. Required Story Addenda

The following story files in the developer-kit repo contain the contaminated doctrine
and require server-acknowledged addenda. These stories represent contracts with the
server side; corrections cannot be made unilaterally by the developer-kit team.

### 5.1 `docs/context/epics/evolution/ce-v5/stories/ce-v5-s42-01.md` — Line 159

**Current (contaminated):**
```
legacy SSE and JSON-RPC transports are tombstoned
the canonical boundary posture is REST/HTTP plus OIDC/PKCE
```

**Required addendum:**
This statement requires scope qualification. The tombstoning applies only to the
pre-S42 Keyhole SDK-internal SSE and JSON-RPC transport layer. It does NOT apply to
the VS Code Model Context Protocol transport (SSE + JSON-RPC between VS Code and the
MCP server). The VS Code MCP SSE transport is a separate, orthogonal integration path
that was never part of the SDK-internal transport being deprecated.

**Action required:** Server team to acknowledge and approve addendum language. Story
to receive a correction note below Section F.

### 5.2 `docs/context/epics/evolution/ce-v5/stories/ce-v5-s42-02.md` — Section F, FR-7

**Current (contaminated):**

Section F, "Current Boundary Truth This Story Must Encode":
```
F) Legacy Transport Rule
Legacy SSE and JSON-RPC are tombstoned and must not be used.
```

FR-7:
```
FR-7 — Tombstoned Transport Awareness
The instructions must make clear that legacy SSE and JSON-RPC are not valid
connection paths.
```

Anti-patterns list:
```
using tombstoned transports
```

**Required addendum:**
Section F's Legacy Transport Rule is over-broad. The tombstoning applies to the old
Keyhole SDK-internal SSE transport (Concept A). It does NOT apply to the VS Code MCP
SSE protocol (Concept B). FR-7 must be rewritten to scope the tombstoning correctly
and explicitly exempt the VS Code MCP transport.

**Proposed corrected FR-7:**
```
FR-7 — Transport Distinction Awareness
The instructions must clearly distinguish:
- VS Code MCP transport (SSE + JSON-RPC via Model Context Protocol) — CANONICAL MAIN
- SDK/CLI API transport (REST/HTTP) — CANONICAL for programmatic operations
- Old SDK-internal SSE transport (pre-S42) — DEPRECATED; replaced by REST/HTTP in
  the SDK layer

The old SDK-internal SSE transport must not be used. The VS Code MCP SSE transport
is canonical and must not be deprecated or tombstoned.
```

**Action required:** Server team to approve corrected FR-7 language and confirm the
scope of the original tombstoning. Developer-kit team will apply the addendum once
approved.

### 5.3 `docs/context/epics/evolution/ce-v5/stories/ce-v5-s42-INDEX.md` — Section 2.2

**Current (incomplete):**
```yaml
transport: rest-http
```

Listed as a "Current Public-Safe Boundary Fact" without any mention of the VS Code
MCP SSE transport. Any agent reading this section will again reach the incorrect
single-transport conclusion.

**Required update:**
```yaml
# SDK/CLI REST API transport
transport: rest-http

# VS Code MCP integration transport (canonical main)
mcp_server_transport: sse
mcp_server_endpoint: /sse
mcp_server_protocol: model-context-protocol
```

**Action required:** Server team to confirm these values are correct and stable.
Developer-kit team will update the INDEX posture block.

---

## 6. `/sse` Endpoint — Continuity Commitment Required

The VS Code MCP integration depends on the `/sse` endpoint being:

- Live at `https://mcp.keyholesolution.com/sse`
- Stable (not renamed, moved, or rate-limited)
- Not deprecated or tombstoned in any server-side changelog, deprecation notice, or
  capabilities flag

**Action required:** Server team to provide explicit confirmation that:

1. `/sse` is a first-class, intentional, long-lived endpoint
2. No deprecation or removal is planned
3. Any future changes to this endpoint will be communicated to developer-kit before
   taking effect and before any story authors encode "current boundary truth"

This commitment is required before developer-kit documentation, agent instructions,
and the capabilities contract amendment can be finalized with permanent language.

---

## 7. Server-Side Internal Audit — Investigation Required

The following server-side investigation is required to ensure the contamination has
not propagated into the platform repository:

### 7.1 Platform repo docs

Search for any occurrence of:
- `"SSE tombstoned"` or `"SSE deprecated"` or `"SSE: do not use"` in platform-side docs
- Any reference to the VS Code MCP `/sse` endpoint as deprecated
- Any changelog or migration guide that instructs developers to move from `/sse` to
  `/mcp/v1`

### 7.2 Server-side agent instructions

If the platform repo has its own `copilot-instructions.md`, `AGENT.md`, or equivalent
agent alignment files, those must be audited for the same tombstoning doctrine.

### 7.3 Capabilities response code

Audit the server-side implementation of `GET /mcp/v1/capabilities` to confirm:
- There is no code or comment that marks the `/sse` endpoint as deprecated
- The `transport: rest-http` field is accurately scoped to the SDK/CLI API transport
- No feature flag or environment variable could accidentally disable the SSE endpoint

### 7.4 OpenAPI spec (server-side)

If the server maintains an OpenAPI spec for its MCP boundary, that spec must document
both transport tiers and not imply `/sse` is deprecated.

---

## 8. Story Authorship Guard — Going-Forward Requirement

### 8.1 The systemic failure mode

The transport doctrine regression was caused by a story author accurately reading the
capabilities contract and drawing an incorrect (but logical) inference. The author saw
`transport: rest-http` and concluded SSE was deprecated — because nothing in the
capabilities response indicated otherwise.

This is a **contract communication failure**, not solely a human error.

### 8.2 Required process change

For any future story that modifies transport posture, the server team must:

1. **Include a `client_transports` section** in the capabilities response (proposed
   in §4 above) before the story is authored, so authors have a complete picture
2. **Explicitly enumerate which transport concepts are in scope** for any tombstoning
   or deprecation announcement
3. **Require that story FR sections addressing transport** include a review step that
   confirms the scope of any tombstoning before the story is ACCEPTED

### 8.3 Capabilities contract as the canonical guard

The `client_transports` field in the capabilities response (§4.1) is the primary
structural guard. Once it is live, any future story author reading capabilities will
see both transport tiers explicitly. The scope of REST/HTTP will be unambiguous. The
canonical status of VS Code MCP SSE will be undeniable.

This makes the capabilities contract self-documenting about transport posture —
consistent with the boundary-as-truth-surface principle already embedded in the S42
epic.

---

## 9. Immediate Actions — Priority Order

| Priority | Action | Owner | Dependency |
|----------|--------|-------|------------|
| 1 | Confirm `/sse` endpoint is live, stable, and intentional | Server | None |
| 2 | Approve addendum language for S42-01, S42-02 FR-7, S42-INDEX | Server | None |
| 3 | Amend `GET /mcp/v1/capabilities` — add `client_transports` block | Server | None |
| 4 | Audit platform repo for internal propagation of tombstoning doctrine | Server | None |
| 5 | Apply story addenda to S42-01, S42-02, S42-INDEX | Developer-kit | Server approval (#2) |
| 6 | Update `CapabilitiesResult` SDK model for `client_transports` | Developer-kit | Server contract (#3) |
| 7 | Update OpenAPI spec to document `client_transports` | Developer-kit | Server contract (#3) |
| 8 | Add `client_transports` to governed surface inventory | Developer-kit | Server contract (#3) |

---

## 10. Impact of Inaction

If the capabilities contract is not amended:

- The next story author who sources "current boundary truth" from capabilities will
  again see only `transport: rest-http` and again tombstone SSE globally
- The `client_transports` field will remain absent, meaning the VS Code MCP transport
  tier is perpetually invisible to any automated or agent-driven audit
- External participants onboarding through the developer kit will continue to receive
  (corrected) client-side docs but no canonical server-side confirmation of the
  VS Code integration path

If the story addenda are not applied:

- The story files remain as contaminated canonical "current truth" references
- Any agent recovering context from these stories will re-derive the incorrect doctrine
- The S42-02 functional requirement FR-7 will continue to mandate incorrect agent behavior

---

## 11. Cross-Reference

| Document | Location | Status |
|----------|----------|--------|
| Client-side audit (full root cause) | `docs/evidence/sse-transport-regression-audit-2026-04-27.md` | Complete |
| Client-side corrections (7 files) | Applied 2026-04-27 | Complete |
| This report (server-side remediation) | `docs/evidence/sse-transport-doctrine-server-audit-2026-04-27.md` | Awaiting server action |
| Capabilities contract amendment | `GET /mcp/v1/capabilities` | **Pending server** |
| Story addenda (S42-01, S42-02, S42-INDEX) | Story files in `docs/context/epics/` | **Pending server approval** |
| Platform repo internal audit | Platform source | **Pending server** |

---

## 12. The Correct Two-Tier Transport Doctrine (Reference)

This is the doctrine that must be reflected in both the capabilities contract and all
story-level "current boundary truth" sections going forward:

### Tier 1 — VS Code / MCP Client Transport (CANONICAL MAIN)

| Aspect | Value |
|--------|-------|
| Protocol | SSE (Server-Sent Events + JSON-RPC) |
| Standard | Model Context Protocol (MCP) |
| Endpoint | `https://mcp.keyholesolution.com/sse` |
| Config | `.vscode/mcp.json` with `"type": "http"`, `"url": ".../sse"` |
| Auth | OIDC/PKCE token acquired by VS Code |
| Status | **CANONICAL** — primary AI agent ↔ Keyhole integration path |

### Tier 2 — SDK/CLI REST API Transport (GOVERNED OPERATIONS)

| Aspect | Value |
|--------|-------|
| Protocol | REST/HTTP |
| Base path | `https://mcp.keyholesolution.com/mcp/v1/` |
| Operations | `GET /capabilities`, `GET /whoami`, `POST /runs/start`, `POST /events/query` |
| Auth | Bearer token via `Authorization` header |
| Status | **CANONICAL** for `keyhole-sdk` and `keyhole-cli` operations |

### Deprecated (scoped)

| Item | Scope of deprecation |
|------|---------------------|
| Old SDK-internal SSE transport | Pre-S42 SDK code that called Keyhole API endpoints over SSE. Replaced by REST/HTTP in the SDK transport layer. Does **not** apply to VS Code MCP. |
| Old JSON-RPC API protocol | Pre-S42 direct JSON-RPC calls to Keyhole API endpoints. Does **not** apply to VS Code MCP protocol. |

The VS Code MCP protocol (SSE + JSON-RPC between VS Code and the MCP server at `/sse`)
is architecturally unrelated to the old SDK-internal SSE transport. They share the
protocol name "SSE" and nothing else. This must never be conflated again.
