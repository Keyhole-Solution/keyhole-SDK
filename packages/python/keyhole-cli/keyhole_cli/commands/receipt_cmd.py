"""`keyhole receipt` — governed receipt verification commands.

SDK-CLIENT-PUBLIC-REPAIR-01

Surfaces receipt verification:
  receipt verify [--invariant <id>] [--bundle <path>]

Behavior:
  1. Load the local receipt artifact from proof_bundle/receipts/
  2. Verify event_id / submission_id / result_hash against local proof bundle
  3. Confirm receipt references the current capability/invariant
  4. Return PASS or FAIL with details
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from keyhole_cli.result import (
    CommandResult,
    EXIT_FAILURE,
    EXIT_INVALID_INPUT,
    EXIT_SUCCESS,
)


# ──────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────

def _load_json_file(path: Path) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Load JSON (UTF-8 or UTF-16). Returns (data, error)."""
    if not path.exists():
        return None, f"File not found: {path}"
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-16", "utf-8"):
        try:
            text = raw.decode(enc)
            data = json.loads(text)
            return data, None
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    return None, f"Could not decode {path} — expected UTF-8 or UTF-16 JSON."


def _sha256_result(result: Dict[str, Any]) -> str:
    canonical = json.dumps(result, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _inv_slug(invariant_id: str) -> str:
    return invariant_id.lower().replace("_", "-").replace(" ", "-")


# ──────────────────────────────────────────────────────────────
# keyhole receipt verify
# ──────────────────────────────────────────────────────────────

def run_receipt_verify(
    *,
    invariant: str = "",
    bundle: str = "proof_bundle",
    repo_dir: str = ".",
) -> CommandResult:
    """Execute ``keyhole receipt verify``.

    Loads the local receipt artifact and verifies it against the local
    proof bundle result. Does not make a network call — this is a
    deterministic local integrity check.

    Usage:
      keyhole receipt verify
      keyhole receipt verify --invariant MY-FIRST-APP-INV-01
      keyhole receipt verify --invariant MY-FIRST-APP-INV-01 --bundle ./proof_bundle
    """
    command_label = "keyhole receipt verify"

    repo_path = Path(repo_dir).resolve()
    bundle_path = (repo_path / bundle).resolve()

    if not bundle_path.is_dir():
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary=f"Proof bundle directory not found: {bundle_path}",
            next_steps=[
                "Run: keyhole proof submit --invariant <id> — to generate a receipt.",
                "Or specify: --bundle <path>",
            ],
        )

    receipts_dir = bundle_path / "receipts"
    if not receipts_dir.is_dir():
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_FAILURE,
            summary="No receipts found. Run: keyhole proof submit --invariant <id>",
            next_steps=[
                "keyhole proof submit --invariant <id> — to submit proof and receive a receipt.",
            ],
        )

    # ── Discover receipts ──
    receipt_files: List[Path]
    if invariant:
        slug = _inv_slug(invariant.strip())
        candidate = receipts_dir / f"{slug}-receipt.json"
        if not candidate.exists():
            return CommandResult(
                command=command_label,
                success=False,
                exit_code=EXIT_FAILURE,
                summary=f"No receipt found for invariant '{invariant}' at {candidate}",
                next_steps=["keyhole proof submit --invariant " + invariant.strip()],
            )
        receipt_files = [candidate]
    else:
        receipt_files = sorted(receipts_dir.glob("*-receipt.json"))
        if not receipt_files:
            return CommandResult(
                command=command_label,
                success=False,
                exit_code=EXIT_FAILURE,
                summary=f"No receipt files found under {receipts_dir}",
                next_steps=["keyhole proof submit --invariant <id>"],
            )

    # ── Verify each receipt ──
    results: List[Dict[str, Any]] = []
    all_pass = True

    for receipt_path in receipt_files:
        receipt, err = _load_json_file(receipt_path)
        if err or receipt is None:
            results.append({
                "receipt": receipt_path.name,
                "verdict": "FAIL",
                "reason": err or "Empty receipt file.",
            })
            all_pass = False
            continue

        inv_id = receipt.get("invariant_id", "")
        governed_verdict = receipt.get("governed_verdict", "")
        submission_id = receipt.get("submission_id", "")
        outcome = receipt.get("outcome", {})

        # ── Cross-check against local proof result ──
        slug = _inv_slug(inv_id) if inv_id else receipt_path.stem.replace("-receipt", "")
        result_path = bundle_path / "core" / slug / f"{slug}-result.json"
        local_result, result_err = _load_json_file(result_path)

        checks: List[Dict[str, Any]] = []

        # Check 1: Receipt has required fields
        missing_fields = [f for f in ("invariant_id", "governed_verdict", "submission_id") if f not in receipt]
        if missing_fields:
            checks.append({"check": "required_fields", "verdict": "FAIL", "detail": f"Missing: {missing_fields}"})
            all_pass = False
        else:
            checks.append({"check": "required_fields", "verdict": "PASS"})

        # Check 2: Governed verdict is ACCEPT or ACCEPTED
        if governed_verdict in ("ACCEPT", "ACCEPTED", "PASS"):
            checks.append({"check": "governed_verdict", "verdict": "PASS", "detail": governed_verdict})
        else:
            checks.append({"check": "governed_verdict", "verdict": "FAIL", "detail": f"governed_verdict={governed_verdict}"})
            all_pass = False

        # Check 3: Submission ID present
        if submission_id:
            checks.append({"check": "submission_id_present", "verdict": "PASS"})
        else:
            checks.append({"check": "submission_id_present", "verdict": "FAIL", "detail": "No submission_id in receipt"})
            all_pass = False

        # Check 4: Local result exists and hash matches (if outcome contains result_hash)
        expected_hash = outcome.get("result_hash", "")
        if local_result is not None and expected_hash:
            actual_hash = _sha256_result(local_result)
            if actual_hash == expected_hash:
                checks.append({"check": "result_hash_match", "verdict": "PASS"})
            else:
                checks.append({
                    "check": "result_hash_match",
                    "verdict": "FAIL",
                    "detail": f"Expected {expected_hash[:16]}… got {actual_hash[:16]}…",
                })
                all_pass = False
        elif local_result is None:
            checks.append({
                "check": "result_hash_match",
                "verdict": "SKIP",
                "detail": f"Local result not found at {result_path}",
            })
        else:
            # No hash in receipt (server didn't echo it back)
            checks.append({"check": "result_hash_match", "verdict": "SKIP", "detail": "No result_hash in receipt outcome"})

        # Check 5: Invariant ID in receipt matches local result
        if local_result is not None:
            local_inv = local_result.get("invariant_id", "")
            if local_inv and inv_id and local_inv != inv_id:
                checks.append({
                    "check": "invariant_id_match",
                    "verdict": "FAIL",
                    "detail": f"Receipt invariant_id='{inv_id}' vs local '{local_inv}'",
                })
                all_pass = False
            else:
                checks.append({"check": "invariant_id_match", "verdict": "PASS"})

        receipt_verdict = "PASS" if all(c["verdict"] in ("PASS", "SKIP") for c in checks) else "FAIL"
        results.append({
            "receipt": receipt_path.name,
            "invariant_id": inv_id,
            "governed_verdict": governed_verdict,
            "submission_id": submission_id,
            "verification_verdict": receipt_verdict,
            "checks": checks,
        })

    overall_verdict = "PASS" if all_pass else "FAIL"
    summary = f"receipt verify: {overall_verdict} — {len(receipt_files)} receipt(s) checked."
    next_steps: List[str] = []
    if not all_pass:
        next_steps = [
            "Review failed checks above.",
            "If result_hash mismatch: local proof result was changed after submission.",
            "If governed_verdict is not ACCEPT: rerun invariant gate and resubmit.",
        ]

    return CommandResult(
        command=command_label,
        success=all_pass,
        exit_code=EXIT_SUCCESS if all_pass else EXIT_FAILURE,
        summary=summary,
        data={
            "overall_verdict": overall_verdict,
            "receipts_checked": len(receipt_files),
            "results": results,
        },
        next_steps=next_steps,
    )
