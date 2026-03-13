<!-- Path: docs/context/epics/evolution/ce-v5/stories/ce-v5-s42-index.md Owner: Keyhole Solution Foundation Epic: CE-V5-S42 — Governed External Participant & Developer Kit Boundary Lane: External Participant (Developer Kit), Dev/Verification first Status: DRAFT Created: 2026-03-13 Purpose: Make `keyhole-developer-kit` the first clean governed external participant that learns, connects, and operates through the Keyhole MCP boundary as source of truth rather than through private platform source intimacy. -->
CE-V5-S42 — Governed External Participant & Developer Kit Boundary
Doctrine + Epic Story Index
1) Epic Thesis
1.1 Core Thesis

The first external participant must not depend on private source intimacy.

It must learn the platform through the platform’s own governed boundary.

For CE-V5-S42, that participant is:

keyhole-developer-kit

The epic proves that a separate repo can:

discover the platform through GET /mcp/v1/capabilities

authenticate through the published auth model

retrieve governed context through MCP

use exact canonical run types instead of guessing

obey charter, workspace, and boundary rules

become proof-ready for later recursive governance demonstrations

1.2 Why It Matters

This is the first real demonstration that Keyhole can govern a connected repo without absorbing it.

The developer kit becomes:

the first clean external participant

the first machine-usable public onboarding surface

the first repo whose agents are taught to consult MCP truth before acting

the first bridge between private platform truth and external governed usage

1.3 Constitutional Alignment

CE-V5-S42 extends and depends on existing doctrine. It does not alter it.

This epic must remain aligned with:

Rule 00 — Builders Out, Declarations In

One Mint — promotion is sole canonical mutation

Single Spine / Dual Lens

Proof-Before-Power

Runtime Bridge Doctrine

Snapshot Workspace Safety

Capability Preservation

MCP Boundary Closure

Boundary Replay Determinism

Public Anti-Drift / selective disclosure doctrine

1.4 Core Principle

The developer kit must be taught:

boundary truth first, assumptions never.

That means:

capabilities before guessing

context before implementation

schema before dispatch

identity before writes

proof before promotion

2) Current Boundary Truth This Epic Must Respect

These are the operative truths reflected in the current MCP boundary contract and capabilities disclosure.

2.1 Discovery Surface

The canonical public discovery surface is:

GET /mcp/v1/capabilities

This is public-safe, read-only, and unauthenticated.

It must be treated as the first source of truth for:

contract version

implemented vs declared surfaces

compatibility posture

current transport posture

context-access contract

invariants and attested boundary posture

public-safe client guidance

2.2 Current Public-Safe Boundary Facts

The current public-safe posture indicates:

contract: mcp/v1

transport: rest-http

auth flow: OIDC/PKCE

auth realm: keyhole-mcp

minimum SDK version: 0.1.0

charter required: true

workspace supported: true

operations declared: 30

operations implemented: 9

2.3 Current Read-Only Context Access Surfaces

The current context-access contract indicates these read-only run types are implemented:

context.compile

gaps.list

lineage.get.v0_1

convergence.status.v0_1

2.4 Critical Client Rules

The developer kit must teach humans and agents that:

run types are exact canonical keys

pluralization or guessing must be treated as failure-prone behavior

runs are named workflows, not REST resources

capabilities/context must be consulted before dispatch

authenticated identity is required for identity and write-oriented surfaces

legacy SSE and JSON-RPC transports are tombstoned and must not be used

3) Epic Goal

Implement the first clean external participant posture for keyhole-developer-kit, such that the repo can:

discover the platform safely

connect correctly

retrieve governed context

enforce schema- and run-type-safe execution behavior

provide a minimal read-only smoke path

become ready for later contract/proof participation once DEV-UX surfaces stabilize

4) Non-Goals

CE-V5-S42 must not:

redesign the MCP boundary

introduce private-source coupling back into the developer kit

bypass charter or workspace rules

guess run types or infer hidden surfaces by convention

expose private enforcement topology or protected internals

mutate platform runtime directly

expand the sealed boundary surface merely for convenience

This epic consumes the boundary.
It does not redefine the boundary.

5) Success Criteria

The epic succeeds when all of the following are true:

keyhole-developer-kit operates as a fully separate governed repo

the repo’s Copilot/agent instructions teach MCP-first behavior

capabilities retrieval is implemented and documented

auth/bootstrap guidance is correct and current

context retrieval works through MCP, not private code reading

run dispatch helpers validate exact run types and schema before use

a read-only smoke flow works end to end

the repo is positioned to become the first external participant in the recursive governance demo

6) Story Map (S42 Series)
CE-V5-S42-01 — External Participant Boundary Constitution
Goal

Lock the repo split as canonical and define the external participant posture for keyhole-developer-kit.

Why It Matters

The platform must govern adjacent repos by contract and boundary, not by nesting them inside itself.

Deliverables

explicit repo-boundary doctrine for keyhole-developer-kit

ownership and relationship statement between platform repo and developer-kit repo

removal of any remaining assumptions that the SDK/developer kit lives inside platform source

canonical developer-kit boundary note in repo docs

Acceptance Criteria

keyhole-developer-kit is documented as a separate governed participant

platform source intimacy is declared non-canonical for the developer kit

developer kit guidance points to MCP discovery/capabilities as first truth surface

no instructions remain that imply nested-repo dependency

CE-V5-S42-02 — Copilot / Agent Instruction Rehydration
Goal

Rewrite the repo’s formative and legacy agent instructions so they reflect the live MCP boundary rather than stale assumptions.

Why It Matters

This is the first place where agent behavior becomes boundary-governed instead of repo-folklore-driven.

Deliverables

rewritten copilot-instructions for the developer kit

MCP-first instruction set

explicit rule to consult capabilities/context before architectural assumptions

explicit warning against guessing run types

explicit connection guidance for auth, transport, and boundary-safe usage

Acceptance Criteria

instructions reference GET /mcp/v1/capabilities as the initial source of truth

instructions reflect current transport/auth posture

instructions require exact canonical run-type usage

instructions forbid stale-source or private-source dependency for platform truth

CE-V5-S42-03 — Capabilities Discovery Client
Goal

Implement a minimal client path in the developer kit that retrieves and normalizes the public-safe boundary contract from the capabilities surface.

Why It Matters

The developer kit must be able to learn the boundary from the boundary itself.

Deliverables

capabilities fetch client

normalized capabilities model

caching / digest handling for discovery snapshots

helper for extracting compatibility, context-access, and client guidance data

Acceptance Criteria

developer kit retrieves mcp/v1 capabilities successfully

normalized structure exposes contract, compatibility, auth, transport, and implemented context surfaces

boundary digest / generated-at metadata is preserved where present

consumers can use the normalized result without reading raw platform code

CE-V5-S42-04 — Auth & Identity Bootstrap Guidance
Goal

Provide the correct developer-kit posture for authentication and initial identity inspection.

Why It Matters

External participant onboarding fails immediately if auth and identity are wrong.

Deliverables

documented OIDC/PKCE bootstrap guidance

token acquisition guidance aligned with keyhole-mcp

identity inspection usage guidance for GET /mcp/v1/whoami

authenticated vs unauthenticated surface distinction

Acceptance Criteria

developer kit docs explain discovery vs authenticated surfaces clearly

identity guidance matches current boundary rules

write/read distinctions are made explicit

bootstrap flow is machine- and human-readable

CE-V5-S42-05 — Governed Context Retrieval Bootstrap
Goal

Add the first context-retrieval flow to the developer kit so it can consult governed platform truth before implementation or dispatch.

Why It Matters

This is where the developer kit stops behaving like a static SDK and starts behaving like a governed participant.

Deliverables

context bootstrap helper

support for current context-access run types

context snapshot normalization

usage examples for retrieving platform context before work

Acceptance Criteria

developer kit can invoke current read-only context surfaces through MCP

context retrieval occurs without reading private platform internals

context responses can be normalized into a stable local representation

docs instruct agents to retrieve context before assumption-making

CE-V5-S42-06 — Run-Type Safety & Schema Discovery Helpers
Goal

Prevent humans and agents from guessing workflows, request shapes, or invalid dispatch names.

Why It Matters

The current boundary explicitly requires exact canonical run types. Guessing must become structurally difficult.

Deliverables

run-type validation helpers

schema discovery helper usage

dispatch preflight checks

error-path guidance for unknown run types and invalid request shapes

Acceptance Criteria

developer kit refuses or warns on guessed/invalid run names before dispatch

helpers guide users toward exact canonical run types

schema discovery usage is documented where applicable

client guidance from capabilities is reflected in helper behavior

CE-V5-S42-07 — Read-Only Smoke Path
Goal

Create the first clean end-to-end read-only participant path:

discover → authenticate if needed → inspect identity → retrieve context → perform safe read-only run.

Why It Matters

The first external participant demo must succeed before proof or promotion behavior is layered on top.

Deliverables

smoke command or script path

deterministic read-only example flow

example output capture

troubleshooting notes for common misconfiguration

Acceptance Criteria

a new developer can perform a full boundary-safe smoke path from the developer kit

smoke path uses live MCP surfaces rather than mocked assumptions

flow remains read-only and public-safe where intended

common connection and run-type errors are documented

CE-V5-S42-08 — Proof-Ready Participant Scaffolding
Goal

Prepare the developer kit to become a governed participant in later recursive-governance flows once DEV-UX contract/proof surfaces stabilize.

Why It Matters

S42 should not stop at connection. It should prepare the first participant for contract and proof participation without prematurely coupling to unstable internals.

Deliverables

participant contract placeholder posture

verification runner scaffolding

proof-bundle shape placeholder aligned to emerging platform expectations

clear separation between current supported flows and proof-ready future flows

Acceptance Criteria

developer kit contains explicit proof-ready scaffolding

scaffolding is clearly marked as boundary-consuming, not boundary-defining

no unstable platform internals are hardcoded

future integration points are isolated behind adapters

CE-V5-S42-09 — Recursive Demo Readiness Pack
Goal

Prepare the developer kit to serve as the first external participant in the recursive governance demonstration.

Why It Matters

This is the bridge between developer onboarding and the DEV-UX recursive proof story.

Deliverables

candidate demo workflow in the developer kit

small demo-safe feature/change path

operator notes for running the external-side half of the recursive demo

mapping from developer-kit actions to expected platform-side evidence

Acceptance Criteria

developer kit can participate in a scripted external-side recursive demo flow

the developer-kit side of the story is deterministic and well documented

expected handoff points to DEV-UX proof/promotion flows are explicit

repo is ready to be used in DEV-UX-09 or its successor demo story

CE-V5-S42-10 — Developer Kit Launch Readiness Seal
Goal

Seal the developer kit as the first trustworthy external participant surface.

Why It Matters

The repo should become a launch-grade participant surface, not just a technical experiment.

Deliverables

readiness checklist

public-safe trust posture summary

supported environment matrix

first-success smoke evidence bundle

launch-grade external participant attestation

Acceptance Criteria

discovery/auth/context/smoke flows are documented and reproducible

repo instructions are current and non-legacy

connection posture matches live boundary truth

repo is usable by Lance and future external builders without private platform intimacy

7) Execution Order

The correct execution order for S42 is:

S42-01 — External Participant Boundary Constitution

S42-02 — Copilot / Agent Instruction Rehydration

S42-03 — Capabilities Discovery Client

S42-04 — Auth & Identity Bootstrap Guidance

S42-05 — Governed Context Retrieval Bootstrap

S42-06 — Run-Type Safety & Schema Discovery Helpers

S42-07 — Read-Only Smoke Path

S42-08 — Proof-Ready Participant Scaffolding

S42-09 — Recursive Demo Readiness Pack

S42-10 — Developer Kit Launch Readiness Seal

8) Dependency Notes
Hard Inputs Already Available

This epic can proceed now because:

MCP boundary closure is attested

boundary stabilization is attested

public capabilities discovery exists

the developer-kit repo has been split into its own private location

Inputs From DEV-UX

This epic should consume DEV-UX results as they stabilize, especially:

DEV-UX-02 — MCP Context Surface

DEV-UX-03 — Participant Contract Registry

DEV-UX-04 — Proof Submission Pipeline

DEV-UX-06 — Structured Verdict & Repair Artifacts

DEV-UX-09 — Recursive Story Demonstration

S42 must remain loosely coupled to these surfaces until they are stable.

9) Architectural Promise

CE-V5-S42 guarantees that the first external participant learns the platform through:

discovery

context

schema

identity

boundary-safe execution

rather than through:

private repo intimacy

stale docs

guessed workflows

hidden assumptions

This is the first public-facing proof that Keyhole can teach its own ecosystem how to connect correctly.

10) Epic Completion Condition

CE-V5-S42 is complete when keyhole-developer-kit can demonstrably:

exist as a clean separate governed repo

discover the platform from GET /mcp/v1/capabilities

bootstrap correct auth/identity behavior

retrieve governed context through MCP

prevent run-type and schema guessing

execute a safe read-only smoke path

stand ready as the first external participant in the recursive governance demo

At that point, the developer kit stops looking like:

an isolated helper repo

and starts looking like:

the first governed external participant in the Keyhole ecosystem.

If you want, I’ll turn this next into the fully expanded CE-V5-S42-01 story.