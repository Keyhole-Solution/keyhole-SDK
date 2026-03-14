"""Proof-ready placeholder models.

CE-V5-S42-08: Proof-Ready Participant Scaffolding.

Defines provisional data shapes for future participant contract posture,
proof-bundle assembly, and verification outputs.

**BOUNDARY POSTURE: These models are boundary-consuming placeholders.**

They are:
    - future-facing and provisional
    - not authoritative platform contract definitions
    - not final sealed schemas
    - awaiting stabilized DEV-UX boundary surfaces

They exist so that later recursive-governance integration is clean and
predictable, not so that builders treat scaffolding as live contract law.

Must never:
    - hardcode unstable platform internals
    - claim proof submission is already operational
    - define platform contract law from the participant side
    - blur the distinction between supported-now and planned-later
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────
# Support Status
# ──────────────────────────────────────────────────────────────

class SupportStatus(str, Enum):
    """Distinguishes current support level for SDK surfaces.

    Used to signal whether a capability is live and tested, scaffolded
    for future integration, or not yet available.
    """

    SUPPORTED = "supported"
    """Live and tested — safe for production use."""

    SCAFFOLDED = "scaffolded"
    """Shape exists but the platform surface is not yet stable.
    Local-only usage; not yet connected to live boundary flows."""

    NOT_YET_AVAILABLE = "not_yet_available"
    """No implementation exists yet.  Planned for future stories."""


# ──────────────────────────────────────────────────────────────
# Participant Contract Placeholder
# ──────────────────────────────────────────────────────────────

class ParticipantContractPlaceholder(BaseModel):
    """Provisional participant identity and contract posture.

    **Support status: SCAFFOLDED — not yet the live registered contract.**

    This placeholder captures the *shape* of information a governed
    participant will eventually declare when platform-side contract
    registration surfaces (DEV-UX-03) stabilize:

        - who is this participant
        - what verification classes it may later claim
        - what environments it supports
        - what scope or blast-radius posture it holds

    This model is:
        - boundary-consuming (shaped by expected platform expectations)
        - non-authoritative (not a sealed contract definition)
        - provisional (will evolve when DEV-UX surfaces stabilize)

    It must not be treated as a finalized contract registration payload.
    """

    support_status: SupportStatus = SupportStatus.SCAFFOLDED
    """Always SCAFFOLDED until live contract registration is operational."""

    # ── Participant identity ────────────────────────────────
    participant_name: str = "keyhole-developer-kit"
    """The canonical name of this participant repository."""

    participant_type: str = "external-developer-kit"
    """The participant category.  Provisional — will be constrained by
    the platform contract registry when it stabilizes."""

    repository_url: str = "https://github.com/Keyhole-Solution/keyhole-developer-kit"
    """Source repository for provenance tracking."""

    # ── Future verification classes ─────────────────────────
    verification_classes: List[str] = Field(default_factory=lambda: [
        "unit-tests",
        "contract-surface-tests",
        "boundary-smoke-tests",
    ])
    """Verification classes this participant may eventually claim.
    Provisional — the taxonomy is not yet sealed by the platform."""

    # ── Environment posture ─────────────────────────────────
    supported_environments: List[str] = Field(default_factory=lambda: [
        "local-only",
        "governed",
    ])
    """Environments this participant is designed to operate in."""

    supported_python_versions: List[str] = Field(default_factory=lambda: [
        "3.9", "3.10", "3.11", "3.12",
    ])
    """Python versions validated by the participant's test suite."""

    # ── Scope and compatibility ─────────────────────────────
    scope_hint: str = "public-sdk-and-cli"
    """Blast-radius or scope hint for future governance posture.
    Provisional — final scope taxonomy is platform-defined."""

    compatibility_posture: str = "boundary-consuming"
    """This participant consumes public boundary surfaces only.
    It does not define, extend, or govern those surfaces."""

    # ── Provisional notes ───────────────────────────────────
    notes: str = (
        "This is a provisional participant contract placeholder. "
        "It will be replaced by a live contract registration payload "
        "when platform-side DEV-UX-03 surfaces stabilize."
    )


# ──────────────────────────────────────────────────────────────
# Verification Output
# ──────────────────────────────────────────────────────────────

class VerificationOutput(BaseModel):
    """Normalized output from a single verification execution.

    **Support status: SCAFFOLDED.**

    Captures the kind of information a verification runner will
    produce for proof-bundle assembly.  The shape is deliberate
    but the exact fields may evolve when platform proof schemas
    (DEV-UX-04) stabilize.
    """

    verification_class: str = ""
    """The class of verification that was run (e.g., 'unit-tests')."""

    passed: bool = False
    """Whether the verification passed."""

    total_tests: int = 0
    """Total number of test cases executed."""

    passed_tests: int = 0
    """Number of test cases that passed."""

    failed_tests: int = 0
    """Number of test cases that failed."""

    skipped_tests: int = 0
    """Number of test cases that were skipped."""

    error_summary: str = ""
    """Summary of errors if the verification did not pass."""

    executed_at: Optional[datetime] = None
    """When the verification was executed (ISO-8601)."""

    duration_seconds: Optional[float] = None
    """Duration of the verification in seconds."""

    metadata: Dict[str, Any] = Field(default_factory=dict)
    """Extensible metadata for future schema evolution."""


# ──────────────────────────────────────────────────────────────
# Proof Bundle Placeholder
# ──────────────────────────────────────────────────────────────

class ProofBundlePlaceholder(BaseModel):
    """Provisional proof-bundle shape for future assembly and submission.

    **Support status: SCAFFOLDED — local assembly only, no live submission.**

    This placeholder represents the kind of proof-bearing artifact a
    governed participant would eventually assemble and submit to the
    platform's proof submission pipeline (DEV-UX-04).

    The shape aligns conceptually with expected platform expectations:
        - participant identity
        - source provenance (commit, ref)
        - verification outputs
        - environment metadata
        - context references
        - traceability fields
        - future signature / attestation sections

    This model is:
        - provisional and local-only
        - not a final platform proof schema
        - awaiting stabilized proof submission surfaces
        - boundary-consuming (shaped by expectations, not defining them)

    It must not be submitted to any endpoint as-is — the submission
    adapter will handle format translation when the surface stabilizes.
    """

    support_status: SupportStatus = SupportStatus.SCAFFOLDED
    """Always SCAFFOLDED until live proof submission is operational."""

    # ── Participant metadata ────────────────────────────────
    participant_name: str = ""
    """The participant submitting the proof."""

    participant_type: str = ""
    """The participant category."""

    # ── Provenance metadata ─────────────────────────────────
    source_repository: str = ""
    """Git repository URL."""

    source_commit: str = ""
    """Git commit SHA at the time of proof assembly."""

    source_ref: str = ""
    """Git branch or tag reference."""

    # ── Verification outputs ────────────────────────────────
    verification_outputs: List[VerificationOutput] = Field(default_factory=list)
    """Collected verification results included in this proof bundle."""

    # ── Environment metadata ────────────────────────────────
    environment: str = "local-only"
    """The environment where verification was executed."""

    python_version: str = ""
    """Python version used for verification."""

    sdk_version: str = ""
    """SDK version used during verification."""

    platform_info: str = ""
    """Operating system / platform identification."""

    # ── Context references ──────────────────────────────────
    context_digest: str = ""
    """Digest from the most recent governed context retrieval, if any."""

    capabilities_contract_version: str = ""
    """MCP contract version from the most recent capabilities discovery."""

    # ── Traceability fields ─────────────────────────────────
    assembled_at: Optional[datetime] = None
    """Timestamp of proof bundle assembly."""

    bundle_digest: str = ""
    """A local digest of this bundle's contents (future integrity check)."""

    # ── Future signature / attestation ──────────────────────
    signature: str = ""
    """Reserved for future cryptographic signature.
    Not populated until platform attestation surfaces stabilize."""

    attestation_chain: List[str] = Field(default_factory=list)
    """Reserved for future attestation chain references.
    Not populated until platform attestation surfaces stabilize."""

    # ── Provisional notes ───────────────────────────────────
    notes: str = (
        "This is a provisional proof-bundle placeholder. "
        "It will be replaced by a submission-ready payload "
        "when platform-side DEV-UX-04 surfaces stabilize."
    )

    def add_verification(self, output: VerificationOutput) -> None:
        """Add a verification output to this bundle."""
        self.verification_outputs.append(output)

    @property
    def all_passed(self) -> bool:
        """True if all verification outputs passed."""
        return (
            len(self.verification_outputs) > 0
            and all(v.passed for v in self.verification_outputs)
        )

    @property
    def verification_summary(self) -> Dict[str, Any]:
        """Summary of verification results for display."""
        total = len(self.verification_outputs)
        passed = sum(1 for v in self.verification_outputs if v.passed)
        return {
            "total_verifications": total,
            "passed": passed,
            "failed": total - passed,
            "all_passed": self.all_passed,
        }
