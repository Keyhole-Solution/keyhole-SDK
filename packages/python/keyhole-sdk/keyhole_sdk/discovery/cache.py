"""Advisory discovery cache — local convenience, not governing truth.

CE-V5-S42-03: Capabilities Discovery Client.

Cache rules:
  1. Live discovery is authoritative.
  2. Cache is advisory — a convenience artifact, not a truth source.
  3. Timestamps and digests are preserved.
  4. A cache miss must not cause fabrication of missing capabilities.
  5. Local file only — no shared-state complexity.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from keyhole_sdk.discovery.models import CapabilitiesResult


DEFAULT_CACHE_DIR = ".keyhole"
DEFAULT_CACHE_FILE = "capabilities_cache.json"


class CapabilitiesCache:
    """Local advisory cache for capabilities discovery snapshots.

    Usage::

        cache = CapabilitiesCache()
        result = client.fetch()
        cache.store(result)

        # Later:
        cached = cache.load()
        if cached is not None:
            print(cached.get_contract_version())
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        cache_file: str = DEFAULT_CACHE_FILE,
    ) -> None:
        self._cache_dir = Path(cache_dir or DEFAULT_CACHE_DIR)
        self._cache_file = cache_file

    @property
    def cache_path(self) -> Path:
        """Full path to the cache file."""
        return self._cache_dir / self._cache_file

    def store(self, result: CapabilitiesResult) -> Path:
        """Store a discovery snapshot to the local cache.

        Returns the path where the snapshot was written.
        Preserves all metadata and the full raw response.
        """
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        envelope = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "advisory": True,
            "result": result.model_dump(),
        }

        path = self.cache_path
        path.write_text(
            json.dumps(envelope, indent=2, default=str),
            encoding="utf-8",
        )
        return path

    def load(self) -> Optional[CapabilitiesResult]:
        """Load a cached discovery snapshot if one exists.

        Returns ``None`` on cache miss or parse failure.
        Never fabricates missing capabilities.
        """
        path = self.cache_path
        if not path.exists():
            return None

        try:
            text = path.read_text(encoding="utf-8")
            envelope = json.loads(text)
        except (OSError, json.JSONDecodeError):
            return None

        result_data = envelope.get("result")
        if not isinstance(result_data, dict):
            return None

        try:
            return CapabilitiesResult.model_validate(result_data)
        except Exception:
            return None

    def exists(self) -> bool:
        """Return True if a cached snapshot exists on disk."""
        return self.cache_path.exists()

    def cached_at(self) -> Optional[str]:
        """Return the ISO-8601 timestamp of the cached snapshot, or None."""
        path = self.cache_path
        if not path.exists():
            return None
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            return envelope.get("cached_at")
        except (OSError, json.JSONDecodeError):
            return None

    def clear(self) -> None:
        """Remove the cached snapshot."""
        path = self.cache_path
        if path.exists():
            path.unlink()
