"""Onboarding client — orchestrates registration, verification, and status.

Communicates only through the MCP boundary.  The client never treats
an identity as active until the server says so.
"""

from __future__ import annotations

import uuid
from typing import Optional

import requests

from keyhole_sdk.envelope import unwrap_mcp_envelope
from keyhole_sdk.onboarding.errors import (
    DuplicateRegistrationError,
    MissingClassificationError,
    OnboardingError,
    OnboardingNetworkError,
    RegistrationRejectedError,
    VerificationExpiredError,
    VerificationFailedError,
)
from keyhole_sdk.onboarding.models import (
    OnboardingRealm,
    OnboardingResult,
    OnboardingState,
    RegistrationRequest,
    RegistrationResponse,
    RegistrationStatusResponse,
    VerificationRequest,
    VerificationResponse,
)

_DEFAULT_MCP_URL = "https://mcp.keyholesolution.com"
_REGISTER_PATH = "/auth/register"
_VERIFY_PATH = "/auth/verify"
_STATUS_PATH = "/auth/registration-status"
_RESEND_PATH = "/auth/resend-verification"


class OnboardingClient:
    """Client-side onboarding orchestrator.

    Submits registration, verification, and status requests to the
    governed MCP boundary.  Never persists auth credentials (that
    belongs to DEV-SDK-01).
    """

    def __init__(
        self,
        *,
        mcp_base_url: str = _DEFAULT_MCP_URL,
        timeout: int = 30,
    ) -> None:
        self._mcp_base_url = mcp_base_url.rstrip("/")
        self._timeout = timeout

    # ── Registration ────────────────────────────────────────

    def register(
        self,
        request: RegistrationRequest,
        *,
        correlation_id: Optional[str] = None,
    ) -> RegistrationResponse:
        """Submit a registration request to the MCP boundary.

        Validates classification fields for ``kh-dev`` before sending.
        """
        # Enforce classification for kh-dev
        missing = request.validate_classification()
        if missing:
            raise MissingClassificationError(missing)

        cid = correlation_id or str(uuid.uuid4())
        payload = {
            "email": request.email,
            "username": request.username,
            "display_name": request.display_name,
            "realm": request.realm.value,
            "correlation_id": cid,
        }
        if request.origin:
            payload["origin"] = request.origin
        if request.purpose:
            payload["purpose"] = request.purpose
        if request.tenant:
            payload["tenant"] = request.tenant
        if request.org:
            payload["org"] = request.org

        data = self._post(_REGISTER_PATH, payload)

        return RegistrationResponse.model_validate(data)

    # ── Verification ────────────────────────────────────────

    def verify(
        self,
        request: VerificationRequest,
        *,
        correlation_id: Optional[str] = None,
    ) -> VerificationResponse:
        """Submit a verification completion request."""
        cid = correlation_id or str(uuid.uuid4())
        payload: dict = {
            "user_id": request.registration_id,
            "correlation_id": cid,
        }
        if request.code:
            payload["code"] = request.code
        if request.token:
            payload["token"] = request.token

        data = self._post(_VERIFY_PATH, payload)

        return VerificationResponse.model_validate(data)

    # ── Status ──────────────────────────────────────────────

    def get_status(
        self,
        registration_id: str,
        *,
        correlation_id: Optional[str] = None,
    ) -> RegistrationStatusResponse:
        """Inspect the current onboarding state for a registration."""
        cid = correlation_id or str(uuid.uuid4())
        try:
            resp = requests.get(
                f"{self._mcp_base_url}{_STATUS_PATH}",
                params={
                    "user_id": registration_id,
                    "correlation_id": cid,
                },
                headers={"Content-Type": "application/json"},
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise OnboardingNetworkError(str(exc)) from exc

        data = unwrap_mcp_envelope(resp.json())
        self._check_error(resp.status_code, data)

        return RegistrationStatusResponse.model_validate(data)

    # ── Resend verification ─────────────────────────────────

    def resend_verification(
        self,
        registration_id: str,
        *,
        correlation_id: Optional[str] = None,
    ) -> RegistrationStatusResponse:
        """Request a new verification code/email."""
        cid = correlation_id or str(uuid.uuid4())
        payload = {
            "registration_id": registration_id,
            "correlation_id": cid,
        }
        data = self._post(_RESEND_PATH, payload)
        return RegistrationStatusResponse.model_validate(data)

    # ── Helpers ─────────────────────────────────────────────

    def _post(self, path: str, payload: dict) -> dict:
        """POST to the MCP boundary, unwrap envelope, check errors."""
        try:
            resp = requests.post(
                f"{self._mcp_base_url}{path}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise OnboardingNetworkError(str(exc)) from exc

        data = unwrap_mcp_envelope(resp.json())
        self._check_error(resp.status_code, data)
        return data

    @staticmethod
    def _check_error(status_code: int, data: dict) -> None:
        """Raise a typed error if the server indicates failure."""
        # Normalise nested error envelope: {"ok": false, "error": {"code": ..., "message": ...}}
        error_envelope = data.get("error") if isinstance(data.get("error"), dict) else {}
        error_class = (
            data.get("error_class")
            or error_envelope.get("code")
            or ""
        )
        raw_message = (
            data.get("message")
            or error_envelope.get("message")
            or data.get("error")
            or "Request failed"
        )
        message = str(raw_message) if not isinstance(raw_message, str) else raw_message

        if status_code == 409:
            raise DuplicateRegistrationError(
                message or "Identity already registered",
            )
        if status_code == 422:
            raise RegistrationRejectedError(
                message or "Registration rejected",
                reason=data.get("reason") or error_envelope.get("detail"),
                repair_suggestions=data.get("repair_suggestions"),
            )
        if status_code == 410:
            raise VerificationExpiredError(
                message or "Verification expired",
            )
        if status_code >= 400:
            if "verification" in error_class.lower() or "verification" in message.lower():
                raise VerificationFailedError(
                    message, reason=data.get("reason") or error_envelope.get("repair"),
                )
            raise OnboardingError(
                message,
                reason=data.get("reason"),
                repair_suggestions=data.get("repair_suggestions"),
            )
