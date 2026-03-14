"""Verification runner scaffold.

CE-V5-S42-08: Proof-Ready Participant Scaffolding.

Provides a future-facing runner shape for local verification execution,
environment capture, result normalization, and proof-material preparation.

**Support status: SCAFFOLDED — shape exists, not yet connected to
live platform proof flows.**

The verification runner is designed to later support:
    - local test execution (e.g., pytest invocation)
    - environment capture (Python version, OS, SDK version)
    - verification result collection and normalization
    - proof-bundle assembly from collected outputs

At this stage, the runner is primarily about:
    - deliberate shape and extension points
    - adapter boundaries for future integration
    - honest separation from current supported flows

It does not claim a sealed platform proof flow already exists.

Must never:
    - hardcode unstable platform internals
    - pretend proof submission is operational
    - define platform verification law from the participant side
    - couple to private platform source
"""

from __future__ import annotations

import platform
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from keyhole_sdk.proof.models import (
    ProofBundlePlaceholder,
    SupportStatus,
    VerificationOutput,
)


class VerificationRunner:
    """Scaffold for future local verification and proof assembly.

    **Support status: SCAFFOLDED — local-only operations.**

    The runner coordinates:
        1. Environment capture
        2. Verification execution (via registered collectors)
        3. Result normalization into :class:`VerificationOutput` models
        4. Proof-bundle assembly from collected outputs

    Collectors are callables that return a :class:`VerificationOutput`.
    They are the extension points for adding specific verification types
    (unit tests, contract surface tests, smoke tests, etc.).

    Example (local-only, no live platform interaction)::

        runner = VerificationRunner(participant_name="keyhole-developer-kit")
        runner.register_collector("unit-tests", my_unit_test_collector)
        bundle = runner.run()
        print(bundle.verification_summary)

    The runner does not submit anything to the platform.  Submission
    is handled by :class:`ProofSubmissionAdapter` when the platform
    surface stabilizes.
    """

    def __init__(
        self,
        *,
        participant_name: str = "keyhole-developer-kit",
        participant_type: str = "external-developer-kit",
        source_repository: str = "",
        environment: str = "local-only",
    ) -> None:
        self._participant_name = participant_name
        self._participant_type = participant_type
        self._source_repository = source_repository
        self._environment = environment
        self._collectors: Dict[str, Any] = {}

    @property
    def support_status(self) -> SupportStatus:
        """This runner is scaffolded, not yet connected to live flows."""
        return SupportStatus.SCAFFOLDED

    def register_collector(
        self,
        verification_class: str,
        collector: Any,
    ) -> None:
        """Register a verification collector for a given class.

        A collector is a callable that takes no arguments and returns
        a :class:`VerificationOutput`.  Collectors are the extension
        points that adapt specific verification tools (pytest, etc.)
        into the normalized output shape.

        Args:
            verification_class: Name of the verification class
                (e.g., ``'unit-tests'``, ``'contract-surface-tests'``).
            collector: A callable returning a ``VerificationOutput``.
        """
        self._collectors[verification_class] = collector

    def capture_environment(self) -> Dict[str, str]:
        """Capture current environment metadata.

        Returns a dictionary with:
            - python_version
            - platform_info
            - sdk_version
        """
        try:
            from keyhole_sdk import __version__ as sdk_version
        except ImportError:
            sdk_version = "unknown"

        return {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform_info": platform.platform(),
            "sdk_version": sdk_version,
        }

    def capture_source_info(self) -> Dict[str, str]:
        """Capture source provenance metadata.

        Attempts to read the current git commit and ref.  Falls back
        to empty strings if git is not available or the working
        directory is not a git repository.
        """
        commit = ""
        ref = ""

        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                commit = result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                ref = result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return {
            "source_commit": commit,
            "source_ref": ref,
        }

    def run(
        self,
        *,
        context_digest: str = "",
        capabilities_contract_version: str = "",
    ) -> ProofBundlePlaceholder:
        """Execute all registered collectors and assemble a proof bundle.

        This is a local-only operation.  The resulting bundle is a
        placeholder that can later be submitted through the
        :class:`ProofSubmissionAdapter` when the platform surface
        stabilizes.

        Args:
            context_digest: Optional digest from recent context retrieval.
            capabilities_contract_version: Optional MCP contract version
                from recent capabilities discovery.

        Returns:
            A :class:`ProofBundlePlaceholder` containing environment
            metadata and all collected verification outputs.
        """
        env = self.capture_environment()
        source = self.capture_source_info()

        outputs: List[VerificationOutput] = []
        for verification_class, collector in self._collectors.items():
            try:
                output = collector()
                if isinstance(output, VerificationOutput):
                    if not output.verification_class:
                        output.verification_class = verification_class
                    outputs.append(output)
            except Exception as exc:
                outputs.append(VerificationOutput(
                    verification_class=verification_class,
                    passed=False,
                    error_summary=f"Collector raised: {exc}",
                    executed_at=datetime.now(timezone.utc),
                ))

        bundle = ProofBundlePlaceholder(
            participant_name=self._participant_name,
            participant_type=self._participant_type,
            source_repository=self._source_repository,
            source_commit=source.get("source_commit", ""),
            source_ref=source.get("source_ref", ""),
            verification_outputs=outputs,
            environment=self._environment,
            python_version=env.get("python_version", ""),
            sdk_version=env.get("sdk_version", ""),
            platform_info=env.get("platform_info", ""),
            context_digest=context_digest,
            capabilities_contract_version=capabilities_contract_version,
            assembled_at=datetime.now(timezone.utc),
        )

        return bundle
