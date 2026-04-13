"""Capability search submitter — SDK-CLIENT-08 §8.1, §11.

Shapes a capability search request and submits it to the MCP
boundary.  Returns a CapabilitySearchResult with candidates,
empty-result handling, and repair guidance.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from keyhole_sdk.capability.models import (
    CapabilityCandidate,
    CapabilitySearchRequest,
    CapabilitySearchResult,
)
from keyhole_sdk.transport.client import GovernedTransport, TransportResult


def submit_capability_search(
    *,
    transport: GovernedTransport,
    request: CapabilitySearchRequest,
) -> CapabilitySearchResult:
    """Submit a governed capability search to the MCP boundary.

    Returns a :class:`CapabilitySearchResult` — never raises on
    boundary errors; instead classifies the failure into the result.
    """
    try:
        result: TransportResult = transport.execute(
            "POST",
            "/mcp/v1/capabilities/search",
            operation_name="capability.search",
            json=request.to_payload(),
        )
    except Exception as exc:
        return _handle_search_exception(exc, request)

    return _classify_search_result(result, request)


def _classify_search_result(
    result: TransportResult,
    request: CapabilitySearchRequest,
) -> CapabilitySearchResult:
    """Classify the transport result into a deterministic search result."""
    data = result.data
    status_code = result.status_code
    raw_candidates = data.get("candidates", data.get("results", []))

    candidates: List[CapabilityCandidate] = []
    for raw in raw_candidates:
        if isinstance(raw, dict):
            candidates.append(CapabilityCandidate(
                capability=raw.get("capability", raw.get("name", "")),
                provider=raw.get("provider", ""),
                version=raw.get("version", ""),
                visibility=raw.get("visibility", "public"),
                summary=raw.get("summary", raw.get("description", "")),
                digest=raw.get("digest", ""),
                matches_inferred_need=raw.get("matches_inferred_need", False),
                already_pinned_locally=raw.get("already_pinned_locally", False),
            ))

    total_count = data.get("total_count", data.get("total", len(candidates)))
    is_empty = len(candidates) == 0
    warnings = data.get("warnings", [])

    next_steps: List[str] = []
    if is_empty:
        next_steps.extend(_empty_search_next_steps(request))

    # Handle error responses
    if status_code >= 400:
        return CapabilitySearchResult(
            query=request.query,
            candidates=[],
            total_count=0,
            correlation_id=request.correlation_id,
            is_empty=True,
            http_status=status_code,
            error_class=data.get("error_class", "server_rejection"),
            reason=data.get("reason", data.get("message", "")),
            next_steps=data.get("repair_guidance", next_steps),
            warnings=warnings,
        )

    return CapabilitySearchResult(
        query=request.query,
        candidates=candidates,
        total_count=total_count,
        correlation_id=request.correlation_id,
        is_empty=is_empty,
        http_status=status_code,
        next_steps=next_steps,
        warnings=warnings,
    )


def _handle_search_exception(
    exc: Exception,
    request: CapabilitySearchRequest,
) -> CapabilitySearchResult:
    """Convert a transport exception into a deterministic search result."""
    from keyhole_sdk.capability.repair import map_capability_repair

    error_class = type(exc).__name__
    guidance = map_capability_repair(error_class)
    return CapabilitySearchResult(
        query=request.query,
        candidates=[],
        total_count=0,
        correlation_id=request.correlation_id,
        is_empty=True,
        http_status=0,
        error_class=error_class,
        reason=str(exc),
        next_steps=guidance,
    )


def _empty_search_next_steps(request: CapabilitySearchRequest) -> List[str]:
    """§11.2: Deterministic next steps for empty search results."""
    steps = [
        f"No capabilities matched '{request.query}'.",
        "Check spelling and namespace prefix.",
    ]
    if request.provider:
        steps.append(
            f"Try relaxing the --provider filter (currently '{request.provider}')."
        )
    if request.version:
        steps.append(
            f"Try relaxing the --version filter (currently '{request.version}')."
        )
    steps.append("Try: keyhole search <broader-namespace> — to discover related capabilities.")
    return steps
