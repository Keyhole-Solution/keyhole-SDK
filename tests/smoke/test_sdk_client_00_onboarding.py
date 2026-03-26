"""SDK-CLIENT-00 Smoke Test — Identity Creation & Verification (Client).

Live smoke test for the registration, verification, and status inspection
flow exposed by SDK-CLIENT-00.  Exercises the CLI surface end-to-end against
the governed boundary.

Required environment variables
--------------------------------
ONBOARDING_AVAILABLE=true   Enable these smoke tests (gate).
MCP_BASE_URL                Override MCP server URL
                              (default: https://mcp.keyholesolution.com).
KEYHOLE_MCP_URL             Passed to the CLI for --mcp-url resolution.
                              Auto-derived from MCP_BASE_URL when not set.
SMOKE_TEST_TIMEOUT          Per-subprocess timeout in seconds (default: 30).

Layer ordering
--------------
L0  Prerequisites — CLI available, server reachable
L1  Register      — new kh-dev identity, explicit origin + purpose
L2  Pre-verify status — confirm registered_pending_verification
L3  Verify        — extract dev token from hint, complete verification
L4  Post-verify status — confirm verified_active
L5  Handoff       — next_steps points to keyhole login
L6  Proof bundle  — proof files exist, no secret leakage
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
import requests

# =============================================================================
# Environment configuration
# =============================================================================

ONBOARDING_AVAILABLE: bool = os.environ.get("ONBOARDING_AVAILABLE", "").lower() in (
    "true",
    "1",
    "yes",
)
MCP_BASE_URL: str = os.environ.get("MCP_BASE_URL", "https://mcp.keyholesolution.com")
SMOKE_TEST_TIMEOUT: int = int(os.environ.get("SMOKE_TEST_TIMEOUT", "30"))

# CLI env for mcp_url — falls through to keyhole's KEYHOLE_MCP_URL envvar
_KEYHOLE_MCP_URL: str = os.environ.get("KEYHOLE_MCP_URL", MCP_BASE_URL)

# =============================================================================
# Markers
# =============================================================================

requires_onboarding = pytest.mark.skipif(
    not ONBOARDING_AVAILABLE,
    reason=(
        "ONBOARDING_AVAILABLE is not set to 'true'. "
        "Set ONBOARDING_AVAILABLE=true to run SDK-CLIENT-00 smoke tests."
    ),
)

# =============================================================================
# Session-scoped fixtures
# =============================================================================

# Unique suffix for this smoke-test run (avoids duplicate-user conflicts)
_RUN_UID: str = str(uuid.uuid4())[:8]


@pytest.fixture(scope="session")
def keyhole_cli() -> str:
    """Return path to the keyhole CLI binary or skip if unavailable."""
    cli = shutil.which("keyhole")
    if cli is None:
        pytest.skip("keyhole CLI not found in PATH — install the CLI first")
    return cli


@pytest.fixture(scope="session")
def smoke_keyhole_home(tmp_path_factory) -> Path:
    """Isolated KEYHOLE_HOME for this smoke run (proof bundle lands here)."""
    return tmp_path_factory.mktemp("keyhole_home_sdk00")


def _run_cli(
    keyhole_cli: str,
    args: list[str],
    *,
    keyhole_home: Path,
    timeout: int = SMOKE_TEST_TIMEOUT,
) -> Dict[str, Any]:
    """Run a keyhole CLI command with ``--json``, return parsed output.

    Raises ``pytest.fail`` on non-zero exit code or invalid JSON.
    """
    env = {**os.environ, "KEYHOLE_HOME": str(keyhole_home), "KEYHOLE_MCP_URL": _KEYHOLE_MCP_URL}
    result = subprocess.run(
        [keyhole_cli, *args, "--json"],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    combined = result.stdout + result.stderr
    if not result.stdout.strip():
        pytest.fail(
            f"CLI command produced no stdout (exit={result.returncode}). "
            f"stderr: {result.stderr[:500]}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail(
            f"CLI output is not valid JSON (exit={result.returncode}). "
            f"stdout: {result.stdout[:500]}"
        )


@pytest.fixture(scope="session")
def smoke_register_result(
    keyhole_cli: str,
    smoke_keyhole_home: Path,
) -> Dict[str, Any]:
    """Register a new kh-dev test identity.  Session-scoped — created once."""
    if not ONBOARDING_AVAILABLE:
        pytest.skip("ONBOARDING_AVAILABLE not set")

    email = f"sdk00-smoke-{_RUN_UID}@example.com"
    username = f"sdk00smoke{_RUN_UID}"

    result = _run_cli(
        keyhole_cli,
        [
            "register",
            "--email", email,
            "--username", username,
            "--display-name", f"SDK-00 Smoke {_RUN_UID}",
            "--realm", "kh-dev",
            "--origin", "smoke",
            "--purpose", "sdk_onboarding",
        ],
        keyhole_home=smoke_keyhole_home,
    )

    if not result.get("success"):
        error_class = result.get("error_class", "unknown")
        # Duplicate user from a previous smoke run with same UID prefix — very
        # unlikely with UUID, but guard explicitly.
        if error_class == "duplicate_registration":
            pytest.skip(
                f"Test user already registered (duplicate_registration).  "
                f"Try re-running with a fresh environment."
            )
        pytest.fail(
            f"register failed: error_class={error_class} "
            f"summary={result.get('summary')}"
        )

    return result


@pytest.fixture(scope="session")
def smoke_verify_result(
    keyhole_cli: str,
    smoke_keyhole_home: Path,
    smoke_register_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Verify the registration using the dev token from the hint.

    Session-scoped — runs once after registration.
    """
    if not ONBOARDING_AVAILABLE:
        pytest.skip("ONBOARDING_AVAILABLE not set")

    hint = smoke_register_result.get("verification_hint", "")
    token: str = ""
    if "Dev/test token:" in hint:
        token = hint.split("Dev/test token:")[-1].strip()
    if not token:
        pytest.fail(
            f"No dev/test token found in verification_hint.  "
            f"hint={hint!r}"
        )

    reg_id = smoke_register_result["registration_id"]

    result = _run_cli(
        keyhole_cli,
        [
            "verify",
            "--registration-id", reg_id,
            "--token", token,
        ],
        keyhole_home=smoke_keyhole_home,
    )

    if not result.get("success"):
        pytest.fail(
            f"verify failed: {result.get('summary') or result.get('error_class')}"
        )

    return result


@pytest.fixture(scope="session")
def smoke_status_post(
    keyhole_cli: str,
    smoke_keyhole_home: Path,
    smoke_verify_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Registration status after verification.  Session-scoped."""
    if not ONBOARDING_AVAILABLE:
        pytest.skip("ONBOARDING_AVAILABLE not set")

    reg_id = smoke_verify_result["registration_id"]

    result = _run_cli(
        keyhole_cli,
        [
            "registration-status",
            "--registration-id", reg_id,
        ],
        keyhole_home=smoke_keyhole_home,
    )

    if not result.get("success"):
        pytest.fail(f"registration-status failed: {result.get('summary')}")

    return result


# =============================================================================
# Layer 0 — Prerequisites
# =============================================================================


class TestLayer0Prerequisites:
    """Layer 0 — Prerequisites Check.

    These tests run unconditionally (no ONBOARDING_AVAILABLE gate) to give
    early signal about the environment.
    """

    def test_keyhole_cli_available(self, keyhole_cli: str):
        """keyhole CLI is discoverable in PATH."""
        assert keyhole_cli is not None

    def test_curl_available(self):
        """curl is available for direct probe tests."""
        assert shutil.which("curl"), "curl not found in PATH"

    def test_register_endpoint_reachable(self):
        """POST /auth/register returns a non-404 response (server is up)."""
        try:
            resp = requests.post(
                f"{MCP_BASE_URL}/auth/register",
                json={},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            # 422 = validation error (server is up, endpoint exists)
            # 404 = wrong path or server down
            assert resp.status_code != 404, (
                f"POST /auth/register returned 404 — server may be down or "
                f"endpoint path has changed (MCP_BASE_URL={MCP_BASE_URL})"
            )
        except requests.RequestException as exc:
            pytest.fail(f"MCP server not reachable at {MCP_BASE_URL}: {exc}")

    def test_status_endpoint_reachable(self):
        """GET /auth/registration-status responds (server is up)."""
        try:
            resp = requests.get(
                f"{MCP_BASE_URL}/auth/registration-status",
                params={"user_id": str(uuid.uuid4())},
                timeout=10,
            )
            # 404 = user not found (expected for a random UUID) — server is up
            # 422 = validation error — server is up
            # 500+ = server error — that's a failure
            # What we must NOT get is a connection error or 503 (service unavailable)
            assert resp.status_code < 500, (
                f"GET /auth/registration-status returned HTTP {resp.status_code} "
                f"(MCP_BASE_URL={MCP_BASE_URL})"
            )
        except requests.RequestException as exc:
            pytest.fail(f"MCP server not reachable: {exc}")


# =============================================================================
# Layer 1 — Register
# =============================================================================


@requires_onboarding
class TestLayer1Register:
    """Layer 1 — New Identity Registration."""

    def test_register_success(self, smoke_register_result: Dict[str, Any]):
        """register command reports success=true."""
        assert smoke_register_result.get("success") is True

    def test_register_has_registration_id(self, smoke_register_result: Dict[str, Any]):
        """Registration result includes a registration_id (user_id)."""
        reg_id = smoke_register_result.get("registration_id")
        assert reg_id is not None, "Missing registration_id in register output"
        assert len(reg_id) > 10, f"registration_id looks malformed: {reg_id!r}"

    def test_register_state_is_pending(self, smoke_register_result: Dict[str, Any]):
        """Registration state indicates pending verification."""
        state = smoke_register_result.get("state", "")
        assert "pending" in state.lower() or "registered" in state.lower(), (
            f"Expected pending state after register, got: {state!r}"
        )

    def test_register_realm_is_kh_dev(self, smoke_register_result: Dict[str, Any]):
        """Registration targets kh-dev realm."""
        assert smoke_register_result.get("realm") == "kh-dev"

    def test_register_origin_set(self, smoke_register_result: Dict[str, Any]):
        """Registration origin=smoke is captured."""
        assert smoke_register_result.get("origin") == "smoke"

    def test_register_purpose_set(self, smoke_register_result: Dict[str, Any]):
        """Registration purpose=sdk_onboarding is captured."""
        assert smoke_register_result.get("purpose") == "sdk_onboarding"

    def test_register_verification_hint_present(self, smoke_register_result: Dict[str, Any]):
        """Registration result includes a verification_hint for dev flow."""
        hint = smoke_register_result.get("verification_hint", "")
        assert hint, "No verification_hint in register output — cannot complete dev verification"

    def test_register_dev_token_in_hint(self, smoke_register_result: Dict[str, Any]):
        """Verification hint contains a dev/test token."""
        hint = smoke_register_result.get("verification_hint", "")
        assert "Dev/test token:" in hint, (
            f"Expected 'Dev/test token:' marker in hint for kh-dev realm. "
            f"hint={hint!r}"
        )

    def test_register_next_steps_present(self, smoke_register_result: Dict[str, Any]):
        """Registration result includes next step guidance."""
        next_steps = smoke_register_result.get("next_steps") or []
        assert len(next_steps) > 0, "No next_steps returned after registration"

    def test_register_next_steps_mention_verify(self, smoke_register_result: Dict[str, Any]):
        """Next steps mention verification."""
        next_steps = smoke_register_result.get("next_steps") or []
        combined = " ".join(next_steps).lower()
        assert "verify" in combined, (
            f"Expected 'verify' in next_steps, got: {next_steps}"
        )


# =============================================================================
# Layer 2 — Pre-verify Status
# =============================================================================


@requires_onboarding
class TestLayer2PreVerifyStatus:
    """Layer 2 — Registration Status (pre-verification)."""

    @pytest.fixture(scope="class")
    def pre_verify_status(
        self,
        keyhole_cli: str,
        smoke_keyhole_home: Path,
        smoke_register_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run registration-status before verification."""
        reg_id = smoke_register_result["registration_id"]
        result = _run_cli(
            keyhole_cli,
            ["registration-status", "--registration-id", reg_id],
            keyhole_home=smoke_keyhole_home,
        )
        if not result.get("success"):
            pytest.fail(f"registration-status failed (pre-verify): {result.get('summary')}")
        return result

    def test_status_success(self, pre_verify_status: Dict[str, Any]):
        """registration-status reports success=true."""
        assert pre_verify_status.get("success") is True

    def test_status_has_registration_id(
        self,
        pre_verify_status: Dict[str, Any],
        smoke_register_result: Dict[str, Any],
    ):
        """Status registration_id matches registration result."""
        assert pre_verify_status.get("registration_id") == smoke_register_result.get("registration_id")

    def test_status_shows_realm(self, pre_verify_status: Dict[str, Any]):
        """Status shows realm=kh-dev."""
        assert pre_verify_status.get("realm") == "kh-dev"

    def test_status_shows_origin(self, pre_verify_status: Dict[str, Any]):
        """Status shows origin=smoke."""
        assert pre_verify_status.get("origin") == "smoke"

    def test_status_shows_purpose(self, pre_verify_status: Dict[str, Any]):
        """Status shows purpose=sdk_onboarding."""
        assert pre_verify_status.get("purpose") == "sdk_onboarding"

    def test_status_state_pending_before_verify(self, pre_verify_status: Dict[str, Any]):
        """Status state indicates pending_verification before verify step."""
        state = pre_verify_status.get("state", "")
        assert "pending" in state.lower() or "registered" in state.lower(), (
            f"Expected pending state pre-verification, got: {state!r}"
        )


# =============================================================================
# Layer 3 — Verify
# =============================================================================


@requires_onboarding
class TestLayer3Verify:
    """Layer 3 — Verification Completion."""

    def test_verify_success(self, smoke_verify_result: Dict[str, Any]):
        """verify command reports success=true."""
        assert smoke_verify_result.get("success") is True, (
            f"verify failed: {smoke_verify_result.get('summary')}"
        )

    def test_verify_has_registration_id(self, smoke_verify_result: Dict[str, Any]):
        """Verify result includes registration_id."""
        assert smoke_verify_result.get("registration_id"), "Missing registration_id in verify output"

    def test_verify_state_active(self, smoke_verify_result: Dict[str, Any]):
        """Verify result state is verified_active (or verified/active)."""
        state = smoke_verify_result.get("state", "")
        assert "verified" in state.lower() or "active" in state.lower(), (
            f"Expected verified/active state after verification, got: {state!r}"
        )

    def test_verify_registration_id_matches(
        self,
        smoke_register_result: Dict[str, Any],
        smoke_verify_result: Dict[str, Any],
    ):
        """Verify registration_id matches what register returned."""
        assert smoke_verify_result.get("registration_id") == smoke_register_result.get("registration_id"), (
            "registration_id mismatch between register and verify results"
        )


# =============================================================================
# Layer 4 — Post-verify Status
# =============================================================================


@requires_onboarding
class TestLayer4PostVerifyStatus:
    """Layer 4 — Registration Status (post-verification)."""

    def test_status_success(self, smoke_status_post: Dict[str, Any]):
        """registration-status reports success=true after verification."""
        assert smoke_status_post.get("success") is True

    def test_status_state_verified_active(self, smoke_status_post: Dict[str, Any]):
        """Post-verify status shows verified_active (or equivalent active state)."""
        state = smoke_status_post.get("state", "")
        assert "verified" in state.lower() or "active" in state.lower(), (
            f"Expected verified/active state after verify, got: {state!r}"
        )

    def test_status_realm_unchanged(self, smoke_status_post: Dict[str, Any]):
        """Realm is still kh-dev after verification."""
        assert smoke_status_post.get("realm") == "kh-dev"

    def test_status_origin_unchanged(self, smoke_status_post: Dict[str, Any]):
        """Origin classification is preserved after verification."""
        assert smoke_status_post.get("origin") == "smoke"

    def test_status_purpose_unchanged(self, smoke_status_post: Dict[str, Any]):
        """Purpose classification is preserved after verification."""
        assert smoke_status_post.get("purpose") == "sdk_onboarding"


# =============================================================================
# Layer 5 — Handoff to SDK-CLIENT-01
# =============================================================================


@requires_onboarding
class TestLayer5Handoff:
    """Layer 5 — Handoff Guidance to SDK-CLIENT-01 Login."""

    def test_next_steps_present(self, smoke_status_post: Dict[str, Any]):
        """Post-verify status provides next_steps guidance."""
        next_steps = smoke_status_post.get("next_steps") or []
        assert len(next_steps) > 0, "No next_steps returned after completed onboarding"

    def test_next_steps_mention_login_or_sdk01(self, smoke_status_post: Dict[str, Any]):
        """Next steps for active identity point toward login or SDK-CLIENT-01."""
        next_steps = smoke_status_post.get("next_steps") or []
        combined = " ".join(next_steps).lower()
        assert "login" in combined or "authentication" in combined or "sdk-01" in combined or "sdk-client-01" in combined, (
            f"Expected next_steps to mention login or SDK-CLIENT-01 authentication. "
            f"Got: {next_steps}"
        )

    def test_no_auth_credentials_in_output(
        self,
        smoke_register_result: Dict[str, Any],
        smoke_verify_result: Dict[str, Any],
        smoke_status_post: Dict[str, Any],
    ):
        """No auth access tokens or session credentials leak into CLI outputs.

        SDK-CLIENT-00 must not persist or expose session credentials — that is
        SDK-CLIENT-01's responsibility.
        """
        _CREDENTIAL_PATTERNS = [
            r'"access_token"\s*:',
            r'"refresh_token"\s*:',
            r'"session_token"\s*:',
            r'"bearer"\s*:',
            r'"id_token"\s*:',
        ]
        for result in (smoke_register_result, smoke_verify_result, smoke_status_post):
            serialized = json.dumps(result)
            for pattern in _CREDENTIAL_PATTERNS:
                if re.search(pattern, serialized, re.IGNORECASE):
                    pytest.fail(
                        f"Auth credential pattern {pattern!r} found in CLI output. "
                        f"SDK-CLIENT-00 must not persist session credentials."
                    )


# =============================================================================
# Layer 6 — Proof Bundle
# =============================================================================


@requires_onboarding
class TestLayer6ProofBundle:
    """Layer 6 — Onboarding Proof Bundle Verification.

    At minimum the proof directory must contain the hot proof core files
    declared in §16 of the story.
    """

    _HOT_CORE_FILES = [
        "core.json",
        "request.json",
        "response.json",
        "event_chain.json",
        "registration_context.json",
        "verification_result.json",
        "identity_context.json",
        "correlation.json",
        "summary.md",
        "diff.json",
        "digest.txt",
    ]

    # Patterns that must never appear in proof artifacts (secret leakage guard)
    _SECRET_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
        r"access_token",
        r"refresh_token",
        r"bearer",
        r"id_token",
        r"private_key",
        r"client_secret",
    ]]

    def _find_proof_dir(self, keyhole_home: Path) -> Optional[Path]:
        """Locate the proof bundle directory under KEYHOLE_HOME."""
        for candidate in (
            "proof_bundle",
            "onboarding_proof_bundle",
            "proof",
            "onboarding_proof",
        ):
            p = keyhole_home / candidate
            if p.exists():
                return p
        # Search one level deeper
        for child in keyhole_home.iterdir():
            if child.is_dir():
                for candidate in ("proof_bundle", "onboarding_proof_bundle", "proof"):
                    p = child / candidate
                    if p.exists():
                        return p
        return None

    def test_proof_directory_created(
        self,
        smoke_keyhole_home: Path,
        smoke_verify_result: Dict[str, Any],
    ):
        """Proof bundle directory was created after onboarding completes."""
        proof_dir = self._find_proof_dir(smoke_keyhole_home)
        assert proof_dir is not None, (
            f"No proof bundle directory found under KEYHOLE_HOME={smoke_keyhole_home}. "
            f"Expected 'proof_bundle/' or 'proof/' to be created."
        )

    def test_core_json_exists(
        self,
        smoke_keyhole_home: Path,
        smoke_verify_result: Dict[str, Any],
    ):
        """core.json proof artifact exists."""
        proof_dir = self._find_proof_dir(smoke_keyhole_home)
        if proof_dir is None:
            pytest.skip("Proof dir not found — covered by test_proof_directory_created")
        assert (proof_dir / "core.json").exists(), (
            f"core.json not found in proof dir {proof_dir}"
        )

    def test_hot_core_files_present(
        self,
        smoke_keyhole_home: Path,
        smoke_verify_result: Dict[str, Any],
    ):
        """All §16 hot-core proof files are present in the bundle."""
        proof_dir = self._find_proof_dir(smoke_keyhole_home)
        if proof_dir is None:
            pytest.skip("Proof dir not found — covered by test_proof_directory_created")
        missing = [f for f in self._HOT_CORE_FILES if not (proof_dir / f).exists()]
        assert not missing, (
            f"Missing proof files in {proof_dir}: {missing}"
        )

    def test_digest_format(
        self,
        smoke_keyhole_home: Path,
        smoke_verify_result: Dict[str, Any],
    ):
        """digest.txt contains a sha256: prefixed digest."""
        proof_dir = self._find_proof_dir(smoke_keyhole_home)
        if proof_dir is None:
            pytest.skip("Proof dir not found")
        digest_path = proof_dir / "digest.txt"
        if not digest_path.exists():
            pytest.skip("digest.txt not present — covered by test_hot_core_files_present")
        content = digest_path.read_text().strip()
        assert content.startswith("sha256:"), (
            f"digest.txt does not start with 'sha256:'. Content: {content[:80]}"
        )

    def test_no_secret_leakage_in_proof(
        self,
        smoke_keyhole_home: Path,
        smoke_verify_result: Dict[str, Any],
    ):
        """No secret-bearing material (tokens, keys) leaks into proof files.

        §12.3 of the story: verification artifacts must not leak into proof
        bundles, logs, or user-facing summaries.
        """
        proof_dir = self._find_proof_dir(smoke_keyhole_home)
        if proof_dir is None:
            pytest.skip("Proof dir not found")
        violations: list[str] = []
        for artifact in proof_dir.rglob("*.json"):
            try:
                content = artifact.read_text()
            except Exception:
                continue
            for pattern in self._SECRET_PATTERNS:
                if pattern.search(content):
                    violations.append(f"{artifact.name}: matched {pattern.pattern!r}")
        assert not violations, (
            f"Secret patterns found in proof artifacts:\n" + "\n".join(violations)
        )

    def test_summary_mentions_onboarding_closure(
        self,
        smoke_keyhole_home: Path,
        smoke_verify_result: Dict[str, Any],
    ):
        """summary.md describes onboarding closure (title and verification state)."""
        proof_dir = self._find_proof_dir(smoke_keyhole_home)
        if proof_dir is None:
            pytest.skip("Proof dir not found")
        summary_path = proof_dir / "summary.md"
        if not summary_path.exists():
            pytest.skip("summary.md not present — covered by test_hot_core_files_present")
        content = summary_path.read_text().lower()
        assert "sdk-client-00" in content or "onboarding" in content, (
            "summary.md does not mention SDK-CLIENT-00 or onboarding"
        )
        assert "verif" in content, (
            "summary.md does not mention verification"
        )

    def test_verification_result_has_active_state(
        self,
        smoke_keyhole_home: Path,
        smoke_verify_result: Dict[str, Any],
    ):
        """verification_result.json shows an active/verified state."""
        proof_dir = self._find_proof_dir(smoke_keyhole_home)
        if proof_dir is None:
            pytest.skip("Proof dir not found")
        vr_path = proof_dir / "verification_result.json"
        if not vr_path.exists():
            pytest.skip("verification_result.json not present")
        vr = json.loads(vr_path.read_text())
        state = vr.get("state", "")
        assert "verified" in state.lower() or "active" in state.lower(), (
            f"verification_result.json state does not indicate verified/active: {state!r}"
        )

    def test_event_chain_has_verification_event(
        self,
        smoke_keyhole_home: Path,
        smoke_verify_result: Dict[str, Any],
    ):
        """event_chain.json includes at least one verification event."""
        proof_dir = self._find_proof_dir(smoke_keyhole_home)
        if proof_dir is None:
            pytest.skip("Proof dir not found")
        ec_path = proof_dir / "event_chain.json"
        if not ec_path.exists():
            pytest.skip("event_chain.json not present")
        ec = json.loads(ec_path.read_text())
        events = ec.get("events", [])
        assert len(events) > 0, "event_chain.json has no events"
        event_types = [e.get("event_type", "") for e in events]
        assert any("verif" in t.lower() for t in event_types), (
            f"No verification event in event_chain. Found: {event_types}"
        )
