"""`keyhole surfaces` — surface negotiation and compatibility inspection.

SDK-CLIENT-21: Surface Negotiation and Compatibility Guardrails.

Fetches live server capabilities, classifies surfaces as required /
optional / transitional, evaluates command compatibility, and renders
an inspectable negotiation result.

§5  Scope: negotiation against GET /mcp/v1/capabilities.
§13 Command UX: show server posture, negotiated surfaces, repair steps.
§12 Local artifact: write compatibility/ artifacts to state_dir.
§14 Fail-closed: BLOCKED posture returns EXIT_CONTRACT_FAILURE.
§15 Graceful degradation: DEGRADED posture returns EXIT_SUCCESS.

Negotiation is repo-neutral (§6): it describes environment truth,
not whether a local repo "deserves" a surface.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from keyhole_sdk.discovery.client import CapabilitiesClient
from keyhole_sdk.discovery.models import CapabilitiesResult
from keyhole_sdk.exceptions import SchemaError, TransportError
from keyhole_sdk.negotiation import (
    NegotiationResult,
    NegotiationStatus,
    evaluate_all_commands,
    map_negotiation_repair,
    negotiate,
    write_negotiation_artifacts,
)

from keyhole_cli.result import (
    EXIT_CONTRACT_FAILURE,
    EXIT_RUNTIME_UNAVAILABLE,
    EXIT_SUCCESS,
    CommandResult,
)

_COMMAND_LABEL = "keyhole surfaces"
_DEFAULT_MCP_URL = "https://mcp.keyholesolution.com"


def run_surfaces(
    *,
    mcp_url: str = _DEFAULT_MCP_URL,
    keyhole_home: str = "",
    state_dir: str = "",
    refresh: bool = False,
) -> CommandResult:
    """Execute ``keyhole surfaces``.

    §9 Negotiation trigger: fetches capabilities, normalizes, evaluates,
    caches.

    §13 Renders: server version, negotiated surface set, missing required,
    missing optional, transitional, resulting posture, repair steps.

    §12 Artifacts: writes capabilities_raw.json, negotiation_result.json,
    summary.md to <state_dir>/compatibility/.

    §14 Fail-closed: if any required surface is missing, exit code is
    EXIT_CONTRACT_FAILURE — but the result is still returned so the
    builder can read the full negotiation report.

    §15 Graceful degradation: DEGRADED posture exits 0 (success) with
    reduced-capability messaging.

    §6  Repo-neutral: this command never reads local repo files.
    """
    # ── Fetch capabilities from the live boundary (§10) ──────────────────
    caps: Optional[CapabilitiesResult] = None
    try:
        with CapabilitiesClient(base_url=mcp_url) as client:
            caps = client.fetch()
    except (TransportError, SchemaError) as exc:
        return CommandResult(
            command=_COMMAND_LABEL,
            success=False,
            exit_code=EXIT_RUNTIME_UNAVAILABLE,
            summary=f"Cannot reach MCP boundary at {mcp_url!r}: {exc}",
            data={
                "error_class": "TransportFailure",
                "mcp_url": mcp_url,
                "detail": str(exc),
            },
            next_steps=map_negotiation_repair("transport_failure"),
        )
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            command=_COMMAND_LABEL,
            success=False,
            exit_code=EXIT_RUNTIME_UNAVAILABLE,
            summary=f"Unexpected error fetching capabilities: {exc}",
            data={
                "error_class": "UnexpectedFailure",
                "mcp_url": mcp_url,
                "detail": str(exc),
            },
            next_steps=map_negotiation_repair("transport_failure"),
        )

    # ── Negotiate (§9 §11) ────────────────────────────────────────────────
    result: NegotiationResult = negotiate(caps)

    # ── Write local artifacts (§12) ───────────────────────────────────────
    state = _resolve_state_dir(state_dir, keyhole_home)
    if state:
        try:
            write_negotiation_artifacts(state, caps, result)
        except Exception:  # noqa: BLE001
            pass  # artifact writing is fire-and-continue; never blocks the result

    # ── Determine exit code (§14 §15) ─────────────────────────────────────
    # BLOCKED → fail closed (EXIT_CONTRACT_FAILURE)
    # DEGRADED → success with reduced UX  (EXIT_SUCCESS)
    # COMPATIBLE → full success             (EXIT_SUCCESS)
    is_blocked = result.is_blocked()
    exit_code = EXIT_CONTRACT_FAILURE if is_blocked else EXIT_SUCCESS

    return CommandResult(
        command=_COMMAND_LABEL,
        success=not is_blocked,
        exit_code=exit_code,
        summary=_build_summary(result),
        data=result.to_dict(),
        next_steps=_build_next_steps(result),
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

def _resolve_state_dir(state_dir: str, keyhole_home: str) -> str:
    """Return a writable state directory path, or empty string if none configured."""
    if state_dir:
        return state_dir
    if keyhole_home:
        return str(Path(keyhole_home) / "state")
    env = os.environ.get("KEYHOLE_STATE_DIR", "").strip()
    if env:
        return env
    return ""


def _build_summary(result: NegotiationResult) -> str:
    """Build a multi-line human-readable negotiation summary (§13)."""
    status_str = result.compatibility.status.value.upper()
    lines = [
        f"Surface Negotiation: {status_str}",
        f"Server: {result.server_version or '(unknown)'}",
        f"Fingerprint: {result.surface_fingerprint or '(none)'}",
    ]

    if result.compatibility.required_missing:
        lines.append(
            "Required missing: " + ", ".join(result.compatibility.required_missing)
        )
    if result.compatibility.optional_missing:
        lines.append(
            "Optional missing: " + ", ".join(result.compatibility.optional_missing)
        )
    if result.compatibility.transitional:
        lines.append(
            "Transitional: " + ", ".join(result.compatibility.transitional)
        )

    return "\n".join(lines)


def _build_next_steps(result: NegotiationResult) -> List[str]:
    """Build repair steps from missing surfaces (§14 §15)."""
    steps: List[str] = []
    seen: set = set()

    for surface in result.compatibility.required_missing:
        for step in map_negotiation_repair(surface):
            if step not in seen:
                seen.add(step)
                steps.append(step)

    # For optional missing, add brief pointers (don't flood the output)
    if result.compatibility.optional_missing and not result.compatibility.required_missing:
        for surface in result.compatibility.optional_missing[:3]:  # limit to 3
            for step in map_negotiation_repair(surface)[:1]:  # one step each
                if step not in seen:
                    seen.add(step)
                    steps.append(step)

    return steps
