"""Registration readiness assessment — SDK-CLIENT-07 §8, §9.

Client-side preflight that determines whether a repo is
registration-eligible before sending to the MCP boundary.
Follows the fail-local rule: block when problems are obvious locally.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from keyhole_sdk.registration.models import (
    IngestionReference,
    NativeArtifacts,
    RegistrationReadiness,
    RegistrationSource,
)


class ReadinessCheck:
    """Result of a registration readiness assessment."""

    def __init__(
        self,
        readiness: RegistrationReadiness,
        source: RegistrationSource,
        *,
        blockers: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ) -> None:
        self.readiness = readiness
        self.source = source
        self.blockers: List[str] = blockers or []
        self.warnings: List[str] = warnings or []

    @property
    def can_proceed(self) -> bool:
        """Whether registration can proceed (no blockers)."""
        return len(self.blockers) == 0

    @property
    def preflight_status(self) -> str:
        return "PASS" if self.can_proceed else "FAIL"

    def to_dict(self) -> dict:
        return {
            "readiness": self.readiness.value,
            "source": self.source.value,
            "preflight_status": self.preflight_status,
            "blockers": self.blockers,
            "warnings": self.warnings,
        }


def assess_readiness(
    *,
    repo_path: Path,
    has_auth: bool,
    native_artifacts: Optional[NativeArtifacts] = None,
    ingestion_ref: Optional[IngestionReference] = None,
    from_ingest: str = "",
) -> ReadinessCheck:
    """Assess registration readiness for a repository (§8, §9).

    Determines the registration source and readiness state based on
    locally verifiable conditions. This is client-side preflight —
    not canonical server truth.

    Args:
        repo_path: Resolved path to the target repository.
        has_auth: Whether the user has a valid auth session.
        native_artifacts: Loaded native Keyhole artifacts, if any.
        ingestion_ref: Prior ingestion reference, if available.
        from_ingest: Explicit ingestion ID from --from-ingest flag.

    Returns:
        ReadinessCheck with readiness state, source, and any blockers.
    """
    blockers: List[str] = []
    warnings: List[str] = []

    # §8.1: Required baseline — auth
    if not has_auth:
        blockers.append("Not authenticated. Run: keyhole login")

    # §8.1: Required baseline — path
    if not repo_path.is_dir():
        blockers.append(f"Repository path does not exist or is not a directory: {repo_path}")

    # Determine source: explicit --from-ingest overrides native detection
    if from_ingest or ingestion_ref:
        return _assess_ingestion_readiness(
            blockers=blockers,
            warnings=warnings,
            ingestion_ref=ingestion_ref,
            from_ingest=from_ingest,
        )

    # Check for native artifacts
    if native_artifacts and native_artifacts.has_keyhole:
        return _assess_native_readiness(
            blockers=blockers,
            warnings=warnings,
            native_artifacts=native_artifacts,
        )

    # No native artifacts and no ingestion ref — not ready
    if not blockers:
        blockers.append(
            "No Keyhole scaffold and no ingestion reference found. "
            "Run: keyhole ingest . — then: keyhole repo register --from-ingest <id>"
        )

    return ReadinessCheck(
        readiness=RegistrationReadiness.NOT_READY,
        source=RegistrationSource.NATIVE,
        blockers=blockers,
        warnings=warnings,
    )


def _assess_native_readiness(
    *,
    blockers: List[str],
    warnings: List[str],
    native_artifacts: NativeArtifacts,
) -> ReadinessCheck:
    """Assess readiness for a Keyhole-native repo (§8.2)."""
    if not native_artifacts.has_governance_contract:
        warnings.append(
            "governance_contract.yaml not found. Registration may proceed "
            "but the server may request it later."
        )
    if not native_artifacts.has_capability_passport:
        warnings.append(
            "capability_passport.yaml not found. "
            "Generate or repair the capability passport for full alignment."
        )

    if blockers:
        return ReadinessCheck(
            readiness=RegistrationReadiness.NOT_READY,
            source=RegistrationSource.NATIVE,
            blockers=blockers,
            warnings=warnings,
        )

    if native_artifacts.artifact_count >= 3:
        return ReadinessCheck(
            readiness=RegistrationReadiness.NATIVE_READY,
            source=RegistrationSource.NATIVE,
            warnings=warnings,
        )

    return ReadinessCheck(
        readiness=RegistrationReadiness.PARTIALLY_READY,
        source=RegistrationSource.NATIVE,
        warnings=warnings,
    )


def _assess_ingestion_readiness(
    *,
    blockers: List[str],
    warnings: List[str],
    ingestion_ref: Optional[IngestionReference],
    from_ingest: str,
) -> ReadinessCheck:
    """Assess readiness for an ingestion-backed registration (§8.3)."""
    # §8.3: Must have a valid ingestion reference
    if not ingestion_ref and not from_ingest:
        blockers.append(
            "Ingestion-backed registration requires an ingestion reference. "
            "Run: keyhole ingest . — then --from-ingest <id>."
        )
        return ReadinessCheck(
            readiness=RegistrationReadiness.NOT_READY,
            source=RegistrationSource.INGESTION,
            blockers=blockers,
            warnings=warnings,
        )

    if ingestion_ref:
        posture = ingestion_ref.compatibility_posture
        if posture == "foreign":
            warnings.append(
                "Compatibility posture is 'foreign'. "
                "Registration may be accepted but alignment guidance is recommended."
            )

    if blockers:
        return ReadinessCheck(
            readiness=RegistrationReadiness.NOT_READY,
            source=RegistrationSource.INGESTION,
            blockers=blockers,
            warnings=warnings,
        )

    return ReadinessCheck(
        readiness=RegistrationReadiness.INGESTION_READY,
        source=RegistrationSource.INGESTION,
        warnings=warnings,
    )
