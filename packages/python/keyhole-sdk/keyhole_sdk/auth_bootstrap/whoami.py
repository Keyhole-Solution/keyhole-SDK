"""Whoami client — identity inspection via MCP boundary.

Implements §6.5 of DEV-SDK-01: `keyhole whoami`.

Calls GET /mcp/v1/whoami to resolve the authenticated participant's
identity context including tenant, org, cohort, workspace, mode, and limits.
"""

from __future__ import annotations

from typing import Optional

import requests

from keyhole_sdk.auth_bootstrap.errors import NetworkError, WhoamiVerificationError
from keyhole_sdk.auth_bootstrap.models import WhoamiResponse
from keyhole_sdk.envelope import unwrap_mcp_envelope, unwrap_identity


class WhoamiClient:
    """Client for the /mcp/v1/whoami identity surface.

    whoami is the first authenticated action after login.
    It confirms boundary identity and surfaces participation context.
    """

    def __init__(
        self,
        mcp_base_url: str,
        *,
        timeout: int = 30,
    ) -> None:
        self._base_url = mcp_base_url.rstrip("/")
        self._timeout = timeout

    def whoami(self, access_token: str, *, correlation_id: str | None = None) -> WhoamiResponse:
        """Call GET /mcp/v1/whoami and return structured identity.

        Args:
            access_token: Bearer token from the auth flow.
            correlation_id: Optional correlation ID for request tracing.

        Returns:
            WhoamiResponse with full identity context.

        Raises:
            NetworkError: Cannot reach the MCP boundary.
            WhoamiVerificationError: Server returned non-200 or bad data.
        """
        url = f"{self._base_url}/mcp/v1/whoami"
        headers = {"Authorization": f"Bearer {access_token}"}
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id

        try:
            resp = requests.get(url, headers=headers, timeout=self._timeout)
        except requests.ConnectionError as exc:
            raise NetworkError(
                f"Cannot reach whoami endpoint: {exc}"
            ) from exc
        except requests.Timeout as exc:
            raise NetworkError(
                f"Whoami endpoint timed out: {exc}"
            ) from exc

        if resp.status_code == 401:
            raise WhoamiVerificationError(
                "Authentication rejected by whoami endpoint (401)"
            )
        if resp.status_code == 403:
            raise WhoamiVerificationError(
                "Access denied by whoami endpoint (403)"
            )
        if resp.status_code != 200:
            raise WhoamiVerificationError(
                f"Whoami returned unexpected status: {resp.status_code}"
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise WhoamiVerificationError(
                "Whoami response is not valid JSON"
            ) from exc

        # Unwrap MCP envelope → flat identity dict → validate
        data = unwrap_identity(unwrap_mcp_envelope(data))

        try:
            return WhoamiResponse.model_validate(data)
        except Exception as exc:
            raise WhoamiVerificationError(
                f"Whoami response does not match expected schema: {exc}"
            ) from exc
