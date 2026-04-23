"""Browser OIDC compatibility check — core validation logic.

Implements §11.1 and §14 of SDK-CLIENT-01-F.

Performs a pure client-side validation of whether a standards-based browser
OIDC client is correctly positioned to authenticate against Keyhole via the
Authorization Code + PKCE flow.

This module makes lightweight network requests ONLY to:
  - the OIDC discovery endpoint (/.well-known/openid-configuration)
  - the authorization endpoint (HTTP HEAD to test reachability)
  - the token endpoint (HTTP HEAD to test reachability)

It does NOT initiate auth sessions, open browsers, or exchange tokens.

INV-SDK-CLIENT-01-F-001 — Standard browser path is primary.
INV-SDK-CLIENT-01-F-004 — Browser validation is explicit.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from keyhole_sdk.auth_browser.detours import detect_unsupported_detour, is_loopback_redirect
from keyhole_sdk.auth_browser.models import (
    BrowserCheckVerdict,
    BrowserCompatibilityReport,
    BrowserFailureClass,
    DirectMcpPosture,
    PasswordlessBrowserPosture,
    PkcePosture,
    RedirectPosture,
    RepairItem,
)

# Discovery metadata field that signals passwordless browser continuation (SDK-SERVER-01-F)
_PASSWORDLESS_BROWSER_CLAIM = "keyhole_passwordless_browser_continuation"

# PKCE methods field from OIDC discovery
_PKCE_METHODS_FIELD = "code_challenge_methods_supported"

_TIMEOUT = 5  # seconds — short; check is non-blocking


def _build_discovery_url(auth_server_url: str) -> str:
    """Derive the OIDC well-known URL from the auth server base URL."""
    base = auth_server_url.rstrip("/")
    if "/.well-known/openid-configuration" in base:
        return base
    return f"{base}/.well-known/openid-configuration"


def _fetch_oidc_discovery(discovery_url: str) -> Optional[Dict[str, Any]]:
    """Attempt to fetch OIDC discovery document.  Returns None on failure."""
    try:
        resp = requests.get(discovery_url, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _check_endpoint_reachable(url: str) -> bool:
    """Return True if the endpoint is reachable (HTTP 2xx/3xx/4xx on HEAD)."""
    try:
        resp = requests.head(url, timeout=_TIMEOUT, allow_redirects=True)
        return resp.status_code < 500
    except Exception:
        return False


def _classify_redirect_posture(redirect_uri: Optional[str]) -> RedirectPosture:
    if not redirect_uri:
        return RedirectPosture.NOT_PROVIDED
    if is_loopback_redirect(redirect_uri):
        return RedirectPosture.LOOPBACK
    try:
        parsed = urlparse(redirect_uri)
        if parsed.scheme and "://" not in redirect_uri[:20] and ":" in redirect_uri.split("//")[0]:
            return RedirectPosture.CUSTOM_SCHEME
    except Exception:
        pass
    # Non-loopback, non-custom-scheme URI for a public client is unusual
    return RedirectPosture.MISMATCH


def _pkce_posture_from_discovery(discovery: Dict[str, Any]) -> PkcePosture:
    methods = discovery.get(_PKCE_METHODS_FIELD, [])
    if "S256" in methods:
        return PkcePosture.SUPPORTED
    if methods:
        return PkcePosture.NOT_ADVERTISED
    return PkcePosture.UNKNOWN


def _passwordless_browser_posture_from_discovery(
    discovery: Dict[str, Any],
) -> PasswordlessBrowserPosture:
    """Infer passwordless browser continuation support from discovery metadata.

    §14.3: The server-side posture signal is introduced by SDK-SERVER-01-F.
    Until that signal is present, posture is UNKNOWN (not assumed supported).
    """
    if discovery.get(_PASSWORDLESS_BROWSER_CLAIM) is True:
        return PasswordlessBrowserPosture.SUPPORTED
    if discovery.get(_PASSWORDLESS_BROWSER_CLAIM) is False:
        return PasswordlessBrowserPosture.NOT_SUPPORTED
    # Not present in discovery → server has not deployed SDK-SERVER-01-F yet
    return PasswordlessBrowserPosture.UNKNOWN


def _build_repair(
    failure_classes: List[BrowserFailureClass],
) -> List[RepairItem]:
    """Generate ordered repair steps for all detected failures."""
    repair: List[RepairItem] = []
    step = 1

    REPAIR_MAP = {
        BrowserFailureClass.OIDC_DISCOVERY_UNAVAILABLE: [
            "Verify the realm URL and auth host reachability.",
            "Rerun keyhole auth browser-check after confirming auth host is up.",
        ],
        BrowserFailureClass.PASSWORDLESS_BROWSER_NOT_SUPPORTED: [
            "Deploy SDK-SERVER-01-F to enable browser passwordless continuation.",
            "Rerun keyhole auth browser-check.",
            "Do not switch to mcp-proxy as an alternate auth path.",
        ],
        BrowserFailureClass.REDIRECT_URI_MISMATCH: [
            "Correct the client redirect URI to use a loopback address (http://127.0.0.1:<port>/).",
            "Rerun keyhole auth browser-check --redirect-uri <corrected>.",
        ],
        BrowserFailureClass.UNSUPPORTED_DETOUR_DETECTED: [
            "Remove proxy/token-injection configuration.",
            "Restore direct Keyhole endpoint usage.",
            "Rerun keyhole auth browser-check.",
        ],
        BrowserFailureClass.BROWSER_AUTH_TIMEOUT: [
            "Capture a support bundle: keyhole auth browser-support-bundle.",
            "Confirm passwordless browser continuation support with the above check.",
            "Retry using the standard browser flow.",
        ],
        BrowserFailureClass.LOOPBACK_CALLBACK_NOT_COMPLETED: [
            "Verify local callback listener behavior in the client.",
            "Verify the browser completion actually resumed the original auth session.",
        ],
    }

    for fc in failure_classes:
        instructions = REPAIR_MAP.get(fc, [f"Investigate failure: {fc.value}"])
        for instr in instructions:
            repair.append(RepairItem(step=step, instruction=instr, failure_class=fc))
            step += 1

    return repair


def run_browser_check(
    *,
    realm: str,
    client_id: str,
    auth_server_url: str,
    redirect_uri: Optional[str] = None,
    timeout: int = _TIMEOUT,
) -> BrowserCompatibilityReport:
    """Run a full browser OIDC compatibility check.

    Validates:
      1. OIDC discovery reachability
      2. Authorization / token endpoint reachability
      3. PKCE posture from discovery
      4. Redirect URI loopback posture (when provided)
      5. Passwordless browser continuation posture
      6. Direct vs detour posture of the auth server URL

    Returns a BrowserCompatibilityReport with verdict and repair guidance.

    This function does NOT open a browser or attempt authentication.
    """
    failure_classes: List[BrowserFailureClass] = []

    # ── Step 1: Detour detection ──────────────────────────────
    direct_mcp_posture = detect_unsupported_detour(auth_server_url)
    unsupported_detour_detected = direct_mcp_posture == DirectMcpPosture.DETOUR
    if unsupported_detour_detected:
        failure_classes.append(BrowserFailureClass.UNSUPPORTED_DETOUR_DETECTED)

    # ── Step 2: OIDC discovery ────────────────────────────────
    discovery_url = _build_discovery_url(auth_server_url)
    discovery = _fetch_oidc_discovery(discovery_url)
    discovery_reachable = discovery is not None

    if not discovery_reachable:
        failure_classes.append(BrowserFailureClass.OIDC_DISCOVERY_UNAVAILABLE)

    # ── Step 3: Extract endpoints ─────────────────────────────
    issuer: Optional[str] = None
    authorization_endpoint: Optional[str] = None
    token_endpoint: Optional[str] = None
    pkce_posture = PkcePosture.UNKNOWN
    passwordless_posture = PasswordlessBrowserPosture.UNKNOWN

    if discovery:
        issuer = discovery.get("issuer")
        authorization_endpoint = discovery.get("authorization_endpoint")
        token_endpoint = discovery.get("token_endpoint")
        pkce_posture = _pkce_posture_from_discovery(discovery)
        passwordless_posture = _passwordless_browser_posture_from_discovery(discovery)

    if passwordless_posture == PasswordlessBrowserPosture.NOT_SUPPORTED:
        failure_classes.append(BrowserFailureClass.PASSWORDLESS_BROWSER_NOT_SUPPORTED)

    # ── Step 4: Redirect URI posture ──────────────────────────
    redirect_posture = _classify_redirect_posture(redirect_uri)
    if redirect_uri and redirect_posture == RedirectPosture.MISMATCH:
        failure_classes.append(BrowserFailureClass.REDIRECT_URI_MISMATCH)

    # ── Step 5: Determine verdict ─────────────────────────────
    if unsupported_detour_detected:
        verdict = BrowserCheckVerdict.UNSUPPORTED_DETOUR_DETECTED
    elif BrowserFailureClass.OIDC_DISCOVERY_UNAVAILABLE in failure_classes:
        verdict = BrowserCheckVerdict.MISCONFIGURED
    elif BrowserFailureClass.REDIRECT_URI_MISMATCH in failure_classes:
        verdict = BrowserCheckVerdict.MISCONFIGURED
    elif BrowserFailureClass.PASSWORDLESS_BROWSER_NOT_SUPPORTED in failure_classes:
        verdict = BrowserCheckVerdict.BLOCKED
    elif not discovery_reachable:
        verdict = BrowserCheckVerdict.MISCONFIGURED
    else:
        verdict = BrowserCheckVerdict.COMPATIBLE

    repair = _build_repair(failure_classes)

    return BrowserCompatibilityReport(
        realm=realm,
        client_id=client_id,
        issuer=issuer,
        authorization_endpoint=authorization_endpoint,
        token_endpoint=token_endpoint,
        redirect_uri=redirect_uri,
        pkce_posture=pkce_posture,
        passwordless_browser_posture=passwordless_posture,
        direct_mcp_posture=direct_mcp_posture,
        unsupported_detour_detected=unsupported_detour_detected,
        discovery_reachable=discovery_reachable,
        redirect_posture=redirect_posture,
        verdict=verdict,
        failure_classes=failure_classes,
        repair=repair,
    )
