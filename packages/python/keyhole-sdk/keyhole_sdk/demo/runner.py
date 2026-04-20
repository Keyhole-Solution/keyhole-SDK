"""Recursive demo flow runner.

CE-V5-S42-09: Recursive Demo Readiness Pack.

Composes the full external-side recursive governance demo into a
scriptable, deterministic, and boundary-consuming flow.

The runner orchestrates:
    1. Discovery — retrieve boundary capabilities
    2. Identity — inspect authenticated participant
    3. Context — retrieve governed context
    4. Posture — confirm participant contract posture
    5. Verification — execute local verification collectors
    6. Bundle — assemble proof bundle from results
    7. Handoff — attempt proof submission (scaffolded)

Each phase produces a :class:`DemoStepResult`.  The aggregate
:class:`DemoResult` contains all phase results plus the proof bundle.

**Boundary posture: boundary-consuming.**

This runner composes existing SDK client surfaces.  It does not
define platform contract shapes or claim platform-side governance
is operational.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from keyhole_sdk.discovery.client import CapabilitiesClient
from keyhole_sdk.context.client import ContextClient
from keyhole_sdk.exceptions import (
    AuthenticationError,
    SchemaError,
    TransportError,
)
from keyhole_sdk.proof.adapters import (
    AdapterResult,
    LocalProofSubmissionAdapter,
    ProofSubmissionAdapter,
)
from keyhole_sdk.proof.models import (
    ParticipantContractPlaceholder,
    ProofBundlePlaceholder,
    SupportStatus,
    VerificationOutput,
)
from keyhole_sdk.proof.runner import VerificationRunner
from keyhole_sdk.config import DEFAULT_REALM

from keyhole_sdk.demo.models import (
    DemoPhase,
    DemoResult,
    DemoStepResult,
)


WHOAMI_PATH = "/mcp/v1/whoami"


class DemoFlowRunner:
    """Orchestrates the recursive demo flow.

    Composes capabilities discovery, context retrieval, participant
    posture, verification, proof assembly, and handoff into a single
    scriptable runner.

    Usage::

        demo = DemoFlowRunner(
            base_url="https://boundary.example.com",
            token="<bearer-token>",
        )
        result = demo.run()
        print(result.summary())

    Individual phases can also be invoked directly::

        result = demo.run_verification()
        bundle = demo.assemble_proof_bundle()
        handoff = demo.submit_proof()

    **Boundary posture: boundary-consuming.**
    """

    def __init__(
        self,
        base_url: str,
        *,
        token: str = "",
        timeout: float = 15.0,
        session: Optional[requests.Session] = None,
        submission_adapter: Optional[ProofSubmissionAdapter] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._session = session or requests.Session()
        self._submission_adapter = submission_adapter or LocalProofSubmissionAdapter()
        self._verification_runner = VerificationRunner(
            participant_name="keyhole-developer-kit",
            participant_type="external-developer-kit",
        )
        self._capabilities_data: Dict[str, Any] = {}
        self._context_data: Dict[str, Any] = {}

    @property
    def support_status(self) -> SupportStatus:
        """Demo flow is scaffolded until full platform loop closes."""
        return SupportStatus.SCAFFOLDED

    def register_collector(
        self,
        verification_class: str,
        collector: Any,
    ) -> None:
        """Register a verification collector for the demo flow.

        Delegates to the underlying :class:`VerificationRunner`.
        """
        self._verification_runner.register_collector(
            verification_class, collector,
        )

    # ── Full flow ───────────────────────────────────────────

    def run(self) -> DemoResult:
        """Execute the full recursive demo flow.

        Runs each phase in order.  If a critical phase fails,
        dependent phases are skipped with clear reasons.
        """
        result = DemoResult()

        # Phase 1: Discovery
        discovery = self._phase_discovery()
        result.steps.append(discovery)

        # Phase 2: Identity
        identity = self._phase_identity()
        result.steps.append(identity)

        if not identity.success:
            for phase in (DemoPhase.CONTEXT, DemoPhase.POSTURE,
                          DemoPhase.VERIFICATION, DemoPhase.BUNDLE,
                          DemoPhase.HANDOFF):
                result.steps.append(DemoStepResult(
                    phase=phase,
                    error="Skipped — identity inspection failed.",
                    suggestion="Fix authentication before retrying.",
                ))
            return result

        # Phase 3: Context
        context = self._phase_context()
        result.steps.append(context)

        # Phase 4: Posture
        posture = self._phase_posture()
        result.steps.append(posture)

        # Phase 5: Verification
        verification = self._phase_verification()
        result.steps.append(verification)
        if verification.success:
            result.verification_outputs = verification.data.get(
                "_outputs", [],
            )

        # Phase 6: Bundle
        bundle = self._phase_bundle()
        result.steps.append(bundle)
        if bundle.success or bundle.scaffolded:
            result.proof_bundle = bundle.data.get("_bundle")

        # Phase 7: Handoff
        handoff = self._phase_handoff(result.proof_bundle)
        result.steps.append(handoff)

        return result

    # ── Convenience methods ─────────────────────────────────

    def run_verification(self) -> ProofBundlePlaceholder:
        """Execute verification collectors and return proof bundle.

        Convenience method that runs the underlying VerificationRunner
        and returns the assembled proof bundle directly.
        """
        contract_version = self._capabilities_data.get(
            "contract_version", "",
        )
        return self._verification_runner.run(
            capabilities_contract_version=contract_version,
        )

    def assemble_proof_bundle(self) -> ProofBundlePlaceholder:
        """Assemble a proof bundle from the current state.

        Alias for :meth:`run_verification` — provided for API clarity
        in demo scripts.
        """
        return self.run_verification()

    def submit_proof(
        self,
        bundle: Optional[ProofBundlePlaceholder] = None,
    ) -> AdapterResult:
        """Attempt to submit a proof bundle.

        If no bundle is provided, one is assembled first.
        Returns an :class:`AdapterResult` — currently always
        ``supported=False`` since DEV-UX surfaces are not yet stable.
        """
        if bundle is None:
            bundle = self.assemble_proof_bundle()
        return self._submission_adapter.submit(bundle)

    # ── Phase implementations ───────────────────────────────

    def _phase_discovery(self) -> DemoStepResult:
        """Phase 1: Discover boundary capabilities."""
        try:
            with CapabilitiesClient(
                self.base_url,
                timeout=self.timeout,
                session=self._session,
            ) as client:
                caps = client.fetch()

            self._capabilities_data = {
                "contract_version": caps.get_contract_version(),
                "auth_flow": caps.get_auth_flow(),
                "transport": caps.get_transport(),
                "context_surfaces": caps.get_implemented_context_surfaces(),
            }
            return DemoStepResult(
                phase=DemoPhase.DISCOVERY,
                success=True,
                data=dict(self._capabilities_data),
            )
        except TransportError as exc:
            return DemoStepResult(
                phase=DemoPhase.DISCOVERY,
                error=str(exc),
                suggestion="Check MCP boundary URL and network connectivity.",
            )
        except SchemaError as exc:
            return DemoStepResult(
                phase=DemoPhase.DISCOVERY,
                error=str(exc),
                suggestion="Capabilities response malformed. Check boundary version.",
            )

    def _phase_identity(self) -> DemoStepResult:
        """Phase 2: Inspect authenticated participant identity."""
        url = f"{self.base_url}{WHOAMI_PATH}"
        try:
            response = self._session.get(
                url,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=self.timeout,
            )
        except (requests.ConnectionError, requests.Timeout, OSError) as exc:
            return DemoStepResult(
                phase=DemoPhase.IDENTITY,
                error=f"Identity inspection failed: {exc}",
                suggestion="Check network connectivity to MCP boundary.",
            )

        if response.status_code == 401:
            return DemoStepResult(
                phase=DemoPhase.IDENTITY,
                error="Authentication failed (401).",
                suggestion=f"Acquire fresh OIDC/PKCE token for realm '{DEFAULT_REALM}'.",
            )

        if response.status_code == 403:
            return DemoStepResult(
                phase=DemoPhase.IDENTITY,
                error="Insufficient authority (403).",
                suggestion="Check participant identity and charter posture.",
            )

        if response.status_code != 200:
            return DemoStepResult(
                phase=DemoPhase.IDENTITY,
                error=f"Identity endpoint returned {response.status_code}.",
                suggestion="Unexpected status. Check MCP boundary health.",
            )

        try:
            data = response.json()
        except ValueError:
            return DemoStepResult(
                phase=DemoPhase.IDENTITY,
                error="Identity response is not valid JSON.",
                suggestion="Check boundary version compatibility.",
            )

        return DemoStepResult(
            phase=DemoPhase.IDENTITY,
            success=True,
            data=data,
        )

    def _phase_context(self) -> DemoStepResult:
        """Phase 3: Retrieve governed context."""
        try:
            with ContextClient(
                self.base_url,
                token=self.token,
                timeout=self.timeout,
                session=self._session,
            ) as ctx:
                snapshot = ctx.compile_context()

            self._context_data = {
                "platform_name": snapshot.get_platform_name(),
                "governance_model": snapshot.get_governance_model(),
                "mcp_contract": snapshot.get_mcp_contract(),
                "implemented_surfaces": snapshot.get_implemented_surfaces(),
            }
            return DemoStepResult(
                phase=DemoPhase.CONTEXT,
                success=True,
                data=dict(self._context_data),
            )
        except AuthenticationError as exc:
            return DemoStepResult(
                phase=DemoPhase.CONTEXT,
                error=f"Auth error during context retrieval: {exc}",
                suggestion="Token may have expired. Re-authenticate.",
            )
        except TransportError as exc:
            return DemoStepResult(
                phase=DemoPhase.CONTEXT,
                error=f"Transport error during context retrieval: {exc}",
                suggestion="Check network connectivity.",
            )
        except SchemaError as exc:
            return DemoStepResult(
                phase=DemoPhase.CONTEXT,
                error=f"Schema error during context retrieval: {exc}",
                suggestion="Check SDK and boundary version compatibility.",
            )

    def _phase_posture(self) -> DemoStepResult:
        """Phase 4: Confirm participant contract posture."""
        contract = ParticipantContractPlaceholder()
        return DemoStepResult(
            phase=DemoPhase.POSTURE,
            success=True,
            data={
                "participant_name": contract.participant_name,
                "participant_type": contract.participant_type,
                "compatibility_posture": contract.compatibility_posture,
                "support_status": contract.support_status.value,
                "verification_classes": contract.verification_classes,
            },
        )

    def _phase_verification(self) -> DemoStepResult:
        """Phase 5: Execute local verification collectors."""
        try:
            bundle = self._verification_runner.run(
                capabilities_contract_version=self._capabilities_data.get(
                    "contract_version", "",
                ),
            )
            outputs = bundle.verification_outputs
            all_passed = bundle.all_passed

            return DemoStepResult(
                phase=DemoPhase.VERIFICATION,
                success=all_passed,
                data={
                    "total": len(outputs),
                    "passed": sum(1 for v in outputs if v.passed),
                    "failed": sum(1 for v in outputs if not v.passed),
                    "_outputs": outputs,
                },
            )
        except Exception as exc:
            return DemoStepResult(
                phase=DemoPhase.VERIFICATION,
                error=f"Verification runner error: {exc}",
                suggestion="Check registered collectors for errors.",
            )

    def _phase_bundle(self) -> DemoStepResult:
        """Phase 6: Assemble proof bundle."""
        try:
            bundle = self.run_verification()
            return DemoStepResult(
                phase=DemoPhase.BUNDLE,
                success=True,
                scaffolded=True,
                data={
                    "participant_name": bundle.participant_name,
                    "source_commit": bundle.source_commit,
                    "source_ref": bundle.source_ref,
                    "environment": bundle.environment,
                    "sdk_version": bundle.sdk_version,
                    "python_version": bundle.python_version,
                    "verification_summary": bundle.verification_summary,
                    "support_status": bundle.support_status.value,
                    "_bundle": bundle,
                },
            )
        except Exception as exc:
            return DemoStepResult(
                phase=DemoPhase.BUNDLE,
                error=f"Proof bundle assembly error: {exc}",
                suggestion="Check verification runner and collectors.",
            )

    def _phase_handoff(
        self,
        bundle: Optional[ProofBundlePlaceholder] = None,
    ) -> DemoStepResult:
        """Phase 7: Attempt proof handoff (scaffolded)."""
        if bundle is None:
            return DemoStepResult(
                phase=DemoPhase.HANDOFF,
                scaffolded=True,
                data={
                    "supported": False,
                    "reason": "No proof bundle available for submission.",
                },
            )

        adapter_result = self._submission_adapter.submit(bundle)
        return DemoStepResult(
            phase=DemoPhase.HANDOFF,
            success=adapter_result.success,
            scaffolded=not adapter_result.supported,
            data={
                "supported": adapter_result.supported,
                "reason": adapter_result.reason,
            },
        )
