"""§13.6 — Publish Compatibility Tests.

Verifies that SDK and CLI packages have valid pyproject.toml files
with parseable version strings and required metadata for PyPI publish.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from developer_surface_contract.invariants import INV_PUBLISH_COMPATIBILITY_CLOSED, Verdict
from developer_surface_contract.validate import check_version_alignment


class TestPublishCompatibility:
    """SDK/CLI packages must be publishable with valid metadata."""

    def test_version_alignment_accepts(self, repo_root: Path) -> None:
        result = check_version_alignment(repo_root)
        assert result.passed, (
            f"Version alignment failed:\n" + "\n".join(f"  - {r}" for r in result.reasons)
        )
        assert result.invariant_id == INV_PUBLISH_COMPATIBILITY_CLOSED

    def test_sdk_pyproject_has_name(self, repo_root: Path) -> None:
        toml = (
            repo_root / "packages" / "python" / "keyhole-sdk" / "pyproject.toml"
        ).read_text()
        assert re.search(r'^name\s*=\s*"keyhole-sdk"', toml, re.MULTILINE), (
            "SDK pyproject.toml missing name = 'keyhole-sdk'"
        )

    def test_cli_pyproject_has_name(self, repo_root: Path) -> None:
        toml = (
            repo_root / "packages" / "python" / "keyhole-cli" / "pyproject.toml"
        ).read_text()
        assert re.search(r'^name\s*=\s*"keyhole-cli"', toml, re.MULTILINE), (
            "CLI pyproject.toml missing name = 'keyhole-cli'"
        )

    def test_sdk_has_version(self, repo_root: Path) -> None:
        toml = (
            repo_root / "packages" / "python" / "keyhole-sdk" / "pyproject.toml"
        ).read_text()
        match = re.search(r'^version\s*=\s*"([^"]+)"', toml, re.MULTILINE)
        assert match, "SDK pyproject.toml missing version"
        version = match.group(1)
        # Must be valid semver-ish
        assert re.match(r"\d+\.\d+\.\d+", version), f"Invalid version: {version}"

    def test_cli_has_version(self, repo_root: Path) -> None:
        toml = (
            repo_root / "packages" / "python" / "keyhole-cli" / "pyproject.toml"
        ).read_text()
        match = re.search(r'^version\s*=\s*"([^"]+)"', toml, re.MULTILINE)
        assert match, "CLI pyproject.toml missing version"
        version = match.group(1)
        assert re.match(r"\d+\.\d+\.\d+", version), f"Invalid version: {version}"

    def test_sdk_has_readme(self, repo_root: Path) -> None:
        readme = repo_root / "packages" / "python" / "keyhole-sdk" / "README.md"
        assert readme.exists(), "SDK README.md missing"
        assert readme.stat().st_size > 100, "SDK README.md too short"

    def test_cli_has_readme(self, repo_root: Path) -> None:
        readme = repo_root / "packages" / "python" / "keyhole-cli" / "README.md"
        assert readme.exists(), "CLI README.md missing"
        assert readme.stat().st_size > 100, "CLI README.md too short"
