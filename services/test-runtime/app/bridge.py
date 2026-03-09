"""MCP Governance Bridge

Gates all realization requests through the Keyhole MCP governance controller.

When KEYHOLE_MCP_URL and KEYHOLE_MCP_TOKEN are configured, every POST /realize
is evaluated against live governance before any local mutation is applied.

Environment variables:
    KEYHOLE_MCP_URL   — Base URL of the Keyhole MCP server.
                        Example: https://mcp.keyholesolution.com
    KEYHOLE_MCP_TOKEN — Bearer token for authenticating with the MCP server.
                        Issue machine identity credentials from the Keyhole
                        tenant portal before deploying this runtime.
    KEYHOLE_MCP_RUN_TYPE — run_type sent to MCP for candidate verification.
                           Defaults to convergence.status.v0_1.
    KEYHOLE_MCP_TIMEOUT  — HTTP timeout in seconds. Defaults to 10.

If KEYHOLE_MCP_URL is not set the runtime operates in local-only mode.
Realization requests will succeed locally but are NOT gated by governance.
Local-only mode is intended for initial SDK and tooling development only.
Production and staging deployments must configure MCP governance.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_MCP_URL: str = os.environ.get("KEYHOLE_MCP_URL", "").rstrip("/")
_MCP_TOKEN: str = os.environ.get("KEYHOLE_MCP_TOKEN", "")
_MCP_RUN_TYPE: str = os.environ.get("KEYHOLE_MCP_RUN_TYPE", "convergence.status.v0_1")
_MCP_TIMEOUT: float = float(os.environ.get("KEYHOLE_MCP_TIMEOUT", "10"))

# Runs endpoint on the MCP server
_RUNS_PATH = "/mcp/v1/runs/start"


def governance_mode() -> str:
    """Return the current bridge mode for startup logging and /identity."""
    if _MCP_URL and _MCP_TOKEN:
        return "governed"
    if _MCP_URL and not _MCP_TOKEN:
        return "misconfigured"  # URL set but no token — will fail at call time
    return "local-only"


def _headers() -> dict[str, str]:
    h: dict[str, str] = {"Content-Type": "application/json"}
    if _MCP_TOKEN:
        h["Authorization"] = f"Bearer {_MCP_TOKEN}"
    return h


async def governance_check(
    candidate_digest: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Verify a candidate digest against the Keyhole MCP governance controller.

    Returns a verdict dict:
        ok      : bool   — True if realization is approved by governance
        verdict : str    — "APPROVED" | "REJECT" | "LOCAL_ONLY"
        reason  : str    — Human-readable verdict reason
        mcp     : dict   — Raw MCP response result (absent in local-only mode)

    Raises nothing — all errors produce a REJECT verdict with a reason string.
    """
    if not _MCP_URL:
        logger.warning(
            "KEYHOLE_MCP_URL not configured — running in local-only mode. "
            "Realization is NOT gated by Keyhole governance."
        )
        return {
            "ok": True,
            "verdict": "LOCAL_ONLY",
            "reason": "No MCP governance configured. Set KEYHOLE_MCP_URL and KEYHOLE_MCP_TOKEN.",
        }

    if not _MCP_TOKEN:
        logger.error(
            "KEYHOLE_MCP_URL is set but KEYHOLE_MCP_TOKEN is missing. "
            "Cannot authenticate with governance controller."
        )
        return {
            "ok": False,
            "verdict": "REJECT",
            "reason": "Governance misconfigured: KEYHOLE_MCP_TOKEN is required when KEYHOLE_MCP_URL is set.",
        }

    url = f"{_MCP_URL}{_RUNS_PATH}"
    body: dict[str, Any] = {
        "run_type": _MCP_RUN_TYPE,
        "parameters": {
            "candidate_digest": candidate_digest,
            "payload": payload,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=_MCP_TIMEOUT) as client:
            resp = await client.post(url, json=body, headers=_headers())

        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                return {
                    "ok": True,
                    "verdict": "APPROVED",
                    "reason": "Keyhole governance approved the candidate.",
                    "mcp": data.get("result"),
                }
            error = data.get("error", {})
            logger.warning("MCP governance rejected candidate %s: %s", candidate_digest, error)
            return {
                "ok": False,
                "verdict": "REJECT",
                "reason": error.get("message", "Governance rejected the candidate."),
                "mcp": error,
            }

        if resp.status_code in (401, 403):
            logger.error(
                "MCP governance auth failure: HTTP %d — verify KEYHOLE_MCP_TOKEN.",
                resp.status_code,
            )
            return {
                "ok": False,
                "verdict": "REJECT",
                "reason": f"Governance auth failure (HTTP {resp.status_code}). Check KEYHOLE_MCP_TOKEN.",
            }

        logger.warning("MCP governance check returned HTTP %d", resp.status_code)
        return {
            "ok": False,
            "verdict": "REJECT",
            "reason": f"Governance check failed with HTTP {resp.status_code}.",
        }

    except httpx.TimeoutException:
        logger.error("MCP governance check timed out after %.1fs", _MCP_TIMEOUT)
        return {
            "ok": False,
            "verdict": "REJECT",
            "reason": f"Governance check timed out after {_MCP_TIMEOUT}s.",
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("MCP governance check raised unexpected error: %s", exc)
        return {
            "ok": False,
            "verdict": "REJECT",
            "reason": f"Governance check error: {exc}",
        }
