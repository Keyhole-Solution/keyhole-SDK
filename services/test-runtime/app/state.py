import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

RUNTIME_VERSION = os.environ.get("RUNTIME_VERSION", "0.1.0")


class RuntimeState:
    def __init__(self) -> None:
        self.current_digest: Optional[str] = None
        self.realized_digests: List[str] = []
        self.governance_receipts: List[Dict[str, Any]] = []
        self.updated_at: str = datetime.now(timezone.utc).isoformat()
        self._pointer: int = 0

    def get_state(self) -> Dict:
        return {
            "current_digest": self.current_digest,
            "realized_digests": list(self.realized_digests),
            "updated_at": self.updated_at,
            "governance_receipts": list(self.governance_receipts),
        }

    def is_realized(self, digest: str) -> bool:
        return digest in self.realized_digests

    def apply_digest(
        self,
        digest: str,
        governance_verdict: str = "LOCAL_ONLY",
        governance_reason: str = "",
        governed: bool = False,
        event_spine_evidence: bool = False,
        governance_context_id: str = "",
        drift_state: str = "",
        mcp_event_id: str = "",
        proof_id: str = "",
        receipt_id: str = "",
        passport_digest: str = "",
        trust_digest: str = "",
    ) -> Dict:
        now = datetime.now(timezone.utc).isoformat()
        public_receipt = {
            "governed": governed,
            "event_spine_evidence": event_spine_evidence,
            "governance_verdict": governance_verdict,
            "drift_state": drift_state or ("not_applicable" if not governed else "not_reported"),
            "governance_context_id": governance_context_id or None,
            "mcp_event_id": mcp_event_id or None,
            "proof_id": proof_id or None,
            "receipt_id": receipt_id or None,
            "passport_digest": passport_digest or None,
            "trust_digest": trust_digest or None,
        }
        if self.is_realized(digest):
            return {
                "digest": digest,
                "status": "ALREADY_REALIZED",
                "message": "Digest has already been realized. No state mutation performed.",
                "realized_at": now,
                **public_receipt,
            }
        self.realized_digests.append(digest)
        self.current_digest = digest
        self.updated_at = now
        self._pointer += 1
        self.governance_receipts.append(
            {
                "digest": digest,
                "realized_at": now,
                **public_receipt,
            }
        )
        return {
            "digest": digest,
            "status": "ACCEPT",
            "message": "Digest realized successfully.",
            "realized_at": now,
            **public_receipt,
        }


runtime_state = RuntimeState()
