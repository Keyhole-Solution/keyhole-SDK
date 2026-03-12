"""Keyhole SDK client — stable public interface to Keyhole runtimes.

CE-V5-S41-05: SDK Surface Contract.

Provides both direct methods and grouped surface namespaces.
The client is a stable façade over internal transport (§12.1).

Per §12.2: KeyholeClient for synchronous flows.
AsyncKeyholeClient is reserved for future async implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

import requests
from pydantic import ValidationError

from keyhole_sdk import __version__
from keyhole_sdk.auth import AuthProvider
from keyhole_sdk.config import KeyholeConfig
from keyhole_sdk.exceptions import (
    AuthenticationError,
    CompatibilityError,
    PublicEndpointError,
    RuntimeUnavailableError,
    SchemaError,
    TransportError,
)
from keyhole_sdk.models import (
    CompatibilityResult,
    CompatibilityStatus,
    RealizationReceipt,
    RealizationRequest,
    RuntimeHealth,
    RuntimeIdentity,
    RuntimeState,
)
from keyhole_sdk.transport.http import HttpTransport
from keyhole_sdk.surfaces.system import SystemSurface
from keyhole_sdk.surfaces.identity import IdentitySurface
from keyhole_sdk.surfaces.declarations import DeclarationsSurface
from keyhole_sdk.surfaces.runs import RunsSurface
from keyhole_sdk.surfaces.evidence import EvidenceSurface


DEFAULT_TIMEOUT = 10.0

# Required public contract fields by endpoint
_REQUIRED_IDENTITY_FIELDS = {
    "runtime_id",
    "runtime_name",
    "runtime_version",
    "environment",
    "capabilities",
}
_REQUIRED_RECEIPT_FIELDS = {"digest", "status", "message", "realized_at"}
_REQUIRED_STATE_FIELDS = {"updated_at"}


class KeyholeClient:
    """Python client for interacting with a Keyhole-compatible runtime.

    Can be constructed directly or via KeyholeConfig:

        # Direct construction (backward compatible)
        client = KeyholeClient("http://localhost:8080")

        # Config-based construction (S41-05)
        config = KeyholeConfig(base_url="http://localhost:8080", token="...")
        client = KeyholeClient.from_config(config)

    Grouped surfaces (§11):
        client.system      — health, compatibility
        client.identity    — whoami
        client.declarations — submit declarations
        client.runs        — state, results
        client.evidence    — evidence retrieval
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        *,
        timeout: float = DEFAULT_TIMEOUT,
        session: Optional[requests.Session] = None,
        auth_provider: Optional[AuthProvider] = None,
        config: Optional[KeyholeConfig] = None,
    ) -> None:
        if config is not None:
            base_url = config.base_url
            timeout = config.timeout
            auth_provider = config.resolve_auth_provider()

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport = HttpTransport(
            base_url=self.base_url,
            timeout=timeout,
            auth_provider=auth_provider,
            user_agent=config.user_agent if config else "keyhole-sdk-python",
            session=session,
        )

        # Grouped surfaces per §11
        self.system = SystemSurface(self._transport)
        self.identity_surface = IdentitySurface(self._transport)
        self.declarations = DeclarationsSurface(self._transport)
        self.runs = RunsSurface(self._transport)
        self.evidence = EvidenceSurface(self._transport)

    @classmethod
    def from_config(cls, config: KeyholeConfig, **kwargs: Any) -> "KeyholeClient":
        """Create a client from a KeyholeConfig object."""
        return cls(config=config, **kwargs)

    # ── raw request helper (backward compat) ────────────────

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        return self._transport.request(method, path, **kwargs)

    # ── legacy dict-returning methods (backward-compatible) ──

    def health(self) -> dict[str, Any]:
        """Return runtime health information (raw dict)."""
        return self._request("GET", "/healthz")

    def identity(self) -> dict[str, Any]:
        """Return runtime identity and declared capabilities (raw dict)."""
        return self._request("GET", "/identity")

    def state(self) -> dict[str, Any]:
        """Return the current runtime-local state view (raw dict)."""
        return self._request("GET", "/state")

    def realize(
        self,
        candidate_digest: str,
        payload: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        """Submit a bounded realization request (raw dict return)."""
        body = {
            "candidate_digest": candidate_digest,
            "payload": dict(payload or {}),
        }
        return self._request("POST", "/realize", json=body)

    def realize_request(self, request_body: Mapping[str, Any]) -> dict[str, Any]:
        """Submit a prebuilt realization request body (raw dict return)."""
        return self._request("POST", "/realize", json=dict(request_body))

    # ── typed methods (S41-03 + S41-05) ─────────────────────

    def get_identity(self) -> RuntimeIdentity:
        """Return typed runtime identity."""
        return self.identity_surface.whoami()

    def get_health(self) -> RuntimeHealth:
        """Return typed runtime health."""
        return self.system.health()

    def get_state(self) -> RuntimeState:
        """Return typed runtime state."""
        return self.runs.get_state()

    def realize_typed(
        self,
        candidate_digest: str,
        payload: Optional[Mapping[str, Any]] = None,
    ) -> RealizationReceipt:
        """Submit a realization request and return a typed receipt."""
        return self.declarations.submit(candidate_digest, payload)

    def check_compatibility(self) -> CompatibilityResult:
        """Check SDK / runtime compatibility deterministically."""
        return self.system.check_compatibility()

    # ── lifecycle ────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._transport.close()

    def __enter__(self) -> "KeyholeClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


# Backward-compatible alias for the current class name on main.
RuntimeBridgeClient = KeyholeClient
