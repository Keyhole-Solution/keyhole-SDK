"""`keyhole runtime start|stop|status` — truthful local runtime lifecycle."""

from __future__ import annotations

import subprocess
import time
from typing import Any, Dict, List, Optional

import requests

from keyhole_cli.result import CommandResult, EXIT_SUCCESS, EXIT_FAILURE, EXIT_RUNTIME_UNAVAILABLE
from keyhole_sdk.config import DEFAULT_BASE_URL


_HEALTH_TIMEOUT = 30  # seconds to wait for runtime health
_HEALTH_POLL = 2  # seconds between polls
_DEFAULT_ENDPOINT = DEFAULT_BASE_URL

# Forbidden private fields that must never surface in public output
_PRIVATE_FIELDS = frozenset({
    "pointer_state", "promotion_state", "canonical_digest",
    "cluster_topology", "internal_lane", "controller_state",
    "governance_verdict", "drift_state",
})


def _compose_cmd() -> List[str]:
    """Return the docker compose invocation list."""
    return ["docker", "compose"]


def _runtime_reachable(endpoint: str) -> bool:
    """Check whether the runtime healthz endpoint responds."""
    try:
        resp = requests.get(f"{endpoint}/healthz", timeout=5)
        return resp.status_code == 200
    except (requests.ConnectionError, requests.Timeout, OSError):
        return False


def _query_identity(endpoint: str) -> Optional[Dict[str, Any]]:
    """Query the public /identity endpoint.  Returns None if unreachable."""
    try:
        resp = requests.get(f"{endpoint}/identity", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except (requests.ConnectionError, requests.Timeout, ValueError, OSError):
        pass
    return None


def _filter_private(data: Dict[str, Any]) -> Dict[str, Any]:
    """Strip any private/governance fields from public output."""
    return {k: v for k, v in data.items() if k not in _PRIVATE_FIELDS}


def _is_compose_running() -> bool:
    """Detect whether docker compose services are running."""
    try:
        result = subprocess.run(
            [*_compose_cmd(), "ps", "--format", "json", "-q"],
            capture_output=True, text=True, timeout=10,
        )
        return bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


# ──────────────────────────────────────────────────────────────
# runtime start
# ──────────────────────────────────────────────────────────────
def run_start(*, endpoint: str = _DEFAULT_ENDPOINT) -> CommandResult:
    """Start the local public test runtime and verify health."""
    # Already running?
    if _runtime_reachable(endpoint):
        identity = _query_identity(endpoint)
        return CommandResult(
            command="runtime start",
            success=True,
            exit_code=EXIT_SUCCESS,
            data={
                "runtime_started": True,
                "runtime_name": (identity or {}).get("name", "unknown"),
                "runtime_endpoint": endpoint,
                "health_status": "healthy",
                "detected_mode": _safe_mode(identity),
                "already_running": True,
            },
            summary="Runtime is already running and healthy.",
            next_steps=["Run 'keyhole runtime status' or 'keyhole smoke'."],
        )

    # Start via docker compose
    try:
        subprocess.run(
            [*_compose_cmd(), "up", "-d"],
            capture_output=True, text=True, timeout=60, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        return CommandResult(
            command="runtime start",
            success=False,
            exit_code=EXIT_FAILURE,
            data={"runtime_started": False, "health_status": "failed"},
            summary=f"Failed to start runtime: {exc}",
            next_steps=["Ensure Docker is running and docker-compose.yml exists."],
        )

    # Wait for health
    deadline = time.monotonic() + _HEALTH_TIMEOUT
    healthy = False
    while time.monotonic() < deadline:
        if _runtime_reachable(endpoint):
            healthy = True
            break
        time.sleep(_HEALTH_POLL)

    if not healthy:
        return CommandResult(
            command="runtime start",
            success=False,
            exit_code=EXIT_RUNTIME_UNAVAILABLE,
            data={"runtime_started": False, "health_status": "unhealthy"},
            summary="Runtime started but did not become healthy within timeout.",
            next_steps=["Check 'docker compose logs' for errors."],
        )

    identity = _query_identity(endpoint)
    return CommandResult(
        command="runtime start",
        success=True,
        exit_code=EXIT_SUCCESS,
        data={
            "runtime_started": True,
            "runtime_name": (identity or {}).get("name", "unknown"),
            "runtime_endpoint": endpoint,
            "health_status": "healthy",
            "detected_mode": _safe_mode(identity),
            "already_running": False,
        },
        summary="Runtime started and healthy.",
        next_steps=["Run 'keyhole smoke' to verify first success."],
    )


# ──────────────────────────────────────────────────────────────
# runtime stop
# ──────────────────────────────────────────────────────────────
def run_stop() -> CommandResult:
    """Stop the local public test runtime."""
    was_running = _is_compose_running()

    if not was_running:
        return CommandResult(
            command="runtime stop",
            success=True,
            exit_code=EXIT_SUCCESS,
            data={
                "runtime_stopped": True,
                "prior_state": "stopped",
                "current_state": "stopped",
            },
            summary="Runtime was already stopped (no-op).",
        )

    try:
        subprocess.run(
            [*_compose_cmd(), "down"],
            capture_output=True, text=True, timeout=60, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        return CommandResult(
            command="runtime stop",
            success=False,
            exit_code=EXIT_FAILURE,
            data={
                "runtime_stopped": False,
                "prior_state": "running",
                "current_state": "unknown",
            },
            summary=f"Failed to stop runtime: {exc}",
        )

    return CommandResult(
        command="runtime stop",
        success=True,
        exit_code=EXIT_SUCCESS,
        data={
            "runtime_stopped": True,
            "prior_state": "running",
            "current_state": "stopped",
        },
        summary="Runtime stopped.",
    )


# ──────────────────────────────────────────────────────────────
# runtime status
# ──────────────────────────────────────────────────────────────
def run_status(*, endpoint: str = _DEFAULT_ENDPOINT) -> CommandResult:
    """Report truthful runtime state and publicly visible mode."""
    reachable = _runtime_reachable(endpoint)

    if not reachable:
        return CommandResult(
            command="runtime status",
            success=True,  # status itself succeeded; runtime is just not there
            exit_code=EXIT_RUNTIME_UNAVAILABLE,
            data={
                "reachable": False,
                "runtime_name": "unknown",
                "runtime_version": "unknown",
                "runtime_environment": "unknown",
                "capabilities": [],
                "mode_truth_source": "none",
            },
            summary="Runtime is not reachable.",
            next_steps=["Run 'keyhole runtime start' to start the runtime."],
        )

    identity = _query_identity(endpoint)
    if identity is None:
        return CommandResult(
            command="runtime status",
            success=True,
            exit_code=EXIT_SUCCESS,
            data={
                "reachable": True,
                "runtime_name": "unknown",
                "runtime_version": "unknown",
                "runtime_environment": "unknown",
                "capabilities": [],
                "mode_truth_source": "healthz_only",
            },
            summary="Runtime is reachable but identity endpoint unavailable.",
            warnings=["Could not query /identity — mode unknown."],
        )

    safe = _filter_private(identity)
    return CommandResult(
        command="runtime status",
        success=True,
        exit_code=EXIT_SUCCESS,
        data={
            "reachable": True,
            "runtime_name": safe.get("name", "unknown"),
            "runtime_version": safe.get("version", "unknown"),
            "runtime_environment": safe.get("environment", "unknown"),
            "capabilities": safe.get("capabilities", []),
            "mode_truth_source": "identity_endpoint",
        },
        summary=f"Runtime reachable: {safe.get('name', 'unknown')} v{safe.get('version', 'unknown')}",
    )


# ──────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────
def _safe_mode(identity: Optional[Dict[str, Any]]) -> str:
    """Extract runtime mode from identity, bounded to public truth."""
    if identity is None:
        return "unknown"
    env = identity.get("environment")
    if isinstance(env, str):
        return env
    return "unknown"
