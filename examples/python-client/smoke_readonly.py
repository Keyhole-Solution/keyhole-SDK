"""Keyhole SDK — Read-Only Smoke Path example.

CE-V5-S42-07: Read-Only Smoke Path.

Runs the full read-only participant verification path:
  1. Discover capabilities (unauthenticated)
  2. Inspect identity via whoami (authenticated)
  3. Retrieve context via context.compile (authenticated)
  4. Safe read-only run via gaps.list (authenticated)

Usage:
    export KEYHOLE_MCP_URL="https://boundary.example.com"
    export KEYHOLE_MCP_TOKEN="<bearer-token>"
    python smoke_readonly.py

Environment variables:
    KEYHOLE_MCP_URL    — MCP boundary base URL (required)
    KEYHOLE_MCP_TOKEN  — Bearer token for authenticated surfaces (required)
"""

from __future__ import annotations

import os
import sys

from keyhole_sdk import ReadOnlySmokeRunner


def main() -> None:
    base_url = os.environ.get("KEYHOLE_MCP_URL", "")
    token = os.environ.get("KEYHOLE_MCP_TOKEN", "")

    if not base_url:
        print("Error: KEYHOLE_MCP_URL environment variable is required.", file=sys.stderr)
        sys.exit(1)

    if not token:
        print("Error: KEYHOLE_MCP_TOKEN environment variable is required.", file=sys.stderr)
        sys.exit(1)

    with ReadOnlySmokeRunner(base_url=base_url, token=token) as runner:
        result = runner.run()

    print(result.summary())
    sys.exit(0 if result.all_passed else 1)


if __name__ == "__main__":
    main()
