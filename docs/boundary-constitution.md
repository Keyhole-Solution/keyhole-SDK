# Boundary Constitution — Keyhole Developer Kit

## Canonical Boundary Statement

**keyhole-developer-kit** is the first governed external participant repository
in the Keyhole ecosystem. It is separate from **keyhole_Platform** and must
learn platform truth through the MCP boundary — beginning with capabilities
discovery — rather than through private platform source intimacy.

This separation is constitutional, not incidental.

---

## Repository Identity

This repository is:

- a **separate governed participant**, not a subcomponent of the platform
- an **adjacent repository**, not a nested subtree
- a **boundary-informed consumer**, not a source-intimate insider
- a **public builder surface**, not a private control-plane extension

It has its own lifecycle, documentation, agent guidance, and onboarding posture.

---

## Relationship Between Repositories

### keyhole_Platform

The platform repository is the **governor**. It owns:

- the MCP governance boundary
- promotion and policy enforcement
- protected control-plane logic
- canonical event orchestration
- private operational internals

### keyhole-developer-kit

The developer kit repository is a **governed participant**. It owns:

- public SDKs and CLI tooling
- public JSON schemas and OpenAPI contracts
- the local test runtime
- bridge examples and integration smoke tests
- deployment templates
- developer onboarding documentation

### How They Relate

- The platform **governs**; the developer kit **participates**.
- Governance crosses the boundary through the MCP surface, not through source access.
- The developer kit does not depend on platform source code, internal paths,
  or private implementation details.
- The developer kit discovers platform capabilities through the public
  MCP boundary — it does not assume or inspect private internals.

### What Each May Assume About the Other

The developer kit may assume:

- the platform exposes `GET /mcp/v1/capabilities` as the first discovery surface
- the MCP boundary exposes an SSE endpoint at `/sse` for VS Code / MCP client integration (canonical main transport)
- the SDK/CLI API transport operates over REST/HTTP with OIDC/PKCE auth at `/mcp/v1/`
- boundary rules and implemented surfaces are disclosed through capabilities
- the boundary is stable and replay-deterministic

The developer kit must **not** assume:

- access to platform source code
- co-location in the same filesystem or repository tree
- private governance engine internals
- internal cluster topology or namespace layout
- undisclosed or future MCP surfaces

---

## First Truth Surface

The first truth surface for any external participant — human or agent — is:

```
GET /mcp/v1/capabilities
```

All external participant understanding should begin there before further
assumptions are made about platform structure, interfaces, or supported behavior.

This surface discloses:

- transport posture
- auth requirements
- available read-only surfaces
- client guidance

Do not guess hidden or future surfaces. Discover what is disclosed.

---

## Non-Canonical: Private Platform Source Intimacy

Private platform source intimacy is **non-canonical** for this repository.

This means:

- Reading private platform source code is not a prerequisite for using,
  developing in, or contributing to this repository.
- Agent guidance must not instruct browsing private platform internals
  as a discovery or onboarding method.
- Developer onboarding must not require access to the platform repository.
- Relative paths or imports into the platform source tree are not valid
  assumptions for developer-kit operation.

The canonical path to platform truth is the MCP boundary, not private source.

---

## Public-Safe Posture

This document — and all boundary documentation in this repository — follows
public-safe doctrine:

- Laws, outcomes, and interface posture may be described.
- Protected enforcement internals, hidden locks, and private control-plane
  topology must not be exposed as onboarding requirements or operational
  assumptions.

---

## Future Expansion

This boundary posture establishes the foundation for later governed
participation workflows, including:

- capabilities discovery client
- ~~auth and identity bootstrap~~ (see [auth-bootstrap.md](auth-bootstrap.md))
- ~~governed context retrieval~~ (see SDK `ContextClient` — CE-V5-S42-05)
- run-type safety and schema discovery
- proof-ready participant scaffolding
- recursive demo readiness

Those capabilities will be added in subsequent stories. This document
establishes the constitutional boundary they must obey.
