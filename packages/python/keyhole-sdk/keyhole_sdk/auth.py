"""SDK authentication — public-safe auth injection.

Implements §14 of CE-V5-S41-05: Authentication Posture.

The SDK must support public-safe authentication injection without
pretending to own identity authority.

Important boundary rule:
  The SDK may carry identity material.
  It may not create governance legitimacy.
  Only the server can do that.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional


class AuthProvider(ABC):
    """Base class for pluggable authentication providers.

    Implementations must supply bearer tokens on demand.
    The SDK never fabricates scopes or worker bindings.
    """

    @abstractmethod
    def get_token(self) -> Optional[str]:
        """Return the current bearer token, or None if unauthenticated."""

    def get_headers(self) -> dict[str, str]:
        """Return authentication headers for HTTP requests."""
        token = self.get_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}


class BearerTokenProvider(AuthProvider):
    """Static bearer token provider.

    Suitable for development and environment-based configuration.
    Never embed privileged static secrets in examples.
    """

    def __init__(self, token: str) -> None:
        if not token:
            raise ValueError("token must not be empty")
        self._token = token

    def get_token(self) -> Optional[str]:
        return self._token


class EnvironmentTokenProvider(AuthProvider):
    """Token provider that reads from an environment variable.

    Suitable for CI/CD and containerized environments.
    """

    def __init__(self, env_var: str = "KEYHOLE_TOKEN") -> None:
        self._env_var = env_var

    def get_token(self) -> Optional[str]:
        import os

        return os.environ.get(self._env_var)


class CallbackTokenProvider(AuthProvider):
    """Token provider using a callback function.

    Suitable for dynamic token refresh flows.
    """

    def __init__(self, callback: Callable[[], Optional[str]]) -> None:
        self._callback = callback

    def get_token(self) -> Optional[str]:
        return self._callback()
