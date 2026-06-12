from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GateResult:
    invariant_id: str
    verdict: str
    details: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return {
            "invariant_id": self.invariant_id,
            "verdict": self.verdict,
            "details": self.details,
        }


def run_gate() -> GateResult:
    sample = {"echo": "Hello, Ada", "name": "Ada"}
    verdict = "ACCEPT" if isinstance(sample["echo"], str) and isinstance(sample["name"], str) else "REJECT"
    return GateResult(
        invariant_id="SECOND-GOVERNED-APP-INV-01",
        verdict=verdict,
        details={"capability": "second-governed-app.echo.user.v1"},
    )
