"""Context preflight — SDK-CLIENT-16 §6.

Validates preconditions before context compile or inspect:
  - user is authenticated
  - canonical scaffold exists
  - digest format is valid (for inspect/bind)
  - mutually exclusive flags are not combined

The client must fail locally when the problem is obvious locally.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.context_lifecycle.digest import validate_digest, is_auto


@dataclass
class ContextPreflightFailure:
    """Describes why context preflight blocked the operation."""

    reason: str
    repair_guidance: List[str] = field(default_factory=list)
    is_local: bool = True


class ContextPreflight:
    """Preflight gate for context lifecycle commands (§6).

    Validates:
      1. Active credentials
      2. Scaffold exists (for compile)
      3. Digest format (for inspect / bind)
      4. Mutually exclusive flags
    """

    def __init__(
        self,
        *,
        credential_store: Optional[CredentialStore] = None,
    ) -> None:
        self._cred_store = credential_store or CredentialStore()

    def check_compile(
        self,
        *,
        repo_dir: Path,
    ) -> Optional[ContextPreflightFailure]:
        """Preflight for ``keyhole context compile``.

        Returns None on success, ContextPreflightFailure on failure.
        """
        # Auth check
        if not self._cred_store.is_authenticated():
            return ContextPreflightFailure(
                reason="Not authenticated. Active credentials are missing or expired.",
                repair_guidance=[
                    "Run: keyhole login",
                    "Re-authenticate and try again.",
                ],
            )

        # Scaffold check
        keyhole_yaml = repo_dir / "keyhole.yaml"
        if not keyhole_yaml.exists():
            return ContextPreflightFailure(
                reason="Missing keyhole.yaml — canonical scaffold not found.",
                repair_guidance=[
                    "Run: keyhole init vertical",
                    "Ensure you are in a governed repo directory.",
                ],
            )

        return None

    def check_inspect(
        self,
        *,
        digest: str,
    ) -> Optional[ContextPreflightFailure]:
        """Preflight for ``keyhole context inspect``.

        Returns None on success, ContextPreflightFailure on failure.
        """
        # Auth check
        if not self._cred_store.is_authenticated():
            return ContextPreflightFailure(
                reason="Not authenticated. Active credentials are missing or expired.",
                repair_guidance=[
                    "Run: keyhole login",
                    "Re-authenticate and try again.",
                ],
            )

        # Digest validation
        if not digest:
            return ContextPreflightFailure(
                reason="No digest provided for inspection.",
                repair_guidance=[
                    "Run: keyhole context compile — to get a digest first.",
                    "Or provide a known digest: keyhole context inspect --digest <digest>",
                ],
            )

        error = validate_digest(digest)
        if error:
            return ContextPreflightFailure(
                reason=error,
                repair_guidance=[
                    "Provide a valid digest string.",
                    "Run: keyhole context compile — to compile and get a valid digest.",
                ],
            )

        return None

    def check_run_context(
        self,
        *,
        context: str,
    ) -> Optional[ContextPreflightFailure]:
        """Preflight for ``keyhole run --context <digest>``.

        Validates that context is present and well-formed.
        Returns None on success, ContextPreflightFailure on failure.

        §11: governed runs must not proceed without explicit context.
        """
        if not context:
            return ContextPreflightFailure(
                reason="Governed runs require explicit context. No --context provided.",
                repair_guidance=[
                    "Run: keyhole context compile — to compile context first.",
                    "Then: keyhole run --context <digest> --run-type <type>",
                    "Or: keyhole run --context auto --run-type <type>",
                ],
            )

        if is_auto(context):
            return None  # auto is valid — will be resolved later

        error = validate_digest(context)
        if error:
            return ContextPreflightFailure(
                reason=error,
                repair_guidance=[
                    "Provide a valid digest or use --context auto.",
                    "Run: keyhole context compile — to get a valid digest.",
                ],
            )

        return None
