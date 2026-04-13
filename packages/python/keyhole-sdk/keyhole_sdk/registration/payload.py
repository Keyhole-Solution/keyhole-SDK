"""Registration payload builder — SDK-CLIENT-07 §10.

Constructs a deterministic registration payload from known repo truth.
Same repo state + same registration source → same payload shape.

Never invents missing artifact fields.
Never silently mutates repo declarations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import keyhole_sdk

from keyhole_sdk.registration.models import (
    IngestionReference,
    NativeArtifacts,
    RegistrationPayload,
    RegistrationReadiness,
    RegistrationSource,
    compute_path_digest,
    compute_repo_digest,
)
from keyhole_sdk.registration.readiness import ReadinessCheck


def build_registration_payload(
    *,
    repo_path: Path,
    readiness_check: ReadinessCheck,
    native_artifacts: Optional[NativeArtifacts] = None,
    ingestion_ref: Optional[IngestionReference] = None,
    shadow: bool = False,
    correlation_id: str = "",
    command: str = "keyhole repo register",
) -> RegistrationPayload:
    """Build a deterministic registration payload (§10).

    Args:
        repo_path: Resolved absolute path to the repository.
        readiness_check: Result of assess_readiness().
        native_artifacts: Loaded native artifacts, if any.
        ingestion_ref: Ingestion reference, if any.
        shadow: Whether this is a shadow registration.
        correlation_id: Correlation ID for proof tracing.
        command: CLI command label.

    Returns:
        A RegistrationPayload ready for wire-format submission.
    """
    repo_name = repo_path.name
    path_digest = compute_path_digest(str(repo_path))
    source = readiness_check.source

    # Build repo digest from deterministic identity inputs
    extra_parts = []
    if ingestion_ref:
        extra_parts.append(ingestion_ref.ingest_id)
    if native_artifacts and native_artifacts.has_keyhole:
        extra_parts.append("native")
    repo_digest = compute_repo_digest(repo_name, source.value, ":".join(extra_parts))

    return RegistrationPayload(
        repo_name=repo_name,
        path_digest=path_digest,
        repo_digest=repo_digest,
        registration_source=source,
        native_artifacts=native_artifacts if source == RegistrationSource.NATIVE else None,
        ingestion=ingestion_ref if source == RegistrationSource.INGESTION else None,
        preflight_status=readiness_check.preflight_status,
        readiness=readiness_check.readiness,
        shadow=shadow,
        cli_version=keyhole_sdk.__version__,
        command=command,
        correlation_id=correlation_id,
    )
