"""SDK configuration — narrow, explicit configuration contract.

Implements §15 of CE-V5-S41-05: Configuration Contract.

The SDK must have a narrow, explicit configuration object.
Simple onboarding matters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import os

from keyhole_sdk.auth import AuthProvider, BearerTokenProvider


# ---------------------------------------------------------------------------
# Canonical defaults — single source of truth for all SDK/CLI modules.
#
# Every value is overridable via environment variable for portability.
# Forkable deployments change ONLY this file (or set env vars).
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL: str = os.environ.get(
    "KEYHOLE_MCP_URL", "https://mcp.keyholesolution.com"
)
DEFAULT_AUTH_SERVER: str = os.environ.get(
    "KEYHOLE_AUTH_SERVER", "https://auth.keyholesolution.com/realms/kh-prod"
)
DEFAULT_REALM: str = os.environ.get("KEYHOLE_REALM", "kh-prod")
DEFAULT_CLIENT_ID: str = os.environ.get("KEYHOLE_CLIENT_ID", "keyhole-cli")
DEFAULT_TIMEOUT = 10.0
DEFAULT_USER_AGENT = "keyhole-sdk-python"


@dataclass(frozen=True)
class KeyholeConfig:
    """Narrow, explicit SDK configuration.

    Required minimum fields per §15:
      - base_url
      - auth_provider or token
      - timeout
      - user_agent / client metadata
      - retry_enabled (optional)
      - compatibility_guard (optional)
    """

    base_url: str = DEFAULT_BASE_URL
    auth_provider: Optional[AuthProvider] = None
    token: Optional[str] = None
    timeout: float = DEFAULT_TIMEOUT
    user_agent: str = DEFAULT_USER_AGENT
    retry_enabled: bool = False
    max_retries: int = 3
    compatibility_guard: bool = True

    def __post_init__(self) -> None:
        if not self.base_url:
            raise ValueError("base_url must not be empty")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")

    def resolve_auth_provider(self) -> Optional[AuthProvider]:
        """Return the effective auth provider.

        Priority: explicit auth_provider > token shorthand > None.
        """
        if self.auth_provider is not None:
            return self.auth_provider
        if self.token is not None:
            return BearerTokenProvider(self.token)
        return None
