"""Run preflight checks — SDK-CLIENT-09 §6.

Validates preconditions before dispatching a governed run:
  - user is authenticated
  - canonical scaffold exists (keyhole.yaml)
  - run type is valid
  - operation can be classified for transport

If any check fails, returns a PreflightFailure with repair guidance
instead of sending an ambiguous network request.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.dispatch.preflight import DispatchPreflight
from keyhole_sdk.dispatch.models import PreflightStatus
from keyhole_sdk.transport.operation_registry import get_operation


@dataclass
class PreflightFailure:
    """Describes why preflight blocked dispatch, with repair guidance."""

    reason: str
    repair_guidance: List[str] = field(default_factory=list)
    is_local: bool = True  # True = client-side, False = boundary-side


class RunPreflight:
    """Preflight gate for ``keyhole run`` (§6).

    Validates:
      1. Active credentials
      2. Scaffold exists
      3. Run-type validity
      4. Operation classification
    """

    def __init__(
        self,
        *,
        credential_store: Optional[CredentialStore] = None,
        dispatch_preflight: Optional[DispatchPreflight] = None,
    ) -> None:
        self._cred_store = credential_store or CredentialStore()
        self._dispatch = dispatch_preflight or DispatchPreflight()

    def check(
        self,
        *,
        repo_dir: Path,
        run_type: str,
    ) -> Optional[PreflightFailure]:
        """Run all preflight checks. Returns None on success.

        If any check fails, returns a PreflightFailure with guidance.
        """
        # §6.1: User must be authenticated
        if not self._cred_store.is_authenticated():
            return PreflightFailure(
                reason="Not authenticated. Active credentials are missing or expired.",
                repair_guidance=[
                    "Run: keyhole login",
                    "Re-authenticate and try again.",
                ],
            )

        # §6.2: Repo must have canonical scaffold
        keyhole_yaml = repo_dir / "keyhole.yaml"
        if not keyhole_yaml.exists():
            return PreflightFailure(
                reason="Missing keyhole.yaml — canonical scaffold not found.",
                repair_guidance=[
                    "Run: keyhole init vertical",
                    "Ensure you are in a governed repo directory.",
                ],
            )

        # §6.3: Validate run-type
        preflight_result = self._dispatch.check(run_type)
        if not preflight_result.should_proceed:
            guidance = []
            if preflight_result.suggested_next_step:
                guidance.append(preflight_result.suggested_next_step)
            guidance.append(
                "Run: keyhole run --run-type <valid-type>"
            )
            return PreflightFailure(
                reason=f"Run-type preflight rejected: {preflight_result.reason}",
                repair_guidance=guidance,
            )

        # §6.4: Operation must be classifiable for transport
        descriptor = get_operation("run.start")
        if descriptor is None:
            return PreflightFailure(
                reason="Operation 'run.start' is not registered in the transport registry.",
                repair_guidance=[
                    "This is an internal SDK error. Update the SDK.",
                ],
            )

        return None

    def load_repo_name(self, repo_dir: Path) -> Optional[str]:
        """Extract repo name from keyhole.yaml (best-effort)."""
        keyhole_yaml = repo_dir / "keyhole.yaml"
        if not keyhole_yaml.exists():
            return None
        try:
            import yaml  # noqa: F811
            data = yaml.safe_load(keyhole_yaml.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                repo = data.get("repo", {})
                if isinstance(repo, dict):
                    return repo.get("name")
        except Exception:
            pass
        # Fallback: parse simple YAML manually
        try:
            for line in keyhole_yaml.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("name:"):
                    return stripped.split(":", 1)[1].strip()
        except Exception:
            pass
        return repo_dir.name
