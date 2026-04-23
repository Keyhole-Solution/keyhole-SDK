"""PKCE authentication flow — browser-based OIDC login.

Implements §6.2 of SDK-CLIENT-01: PKCE Flow Support.

Flow:
  1. Generate code_verifier + code_challenge (S256)
  2. Build authorization URL with PKCE challenge
  3. Open browser or display URL
  4. Start local callback server to receive auth code
  5. Exchange auth code + code_verifier for tokens
  6. Return TokenResponse
"""

from __future__ import annotations

import atexit
import hashlib
import os
import secrets
import signal
import socket
import base64
import subprocess
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs

import requests

from keyhole_sdk.auth_bootstrap.errors import (
    BrowserLaunchError,
    ExpiredChallengeError,
    InvalidTokenError,
    NetworkError,
)
from keyhole_sdk.auth_bootstrap.models import PKCEChallenge, TokenResponse


_CALLBACK_PORT = int(os.environ.get("KEYHOLE_PKCE_PORT", "9876"))
_CALLBACK_PATH = "/callback"


def _generate_code_verifier(length: int = 64) -> str:
    """Generate a cryptographically random PKCE code verifier."""
    return secrets.token_urlsafe(length)[:128]


def _generate_code_challenge(verifier: str) -> str:
    """Compute S256 code challenge from the verifier."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class _CallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for the local PKCE callback server."""

    auth_code: Optional[str] = None
    error: Optional[str] = None
    state: Optional[str] = None

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == _CALLBACK_PATH:
            _CallbackHandler.auth_code = params.get("code", [None])[0]
            _CallbackHandler.error = params.get("error", [None])[0]
            _CallbackHandler.state = params.get("state", [None])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            if _CallbackHandler.auth_code:
                body = (
                    "<html><body><h2>Login successful!</h2>"
                    "<p>You can close this window and return to the terminal.</p>"
                    "</body></html>"
                )
            else:
                body = (
                    "<html><body><h2>Login failed</h2>"
                    f"<p>Error: {_CallbackHandler.error or 'unknown'}</p>"
                    "</body></html>"
                )
            self.wfile.write(body.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """Suppress default HTTP server logging."""


class _ReuseAddrHTTPServer(HTTPServer):
    """HTTPServer with SO_REUSEADDR to avoid 'Address already in use' after killed processes."""

    allow_reuse_address = True


def _kill_stale_listener(port: int) -> None:
    """Kill any stale process listening on *port*.

    Uses a quick socket probe first (cheap). If the port is occupied, falls
    back to ``lsof`` / ``ss`` to identify the PID and sends SIGTERM+SIGKILL.
    This makes ``keyhole login`` idempotent — a previously-crashed or
    suspended login process will not block a new attempt.
    """
    # Fast probe: can we bind?
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", port))
        # Port is free — nothing to do.
        return
    except OSError:
        pass  # Port occupied; continue to kill
    finally:
        probe.close()

    # Find the PID owning the port.  Try lsof first, then ss.
    pid = _find_pid_on_port(port)
    if pid is None or pid == os.getpid():
        return

    # Kill it: SIGTERM first, SIGKILL as fallback.
    try:
        os.kill(pid, signal.SIGTERM)
        # Give it a moment to release the socket.
        for _ in range(10):
            time.sleep(0.1)
            try:
                os.kill(pid, 0)  # probe — raises if dead
            except OSError:
                return
        # Still alive — hard-kill.
        os.kill(pid, signal.SIGKILL)
        time.sleep(0.2)
    except OSError:
        pass  # already dead or not ours


def _find_pid_on_port(port: int) -> Optional[int]:
    """Return the PID of the process listening on *port*, or None."""
    # Try lsof (available on macOS and most Linux)
    try:
        out = subprocess.check_output(
            ["lsof", "-ti", f":{port}"],
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
        for line in out.decode().strip().splitlines():
            line = line.strip()
            if line.isdigit():
                return int(line)
    except (FileNotFoundError, subprocess.SubprocessError):
        pass

    # Fall back to ss (Linux)
    try:
        out = subprocess.check_output(
            ["ss", "-tlnp", f"sport = :{port}"],
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
        # ss output: lines contain pid=NNN
        import re
        for m in re.finditer(r"pid=(\d+)", out.decode()):
            return int(m.group(1))
    except (FileNotFoundError, subprocess.SubprocessError):
        pass

    return None


class PKCEFlow:
    """PKCE (Proof Key for Code Exchange) authentication flow.

    This is the primary interactive browser-based login path.
    """

    def __init__(
        self,
        auth_server_url: str,
        client_id: str,
        *,
        redirect_uri: str = f"http://localhost:{_CALLBACK_PORT}{_CALLBACK_PATH}",
        scope: str = "openid profile email",
        timeout: int = 300,
    ) -> None:
        self._auth_server_url = auth_server_url.rstrip("/")
        self._client_id = client_id
        self._redirect_uri = redirect_uri
        self._scope = scope
        self._timeout = timeout

    def generate_challenge(self) -> PKCEChallenge:
        """Generate a new PKCE challenge with cryptographic state."""
        verifier = _generate_code_verifier()
        challenge = _generate_code_challenge(verifier)
        state = secrets.token_urlsafe(32)

        params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "scope": self._scope,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"{self._auth_server_url}/protocol/openid-connect/auth?{urlencode(params)}"

        return PKCEChallenge(
            code_verifier=verifier,
            code_challenge=challenge,
            state=state,
            authorization_url=auth_url,
            redirect_uri=self._redirect_uri,
        )

    def open_browser(self, url: str) -> bool:
        """Attempt to open the authorization URL in the default browser."""
        try:
            return webbrowser.open(url)
        except Exception:
            return False

    def wait_for_callback(self, expected_state: str) -> str:
        """Start local server and wait for the auth callback.

        Kills any stale listener on the callback port first, making the
        flow idempotent even after crashed or suspended prior runs.

        Returns the authorization code on success.
        Raises on timeout or error.
        """
        # Kill any zombie from a prior login attempt
        _kill_stale_listener(_CALLBACK_PORT)

        # Reset class state
        _CallbackHandler.auth_code = None
        _CallbackHandler.error = None
        _CallbackHandler.state = None

        server = _ReuseAddrHTTPServer(("127.0.0.1", _CALLBACK_PORT), _CallbackHandler)
        server.timeout = 1

        # Ensure the socket is released on process exit / signals
        def _cleanup() -> None:
            try:
                server.server_close()
            except Exception:
                pass

        atexit.register(_cleanup)

        thread = Thread(target=self._serve_until_callback, args=(server,), daemon=True)
        thread.start()

        try:
            deadline = time.monotonic() + self._timeout
            while time.monotonic() < deadline:
                if _CallbackHandler.auth_code or _CallbackHandler.error:
                    break
                time.sleep(0.5)
        finally:
            server.shutdown()
            thread.join(timeout=5)
            _cleanup()
            atexit.unregister(_cleanup)

        if _CallbackHandler.error:
            raise InvalidTokenError(
                f"Auth server returned error: {_CallbackHandler.error}"
            )

        if not _CallbackHandler.auth_code:
            raise ExpiredChallengeError()

        if _CallbackHandler.state != expected_state:
            raise InvalidTokenError(
                "State parameter mismatch — possible CSRF attack."
            )

        return _CallbackHandler.auth_code

    def exchange_code(self, code: str, code_verifier: str) -> TokenResponse:
        """Exchange the authorization code for tokens.

        Posts to the token endpoint with the PKCE code_verifier.
        """
        token_url = f"{self._auth_server_url}/token"
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._redirect_uri,
            "client_id": self._client_id,
            "code_verifier": code_verifier,
        }

        try:
            resp = requests.post(token_url, data=payload, timeout=30)
        except requests.ConnectionError as exc:
            raise NetworkError(f"Cannot reach token endpoint: {exc}") from exc
        except requests.Timeout as exc:
            raise NetworkError(f"Token endpoint timed out: {exc}") from exc

        if resp.status_code != 200:
            error_detail = resp.text[:500] if resp.text else "no detail"
            raise InvalidTokenError(
                f"Token exchange failed (HTTP {resp.status_code}): {error_detail}"
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise InvalidTokenError("Token response is not valid JSON") from exc

        return TokenResponse.model_validate(data)

    @staticmethod
    def _serve_until_callback(server: HTTPServer) -> None:
        """Serve requests until a callback is received."""
        while _CallbackHandler.auth_code is None and _CallbackHandler.error is None:
            server.handle_request()
