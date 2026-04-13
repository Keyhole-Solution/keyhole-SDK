"""Context inspect — SDK-CLIENT-16 §5.2/§9.

Retrieves and renders a context digest for builder inspection.
Makes context intelligible — not just raw JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from keyhole_sdk.transport.client import GovernedTransport, TransportResult
from keyhole_sdk.transport.proof_metadata import TransportProofMetadata


@dataclass
class ContextInspectResult:
    """Result of inspecting a context digest.

    §9: Surface enough for the builder to understand what
    state-of-truth the digest represents.
    """

    success: bool
    ctxpack_digest: str = ""
    summary: str = ""
    repo_name: str = ""
    tenant: str = ""
    org: str = ""
    workspace: str = ""
    lane: str = ""
    lens: str = ""
    generated_at: str = ""
    observed_at: str = ""
    is_recent: bool = False
    is_run_bound: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    http_status: int = 0
    response_data: Dict[str, Any] = field(default_factory=dict)
    proof: Optional[TransportProofMetadata] = None
    error_class: str = ""
    reason: str = ""
    repair_guidance: List[str] = field(default_factory=list)

    def render_human(self) -> str:
        """Render a human-readable inspection summary."""
        if not self.success:
            lines = [
                f"Context Inspect — FAILED",
                f"  Digest: {self.ctxpack_digest or '(unknown)'}",
                f"  Error: {self.reason}",
            ]
            if self.repair_guidance:
                lines.append("  Repair:")
                for g in self.repair_guidance:
                    lines.append(f"    - {g}")
            return "\n".join(lines)

        lines = [
            f"Context Inspect — OK",
            f"  Digest:      {self.ctxpack_digest}",
        ]
        if self.summary:
            lines.append(f"  Summary:     {self.summary}")
        if self.repo_name:
            lines.append(f"  Repo:        {self.repo_name}")
        if self.tenant:
            lines.append(f"  Tenant:      {self.tenant}")
        if self.org:
            lines.append(f"  Org:         {self.org}")
        if self.workspace:
            lines.append(f"  Workspace:   {self.workspace}")
        if self.lane:
            lines.append(f"  Lane:        {self.lane}")
        if self.lens:
            lines.append(f"  Lens:        {self.lens}")
        if self.generated_at:
            lines.append(f"  Generated:   {self.generated_at}")
        if self.observed_at:
            lines.append(f"  Observed:    {self.observed_at}")
        if self.is_recent:
            lines.append(f"  Recent:      yes (most recently compiled)")
        if self.is_run_bound:
            lines.append(f"  Run-bound:   yes")
        return "\n".join(lines)


def inspect_context(
    *,
    transport: GovernedTransport,
    ctxpack_digest: str,
    repo_name: str = "",
) -> ContextInspectResult:
    """Inspect a context digest through the boundary.

    Uses context.compile with an inspect intent — the server
    may return cached metadata for a known digest.

    §9: The point is to let the builder understand what
    state-of-truth this digest actually represents.
    """
    from keyhole_sdk.context_lifecycle.repair import map_context_repair

    payload = {
        "run_type": "context.compile",
        "params": {
            "digest": ctxpack_digest,
            "intent": "inspect",
        },
    }
    if repo_name:
        payload["params"]["repo"] = repo_name

    try:
        result: TransportResult = transport.execute(
            "POST",
            "/mcp/v1/runs/start",
            operation_name="context.compile",
            json=payload,
        )
    except Exception as exc:
        return _handle_inspect_exception(exc, ctxpack_digest)

    return _classify_inspect_result(result, ctxpack_digest)


def _classify_inspect_result(
    result: TransportResult,
    requested_digest: str,
) -> ContextInspectResult:
    """Classify the boundary response into an inspect result."""
    data = result.data
    status_str = data.get("status", "").lower()

    # Extract fields from response (may be nested under 'data')
    inner = data.get("data", {}) if isinstance(data.get("data"), dict) else {}
    merged = {**data, **inner}

    digest = (
        merged.get("ctxpack_digest")
        or merged.get("digest")
        or merged.get("ctx_ref_sha256")
        or requested_digest
    )

    if status_str in ("rejected", "error", "failed", "not_found"):
        guidance = _extract_guidance(data)
        if not guidance:
            guidance = map_context_repair("unknown_digest")
        return ContextInspectResult(
            success=False,
            ctxpack_digest=requested_digest,
            http_status=result.status_code,
            response_data=data,
            proof=result.proof,
            error_class=data.get("error_class", "inspect_failed"),
            reason=data.get("reason", data.get("message", "Unknown digest or inspect failure.")),
            repair_guidance=guidance,
        )

    return ContextInspectResult(
        success=True,
        ctxpack_digest=digest,
        summary=merged.get("summary", ""),
        repo_name=merged.get("repo", merged.get("repo_name", "")),
        tenant=merged.get("tenant", ""),
        org=merged.get("org", ""),
        workspace=merged.get("workspace", ""),
        lane=merged.get("lane", ""),
        lens=merged.get("lens", ""),
        generated_at=merged.get("generated_at", ""),
        observed_at=datetime.now(timezone.utc).isoformat(),
        metadata={k: v for k, v in merged.items() if k not in (
            "ctxpack_digest", "digest", "ctx_ref_sha256", "summary",
            "repo", "repo_name", "tenant", "org", "workspace",
            "lane", "lens", "generated_at", "status",
        )},
        http_status=result.status_code,
        response_data=data,
        proof=result.proof,
    )


def _handle_inspect_exception(
    exc: Exception,
    requested_digest: str,
) -> ContextInspectResult:
    """Convert transport exceptions to ContextInspectResult."""
    from keyhole_sdk.context_lifecycle.repair import map_context_repair

    error_class = type(exc).__name__
    guidance = map_context_repair(error_class)

    proof = None
    if hasattr(exc, "request_id"):
        proof = TransportProofMetadata(
            request_id=getattr(exc, "request_id", ""),
            idempotency_key=getattr(exc, "idempotency_key", None),
            command_name="context.inspect",
        )

    return ContextInspectResult(
        success=False,
        ctxpack_digest=requested_digest,
        http_status=getattr(exc, "status_code", 0),
        proof=proof,
        error_class=error_class,
        reason=str(exc),
        repair_guidance=guidance,
    )


def _extract_guidance(data: Dict[str, Any]) -> List[str]:
    """Extract repair guidance from a server response body."""
    guidance: List[str] = []
    if "repair_guidance" in data and isinstance(data["repair_guidance"], list):
        guidance.extend(str(g) for g in data["repair_guidance"])
    if "suggested_next_step" in data:
        guidance.append(str(data["suggested_next_step"]))
    return guidance


# Import here to avoid circular at module level
def map_context_repair(error_class: str) -> List[str]:
    from keyhole_sdk.context_lifecycle.repair import map_context_repair as _map
    return _map(error_class)
