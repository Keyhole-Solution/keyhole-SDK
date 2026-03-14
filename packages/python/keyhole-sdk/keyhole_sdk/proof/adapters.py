"""Adapter interfaces for future platform integration.

CE-V5-S42-08: Proof-Ready Participant Scaffolding.

Defines adapter seam boundaries for future:
    - contract registration (DEV-UX-03)
    - proof submission (DEV-UX-04)
    - verdict retrieval / interpretation (DEV-UX-06)

**Support status: SCAFFOLDED — interfaces only, no live integration.**

These adapters are boundary-consuming: they exist so that when platform-side
recursive-governance surfaces stabilize, the developer kit can connect
cleanly without rewiring the rest of the repo.

Each adapter is a minimal abstract base that defines the expected
interaction shape.  Concrete implementations will be provided when
the platform surfaces they depend on are stable and published.

Must never:
    - hardcode unstable platform endpoint contracts
    - pretend live integration is operational
    - define platform-side contract shapes authoritatively
    - couple to private platform source
    - submit to undisclosed endpoints
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from keyhole_sdk.proof.models import (
    ParticipantContractPlaceholder,
    ProofBundlePlaceholder,
    SupportStatus,
)


# ──────────────────────────────────────────────────────────────
# Adapter Result
# ──────────────────────────────────────────────────────────────

class AdapterResult:
    """Result from an adapter operation.

    Provides a uniform response shape for all adapter calls.
    When the adapter is not yet connected to a live surface,
    ``supported`` is False and ``reason`` explains why.
    """

    __slots__ = ("supported", "success", "reason", "data")

    def __init__(
        self,
        *,
        supported: bool = False,
        success: bool = False,
        reason: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.supported = supported
        self.success = success
        self.reason = reason
        self.data = data or {}

    def __repr__(self) -> str:
        return (
            f"AdapterResult(supported={self.supported}, "
            f"success={self.success}, reason={self.reason!r})"
        )


def _not_yet_available(operation: str) -> AdapterResult:
    """Standard result for operations not yet connected to live surfaces."""
    return AdapterResult(
        supported=False,
        success=False,
        reason=(
            f"{operation} is not yet available. "
            f"Platform-side surfaces are still stabilizing. "
            f"This adapter is scaffolded for future integration "
            f"(CE-V5-S42-08)."
        ),
    )


# ──────────────────────────────────────────────────────────────
# Contract Registration Adapter
# ──────────────────────────────────────────────────────────────

class ContractRegistrationAdapter(ABC):
    """Adapter seam for future participant contract registration.

    **Support status: SCAFFOLDED — awaiting DEV-UX-03 stabilization.**

    When the platform-side participant contract registry (DEV-UX-03)
    stabilizes, a concrete implementation of this adapter will handle:
        - translating the participant contract placeholder into the
          platform's expected registration format
        - submitting the registration through the published surface
        - returning the registration result

    The abstract interface is intentionally narrow to minimize the
    coupling surface that will need to change.
    """

    @property
    def support_status(self) -> SupportStatus:
        """Current support status of this adapter."""
        return SupportStatus.SCAFFOLDED

    @abstractmethod
    def register(
        self,
        contract: ParticipantContractPlaceholder,
    ) -> AdapterResult:
        """Submit a participant contract for registration.

        Not yet operational.  Concrete implementations will be
        provided when DEV-UX-03 stabilizes.
        """


class LocalContractRegistrationAdapter(ContractRegistrationAdapter):
    """Local-only contract registration adapter.

    Returns a not-yet-available result for all operations.
    This is the default adapter until platform surfaces stabilize.
    """

    def register(
        self,
        contract: ParticipantContractPlaceholder,
    ) -> AdapterResult:
        """No-op: contract registration is not yet available."""
        return _not_yet_available("Contract registration")


# ──────────────────────────────────────────────────────────────
# Proof Submission Adapter
# ──────────────────────────────────────────────────────────────

class ProofSubmissionAdapter(ABC):
    """Adapter seam for future proof-bundle submission.

    **Support status: SCAFFOLDED — awaiting DEV-UX-04 stabilization.**

    When the platform-side proof submission pipeline (DEV-UX-04)
    stabilizes, a concrete implementation of this adapter will handle:
        - translating the proof-bundle placeholder into the platform's
          expected submission format
        - submitting the bundle through the published surface
        - returning the submission acknowledgement

    The abstract interface is intentionally narrow.
    """

    @property
    def support_status(self) -> SupportStatus:
        """Current support status of this adapter."""
        return SupportStatus.SCAFFOLDED

    @abstractmethod
    def submit(
        self,
        bundle: ProofBundlePlaceholder,
    ) -> AdapterResult:
        """Submit a proof bundle.

        Not yet operational.  Concrete implementations will be
        provided when DEV-UX-04 stabilizes.
        """


class LocalProofSubmissionAdapter(ProofSubmissionAdapter):
    """Local-only proof submission adapter.

    Returns a not-yet-available result for all operations.
    This is the default adapter until platform surfaces stabilize.
    """

    def submit(
        self,
        bundle: ProofBundlePlaceholder,
    ) -> AdapterResult:
        """No-op: proof submission is not yet available."""
        return _not_yet_available("Proof submission")


# ──────────────────────────────────────────────────────────────
# Verdict Retrieval Adapter
# ──────────────────────────────────────────────────────────────

class VerdictRetrievalAdapter(ABC):
    """Adapter seam for future verdict retrieval and interpretation.

    **Support status: SCAFFOLDED — awaiting DEV-UX-06 stabilization.**

    When the platform-side structured verdict and repair artifacts
    (DEV-UX-06) stabilize, a concrete implementation of this adapter
    will handle:
        - querying the platform for verdicts on submitted proof
        - interpreting verdict results
        - extracting repair guidance when verdicts indicate failure

    The abstract interface is intentionally narrow.
    """

    @property
    def support_status(self) -> SupportStatus:
        """Current support status of this adapter."""
        return SupportStatus.SCAFFOLDED

    @abstractmethod
    def retrieve_verdict(
        self,
        submission_reference: str,
    ) -> AdapterResult:
        """Retrieve a verdict for a previously submitted proof bundle.

        Not yet operational.  Concrete implementations will be
        provided when DEV-UX-06 stabilizes.

        Args:
            submission_reference: An identifier for the submission
                whose verdict is being queried.
        """

    @abstractmethod
    def get_repair_guidance(
        self,
        verdict_reference: str,
    ) -> AdapterResult:
        """Retrieve repair guidance for a failed verdict.

        Not yet operational.  Concrete implementations will be
        provided when DEV-UX-06 stabilizes.

        Args:
            verdict_reference: An identifier for the verdict
                whose repair guidance is being requested.
        """


class LocalVerdictRetrievalAdapter(VerdictRetrievalAdapter):
    """Local-only verdict retrieval adapter.

    Returns a not-yet-available result for all operations.
    This is the default adapter until platform surfaces stabilize.
    """

    def retrieve_verdict(
        self,
        submission_reference: str,
    ) -> AdapterResult:
        """No-op: verdict retrieval is not yet available."""
        return _not_yet_available("Verdict retrieval")

    def get_repair_guidance(
        self,
        verdict_reference: str,
    ) -> AdapterResult:
        """No-op: repair guidance retrieval is not yet available."""
        return _not_yet_available("Repair guidance retrieval")
