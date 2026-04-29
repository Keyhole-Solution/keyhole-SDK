"""Unit tests — SDK-CLIENT-24 Runtime Contract Verification.

Constitutional invariants verified here:
  - Client never self-certifies trust (server alone classifies).
  - Container mode requires an image digest.
  - External mode produces a deterministic claims digest.
  - The negative ``.venv`` context is rejected by the boundary.
  - Diagnostics never elevate ``.venv`` to canonical.
  - The runtime_contract package contains no ``keyhole_platform`` imports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock

import pytest

from keyhole_sdk.discovery.models import CapabilitiesResult
from keyhole_sdk.exceptions import PublicEndpointError
from keyhole_sdk.runtime_contract import (
    COMPATIBILITY_CHECK_RUN_TYPE,
    CONTRACT_VERSION,
    RuntimeCompatibilityResult,
    RuntimeCompatibilityStatus,
    RuntimeContextBuilder,
    RuntimeContractClient,
    RuntimeMode,
    RuntimeProfile,
    RuntimeProfileKind,
    RuntimeSurfaceResult,
    RuntimeTrustLevel,
    SURFACE_GET_RUN_TYPE,
    collect_diagnostics,
)


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────


def _make_caps(profiles: Optional[list] = None) -> CapabilitiesResult:
    """Build a CapabilitiesResult carrying runtime_profiles in raw."""
    raw: Dict[str, Any] = {
        "contract_version": "mcp/v1",
        "operations": [],
    }
    if profiles is not None:
        raw["runtime_profiles"] = {"profiles": profiles}
    return CapabilitiesResult(raw=raw)


def _build_transport_result(payload: Dict[str, Any]) -> Any:
    """Construct a fake TransportResult-like object."""
    fake = MagicMock()
    fake.data = payload
    fake.status_code = 200
    fake.response_headers = {}
    fake.proof = MagicMock()
    return fake


def _container_profile_payload() -> Dict[str, Any]:
    return {
        "profile_id": "keyhole.sdk.container.v1",
        "kind": "container",
        "canonical": True,
        "requires_container_runtime": True,
        "description": "Canonical container runtime.",
    }


def _external_profile_payload() -> Dict[str, Any]:
    return {
        "profile_id": "external.runtime.v1",
        "kind": "external",
        "canonical": False,
        "requires_container_runtime": False,
        "description": "External runtime — server-attested.",
    }


# ──────────────────────────────────────────────────────────────
# Model parsing
# ──────────────────────────────────────────────────────────────


def test_runtime_profile_model_parses_container_profile():
    profile = RuntimeProfile.from_raw(_container_profile_payload())
    assert profile.profile_id == "keyhole.sdk.container.v1"
    assert profile.kind == RuntimeProfileKind.CONTAINER
    assert profile.canonical is True
    assert profile.requires_container_runtime is True


def test_runtime_profile_model_parses_external_profile():
    profile = RuntimeProfile.from_raw(_external_profile_payload())
    assert profile.profile_id == "external.runtime.v1"
    assert profile.kind == RuntimeProfileKind.EXTERNAL
    assert profile.canonical is False


def test_runtime_surface_result_parses_server_payload():
    payload = {
        "status": "ACCEPT",
        "contract_version": CONTRACT_VERSION,
        "canonical_profile_id": "keyhole.sdk.container.v1",
        "external_profile_id": "external.runtime.v1",
        "profiles": [_container_profile_payload(), _external_profile_payload()],
    }
    transport = MagicMock()
    transport.execute = MagicMock(return_value=_build_transport_result(payload))
    transport.base_url = "https://mcp.test"
    client = RuntimeContractClient(transport=transport)
    result = client.get_runtime_surface()
    assert result.status == "ACCEPT"
    assert result.canonical_profile_id == "keyhole.sdk.container.v1"
    assert result.external_profile_id == "external.runtime.v1"
    assert len(result.profiles) == 2


def test_runtime_compatibility_result_accept():
    raw = {
        "status": "ACCEPT",
        "selected_profile": "keyhole.sdk.container.v1",
        "runtime_trust_level": "canonical_container",
        "contract_version": CONTRACT_VERSION,
    }
    out = RuntimeCompatibilityResult.from_raw(raw, correlation_id="cid")
    assert out.status == RuntimeCompatibilityStatus.ACCEPT
    assert out.runtime_trust_level == RuntimeTrustLevel.CANONICAL_CONTAINER
    assert out.selected_profile == "keyhole.sdk.container.v1"
    assert out.correlation_id == "cid"


def test_runtime_compatibility_result_reject_with_repair():
    raw = {
        "status": "REJECT",
        "reason": "missing_container_digest",
        "message": "container_image_digest is required",
        "repair": [
            "Build the canonical image and re-submit with --image-digest.",
        ],
    }
    out = RuntimeCompatibilityResult.from_raw(raw)
    assert out.status == RuntimeCompatibilityStatus.REJECT
    assert out.reason == "missing_container_digest"
    assert out.repair.repair  # repair guidance preserved


# ──────────────────────────────────────────────────────────────
# Builder
# ──────────────────────────────────────────────────────────────


def test_runtime_context_builder_container_requires_digest():
    builder = RuntimeContextBuilder()
    with pytest.raises(ValueError, match="missing_container_digest"):
        builder.build_container_context(container_image_digest="")
    with pytest.raises(ValueError, match="missing_container_digest"):
        builder.build_container_context(container_image_digest=None)


def test_runtime_context_builder_external_generates_claims_digest():
    builder = RuntimeContextBuilder(sdk_version="0.4.1", cli_version="0.3.1")
    ctx_a = builder.build_external_context(
        runtime_kind="local-python",
        platform="linux/x86_64",
        python_version="3.11.6",
    )
    ctx_b = builder.build_external_context(
        runtime_kind="local-python",
        platform="linux/x86_64",
        python_version="3.11.6",
    )
    assert ctx_a.runtime_claims_digest is not None
    assert ctx_a.runtime_claims_digest.startswith("sha256:")
    # Determinism
    assert ctx_a.runtime_claims_digest == ctx_b.runtime_claims_digest
    # Platform/version change → different digest
    ctx_c = builder.build_external_context(
        runtime_kind="local-python",
        platform="darwin/arm64",
        python_version="3.11.6",
    )
    assert ctx_a.runtime_claims_digest != ctx_c.runtime_claims_digest


def test_runtime_context_builder_marks_venv_noncanonical():
    diag = collect_diagnostics()
    # Invariant §12.3 — local .venv is never canonical.
    assert diag.local_venv_canonical is False


def test_runtime_context_builder_negative_nonportable_venv():
    builder = RuntimeContextBuilder()
    ctx = builder.build_nonportable_venv_context()
    assert ctx.runtime_mode == RuntimeMode.EXTERNAL
    assert ctx.nonportable_paths
    payload = ctx.to_payload()
    assert "nonportable_paths" in payload
    assert any(".venv" in p for p in payload["nonportable_paths"])


# ──────────────────────────────────────────────────────────────
# Client behavior
# ──────────────────────────────────────────────────────────────


def test_runtime_client_reads_capabilities_runtime_profiles():
    caps = _make_caps(
        profiles=[_container_profile_payload(), _external_profile_payload()]
    )
    transport = MagicMock()
    transport.base_url = "https://mcp.test"
    client = RuntimeContractClient(transport=transport)
    profiles = client.get_runtime_profiles(capabilities=caps)
    assert len(profiles) == 2
    assert any(p.canonical for p in profiles)


def test_runtime_client_reads_capabilities_runtime_profiles_missing_raises():
    caps = _make_caps(profiles=None)
    transport = MagicMock()
    transport.base_url = "https://mcp.test"
    client = RuntimeContractClient(transport=transport)
    with pytest.raises(PublicEndpointError) as exc_info:
        client.get_runtime_profiles(capabilities=caps)
    assert "runtime_profiles_missing" in str(exc_info.value.detail or "")


def test_runtime_client_calls_surface_get_run_type():
    payload = {
        "status": "ACCEPT",
        "contract_version": CONTRACT_VERSION,
        "profiles": [_container_profile_payload(), _external_profile_payload()],
    }
    transport = MagicMock()
    transport.base_url = "https://mcp.test"
    transport.execute = MagicMock(return_value=_build_transport_result(payload))
    client = RuntimeContractClient(transport=transport)
    client.get_runtime_surface()
    args, kwargs = transport.execute.call_args
    assert args[0] == "POST"
    assert args[1] == "/mcp/v1/runs/start"
    assert kwargs["operation_name"] == SURFACE_GET_RUN_TYPE
    assert kwargs["json"]["run_type"] == SURFACE_GET_RUN_TYPE


def test_runtime_client_calls_compatibility_check_run_type():
    payload = {
        "status": "ACCEPT",
        "selected_profile": "external.runtime.v1",
        "runtime_trust_level": "external_attested",
        "contract_version": CONTRACT_VERSION,
    }
    transport = MagicMock()
    transport.base_url = "https://mcp.test"
    transport.execute = MagicMock(return_value=_build_transport_result(payload))
    builder = RuntimeContextBuilder()
    ctx = builder.build_external_context(
        runtime_kind="local-python",
        platform="linux/x86_64",
        python_version="3.11.6",
    )
    client = RuntimeContractClient(transport=transport)
    out = client.check_compatibility(ctx, correlation_id="cid-1")
    args, kwargs = transport.execute.call_args
    assert kwargs["operation_name"] == COMPATIBILITY_CHECK_RUN_TYPE
    assert kwargs["json"]["run_type"] == COMPATIBILITY_CHECK_RUN_TYPE
    assert (
        kwargs["json"]["input"]["runtime_context"]["runtime_mode"]
        == "external"
    )
    assert out.status == RuntimeCompatibilityStatus.ACCEPT
    assert out.runtime_trust_level == RuntimeTrustLevel.EXTERNAL_ATTESTED


def test_runtime_client_translates_endpoint_error_to_typed_reject():
    transport = MagicMock()
    transport.base_url = "https://mcp.test"
    transport.execute = MagicMock(
        side_effect=PublicEndpointError(
            "nonportable_runtime_coupling: .venv symlink is not portable",
            status_code=400,
            detail="nonportable_runtime_coupling",
        )
    )
    builder = RuntimeContextBuilder()
    ctx = builder.build_nonportable_venv_context()
    client = RuntimeContractClient(transport=transport)
    out = client.check_compatibility(ctx, correlation_id="cid-2")
    assert out.status == RuntimeCompatibilityStatus.REJECT
    assert out.reason == "nonportable_runtime_coupling"
    assert out.repair.repair  # default repair guidance was filled


# ──────────────────────────────────────────────────────────────
# CLI handlers (direct function dispatch)
# ──────────────────────────────────────────────────────────────


def test_cli_runtime_profiles_renders_profiles(monkeypatch):
    from keyhole_cli.commands import runtime_contract as rc_cmd

    fake_caps = _make_caps(
        profiles=[_container_profile_payload(), _external_profile_payload()]
    )

    class _FakeCapsClient:
        def __init__(self, *a, **kw):
            pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def fetch(self): return fake_caps

    monkeypatch.setattr(rc_cmd, "CapabilitiesClient", _FakeCapsClient)

    class _FakeTransport:
        base_url = "https://mcp.test"
        def __init__(self, *a, **kw): pass
        def close(self): pass

    monkeypatch.setattr(rc_cmd, "GovernedTransport", _FakeTransport)

    result = rc_cmd.run_runtime_profiles(mcp_url="https://mcp.test")
    assert result.success is True
    assert result.data["profile_count"] == 2
    assert result.data["canonical_profile_id"] == "keyhole.sdk.container.v1"


def test_cli_runtime_surface_renders_contract(monkeypatch):
    from keyhole_cli.commands import runtime_contract as rc_cmd

    payload = {
        "status": "ACCEPT",
        "contract_version": CONTRACT_VERSION,
        "profiles": [_container_profile_payload(), _external_profile_payload()],
    }

    class _FakeTransport:
        base_url = "https://mcp.test"
        def __init__(self, *a, **kw): pass
        def execute(self, *a, **kw): return _build_transport_result(payload)
        def close(self): pass

    monkeypatch.setattr(rc_cmd, "GovernedTransport", _FakeTransport)
    monkeypatch.setattr(rc_cmd, "_resolve_token", lambda *_a, **_k: "")

    result = rc_cmd.run_runtime_surface(mcp_url="https://mcp.test")
    assert result.success is True
    assert result.data["canonical_profile_id"] == "keyhole.sdk.container.v1"
    assert result.data["contract_version"] == CONTRACT_VERSION


def test_cli_runtime_check_renders_accept(monkeypatch, tmp_path):
    from keyhole_cli.commands import runtime_contract as rc_cmd

    accept_payload = {
        "status": "ACCEPT",
        "selected_profile": "external.runtime.v1",
        "runtime_trust_level": "external_attested",
        "contract_version": CONTRACT_VERSION,
    }
    surface_payload = {
        "status": "ACCEPT",
        "contract_version": CONTRACT_VERSION,
        "profiles": [_container_profile_payload(), _external_profile_payload()],
    }

    class _FakeTransport:
        base_url = "https://mcp.test"
        def __init__(self, *a, **kw): pass
        def execute(self, *a, **kw):
            op = kw.get("operation_name", "")
            if op == COMPATIBILITY_CHECK_RUN_TYPE:
                return _build_transport_result(accept_payload)
            return _build_transport_result(surface_payload)
        def close(self): pass

    monkeypatch.setattr(rc_cmd, "GovernedTransport", _FakeTransport)
    monkeypatch.setattr(rc_cmd, "_resolve_token", lambda *_a, **_k: "")
    monkeypatch.setattr(
        rc_cmd, "RuntimeContractProofEmitter",
        lambda *a, **kw: _SilentEmitter(tmp_path),
    )

    result = rc_cmd.run_runtime_check(
        mode="external",
        runtime_kind="local-python",
        mcp_url="https://mcp.test",
    )
    assert result.success is True
    assert result.data["status"] == "ACCEPT"
    assert result.data["trust_level"] == "external_attested"


def test_cli_runtime_check_renders_reject_repair(monkeypatch, tmp_path):
    from keyhole_cli.commands import runtime_contract as rc_cmd

    reject_payload = {
        "status": "REJECT",
        "reason": "missing_container_digest",
        "message": "container_image_digest is required",
        "repair": ["Build the canonical image and pass --image-digest."],
    }

    class _FakeTransport:
        base_url = "https://mcp.test"
        def __init__(self, *a, **kw): pass
        def execute(self, *a, **kw):
            return _build_transport_result(reject_payload)
        def close(self): pass

    monkeypatch.setattr(rc_cmd, "GovernedTransport", _FakeTransport)
    monkeypatch.setattr(rc_cmd, "_resolve_token", lambda *_a, **_k: "")
    monkeypatch.setattr(
        rc_cmd, "RuntimeContractProofEmitter",
        lambda *a, **kw: _SilentEmitter(tmp_path),
    )

    result = rc_cmd.run_runtime_check(
        mode="external",
        runtime_kind="local-python",
        mcp_url="https://mcp.test",
    )
    assert result.success is False
    assert result.data["status"] == "REJECT"
    assert result.next_steps  # repair guidance present


def test_cli_runtime_check_nonportable_venv_negative(monkeypatch, tmp_path):
    from keyhole_cli.commands import runtime_contract as rc_cmd

    class _FakeTransport:
        base_url = "https://mcp.test"
        def __init__(self, *a, **kw): pass
        def execute(self, *a, **kw):
            raise PublicEndpointError(
                "nonportable_runtime_coupling",
                status_code=400,
                detail="nonportable_runtime_coupling",
            )
        def close(self): pass

    monkeypatch.setattr(rc_cmd, "GovernedTransport", _FakeTransport)
    monkeypatch.setattr(rc_cmd, "_resolve_token", lambda *_a, **_k: "")
    monkeypatch.setattr(
        rc_cmd, "RuntimeContractProofEmitter",
        lambda *a, **kw: _SilentEmitter(tmp_path),
    )

    result = rc_cmd.run_runtime_check(
        negative="nonportable-venv",
        mcp_url="https://mcp.test",
    )
    # Negative test: REJECT is the *expected* outcome → success=True
    assert result.success is True
    assert result.data["status"] == "REJECT"
    assert result.data["reason"] == "nonportable_runtime_coupling"


def test_cli_doctor_includes_runtime_contract_section(monkeypatch):
    from keyhole_cli.commands import doctor as doctor_cmd

    fake_caps = _make_caps(
        profiles=[_container_profile_payload(), _external_profile_payload()]
    )

    class _FakeCapsClient:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def fetch(self): return fake_caps

    # Patch CapabilitiesClient at the import site used by the helper.
    import keyhole_sdk.discovery.client as disc_mod
    monkeypatch.setattr(disc_mod, "CapabilitiesClient", _FakeCapsClient)

    section = doctor_cmd._build_runtime_contract_report(
        mcp_url="https://mcp.test"
    )
    assert section is not None
    assert section["contract_version"] == CONTRACT_VERSION
    assert section["canonical_profile_id"] == "keyhole.sdk.container.v1"
    assert section["external_profile_id"] == "external.runtime.v1"
    assert section["diagnostics"]["local_venv_canonical"] is False


# ──────────────────────────────────────────────────────────────
# Constitutional invariant: no platform imports
# ──────────────────────────────────────────────────────────────


def test_no_keyhole_platform_imports():
    """INVARIANT-8 + AC-13: runtime_contract code must never import
    keyhole_platform, and must never use control-plane decision logic."""
    import ast

    pkg_root = Path(__file__).resolve().parents[2]
    targets = [
        pkg_root / "packages" / "python" / "keyhole-sdk" / "keyhole_sdk" / "runtime_contract",
        pkg_root / "packages" / "python" / "keyhole-cli" / "keyhole_cli" / "commands" / "runtime_contract.py",
    ]
    for target in targets:
        files = [target] if target.is_file() else list(target.rglob("*.py"))
        assert files, f"No files found at {target}"
        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert not node.module.startswith("keyhole_platform"), (
                        f"Forbidden ImportFrom keyhole_platform in {path}"
                    )
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith("keyhole_platform"), (
                            f"Forbidden Import keyhole_platform in {path}"
                        )


# ──────────────────────────────────────────────────────────────
# Test helpers
# ──────────────────────────────────────────────────────────────


class _SilentEmitter:
    """Minimal stand-in for RuntimeContractProofEmitter (writes nothing)."""

    def __init__(self, base: Path) -> None:
        self.base = Path(base)

    def emit(self, **kwargs: Any) -> Any:
        artifact = MagicMock()
        artifact.bundle_dir = str(self.base / "runtime-contract" / "test")
        return artifact
