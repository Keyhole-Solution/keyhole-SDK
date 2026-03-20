"""DEV-SDK-01 — Session Reuse Smoke Test (Client-Side).

Test Name: sdk-client-01-smoke-session-reuse

This pytest-based smoke test proves **warm-path session reuse** of the
SDK + CLI against the live MCP server.  It validates:

1. Environment can boot
2. Pre-seeded credential is accepted (session reuse — no device flow)
3. Identity is real and correct
4. Token is usable across endpoints
5. Event spine accessible (if available)
6. Proof bundle persisted with auth_path=session_reuse

This is the **warm-path** test.  A pre-seeded token (e.g. a service
account JWT) is injected into KEYHOLE_HOME before invoking the CLI.  The
CLI detects valid credentials and reuses them rather than launching an
interactive device flow.

For the **cold-path** (device flow bootstrap) test see:
    tests/smoke/test_sdk_client_01_auth_bootstrap.py

Requirements:
  - PRE_SEED_TOKEN_FILE must be set to the path of a valid bearer token
  - KEYHOLE_AUTH_SERVER and KEYHOLE_MCP_URL should be set for boundary
    targeting (defaults: https://auth.keyholesolution.com/realms/keyhole-mcp
    and https://mcp.keyholesolution.com)

Run with:
  PRE_SEED_TOKEN_FILE=/path/to/token.jwt \
  MCP_AVAILABLE=true \
  pytest tests/smoke/test_sdk_client_01_session_reuse.py -v --tb=short
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
import requests


# =============================================================================
# Configuration
# =============================================================================

PRE_SEED_TOKEN_FILE = os.environ.get("PRE_SEED_TOKEN_FILE", "")
MCP_BASE_URL = os.environ.get("MCP_BASE_URL", "https://mcp.keyholesolution.com")
KEYHOLE_AUTH_SERVER = os.environ.get(
    "KEYHOLE_AUTH_SERVER",
    "https://auth.keyholesolution.com/realms/keyhole-mcp",
)
KEYHOLE_MCP_URL = os.environ.get("KEYHOLE_MCP_URL", MCP_BASE_URL)
SKIP_EVENT_CHECK = os.environ.get("SKIP_EVENT_CHECK", "false").lower() == "true"
EVENT_CHECK_REQUIRED = os.environ.get("EVENT_CHECK_REQUIRED", "false").lower() == "true"
SECONDARY_AUTH_URL = os.environ.get(
    "SECONDARY_AUTH_URL", f"{MCP_BASE_URL}/mcp/v1/memory/search"
)
SECONDARY_AUTH_PAYLOAD = json.loads(
    os.environ.get("SECONDARY_AUTH_PAYLOAD", '{"query":"smoke test identity","limit":1}')
)
SMOKE_TEST_TIMEOUT = int(os.environ.get("SMOKE_TEST_TIMEOUT", "30"))

MCP_AVAILABLE = os.environ.get("MCP_AVAILABLE", "false").lower() == "true"

# Gate the entire module on PRE_SEED_TOKEN_FILE
pytestmark = [
    pytest.mark.skipif(
        not PRE_SEED_TOKEN_FILE or not Path(PRE_SEED_TOKEN_FILE).exists(),
        reason="PRE_SEED_TOKEN_FILE not set or file missing — session reuse test requires a pre-seeded token",
    ),
    pytest.mark.skipif(
        not MCP_AVAILABLE,
        reason="Requires real MCP infrastructure (set MCP_AVAILABLE=true)",
    ),
]


# =============================================================================
# Helpers
# =============================================================================


def _write_credentials(home: Path, token: str) -> None:
    """Write a pre-seeded credentials.json in AuthSession format."""
    creds = {
        "access_token": token,
        "token_type": "Bearer",
        "refresh_token": None,
        "expires_at": None,
        "scope": None,
        "flow_type": "device",
        "mode": "real",
        "realm": "keyhole-mcp",
        "auth_server_url": KEYHOLE_AUTH_SERVER,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_verified_at": None,
    }
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    creds_file = home / "credentials.json"
    creds_file.write_text(json.dumps(creds, indent=2))
    os.chmod(creds_file, stat.S_IRUSR | stat.S_IWUSR)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def keyhole_cli() -> str:
    """Ensure keyhole CLI is available."""
    path = shutil.which("keyhole")
    if not path:
        pytest.skip("keyhole CLI not found in PATH")
    return path


@pytest.fixture(scope="module")
def clean_keyhole_home() -> Path:
    """Provide a keyhole home directory pre-seeded with credentials.

    Warm path: the token from PRE_SEED_TOKEN_FILE is injected into
    credentials.json so the CLI detects an existing session.
    """
    test_home = Path(tempfile.mkdtemp(prefix="keyhole_reuse_"))

    token = Path(PRE_SEED_TOKEN_FILE).read_text().strip()
    _write_credentials(test_home, token)

    yield test_home
    shutil.rmtree(test_home, ignore_errors=True)


@pytest.fixture(scope="module")
def login_result(
    keyhole_cli: str,
    clean_keyhole_home: Path,
) -> Dict[str, Any]:
    """Execute login with pre-seeded credentials (session reuse path).

    The CLI should detect existing credentials and reuse them rather than
    launching an interactive device flow.
    """
    env = os.environ.copy()
    env["KEYHOLE_HOME"] = str(clean_keyhole_home)

    cmd = [
        keyhole_cli, "login", "--flow", "device", "--json",
        "--auth-server", KEYHOLE_AUTH_SERVER,
        "--mcp-url", KEYHOLE_MCP_URL,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )

    if result.returncode != 0:
        pytest.fail(f"Login failed: {result.stderr or result.stdout}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"Login output is not valid JSON: {result.stdout}")


@pytest.fixture(scope="module")
def access_token(
    clean_keyhole_home: Path,
    login_result: Dict[str, Any],
) -> str:
    """Extract access token from credential store."""
    creds_file = clean_keyhole_home / "credentials.json"

    if not creds_file.exists():
        pytest.fail("Credentials file not present after login")

    with open(creds_file) as f:
        creds = json.load(f)

    token = creds.get("access_token")
    if not token:
        pytest.fail("No access_token in credentials file")

    return token


@pytest.fixture(scope="module")
def whoami_cli_result(
    keyhole_cli: str,
    clean_keyhole_home: Path,
    login_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute whoami via CLI and return result (flat JSON)."""
    env = os.environ.copy()
    env["KEYHOLE_HOME"] = str(clean_keyhole_home)

    result = subprocess.run(
        [keyhole_cli, "whoami", "--json"],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )

    if result.returncode != 0:
        pytest.fail(f"Whoami failed: {result.stderr or result.stdout}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"Whoami output is not valid JSON: {result.stdout}")


# =============================================================================
# Layer 0 — Prerequisites
# =============================================================================


class TestLayer0Prerequisites:
    """Layer 0 — Prerequisites Check."""

    def test_keyhole_cli_available(self, keyhole_cli: str):
        """keyhole CLI is available."""
        assert keyhole_cli is not None

    def test_token_file_readable(self):
        """Pre-seeded token file is readable."""
        token_path = Path(PRE_SEED_TOKEN_FILE)
        assert token_path.exists(), f"Token file missing: {PRE_SEED_TOKEN_FILE}"
        token = token_path.read_text().strip()
        assert len(token) > 20, "Token appears too short"

    def test_credentials_pre_seeded(self, clean_keyhole_home: Path):
        """Credentials were written to the test KEYHOLE_HOME."""
        creds_file = clean_keyhole_home / "credentials.json"
        assert creds_file.exists(), "Pre-seeded credentials.json missing"


# =============================================================================
# Layer 1 — CLI Login (Session Reuse)
# =============================================================================


class TestLayer1CLILogin:
    """Layer 1 — CLI Login via Session Reuse."""

    def test_login_success(self, login_result: Dict[str, Any]):
        """Login command reports success=true."""
        assert login_result.get("success") is True, (
            f"Login failed: {login_result.get('summary')}"
        )

    def test_login_has_mode(self, login_result: Dict[str, Any]):
        """Login result includes mode (flat CLI JSON)."""
        mode = login_result.get("mode")
        assert mode is not None, (
            f"Login result missing top-level 'mode' — CLI must flatten data. "
            f"Got keys: {list(login_result.keys())}"
        )
        assert mode in ("shadow", "real", "local"), f"Unexpected mode: {mode}"

    def test_login_has_auth_path(self, login_result: Dict[str, Any]):
        """Login result includes auth_path indicating reuse."""
        auth_path = login_result.get("auth_path")
        assert auth_path is not None, (
            f"Login result missing 'auth_path'. Got keys: {list(login_result.keys())}"
        )
        assert auth_path == "session_reuse", (
            f"Expected auth_path='session_reuse', got '{auth_path}'"
        )


# =============================================================================
# Layer 2 — Token Capture
# =============================================================================


class TestLayer2TokenCapture:
    """Layer 2 — Token Capture and Validation."""

    def test_credentials_file_exists(
        self,
        clean_keyhole_home: Path,
        login_result: Dict[str, Any],
    ):
        """Credentials file persists after login."""
        creds_file = clean_keyhole_home / "credentials.json"
        assert creds_file.exists(), "Credentials file not found"

    def test_credentials_file_permissions(
        self,
        clean_keyhole_home: Path,
        login_result: Dict[str, Any],
    ):
        """Credentials file has secure permissions (600)."""
        creds_file = clean_keyhole_home / "credentials.json"
        if creds_file.exists():
            perms = oct(creds_file.stat().st_mode)[-3:]
            assert perms == "600", f"Insecure permissions: {perms}"

    def test_token_exists(self, access_token: str):
        """Access token was extracted from credentials."""
        assert access_token is not None
        assert len(access_token) > 20, "Token appears malformed"


# =============================================================================
# Layer 3 — Whoami CLI
# =============================================================================


class TestLayer3WhoamiCLI:
    """Layer 3 — Whoami Verification via CLI."""

    def test_whoami_success(self, whoami_cli_result: Dict[str, Any]):
        """Whoami command reports success=true."""
        assert whoami_cli_result.get("success") is True

    def test_whoami_has_user_id(self, whoami_cli_result: Dict[str, Any]):
        """Whoami response includes user_id (flat CLI JSON)."""
        user_id = whoami_cli_result.get("user_id")
        assert user_id is not None, (
            f"Whoami missing top-level 'user_id' — CLI must flatten data. "
            f"Got keys: {list(whoami_cli_result.keys())}"
        )
        assert len(user_id) > 0, "user_id is empty"

    def test_whoami_has_mode(self, whoami_cli_result: Dict[str, Any]):
        """Whoami response includes mode (flat CLI JSON)."""
        mode = whoami_cli_result.get("mode")
        assert mode is not None, (
            f"Whoami missing top-level 'mode' — CLI must flatten data. "
            f"Got keys: {list(whoami_cli_result.keys())}"
        )


# =============================================================================
# Layer 4 — Direct MCP Call
# =============================================================================


class TestLayer4DirectMCPCall:
    """Layer 4 — Direct MCP /whoami Call."""

    def test_direct_whoami_success(self, access_token: str):
        """Direct MCP /whoami returns HTTP 200."""
        resp = requests.get(
            f"{MCP_BASE_URL}/mcp/v1/whoami",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        assert resp.status_code == 200, f"Got HTTP {resp.status_code}"

    def test_direct_whoami_has_user_id(self, access_token: str):
        """Direct MCP /whoami returns user_id inside MCPEnvelope."""
        resp = requests.get(
            f"{MCP_BASE_URL}/mcp/v1/whoami",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        envelope = resp.json()
        assert "data" in envelope, (
            f"Response missing MCPEnvelope 'data' key: {list(envelope.keys())}"
        )
        identity = envelope["data"].get("identity", {})
        assert "user_id" in identity, (
            f"MCPEnvelope data.identity missing user_id. "
            f"Got data keys: {list(envelope['data'].keys())}"
        )

    def test_identity_matches_cli(
        self,
        access_token: str,
        whoami_cli_result: Dict[str, Any],
    ):
        """Direct whoami user_id matches CLI whoami user_id."""
        resp = requests.get(
            f"{MCP_BASE_URL}/mcp/v1/whoami",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        envelope = resp.json()
        direct_user_id = envelope["data"]["identity"]["user_id"]
        cli_user_id = whoami_cli_result.get("user_id")
        assert direct_user_id == cli_user_id, (
            f"Identity mismatch: direct={direct_user_id}, cli={cli_user_id}"
        )


# =============================================================================
# Layer 5 — Secondary Authenticated Endpoint
# =============================================================================


class TestLayer5SecondaryEndpoint:
    """Layer 5 — Secondary Authenticated Endpoint."""

    def test_secondary_endpoint(self, access_token: str):
        """Token works on secondary authenticated endpoint."""
        try:
            resp = requests.post(
                SECONDARY_AUTH_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=SECONDARY_AUTH_PAYLOAD,
                timeout=10,
            )
            assert resp.status_code != 401, (
                "Secondary authenticated endpoint rejected token with HTTP 401"
            )
        except requests.RequestException as e:
            pytest.skip(f"Secondary endpoint not reachable: {e}")


# =============================================================================
# Layer 6 — Event Spine (Optional)
# =============================================================================


@pytest.mark.skipif(SKIP_EVENT_CHECK, reason="SKIP_EVENT_CHECK=true")
class TestLayer6EventSpine:
    """Layer 6 — Event Spine Verification (Optional)."""

    def test_event_query_endpoint_accessible(self, access_token: str):
        """Event query endpoint is accessible."""
        try:
            resp = requests.post(
                f"{MCP_BASE_URL}/mcp/v1/events/query",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"types": ["type:AUTH_SUCCESS"], "limit": 5},
                timeout=10,
            )
        except requests.RequestException as e:
            if EVENT_CHECK_REQUIRED:
                pytest.fail(f"Event query endpoint unreachable: {e}")
            pytest.skip(f"Event query endpoint unreachable: {e}")

        if resp.status_code == 200:
            data = resp.json()
            event_count = (
                len(data.get("events", []))
                or len(data.get("data", {}).get("events", []))
                or len(data.get("results", []))
                or len(data.get("data", {}).get("results", []))
            )
            if event_count == 0 and EVENT_CHECK_REQUIRED:
                pytest.fail("No AUTH_SUCCESS events found")
        elif resp.status_code == 404:
            if EVENT_CHECK_REQUIRED:
                pytest.fail("Event query endpoint unavailable (HTTP 404)")
            pytest.skip("Event query endpoint unavailable (HTTP 404)")
        elif resp.status_code in (401, 403):
            if EVENT_CHECK_REQUIRED:
                pytest.fail(f"Event query authorization insufficient (HTTP {resp.status_code})")
            pytest.skip(f"Event query authorization insufficient (HTTP {resp.status_code})")
        else:
            if EVENT_CHECK_REQUIRED:
                pytest.fail(f"Event query returned HTTP {resp.status_code}")


# =============================================================================
# Layer 7 — Proof Bundle
# =============================================================================


class TestLayer7ProofBundle:
    """Layer 7 — Proof Bundle Verification (Session Reuse Path)."""

    def test_proof_bundle_exists(
        self,
        clean_keyhole_home: Path,
        login_result: Dict[str, Any],
    ):
        """Proof bundle directory was created on session reuse."""
        proof_dir = clean_keyhole_home / "proof_bundle"
        if not proof_dir.exists():
            proof_dir = clean_keyhole_home / "proof"
        assert proof_dir.exists(), (
            "Proof bundle directory not created — session reuse must persist proof"
        )

    def test_core_json_exists(
        self,
        clean_keyhole_home: Path,
        login_result: Dict[str, Any],
    ):
        """core.json proof artifact exists."""
        for dirname in ("proof_bundle", "proof"):
            path = clean_keyhole_home / dirname / "core.json"
            if path.exists():
                return
        pytest.fail("core.json not found in proof bundle")

    def test_event_chain_exists(
        self,
        clean_keyhole_home: Path,
        login_result: Dict[str, Any],
    ):
        """event_chain.json proof artifact exists."""
        for dirname in ("proof_bundle", "proof"):
            path = clean_keyhole_home / dirname / "event_chain.json"
            if path.exists():
                return
        pytest.fail("event_chain.json not found in proof bundle")

    def test_identity_context_exists(
        self,
        clean_keyhole_home: Path,
        login_result: Dict[str, Any],
    ):
        """identity_context.json proof artifact exists."""
        for dirname in ("proof_bundle", "proof"):
            path = clean_keyhole_home / dirname / "identity_context.json"
            if path.exists():
                return
        pytest.fail("identity_context.json not found in proof bundle")

    def test_verification_result_exists(
        self,
        clean_keyhole_home: Path,
        login_result: Dict[str, Any],
    ):
        """verification_result.json proof artifact exists."""
        for dirname in ("proof_bundle", "proof"):
            path = clean_keyhole_home / dirname / "verification_result.json"
            if path.exists():
                return
        pytest.fail("verification_result.json not found in proof bundle")

    def test_core_json_proof_type(
        self,
        clean_keyhole_home: Path,
        login_result: Dict[str, Any],
    ):
        """core.json has proof_type='auth_bootstrap'."""
        for dirname in ("proof_bundle", "proof"):
            path = clean_keyhole_home / dirname / "core.json"
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                assert data.get("proof_type") == "auth_bootstrap"
                return
        pytest.fail("core.json not found")

    def test_identity_context_source(
        self,
        clean_keyhole_home: Path,
        login_result: Dict[str, Any],
    ):
        """identity_context.json source is 'server/whoami'."""
        for dirname in ("proof_bundle", "proof"):
            path = clean_keyhole_home / dirname / "identity_context.json"
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                source = data.get("source")
                assert source == "server/whoami", f"Unexpected source: {source}"
                return
        pytest.fail("identity_context.json not found")

    def test_no_secret_leakage(
        self,
        clean_keyhole_home: Path,
        login_result: Dict[str, Any],
    ):
        """Proof bundle does not contain access tokens."""
        for dirname in ("proof_bundle", "proof"):
            proof_dir = clean_keyhole_home / dirname
            if not proof_dir.exists():
                continue
            for file in proof_dir.rglob("*.json"):
                content = file.read_text()
                if '"access_token":' in content:
                    data = json.loads(content)
                    if "access_token" in data and len(data.get("access_token", "")) > 20:
                        pytest.fail(f"Token leakage in {file.name}")


# =============================================================================
# Integration Summary
# =============================================================================


class TestIntegrationSummary:
    """Integration summary — prove session reuse end-to-end viability."""

    def test_full_session_reuse_lifecycle(
        self,
        login_result: Dict[str, Any],
        access_token: str,
        whoami_cli_result: Dict[str, Any],
    ):
        """Full session reuse lifecycle completes successfully."""
        # Login succeeded via session reuse
        assert login_result.get("success") is True

        # Token was issued
        assert access_token is not None
        assert len(access_token) > 20

        # Identity is verifiable (flat CLI JSON)
        assert whoami_cli_result.get("success") is True
        assert whoami_cli_result.get("user_id") is not None, (
            "Whoami missing top-level user_id"
        )

    def test_token_works_on_mcp(self, access_token: str):
        """Token can successfully authenticate to MCP server."""
        resp = requests.get(
            f"{MCP_BASE_URL}/mcp/v1/whoami",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        assert resp.status_code == 200
        envelope = resp.json()
        assert "data" in envelope, "MCPEnvelope missing 'data' key"
        identity = envelope["data"].get("identity", {})
        assert "user_id" in identity, "MCPEnvelope data.identity missing user_id"
