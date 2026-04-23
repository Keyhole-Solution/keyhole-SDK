"""`keyhole auth browser-support-bundle` — browser auth support bundle command.

Implements §11.2 of SDK-CLIENT-01-F.

Generates a deterministic support bundle for browser auth failures.
All artifacts are tool-owned and repo-neutral — written to
~/.keyhole/auth/browser/<bundle-id>/.

INV-SDK-CLIENT-01-F-005 — Support artifacts are deterministic.
INV-SDK-CLIENT-01-F-006 — No alternate auth protocol is introduced.
"""

from __future__ import annotations

from typing import Optional

from keyhole_cli.result import CommandResult, EXIT_SUCCESS, EXIT_FAILURE
from keyhole_sdk.auth_browser.check import run_browser_check
from keyhole_sdk.auth_browser.models import BrowserFailureClass
from keyhole_sdk.auth_browser.proof import write_support_bundle
from keyhole_sdk.config import DEFAULT_AUTH_SERVER


def run_auth_browser_support_bundle(
    *,
    realm: str,
    client_id: str,
    auth_server_url: str = DEFAULT_AUTH_SERVER,
    redirect_uri: Optional[str] = None,
    failure_classification: Optional[str] = None,
) -> CommandResult:
    """Generate a browser auth support bundle and return a structured result.

    §19.6: Given a failed browser login, the client can generate a
    deterministic support bundle.

    The bundle is written to ~/.keyhole/auth/browser/<bundle-id>/ and
    is suitable for ingestion into broader explainability workflows.
    """
    report = run_browser_check(
        realm=realm,
        client_id=client_id,
        auth_server_url=auth_server_url,
        redirect_uri=redirect_uri,
    )

    fc: Optional[BrowserFailureClass] = None
    if failure_classification:
        try:
            fc = BrowserFailureClass(failure_classification)
        except ValueError:
            pass

    index = write_support_bundle(report, failure_classification=fc)

    summary_lines = [
        "Browser Auth Support Bundle Generated",
        "",
        f"Bundle ID:   {index.bundle_id}",
        f"Realm:       {index.realm}",
        f"Client ID:   {index.client_id}",
        f"Verdict:     {index.verdict.value.upper()}",
        f"Bundle Path: {index.bundle_path}",
        "",
        "Artifacts:",
    ]
    for artifact in index.artifacts:
        summary_lines.append(f"  • {artifact}")

    summary_lines += [
        "",
        "To explain this bundle:",
        f"  keyhole auth explain-browser --bundle {index.bundle_path}",
    ]

    return CommandResult(
        command="auth browser-support-bundle",
        success=True,
        exit_code=EXIT_SUCCESS,
        summary="\n".join(summary_lines),
        data={
            "bundle_id": index.bundle_id,
            "realm": index.realm,
            "client_id": index.client_id,
            "redirect_uri": index.redirect_uri,
            "verdict": index.verdict.value,
            "classification": index.classification.value if index.classification else None,
            "artifacts": index.artifacts,
            "bundle_path": index.bundle_path,
        },
        next_steps=[
            f"keyhole auth explain-browser --bundle {index.bundle_path}",
        ],
    )
