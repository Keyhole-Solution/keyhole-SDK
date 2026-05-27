"""Run dispatcher — SDK-CLIENT-09 §8-§10.

Dispatches a governed run request through the GovernedTransport layer,
handles outcome modes (inline terminal result vs accepted/deferred),
and captures proof metadata.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from keyhole_sdk.auth import BearerTokenProvider
from keyhole_sdk.transport.client import GovernedTransport, TransportResult
from keyhole_sdk.transport.proof_metadata import TransportProofMetadata
from keyhole_sdk.run_dispatch.request_builder import RunRequest


class OutcomeStatus(enum.Enum):
    """Classified outcome of a governed run dispatch."""

    SUCCESS = "success"
    ACCEPTED = "accepted"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    FAILED = "failed"
    TRANSPORT_ERROR = "transport_error"


@dataclass
class RunOutcome:
    """Result of a governed run dispatch — honest rendering of what happened."""

    status: OutcomeStatus
    run_type: str = ""
    repo_name: str = ""
    shadow: bool = False
    correlation_id: str = ""
    run_id: Optional[str] = None
    http_status: int = 0
    response_data: Dict[str, Any] = field(default_factory=dict)
    proof: Optional[TransportProofMetadata] = None
    error_class: str = ""
    reason: str = ""
    repair_guidance: List[str] = field(default_factory=list)
    is_local_failure: bool = False

    def to_proof_dict(self) -> Dict[str, Any]:
        """Proof-safe serialization of the outcome."""
        d: Dict[str, Any] = {
            "status": self.status.value,
            "run_type": self.run_type,
            "repo": self.repo_name,
            "shadow": self.shadow,
            "correlation_id": self.correlation_id,
            "http_status": self.http_status,
        }
        if self.run_id:
            d["run_id"] = self.run_id
        if self.error_class:
            d["error_class"] = self.error_class
        if self.reason:
            d["reason"] = self.reason
        if self.repair_guidance:
            d["repair_guidance"] = self.repair_guidance
        if self.proof:
            d["transport_proof"] = self.proof.to_dict()
        return d


def dispatch_run(
    *,
    transport: GovernedTransport,
    request: RunRequest,
) -> RunOutcome:
    """Dispatch a governed run through the transport layer.

    This function:
    1. Sends the request via GovernedTransport (inheriting SDK-CLIENT-15)
    2. Classifies the outcome (success/accepted/deferred/rejected/failed)
    3. Returns a structured RunOutcome with proof metadata

    The transport layer handles X-Request-Id, X-Idempotency-Key,
    retry, and replay detection automatically.
    """
    from keyhole_sdk.run_dispatch.repair import map_repair_guidance

    try:
        result: TransportResult = transport.execute(
            "POST",
            "/mcp/v1/runs/start",
            operation_name="run.start",
            json=request.to_payload(),
        )
    except Exception as exc:
        return _handle_transport_exception(exc, request)

    return _classify_outcome(result, request)


def _classify_outcome(result: TransportResult, request: RunRequest) -> RunOutcome:
    """Classify the boundary response into an honest outcome."""
    data = result.data
    status_code = result.status_code

    # Extract run-level metadata.
    # The server nests run_id under data.data.run_id for async 202 responses.
    inner_data = data.get("data") or {}
    run_id = (
        data.get("run_id")
        or data.get("id")
        or (inner_data.get("run_id") if isinstance(inner_data, dict) else None)
    )
    server_status = (
        data.get("status")
        or (inner_data.get("status") if isinstance(inner_data, dict) else None)
        or ""
    ).lower()

    # §10.2: Accepted / deferred — NOT a terminal result
    if status_code == 202 or server_status in ("accepted", "pending"):
        return RunOutcome(
            status=OutcomeStatus.ACCEPTED,
            run_type=request.run_type,
            repo_name=request.repo_name,
            shadow=request.shadow,
            correlation_id=request.correlation_id,
            run_id=run_id,
            http_status=status_code,
            response_data=data,
            proof=result.proof,
        )

    if server_status == "deferred":
        return RunOutcome(
            status=OutcomeStatus.DEFERRED,
            run_type=request.run_type,
            repo_name=request.repo_name,
            shadow=request.shadow,
            correlation_id=request.correlation_id,
            run_id=run_id,
            http_status=status_code,
            response_data=data,
            proof=result.proof,
        )

    # §10.3: Server-side rejection
    if server_status in ("rejected", "error", "failed"):
        guidance = _extract_server_guidance(data)
        return RunOutcome(
            status=OutcomeStatus.REJECTED,
            run_type=request.run_type,
            repo_name=request.repo_name,
            shadow=request.shadow,
            correlation_id=request.correlation_id,
            run_id=run_id,
            http_status=status_code,
            response_data=data,
            proof=result.proof,
            error_class=data.get("error_class", "server_rejection"),
            reason=data.get("reason", data.get("message", "")),
            repair_guidance=guidance,
        )

    # §10.1: Inline terminal success
    return RunOutcome(
        status=OutcomeStatus.SUCCESS,
        run_type=request.run_type,
        repo_name=request.repo_name,
        shadow=request.shadow,
        correlation_id=request.correlation_id,
        run_id=run_id,
        http_status=status_code,
        response_data=data,
        proof=result.proof,
    )


def _handle_transport_exception(
    exc: Exception, request: RunRequest
) -> RunOutcome:
    """Convert transport exceptions to RunOutcome with repair guidance."""
    from keyhole_sdk.run_dispatch.repair import map_repair_guidance
    from keyhole_sdk.exceptions import (
        AuthenticationError,
        PublicEndpointError,
        RuntimeUnavailableError,
    )
    from keyhole_sdk.transport.errors import (
        IdempotencyConflictError,
        RateLimitedError,
        RetryExhaustedError,
        TransportUnknownError,
    )

    error_class = type(exc).__name__
    guidance = map_repair_guidance(error_class)

    proof = None
    if hasattr(exc, "request_id"):
        proof = TransportProofMetadata(
            request_id=getattr(exc, "request_id", ""),
            idempotency_key=getattr(exc, "idempotency_key", None),
            command_name="run.start",
        )

    return RunOutcome(
        status=OutcomeStatus.TRANSPORT_ERROR if isinstance(
            exc, (TransportUnknownError, RetryExhaustedError, RuntimeUnavailableError)
        ) else OutcomeStatus.FAILED,
        run_type=request.run_type,
        repo_name=request.repo_name,
        shadow=request.shadow,
        correlation_id=request.correlation_id,
        http_status=getattr(exc, "status_code", 0),
        proof=proof,
        error_class=error_class,
        reason=str(exc),
        repair_guidance=guidance,
    )


def _extract_server_guidance(data: Dict[str, Any]) -> List[str]:
    """Extract repair guidance from a server response body."""
    guidance: List[str] = []
    if "repair_guidance" in data and isinstance(data["repair_guidance"], list):
        guidance.extend(str(g) for g in data["repair_guidance"])
    if "suggested_next_step" in data:
        guidance.append(str(data["suggested_next_step"]))
    if "hint" in data:
        guidance.append(str(data["hint"]))
    return guidance
