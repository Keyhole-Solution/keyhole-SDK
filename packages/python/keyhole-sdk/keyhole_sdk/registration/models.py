"""Registration data models — SDK-CLIENT-07 §6, §9, §10, §11, §17.

Covers: registration source, readiness, native artifacts, ingestion
reference, payload, identity binding, and registration outcome.
All models use Pydantic v2 for validation and serialization.
"""

from __future__ import annotations

import enum
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────


class RegistrationSource(str, enum.Enum):
    """§6: How the repo arrived at registration."""

    NATIVE = "native"
    INGESTION = "ingestion"


class RegistrationReadiness(str, enum.Enum):
    """§9: Client-side registration readiness assessment."""

    NATIVE_READY = "native_ready"
    INGESTION_READY = "ingestion_ready"
    PARTIALLY_READY = "partially_ready"
    NOT_READY = "not_ready"


# ── Native Artifact Models ───────────────────────────────


class NativeArtifacts(BaseModel):
    """§6.1: Declaration artifacts from a Keyhole-native repo.

    These are loaded from local files. Null means the file was not found.
    """

    keyhole: Optional[Dict[str, Any]] = Field(
        None, description="Contents of keyhole.yaml, if present.",
    )
    governance_contract: Optional[Dict[str, Any]] = Field(
        None, description="Contents of governance_contract.yaml, if present.",
    )
    capability_passport: Optional[Dict[str, Any]] = Field(
        None, description="Contents of capability_passport.yaml, if present.",
    )
    dependencies: Optional[Dict[str, Any]] = Field(
        None, description="Contents of dependencies.yaml, if present.",
    )

    @property
    def has_keyhole(self) -> bool:
        return self.keyhole is not None

    @property
    def has_governance_contract(self) -> bool:
        return self.governance_contract is not None

    @property
    def has_capability_passport(self) -> bool:
        return self.capability_passport is not None

    @property
    def artifact_count(self) -> int:
        return sum(1 for v in [
            self.keyhole, self.governance_contract,
            self.capability_passport, self.dependencies,
        ] if v is not None)

    def to_snapshot(self) -> Dict[str, Any]:
        """Snapshot dict for proof — includes what was present and absent."""
        return {
            "keyhole": self.keyhole,
            "governance_contract": self.governance_contract,
            "capability_passport": self.capability_passport,
            "dependencies": self.dependencies,
            "artifact_count": self.artifact_count,
        }


# ── Ingestion Reference ─────────────────────────────────


class IngestionReference(BaseModel):
    """§6.2: Reference to a prior ingestion result.

    Used for ingestion-backed registration of foreign repos.
    """

    ingest_id: str = Field(..., description="Ingestion ID or correlation ID from prior ingest.")
    compatibility_posture: str = Field(
        "foreign", description="Compatibility posture from ingestion.",
    )
    repo_identity: str = Field("", description="Repo identity as observed during ingestion.")
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    has_keyhole_scaffold: bool = Field(False)
    ingestion_timestamp: str = Field("")

    def to_snapshot(self) -> Dict[str, Any]:
        """Snapshot dict for proof."""
        return self.model_dump(mode="json")


# ── Registration Payload ─────────────────────────────────


class RegistrationPayload(BaseModel):
    """§10: Deterministic registration payload for MCP boundary.

    Assembled from known local and observed repo truth.
    Never invents missing governance state.
    """

    repo_name: str = Field(..., description="Repo name or directory name.")
    path_digest: str = Field("", description="SHA-256 digest of the absolute repo path.")
    repo_digest: str = Field("", description="SHA-256 of the repo identity inputs.")
    registration_source: RegistrationSource = Field(
        ..., description="Native or ingestion-backed.",
    )

    # §6.1: Native artifacts, if present
    native_artifacts: Optional[NativeArtifacts] = Field(None)

    # §6.2: Ingestion reference, if present
    ingestion: Optional[IngestionReference] = Field(None)

    # §9: Preflight readiness
    preflight_status: str = Field("PASS")
    readiness: RegistrationReadiness = Field(RegistrationReadiness.NOT_READY)

    # §19: Shadow mode
    shadow: bool = Field(False)

    # Client metadata
    cli_version: str = Field("")
    command: str = Field("keyhole repo register")

    # Correlation
    correlation_id: str = Field("")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )

    def to_payload(self) -> Dict[str, Any]:
        """Wire-format payload for transport dispatch."""
        d: Dict[str, Any] = {
            "repo": {
                "name": self.repo_name,
                "path_digest": self.path_digest,
                "repo_digest": self.repo_digest,
                "registration_source": self.registration_source.value,
            },
            "native_artifacts": (
                self.native_artifacts.to_snapshot()
                if self.native_artifacts else None
            ),
            "ingestion": (
                self.ingestion.to_snapshot()
                if self.ingestion else None
            ),
            "preflight": {
                "status": self.preflight_status,
                "readiness": self.readiness.value,
            },
            "shadow": self.shadow,
            "client": {
                "command": self.command,
                "cli_version": self.cli_version,
            },
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
        }
        return d

    def to_proof_dict(self) -> Dict[str, Any]:
        """Proof-safe serialization — no local paths."""
        return {
            "repo_name": self.repo_name,
            "path_digest": self.path_digest,
            "repo_digest": self.repo_digest,
            "registration_source": self.registration_source.value,
            "readiness": self.readiness.value,
            "shadow": self.shadow,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
        }


# ── Registration Request ─────────────────────────────────


class RegistrationRequest(BaseModel):
    """Shaped request for the registration boundary endpoint."""

    payload: RegistrationPayload
    identity_fingerprint: str = Field("")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )

    def to_payload(self) -> Dict[str, Any]:
        """Wire-format dict for transport dispatch."""
        return {
            "registration": self.payload.to_payload(),
            "identity_fingerprint": self.identity_fingerprint,
            "timestamp": self.timestamp,
        }

    def to_proof_dict(self) -> Dict[str, Any]:
        """Proof-safe serialization."""
        return {
            "payload_summary": self.payload.to_proof_dict(),
            "identity_fingerprint": self.identity_fingerprint,
            "timestamp": self.timestamp,
        }


# ── Identity Binding ─────────────────────────────────────


class IdentityBinding(BaseModel):
    """§11: Server-resolved identity binding from registration."""

    tenant_id: str = Field("")
    org_id: str = Field("")
    user_id: str = Field("")
    cohort_id: str = Field("")
    worker_id: str = Field("")
    repo_id: str = Field("")
    workspace_id: str = Field("")
    origin: str = Field("")
    purpose: str = Field("")

    def to_dict(self) -> Dict[str, Any]:
        """Serialization for proof and display."""
        d: Dict[str, Any] = {}
        for field_name in [
            "tenant_id", "org_id", "user_id", "cohort_id",
            "worker_id", "repo_id", "workspace_id", "origin", "purpose",
        ]:
            val = getattr(self, field_name, "")
            if val:
                d[field_name] = val
        return d


# ── Registration Outcome ─────────────────────────────────


class RegistrationOutcome(BaseModel):
    """Complete registration outcome — honest rendering (§13, §17).

    Preserves the distinction between:
    - declared native truth
    - observed ingestion facts
    - server-resolved registration
    """

    status: str = Field(
        ...,
        description="Outcome: success, accepted, deferred, replayed, rejected, failed.",
    )
    registration_id: Optional[str] = Field(
        None, description="Server-assigned registration/repo ID.",
    )
    repo_name: str = Field("")
    registration_source: RegistrationSource = Field(RegistrationSource.NATIVE)
    readiness: RegistrationReadiness = Field(RegistrationReadiness.NOT_READY)
    shadow: bool = Field(False)
    correlation_id: str = Field("")
    is_replay: bool = Field(False, description="Whether this was a replayed idempotent outcome.")

    # §11: Identity binding from server
    identity_binding: Optional[IdentityBinding] = Field(None)

    # Transport/proof metadata
    http_status: int = Field(0)
    response_data: Dict[str, Any] = Field(default_factory=dict)

    # Error state
    error_class: str = Field("")
    reason: str = Field("")
    repair_guidance: List[str] = Field(default_factory=list)
    is_local_failure: bool = Field(False)

    # Warnings and next steps from server
    warnings: List[str] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)

    def to_proof_dict(self) -> Dict[str, Any]:
        """Proof-safe rendering of the outcome."""
        d: Dict[str, Any] = {
            "status": self.status,
            "repo_name": self.repo_name,
            "registration_source": self.registration_source.value,
            "readiness": self.readiness.value,
            "shadow": self.shadow,
            "correlation_id": self.correlation_id,
            "is_replay": self.is_replay,
            "http_status": self.http_status,
        }
        if self.registration_id:
            d["registration_id"] = self.registration_id
        if self.identity_binding:
            d["identity_binding"] = self.identity_binding.to_dict()
        if self.error_class:
            d["error_class"] = self.error_class
        if self.reason:
            d["reason"] = self.reason
        if self.repair_guidance:
            d["repair_guidance"] = self.repair_guidance
        if self.warnings:
            d["warnings"] = self.warnings
        if self.suggested_actions:
            d["suggested_actions"] = self.suggested_actions
        return d


# ── Helpers ──────────────────────────────────────────────


def compute_path_digest(path: str) -> str:
    """Compute a stable SHA-256 digest of a path string."""
    return "sha256:" + hashlib.sha256(path.encode("utf-8")).hexdigest()


def compute_repo_digest(repo_name: str, source: str, extra: str = "") -> str:
    """Compute a deterministic repo identity digest."""
    content = f"{repo_name}:{source}:{extra}"
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
