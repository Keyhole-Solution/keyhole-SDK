"""mcp-proxy command — local auth-injecting HTTP/SSE proxy for the Keyhole MCP server.

Architecture
------------
Runs a lightweight HTTP server on ``localhost:<port>`` (default 7878).

VS Code Remote SSH runs the remote extension host on the Linux VM, so
``localhost:7878`` resolves there directly — no manual port forwarding needed.

The proxy:
  - Accepts SSE connections at ``GET /sse`` (no auth required from VS Code)
  - Opens a single authenticated SSE connection to the upstream MCP server,
    injecting ``Authorization: Bearer <token>``
  - Rewrites the upstream ``endpoint`` event URL so VS Code posts back to the
    local proxy instead of the upstream directly
  - Forwards ``POST`` messages upstream with a fresh bearer token
  - Silently refreshes the access token via the stored ``refresh_token`` before
    every POST (calls Keycloak token endpoint only when near-expiry)

Usage
-----
Configure in ``.vscode/mcp.json`` (workspace-level, lives on the Linux VM):

    {
        "servers": {
            "keyhole": {
                "type": "http",
                "url": "http://localhost:7878/sse"
            }
        }
    }

Start the daemon:
    keyhole mcp-proxy              # foreground, Ctrl-C to stop
    keyhole mcp-proxy --port 7878  # explicit port

Keep it running across sessions:
    systemctl --user enable --now keyhole-mcp-proxy.service

Login once with ``keyhole login``.  The proxy handles all token refresh.
"""

from __future__ import annotations

import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import requests as _http

from keyhole_sdk.auth_bootstrap.token_refresh import get_fresh_token
from keyhole_sdk.config import DEFAULT_BASE_URL

_DEFAULT_PORT: int = 7878
_DEFAULT_UPSTREAM_SSE: str = DEFAULT_BASE_URL.rstrip("/") + "/sse"

# Registry: sessionId → upstream absolute message URL (populated on endpoint event)
_upstream_message_urls: dict[str, str] = {}
_urls_lock = threading.Lock()


# ---------------------------------------------------------------------------
# SSE byte-stream parser (handles chunk boundaries correctly)
# ---------------------------------------------------------------------------

def _iter_sse_lines(response: "_http.Response"):
    """Yield raw SSE lines (bytes, without trailing \\n) from a streaming response.

    Preserves blank lines (event separators) as empty ``b""`` items.
    Uses ``iter_content`` so chunk boundaries don't cause missed data.
    """
    buf = b""
    for chunk in response.iter_content(chunk_size=None):
        if chunk:
            buf += chunk
        while b"\n" in buf:
            raw, buf = buf.split(b"\n", 1)
            yield raw.rstrip(b"\r")
    if buf:
        yield buf.rstrip(b"\r")


# ---------------------------------------------------------------------------
# URL rewriting helpers
# ---------------------------------------------------------------------------

def _resolve_upstream_message_url(upstream_sse_url: str, endpoint_data: str) -> str:
    """Resolve endpoint event data to a full upstream message URL."""
    if endpoint_data.startswith("http"):
        return endpoint_data
    parsed = urlparse(upstream_sse_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    return base + "/" + endpoint_data.lstrip("/")


def _local_path_for_endpoint(endpoint_data: str) -> str:
    """Extract the path+query portion of an endpoint URL for rewriting."""
    if not endpoint_data.startswith("http"):
        return endpoint_data  # already a relative path
    parsed = urlparse(endpoint_data)
    path = parsed.path
    if parsed.query:
        path += "?" + parsed.query
    return path


def _extract_session_id(path_or_url: str) -> str | None:
    parsed = urlparse(path_or_url)
    ids = parse_qs(parsed.query).get("sessionId", [])
    return ids[0] if ids else None


# ---------------------------------------------------------------------------
# HTTP request handler
# ---------------------------------------------------------------------------

class _MCPProxyHandler(BaseHTTPRequestHandler):
    """One instance per incoming request.  Class-level config set before serve."""

    upstream_sse_url: str = _DEFAULT_UPSTREAM_SSE
    local_port: int = _DEFAULT_PORT

    def log_message(self, fmt, *args) -> None:  # silence default HTTP log
        pass

    def log_err(self, msg: str) -> None:
        print(f"[keyhole mcp-proxy] {msg}", file=sys.stderr, flush=True)

    # ── CORS preflight ────────────────────────────────────────────────────

    def _cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    # ── Health check ─────────────────────────────────────────────────────

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path == "/sse":
            self._handle_sse()
        elif path in ("/", "/health"):
            self._handle_health()
        else:
            self.send_error(404)

    def _handle_health(self) -> None:
        body = b'{"status":"ok","service":"keyhole-mcp-proxy"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ── SSE proxy ─────────────────────────────────────────────────────────

    def _handle_sse(self) -> None:
        try:
            token = get_fresh_token()
        except Exception as exc:
            self.log_err(f"Token unavailable: {exc}")
            self.send_error(503, "Authentication token unavailable — run 'keyhole login'")
            return

        upstream_url = self.__class__.upstream_sse_url
        if "?" in self.path:
            upstream_url += "?" + self.path.split("?", 1)[1]

        try:
            upstream_resp = _http.get(
                upstream_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "text/event-stream",
                    "Cache-Control": "no-cache",
                },
                stream=True,
                timeout=(15, None),
            )
            upstream_resp.raise_for_status()
        except Exception as exc:
            self.log_err(f"Upstream SSE connect error: {exc}")
            self.send_error(502, f"Upstream connect failed: {exc}")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self._cors_headers()
        self.end_headers()

        current_event: str | None = None

        try:
            for raw in _iter_sse_lines(upstream_resp):
                line = raw.decode("utf-8", "replace")

                if line.startswith("event:"):
                    current_event = line[6:].strip()
                    self.wfile.write(raw + b"\n")

                elif line.startswith("data:") and current_event == "endpoint":
                    data = line[5:].strip()

                    # Store the upstream message URL for POST routing
                    upstream_msg = _resolve_upstream_message_url(upstream_url, data)
                    session_id = _extract_session_id(data)
                    if session_id:
                        with _urls_lock:
                            _upstream_message_urls[session_id] = upstream_msg

                    # Rewrite to local path so VS Code POSTs to us
                    local_path = _local_path_for_endpoint(data)
                    self.wfile.write(f"data: {local_path}\n".encode("utf-8"))
                    current_event = None

                else:
                    if not line:
                        current_event = None  # SSE event separator
                    self.wfile.write(raw + b"\n")

                self.wfile.flush()

        except (BrokenPipeError, ConnectionResetError):
            pass  # VS Code disconnected — normal lifecycle
        except Exception as exc:
            self.log_err(f"SSE stream error: {exc}")

    # ── POST proxy ────────────────────────────────────────────────────────

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""

        # Find upstream URL: session-specific or derived from SSE base
        session_id = _extract_session_id(self.path)
        with _urls_lock:
            upstream_msg_url = _upstream_message_urls.get(session_id) if session_id else None

        if not upstream_msg_url:
            # Fallback: reconstruct from upstream SSE base + incoming path
            parsed = urlparse(self.__class__.upstream_sse_url)
            upstream_msg_url = f"{parsed.scheme}://{parsed.netloc}{self.path}"

        try:
            token = get_fresh_token()
        except Exception as exc:
            self.send_error(503, f"Token error: {exc}")
            return

        try:
            resp = _http.post(
                upstream_msg_url,
                data=body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": self.headers.get("Content-Type", "application/json"),
                },
                timeout=30,
            )
        except Exception as exc:
            self.send_error(502, f"Upstream POST error: {exc}")
            return

        self.send_response(resp.status_code)
        if "Content-Type" in resp.headers:
            self.send_header("Content-Type", resp.headers["Content-Type"])
        self._cors_headers()
        self.end_headers()
        if resp.content:
            self.wfile.write(resp.content)


# ---------------------------------------------------------------------------
# HTTP proxy runner
# ---------------------------------------------------------------------------

def _run_http_proxy(upstream: str, port: int) -> None:
    _MCPProxyHandler.upstream_sse_url = upstream
    _MCPProxyHandler.local_port = port

    server = HTTPServer(("127.0.0.1", port), _MCPProxyHandler)
    print(
        f"[keyhole mcp-proxy] Listening on http://localhost:{port}/sse\n"
        f"[keyhole mcp-proxy] Upstream:   {upstream}\n"
        f"[keyhole mcp-proxy] Token auto-refresh enabled. Ctrl-C to stop.",
        file=sys.stderr,
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[keyhole mcp-proxy] Shutting down.", file=sys.stderr)
        server.server_close()


# ---------------------------------------------------------------------------
# Command entry point (called from cli.py)
# ---------------------------------------------------------------------------

def run_mcp_proxy(upstream: str, port: int) -> None:
    """Run the local MCP auth proxy.

    Verifies that a credentials file exists before binding the server socket.
    Token validity is checked lazily on first SSE connection (and refreshed
    transparently on every subsequent request), so the daemon can start even
    if the current access token is expired — as long as a ``refresh_token``
    is present.  If the refresh token is also expired the first SSE client
    will receive a 503 with instructions to run ``keyhole login``.
    """
    from keyhole_sdk.auth_bootstrap.token_refresh import _cred_path  # type: ignore[attr-defined]

    cred_file = _cred_path()
    if not cred_file.exists():
        print(
            "[keyhole mcp-proxy] No credentials file found.\n"
            "Run 'keyhole login' first.",
            file=sys.stderr,
        )
        sys.exit(1)

    _run_http_proxy(upstream=upstream, port=port)
