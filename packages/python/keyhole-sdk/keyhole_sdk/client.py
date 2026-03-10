from __future__ import annotations

from typing import Any, Mapping, Optional

import requests

DEFAULT_TIMEOUT = 10.0


class KeyholeClient:
    """Python client for interacting with a Keyhole-compatible runtime."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self.session.request(
            method,
            f"{self.base_url}{path}",
            timeout=self.timeout,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()

    def health(self) -> dict[str, Any]:
        """Return runtime health information."""
        return self._request("GET", "/healthz")

    def identity(self) -> dict[str, Any]:
        """Return runtime identity and declared capabilities."""
        return self._request("GET", "/identity")

    def state(self) -> dict[str, Any]:
        """Return the current runtime-local state view."""
        return self._request("GET", "/state")

    def realize(
        self,
        candidate_digest: str,
        payload: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        """Submit a bounded realization request using the current public contract."""
        body = {
            "candidate_digest": candidate_digest,
            "payload": dict(payload or {}),
        }
        return self._request("POST", "/realize", json=body)

    def realize_request(self, request_body: Mapping[str, Any]) -> dict[str, Any]:
        """Submit a prebuilt realization request body."""
        return self._request("POST", "/realize", json=dict(request_body))

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()


# Backward-compatible alias for the current class name on main.
RuntimeBridgeClient = KeyholeClient