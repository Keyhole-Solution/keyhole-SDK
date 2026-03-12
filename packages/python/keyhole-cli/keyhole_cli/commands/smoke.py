"""`keyhole smoke` — deterministic end-to-end first-success verification."""

from __future__ import annotations

from typing import Any, Dict

from keyhole_cli.commands.doctor import run_doctor
from keyhole_cli.commands.runtime import run_status, _runtime_reachable, _query_identity, _filter_private
from keyhole_cli.result import (
    CommandResult,
    EXIT_SUCCESS,
    EXIT_FAILURE,
    EXIT_UNSUPPORTED,
    EXIT_RUNTIME_UNAVAILABLE,
)


def run_smoke(*, endpoint: str = "http://localhost:8080") -> CommandResult:
    """Execute the canonical first-success end-to-end path.

    Smoke is successful only if:
    1. the environment is supported,
    2. the runtime is reachable,
    3. the runtime identity surface is truthful,
    4. the minimal declared public action succeeds,
    5. all outputs are deterministic and parseable.
    """
    # Step 1 — Doctor (environment check)
    doctor = run_doctor()
    doctor_ok = doctor.success

    if not doctor_ok:
        return CommandResult(
            command="smoke",
            success=False,
            exit_code=EXIT_UNSUPPORTED,
            data={
                "first_success": False,
                "profile": doctor.data.get("detected_profile", "unknown"),
                "doctor_result": "fail",
                "runtime_result": "skipped",
                "identity_result": "skipped",
                "smoke_action_result": "skipped",
            },
            summary="Environment is not supported — cannot prove first success.",
            warnings=doctor.warnings,
            next_steps=doctor.next_steps,
        )

    profile = doctor.data.get("detected_profile", "unknown")

    # Step 2 — Runtime reachability
    reachable = _runtime_reachable(endpoint)
    if not reachable:
        return CommandResult(
            command="smoke",
            success=False,
            exit_code=EXIT_RUNTIME_UNAVAILABLE,
            data={
                "first_success": False,
                "profile": profile,
                "doctor_result": "pass",
                "runtime_result": "unreachable",
                "identity_result": "skipped",
                "smoke_action_result": "skipped",
            },
            summary="Runtime is not reachable.",
            next_steps=["Run 'keyhole runtime start' first."],
        )

    # Step 3 — Identity surface
    identity = _query_identity(endpoint)
    identity_ok = identity is not None
    identity_data: Dict[str, Any] = {}
    if identity_ok:
        identity_data = _filter_private(identity)  # type: ignore[arg-type]

    # Step 4 — Minimal smoke action: hit /healthz as the simplest possible
    # public action that proves the runtime surface works.
    import requests as _req

    smoke_action_ok = False
    try:
        resp = _req.get(f"{endpoint}/healthz", timeout=5)
        smoke_action_ok = resp.status_code == 200
    except (OSError, _req.RequestException):
        smoke_action_ok = False

    # Step 5 — Verdict
    first_success = doctor_ok and reachable and identity_ok and smoke_action_ok

    return CommandResult(
        command="smoke",
        success=first_success,
        exit_code=EXIT_SUCCESS if first_success else EXIT_FAILURE,
        data={
            "first_success": first_success,
            "profile": profile,
            "doctor_result": "pass" if doctor_ok else "fail",
            "runtime_result": "reachable" if reachable else "unreachable",
            "identity_result": "pass" if identity_ok else "fail",
            "smoke_action_result": "pass" if smoke_action_ok else "fail",
            "runtime_identity": identity_data if identity_ok else {},
        },
        summary=(
            "First success verified."
            if first_success
            else "First success verification failed."
        ),
        next_steps=(
            ["Your environment is fully working. Explore 'keyhole runtime realize'."]
            if first_success
            else ["Check failing steps above and re-run 'keyhole smoke'."]
        ),
    )
