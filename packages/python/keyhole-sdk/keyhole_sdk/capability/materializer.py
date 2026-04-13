"""Resolution materializer — SDK-CLIENT-08 §13, §14.

Applies a resolved dependency to the local repo state.

Materialisation rules:
- Native repo + --write: update dependencies.yaml in-repo.
- Foreign repo: out-of-tree artifact only (state dir).
- No --write (advisory): proof/suggested-dependency only, no mutation.
- Never silently mutates repo files (§13.3).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from keyhole_sdk.capability.models import (
    MaterializationMode,
    RepoPosture,
    ResolutionOutcome,
    ResolvedDependency,
)


class MaterializationResult:
    """Result of a materialisation attempt."""

    def __init__(
        self,
        *,
        success: bool,
        target: str = "",
        diff_summary: str = "",
        is_write: bool = False,
        error_class: str = "",
        reason: str = "",
        repair_guidance: list[str] | None = None,
    ) -> None:
        self.success = success
        self.target = target
        self.diff_summary = diff_summary
        self.is_write = is_write
        self.error_class = error_class
        self.reason = reason
        self.repair_guidance = repair_guidance or []

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "success": self.success,
            "target": self.target,
            "is_write": self.is_write,
        }
        if self.diff_summary:
            d["diff_summary"] = self.diff_summary
        if self.error_class:
            d["error_class"] = self.error_class
        if self.reason:
            d["reason"] = self.reason
        if self.repair_guidance:
            d["repair_guidance"] = self.repair_guidance
        return d


def materialize_resolution(
    *,
    outcome: ResolutionOutcome,
    repo_path: Path,
    repo_posture: RepoPosture,
    state_dir: Path,
    mode: MaterializationMode = MaterializationMode.ADVISORY,
) -> MaterializationResult:
    """Materialise a resolved dependency according to posture and mode.

    §13.1: Native repo + --write → update dependencies.yaml.
    §13.2: Foreign repo → out-of-tree only.
    §13.3: No --write → no mutation.
    """
    if not outcome.is_resolved or outcome.resolved is None:
        return MaterializationResult(
            success=False,
            error_class="UnresolvedOutcome",
            reason=f"Cannot materialise: outcome status is '{outcome.status}'.",
            repair_guidance=["Resolve the capability first."],
        )

    resolved = outcome.resolved

    # Advisory mode: out-of-tree only, regardless of posture
    if mode == MaterializationMode.ADVISORY:
        return _emit_advisory_artifact(
            resolved=resolved,
            outcome=outcome,
            state_dir=state_dir,
        )

    # Write mode: check posture
    if repo_posture in (RepoPosture.FOREIGN, RepoPosture.INGESTION_BACKED):
        return MaterializationResult(
            success=False,
            error_class="UnsupportedWriteTarget",
            reason=(
                f"Repo posture is '{repo_posture.value}' — "
                "in-repo write is not lawful for foreign repos by default."
            ),
            repair_guidance=[
                "Use --advisory mode for foreign repos.",
                "Complete alignment before writing dependency state.",
                "Run: keyhole repo register — and alignment steps first.",
            ],
        )

    # Native repo + write: update dependencies.yaml
    return _write_native_dependency(
        resolved=resolved,
        outcome=outcome,
        repo_path=repo_path,
        state_dir=state_dir,
    )


def _emit_advisory_artifact(
    *,
    resolved: ResolvedDependency,
    outcome: ResolutionOutcome,
    state_dir: Path,
) -> MaterializationResult:
    """Emit an out-of-tree suggested-dependency artifact."""
    corr = outcome.correlation_id or "unknown"
    target_dir = state_dir / "resolution" / _safe_dirname(corr)
    target_dir.mkdir(parents=True, exist_ok=True)

    suggested = resolved.to_dependency_entry()
    suggested["advisory"] = True
    suggested["correlation_id"] = outcome.correlation_id

    target_file = target_dir / "suggested-dependency.json"
    target_file.write_text(
        json.dumps(suggested, indent=2),
        encoding="utf-8",
    )

    return MaterializationResult(
        success=True,
        target=str(target_file),
        diff_summary="Advisory artifact emitted (no repo mutation).",
        is_write=False,
    )


def _write_native_dependency(
    *,
    resolved: ResolvedDependency,
    outcome: ResolutionOutcome,
    repo_path: Path,
    state_dir: Path,
) -> MaterializationResult:
    """Write a deterministic dependency entry into dependencies.yaml."""
    dep_file = repo_path / "dependencies.yaml"
    entry = resolved.to_dependency_entry()

    # Build a YAML-safe append block
    block_lines = [
        f"- capability: {entry['capability']}",
        f"  provider: {entry['provider']}",
    ]
    if entry.get("version"):
        block_lines.append(f"  version: {entry['version']}")
    if entry.get("digest"):
        block_lines.append(f"  digest: {entry['digest']}")
    block = "\n".join(block_lines) + "\n"

    # Read existing content
    existing = ""
    if dep_file.is_file():
        existing = dep_file.read_text(encoding="utf-8")

    # Check for duplicate
    if entry["capability"] in existing and entry["provider"] in existing:
        return MaterializationResult(
            success=True,
            target=str(dep_file),
            diff_summary="Dependency already present in dependencies.yaml (no change).",
            is_write=False,
        )

    # Append
    new_content = existing.rstrip("\n") + "\n" + block if existing.strip() else block
    dep_file.write_text(new_content, encoding="utf-8")

    diff_summary = f"Added dependency: {entry['capability']} → {entry['provider']}"
    if entry.get("version"):
        diff_summary += f"@{entry['version']}"

    return MaterializationResult(
        success=True,
        target=str(dep_file),
        diff_summary=diff_summary,
        is_write=True,
    )


def _safe_dirname(name: str) -> str:
    """Sanitize a correlation ID for safe directory naming."""
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
