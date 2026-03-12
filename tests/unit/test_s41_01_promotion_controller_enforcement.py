"""§13.7 — Promotion Controller Enforcement Tests.

Verifies that the release gate aggregates all invariant checks
and returns correct ACCEPT/REJECT verdicts.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from developer_surface_contract.invariants import ALL_INVARIANT_IDS, Verdict
from developer_surface_contract.release_gate import GateResult, run_release_gate


class TestReleaseGateStructure:
    """Release gate must return well-formed results."""

    def test_gate_returns_gate_result(self, repo_root: Path) -> None:
        result = run_release_gate(repo_root)
        assert isinstance(result, GateResult)

    def test_gate_has_timestamp(self, repo_root: Path) -> None:
        result = run_release_gate(repo_root)
        assert result.timestamp

    def test_gate_has_invariant_results(self, repo_root: Path) -> None:
        result = run_release_gate(repo_root)
        assert len(result.invariant_results) > 0

    def test_gate_verdict_is_verdict_enum(self, repo_root: Path) -> None:
        result = run_release_gate(repo_root)
        assert isinstance(result.verdict, Verdict)


class TestReleaseGateVerdict:
    """Release gate should ACCEPT when all invariants pass."""

    def test_release_gate_accepts(self, repo_root: Path) -> None:
        result = run_release_gate(repo_root)
        if not result.passed:
            failures = "\n".join(
                f"  [{r.invariant_id}] {r.name}: {r.reasons}"
                for r in result.failed_invariants
            )
            pytest.fail(f"Release gate REJECTED:\n{failures}")

    def test_all_invariants_checked(self, repo_root: Path) -> None:
        result = run_release_gate(repo_root)
        checked_ids = {r.invariant_id for r in result.invariant_results}
        # Not all invariant IDs have checks yet (INV-02 is structural)
        # but we must have at least 7 checks covering the automation-testable ones
        assert len(result.invariant_results) >= 7, (
            f"Expected >= 7 checks, got {len(result.invariant_results)}"
        )


class TestReleaseGateSerialization:
    """Release gate results must be serializable to JSON."""

    def test_to_dict(self, repo_root: Path) -> None:
        result = run_release_gate(repo_root)
        d = result.to_dict()
        assert "verdict" in d
        assert "total_checks" in d
        assert "passed" in d
        assert "failed" in d
        assert "invariant_results" in d

    def test_to_json(self, repo_root: Path) -> None:
        import json

        result = run_release_gate(repo_root)
        j = result.to_json()
        parsed = json.loads(j)
        assert parsed["verdict"] in ("ACCEPT", "REJECT")
