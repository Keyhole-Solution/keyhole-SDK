"""Capability discovery and resolution data models — SDK-CLIENT-08.

Covers: search requests/results, resolution requests/outcomes,
capability candidates, resolved dependencies, materialization modes,
and repo posture classification.

All models use Pydantic v2 for validation and serialization.
"""

from __future__ import annotations

import enum
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────


class RepoPosture(str, enum.Enum):
    """§6: How the repo relates to Keyhole governance."""
    NATIVE = "native"
    FOREIGN = "foreign"
    INGESTION_BACKED = "ingestion_backed"


class MaterializationMode(str, enum.Enum):
    """§9.3, §13: How resolution results are materialised."""
    ADVISORY = "advisory"
    WRITE = "write"


class ResolutionStatus(str, enum.Enum):
    """Resolution outcome classification."""
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    INCOMPATIBLE = "incompatible"
    NOT_FOUND = "not_found"
    REJECTED = "rejected"
    FAILED = "failed"
    ACCEPTED = "accepted"
    DEFERRED = "deferred"


# ── Search Models ────────────────────────────────────────


class CapabilitySearchRequest(BaseModel):
    """§8.1, §9.1: Shaped search request for the MCP boundary."""
    query: str = Field(..., description="Capability name or namespace prefix.")
    provider: str = Field("", description="Optional provider filter.")
    version: str = Field("", description="Optional version filter.")
    repo_identity: str = Field("", description="Current repo identity for context.")
    repo_posture: RepoPosture = Field(RepoPosture.NATIVE)
    correlation_id: str = Field("")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_payload(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "query": self.query,
            "context": {
                "repo_identity": self.repo_identity,
                "repo_posture": self.repo_posture.value,
            },
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
        }
        if self.provider:
            d["provider"] = self.provider
        if self.version:
            d["version"] = self.version
        return d

    def to_proof_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "provider": self.provider,
            "version": self.version,
            "repo_posture": self.repo_posture.value,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
        }


class CapabilityCandidate(BaseModel):
    """§11.1: A single capability candidate from search results."""
    capability: str = Field(..., description="Full capability name.")
    provider: str = Field("", description="Provider/org name.")
    version: str = Field("", description="Semver version string.")
    visibility: str = Field("public", description="Visibility scope.")
    summary: str = Field("", description="Human-readable summary.")
    digest: str = Field("", description="Immutable content digest if available.")
    matches_inferred_need: bool = Field(
        False,
        description="True when the result matches an inferred need from prior ingestion.",
    )
    already_pinned_locally: bool = Field(
        False,
        description="True when this capability appears in local dependencies.yaml.",
    )

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "capability": self.capability,
            "provider": self.provider,
            "version": self.version,
            "visibility": self.visibility,
        }
        if self.summary:
            d["summary"] = self.summary
        if self.digest:
            d["digest"] = self.digest
        if self.matches_inferred_need:
            d["matches_inferred_need"] = True
        if self.already_pinned_locally:
            d["already_pinned_locally"] = True
        return d


class CapabilitySearchResult(BaseModel):
    """§11: Complete search result with candidates and metadata."""
    query: str = Field("")
    candidates: List[CapabilityCandidate] = Field(default_factory=list)
    total_count: int = Field(0)
    correlation_id: str = Field("")
    is_empty: bool = Field(False)
    next_steps: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    http_status: int = Field(0)
    error_class: str = Field("")
    reason: str = Field("")

    def to_proof_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "total_count": self.total_count,
            "is_empty": self.is_empty,
            "correlation_id": self.correlation_id,
            "http_status": self.http_status,
            "candidate_count": len(self.candidates),
        }


# ── Resolution Models ────────────────────────────────────


class ResolutionRequest(BaseModel):
    """§8.2, §9.2: Shaped resolution request for the MCP boundary."""
    capability: str = Field(..., description="Capability to resolve.")
    provider: str = Field("", description="Optional provider pin.")
    version: str = Field("", description="Optional version pin.")
    repo_identity: str = Field("", description="Current repo identity.")
    repo_posture: RepoPosture = Field(RepoPosture.NATIVE)
    mode: MaterializationMode = Field(MaterializationMode.ADVISORY)
    identity_fingerprint: str = Field("")
    correlation_id: str = Field("")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_payload(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "capability": self.capability,
            "context": {
                "repo_identity": self.repo_identity,
                "repo_posture": self.repo_posture.value,
            },
            "mode": self.mode.value,
            "identity_fingerprint": self.identity_fingerprint,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
        }
        if self.provider:
            d["provider"] = self.provider
        if self.version:
            d["version"] = self.version
        return d

    def to_proof_dict(self) -> Dict[str, Any]:
        return {
            "capability": self.capability,
            "provider": self.provider,
            "version": self.version,
            "repo_posture": self.repo_posture.value,
            "mode": self.mode.value,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
        }


class ResolvedDependency(BaseModel):
    """§12.1: A deterministically resolved dependency entry."""
    capability: str = Field(..., description="Resolved capability name.")
    provider: str = Field(..., description="Resolved provider.")
    version: str = Field("", description="Resolved version.")
    digest: str = Field("", description="Immutable content digest.")
    reason: str = Field("", description="Reason for selection.")

    def to_dependency_entry(self) -> Dict[str, Any]:
        """Produce a deterministic entry suitable for dependencies.yaml."""
        entry: Dict[str, Any] = {
            "capability": self.capability,
            "provider": self.provider,
        }
        if self.version:
            entry["version"] = self.version
        if self.digest:
            entry["digest"] = self.digest
        return entry

    def to_dict(self) -> Dict[str, Any]:
        d = self.to_dependency_entry()
        if self.reason:
            d["reason"] = self.reason
        return d


class ResolutionOutcome(BaseModel):
    """§12, §17: Complete resolution outcome — honest rendering."""
    status: str = Field(..., description="resolved|ambiguous|incompatible|not_found|rejected|failed|accepted|deferred")
    resolved: Optional[ResolvedDependency] = Field(None)
    candidates: List[CapabilityCandidate] = Field(default_factory=list)
    mode: MaterializationMode = Field(MaterializationMode.ADVISORY)
    materialized: bool = Field(False, description="True if written to local artifact.")
    materialized_target: str = Field("", description="Path of the materialised artifact.")
    diff_summary: str = Field("", description="Human-readable diff of the materialization.")
    correlation_id: str = Field("")
    http_status: int = Field(0)
    is_replay: bool = Field(False)
    error_class: str = Field("")
    reason: str = Field("")
    repair_guidance: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    is_local_failure: bool = Field(False)
    response_data: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_resolved(self) -> bool:
        return self.status == "resolved"

    @property
    def is_ambiguous(self) -> bool:
        return self.status == "ambiguous"

    def to_proof_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "status": self.status,
            "mode": self.mode.value,
            "materialized": self.materialized,
            "materialized_target": self.materialized_target,
            "correlation_id": self.correlation_id,
            "http_status": self.http_status,
            "is_replay": self.is_replay,
        }
        if self.resolved:
            d["resolved"] = self.resolved.to_dict()
        if self.candidates:
            d["candidate_count"] = len(self.candidates)
        if self.error_class:
            d["error_class"] = self.error_class
        if self.reason:
            d["reason"] = self.reason
        if self.repair_guidance:
            d["repair_guidance"] = self.repair_guidance
        if self.diff_summary:
            d["diff_summary"] = self.diff_summary
        return d


# ── Helpers ──────────────────────────────────────────────


def compute_resolution_digest(capability: str, provider: str, version: str) -> str:
    """Deterministic digest for a resolved dependency triple."""
    content = f"{capability}:{provider}:{version}"
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
