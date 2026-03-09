from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RuntimeIdentity(BaseModel):
    """Runtime identity and declared capabilities."""

    runtime_id: str
    runtime_name: str
    runtime_version: str
    environment: str
    capabilities: list[str]
    governance_mode: str = "local-only"
    """Governance mode reported by the runtime: ``"governed"``, ``"local-only"``, or ``"misconfigured"``."""


class RuntimeState(BaseModel):
    """Runtime-local state view."""

    current_digest: str | None = None
    realized_digests: list[str] = Field(default_factory=list)
    updated_at: datetime


class RealizationRequest(BaseModel):
    """Public realization request model for the test runtime."""

    candidate_digest: str
    payload: dict[str, Any] = Field(default_factory=dict)


class RealizationReceipt(BaseModel):
    """Public realization receipt returned by the test runtime."""

    digest: str
    status: str
    message: str = ""
    realized_at: datetime
    result: str = ""
    """Same value as *status* — included for bridge-envelope compatibility."""
    governance_verdict: str = "LOCAL_ONLY"
    """``"LOCAL_ONLY"`` when running without MCP governance; ``"APPROVED"`` when governed."""
    version: str = ""
    """Runtime version at time of realization."""
    pointer: str = ""
    """Local pointer state after realization (e.g. ``"v1"``, ``"v2"``)."""