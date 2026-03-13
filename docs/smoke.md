# Read-Only Smoke Path

**CE-V5-S42-07** — First clean end-to-end read-only participant path.

## What It Proves

The smoke path verifies that an external participant can:

1. **Discover** the boundary — `GET /mcp/v1/capabilities` (unauthenticated)
2. **Inspect identity** — `GET /mcp/v1/whoami` (authenticated)
3. **Retrieve context** — `context.compile` via `POST /mcp/v1/runs/start`
4. **Execute a safe read-only run** — `gaps.list` via `POST /mcp/v1/runs/start`

If all four phases pass, the participant has a fully open read-only path
to the governed boundary.

## What It Does NOT Prove

- **Write authority** — the smoke path is strictly read-only.
- **Charter-gated operations** — later stories cover write/proof-bearing surfaces.
- **Event Spine evidence** — local-only runs do not produce upstream-auditable evidence.
- **Full external runtime bridge closure** — a passing smoke path is necessary but not sufficient.

## Usage

```bash
export KEYHOLE_MCP_URL="https://boundary.example.com"
export KEYHOLE_MCP_TOKEN="<bearer-token>"
python examples/python-client/smoke_readonly.py
```

### Programmatic Usage

```python
from keyhole_sdk import ReadOnlySmokeRunner

with ReadOnlySmokeRunner(base_url=url, token=token) as runner:
    result = runner.run()

if result.all_passed:
    print("Read-only path is fully open.")
else:
    print(result.summary())
```

## Example Output

### All Phases Pass

```
Read-Only Smoke Path Results
========================================
  [PASS] discovery
  [PASS] identity
  [PASS] context
  [PASS] readonly_run
========================================
  ALL PHASES PASSED
  Read-only: True
```

### Authentication Failure

```
Read-Only Smoke Path Results
========================================
  [PASS] discovery
  [FAIL] identity
         Error: Authentication failed (401). Token is invalid or expired.
         Suggestion: Acquire a fresh OIDC/PKCE token for realm 'keyhole-mcp'. See docs/auth-bootstrap.md.
  [FAIL] context
         Error: Skipped — identity inspection failed.
         Suggestion: Fix authentication before retrying.
  [FAIL] readonly_run
         Error: Skipped — identity inspection failed.
         Suggestion: Fix authentication before retrying.
========================================
  SMOKE PATH INCOMPLETE
  Read-only: True
```

## Common Failure Modes

| Phase | Error | Cause | Fix |
|---|---|---|---|
| Discovery | `Capabilities discovery failed` | MCP boundary unreachable | Check `KEYHOLE_MCP_URL`, verify network connectivity |
| Discovery | `Capabilities endpoint returned 404` | Wrong URL or path | Ensure URL points to the MCP boundary root (no trailing `/mcp/v1/capabilities`) |
| Identity | `Authentication failed (401)` | Invalid or expired token | Acquire a fresh OIDC/PKCE token for realm `keyhole-mcp` |
| Identity | `Insufficient authority (403)` | Token lacks required scopes | Check participant identity and charter posture |
| Context | `Authentication required` | Token expired between phases | Re-authenticate and retry |
| Context | `Context retrieval returned 500` | Boundary internal error | Wait and retry; escalate if persistent |
| Read-only run | `Preflight rejected gaps.list` | Run type not recognized | Re-discover capabilities; check boundary version |

## Phases in Detail

### Phase 1: Discovery

Calls `GET /mcp/v1/capabilities` **without** authentication.
Extracts contract version, auth flow, transport posture, and available
context surfaces.  This phase must succeed before any authenticated
call.

### Phase 2: Identity Inspection

Calls `GET /mcp/v1/whoami` with a Bearer token.
Confirms the participant's identity as the boundary sees it.
If this fails, subsequent phases are skipped.

### Phase 3: Context Retrieval

Invokes `context.compile` through `POST /mcp/v1/runs/start`.
Retrieves the broadest current platform context bundle.
Confirms the participant can read governed context.

### Phase 4: Safe Read-Only Run

Invokes `gaps.list` through `POST /mcp/v1/runs/start`, optionally
with a preflight check against discovered capabilities.
Confirms the participant can execute a safe read-only run type.

## Next Steps After Success

Once the read-only smoke path passes:

1. Explore other context surfaces: `lineage.get.v0_1`, `convergence.status.v0_1`
2. Use `DispatchPreflight` for safe dispatch of any run type
3. Review [auth-bootstrap.md](auth-bootstrap.md) for full auth lifecycle
4. Review the boundary constitution in [boundary-constitution.md](boundary-constitution.md)
