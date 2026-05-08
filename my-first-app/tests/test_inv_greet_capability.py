"""pytest wrapper for MY-FIRST-APP-INV-01.

This test is the required_test declared in governance_contract.yaml.
It runs the invariant gate and asserts ACCEPT — any REJECT fails the
test suite and blocks promotion.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# Allow running from repo root or this directory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "invariants"))
from inv_greet import CheckResult, InvariantResult, Verdict, run_gate


def test_inv_greet_verdict_is_accept() -> None:
    """MY-FIRST-APP-INV-01 must return ACCEPT."""
    result = run_gate()
    failed = [c for c in result.checks if not c.passed]
    assert result.verdict == Verdict.ACCEPT, (
        f"INV-01 REJECT — {len(failed)} check(s) failed:\n"
        + "\n".join(f"  {c.check}: {c.detail}" for c in failed)
    )


def test_inv_greet_all_checks_present() -> None:
    """All 7 defined checks must be present in the result."""
    result = run_gate()
    expected = {
        "has_greeting_str",
        "has_name_str",
        "capability_field_correct",
        "name_in_greeting",
        "default_name_is_world",
        "response_immutable",
    }
    found = {c.check for c in result.checks}
    missing = expected - found
    assert not missing, f"Missing checks: {missing}"


def test_inv_greet_named_greeting() -> None:
    """greet('Alice') must produce greeting containing 'Alice'."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from greet import greet
    resp = greet("Alice")
    assert resp.name == "Alice"
    assert "Alice" in resp.greeting
    assert resp.capability == "my-first-app.greet.user.v1"


def test_inv_greet_default_name() -> None:
    """greet(None) and greet('  ') must both default to 'World'."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from greet import greet
    assert greet(None).name == "World"
    assert greet("   ").name == "World"


def test_inv_greet_response_immutable() -> None:
    """GreetResponse must be frozen."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from greet import greet
    resp = greet("Bob")
    with pytest.raises((AttributeError, TypeError)):
        resp.greeting = "hacked"  # type: ignore[misc]
