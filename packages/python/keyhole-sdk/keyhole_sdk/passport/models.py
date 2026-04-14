"""Capability passport models — SDK-CLIENT-05.

§10: Canonical transport-safe passport shape.
§11: Deterministic serialization contract.
§12: Transport safety contract (no secrets, no absolute paths).
"""

from __future__ import annotations

import enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Status / readiness enums ──────────────────────────────────────────────────


class PassportStatus(str, enum.Enum):
    """Top-level generation outcome."""
    GENERATED = "generated"
    REJECTED = "rejected"


class PassportReadiness(str, enum.Enum):
    """Repo passport-generation readiness assessment.

    §5: The client must distinguish native governed repos from foreign or
    partially-aligned repos.
    """
    READY = "ready"                    # Native governed → authoritative generation lawful
    PARTIALLY_ALIGNED = "partially_aligned"  # Has some Keyhole files but not fully native
    NOT_READY = "not_ready"            # Missing declared capabilities / repo identity
    FOREIGN = "foreign"                # No Keyhole governance files


# ── Per-capability entry in the passport ─────────────────────────────────────


class CapabilityEntry(BaseModel):
    """§10 — One declared capability in the passport.

    §9: Only declared capabilities are included. Inferred-only capabilities
    are not included.
    """
    name: str
    visibility: str = "private"
    status: str = "declared"


# ── Passport shape sections ───────────────────────────────────────────────────


class PassportRepo(BaseModel):
    """§10: Repo identity section."""
    repo_name: str = ""
    repo_id: str = ""
    owner: str = ""


class PassportIdentity(BaseModel):
    """§10: Optional identity section (tenant/org when legitimately known)."""
    tenant_id: str = ""
    org_id: str = ""


class PassportLineage(BaseModel):
    """§14: Lineage-ready material for later server verification and linking.

    The client does not finalize lineage — it only emits enough for the
    server to do so.
    """
    parent_repo: str = ""
    parent_passport_digest: str = ""


class PassportProof(BaseModel):
    """§18: Reference to any local proof artifact supporting this passport."""
    local_proof_ref: str = ""


class PassportTransport(BaseModel):
    """§10: Transport metadata (generated_at kept for human readability;
    NOT included in the digest basis — see §11).
    """
    generated_at: str = ""
    digest: str = ""


# ── The full portable passport artifact ──────────────────────────────────────


class CapabilityPassportArtifact(BaseModel):
    """§10 — Canonical transport-safe passport artifact.

    §11: Deterministic serialization. §12: No secrets or absolute paths.
    """
    schema_version: str = "v1"
    artifact_kind: str = "capability_passport"

    repo: PassportRepo = Field(default_factory=PassportRepo)
    identity: PassportIdentity = Field(default_factory=PassportIdentity)
    capabilities: List[CapabilityEntry] = Field(default_factory=list)
    lineage: PassportLineage = Field(default_factory=PassportLineage)
    proof: PassportProof = Field(default_factory=PassportProof)
    transport: PassportTransport = Field(default_factory=PassportTransport)

    def to_payload(self) -> Dict[str, Any]:
        """§12: Transport-safe serialization — stable field ordering."""
        return {
            "schema_version": self.schema_version,
            "artifact_kind": self.artifact_kind,
            "repo": {
                "repo_name": self.repo.repo_name,
                "repo_id": self.repo.repo_id,
                "owner": self.repo.owner,
            },
            "identity": {
                "tenant_id": self.identity.tenant_id,
                "org_id": self.identity.org_id,
            },
            "capabilities": [
                {"name": c.name, "visibility": c.visibility, "status": c.status}
                for c in self.capabilities
            ],
            "lineage": {
                "parent_repo": self.lineage.parent_repo,
                "parent_passport_digest": self.lineage.parent_passport_digest,
            },
            "proof": {
                "local_proof_ref": self.proof.local_proof_ref,
            },
            "transport": {
                "generated_at": self.transport.generated_at,
                "digest": self.transport.digest,
            },
        }


# ── Issue and result models ───────────────────────────────────────────────────


class PassportIssue(BaseModel):
    """Generation failure detail with repair guidance."""
    file: str = ""
    field: str = ""
    reason: str
    repair: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "field": self.field,
            "reason": self.reason,
            "repair": self.repair,
        }


class PassportGenerationResult(BaseModel):
    """§16/§17 — Structured result of a generation attempt.

    Both success and failure paths return this — failure has status=REJECTED,
    success has status=GENERATED with artifact populated.
    """
    status: PassportStatus
    readiness: PassportReadiness
    repo: str = ""
    repo_path: str = ""
    capability_count: int = 0
    digest: str = ""
    artifact_path: str = ""         # Absolute path written, or "" if not written.
    artifact: Optional[CapabilityPassportArtifact] = None
    issues: List[PassportIssue] = Field(default_factory=list)
    source_files: List[str] = Field(default_factory=list)

    @property
    def generated(self) -> bool:
        return self.status == PassportStatus.GENERATED

    @property
    def rejected(self) -> bool:
        return self.status == PassportStatus.REJECTED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "readiness": self.readiness.value,
            "repo": self.repo,
            "repo_path": self.repo_path,
            "capability_count": self.capability_count,
            "digest": self.digest,
            "artifact_path": self.artifact_path,
            "artifact": self.artifact.to_payload() if self.artifact else None,
            "issues": [i.to_dict() for i in self.issues],
            "source_files": self.source_files,
        }
