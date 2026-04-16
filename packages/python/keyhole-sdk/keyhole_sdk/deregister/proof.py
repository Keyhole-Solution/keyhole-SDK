"""SDK-CLIENT-22 — Deregistration proof bundle.

Identity-scoped proof artifacts — §17.
Default location: ``~/.keyhole/deregister/<correlation-id>/``
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class DeregistrationProofBundle:
    """Generates proof artifacts for the deregistration lifecycle.

    All materials are secret-safe — no tokens, passwords, or
    sensitive credentials appear in any artifact.
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
        request: Optional[Dict[str, Any]] = None,
        outcome: Optional[Dict[str, Any]] = None,
        identity_snapshot: Optional[Dict[str, Any]] = None,
        success: bool = False,
    ) -> Dict[str, Any]:
        """Generate the full proof bundle.

        Parameters
        ----------
        request:
            to_proof_dict() from DeregistrationRequest.
        outcome:
            safe_summary() from DeregistrationOutcome.
        identity_snapshot:
            Acting identity from whoami.
        success:
            Whether the deregistration was accepted.
        """
        completed_at = datetime.now(timezone.utc)

        core = {
            "proof_type": "deregistration",
            "story_id": "SDK-CLIENT-22",
            "correlation_id": self._correlation_id,
            "success": success,
            "registration_id": (request or {}).get("registration_id"),
            "realm": (request or {}).get("realm"),
            "status": (outcome or {}).get("status"),
            "run_id": (outcome or {}).get("run_id"),
            "started_at": self._started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
        }

        request_doc = request or {"initiated_at": self._started_at.isoformat()}
        response_doc = outcome or {}

        identity_doc = identity_snapshot or {}

        event_chain = {
            "correlation_id": self._correlation_id,
            "events": self._events,
        }

        correlation_doc = {
            "correlation_id": self._correlation_id,
            "run_id": (outcome or {}).get("run_id"),
            "started_at": self._started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
        }

        # Repair is only relevant for non-success paths
        repair_doc = {}
        if not success and outcome:
            repair_doc = {
                "status": outcome.get("status"),
                "reason": outcome.get("reason"),
                "repair_guidance": outcome.get("repair_guidance", []),
            }

        summary_lines = [
            f"# Deregistration Proof — {self._correlation_id}",
            "",
            f"- **Story:** SDK-CLIENT-22",
            f"- **Registration ID:** {(request or {}).get('registration_id', 'N/A')}",
            f"- **Status:** {(outcome or {}).get('status', 'N/A')}",
            f"- **Success:** {success}",
            f"- **Started:** {self._started_at.isoformat()}",
            f"- **Completed:** {completed_at.isoformat()}",
        ]
        if outcome and outcome.get("run_id"):
            summary_lines.append(f"- **Run ID:** {outcome['run_id']}")
        summary_md = "\n".join(summary_lines) + "\n"

        # Compute digest over core
        core_json = json.dumps(core, sort_keys=True, default=str)
        digest = hashlib.sha256(core_json.encode()).hexdigest()

        return {
            "core.json": core,
            "request.json": request_doc,
            "response.json": response_doc,
            "identity_snapshot.json": identity_doc,
            "event_chain.json": event_chain,
            "correlation.json": correlation_doc,
            "repair.json": repair_doc,
            "summary.md": summary_md,
            "digest.txt": f"sha256:{digest}",
        }

    def write(
        self,
        *,
        request: Optional[Dict[str, Any]] = None,
        outcome: Optional[Dict[str, Any]] = None,
        identity_snapshot: Optional[Dict[str, Any]] = None,
        success: bool = False,
        output_dir: Path,
    ) -> Path:
        """Write proof bundle to disk — §17.

        Default target: ``<output_dir>/deregister/<correlation-id>/``
        """
        bundle = self.generate(
            request=request,
            outcome=outcome,
            identity_snapshot=identity_snapshot,
            success=success,
        )
        bundle_dir = output_dir / "deregister" / self._correlation_id
        bundle_dir.mkdir(parents=True, exist_ok=True)

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
