# CLIENT-SIDE AUDIT — keyhole-sdk Public Baseline Readiness
**Audit ID:** sdk-public-readiness-client-20260515  
**Audit Date:** 2026-05-15  
**Scope:** CLIENT-SIDE ONLY (this repo)  
**CLI Version:** 0.3.1  
**SDK Version:** 0.4.1  
**Auditor:** GitHub Copilot / Keyhole Developer Kit agent  
**Final Verdict:** NOT_PUBLIC_READY  

---

## §1 Purpose

This audit determines whether `keyhole-sdk` and `keyhole-cli` are ready to be
made public. It covers the complete developer lifecycle that a first-time external
participant would need to exercise from a clean install through a governed proof
submission.

This is a CLIENT-SIDE audit only. Server behavior is noted where it creates client
blockers, but server-side implementation decisions are outside this repository's scope.

---

## §2 Audit Scope

The following capabilities were audited:

| Category | Items |
|----------|-------|
| Install and version | Fresh install, version reporting |
| Auth | Login, whoami, logout (PKCE/device/passwordless) |
| Config | Defaults, env var overrides, realm correctness |
| Init | vertical scaffold generation |
| Validate | Local YAML/governance contract validation |
| Context | context.compile MCP call |
| Gap lifecycle | gaps.list / gaps.create / gaps.claim |
| Workspace | workspace.provision |
| Proof | proof bundle assembly + submission |
| Receipt | governed receipt verification |
| Capability | capability registration |
| Repo sanitation | Private paths, credentials, tenant IDs |
| Dependency audit | Hard vs soft deps, license |
| Docs | Quickstart, examples, error paths |
| Release gates | 15-gate pass/fail matrix |

---

## §3 Auth Posture (PASS)

Auth defaults were patched on 2026-05-15 (event `3c15c35b`):

```python
DEFAULT_AUTH_SERVER = "https://auth.keyholesolution.com/realms/kh-prod"
DEFAULT_REALM = "kh-prod"
DEFAULT_CLIENT_ID = "keyhole-cli"
DEFAULT_BASE_URL = "https://mcp.keyholesolution.com"
```

Live identity confirmed (`GET /mcp/v1/whoami`):
- `user_id`: c2a432d8-0164-499b-ad84-b662e1f174ec
- `tenant`: tenant-6f4f45b96f64
- `org`: org-bf06d8b73238
- `lane`: prod
- `plan`: free

Auth convergence was also confirmed equivalent between VS Code MCP and keyhole-cli
via identity equivalence audit (8/8 dimensions EQUIVALENT).

**Verdict: PASS**

---

## §4 Install Audit (PASS)

```
pip install -e packages/python/keyhole-sdk packages/python/keyhole-cli
```

Both packages install cleanly with no errors. No private index required.

**Verdict: PASS**

---

## §5 Command Inventory

Full CLI command tree (from `keyhole --help` + sub-app exploration):

**Sub-apps:** `init`, `context`, `runs`, `capability`, `repo`, `auth`, `runtime`,
`explain`, `dependency`, `passport`, `connection`, `host`

**Top-level commands:** `register`, `verify`, `registration-status`, `deregister`,
`login`, `whoami`, `logout`, `run`, `ingest`, `align`, `doctor`, `smoke`,
`auth-doctor`, `connections`, `hosts`

### Missing Commands (BLOCKING)

| Required Command | Status |
|-----------------|--------|
| `keyhole gaps list` | **COMMAND_MISSING** |
| `keyhole gaps create` | **COMMAND_MISSING** |
| `keyhole gaps claim` | **COMMAND_MISSING** |
| `keyhole workspace provision` | **COMMAND_MISSING** |
| `keyhole proof submit` | **COMMAND_MISSING** |
| `keyhole receipt verify` | **COMMAND_MISSING** |
| `keyhole capability register` | **COMMAND_MISSING** |

No `gaps_cmd.py`, `workspace_cmd.py`, `proof_cmd.py`, or `receipt_cmd.py` exist
in `packages/python/keyhole-cli/keyhole_cli/commands/`.

The gap lifecycle, workspace provision, proof submission, and receipt verification
are the core governed developer flow. Without these commands, a first-time developer
cannot complete the lifecycle from the CLI.

**Workaround (degraded path):** `keyhole run --run-type gaps.list` exercises the
MCP endpoint directly but provides no CLI UX, validation, or error messaging.

---

## §6 Validate Command (CLIENT_DEFECT)

```
keyhole validate
```

Fails on clean install with:
```
Cannot parse governance_contract.yaml: pyyaml is not installed.
Install with: pip install pyyaml
```

Root cause: `pyyaml` is lazy-imported in `keyhole_sdk/validation/parser.py` but
not declared in `pyproject.toml` dependencies.

The error message IS actionable. However, a first-time developer installing
`keyhole-sdk` from PyPI would not receive `pyyaml` and the validate command
would silently degrade until they encounter the error in the field.

**Verdict: CLIENT_DEFECT**  
**Repair:** Add `pyyaml>=5.0` to `dependencies` in `packages/python/keyhole-sdk/pyproject.toml`

---

## §7 Context Compile (SERVER_BLOCKED)

```
keyhole context compile
```

Returns: `BLOCKED: No enabled binding`

Root cause: The target workspace has not been admitted via an enabled WorkerBinding
on the server side. The CLI command exists and the error message is clear.

**Verdict: SERVER_BLOCKED (not a client defect)**  
**Note:** Per backend evidence, cohort-0 WorkerBinding was subsequently inserted
by backend-custodian (`fab2b57c`). A re-audit after binding confirmation should
return a context compile result.

---

## §8 Gap Lifecycle (BLOCKED — no CLI commands)

The gap lifecycle (`gaps.list` → `gaps.create` → `gaps.claim` → `workspace.provision`)
cannot be exercised through the CLI at all. The commands do not exist.

Direct MCP test via `keyhole run --run-type gaps.list`:
- Was BLOCKED at time of initial audit (no enabled binding)
- Backend subsequently enabled binding — a re-run after binding confirmation would be needed

**Verdict: BLOCKED — client defect is primary blocker; server binding was secondary**

---

## §9 Local Tests (PASS)

```
cd my-first-app
python -m pytest tests/ -v
```

Result: **5/5 PASS**

- `test_inv_greet_capability.py::test_inv_greet_check_count` — PASS
- `test_inv_greet_capability.py::test_inv_greet_returns_accept` — PASS
- `test_inv_greet_capability.py::test_inv_greet_all_checks_pass` — PASS
- `test_inv_greet_capability.py::test_inv_greet_result_has_required_fields` — PASS
- `test_inv_greet_capability.py::test_inv_greet_result_serializable` — PASS

Local governance gate MY-FIRST-APP-INV-01 passes 7/7 checks locally.
No governed receipt has been received upstream — proof_bundle/core/ contains
local result only.

**Verdict: PASS (local scope only)**

---

## §10 Repo Sanitation (PASS with note)

### Findings

| Finding | File | Classification |
|---------|------|----------------|
| `/opt/keyhole_platform/.venv` | `keyhole_sdk/runtime_contract/builder.py:144` | **INTENTIONAL — negative proof test fixture** |
| No real credentials | All source | CLEAN |
| No real tenant IDs in source | All source | CLEAN |
| No private user paths | All source | CLEAN |
| No DATABASE_URL / KUBECONFIG / Twilio | All source | CLEAN |

The `/opt/keyhole_platform/.venv` reference is inside `build_nonportable_venv_context()`,
a method that INTENTIONALLY builds an invalid context to verify that the server
REJECTS nonportable VM symlinks (§9.7 negative proof). It is not a dependency on
platform internals.

**Verdict: PASS** (intentional test fixture documented; no real leakage)

---

## §11 Dependency Audit

| Package | Version | Declared | Impact |
|---------|---------|----------|--------|
| requests | >=2.25 | YES | CLEAN |
| pydantic | >=2.0 | YES | CLEAN |
| typer | unspecified | YES (CLI only) | CLEAN |
| pyyaml | >=5.0 (suggested) | **NO — soft dep** | **CLIENT_DEFECT** |

Both packages: **Apache-2.0** license — PASS for public distribution.

---

## §12 Docs Audit (PARTIAL)

| Document | Status |
|----------|--------|
| docs/quickstart.md | EXISTS — covers init/validate/login but not gap lifecycle |
| docs/auth-bootstrap.md | EXISTS — adequate |
| docs/boundary-constitution.md | EXISTS — adequate |
| Gap lifecycle guide | **MISSING** |
| Workspace provision guide | **MISSING** |
| Proof submission guide | **MISSING** |
| Receipt verification guide | **MISSING** |
| examples/python-client/*.py | EXISTS — partial coverage |

**Verdict: PARTIAL — gap lifecycle docs absent (consistent with missing commands)**

---

## §13 Release Gates Summary

| Gate | Description | Verdict |
|------|-------------|---------|
| PR-01 | Fresh install | PASS |
| PR-02 | Auth login/whoami | PASS |
| PR-03 | Init vertical | PASS |
| PR-04 | Local validate/test | **CLIENT_DEFECT** |
| PR-05 | Context compile | SERVER_BLOCKED |
| PR-06 | Gap create/list/claim | **COMMAND_MISSING** |
| PR-07 | Workspace provision | **COMMAND_MISSING** |
| PR-08 | Proof submit | **COMMAND_MISSING** |
| PR-09 | Receipt verify | **COMMAND_MISSING** |
| PR-10 | Capability registration | **COMMAND_MISSING** |
| PR-11 | Repo sanitation | PASS with note |
| PR-12 | Docs quickstart | PARTIAL |
| PR-13 | Package build | PARTIAL |
| PR-14 | Error/security redaction | PARTIAL |
| PR-15 | Release tag + manifest | MISSING |

**Blocking gates: 7 (PR-04, PR-06, PR-07, PR-08, PR-09, PR-10, PR-15)**

---

## §14 Blocking Defects

| ID | Severity | Category | Description |
|----|----------|----------|-------------|
| DEF-01 | BLOCKING | COMMAND_MISSING | `keyhole gaps` group absent — no gaps.list/create/claim |
| DEF-02 | BLOCKING | COMMAND_MISSING | `keyhole workspace` group absent — no workspace.provision |
| DEF-03 | BLOCKING | COMMAND_MISSING | `keyhole proof submit` absent |
| DEF-04 | BLOCKING | COMMAND_MISSING | `keyhole receipt verify` absent |
| DEF-05 | BLOCKING | CLIENT_DEFECT | pyyaml soft dep — validate fails on clean install |
| DEF-06 | BLOCKING | SERVER_BLOCKED | context.compile blocked — no enabled binding (backend gate) |
| DEF-07 | ADVISORY | MISSING_DOCS | Quickstart omits gap/workspace/proof/receipt lifecycle |

---

## §15 Minimum Repair Set (for re-audit)

To advance from **NOT_PUBLIC_READY** → **REVIEW_CANDIDATE**:

1. Implement `keyhole_cli/commands/gaps_cmd.py` with `list`, `create`, `claim` subcommands
2. Implement `keyhole_cli/commands/workspace_cmd.py` with `provision` subcommand
3. Implement `keyhole_cli/commands/proof_cmd.py` with `submit` subcommand
4. Implement `keyhole_cli/commands/receipt_cmd.py` with `verify` subcommand
5. Register all new command groups in `keyhole_cli/cli.py`
6. Add `pyyaml>=5.0` to `dependencies` in `packages/python/keyhole-sdk/pyproject.toml`
7. Add corresponding SDK client methods in `keyhole_sdk/` for each new lifecycle step
8. Update `docs/quickstart.md` to cover the complete gap → workspace → proof → receipt lifecycle
9. Tag v0.3.1 / v0.4.1 in git; update CHANGELOG

Server-side prerequisite: backend-custodian must confirm enabled binding for
workspace before DEF-06 can be cleared.

---

## §16 Final Verdict

```
VERDICT: NOT_PUBLIC_READY
RELEASE LABEL: ALPHA_PRIVATE_ONLY
RE-AUDIT TRIGGER: After DEF-01..DEF-05 resolved
```

The SDK and CLI are internally coherent and auth is correctly configured post-patch.
However, the core governed developer lifecycle (gap → workspace → proof → receipt)
has zero CLI surface. A developer following the published quickstart will be unable
to complete the flow.

This is an honest assessment. The SDK is not ready for public release until the
gap lifecycle commands exist and the pyyaml dependency is declared correctly.

---

*Produced by CLIENT-SIDE AUDIT, 2026-05-15. Evidence bundle: `docs/remediation/evidence/sdk-public-readiness-client-20260515/`*
