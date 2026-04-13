"""Ingestion submitter — SDK-CLIENT-10 §12, §14.

Submits a shaped ingestion package through the GovernedTransport
layer. Handles terminal, accepted, and deferred outcomes honestly.
Inherits SDK-CLIENT-15 transport discipline.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from keyhole_sdk.ingest.models import (
    CompatibilityPosture,
    ConfidenceLevel,
    GraphSummary,
    InferredCapability,
    IngestionOutcome,
    IngestionRequest,
)
from keyhole_sdk.transport.client import GovernedTransport, TransportResult


def submit_ingestion(
    *,
    transport: GovernedTransport,
    request: IngestionRequest,
) -> IngestionOutcome:
    """Submit an ingestion request and classify the outcome (§12, §14).

    Uses the GovernedTransport, which automatically handles:
    - X-Request-Id injection
    - X-Idempotency-Key for ingest.submit (WRITE_IDEMPOTENT_REQUIRED)
    - Retry with preserved identity
    - Replay detection

    Returns an IngestionOutcome with honest rendering of what happened.
    """
    from keyhole_sdk.ingest.repair import map_ingestion_repair

    try:
        result: TransportResult = transport.execute(
            "POST",
            "/mcp/v1/ingest",
            operation_name="ingest.submit",
            json=request.to_payload(),
        )
    except Exception as exc:
        return _handle_transport_exception(exc, request)

    return _classify_outcome(result, request)


def _classify_outcome(
    result: TransportResult,
    request: IngestionRequest,
) -> IngestionOutcome:
    """Classify the boundary response into an honest ingestion outcome."""
    data = result.data
    status_code = result.status_code
    pkg = request.package

    ingestion_id = data.get("ingestion_id") or data.get("run_id") or data.get("id")
    server_status = data.get("status", "").lower()

    # Build graph summary from response
    graph_summary = _extract_graph_summary(data)

    # Build inferred capabilities
    inferred_caps = _extract_inferred_capabilities(data)

    # Extract compatibility posture
    compatibility = _extract_compatibility(data)

    # Extract warnings and suggestions
    warnings = data.get("warnings", [])
    suggested_actions = data.get("suggested_actions", data.get("next_steps", []))

    # Accepted/deferred — not terminal
    if status_code == 202 or server_status in ("accepted", "pending"):
        return IngestionOutcome(
            status="accepted",
            ingestion_id=ingestion_id,
            repo_identity=pkg.repo_identity,
            shadow=pkg.shadow,
            correlation_id=pkg.correlation_id,
            compatibility=compatibility,
            graph_summary=graph_summary,
            inferred_capabilities=inferred_caps,
            warnings=warnings,
            suggested_actions=suggested_actions,
            http_status=status_code,
            response_data=data,
        )

    if server_status == "deferred":
        return IngestionOutcome(
            status="deferred",
            ingestion_id=ingestion_id,
            repo_identity=pkg.repo_identity,
            shadow=pkg.shadow,
            correlation_id=pkg.correlation_id,
            compatibility=compatibility,
            graph_summary=graph_summary,
            inferred_capabilities=inferred_caps,
            warnings=warnings,
            suggested_actions=suggested_actions,
            http_status=status_code,
            response_data=data,
        )

    # Server rejection
    if server_status in ("rejected", "error", "failed"):
        guidance = data.get("repair_guidance", [])
        return IngestionOutcome(
            status="rejected",
            ingestion_id=ingestion_id,
            repo_identity=pkg.repo_identity,
            shadow=pkg.shadow,
            correlation_id=pkg.correlation_id,
            compatibility=compatibility,
            http_status=status_code,
            response_data=data,
            error_class=data.get("error_class", "server_rejection"),
            reason=data.get("reason", data.get("message", "")),
            repair_guidance=guidance,
        )

    # Terminal success
    return IngestionOutcome(
        status="success",
        ingestion_id=ingestion_id,
        repo_identity=pkg.repo_identity,
        shadow=pkg.shadow,
        correlation_id=pkg.correlation_id,
        compatibility=compatibility,
        graph_summary=graph_summary,
        inferred_capabilities=inferred_caps,
        warnings=warnings,
        suggested_actions=suggested_actions,
        http_status=status_code,
        response_data=data,
    )


def _handle_transport_exception(
    exc: Exception,
    request: IngestionRequest,
) -> IngestionOutcome:
    """Convert transport exceptions to IngestionOutcome with repair guidance."""
    from keyhole_sdk.ingest.repair import map_ingestion_repair

    error_class = type(exc).__name__
    guidance = map_ingestion_repair(error_class)
    pkg = request.package

    return IngestionOutcome(
        status="failed",
        repo_identity=pkg.repo_identity,
        shadow=pkg.shadow,
        correlation_id=pkg.correlation_id,
        error_class=error_class,
        reason=str(exc),
        repair_guidance=guidance,
        is_local_failure=True,
    )


def _extract_graph_summary(data: Dict[str, Any]) -> Optional[GraphSummary]:
    """Extract graph summary from server response, if present."""
    gs = data.get("graph_summary") or data.get("graph")
    if not gs or not isinstance(gs, dict):
        return None
    return GraphSummary(
        node_count=gs.get("node_count", gs.get("nodes", 0)),
        edge_count=gs.get("edge_count", gs.get("edges", 0)),
        components=gs.get("components", 0),
        primary_language=gs.get("primary_language", ""),
        topology_notes=gs.get("topology_notes", []),
    )


def _extract_inferred_capabilities(data: Dict[str, Any]) -> List[InferredCapability]:
    """Extract inferred capabilities from server response."""
    raw = data.get("inferred_capabilities", data.get("capabilities", []))
    if not isinstance(raw, list):
        return []
    caps: List[InferredCapability] = []
    for item in raw:
        if isinstance(item, dict):
            confidence_str = item.get("confidence", "low")
            try:
                confidence = ConfidenceLevel(confidence_str)
            except ValueError:
                confidence = ConfidenceLevel.LOW
            caps.append(InferredCapability(
                name=item.get("name", ""),
                confidence=confidence,
                basis=item.get("basis", ""),
                category=item.get("category", ""),
            ))
        elif isinstance(item, str):
            caps.append(InferredCapability(name=item))
    return caps


def _extract_compatibility(data: Dict[str, Any]) -> CompatibilityPosture:
    """Extract compatibility posture from server response."""
    raw = data.get("compatibility", data.get("compatibility_posture", "foreign"))
    try:
        return CompatibilityPosture(raw)
    except ValueError:
        return CompatibilityPosture.FOREIGN
