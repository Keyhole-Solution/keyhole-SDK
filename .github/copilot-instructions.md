# Copilot Instructions — Keyhole Developer Kit

## Repo Identity and Boundary Posture

**keyhole-developer-kit** is a separate governed participant repository — not
a subcomponent of the Keyhole platform source tree.

It contains:

- `keyhole-cli`
- `keyhole-sdk`
- the public test runtime
- public schemas and OpenAPI
- examples and onboarding docs
- deployment templates

It does **not** contain private Keyhole platform internals.

This repository learns platform truth through the **MCP boundary**, not
through private source inspection. See
[docs/boundary-constitution.md](../docs/boundary-constitution.md) for the
full boundary posture.

---

## First Truth Surface: Capabilities Discovery

Before making platform-structure, endpoint, run-type, or supported-surface
assumptions, consult the live boundary beginning with:

```
GET /mcp/v1/capabilities
```

This is the **initial source of truth** for any external participant — human
or agent. It is public-safe, read-only, and available before authentication.

From capabilities, you learn:

- the current contract version
- transport posture
- auth requirements
- minimum SDK version
- whether charter and workspace are required
- what operations are available

**Do not guess** platform structure, surfaces, or run types from repo docs,
old comments, or naming conventions. Capabilities is always fresher than
local docs.

---

## Current Transport and Auth Posture

The MCP boundary operates over:

| Aspect    | Current Value  |
|-----------|----------------|
| Transport | REST/HTTP      |
| Auth flow | OIDC/PKCE      |
| Realm     | `keyhole-mcp`  |
| Contract  | `mcp/v1`       |
| Min SDK   | `0.1.0`        |
| Charter   | required       |
| Workspace | supported      |

### Surface Categories

Agents must distinguish these surface categories:

1. **Public discovery** (unauthenticated):
   - `GET /mcp/v1/capabilities` — discover boundary posture and operations

2. **Authenticated identity**:
   - `GET /mcp/v1/whoami` — inspect current participant identity

3. **Run dispatch** (authenticated):
   - `POST /mcp/v1/runs/start` — dispatch a named run type

4. **Event query** (authenticated):
   - `POST /mcp/v1/events/query` — query the Event Spine

5. **Memory surfaces** (authenticated, where relevant):
   - Used for governed context retrieval and storage

### Tombstoned Transports

Legacy **SSE** and **JSON-RPC** transports are tombstoned.
Do not use them. Do not suggest them. They are not valid connection paths.

---

## Context-Before-Assumption Rule

When capabilities alone are insufficient for architectural certainty:

1. Retrieve governed context before making assumptions.
2. Use context-access run types to compile truth from the live boundary.
3. Do not substitute stale repo docs, old comments, or remembered patterns
   for live boundary truth.

Current implemented read-only context-access run types include:

- `context.compile`
- `gaps.list`
- `lineage.get.v0_1`
- `convergence.status.v0_1`

Use these through `POST /mcp/v1/runs/start` with the exact run type key.

---

## Exact Run-Type Discipline

Run types are **exact canonical keys** — not REST resource guesses.

They are named workflows with precise identifiers. They are:

- singular when declared singular
- not discoverable by convention
- not safely guessable by pluralization or naming instinct

### Examples

| Correct             | Incorrect (do not use) |
|---------------------|------------------------|
| `gaps.status`       | `gaps.states`          |
| `gaps.list`         | `gap.status`           |
| `convergence.status.v0_1` | `convergence.statuses` |

### Rules

- Always use the **exact** run-type key from `operations[]` or published guidance.
- Do not pluralize, singularize, or improvise run-type names.
- Do not guess a run type exists because a similar name feels right.
- If you encounter an unknown run type, **re-discover** — consult
  capabilities or context. Do not improvise.

---

## Truthfulness Rules

1. **Local-only is the default.** Unless the user has explicitly configured
   MCP connectivity, examples, smoke tests, and quickstart flows should be
   treated as running in local-only mode.

2. **Do not claim Event Spine evidence from local-only runs.** Local-only
   realizations are useful for first-run development and replay testing, but
   they are not upstream-auditable.

3. **Label runtime mode explicitly.** When showing example output or
   describing behavior, distinguish between:
   - `local-only`
   - `governed`

4. **Do not invent governed behavior.** Only describe governed-mode behavior
   when the relevant MCP configuration is actually present and the current
   runtime contract supports it.

5. **Do not expose private platform internals.** Never reference internal
   cluster topology, private governance engine details, promotion kernel
   internals, production secrets, or protected control-plane logic.

6. **Do not overclaim proof.** A working local developer loop is not, by
   itself, proof of full external runtime bridge closure.

## Public Contract Discipline

### `/identity`
Examples and docs should reflect the current public runtime contract:
`runtime_id`, `runtime_name`, `runtime_version`, `environment`, `capabilities`.
No `governance_mode` field exists in the current contract.

### `/realize`
Examples and docs must match the current public runtime receipt shape:
`digest`, `status`, `message`, `realized_at`.
Do not add `governance_verdict`, `result`, `version`, or `pointer` — these
are not emitted by the runtime today.

## Mode Model

### Local-only
Use this when MCP is not configured.
Do not imply governance gating, Event Spine evidence, or upstream auditability.

### Governed
Use this only when MCP is configured and the runtime is actually operating
against the public governance boundary.
Do not assume a successful verdict; show only what the current runtime
contract actually returns.

---

## Anti-Patterns — Forbidden Agent Behavior

Do not:

- **Guess run types** by pluralizing, singularizing, or constructing names
  from convention.
- **Assume internal platform code is authoritative** for external participant
  usage. Platform truth comes through the MCP boundary.
- **Use tombstoned transports** (SSE, JSON-RPC).
- **Treat repo docs as fresher than live capabilities.** When in doubt,
  capabilities is the canonical source.
- **Browse or reference private platform source** as a discovery or
  onboarding method.
- **Assume co-location** with the platform repository, relative paths into
  platform source, or internal platform file structures.
- **Fabricate hidden surface names** or undisclosed endpoints.
- **Claim Event Spine evidence** from local-only runs.
- **Add unimplemented fields** to example responses, schemas, or models.

---

## Behavior Under Uncertainty

When encountering unknown run types, auth ambiguity, or schema uncertainty:

1. **Re-check capabilities** — `GET /mcp/v1/capabilities`
2. **Consult governed context** — use context-access run types
3. **Consult schema discovery** where available
4. **Do not improvise** hidden surface names or run-type keys
5. **Prefer discovery over convention** — always

When uncertain about any claim, prefer conservative wording over ambitious
wording.

---

## No Private-Source Truth

Platform truth for external participants must not depend on:

- browsing private platform source code
- stale copied docs or old comments
- internal path assumptions or nested-repo conventions
- verbal lore or tribal knowledge

The canonical path to platform truth is the **MCP boundary** — beginning
with `GET /mcp/v1/capabilities`, then governed context retrieval as needed.

This is not optional. It is constitutional.