from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SDK_PKG = Path(__file__).resolve().parents[2] / "packages" / "python" / "keyhole-sdk"
if str(_SDK_PKG) not in sys.path:
    sys.path.insert(0, str(_SDK_PKG))
_CLI_PKG = Path(__file__).resolve().parents[2] / "packages" / "python" / "keyhole-cli"
if str(_CLI_PKG) not in sys.path:
    sys.path.insert(0, str(_CLI_PKG))

from keyhole_sdk.discovery.client import CapabilitiesClient
from keyhole_sdk.discovery.cache import CapabilitiesCache
from keyhole_sdk.discovery.operations import (
    DiscoveredOperationRegistry,
    AmbiguousOperationAliasError,
)
from keyhole_sdk.dispatch.models import RunTypeStatus
from keyhole_sdk.dispatch.schema import SchemaHelper
from keyhole_sdk.dispatch.validator import RunTypeValidator


LIVE_OPERATION_SCHEMA = {
    "type": "object",
    "required": ["claim_id", "repo_remote"],
    "properties": {
        "claim_id": {"type": "string"},
        "repo_remote": {"type": "string"},
    },
}


LIVE_CAPABILITIES = {
    "ok": True,
    "data": {
        "contract": "mcp/v1",
        "operations_declared": 30,
        "operations_implemented": 12,
        "operations": [
            {
                "name": "ingest.submit",
                "operation_id": "ingest.submit",
                "canonical_run_type": "governance.context.create",
                "aliases": ["repo.register"],
                "status": "available",
                "method": "POST",
                "path": "/mcp/v1/ingest",
                "canonical_endpoint": {
                    "method": "POST",
                    "path": "/mcp/v1/runs/start",
                },
                "governed": True,
                "event_spine_evidence": True,
                "authorization": {
                    "required_scopes": ["run:write"],
                },
                "input_schema": LIVE_OPERATION_SCHEMA,
                "output_schema": {"type": "object"},
                "capability": {
                    "name": "repo.governance.context",
                    "version": "v1",
                },
            }
        ],
        "meta": {
            "digest": "sha256:capability-contract",
        },
    },
}


def _result():
    return CapabilitiesClient._normalize(LIVE_CAPABILITIES)


def test_capability_normalization_creates_one_canonical_operation() -> None:
    result = _result()

    assert len(result.operations) == 1
    operation = result.operations[0]

    assert operation.operation_name == "ingest.submit"
    assert operation.canonical_run_type == "governance.context.create"
    assert operation.aliases == ["repo.register"]
    assert operation.canonical_endpoint == {
        "method": "POST",
        "path": "/mcp/v1/runs/start",
    }
    assert operation.governed is True
    assert operation.event_spine_evidence is True
    assert operation.required_authorization == {"required_scopes": ["run:write"]}
    assert operation.input_schema == LIVE_OPERATION_SCHEMA
    assert operation.capability_metadata == {
        "name": "repo.governance.context",
        "version": "v1",
    }


def test_registry_resolves_operation_name_canonical_type_and_alias_to_same_definition() -> None:
    registry = DiscoveredOperationRegistry.from_capabilities(_result())

    resolved = [
        registry.resolve("ingest.submit"),
        registry.resolve("governance.context.create"),
        registry.resolve("repo.register"),
    ]

    assert all(item is not None for item in resolved)
    assert len({id(item) for item in resolved}) == 1
    assert resolved[0].canonical_run_type == "governance.context.create"


def test_ambiguous_alias_is_rejected_during_registry_build() -> None:
    raw = {
        "operations": [
            {
                "name": "first.operation",
                "canonical_run_type": "first.run",
                "aliases": ["shared.alias"],
            },
            {
                "name": "second.operation",
                "canonical_run_type": "second.run",
                "aliases": ["shared.alias"],
            },
        ]
    }
    result = CapabilitiesClient._normalize(raw)

    with pytest.raises(AmbiguousOperationAliasError):
        DiscoveredOperationRegistry.from_capabilities(result)


def test_validator_marks_live_operation_identifiers_as_known_discovered() -> None:
    registry = DiscoveredOperationRegistry.from_capabilities(_result())
    validator = RunTypeValidator(discovered_registry=registry)

    for identifier in ("ingest.submit", "governance.context.create", "repo.register"):
        check = validator.check(identifier)
        assert check.is_valid
        assert check.source == "known_discovered"
        assert check.supplied_identifier == identifier
        assert check.canonical_run_type == "governance.context.create"
        assert check.operation_name == "ingest.submit"


def test_schema_helper_uses_live_schema_for_operation_name_type_and_alias() -> None:
    registry = DiscoveredOperationRegistry.from_capabilities(_result())
    helper = SchemaHelper(discovered_registry=registry)

    hints = [
        helper.get_hint("ingest.submit"),
        helper.get_hint("governance.context.create"),
        helper.get_hint("repo.register"),
    ]

    assert all(hint.available for hint in hints)
    for hint in hints:
        assert hint.run_type == "governance.context.create"
        assert hint.operation_name == "ingest.submit"
        assert hint.canonical_run_type == "governance.context.create"
        assert hint.schema_source == "live_capabilities"
        assert hint.input_schema == LIVE_OPERATION_SCHEMA


def test_server_advertised_operation_is_not_rejected_because_static_registry_lacks_it() -> None:
    registry = DiscoveredOperationRegistry.from_capabilities(_result())
    validator = RunTypeValidator(discovered_registry=registry)

    assert validator.check("ingest.submit").is_valid


def test_get_all_run_types_includes_operation_name_canonical_type_and_alias() -> None:
    result = _result()

    all_run_types = result.get_all_run_types()

    assert "ingest.submit" in all_run_types
    assert "governance.context.create" in all_run_types
    assert "repo.register" in all_run_types


def test_validator_reports_ambiguous_live_contract() -> None:
    raw = {
        "operations": [
            {
                "name": "first.operation",
                "canonical_run_type": "first.run",
                "aliases": ["shared.alias"],
            },
            {
                "name": "second.operation",
                "canonical_run_type": "second.run",
                "aliases": ["shared.alias"],
            },
        ]
    }
    validator = RunTypeValidator.from_capabilities(CapabilitiesClient._normalize(raw))

    check = validator.check("unrelated.surface")

    assert check.status == RunTypeStatus.AMBIGUOUS
    assert "shared.alias" in check.reason


def test_cache_is_partitioned_by_base_url_and_load_valid_honors_expiry(tmp_path: Path) -> None:
    first = CapabilitiesCache(cache_dir=str(tmp_path), base_url="https://one.example")
    second = CapabilitiesCache(cache_dir=str(tmp_path), base_url="https://two.example")

    assert first.cache_path != second.cache_path

    first.store(_result())
    assert first.load_valid() is not None
    assert second.load_valid() is None

    expired = CapabilitiesCache(
        cache_dir=str(tmp_path),
        base_url="https://expired.example",
        ttl_seconds=0,
    )
    expired.store(_result())
    assert expired.load_valid() is None


def test_cache_load_valid_fails_safely_on_corrupt_payload(tmp_path: Path) -> None:
    cache = CapabilitiesCache(cache_dir=str(tmp_path), base_url="https://boundary.example")
    cache.cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache.cache_path.write_text("not-json", encoding="utf-8")

    assert cache.load_valid() is None


def test_cli_dispatch_preflight_refreshes_capabilities_before_rejecting_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from keyhole_cli.commands import run_cmd

    class FakeCapabilitiesClient:
        def __init__(self, base_url: str) -> None:
            self.base_url = base_url

        def __enter__(self) -> "FakeCapabilitiesClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def fetch(self):
            return _result()

    monkeypatch.setattr(run_cmd, "CapabilitiesClient", FakeCapabilitiesClient)

    preflight = run_cmd._build_dispatch_preflight(
        repo_path=tmp_path,
        mcp_url="https://boundary.example",
        run_type="repo.register",
    )

    check = preflight.check("repo.register")
    assert check.should_proceed
    assert check.run_type == "governance.context.create"
    assert preflight.resolve_run_type("ingest.submit") == "governance.context.create"


def test_cli_dispatch_preflight_reports_discovery_unavailable_without_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from keyhole_cli.commands import run_cmd

    class FailingCapabilitiesClient:
        def __init__(self, base_url: str) -> None:
            self.base_url = base_url

        def __enter__(self) -> "FailingCapabilitiesClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def fetch(self):
            raise OSError("offline")

    monkeypatch.setattr(run_cmd, "CapabilitiesClient", FailingCapabilitiesClient)

    preflight = run_cmd._build_dispatch_preflight(
        repo_path=tmp_path,
        mcp_url="https://boundary.example",
        run_type="server.added.operation",
    )

    check = preflight.check("server.added.operation")
    assert check.status.value == "reject"
    assert "discovery is unavailable" in check.reason


def test_governed_demo_extracts_aliases_as_same_canonical_runs_start_operation() -> None:
    from keyhole_sdk.governed_demo import _extract_operations

    operations = _extract_operations(LIVE_CAPABILITIES)

    assert operations["ingest.submit"].run_type == "governance.context.create"
    assert operations["governance.context.create"].run_type == "governance.context.create"
    assert operations["repo.register"].run_type == "governance.context.create"
    assert operations["repo.register"].path == "/mcp/v1/runs/start"
