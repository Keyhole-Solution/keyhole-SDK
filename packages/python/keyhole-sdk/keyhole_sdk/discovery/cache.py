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
import hashlib
from datetime import datetime, timedelta, timezone
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
        base_url: str = "",
        ttl_seconds: int = 3600,
    ) -> None:
        self._cache_dir = Path(cache_dir or DEFAULT_CACHE_DIR)
        self._base_url = base_url.rstrip("/")
        self._ttl_seconds = ttl_seconds
        if base_url and cache_file == DEFAULT_CACHE_FILE:
            digest = hashlib.sha256(self._base_url.encode("utf-8")).hexdigest()[:16]
            cache_file = f"capabilities_cache_{digest}.json"
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

        cached_at = datetime.now(timezone.utc)
        expires_at = cached_at + timedelta(seconds=max(self._ttl_seconds, 0))
        raw_digest = hashlib.sha256(
            json.dumps(result.raw, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        envelope = {
            "base_url": self._base_url,
            "server_identity": result.get_contract_version(),
            "capability_contract_version": result.get_contract_version(),
            "runtime_digest": result.metadata.digest or result.metadata.ctx_ref_sha256,
            "raw_response_digest": f"sha256:{raw_digest}",
            "cached_at": cached_at.isoformat(),
            "fetched_at": cached_at.isoformat(),
            "expires_at": expires_at.isoformat(),
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

    def load_valid(self) -> Optional[CapabilitiesResult]:
        """Load the cache only when it matches the base URL and is not expired."""
        path = self.cache_path
        if not path.exists():
            return None
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if self._base_url and envelope.get("base_url") != self._base_url:
            return None
        expires_at = envelope.get("expires_at")
        if isinstance(expires_at, str) and expires_at:
            try:
                parsed = datetime.fromisoformat(expires_at)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                if parsed <= datetime.now(timezone.utc):
                    return None
            except ValueError:
                return None
        return self.load()

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
