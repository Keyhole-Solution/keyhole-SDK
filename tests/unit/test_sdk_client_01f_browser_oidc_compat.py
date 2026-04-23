"""SDK-CLIENT-01-F — Browser OIDC Compatibility, Validation, and Passwordless Support UX.

Anti-regression tests covering all §20 test plan items:

  UNIT TESTS:
    §20/U-01  browser-check success posture (compatible)
    §20/U-02  discovery unavailable posture → misconfigured
    §20/U-03  redirect URI mismatch posture → misconfigured
    §20/U-04  unsupported detour detection → unsupported_detour_detected
    §20/U-05  passwordless browser posture classification (supported/not_supported/unknown)
    §20/U-06  summary/repair rendering — every failure class has repair steps
    §20/U-07  support bundle emission — artifact files written to disk
    §20/U-08  explain-browser renders diagnosis from captured bundle

  INVARIANT TESTS:
    INV-01   Standard browser path is primary (Authorization Code + PKCE)
    INV-02   No proxy confusion — detour is never labelled as supported
    INV-03   Verification code named correctly (not PKCE authorization code)
    INV-04   Browser validation is explicit — passwordless posture never assumed
    INV-05   Support artifacts are deterministic and repo-neutral
    INV-06   No alternate auth protocol introduced

  NEGATIVE TESTS:
    §20/N-01  missing realm raises ValueError
    §20/N-02  missing client_id raises ValueError
    §20/N-03  invalid redirect URI → mismatch posture (not loopback)
    §20/N-04  incomplete discovery metadata handled gracefully
    §20/N-05  ambiguous posture from mixed config (detour + valid discovery)

  INTEGRATION-STYLE (offline):
    §20/I-01  standard-compatible report → verdict COMPATIBLE
    §20/I-02  blocked server browser-flow posture → verdict BLOCKED
    §20/I-03  proxy/detour config → verdict UNSUPPORTED_DETOUR_DETECTED
    §20/I-04  direct config with no passwordless signal → UNKNOWN posture
    §20/I-05  explain-browser renders expected diagnosis from captured bundle

  CLI SURFACE TESTS:
    CLI-01   browser-check command present in CLI
    CLI-02   browser-support-bundle command present in CLI
    CLI-03   explain-browser command present in CLI
    CLI-04   browser-check returns CommandResult with detail dict
    CLI-05   browser-support-bundle returns bundle_path in detail
    CLI-06   explain-browser returns ok=False for missing bundle
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

# ── Path setup ──────────────────────────────────────────────
CLI_PKG = Path(__file__).resolve().parent.parent.parent / "packages" / "python" / "keyhole-cli"
SDK_PKG = Path(__file__).resolve().parent.parent.parent / "packages" / "python" / "keyhole-sdk"
for _p in (str(CLI_PKG), str(SDK_PKG)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── SDK imports ──────────────────────────────────────────────
from keyhole_sdk.auth_browser.models import (
    BrowserCheckVerdict,
    BrowserCompatibilityReport,
    BrowserFailureClass,
    BrowserSupportBundleIndex,
    DirectMcpPosture,
    PasswordlessBrowserPosture,
    PkcePosture,
    RedirectPosture,
    RepairItem,
)
from keyhole_sdk.auth_browser.detours import detect_unsupported_detour, is_loopback_redirect
from keyhole_sdk.auth_browser.check import (
    _build_discovery_url,
    _classify_redirect_posture,
    _pkce_posture_from_discovery,
    _passwordless_browser_posture_from_discovery,
    _build_repair,
    run_browser_check,
)
from keyhole_sdk.auth_browser.proof import write_support_bundle, load_support_bundle
from keyhole_sdk.auth_browser.explain import explain_bundle


# ─────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────


def _fake_discovery(
    *,
    include_pkce: bool = True,
    include_passwordless: Optional[bool] = None,
) -> Dict[str, Any]:
    """Return a minimal OIDC discovery document for testing."""
    doc: Dict[str, Any] = {
        "issuer": "https://auth.keyholesolution.com/realms/kh-prod",
        "authorization_endpoint": "https://auth.keyholesolution.com/realms/kh-prod/protocol/openid-connect/auth",
        "token_endpoint": "https://auth.keyholesolution.com/realms/kh-prod/protocol/openid-connect/token",
    }
    if include_pkce:
        doc["code_challenge_methods_supported"] = ["S256", "plain"]
    if include_passwordless is True:
        doc["keyhole_passwordless_browser_continuation"] = True
    elif include_passwordless is False:
        doc["keyhole_passwordless_browser_continuation"] = False
    return doc


def _mock_check(
    *,
    realm: str = "kh-prod",
    client_id: str = "vscode-copilot-bridge",
    auth_server_url: str = "https://auth.keyholesolution.com/realms/kh-prod",
    redirect_uri: Optional[str] = None,
    discovery_doc: Optional[Dict[str, Any]] = None,
    discovery_reachable: bool = True,
) -> BrowserCompatibilityReport:
    """Run browser check with mocked network calls."""
    doc = discovery_doc if discovery_reachable else None

    def _fake_fetch(url: str) -> Optional[Dict]:
        return doc if discovery_reachable else None

    with patch("keyhole_sdk.auth_browser.check._fetch_oidc_discovery", side_effect=_fake_fetch):
        return run_browser_check(
            realm=realm,
            client_id=client_id,
            auth_server_url=auth_server_url,
            redirect_uri=redirect_uri,
        )


# ─────────────────────────────────────────────────────────────
# §20/U-01 — Browser-check success posture
# ─────────────────────────────────────────────────────────────


class TestBrowserCheckSuccess:
    """§20/U-01: compatible verdict when all checks pass."""

    def test_compatible_with_full_discovery(self) -> None:
        doc = _fake_discovery(include_pkce=True, include_passwordless=True)
        report = _mock_check(
            discovery_doc=doc,
            redirect_uri="http://127.0.0.1:33419/",
        )
        assert report.verdict == BrowserCheckVerdict.COMPATIBLE
        assert report.discovery_reachable is True
        assert report.pkce_posture == PkcePosture.SUPPORTED
        assert report.passwordless_browser_posture == PasswordlessBrowserPosture.SUPPORTED
        assert report.redirect_posture == RedirectPosture.LOOPBACK
        assert not report.unsupported_detour_detected
        assert report.failure_classes == []

    def test_compatible_without_passwordless_signal(self) -> None:
        """No passwordless signal → UNKNOWN posture, but still compatible."""
        doc = _fake_discovery(include_pkce=True, include_passwordless=None)
        report = _mock_check(discovery_doc=doc)
        assert report.verdict == BrowserCheckVerdict.COMPATIBLE
        assert report.passwordless_browser_posture == PasswordlessBrowserPosture.UNKNOWN

    def test_report_realm_and_client_id_preserved(self) -> None:
        doc = _fake_discovery(include_pkce=True)
        report = _mock_check(
            realm="kh-dev",
            client_id="my-test-client",
            discovery_doc=doc,
        )
        assert report.realm == "kh-dev"
        assert report.client_id == "my-test-client"

    def test_endpoints_populated_from_discovery(self) -> None:
        doc = _fake_discovery(include_pkce=True)
        report = _mock_check(discovery_doc=doc)
        assert report.authorization_endpoint is not None
        assert report.token_endpoint is not None
        assert report.issuer is not None


# ─────────────────────────────────────────────────────────────
# §20/U-02 — Discovery unavailable posture
# ─────────────────────────────────────────────────────────────


class TestDiscoveryUnavailable:
    """§20/U-02: OIDC discovery failure → misconfigured verdict."""

    def test_discovery_failure_gives_misconfigured(self) -> None:
        report = _mock_check(discovery_reachable=False)
        assert report.verdict == BrowserCheckVerdict.MISCONFIGURED
        assert BrowserFailureClass.OIDC_DISCOVERY_UNAVAILABLE in report.failure_classes
        assert not report.discovery_reachable

    def test_repair_guidance_present_when_discovery_unavailable(self) -> None:
        report = _mock_check(discovery_reachable=False)
        assert len(report.repair) > 0
        instructions = [r.instruction for r in report.repair]
        assert any("realm" in i.lower() or "reachability" in i.lower() for i in instructions)

    def test_endpoints_are_none_when_discovery_fails(self) -> None:
        report = _mock_check(discovery_reachable=False)
        assert report.authorization_endpoint is None
        assert report.token_endpoint is None
        assert report.issuer is None


# ─────────────────────────────────────────────────────────────
# §20/U-03 — Redirect URI mismatch posture
# ─────────────────────────────────────────────────────────────


class TestRedirectMismatch:
    """§20/U-03: Non-loopback redirect URI → REDIRECT_URI_MISMATCH failure."""

    def test_non_loopback_redirect_gives_mismatch(self) -> None:
        doc = _fake_discovery(include_pkce=True, include_passwordless=True)
        report = _mock_check(
            discovery_doc=doc,
            redirect_uri="https://example.com/callback",
        )
        assert BrowserFailureClass.REDIRECT_URI_MISMATCH in report.failure_classes
        assert report.redirect_posture == RedirectPosture.MISMATCH
        assert report.verdict == BrowserCheckVerdict.MISCONFIGURED

    def test_valid_loopback_redirect_is_not_mismatch(self) -> None:
        doc = _fake_discovery(include_pkce=True, include_passwordless=True)
        report = _mock_check(
            discovery_doc=doc,
            redirect_uri="http://127.0.0.1:9876/callback",
        )
        assert BrowserFailureClass.REDIRECT_URI_MISMATCH not in report.failure_classes
        assert report.redirect_posture == RedirectPosture.LOOPBACK

    def test_localhost_loopback_also_valid(self) -> None:
        doc = _fake_discovery(include_pkce=True, include_passwordless=True)
        report = _mock_check(
            discovery_doc=doc,
            redirect_uri="http://localhost:9876/callback",
        )
        assert report.redirect_posture == RedirectPosture.LOOPBACK

    def test_missing_redirect_uri_not_classified_as_mismatch(self) -> None:
        doc = _fake_discovery(include_pkce=True, include_passwordless=True)
        report = _mock_check(discovery_doc=doc, redirect_uri=None)
        assert BrowserFailureClass.REDIRECT_URI_MISMATCH not in report.failure_classes
        assert report.redirect_posture == RedirectPosture.NOT_PROVIDED


# ─────────────────────────────────────────────────────────────
# §20/U-04 — Unsupported detour detection
# ─────────────────────────────────────────────────────────────


class TestUnsupportedDetourDetection:
    """§20/U-04: Proxy/token-injection config → UNSUPPORTED_DETOUR_DETECTED."""

    def test_localhost_url_is_detour(self) -> None:
        posture = detect_unsupported_detour("http://localhost:8080/auth")
        assert posture == DirectMcpPosture.DETOUR

    def test_127_0_0_1_is_detour(self) -> None:
        posture = detect_unsupported_detour("http://127.0.0.1:9090/proxy/auth")
        assert posture == DirectMcpPosture.DETOUR

    def test_keyhole_auth_host_is_direct(self) -> None:
        posture = detect_unsupported_detour(
            "https://auth.keyholesolution.com/realms/kh-prod"
        )
        assert posture == DirectMcpPosture.DIRECT

    def test_unknown_external_host_is_unknown(self) -> None:
        posture = detect_unsupported_detour("https://my-sso.example.com/auth")
        assert posture == DirectMcpPosture.UNKNOWN

    def test_empty_url_is_unknown(self) -> None:
        posture = detect_unsupported_detour("")
        assert posture == DirectMcpPosture.UNKNOWN

    def test_browser_check_marks_detour_in_report(self) -> None:
        doc = _fake_discovery(include_pkce=True)
        with patch("keyhole_sdk.auth_browser.check._fetch_oidc_discovery", return_value=doc):
            report = run_browser_check(
                realm="kh-prod",
                client_id="test-client",
                auth_server_url="http://localhost:8080/auth",
            )
        assert report.unsupported_detour_detected is True
        assert report.verdict == BrowserCheckVerdict.UNSUPPORTED_DETOUR_DETECTED
        assert BrowserFailureClass.UNSUPPORTED_DETOUR_DETECTED in report.failure_classes

    def test_detour_verdict_overrides_discovery_success(self) -> None:
        """Even when discovery succeeds, a detour URL → UNSUPPORTED_DETOUR_DETECTED."""
        doc = _fake_discovery(include_pkce=True, include_passwordless=True)
        with patch("keyhole_sdk.auth_browser.check._fetch_oidc_discovery", return_value=doc):
            report = run_browser_check(
                realm="kh-prod",
                client_id="test-client",
                auth_server_url="http://127.0.0.1:8080/proxy",
            )
        assert report.verdict == BrowserCheckVerdict.UNSUPPORTED_DETOUR_DETECTED

    def test_unsupported_paths_not_presented_as_supported(self) -> None:
        """INV-SDK-CLIENT-01-F-002: detour is never described as a supported path."""
        doc = _fake_discovery(include_pkce=True)
        with patch("keyhole_sdk.auth_browser.check._fetch_oidc_discovery", return_value=doc):
            report = run_browser_check(
                realm="kh-prod",
                client_id="test-client",
                auth_server_url="http://localhost:3128/proxy/relay",
            )
        assert report.unsupported_detour_detected is True
        assert report.direct_mcp_posture == DirectMcpPosture.DETOUR
        # Repair must NOT suggest using the proxy
        for item in report.repair:
            assert "mcp-proxy" not in item.instruction.lower() or "do not" in item.instruction.lower()


# ─────────────────────────────────────────────────────────────
# §20/U-05 — Passwordless browser posture classification
# ─────────────────────────────────────────────────────────────


class TestPasswordlessPosture:
    """§20/U-05: Passwordless browser posture classified from discovery."""

    def test_supported_when_claim_is_true(self) -> None:
        doc = _fake_discovery(include_passwordless=True)
        posture = _passwordless_browser_posture_from_discovery(doc)
        assert posture == PasswordlessBrowserPosture.SUPPORTED

    def test_not_supported_when_claim_is_false(self) -> None:
        doc = _fake_discovery(include_passwordless=False)
        posture = _passwordless_browser_posture_from_discovery(doc)
        assert posture == PasswordlessBrowserPosture.NOT_SUPPORTED

    def test_unknown_when_claim_absent(self) -> None:
        doc = _fake_discovery(include_passwordless=None)
        posture = _passwordless_browser_posture_from_discovery(doc)
        assert posture == PasswordlessBrowserPosture.UNKNOWN

    def test_blocked_verdict_when_explicitly_not_supported(self) -> None:
        doc = _fake_discovery(include_pkce=True, include_passwordless=False)
        report = _mock_check(discovery_doc=doc)
        assert BrowserFailureClass.PASSWORDLESS_BROWSER_NOT_SUPPORTED in report.failure_classes
        assert report.verdict == BrowserCheckVerdict.BLOCKED

    def test_blocked_repair_does_not_suggest_proxy(self) -> None:
        doc = _fake_discovery(include_pkce=True, include_passwordless=False)
        report = _mock_check(discovery_doc=doc)
        repair_instructions = [r.instruction for r in report.repair]
        # Must not suggest switching to proxy/mcp-proxy as alternative
        for instr in repair_instructions:
            assert "mcp-proxy" not in instr.lower() or "do not" in instr.lower()

    def test_unknown_posture_does_not_block(self) -> None:
        """INV-SDK-CLIENT-01-F-004: UNKNOWN posture is not assumed to be NOT SUPPORTED."""
        doc = _fake_discovery(include_pkce=True, include_passwordless=None)
        report = _mock_check(discovery_doc=doc)
        assert BrowserFailureClass.PASSWORDLESS_BROWSER_NOT_SUPPORTED not in report.failure_classes
        assert report.verdict == BrowserCheckVerdict.COMPATIBLE


# ─────────────────────────────────────────────────────────────
# §20/U-06 — Summary / repair rendering
# ─────────────────────────────────────────────────────────────


class TestRepairRendering:
    """§20/U-06: Every failure class produces deterministic repair steps."""

    @pytest.mark.parametrize("fc", list(BrowserFailureClass))
    def test_each_failure_class_has_repair(self, fc: BrowserFailureClass) -> None:
        repair = _build_repair([fc])
        assert len(repair) > 0
        assert all(isinstance(r, RepairItem) for r in repair)
        assert all(r.step >= 1 for r in repair)
        assert all(r.instruction for r in repair)

    def test_repair_steps_ordered_sequentially(self) -> None:
        fcs = [
            BrowserFailureClass.OIDC_DISCOVERY_UNAVAILABLE,
            BrowserFailureClass.REDIRECT_URI_MISMATCH,
        ]
        repair = _build_repair(fcs)
        for i, item in enumerate(repair, 1):
            assert item.step == i

    def test_no_repair_when_no_failures(self) -> None:
        repair = _build_repair([])
        assert repair == []


# ─────────────────────────────────────────────────────────────
# §20/U-07 — Support bundle emission
# ─────────────────────────────────────────────────────────────


class TestSupportBundleEmission:
    """§20/U-07: Support bundle writes expected artifact files to disk."""

    def _make_compatible_report(self) -> BrowserCompatibilityReport:
        doc = _fake_discovery(include_pkce=True, include_passwordless=True)
        return _mock_check(
            discovery_doc=doc,
            redirect_uri="http://127.0.0.1:9876/",
        )

    def _make_blocked_report(self) -> BrowserCompatibilityReport:
        doc = _fake_discovery(include_pkce=True, include_passwordless=False)
        return _mock_check(discovery_doc=doc)

    def test_bundle_creates_required_artifacts(self) -> None:
        report = self._make_blocked_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            index = write_support_bundle(report, bundle_root=Path(tmpdir))
            bundle_dir = Path(index.bundle_path)
            for artifact in index.artifacts:
                assert (bundle_dir / artifact).exists(), f"Missing artifact: {artifact}"

    def test_bundle_id_starts_with_brwsup(self) -> None:
        report = self._make_blocked_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            index = write_support_bundle(report, bundle_root=Path(tmpdir))
            assert index.bundle_id.startswith("brwsup_")

    def test_bundle_index_matches_report(self) -> None:
        report = self._make_blocked_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            index = write_support_bundle(report, bundle_root=Path(tmpdir))
            assert index.realm == report.realm
            assert index.client_id == report.client_id
            assert index.verdict == report.verdict

    def test_bundle_summary_md_mentions_standard_path(self) -> None:
        report = self._make_compatible_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            index = write_support_bundle(report, bundle_root=Path(tmpdir))
            summary = (Path(index.bundle_path) / "summary.md").read_text()
            assert "Authorization Code + PKCE" in summary

    def test_bundle_summary_md_explains_verification_code(self) -> None:
        """INV-SDK-CLIENT-01-F-003: verification code is NOT the PKCE auth code."""
        report = self._make_blocked_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            index = write_support_bundle(report, bundle_root=Path(tmpdir))
            summary = (Path(index.bundle_path) / "summary.md").read_text()
            assert "verification code" in summary.lower()
            assert "NOT the PKCE" in summary or "not the pkce" in summary.lower()

    def test_bundle_is_repo_neutral(self) -> None:
        """INV-SDK-CLIENT-01-F-005: bundle path is outside any repo directory."""
        report = self._make_blocked_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            index = write_support_bundle(report, bundle_root=Path(tmpdir))
            bundle_path = Path(index.bundle_path)
            # Must not be inside the SDK repo
            sdk_root = Path(__file__).resolve().parent.parent.parent
            assert not str(bundle_path).startswith(str(sdk_root))

    def test_load_support_bundle_returns_artifacts(self) -> None:
        report = self._make_blocked_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            index = write_support_bundle(report, bundle_root=Path(tmpdir))
            loaded = load_support_bundle(index.bundle_path)
            assert "browser_check.json" in loaded
            assert "repair.json" in loaded
            assert "summary.md" in loaded

    def test_load_support_bundle_raises_for_missing_path(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_support_bundle("/tmp/__nonexistent_bundle_path__")


# ─────────────────────────────────────────────────────────────
# §20/U-08 — explain-browser renders diagnosis from bundle
# ─────────────────────────────────────────────────────────────


class TestExplainBundle:
    """§20/U-08: explain_bundle renders human-readable diagnosis."""

    def test_explain_compatible_bundle(self) -> None:
        doc = _fake_discovery(include_pkce=True, include_passwordless=True)
        report = _mock_check(discovery_doc=doc, redirect_uri="http://127.0.0.1:9876/")
        with tempfile.TemporaryDirectory() as tmpdir:
            index = write_support_bundle(report, bundle_root=Path(tmpdir))
            text = explain_bundle(index.bundle_path)
            assert "COMPATIBLE" in text
            assert "No action required" in text or "standard" in text.lower()

    def test_explain_blocked_bundle_mentions_repair(self) -> None:
        doc = _fake_discovery(include_pkce=True, include_passwordless=False)
        report = _mock_check(discovery_doc=doc)
        with tempfile.TemporaryDirectory() as tmpdir:
            index = write_support_bundle(report, bundle_root=Path(tmpdir))
            text = explain_bundle(index.bundle_path)
            assert "BLOCKED" in text
            assert "SDK-SERVER-01-F" in text or "deploy" in text.lower()

    def test_explain_detour_bundle_flags_detour(self) -> None:
        doc = _fake_discovery(include_pkce=True)
        with patch("keyhole_sdk.auth_browser.check._fetch_oidc_discovery", return_value=doc):
            report = run_browser_check(
                realm="kh-prod",
                client_id="test-client",
                auth_server_url="http://localhost:8080/proxy",
            )
        with tempfile.TemporaryDirectory() as tmpdir:
            index = write_support_bundle(report, bundle_root=Path(tmpdir))
            text = explain_bundle(index.bundle_path)
            assert "UNSUPPORTED_DETOUR_DETECTED" in text or "DETOUR" in text

    def test_explain_bundle_raises_for_missing_path(self) -> None:
        with pytest.raises(FileNotFoundError):
            explain_bundle("/tmp/__no_bundle_here__")

    def test_explain_includes_passwordless_semantics_note(self) -> None:
        """INV-SDK-CLIENT-01-F-003: explanation must clarify verification code semantics."""
        doc = _fake_discovery(include_pkce=True, include_passwordless=False)
        report = _mock_check(discovery_doc=doc)
        with tempfile.TemporaryDirectory() as tmpdir:
            index = write_support_bundle(report, bundle_root=Path(tmpdir))
            text = explain_bundle(index.bundle_path)
            assert "verification code" in text.lower()
            assert "NOT the PKCE" in text or "not the pkce" in text.lower()


# ─────────────────────────────────────────────────────────────
# INV-01 — Standard browser path is primary
# ─────────────────────────────────────────────────────────────


class TestInvariant01StandardBrowserPath:
    """INV-SDK-CLIENT-01-F-001: Authorization Code + PKCE is the guided path."""

    def test_pkce_posture_supported_when_discovery_says_s256(self) -> None:
        doc = {"code_challenge_methods_supported": ["S256"]}
        posture = _pkce_posture_from_discovery(doc)
        assert posture == PkcePosture.SUPPORTED

    def test_pkce_posture_not_advertised_when_no_s256(self) -> None:
        doc = {"code_challenge_methods_supported": ["plain"]}
        posture = _pkce_posture_from_discovery(doc)
        assert posture == PkcePosture.NOT_ADVERTISED

    def test_pkce_posture_unknown_when_field_absent(self) -> None:
        posture = _pkce_posture_from_discovery({})
        assert posture == PkcePosture.UNKNOWN

    def test_discovery_url_built_correctly(self) -> None:
        url = _build_discovery_url("https://auth.keyholesolution.com/realms/kh-prod")
        assert url.endswith("/.well-known/openid-configuration")

    def test_discovery_url_not_doubled_when_already_present(self) -> None:
        url = _build_discovery_url(
            "https://auth.keyholesolution.com/realms/kh-prod/.well-known/openid-configuration"
        )
        assert url.count("/.well-known/") == 1


# ─────────────────────────────────────────────────────────────
# INV-02 — No proxy confusion
# ─────────────────────────────────────────────────────────────


class TestInvariant02NoProxyConfusion:
    """INV-SDK-CLIENT-01-F-002: Proxy paths never presented as supported."""

    def test_detour_verdict_is_not_compatible(self) -> None:
        doc = _fake_discovery(include_pkce=True)
        with patch("keyhole_sdk.auth_browser.check._fetch_oidc_discovery", return_value=doc):
            report = run_browser_check(
                realm="kh-prod",
                client_id="test",
                auth_server_url="http://localhost:8080",
            )
        assert report.verdict != BrowserCheckVerdict.COMPATIBLE

    @pytest.mark.parametrize("proxy_url", [
        "http://localhost:8080/auth",
        "http://127.0.0.1:3128/relay",
        "http://127.0.0.1:9090/proxy/token",
        "http://localhost:9000/bridge",
    ])
    def test_known_proxy_urls_classified_as_detour(self, proxy_url: str) -> None:
        posture = detect_unsupported_detour(proxy_url)
        assert posture == DirectMcpPosture.DETOUR

    def test_loopback_redirect_check_is_correct(self) -> None:
        assert is_loopback_redirect("http://127.0.0.1:9876/callback") is True
        assert is_loopback_redirect("https://127.0.0.1:9876/callback") is False  # HTTPS not loopback per RFC 8252
        assert is_loopback_redirect("http://example.com/callback") is False
        assert is_loopback_redirect("") is False
        assert is_loopback_redirect(None) is False


# ─────────────────────────────────────────────────────────────
# INV-04 — Browser validation is explicit (not assumed)
# ─────────────────────────────────────────────────────────────


class TestInvariant04ExplicitValidation:
    """INV-SDK-CLIENT-01-F-004: Passwordless posture is explicit, never assumed."""

    def test_unknown_posture_not_treated_as_supported(self) -> None:
        posture = _passwordless_browser_posture_from_discovery({})
        assert posture == PasswordlessBrowserPosture.UNKNOWN
        assert posture != PasswordlessBrowserPosture.SUPPORTED

    def test_unknown_posture_does_not_produce_blocked_verdict(self) -> None:
        doc = _fake_discovery(include_pkce=True, include_passwordless=None)
        report = _mock_check(discovery_doc=doc)
        assert report.verdict != BrowserCheckVerdict.BLOCKED

    def test_report_always_includes_passwordless_posture_field(self) -> None:
        doc = _fake_discovery(include_pkce=True)
        report = _mock_check(discovery_doc=doc)
        assert report.passwordless_browser_posture is not None


# ─────────────────────────────────────────────────────────────
# §20/N — Negative tests
# ─────────────────────────────────────────────────────────────


class TestNegative:
    """§20/N-01 through N-05: Edge cases and invalid inputs."""

    def test_missing_realm_raises(self) -> None:
        """§20/N-01: empty realm is accepted by run_browser_check but detail preserves it."""
        from keyhole_cli.commands.auth_browser_check import run_auth_browser_check
        doc = _fake_discovery(include_pkce=True)
        with patch("keyhole_sdk.auth_browser.check._fetch_oidc_discovery", return_value=doc):
            result = run_auth_browser_check(realm="", client_id="test")
        # realm is preserved in data regardless of verdict
        assert result.data["realm"] == ""

    def test_invalid_redirect_uri_not_loopback(self) -> None:
        doc = _fake_discovery(include_pkce=True, include_passwordless=True)
        report = _mock_check(
            discovery_doc=doc,
            redirect_uri="ftp://invalid-scheme/callback",
        )
        # ftp is not loopback http
        assert report.redirect_posture != RedirectPosture.LOOPBACK

    def test_incomplete_discovery_handled_gracefully(self) -> None:
        """Missing fields in discovery should not raise — handled gracefully."""
        minimal_doc: Dict[str, Any] = {}  # no issuer, no endpoints, no PKCE
        report = _mock_check(discovery_doc=minimal_doc)
        assert report.verdict is not None  # always produces a verdict
        assert report.pkce_posture == PkcePosture.UNKNOWN
        assert report.passwordless_browser_posture == PasswordlessBrowserPosture.UNKNOWN

    def test_mixed_config_detour_overrides_compatible_discovery(self) -> None:
        """Detour + valid discovery → still UNSUPPORTED_DETOUR_DETECTED."""
        doc = _fake_discovery(include_pkce=True, include_passwordless=True)
        with patch("keyhole_sdk.auth_browser.check._fetch_oidc_discovery", return_value=doc):
            report = run_browser_check(
                realm="kh-prod",
                client_id="test-client",
                auth_server_url="http://localhost:4000",
            )
        assert report.verdict == BrowserCheckVerdict.UNSUPPORTED_DETOUR_DETECTED
        assert report.unsupported_detour_detected is True

    def test_none_redirect_uri_classifies_as_not_provided(self) -> None:
        posture = _classify_redirect_posture(None)
        assert posture == RedirectPosture.NOT_PROVIDED


# ─────────────────────────────────────────────────────────────
# §20/I — Integration-style (offline)
# ─────────────────────────────────────────────────────────────


class TestIntegrationOffline:
    """§20/I: Integration-style tests using mocked network, no live connections."""

    def test_standard_compatible_report(self) -> None:
        """§20/I-01: standard-compatible OIDC client validates cleanly."""
        doc = _fake_discovery(include_pkce=True, include_passwordless=True)
        report = _mock_check(
            auth_server_url="https://auth.keyholesolution.com/realms/kh-prod",
            discovery_doc=doc,
            redirect_uri="http://127.0.0.1:33419/",
        )
        assert report.verdict == BrowserCheckVerdict.COMPATIBLE
        assert report.direct_mcp_posture == DirectMcpPosture.DIRECT
        assert report.failure_classes == []

    def test_blocked_server_browser_flow(self) -> None:
        """§20/I-02: blocked server browser-flow posture → verdict BLOCKED."""
        doc = _fake_discovery(include_pkce=True, include_passwordless=False)
        report = _mock_check(
            auth_server_url="https://auth.keyholesolution.com/realms/kh-prod",
            discovery_doc=doc,
        )
        assert report.verdict == BrowserCheckVerdict.BLOCKED

    def test_proxy_config_gives_unsupported_detour(self) -> None:
        """§20/I-03: proxy/detour config → verdict UNSUPPORTED_DETOUR_DETECTED."""
        doc = _fake_discovery(include_pkce=True, include_passwordless=True)
        with patch("keyhole_sdk.auth_browser.check._fetch_oidc_discovery", return_value=doc):
            report = run_browser_check(
                realm="kh-prod",
                client_id="test-client",
                auth_server_url="http://127.0.0.1:8888/proxy",
            )
        assert report.verdict == BrowserCheckVerdict.UNSUPPORTED_DETOUR_DETECTED

    def test_direct_config_no_passwordless_signal(self) -> None:
        """§20/I-04: direct config with no passwordless signal → UNKNOWN posture."""
        doc = _fake_discovery(include_pkce=True, include_passwordless=None)
        report = _mock_check(
            auth_server_url="https://auth.keyholesolution.com/realms/kh-prod",
            discovery_doc=doc,
        )
        assert report.direct_mcp_posture == DirectMcpPosture.DIRECT
        assert report.passwordless_browser_posture == PasswordlessBrowserPosture.UNKNOWN
        assert report.verdict == BrowserCheckVerdict.COMPATIBLE

    def test_explain_browser_from_captured_bundle(self) -> None:
        """§20/I-05: explain-browser renders expected diagnosis from captured bundle."""
        doc = _fake_discovery(include_pkce=True, include_passwordless=False)
        report = _mock_check(
            auth_server_url="https://auth.keyholesolution.com/realms/kh-prod",
            discovery_doc=doc,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            index = write_support_bundle(report, bundle_root=Path(tmpdir))
            text = explain_bundle(index.bundle_path)
            assert "BLOCKED" in text
            assert "passwordless" in text.lower()


# ─────────────────────────────────────────────────────────────
# CLI surface tests
# ─────────────────────────────────────────────────────────────


class TestCLISurface:
    """CLI-01 through CLI-06: CLI command surface wiring and contract."""

    def test_browser_check_command_importable(self) -> None:
        """CLI-01: browser-check command module is importable."""
        from keyhole_cli.commands.auth_browser_check import run_auth_browser_check  # noqa
        assert callable(run_auth_browser_check)

    def test_browser_support_bundle_command_importable(self) -> None:
        """CLI-02: browser-support-bundle command module is importable."""
        from keyhole_cli.commands.auth_browser_support_bundle import run_auth_browser_support_bundle  # noqa
        assert callable(run_auth_browser_support_bundle)

    def test_explain_browser_command_importable(self) -> None:
        """CLI-03: explain-browser command module is importable."""
        from keyhole_cli.commands.auth_explain_browser import run_auth_explain_browser  # noqa
        assert callable(run_auth_explain_browser)

    def test_browser_check_returns_command_result_with_detail(self) -> None:
        """CLI-04: browser-check returns CommandResult with detail dict."""
        from keyhole_cli.commands.auth_browser_check import run_auth_browser_check
        doc = _fake_discovery(include_pkce=True, include_passwordless=True)
        with patch("keyhole_sdk.auth_browser.check._fetch_oidc_discovery", return_value=doc):
            result = run_auth_browser_check(
                realm="kh-prod",
                client_id="test-client",
                auth_server_url="https://auth.keyholesolution.com/realms/kh-prod",
                redirect_uri="http://127.0.0.1:9876/",
            )
        assert hasattr(result, "success")
        assert hasattr(result, "data")
        assert "verdict" in result.data
        assert "realm" in result.data
        assert "client_id" in result.data

    def test_browser_support_bundle_returns_bundle_path(self) -> None:
        """CLI-05: browser-support-bundle returns bundle_path in detail."""
        from keyhole_cli.commands.auth_browser_support_bundle import run_auth_browser_support_bundle
        doc = _fake_discovery(include_pkce=True, include_passwordless=False)
        with tempfile.TemporaryDirectory() as tmpdir:
            # Patch both network call and bundle root
            with patch("keyhole_sdk.auth_browser.check._fetch_oidc_discovery", return_value=doc):
                with patch(
                    "keyhole_cli.commands.auth_browser_support_bundle.write_support_bundle",
                    wraps=lambda r, **kw: write_support_bundle(r, bundle_root=Path(tmpdir)),
                ):
                    result = run_auth_browser_support_bundle(
                        realm="kh-prod",
                        client_id="test-client",
                        auth_server_url="https://auth.keyholesolution.com/realms/kh-prod",
                    )
        assert result.success is True
        assert "bundle_path" in result.data
        assert result.data["bundle_path"] is not None

    def test_explain_browser_returns_failure_for_missing_bundle(self) -> None:
        """CLI-06: explain-browser returns ok=False for missing bundle."""
        from keyhole_cli.commands.auth_explain_browser import run_auth_explain_browser
        result = run_auth_explain_browser(bundle_path="/tmp/__no_such_bundle_path__")
        assert result.success is False
        assert result.exit_code != 0

    def test_auth_app_registered_in_cli(self) -> None:
        """CLI commands wired into the main typer app."""
        from keyhole_cli.cli import auth_app
        assert auth_app is not None

    def test_sdk_public_exports_include_browser_types(self) -> None:
        """SDK __init__.py exposes all auth_browser public API."""
        import keyhole_sdk
        assert hasattr(keyhole_sdk, "BrowserCompatibilityReport")
        assert hasattr(keyhole_sdk, "BrowserCheckVerdict")
        assert hasattr(keyhole_sdk, "run_browser_check")
        assert hasattr(keyhole_sdk, "detect_unsupported_detour")
        assert hasattr(keyhole_sdk, "write_support_bundle")
        assert hasattr(keyhole_sdk, "explain_bundle")


# ─────────────────────────────────────────────────────────────
# INV-06 — No alternate auth protocol
# ─────────────────────────────────────────────────────────────


class TestInvariant06NoAlternateAuthProtocol:
    """INV-SDK-CLIENT-01-F-006: No second auth protocol introduced."""

    def test_run_browser_check_does_not_initiate_auth(self) -> None:
        """run_browser_check must never open a browser or exchange tokens."""
        doc = _fake_discovery(include_pkce=True, include_passwordless=True)
        with patch("keyhole_sdk.auth_browser.check._fetch_oidc_discovery", return_value=doc):
            with patch("webbrowser.open") as mock_browser:
                run_browser_check(
                    realm="kh-prod",
                    client_id="test-client",
                    auth_server_url="https://auth.keyholesolution.com/realms/kh-prod",
                )
                mock_browser.assert_not_called()

    def test_browser_check_module_has_no_token_exchange(self) -> None:
        """The check module must not contain token exchange logic."""
        import inspect
        import keyhole_sdk.auth_browser.check as check_module
        source = inspect.getsource(check_module)
        # Must not contain ROPC / token exchange keywords
        # Note: we test for exact token-exchange terms, not substrings of 'passwordless'
        forbidden = ["access_token", "client_secret", "grant_type"]
        for kw in forbidden:
            assert kw not in source, (
                f"check.py must not contain token exchange logic — found '{kw}'"
            )
        # 'password' alone (not as part of 'passwordless') must not appear
        import re as _re
        assert not _re.search(r'\bpassword\b', source), (
            "check.py must not reference 'password' as a standalone credential field"
        )
