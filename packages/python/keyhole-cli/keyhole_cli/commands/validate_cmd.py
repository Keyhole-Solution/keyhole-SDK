"""`keyhole validate` — local governance contract and dependency schema validation.

SDK-CLIENT-04: Governance Contract + Dependency Schema.
SDK-CLIENT-06: Local Validation Pipeline — strict mode, compatibility domain,
               --proof flag, --quiet flag.

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

# Default state dir for `--proof` without explicit state-dir
_DEFAULT_PROOF_STATE = os.path.expanduser("~/.keyhole/state")


def run_validate(
    *,
    repo_path: str = ".",
    mode: str = "auto",
    state_dir: str = "",
    keyhole_home: str = "",
    strict: bool = False,
    proof: bool = False,
    quiet: bool = False,
) -> CommandResult:
    """Execute ``keyhole validate``.

    Returns a CommandResult for the CLI to render.

    §4 mode semantics:
    - ``auto``     — detect posture from files present in *repo_path*.
    - ``native``   — force NATIVE posture rules (strict).
    - ``advisory`` — force advisory-only FOREIGN posture.

    §11 strict mode (SDK-CLIENT-06):
    - All warnings are elevated to REJECT.
    - Additional checks run (e.g. dependency provider required).

    §12 proof flag (SDK-CLIENT-06):
    - ``proof=True`` forces proof emission even when no state_dir is configured.
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
    result = run_validation(target, mode=mode, strict=strict)

    # ── Emit proof if possible ────────────────────────────────────────────
    state = _resolve_state_dir(state_dir, keyhole_home)
    if not state and proof:
        state = _DEFAULT_PROOF_STATE
    if state:
        try:
            proof_dir = emit_validation_proof(state, result, session_ref=target.name)
            result.proof_ref = str(proof_dir)
        except Exception:
            pass  # proof emission is fire-and-continue; never blocks the result

    # ── Map result to CommandResult ───────────────────────────────────────
    success = result.status != ValidationStatus.REJECT
    exit_code = EXIT_SUCCESS if success else EXIT_CONTRACT_FAILURE

    return CommandResult(
        command=_COMMAND_LABEL,
        success=success,
        exit_code=exit_code,
        summary="" if (quiet and success) else _build_human_summary(result),
        data=result.to_dict(),
        next_steps=[] if (quiet and success) else _build_next_steps(result),
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
    if result.checks:
        check_str = " ".join(f"{k}:{v}" for k, v in result.checks.items())
        parts.append(f"checks=({check_str})")
    issue_count = len(result.issues)
    if issue_count:
        parts.append(f"issues={issue_count}")
    if result.strict:
        parts.append("strict=on")
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
