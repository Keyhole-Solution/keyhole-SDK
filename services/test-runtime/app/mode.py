"""Runtime mode determination and signaling.

The public runtime operates in exactly one of two modes:

- **local-only**: No MCP governance configured. Realization requests execute
  locally without governance gating. Results are NOT auditable upstream and
  do NOT imply Event Spine evidence or governed attestation.

- **governed**: KEYHOLE_MCP_URL and KEYHOLE_MCP_TOKEN are both configured.
  Every POST /realize is gate-checked through the Keyhole MCP governance
  surface before mutating local state.  Governed mode does NOT automatically
  imply canonical promotion — candidate / verification isolation still applies.

Mode must never be silently inferred or switched at runtime.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

RuntimeMode = Literal["local-only", "governed", "misconfigured"]

_MCP_URL: str = os.environ.get("KEYHOLE_MCP_URL", "").rstrip("/")
_MCP_TOKEN: str = os.environ.get("KEYHOLE_MCP_TOKEN", "")


@dataclass(frozen=True)
class ModeStatus:
    """Immutable snapshot of the current runtime mode."""

    mode: RuntimeMode
    mcp_configured: bool
    auditable_upstream: bool
    evidence_disclaimer: str


def resolve_mode() -> ModeStatus:
    """Determine runtime mode from environment configuration.

    This function is deterministic for a given set of environment variables
    and never silently transitions between modes.
    """
    if _MCP_URL and _MCP_TOKEN:
        return ModeStatus(
            mode="governed",
            mcp_configured=True,
            auditable_upstream=True,
            evidence_disclaimer=(
                "Governed mode: realization requests are gated through the "
                "Keyhole MCP governance surface. Upstream evidence may exist "
                "when properly configured. Governed mode does NOT automatically "
                "imply canonical promotion."
            ),
        )
    if _MCP_URL and not _MCP_TOKEN:
        return ModeStatus(
            mode="misconfigured",
            mcp_configured=False,
            auditable_upstream=False,
            evidence_disclaimer=(
                "Misconfigured: KEYHOLE_MCP_URL is set but KEYHOLE_MCP_TOKEN "
                "is missing. Requests will be rejected."
            ),
        )
    return ModeStatus(
        mode="local-only",
        mcp_configured=False,
        auditable_upstream=False,
        evidence_disclaimer=(
            "Local-only mode: results are local-only. No upstream Event Spine "
            "evidence is implied. Local success is valuable for development "
            "but is NOT constitutional proof."
        ),
    )
