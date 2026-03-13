"""Normalized context models for governed context retrieval.

CE-V5-S42-05: Governed Context Retrieval Bootstrap.

These models shape retrieved context into a stable local representation
that downstream consumers can rely on without inspecting raw JSON.

Design rules:
  - Never fabricate missing context.
  - Preserve retrieval metadata for traceability.
  - Tolerate evolving response shapes within contract bounds.
  - Live boundary retrieval remains authoritative; local snapshots
    are convenience artifacts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────
# Run dispatch request / response
# ──────────────────────────────────────────────────────────────

class RunStartRequest(BaseModel):
    """Request payload for ``POST /mcp/v1/runs/start``."""

    run_type: str
    params: Dict[str, Any] = Field(default_factory=dict)


class RunStartResponse(BaseModel):
    """Raw response from a ``POST /mcp/v1/runs/start`` invocation.

    Preserves the full response body so downstream normalization
    can extract participant-relevant fields without losing data.
    """

    run_type: str = ""
    status: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    raw: Dict[str, Any] = Field(default_factory=dict)


# ──────────────────────────────────────────────────────────────
# A) Topology / Platform Shape
# ──────────────────────────────────────────────────────────────

class TopologyInfo(BaseModel):
    """Platform shape and governance model extracted from context."""

    platform_name: str = ""
    governance_model: str = ""
    primary_surfaces: List[str] = Field(default_factory=list)
    runtime_model: str = ""
    deployment_model: str = ""


# ──────────────────────────────────────────────────────────────
# B) Contracts / Interfaces
# ──────────────────────────────────────────────────────────────

class ContractInfo(BaseModel):
    """MCP contract and schema posture from context."""

    mcp_contract: str = ""
    envelope_schema: str = ""
    passport_schema: str = ""
    event_schema: str = ""
    identity_model: str = ""
    charter_model: str = ""
    workspace_model: str = ""


class InterfaceInfo(BaseModel):
    """Participant-relevant interface endpoints from context."""

    endpoints: Dict[str, str] = Field(default_factory=dict)


# ──────────────────────────────────────────────────────────────
# C) Context Access Availability
# ──────────────────────────────────────────────────────────────

class ContextAccessInfo(BaseModel):
    """Implemented context-access surfaces from context."""

    implemented_surfaces: List[str] = Field(default_factory=list)
    declared_count: int = 0
    implemented_count: int = 0


# ──────────────────────────────────────────────────────────────
# D) Participant Guidance
# ──────────────────────────────────────────────────────────────

class GuidanceInfo(BaseModel):
    """Participant guidance slice from context."""

    run_type_discipline: str = ""
    discovery_guidance: str = ""
    gap_workflow_guidance: str = ""
    event_query_guidance: str = ""


# ──────────────────────────────────────────────────────────────
# E) Retrieval Metadata
# ──────────────────────────────────────────────────────────────

class RetrievalMetadata(BaseModel):
    """Metadata from the context retrieval response."""

    run_type: str = ""
    retrieved_at: str = ""
    generated_at: str = ""
    digest: str = ""
    ctx_ref_sha256: str = ""
    correlation_id: str = ""
    server_time: str = ""


# ──────────────────────────────────────────────────────────────
# Top-level Context Snapshot
# ──────────────────────────────────────────────────────────────

class ContextSnapshot(BaseModel):
    """Normalized local representation of retrieved governed context.

    This is the stable model that downstream consumers use.
    It aggregates topology, contracts, interfaces, context-access
    availability, guidance, and retrieval metadata into a single
    participant-facing structure.

    Live boundary retrieval remains authoritative.  This snapshot
    is a convenience artifact — not a replacement for live truth.
    """

    topology: TopologyInfo = Field(default_factory=TopologyInfo)
    contracts: ContractInfo = Field(default_factory=ContractInfo)
    interfaces: InterfaceInfo = Field(default_factory=InterfaceInfo)
    context_access: ContextAccessInfo = Field(default_factory=ContextAccessInfo)
    guidance: GuidanceInfo = Field(default_factory=GuidanceInfo)
    retrieval: RetrievalMetadata = Field(default_factory=RetrievalMetadata)
    raw: Dict[str, Any] = Field(
        default_factory=dict,
        description="Full raw response preserved for traceability.",
    )

    # ── Helper accessors ────────────────────────────────────

    def get_platform_name(self) -> str:
        """Return the platform name from topology."""
        return self.topology.platform_name

    def get_governance_model(self) -> str:
        """Return the governance model from topology."""
        return self.topology.governance_model

    def get_mcp_contract(self) -> str:
        """Return the MCP contract version from contracts."""
        return self.contracts.mcp_contract

    def get_implemented_surfaces(self) -> List[str]:
        """Return the list of implemented context-access surfaces."""
        return list(self.context_access.implemented_surfaces)

    def get_run_type_discipline(self) -> str:
        """Return the run-type discipline guidance."""
        return self.guidance.run_type_discipline

    def get_digest(self) -> str:
        """Return the retrieval digest."""
        return self.retrieval.digest

    def get_correlation_id(self) -> str:
        """Return the retrieval correlation ID."""
        return self.retrieval.correlation_id
