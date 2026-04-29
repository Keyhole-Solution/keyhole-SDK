"""`keyhole runtime profiles | surface | check` — SDK-CLIENT-24.

Productizes the SDK-SERVER-24 runtime contract surfaces. These commands
discover the canonical/external runtime profiles, negotiate the
authoritative runtime surface, and verify a participant's runtime claims
against the boundary.

Constitutional invariants:
  - The CLI never decides runtime trust (server-only classification).
  - Docker is *not* required — diagnostics remain advisory.
  - The CLI never imports platform internals.
  - ``.venv`` is never treated as a canonical execution surface.
"""

from __future__ import annotations

import platform as _platform
import sys
from pathlib import Path
from typing import Optional

from keyhole_sdk.auth import BearerTokenProvider
from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.config import DEFAULT_BASE_URL
from keyhole_sdk.discovery.client import CapabilitiesClient
from keyhole_sdk.exceptions import (
    PublicEndpointError,
    SchemaError,
    TransportError,
)
from keyhole_sdk.runtime_contract import (
    RuntimeCompatibilityResult,
    RuntimeCompatibilityStatus,
    RuntimeContext,
    RuntimeContextBuilder,
    RuntimeContractClient,
    RuntimeContractProofEmitter,
    RuntimeProfile,
    RuntimeSurfaceResult,
    collect_diagnostics,
    fill_repair_defaults,
    map_runtime_repair,
)
from keyhole_sdk.runtime_contract.models import RuntimeRepairGuidance
from keyhole_sdk.transport.client import GovernedTransport
from keyhole_sdk.transport.idempotency import generate_request_id

from keyhole_cli.result import (
    EXIT_CONTRACT_FAILURE,
    EXIT_INVALID_INPUT,
    EXIT_RUNTIME_UNAVAILABLE,
    EXIT_SUCCESS,
    CommandResult,
)


_PROFILES_LABEL = "keyhole runtime profiles"
_SURFACE_LABEL = "keyhole runtime surface"
_CHECK_LABEL = "keyhole runtime check"
_DEFAULT_REPO = "keyhole-sdk"


# ──────────────────────────────────────────────────────────────
# `keyhole runtime profiles`
# ──────────────────────────────────────────────────────────────

def run_runtime_profiles(
    *,
    mcp_url: str = DEFAULT_BASE_URL,
) -> CommandResult:
    """Render runtime profiles disclosed in capabilities (§9.1)."""
    try:
        with CapabilitiesClient(base_url=mcp_url) as caps_client:
            caps = caps_client.fetch()
    except (TransportError, SchemaError) as exc:
        return CommandResult(
            command=_PROFILES_LABEL,
            success=False,
            exit_code=EXIT_RUNTIME_UNAVAILABLE,
            summary=f"Cannot reach MCP boundary at {mcp_url!r}: {exc}",
            data={"mcp_url": mcp_url, "detail": str(exc)},
            next_steps=map_runtime_repair("transport_failure"),
        )

    transport = GovernedTransport(base_url=mcp_url)
    try:
        client = RuntimeContractClient(
            transport=transport, capabilities_client=None, repo_name=_DEFAULT_REPO
        )
        try:
            profiles = client.get_runtime_profiles(capabilities=caps)
        except PublicEndpointError as exc:
            return CommandResult(
                command=_PROFILES_LABEL,
                success=False,
                exit_code=EXIT_CONTRACT_FAILURE,
                summary=(
                    "Runtime profiles missing from capabilities — "
                    "boundary does not advertise SDK-SERVER-24 contract."
                ),
                data={
                    "mcp_url": mcp_url,
                    "reason": "runtime_profiles_missing",
                    "detail": str(exc),
                },
                next_steps=map_runtime_repair("runtime_profiles_missing"),
            )
    finally:
        transport.close()

    profiles_data = [_profile_to_dict(p) for p in profiles]
    canonical = next(
        (p for p in profiles if p.canonical and p.kind.value == "container"),
        None,
    )
    return CommandResult(
        command=_PROFILES_LABEL,
        success=True,
        exit_code=EXIT_SUCCESS,
        summary=(
            f"Discovered {len(profiles)} runtime profile(s); "
            f"canonical: {canonical.profile_id if canonical else 'none'}"
        ),
        data={
            "mcp_url": mcp_url,
            "profile_count": len(profiles),
            "canonical_profile_id": canonical.profile_id if canonical else "",
            "profiles": profiles_data,
        },
    )


# ──────────────────────────────────────────────────────────────
# `keyhole runtime surface`
# ──────────────────────────────────────────────────────────────

def run_runtime_surface(
    *,
    mcp_url: str = DEFAULT_BASE_URL,
    keyhole_home: str = "",
) -> CommandResult:
    """Negotiate the authoritative runtime surface (§9.2)."""
    token = _resolve_token(keyhole_home)
    auth = BearerTokenProvider(token=token) if token else None
    transport = GovernedTransport(base_url=mcp_url, auth_provider=auth)
    try:
        client = RuntimeContractClient(
            transport=transport, repo_name=_DEFAULT_REPO
        )
        try:
            result = client.get_runtime_surface()
        except (TransportError, SchemaError) as exc:
            return CommandResult(
                command=_SURFACE_LABEL,
                success=False,
                exit_code=EXIT_RUNTIME_UNAVAILABLE,
                summary=f"Cannot reach MCP boundary at {mcp_url!r}: {exc}",
                data={"mcp_url": mcp_url, "detail": str(exc)},
                next_steps=map_runtime_repair("transport_failure"),
            )
        except PublicEndpointError as exc:
            return CommandResult(
                command=_SURFACE_LABEL,
                success=False,
                exit_code=EXIT_CONTRACT_FAILURE,
                summary=f"Runtime surface unavailable: {exc}",
                data={
                    "mcp_url": mcp_url,
                    "reason": "runtime_surface_unavailable",
                    "detail": getattr(exc, "detail", str(exc)),
                },
                next_steps=map_runtime_repair("runtime_surface_unavailable"),
            )
    finally:
        transport.close()

    return CommandResult(
        command=_SURFACE_LABEL,
        success=True,
        exit_code=EXIT_SUCCESS,
        summary=(
            f"Surface negotiated; canonical={result.canonical_profile_id} "
            f"external={result.external_profile_id} "
            f"contract={result.contract_version}"
        ),
        data={
            "mcp_url": mcp_url,
            "status": result.status,
            "contract_version": result.contract_version,
            "canonical_profile_id": result.canonical_profile_id,
            "external_profile_id": result.external_profile_id,
            "profiles": [_profile_to_dict(p) for p in result.profiles],
        },
    )


# ──────────────────────────────────────────────────────────────
# `keyhole runtime check`
# ──────────────────────────────────────────────────────────────

def run_runtime_check(
    *,
    mode: str = "auto",
    runtime_kind: str = "local-python",
    image_digest: str = "",
    negative: str = "",
    mcp_url: str = DEFAULT_BASE_URL,
    keyhole_home: str = "",
) -> CommandResult:
    """Verify a runtime context against the boundary (§9.3 §9.4 §9.5)."""
    diagnostics = collect_diagnostics()
    builder = RuntimeContextBuilder()

    # ── Negative test surfaces (§9.5) ────────────────────────
    if negative:
        if negative == "nonportable-venv":
            ctx = builder.build_nonportable_venv_context()
        else:
            return CommandResult(
                command=_CHECK_LABEL,
                success=False,
                exit_code=EXIT_INVALID_INPUT,
                summary=f"Unknown negative-test mode: {negative!r}",
                next_steps=[
                    "Supported negative modes: nonportable-venv.",
                ],
            )
    else:
        try:
            ctx = _build_context(
                builder=builder,
                mode=mode,
                runtime_kind=runtime_kind,
                image_digest=image_digest,
                inside_container=diagnostics.inside_container,
            )
        except ValueError as exc:
            reason = "missing_container_digest"
            return CommandResult(
                command=_CHECK_LABEL,
                success=False,
                exit_code=EXIT_INVALID_INPUT,
                summary=str(exc),
                data={"reason": reason, "mode": mode},
                next_steps=map_runtime_repair(reason),
            )

    # ── Dispatch ─────────────────────────────────────────────
    correlation_id = generate_request_id()
    token = _resolve_token(keyhole_home)
    auth = BearerTokenProvider(token=token) if token else None
    transport = GovernedTransport(base_url=mcp_url, auth_provider=auth)
    request_payload = {
        "run_type": "sdk.runtime.compatibility.check.v1",
        "repo": _DEFAULT_REPO,
        "shadow": False,
        "correlation_id": correlation_id,
        "input": {"runtime_context": ctx.to_payload()},
    }
    surface: Optional[RuntimeSurfaceResult] = None
    try:
        client = RuntimeContractClient(
            transport=transport, repo_name=_DEFAULT_REPO
        )
        try:
            surface = client.get_runtime_surface()
        except Exception:  # noqa: BLE001 — surface is informational here
            surface = None

        try:
            outcome = client.check_compatibility(
                ctx, correlation_id=correlation_id
            )
        except (TransportError, SchemaError) as exc:
            return CommandResult(
                command=_CHECK_LABEL,
                success=False,
                exit_code=EXIT_RUNTIME_UNAVAILABLE,
                summary=f"Cannot reach MCP boundary at {mcp_url!r}: {exc}",
                data={"mcp_url": mcp_url, "detail": str(exc)},
                next_steps=map_runtime_repair("transport_failure"),
            )
    finally:
        transport.close()

    outcome.repair = fill_repair_defaults(outcome.repair)

    # ── Emit local proof (§13) ────────────────────────────────
    proof_dir = ""
    try:
        emitter = RuntimeContractProofEmitter()
        artifact = emitter.emit(
            correlation_id=correlation_id,
            request_payload=request_payload,
            response_payload=outcome.raw,
            runtime_context=ctx,
            diagnostics=diagnostics,
            surface=surface,
            compatibility=outcome,
            command=_CHECK_LABEL,
        )
        proof_dir = artifact.bundle_dir
    except Exception:  # noqa: BLE001 — proof is fire-and-continue
        proof_dir = ""

    # ── Negative-test contract: REJECT is the *expected* outcome ─
    if negative:
        if outcome.status == RuntimeCompatibilityStatus.REJECT:
            return CommandResult(
                command=_CHECK_LABEL,
                success=True,
                exit_code=EXIT_SUCCESS,
                summary=(
                    f"Negative test {negative!r} produced expected REJECT "
                    f"({outcome.reason or 'no_reason'})"
                ),
                data={
                    "mcp_url": mcp_url,
                    "negative": negative,
                    "status": outcome.status.value,
                    "reason": outcome.reason,
                    "correlation_id": correlation_id,
                    "proof_dir": proof_dir,
                },
                next_steps=outcome.repair.repair,
            )
        return CommandResult(
            command=_CHECK_LABEL,
            success=False,
            exit_code=EXIT_CONTRACT_FAILURE,
            summary=(
                f"Negative test {negative!r} unexpectedly produced "
                f"{outcome.status.value} — boundary did not reject "
                f"nonportable runtime coupling."
            ),
            data={
                "mcp_url": mcp_url,
                "negative": negative,
                "status": outcome.status.value,
                "correlation_id": correlation_id,
                "proof_dir": proof_dir,
            },
            next_steps=map_runtime_repair("nonportable_runtime_coupling"),
        )

    # ── Normal-path render ───────────────────────────────────
    success = outcome.status == RuntimeCompatibilityStatus.ACCEPT
    exit_code = EXIT_SUCCESS if success else EXIT_CONTRACT_FAILURE
    summary = _summarize_outcome(outcome, ctx)
    return CommandResult(
        command=_CHECK_LABEL,
        success=success,
        exit_code=exit_code,
        summary=summary,
        data={
            "mcp_url": mcp_url,
            "status": outcome.status.value,
            "reason": outcome.reason,
            "trust_level": (
                outcome.runtime_trust_level.value
                if outcome.runtime_trust_level
                else ""
            ),
            "selected_profile_id": outcome.selected_profile,
            "correlation_id": correlation_id,
            "proof_dir": proof_dir,
            "runtime_context": ctx.to_payload(),
            "diagnostics": _diagnostics_to_dict(diagnostics),
        },
        next_steps=outcome.repair.repair if not success else [],
    )


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────


def _resolve_token(keyhole_home: str) -> str:
    """Best-effort resolution of an authenticated session token."""
    try:
        store_dir = Path(keyhole_home) if keyhole_home else None
        cred_store = CredentialStore(store_dir=store_dir)
        session = cred_store.load()
        return session.access_token if session else ""
    except Exception:  # noqa: BLE001
        return ""


def _build_context(
    *,
    builder: RuntimeContextBuilder,
    mode: str,
    runtime_kind: str,
    image_digest: str,
    inside_container: bool,
) -> RuntimeContext:
    """Construct a runtime context from CLI flags + diagnostics."""
    normalized = (mode or "auto").strip().lower()
    if normalized == "auto":
        normalized = "container" if inside_container and image_digest else "external"

    if normalized == "container":
        return builder.build_container_context(
            container_image_digest=image_digest
        )
    if normalized == "external":
        return builder.build_external_context(
            runtime_kind=runtime_kind,
            platform=_platform.platform(),
            python_version=_python_version_string(),
        )
    raise ValueError(
        f"Unsupported --mode {mode!r}; expected one of: auto, container, external."
    )


def _python_version_string() -> str:
    return ".".join(str(part) for part in sys.version_info[:3])


def _profile_to_dict(profile: RuntimeProfile) -> dict:
    return {
        "profile_id": profile.profile_id,
        "kind": profile.kind.value,
        "canonical": profile.canonical,
        "requires_container_runtime": profile.requires_container_runtime,
        "requires_local_venv": profile.requires_local_venv,
        "description": profile.description,
    }


def _diagnostics_to_dict(diag) -> dict:
    return {
        "container_runtime_kind": diag.container_runtime_kind,
        "container_runtime_detected": diag.container_runtime_detected,
        "inside_container": diag.inside_container,
        "local_venv_path": diag.local_venv_path,
        "local_venv_present": diag.local_venv_present,
        "local_venv_canonical": diag.local_venv_canonical,
        "platform": diag.platform,
        "python_version": diag.python_version,
    }


def _summarize_outcome(
    outcome: RuntimeCompatibilityResult, ctx: RuntimeContext
) -> str:
    status = outcome.status.value
    trust = (
        outcome.runtime_trust_level.value
        if outcome.runtime_trust_level
        else "unclassified"
    )
    if outcome.status == RuntimeCompatibilityStatus.ACCEPT:
        return (
            f"ACCEPT — trust={trust} profile={outcome.selected_profile or 'n/a'} "
            f"mode={ctx.runtime_mode.value}"
        )
    reason = outcome.reason or "compatibility_check_failed"
    return f"{status} — reason={reason} mode={ctx.runtime_mode.value}"
