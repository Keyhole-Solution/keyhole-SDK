"""SDK-CLIENT-23 — Local identity coherence classification engine (§D).

Reads CLI credentials, discovered host attestations, and any
split-identity override to produce a deterministic coherence verdict.

Decision logic (from spec):
  - No host attestation → WARNING_NO_HOST_ATTESTATION
  - Host attestation stale → WARNING_STALE_HOST_ATTESTATION
  - Host attestation unknown/probable confidence → WARNING_UNKNOWN_HOST_IDENTITY
  - Fresh confirmed, principal matches → ACCEPT_MATCH
  - Fresh confirmed, principal conflicts, override present → ACCEPT_INTENTIONAL_SPLIT
  - Fresh confirmed, principal conflicts, no override → REJECT_HOST_CONFLICT

Hard conflict rule: ONLY a fresh confirmed conflicting attestation
triggers REJECT_HOST_CONFLICT.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from keyhole_sdk.doctor.models import (
    AttestationConfidence,
    CoherenceVerdict,
    HostIdentityAttestation,
    IdentityPolicyOverride,
)


@dataclass
class CoherenceResult:
    """Full coherence classification output."""

    verdict: CoherenceVerdict
    cli_principal: str = ""
    conflicting_attestations: List[HostIdentityAttestation] = field(default_factory=list)
    matching_attestations: List[HostIdentityAttestation] = field(default_factory=list)
    stale_attestations: List[HostIdentityAttestation] = field(default_factory=list)
    unknown_attestations: List[HostIdentityAttestation] = field(default_factory=list)
    override: Optional[IdentityPolicyOverride] = None
    description: str = ""
    fix_steps: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "verdict": self.verdict.value,
            "cli_principal": self.cli_principal,
            "conflicting_hosts": [a.host_kind for a in self.conflicting_attestations],
            "matching_hosts": [a.host_kind for a in self.matching_attestations],
            "stale_hosts": [a.host_kind for a in self.stale_attestations],
            "unknown_hosts": [a.host_kind for a in self.unknown_attestations],
            "has_override": self.override is not None,
            "description": self.description,
            "fix_steps": self.fix_steps,
        }


def _principals_match(a: str, b: str) -> bool:
    """Case-insensitive principal comparison."""
    return a.strip().lower() == b.strip().lower()


def classify_coherence(
    *,
    cli_principal: str,
    attestations: List[HostIdentityAttestation],
    override: Optional[IdentityPolicyOverride] = None,
    now: Optional[datetime] = None,
) -> CoherenceResult:
    """Classify the identity coherence state of this workstation.

    Returns a CoherenceResult with verdict, explanations, and fix steps.
    """
    if not cli_principal:
        if not attestations:
            return CoherenceResult(
                verdict=CoherenceVerdict.WARNING_NO_HOST_ATTESTATION,
                cli_principal="",
                description=(
                    "CLI identity is not verified. "
                    "No host attestations found."
                ),
                fix_steps=[
                    "Run: keyhole whoami",
                    "Run: keyhole host attest",
                    "Re-run: keyhole doctor",
                ],
            )
        return CoherenceResult(
            verdict=CoherenceVerdict.WARNING_NO_HOST_ATTESTATION,
            cli_principal="",
            description=(
                "CLI identity is not verified. "
                "Cannot compare against host attestations."
            ),
            fix_steps=[
                "Run: keyhole whoami",
                "Re-run: keyhole doctor",
            ],
        )

    if not attestations:
        return CoherenceResult(
            verdict=CoherenceVerdict.WARNING_NO_HOST_ATTESTATION,
            cli_principal=cli_principal,
            description="No host identity attestations found. Host environments have not been inspected.",
            fix_steps=[
                "Open VS Code where the Keyhole host is installed.",
                "Run the Keyhole host identity attestation helper.",
                "Re-run: keyhole doctor",
            ],
        )

    matching: List[HostIdentityAttestation] = []
    conflicting: List[HostIdentityAttestation] = []
    stale: List[HostIdentityAttestation] = []
    unknown: List[HostIdentityAttestation] = []

    for att in attestations:
        if not att.is_fresh(now=now):
            stale.append(att)
            continue

        if att.confidence != AttestationConfidence.CONFIRMED:
            unknown.append(att)
            continue

        # Fresh and confirmed — compare principals
        if _principals_match(att.effective_principal, cli_principal):
            matching.append(att)
        else:
            conflicting.append(att)

    # Decision tree
    if conflicting:
        # Check for valid override
        if override and not override.is_expired(now=now):
            return CoherenceResult(
                verdict=CoherenceVerdict.ACCEPT_INTENTIONAL_SPLIT,
                cli_principal=cli_principal,
                conflicting_attestations=conflicting,
                matching_attestations=matching,
                stale_attestations=stale,
                unknown_attestations=unknown,
                override=override,
                description=(
                    f"Identity split allowed by override. "
                    f"CLI: {cli_principal}, "
                    f"Host: {conflicting[0].effective_principal}"
                ),
            )

        host_labels = ", ".join(
            f"{a.host_display_name or a.host_kind} ({a.effective_principal})"
            for a in conflicting
        )
        return CoherenceResult(
            verdict=CoherenceVerdict.REJECT_HOST_CONFLICT,
            cli_principal=cli_principal,
            conflicting_attestations=conflicting,
            matching_attestations=matching,
            stale_attestations=stale,
            unknown_attestations=unknown,
            description=(
                f"Fresh confirmed host conflict detected. "
                f"CLI: {cli_principal}, "
                f"Hosts: {host_labels}"
            ),
            fix_steps=[
                "Open VS Code where the Keyhole host is installed.",
                "Confirm the host is acting as the intended user.",
                "If the host is bound to the wrong user, sign out of the Keyhole host connection in VS Code.",
                "Re-authenticate VS Code as the intended user.",
                "Re-run the host attestation helper.",
                "Re-run: keyhole doctor",
                "Retry: keyhole login",
                "Or use: keyhole login --allow-split-identity",
            ],
        )

    if matching:
        return CoherenceResult(
            verdict=CoherenceVerdict.ACCEPT_MATCH,
            cli_principal=cli_principal,
            matching_attestations=matching,
            stale_attestations=stale,
            unknown_attestations=unknown,
            description=f"CLI and host identities match: {cli_principal}",
        )

    if stale:
        return CoherenceResult(
            verdict=CoherenceVerdict.WARNING_STALE_HOST_ATTESTATION,
            cli_principal=cli_principal,
            stale_attestations=stale,
            unknown_attestations=unknown,
            description=(
                "Host attestation(s) are stale. "
                "Refresh attestation for strong coherence checks."
            ),
            fix_steps=[
                "Open VS Code where the Keyhole host is installed.",
                "Re-run the Keyhole host identity attestation helper.",
                "Re-run: keyhole doctor",
            ],
        )

    # Only unknown/probable attestations remain
    return CoherenceResult(
        verdict=CoherenceVerdict.WARNING_UNKNOWN_HOST_IDENTITY,
        cli_principal=cli_principal,
        unknown_attestations=unknown,
        description=(
            "Host identity could not be confirmed. "
            "Proof method may be degraded."
        ),
        fix_steps=[
            "Open VS Code where the Keyhole host is installed.",
            "Run the Keyhole host identity attestation helper with live whoami.",
            "Re-run: keyhole doctor",
        ],
    )
