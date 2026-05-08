"""my-first-app.greet.user.v1 — governed capability implementation.

Capability:  my-first-app.greet.user.v1
INV gate:    MY-FIRST-APP-INV-01 (GREET-USER-CAPABILITY-SHAPE-STABLE)

Response shape is a versioned, stable contract. Do not remove or rename
'greeting' or 'name' without incrementing the capability version and
updating the INV gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ── Response contract (shape is what INV-01 guards) ─────────────────────────

@dataclass(frozen=True)
class GreetResponse:
    """Stable, versioned response for my-first-app.greet.user.v1."""

    greeting: str
    name: str
    capability: str = "my-first-app.greet.user.v1"


# ── Capability implementation ────────────────────────────────────────────────

def greet(name: Optional[str] = None) -> GreetResponse:
    """Return a governed greeting for the supplied name.

    Parameters
    ----------
    name:
        Caller-supplied display name.  Defaults to "World" when absent or blank.

    Returns
    -------
    GreetResponse
        Stable response shape enforced by MY-FIRST-APP-INV-01.
    """
    resolved = (name or "").strip() or "World"
    return GreetResponse(
        greeting=f"Hello, {resolved}!",
        name=resolved,
    )
