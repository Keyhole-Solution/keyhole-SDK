"""`keyhole validate` — local governance contract and dependency schema validation.

SDK-CLIENT-04: Governance Contract + Dependency Schema.

Validates the local governance contract files present in a repository
directory without requiring MCP connectivity.  Advisory-only for foreign
repos — never fails on a bare directory.

Validation is deterministic and never mutates the target repository.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from keyhole_sdk.validation import (
    ValidationStatus,
    emit_validation_proof,
    map_validation_repair,
    run_validation,
)
from keyhole_sdk.validation.models import ValidationResult

from keyhole_cli.result import (
    CommandResult,
    EXIT_CONTRACT_FAILURE,
    EXIT_INVALID_INPUT,
    EXIT_SUCCESS,
)

_COMMAND_LABEL = "keyhole validate"


def run_validate(
    *,
    repo_path: str = ".",
    mode: str = "auto",
    state_dir: str = "",
    keyhole_home: str = "",
) -> CommandResult:
    """Execute ``keyhole validate``.

    Returns a CommandResult for the CLI to render.

    §4 mode semantics:
    - ``auto``     — detect posture from files present in *repo_path*.
    - ``native``   — force NATIVE posture rules (strict).
    - ``advisory`` — force advisory-only FOREIGN posture.
    """
    target = Path(repo_path).resolve()

    # ── Validate repo path ────────────────────────────────────────────────
    if not target.is_dir():
        return CommandResult(
            command=_COMMAND_LABEL,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary=f"Not a directory: {target}",
            data={"error_class": "InvalidRepoPath"},
            next_steps=map_validation_repair("InvalidRepoPath"),
        )

    # ── Run validation ────────────────────────────────────────────────────
    result = run_validation(target, mode=mode)

    # ── Emit proof if possible ────────────────────────────────────────────
    state = _resolve_state_dir(state_dir, keyhole_home)
    if state:
        try:
            emit_validation_proof(state, result, session_ref=target.name)
        except Exception:
            pass  # proof emission is fire-and-continue; never blocks the result

    # ── Map result to CommandResult ───────────────────────────────────────
    success = result.status != ValidationStatus.REJECT
    exit_code = EXIT_SUCCESS if success else EXIT_CONTRACT_FAILURE

    return CommandResult(
        command=_COMMAND_LABEL,
        success=success,
        exit_code=exit_code,
        summary=_build_human_summary(result),
        data=result.to_dict(),
        next_steps=_build_next_steps(result),
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

def _resolve_state_dir(state_dir: str, keyhole_home: str) -> str:
    """Return a writable state directory path, or empty string if none available."""
    if state_dir:
        return state_dir
    if keyhole_home:
        return str(Path(keyhole_home) / "state")
    env = os.environ.get("KEYHOLE_STATE_DIR", "").strip()
    if env:
        return env
    return ""


def _build_human_summary(result: ValidationResult) -> str:
    """Build a one-line human-readable summary."""
    parts = [
        f"[{result.status.value}]",
        f"posture={result.repo_posture.value}",
        f"readiness={result.readiness.value}",
    ]
    if result.repo:
        parts.append(f"repo={result.repo}")
    issue_count = len(result.issues)
    if issue_count:
        parts.append(f"issues={issue_count}")
    return "  ".join(parts)


def _build_next_steps(result: ValidationResult) -> List[str]:
    """Collect unique repair steps from validation issues."""
    seen: set = set()
    steps: List[str] = []
    for issue in result.issues:
        for step in issue.repair:
            if step not in seen:
                seen.add(step)
                steps.append(step)
    if not steps and result.status == ValidationStatus.REJECT:
        steps = map_validation_repair("missing_required_file")
    return steps
