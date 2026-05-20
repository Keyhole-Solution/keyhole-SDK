"""SDK-CLIENT-29 — Consume MCP Actor Envelope and Prove Client Auth Parity.

Tests:
  T1  whoami parses actor_envelope when present
  T2  missing envelope is backward-compatible (no exception)
  T3  envelope flows through unwrap_identity for nested envelope payloads
  T4  CLI whoami output never exposes raw access tokens
  T5  auth doctor uses server whoami as the authority
  T6  JWT decoding is diagnostic only (no authority decision)
  T7  direct kh-prod token in stored credential triggers a fail check
  T8  write-bearing ops carry idempotency descriptors (carry-over)
  T9  read-only ops do not require idempotency
  T10 unknown server fields on the envelope are preserved
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from keyhole_sdk.auth_bootstrap.actor_envelope import (
    ActingPrincipal,
    ActorEnvelope,
    Authorization,
    Delegation,
    HumanPrincipal,
)
from keyhole_sdk.auth_bootstrap.models import (
    AuthFlowType,
    AuthMode,
    AuthSession,
    WhoamiResponse,
)
from keyhole_sdk.envelope import unwrap_identity, unwrap_mcp_envelope
from keyhole_sdk.transport.operation_registry import get_operation


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

CANONICAL_ENVELOPE: Dict[str, Any] = {
    "human_principal": {
        "realm": "kh-prod",
        "subject_id": "user-abc-123",
        "tenant_id": "tenant-1",
        "org_id": "org-1",
        "display_name": "Test User",
    },
    "acting_principal": {
        "realm": "keyhole-mcp",
        "client_id": "keyhole-cli",
        "kind": "cli",
    },
    "delegation": {
        "kind": "brokered_human",
        "assurance": "interactive_sso",
    },
    "authorization": {
        "effective_scopes": ["runs:start", "runs:read"],
        "tool_grants": ["context.compile", "gaps.list"],
    },
}


@pytest.fixture
def session_kh_mcp() -> AuthSession:
    """A normal session whose JWT iss looks like keyhole-mcp."""
    payload = {
        "iss": "https://auth.keyholesolution.com/realms/keyhole-mcp",
        "azp": "keyhole-cli",
        "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,
    }
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode().rstrip("=")
    fake_jwt = f"header.{payload_b64}.signature"

    return AuthSession(
        access_token=fake_jwt,
        refresh_token="refresh-xyz",
        flow_type=AuthFlowType.PKCE,
        mode=AuthMode.REAL,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        last_verified_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def session_kh_prod_direct() -> AuthSession:
    """A misconfigured session whose JWT iss points to kh-prod realm."""
    payload = {
        "iss": "https://auth.keyholesolution.com/realms/kh-prod",
        "azp": "kh-prod-public",
        "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,
    }
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode().rstrip("=")
    fake_jwt = f"header.{payload_b64}.signature"

    return AuthSession(
        access_token=fake_jwt,
        refresh_token="refresh-xyz",
        flow_type=AuthFlowType.PKCE,
        mode=AuthMode.REAL,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        last_verified_at=datetime.now(timezone.utc),
    )


# ──────────────────────────────────────────────────────────────
# T1 — whoami parses actor_envelope when present
# ──────────────────────────────────────────────────────────────

def test_whoami_parses_actor_envelope_when_present():
    payload = {
        "user_id": "u-1",
        "tenant_id": "t-1",
        "mode": "real",
        "actor_envelope": CANONICAL_ENVELOPE,
    }
    whoami = WhoamiResponse.model_validate(payload)

    assert whoami.actor_envelope is not None
    assert whoami.actor_envelope.human_principal.realm == "kh-prod"
    assert whoami.actor_envelope.acting_principal.realm == "keyhole-mcp"
    assert whoami.actor_envelope.acting_principal.client_id == "keyhole-cli"
    assert whoami.actor_envelope.delegation.kind == "brokered_human"
    assert "runs:start" in whoami.actor_envelope.authorization.effective_scopes


# ──────────────────────────────────────────────────────────────
# T2 — backward compat: missing envelope is allowed
# ──────────────────────────────────────────────────────────────

def test_whoami_without_envelope_is_backward_compatible():
    payload = {"user_id": "u-1", "tenant_id": "t-1", "mode": "real"}
    whoami = WhoamiResponse.model_validate(payload)
    assert whoami.actor_envelope is None
    assert whoami.user_id == "u-1"


# ──────────────────────────────────────────────────────────────
# T3 — unwrap_identity propagates actor_envelope from nested form
# ──────────────────────────────────────────────────────────────

def test_unwrap_identity_propagates_actor_envelope():
    nested = {
        "ok": True,
        "data": {
            "identity": {"user_id": "u-1", "tenant_id": "t-1"},
            "actor_envelope": CANONICAL_ENVELOPE,
        },
    }
    inner = unwrap_mcp_envelope(nested)
    flat = unwrap_identity(inner)

    assert flat["user_id"] == "u-1"
    assert "actor_envelope" in flat
    assert flat["actor_envelope"]["acting_principal"]["client_id"] == "keyhole-cli"


# ──────────────────────────────────────────────────────────────
# T4 — CLI whoami output never exposes raw access tokens
# ──────────────────────────────────────────────────────────────

def test_cli_whoami_output_redacts_token(session_kh_mcp, tmp_path, monkeypatch):
    monkeypatch.setenv("KEYHOLE_HOME", str(tmp_path))

    from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
    CredentialStore().save(session_kh_mcp)

    fake_whoami = WhoamiResponse.model_validate({
        "user_id": "u-1",
        "tenant_id": "t-1",
        "mode": "real",
        "actor_envelope": CANONICAL_ENVELOPE,
    })

    from keyhole_cli.commands.whoami import run_whoami

    with patch(
        "keyhole_cli.commands.whoami.WhoamiClient.whoami",
        return_value=fake_whoami,
    ):
        result = run_whoami(show_envelope=True)

    serialized = json.dumps(result.to_dict())
    assert session_kh_mcp.access_token not in serialized
    assert "refresh-xyz" not in serialized
    assert result.data["actor_envelope_present"] is True
    assert result.data["actor_envelope"]["acting_principal"]["client_id"] == "keyhole-cli"


# ──────────────────────────────────────────────────────────────
# T5 — auth doctor uses server whoami as authority
# ──────────────────────────────────────────────────────────────

def test_auth_doctor_uses_server_whoami_as_authority(
    session_kh_mcp, tmp_path, monkeypatch
):
    monkeypatch.setenv("KEYHOLE_HOME", str(tmp_path))

    from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
    CredentialStore().save(session_kh_mcp)

    fake_whoami = WhoamiResponse.model_validate({
        "user_id": "u-1",
        "tenant_id": "t-1",
        "mode": "real",
        "actor_envelope": CANONICAL_ENVELOPE,
    })

    from keyhole_cli.commands.auth_doctor import run_auth_doctor

    with patch(
        "keyhole_cli.commands.auth_doctor.WhoamiClient.whoami",
        return_value=fake_whoami,
    ):
        result = run_auth_doctor()

    assert result.success is True
    names = {c["name"]: c["status"] for c in result.data["checks"]}
    assert names["whoami_reachable"] == "pass"
    assert names["actor_envelope_present"] == "pass"
    assert names["human_principal_realm"] == "pass"
    assert names["acting_principal_realm"] == "pass"
    assert names["acting_principal_client_id"] == "pass"
    assert names["write_idempotency_headers"] == "pass"


# ──────────────────────────────────────────────────────────────
# T6 — JWT decoding is diagnostic only (no authority decision)
# ──────────────────────────────────────────────────────────────

def test_auth_doctor_does_not_use_jwt_for_authority(
    session_kh_mcp, tmp_path, monkeypatch
):
    """Even with a benign JWT, if the server returns no envelope, the
    doctor must FAIL — proving JWT inspection is diagnostic only and
    not used as a fallback authority."""
    monkeypatch.setenv("KEYHOLE_HOME", str(tmp_path))

    from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
    CredentialStore().save(session_kh_mcp)

    server_whoami = WhoamiResponse.model_validate({
        "user_id": "u-1",
        "mode": "real",
        # NO actor_envelope returned by server
    })

    from keyhole_cli.commands.auth_doctor import run_auth_doctor

    with patch(
        "keyhole_cli.commands.auth_doctor.WhoamiClient.whoami",
        return_value=server_whoami,
    ):
        result = run_auth_doctor()

    names = {c["name"]: c["status"] for c in result.data["checks"]}
    assert names["actor_envelope_present"] == "fail"
    assert result.success is False


# ──────────────────────────────────────────────────────────────
# T7 — direct kh-prod token triggers a fail check
# ──────────────────────────────────────────────────────────────

def test_auth_doctor_flags_direct_kh_prod_token(
    session_kh_prod_direct, tmp_path, monkeypatch
):
    monkeypatch.setenv("KEYHOLE_HOME", str(tmp_path))

    from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
    CredentialStore().save(session_kh_prod_direct)

    fake_whoami = WhoamiResponse.model_validate({
        "user_id": "u-1",
        "mode": "real",
        "actor_envelope": CANONICAL_ENVELOPE,
    })

    from keyhole_cli.commands.auth_doctor import run_auth_doctor

    with patch(
        "keyhole_cli.commands.auth_doctor.WhoamiClient.whoami",
        return_value=fake_whoami,
    ):
        result = run_auth_doctor()

    names = {c["name"]: c["status"] for c in result.data["checks"]}
    assert names["no_direct_kh_prod_token"] == "fail"
    assert names["jwt_issuer_realm"] == "fail"
    assert result.success is False


# ──────────────────────────────────────────────────────────────
# T8 — write-bearing ops carry idempotency descriptors (carry-over)
# ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "op_name",
    ["run.start", "register", "realize", "ingest.submit", "repo.register"],
)
def test_write_bearing_ops_require_idempotency(op_name):
    desc = get_operation(op_name)
    assert desc is not None, f"{op_name} must be registered"
    assert desc.idempotency_required is True


# ──────────────────────────────────────────────────────────────
# T9 — read-only ops do not require idempotency
# ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "op_name",
    ["context.compile", "gaps.list", "events.query", "run.status"],
)
def test_read_only_ops_do_not_require_idempotency(op_name):
    desc = get_operation(op_name)
    assert desc is not None
    assert desc.idempotency_required is False


# ──────────────────────────────────────────────────────────────
# T10 — unknown server fields are preserved (forward-compat)
# ──────────────────────────────────────────────────────────────

def test_envelope_preserves_unknown_fields():
    extended = dict(CANONICAL_ENVELOPE)
    extended["future_field"] = {"x": 1}
    extended["acting_principal"] = dict(extended["acting_principal"])
    extended["acting_principal"]["future_subfield"] = "v"

    env = ActorEnvelope.model_validate(extended)
    dumped = env.model_dump()
    assert dumped.get("future_field") == {"x": 1}
    # Acting principal future subfield preserved via extra=allow
    ap = env.acting_principal.model_dump()
    assert ap.get("future_subfield") == "v"


# ──────────────────────────────────────────────────────────────
# T11 — login success result reports actor_envelope_present
# ──────────────────────────────────────────────────────────────

def test_login_success_reports_actor_envelope_present():
    """When LoginResult carries a whoami with actor_envelope, the CLI
    success result must surface ``actor_envelope_present`` in data."""
    from keyhole_sdk.auth_bootstrap.models import LoginResult
    from keyhole_sdk.auth_bootstrap.proof import AuthProofBundle
    from keyhole_cli.commands.login import _success_result

    whoami = WhoamiResponse.model_validate({
        "user_id": "u-1",
        "tenant_id": "t-1",
        "mode": "real",
        "actor_envelope": CANONICAL_ENVELOPE,
    })
    login = LoginResult(
        success=True,
        flow_type=AuthFlowType.PKCE,
        mode=AuthMode.REAL,
        whoami=whoami,
        correlation_id="cid-1",
        credential_persisted=True,
        verification_passed=True,
        identity_source="server/whoami",
    )
    proof = AuthProofBundle(correlation_id="cid-1")
    out = _success_result(login, proof, "cid-1", auth_path="pkce")
    assert out.data["actor_envelope_present"] is True
    assert out.warnings == []


def test_login_success_warns_when_envelope_missing():
    from keyhole_sdk.auth_bootstrap.models import LoginResult
    from keyhole_sdk.auth_bootstrap.proof import AuthProofBundle
    from keyhole_cli.commands.login import _success_result

    whoami = WhoamiResponse.model_validate({
        "user_id": "u-1",
        "mode": "real",
    })
    login = LoginResult(
        success=True,
        flow_type=AuthFlowType.PKCE,
        mode=AuthMode.REAL,
        whoami=whoami,
        correlation_id="cid-1",
        credential_persisted=True,
        verification_passed=True,
        identity_source="server/whoami",
    )
    proof = AuthProofBundle(correlation_id="cid-1")
    out = _success_result(login, proof, "cid-1", auth_path="pkce")
    assert out.data["actor_envelope_present"] is False
    assert any("actor_envelope_missing" in w for w in out.warnings)
