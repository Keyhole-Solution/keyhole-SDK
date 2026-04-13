"""Run lifecycle — SDK-CLIENT-17.

Async run tracking, polling, wait, tail, resume, and durable run UX.

Public surface:

  Models:
    RunRecord         — local run record for continuity
    RunStatus         — classified run status
    TerminalState     — terminal state enum

  Operations:
    fetch_run_status  — retrieve current run state
    wait_for_terminal — poll until terminal or interrupted
    tail_run          — follow observations chronologically
    resume_run        — reconnect to an existing run identity

  Proof:
    emit_run_lifecycle_proof — persist lifecycle proof artifacts

  Repair:
    map_run_lifecycle_repair — error → guidance

  Records:
    LocalRunRecordStore      — persist/retrieve local run records
"""

from keyhole_sdk.run_lifecycle.record import (
    LocalRunRecordStore,
    RunRecord,
)
from keyhole_sdk.run_lifecycle.models import (
    RunStatus,
    TerminalState,
    RunStatusResult,
    RunWaitResult,
    RunTailEntry,
    RunTailResult,
    RunResumeResult,
)
from keyhole_sdk.run_lifecycle.status import fetch_run_status
from keyhole_sdk.run_lifecycle.wait import wait_for_terminal
from keyhole_sdk.run_lifecycle.tail import tail_run
from keyhole_sdk.run_lifecycle.resume import resume_run
from keyhole_sdk.run_lifecycle.proof import emit_run_lifecycle_proof
from keyhole_sdk.run_lifecycle.repair import map_run_lifecycle_repair

__all__ = [
    "RunRecord",
    "LocalRunRecordStore",
    "RunStatus",
    "TerminalState",
    "RunStatusResult",
    "RunWaitResult",
    "RunTailEntry",
    "RunTailResult",
    "RunResumeResult",
    "fetch_run_status",
    "wait_for_terminal",
    "tail_run",
    "resume_run",
    "emit_run_lifecycle_proof",
    "map_run_lifecycle_repair",
]
