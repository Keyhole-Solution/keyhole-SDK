"""S41-01 Invariant Definitions.

Machine-enforceable invariant set for the public Keyhole developer surface.
Each invariant is a named check with an ID, description, and validation method.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class Verdict(Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


@dataclass
class InvariantResult:
    invariant_id: str
    name: str
    verdict: Verdict
    reasons: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.verdict == Verdict.ACCEPT


# ── Invariant IDs ───────────────────────────────────────────────────────────

INV_PUBLIC_SURFACE_CONTRACT_CLOSED = "S41-01-INV-01"
INV_PUBLIC_SURFACE_PROMOTION_GATED = "S41-01-INV-02"
INV_CLI_SDK_RUNTIME_ALIGNED = "S41-01-INV-03"
INV_DOCS_EXAMPLES_TRUTHFUL = "S41-01-INV-04"
INV_MODE_TRUTHFULNESS = "S41-01-INV-05"
INV_PUBLIC_PRIVATE_BOUNDARY_CLOSED = "S41-01-INV-06"
INV_PUBLISH_COMPATIBILITY_CLOSED = "S41-01-INV-07"

ALL_INVARIANT_IDS = [
    INV_PUBLIC_SURFACE_CONTRACT_CLOSED,
    INV_PUBLIC_SURFACE_PROMOTION_GATED,
    INV_CLI_SDK_RUNTIME_ALIGNED,
    INV_DOCS_EXAMPLES_TRUTHFUL,
    INV_MODE_TRUTHFULNESS,
    INV_PUBLIC_PRIVATE_BOUNDARY_CLOSED,
    INV_PUBLISH_COMPATIBILITY_CLOSED,
]

INVARIANT_NAMES = {
    INV_PUBLIC_SURFACE_CONTRACT_CLOSED: "PUBLIC-SURFACE-CONTRACT-CLOSED",
    INV_PUBLIC_SURFACE_PROMOTION_GATED: "PUBLIC-SURFACE-PROMOTION-GATED",
    INV_CLI_SDK_RUNTIME_ALIGNED: "CLI-SDK-RUNTIME-ALIGNED",
    INV_DOCS_EXAMPLES_TRUTHFUL: "DOCS-EXAMPLES-TRUTHFUL",
    INV_MODE_TRUTHFULNESS: "MODE-TRUTHFULNESS",
    INV_PUBLIC_PRIVATE_BOUNDARY_CLOSED: "PUBLIC-PRIVATE-BOUNDARY-CLOSED",
    INV_PUBLISH_COMPATIBILITY_CLOSED: "PUBLISH-COMPATIBILITY-CLOSED",
}

INVARIANT_DESCRIPTIONS = {
    INV_PUBLIC_SURFACE_CONTRACT_CLOSED: (
        "The public Keyhole developer surface exists as a bounded, declared "
        "contract with explicit inventory, mode truth rules, and public/private "
        "separation."
    ),
    INV_PUBLIC_SURFACE_PROMOTION_GATED: (
        "No canonical public developer release may advance unless the promotion "
        "controller verifies contract, compatibility, and truthfulness invariants."
    ),
    INV_CLI_SDK_RUNTIME_ALIGNED: (
        "The CLI, SDK, and runtime agree on the current public contract and "
        "mode semantics."
    ),
    INV_DOCS_EXAMPLES_TRUTHFUL: (
        "All public docs and examples match the currently implemented public "
        "runtime and SDK behavior."
    ),
    INV_MODE_TRUTHFULNESS: (
        "Local-only and governed behavior are distinguished explicitly and "
        "truthfully wherever behavior differs."
    ),
    INV_PUBLIC_PRIVATE_BOUNDARY_CLOSED: (
        "The public repo does not leak private platform details or protected "
        "operational internals."
    ),
    INV_PUBLISH_COMPATIBILITY_CLOSED: (
        "A public package, image, or docs release does not advance unless the "
        "released surface is compatible across runtime, SDK, CLI, docs, examples, "
        "and published metadata."
    ),
}
