# Agent Alignment — Keyhole Developer Kit

This document defines alignment rules for any AI agent, copilot, or automated contributor working in this repository.

## Purpose

The **Keyhole Developer Kit** is the public builder-facing surface of the Keyhole ecosystem.

It contains:

- `keyhole-cli`
- `keyhole-sdk`
- the public test runtime
- public schemas and OpenAPI
- examples and onboarding docs
- deployment templates

It does **not** contain private Keyhole platform internals.

Agents working in this repository must optimize for **truthfulness, contract fidelity, and public-boundary discipline**.

---

## Core Principles

### 1. Truth over aspiration

Only describe behavior that the current codebase actually implements.

Do not describe:

- planned features as shipped
- governed behavior as active when it is not
- local-only flows as if they were upstream-auditable
- public ergonomics as if they were constitutional proof

When uncertain, prefer conservative wording.

---

### 2. Mode awareness is mandatory

The public test runtime may operate in different modes. At minimum, agents must distinguish between:

- **local-only** — no MCP governance call is made
- **governed** — MCP connectivity is configured and the runtime is operating against the public governance boundary

All documentation, examples, smoke tests, SDK examples, and CLI examples must make mode explicit when it affects behavior.

Do not present a single unlabeled example that could be misread as both local-only and governed.

---

### 3. No silent overclaim

Never imply any of the following from a local-only run:

- Event Spine evidence
- upstream auditability
- governed approval
- cluster-side visibility
- constitutional bridge proof

If a flow is local-only, say so plainly.

If a flow is governed, only describe the behavior that the current runtime contract actually returns.

---

### 4. Public boundary discipline

This repository is the public developer surface.

Do not add references to:

- private cluster topology
- internal Keyhole namespaces
- production credentials
- protected control-plane APIs
- private governance engine internals
- promotion kernel internals
- sovereign platform implementation details not intentionally exposed in the public contract

The public repo may describe the existence of a governance boundary, but must not leak internal architecture that belongs behind it.

---

### 5. Contract fidelity is mandatory

The following must stay aligned:

- runtime implementation
- OpenAPI spec
- schemas
- SDK models
- CLI expectations
- docs
- examples
- smoke tests

If the runtime response shape changes, update every public surface that depends on it.

If the runtime does **not** return a field, do not add that field to examples or schemas.

If a field **is** part of the current public contract, do not omit it from examples without justification.

---

### 6. Keep requests bounded

Do not widen the public request surface casually.

The public runtime contract must remain:

- narrow
- explicit
- replay-safe
- bounded

Do not introduce extra top-level request fields or ad hoc semantics unless the contract is intentionally revised across implementation, OpenAPI, SDK, CLI, docs, and examples.

---

## Mode Rules

### Local-only mode

Use local-only language when MCP connectivity is absent or inactive.

In local-only mode:

- the runtime may still realize locally
- replay behavior may still work
- local runtime state may still change
- Event Spine evidence must **not** be implied
- upstream governance approval must **not** be implied

### Governed mode

Use governed language only when MCP connectivity is configured and the runtime is actually operating against the governance boundary.

In governed mode:

- upstream governance interaction may occur
- auditable behavior may be possible
- Event Spine evidence may be expected if the current contract and configuration support it

Do not assume a successful governance verdict. Show only what the current runtime implementation and contract actually produce.

---

## Forbidden Patterns

The following are forbidden unless the implementation and public contract explicitly support them:

- Example `/identity` output that hides runtime mode when mode materially affects behavior
- Example `/realize` output that invents governance fields not actually returned by the runtime
- Claiming Event Spine evidence from a local-only run
- Describing the test runtime as “the Keyhole governance engine”
- Implying production-grade persistence or upstream auditability in local-only mode
- Mixing stale and current receipt field names across docs, SDK, CLI, and OpenAPI
- Treating a successful local smoke test as proof of S40-07 closure
- Adding private platform internals to public documentation
- Widening the public contract without updating every dependent surface

---

## File Governance

When modifying any of the following files, verify that examples, schemas, and wording remain truthful and aligned with the current runtime contract:

- `README.md`
- `docs/quickstart.md`
- `docs/test-runtime.md`
- `docs/bridge-contract.md`
- `docs/architecture.md`
- `docs/traefik-deploy.md`
- `openapi/test-runtime.openapi.yaml`
- `packages/python/keyhole-sdk/keyhole_sdk/models.py`
- `packages/python/keyhole-sdk/README.md`
- `packages/python/keyhole-cli/keyhole_cli/cli.py`
- `packages/python/keyhole-cli/README.md`
- `examples/bridge-smoke-test/smoke-test.sh`
- `examples/bridge-smoke-test/smoke-test.ps1`
- `examples/bridge-smoke-test/README.md`
- `examples/python-client/README.md`

Before changing any of these files, check whether the change affects:

- mode semantics
- response shape
- request shape
- smoke-test expectations
- SDK / CLI examples
- documentation truthfulness

---

## Review Checklist for Agents

Before finalizing any change, confirm all of the following:

1. The repo does not claim governed behavior when the example is local-only.
2. The repo does not claim Event Spine evidence unless the flow is actually governed.
3. The docs, OpenAPI, SDK, CLI, and examples all describe the same public contract.
4. No private platform detail was introduced.
5. No future or planned behavior was documented as current.
6. No public contract widening was introduced accidentally.

If any answer is “no,” the change is not aligned yet.

---

## Default Editing Posture

When editing this repository:

- prefer conservative wording
- prefer exact contract matching
- prefer explicit mode labeling
- prefer public-surface clarity over internal sophistication
- prefer truth over ambition

The public developer kit must be useful and interactive, but it must never overstate what has actually been proven.