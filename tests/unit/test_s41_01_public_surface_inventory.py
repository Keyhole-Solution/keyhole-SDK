"""§13.2 — Public Surface Inventory Tests.

Verifies CLI, SDK, runtime, OpenAPI, and JSON schema surfaces are
aligned with the declared runtime contract.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from developer_surface_contract.invariants import INV_CLI_SDK_RUNTIME_ALIGNED, Verdict
from developer_surface_contract.validate import (
    check_json_schema_matches_contract,
    check_openapi_matches_contract,
    check_runtime_models_match_contract,
    check_sdk_models_match_contract,
    load_inventory,
)


class TestSDKAlignment:
    """SDK models must match the declared contract fields."""

    def test_sdk_models_exist(self, repo_root: Path) -> None:
        p = repo_root / "packages" / "python" / "keyhole-sdk" / "keyhole_sdk" / "models.py"
        assert p.exists()

    def test_sdk_models_match_contract(self, repo_root: Path) -> None:
        result = check_sdk_models_match_contract(repo_root)
        assert result.passed, f"SDK alignment failed:\n" + "\n".join(
            f"  - {r}" for r in result.reasons
        )

    def test_sdk_identity_has_all_fields(self, repo_root: Path) -> None:
        content = (
            repo_root / "packages" / "python" / "keyhole-sdk" / "keyhole_sdk" / "models.py"
        ).read_text()
        inv = load_inventory(repo_root)
        for field_name in inv["runtime_contract"]["identity_fields"]:
            assert field_name in content, f"SDK missing identity field: {field_name}"

    def test_sdk_receipt_has_all_fields(self, repo_root: Path) -> None:
        content = (
            repo_root / "packages" / "python" / "keyhole-sdk" / "keyhole_sdk" / "models.py"
        ).read_text()
        inv = load_inventory(repo_root)
        for field_name in inv["runtime_contract"]["receipt_fields"]:
            assert field_name in content, f"SDK missing receipt field: {field_name}"


class TestRuntimeAlignment:
    """Runtime Pydantic models must match the declared contract fields."""

    def test_runtime_models_exist(self, repo_root: Path) -> None:
        p = repo_root / "services" / "test-runtime" / "app" / "models.py"
        assert p.exists()

    def test_runtime_models_match_contract(self, repo_root: Path) -> None:
        result = check_runtime_models_match_contract(repo_root)
        assert result.passed, f"Runtime alignment failed:\n" + "\n".join(
            f"  - {r}" for r in result.reasons
        )


class TestOpenAPIAlignment:
    """OpenAPI schema must match the declared contract fields."""

    def test_openapi_exists(self, repo_root: Path) -> None:
        p = repo_root / "openapi" / "test-runtime.openapi.yaml"
        assert p.exists()

    def test_openapi_matches_contract(self, repo_root: Path) -> None:
        result = check_openapi_matches_contract(repo_root)
        assert result.passed, f"OpenAPI alignment failed:\n" + "\n".join(
            f"  - {r}" for r in result.reasons
        )


class TestJSONSchemaAlignment:
    """JSON schema files must match the declared contract fields."""

    def test_receipt_schema_exists(self, repo_root: Path) -> None:
        p = repo_root / "schemas" / "runtime_realization_receipt.v1.schema.json"
        assert p.exists()

    def test_json_schema_matches_contract(self, repo_root: Path) -> None:
        result = check_json_schema_matches_contract(repo_root)
        assert result.passed, f"JSON schema alignment failed:\n" + "\n".join(
            f"  - {r}" for r in result.reasons
        )
