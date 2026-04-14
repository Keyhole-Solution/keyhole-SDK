"""`keyhole passport` commands — capability passport generation.

SDK-CLIENT-05: Capability Passport Generation.

Deterministically generates a transport-safe capability passport from
declared local repo truth.  Advisory-honest about repo posture.
Never mutates foreign repos.  Never requires MCP connectivity.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from keyhole_sdk.passport import (
    PassportStatus,
    emit_passport_proof,
    generate_passport,
    map_passport_repair,
)
from keyhole_sdk.passport.models import PassportGenerationResult

from keyhole_cli.result import (
    CommandResult,
    EXIT_CONTRACT_FAILURE,
    EXIT_INVALID_INPUT,
    EXIT_SUCCESS,
)

_COMMAND_GENERATE = "keyhole passport generate"
_COMMAND_SHOW = "keyhole passport show"


def run_passport_generate(
    *,
    repo_path: str = ".",
    output: str = "",
    state_dir: str = "",
    keyhole_home: str = "",
    write: bool = True,
) -> CommandResult:
    """Execute ``keyhole passport generate``.

    §5: Only native governed repos produce authoritative passports.
    §13: Writes capability_passport.yaml into the repo when lawful and write=True.
    §18: Emits proof into tool-owned state dir when available.

    Returns CommandResult.  EXIT_SUCCESS on GENERATED; EXIT_CONTRACT_FAILURE
    on REJECTED; EXIT_INVALID_INPUT for bad path.
    """
    target = Path(repo_path).resolve()
    if not target.is_dir():
        return CommandResult(
            command=_COMMAND_GENERATE,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary=f"Not a directory: {target}",
            data={"error_class": "InvalidRepoPath"},
            next_steps=map_passport_repair("InvalidRepoPath"),
        )

    output_path: Optional[Path] = Path(output).resolve() if output else None

    result = generate_passport(target, write=write, output_path=output_path)

    # ── Emit proof ────────────────────────────────────────────────────────
    state = _resolve_state_dir(state_dir, keyhole_home)
    if state:
        try:
            emit_passport_proof(state, result, session_ref=target.name)
        except Exception:
            pass  # proof is fire-and-continue

    # ── Map result ────────────────────────────────────────────────────────
    success = result.status == PassportStatus.GENERATED
    exit_code = EXIT_SUCCESS if success else EXIT_CONTRACT_FAILURE

    return CommandResult(
        command=_COMMAND_GENERATE,
        success=success,
        exit_code=exit_code,
        summary=_build_generate_summary(result, write),
        data=result.to_dict(),
        next_steps=_build_next_steps(result),
    )


def run_passport_show(
    *,
    repo_path: str = ".",
) -> CommandResult:
    """Execute ``keyhole passport show``.

    Reads and displays capability_passport.yaml from the repo.
    Read-only — never mutates.
    """
    target = Path(repo_path).resolve()
    if not target.is_dir():
        return CommandResult(
            command=_COMMAND_SHOW,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary=f"Not a directory: {target}",
            next_steps=map_passport_repair("InvalidRepoPath"),
        )

    passport_file = target / "capability_passport.yaml"
    if not passport_file.exists():
        return CommandResult(
            command=_COMMAND_SHOW,
            success=False,
            exit_code=EXIT_CONTRACT_FAILURE,
            summary=f"No capability_passport.yaml found in: {target}",
            next_steps=[
                "Run: keyhole passport generate — to generate one.",
            ],
        )

    try:
        content = passport_file.read_text(encoding="utf-8")
    except OSError as exc:
        return CommandResult(
            command=_COMMAND_SHOW,
            success=False,
            exit_code=EXIT_CONTRACT_FAILURE,
            summary=f"Cannot read capability_passport.yaml: {exc}",
        )

    return CommandResult(
        command=_COMMAND_SHOW,
        success=True,
        exit_code=EXIT_SUCCESS,
        summary=f"capability_passport.yaml ({len(content)} bytes)",
        data={"path": str(passport_file), "content": content},
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

def _resolve_state_dir(state_dir: str, keyhole_home: str) -> str:
    if state_dir:
        return state_dir
    if keyhole_home:
        return str(Path(keyhole_home) / "state")
    env = os.environ.get("KEYHOLE_STATE_DIR", "").strip()
    return env


def _build_generate_summary(result: PassportGenerationResult, write: bool) -> str:
    if result.status == PassportStatus.GENERATED:
        parts = [
            "Capability passport generated.",
            f"Capabilities: {result.capability_count}",
            f"Digest: {result.digest}",
        ]
        if result.artifact_path:
            parts.append(f"Path: {result.artifact_path}")
        return "  ".join(parts)
    # Rejected
    reasons = ", ".join(i.reason for i in result.issues[:3])
    return f"[REJECTED] repo={result.repo}  readiness={result.readiness.value}  ({reasons})"


def _build_next_steps(result: PassportGenerationResult) -> List[str]:
    if result.status == PassportStatus.GENERATED:
        return [
            "The passport is ready for later boundary verification.",
            "Run: keyhole register — when ready to submit to the MCP boundary.",
        ]
    seen: set = set()
    steps: List[str] = []
    for issue in result.issues:
        for step in issue.repair:
            if step not in seen:
                seen.add(step)
                steps.append(step)
    return steps or map_passport_repair("_default")
