"""Registration submitter — SDK-CLIENT-07 §12, §13, §17.

Submits a shaped registration request through the GovernedTransport
layer. Handles success, replayed, accepted, deferred, and rejected
outcomes honestly. Inherits SDK-CLIENT-15 transport discipline.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from keyhole_sdk.registration.models import (
    IdentityBinding,
    RegistrationOutcome,
    RegistrationRequest,
    RegistrationSource,
)
from keyhole_sdk.transport.client import GovernedTransport, TransportResult


def submit_registration(
    *,
    transport: GovernedTransport,
    request: RegistrationRequest,
) -> RegistrationOutcome:
    """Submit a registration request and classify the outcome (§12, §13).

    Uses the GovernedTransport, which automatically handles:
    - X-Request-Id injection
    - X-Idempotency-Key for repo.register (WRITE_IDEMPOTENT_REQUIRED)
    - Retry with preserved identity
    - Replay detection

    Returns a RegistrationOutcome with honest rendering.
    """
    try:
        result: TransportResult = transport.execute(
            "POST",
            "/mcp/v1/repos/register",
            operation_name="repo.register",
            json=request.to_payload(),
        )
    except Exception as exc:
        return _handle_transport_exception(exc, request)

    return _classify_outcome(result, request)


def _classify_outcome(
    result: TransportResult,
    request: RegistrationRequest,
) -> RegistrationOutcome:
    """Classify the boundary response into an honest registration outcome."""
    data = result.data
    status_code = result.status_code
    payload = request.payload

    registration_id = (
        data.get("registration_id")
        or data.get("repo_id")
        or data.get("id")
    )
    server_status = data.get("status", "").lower()
    is_replay = data.get("is_replay", data.get("replayed", False))

    # Extract identity binding from server
    identity_binding = _extract_identity_binding(data)

    # Warnings and suggestions
    warnings = data.get("warnings", [])
    suggested_actions = data.get("suggested_actions", data.get("next_steps", []))

    base_kwargs: Dict[str, Any] = {
        "registration_id": registration_id,
        "repo_name": payload.repo_name,
        "registration_source": payload.registration_source,
        "readiness": payload.readiness,
        "shadow": payload.shadow,
        "correlation_id": payload.correlation_id,
        "identity_binding": identity_binding,
        "http_status": status_code,
        "response_data": data,
        "warnings": warnings,
        "suggested_actions": suggested_actions,
    }

    # §13.2: Replayed outcome
    if is_replay:
        return RegistrationOutcome(
            status="replayed",
            is_replay=True,
            **base_kwargs,
        )

    # §13.3: Accepted/deferred
    if status_code == 202 or server_status in ("accepted", "pending"):
        return RegistrationOutcome(status="accepted", **base_kwargs)

    if server_status == "deferred":
        return RegistrationOutcome(status="deferred", **base_kwargs)

    # Server rejection
    if server_status in ("rejected", "error", "failed"):
        guidance = data.get("repair_guidance", [])
        return RegistrationOutcome(
            status="rejected",
            error_class=data.get("error_class", "server_rejection"),
            reason=data.get("reason", data.get("message", "")),
            repair_guidance=guidance,
            **base_kwargs,
        )

    # Terminal success
    return RegistrationOutcome(status="success", **base_kwargs)


def _handle_transport_exception(
    exc: Exception,
    request: RegistrationRequest,
) -> RegistrationOutcome:
    """Convert transport exceptions to RegistrationOutcome with repair guidance."""
    from keyhole_sdk.registration.repair import map_registration_repair

    error_class = type(exc).__name__
    guidance = map_registration_repair(error_class)
    payload = request.payload

    return RegistrationOutcome(
        status="failed",
        repo_name=payload.repo_name,
        registration_source=payload.registration_source,
        readiness=payload.readiness,
        shadow=payload.shadow,
        correlation_id=payload.correlation_id,
        error_class=error_class,
        reason=str(exc),
        repair_guidance=guidance,
        is_local_failure=True,
    )


def _extract_identity_binding(data: Dict[str, Any]) -> Optional[IdentityBinding]:
    """Extract identity binding from server response (§11)."""
    # Server may return binding at top level or in nested object
    binding_data = data.get("identity_binding") or data.get("binding") or {}

    if not isinstance(binding_data, dict):
        binding_data = {}

    # Also check top-level fields as fallback
    fields = {
        "tenant_id": binding_data.get("tenant_id", data.get("tenant_id", "")),
        "org_id": binding_data.get("org_id", data.get("org_id", "")),
        "user_id": binding_data.get("user_id", data.get("user_id", "")),
        "cohort_id": binding_data.get("cohort_id", data.get("cohort_id", "")),
        "worker_id": binding_data.get("worker_id", data.get("worker_id", "")),
        "repo_id": binding_data.get("repo_id", data.get("repo_id", "")),
        "workspace_id": binding_data.get("workspace_id", data.get("workspace_id", "")),
        "origin": binding_data.get("origin", data.get("origin", "")),
        "purpose": binding_data.get("purpose", data.get("purpose", "")),
    }

    # Only return if at least one field is populated
    if any(v for v in fields.values()):
        return IdentityBinding(**fields)

    return None
