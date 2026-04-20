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

from keyhole_sdk.capability import (
    CapabilityNameError,
    CapabilityValidationResult,
    create_capability_name,
    emit_namespace_proof,
    normalize_capability_parts,
    validate_capability_name,
)

from keyhole_cli.result import (
    EXIT_INVALID_INPUT,
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
