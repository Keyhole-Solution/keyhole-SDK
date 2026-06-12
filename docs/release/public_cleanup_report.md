# Public Cleanup Report

Status: draft generated during cleanup. Final command results are appended after verification.

## 1. Baseline

- Workspace path: `C:\Users\natha\Keyhole-SDK\keyhole-sdk-public-cleanup`
- Branch: `public-release-cleanup`
- Original HEAD: `5cf075c62137e4abd8cbb35a2c0736d290f1f034`
- Tags confirmed: `sdk-governed-baseline-accepted`, `sdk-pre-public-release`
- Cleanup start time: `2026-06-12T18:17:55.3528671+04:00`

## 2. Files Removed

Removed generated artifacts, internal-only notes, obsolete docs, temporary test debris, server deployment files, build/cache output, and live probe material.

Major categories:

- `.keyhole/`, `proof_bundle/`, `my-first-app/.keyhole/`, and `my-first-app/proof_bundle/`: generated local governance state and receipts.
- `probe-live-*.txt`, `_probe*.py`, `check_*.py`, root `*_input.json`, and root `test_*.py`: operator scratch files and live-debug harnesses.
- `docs/context/`, `docs/evidence/`, `docs/remediation/`, cutover docs, recursive demo docs, and launch evidence: internal development history and incident evidence.
- `services/`, `deploy/`, `docker-compose.yml`, `openapi/test-runtime.openapi.yaml`, and `.devcontainer/`: server/runtime deployment details outside the public SDK boundary.
- `examples/`: non-minimal examples and generated governed state; `my-first-app` is retained as the public starter.
- `tests/`: internal story/cutover tests replaced with a small public contract suite.
- `packages/python/*/*.egg-info`: generated package metadata.
- `.github/` and `.vscode/`: local/internal workflow and host configuration.

## 3. Files Modified

- `README.md`: rewritten as a public SDK README with install, validation, server configuration, first-app flow, generated-file guidance, and boundary rules.
- `.env.example`: sanitized to placeholder governed server values only.
- `.gitignore`: expanded to block local Keyhole state, generated governance artifacts, Python caches, build output, local env files, IDE files, and logs.
- `pyproject.toml`: added root editable install for fresh public clones.
- `packages/python/keyhole-cli/keyhole_cli/cli.py`: reduced to intentional public commands and removed private hosted defaults.
- `packages/python/keyhole-sdk/keyhole_sdk/__init__.py`: narrowed top-level public SDK exports.
- `packages/python/keyhole-sdk/keyhole_sdk/config.py`: removed private hosted default URLs.
- `my-first-app/*`: sanitized as a minimal public starter app.
- `docs/guides/public-quickstart.md`: added public fresh-clone walkthrough.
- `tests/`: added focused public contract tests.

## 4. Files Intentionally Kept

- `packages/python/keyhole-sdk/`: SDK implementation retained. Some advanced client modules remain importable by path, but are no longer advertised as top-level public authority.
- `packages/python/keyhole-cli/keyhole_cli/commands/`: command adapters retained for public CLI commands and future audited expansion.
- `schemas/`: public JSON schemas retained.
- `my-first-app/`: retained as the minimal starter app.
- `.env.example`: retained because it contains placeholders only.
- `repo-file-inventory-before-cleanup.txt`: retained as requested cleanup evidence.
- `docs/release/public_cleanup_start.md`: retained as required baseline evidence.

## 5. Public CLI Surface

Final intended commands:

- `keyhole version`
- `keyhole doctor`
- `keyhole validate`
- `keyhole repo register`
- `keyhole context compile`
- `keyhole context inspect`
- `keyhole run`
- `keyhole governed run`
- `keyhole governed status`
- `keyhole governed resume`
- `keyhole governed receipt`

## 6. SDK Public API Surface

Final intended top-level SDK entry points:

- `KeyholeClient`
- `RuntimeBridgeClient`
- `KeyholeConfig`
- `GovernanceReceipt`
- `RealizationReceipt`
- `RealizationRequest`
- `RuntimeHealth`
- `RuntimeIdentity`
- `RuntimeState`
- `run_validation`
- `validate_keyhole_yaml`
- `validate_governance_contract`
- `validate_capability_passport`
- `validate_dependencies`
- public exception and auth provider classes

## 7. Documentation Status

README and public quickstart were rewritten for a fresh external developer. Internal cutover notes, remediation evidence, private deployment assumptions, and local generated proof history were removed.

## 8. Test Results

Pending final verification.

## 9. Secret Scan Results

Initial scan found live probe tokens, generated pycache paths containing `C:\Users\...`, private hosted defaults, and many generated proof artifacts. These were removed or sanitized.

Pending final scan.

## 10. Remaining Risks

- Some advanced SDK modules remain in the package tree for compatibility but should receive a future API-by-module review before a major public announcement.
- Package-level `pyproject.toml` files still exist alongside the new root install metadata.
- Live governed behavior was not expected to pass without real placeholder-replaced credentials.

## 11. Human Verification Commands

```powershell
cd C:\Users\natha\Keyhole-SDK\keyhole-sdk-public-cleanup
git status --short --branch
git tag --points-at 5cf075c62137e4abd8cbb35a2c0736d290f1f034
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
keyhole doctor
keyhole validate
keyhole validate .\my-first-app
pytest
keyhole governed run --repo-dir .\my-first-app --no-live
```
