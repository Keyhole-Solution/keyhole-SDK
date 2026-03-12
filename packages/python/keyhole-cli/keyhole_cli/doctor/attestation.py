"""`keyhole doctor` — CE-V5-S41-08 doctor truth & repair attestation.

Builds attestation artifacts from the complete doctor evaluation
cycle.  Attestation captures the final ACCEPT / REJECT truth.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from .contract import (
    DOCTOR_SCHEMA_VERSION,
    DiagnosticResult,
    DoctorAttestation,
    DoctorVerdict,
    ReasonCode,
    RepairPlan,
    VerificationResult,
    _canonical_json,
)


def build_doctor_attestation(
    *,
    diagnostic: DiagnosticResult,
    repair_plan: Optional[RepairPlan] = None,
    verification: Optional[VerificationResult] = None,
) -> DoctorAttestation:
    """Build the doctor truth & repair attestation per §15.5."""
    reason_codes: List[str] = list(diagnostic.reason_codes)

    # Determine final outcome
    if verification is not None:
        if verification.verified:
            final = DoctorVerdict.ACCEPT.value
            reason_codes.append(ReasonCode.REPAIR_VERIFICATION_PASSED.value)
            reason_codes.append(ReasonCode.DOCTOR_TRUTH_ACCEPTED.value)
        else:
            final = DoctorVerdict.REJECT.value
            reason_codes.append(ReasonCode.REPAIR_VERIFICATION_FAILED.value)
            reason_codes.append(ReasonCode.DOCTOR_TRUTH_REJECTED.value)
    else:
        final = diagnostic.final_posture
        if final == DoctorVerdict.ACCEPT.value:
            reason_codes.append(ReasonCode.DOCTOR_TRUTH_ACCEPTED.value)
        else:
            reason_codes.append(ReasonCode.DOCTOR_TRUTH_REJECTED.value)

    reason_codes.append(ReasonCode.NO_HIDDEN_MUTATION_ENFORCED.value)

    return DoctorAttestation(
        diagnostic_result_ref=diagnostic.diagnostic_run_id,
        repair_plan_ref=(
            repair_plan.plan_id if repair_plan else ""
        ),
        verification_result_ref=(
            verification.verification_id if verification else ""
        ),
        final_outcome=final,
        reason_codes=sorted(set(reason_codes)),
    )


def build_attestation_event(
    attestation: DoctorAttestation,
    *,
    lane: str = "dev",
    correlation_id: str = "",
) -> Dict[str, Any]:
    """Build an attestation event payload for Event Spine emission.

    This is metadata only — the CLI may choose to emit this when
    running in governed mode.
    """
    payload = attestation.to_dict()
    att_digest = hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()
    return {
        "schema": f"keyhole/{DOCTOR_SCHEMA_VERSION}",
        "version": "v1.0",
        "attestation_digest": att_digest,
        "attestation_id": attestation.attestation_id,
        "final_outcome": attestation.final_outcome,
        "reason_codes": attestation.reason_codes,
        "lane": lane,
        "correlation_id": correlation_id,
        "emitted_at": attestation.emitted_at,
        "payload": payload,
    }
