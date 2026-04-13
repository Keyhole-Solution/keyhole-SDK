"""Context compile — SDK-CLIENT-16 §5.1/§8.

Deterministic compile request construction, dispatch through
GovernedTransport, and structured result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from keyhole_sdk.auth import BearerTokenProvider
from keyhole_sdk.transport.client import GovernedTransport, TransportResult
from keyhole_sdk.transport.proof_metadata import TransportProofMetadata


@dataclass
class ContextCompileRequest:
    """Shaped context compile request ready for transport dispatch.

    §8: Deterministic for the same local state.
    """

    repo_name: str
    identity_fingerprint: str = ""
    correlation_id: str = ""
    timestamp: str = ""
    mode: str = ""
    origin: str = ""
    purpose: str = ""
    repo_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        """Build the wire-format payload for POST /mcp/v1/runs/start."""
        payload: Dict[str, Any] = {
            "run_type": "context.compile",
            "params": {
                "repo": self.repo_name,
            },
        }
        if self.mode:
            payload["params"]["mode"] = self.mode
        if self.origin:
            payload["params"]["origin"] = self.origin
        if self.purpose:
            payload["params"]["purpose"] = self.purpose
        if self.correlation_id:
            payload["params"]["correlation_id"] = self.correlation_id
        if self.repo_metadata:
            payload["params"]["repo_metadata"] = self.repo_metadata
        return payload

    def to_proof_dict(self) -> Dict[str, Any]:
        """Proof-safe serialization — no secrets."""
        return {
            "run_type": "context.compile",
            "repo": self.repo_name,
            "identity_fingerprint": self.identity_fingerprint,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "mode": self.mode,
            "origin": self.origin,
            "purpose": self.purpose,
        }


@dataclass
class ContextCompileResult:
    """Result of a context compile dispatch."""

    success: bool
    ctxpack_digest: str = ""
    repo_name: str = ""
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    http_status: int = 0
    response_data: Dict[str, Any] = field(default_factory=dict)
    proof: Optional[TransportProofMetadata] = None
    error_class: str = ""
    reason: str = ""
    repair_guidance: List[str] = field(default_factory=list)
    correlation_id: str = ""


def build_compile_request(
    *,
    repo_name: str,
    identity_fingerprint: str = "",
    correlation_id: str = "",
    mode: str = "",
    origin: str = "",
    purpose: str = "",
    repo_metadata: Optional[Dict[str, Any]] = None,
) -> ContextCompileRequest:
    """Construct a deterministic ContextCompileRequest.

    The timestamp is captured at construction for proof traceability.
    """
    return ContextCompileRequest(
        repo_name=repo_name,
        identity_fingerprint=identity_fingerprint,
        correlation_id=correlation_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        mode=mode,
        origin=origin,
        purpose=purpose,
        repo_metadata=repo_metadata or {},
    )


def compile_context(
    *,
    transport: GovernedTransport,
    request: ContextCompileRequest,
) -> ContextCompileResult:
    """Dispatch a context.compile request through the transport layer.

    Uses the GovernedTransport (SDK-CLIENT-15) for request identity,
    retry, and idempotency. Returns a structured ContextCompileResult.
    """
    from keyhole_sdk.context_lifecycle.repair import map_context_repair

    try:
        result: TransportResult = transport.execute(
            "POST",
            "/mcp/v1/runs/start",
            operation_name="context.compile",
            json=request.to_payload(),
        )
    except Exception as exc:
        return _handle_compile_exception(exc, request)

    return _classify_compile_result(result, request)


def _classify_compile_result(
    result: TransportResult,
    request: ContextCompileRequest,
) -> ContextCompileResult:
    """Classify the boundary response into a compile result."""
    data = result.data
    status_str = data.get("status", "").lower()

    # Extract digest from response
    ctxpack_digest = (
        data.get("ctxpack_digest")
        or data.get("digest")
        or data.get("ctx_ref_sha256", "")
    )

    # Extract metadata
    metadata = {}
    for key in ("lane", "lens", "tenant", "org", "workspace", "generated_at",
                "retrieved_at", "server_time"):
        if key in data:
            metadata[key] = data[key]
    # Nested data payloads
    if "data" in data and isinstance(data["data"], dict):
        inner = data["data"]
        if not ctxpack_digest:
            ctxpack_digest = (
                inner.get("ctxpack_digest")
                or inner.get("digest")
                or inner.get("ctx_ref_sha256", "")
            )
        for key in ("lane", "lens", "tenant", "org", "workspace",
                     "generated_at", "summary"):
            if key in inner and key not in metadata:
                metadata[key] = inner[key]

    summary = data.get("summary") or metadata.get("summary", "")

    if status_str in ("rejected", "error", "failed"):
        guidance = _extract_guidance(data)
        return ContextCompileResult(
            success=False,
            repo_name=request.repo_name,
            http_status=result.status_code,
            response_data=data,
            proof=result.proof,
            error_class=data.get("error_class", "compile_rejected"),
            reason=data.get("reason", data.get("message", "")),
            repair_guidance=guidance,
            correlation_id=request.correlation_id,
        )

    return ContextCompileResult(
        success=True,
        ctxpack_digest=ctxpack_digest,
        repo_name=request.repo_name,
        summary=summary,
        metadata=metadata,
        http_status=result.status_code,
        response_data=data,
        proof=result.proof,
        correlation_id=request.correlation_id,
    )


def _handle_compile_exception(
    exc: Exception,
    request: ContextCompileRequest,
) -> ContextCompileResult:
    """Convert transport exceptions to ContextCompileResult with repair guidance."""
    from keyhole_sdk.context_lifecycle.repair import map_context_repair

    error_class = type(exc).__name__
    guidance = map_context_repair(error_class)

    proof = None
    if hasattr(exc, "request_id"):
        proof = TransportProofMetadata(
            request_id=getattr(exc, "request_id", ""),
            idempotency_key=getattr(exc, "idempotency_key", None),
            command_name="context.compile",
        )

    return ContextCompileResult(
        success=False,
        repo_name=request.repo_name,
        http_status=getattr(exc, "status_code", 0),
        proof=proof,
        error_class=error_class,
        reason=str(exc),
        repair_guidance=guidance,
        correlation_id=request.correlation_id,
    )


def _extract_guidance(data: Dict[str, Any]) -> List[str]:
    """Extract repair guidance from a server response body."""
    guidance: List[str] = []
    if "repair_guidance" in data and isinstance(data["repair_guidance"], list):
        guidance.extend(str(g) for g in data["repair_guidance"])
    if "suggested_next_step" in data:
        guidance.append(str(data["suggested_next_step"]))
    if "hint" in data:
        guidance.append(str(data["hint"]))
    return guidance
