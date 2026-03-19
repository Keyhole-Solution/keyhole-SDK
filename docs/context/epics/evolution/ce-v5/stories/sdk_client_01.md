# sdk-client-01.md

# DEV-SDK-01 — Authentication Bootstrap (Client)

**Story ID:** DEV-SDK-01 / sdk-client-01  
**Epic:** DEV-SDK — Governed Developer SDK, Onboarding, and Repository Ingestion  
**Status:** READY FOR IMPLEMENTATION  
**Owner / Author:** Keyhole Solution Foundation  
**Lane:** Dev (implementation + validation), Prod (promotion only)  
**System:** SDK / CLI / Local Builder Runtime  
**Story Type:** Client-side zipper story  
**Paired Server Story:** `sdk-server-01.md`

---

## 1. Story Purpose

Implement the **client-side authentication bootstrap flow** that allows a brand-new builder to authenticate into the Keyhole ecosystem, persist usable local credentials safely, inspect their governed identity context, and immediately continue into the next SDK workflow without manual configuration.

This story is responsible for the builder-facing experience of:

- `keyhole login`
- PKCE and/or device flow initiation/completion from the CLI
- secure local credential storage
- `keyhole whoami`
- clear visibility into shadow vs real participation mode

This story closes the client half of the **first zipper** of the SDK boundary. If this story is awkward, brittle, or ambiguous, the entire SDK onboarding experience will feel heavy before the builder sees any value.

---

## 2. Why This Story Exists

The SDK must not assume:

- a pre-existing `.env`,
- a manually provisioned token,
- hidden configuration,
- prior familiarity with Keyhole doctrine.

The client must therefore give the builder a first-run flow that is:

- simple,
- secure,
- attributable,
- explainable,
- easy to recover when it fails,
- good enough to get from zero to first useful result quickly.

This story exists to make the first builder handshake with Keyhole feel trustworthy and easy.

---

## 3. Story Outcome

When this story is complete, the CLI/SDK must be able to:

1. initiate an approved login flow,
2. support PKCE and/or constrained/device login depending on environment,
3. receive and persist a usable local credential/session safely,
4. call `/whoami` using the issued credential,
5. render identity context clearly for the builder,
6. surface whether the builder is in shadow or real mode,
7. hand off usable credentials to subsequent SDK commands,
8. contribute client-side artifacts to the zipper proof bundle.

---

## 4. Scope

### In scope

- `keyhole login` command implementation
- PKCE-first login flow support
- constrained/device-style login support where required
- secure local credential persistence
- `keyhole whoami` command implementation
- visibility of mode (`shadow` vs `real`)
- local proof bundle contribution for the auth zipper
- builder-facing repair guidance for common login failures

### Out of scope

- auth provider internals
- server-side token issuance logic
- multi-user desktop account switching UX beyond the minimum needed for a usable CLI
- deep admin workflows
- advanced identity management beyond login + whoami bootstrap

---

## 5. Constitutional Requirements

This client-side story must preserve the following truths:

- the SDK is not the control plane,
- all participation flows through the MCP/auth boundary,
- no floating execution is allowed,
- identity context must be visible and attributable,
- a zipper is not closed until it produces a replayable proof bundle,
- failure must produce repair guidance rather than dead ends,
- onboarding must feel easy before governance depth is fully revealed.

---

## 6. Client Responsibilities

The client-side implementation must provide the following capabilities.

### 6.1 `keyhole login`

The CLI must implement a `keyhole login` command that:

- initiates auth with the server,
- chooses the appropriate flow for the environment,
- guides the builder through completion,
- persists the resulting credential/session,
- validates success by calling `/whoami`.

### 6.2 PKCE flow support

The client must support the primary interactive browser-oriented flow.

Expected behavior:

- request login start from server,
- open browser or display URL,
- accept completion artifact or poll/complete as required,
- exchange completion artifact for usable session/token,
- verify resulting auth state.

### 6.3 Device/constrained flow support

The client must support a fallback or environment-appropriate path for situations where browser-first login is not ideal.

Expected behavior:

- request device/constrained flow start,
- display code and verification instructions when needed,
- poll or complete until success/failure,
- obtain usable session/token,
- verify auth state.

### 6.4 Secure local credential store

The client must persist credentials/session metadata in a secure local store.

The local store must be:

- CLI-owned,
- scoped to Keyhole use,
- not dependent on a manually created `.env`,
- suitable for later SDK commands.

### 6.5 `keyhole whoami`

The client must implement a `keyhole whoami` command that calls the server identity surface and renders enough context for the builder to understand:

- who they are acting as,
- what tenant/org they belong to,
- what cohort/worker/workspace is active,
- whether they are in shadow or real mode,
- what their next likely step is.

### 6.6 Proof bundle contribution

The client must contribute the client-side half of the zipper proof bundle, including:

- user-facing request parameters where safe,
- flow path chosen,
- local completion state,
- credential persistence result,
- whoami output reference,
- final verification state.

---

## 7. UX Requirements

The authentication bootstrap is the first live experience of the platform. UX is part of correctness here.

### 7.1 First-run expectation

A new builder should be able to run:

```text
keyhole login
```

and be guided to success without reading platform doctrine first.

### 7.2 Minimal output requirements

On success, the CLI must show enough to establish confidence.

At minimum it should communicate:

- login succeeded,
- identity resolved,
- current tenant/org,
- mode (`shadow` or `real`),
- what to do next.

### 7.3 Repair-oriented failure output

If login fails, the CLI must report:

- what failed,
- whether the issue is local, auth-related, or network-related,
- what action to take next.

### 7.4 Progressive disclosure

The CLI should show only the most useful identity information by default, while still supporting more detailed inspection when needed.

---

## 8. Command Requirements

### 8.1 `keyhole login`

The command must:

1. request auth bootstrap from the server,
2. select or honor the correct flow,
3. complete auth,
4. persist the resulting credential/session locally,
5. call `/whoami`,
6. render success state.

### 8.2 `keyhole whoami`

The command must:

1. load the local credential/session,
2. call the server identity endpoint,
3. render the returned identity context clearly,
4. surface mode and workspace context.

### 8.3 Recommended helper behavior

The client should guide the builder toward the next meaningful step.

Examples:

- `keyhole init vertical`
- `keyhole ingest .`
- `keyhole validate`

---

## 9. Local Credential Store Requirements

This is one of the most important implementation details in the story.

### 9.1 Minimum requirements

The credential store must:

- be created automatically,
- not rely on `.env`,
- store the minimum necessary token/session metadata,
- be readable by subsequent SDK commands,
- avoid printing secrets to the terminal,
- support clear invalidation/refresh behavior in later stories.

### 9.2 Safe storage requirements

The store must avoid careless leakage through:

- logs,
- stdout,
- proof artifacts,
- debug dumps.

### 9.3 Local state model

The client must track enough local state to know:

- whether the user is authenticated,
- whether the stored session is usable,
- whether the current mode is shadow or real,
- which identity context was last verified.

---

## 10. Identity Visibility Requirements

The identity model is only useful if the builder can see and understand it.

### 10.1 Minimum fields to render in `keyhole whoami`

The command should render at least:

- user identifier,
- tenant,
- org,
- cohort,
- worker if applicable,
- workspace reference,
- plan,
- mode,
- limits summary or relevant operational constraints if returned.

### 10.2 Human-readable rendering

The output must be useful to a human builder and not force them to inspect raw JSON to understand context.

### 10.3 Machine-readable option

The client should allow structured output in a later or optional mode, but default output must optimize for comprehension.

---

## 11. Shadow vs Real Mode Requirements

Builders must understand whether they are participating in:

- shadow/noncanonical mode,
- real/governed mode.

### 11.1 Requirements

The client must:

- render mode explicitly,
- preserve mode in proof artifacts,
- avoid making builders infer mode from vague wording.

### 11.2 Principle

Mode visibility is part of trust.

---

## 12. Failure and Repair UX

Authentication bootstrap must not strand the builder.

### 12.1 Failure classes the client must handle cleanly

- network/connectivity failure,
- browser launch failure,
- expired challenge,
- invalid completion token/code,
- denied login,
- unusable token after completion,
- local credential store write failure,
- `/whoami` verification failure after login.

### 12.2 Required error behavior

For each failure, the client must provide:

- clear description,
- deterministic reason where known,
- next action.

### 12.3 Examples of repair guidance

- retry login,
- use device flow,
- clear local session and retry,
- verify browser completion,
- check connectivity,
- contact org admin only when truly needed.

---

## 13. Proof Bundle Requirements

This story must emit the client-side half of a replayable proof bundle.

### 13.1 Minimum proof bundle shape

```text
proof_bundle/
  ├── core.json
  ├── request.json
  ├── response.json
  ├── event_chain.json
  ├── passport.json
  ├── verification_result.json
  ├── identity_context.json
  ├── correlation.json
  ├── summary.md
  ├── diff.json
  ├── digest.txt
  └── extended/
```

### 13.2 Client-specific requirements

For authentication bootstrap, the client-side proof materials must capture:

- flow type used,
- login initiation metadata,
- local completion state,
- credential persistence outcome,
- whoami verification outcome,
- mode visibility,
- final client-side verification result.

### 13.3 Sensitive data rule

Proof artifacts must never store secrets in cleartext.

---

## 14. Functional Flow

### 14.1 Happy path

```text
keyhole login
→ auth flow initiated
→ builder completes auth
→ client receives token/session
→ local credential store written
→ client calls whoami
→ identity rendered
→ proof bundle closed
```

### 14.2 Shadow path

```text
keyhole login
→ auth completes in shadow/noncanonical mode
→ client stores local context
→ whoami shows shadow mode
→ builder can proceed safely
```

### 14.3 Failure path

```text
keyhole login
→ auth fails or verification fails
→ client reports failure class
→ repair guidance shown
→ no false success state
```

---

## 15. Acceptance Criteria

This story is complete only when all of the following are true:

1. `keyhole login` can initiate a valid auth flow,
2. the client supports PKCE and/or constrained/device flow as required by environment,
3. the client can receive a usable token/session from the server flow,
4. the client writes credentials/session metadata to a secure local store,
5. the client does not require manual `.env` setup,
6. `keyhole whoami` returns and renders correct identity context,
7. `keyhole whoami` makes shadow vs real mode visible,
8. stored credentials/session are usable for subsequent commands,
9. the client contributes proof artifacts sufficient to close the zipper,
10. failure paths produce deterministic repair guidance.

---

## 16. Test Plan

### 16.1 Positive tests

#### Test A — Browser/PKCE login success

- run `keyhole login`
- complete browser flow
- verify session/token obtained
- verify local credential store written
- run `keyhole whoami`
- verify expected identity output

#### Test B — Device/constrained flow success

- run `keyhole login` in constrained/device mode
- complete verification sequence
- verify local credential store written
- verify whoami succeeds

#### Test C — Token/session usable across commands

- authenticate successfully
- run `keyhole whoami`
- run one additional auth-protected command placeholder or helper check
- verify client uses stored credential/session correctly

#### Test D — Shadow mode visible

- authenticate into shadow/noncanonical mode
- verify mode displayed clearly in whoami output
- verify proof bundle captures mode

#### Test E — Real mode visible

- authenticate into real/governed mode
- verify mode displayed clearly in whoami output
- verify proof bundle captures mode

### 16.2 Negative tests

#### Test F — Browser flow cannot open

- simulate browser launch failure
- verify client falls back or provides repair guidance

#### Test G — Completion artifact invalid

- simulate invalid completion token/code
- verify no false success state
- verify repair guidance shown

#### Test H — Credential store write failure

- simulate local secure store failure
- verify clear error and no broken partial success state

#### Test I — Whoami fails after login

- simulate token/session issuance followed by whoami failure
- verify client reports verification failure and does not report a complete success

#### Test J — Missing/expired local session

- run `keyhole whoami` with no valid local credential/session
- verify clean failure + suggested next action (`keyhole login`)

### 16.3 Proof tests

#### Test K — Client proof bundle sufficiency

- perform successful login flow
- verify generated proof data contains client-side flow choice, local store result, whoami outcome, and final verification state

#### Test L — No secret leakage in proof artifacts

- inspect proof bundle and logs
- verify secrets/tokens are not stored or printed in unsafe form

---

## 17. Expected Proof Artifacts

At minimum this story must contribute proof material sufficient to confirm:

- login initiated,
- login completed,
- local credential written,
- whoami verified,
- mode visible,
- zipper closed on the client side.

Expected key artifacts:

- login initiation metadata
- flow selection metadata
- local store result
- whoami output reference
- identity_context.json
- verification_result.json
- summary.md

---

## 18. Completion Proof

This story is zipper-closed only when the paired server story and this client story together prove:

```text
keyhole login
→ server issues usable session
→ client stores credential
→ keyhole whoami
→ correct identity context rendered
→ AUTH_SUCCESS emitted
→ proof bundle generated
```

No partial success is acceptable.

---

## 19. Final Story Summary

DEV-SDK-01 client-side authentication bootstrap is the builder’s first experience of Keyhole.

If it is weak:

- onboarding friction rises,
- identity feels abstract,
- trust drops immediately,
- later SDK stories inherit confusion.

If it is strong:

- the builder gets in quickly,
- the local environment is configured automatically,
- identity becomes visible and trustworthy,
- shadow vs real mode is obvious,
- the zipper closes with replayable proof,
- the rest of the SDK can build on a stable first-run experience.

