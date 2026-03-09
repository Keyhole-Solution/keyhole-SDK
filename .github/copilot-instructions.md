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
Examples and docs should reflect the current public runtime contract. If runtime mode is exposed, show it truthfully.

### `/realize`
Examples and docs must match the current public runtime receipt shape exactly. Do not add undocumented fields or omit implemented ones.

## Mode Model

### Local-only
Use this when MCP is not configured.  
Do not imply governance gating, Event Spine evidence, or upstream auditability.

### Governed
Use this only when MCP is configured and the runtime is actually operating against the public governance boundary.  
Do not assume a successful verdict; show only what the current runtime contract actually returns.

## Repo Boundary

This repository must remain:

- public
- minimal
- contract-driven
- truthful
- safe for external builders

When uncertain, prefer conservative wording over ambitious wording.