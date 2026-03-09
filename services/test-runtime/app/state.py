import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

RUNTIME_VERSION = os.environ.get("RUNTIME_VERSION", "0.1.0")


class RuntimeState:
    def __init__(self) -> None:
        self.current_digest: Optional[str] = None
        self.realized_digests: List[str] = []
        self.updated_at: str = datetime.now(timezone.utc).isoformat()
        self._pointer: int = 0

    def get_state(self) -> Dict:
        return {
            "current_digest": self.current_digest,
            "realized_digests": list(self.realized_digests),
            "updated_at": self.updated_at,
        }

    def is_realized(self, digest: str) -> bool:
        return digest in self.realized_digests

    def apply_digest(
        self,
        digest: str,
        governance_verdict: str = "LOCAL_ONLY",
        governance_reason: str = "",
    ) -> Dict:
        now = datetime.now(timezone.utc).isoformat()
        if self.is_realized(digest):
            return {
                "digest": digest,
                "status": "ALREADY_REALIZED",
                "message": "Digest has already been realized. No state mutation performed.",
                "realized_at": now,
            }
        self.realized_digests.append(digest)
        self.current_digest = digest
        self.updated_at = now
        self._pointer += 1
        return {
            "digest": digest,
            "status": "ACCEPT",
            "message": "Digest realized successfully.",
            "realized_at": now,
        }


runtime_state = RuntimeState()
