"""Unsupported detour detection for browser OIDC flows.

Implements §14.4 of SDK-CLIENT-01-F: Unsupported Detour Detection.

Detects and classifies configurations that route auth through a local
proxy, token-injection shim, or other unsupported path rather than
pointing directly at the Keyhole auth boundary.

INV-SDK-CLIENT-01-F-002 — No proxy confusion.
  Unsupported proxy/token-injection detours must never be presented
  as supported product behavior.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

from keyhole_sdk.auth_browser.models import DirectMcpPosture

# Known local proxy ports and paths — not exhaustive, but covers common shims
_LOCAL_PROXY_PORTS = {8080, 8888, 3128, 3000, 4000, 8000, 8081, 9090, 9000}
_DETOUR_PATH_KEYWORDS = ("proxy", "inject", "relay", "bridge", "forward")
_KEYHOLE_AUTH_HOSTS = (
    "auth.keyholesolution.com",
    "auth.keyhole",
)


def detect_unsupported_detour(auth_server_url: str) -> DirectMcpPosture:
    """Classify the auth server URL as direct Keyhole boundary or detour.

    Returns:
        DirectMcpPosture.DIRECT    — URL points at a known Keyhole auth host
        DirectMcpPosture.DETOUR    — URL looks like a local proxy or injection shim
        DirectMcpPosture.UNKNOWN   — Cannot determine without network introspection

    This check is conservative — it does NOT make network requests.
    It inspects host, port, and path for detour indicators.
    """
    if not auth_server_url:
        return DirectMcpPosture.UNKNOWN

    try:
        parsed = urlparse(auth_server_url)
    except Exception:
        return DirectMcpPosture.UNKNOWN

    host = (parsed.hostname or "").lower()
    port = parsed.port
    path = (parsed.path or "").lower()

    # Explicit Keyhole auth hosts → direct
    for known_host in _KEYHOLE_AUTH_HOSTS:
        if host == known_host or host.endswith("." + known_host):
            return DirectMcpPosture.DIRECT

    # Localhost / loopback with a known proxy port → detour
    if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        if port in _LOCAL_PROXY_PORTS:
            return DirectMcpPosture.DETOUR
        # Any localhost port with a detour keyword in path
        for kw in _DETOUR_PATH_KEYWORDS:
            if kw in path:
                return DirectMcpPosture.DETOUR
        # Generic localhost without a keyword — flag as detour
        # (no legitimate browser OIDC flow uses localhost as the auth host)
        return DirectMcpPosture.DETOUR

    # Path contains detour keyword on any host
    for kw in _DETOUR_PATH_KEYWORDS:
        if kw in path:
            return DirectMcpPosture.DETOUR

    # Non-local, non-Keyhole host — cannot confirm
    return DirectMcpPosture.UNKNOWN


def is_loopback_redirect(redirect_uri: Optional[str]) -> bool:
    """Return True if the redirect URI targets a loopback address.

    A valid browser PKCE callback should be:
      http://127.0.0.1:<port>/<path>
      http://localhost:<port>/<path>

    HTTP (not HTTPS) is required for loopback per RFC 8252 §8.3.
    """
    if not redirect_uri:
        return False
    try:
        parsed = urlparse(redirect_uri)
    except Exception:
        return False

    host = (parsed.hostname or "").lower()
    scheme = (parsed.scheme or "").lower()
    return scheme == "http" and host in ("127.0.0.1", "localhost", "::1")
