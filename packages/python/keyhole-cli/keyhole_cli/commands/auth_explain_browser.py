"""`keyhole auth explain-browser` — explain a captured browser auth bundle.

Implements §11.3 of SDK-CLIENT-01-F.

Loads a previously captured browser auth support bundle and renders
a concrete diagnosis and repair plan in human-readable form.

INV-SDK-CLIENT-01-F-005 — Support artifacts are deterministic.
"""

from __future__ import annotations

from keyhole_cli.result import CommandResult, EXIT_SUCCESS, EXIT_FAILURE
from keyhole_sdk.auth_browser.explain import explain_bundle


def run_auth_explain_browser(
    *,
    bundle_path: str,
) -> CommandResult:
    """Load a browser auth support bundle and render a human-readable explanation.

    §19.7: Given a support bundle, render a concrete diagnosis and repair plan.

    Raises FileNotFoundError if the bundle path does not exist.
    """
    try:
        explanation = explain_bundle(bundle_path)
    except FileNotFoundError as exc:
        return CommandResult(
            command="auth explain-browser",
            success=False,
            exit_code=EXIT_FAILURE,
            summary=f"Bundle not found: {bundle_path}",
            data={"error": str(exc), "bundle_path": bundle_path},
            next_steps=["Verify the bundle path and rerun: keyhole auth explain-browser --bundle <path>"],
        )
    except Exception as exc:
        return CommandResult(
            command="auth explain-browser",
            success=False,
            exit_code=EXIT_FAILURE,
            summary=f"Failed to explain bundle: {exc}",
            data={"error": str(exc), "bundle_path": bundle_path},
            next_steps=["Check bundle integrity and rerun: keyhole auth explain-browser --bundle <path>"],
        )

    return CommandResult(
        command="auth explain-browser",
        success=True,
        exit_code=EXIT_SUCCESS,
        summary=explanation,
        data={"bundle_path": bundle_path},
        next_steps=[],
    )
