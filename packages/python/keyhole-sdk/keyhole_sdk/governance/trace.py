"""Governance trace builder — causal chain and graph artifacts.

CE-V5 — Recursive Governance Proof Test (RG-01).

Builds the causal governance trace from proof protocol events:
    SDK commit → proof bundle → verification → verdict → promotion

Produces:
    - governance_trace as structured data
    - governance_trace.graph as a text-based causal graph
    - validation of event chain completeness

Must never:
    - fabricate events that did not occur
    - claim causal links without supporting evidence
    - expose private platform topology
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from keyhole_sdk.governance.models import (
    EXPECTED_EVENTS,
    GovernanceEvent,
    GovernancePhase,
    GovernanceProofResult,
)


class GovernanceTraceBuilder:
    """Builds and validates the causal governance trace.

    The trace connects governance events into a causal chain that
    demonstrates cross-boundary governance.  When all phases succeed,
    the trace proves that an external participant's work was governed
    through proof-backed contracts.

    Example::

        builder = GovernanceTraceBuilder(result)
        trace = builder.build_trace()
        graph = builder.build_graph()
        print(graph)
    """

    def __init__(self, result: GovernanceProofResult) -> None:
        self._result = result

    @property
    def events(self) -> List[GovernanceEvent]:
        """All events from the proof result, in phase order."""
        return [
            p.event
            for p in self._result.phases
            if p.event is not None
        ]

    @property
    def correlation_id(self) -> str:
        """Shared correlation ID for the trace."""
        return self._result.correlation_id

    def build_trace(self) -> Dict[str, Any]:
        """Build the structured governance trace.

        Returns a dictionary suitable for serialization as
        ``governance_trace.json``.
        """
        events_data = []
        for i, event in enumerate(self.events, start=1):
            events_data.append({
                "sequence": i,
                "event_type": event.event_type,
                "phase": event.phase.value,
                "participant_id": event.participant_id,
                "correlation_id": event.correlation_id,
                "event_digest": event.event_digest,
                "timestamp": event.timestamp.isoformat(),
                "scaffolded": event.scaffolded,
            })

        return {
            "trace_id": self.correlation_id,
            "participant": self._result.participant,
            "event_count": len(events_data),
            "events": events_data,
            "chain_complete": self.validate_chain(),
            "supported_chain_complete": self.validate_supported_chain(),
        }

    def build_graph(self) -> str:
        """Build a text-based causal graph of the governance trace.

        Returns a human-readable representation showing the causal
        chain from SDK commit through promotion.
        """
        lines = [
            "=== Governance Trace Graph ===",
            f"Trace ID: {self.correlation_id}",
            f"Participant: {self._result.participant}",
            "",
        ]

        events = self.events
        if not events:
            lines.append("(no events recorded)")
            return "\n".join(lines)

        for i, event in enumerate(events):
            marker = "[scaffolded]" if event.scaffolded else "[supported]"
            lines.append(f"  {event.event_type} {marker}")
            if i < len(events) - 1:
                lines.append("      |")
                lines.append("      v")

        lines.append("")

        # Compact causal chain
        event_names = [e.event_type for e in events]
        lines.append("Causal chain:")
        lines.append("  " + " → ".join(event_names))

        return "\n".join(lines)

    def validate_chain(self) -> bool:
        """Validate that the full causal chain is present.

        Returns True only if all expected events are present.
        """
        expected = set(EXPECTED_EVENTS.values())
        actual = {e.event_type for e in self.events}
        return expected.issubset(actual)

    def validate_supported_chain(self) -> bool:
        """Validate that supported (non-scaffolded) phase events are present.

        Returns True if all supported phase events are in the trace.
        """
        supported_events = {
            EXPECTED_EVENTS[GovernancePhase.CONTEXT],
            EXPECTED_EVENTS[GovernancePhase.IMPLEMENTATION],
        }
        # Verification phase doesn't have a standard EXPECTED_EVENTS entry
        # but produces an event via the runner
        actual = {e.event_type for e in self.events if not e.scaffolded}
        return supported_events.issubset(actual)

    def missing_events(self) -> List[str]:
        """Return expected event types not present in the trace."""
        expected = set(EXPECTED_EVENTS.values())
        actual = {e.event_type for e in self.events}
        return sorted(expected - actual)
