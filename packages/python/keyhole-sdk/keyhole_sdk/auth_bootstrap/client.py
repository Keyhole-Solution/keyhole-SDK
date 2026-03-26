"""Auth bootstrap client — orchestrates the full login flow.

Implements §6.1 and §14 of SDK-CLIENT-01: Functional Flow.

Hardened flow ordering (server-aligned identity governance):
  1. Initiate auth flow
  2. Complete auth, receive provisional token/session
  3. Call /whoami — mandatory identity acquisition
  4. Validate governed identity completeness
  5. ONLY THEN persist credentials
  6. Finalize proof from server-issued truth
  7. Return success

Credentials are NEVER persisted before governed identity confirmation.
Identity is NEVER inferred from tokens — only from /whoami.
Mode is server-determined and client-read-only.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.auth_bootstrap.device import DeviceFlow
from keyhole_sdk.auth_bootstrap.errors import (
    AuthBootstrapError,
    BrowserLaunchError,
    CredentialStoreError,
    IncompleteIdentityError,
    WhoamiVerificationError,
)
from keyhole_sdk.auth_bootstrap.models import (
    AuthFlowType,
    AuthMode,
    AuthSession,
    LoginResult,
)
from keyhole_sdk.auth_bootstrap.pkce import PKCEFlow
from keyhole_sdk.auth_bootstrap.proof import AuthProofBundle
from keyhole_sdk.auth_bootstrap.whoami import WhoamiClient


# Default auth server configuration (from capabilities discovery)
_DEFAULT_AUTH_SERVER = "https://auth.keyholesolution.com/realms/keyhole-mcp"
_DEFAULT_CLIENT_ID = "keyhole-cli"
_DEFAULT_MCP_URL = "https://mcp.keyholesolution.com"
_IDENTITY_SOURCE = "server/whoami"


class AuthBootstrapClient:
    """Orchestrates the full authentication bootstrap flow.

    Manages PKCE and device flows, credential storage, whoami
    verification, and proof bundle generation.
    """

    def __init__(
        self,
        *,
        auth_server_url: str = _DEFAULT_AUTH_SERVER,
        client_id: str = _DEFAULT_CLIENT_ID,
        mcp_base_url: str = _DEFAULT_MCP_URL,
        credential_store: Optional[CredentialStore] = None,
        scope: str = "openid profile email",
    ) -> None:
        self._auth_server_url = auth_server_url
        self._client_id = client_id
        self._mcp_base_url = mcp_base_url
        self._credential_store = credential_store or CredentialStore()
        self._scope = scope

        self._pkce_flow = PKCEFlow(
            auth_server_url=auth_server_url,
            client_id=client_id,
            scope=scope,
        )
        self._device_flow = DeviceFlow(
            auth_server_url=auth_server_url,
            client_id=client_id,
            scope=scope,
        )
        self._whoami_client = WhoamiClient(mcp_base_url=mcp_base_url)

    @property
    def credential_store(self) -> CredentialStore:
        return self._credential_store

    def login(
        self,
        *,
        flow_type: AuthFlowType = AuthFlowType.PKCE,
        force: bool = False,
        correlation_id: Optional[str] = None,
        on_browser_url: Optional[callable] = None,
        on_device_code: Optional[callable] = None,
        on_status: Optional[callable] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> LoginResult:
        """Execute the full login flow.

        Hardened ordering:
          1. Auth flow → provisional token
          2. /whoami → governed identity acquisition (mandatory)
          3. Validate identity completeness
          4. Persist credentials ONLY after identity confirmed
          5. Return success

        Credentials are never persisted before /whoami success.
        Identity is never inferred from token contents.

        Args:
            flow_type: Preferred auth flow (PKCE, device, or password).
            force: If True, ignore existing credentials and re-authenticate.
            correlation_id: Lifecycle correlation ID (generated if not provided).
            on_browser_url: Callback when PKCE URL is ready (receives URL string).
            on_device_code: Callback when device code is ready (receives DeviceCodeResponse).
            on_status: Callback for status updates (receives status string).
            username: Username for password (ROPC) flow.
            password: Password for password (ROPC) flow.

        Returns:
            LoginResult with success/failure status and identity context.
        """
        cid = correlation_id or str(uuid.uuid4())

        # Check if already authenticated (unless forced)
        if not force and self._credential_store.is_authenticated():
            session = self._credential_store.load()
            if session:
                try:
                    whoami = self._whoami_client.whoami(
                        session.access_token, correlation_id=cid
                    )
                    missing = whoami.validate_required_identity()
                    if missing:
                        raise IncompleteIdentityError(missing_fields=missing)
                    session.mode = whoami.mode
                    session.last_verified_at = datetime.now(timezone.utc)
                    self._credential_store.save(session)
                    return LoginResult(
                        success=True,
                        flow_type=session.flow_type,
                        mode=whoami.mode,
                        whoami=whoami,
                        correlation_id=cid,
                        credential_persisted=True,
                        verification_passed=True,
                        identity_source=_IDENTITY_SOURCE,
                    )
                except (AuthBootstrapError, Exception):
                    # Existing session is stale, proceed with fresh login
                    pass

        if on_status:
            on_status(f"Starting {flow_type.value} authentication flow...")

        try:
            if flow_type == AuthFlowType.PKCE:
                token_response = self._do_pkce_flow(
                    on_browser_url=on_browser_url,
                    on_status=on_status,
                )
            elif flow_type == AuthFlowType.PASSWORD:
                if not username or not password:
                    from keyhole_sdk.auth_bootstrap.errors import InvalidTokenError
                    raise InvalidTokenError(
                        "Password flow requires username and password."
                    )
                token_response = self._do_password_flow(
                    username=username,
                    password=password,
                    on_status=on_status,
                )
            else:
                token_response = self._do_device_flow(
                    on_device_code=on_device_code,
                    on_status=on_status,
                )
        except AuthBootstrapError as exc:
            return LoginResult(
                success=False,
                flow_type=flow_type,
                correlation_id=cid,
                error_class=exc.error_class,
                error_message=str(exc),
                repair_suggestions=exc.repair_suggestions,
            )

        # Build provisional session from token response (NOT yet persisted)
        expires_at = None
        if token_response.expires_in is not None:
            from datetime import timedelta
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=token_response.expires_in
            )

        session = AuthSession(
            access_token=token_response.access_token,
            token_type=token_response.token_type,
            refresh_token=token_response.refresh_token,
            expires_at=expires_at,
            scope=token_response.scope,
            flow_type=flow_type,
            auth_server_url=self._auth_server_url,
        )

        # ── MANDATORY: Acquire governed identity via /whoami ──
        if on_status:
            on_status("Acquiring governed identity...")
        try:
            whoami = self._whoami_client.whoami(
                session.access_token, correlation_id=cid
            )
        except (WhoamiVerificationError, AuthBootstrapError) as exc:
            # Token was received but identity acquisition failed.
            # Do NOT persist credentials. This is a failed login.
            return LoginResult(
                success=False,
                flow_type=flow_type,
                correlation_id=cid,
                error_class=getattr(exc, "error_class", "whoami_verification_error"),
                error_message=str(exc),
                repair_suggestions=getattr(exc, "repair_suggestions", [
                    "Retry login: keyhole login",
                    "Check that the MCP server is reachable.",
                ]),
                credential_persisted=False,
                verification_passed=False,
            )

        # ── Validate governed identity completeness ──
        missing = whoami.validate_required_identity()
        if missing:
            return LoginResult(
                success=False,
                flow_type=flow_type,
                correlation_id=cid,
                error_class="incomplete_identity",
                error_message=f"Server returned incomplete identity: missing {', '.join(missing)}",
                repair_suggestions=[
                    "Retry login: keyhole login --force",
                    "Contact your organization admin — your account may not be fully provisioned.",
                ],
                credential_persisted=False,
                verification_passed=False,
            )

        # ── Mode comes from server only ──
        session.mode = whoami.mode
        session.last_verified_at = datetime.now(timezone.utc)

        # ── Persist credentials ONLY after identity confirmed ──
        if on_status:
            on_status("Storing credentials...")
        try:
            self._credential_store.save(session)
        except CredentialStoreError as exc:
            return LoginResult(
                success=False,
                flow_type=flow_type,
                correlation_id=cid,
                error_class=exc.error_class,
                error_message=str(exc),
                repair_suggestions=exc.repair_suggestions,
                credential_persisted=False,
                verification_passed=True,
            )

        return LoginResult(
            success=True,
            flow_type=flow_type,
            mode=whoami.mode,
            whoami=whoami,
            correlation_id=cid,
            credential_persisted=True,
            verification_passed=True,
            identity_source=_IDENTITY_SOURCE,
        )

    def _do_pkce_flow(
        self,
        *,
        on_browser_url: Optional[callable] = None,
        on_status: Optional[callable] = None,
    ):
        """Execute the PKCE browser-based authentication flow."""
        challenge = self._pkce_flow.generate_challenge()

        if on_status:
            on_status("Opening browser for authentication...")

        browser_opened = self._pkce_flow.open_browser(challenge.authorization_url)

        if not browser_opened:
            if on_browser_url:
                on_browser_url(challenge.authorization_url)
            else:
                raise BrowserLaunchError()

        if on_browser_url:
            on_browser_url(challenge.authorization_url)

        if on_status:
            on_status("Waiting for browser callback...")

        code = self._pkce_flow.wait_for_callback(challenge.state)

        if on_status:
            on_status("Exchanging authorization code...")

        return self._pkce_flow.exchange_code(code, challenge.code_verifier)

    def _do_device_flow(
        self,
        *,
        on_device_code: Optional[callable] = None,
        on_status: Optional[callable] = None,
    ):
        """Execute the device/constrained authentication flow."""
        device_resp = self._device_flow.request_device_code()

        if on_device_code:
            on_device_code(device_resp)

        if on_status:
            on_status("Waiting for device authorization...")

        return self._device_flow.poll_for_token(
            device_resp.device_code,
            interval=device_resp.interval,
            expires_in=device_resp.expires_in,
        )

    def _do_password_flow(
        self,
        *,
        username: str,
        password: str,
        on_status: Optional[callable] = None,
    ):
        """Execute the Resource Owner Password Credentials (ROPC) flow.

        Only for dev/test environments where ROPC is enabled on the client.
        Production clients MUST use device or PKCE flows.
        """
        import requests
        from keyhole_sdk.auth_bootstrap.errors import InvalidTokenError, NetworkError

        if on_status:
            on_status("Authenticating with password flow...")

        # Discover OIDC endpoints via the device flow helper (reuse discovery logic)
        oidc = self._device_flow._discover_oidc()
        token_url = oidc.get("token_endpoint") or (
            f"{self._auth_server_url}/protocol/openid-connect/token"
        )

        payload = {
            "grant_type": "password",
            "client_id": self._client_id,
            "username": username,
            "password": password,
            "scope": self._scope,
        }

        try:
            resp = requests.post(token_url, data=payload, timeout=30)
        except requests.ConnectionError as exc:
            raise NetworkError(f"Cannot reach token endpoint: {exc}") from exc
        except requests.Timeout as exc:
            raise NetworkError(f"Token endpoint timed out: {exc}") from exc

        if resp.status_code != 200:
            try:
                err = resp.json().get("error_description") or resp.json().get("error") or resp.text[:200]
            except ValueError:
                err = resp.text[:200]
            raise InvalidTokenError(f"Password flow failed (HTTP {resp.status_code}): {err}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise InvalidTokenError("Token response is not valid JSON") from exc

        from keyhole_sdk.auth_bootstrap.models import TokenResponse
        return TokenResponse.model_validate(data)
