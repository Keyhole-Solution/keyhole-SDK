"""§13.1 — Contract Inventory Closure Tests.

Verifies that the public surface contract spec and inventory exist,
and that every path declared in the inventory actually exists on disk.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from developer_surface_contract.invariants import INV_PUBLIC_SURFACE_CONTRACT_CLOSED, Verdict
from developer_surface_contract.validate import (
    check_contract_spec_exists,
    check_inventory_complete,
    load_inventory,
)


class TestContractSpecExists:
    """The spec and inventory files must exist."""

    def test_contract_spec_file_exists(self, repo_root: Path) -> None:
        spec = repo_root / "docs" / "specs" / "developer_ecosystem" / "public_surface_contract.md"
        assert spec.exists(), "Contract spec missing"

    def test_inventory_file_exists(self, repo_root: Path) -> None:
        inv = repo_root / "docs" / "specs" / "developer_ecosystem" / "public_surface_inventory.yaml"
        assert inv.exists(), "Surface inventory missing"

    def test_check_contract_spec_exists_accepts(self, repo_root: Path) -> None:
        result = check_contract_spec_exists(repo_root)
        assert result.passed, f"Failed: {result.reasons}"
        assert result.invariant_id == INV_PUBLIC_SURFACE_CONTRACT_CLOSED


class TestInventoryComplete:
    """Every path declared in the inventory must exist on disk."""

    def test_inventory_valid_yaml(self, repo_root: Path) -> None:
        inv = load_inventory(repo_root)
        assert "surfaces" in inv
        assert "runtime_contract" in inv
        assert "forbidden_patterns" in inv

    def test_all_declared_paths_exist(self, repo_root: Path) -> None:
        result = check_inventory_complete(repo_root)
        assert result.passed, (
            f"Missing paths:\n" + "\n".join(f"  - {r}" for r in result.reasons)
        )

    def test_inventory_has_version(self, repo_root: Path) -> None:
        inv = load_inventory(repo_root)
        assert "version" in inv

    def test_inventory_has_story_reference(self, repo_root: Path) -> None:
        inv = load_inventory(repo_root)
        assert inv.get("story") == "CE-V5-S41-01"

    def test_runtime_contract_identity_fields_declared(self, repo_root: Path) -> None:
        inv = load_inventory(repo_root)
        assert set(inv["runtime_contract"]["identity_fields"]) == {
            "runtime_id",
            "runtime_name",
            "runtime_version",
            "environment",
            "capabilities",
        }

    def test_runtime_contract_receipt_fields_declared(self, repo_root: Path) -> None:
        inv = load_inventory(repo_root)
        assert set(inv["runtime_contract"]["receipt_fields"]) == {
            "digest",
            "status",
            "message",
            "realized_at",
        }
