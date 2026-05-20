"""MCP response envelope parser — shared across all boundary clients.

The MCP boundary wraps all authenticated responses in a standard envelope::

    {
        "ok": true,
        "data": { ... },
        "error": null,
        "keyhole": { "contract": "mcp/v1", ... },
        "meta": null,
    }

This module provides a single canonical parsing path so that individual
surface clients (whoami, capabilities, events, memory, etc.) do not
each re-implement ad-hoc unwrapping logic.

Usage::

    from keyhole_sdk.envelope import unwrap_mcp_envelope

    raw = resp.json()
    payload = unwrap_mcp_envelope(raw)
    # payload is the inner ``data`` dict, or ``raw`` if not an envelope.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def unwrap_mcp_envelope(raw: Any) -> Dict[str, Any]:
    """Extract the ``data`` payload from an MCP response envelope.

    If *raw* is an MCP envelope (``{"ok": ..., "data": {...}, ...}``),
    returns the ``data`` dict.  Otherwise returns *raw* unchanged so
    that callers work transparently against both wrapped and unwrapped
    shapes.

    This function never raises; if the shape is unexpected, it returns
    *raw* as-is.
    """
    if not isinstance(raw, dict):
        return raw
    if "ok" in raw and "data" in raw and isinstance(raw["data"], dict):
        return raw["data"]
    return raw


def unwrap_identity(envelope_data: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten an unwrapped whoami ``data`` payload into a flat identity dict.

    The ``data`` section of a ``/mcp/v1/whoami`` response has nested
    structure::

        {
            "identity": {"user_id": ..., "tenant_id": ..., ...},
            "cohort": {"cohort_id": ..., ...},
            "workspace": {"workspace_ref": ...},
            "plan": "free",
            "limits": {...},
            "context_overlay": {"governance_rules": {...}, ...},
            ...
        }

    This function collapses those nested groups into a single flat dict
    suitable for ``WhoamiResponse.model_validate()``.

    If *envelope_data* already looks flat (has ``user_id`` at top level),
    it is returned unchanged.
    """
    if not isinstance(envelope_data, dict):
        return envelope_data

    # Already flat — nothing to do.
    if "user_id" in envelope_data:
        return envelope_data

    flat: Dict[str, Any] = {}

    # identity.*
    identity = envelope_data.get("identity")
    if isinstance(identity, dict):
        flat.update(identity)

    # SDK-CLIENT-29: preserve server-resolved actor envelope verbatim.
    # Server is the only authority for actor truth.  The client must
    # never invent this structure.
    actor_envelope = envelope_data.get("actor_envelope")
    if isinstance(actor_envelope, dict):
        flat["actor_envelope"] = actor_envelope

    # Top-level scalars
    for key in ("plan", "limits", "scopes"):
        val = envelope_data.get(key)
        if val is not None:
            flat.setdefault(key, val)

    # cohort.cohort_id
    cohort = envelope_data.get("cohort")
    if isinstance(cohort, dict):
        flat.setdefault("cohort_id", cohort.get("cohort_id"))

    # workspace.workspace_ref
    workspace = envelope_data.get("workspace")
    if isinstance(workspace, dict):
        flat.setdefault("workspace_id", workspace.get("workspace_ref"))

    # Derive mode from governance_rules when not already set by identity
    if "mode" not in flat:
        governance = _deep_get(envelope_data, "context_overlay", "governance_rules")
        if isinstance(governance, dict):
            flat["mode"] = "shadow" if governance.get("noncanonical") else "real"

    return flat


def _deep_get(d: Dict[str, Any], *keys: str) -> Any:
    """Traverse nested dicts by key path, returning ``None`` on miss."""
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)  # type: ignore[assignment]
    return d
