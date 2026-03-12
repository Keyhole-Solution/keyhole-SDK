"""HTTP transport — internal transport implementation.

This module is NOT part of the public API surface.
Users program against client methods, not transport internals.
"""

from __future__ import annotations

from typing import Any, Optional

import requests

from keyhole_sdk.auth import AuthProvider
from keyhole_sdk.exceptions import (
    PublicEndpointError,
    RuntimeUnavailableError,
    SchemaError,
    TransportError,
)


class HttpTransport:
    """Low-level HTTP transport for Keyhole runtime communication."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        auth_provider: Optional[AuthProvider] = None,
        user_agent: str = "keyhole-sdk-python",
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.auth_provider = auth_provider
        self.user_agent = user_agent
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = self.user_agent

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Execute an HTTP request and return parsed JSON."""
        headers = kwargs.pop("headers", {})
        if self.auth_provider:
            headers.update(self.auth_provider.get_headers())

        try:
            response = self.session.request(
                method,
                f"{self.base_url}{path}",
                timeout=self.timeout,
                headers=headers,
                **kwargs,
            )
        except (requests.ConnectionError, requests.Timeout, OSError) as exc:
            raise TransportError(str(exc)) from exc

        if response.status_code >= 500:
            raise RuntimeUnavailableError(
                f"Runtime returned {response.status_code}: {response.text[:200]}"
            )

        if response.status_code >= 400:
            try:
                body = response.json()
            except ValueError:
                body = {}
            raise PublicEndpointError(
                body.get("error", response.reason or "request failed"),
                status_code=response.status_code,
                detail=body.get("detail", ""),
            )

        try:
            return response.json()
        except ValueError as exc:
            raise SchemaError("Response is not valid JSON", raw_data=None) from exc

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()
