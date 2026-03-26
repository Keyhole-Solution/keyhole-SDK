"""Onboarding proof bundle — client-side zipper proof contribution.

Implements §16 of SDK-CLIENT-00: Proof Bundle Requirements.

Proof semantics:
  - registration_context.json captures realm, origin, purpose
  - verification_result.json marks completion only after server confirms
  - identity_context.json is derived ONLY from server response
  - event_chain.json reflects authoritative onboarding lifecycle
  - summary.md describes closure in terms of governed identity readiness
  - no verification codes, tokens, or secrets appear in any artifact
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class OnboardingProofBundle:
    """Generates proof artifacts for the onboarding zipper.

    All proof materials are secret-safe — no verification codes,
    tokens, passwords, or sensitive credentials appear in any artifact.
    """

    def __init__(self, correlation_id: str) -> None:
        self._correlation_id = correlation_id
        self._events: List[Dict[str, Any]] = []
        self._started_at = datetime.now(timezone.utc)

    def record_event(self, event_type: str, detail: Dict[str, Any]) -> None:
        """Record a proof event in the event chain."""
        self._events.append({
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": detail,
        })

    def generate(
        self,
        *,
        registration: Optional[Dict[str, Any]] = None,
        verification: Optional[Dict[str, Any]] = None,
        status: Optional[Dict[str, Any]] = None,
        success: bool = False,
    ) -> Dict[str, Any]:
        """Generate the full proof bundle from onboarding results.

        Parameters
        ----------
        registration:
            safe_summary() dict from RegistrationResponse.
        verification:
            safe_summary() dict from VerificationResponse.
        status:
            safe_summary() dict from RegistrationStatusResponse.
        success:
            Whether the onboarding flow completed successfully.
        """
        completed_at = datetime.now(timezone.utc)

        core = self._build_core(success, completed_at, registration, verification)
        request_doc = self._build_request(registration)
        response_doc = self._build_response(registration, verification)
        event_chain = self._build_event_chain()
        reg_context = self._build_registration_context(registration)
        verification_result = self._build_verification_result(verification)
        identity_context = self._build_identity_context(verification, status)
        correlation = self._build_correlation(completed_at)
        summary = self._build_summary(
            success, completed_at, registration, verification, status,
        )
        diff = self._build_diff(registration, verification)

        # Compute digest over core
        core_json = json.dumps(core, sort_keys=True, default=str)
        digest = hashlib.sha256(core_json.encode()).hexdigest()

        return {
            "core.json": core,
            "request.json": request_doc,
            "response.json": response_doc,
            "event_chain.json": event_chain,
            "registration_context.json": reg_context,
            "verification_result.json": verification_result,
            "identity_context.json": identity_context,
            "correlation.json": correlation,
            "summary.md": summary,
            "diff.json": diff,
            "digest.txt": f"sha256:{digest}",
        }

    def write(
        self,
        *,
        registration: Optional[Dict[str, Any]] = None,
        verification: Optional[Dict[str, Any]] = None,
        status: Optional[Dict[str, Any]] = None,
        success: bool = False,
        output_dir: Path,
    ) -> Path:
        """Write proof bundle to disk."""
        bundle = self.generate(
            registration=registration,
            verification=verification,
            status=status,
            success=success,
        )
        bundle_dir = output_dir / "onboarding_proof_bundle"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        (bundle_dir / "extended").mkdir(exist_ok=True)

        for filename, content in bundle.items():
            path = bundle_dir / filename
            if isinstance(content, str):
                path.write_text(content, encoding="utf-8")
            else:
                path.write_text(
                    json.dumps(content, indent=2, default=str),
                    encoding="utf-8",
                )

        return bundle_dir

    # ── Private builders ────────────────────────────────────

    def _build_core(
        self,
        success: bool,
        completed_at: datetime,
        registration: Optional[Dict[str, Any]],
        verification: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "proof_type": "onboarding",
            "story_id": "SDK-CLIENT-00",
            "correlation_id": self._correlation_id,
            "success": success,
            "realm": (registration or {}).get("realm"),
            "origin": (registration or {}).get("origin"),
            "purpose": (registration or {}).get("purpose"),
            "registration_completed": registration is not None,
            "verification_completed": verification is not None,
            "verification_state": (verification or {}).get("state"),
            "started_at": self._started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
        }

    def _build_request(
        self, registration: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not registration:
            return {"initiated_at": self._started_at.isoformat()}
        return {
            "registration_id": registration.get("registration_id"),
            "realm": registration.get("realm"),
            "origin": registration.get("origin"),
            "purpose": registration.get("purpose"),
            "username": registration.get("username"),
            "initiated_at": self._started_at.isoformat(),
        }

    def _build_response(
        self,
        registration: Optional[Dict[str, Any]],
        verification: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        resp: Dict[str, Any] = {
            "registration_accepted": registration is not None,
        }
        if registration:
            resp["registration_state"] = registration.get("state")
            resp["registration_id"] = registration.get("registration_id")
            resp["next_step"] = registration.get("next_step")
        if verification:
            resp["verification_completed"] = True
            resp["verification_state"] = verification.get("state")
            resp["user_id"] = verification.get("user_id")
        return resp

    def _build_event_chain(self) -> Dict[str, Any]:
        return {
            "correlation_id": self._correlation_id,
            "events": self._events,
        }

    def _build_registration_context(
        self, registration: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not registration:
            return {"source": None, "registration_completed": False}
        return {
            "source": "server/register",
            "registration_id": registration.get("registration_id"),
            "state": registration.get("state"),
            "realm": registration.get("realm"),
            "origin": registration.get("origin"),
            "purpose": registration.get("purpose"),
            "username": registration.get("username"),
            "verification_hint": registration.get("verification_hint"),
        }

    def _build_verification_result(
        self, verification: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not verification:
            return {
                "verification_completed": False,
                "identity_activated": False,
            }
        state = verification.get("state", "")
        return {
            "verification_completed": True,
            "state": state,
            "registration_id": verification.get("registration_id"),
            "user_id": verification.get("user_id"),
            "username": verification.get("username"),
            "realm": verification.get("realm"),
            "identity_activated": state in ("active", "verified", "activation_ready"),
            "next_step": verification.get("next_step"),
        }

    def _build_identity_context(
        self,
        verification: Optional[Dict[str, Any]],
        status: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        # Prefer status (most complete), fall back to verification
        source = status or verification
        if not source:
            return {"source": None, "identity_resolved": False}
        return {
            "source": "server/status" if status else "server/verify",
            "registration_id": source.get("registration_id"),
            "user_id": source.get("user_id"),
            "username": source.get("username"),
            "realm": source.get("realm"),
            "origin": source.get("origin"),
            "purpose": source.get("purpose"),
            "state": source.get("state"),
            "identity_resolved": source.get("user_id") is not None,
        }

    def _build_correlation(self, completed_at: datetime) -> Dict[str, Any]:
        return {
            "correlation_id": self._correlation_id,
            "story_id": "SDK-CLIENT-00",
            "started_at": self._started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
        }

    def _build_diff(
        self,
        registration: Optional[Dict[str, Any]],
        verification: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Diff between registration and verification states."""
        before_state = (registration or {}).get("state")
        after_state = (verification or {}).get("state")
        return {
            "onboarding_state_transition": {
                "before": before_state,
                "after": after_state,
            },
            "identity_resolved": verification is not None and verification.get("user_id") is not None,
        }

    def _build_summary(
        self,
        success: bool,
        completed_at: datetime,
        registration: Optional[Dict[str, Any]],
        verification: Optional[Dict[str, Any]],
        status: Optional[Dict[str, Any]],
    ) -> str:
        lines = [
            "# Onboarding Proof Summary — SDK-CLIENT-00",
            "",
            f"**Correlation ID:** {self._correlation_id}",
            f"**Started:** {self._started_at.isoformat()}",
            f"**Completed:** {completed_at.isoformat()}",
            "",
            "## Result",
            "",
            f"- **Success:** {success}",
        ]

        if registration:
            lines.extend([
                f"- **Realm:** {registration.get('realm', 'N/A')}",
                f"- **Origin:** {registration.get('origin', 'N/A')}",
                f"- **Purpose:** {registration.get('purpose', 'N/A')}",
                f"- **Registration ID:** {registration.get('registration_id', 'N/A')}",
                f"- **Registration state:** {registration.get('state', 'N/A')}",
            ])
        elif verification and verification.get("realm"):
            # Verification-only proof still shows realm classification
            lines.extend([
                f"- **Realm:** {verification.get('realm', 'N/A')}",
            ])

        if verification:
            lines.extend([
                "",
                "## Verification",
                "",
                f"- **State:** {verification.get('state', 'N/A')}",
                f"- **User ID:** {verification.get('user_id', 'N/A')}",
                f"- **Username:** {verification.get('username', 'N/A')}",
                f"- **Next step:** {verification.get('next_step', 'N/A')}",
            ])

        if status:
            lines.extend([
                "",
                "## Status",
                "",
                f"- **State:** {status.get('state', 'N/A')}",
                f"- **User ID:** {status.get('user_id', 'N/A')}",
            ])

        if success:
            lines.extend([
                "",
                "## Handoff",
                "",
                "Identity is activation-ready. Next step: `keyhole login`",
            ])

        lines.extend([
            "",
            "---",
            "*Generated by keyhole-sdk onboarding proof*",
        ])
        return "\n".join(lines) + "\n"
