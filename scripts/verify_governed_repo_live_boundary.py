from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SDK_ROOT = REPO_ROOT / "packages" / "python" / "keyhole-sdk"
CLI_ROOT = REPO_ROOT / "packages" / "python" / "keyhole-cli"
for path in (SDK_ROOT, CLI_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from keyhole_sdk.auth_bootstrap.token_refresh import get_fresh_token
from keyhole_sdk.governed_demo import GovernedDemoError, _redact
from keyhole_sdk.governed_flow import GovernedRepoFlowClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a governed repo flow against live MCP.")
    parser.add_argument("--repo-dir", default=".", help="Repository directory to govern.")
    parser.add_argument("--story-id", default="", help="Optional story label for gap discovery.")
    parser.add_argument("--capability-id", default="", help="Optional capability selector.")
    parser.add_argument("--repo-class", default="", help="Optional repo class override.")
    parser.add_argument("--gap-id", default="", help="Explicit canonical gap_* id supplied by operator.")
    parser.add_argument("--dry-run", action="store_true", help="Resolve/explain without mutating MCP.")
    args = parser.parse_args()

    if not os.environ.get("KEYHOLE_MCP_URL"):
        print(json.dumps({
            "success": False,
            "skipped": True,
            "reason": "live proof not performed: KEYHOLE_MCP_URL is required",
        }, indent=2))
        return 2

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
            return 2

    try:
        client = GovernedRepoFlowClient(
            mcp_url=os.environ["KEYHOLE_MCP_URL"],
            token=token,
            runtime_url=os.environ.get("KEYHOLE_RUNTIME_URL", "http://localhost:8080"),
            story_id=args.story_id,
            capability_id=args.capability_id,
            repo_class=args.repo_class,
            gap_id=args.gap_id,
        )
        result = client.run_governed_repo_flow(args.repo_dir, dry_run=args.dry_run)
        print(json.dumps(_redact({"success": True, "skipped": False, **result}), indent=2, default=str))
        return 0
    except GovernedDemoError as exc:
        print(json.dumps({
            "success": False,
            "skipped": False,
            "error_class": type(exc).__name__,
            "reason": str(exc),
        }, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
