"""S41-01 Release Gate Module.

Wraps the validation checks into a single promotion gate that
returns an aggregate ACCEPT / REJECT verdict with full evidence.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .invariants import ALL_INVARIANT_IDS, InvariantResult, Verdict
from .validate import (
    check_contract_spec_exists,
    check_docs_no_forbidden_response_fields,
    check_inventory_complete,
    check_json_schema_matches_contract,
    check_mode_truthfulness,
    check_no_private_leakage,
    check_openapi_matches_contract,
    check_runtime_models_match_contract,
    check_sdk_models_match_contract,
    check_version_alignment,
)


@dataclass
class GateResult:
    """Aggregate result of the release gate evaluation."""

    verdict: Verdict
    invariant_results: List[InvariantResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def passed(self) -> bool:
        return self.verdict == Verdict.ACCEPT

    @property
    def failed_invariants(self) -> List[InvariantResult]:
        return [r for r in self.invariant_results if not r.passed]

    @property
    def passed_invariants(self) -> List[InvariantResult]:
        return [r for r in self.invariant_results if r.passed]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "timestamp": self.timestamp,
            "total_checks": len(self.invariant_results),
            "passed": len(self.passed_invariants),
            "failed": len(self.failed_invariants),
            "invariant_results": [asdict(r) for r in self.invariant_results],
        }

    def to_json(self) -> str:
        d = self.to_dict()
        # Convert Verdict enums in nested results
        for ir in d["invariant_results"]:
            ir["verdict"] = ir["verdict"].value if hasattr(ir["verdict"], "value") else ir["verdict"]
        return json.dumps(d, indent=2)


# ── All checks, grouped by invariant ────────────────────────────────────────

_ALL_CHECKS = [
    # INV-01: Public Surface Contract Closed
    check_contract_spec_exists,
    check_inventory_complete,
    # INV-03: CLI/SDK/Runtime Aligned
    check_sdk_models_match_contract,
    check_runtime_models_match_contract,
    check_openapi_matches_contract,
    check_json_schema_matches_contract,
    # INV-04: Docs/Examples Truthful
    check_docs_no_forbidden_response_fields,
    # INV-05: Mode Truthfulness
    check_mode_truthfulness,
    # INV-06: Public/Private Boundary Closed
    check_no_private_leakage,
    # INV-07: Publish Compatibility Closed
    check_version_alignment,
]


def run_release_gate(repo_root: Optional[Path] = None) -> GateResult:
    """Execute all S41-01 invariant checks and return aggregate result."""
    results: List[InvariantResult] = []
    for check_fn in _ALL_CHECKS:
        result = check_fn(repo_root)
        results.append(result)

    # Aggregate: ANY failure → REJECT
    overall = Verdict.ACCEPT if all(r.passed for r in results) else Verdict.REJECT

    return GateResult(verdict=overall, invariant_results=results)


def main() -> None:
    """CLI entry point — run the release gate and print results."""
    gate = run_release_gate()
    print(gate.to_json())
    raise SystemExit(0 if gate.passed else 1)


if __name__ == "__main__":
    main()
