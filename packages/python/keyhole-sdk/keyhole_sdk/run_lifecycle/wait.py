"""Run wait — SDK-CLIENT-17 §5.3/§11.

Polls until terminal state or explicit client interruption.
Waiting does not change the run — it only observes.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from keyhole_sdk.run_lifecycle.models import (
    RunStatus,
    RunWaitResult,
)
from keyhole_sdk.run_lifecycle.status import fetch_run_status


# Default poll interval and max-poll limits
DEFAULT_POLL_INTERVAL = 3.0  # seconds
DEFAULT_MAX_POLLS = 200      # ~10 minutes at 3s intervals


def wait_for_terminal(
    *,
    transport: Any,  # GovernedTransport
    run_id: str,
    repo_name: str = "",
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    max_polls: int = DEFAULT_MAX_POLLS,
    on_poll: Optional[Any] = None,  # callable(RunStatusResult, int) -> bool; return True to stop
) -> RunWaitResult:
    """Poll the run until terminal state, timeout, or on_poll returns True.

    §11: Waiting does not change the run. It only observes.
    The client must stop on terminal result and render honestly.
    """
    start = time.monotonic()
    polls = 0

    while polls < max_polls:
        polls += 1
        status_result = fetch_run_status(
            transport=transport,
            run_id=run_id,
            repo_name=repo_name,
        )

        if not status_result.success:
            # §17.2: observation failure ≠ execution failure
            return RunWaitResult(
                success=False,
                run_id=run_id,
                polls=polls,
                elapsed_seconds=time.monotonic() - start,
                error_class=status_result.error_class or "observation_failed",
                reason=f"Status retrieval failed: {status_result.reason}",
                repair_guidance=status_result.repair_guidance or [
                    f"Retry: keyhole runs status {run_id}",
                    "Observation failure does not mean execution failed.",
                ],
            )

        # Callback for progress rendering
        if on_poll is not None:
            try:
                if on_poll(status_result, polls):
                    return RunWaitResult(
                        success=True,
                        run_id=run_id,
                        terminal_status=status_result.status,
                        polls=polls,
                        elapsed_seconds=time.monotonic() - start,
                        final_data=status_result.response_data,
                        interrupted=True,
                    )
            except KeyboardInterrupt:
                return RunWaitResult(
                    success=True,
                    run_id=run_id,
                    terminal_status=status_result.status,
                    polls=polls,
                    elapsed_seconds=time.monotonic() - start,
                    final_data=status_result.response_data,
                    interrupted=True,
                )

        # Terminal state reached
        if status_result.status.is_terminal:
            return RunWaitResult(
                success=True,
                run_id=run_id,
                terminal_status=status_result.status,
                polls=polls,
                elapsed_seconds=time.monotonic() - start,
                final_data=status_result.response_data,
            )

        # Not terminal — wait and poll again
        time.sleep(poll_interval)

    # Max polls reached before terminal
    return RunWaitResult(
        success=False,
        run_id=run_id,
        terminal_status=RunStatus.UNKNOWN,
        polls=polls,
        elapsed_seconds=time.monotonic() - start,
        error_class="wait_timeout",
        reason=f"Run did not reach terminal state after {polls} polls.",
        repair_guidance=[
            f"Try again: keyhole runs wait {run_id}",
            f"Check status: keyhole runs status {run_id}",
            "The run may still be in progress.",
        ],
    )
