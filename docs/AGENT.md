# Agent Alignment — Keyhole Developer Kit

This document defines alignment rules for any AI agent, copilot, or automated
contributor working in this repository.

## Boundary Posture

**keyhole-developer-kit** is a separate governed participant repository — not
a subcomponent of keyhole_Platform.

1. **Boundary-first discovery.** The first truth surface is
   `GET /mcp/v1/capabilities`. Begin there before making assumptions about
   platform structure, interfaces, or supported behavior.

2. **No source intimacy.** Do not browse, reference, or depend on private
   platform source code. Platform truth is retrieved through the MCP
   boundary, not through source inspection.

3. **No nested-repo assumptions.** Do not assume co-location with the
   platform repository, relative paths into platform source, or internal
   platform file structures.

See [boundary-constitution.md](boundary-constitution.md) for the full
boundary constitution.

## Core Principles

1. **Truth over aspiration.** Only describe behavior that the current codebase
   implements. Do not describe planned features as if they already work.

2. **Mode awareness is prose-only.** The test runtime operates in two modes:
   - **local-only** (default): no MCP governance gating.
   - **governed**: MCP governance gating active.
   Mode is an operational distinction described in prose. It is **not** a
   response field. Do not add `governance_mode` to example responses.

3. **Contract fidelity.** The current runtime contract is minimal:
   - `/identity` returns: `runtime_id`, `runtime_name`, `runtime_version`,
     `environment`, `capabilities`.
   - `/realize` receipt returns: `digest`, `status`, `message`, `realized_at`.
   Do not add fields that the runtime does not actually emit. Specifically,
   do **not** add `governance_mode`, `governance_verdict`, `result`, `version`,
   or `pointer` to example responses — these are planned for S41 but not
   implemented today.

4. **Public boundary discipline.** This repository is the public developer
   surface. Do not add references to private cluster topology, internal
   Keyhole namespaces, production credentials, or protected control-plane
   APIs.

5. **Schema fidelity.** The OpenAPI spec, JSON schemas, and SDK/CLI models
   must match what the runtime actually returns. If the runtime changes,
   update all surfaces.

## Forbidden Patterns

- Example `/realize` response with `governance_verdict`, `result`, `version`, or `pointer`
- Example `/identity` response with `governance_mode`
- Claiming Event Spine evidence from a local-only run
- Describing the test runtime as "the Keyhole governance engine"
- Implying production-grade persistence or audit in local-only mode
- Adding unimplemented fields to schemas or models

## File Governance

When modifying any of the following files, verify that example responses
and schemas match the current minimal contract:

- `README.md`
- `docs/boundary-constitution.md`
- `docs/quickstart.md`
- `docs/test-runtime.md`
- `docs/bridge-contract.md`
- `docs/architecture.md`
- `openapi/test-runtime.openapi.yaml`
- `packages/python/keyhole-sdk/keyhole_sdk/models.py`
- `examples/bridge-smoke-test/smoke-test.sh`
- `examples/bridge-smoke-test/smoke-test.ps1`
- `examples/bridge-smoke-test/README.md`
