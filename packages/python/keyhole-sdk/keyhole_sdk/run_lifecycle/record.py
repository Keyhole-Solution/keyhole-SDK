"""Local run record store — SDK-CLIENT-17 §8.

Persists minimal local run records under .keyhole/state/runs/
to support resume, wait, tail, and proof continuity across
client interruptions.

These records are NOT authoritative — the server is always
the source of truth for run state.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict


STATE_DIR = ".keyhole/state/runs"


@dataclass
class RunRecord:
    """Minimal local run record — §8.

    Supports resume, wait, tail, and proof continuity.
    NOT the source of truth — local convenience only.
    """

    request_id: str = ""
    run_id: str = ""
    command: str = "keyhole run"
    mode: str = "regular"  # "shadow" or "regular"
    run_type: str = ""
    ctxpack_digest: str = ""
    submitted_at: str = ""
    last_known_status: str = "accepted"
    proof_path: str = ""
    repo_name: str = ""
    repo_path: str = ""
    correlation_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunRecord":
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


class LocalRunRecordStore:
    """Persist and retrieve local run records.

    Stores in <repo_dir>/.keyhole/state/runs/<run-id>.json.
    """

    def __init__(self, repo_dir: Path) -> None:
        self._repo_dir = repo_dir
        self._runs_dir = repo_dir / STATE_DIR

    def save(self, record: RunRecord) -> Path:
        """Persist a run record. Uses run_id if available, else request_id."""
        self._runs_dir.mkdir(parents=True, exist_ok=True)
        key = record.run_id or record.request_id or record.correlation_id
        if not key:
            raise ValueError("RunRecord must have run_id, request_id, or correlation_id")
        safe_name = _safe_filename(key)
        path = self._runs_dir / f"{safe_name}.json"
        data = record.to_dict()
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        path.write_text(
            json.dumps(data, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        return path

    def load(self, run_id: str) -> Optional[RunRecord]:
        """Load a run record by run_id or request_id."""
        safe_name = _safe_filename(run_id)
        path = self._runs_dir / f"{safe_name}.json"
        if path.exists():
            return self._parse_file(path)
        # Fallback: scan for matching request_id or correlation_id
        return self._scan_for(run_id)

    def update_status(self, run_id: str, status: str) -> Optional[Path]:
        """Update last_known_status on an existing record."""
        record = self.load(run_id)
        if record is None:
            return None
        record.last_known_status = status
        return self.save(record)

    def list_recent(self, limit: int = 10) -> List[RunRecord]:
        """List the most recent run records (by file mtime)."""
        if not self._runs_dir.exists():
            return []
        files = sorted(
            self._runs_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        records: List[RunRecord] = []
        for f in files[:limit]:
            rec = self._parse_file(f)
            if rec:
                records.append(rec)
        return records

    def _scan_for(self, identifier: str) -> Optional[RunRecord]:
        """Scan all records for a matching run_id, request_id, or correlation_id."""
        if not self._runs_dir.exists():
            return None
        for f in self._runs_dir.glob("*.json"):
            rec = self._parse_file(f)
            if rec and (
                rec.run_id == identifier
                or rec.request_id == identifier
                or rec.correlation_id == identifier
            ):
                return rec
        return None

    def _parse_file(self, path: Path) -> Optional[RunRecord]:
        """Parse a run record file, returning None on failure."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return RunRecord.from_dict(data)
        except (json.JSONDecodeError, OSError):
            pass
        return None


def _safe_filename(key: str) -> str:
    """Sanitize a key for use as a filename."""
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in key)[:128]
