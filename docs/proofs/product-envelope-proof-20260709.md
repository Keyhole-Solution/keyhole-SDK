# Product Envelope Proof - 2026-07-09

## Verdict

**PASS_WITH_LIMITATION - Public technical preview accepted, complete product-envelope launch blocked.**

The public SDK path produced a fresh governed `ACCEPT` receipt with Event Spine, proof, receipt, and governance-context evidence. The complete product-envelope gate did **not** pass because the fresh governed run did not expose a durable `run_id` or `request_id`, and the optional observability surfaces could not bind to the accepted chain.

## Scope

| Field | Value |
| --- | --- |
| Proof time | 2026-07-09T09:31:24Z through 2026-07-09T09:40:38Z |
| SDK commit | `37f69e6ef314e7050552c18a495fd3b4704352b8` |
| MCP URL | `https://mcp.keyholesolution.com` |
| Realm | `kh-prod` |
| Identity class | Public device-login builder |
| Repo | Public Keyhole SDK / developer kit |
| Proof checkout | `<TEMP>/keyhole-sdk-product-envelope-proof` |
| Blessed example | `examples/second-governed-app` |
| Capability | `second-governed-app.echo.user.v1` |

Proof checkout limitation: the final proof checkout was refreshed from the local SDK repo because commits through `37f69e6` were not yet present on `origin/main`. The checkout remote was set to `https://github.com/Keyhole-Solution/keyhole-SDK.git`, and live repo facts used that GitHub remote. No private platform source, private database access, manual Event Spine mutation, or proof-store mutation was used.

## Fresh Governed Chain

| Field | Value |
| --- | --- |
| Gap ID | `gap_8488f30fb4e1ef82` |
| Gap pre-run state | `OPEN`, `claimable=true`, `blocked=false` |
| Governed run status | `succeeded` |
| Governance verdict | `ACCEPT` |
| Drift state | `non_drifted` |
| Event Spine evidence | `true` |
| Run ID | Empty / not returned |
| Request ID | Not returned |
| Correlation ID | `1df1cdcb-ab22-476b-8127-a8b0e3e30d30` |
| Governance context ID | `gctx_217433e9ca3f30e40c1cf430dee3430d` |
| MCP event ID | `run.complete:1df1cdcb-ab22-476b-8127-a8b0e3e30d30` |
| Proof ID | `gproof_ee9031fb6b40f436f72308d5` |
| Receipt ID | `grcpt_37161dff800ed2299845d771` |

## Surface Evidence

| Surface | Required Result | Actual Result |
| --- | --- | --- |
| whoami | `mode=real` | PASS: `success=true`, `mode=real`, public identity visible, no tokens printed. |
| surfaces | compatible, no missing | PASS as advertised: `compatibility.status=compatible`, `required_missing=[]`, `optional_missing=[]`; flags true for async runs, explain, support bundle, tail, budget, context requirement, and idempotency. |
| gaps list | `claimable=true`, `blocked=false` | PASS before final run and after release: `gap_8488f30fb4e1ef82`, `OPEN`, `claimable=true`, `blocked=false`. |
| validate | PASS | PASS for `examples/second-governed-app`; schema, dependencies, namespace, compatibility all PASS. |
| doctor launch | PASS | PASS at commit `37f69e6`, live MCP URL, GitHub remote, actionable gap availability. |
| governed run/resume | ACCEPT | PASS: fresh `governed run` reached `ACCEPT`, `event_spine_evidence=true`, `drift_state=non_drifted`. |
| governed status | terminal, same ID chain | PARTIAL: local status is terminal/succeeded and live-confirmed, but `run_id` is empty and no `request_id` is present. |
| governed receipt | proof/event/receipt evidence | PASS for receipt evidence: `proof_id`, `receipt_id`, `mcp_event_id`, context ID, verdict, and drift state present. Missing durable run/request identity. |
| run.explain | server-backed, not unknown | FAIL: probing the fresh correlation/event UUID returned `outcome_class=unknown`, `is_terminal=false`, empty context/event/proof refs, and inferred reason. |
| request.inspect | linked request/run/proof/receipt | FAIL: returned `outcome_class=unknown`, empty `run_id`, `executed=false`, and no link to proof/receipt. |
| support.bundle | redacted manifest, required refs | FAIL: local bundle assembled but missing `context`, `events`, and `proof_refs`; not sufficient as server-backed support bundle evidence. |
| runs tail | server-backed ordered observations | FAIL: `observation_method=status_poll`, one `unknown` entry, no terminal observation or server-backed ordering/cursor proof. |
| runs budget | structured run-level budget posture | FAIL: `limit_outcome=no_pressure_data`, empty request/correlation/status linkage, empty budget snapshot. |
| unit tests | pass | PASS: clean proof checkout `tests/unit` returned `3678 passed in 73.70s`; release gate repeated unit suite with `3678 passed in 75.05s`. |
| release gate | pass | PASS: `scripts/public-release-gate.ps1 -IncludeLiveProof` completed with live identity, surfaces, doctor, status, and receipt. It warned only about ignored local generated artifacts. |
| git safety | no generated state tracked | PASS: `git ls-files` returned no `.keyhole` or `proof_bundle` paths; `git diff --check` passed. |

## Capability Advertisement

`keyhole surfaces --json --refresh` advertised the complete envelope as compatible. Raw capabilities also reported:

| Field | Value |
| --- | --- |
| `operations_count` | `30` |
| `operations_declared` | `30` |
| `operations_implemented` | `12` |
| Product run types | `run.status`, `run.budget`, `run.explain`, `request.inspect`, `support.bundle`, `run.tail` |
| Product transport | All listed as `POST /mcp/v1/runs/start`, `transport=runs_start`, `status=live`, `read_only=true` |

The advertisement and behavior do not agree for this fresh accepted governed chain.

## Commands Run

```powershell
git status --short
git diff --stat
git diff --check
git log --oneline origin/main..main
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e packages/python/keyhole-sdk -e packages/python/keyhole-cli pytest
.\.venv\Scripts\python.exe -m keyhole_cli.cli login --help
.\.venv\Scripts\python.exe -m keyhole_cli.cli whoami --json
.\.venv\Scripts\python.exe -m keyhole_cli.cli surfaces --json --refresh
curl.exe -s https://mcp.keyholesolution.com/mcp/v1/capabilities
.\.venv\Scripts\python.exe -m keyhole_cli.cli gaps list --repo-dir examples\second-governed-app --json
.\.venv\Scripts\python.exe -m keyhole_cli.cli validate examples\second-governed-app --json
.\.venv\Scripts\python.exe -m keyhole_cli.cli doctor launch --repo-dir examples\second-governed-app --json
.\.venv\Scripts\python.exe -m keyhole_cli.cli governed run --repo-dir examples\second-governed-app --json
.\.venv\Scripts\python.exe -m keyhole_cli.cli governed status --repo-dir examples\second-governed-app --last --json
.\.venv\Scripts\python.exe -m keyhole_cli.cli governed receipt --repo-dir examples\second-governed-app --last --json
.\.venv\Scripts\python.exe -m keyhole_cli.cli runs status 1df1cdcb-ab22-476b-8127-a8b0e3e30d30 --repo-dir examples\second-governed-app --json
.\.venv\Scripts\python.exe -m keyhole_cli.cli explain run 1df1cdcb-ab22-476b-8127-a8b0e3e30d30 --repo-dir examples\second-governed-app --json
.\.venv\Scripts\python.exe -m keyhole_cli.cli inspect 1df1cdcb-ab22-476b-8127-a8b0e3e30d30 --repo-dir examples\second-governed-app --json
.\.venv\Scripts\python.exe -m keyhole_cli.cli support-bundle 1df1cdcb-ab22-476b-8127-a8b0e3e30d30 --repo-dir examples\second-governed-app --json
.\.venv\Scripts\python.exe -m keyhole_cli.cli runs tail 1df1cdcb-ab22-476b-8127-a8b0e3e30d30 --repo-dir examples\second-governed-app --poll-interval 0.2 --max-entries 3 --json
.\.venv\Scripts\python.exe -m keyhole_cli.cli runs budget 1df1cdcb-ab22-476b-8127-a8b0e3e30d30 --repo-dir examples\second-governed-app --json
.\.venv\Scripts\python.exe -m pytest tests\unit -q --basetemp .pytest-tmp
.\.venv\Scripts\python.exe -m pytest tests -q --basetemp .pytest-tmp
powershell -ExecutionPolicy Bypass -File .\scripts\public-release-gate.ps1 -IncludeLiveProof
git ls-files -- .keyhole proof_bundle examples/second-governed-app/.keyhole examples/second-governed-app/proof_bundle my-first-app/.keyhole my-first-app/proof_bundle
```

Interactive forced login was not rerun during this proof because an active public device-login session was already verified by `whoami`. CLI help at this commit shows `--flow` defaulting to `device`, and `--mcp-url` defaulting to `https://mcp.keyholesolution.com`; the login/default-flow behavior is covered by the unit suite.

## Test Results

| Check | Result |
| --- | --- |
| Focused public release-gate unit coverage | PASS: `3 passed` before committing gate fixes. |
| Clean proof `tests/unit` | PASS: `3678 passed in 73.70s`. |
| Clean proof broader `tests` | FAIL: `3684 passed, 92 skipped, 1 failed`; only failure was smoke prerequisite `jq not found in PATH`. |
| Public release gate with live proof | PASS: completed after unit tests, validation, sanitation scan, generated-state tracking scan, live identity, surfaces, doctor, status, and receipt. |

## Changes Made During Proof

Two public release-gate fixes were committed after the governed-flow fix:

1. `545d115` - install `setuptools` and `services/test-runtime/requirements.txt` in the release gate so a clean venv can build wheels and run unit tests.
2. `37f69e6` - check generated governance artifacts with `git ls-files`; ignored local proof state now warns instead of failing the live proof gate.

These fixes keep generated `.keyhole` and `proof_bundle` artifacts untracked while allowing `-IncludeLiveProof` to read the local status/receipt created by the live proof run.

## Failure Classification

Primary classification: **Backend failure / capability-contract failure.**

Reasons:

- The fresh governed chain reached `ACCEPT` but did not expose `run_id` or `request_id`.
- Capabilities advertised `run.explain`, `request.inspect`, `support.bundle`, `run.tail`, and `run.budget` as live public product surfaces.
- Those surfaces could not bind to the fresh accepted correlation/event chain and returned fallback-like or unknown results.
- `run.tail` explicitly used `status_poll`, which the launch gate says is not sufficient for full `run_tail=true`.
- `runs budget` returned hollow `no_pressure_data` without identity/request/correlation linkage.

Secondary SDK follow-up:

- Optional-surface commands currently return `success=true` for unknown/fallback-only output. For launch safety, the SDK should make this degradation unmistakable or fail closed when a surface cannot prove server-backed truth.

## Known Limitations

- Final proof commits were local and not yet on `origin/main`; the proof checkout was refreshed from the local repo while retaining the public GitHub remote for live repo facts.
- Forced interactive login was not rerun; active auth was proven with `whoami`, and login defaults were checked through CLI help and unit coverage.
- The broader `tests` command requires `jq` for a smoke prerequisite on this host; unit tests and the public release gate passed.
- Support bundle output was not accepted as complete envelope proof because it omitted required context, event, and proof references for the fresh identifier.

## Final Decision

Core governed repo proof is live and acceptable for technical preview:

- Fresh governed run reached `ACCEPT`.
- Receipt evidence includes Event Spine evidence, proof ID, receipt ID, governance context, and non-drifted verdict.
- Public release gate passes with live proof.
- Generated governance state remains untracked.

Complete governed repo product launch remains blocked until the server and SDK expose a durable run/request identity for the accepted governed chain and the advertised optional product surfaces bind to that same identity with non-unknown, server-backed results.
