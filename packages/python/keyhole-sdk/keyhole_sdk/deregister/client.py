"""SDK-CLIENT-22 — Deregistration client.

Dispatches account deletion through the governed run surface
(``POST /mcp/v1/runs/start``) with run type ``auth.remove``.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

import requests

from keyhole_sdk.envelope import unwrap_mcp_envelope
from keyhole_sdk.deregister.errors import (
    DeregistrationAlreadyDeletedError,
    DeregistrationError,
    DeregistrationNetworkError,
    DeregistrationPolicyBlockedError,
)
from keyhole_sdk.deregister.models import (
    DeregistrationOutcome,
    DeregistrationRequest,
    DeregistrationStatus,
)

_DEFAULT_MCP_URL = "https://mcp.keyholesolution.com"
_RUNS_START_PATH = "/mcp/v1/runs"


class DeregistrationClient:
    """Client-side deregistration orchestrator — §8, §13, §14.

    Dispatches ``auth.remove`` through the governed run surface.
    Requires a valid access token (authentication enforced by caller).
    """

    def __init__(
        self,
        *,
        mcp_base_url: str = _DEFAULT_MCP_URL,
        timeout: int = 30,
    ) -> None:
        self._mcp_base_url = mcp_base_url.rstrip("/")
        self._timeout = timeout

    def deregister(
        self,
        request: DeregistrationRequest,
        *,
        access_token: str,
        correlation_id: Optional[str] = None,
    ) -> DeregistrationOutcome:
        """Dispatch account deletion through the governed run surface.

        Parameters
        ----------
        request:
            The deregistration request with registration_id and realm.
        access_token:
            Valid bearer token from an authenticated session.
        correlation_id:
            Optional correlation ID for traceability.
        """
        cid = correlation_id or request.correlation_id
        idempotency_key = str(uuid.uuid4())

        payload = request.to_run_payload()

        try:
            resp = requests.post(
                f"{self._mcp_base_url}{_RUNS_START_PATH}",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "X-Idempotency-Key": idempotency_key,
                    "X-Request-Id": idempotency_key,
                },
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise DeregistrationNetworkError(str(exc)) from exc

        data = unwrap_mcp_envelope(resp.json())

        return self._classify_outcome(
            status_code=resp.status_code,
            data=data,
            registration_id=request.registration_id,
            correlation_id=cid,
        )

    @staticmethod
    def _classify_outcome(
        *,
        status_code: int,
        data: Dict[str, Any],
        registration_id: str,
        correlation_id: str,
    ) -> DeregistrationOutcome:
        """Classify the server response into a typed outcome — §14, §18."""
        error = data.get("error") or ""
        removed = data.get("removed")
        lifecycle_state = data.get("lifecycle_state", "")

        # identity_not_found → already deleted (§18.4)
        if "identity_not_found" in str(error).lower():
            return DeregistrationOutcome(
                status=DeregistrationStatus.ALREADY_DELETED,
                registration_id=registration_id,
                correlation_id=correlation_id,
                reason="The target identity was not found (already removed).",
                repair_guidance=[
                    "Inspect the prior deletion outcome instead of retrying a new delete.",
                ],
                raw_response=data,
            )

        # Successful removal
        if removed is True or lifecycle_state == "removed":
            return DeregistrationOutcome(
                status=DeregistrationStatus.ACCEPTED,
                registration_id=registration_id,
                run_id=data.get("run_id") or data.get("correlation_id"),
                correlation_id=correlation_id,
                raw_response=data,
            )

        # Server rejection (4xx)
        if 400 <= status_code < 500:
            reason = (
                data.get("message")
                or data.get("reason")
                or str(data.get("error", "Request rejected"))
            )
            return DeregistrationOutcome(
                status=DeregistrationStatus.REJECTED,
                registration_id=registration_id,
                correlation_id=correlation_id,
                reason=reason,
                repair_guidance=data.get("repair_suggestions", []),
                raw_response=data,
            )

        # Server error (5xx)
        if status_code >= 500:
            return DeregistrationOutcome(
                status=DeregistrationStatus.FAILED,
                registration_id=registration_id,
                correlation_id=correlation_id,
                reason=f"Server error (HTTP {status_code})",
                repair_guidance=["Retry the deletion request.", "If the issue persists, contact support."],
                raw_response=data,
            )

        # Accepted/deferred (2xx but not terminal)
        return DeregistrationOutcome(
            status=DeregistrationStatus.ACCEPTED,
            registration_id=registration_id,
            run_id=data.get("run_id"),
            correlation_id=correlation_id,
            raw_response=data,
        )
