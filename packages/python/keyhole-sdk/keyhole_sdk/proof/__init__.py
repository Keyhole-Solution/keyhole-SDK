"""Proof-ready participant scaffolding — keyhole_sdk.proof.

CE-V5-S42-08: Proof-Ready Participant Scaffolding.

Prepares the developer kit to become a governed participant in later
recursive-governance flows once DEV-UX contract/proof surfaces stabilize.

**Support Status: SCAFFOLDED FOR LATER — NOT YET LIVE.**

The modules in this package are boundary-consuming placeholders.  They
define the *shape* of future participation without hardcoding unstable
platform internals or claiming that proof submission, contract
registration, or verdict handling are already operational.

What this package provides (all placeholder / future-facing):

    ParticipantContractPlaceholder  — provisional participant identity shape
    ProofBundlePlaceholder          — provisional proof-bundle assembly shape
    VerificationOutput              — normalized verification result shape
    VerificationRunner              — scaffold for local verification execution
    SupportStatus                   — enum distinguishing supported-now vs later
    ContractRegistrationAdapter     — adapter seam for future contract registration
    ProofSubmissionAdapter          — adapter seam for future proof submission
    VerdictRetrievalAdapter         — adapter seam for future verdict retrieval

What is **supported now** (via other SDK packages):

    - Capabilities discovery (keyhole_sdk.discovery)
    - Auth / identity bootstrap (keyhole_sdk.auth, keyhole_sdk.client)
    - Governed context retrieval (keyhole_sdk.context)
    - Read-only smoke path (keyhole_sdk.smoke)
    - Dispatch safety (keyhole_sdk.dispatch)

What is **not yet claimed**:

    - Live contract registration
    - Live proof submission
    - Promotion participation
    - Verdict/repair handling

See docs/proof-ready.md for the full posture explanation.
"""

from keyhole_sdk.proof.models import (
    ParticipantContractPlaceholder,
    ProofBundlePlaceholder,
    SupportStatus,
    VerificationOutput,
)
from keyhole_sdk.proof.runner import VerificationRunner
from keyhole_sdk.proof.adapters import (
    ContractRegistrationAdapter,
    ProofSubmissionAdapter,
    VerdictRetrievalAdapter,
)

__all__ = [
    # Placeholder models
    "ParticipantContractPlaceholder",
    "ProofBundlePlaceholder",
    "VerificationOutput",
    # Support status
    "SupportStatus",
    # Verification runner scaffold
    "VerificationRunner",
    # Adapter interfaces (future integration seams)
    "ContractRegistrationAdapter",
    "ProofSubmissionAdapter",
    "VerdictRetrievalAdapter",
]
