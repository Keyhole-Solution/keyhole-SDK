"""Deterministic dependency resolver — SDK-CLIENT-08 §8.2, §12, §16.

Shapes a resolution request and submits it to the MCP boundary.
Classifies the outcome as resolved, ambiguous, incompatible,
not-found, rejected, failed, accepted, or deferred.

Fail-closed: if ambiguity remains, the client does NOT silently
pick a winner — it returns an ambiguous outcome with repair guidance.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from keyhole_sdk.capability.models import (
    CapabilityCandidate,
    MaterializationMode,
    ResolutionOutcome,
    ResolutionRequest,
    ResolvedDependency,
)
from keyhole_sdk.transport.client import GovernedTransport, TransportResult


def submit_resolution(
    *,
    transport: GovernedTransport,
    request: ResolutionRequest,
) -> ResolutionOutcome:
    """Submit a deterministic resolution request to the MCP boundary.

    Returns a :class:`ResolutionOutcome`.  Fail-closed on ambiguity (§8.3).
    """
    try:
        result: TransportResult = transport.execute(
            "POST",
            "/mcp/v1/capabilities/resolve",
            operation_name="capability.resolve",
            json=request.to_payload(),
        )
    except Exception as exc:
        return _handle_resolution_exception(exc, request)

    return _classify_resolution(result, request)


def _classify_resolution(
    result: TransportResult,
    request: ResolutionRequest,
) -> ResolutionOutcome:
    """Classify a boundary response into a deterministic resolution outcome."""
    data = result.data
    status_code = result.status_code
    server_status = data.get("status", "").lower()

    base_kwargs: Dict[str, Any] = {
        "mode": request.mode,
        "correlation_id": request.correlation_id,
        "http_status": status_code,
        "response_data": data,
        "warnings": data.get("warnings", []),
        "is_replay": data.get("is_replay", data.get("replayed", False)),
    }

    # ── Error responses ──
    if status_code >= 400:
        return _classify_error(data, status_code, request, base_kwargs)

    # ── Accepted / deferred (async) ──
    if status_code == 202 or server_status in ("accepted", "pending"):
        return ResolutionOutcome(status="accepted", **base_kwargs)
    if server_status == "deferred":
        return ResolutionOutcome(status="deferred", **base_kwargs)

    # ── Ambiguous (fail-closed) ──
    if server_status == "ambiguous":
        candidates = _parse_candidates(data.get("candidates", []))
        guidance = _ambiguity_repair(request, candidates)
        return ResolutionOutcome(
            status="ambiguous",
            candidates=candidates,
            repair_guidance=guidance,
            **base_kwargs,
        )

    # ── Incompatible ──
    if server_status == "incompatible":
        candidates = _parse_candidates(data.get("candidates", []))
        return ResolutionOutcome(
            status="incompatible",
            candidates=candidates,
            reason=data.get("reason", "No compatible provider found."),
            repair_guidance=data.get("repair_guidance", [
                "Inspect candidate providers: keyhole search " + request.capability,
                "Refine version or provider constraints.",
            ]),
            **base_kwargs,
        )

    # ── Not found ──
    if server_status == "not_found":
        return ResolutionOutcome(
            status="not_found",
            reason=data.get("reason", f"Capability '{request.capability}' not found."),
            repair_guidance=[
                f"Check spelling: '{request.capability}'.",
                f"Try: keyhole search {request.capability} — to discover candidates.",
            ],
            **base_kwargs,
        )

    # ── Resolved ──
    resolved_data = data.get("resolved", data)
    resolved = ResolvedDependency(
        capability=resolved_data.get("capability", request.capability),
        provider=resolved_data.get("provider", ""),
        version=resolved_data.get("version", ""),
        digest=resolved_data.get("digest", ""),
        reason=resolved_data.get("reason", resolved_data.get("selection_reason", "")),
    )
    return ResolutionOutcome(
        status="resolved",
        resolved=resolved,
        **base_kwargs,
    )


def _classify_error(
    data: Dict[str, Any],
    status_code: int,
    request: ResolutionRequest,
    base_kwargs: Dict[str, Any],
) -> ResolutionOutcome:
    """Classify an error response."""
    server_status = data.get("status", "rejected").lower()
    if server_status == "ambiguous":
        candidates = _parse_candidates(data.get("candidates", []))
        guidance = _ambiguity_repair(request, candidates)
        return ResolutionOutcome(
            status="ambiguous",
            candidates=candidates,
            repair_guidance=guidance,
            **base_kwargs,
        )
    return ResolutionOutcome(
        status="rejected",
        error_class=data.get("error_class", "server_rejection"),
        reason=data.get("reason", data.get("message", "")),
        repair_guidance=data.get("repair_guidance", []),
        **base_kwargs,
    )


def _handle_resolution_exception(
    exc: Exception,
    request: ResolutionRequest,
) -> ResolutionOutcome:
    """Convert transport exception into a deterministic outcome."""
    from keyhole_sdk.capability.repair import map_capability_repair

    error_class = type(exc).__name__
    guidance = map_capability_repair(error_class)
    return ResolutionOutcome(
        status="failed",
        mode=request.mode,
        correlation_id=request.correlation_id,
        error_class=error_class,
        reason=str(exc),
        repair_guidance=guidance,
        is_local_failure=True,
    )


def _parse_candidates(raw_list: List[Any]) -> List[CapabilityCandidate]:
    """Parse raw candidate dicts into typed models."""
    candidates: List[CapabilityCandidate] = []
    for raw in raw_list:
        if isinstance(raw, dict):
            candidates.append(CapabilityCandidate(
                capability=raw.get("capability", raw.get("name", "")),
                provider=raw.get("provider", ""),
                version=raw.get("version", ""),
                visibility=raw.get("visibility", "public"),
                summary=raw.get("summary", ""),
                digest=raw.get("digest", ""),
            ))
    return candidates


def _ambiguity_repair(
    request: ResolutionRequest,
    candidates: List[CapabilityCandidate],
) -> List[str]:
    """§12.2: Deterministic repair guidance for ambiguous resolution."""
    guidance = [
        f"Multiple providers satisfy '{request.capability}' — no lawful tie-break exists.",
    ]
    if candidates:
        providers = ", ".join(c.provider for c in candidates if c.provider)
        if providers:
            guidance.append(f"Candidates: {providers}")
    guidance.extend([
        f"Specify --provider <name> to pin a provider explicitly.",
        f"Inspect candidates: keyhole search {request.capability}",
    ])
    return guidance
