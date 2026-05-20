"""`keyhole capability create` / `keyhole capability validate` — SDK-CLIENT-03.

Client-side capability namespace enforcement.

§6.1: Creation helper — validate parts, assemble canonical name, optionally
      write to governed local artifact.
§6.2: Namespace validator — reusable, advisory-by-default, deterministic.
§9.2: Foreign-repo behavior — advisory validation, out-of-tree proof only.
§13: Deterministic — same input → same canonical name and same errors.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.capability import (
    CapabilityNameError,
    CapabilityValidationResult,
    create_capability_name,
    emit_namespace_proof,
    normalize_capability_parts,
    validate_capability_name,
)
from keyhole_sdk.run_dispatch.dispatcher import dispatch_run, OutcomeStatus
from keyhole_sdk.run_dispatch.request_builder import build_run_request
from keyhole_sdk.transport.client import GovernedTransport
from keyhole_sdk.transport.idempotency import generate_request_id

from keyhole_cli.result import (
    EXIT_FAILURE,
    EXIT_INVALID_INPUT,
    EXIT_RUNTIME_UNAVAILABLE,
    EXIT_SUCCESS,
    CommandResult,
)
from keyhole_sdk.config import DEFAULT_BASE_URL


def _resolve_state_dir(state_dir: str, keyhole_home: str = "") -> Path:
    """Resolve the tool-owned state directory for proof artifacts.

    Prefers explicit ``state_dir``, then ``keyhole_home``, then a
    well-known default under $HOME/.keyhole or a temp dir.
    """
    if state_dir:
        return Path(state_dir)
    if keyhole_home:
        return Path(keyhole_home) / "state"
    env_home = os.environ.get("KEYHOLE_STATE_DIR", "")
    if env_home:
        return Path(env_home)
    return Path.home() / ".keyhole" / "state"


# ──────────────────────────────────────────────────────────────
# keyhole capability create
# ──────────────────────────────────────────────────────────────

def run_capability_create(
    *,
    domain: str,
    category: str,
    name: str,
    major: int | str = 1,
    repo_dir: str = ".",
    write: bool = False,
    state_dir: str = "",
    mcp_url: str = DEFAULT_BASE_URL,
    keyhole_home: str = "",
) -> CommandResult:
    """Execute ``keyhole capability create``.

    §6.1: Validate parts, normalize safe input, assemble canonical name.
    §9.3: Validation is universal; in-repo mutation is conditional on write mode.
    §13: Deterministic — same input → same name.
    """
    command_label = "keyhole capability create"

    # ── Validate that required parts are non-empty ──────────────────────────
    if not domain or not domain.strip():
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary="--domain is required.",
            next_steps=["Provide a lowercase domain, e.g. --domain payment"],
        )
    if not category or not category.strip():
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary="--category is required.",
            next_steps=["Provide a lowercase category, e.g. --category stripe"],
        )
    if not name or not name.strip():
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary="--name is required.",
            next_steps=["Provide a lowercase capability name, e.g. --name integration"],
        )

    # ── §8.4 Safe normalization ─────────────────────────────────────────────
    try:
        d, c, n, m = normalize_capability_parts(domain, category, name, major)
    except ValueError as exc:
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary=str(exc),
            next_steps=["--major must be a positive integer, e.g. --major 1"],
        )

    # ── Assemble and validate canonical name ────────────────────────────────
    try:
        canonical = create_capability_name(d, c, n, m)
    except CapabilityNameError as exc:
        validation_result = validate_capability_name(f"{d}.{c}.{n}.v{m}")
        resolved_state = _resolve_state_dir(state_dir, keyhole_home)
        try:
            emit_namespace_proof(
                resolved_state,
                validation_result,
                session_ref=f"create-{d}-{c}-{n}-v{m}",
                write_mode=False,
            )
        except Exception:  # noqa: BLE001 — proof emission is best-effort
            pass
        repair = [
            f"Reason(s): {', '.join(r.value for r in exc.reject_reasons)}",
            "Format:    <domain>.<category>.<capability>.v<major>",
            "Example:   payment.stripe.integration.v1",
        ]
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary=f"Invalid capability name: {exc}",
            next_steps=repair,
        )

    # ── Validation result for proof ─────────────────────────────────────────
    validation_result = validate_capability_name(canonical)
    resolved_state = _resolve_state_dir(state_dir, keyhole_home)

    # ── Optional write mode §6.1, §9.1 ─────────────────────────────────────
    artifact_path = ""
    written = False
    warning_msgs: list[str] = []

    if write:
        write_result = _attempt_artifact_write(
            canonical=canonical,
            repo_dir=repo_dir,
        )
        artifact_path = write_result.get("artifact_path", "")
        written = write_result.get("written", False)
        if write_result.get("warning"):
            warning_msgs.append(write_result["warning"])

    # ── Emit proof ──────────────────────────────────────────────────────────
    try:
        emit_namespace_proof(
            resolved_state,
            validation_result,
            session_ref=f"create-{canonical}",
            write_mode=write and written,
            artifact_path=artifact_path,
        )
    except Exception:  # noqa: BLE001 — proof emission is best-effort
        pass

    # ── Assemble result ─────────────────────────────────────────────────────
    data: dict = {
        "capability": canonical,
        "domain": d,
        "category": c,
        "name": n,
        "major": m,
        "write_mode": write,
        "written": written,
    }
    if artifact_path:
        data["artifact_path"] = artifact_path

    summary_parts = [f"Created: {canonical}"]
    if write and written:
        summary_parts.append(f"Written to: {artifact_path}")
    elif write and not written:
        summary_parts.append("Advisory mode — no in-repo artifact was written.")

    return CommandResult(
        command=command_label,
        success=True,
        exit_code=EXIT_SUCCESS,
        summary=" | ".join(summary_parts),
        data=data,
        warnings=warning_msgs,
    )


# ──────────────────────────────────────────────────────────────
# keyhole capability validate
# ──────────────────────────────────────────────────────────────

def run_capability_validate(
    *,
    capability_name: str,
    repo_dir: str = ".",
    state_dir: str = "",
    keyhole_home: str = "",
) -> CommandResult:
    """Execute ``keyhole capability validate <name>``.

    §6.2: Reusable namespace validator.  Advisory by default — pass or fail.
    §12.2: Validation messages must teach the expected format.
    §12.4: Foreign-repo success only means namespace-valid, not registered.
    §13: Deterministic — same input → same result.
    """
    command_label = "keyhole capability validate"

    if not capability_name or not capability_name.strip():
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary="No capability name provided.",
            next_steps=[
                "Provide a capability name, e.g. keyhole capability validate payment.stripe.integration.v1",
            ],
        )

    result: CapabilityValidationResult = validate_capability_name(capability_name.strip())

    resolved_state = _resolve_state_dir(state_dir, keyhole_home)
    safe_ref = capability_name.strip().replace(".", "-").replace("/", "_")
    try:
        emit_namespace_proof(
            resolved_state,
            result,
            session_ref=f"validate-{safe_ref}",
            write_mode=False,
        )
    except Exception:  # noqa: BLE001 — proof emission is best-effort
        pass

    if result.valid:
        return CommandResult(
            command=command_label,
            success=True,
            exit_code=EXIT_SUCCESS,
            summary=result.message,
            data=result.to_dict(),
        )

    repair = [
        "Format:   <domain>.<category>.<capability>.v<major>",
        "Example:  payment.stripe.integration.v1",
    ]
    for r in result.reject_reasons:
        repair.append(f"Issue:    {r.value}")
    if result.suggestion:
        repair.append(f"Suggestion: {result.suggestion}")

    return CommandResult(
        command=command_label,
        success=False,
        exit_code=EXIT_INVALID_INPUT,
        summary=result.message,
        data=result.to_dict(),
        next_steps=repair,
    )


# ──────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────

def _attempt_artifact_write(
    *,
    canonical: str,
    repo_dir: str,
) -> dict:
    """Attempt to write the capability name into a governed local artifact.

    §9.1: Only allowed for Keyhole-native repos.
    §10: Fail safely if the target artifact is missing or malformed.
    Returns a dict with keys: artifact_path, written, warning.
    """
    target = Path(repo_dir).resolve()
    if not target.is_dir():
        return {
            "written": False,
            "warning": f"Repo path does not exist or is not a directory: {target}",
        }

    # Lawful insertion candidates §10
    for candidate_name in ("capability_passport.yaml", "governance_contract.yaml"):
        candidate = target / candidate_name
        if candidate.exists():
            try:
                content = candidate.read_text(encoding="utf-8")
                # Duplicate suppression §10
                if canonical in content:
                    return {
                        "written": False,
                        "warning": (
                            f"Capability '{canonical}' is already declared in {candidate.name}. "
                            "No duplicate was inserted."
                        ),
                        "artifact_path": str(candidate),
                    }
                # Append under a 'capabilities:' section or at end
                if "capabilities:" in content:
                    new_content = content.rstrip() + f"\n  - {canonical}\n"
                else:
                    new_content = content.rstrip() + f"\ncapabilities:\n  - {canonical}\n"
                candidate.write_text(new_content, encoding="utf-8")
                return {
                    "written": True,
                    "artifact_path": str(candidate),
                }
            except OSError as exc:
                return {
                    "written": False,
                    "warning": f"Could not write to {candidate.name}: {exc}",
                }

    # No native artifact found → advisory mode for this repo
    return {
        "written": False,
        "warning": (
            "No governed artifact found (capability_passport.yaml or governance_contract.yaml). "
            "Advisory mode — no in-repo write occurred. §9.2"
        ),
    }


# ──────────────────────────────────────────────────────────────
# keyhole capability register
# ──────────────────────────────────────────────────────────────

def run_capability_register(
    *,
    capability_name: str,
    invariant: str = "",
    bundle: str = "proof_bundle",
    repo_dir: str = ".",
    mcp_url: str = DEFAULT_BASE_URL,
    keyhole_home: str = "",
) -> CommandResult:
    """Execute ``keyhole capability register``.

    Receipt-backed capability registration (Option B).

    Registration is not standalone: it requires an accepted proof receipt
    to prove governance gate passage before marking the capability as
    registered at the MCP boundary (run_type=capability.register).

    Contract:
      - A proof receipt must exist at proof_bundle/receipts/<inv-slug>-receipt.json
      - The receipt governed_verdict must be ACCEPT or ACCEPTED
      - The capability name must be namespace-valid
      - Submits run_type=capability.register with receipt reference

    If no receipt exists: directs developer to keyhole proof submit first.
    If the server does not yet support capability.register: returns SERVER_BLOCKED.

    This is the public contract: "No verified governed receipt, no registration."
    """
    command_label = "keyhole capability register"

    # ── Validate capability name ──
    if not capability_name or not capability_name.strip():
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary="--capability is required.",
            next_steps=["keyhole capability register --capability <name> [--invariant <id>]"],
        )

    cap_name = capability_name.strip()
    validation_result = validate_capability_name(cap_name)
    if not validation_result.valid:
        repair = [
            "Format:   <domain>.<category>.<capability>.v<major>",
            "Example:  payment.stripe.integration.v1",
        ]
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_INVALID_INPUT,
            summary=f"Invalid capability name: {cap_name}",
            data=validation_result.to_dict(),
            next_steps=repair,
        )

    # ── Locate receipt ──
    repo_path = Path(repo_dir).resolve()
    bundle_path = (repo_path / bundle).resolve()
    receipts_dir = bundle_path / "receipts"

    receipt_data = None
    receipt_path = None

    if invariant:
        inv_slug = invariant.strip().lower().replace("_", "-").replace(" ", "-")
        candidate = receipts_dir / f"{inv_slug}-receipt.json"
        if candidate.exists():
            receipt_path = candidate
    else:
        # Find any receipt with governed_verdict=ACCEPT
        if receipts_dir.is_dir():
            for rf in sorted(receipts_dir.glob("*-receipt.json")):
                try:
                    raw = rf.read_bytes()
                    for enc in ("utf-8-sig", "utf-16", "utf-8"):
                        try:
                            data = __import__("json").loads(raw.decode(enc))
                            if data.get("governed_verdict") in ("ACCEPT", "ACCEPTED", "PASS"):
                                receipt_path = rf
                                receipt_data = data
                                break
                        except (UnicodeDecodeError, __import__("json").JSONDecodeError):
                            continue
                    if receipt_path:
                        break
                except OSError:
                    continue

    if receipt_path and receipt_data is None:
        try:
            raw = receipt_path.read_bytes()
            for enc in ("utf-8-sig", "utf-16", "utf-8"):
                try:
                    receipt_data = __import__("json").loads(raw.decode(enc))
                    break
                except (UnicodeDecodeError, __import__("json").JSONDecodeError):
                    continue
        except OSError:
            receipt_data = None

    if not receipt_path or receipt_data is None:
        inv_hint = f"--invariant {invariant}" if invariant else "--invariant <id>"
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_FAILURE,
            summary="No accepted proof receipt found. Proof submission is required before capability registration.",
            data={"capability": cap_name},
            next_steps=[
                f"keyhole proof submit {inv_hint} — to submit proof and receive a receipt.",
                f"Then: keyhole capability register --capability {cap_name}",
                'This is the public contract: "No verified governed receipt, no registration."',
            ],
        )

    governed_verdict = receipt_data.get("governed_verdict", "")
    if governed_verdict not in ("ACCEPT", "ACCEPTED", "PASS"):
        return CommandResult(
            command=command_label,
            success=False,
            exit_code=EXIT_FAILURE,
            summary=f"Receipt governed_verdict is '{governed_verdict}' — only ACCEPT allows registration.",
            data={"capability": cap_name, "governed_verdict": governed_verdict},
            next_steps=[
                "Fix failing invariant checks and resubmit proof.",
                f"keyhole proof submit {f'--invariant {invariant}' if invariant else ''}",
            ],
        )

    submission_id = receipt_data.get("submission_id", "")
    invariant_id = receipt_data.get("invariant_id", invariant)

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

    correlation_id = generate_request_id()
    request = build_run_request(
        run_type="capability.register",
        repo_name=repo_path.name,
        context_ref=None,
        input_data={
            "capability": cap_name,
            "invariant_id": invariant_id,
            "submission_id": submission_id,
            "governed_verdict": governed_verdict,
        },
        correlation_id=correlation_id,
    )

    try:
        outcome = dispatch_run(transport=transport, request=request)
    finally:
        transport.close()

    if outcome.status in (OutcomeStatus.SUCCESS, OutcomeStatus.ACCEPTED):
        reg_status = (
            outcome.response_data.get("status", "ACCEPTED")
            if outcome.status == OutcomeStatus.SUCCESS
            else "ACCEPTED"
        )
        return CommandResult(
            command=command_label,
            success=True,
            exit_code=EXIT_SUCCESS,
            summary=f"Capability registered. status={reg_status} capability={cap_name}",
            data={
                "capability": cap_name,
                "registration_status": reg_status,
                "run_id": outcome.run_id,
                "invariant_id": invariant_id,
                "submission_id": submission_id,
                "outcome": outcome.response_data,
            },
        )

    reason = outcome.reason or "capability.register rejected by server."
    error_class = outcome.error_class or "unknown"
    next_steps: list[str] = outcome.repair_guidance or []

    if error_class in ("NOT_IMPLEMENTED", "METHOD_NOT_ALLOWED", "BLOCKED"):
        next_steps = [
            "capability.register may not yet be available for your workspace.",
            "Contact your Keyhole operator to enable capability registration.",
            "Check: keyhole context compile — to confirm workspace binding status.",
        ] + next_steps

    return CommandResult(
        command=command_label,
        success=False,
        exit_code=EXIT_FAILURE,
        summary=reason,
        data={
            "error_class": error_class,
            "run_type": "capability.register",
            "http_status": outcome.http_status,
            "capability": cap_name,
        },
        next_steps=next_steps,
    )

