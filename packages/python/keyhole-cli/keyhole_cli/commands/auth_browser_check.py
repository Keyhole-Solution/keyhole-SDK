"""`keyhole auth browser-check` — browser OIDC compatibility check command.

Implements §11.1 of SDK-CLIENT-01-F.

Validates whether a standards-based browser OIDC client is correctly
positioned to authenticate against Keyhole using the Authorization Code
+ PKCE flow.

INV-SDK-CLIENT-01-F-001 — Standard browser path is primary.
INV-SDK-CLIENT-01-F-002 — No proxy confusion.
INV-SDK-CLIENT-01-F-003 — Verification code is named correctly.
"""

from __future__ import annotations

from typing import Optional

from keyhole_cli.result import CommandResult, EXIT_SUCCESS, EXIT_FAILURE
from keyhole_sdk.auth_browser.check import run_browser_check
from keyhole_sdk.auth_browser.models import BrowserCheckVerdict
from keyhole_sdk.config import DEFAULT_AUTH_SERVER


def run_auth_browser_check(
    *,
    realm: str,
    client_id: str,
    auth_server_url: str = DEFAULT_AUTH_SERVER,
    redirect_uri: Optional[str] = None,
) -> CommandResult:
    """Run a browser OIDC compatibility check and return a structured result.

    §19.3: Given a browser OIDC client configuration, determine whether the
    environment is compatible, blocked, misconfigured, or using an unsupported
    detour.

    This command does NOT open a browser or attempt authentication.
    It is a pure validation surface.
    """
    report = run_browser_check(
        realm=realm,
        client_id=client_id,
        auth_server_url=auth_server_url,
        redirect_uri=redirect_uri,
    )

    ok = report.verdict == BrowserCheckVerdict.COMPATIBLE
    exit_code = EXIT_SUCCESS if ok else EXIT_FAILURE

    # Build summary text
    summary_lines = [
        "OIDC Browser Compatibility Check",
        f"Realm:     {report.realm}",
        f"Client:    {report.client_id}",
        "",
        f"Authorization Code + PKCE: {_posture_label(report.pkce_posture.value)}",
        f"OIDC discovery:            {'OK' if report.discovery_reachable else 'FAILED'}",
        f"Authorization endpoint:    {_endpoint_label(report.authorization_endpoint)}",
        f"Token endpoint:            {_endpoint_label(report.token_endpoint)}",
        f"Redirect URI posture:      {report.redirect_posture.value}",
        f"Passwordless browser:      {_posture_label(report.passwordless_browser_posture.value)}",
        f"Direct MCP posture:        {report.direct_mcp_posture.value}",
        "",
        f"Verdict: {report.verdict.value.upper()}",
    ]

    if report.verdict == BrowserCheckVerdict.COMPATIBLE:
        summary_lines += [
            "Recommended path: use direct browser PKCE login",
            "Unsupported paths: mcp-proxy, token injection, CLI credential shadowing",
        ]
    elif report.repair:
        summary_lines.append("Repair:")
        for item in report.repair:
            summary_lines.append(f"  {item.step}. {item.instruction}")

    summary = "\n".join(summary_lines)

    return CommandResult(
        command="auth browser-check",
        success=ok,
        exit_code=exit_code,
        summary=summary,
        data={
            "realm": report.realm,
            "client_id": report.client_id,
            "issuer": report.issuer,
            "authorization_endpoint": report.authorization_endpoint,
            "token_endpoint": report.token_endpoint,
            "redirect_uri": report.redirect_uri,
            "pkce_posture": report.pkce_posture.value,
            "passwordless_browser_posture": report.passwordless_browser_posture.value,
            "direct_mcp_posture": report.direct_mcp_posture.value,
            "unsupported_detour_detected": report.unsupported_detour_detected,
            "redirect_posture": report.redirect_posture.value,
            "verdict": report.verdict.value,
            "failure_classes": [fc.value for fc in report.failure_classes],
            "repair": [r.model_dump() for r in report.repair],
        },
        next_steps=[item.instruction for item in report.repair],
    )  # type: ignore[call-arg]


def _posture_label(value: str) -> str:
    return "supported" if value == "supported" else value.upper().replace("_", " ")


def _endpoint_label(url: Optional[str]) -> str:
    return "OK" if url else "unavailable"
