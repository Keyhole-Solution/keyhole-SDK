"""Unit tests for SDK-CLIENT-25.

Covers:

  - capabilities parsing (supported_flows / preferred_interactive_flow)
  - flow selection (device → PKCE fallback → unsupported error)
  - device authorization response parsing
  - polling pending / slow_down / success / expired / denied
  - bounded network retry budget
  - auth attempt supersession
  - logout deletes all auth state
  - re-auth after logout starts fresh transaction
  - identity mismatch detection
  - redaction of secrets in diagnostics

These tests do not contact any network.  They drive the SDK with
in-memory ``requests.Session`` doubles and a temp KEYHOLE_HOME.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.auth_bootstrap.models import (
    AuthFlowType,
    AuthSession,
    WhoamiResponse,
)
from keyhole_sdk.discovery.client import CapabilitiesClient
from keyhole_sdk.discovery.models import CapabilitiesResult, AuthPosture
from keyhole_sdk.sdk_client_25 import (
    AuthAttemptRegistry,
    AuthFlowName,
    DeviceAuthorizationCancelled,
    DeviceAuthorizationDenied,
    DeviceAuthorizationExpired,
    DeviceAuthorizationFlow,
    DeviceAuthorizationNetworkError,
    DeviceAuthorizationResponse,
    DevicePollOutcome,
    DevicePollStatus,
    DiagnosticRecorder,
    SignOutManager,
    UnsupportedAuthFlowError,
    detect_identity_mismatch,
    redact_text,
    select_auth_flow,
)


# ── Test doubles ───────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, status_code: int, body: Optional[Dict[str, Any]] = None,
                 text: str = "") -> None:
        self.status_code = status_code
        self._body = body
        self.text = text or (json.dumps(body) if body is not None else "")
        self.content = self.text.encode("utf-8") if self.text else b""

    def json(self) -> Any:
        if self._body is None:
            raise ValueError("no JSON body")
        return self._body


class _FakeSession:
    """Minimal ``requests.Session`` stand-in driven by a script of responses."""

    def __init__(self, script: List[_FakeResponse]) -> None:
        self._script = list(script)
        self.calls: List[Dict[str, Any]] = []
        self.headers: Dict[str, str] = {}

    def get(self, url, timeout=None, **_):  # noqa: D401 - signature mirrors requests
        return self._respond("GET", url)

    def post(self, url, data=None, timeout=None, **_):
        return self._respond("POST", url, data=data)

    def close(self) -> None:
        return None

    def _respond(self, method: str, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        if not self._script:
            return _FakeResponse(500, {"error": "no_more_scripted_responses"})
        return self._script.pop(0)


# ── Capabilities parsing ───────────────────────────────────────


def test_capabilities_parses_supported_flows_and_preferred() -> None:
    raw = {
        "contract": "mcp/v1",
        "auth": {
            "flow": "oidc_pkce",
            "realm": "kh-prod",
            "supported_flows": [
                "authorization_code_pkce",
                "device_authorization",
            ],
            "preferred_interactive_flow": "device_authorization",
        },
    }
    normalized = CapabilitiesClient._normalize(raw)  # type: ignore[attr-defined]
    assert normalized.auth.supported_flows == [
        "authorization_code_pkce",
        "device_authorization",
    ]
    assert normalized.auth.preferred_interactive_flow == "device_authorization"
    assert normalized.auth.supports_device_authorization() is True
    assert normalized.auth.supports_pkce() is True


def test_capabilities_missing_supported_flows_defaults_empty() -> None:
    raw = {"contract": "mcp/v1", "auth": {"realm": "kh-prod"}}
    normalized = CapabilitiesClient._normalize(raw)  # type: ignore[attr-defined]
    assert normalized.auth.supported_flows == []
    assert normalized.auth.preferred_interactive_flow == ""
    assert normalized.auth.supports_device_authorization() is False


# ── Flow selection ─────────────────────────────────────────────


def _caps_with(supported: List[str], preferred: str = "") -> CapabilitiesResult:
    return CapabilitiesResult(
        auth=AuthPosture(
            supported_flows=list(supported),
            preferred_interactive_flow=preferred,
        )
    )


def test_select_device_when_advertised_and_preferred() -> None:
    caps = _caps_with(
        ["authorization_code_pkce", "device_authorization"],
        preferred="device_authorization",
    )
    decision = select_auth_flow(caps)
    assert decision.flow is AuthFlowName.DEVICE_AUTHORIZATION
    assert decision.reason == "server_preferred_device_authorization"


def test_select_device_when_advertised_without_preference() -> None:
    caps = _caps_with(["device_authorization", "authorization_code_pkce"])
    decision = select_auth_flow(caps)
    assert decision.flow is AuthFlowName.DEVICE_AUTHORIZATION


def test_select_pkce_fallback_when_device_not_advertised() -> None:
    caps = _caps_with(["authorization_code_pkce"])
    decision = select_auth_flow(caps)
    assert decision.flow is AuthFlowName.AUTHORIZATION_CODE_PKCE
    assert decision.reason == "pkce_fallback_advertised"


def test_select_rejects_when_no_supported_flow() -> None:
    caps = _caps_with([])
    with pytest.raises(UnsupportedAuthFlowError):
        select_auth_flow(caps)


def test_select_pkce_fallback_when_capabilities_empty_and_allowed() -> None:
    caps = _caps_with([])
    decision = select_auth_flow(caps, allow_pkce_when_unadvertised=True)
    assert decision.flow is AuthFlowName.AUTHORIZATION_CODE_PKCE


def test_select_never_picks_forbidden_flow() -> None:
    caps = _caps_with(["custom_magic_link_queue"])
    with pytest.raises(UnsupportedAuthFlowError):
        select_auth_flow(caps)


# ── Device authorization parsing ───────────────────────────────


def test_device_authorization_response_parses_required_fields() -> None:
    parsed = DeviceAuthorizationResponse.from_dict({
        "device_code": "abc",
        "user_code": "ABCD-1234",
        "verification_uri": "https://example.com/device",
        "verification_uri_complete": "https://example.com/device?user_code=ABCD-1234",
        "expires_in": 900,
        "interval": 5,
    })
    assert parsed.user_code == "ABCD-1234"
    assert parsed.expires_in == 900
    assert parsed.interval == 5
    summary = parsed.safe_summary()
    assert "device_code" not in summary
    assert summary["has_verification_uri_complete"] is True


def test_device_authorization_response_rejects_missing_device_code() -> None:
    with pytest.raises(ValueError):
        DeviceAuthorizationResponse.from_dict({
            "user_code": "X", "verification_uri": "https://x"
        })


# ── Device polling state machine ───────────────────────────────


def _flow_with(script: List[_FakeResponse]) -> tuple[DeviceAuthorizationFlow, _FakeSession, List[float]]:
    fake = _FakeSession(script)
    sleeps: List[float] = []
    clock = {"t": 0.0}

    def sleep(s: float) -> None:
        sleeps.append(s)
        clock["t"] += s

    def now() -> float:
        return clock["t"]

    flow = DeviceAuthorizationFlow(
        device_authorization_endpoint="https://auth/device",
        token_endpoint="https://auth/token",
        client_id="keyhole-cli",
        session=fake,
        sleep=sleep,
        clock=now,
    )
    return flow, fake, sleeps


def _device(expires_in: int = 60, interval: int = 5) -> DeviceAuthorizationResponse:
    return DeviceAuthorizationResponse(
        device_code="DEV", user_code="USER",
        verification_uri="https://x/device",
        verification_uri_complete="https://x/device?user_code=USER",
        expires_in=expires_in, interval=interval,
    )


def test_polling_authorization_pending_then_success() -> None:
    flow, fake, sleeps = _flow_with([
        _FakeResponse(400, {"error": "authorization_pending"}),
        _FakeResponse(200, {
            "access_token": "ACCESS", "token_type": "Bearer",
            "refresh_token": "REFRESH", "expires_in": 3600,
        }),
    ])
    token = flow.poll_for_token(_device())
    assert token.access_token == "ACCESS"
    assert sleeps == [5]


def test_polling_slow_down_increases_interval() -> None:
    flow, fake, sleeps = _flow_with([
        _FakeResponse(400, {"error": "slow_down"}),
        _FakeResponse(400, {"error": "authorization_pending"}),
        _FakeResponse(200, {"access_token": "T", "token_type": "Bearer"}),
    ])
    flow.poll_for_token(_device(interval=5))
    # First interval bump 5 → 10, second remains 10.
    assert sleeps[0] == 10
    assert sleeps[1] == 10


def test_polling_access_denied_raises() -> None:
    flow, *_ = _flow_with([_FakeResponse(400, {"error": "access_denied"})])
    with pytest.raises(DeviceAuthorizationDenied):
        flow.poll_for_token(_device())


def test_polling_expired_token_raises() -> None:
    flow, *_ = _flow_with([_FakeResponse(400, {"error": "expired_token"})])
    with pytest.raises(DeviceAuthorizationExpired):
        flow.poll_for_token(_device())


def test_polling_bounded_network_retry_then_fails() -> None:
    flow, *_ = _flow_with([
        _FakeResponse(503, {"error": "server_busy"}),
        _FakeResponse(503, {"error": "server_busy"}),
        _FakeResponse(503, {"error": "server_busy"}),
    ])
    with pytest.raises(DeviceAuthorizationNetworkError):
        flow.poll_for_token(_device())


def test_polling_supersession_short_circuits() -> None:
    flow, *_ = _flow_with([_FakeResponse(400, {"error": "authorization_pending"})])
    superseded = {"value": False}

    def is_super() -> bool:
        # Become superseded immediately after first poll.
        if superseded["value"]:
            return True
        superseded["value"] = True
        return False

    with pytest.raises(DeviceAuthorizationCancelled):
        flow.poll_for_token(_device(), is_superseded=is_super)


# ── Auth attempt registry / supersession ───────────────────────


def test_registry_supersedes_prior_attempts() -> None:
    reg = AuthAttemptRegistry()
    a = reg.start("device_authorization")
    b = reg.start("device_authorization")
    assert reg.is_superseded(a.attempt_id) is True
    assert reg.is_superseded(b.attempt_id) is False
    assert reg.is_active(b.attempt_id) is True


def test_registry_cancel_all_marks_pending_superseded() -> None:
    reg = AuthAttemptRegistry()
    a = reg.start("device_authorization")
    cancelled = reg.cancel_all()
    assert a.attempt_id in cancelled
    assert reg.is_superseded(a.attempt_id) is True


# ── Logout / re-auth hygiene ───────────────────────────────────


@pytest.fixture
def keyhole_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("KEYHOLE_HOME", str(tmp_path))
    return tmp_path


def _seed_session(store: CredentialStore) -> None:
    session = AuthSession(
        access_token="ACCESS",
        refresh_token="REFRESH",
        flow_type=AuthFlowType.DEVICE,
        auth_server_url="https://auth.example.com",
    )
    store.save(session)


def test_logout_clears_all_auth_state(keyhole_home: Path) -> None:
    store = CredentialStore()
    _seed_session(store)
    assert store.exists()

    extra = keyhole_home / "mcp_account.json"
    extra.write_text("{}", encoding="utf-8")

    fake = _FakeSession([_FakeResponse(200, {})])  # revocation OK
    registry = AuthAttemptRegistry()
    registry.start("device_authorization")

    manager = SignOutManager(
        credential_store=store,
        registry=registry,
        revocation_endpoint="https://auth.example.com/revoke",
        client_id="keyhole-cli",
        extra_paths=[extra],
        session=fake,
    )
    result = manager.sign_out()

    assert result.cleared_credential_store is True
    assert store.exists() is False
    assert not extra.exists()
    assert result.cleared_pending_attempts  # at least one cancelled


def test_logout_succeeds_even_if_revocation_fails(keyhole_home: Path) -> None:
    store = CredentialStore()
    _seed_session(store)
    fake = _FakeSession([_FakeResponse(500, {"error": "boom"})])
    manager = SignOutManager(
        credential_store=store,
        revocation_endpoint="https://auth.example.com/revoke",
        client_id="keyhole-cli",
        session=fake,
    )
    result = manager.sign_out()
    assert result.cleared_credential_store is True
    assert result.revoked_refresh_token is False
    assert store.exists() is False


def test_reauth_after_logout_finds_no_credentials(keyhole_home: Path) -> None:
    store = CredentialStore()
    _seed_session(store)
    SignOutManager(credential_store=store, revocation_endpoint=None,
                   client_id="keyhole-cli").sign_out()
    # Re-auth precondition: no credentials → fresh login required.
    assert store.is_authenticated() is False
    assert store.load() is None


# ── Identity mismatch ──────────────────────────────────────────


def test_identity_match_when_subjects_align() -> None:
    a = WhoamiResponse(user_id="alice", tenant_id="acme")
    b = WhoamiResponse(user_id="alice", tenant_id="acme")
    result = detect_identity_mismatch(a, b)
    assert result.matched is True
    assert result.differing_fields == []


def test_identity_mismatch_detected_for_different_users() -> None:
    a = WhoamiResponse(user_id="alice")
    b = WhoamiResponse(user_id="bob")
    result = detect_identity_mismatch(a, b)
    assert result.matched is False
    assert "user_id" in result.differing_fields
    assert "Detected Keyhole identity mismatch" in result.warning_text()


def test_identity_match_tolerates_one_side_unknown() -> None:
    a = WhoamiResponse(user_id="alice")
    result = detect_identity_mismatch(a, None)
    assert result.matched is True


# ── Diagnostic redaction ───────────────────────────────────────


def test_diagnostic_redacts_secret_fields(keyhole_home: Path) -> None:
    log_path = keyhole_home / "diag.log"
    rec = DiagnosticRecorder(log_path=log_path)
    rec.record("auth.token.stored", {
        "access_token": "secret-token",
        "refresh_token": "secret-refresh",
        "device_code": "DEV",
        "user_email": "alice@example.com",
        "verification_uri_complete": "https://example.com/device?user_code=ABCD",
        "client_id": "keyhole-cli",
    })
    safe = rec.export_safe()[0]
    payload = safe["payload"]
    assert payload["access_token"] == "***redacted***"
    assert payload["refresh_token"] == "***redacted***"
    assert payload["device_code"] == "***redacted***"
    assert "alice@" not in payload["user_email"]
    assert "user_code" not in payload["verification_uri_complete"]
    assert payload["client_id"] == "keyhole-cli"
    # Log file is JSON-lines.
    raw = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(raw) == 1
    assert "secret-token" not in raw[0]
    assert "secret-refresh" not in raw[0]


def test_redact_text_scrubs_bearer_and_jwt() -> None:
    jwt = "eyJhbGciOi.eyJzdWIiOi.SflKxwRJSM"
    text = f"Authorization: Bearer {jwt} sent to alice@example.com"
    redacted = redact_text(text)
    assert jwt not in redacted
    assert "alice@example.com" not in redacted
    assert "Bearer ***redacted***" in redacted
