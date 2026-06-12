# Public Release Candidate Report

Status: PUBLICATION READY pending repository visibility change.

## Merge State

- Main merge commit: `53d68c5adca02f0fae020609fdcaf123c2cbcf10`
- Approved cleanup commit: `b4e554c7c68649c3cfa974d859bfc691bc517827`
- Approved cleanup branch: `public-release-cleanup`
- Preserved baseline commit: `5cf075c62137e4abd8cbb35a2c0736d290f1f034`
- Preservation tags on baseline: `sdk-governed-baseline-accepted`, `sdk-pre-public-release`
- Release candidate tag: `sdk-public-release-candidate-2026-06`

## Verification Clone

- Verification clone path: external `sdk-public-main-verification` clone outside the repository.

## Commands Run

```powershell
git status --short --branch
git rev-parse HEAD
git log --oneline -n 10
git tag --points-at 5cf075c62137e4abd8cbb35a2c0736d290f1f034
git merge --no-ff public-release-cleanup
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\keyhole doctor
.\.venv\Scripts\keyhole validate
.\.venv\Scripts\keyhole validate .\my-first-app
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\keyhole governed run --repo-dir .\my-first-app --no-live --json
```

## Test Results

- `pip install -e ".[dev]"`: pass.
- `keyhole doctor`: pass.
- `keyhole validate`: expected `WARN` at SDK root because the SDK root is not itself a governed app.
- `keyhole validate .\my-first-app`: pass.
- `pytest`: pass, `11 passed`.
- `keyhole governed run --repo-dir .\my-first-app --no-live --json`: pass with `would_mutate_mcp=false`.

## Secret Scan Results

Final scan terms covered real tokens, private hostnames, personal email, personal machine paths, `/opt/keyhole`, `/opt/keyhole_worktrees`, `mcp-prod-us1`, `ubuntu@`, bearer-token patterns, authorization secrets, `.env` values, and generated receipt bundles.

Classifications:

- SAFE PLACEHOLDER: `KEYHOLE_MCP_TOKEN=replace_me` and documentation examples that instruct users to provide their own server/token.
- SDK AUTH IMPLEMENTATION REFERENCE: `Authorization`, `Bearer`, passwordless, and secret-redaction references inside SDK/CLI authentication code.
- REMOVE BEFORE PUBLIC: none found.

No real token, private hostname, personal email, personal machine path, internal deployment assumption, or generated receipt bundle remains tracked.

## README Scope Decision

PASS. The README is SDK/client/starter focused and describes local validation, governed request submission, receipt handling, fail-closed behavior, and `my-first-app`. It does not present the removed runtime/deployment stack as the repository purpose.

## CLI Surface Decision

PASS. Public CLI help exposes the intentional SDK commands: `version`, `doctor`, `validate`, `run`, `repo`, `context`, and `governed`. The old runtime-first command group is not exposed.

## SDK Boundary Decision

PASS. The SDK validates local declarations, submits governed requests to a configured server, normalizes receipts, exposes client APIs, and fails closed without MCP credentials. It does not act as the governance authority, ship private evidence, or require private MCP infrastructure for basic tests.

## Known Remaining Risks

- Advanced SDK modules remain importable by package path and should receive a future module-level public API review.
- Root `keyhole validate` intentionally returns `WARN`; developers should validate `my-first-app` or their governed application directory for native readiness.
- Live governed flows require operator-provided server URL and token.

## Final Publication Recommendation

PUBLICATION READY.
