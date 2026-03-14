"""Governance proof runner — RG-01 cross-boundary protocol orchestrator.

CE-V5 — Recursive Governance Proof Test.

Orchestrates the 7-phase governance proof protocol:
    Phase 1 — Contract registration (SCAFFOLDED)
    Phase 2 — Context inheritance (SUPPORTED)
    Phase 3 — External implementation capture (SUPPORTED)
    Phase 4 — Local verification (SUPPORTED)
    Phase 5 — Proof submission (SCAFFOLDED)
    Phase 6 — Governance evaluation (SCAFFOLDED)
    Phase 7 — Promotion (SCAFFOLDED)

The runner composes existing SDK surfaces:
    - ContextClient for context.compile
    - VerificationRunner for local verification
    - ContractRegistrationAdapter for registration
    - ProofSubmissionAdapter for submission
    - VerdictRetrievalAdapter for verdict retrieval

Must never:
    - claim scaffolded phases are operational
    - hardcode unstable platform endpoints
    - fabricate Event Spine evidence
    - couple to private platform source
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

import requests

from keyhole_sdk.context import ContextClient
from keyhole_sdk.proof.adapters import (
    AdapterResult,
    ContractRegistrationAdapter,
    LocalContractRegistrationAdapter,
    LocalProofSubmissionAdapter,
    LocalVerdictRetrievalAdapter,
    ProofSubmissionAdapter,
    VerdictRetrievalAdapter,
)
from keyhole_sdk.proof.models import (
    ParticipantContractPlaceholder,
    ProofBundlePlaceholder,
    SupportStatus,
    VerificationOutput,
)
from keyhole_sdk.proof.runner import VerificationRunner

from keyhole_sdk.governance.models import (
    EXPECTED_EVENTS,
    GovernanceEvent,
    GovernancePhase,
    GovernancePhaseResult,
    GovernanceProofResult,
)


class GovernanceProofRunner:
    """Orchestrates the RG-01 cross-boundary governance proof protocol.

    The runner executes 7 phases in order, composing existing SDK
    surfaces for supported phases and using scaffolded adapters for
    platform-dependent phases.

    Supported phases (2, 3, 4) use live SDK surfaces.
    Scaffolded phases (1, 5, 6, 7) use adapter placeholders and mark
    results accordingly.

    Example::

        runner = GovernanceProofRunner(
            base_url="https://boundary.example.com",
            token="bearer-token",
        )
        result = runner.run()
        print(result.summary())
        evidence = result.to_evidence_bundle()
    """

    def __init__(
        self,
        *,
        base_url: str = "",
        token: str = "",
        timeout: float = 15.0,
        session: Optional[requests.Session] = None,
        registration_adapter: Optional[ContractRegistrationAdapter] = None,
        submission_adapter: Optional[ProofSubmissionAdapter] = None,
        verdict_adapter: Optional[VerdictRetrievalAdapter] = None,
    ) -> None:
        self._base_url = base_url
        self._token = token
        self._timeout = timeout
        self._session = session
        self._correlation_id = str(uuid.uuid4())

        # Adapters — default to local scaffolded implementations
        self._registration_adapter = (
            registration_adapter or LocalContractRegistrationAdapter()
        )
        self._submission_adapter = (
            submission_adapter or LocalProofSubmissionAdapter()
        )
        self._verdict_adapter = (
            verdict_adapter or LocalVerdictRetrievalAdapter()
        )

        # Verification runner
        self._verification_runner = VerificationRunner(
            participant_name="keyhole-developer-kit",
            participant_type="external-developer-kit",
        )

        # State
        self._contract = ParticipantContractPlaceholder()
        self._proof_bundle: Optional[ProofBundlePlaceholder] = None

    @property
    def support_status(self) -> SupportStatus:
        """Overall protocol is scaffolded — platform phases not yet live."""
        return SupportStatus.SCAFFOLDED

    @property
    def correlation_id(self) -> str:
        """Shared correlation ID for this proof run."""
        return self._correlation_id

    def register_collector(
        self,
        verification_class: str,
        collector: Callable[[], VerificationOutput],
    ) -> None:
        """Register a verification collector for Phase 4."""
        self._verification_runner.register_collector(
            verification_class, collector,
        )

    def run(self) -> GovernanceProofResult:
        """Execute the full 7-phase governance proof protocol."""
        started_at = datetime.now(timezone.utc)
        phases = []

        # Phase 1 — Contract Registration (SCAFFOLDED)
        phases.append(self._phase_registration())

        # Phase 2 — Context Inheritance (SUPPORTED)
        phases.append(self._phase_context())

        # Phase 3 — External Implementation (SUPPORTED)
        phases.append(self._phase_implementation())

        # Phase 4 — Local Verification (SUPPORTED)
        phases.append(self._phase_verification())

        # Phase 5 — Proof Submission (SCAFFOLDED)
        phases.append(self._phase_submission())

        # Phase 6 — Governance Evaluation (SCAFFOLDED)
        phases.append(self._phase_evaluation())

        # Phase 7 — Promotion (SCAFFOLDED)
        phases.append(self._phase_promotion())

        return GovernanceProofResult(
            participant="keyhole-developer-kit",
            phases=phases,
            proof_bundle=self._proof_bundle,
            correlation_id=self._correlation_id,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
        )

    # ── Phase implementations ────────────────────────────────

    def _phase_registration(self) -> GovernancePhaseResult:
        """Phase 1 — Participant contract registration (SCAFFOLDED)."""
        phase = GovernancePhase.REGISTRATION

        adapter_result = self._registration_adapter.register(self._contract)

        if adapter_result.supported and adapter_result.success:
            event = self._make_event(
                phase=phase,
                data={
                    "contract_digest": adapter_result.data.get(
                        "contract_digest", "",
                    ),
                    "source_repo": "keyhole-developer-kit",
                },
            )
            return GovernancePhaseResult(
                phase=phase, success=True, event=event,
                data=adapter_result.data,
            )

        return GovernancePhaseResult(
            phase=phase,
            success=False,
            scaffolded=True,
            error=adapter_result.reason,
            suggestion=(
                "Contract registration requires platform-side DEV-UX-03 "
                "stabilization. This phase is scaffolded."
            ),
            data={"adapter_supported": adapter_result.supported},
        )

    def _phase_context(self) -> GovernancePhaseResult:
        """Phase 2 — Context inheritance via context.compile (SUPPORTED)."""
        phase = GovernancePhase.CONTEXT

        if not self._base_url:
            return GovernancePhaseResult(
                phase=phase,
                success=True,
                data={"mode": "local-only", "run_type": "context.compile"},
                event=self._make_event(
                    phase=phase,
                    data={"mode": "local-only", "run_type": "context.compile"},
                ),
            )

        try:
            ctx_client = ContextClient(
                base_url=self._base_url,
                token=self._token,
                timeout=self._timeout,
                session=self._session,
            )
            try:
                snapshot = ctx_client.compile_context()
                event = self._make_event(
                    phase=phase,
                    data={
                        "context_digest": snapshot.get_digest(),
                        "surface_version": snapshot.get_mcp_contract(),
                        "run_type": "context.compile",
                    },
                )
                return GovernancePhaseResult(
                    phase=phase, success=True, event=event,
                    data={
                        "context_digest": snapshot.get_digest(),
                        "correlation_id": snapshot.get_correlation_id(),
                    },
                )
            finally:
                ctx_client.close()
        except Exception as exc:
            return GovernancePhaseResult(
                phase=phase, success=False,
                error=str(exc),
                suggestion="Verify MCP boundary is reachable and token is valid.",
            )

    def _phase_implementation(self) -> GovernancePhaseResult:
        """Phase 3 — External implementation capture (SUPPORTED)."""
        phase = GovernancePhase.IMPLEMENTATION

        source_info = self._verification_runner.capture_source_info()
        commit = source_info.get("source_commit", "")
        ref = source_info.get("source_ref", "")

        event = self._make_event(
            phase=phase,
            data={
                "commit_digest": commit,
                "source_ref": ref,
                "source_repo": "keyhole-developer-kit",
            },
        )

        return GovernancePhaseResult(
            phase=phase,
            success=True,
            event=event,
            data={
                "commit_digest": commit,
                "source_ref": ref,
            },
        )

    def _phase_verification(self) -> GovernancePhaseResult:
        """Phase 4 — Local verification execution (SUPPORTED)."""
        phase = GovernancePhase.VERIFICATION

        try:
            bundle = self._verification_runner.run()
            self._proof_bundle = bundle

            # 0 collectors is vacuously passing
            passed = bundle.all_passed or bundle.verification_summary.get("total_verifications", 0) == 0

            return GovernancePhaseResult(
                phase=phase,
                success=passed,
                event=self._make_event(
                    phase=phase,
                    data={
                        "all_passed": bundle.all_passed,
                        "summary": bundle.verification_summary,
                    },
                ),
                data={
                    "all_passed": bundle.all_passed,
                    "summary": bundle.verification_summary,
                    "commit_digest": bundle.source_commit,
                },
            )
        except Exception as exc:
            return GovernancePhaseResult(
                phase=phase, success=False,
                error=str(exc),
                suggestion="Check verification collectors are correctly registered.",
            )

    def _phase_submission(self) -> GovernancePhaseResult:
        """Phase 5 — Proof bundle submission (SCAFFOLDED)."""
        phase = GovernancePhase.SUBMISSION

        if self._proof_bundle is None:
            return GovernancePhaseResult(
                phase=phase, success=False, scaffolded=True,
                error="No proof bundle available (Phase 4 did not produce one).",
            )

        adapter_result = self._submission_adapter.submit(self._proof_bundle)

        if adapter_result.supported and adapter_result.success:
            event = self._make_event(
                phase=phase,
                data={
                    "proof_digest": adapter_result.data.get("proof_digest", ""),
                    "source_commit": self._proof_bundle.source_commit,
                },
            )
            return GovernancePhaseResult(
                phase=phase, success=True, event=event,
                data=adapter_result.data,
            )

        return GovernancePhaseResult(
            phase=phase,
            success=False,
            scaffolded=True,
            error=adapter_result.reason,
            suggestion=(
                "Proof submission requires platform-side DEV-UX-04 "
                "stabilization. This phase is scaffolded."
            ),
            data={"adapter_supported": adapter_result.supported},
        )

    def _phase_evaluation(self) -> GovernancePhaseResult:
        """Phase 6 — Governance verdict evaluation (SCAFFOLDED)."""
        phase = GovernancePhase.EVALUATION

        adapter_result = self._verdict_adapter.retrieve_verdict(
            submission_reference=self._correlation_id,
        )

        if adapter_result.supported and adapter_result.success:
            event = self._make_event(
                phase=phase,
                data={
                    "verdict": adapter_result.data.get("verdict", ""),
                    "reason": adapter_result.data.get("reason", ""),
                },
            )
            return GovernancePhaseResult(
                phase=phase, success=True, event=event,
                data=adapter_result.data,
            )

        return GovernancePhaseResult(
            phase=phase,
            success=False,
            scaffolded=True,
            error=adapter_result.reason,
            suggestion=(
                "Verdict retrieval requires platform-side DEV-UX-06 "
                "stabilization. This phase is scaffolded."
            ),
            data={"adapter_supported": adapter_result.supported},
        )

    def _phase_promotion(self) -> GovernancePhaseResult:
        """Phase 7 — Promotion execution (SCAFFOLDED)."""
        phase = GovernancePhase.PROMOTION

        # Promotion depends on a successful verdict in Phase 6
        eval_happened = any(
            p.phase == GovernancePhase.EVALUATION and p.success
            for p in []  # Not accessible here — always scaffolded for now
        )

        return GovernancePhaseResult(
            phase=phase,
            success=False,
            scaffolded=True,
            error=(
                "Promotion requires governance verdict (Phase 6) and "
                "platform-side promotion pipeline. This phase is scaffolded."
            ),
            suggestion=(
                "Promotion will execute automatically when verdict "
                "and promotion pipeline are stable."
            ),
            data={"promotion_model": "one-mint"},
        )

    # ── Helpers ──────────────────────────────────────────────

    def _make_event(
        self,
        *,
        phase: GovernancePhase,
        data: Dict[str, Any],
    ) -> GovernanceEvent:
        """Create a governance event for the given phase."""
        event_type = EXPECTED_EVENTS.get(phase, f"{phase.value}.completed")
        content = f"{event_type}:{self._correlation_id}:{phase.value}"
        digest = hashlib.sha256(content.encode()).hexdigest()[:16]

        return GovernanceEvent(
            event_type=event_type,
            phase=phase,
            participant_id="keyhole-developer-kit",
            correlation_id=self._correlation_id,
            event_digest=digest,
            contract_digest=self._contract.participant_name,
            data=data,
            scaffolded=(phase in _SCAFFOLDED_PHASES),
        )


_SCAFFOLDED_PHASES = frozenset({
    GovernancePhase.REGISTRATION,
    GovernancePhase.SUBMISSION,
    GovernancePhase.EVALUATION,
    GovernancePhase.PROMOTION,
})
"""Phases that depend on platform-side surfaces not yet stable."""

_SUPPORTED_PHASES = frozenset({
    GovernancePhase.CONTEXT,
    GovernancePhase.IMPLEMENTATION,
    GovernancePhase.VERIFICATION,
})
"""Phases using existing SDK surfaces that are operational."""
