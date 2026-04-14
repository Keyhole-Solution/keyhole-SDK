"""Passport generation — SDK-CLIENT-05.

§8: Source inputs from declared repo truth only.
§9: Capability discovery rules — declared only, deterministic order.
§11: Deterministic serialization.
§12: Transport safety.
§13: Local persistence rules.
§15: Validation before generation.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from keyhole_sdk.passport.digest import compute_passport_digest, serialize_passport_for_storage
from keyhole_sdk.passport.models import (
    CapabilityEntry,
    CapabilityPassportArtifact,
    PassportGenerationResult,
    PassportIdentity,
    PassportIssue,
    PassportLineage,
    PassportProof,
    PassportReadiness,
    PassportRepo,
    PassportStatus,
    PassportTransport,
)
from keyhole_sdk.passport.repair import map_passport_repair
from keyhole_sdk.validation.detector import detect_repo_posture
from keyhole_sdk.validation.models import ContractRepoPosture
from keyhole_sdk.validation.parser import load_yaml_safe

# §12: Forbidden characters in repo identity values that could contaminate transport.
_UNSAFE_REPO_NAME_RE = re.compile(r"[^\w\-.]")


def generate_passport(
    repo_path: Path,
    *,
    write: bool = True,
    output_path: Optional[Path] = None,
) -> PassportGenerationResult:
    """§6 — Generate a capability passport from declared local repo truth.

    §5: Only native governed repos produce authoritative passports.
    §8: Source is declared truth only — inferred capabilities are not included.
    §11: Deterministic — same effective input → same digest.
    §13: Writes to capability_passport.yaml in native repos when write=True.

    Args:
        repo_path:   Resolved repo root directory.
        write:       When True, write capability_passport.yaml into native repo.
        output_path: Override write path (optional).

    Returns:
        PassportGenerationResult (GENERATED or REJECTED).
    """
    # ── 1. Determine posture ───────────────────────────────────────────────
    posture = detect_repo_posture(repo_path)

    if posture == ContractRepoPosture.FOREIGN:
        return _reject(
            repo_path,
            PassportReadiness.FOREIGN,
            reason="ForeignRepoNotReady",
            file="",
            field="",
        )

    # ── 2. Load keyhole.yaml ───────────────────────────────────────────────
    kh_path = repo_path / "keyhole.yaml"
    if not kh_path.exists():
        if posture == ContractRepoPosture.PARTIALLY_ALIGNED:
            return _reject(
                repo_path,
                PassportReadiness.PARTIALLY_ALIGNED,
                reason="PartiallyAlignedNotReady",
                file="keyhole.yaml",
                field="",
            )
        return _reject(
            repo_path,
            PassportReadiness.NOT_READY,
            reason="MissingKeyholeYaml",
            file="keyhole.yaml",
            field="",
        )

    kh_data, kh_err = load_yaml_safe(kh_path)
    if kh_err:
        return _reject(
            repo_path,
            PassportReadiness.NOT_READY,
            reason="ValidationRejected",
            file="keyhole.yaml",
            field="",
            detail=kh_err,
        )

    repo_name = (kh_data or {}).get("repo", "")
    if not isinstance(repo_name, str) or not repo_name.strip():
        return _reject(
            repo_path,
            PassportReadiness.NOT_READY,
            reason="MissingRepoIdentity",
            file="keyhole.yaml",
            field="repo",
        )
    repo_name = repo_name.strip()

    # §12: Reject unsafe repo names early
    if _UNSAFE_REPO_NAME_RE.search(repo_name):
        return _reject(
            repo_path,
            PassportReadiness.NOT_READY,
            reason="UnsafeRepoName",
            file="keyhole.yaml",
            field="repo",
        )

    owner = str((kh_data or {}).get("owner", ""))

    # ── 3. Load governance_contract.yaml ──────────────────────────────────
    gc_path = repo_path / "governance_contract.yaml"
    if not gc_path.exists():
        if posture == ContractRepoPosture.PARTIALLY_ALIGNED:
            return _reject(
                repo_path,
                PassportReadiness.PARTIALLY_ALIGNED,
                reason="PartiallyAlignedNotReady",
                file="governance_contract.yaml",
                field="",
            )
        return _reject(
            repo_path,
            PassportReadiness.NOT_READY,
            reason="MissingGovernanceContract",
            file="governance_contract.yaml",
            field="",
        )

    gc_data, gc_err = load_yaml_safe(gc_path)
    if gc_err:
        return _reject(
            repo_path,
            PassportReadiness.NOT_READY,
            reason="ValidationRejected",
            file="governance_contract.yaml",
            field="",
            detail=gc_err,
        )

    # ── 4. Extract and validate declared capabilities ─────────────────────
    raw_caps = (gc_data or {}).get("produces", [])
    issues, validated_caps = _validate_capabilities(raw_caps, "governance_contract.yaml")
    if issues:
        return PassportGenerationResult(
            status=PassportStatus.REJECTED,
            readiness=PassportReadiness.NOT_READY,
            repo=repo_name,
            repo_path=str(repo_path),
            issues=issues,
            source_files=["keyhole.yaml", "governance_contract.yaml"],
        )

    if not validated_caps:
        return PassportGenerationResult(
            status=PassportStatus.REJECTED,
            readiness=PassportReadiness.NOT_READY,
            repo=repo_name,
            repo_path=str(repo_path),
            issues=[PassportIssue(
                file="governance_contract.yaml",
                field="produces",
                reason="NoDeclaredCapabilities",
                repair=map_passport_repair("NoDeclaredCapabilities"),
            )],
            source_files=["keyhole.yaml", "governance_contract.yaml"],
        )

    # ── 5. Load optional lineage hints ────────────────────────────────────
    parent_repo = str((gc_data or {}).get("parent_repo", ""))
    parent_passport_digest = str((gc_data or {}).get("parent_passport_digest", ""))

    # ── 6. Compute digest (§11) ───────────────────────────────────────────
    digest = compute_passport_digest(
        repo_name=repo_name,
        capabilities=[c.name for c in validated_caps],
        owner=owner,
        parent_repo=parent_repo,
        parent_passport_digest=parent_passport_digest,
    )

    # ── 7. Build the artifact ─────────────────────────────────────────────
    generated_at = datetime.now(timezone.utc).isoformat()
    artifact = CapabilityPassportArtifact(
        repo=PassportRepo(repo_name=repo_name, owner=owner),
        identity=PassportIdentity(),
        capabilities=validated_caps,
        lineage=PassportLineage(
            parent_repo=parent_repo,
            parent_passport_digest=parent_passport_digest,
        ),
        proof=PassportProof(),
        transport=PassportTransport(generated_at=generated_at, digest=digest),
    )

    # ── 8. Write artifact (§13) ───────────────────────────────────────────
    artifact_path = ""
    if write:
        target = output_path or (repo_path / "capability_passport.yaml")
        try:
            target.write_text(
                serialize_passport_for_storage(artifact.to_payload()),
                encoding="utf-8",
            )
            artifact_path = str(target)
        except OSError:
            pass  # Write failure is non-fatal; result still returned

    return PassportGenerationResult(
        status=PassportStatus.GENERATED,
        readiness=PassportReadiness.READY,
        repo=repo_name,
        repo_path=str(repo_path),
        capability_count=len(validated_caps),
        digest=digest,
        artifact_path=artifact_path,
        artifact=artifact,
        issues=[],
        source_files=["keyhole.yaml", "governance_contract.yaml"],
    )


# ── Private helpers ───────────────────────────────────────────────────────────


def _reject(
    repo_path: Path,
    readiness: PassportReadiness,
    *,
    reason: str,
    file: str = "",
    field: str = "",
    detail: str = "",
) -> PassportGenerationResult:
    repair = map_passport_repair(reason)
    if detail:
        repair = [detail] + repair
    return PassportGenerationResult(
        status=PassportStatus.REJECTED,
        readiness=readiness,
        repo=repo_path.name,
        repo_path=str(repo_path),
        issues=[PassportIssue(file=file, field=field, reason=reason, repair=repair)],
    )


def _validate_capabilities(
    raw_caps: object,
    file_label: str,
) -> Tuple[List[PassportIssue], List[CapabilityEntry]]:
    """§9 — Validate declared capabilities.

    Rules:
    - must be a list of strings
    - each must be a valid capability namespace (via SDK-CLIENT-03)
    - duplicates are rejected deterministically
    - §9: ordering is canonical (sorted)
    """
    from keyhole_sdk.capability.namespace import validate_capability_name

    issues: List[PassportIssue] = []
    entries: List[CapabilityEntry] = []
    seen: set = set()

    if not isinstance(raw_caps, list):
        issues.append(PassportIssue(
            file=file_label,
            field="produces",
            reason="NoDeclaredCapabilities",
            repair=map_passport_repair("NoDeclaredCapabilities"),
        ))
        return issues, entries

    for idx, cap in enumerate(raw_caps):
        if not isinstance(cap, str):
            issues.append(PassportIssue(
                file=file_label,
                field=f"produces[{idx}]",
                reason="InvalidCapabilityName",
                repair=map_passport_repair("InvalidCapabilityName"),
            ))
            continue

        result = validate_capability_name(cap)
        if not result.valid:
            repair = map_passport_repair("InvalidCapabilityName")
            if result.suggestion:
                repair = repair + [f"Did you mean: {result.suggestion}?"]
            issues.append(PassportIssue(
                file=file_label,
                field=f"produces[{idx}]",
                reason="InvalidCapabilityName",
                repair=repair,
            ))
            continue

        if cap in seen:
            issues.append(PassportIssue(
                file=file_label,
                field=f"produces[{idx}]",
                reason="DuplicateCapabilityDeclaration",
                repair=map_passport_repair("DuplicateCapabilityDeclaration"),
            ))
            continue

        seen.add(cap)
        entries.append(CapabilityEntry(name=cap))

    # §9: canonical (sorted) ordering
    entries.sort(key=lambda e: e.name)

    return issues, entries
