"""Browser auth bundle explanation — human-readable rendering.

Implements §11.3 of SDK-CLIENT-01-F: keyhole auth explain-browser.

Loads a previously captured browser auth support bundle and renders
a concrete diagnosis and repair plan in human-readable form.

INV-SDK-CLIENT-01-F-005 — Support artifacts are deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from keyhole_sdk.auth_browser.models import (
    BrowserCheckVerdict,
    BrowserFailureClass,
)
from keyhole_sdk.auth_browser.proof import load_support_bundle


def explain_bundle(bundle_path: str) -> str:
    """Load a support bundle and return a human-readable explanation.

    Distinguishes:
      - auth-boundary failure
      - browser-flow incompatibility
      - redirect/callback mismatch
      - unsupported workaround path
    Renders concrete repair guidance.

    Raises FileNotFoundError if bundle_path does not exist.
    """
    artifacts = load_support_bundle(bundle_path)
    check = artifacts.get("browser_check.json") or {}
    repair_items = artifacts.get("repair.json") or []
    index = artifacts.get("index.json") or {}

    realm = check.get("realm") or index.get("realm") or "(unknown)"
    client_id = check.get("client_id") or index.get("client_id") or "(unknown)"
    verdict_raw = check.get("verdict") or index.get("verdict") or "unknown"
    failure_classes = check.get("failure_classes") or []
    discovery_reachable = check.get("discovery_reachable", None)
    detour_doc = artifacts.get("detour_detection.json") or {}
    detour_detected = detour_doc.get("unsupported_detour_detected", False)
    passwordless_posture = check.get("passwordless_browser_posture", "unknown")
    redirect_posture = check.get("redirect_posture", "not_provided")

    lines = [
        "Browser Auth Explanation",
        "=" * 40,
        f"Realm:     {realm}",
        f"Client ID: {client_id}",
        f"Verdict:   {verdict_raw.upper()}",
        "",
    ]

    # ── Failure classification ────────────────────────────────
    lines.append("Failure Classification")
    lines.append("-" * 30)

    if not failure_classes:
        lines.append("No failures detected — auth flow appears compatible.")
    else:
        for fc in failure_classes:
            lines.append(f"  • {_classify_failure_label(fc)}")
    lines.append("")

    # ── Discovery / auth boundary ─────────────────────────────
    lines.append("Auth Boundary Posture")
    lines.append("-" * 30)
    if discovery_reachable is True:
        lines.append("  OIDC discovery: OK")
    elif discovery_reachable is False:
        lines.append("  OIDC discovery: FAILED — auth host unreachable or realm URL incorrect")
    else:
        lines.append("  OIDC discovery: unknown")

    if detour_detected:
        lines.append("  Direct MCP posture: DETOUR DETECTED — config points at proxy, not Keyhole")
    else:
        lines.append(f"  Direct MCP posture: {detour_doc.get('direct_mcp_posture', 'unknown')}")
    lines.append("")

    # ── Browser flow compatibility ─────────────────────────────
    lines.append("Browser Flow Compatibility")
    lines.append("-" * 30)
    lines.append(f"  Passwordless browser continuation: {passwordless_posture.upper()}")
    lines.append(f"  Redirect URI posture: {redirect_posture}")
    lines.append("")

    # ── Unsupported workaround ────────────────────────────────
    if detour_detected:
        lines.append("Unsupported Workaround Detected")
        lines.append("-" * 30)
        lines.append(
            "  The auth configuration routes through a local proxy or token-injection shim."
        )
        lines.append("  This is NOT a supported product integration path.")
        lines.append(
            "  Restore direct Keyhole endpoint configuration to use the standard PKCE path."
        )
        lines.append("")

    # ── Passwordless semantics note ───────────────────────────
    lines.append("Passwordless Semantics")
    lines.append("-" * 30)
    lines.append(
        "  The emailed verification code is NOT the PKCE/OIDC authorization code."
    )
    lines.append(
        "  Both the email code and the magic link complete the same suspended browser "
        "auth session."
    )
    lines.append("")

    # ── Repair plan ───────────────────────────────────────────
    if repair_items:
        lines.append("Repair Steps")
        lines.append("-" * 30)
        for item in repair_items:
            step = item.get("step", "?")
            instr = item.get("instruction", "")
            lines.append(f"  {step}. {instr}")
        lines.append("")

    # ── Next action ───────────────────────────────────────────
    lines.append("Next Action")
    lines.append("-" * 30)
    lines.append(f"  {_next_action(verdict_raw, failure_classes)}")
    lines.append("")

    return "\n".join(lines)


def _classify_failure_label(fc: str) -> str:
    labels = {
        "passwordless_browser_not_supported": "Browser passwordless continuation not supported by server",
        "oidc_discovery_unavailable": "OIDC discovery unavailable — auth host unreachable",
        "redirect_uri_mismatch": "Redirect URI mismatch — not a valid loopback address",
        "unsupported_detour_detected": "Unsupported detour — auth routed via proxy or injection shim",
        "browser_auth_timeout": "Browser auth timeout",
        "loopback_callback_not_completed": "Loopback callback did not complete",
    }
    return labels.get(fc, fc)


def _next_action(verdict: str, failure_classes: list) -> str:
    if verdict == "compatible":
        return "No action required. Use the standard OIDC Authorization Code + PKCE browser login path."
    if "unsupported_detour_detected" in failure_classes:
        return (
            "Remove proxy/injection config. Restore direct Keyhole endpoint. "
            "Rerun: keyhole auth browser-check"
        )
    if "oidc_discovery_unavailable" in failure_classes:
        return (
            "Verify realm URL and auth host reachability. "
            "Rerun: keyhole auth browser-check"
        )
    if "redirect_uri_mismatch" in failure_classes:
        return (
            "Correct the redirect URI to http://127.0.0.1:<port>/. "
            "Rerun: keyhole auth browser-check --redirect-uri <corrected>"
        )
    if "passwordless_browser_not_supported" in failure_classes:
        return (
            "Deploy SDK-SERVER-01-F. "
            "Rerun: keyhole auth browser-check"
        )
    return "Review the repair steps above. Rerun: keyhole auth browser-check"
