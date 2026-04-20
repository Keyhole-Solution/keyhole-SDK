"""SDK-CLIENT-01-C — Doctor proof bundle emission (§15, §17).

Generates repo-neutral proof/support artifacts for doctor scans
and reconciliation fix flows.

INV-SDK-CLIENT-01-C-007: Doctor artifacts are repo-neutral.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


_STORY_ID = "sdk-client-01-c"


class DoctorProofBundle:
    """Proof bundle for doctor scans and reconciliation flows (§15, §17)."""

    def __init__(self, correlation_id: Optional[str] = None) -> None:
        self._correlation_id = correlation_id or str(uuid.uuid4())
        self._events: List[Dict[str, Any]] = []
        self._started_at = datetime.now(timezone.utc)

    @property
    def correlation_id(self) -> str:
        return self._correlation_id

    def record_event(self, event_type: str, detail: Dict[str, Any]) -> None:
        """Record a proof event in the event chain."""
        self._events.append(
            {
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "detail": detail,
            }
        )

    def generate(
        self,
        *,
        report: Optional[Dict[str, Any]] = None,
        local_profile: Optional[Dict[str, Any]] = None,
        host_inventory: Optional[List[Dict[str, Any]]] = None,
        connection_truth: Optional[Dict[str, Any]] = None,
        negotiation: Optional[Dict[str, Any]] = None,
        requested_fix: Optional[Dict[str, Any]] = None,
        fix_response: Optional[Dict[str, Any]] = None,
        verification: Optional[Dict[str, Any]] = None,
        success: bool = False,
    ) -> Dict[str, str]:
        """Generate proof bundle documents (§15.2).

        Returns a dict of filename → content (JSON or Markdown).
        """
        completed_at = datetime.now(timezone.utc).isoformat()

        # Core report
        core: Dict[str, Any] = {
            "proof_type": "doctor_reconciliation",
            "story_id": _STORY_ID,
            "correlation_id": self._correlation_id,
            "success": success,
            "started_at": self._started_at.isoformat(),
            "completed_at": completed_at,
        }

        core_json = json.dumps(core, indent=2)
        digest = hashlib.sha256(core_json.encode()).hexdigest()

        docs: Dict[str, str] = {
            "report.json": json.dumps(report or {}, indent=2),
            "local_profile_snapshot.json": json.dumps(local_profile or {}, indent=2),
            "host_inventory.json": json.dumps(host_inventory or [], indent=2),
            "connection_truth.json": json.dumps(connection_truth or {}, indent=2),
            "negotiation.json": json.dumps(negotiation or {}, indent=2),
            "requested_fix.json": json.dumps(requested_fix or {}, indent=2),
            "response.json": json.dumps(fix_response or {}, indent=2),
            "verification.json": json.dumps(verification or {}, indent=2),
            "repair.json": json.dumps(
                {"events": self._events, "correlation_id": self._correlation_id},
                indent=2,
            ),
            "summary.md": self._build_summary(
                report=report,
                requested_fix=requested_fix,
                verification=verification,
                success=success,
            ),
            "digest.txt": f"sha256:{digest}",
        }

        return docs

    def write(
        self,
        *,
        report: Optional[Dict[str, Any]] = None,
        local_profile: Optional[Dict[str, Any]] = None,
        host_inventory: Optional[List[Dict[str, Any]]] = None,
        connection_truth: Optional[Dict[str, Any]] = None,
        negotiation: Optional[Dict[str, Any]] = None,
        requested_fix: Optional[Dict[str, Any]] = None,
        fix_response: Optional[Dict[str, Any]] = None,
        verification: Optional[Dict[str, Any]] = None,
        success: bool = False,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Write proof bundle to disk (§15.1).

        Default path: ~/.keyhole/doctor/<correlation-id>/
        """
        if output_dir is None:
            home = os.environ.get("KEYHOLE_HOME")
            base = Path(home) if home else Path.home() / ".keyhole"
            output_dir = base

        bundle_dir = output_dir / "doctor" / self._correlation_id
        bundle_dir.mkdir(parents=True, exist_ok=True)

        docs = self.generate(
            report=report,
            local_profile=local_profile,
            host_inventory=host_inventory,
            connection_truth=connection_truth,
            negotiation=negotiation,
            requested_fix=requested_fix,
            fix_response=fix_response,
            verification=verification,
            success=success,
        )

        for filename, content in docs.items():
            (bundle_dir / filename).write_text(content, encoding="utf-8")

        return bundle_dir

    @staticmethod
    def _build_summary(
        *,
        report: Optional[Dict[str, Any]],
        requested_fix: Optional[Dict[str, Any]],
        verification: Optional[Dict[str, Any]],
        success: bool,
    ) -> str:
        """Build human-readable summary (§17.2)."""
        lines = ["# Doctor Reconciliation Summary", ""]

        status = (report or {}).get("summary_status", "unknown")
        lines.append(f"**Overall status:** {status}")
        lines.append(f"**Success:** {success}")
        lines.append("")

        # Hosts
        hosts = (report or {}).get("hosts", [])
        if hosts:
            lines.append("## Hosts")
            for host in hosts:
                diag = host.get("diagnosis", "unknown")
                principal = host.get("current_connection_principal", "unknown")
                lines.append(
                    f"- **{host.get('host_id', '?')}**: {diag} "
                    f"(principal: {principal})"
                )
            lines.append("")

        # Fix action
        if requested_fix:
            lines.append("## Requested Fix")
            lines.append(f"- Action: {requested_fix.get('action', 'none')}")
            lines.append(f"- Host: {requested_fix.get('host_id', 'n/a')}")
            lines.append(f"- Target profile: {requested_fix.get('target_profile', 'n/a')}")
            lines.append("")

        # Verification
        if verification:
            lines.append("## Post-Fix Verification")
            verified = verification.get("verified", False)
            lines.append(f"- Verified: {verified}")
            post_principal = verification.get("post_fix_principal", "unknown")
            lines.append(f"- Post-fix principal: {post_principal}")
            lines.append("")

        return "\n".join(lines)
