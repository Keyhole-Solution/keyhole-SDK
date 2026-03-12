"""Keyhole SDK typed client example.

Demonstrates the governed SDK surface (S41-03) using typed models,
structured error handling, and compatibility checking.

Usage:
    python example_typed.py [BASE_URL]

Requires the Keyhole Test Runtime at BASE_URL (default: http://localhost:8080).
"""

from __future__ import annotations

import json
import sys

from keyhole_sdk import (
    KeyholeClient,
    RuntimeIdentity,
    RealizationReceipt,
    CompatibilityResult,
    TransportError,
    RuntimeUnavailableError,
    SchemaError,
    PublicEndpointError,
)


def main(base_url: str = "http://localhost:8080") -> None:
    # Context manager closes the session automatically
    with KeyholeClient(base_url=base_url) as client:

        # ── 1. Compatibility check ─────────────────────────
        print("== compatibility check ==")
        compat: CompatibilityResult = client.check_compatibility()
        print(f"  SDK version:    {compat.sdk_version}")
        print(f"  Runtime:        {compat.runtime_name} {compat.runtime_version}")
        print(f"  Status:         {compat.compatibility_status.value}")
        if compat.warnings:
            print(f"  Warnings:       {compat.warnings}")
        if compat.failures:
            print(f"  Failures:       {compat.failures}")
            print("\nRuntime is incompatible — aborting.")
            sys.exit(1)
        print()

        # ── 2. Typed identity ──────────────────────────────
        print("== typed identity ==")
        identity: RuntimeIdentity = client.get_identity()
        print(f"  ID:             {identity.runtime_id}")
        print(f"  Name:           {identity.runtime_name}")
        print(f"  Version:        {identity.runtime_version}")
        print(f"  Environment:    {identity.environment}")
        print(f"  Capabilities:   {identity.capabilities}")
        print()

        # ── 3. Typed health ────────────────────────────────
        print("== typed health ==")
        health = client.get_health()
        print(f"  Status:         {health.status}")
        print()

        # ── 4. Typed state ─────────────────────────────────
        print("== typed state (before realize) ==")
        state = client.get_state()
        print(f"  Current digest: {state.current_digest}")
        print(f"  Updated at:     {state.updated_at}")
        print()

        # ── 5. Typed realize ───────────────────────────────
        print("== typed realize ==")
        try:
            receipt: RealizationReceipt = client.realize_typed(
                candidate_digest="sha256:sdk-typed-example",
                payload={"source": "example_typed.py"},
            )
            print(f"  Digest:         {receipt.digest}")
            print(f"  Status:         {receipt.status}")
            print(f"  Message:        {receipt.message}")
            print(f"  Realized at:    {receipt.realized_at}")
        except PublicEndpointError as exc:
            print(f"  Runtime error:  {exc} (status={exc.status_code})")
        except SchemaError as exc:
            print(f"  Schema error:   {exc}")
        print()

        # ── 6. Final state ─────────────────────────────────
        print("== typed state (after realize) ==")
        state_after = client.get_state()
        print(f"  Current digest: {state_after.current_digest}")
        print(f"  Realized list:  {state_after.realized_digests}")
        print()

        # ── 7. JSON serialization example ──────────────────
        print("== JSON serialization ==")
        print(json.dumps(identity.model_dump(), indent=2, default=str))


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    try:
        main(url)
    except TransportError as exc:
        print(f"\nTransport error: {exc}", file=sys.stderr)
        print("Is the runtime running? Try: docker compose up", file=sys.stderr)
        sys.exit(1)
    except RuntimeUnavailableError as exc:
        print(f"\nRuntime unavailable: {exc}", file=sys.stderr)
        sys.exit(1)
