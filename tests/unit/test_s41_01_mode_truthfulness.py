"""§13.4 — Mode Truthfulness Tests.

Verifies that local-only documentation does not make false claims
about governed capabilities, and that governed-mode documentation
provides required context.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from developer_surface_contract.invariants import INV_MODE_TRUTHFULNESS, Verdict
from developer_surface_contract.validate import check_mode_truthfulness, load_inventory


class TestModetruthfulness:
    """Local-only docs must not claim governed capabilities."""

    def test_mode_truth_check_accepts(self, repo_root: Path) -> None:
        result = check_mode_truthfulness(repo_root)
        assert result.passed, (
            f"Mode truthfulness failed:\n" + "\n".join(f"  - {r}" for r in result.reasons)
        )
        assert result.invariant_id == INV_MODE_TRUTHFULNESS

    def test_readme_no_false_governance_claims(self, repo_root: Path) -> None:
        """README.md must not claim Event Spine, upstream audit, etc."""
        readme_text = (repo_root / "README.md").read_text()
        lines = readme_text.split("\n")
        inv = load_inventory(repo_root)
        forbidden = inv["mode_truth"]["local_only_forbidden_claims"]
        negation_kw = [
            "not", "no ", "without", "does not", "governed mode",
            "governed)", "when configured", "may not", "must not",
            "do not", "cannot", "warning", "note:",
        ]
        for claim in forbidden:
            for i, line in enumerate(lines, 1):
                if claim not in line:
                    continue
                # Check a 3-line window for negation context
                window_start = max(0, i - 2)
                window_end = min(len(lines), i + 1)
                window_text = " ".join(lines[window_start:window_end]).lower()
                if any(kw in window_text for kw in negation_kw):
                    continue
                pytest.fail(
                    f"README.md:{i} claims '{claim}' without governed context"
                )

    def test_quickstart_no_false_governance_claims(self, repo_root: Path) -> None:
        """quickstart.md must not claim governed features unconditionally."""
        qs = repo_root / "docs" / "quickstart.md"
        if not qs.exists():
            pytest.skip("quickstart.md not found")
        content = qs.read_text()
        inv = load_inventory(repo_root)
        forbidden = inv["mode_truth"]["local_only_forbidden_claims"]
        for claim in forbidden:
            if claim in content:
                for i, line in enumerate(content.split("\n"), 1):
                    if claim not in line:
                        continue
                    lower = line.lower()
                    allowed_contexts = [
                        "not", "no ", "without", "does not", "governed mode",
                        "governed)", "when configured", "may not", "must not",
                        "do not", "cannot", "warning", "note:",
                    ]
                    if not any(kw in lower for kw in allowed_contexts):
                        pytest.fail(
                            f"quickstart.md:{i} claims '{claim}' without governed context"
                        )
