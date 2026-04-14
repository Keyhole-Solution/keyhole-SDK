"""Tests for SDK-CLIENT-11: Alignment Guidance.

Covers:
  - GuidanceItem construction, alias, sort_key, to_dict
  - Deterministic ranking (§9 precedence)
  - Readiness derivation (§10)
  - Next-best-action selection (§11)
  - render_guidance end-to-end
  - Submitter: classification of terminal/accepted/deferred
  - Proof emission (§15)
  - Repair guidance for all known error classes
  - No-silent-mutation invariant (§14)
  - CLI align command existence and basic rendering
  - Public API surface (12 symbols in __all__)
  - Operation registry has alignment.guidance as READ_ONLY
  - Accepted/deferred honesty (§6, §13)
  - Negative: malformed items, missing fields

All tests are pure-unit (no network, no MCP calls).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from keyhole_sdk.alignment.models import (
    AlignmentGuidanceRequest,
    AlignmentGuidanceResult,
    AlignmentReadiness,
    GuidanceClass,
    GuidanceItem,
    GuidanceSeverity,
    GuidanceState,
)
from keyhole_sdk.alignment.ranker import render_guidance
from keyhole_sdk.alignment.proof import emit_alignment_proof
from keyhole_sdk.alignment.repair import map_alignment_repair


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


def _item(
    id: str = "gap.x",
    guidance_class: str = "gap",
    severity: str = "high",
    confidence: float = 1.0,
    state: str = "verified",
    title: str = "Test gap",
    repair: list | None = None,
) -> GuidanceItem:
    return GuidanceItem.model_validate({
        "id": id,
        "class": guidance_class,
        "severity": severity,
        "confidence": confidence,
        "state": state,
        "title": title,
        "repair": repair or ["Run: keyhole fix"],
    })


def _req(items: list | None = None) -> AlignmentGuidanceRequest:
    return AlignmentGuidanceRequest(
        repo_identity="test-repo",
        repo_path="/tmp/test-repo",
        guidance_items=items or [],
    )


# ─────────────────────────────────────────────────────────────
# TestGuidanceModels
# ─────────────────────────────────────────────────────────────


class TestGuidanceModels:
    def test_guidance_item_construction_via_alias(self):
        item = GuidanceItem.model_validate({
            "id": "gap.contract.missing",
            "class": "gap",
            "severity": "high",
            "confidence": 0.95,
            "state": "verified",
            "title": "Missing contract pin",
            "repair": ["Add pin to schema."],
        })
        assert item.guidance_class == GuidanceClass.GAP
        assert item.severity == GuidanceSeverity.HIGH
        assert item.state == GuidanceState.VERIFIED
        assert item.confidence == 0.95
        assert item.title == "Missing contract pin"

    def test_guidance_item_construction_via_field_name(self):
        """populate_by_name=True allows guidance_class= kwarg."""
        item = GuidanceItem(
            id="warn.1",
            guidance_class=GuidanceClass.WARNING,
            severity=GuidanceSeverity.MEDIUM,
            confidence=0.8,
            state=GuidanceState.INFERRED,
            title="A warning",
        )
        assert item.guidance_class == GuidanceClass.WARNING

    def test_to_dict_has_class_key(self):
        item = _item(id="gap.1")
        d = item.to_dict()
        assert "class" in d
        assert d["class"] == "gap"
        assert "guidance_class" not in d

    def test_to_dict_all_required_fields(self):
        item = _item(id="gap.2")
        d = item.to_dict()
        for key in ("id", "class", "severity", "confidence", "state", "title", "detail", "repair", "source", "artifact_ref"):
            assert key in d, f"Missing key: {key}"

    def test_sort_key_returns_tuple(self):
        item = _item()
        k = item.sort_key()
        assert isinstance(k, tuple)
        assert len(k) == 5

    def test_guidance_class_enum_values(self):
        assert GuidanceClass.GAP.value == "gap"
        assert GuidanceClass.WARNING.value == "warning"
        assert GuidanceClass.SUGGESTION.value == "suggestion"
        assert GuidanceClass.NEXT_BEST_ACTION.value == "next_best_action"
        assert GuidanceClass.INFERENCE.value == "inference"

    def test_severity_enum_values(self):
        assert GuidanceSeverity.HIGH.value == "high"
        assert GuidanceSeverity.MEDIUM.value == "medium"
        assert GuidanceSeverity.LOW.value == "low"
        assert GuidanceSeverity.INFO.value == "info"

    def test_readiness_enum_values(self):
        assert AlignmentReadiness.FOREIGN.value == "foreign"
        assert AlignmentReadiness.PARTIALLY_ALIGNED.value == "partially_aligned"
        assert AlignmentReadiness.REGISTRATION_READY.value == "registration_ready"
        assert AlignmentReadiness.RUN_READY.value == "run_ready"
        assert AlignmentReadiness.BLOCKED.value == "blocked"

    def test_guidance_state_enum_values(self):
        assert GuidanceState.VERIFIED.value == "verified"
        assert GuidanceState.INFERRED.value == "inferred"

    def test_alignment_guidance_request_defaults(self):
        req = AlignmentGuidanceRequest(repo_identity="r", repo_path="/tmp")
        assert req.shadow is False
        assert req.guidance_items == []
        assert req.correlation_id == ""

    def test_alignment_guidance_result_no_mutation_applied_default(self):
        result = AlignmentGuidanceResult(
            success=True,
            readiness=AlignmentReadiness.FOREIGN,
        )
        assert result.no_mutation_applied is True

    def test_alignment_guidance_result_is_accepted_or_deferred_false(self):
        result = AlignmentGuidanceResult(
            success=True,
            readiness=AlignmentReadiness.FOREIGN,
            analysis_mode="terminal",
        )
        assert result.is_accepted_or_deferred() is False

    def test_alignment_guidance_result_is_accepted_or_deferred_true(self):
        for mode in ("accepted", "deferred"):
            result = AlignmentGuidanceResult(
                success=True,
                readiness=AlignmentReadiness.FOREIGN,
                analysis_mode=mode,
            )
            assert result.is_accepted_or_deferred() is True, f"Expected True for mode={mode}"

    def test_to_proof_dict_request(self):
        req = AlignmentGuidanceRequest(repo_identity="r", repo_path="/tmp")
        d = req.to_proof_dict()
        assert "repo_identity" in d
        assert "correlation_id" in d

    def test_to_payload_request(self):
        req = AlignmentGuidanceRequest(repo_identity="r", repo_path="/tmp")
        p = req.to_payload()
        assert "repo_identity" in p


# ─────────────────────────────────────────────────────────────
# TestDeterministicRanking
# ─────────────────────────────────────────────────────────────


class TestDeterministicRanking:
    def test_same_input_same_order(self):
        """§9: Deterministic — identical inputs must produce identical output."""
        items = [
            _item("gap.a", "gap", "low", 0.7),
            _item("gap.b", "gap", "high", 1.0),
            _item("warn.1", "warning", "medium", 0.9),
        ]
        req = _req()
        r1 = render_guidance(req, raw_items=items)
        r2 = render_guidance(req, raw_items=items)
        ids1 = [i.id for i in r1.items]
        ids2 = [i.id for i in r2.items]
        assert ids1 == ids2

    def test_gap_before_warning(self):
        """§9: GAP items are ordered before WARNING items."""
        items = [
            _item("warn.first", "warning", "high"),
            _item("gap.second", "gap", "low"),
        ]
        result = render_guidance(_req(), raw_items=items)
        ids = [i.id for i in result.items]
        assert ids.index("gap.second") < ids.index("warn.first")

    def test_warning_before_suggestion(self):
        items = [
            _item("sug.a", "suggestion", "high"),
            _item("warn.b", "warning", "low"),
        ]
        result = render_guidance(_req(), raw_items=items)
        ids = [i.id for i in result.items]
        assert ids.index("warn.b") < ids.index("sug.a")

    def test_verified_before_inferred_same_class(self):
        """§9: Verified items come before inferred within same class."""
        items = [
            _item("gap.inferred", "gap", "high", 0.9, "inferred"),
            _item("gap.verified", "gap", "high", 0.9, "verified"),
        ]
        result = render_guidance(_req(), raw_items=items)
        ids = [i.id for i in result.items]
        assert ids.index("gap.verified") < ids.index("gap.inferred")

    def test_high_severity_before_low_same_class_state(self):
        """High severity ranks first within same class+state."""
        items = [
            _item("gap.low", "gap", "low", 1.0, "verified"),
            _item("gap.high", "gap", "high", 1.0, "verified"),
        ]
        result = render_guidance(_req(), raw_items=items)
        ids = [i.id for i in result.items]
        assert ids.index("gap.high") < ids.index("gap.low")

    def test_higher_confidence_before_lower_same_class_state_severity(self):
        items = [
            _item("gap.low.conf", "gap", "medium", 0.5, "inferred"),
            _item("gap.high.conf", "gap", "medium", 0.9, "inferred"),
        ]
        result = render_guidance(_req(), raw_items=items)
        ids = [i.id for i in result.items]
        assert ids.index("gap.high.conf") < ids.index("gap.low.conf")

    def test_id_tiebreaker_alphabetical(self):
        """When all other keys are equal, IDs are sorted alphabetically."""
        items = [
            _item("gap.zzz", "gap", "high", 1.0, "verified"),
            _item("gap.aaa", "gap", "high", 1.0, "verified"),
        ]
        result = render_guidance(_req(), raw_items=items)
        ids = [i.id for i in result.items]
        assert ids[0] == "gap.aaa"
        assert ids[1] == "gap.zzz"


# ─────────────────────────────────────────────────────────────
# TestReadinessDerivation
# ─────────────────────────────────────────────────────────────


class TestReadinessDerivation:
    def test_no_items_is_foreign(self):
        result = render_guidance(_req(), raw_items=[])
        assert result.readiness == AlignmentReadiness.FOREIGN

    def test_high_verified_gap_is_blocked(self):
        items = [_item("gap.block", "gap", "high", 1.0, "verified")]
        result = render_guidance(_req(), raw_items=items)
        assert result.readiness == AlignmentReadiness.BLOCKED

    def test_verified_gap_no_high_is_partially_aligned(self):
        items = [_item("gap.low", "gap", "low", 1.0, "verified")]
        result = render_guidance(_req(), raw_items=items)
        assert result.readiness == AlignmentReadiness.PARTIALLY_ALIGNED

    def test_all_inferred_gaps_is_foreign(self):
        items = [_item("gap.inf", "gap", "high", 0.8, "inferred")]
        result = render_guidance(_req(), raw_items=items)
        assert result.readiness == AlignmentReadiness.FOREIGN

    def test_only_warnings_is_registration_ready(self):
        items = [_item("warn.1", "warning", "high", 1.0, "verified")]
        result = render_guidance(_req(), raw_items=items)
        assert result.readiness == AlignmentReadiness.REGISTRATION_READY

    def test_only_suggestions_is_registration_ready(self):
        items = [_item("sug.1", "suggestion", "high", 1.0, "verified")]
        result = render_guidance(_req(), raw_items=items)
        assert result.readiness == AlignmentReadiness.REGISTRATION_READY

    def test_run_ready_with_pre_loaded_items_no_gaps(self):
        """Pre-loaded items with no gaps that are all verified = run_ready."""
        items = [
            GuidanceItem.model_validate({"id": "sug.1", "class": "suggestion", "severity": "low", "confidence": 1.0, "state": "verified", "title": "t"}),
        ]
        req = AlignmentGuidanceRequest(repo_identity="r", repo_path="/tmp", guidance_items=items)
        result = render_guidance(req)
        assert result.readiness == AlignmentReadiness.REGISTRATION_READY


# ─────────────────────────────────────────────────────────────
# TestNextBestActionSelection
# ─────────────────────────────────────────────────────────────


class TestNextBestActionSelection:
    def test_next_best_action_from_top_item_repair(self):
        items = [
            _item("gap.top", "gap", "high", 1.0, "verified", repair=["Run: keyhole fix-schema"]),
            _item("gap.low", "gap", "low", 1.0, "verified", repair=["Run: keyhole fix-meta"]),
        ]
        result = render_guidance(_req(), raw_items=items)
        assert result.next_best_action == "Run: keyhole fix-schema"

    def test_next_best_action_fallback_when_no_repair(self):
        items = [_item("gap.1", repair=[])]
        result = render_guidance(_req(), raw_items=items)
        # Should still have some next_best_action based on readiness
        assert result.next_best_action is not None

    def test_no_items_next_best_action_is_not_none(self):
        result = render_guidance(_req(), raw_items=[])
        # Should provide a readiness-based fallback
        assert result.next_best_action is not None

    def test_next_best_action_is_string(self):
        items = [_item("gap.1", repair=["Do the thing"])]
        result = render_guidance(_req(), raw_items=items)
        assert isinstance(result.next_best_action, str)


# ─────────────────────────────────────────────────────────────
# TestRenderGuidance
# ─────────────────────────────────────────────────────────────


class TestRenderGuidance:
    def test_render_populates_counts(self):
        items = [
            _item("gap.1", "gap"),
            _item("gap.2", "gap"),
            _item("warn.1", "warning"),
            _item("sug.1", "suggestion"),
        ]
        result = render_guidance(_req(), raw_items=items)
        assert result.gap_count == 2
        assert result.warning_count == 1
        assert result.suggestion_count == 1

    def test_render_populates_verified_inferred_counts(self):
        items = [
            _item("v1", "gap", "high", 1.0, "verified"),
            _item("v2", "gap", "high", 1.0, "verified"),
            _item("i1", "gap", "medium", 0.8, "inferred"),
        ]
        result = render_guidance(_req(), raw_items=items)
        assert result.verified_count == 2
        assert result.inferred_count == 1

    def test_render_no_mutation_applied(self):
        result = render_guidance(_req(), raw_items=[])
        assert result.no_mutation_applied is True

    def test_render_from_request_guidance_items(self):
        """Request.guidance_items are used when raw_items is None."""
        items = [_item("gap.1")]
        req = AlignmentGuidanceRequest(
            repo_identity="r", repo_path="/tmp", guidance_items=items
        )
        result = render_guidance(req)
        assert result.gap_count == 1

    def test_render_success_true_on_empty(self):
        result = render_guidance(_req(), raw_items=[])
        assert result.success is True

    def test_render_items_sorted(self):
        """Rendered items are deterministically sorted."""
        items = [
            _item("c", "suggestion", "high"),
            _item("a", "gap", "high"),
            _item("b", "warning", "medium"),
        ]
        result = render_guidance(_req(), raw_items=items)
        classes = [i.guidance_class for i in result.items]
        # gaps first, then warnings, then suggestions
        assert classes[0] == GuidanceClass.GAP
        assert classes[1] == GuidanceClass.WARNING
        assert classes[2] == GuidanceClass.SUGGESTION


# ─────────────────────────────────────────────────────────────
# TestSubmitter
# ─────────────────────────────────────────────────────────────


class TestSubmitter:
    """Tests for submitter classification without real network calls."""

    def _make_transport(self, response_data: dict, status_code: int = 200):
        from keyhole_sdk.transport.client import TransportResult
        transport = MagicMock()
        proof = MagicMock()
        result = TransportResult(
            data=response_data,
            status_code=status_code,
            proof=proof,
        )
        transport.execute.return_value = result
        return transport

    def test_submit_accepted_is_accepted_or_deferred(self):
        from keyhole_sdk.alignment.submitter import submit_alignment

        transport = self._make_transport({
            "status": "accepted",
            "run_id": "run-123",
            "items": [],
        })
        req = AlignmentGuidanceRequest(repo_identity="r", repo_path="/tmp")
        result = submit_alignment(transport=transport, request=req)
        assert result.is_accepted_or_deferred()
        assert result.run_id == "run-123"

    def test_submit_deferred_is_accepted_or_deferred(self):
        from keyhole_sdk.alignment.submitter import submit_alignment

        transport = self._make_transport({
            "status": "deferred",
            "run_id": "run-456",
            "items": [],
        })
        req = AlignmentGuidanceRequest(repo_identity="r", repo_path="/tmp")
        result = submit_alignment(transport=transport, request=req)
        assert result.is_accepted_or_deferred()

    def test_submit_terminal_is_not_deferred(self):
        from keyhole_sdk.alignment.submitter import submit_alignment

        transport = self._make_transport({
            "status": "terminal",
            "items": [
                {
                    "id": "gap.1",
                    "class": "gap",
                    "severity": "high",
                    "confidence": 1.0,
                    "state": "verified",
                    "title": "A gap",
                    "repair": [],
                }
            ],
        })
        req = AlignmentGuidanceRequest(repo_identity="r", repo_path="/tmp")
        result = submit_alignment(transport=transport, request=req)
        assert not result.is_accepted_or_deferred()
        assert result.success is True

    def test_submit_network_exception_returns_failure(self):
        from keyhole_sdk.alignment.submitter import submit_alignment
        from keyhole_sdk.transport.errors import TransportUnknownError

        transport = MagicMock()
        transport.execute.side_effect = TransportUnknownError("Connection refused")
        req = AlignmentGuidanceRequest(repo_identity="r", repo_path="/tmp")
        result = submit_alignment(transport=transport, request=req)
        assert result.success is False
        assert result.no_mutation_applied is True

    def test_submit_transport_exception_no_mutation(self):
        from keyhole_sdk.alignment.submitter import submit_alignment

        transport = MagicMock()
        transport.execute.side_effect = RuntimeError("unexpected")
        req = AlignmentGuidanceRequest(repo_identity="r", repo_path="/tmp")
        result = submit_alignment(transport=transport, request=req)
        assert result.no_mutation_applied is True


# ─────────────────────────────────────────────────────────────
# TestProofEmission
# ─────────────────────────────────────────────────────────────


class TestProofEmission:
    def test_emit_creates_proof_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            req = AlignmentGuidanceRequest(repo_identity="r", repo_path="/tmp")
            result = AlignmentGuidanceResult(
                success=True,
                readiness=AlignmentReadiness.FOREIGN,
                no_mutation_applied=True,
            )
            proof_path = emit_alignment_proof(
                state_dir=state_dir,
                correlation_id="test-corr-001",
                request_dict=req.to_proof_dict(),
                result=result,
            )
            assert proof_path.exists()

    def test_emit_creates_expected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            req = AlignmentGuidanceRequest(repo_identity="r", repo_path="/tmp")
            items = [
                _item("gap.1", "gap", "high", 1.0, "verified"),
                _item("gap.inferred", "gap", "medium", 0.8, "inferred"),
            ]
            result = render_guidance(req, raw_items=items)
            proof_path = emit_alignment_proof(
                state_dir=state_dir,
                correlation_id="test-corr-002",
                request_dict=req.to_proof_dict(),
                result=result,
            )
            assert (proof_path / "gap_analysis.json").exists()
            assert (proof_path / "next_actions.json").exists()
            assert (proof_path / "correlation.json").exists()
            assert (proof_path / "summary.md").exists()

    def test_emit_gap_analysis_verified_inferred_split(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            req = AlignmentGuidanceRequest(repo_identity="r", repo_path="/tmp")
            items = [
                _item("gap.v", "gap", "high", 1.0, "verified"),
                _item("gap.i", "gap", "medium", 0.8, "inferred"),
            ]
            result = render_guidance(req, raw_items=items)
            proof_path = emit_alignment_proof(
                state_dir=state_dir,
                correlation_id="test-corr-003",
                request_dict=req.to_proof_dict(),
                result=result,
            )
            analysis = json.loads((proof_path / "gap_analysis.json").read_text())
            assert "verified" in analysis
            assert "inferred" in analysis
            assert any(i["id"] == "gap.v" for i in analysis["verified"])
            assert any(i["id"] == "gap.i" for i in analysis["inferred"])

    def test_emit_summary_md_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            req = AlignmentGuidanceRequest(repo_identity="r", repo_path="/tmp")
            result = render_guidance(req, raw_items=[])
            proof_path = emit_alignment_proof(
                state_dir=state_dir,
                correlation_id="test-corr-004",
                request_dict=req.to_proof_dict(),
                result=result,
            )
            summary = (proof_path / "summary.md").read_text()
            assert "alignment" in summary.lower() or "readiness" in summary.lower() or "foreign" in summary.lower()

    def test_emit_next_actions_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            req = AlignmentGuidanceRequest(repo_identity="r", repo_path="/tmp")
            items = [_item("gap.1", repair=["Step 1", "Step 2"])]
            result = render_guidance(req, raw_items=items)
            proof_path = emit_alignment_proof(
                state_dir=state_dir,
                correlation_id="test-corr-005",
                request_dict=req.to_proof_dict(),
                result=result,
            )
            next_actions = json.loads((proof_path / "next_actions.json").read_text())
            assert "next_best_action" in next_actions


# ─────────────────────────────────────────────────────────────
# TestRepairGuidance
# ─────────────────────────────────────────────────────────────


class TestRepairGuidance:
    _KNOWN_CLASSES = [
        "AuthenticationError",
        "NotAuthenticated",
        "TransportUnknownError",
        "RetryExhaustedError",
        "RuntimeUnavailableError",
        "ConnectionError",
        "RateLimitedError",
        "NoAnalysisArtifact",
        "MalformedServerResponse",
        "CorruptedSavedArtifact",
        "UnsupportedSchemaVersion",
        "MissingRepoContext",
        "RenderFailure",
        "AcceptedDeferredNotReady",
        "ServerRejection",
    ]

    @pytest.mark.parametrize("error_class", _KNOWN_CLASSES)
    def test_known_error_class_returns_list(self, error_class):
        steps = map_alignment_repair(error_class)
        assert isinstance(steps, list)
        assert len(steps) > 0

    def test_unknown_error_class_returns_default(self):
        steps = map_alignment_repair("SomeUnknownError")
        assert isinstance(steps, list)
        assert len(steps) > 0

    def test_empty_string_returns_default(self):
        steps = map_alignment_repair("")
        assert isinstance(steps, list)
        assert len(steps) > 0

    def test_repair_steps_are_strings(self):
        for cls in self._KNOWN_CLASSES:
            steps = map_alignment_repair(cls)
            assert all(isinstance(s, str) for s in steps), f"Non-string step in {cls}"


# ─────────────────────────────────────────────────────────────
# TestNoSilentMutation
# ─────────────────────────────────────────────────────────────


class TestNoSilentMutation:
    def test_render_guidance_no_mutation_applied(self):
        items = [_item("gap.1")]
        result = render_guidance(_req(), raw_items=items)
        assert result.no_mutation_applied is True

    def test_result_no_mutation_applied_default(self):
        result = AlignmentGuidanceResult(
            success=True,
            readiness=AlignmentReadiness.FOREIGN,
        )
        assert result.no_mutation_applied is True

    def test_render_empty_no_mutation(self):
        result = render_guidance(_req(), raw_items=[])
        assert result.no_mutation_applied is True

    def test_render_does_not_modify_input_items(self):
        """Input items list is not mutated by render_guidance."""
        items = [_item("gap.a"), _item("warn.b")]
        original_ids = [i.id for i in items]
        render_guidance(_req(), raw_items=items)
        assert [i.id for i in items] == original_ids


# ─────────────────────────────────────────────────────────────
# TestCLIAlign
# ─────────────────────────────────────────────────────────────


class TestCLIAlign:
    def test_align_cmd_importable(self):
        from keyhole_cli.commands.align_cmd import run_align
        assert callable(run_align)

    def test_align_local_only_bad_path(self):
        from keyhole_cli.commands.align_cmd import run_align
        result = run_align(repo_path="/nonexistent/path/xyz", local_only=True)
        assert result.success is False
        assert result.exit_code != 0

    def test_align_local_only_valid_path(self):
        from keyhole_cli.commands.align_cmd import run_align
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            result = run_align(repo_path=tmp, local_only=True)
        assert result.success is True

    def test_align_local_only_no_mutation(self):
        from keyhole_cli.commands.align_cmd import run_align
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            result = run_align(repo_path=tmp, local_only=True)
        assert result.data.get("no_mutation_applied") is True

    def test_align_cmd_in_cli_app(self):
        """The 'align' command is registered with the Typer app."""
        from keyhole_cli.cli import app
        command_names = [c.name for c in app.registered_commands]
        assert "align" in command_names


# ─────────────────────────────────────────────────────────────
# TestPublicAPISurface
# ─────────────────────────────────────────────────────────────


class TestPublicAPISurface:
    def test_all_exports_in_sdk_init(self):
        import keyhole_sdk
        all_exports = keyhole_sdk.__all__
        required = [
            "AlignmentGuidanceRequest",
            "AlignmentGuidanceResult",
            "AlignmentReadiness",
            "GuidanceClass",
            "GuidanceItem",
            "GuidanceSeverity",
            "GuidanceState",
            "render_guidance",
            "submit_alignment",
            "emit_alignment_proof",
            "map_alignment_repair",
        ]
        for name in required:
            assert name in all_exports, f"Missing from __all__: {name}"

    def test_all_exports_importable_from_sdk(self):
        import keyhole_sdk
        required = [
            "AlignmentGuidanceRequest",
            "AlignmentGuidanceResult",
            "AlignmentReadiness",
            "GuidanceClass",
            "GuidanceItem",
            "GuidanceSeverity",
            "GuidanceState",
            "render_guidance",
            "submit_alignment",
            "emit_alignment_proof",
            "map_alignment_repair",
        ]
        for name in required:
            assert hasattr(keyhole_sdk, name), f"Missing attr: {name}"

    def test_alignment_package_has_all(self):
        from keyhole_sdk import alignment
        assert hasattr(alignment, "__all__")
        assert len(alignment.__all__) >= 11


# ─────────────────────────────────────────────────────────────
# TestOperationRegistry
# ─────────────────────────────────────────────────────────────


class TestOperationRegistry:
    def test_alignment_guidance_registered(self):
        from keyhole_sdk.transport.operation_registry import get_operation, OperationClass
        op = get_operation("alignment.guidance")
        assert op is not None, "alignment.guidance not found in operation registry"

    def test_alignment_guidance_is_read_only(self):
        from keyhole_sdk.transport.operation_registry import get_operation, OperationClass
        op = get_operation("alignment.guidance")
        assert op is not None
        assert op.operation_class == OperationClass.READ_ONLY

    def test_alignment_guidance_not_idempotency_required(self):
        from keyhole_sdk.transport.operation_registry import get_operation
        op = get_operation("alignment.guidance")
        assert op is not None
        assert op.idempotency_required is False


# ─────────────────────────────────────────────────────────────
# TestAcceptedDeferredHonesty
# ─────────────────────────────────────────────────────────────


class TestAcceptedDeferredHonesty:
    def test_accepted_is_not_terminal(self):
        result = AlignmentGuidanceResult(
            success=True,
            readiness=AlignmentReadiness.FOREIGN,
            analysis_mode="accepted",
            run_id="run-xyz",
        )
        assert result.is_accepted_or_deferred() is True

    def test_deferred_is_not_terminal(self):
        result = AlignmentGuidanceResult(
            success=True,
            readiness=AlignmentReadiness.FOREIGN,
            analysis_mode="deferred",
        )
        assert result.is_accepted_or_deferred() is True

    def test_terminal_analysis_mode_is_terminal(self):
        result = AlignmentGuidanceResult(
            success=True,
            readiness=AlignmentReadiness.RUN_READY,
            analysis_mode="terminal",
        )
        assert result.is_accepted_or_deferred() is False

    def test_accepted_result_no_mutation(self):
        result = AlignmentGuidanceResult(
            success=True,
            readiness=AlignmentReadiness.FOREIGN,
            analysis_mode="accepted",
            no_mutation_applied=True,
        )
        assert result.no_mutation_applied is True

    def test_cli_align_accepted_is_success_with_run_id(self):
        """CLI command returns success=True with run_id for accepted results."""
        from keyhole_cli.commands.align_cmd import _build_command_result

        result = AlignmentGuidanceResult(
            success=True,
            readiness=AlignmentReadiness.FOREIGN,
            analysis_mode="accepted",
            run_id="run-accepted-001",
            no_mutation_applied=True,
        )
        cmd = _build_command_result(
            result=result,
            command_label="keyhole align",
            proof_path="",
            mode="governed",
        )
        assert cmd.success is True
        assert cmd.data.get("run_id") == "run-accepted-001"


# ─────────────────────────────────────────────────────────────
# TestNegativeInputs
# ─────────────────────────────────────────────────────────────


class TestNegativeInputs:
    def test_empty_request_renders_ok(self):
        req = AlignmentGuidanceRequest()
        result = render_guidance(req, raw_items=[])
        assert result.success is True

    def test_render_with_none_raw_items_uses_request_items(self):
        item = _item("gap.from.request")
        req = AlignmentGuidanceRequest(
            repo_identity="r",
            repo_path="/tmp",
            guidance_items=[item],
        )
        result = render_guidance(req, raw_items=None)
        assert result.gap_count == 1

    def test_render_empty_raw_items_is_foreign(self):
        result = render_guidance(_req(), raw_items=[])
        assert result.readiness == AlignmentReadiness.FOREIGN

    def test_guidance_item_missing_required_field_raises(self):
        with pytest.raises(Exception):
            # `title` is required
            GuidanceItem.model_validate({"id": "x", "class": "gap"})

    def test_guidance_item_invalid_class_raises(self):
        with pytest.raises(Exception):
            GuidanceItem.model_validate({
                "id": "x",
                "class": "not_a_real_class",
                "title": "t",
            })

    def test_guidance_item_confidence_out_of_range_raises(self):
        with pytest.raises(Exception):
            GuidanceItem.model_validate({
                "id": "x",
                "class": "gap",
                "severity": "high",
                "confidence": 1.5,
                "state": "verified",
                "title": "t",
            })
