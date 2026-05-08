"""MY-FIRST-APP-INV-01 — GREET-USER-CAPABILITY-SHAPE-STABLE

Anti-regression gate for my-first-app.greet.user.v1.

This gate is a LOCAL invariant: it runs inside this repo's CI / keyhole
gate runner and does NOT require MCP connectivity.

A Keyhole governed promotion may not advance past this gate unless
verdict == ACCEPT.

Rule
----
The greet() function must return an object that:

  1. has attribute ``greeting`` of type str and non-empty
  2. has attribute ``name`` of type str and non-empty
  3. has attribute ``capability`` == "my-first-app.greet.user.v1"
  4. greeting contains the value of name (shape contract)
  5. passing None or blank string defaults name to "World"
  6. response is immutable (frozen dataclass) — no accidental mutation

Any regression in items 1-6 must produce verdict REJECT and block
promotion.
"""
from __future__ import annotations

import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List


# ── Add src/ to path when run standalone ────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from greet import GreetResponse, greet  # noqa: E402


# ── Shared verdict types ─────────────────────────────────────────────────────

INVARIANT_ID = "MY-FIRST-APP-INV-01"
INVARIANT_NAME = "GREET-USER-CAPABILITY-SHAPE-STABLE"
CAPABILITY = "my-first-app.greet.user.v1"


class Verdict(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


@dataclass
class CheckResult:
    check: str
    verdict: Verdict
    detail: str = ""

    @property
    def passed(self) -> bool:
        return self.verdict == Verdict.ACCEPT


@dataclass
class InvariantResult:
    invariant_id: str = INVARIANT_ID
    invariant_name: str = INVARIANT_NAME
    capability: str = CAPABILITY
    verdict: Verdict = Verdict.ACCEPT
    checks: List[CheckResult] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def passed(self) -> bool:
        return self.verdict == Verdict.ACCEPT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invariant_id": self.invariant_id,
            "invariant_name": self.invariant_name,
            "capability": self.capability,
            "verdict": self.verdict.value,
            "timestamp": self.timestamp,
            "checks_total": len(self.checks),
            "checks_passed": sum(1 for c in self.checks if c.passed),
            "checks_failed": sum(1 for c in self.checks if not c.passed),
            "checks": [asdict(c) for c in self.checks],
        }


# ── Individual checks ────────────────────────────────────────────────────────

def _check_has_greeting_str(resp: GreetResponse) -> CheckResult:
    ok = isinstance(getattr(resp, "greeting", None), str) and bool(resp.greeting)
    return CheckResult(
        check="has_greeting_str",
        verdict=Verdict.ACCEPT if ok else Verdict.REJECT,
        detail="" if ok else f"greeting={resp.greeting!r}",
    )


def _check_has_name_str(resp: GreetResponse) -> CheckResult:
    ok = isinstance(getattr(resp, "name", None), str) and bool(resp.name)
    return CheckResult(
        check="has_name_str",
        verdict=Verdict.ACCEPT if ok else Verdict.REJECT,
        detail="" if ok else f"name={resp.name!r}",
    )


def _check_capability_field(resp: GreetResponse) -> CheckResult:
    ok = getattr(resp, "capability", None) == CAPABILITY
    return CheckResult(
        check="capability_field_correct",
        verdict=Verdict.ACCEPT if ok else Verdict.REJECT,
        detail="" if ok else f"capability={resp.capability!r}",
    )


def _check_name_in_greeting(resp: GreetResponse) -> CheckResult:
    ok = resp.name in resp.greeting
    return CheckResult(
        check="name_in_greeting",
        verdict=Verdict.ACCEPT if ok else Verdict.REJECT,
        detail="" if ok else f"name={resp.name!r} not in greeting={resp.greeting!r}",
    )


def _check_default_name(resp_none: GreetResponse) -> CheckResult:
    ok = resp_none.name == "World"
    return CheckResult(
        check="default_name_is_world",
        verdict=Verdict.ACCEPT if ok else Verdict.REJECT,
        detail="" if ok else f"expected 'World', got {resp_none.name!r}",
    )


def _check_immutable(resp: GreetResponse) -> CheckResult:
    try:
        resp.greeting = "mutated"  # type: ignore[misc]
        return CheckResult(
            check="response_immutable",
            verdict=Verdict.REJECT,
            detail="mutation succeeded — response must be frozen",
        )
    except (AttributeError, TypeError):
        return CheckResult(check="response_immutable", verdict=Verdict.ACCEPT)


# ── Gate runner ──────────────────────────────────────────────────────────────

def run_gate() -> InvariantResult:
    """Execute all checks and return the aggregate InvariantResult."""
    resp_named = greet("Alice")
    resp_default = greet(None)
    resp_blank = greet("   ")

    raw_checks: List[CheckResult] = [
        _check_has_greeting_str(resp_named),
        _check_has_name_str(resp_named),
        _check_capability_field(resp_named),
        _check_name_in_greeting(resp_named),
        _check_default_name(resp_default),
        _check_default_name(resp_blank),
        _check_immutable(resp_named),
    ]

    any_fail = any(not c.passed for c in raw_checks)
    result = InvariantResult(
        verdict=Verdict.REJECT if any_fail else Verdict.ACCEPT,
        checks=raw_checks,
    )
    return result


# ── Standalone execution ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    result = run_gate()
    print(json.dumps(result.to_dict(), indent=2))
    sys.exit(0 if result.passed else 1)
