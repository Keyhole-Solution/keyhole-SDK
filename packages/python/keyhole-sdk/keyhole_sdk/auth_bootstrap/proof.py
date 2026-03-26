"""Auth proof bundle — client-side zipper proof contribution.

Implements §13 of SDK-CLIENT-01: Proof Bundle Requirements.

Hardened proof semantics (server-aligned identity governance):
  - identity_context.json is derived ONLY from /whoami server response
  - verification_result.json marks success only after governed identity confirmed
  - event_chain.json reflects authoritative auth lifecycle
  - summary.md describes closure in terms of governed identity confirmation
  - mode in proof is always server-issued
  - no token secrets appear anywhere in proof
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from keyhole_sdk.auth_bootstrap.models import AuthFlowType, AuthMode, LoginResult


class AuthProofBundle:
    """Generates proof artifacts for the auth bootstrap zipper.

    All proof materials are secret-safe — no tokens, passwords, or
    sensitive credentials appear in any artifact.
    """

    def __init__(self, correlation_id: str) -> None:
        self._correlation_id = correlation_id
        self._events: list[Dict[str, Any]] = []
        self._started_at = datetime.now(timezone.utc)

    def record_event(self, event_type: str, detail: Dict[str, Any]) -> None:
        """Record a proof event in the event chain."""
        self._events.append({
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": detail,
        })

    def generate(self, login_result: LoginResult) -> Dict[str, Any]:
        """Generate the full proof bundle from a login result.

        Returns a dict containing all proof artifacts keyed by filename.
        """
        completed_at = datetime.now(timezone.utc)

        core = self._build_core(login_result, completed_at)
        request_doc = self._build_request(login_result)
        response_doc = self._build_response(login_result)
        event_chain = self._build_event_chain()
        identity_context = self._build_identity_context(login_result)
        verification_result = self._build_verification_result(login_result)
        correlation = self._build_correlation(completed_at)
        summary = self._build_summary(login_result, completed_at)

        # Compute digest over core
        core_json = json.dumps(core, sort_keys=True, default=str)
        digest = hashlib.sha256(core_json.encode()).hexdigest()

        return {
            "core.json": core,
            "request.json": request_doc,
            "response.json": response_doc,
            "event_chain.json": event_chain,
            "identity_context.json": identity_context,
            "verification_result.json": verification_result,
            "correlation.json": correlation,
            "summary.md": summary,
            "digest.txt": f"sha256:{digest}",
        }

    def write(self, login_result: LoginResult, output_dir: Path) -> Path:
        """Write proof bundle to disk."""
        bundle = self.generate(login_result)
        bundle_dir = output_dir / "proof_bundle"
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

    def _build_core(
        self, result: LoginResult, completed_at: datetime
    ) -> Dict[str, Any]:
        return {
            "proof_type": "auth_bootstrap",
            "story_id": "SDK-CLIENT-01",
            "correlation_id": self._correlation_id,
            "success": result.success,
            "flow_type": result.flow_type.value if result.flow_type else None,
            "mode": result.mode.value if result.mode else None,
            "credential_persisted": result.credential_persisted,
            "verification_passed": result.verification_passed,
            "identity_source": result.identity_source,
            "whoami_completed": result.whoami is not None,
            "started_at": self._started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
        }

    def _build_request(self, result: LoginResult) -> Dict[str, Any]:
        return {
            "flow_type_requested": result.flow_type.value if result.flow_type else None,
            "initiated_at": self._started_at.isoformat(),
        }

    def _build_response(self, result: LoginResult) -> Dict[str, Any]:
        resp: Dict[str, Any] = {
            "success": result.success,
            "credential_persisted": result.credential_persisted,
            "verification_passed": result.verification_passed,
        }
        if result.error_class:
            resp["error_class"] = result.error_class
            resp["error_message"] = result.error_message
        if result.whoami:
            resp["identity_resolved"] = True
            resp["mode"] = result.whoami.mode.value
        return resp

    def _build_event_chain(self) -> Dict[str, Any]:
        return {
            "correlation_id": self._correlation_id,
            "events": self._events,
        }

    def _build_identity_context(self, result: LoginResult) -> Dict[str, Any]:
        if result.whoami:
            return {
                "source": "server/whoami",
                "user_id": result.whoami.user_id,
                "tenant_id": result.whoami.tenant_id,
                "org_id": result.whoami.org_id,
                "cohort_id": result.whoami.cohort_id,
                "worker_id": result.whoami.worker_id,
                "workspace_id": result.whoami.workspace_id,
                "mode": result.whoami.mode.value,
                "plan": result.whoami.plan,
            }
        return {"source": None, "identity_resolved": False}

    def _build_verification_result(self, result: LoginResult) -> Dict[str, Any]:
        return {
            "login_completed": result.success,
            "credential_persisted": result.credential_persisted,
            "whoami_verified": result.verification_passed,
            "identity_source": result.identity_source,
            "governed_identity_confirmed": (
                result.success and result.verification_passed and result.whoami is not None
            ),
            "server_auth_event_confirmed": (
                result.success and result.verification_passed
            ),
            "mode_visible": result.mode is not None,
            "mode_source": "server/whoami" if result.whoami is not None else None,
            "error_class": result.error_class,
        }

    def _build_correlation(self, completed_at: datetime) -> Dict[str, Any]:
        return {
            "correlation_id": self._correlation_id,
            "story_id": "SDK-CLIENT-01",
            "started_at": self._started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
        }

    def _build_summary(
        self, result: LoginResult, completed_at: datetime
    ) -> str:
        lines = [
            "# Auth Bootstrap Proof Summary — SDK-CLIENT-01",
            "",
            f"**Correlation ID:** {self._correlation_id}",
            f"**Started:** {self._started_at.isoformat()}",
            f"**Completed:** {completed_at.isoformat()}",
            "",
            "## Result",
            "",
            f"- **Success:** {result.success}",
            f"- **Flow type:** {result.flow_type.value if result.flow_type else 'N/A'}",
            f"- **Mode:** {result.mode.value if result.mode else 'N/A'}",
            f"- **Mode source:** {'server/whoami' if result.whoami else 'N/A'}",
            f"- **Credential persisted:** {result.credential_persisted}",
            f"- **Governed identity confirmed:** {result.verification_passed and result.whoami is not None}",
        ]

        if result.whoami:
            lines.extend([
                "",
                "## Identity Context (from server /whoami)",
                "",
                f"- **User:** {result.whoami.user_id}",
                f"- **Tenant:** {result.whoami.tenant_id}",
                f"- **Org:** {result.whoami.org_id}",
                f"- **Cohort:** {result.whoami.cohort_id}",
                f"- **Mode:** {result.whoami.mode.value}",
            ])

        if result.error_class:
            lines.extend([
                "",
                "## Failure",
                "",
                f"- **Error class:** {result.error_class}",
                f"- **Message:** {result.error_message}",
            ])
            if result.repair_suggestions:
                lines.append("")
                lines.append("### Repair Suggestions")
                lines.append("")
                for s in result.repair_suggestions:
                    lines.append(f"- {s}")

        lines.extend([
            "",
            "---",
            f"*Generated by keyhole-sdk auth bootstrap proof*",
        ])
        return "\n".join(lines) + "\n"
