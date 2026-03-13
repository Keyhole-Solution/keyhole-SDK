# Auth & Identity Bootstrap — Keyhole Developer Kit

This document describes the correct authentication and identity bootstrap
posture for external participants connecting to the Keyhole MCP boundary.

It teaches the governed entrance sequence: **discover, authenticate, inspect
identity, then proceed.**

---

## Bootstrap Sequence Overview

External participants must follow this sequence. Do not skip steps.

```text
Step 1 — Discover     GET /mcp/v1/capabilities     (unauthenticated)
Step 2 — Authenticate Acquire token via OIDC/PKCE   (realm: keyhole-mcp)
Step 3 — Inspect      GET /mcp/v1/whoami            (authenticated)
Step 4 — Proceed      Context retrieval, run dispatch, etc.
```

Each step builds on the prior. A participant that skips discovery or identity
inspection is operating on assumptions rather than boundary truth.

---

## Step 1 — Discover the Boundary

Before authenticating, call the public discovery surface:

```
GET /mcp/v1/capabilities
```

This surface is:

- **public-safe** — no authentication required
- **read-only** — it discloses posture, it does not mutate state
- **the first truth surface** for any external participant

From the capabilities response, you learn:

- the current contract version (`mcp/v1`)
- transport posture (`rest-http`)
- auth flow (`OIDC/PKCE`)
- auth realm (`keyhole-mcp`)
- minimum SDK version
- whether charter is required
- whether workspace is supported
- implemented context-access surfaces
- client guidance for run types, gaps, and events

**Do not guess** auth posture, transport, or supported surfaces from stale
docs, old comments, or naming conventions. The capabilities surface is always
the canonical source.

The developer kit provides a programmatic discovery client:

```python
from keyhole_sdk.discovery import CapabilitiesClient

with CapabilitiesClient("https://boundary.example.com") as client:
    result = client.fetch()
    print(result.get_auth_flow())       # "OIDC/PKCE"
    print(result.get_transport())       # "rest-http"
    print(result.is_charter_required()) # True
```

---

## Step 2 — Authenticate

After discovering the boundary posture, acquire a token through the published
auth model.

### Current Auth Posture

| Aspect    | Current Value  |
|-----------|----------------|
| Auth flow | OIDC/PKCE      |
| Realm     | `keyhole-mcp`  |
| Transport | REST/HTTP      |

### Token Acquisition

1. Initiate an OIDC/PKCE authorization flow against the `keyhole-mcp` realm.
2. Complete the PKCE exchange to receive an access token.
3. Carry the token as a `Bearer` token in the `Authorization` header for all
   subsequent authenticated requests.

### What This Means

- **OIDC/PKCE** is the only supported auth flow. Do not attempt Basic auth,
  API keys, or other mechanisms.
- **`keyhole-mcp`** is the realm. Do not authenticate against other realms
  and expect boundary access.
- Token acquisition happens **after** capabilities discovery, not before.
- The boundary publishes its auth posture through capabilities so
  participants do not need to guess from stale documentation.

### What Tokens Enable

Possessing a valid token enables:

- identity inspection (`GET /mcp/v1/whoami`)
- authenticated read operations (context retrieval)
- later governed execution flows (run dispatch, event query)

Possessing a valid token does **not** imply:

- permission for arbitrary mutation
- automatic charter enrollment
- write authority over all surfaces
- proof-bearing privileges

Authentication is the **entrance** to governed interaction, not a blanket
authorization for all actions.

### Guidance for Agents

Agents and automated consumers should:

1. Never hardcode tokens in source or configuration files.
2. Use environment variables or secure token providers
   (see `EnvironmentTokenProvider` in the SDK).
3. Acquire tokens through the published OIDC/PKCE flow.
4. Treat the capabilities-disclosed auth posture as canonical.

### Guidance for Humans

Developers onboarding manually should:

1. Start with `GET /mcp/v1/capabilities` to confirm the current auth model.
2. Use the OIDC/PKCE flow for the `keyhole-mcp` realm to acquire a token.
3. Never share tokens in documentation, commits, or public channels.
4. Treat tokens as scoped credentials, not universal access grants.

---

## Step 3 — Inspect Identity

After authenticating, the first action must be identity inspection:

```
GET /mcp/v1/whoami
```

### What whoami Confirms

- **Authenticated boundary identity** — who the boundary sees you as
- **Subject visibility** — your participant identity at the boundary
- **Lane/purpose context** — where exposed by the boundary
- **Ownership/participant context** — where exposed by the boundary
- **Bootstrap readiness** — whether the current identity state is suitable
  for proceeding to governed interaction

### Why whoami Is Required

`whoami` is not a convenience endpoint. It is the **first authenticated truth
check**.

Without calling `whoami`, a participant is operating on the assumption that
authentication succeeded and that its identity posture is correct. That
assumption may be wrong.

Common failure modes avoided by calling `whoami`:

- Token was issued for the wrong realm
- Token has expired or been revoked
- Participant identity does not match expected enrollment
- Permissions are narrower than assumed

### Example Usage

```python
from keyhole_sdk import KeyholeClient

client = KeyholeClient(
    base_url="https://boundary.example.com",
    auth_provider=my_auth_provider,
)

# First authenticated action: inspect identity
identity = client.identity()
print(identity)  # Confirm who the boundary sees you as
```

### Anti-Pattern: Skipping whoami

Do **not** authenticate and then proceed directly to run dispatch, context
retrieval, or proof submission without first inspecting identity.

```text
✗ Authenticate → Run dispatch             (skipped identity inspection)
✓ Authenticate → whoami → Run dispatch    (correct sequence)
```

---

## Step 4 — Proceed Carefully

Only after completing Steps 1–3 should a participant move to governed
interaction:

| Next Action                  | Surface                        | Auth Required |
|------------------------------|--------------------------------|---------------|
| Context retrieval            | `POST /mcp/v1/runs/start`     | Yes           |
| Run dispatch                 | `POST /mcp/v1/runs/start`     | Yes           |
| Event query                  | `POST /mcp/v1/events/query`   | Yes           |
| Later proof-bearing flows    | (future stories)               | Yes           |

### Charter and Workspace Awareness

The current capabilities contract indicates:

- **Charter required:** `true`
- **Workspace supported:** `true`

This means that later governed flows may require charter enrollment and
workspace posture beyond what authentication alone provides.

Authentication is the **first** governed entrance step, not the **entire**
participant lifecycle. Later stories (S42-05+) will address charter and
workspace bootstrap.

---

## Surface Categories — Read vs Write Distinction

External participants must distinguish these surface categories:

### 1. Public Discovery (Unauthenticated, Read-Only)

| Surface                       | Description                              |
|-------------------------------|------------------------------------------|
| `GET /mcp/v1/capabilities`   | Boundary posture and operations          |

No token required. Pure read-only disclosure.

### 2. Authenticated Identity (Read-Oriented)

| Surface                       | Description                              |
|-------------------------------|------------------------------------------|
| `GET /mcp/v1/whoami`         | Current participant identity inspection  |

Requires a valid token. Read-oriented. Does not mutate state.

### 3. Authenticated Read (Governed)

| Surface                       | Description                              |
|-------------------------------|------------------------------------------|
| `POST /mcp/v1/runs/start`   | Context-access run types (read-only)     |
| `POST /mcp/v1/events/query` | Event Spine query                        |

Requires a valid token. These are read-only governed operations.
The run types used for context access (`context.compile`, `gaps.list`,
`lineage.get.v0_1`, `convergence.status.v0_1`) are read-only.

### 4. Authenticated Write / Proof-Bearing (Governed, Later Stories)

Later governed flows will involve:

- mutation-bearing run types
- proof submission
- contract registration
- workspace provisioning

These are **not equivalent** to read-only exploration. Possession of a token
does not grant write authority by default.

---

## Anti-Patterns

Do **not**:

- **Guess auth posture** from stale docs, old comments, or naming conventions.
  Always check `GET /mcp/v1/capabilities` for the current auth model.

- **Assume every endpoint is publicly callable.** Only
  `GET /mcp/v1/capabilities` is available without authentication.

- **Confuse public discovery with authenticated execution.** Calling
  `capabilities` does not make you a governed participant.

- **Skip whoami and proceed blindly.** Always inspect identity after
  authenticating, before attempting governed interaction.

- **Treat write-bearing surfaces as equivalent to read-only exploration.**
  Read-only context access and mutation-bearing run dispatch are different
  categories with different authority requirements.

- **Assume authentication completes the participant lifecycle.**
  Later flows may require charter enrollment and workspace posture.

- **Embed secrets in docs or source.** Do not hardcode tokens, passwords,
  or sensitive credentials in repository documentation, example code, or
  configuration files.

---

## Bootstrap Flow — Machine-Readable Summary

For agents and automated consumers, the deterministic bootstrap sequence is:

```
1. GET  /mcp/v1/capabilities     → learn contract, transport, auth, surfaces
2. OIDC/PKCE token acquisition   → realm: keyhole-mcp
3. GET  /mcp/v1/whoami           → confirm authenticated identity posture
4. Proceed                       → context retrieval, run dispatch, etc.
```

### Preconditions for Each Step

| Step | Precondition                                      |
|------|---------------------------------------------------|
| 1    | Network access to the boundary                    |
| 2    | Capabilities response parsed; auth posture known  |
| 3    | Valid token acquired                               |
| 4    | Identity posture confirmed via whoami              |

### Failure at Any Step

If any step fails, **do not proceed** to the next step. Instead:

- Step 1 failure → boundary unreachable; retry or escalate
- Step 2 failure → auth posture may have changed; re-discover
- Step 3 failure → identity mismatch; verify token and realm
- Step 4 prerequisites not met → do not attempt governed interaction

---

## Relationship to Other Documents

| Document                                                          | Purpose                                           |
|-------------------------------------------------------------------|---------------------------------------------------|
| [boundary-constitution.md](boundary-constitution.md)              | Constitutional boundary posture                   |
| [quickstart.md](quickstart.md)                                    | Local test runtime (local-only mode)              |
| [architecture.md](architecture.md)                                | Public developer surface architecture             |
| [AGENT.md](AGENT.md)                                              | Agent alignment rules                             |

This document addresses the **governed boundary bootstrap** — the path from
public discovery through authentication and identity inspection.

The [quickstart](quickstart.md) covers **local-only mode**, which does not
involve MCP authentication or identity inspection.
