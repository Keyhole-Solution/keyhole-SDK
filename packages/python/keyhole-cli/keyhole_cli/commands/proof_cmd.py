"""`keyhole proof` — proof bundle submission commands.

SDK-CLIENT-PUBLIC-REPAIR-01

Surfaces proof submission through the MCP boundary:
  proof submit --invariant <id> --bundle <path>

Behavior:
  1. Read local proof bundle result for the given invariant
  2. Validate result shape (invariant_id, verdict, checks_total, etc.)
  3. Submit through MCP (run_type=proof.submit)
  4. Receive ACCEPT/REJECT governed verdict
  5. Write local receipt artifact to proof_bundle/receipts/

If the server does not yet support proof.submit, returns a clean
SERVER_BLOCKED verdict, not a crash.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from keyhole_sdk.auth import BearerTokenProvider
from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.run_dispatch.dispatcher import dispatch_run, OutcomeStatus
from keyhole_sdk.run_dispatch.request_builder import build_run_request
from keyhole_sdk.transport.client import GovernedTransport
from keyhole_sdk.transport.idempotency import generate_request_id

from keyhole_cli.result import (
    CommandResult,
    EXIT_FAILURE,
    EXIT_INVALID_INPUT,
    EXIT_RUNTIME_UNAVAILABLE,
    EXIT_SUCCESS,
)
from keyhole_sdk.config import DEFAULT_BASE_URL


# ──────────────────────────────────────────────────────────────
# Required fields for a valid proof bundle result
# ──────────────────────────────────────────────────────────────

_REQUIRED_RESULT_FIELDS = (
    "invariant_id",
    "verdict",
    "checks_total",
    "checks_passed",
    "checks",
)


# ──────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────

def _load_result(bundle_path: Path, invariant_id: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Locate and load the proof result JSON for an invariant.

    Returns (result_dict, error_message). On success, error_message is None.
    Handles both UTF-8 and UTF-16 encoded files.
    """
    # Normalise invariant_id to a slug for directory lookup
    inv_slug = invariant_id.lower().replace("_", "-").replace(" ", "-")

    # Try: <bundle>/core/<inv-slug>/<inv-slug>-result.json
    candidate = bundle_path / "core" / inv_slug / f"{inv_slug}-result.json"
    if not candidate.exists():
        # Fallback: any *-result.json in core/<inv_slug>/
        inv_dir = bundle_path / "core" / inv_slug
        if inv_dir.is_dir():
            results = list(inv_dir.glob("*-result.json"))
            if results:
                candidate = results[0]

    if not candidate.exists():
        return None, (
            f"No proof result found for invariant '{invariant_id}' "
            f"under {bundle_path / 'core'}. "
            f"Expected: {bundle_path}/core/{inv_slug}/{inv_slug}-result.json"
        )

    # Try UTF-8 first, then UTF-16
    raw = candidate.read_bytes()
    for enc in ("utf-8-sig", "utf-16", "utf-8"):
        try:
            text = raw.decode(enc)
            data = json.loads(text)
            return data, None
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue

    return None, f"Could not decode {candidate} — expected UTF-8 or UTF-16 JSON."


def _validate_result(result: Dict[str, Any], invariant_id: str) -> Optional[str]:
    """Validate proof result shape. Returns error string or None."""
    for field in _REQUIRED_RESULT_FIELDS:
        if field not in result:
            return f"Proof result missing required field: '{field}'"

    result_inv = result.get("invariant_id", "")
    if result_inv and result_inv != invariant_id:
        return (
            f"Proof result invariant_id '{result_inv}' does not match "
            f"requested invariant '{invariant_id}'."
        )

    verdict = result.get("verdict", "")
    if verdict not in ("ACCEPT", "REJECT"):
        return f"Proof result verdict must be ACCEPT or REJECT, got: '{verdict}'"

    return None


def _sha256_result(result: Dict[str, Any]) -> str:
    canonical = json.dumps(result, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_receipt(
    bundle_path: Path,
    invariant_id: str,
    governed_verdict: str,
    outcome_data: Dict[str, Any],
    submission_id: str,
) -> Path:
    """Write a local receipt artifact after a successful submission."""
    receipts_dir = bundle_path / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    inv_slug = invariant_id.lower().replace("_", "-").replace(" ", "-")
    receipt_path = receipts_dir / f"{inv_slug}-receipt.json"
    receipt = {
        "invariant_id": invariant_id,
        "governed_verdict": governed_verdict,
        "submission_id": submission_id,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "outcome": outcome_data,
    }
    receipt_path.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return receipt_path


# ──────────────────────────────────────────────────────────────
# keyhole proof submit
# ──────────────────────────────────────────────────────────────

def run_proof_submit(
    *,
    invariant: str,
    bundle: str = "proof_bundle",
    repo_dir: str = ".",
    mcp_url: str = DEFAULT_BASE_URL,
    keyhole_home: str = "",
) -> CommandResult:
    """Execute ``keyhole proof submit``.

    Reads the local proof bundle for the given invariant, validates the
    result shape, submits through run_type=proof.submit, and writes a
    local receipt artifact on success.

    Usage:
      keyhole proof submit --invariant MY-FIRST-APP-INV-01
      keyhole proof submit --invariant MY-FIRST-APP-INV-01 --bundle ./proof_bundle
    """
    command_label = "keyhole proof submit"

    if not invariant or not invariant.strip():
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary="--invariant is required.",
            next_steps=["keyhole proof submit --invariant <INVARIANT-ID> [--bundle <path>]"],
        )

    invariant = invariant.strip()
    repo_path = Path(repo_dir).resolve()
    bundle_path = (repo_path / bundle).resolve()

    if not bundle_path.is_dir():
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary=f"Proof bundle directory not found: {bundle_path}",
            next_steps=[
                "Run your invariant gate first: python tests/invariants/inv_greet.py",
                f"Ensure the bundle is at: {bundle_path}",
                "Or specify: --bundle <path>",
            ],
        )

    # ── Load and validate result ──
    result, load_error = _load_result(bundle_path, invariant)
    if load_error:
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary=load_error,
            next_steps=[
                "Run your invariant gate to generate the result JSON.",
                "Check the bundle directory structure matches: core/<inv-id>/<inv-id>-result.json",
            ],
        )

    validate_error = _validate_result(result, invariant)  # type: ignore[arg-type]
    if validate_error:
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary=f"Proof result validation failed: {validate_error}",
            next_steps=["Fix the proof result and rerun."],
        )

    # ── Auth check ──
    store_dir = Path(keyhole_home) if keyhole_home else None
    cred_store = CredentialStore(store_dir=store_dir)
    session = cred_store.load()
    if not session or not session.access_token:
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_RUNTIME_UNAVAILABLE,
            summary="Not authenticated. Run: keyhole login",
            next_steps=["keyhole login", f"Then: {command_label}"],
        )

    token = session.access_token
    auth_provider = BearerTokenProvider(token=token) if token else None
    transport = GovernedTransport(base_url=mcp_url, auth_provider=auth_provider)

    result_hash = _sha256_result(result)  # type: ignore[arg-type]
    correlation_id = generate_request_id()
    request = build_run_request(
        run_type="proof.submit",
        repo_name=repo_path.name,
        context_ref=None,
        input_data={
            "invariant_id": invariant,
            "result": result,
            "result_hash": result_hash,
        },
        correlation_id=correlation_id,
    )

    try:
        outcome = dispatch_run(transport=transport, request=request)
    finally:
        transport.close()

    if outcome.status in (OutcomeStatus.SUCCESS, OutcomeStatus.ACCEPTED):
        governed_verdict = (
            outcome.response_data.get("verdict", "ACCEPTED")
            if outcome.status == OutcomeStatus.SUCCESS
            else "ACCEPTED"
        )
        run_id = outcome.run_id or correlation_id
        receipt_path = _write_receipt(
            bundle_path=bundle_path,
            invariant_id=invariant,
            governed_verdict=governed_verdict,
            outcome_data=outcome.response_data,
            submission_id=run_id,
        )
        return CommandResult(
            command=command_label,
            success=True,
            exit_code=EXIT_SUCCESS,
            summary=f"Proof submitted. governed_verdict={governed_verdict} run_id={run_id}",
            data={
                "governed_verdict": governed_verdict,
                "run_id": run_id,
                "invariant_id": invariant,
                "result_hash": result_hash,
                "receipt_written": str(receipt_path),
            },
        )

    reason = outcome.reason or "Proof submission rejected by server."
    error_class = outcome.error_class or "unknown"
    next_steps: list[str] = outcome.repair_guidance or []

    if error_class in ("NOT_IMPLEMENTED", "METHOD_NOT_ALLOWED", "BLOCKED"):
        next_steps = [
            "The proof.submit run type may not yet be enabled for your workspace.",
            "Contact your Keyhole operator to enable proof submission.",
            "Check: keyhole context compile — to confirm workspace binding status.",
        ] + next_steps
    elif governed_verdict := outcome.response_data.get("verdict", ""):
        if governed_verdict == "REJECT":
            next_steps = [
                "The server rejected the proof. Review invariant gate output.",
                "Fix failing checks and re-run the gate to regenerate the result.",
                "Then resubmit: keyhole proof submit --invariant " + invariant,
            ] + next_steps

    return CommandResult(
        command=command_label,
        success=False,
        exit_code=EXIT_FAILURE,
        summary=reason,
        data={
            "error_class": error_class,
            "run_type": "proof.submit",
            "http_status": outcome.http_status,
            "invariant_id": invariant,
        },
        next_steps=next_steps,
    )
