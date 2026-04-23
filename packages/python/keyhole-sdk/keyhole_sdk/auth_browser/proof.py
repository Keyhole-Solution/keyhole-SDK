"""Browser auth support bundle — deterministic artifact generation and loading.

Implements §16 and §17 of SDK-CLIENT-01-F: Required Local Artifacts and
Proof / Support Bundle Contract.

Support bundles are tool-owned and repo-neutral.  They are written to
~/.keyhole/auth/browser/<bundle-id>/ (never inside the working repository).

INV-SDK-CLIENT-01-F-005 — Support artifacts are deterministic.
INV-SDK-CLIENT-01-F-006 — No alternate auth protocol is introduced.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from keyhole_sdk.auth_browser.models import (
    BrowserCheckVerdict,
    BrowserCompatibilityReport,
    BrowserFailureClass,
    BrowserSupportBundleIndex,
)

_DEFAULT_BUNDLE_ROOT = Path.home() / ".keyhole" / "auth" / "browser"


def _bundle_id() -> str:
    return f"brwsup_{uuid.uuid4().hex[:12]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _primary_failure_class(report: BrowserCompatibilityReport) -> Optional[BrowserFailureClass]:
    """Return the most significant failure class from a report."""
    if report.failure_classes:
        return report.failure_classes[0]
    return None


def write_support_bundle(
    report: BrowserCompatibilityReport,
    *,
    bundle_root: Optional[Path] = None,
    failure_classification: Optional[BrowserFailureClass] = None,
    raw_oidc_discovery: Optional[Dict[str, Any]] = None,
) -> BrowserSupportBundleIndex:
    """Write a deterministic browser auth support bundle to disk.

    §16 artifact layout::

        ~/.keyhole/auth/browser/<bundle-id>/
            oidc_discovery.json
            auth_server_metadata.json
            browser_check.json
            client_input.json
            redirect_posture.json
            detour_detection.json
            summary.md
            repair.json

    Returns the BrowserSupportBundleIndex for the written bundle.
    """
    root = bundle_root or _DEFAULT_BUNDLE_ROOT
    bid = _bundle_id()
    bundle_dir = root / bid
    bundle_dir.mkdir(parents=True, exist_ok=True)

    now = _now_iso()
    classification = failure_classification or _primary_failure_class(report)

    # ── oidc_discovery.json ────────────────────────────────────
    discovery_doc = raw_oidc_discovery or {}
    _write_json(bundle_dir / "oidc_discovery.json", discovery_doc)

    # ── auth_server_metadata.json ──────────────────────────────
    auth_meta = {
        "issuer": report.issuer,
        "authorization_endpoint": report.authorization_endpoint,
        "token_endpoint": report.token_endpoint,
        "pkce_posture": report.pkce_posture.value,
        "passwordless_browser_posture": report.passwordless_browser_posture.value,
        "discovery_reachable": report.discovery_reachable,
    }
    _write_json(bundle_dir / "auth_server_metadata.json", auth_meta)

    # ── browser_check.json ─────────────────────────────────────
    browser_check = json.loads(report.model_dump_json())
    _write_json(bundle_dir / "browser_check.json", browser_check)

    # ── client_input.json ──────────────────────────────────────
    client_input = {
        "realm": report.realm,
        "client_id": report.client_id,
        "redirect_uri": report.redirect_uri,
        "checked_at": report.checked_at.isoformat(),
    }
    _write_json(bundle_dir / "client_input.json", client_input)

    # ── redirect_posture.json ──────────────────────────────────
    redirect_posture_doc = {
        "redirect_uri": report.redirect_uri,
        "redirect_posture": report.redirect_posture.value,
        "is_loopback": report.redirect_posture.value == "loopback",
    }
    _write_json(bundle_dir / "redirect_posture.json", redirect_posture_doc)

    # ── detour_detection.json ──────────────────────────────────
    detour_doc = {
        "direct_mcp_posture": report.direct_mcp_posture.value,
        "unsupported_detour_detected": report.unsupported_detour_detected,
        "unsupported_paths": ["mcp-proxy", "token injection", "CLI credential shadowing"],
    }
    _write_json(bundle_dir / "detour_detection.json", detour_doc)

    # ── repair.json ────────────────────────────────────────────
    repair_doc = [r.model_dump() for r in report.repair]
    _write_json(bundle_dir / "repair.json", repair_doc)

    # ── summary.md ─────────────────────────────────────────────
    summary = _build_summary_md(report, bid, now, classification)
    (bundle_dir / "summary.md").write_text(summary, encoding="utf-8")

    artifacts = [
        "oidc_discovery.json",
        "auth_server_metadata.json",
        "browser_check.json",
        "client_input.json",
        "redirect_posture.json",
        "detour_detection.json",
        "summary.md",
        "repair.json",
    ]

    index = BrowserSupportBundleIndex(
        bundle_id=bid,
        realm=report.realm,
        client_id=report.client_id,
        redirect_uri=report.redirect_uri,
        verdict=report.verdict,
        classification=classification,
        artifacts=artifacts,
        bundle_path=str(bundle_dir),
    )
    _write_json(bundle_dir / "index.json", json.loads(index.model_dump_json()))

    return index


def load_support_bundle(bundle_path: str) -> Dict[str, Any]:
    """Load all artifacts from a support bundle directory.

    Returns a dict keyed by artifact filename.
    Raises FileNotFoundError if the path does not exist.
    """
    path = Path(bundle_path)
    if not path.is_dir():
        raise FileNotFoundError(f"Bundle directory not found: {bundle_path}")

    result: Dict[str, Any] = {}
    for child in sorted(path.iterdir()):
        if child.suffix == ".json":
            try:
                result[child.name] = json.loads(child.read_text(encoding="utf-8"))
            except Exception:
                result[child.name] = None
        elif child.suffix == ".md":
            result[child.name] = child.read_text(encoding="utf-8")

    return result


# ── Internal helpers ───────────────────────────────────────────


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def _build_summary_md(
    report: BrowserCompatibilityReport,
    bundle_id: str,
    created_at: str,
    classification: Optional[BrowserFailureClass],
) -> str:
    lines = [
        "# Browser Auth Support Bundle",
        "",
        f"**Bundle ID:** `{bundle_id}`",
        f"**Created At:** {created_at}",
        f"**Realm:** {report.realm}",
        f"**Client ID:** {report.client_id}",
        "",
        "## Standard Path",
        "",
        "The supported browser client login path is:",
        "",
        "  OIDC Authorization Code + PKCE → browser auth → redirect callback → token exchange",
        "",
        "## Compatibility Verdict",
        "",
        f"**Verdict:** `{report.verdict.value.upper()}`",
        "",
    ]

    if report.verdict == BrowserCheckVerdict.COMPATIBLE:
        lines += [
            "The client is correctly positioned to use the standard browser PKCE login path.",
            "No unsupported detours were detected.",
            "",
        ]
    else:
        lines += [
            "The client is NOT compatible with the standard browser login path.",
            "",
        ]

    lines += ["## Server / Browser Flow Compatibility", ""]

    if report.passwordless_browser_posture.value == "supported":
        lines.append("Passwordless browser continuation: **SUPPORTED**")
    elif report.passwordless_browser_posture.value == "not_supported":
        lines.append("Passwordless browser continuation: **NOT SUPPORTED**")
    else:
        lines.append("Passwordless browser continuation: **UNKNOWN** (server has not signaled support)")

    lines += ["", "## Unsupported Detour Detection", ""]

    if report.unsupported_detour_detected:
        lines.append(
            "An **unsupported detour** was detected. The auth configuration does not point "
            "directly at the Keyhole auth boundary. Proxy and token-injection paths are "
            "not supported product behavior."
        )
    else:
        lines.append("No unsupported detour detected.")

    lines += ["", "## Passwordless Semantics", ""]
    lines += [
        "Important: the emailed **verification code** is NOT the PKCE/OIDC authorization code.",
        "Both the emailed code and the magic link are convenience paths that complete the same",
        "suspended browser auth session.  Do not confuse them with the OIDC authorization code.",
        "",
    ]

    if report.repair:
        lines += ["## Repair Steps", ""]
        for item in report.repair:
            lines.append(f"{item.step}. {item.instruction}")
        lines.append("")

    lines += [
        "## Next Step",
        "",
        _next_step(report),
        "",
    ]

    return "\n".join(lines)


def _next_step(report: BrowserCompatibilityReport) -> str:
    if report.verdict == BrowserCheckVerdict.COMPATIBLE:
        return "Use the standard OIDC Authorization Code + PKCE browser login path."
    if BrowserFailureClass.PASSWORDLESS_BROWSER_NOT_SUPPORTED in report.failure_classes:
        return "Deploy SDK-SERVER-01-F, then rerun keyhole auth browser-check."
    if BrowserFailureClass.UNSUPPORTED_DETOUR_DETECTED in report.failure_classes:
        return "Remove proxy/injection config, restore direct Keyhole endpoint, then rerun check."
    if BrowserFailureClass.OIDC_DISCOVERY_UNAVAILABLE in report.failure_classes:
        return "Verify realm URL and auth host reachability, then rerun check."
    if BrowserFailureClass.REDIRECT_URI_MISMATCH in report.failure_classes:
        return "Correct the redirect URI to a loopback address, then rerun check."
    return "Review the repair steps above and rerun keyhole auth browser-check."
