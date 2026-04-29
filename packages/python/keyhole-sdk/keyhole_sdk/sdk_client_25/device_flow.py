"""OAuth 2.0 Device Authorization Grant client (RFC 8628).

SDK-CLIENT-25 §6.2 / §7.2 / §7.3 / §7.4 implementation.

This module is the standards-only path to portable, magic-link-friendly
authentication.  It does NOT:

  - decode JWTs for authority decisions (tokens are opaque);
  - implement custom MCP magic-link queues;
  - hide network errors as silent retries.

Polling discipline:

  - obey the server-provided ``interval`` (default 5s);
  - on ``slow_down``, increase interval per RFC 8628 §3.5;
  - on ``authorization_pending``, continue polling;
  - on ``access_denied`` / ``expired_token``, stop and surface a
    typed exception;
  - on transient network errors, apply bounded backoff (max 3
    consecutive failures before raising);
  - stop immediately on cancellation or attempt supersession.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional

import requests

from keyhole_sdk.auth_bootstrap.models import DeviceCodeResponse, TokenResponse


# RFC 8628 §3.5 says the client SHOULD increase the polling interval by
# at least 5 seconds when receiving ``slow_down``.
_SLOW_DOWN_INCREMENT_SECONDS = 5

# Hard cap on consecutive transient network failures during polling.
_MAX_CONSECUTIVE_NETWORK_FAILURES = 3

# Hard cap on a single HTTP request during polling.
_POLL_REQUEST_TIMEOUT_SECONDS = 30


class DevicePollStatus(str, Enum):
    """Outcome states for a device authorization polling cycle."""

    PENDING = "authorization_pending"
    SLOW_DOWN = "slow_down"
    APPROVED = "approved"
    EXPIRED = "expired_token"
    DENIED = "access_denied"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"
    NETWORK_ERROR = "network_error"


# ── Typed errors ───────────────────────────────────────────────


class DeviceAuthorizationError(Exception):
    """Base class for device authorization client errors."""


class DeviceAuthorizationExpired(DeviceAuthorizationError):
    """The device code expired before user approval."""


class DeviceAuthorizationDenied(DeviceAuthorizationError):
    """The user denied or canceled the authorization."""


class DeviceAuthorizationCancelled(DeviceAuthorizationError):
    """Polling was cancelled locally (cancel token or supersession)."""


class DeviceAuthorizationNetworkError(DeviceAuthorizationError):
    """Network error exceeded the bounded retry budget."""


# ── Models ─────────────────────────────────────────────────────


@dataclass
class DeviceAuthorizationResponse:
    """RFC 8628 §3.2 device authorization response.

    Wraps the raw OAuth response with redaction-safe accessors.
    The ``device_code`` is private — callers must not log it.
    """

    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: Optional[str]
    expires_in: int
    interval: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceAuthorizationResponse":
        if not isinstance(data, dict):
            raise ValueError("device authorization response must be a JSON object")
        device_code = data.get("device_code")
        user_code = data.get("user_code")
        verification_uri = data.get("verification_uri")
        if not isinstance(device_code, str) or not device_code:
            raise ValueError("device_code missing from device authorization response")
        if not isinstance(user_code, str) or not user_code:
            raise ValueError("user_code missing from device authorization response")
        if not isinstance(verification_uri, str) or not verification_uri:
            raise ValueError(
                "verification_uri missing from device authorization response"
            )
        verification_uri_complete = data.get("verification_uri_complete")
        if verification_uri_complete is not None and not isinstance(
            verification_uri_complete, str
        ):
            verification_uri_complete = None
        expires_in_raw = data.get("expires_in", 900)
        interval_raw = data.get("interval", 5)
        try:
            expires_in = int(expires_in_raw)
        except (TypeError, ValueError):
            expires_in = 900
        try:
            interval = int(interval_raw)
        except (TypeError, ValueError):
            interval = 5
        return cls(
            device_code=device_code,
            user_code=user_code,
            verification_uri=verification_uri,
            verification_uri_complete=verification_uri_complete,
            expires_in=max(60, expires_in),
            interval=max(1, interval),
        )

    def safe_summary(self) -> Dict[str, Any]:
        """Redaction-safe diagnostic projection.

        Never includes ``device_code`` or full ``verification_uri_complete``.
        ``user_code`` is included because the OAuth spec treats it as the
        end-user shareable secondary credential, not a bearer secret.
        """
        return {
            "user_code": self.user_code,
            "verification_uri": self.verification_uri,
            "has_verification_uri_complete": (
                self.verification_uri_complete is not None
            ),
            "expires_in": self.expires_in,
            "interval": self.interval,
        }

    def to_legacy(self) -> DeviceCodeResponse:
        """Convert to the legacy ``DeviceCodeResponse`` model used by SDK-CLIENT-01."""
        return DeviceCodeResponse(
            device_code=self.device_code,
            user_code=self.user_code,
            verification_uri=self.verification_uri,
            verification_uri_complete=self.verification_uri_complete,
            expires_in=self.expires_in,
            interval=self.interval,
        )


@dataclass
class DevicePollOutcome:
    """Single polling-cycle outcome."""

    status: DevicePollStatus
    token: Optional[TokenResponse] = None
    next_interval: int = 5
    detail: str = ""


# ── Cancellation token ─────────────────────────────────────────


class CancelToken:
    """Thread-safe cancellation signal for a device flow attempt."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._reason: str = ""

    def cancel(self, reason: str = "user_cancelled") -> None:
        self._reason = reason
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> str:
        return self._reason


# ── Flow orchestrator ──────────────────────────────────────────


class DeviceAuthorizationFlow:
    """RFC 8628 device authorization grant client.

    Discovers the device authorization endpoint and token endpoint via
    OIDC discovery, requests a device code, and polls the token
    endpoint until approval or terminal state.

    The flow does NOT inspect or decode any token — tokens are returned
    opaque.  Identity must be confirmed by calling ``whoami`` on the MCP
    boundary after a successful grant.
    """

    # Standard OAuth Device Authorization Grant type URN.
    GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"

    def __init__(
        self,
        *,
        device_authorization_endpoint: str,
        token_endpoint: str,
        client_id: str,
        scope: str = "openid profile email",
        session: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._device_authorization_endpoint = device_authorization_endpoint
        self._token_endpoint = token_endpoint
        self._client_id = client_id
        self._scope = scope
        self._session = session or requests.Session()
        self._sleep = sleep
        self._clock = clock

    # ── Public API ────────────────────────────────────────────

    def request_device_authorization(self) -> DeviceAuthorizationResponse:
        """Call ``device_authorization_endpoint`` and parse the response."""
        try:
            resp = self._session.post(
                self._device_authorization_endpoint,
                data={"client_id": self._client_id, "scope": self._scope},
                timeout=_POLL_REQUEST_TIMEOUT_SECONDS,
            )
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise DeviceAuthorizationNetworkError(
                f"Cannot reach device authorization endpoint: {exc}"
            ) from exc

        if resp.status_code != 200:
            # Surface the OAuth error code without leaking secrets.
            try:
                err = resp.json().get("error", "")
            except ValueError:
                err = ""
            raise DeviceAuthorizationError(
                f"device authorization request failed "
                f"(HTTP {resp.status_code}, error={err or 'unknown'})"
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise DeviceAuthorizationError(
                "device authorization response is not valid JSON"
            ) from exc

        return DeviceAuthorizationResponse.from_dict(data)

    def poll_for_token(
        self,
        device: DeviceAuthorizationResponse,
        *,
        cancel_token: Optional[CancelToken] = None,
        is_superseded: Optional[Callable[[], bool]] = None,
        on_status: Optional[Callable[[DevicePollOutcome], None]] = None,
    ) -> TokenResponse:
        """Poll the token endpoint until terminal state.

        Args:
            device: The device authorization response to poll for.
            cancel_token: Optional cancel token honored every cycle.
            is_superseded: Optional callable that returns True when this
                attempt has been superseded by a newer login attempt.
                Late successes from superseded attempts are dropped.
            on_status: Optional observer invoked once per cycle with a
                redaction-safe :class:`DevicePollOutcome`.

        Returns:
            :class:`TokenResponse` on approval.

        Raises:
            DeviceAuthorizationExpired
            DeviceAuthorizationDenied
            DeviceAuthorizationCancelled
            DeviceAuthorizationNetworkError
        """
        interval = device.interval
        deadline = self._clock() + device.expires_in
        consecutive_failures = 0

        while True:
            if cancel_token is not None and cancel_token.cancelled:
                raise DeviceAuthorizationCancelled(
                    cancel_token.reason or "cancelled"
                )
            if is_superseded is not None and is_superseded():
                raise DeviceAuthorizationCancelled("superseded")

            outcome = self._poll_once(device.device_code)

            if on_status is not None:
                on_status(outcome)

            if outcome.status is DevicePollStatus.APPROVED:
                # §7.4: only the active attempt may proceed.  Verify
                # supersession one last time before returning the token.
                if is_superseded is not None and is_superseded():
                    raise DeviceAuthorizationCancelled("superseded")
                assert outcome.token is not None  # for type checker
                return outcome.token

            if outcome.status is DevicePollStatus.DENIED:
                raise DeviceAuthorizationDenied(outcome.detail or "access_denied")

            if outcome.status is DevicePollStatus.EXPIRED:
                raise DeviceAuthorizationExpired(
                    outcome.detail or "expired_token"
                )

            if outcome.status is DevicePollStatus.SLOW_DOWN:
                interval = min(interval + _SLOW_DOWN_INCREMENT_SECONDS, 60)
                consecutive_failures = 0
            elif outcome.status is DevicePollStatus.PENDING:
                consecutive_failures = 0
            elif outcome.status is DevicePollStatus.NETWORK_ERROR:
                consecutive_failures += 1
                if consecutive_failures >= _MAX_CONSECUTIVE_NETWORK_FAILURES:
                    raise DeviceAuthorizationNetworkError(
                        outcome.detail or "network error during polling"
                    )

            # Bounded backoff: never sleep past the deadline.
            now = self._clock()
            if now >= deadline:
                raise DeviceAuthorizationExpired("device code expired")
            sleep_for = min(interval, max(0.0, deadline - now))
            if sleep_for > 0:
                self._sleep(sleep_for)

    # ── Internal ──────────────────────────────────────────────

    def _poll_once(self, device_code: str) -> DevicePollOutcome:
        """Perform a single OAuth token-endpoint poll."""
        payload = {
            "grant_type": self.GRANT_TYPE,
            "device_code": device_code,
            "client_id": self._client_id,
        }
        try:
            resp = self._session.post(
                self._token_endpoint,
                data=payload,
                timeout=_POLL_REQUEST_TIMEOUT_SECONDS,
            )
        except (requests.ConnectionError, requests.Timeout) as exc:
            return DevicePollOutcome(
                status=DevicePollStatus.NETWORK_ERROR,
                detail=str(exc),
            )

        if resp.status_code == 200:
            try:
                data = resp.json()
            except ValueError:
                return DevicePollOutcome(
                    status=DevicePollStatus.NETWORK_ERROR,
                    detail="token response is not valid JSON",
                )
            try:
                token = TokenResponse.model_validate(data)
            except Exception as exc:  # noqa: BLE001 — pydantic + future-proof
                return DevicePollOutcome(
                    status=DevicePollStatus.NETWORK_ERROR,
                    detail=f"unparseable token response: {exc}",
                )
            return DevicePollOutcome(
                status=DevicePollStatus.APPROVED,
                token=token,
            )

        # OAuth device flow uses HTTP 400 with a JSON error code for
        # ``authorization_pending``, ``slow_down``, ``access_denied``,
        # and ``expired_token``.
        try:
            err_payload = resp.json() if resp.content else {}
        except ValueError:
            err_payload = {}
        error = (err_payload.get("error") or "").strip() if isinstance(
            err_payload, dict
        ) else ""

        if error == "authorization_pending":
            return DevicePollOutcome(
                status=DevicePollStatus.PENDING, detail="authorization_pending"
            )
        if error == "slow_down":
            return DevicePollOutcome(
                status=DevicePollStatus.SLOW_DOWN, detail="slow_down"
            )
        if error == "access_denied":
            return DevicePollOutcome(
                status=DevicePollStatus.DENIED, detail="access_denied"
            )
        if error in ("expired_token", "expired_device_code"):
            return DevicePollOutcome(
                status=DevicePollStatus.EXPIRED, detail=error
            )

        # Unknown OAuth error — treat as transient network/server error
        # so the bounded retry budget governs termination.
        if 500 <= resp.status_code < 600:
            return DevicePollOutcome(
                status=DevicePollStatus.NETWORK_ERROR,
                detail=f"server error {resp.status_code}",
            )
        return DevicePollOutcome(
            status=DevicePollStatus.NETWORK_ERROR,
            detail=f"unexpected token endpoint response (HTTP {resp.status_code}, "
            f"error={error or 'none'})",
        )
