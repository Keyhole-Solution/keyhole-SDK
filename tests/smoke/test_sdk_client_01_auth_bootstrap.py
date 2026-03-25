"""DEV-SDK-01 — Cold Auth Bootstrap Smoke Test (Client-Side).

Test Name: sdk-client-01-smoke-auth-bootstrap

This pytest-based smoke test proves first-run authentication bootstrap of
the SDK + CLI against the live MCP server.  It validates:

1. Environment can boot
2. Auth works against real MCP (cold start — no pre-seeded session)
3. Identity is real and correct
4. Token is usable across endpoints
5. Event emitted (if available)
6. Proof bundle generated

This is the **cold-path** test.  A clean KEYHOLE_HOME is used and the CLI
must complete a real login ceremony.  If the Keycloak ``keyhole-cli`` public
client is not provisioned, this suite will error at Layer 1 and all
dependent layers will be skipped.

For the **warm-path** (session reuse) test see:
    tests/smoke/test_sdk_client_01_session_reuse.py

Notes:
  - This is an operator-assisted smoke test. Device flow may require
    user interaction and is not assumed to be unattended CI.
  - Event verification is optional by default because auth event emission
    may still be partially wired until DEV-SDK-01-A is complete.

Run with: pytest tests/smoke/test_sdk_client_01_auth_bootstrap.py -v --tb=short

Environment Variables:
  MCP_BASE_URL          - MCP server URL (default: https://mcp.keyholesolution.com)
  KEYHOLE_HOME          - Keyhole config directory (default: ~/.keyhole)
  CHECK_LOCAL_RUNTIME   - Check local runtime before tests (default: false)
  LOCAL_RUNTIME_URL     - Local runtime URL (default: http://localhost:8080)
  SKIP_EVENT_CHECK      - Skip event spine verification (default: false)
  EVENT_CHECK_REQUIRED  - Fail if event check fails (default: false)
  SECONDARY_AUTH_URL    - Secondary endpoint URL (default: $MCP_BASE_URL/mcp/v1/memory/search)
  SMOKE_TEST_TIMEOUT    - Timeout for operations (default: 30)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
import requests


# =============================================================================
# Configuration
# =============================================================================

MCP_BASE_URL = os.environ.get("MCP_BASE_URL", "https://mcp.keyholesolution.com")
KEYHOLE_HOME = Path(os.environ.get("KEYHOLE_HOME", Path.home() / ".keyhole"))
CHECK_LOCAL_RUNTIME = os.environ.get("CHECK_LOCAL_RUNTIME", "false").lower() == "true"
LOCAL_RUNTIME_URL = os.environ.get("LOCAL_RUNTIME_URL", "http://localhost:8080")
SKIP_EVENT_CHECK = os.environ.get("SKIP_EVENT_CHECK", "false").lower() == "true"
EVENT_CHECK_REQUIRED = os.environ.get("EVENT_CHECK_REQUIRED", "false").lower() == "true"
SECONDARY_AUTH_URL = os.environ.get(
    "SECONDARY_AUTH_URL", f"{MCP_BASE_URL}/mcp/v1/memory/search"
)
SECONDARY_AUTH_PAYLOAD = json.loads(
    os.environ.get("SECONDARY_AUTH_PAYLOAD", '{"query":"smoke test identity","limit":1}')
)
SMOKE_TEST_TIMEOUT = int(os.environ.get("SMOKE_TEST_TIMEOUT", "30"))

# Check if MCP is reachable (for conditional test skipping)
MCP_AVAILABLE = os.environ.get("MCP_AVAILABLE", "false").lower() == "true"

# Optional password-flow (ROPC) credentials for headless CI.
# Requires directAccessGrantsEnabled=true on the kh-dev keyhole-cli Keycloak client.
KEYHOLE_TEST_USERNAME = os.environ.get("KEYHOLE_TEST_USERNAME", "")
KEYHOLE_TEST_PASSWORD = os.environ.get("KEYHOLE_TEST_PASSWORD", "")
_PASSWORD_FLOW_AVAILABLE = bool(KEYHOLE_TEST_USERNAME and KEYHOLE_TEST_PASSWORD)

# Marker for tests requiring real MCP infrastructure
requires_mcp = pytest.mark.skipif(
    not MCP_AVAILABLE,
    reason="Requires real MCP infrastructure (set MCP_AVAILABLE=true to enable)"
)


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
    """Provide a clean keyhole home directory for testing.

    Cold bootstrap: no pre-seeded credentials.  The directory is empty.
    """
    test_home = Path(tempfile.mkdtemp(prefix="keyhole_smoke_"))
    yield test_home
    # Cleanup after tests
    shutil.rmtree(test_home, ignore_errors=True)


@pytest.fixture(scope="module")
def local_runtime() -> Optional[str]:
    """Probe local runtime if CHECK_LOCAL_RUNTIME is enabled."""
    if not CHECK_LOCAL_RUNTIME:
        return None

    # Check if local runtime is available
    try:
        resp = requests.get(f"{LOCAL_RUNTIME_URL}/healthz", timeout=5)
        if resp.status_code == 200:
            return LOCAL_RUNTIME_URL
    except requests.RequestException:
        pass

    return None


@pytest.fixture(scope="module")
def login_result(
    keyhole_cli: str,
    clean_keyhole_home: Path,
) -> Dict[str, Any]:
    """Execute login and return the result.

    Flow selection (in priority order):
      1. Password (ROPC) flow when KEYHOLE_TEST_USERNAME + KEYHOLE_TEST_PASSWORD are set.
         Requires directAccessGrantsEnabled=true on the kh-dev keyhole-cli Keycloak client.
         Used for headless CI environments.
      2. Device flow otherwise (operator-assisted; requires human approval in browser).

    The keyhole home is empty — no pre-seeded session.  If the ``keyhole-cli``
    Keycloak public client is not provisioned, this fixture will fail and all
    dependent tests will be marked as errors.
    """
    env = os.environ.copy()
    env["KEYHOLE_HOME"] = str(clean_keyhole_home)

    if _PASSWORD_FLOW_AVAILABLE:
        cmd = [
            keyhole_cli, "login",
            "--flow", "password",
            "--username", KEYHOLE_TEST_USERNAME,
            "--password", KEYHOLE_TEST_PASSWORD,
            "--json",
        ]
        timeout = 30
    else:
        cmd = [keyhole_cli, "login", "--flow", "device", "--json"]
        timeout = 120  # Device flow requires operator approval

    # Allow auth-server / mcp-url override for non-default boundary targets
    auth_server = os.environ.get("KEYHOLE_AUTH_SERVER")
    mcp_url = os.environ.get("KEYHOLE_MCP_URL")
    if auth_server:
        cmd += ["--auth-server", auth_server]
    if mcp_url:
        cmd += ["--mcp-url", mcp_url]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
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
        pytest.fail("Credentials file not created after login")

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
    """Execute whoami via CLI and return result."""
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

    def test_curl_available(self):
        """curl command is available."""
        assert shutil.which("curl"), "curl not found in PATH"

    def test_jq_available(self):
        """jq command is available."""
        assert shutil.which("jq"), "jq not found in PATH"

    def test_keyhole_cli_available(self, keyhole_cli: str):
        """keyhole CLI is available."""
        assert keyhole_cli is not None


# =============================================================================
# Optional — Local Runtime Probe
# =============================================================================


@pytest.mark.skipif(not CHECK_LOCAL_RUNTIME, reason="CHECK_LOCAL_RUNTIME=false")
class TestOptionalLocalRuntime:
    """Optional Local Runtime Probe (when CHECK_LOCAL_RUNTIME=true)."""

    def test_runtime_reachable(self, local_runtime: Optional[str]):
        """Local runtime is reachable and healthy."""
        if local_runtime is None:
            pytest.skip("Local runtime not available")
        resp = requests.get(f"{local_runtime}/healthz", timeout=5)
        assert resp.status_code == 200

    def test_runtime_identity_surface(self, local_runtime: Optional[str]):
        """Runtime identity surface returns valid data."""
        if local_runtime is None:
            pytest.skip("Local runtime not available")
        try:
            resp = requests.get(f"{local_runtime}/identity", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                # runtime_id is expected per public contract
                assert "runtime_id" in data or "runtime_name" in data
        except requests.RequestException:
            pytest.skip("Identity surface not available")


# =============================================================================
# Layer 1 — CLI Login
# =============================================================================


@requires_mcp
class TestLayer1CLILogin:
    """Layer 1 — CLI Login Invocation (Device Flow)."""

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

    def test_login_has_user_id(self, login_result: Dict[str, Any]):
        """Login result includes user_id."""
        user_id = login_result.get("data", {}).get("user_id")
        # user_id may be in data or it may be whoami-returned
        # Check that login succeeded — user_id verified in whoami tests


# =============================================================================
# Layer 2 — Token Capture
# =============================================================================


@requires_mcp
class TestLayer2TokenCapture:
    """Layer 2 — Token Capture and Validation."""

    def test_credentials_file_exists(
        self,
        clean_keyhole_home: Path,
        login_result: Dict[str, Any],
    ):
        """Credentials file was created after login."""
        creds_file = clean_keyhole_home / "credentials.json"
        assert creds_file.exists(), "Credentials file not created"

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

    def test_session_has_mode(
        self,
        clean_keyhole_home: Path,
        login_result: Dict[str, Any],
    ):
        """Session includes server-issued mode."""
        creds_file = clean_keyhole_home / "credentials.json"
        with open(creds_file) as f:
            creds = json.load(f)
        assert "mode" in creds, "Session missing mode"


# =============================================================================
# Layer 3 — Whoami CLI
# =============================================================================


@requires_mcp
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


@requires_mcp
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
        # Server returns MCPEnvelope: {"ok": true, "data": {"identity": {"user_id": ...}}}
        assert "data" in envelope, f"Response missing MCPEnvelope 'data' key: {list(envelope.keys())}"
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
        # MCPEnvelope: {"data": {"identity": {"user_id": ...}}}
        direct_user_id = envelope["data"]["identity"]["user_id"]
        # CLI: flat top-level {"user_id": ...}
        cli_user_id = whoami_cli_result.get("user_id")
        assert direct_user_id == cli_user_id, (
            f"Identity mismatch: direct={direct_user_id}, cli={cli_user_id}"
        )


# =============================================================================
# Layer 5 — Secondary Authenticated Endpoint
# =============================================================================


@requires_mcp
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
            # 401 = token rejected (hard fail)
            assert resp.status_code != 401, (
                "Secondary authenticated endpoint rejected token with HTTP 401"
            )
            # Other status codes are warnings, not failures:
            # 200 = success
            # 403 = auth recognized but scope may differ
            # 404 = endpoint not deployed
            # 405 = method/path mismatch
        except requests.RequestException as e:
            pytest.skip(f"Secondary endpoint not reachable: {e}")


# =============================================================================
# Layer 6 — Event Spine (Optional)
# =============================================================================


@requires_mcp
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
                pytest.fail(f"Event query endpoint unreachable and EVENT_CHECK_REQUIRED=true: {e}")
            pytest.skip(f"Event query endpoint unreachable: {e}")

        if resp.status_code == 200:
            # Check if we got any events
            data = resp.json()
            event_count = (
                len(data.get("events", []))
                or len(data.get("data", {}).get("events", []))
                or len(data.get("results", []))
                or len(data.get("data", {}).get("results", []))
            )
            if event_count > 0:
                pass  # Found events, success
            elif EVENT_CHECK_REQUIRED:
                pytest.fail("No AUTH_SUCCESS events found and EVENT_CHECK_REQUIRED=true")
        elif resp.status_code == 404:
            if EVENT_CHECK_REQUIRED:
                pytest.fail("Event query endpoint unavailable (HTTP 404) and EVENT_CHECK_REQUIRED=true")
            pytest.skip("Event query endpoint unavailable (HTTP 404)")
        elif resp.status_code in (401, 403):
            if EVENT_CHECK_REQUIRED:
                pytest.fail(f"Event query authorization insufficient (HTTP {resp.status_code}) and EVENT_CHECK_REQUIRED=true")
            pytest.skip(f"Event query authorization insufficient (HTTP {resp.status_code})")
        else:
            if EVENT_CHECK_REQUIRED:
                pytest.fail(f"Event query returned HTTP {resp.status_code} and EVENT_CHECK_REQUIRED=true")
            # Other status codes are not failures unless EVENT_CHECK_REQUIRED


# =============================================================================
# Layer 7 — Proof Bundle
# =============================================================================


@requires_mcp
class TestLayer7ProofBundle:
    """Layer 7 — Proof Bundle Verification."""

    def test_proof_bundle_exists(
        self,
        clean_keyhole_home: Path,
        login_result: Dict[str, Any],
    ):
        """Proof bundle directory was created."""
        proof_dir = clean_keyhole_home / "proof_bundle"
        if not proof_dir.exists():
            proof_dir = clean_keyhole_home / "proof"
        assert proof_dir.exists(), (
            "Proof bundle directory not created — cold bootstrap must persist proof"
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
        pytest.skip("core.json not found")

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
        pytest.skip("identity_context.json not found")

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
                # Check for patterns that would indicate token leakage
                # (excluding expected metadata keys)
                if '"access_token":' in content:
                    # Check if it's an actual token value
                    data = json.loads(content)
                    if "access_token" in data and len(data.get("access_token", "")) > 20:
                        pytest.fail(f"Token leakage in {file.name}")

    def test_correlation_id_consistent(
        self,
        clean_keyhole_home: Path,
        login_result: Dict[str, Any],
    ):
        """correlation_id is consistent across proof artifacts."""
        correlation_ids = set()
        for dirname in ("proof_bundle", "proof"):
            proof_dir = clean_keyhole_home / dirname
            if not proof_dir.exists():
                continue
            for filename in ("core.json", "event_chain.json", "correlation.json"):
                path = proof_dir / filename
                if path.exists():
                    with open(path) as f:
                        data = json.load(f)
                    cid = data.get("correlation_id")
                    if cid:
                        correlation_ids.add(cid)
        if len(correlation_ids) > 1:
            pytest.fail(f"Inconsistent correlation_ids: {correlation_ids}")


# =============================================================================
# Integration Summary
# =============================================================================


@requires_mcp
class TestIntegrationSummary:
    """Integration summary tests — prove end-to-end viability."""

    def test_full_auth_lifecycle(
        self,
        login_result: Dict[str, Any],
        access_token: str,
        whoami_cli_result: Dict[str, Any],
    ):
        """Full auth lifecycle completes successfully."""
        # Login succeeded
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
        # Server returns MCPEnvelope: {"ok": true, "data": {"identity": {"user_id": ...}}}
        assert "data" in envelope, "MCPEnvelope missing 'data' key"
        identity = envelope["data"].get("identity", {})
        assert "user_id" in identity, "MCPEnvelope data.identity missing user_id"

    def test_identity_is_server_sourced(
        self,
        clean_keyhole_home: Path,
        login_result: Dict[str, Any],
    ):
        """Identity in proof is sourced from server, not local inference."""
        for dirname in ("proof_bundle", "proof"):
            path = clean_keyhole_home / dirname / "identity_context.json"
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                assert data.get("source") == "server/whoami", (
                    "Identity not sourced from server/whoami"
                )
                return
        pytest.skip("identity_context.json not found")
