"""Live CE-V5-S51-C02 verifier.

Runs the governed first-app flow only when KEYHOLE_MCP_URL and
KEYHOLE_MCP_TOKEN are present. The token is never printed or written.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SDK_ROOT = REPO_ROOT / "packages" / "python" / "keyhole-sdk"
if str(SDK_ROOT) not in sys.path:
    sys.path.insert(0, str(SDK_ROOT))

from keyhole_sdk.governed_demo import GovernedDemoError, GovernedFirstAppClient
from keyhole_sdk.auth_bootstrap.token_refresh import get_fresh_token


def main() -> int:
    if not os.environ.get("KEYHOLE_MCP_URL"):
        print(json.dumps({
            "success": False,
            "skipped": True,
            "reason": "live proof not performed: KEYHOLE_MCP_URL is required",
        }, indent=2))
        return 0

    token = os.environ.get("KEYHOLE_MCP_TOKEN", "")
    if not token:
        try:
            token = get_fresh_token()
        except Exception as exc:
            print(json.dumps({
                "success": False,
                "skipped": True,
                "reason": (
                    "live proof not performed: KEYHOLE_MCP_TOKEN is not set "
                    f"and no usable device-login credential is available: {exc}"
                ),
            }, indent=2))
            return 0

    repo = REPO_ROOT / "my-first-app"
    try:
        client = GovernedFirstAppClient(
            mcp_url=os.environ.get("KEYHOLE_MCP_URL", ""),
            token=token,
            runtime_url=os.environ.get("KEYHOLE_RUNTIME_URL", "http://localhost:8080"),
        )
        client.register_repo(repo)
        client.compile_context(repo)
        receipt = client.run_governed_realization(repo)
    except GovernedDemoError as exc:
        print(json.dumps({
            "success": False,
            "skipped": False,
            "reason": str(exc),
        }, indent=2))
        return 1

    print(json.dumps({
        "success": True,
        "skipped": False,
        "receipt": {
            "governed": receipt.governed,
            "event_spine_evidence": receipt.event_spine_evidence,
            "governance_verdict": receipt.governance_verdict,
            "drift_state": receipt.drift_state,
            "governance_context_id": receipt.governance_context_id,
            "mcp_event_id": receipt.mcp_event_id,
            "proof_id": receipt.proof_id,
            "receipt_id": receipt.receipt_id,
            "passport_digest": receipt.passport_digest,
            "trust_digest": receipt.trust_digest,
        },
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
