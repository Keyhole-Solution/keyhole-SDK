# Copilot Instructions — Keyhole Developer Kit

This repository is the **public builder-facing surface** of the Keyhole ecosystem.

It contains:

- `keyhole-cli`
- `keyhole-sdk`
- the public test runtime
- public schemas and OpenAPI
- examples and onboarding docs
- deployment templates

It does **not** contain private Keyhole platform internals.

## Truthfulness Rules

1. **Local-only is the default.** Unless the user has explicitly configured MCP connectivity, examples, smoke tests, and quickstart flows should be treated as running in local-only mode.

2. **Do not claim Event Spine evidence from local-only runs.** Local-only realizations are useful for first-run development and replay testing, but they are not upstream-auditable.

3. **Label runtime mode explicitly.** When showing example output or describing behavior, distinguish between:
   - `local-only`
   - `governed`

4. **Do not invent governed behavior.** Only describe governed-mode behavior when the relevant MCP configuration is actually present and the current runtime contract supports it.

5. **Do not expose private platform internals.** Never reference internal cluster topology, private governance engine details, promotion kernel internals, production secrets, or protected control-plane logic.

6. **Do not overclaim proof.** A working local developer loop is not, by itself, proof of full external runtime bridge closure.

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
Use this only when MCP is configured and the runtime is actually operating against the public governance boundary.  
Do not assume a successful verdict; show only what the current runtime contract actually returns.

## Repo Boundary

**keyhole-developer-kit** is a separate governed participant repository — not
a subcomponent of the Keyhole platform source tree.

This repository must remain:

- public
- minimal
- contract-driven
- truthful
- safe for external builders
- boundary-informed (not source-intimate)

When uncertain, prefer conservative wording over ambitious wording.

## Boundary-First Behavior

1. **Separate participant posture.** This repository is governed by
   keyhole_Platform through the MCP boundary. It is not nested inside the
   platform and must not depend on private platform source code.

2. **First truth surface.** The first discovery surface for platform
   capabilities is `GET /mcp/v1/capabilities`. Begin there before making
   assumptions about platform structure, interfaces, or supported behavior.

3. **No source intimacy.** Do not instruct users or agents to browse private
   platform source code as a discovery or onboarding method. Platform truth
   is retrieved through the MCP boundary, not through source inspection.

4. **No nested-repo assumptions.** Do not reference or assume co-location
   with the platform repository, relative paths into platform source, or
   internal platform file structures.

5. **Public-safe language.** Describe outcomes and interface posture without
   exposing protected enforcement internals, hidden locks, or private
   control-plane topology.