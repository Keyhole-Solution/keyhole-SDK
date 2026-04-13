"""Local context tracker — SDK-CLIENT-16 §5.1/§15.

Persists the most recently compiled context digest under
.keyhole/state/ as a local convenience artifact.

This is NOT authoritative platform truth — it is a local
convenience pointer only.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


STATE_DIR = ".keyhole/state"
RECENT_CONTEXT_FILE = "recent-context.json"


class LocalContextTracker:
    """Track the most recently compiled context digest locally.

    Stores in <repo_dir>/.keyhole/state/recent-context.json.
    This is Optional convenience metadata — not authoritative.
    """

    def __init__(self, repo_dir: Path) -> None:
        self._repo_dir = repo_dir
        self._state_dir = repo_dir / STATE_DIR

    def save(
        self,
        *,
        ctxpack_digest: str,
        repo_name: str = "",
        correlation_id: str = "",
    ) -> Path:
        """Persist a recent context reference."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        path = self._state_dir / RECENT_CONTEXT_FILE

        data: Dict[str, Any] = {
            "ctxpack_digest": ctxpack_digest,
            "repo_name": repo_name,
            "correlation_id": correlation_id,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(
            json.dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def load(self) -> Optional[Dict[str, Any]]:
        """Load the most recent context reference, or None."""
        path = self._state_dir / RECENT_CONTEXT_FILE
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("ctxpack_digest"):
                return data
        except (json.JSONDecodeError, OSError):
            pass
        return None

    def get_recent_digest(self) -> Optional[str]:
        """Return the most recently observed digest, or None."""
        data = self.load()
        return data.get("ctxpack_digest") if data else None

    def clear(self) -> None:
        """Remove the recent context reference."""
        path = self._state_dir / RECENT_CONTEXT_FILE
        if path.exists():
            path.unlink()
