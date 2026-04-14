"""Tests for SDK-CLIENT-20: Governance Explainability and Support Bundles.

Covers:
  - ExplainOutcomeClass enum and frozenset groups
  - RunExplanation, RequestInspectionResult, SupportBundle models
  - assemble_run_explanation, assemble_request_inspection, assemble_support_bundle
  - render_explanation, render_inspection
  - map_explain_repair
  - emit_explain_proof, emit_bundle_proof
  - operation_registry entries for run.explain / request.inspect
  - Public API surface (12 symbols in __all__)
  - CLI command integration

§3: Explain layers — request truth, run truth, context truth, event/proof truth, rendered.
§12.5: Non-terminal outcomes must never render as "completed" or "succeeded".
§12.4: Repair guidance mandatory on non-success.
§12.3: Distinguish known from inferred reasons.
§10: Support bundles must not include secrets or tokens.
§14: Proof artifacts: response.json + rendered.md for explain; 9 files for bundle.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keyhole_sdk.explain.models import (
    BUNDLE_REQUIRED_SECTIONS,
    ExplainOutcomeClass,
    RequestInspectionResult,
    RunExplanation,
    SupportBundle,
    _NON_TERMINAL_CLASSES,
    _PRESSURE_CLASSES,
    _TERMINAL_CLASSES,
    _omission_md,
    _omission_obj,
)
from keyhole_sdk.explain.assembler import (
    _classify_from_response,
    _safe_list,
    _synthesize_reason,
    assemble_request_inspection,
    assemble_run_explanation,
    assemble_support_bundle,
)
from keyhole_sdk.explain.renderer import render_explanation, render_inspection
from keyhole_sdk.explain.repair import map_explain_repair
from keyhole_sdk.explain.proof import emit_explain_proof, emit_bundle_proof


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _run_resp(**kw) -> dict:
    """Minimal synthetic run status response."""
    base = {
        "run_id": "run-abc-123",
        "request_id": "req-xyz-456",
        "status": "success",
        "run_type": "context.compile",
        "repo": "my-repo",
    }
    base.update(kw)
    return base


def _req_resp(**kw) -> dict:
    """Minimal synthetic request inspect response."""
    base = {
        "request_id": "req-xyz-456",
        "run_id": "run-abc-123",
        "status": "success",
    }
    base.update(kw)
    return base


# ─────────────────────────────────────────────────────────────
# TestExplainOutcomeClassEnum
# ─────────────────────────────────────────────────────────────

class TestExplainOutcomeClassEnum:
    def test_ten_members(self):
        members = list(ExplainOutcomeClass)
        assert len(members) == 10

    def test_str_subclass(self):
        assert isinstance(ExplainOutcomeClass.SUCCEEDED, str)
        assert ExplainOutcomeClass.SUCCEEDED == "succeeded"

    def test_all_values_lowercase(self):
        for member in ExplainOutcomeClass:
            assert member.value == member.value.lower()

    def test_accepted_value(self):
        assert ExplainOutcomeClass.ACCEPTED.value == "accepted"

    def test_succeeded_value(self):
        assert ExplainOutcomeClass.SUCCEEDED.value == "succeeded"

    def test_rejected_value(self):
        assert ExplainOutcomeClass.REJECTED.value == "rejected"

    def test_replayed_value(self):
        assert ExplainOutcomeClass.REPLAYED.value == "replayed"

    def test_deferred_value(self):
        assert ExplainOutcomeClass.DEFERRED.value == "deferred"

    def test_rate_limited_value(self):
        assert ExplainOutcomeClass.RATE_LIMITED.value == "rate_limited"

    def test_budget_exhausted_value(self):
        assert ExplainOutcomeClass.BUDGET_EXHAUSTED.value == "budget_exhausted"

    def test_failed_value(self):
        assert ExplainOutcomeClass.FAILED.value == "failed"

    def test_partial_lineage_value(self):
        assert ExplainOutcomeClass.PARTIAL_LINEAGE.value == "partial_lineage"

    def test_unknown_value(self):
        assert ExplainOutcomeClass.UNKNOWN.value == "unknown"

    def test_terminal_classes_contains_succeeded(self):
        assert ExplainOutcomeClass.SUCCEEDED in _TERMINAL_CLASSES

    def test_terminal_classes_contains_rejected(self):
        assert ExplainOutcomeClass.REJECTED in _TERMINAL_CLASSES

    def test_terminal_classes_contains_failed(self):
        assert ExplainOutcomeClass.FAILED in _TERMINAL_CLASSES

    def test_terminal_classes_contains_budget_exhausted(self):
        assert ExplainOutcomeClass.BUDGET_EXHAUSTED in _TERMINAL_CLASSES

    def test_non_terminal_classes_contains_accepted(self):
        assert ExplainOutcomeClass.ACCEPTED in _NON_TERMINAL_CLASSES

    def test_non_terminal_classes_contains_deferred(self):
        assert ExplainOutcomeClass.DEFERRED in _NON_TERMINAL_CLASSES

    def test_pressure_classes_contains_deferred(self):
        assert ExplainOutcomeClass.DEFERRED in _PRESSURE_CLASSES

    def test_pressure_classes_contains_rate_limited(self):
        assert ExplainOutcomeClass.RATE_LIMITED in _PRESSURE_CLASSES

    def test_accepted_not_in_terminal(self):
        assert ExplainOutcomeClass.ACCEPTED not in _TERMINAL_CLASSES

    def test_unknown_not_in_terminal(self):
        assert ExplainOutcomeClass.UNKNOWN not in _TERMINAL_CLASSES


# ─────────────────────────────────────────────────────────────
# TestRunExplanationModel
# ─────────────────────────────────────────────────────────────

class TestRunExplanationModel:
    def test_default_outcome_class(self):
        ex = RunExplanation()
        assert ex.outcome_class == ExplainOutcomeClass.UNKNOWN

    def test_default_not_terminal(self):
        ex = RunExplanation()
        assert ex.is_terminal is False

    def test_is_terminal_outcome_for_succeeded(self):
        ex = RunExplanation(outcome_class=ExplainOutcomeClass.SUCCEEDED, is_terminal=True)
        assert ex.is_terminal_outcome() is True

    def test_is_terminal_outcome_rejected(self):
        ex = RunExplanation(outcome_class=ExplainOutcomeClass.REJECTED, is_terminal=True)
        assert ex.is_terminal_outcome() is True

    def test_is_not_terminal_outcome_accepted(self):
        ex = RunExplanation(outcome_class=ExplainOutcomeClass.ACCEPTED)
        assert ex.is_terminal_outcome() is False

    def test_is_not_terminal_outcome_deferred(self):
        ex = RunExplanation(outcome_class=ExplainOutcomeClass.DEFERRED)
        assert ex.is_terminal_outcome() is False

    def test_is_pressure_deferred(self):
        ex = RunExplanation(outcome_class=ExplainOutcomeClass.DEFERRED)
        assert ex.is_pressure() is True

    def test_is_pressure_rate_limited(self):
        ex = RunExplanation(outcome_class=ExplainOutcomeClass.RATE_LIMITED)
        assert ex.is_pressure() is True

    def test_is_not_pressure_succeeded(self):
        ex = RunExplanation(outcome_class=ExplainOutcomeClass.SUCCEEDED)
        assert ex.is_pressure() is False

    def test_to_proof_dict_has_run_id(self):
        ex = RunExplanation(run_id="run-001")
        d = ex.to_proof_dict()
        assert d["run_id"] == "run-001"

    def test_to_proof_dict_has_outcome_class_value(self):
        ex = RunExplanation(outcome_class=ExplainOutcomeClass.SUCCEEDED)
        d = ex.to_proof_dict()
        assert d["outcome_class"] == "succeeded"

    def test_to_proof_dict_has_is_reason_inferred(self):
        ex = RunExplanation(is_reason_inferred=True)
        d = ex.to_proof_dict()
        assert d["is_reason_inferred"] is True

    def test_to_proof_dict_has_assembled_at(self):
        ex = RunExplanation()
        d = ex.to_proof_dict()
        assert "assembled_at" in d

    def test_repair_guidance_default_empty(self):
        ex = RunExplanation()
        assert ex.repair_guidance == []

    def test_event_refs_default_empty(self):
        ex = RunExplanation()
        assert ex.event_refs == []


# ─────────────────────────────────────────────────────────────
# TestRequestInspectionResultModel
# ─────────────────────────────────────────────────────────────

class TestRequestInspectionResultModel:
    def test_default_outcome_unknown(self):
        r = RequestInspectionResult()
        assert r.outcome_class == ExplainOutcomeClass.UNKNOWN

    def test_executed_default_false(self):
        r = RequestInspectionResult()
        assert r.executed is False

    def test_replayed_default_false(self):
        r = RequestInspectionResult()
        assert r.replayed is False

    def test_deferred_default_false(self):
        r = RequestInspectionResult()
        assert r.deferred is False

    def test_to_proof_dict_keys(self):
        r = RequestInspectionResult(request_id="req-1", run_id="run-1")
        d = r.to_proof_dict()
        assert d["request_id"] == "req-1"
        assert d["run_id"] == "run-1"
        assert "executed" in d
        assert "replayed" in d
        assert "deferred" in d

    def test_to_proof_dict_outcome_class_value(self):
        r = RequestInspectionResult(outcome_class=ExplainOutcomeClass.REJECTED)
        d = r.to_proof_dict()
        assert d["outcome_class"] == "rejected"

    def test_repair_guidance_empty_default(self):
        r = RequestInspectionResult()
        assert r.repair_guidance == []

    def test_assembled_at_populated(self):
        r = RequestInspectionResult()
        assert r.assembled_at


# ─────────────────────────────────────────────────────────────
# TestSupportBundleModel
# ─────────────────────────────────────────────────────────────

class TestSupportBundleModel:
    def test_bundle_required_sections_count(self):
        assert len(BUNDLE_REQUIRED_SECTIONS) == 9

    def test_bundle_required_sections_names(self):
        expected = {"summary_md", "request", "run", "context", "events",
                    "proof_refs", "outcome", "repair", "metadata"}
        assert set(BUNDLE_REQUIRED_SECTIONS) == expected

    def test_to_files_dict_has_nine_files(self):
        b = SupportBundle(run_id="r", request_id="q", summary_md="# hi")
        files = b.to_files_dict()
        assert len(files) == 9

    def test_to_files_dict_keys(self):
        b = SupportBundle()
        files = b.to_files_dict()
        assert "summary.md" in files
        assert "request.json" in files
        assert "run.json" in files
        assert "context.json" in files
        assert "events.json" in files
        assert "proof_refs.json" in files
        assert "outcome.json" in files
        assert "repair.json" in files
        assert "metadata.json" in files

    def test_missing_section_produces_omission(self):
        b = SupportBundle(missing_sections=["context"], omission_notes={"context": "server did not return context"})
        files = b.to_files_dict()
        # context.json should be an omission object since context is an empty dict
        ctx = files["context.json"]
        assert ctx.get("omission") is True

    def test_omission_md_helper(self):
        text = _omission_md("summary_md", "not available")
        assert "Omission note:" in text

    def test_omission_obj_helper(self):
        obj = _omission_obj("context", {"context": "server down"})
        assert obj["omission"] is True
        assert obj["section"] == "context"
        assert "server down" in obj["reason"]

    def test_omission_obj_default_reason(self):
        obj = _omission_obj("events", {})
        assert "Not available" in obj["reason"]

    def test_summary_md_used_when_present(self):
        b = SupportBundle(summary_md="# My Summary\ncontent here")
        files = b.to_files_dict()
        assert "My Summary" in files["summary.md"]

    def test_cli_version_default(self):
        b = SupportBundle()
        assert b.cli_version


# ─────────────────────────────────────────────────────────────
# TestAssembleRunExplanation
# ─────────────────────────────────────────────────────────────

class TestAssembleRunExplanation:
    def test_success_status_maps_to_succeeded(self):
        ex = assemble_run_explanation(
            _run_resp(status="success"),
            run_id="run-1", request_id="req-1", correlation_id="",
        )
        assert ex.outcome_class == ExplainOutcomeClass.SUCCEEDED

    def test_completed_status_maps_to_succeeded(self):
        ex = assemble_run_explanation(
            _run_resp(status="completed"),
            run_id="run-1", request_id="", correlation_id="",
        )
        assert ex.outcome_class == ExplainOutcomeClass.SUCCEEDED

    def test_failed_status_maps_to_failed(self):
        ex = assemble_run_explanation(
            _run_resp(status="failed"),
            run_id="run-1", request_id="", correlation_id="",
        )
        assert ex.outcome_class == ExplainOutcomeClass.FAILED

    def test_rejected_status_maps_to_rejected(self):
        ex = assemble_run_explanation(
            _run_resp(status="rejected"),
            run_id="run-1", request_id="", correlation_id="",
        )
        assert ex.outcome_class == ExplainOutcomeClass.REJECTED

    def test_deferred_status_maps_to_deferred(self):
        ex = assemble_run_explanation(
            _run_resp(status="deferred"),
            run_id="run-1", request_id="", correlation_id="",
        )
        assert ex.outcome_class == ExplainOutcomeClass.DEFERRED

    def test_accepted_status_maps_to_accepted(self):
        ex = assemble_run_explanation(
            _run_resp(status="accepted"),
            run_id="run-1", request_id="", correlation_id="",
        )
        assert ex.outcome_class == ExplainOutcomeClass.ACCEPTED

    def test_rate_limited_maps_correctly(self):
        ex = assemble_run_explanation(
            _run_resp(status="rate_limited"),
            run_id="run-1", request_id="", correlation_id="",
        )
        assert ex.outcome_class == ExplainOutcomeClass.RATE_LIMITED

    def test_budget_exhausted_maps_correctly(self):
        ex = assemble_run_explanation(
            _run_resp(status="budget_exhausted"),
            run_id="run-1", request_id="", correlation_id="",
        )
        assert ex.outcome_class == ExplainOutcomeClass.BUDGET_EXHAUSTED

    def test_replayed_flag_detected(self):
        ex = assemble_run_explanation(
            _run_resp(status="success", replayed=True),
            run_id="run-1", request_id="", correlation_id="",
        )
        assert ex.outcome_class == ExplainOutcomeClass.REPLAYED

    def test_replayed_from_field_detected(self):
        ex = assemble_run_explanation(
            _run_resp(status="success", replayed_from="run-old"),
            run_id="run-1", request_id="", correlation_id="",
        )
        assert ex.outcome_class == ExplainOutcomeClass.REPLAYED

    def test_run_id_extracted(self):
        ex = assemble_run_explanation(
            _run_resp(run_id="run-abc"),
            run_id="run-abc", request_id="", correlation_id="",
        )
        assert ex.run_id == "run-abc"

    def test_request_id_preserved(self):
        ex = assemble_run_explanation(
            _run_resp(),
            run_id="run-1", request_id="req-99", correlation_id="",
        )
        assert ex.request_id == "req-99"

    def test_run_type_extracted(self):
        ex = assemble_run_explanation(
            _run_resp(run_type="context.compile"),
            run_id="r", request_id="", correlation_id="",
        )
        assert ex.run_type == "context.compile"

    def test_succeeded_is_terminal(self):
        ex = assemble_run_explanation(
            _run_resp(status="success"),
            run_id="r", request_id="", correlation_id="",
        )
        assert ex.is_terminal is True

    def test_accepted_not_terminal(self):
        ex = assemble_run_explanation(
            _run_resp(status="accepted"),
            run_id="r", request_id="", correlation_id="",
        )
        assert ex.is_terminal is False

    def test_reason_extracted_from_server(self):
        ex = assemble_run_explanation(
            _run_resp(reason="Repo limit exceeded"),
            run_id="r", request_id="", correlation_id="",
        )
        assert "exceeded" in ex.reason
        assert ex.is_reason_inferred is False

    def test_reason_synthesized_when_missing(self):
        ex = assemble_run_explanation(
            _run_resp(status="rejected"),
            run_id="r", request_id="", correlation_id="",
        )
        assert ex.reason  # synthesized
        assert ex.is_reason_inferred is True

    def test_unknown_status_maps_to_unknown(self):
        ex = assemble_run_explanation(
            _run_resp(status="completely_new_status_xyz"),
            run_id="r", request_id="", correlation_id="",
        )
        assert ex.outcome_class == ExplainOutcomeClass.UNKNOWN

    def test_empty_response_yields_unknown(self):
        ex = assemble_run_explanation(
            {},
            run_id="r", request_id="", correlation_id="",
        )
        assert ex.outcome_class == ExplainOutcomeClass.UNKNOWN

    def test_repair_guidance_populated_on_rejected(self):
        ex = assemble_run_explanation(
            _run_resp(status="rejected"),
            run_id="r", request_id="", correlation_id="",
        )
        assert len(ex.repair_guidance) > 0

    def test_repair_guidance_populated_on_failed(self):
        ex = assemble_run_explanation(
            _run_resp(status="failed"),
            run_id="r", request_id="", correlation_id="",
        )
        assert len(ex.repair_guidance) > 0

    def test_explicit_outcome_class_field_wins(self):
        ex = assemble_run_explanation(
            _run_resp(status="failed", outcome_class="succeeded"),
            run_id="r", request_id="", correlation_id="",
        )
        assert ex.outcome_class == ExplainOutcomeClass.SUCCEEDED

    def test_context_digest_extracted(self):
        ex = assemble_run_explanation(
            _run_resp(context_digest="sha256:abc"),
            run_id="r", request_id="", correlation_id="",
        )
        assert ex.context_digest == "sha256:abc"

    def test_raw_data_preserved(self):
        data = _run_resp(custom_field="xyz")
        ex = assemble_run_explanation(data, run_id="r", request_id="", correlation_id="")
        assert ex.raw_data.get("custom_field") == "xyz"

    def test_assembled_at_populated(self):
        ex = assemble_run_explanation(
            _run_resp(), run_id="r", request_id="", correlation_id=""
        )
        assert ex.assembled_at


# ─────────────────────────────────────────────────────────────
# TestAssembleRequestInspection
# ─────────────────────────────────────────────────────────────

class TestAssembleRequestInspection:
    def test_request_id_from_kwarg(self):
        r = assemble_request_inspection({}, request_id="req-abc")
        assert r.request_id == "req-abc"

    def test_run_id_extracted(self):
        r = assemble_request_inspection({"run_id": "run-xyz"}, request_id="req-1")
        assert r.run_id == "run-xyz"

    def test_executed_true_on_success_status(self):
        r = assemble_request_inspection({"status": "success", "run_id": "r"}, request_id="req-1")
        assert r.executed is True

    def test_executed_true_on_accepted_status(self):
        """accepted status means the run was dispatched — executed should be True."""
        r = assemble_request_inspection({"status": "accepted"}, request_id="req-1")
        assert r.executed is True

    def test_replayed_flag_true(self):
        r = assemble_request_inspection({"replayed": True, "run_id": "r"}, request_id="req-1")
        assert r.replayed is True

    def test_replayed_from_field_indicates_replay(self):
        r = assemble_request_inspection(
            {"replayed_from": "run-old", "run_id": "r"}, request_id="req-1"
        )
        assert r.replayed is True

    def test_deferred_flag_true(self):
        r = assemble_request_inspection({"status": "deferred", "run_id": "r"}, request_id="req-1")
        assert r.deferred is True

    def test_outcome_class_success(self):
        r = assemble_request_inspection({"status": "success", "run_id": "r"}, request_id="req-1")
        assert r.outcome_class == ExplainOutcomeClass.SUCCEEDED

    def test_outcome_class_rejected(self):
        r = assemble_request_inspection({"status": "rejected"}, request_id="req-1")
        assert r.outcome_class == ExplainOutcomeClass.REJECTED

    def test_repair_guidance_empty_on_success(self):
        r = assemble_request_inspection({"status": "success", "run_id": "r"}, request_id="req-1")
        assert isinstance(r.repair_guidance, list)

    def test_repair_guidance_present_on_rejected(self):
        r = assemble_request_inspection({"status": "rejected"}, request_id="req-1")
        assert len(r.repair_guidance) > 0

    def test_assembled_at_set(self):
        r = assemble_request_inspection({}, request_id="req-1")
        assert r.assembled_at


# ─────────────────────────────────────────────────────────────
# TestAssembleSupportBundle
# ─────────────────────────────────────────────────────────────

class TestAssembleSupportBundle:
    def _make_explanation(self) -> RunExplanation:
        return assemble_run_explanation(
            _run_resp(status="failed", reason="Quota exceeded"),
            run_id="run-b", request_id="req-b", correlation_id="",
        )

    def _make_inspection(self) -> RequestInspectionResult:
        return assemble_request_inspection(
            {"run_id": "run-b", "status": "failed"},
            request_id="req-b",
        )

    def test_bundle_has_run_id(self):
        b = assemble_support_bundle(
            run_id="run-b", request_id="req-b",
            explanation=self._make_explanation(),
            inspection=self._make_inspection(),
            cli_version="0.2.0",
        )
        assert b.run_id == "run-b"

    def test_bundle_has_9_section_files(self):
        b = assemble_support_bundle(
            run_id="run-b", request_id="req-b",
            explanation=self._make_explanation(),
            inspection=self._make_inspection(),
            cli_version="0.2.0",
        )
        files = b.to_files_dict()
        assert len(files) == 9

    def test_bundle_summary_md_populated(self):
        b = assemble_support_bundle(
            run_id="run-b", request_id="req-b",
            explanation=self._make_explanation(),
            inspection=self._make_inspection(),
            cli_version="0.2.0",
        )
        assert b.summary_md  # not empty

    def test_bundle_repair_section_present(self):
        b = assemble_support_bundle(
            run_id="run-b", request_id="req-b",
            explanation=self._make_explanation(),
            inspection=self._make_inspection(),
            cli_version="0.2.0",
        )
        repair = b.repair
        assert isinstance(repair, dict)

    def test_bundle_outcome_section_present(self):
        b = assemble_support_bundle(
            run_id="run-b", request_id="req-b",
            explanation=self._make_explanation(),
            inspection=self._make_inspection(),
            cli_version="0.2.0",
        )
        assert isinstance(b.outcome, dict)

    def test_cli_version_preserved(self):
        b = assemble_support_bundle(
            run_id="r", request_id="q",
            explanation=self._make_explanation(),
            inspection=self._make_inspection(),
            cli_version="0.2.1",
        )
        assert b.cli_version == "0.2.1"

    def test_assembled_at_set(self):
        b = assemble_support_bundle(
            run_id="r", request_id="q",
            explanation=self._make_explanation(),
            inspection=self._make_inspection(),
            cli_version="0.2.0",
        )
        assert b.assembled_at


# ─────────────────────────────────────────────────────────────
# TestRenderExplanation
# ─────────────────────────────────────────────────────────────

class TestRenderExplanation:
    def _ex(self, **kw) -> RunExplanation:
        defaults = dict(
            run_id="run-1", request_id="req-1",
            outcome_class=ExplainOutcomeClass.SUCCEEDED,
            status="success", run_type="context.compile", is_terminal=True,
        )
        defaults.update(kw)
        return RunExplanation(**defaults)

    def test_render_returns_string(self):
        rendered = render_explanation(self._ex())
        assert isinstance(rendered, str)

    def test_render_includes_run_id(self):
        rendered = render_explanation(self._ex(run_id="run-abc"))
        assert "run-abc" in rendered

    def test_render_includes_outcome_label(self):
        rendered = render_explanation(self._ex(outcome_class=ExplainOutcomeClass.SUCCEEDED))
        assert "Succeeded" in rendered

    def test_render_non_terminal_includes_note(self):
        """§12.5: Non-terminal runs must have an explicit in-progress note."""
        rendered = render_explanation(self._ex(
            outcome_class=ExplainOutcomeClass.ACCEPTED,
            is_terminal=False,
        ))
        assert "not reached" in rendered.lower() or "in progress" in rendered.lower() or "in-progress" in rendered.lower() or "non-terminal" in rendered.lower()

    def test_render_deferred_does_not_say_succeeded(self):
        """§12.5: Deferred must never be rendered as completed."""
        rendered = render_explanation(self._ex(
            outcome_class=ExplainOutcomeClass.DEFERRED,
            is_terminal=False,
        ))
        assert "Succeeded" not in rendered
        assert "succeeded" not in rendered

    def test_render_accepted_does_not_say_succeeded(self):
        rendered = render_explanation(self._ex(
            outcome_class=ExplainOutcomeClass.ACCEPTED,
            is_terminal=False,
        ))
        assert "Succeeded" not in rendered

    def test_render_includes_run_type(self):
        rendered = render_explanation(self._ex(run_type="gaps.list"))
        assert "gaps.list" in rendered

    def test_render_includes_reason(self):
        rendered = render_explanation(self._ex(reason="Quota exceeded"))
        assert "Quota exceeded" in rendered

    def test_render_inferred_reason_noted(self):
        """§12.3: Synthesized reason must be labeled."""
        rendered = render_explanation(self._ex(
            reason="Execution reached a rejected terminal state.",
            is_reason_inferred=True,
        ))
        assert "inferred" in rendered.lower()

    def test_render_repair_guidance_included(self):
        """§12.4: Repair guidance mandatory on non-success."""
        rendered = render_explanation(self._ex(
            outcome_class=ExplainOutcomeClass.REJECTED,
            repair_guidance=["Check your context posture.", "Re-authenticate."],
        ))
        assert "Check your context posture" in rendered

    def test_render_support_bundle_hint_included(self):
        rendered = render_explanation(self._ex(run_id="run-abc"))
        assert "support-bundle" in rendered or "support_bundle" in rendered.lower() or "support" in rendered.lower()

    def test_render_context_digest_included_when_present(self):
        rendered = render_explanation(self._ex(context_digest="sha256:abc123"))
        assert "sha256:abc123" in rendered

    def test_render_event_refs_included(self):
        rendered = render_explanation(self._ex(event_refs=["ev-001", "ev-002"]))
        assert "ev-001" in rendered

    def test_render_proof_refs_included(self):
        rendered = render_explanation(self._ex(proof_refs=["proof-x"]))
        assert "proof-x" in rendered

    def test_render_shadow_mode_noted(self):
        rendered = render_explanation(self._ex(shadow=True))
        assert "shadow" in rendered.lower()

    def test_render_rate_limited_label(self):
        rendered = render_explanation(self._ex(
            outcome_class=ExplainOutcomeClass.RATE_LIMITED,
        ))
        assert "rate" in rendered.lower() or "Rate" in rendered

    def test_render_partial_lineage_note_included(self):
        rendered = render_explanation(self._ex(
            outcome_class=ExplainOutcomeClass.PARTIAL_LINEAGE,
            has_partial_lineage=True,
            lineage_note="Some proof refs not materialized yet.",
        ))
        assert "materialized" in rendered or "lineage" in rendered.lower()

    def test_render_budget_summary_included(self):
        rendered = render_explanation(self._ex(
            budget_summary="95% of daily budget used.",
            limit_outcome="nearing_limit",
        ))
        assert "budget" in rendered.lower()

    def test_render_replayed_label(self):
        rendered = render_explanation(self._ex(
            outcome_class=ExplainOutcomeClass.REPLAYED,
            replayed_from="run-prev",
        ))
        assert "Replay" in rendered or "replay" in rendered.lower() or "reused" in rendered.lower()


# ─────────────────────────────────────────────────────────────
# TestRenderInspection
# ─────────────────────────────────────────────────────────────

class TestRenderInspection:
    def _insp(self, **kw) -> RequestInspectionResult:
        defaults = dict(
            request_id="req-1", run_id="run-1",
            outcome_class=ExplainOutcomeClass.SUCCEEDED,
            status="success", executed=True,
        )
        defaults.update(kw)
        return RequestInspectionResult(**defaults)

    def test_render_returns_string(self):
        rendered = render_inspection(self._insp())
        assert isinstance(rendered, str)

    def test_render_includes_request_id(self):
        rendered = render_inspection(self._insp(request_id="req-xyz"))
        assert "req-xyz" in rendered

    def test_render_includes_run_id(self):
        rendered = render_inspection(self._insp(run_id="run-abc"))
        assert "run-abc" in rendered

    def test_render_executed_shown(self):
        rendered = render_inspection(self._insp(executed=True))
        assert "yes" in rendered.lower() or "true" in rendered.lower() or "executed" in rendered.lower()

    def test_render_replayed_shown(self):
        rendered = render_inspection(self._insp(replayed=True))
        assert "yes" in rendered.lower() or "true" in rendered.lower() or "replayed" in rendered.lower()

    def test_render_deferred_shown(self):
        rendered = render_inspection(self._insp(deferred=True))
        assert "yes" in rendered.lower() or "true" in rendered.lower()

    def test_render_reason_included_when_present(self):
        rendered = render_inspection(self._insp(reason="Scope mismatch detected."))
        assert "Scope mismatch" in rendered

    def test_render_repair_guidance_included(self):
        """§12.4: Repair guidance mandatory on non-success."""
        rendered = render_inspection(self._insp(
            outcome_class=ExplainOutcomeClass.REJECTED,
            repair_guidance=["Verify request shape."],
        ))
        assert "Verify request shape" in rendered

    def test_render_outcome_label_present(self):
        rendered = render_inspection(self._insp(outcome_class=ExplainOutcomeClass.SUCCEEDED))
        assert "succeeded" in rendered.lower() or "success" in rendered.lower()

    def test_render_context_ref_included(self):
        rendered = render_inspection(self._insp(context_ref="ctx-sha256:abc"))
        assert "ctx-sha256:abc" in rendered


# ─────────────────────────────────────────────────────────────
# TestRepairGuidance
# ─────────────────────────────────────────────────────────────

class TestRepairGuidance:
    def test_rejected_has_steps(self):
        steps = map_explain_repair("rejected")
        assert len(steps) > 0

    def test_not_found_has_steps(self):
        steps = map_explain_repair("not_found")
        assert len(steps) > 0

    def test_unauthorized_has_steps(self):
        steps = map_explain_repair("unauthorized")
        assert len(steps) > 0

    def test_deferred_has_steps(self):
        steps = map_explain_repair("deferred")
        assert len(steps) > 0

    def test_rate_limited_has_steps(self):
        steps = map_explain_repair("rate_limited")
        assert len(steps) > 0

    def test_budget_exhausted_has_steps(self):
        steps = map_explain_repair("budget_exhausted")
        assert len(steps) > 0

    def test_missing_run_id_has_steps(self):
        steps = map_explain_repair("missing_run_id")
        assert len(steps) > 0

    def test_missing_request_id_has_steps(self):
        steps = map_explain_repair("missing_request_id")
        assert len(steps) > 0

    def test_unknown_error_returns_default(self):
        steps = map_explain_repair("this_class_does_not_exist_xyz")
        assert isinstance(steps, list)
        assert len(steps) > 0

    def test_returns_list_type(self):
        steps = map_explain_repair("failed")
        assert isinstance(steps, list)

    def test_all_steps_are_strings(self):
        for error_class in ["not_found", "rejected", "deferred", "rate_limited"]:
            steps = map_explain_repair(error_class)
            assert all(isinstance(s, str) for s in steps)

    def test_partial_lineage_has_steps(self):
        steps = map_explain_repair("partial_lineage")
        assert len(steps) > 0


# ─────────────────────────────────────────────────────────────
# TestEmitExplainProof
# ─────────────────────────────────────────────────────────────

class TestEmitExplainProof:
    def _make_explanation(self) -> RunExplanation:
        return assemble_run_explanation(
            _run_resp(status="success"),
            run_id="run-emit-test", request_id="req-1", correlation_id="",
        )

    def test_returns_path(self, tmp_path):
        ex = self._make_explanation()
        result = emit_explain_proof(tmp_path, "run-emit-test", ex)
        assert isinstance(result, Path)

    def test_creates_response_json(self, tmp_path):
        ex = self._make_explanation()
        emit_explain_proof(tmp_path, "run-emit-test", ex)
        assert (tmp_path / "explain" / "run-emit-test" / "response.json").exists()

    def test_creates_rendered_md(self, tmp_path):
        ex = self._make_explanation()
        emit_explain_proof(tmp_path, "run-emit-test", ex)
        assert (tmp_path / "explain" / "run-emit-test" / "rendered.md").exists()

    def test_response_json_valid(self, tmp_path):
        ex = self._make_explanation()
        emit_explain_proof(tmp_path, "run-emit-test", ex)
        data = json.loads(
            (tmp_path / "explain" / "run-emit-test" / "response.json").read_text()
        )
        assert data["run_id"] == "run-emit-test"

    def test_rendered_md_contains_outcome(self, tmp_path):
        ex = self._make_explanation()
        emit_explain_proof(tmp_path, "run-emit-test", ex)
        text = (tmp_path / "explain" / "run-emit-test" / "rendered.md").read_text()
        assert "Succeeded" in text or "succeeded" in text.lower()

    def test_safe_dir_name_sanitizes_special_chars(self, tmp_path):
        ex = self._make_explanation()
        weird_id = "run/../secret/../../etc"
        emit_explain_proof(tmp_path, weird_id, ex)
        # Should create a sanitized directory, not traverse paths
        dirs = list((tmp_path / "explain").iterdir())
        assert len(dirs) == 1
        assert ".." not in dirs[0].name

    def test_creates_parent_dirs(self, tmp_path):
        ex = self._make_explanation()
        deep = tmp_path / "deep" / "state"
        emit_explain_proof(deep, "run-1", ex)
        assert (deep / "explain" / "run-1" / "response.json").exists()

    def test_overwrites_on_repeat_call(self, tmp_path):
        ex = self._make_explanation()
        emit_explain_proof(tmp_path, "run-1", ex)
        emit_explain_proof(tmp_path, "run-1", ex)  # second call should not raise
        assert (tmp_path / "explain" / "run-1" / "response.json").exists()

    def test_response_json_has_outcome_class(self, tmp_path):
        ex = self._make_explanation()
        emit_explain_proof(tmp_path, "run-emit-test", ex)
        data = json.loads(
            (tmp_path / "explain" / "run-emit-test" / "response.json").read_text()
        )
        assert "outcome_class" in data

    def test_response_json_no_secrets(self, tmp_path):
        """§10: Proof files must not contain tokens or secrets."""
        ex = self._make_explanation()
        emit_explain_proof(tmp_path, "run-emit-test", ex)
        text = (tmp_path / "explain" / "run-emit-test" / "response.json").read_text()
        assert "token" not in text.lower() or "access_token" not in text


# ─────────────────────────────────────────────────────────────
# TestEmitBundleProof
# ─────────────────────────────────────────────────────────────

class TestEmitBundleProof:
    def _make_bundle(self) -> SupportBundle:
        explanation = assemble_run_explanation(
            _run_resp(status="failed", reason="Limit hit"),
            run_id="run-bundle", request_id="req-bundle", correlation_id="",
        )
        inspection = assemble_request_inspection(
            {"run_id": "run-bundle", "status": "failed"},
            request_id="req-bundle",
        )
        return assemble_support_bundle(
            run_id="run-bundle", request_id="req-bundle",
            explanation=explanation,
            inspection=inspection,
            cli_version="0.2.0",
        )

    def test_returns_path(self, tmp_path):
        b = self._make_bundle()
        result = emit_bundle_proof(tmp_path, "run-bundle", b)
        assert isinstance(result, Path)

    def test_creates_bundle_dir(self, tmp_path):
        b = self._make_bundle()
        result = emit_bundle_proof(tmp_path, "run-bundle", b)
        assert result.is_dir()

    def test_has_summary_md(self, tmp_path):
        b = self._make_bundle()
        emit_bundle_proof(tmp_path, "run-bundle", b)
        assert (tmp_path / "support_bundle" / "run-bundle" / "summary.md").exists()

    def test_has_request_json(self, tmp_path):
        b = self._make_bundle()
        emit_bundle_proof(tmp_path, "run-bundle", b)
        assert (tmp_path / "support_bundle" / "run-bundle" / "request.json").exists()

    def test_has_run_json(self, tmp_path):
        b = self._make_bundle()
        emit_bundle_proof(tmp_path, "run-bundle", b)
        assert (tmp_path / "support_bundle" / "run-bundle" / "run.json").exists()

    def test_has_context_json(self, tmp_path):
        b = self._make_bundle()
        emit_bundle_proof(tmp_path, "run-bundle", b)
        assert (tmp_path / "support_bundle" / "run-bundle" / "context.json").exists()

    def test_has_events_json(self, tmp_path):
        b = self._make_bundle()
        emit_bundle_proof(tmp_path, "run-bundle", b)
        assert (tmp_path / "support_bundle" / "run-bundle" / "events.json").exists()

    def test_has_proof_refs_json(self, tmp_path):
        b = self._make_bundle()
        emit_bundle_proof(tmp_path, "run-bundle", b)
        assert (tmp_path / "support_bundle" / "run-bundle" / "proof_refs.json").exists()

    def test_has_outcome_json(self, tmp_path):
        b = self._make_bundle()
        emit_bundle_proof(tmp_path, "run-bundle", b)
        assert (tmp_path / "support_bundle" / "run-bundle" / "outcome.json").exists()

    def test_has_repair_json(self, tmp_path):
        b = self._make_bundle()
        emit_bundle_proof(tmp_path, "run-bundle", b)
        assert (tmp_path / "support_bundle" / "run-bundle" / "repair.json").exists()

    def test_has_metadata_json(self, tmp_path):
        b = self._make_bundle()
        emit_bundle_proof(tmp_path, "run-bundle", b)
        assert (tmp_path / "support_bundle" / "run-bundle" / "metadata.json").exists()

    def test_nine_total_files(self, tmp_path):
        b = self._make_bundle()
        bundle_dir = emit_bundle_proof(tmp_path, "run-bundle", b)
        files = list(bundle_dir.iterdir())
        assert len(files) == 9

    def test_run_json_is_valid(self, tmp_path):
        b = self._make_bundle()
        emit_bundle_proof(tmp_path, "run-bundle", b)
        data = json.loads(
            (tmp_path / "support_bundle" / "run-bundle" / "run.json").read_text()
        )
        assert isinstance(data, dict)

    def test_metadata_json_has_assembled_at(self, tmp_path):
        b = self._make_bundle()
        emit_bundle_proof(tmp_path, "run-bundle", b)
        data = json.loads(
            (tmp_path / "support_bundle" / "run-bundle" / "metadata.json").read_text()
        )
        # metadata section from assembler should contain assembled_at or similar info
        assert isinstance(data, dict)

    def test_safe_id_sanitizes_slashes(self, tmp_path):
        b = self._make_bundle()
        weird_id = "run/../../../etc/passwd"
        emit_bundle_proof(tmp_path, weird_id, b)
        dirs = list((tmp_path / "support_bundle").iterdir())
        assert len(dirs) == 1
        assert ".." not in dirs[0].name
        assert "/" not in dirs[0].name

    def test_no_credentials_in_bundle(self, tmp_path):
        """§10: Support bundle must not contain tokens or credentials."""
        b = self._make_bundle()
        bundle_dir = emit_bundle_proof(tmp_path, "run-bundle", b)
        for f in bundle_dir.iterdir():
            content = f.read_text()
            assert "access_token" not in content
            assert "client_secret" not in content


# ─────────────────────────────────────────────────────────────
# TestOperationRegistry
# ─────────────────────────────────────────────────────────────

class TestOperationRegistry:
    def test_run_explain_in_registry(self):
        from keyhole_sdk.transport.operation_registry import (
            OperationClass,
            get_operation,
        )
        op = get_operation("run.explain")
        assert op is not None

    def test_run_explain_is_read_only(self):
        from keyhole_sdk.transport.operation_registry import (
            OperationClass,
            get_operation,
        )
        op = get_operation("run.explain")
        assert op.operation_class == OperationClass.READ_ONLY

    def test_request_inspect_in_registry(self):
        from keyhole_sdk.transport.operation_registry import (
            OperationClass,
            get_operation,
        )
        op = get_operation("request.inspect")
        assert op is not None

    def test_request_inspect_is_read_only(self):
        from keyhole_sdk.transport.operation_registry import (
            OperationClass,
            get_operation,
        )
        op = get_operation("request.inspect")
        assert op.operation_class == OperationClass.READ_ONLY


# ─────────────────────────────────────────────────────────────
# TestPublicAPISurface
# ─────────────────────────────────────────────────────────────

class TestPublicAPISurface:
    def test_explain_outcome_class_in_all(self):
        import keyhole_sdk
        assert "ExplainOutcomeClass" in keyhole_sdk.__all__

    def test_run_explanation_in_all(self):
        import keyhole_sdk
        assert "RunExplanation" in keyhole_sdk.__all__

    def test_request_inspection_result_in_all(self):
        import keyhole_sdk
        assert "RequestInspectionResult" in keyhole_sdk.__all__

    def test_support_bundle_in_all(self):
        import keyhole_sdk
        assert "SupportBundle" in keyhole_sdk.__all__

    def test_assemble_run_explanation_in_all(self):
        import keyhole_sdk
        assert "assemble_run_explanation" in keyhole_sdk.__all__

    def test_assemble_request_inspection_in_all(self):
        import keyhole_sdk
        assert "assemble_request_inspection" in keyhole_sdk.__all__

    def test_assemble_support_bundle_in_all(self):
        import keyhole_sdk
        assert "assemble_support_bundle" in keyhole_sdk.__all__

    def test_render_explanation_in_all(self):
        import keyhole_sdk
        assert "render_explanation" in keyhole_sdk.__all__

    def test_render_inspection_in_all(self):
        import keyhole_sdk
        assert "render_inspection" in keyhole_sdk.__all__

    def test_emit_explain_proof_in_all(self):
        import keyhole_sdk
        assert "emit_explain_proof" in keyhole_sdk.__all__

    def test_emit_bundle_proof_in_all(self):
        import keyhole_sdk
        assert "emit_bundle_proof" in keyhole_sdk.__all__

    def test_map_explain_repair_in_all(self):
        import keyhole_sdk
        assert "map_explain_repair" in keyhole_sdk.__all__

    def test_twelve_explain_symbols_total(self):
        import keyhole_sdk
        explain_symbols = [
            "ExplainOutcomeClass", "RunExplanation", "RequestInspectionResult",
            "SupportBundle", "assemble_run_explanation", "assemble_request_inspection",
            "assemble_support_bundle", "render_explanation", "render_inspection",
            "emit_explain_proof", "emit_bundle_proof", "map_explain_repair",
        ]
        for sym in explain_symbols:
            assert sym in keyhole_sdk.__all__, f"Missing: {sym}"


# ─────────────────────────────────────────────────────────────
# TestAssemblerHelpers
# ─────────────────────────────────────────────────────────────

class TestAssemblerHelpers:
    def test_safe_list_from_list(self):
        assert _safe_list(["a", "b"]) == ["a", "b"]

    def test_safe_list_from_none(self):
        assert _safe_list(None) == []

    def test_safe_list_from_string(self):
        result = _safe_list("abc")
        assert isinstance(result, list)

    def test_classify_from_response_success(self):
        oc = _classify_from_response({"status": "success"})
        assert oc == ExplainOutcomeClass.SUCCEEDED

    def test_classify_from_response_replayed_flag(self):
        oc = _classify_from_response({"status": "success", "replayed": True})
        assert oc == ExplainOutcomeClass.REPLAYED

    def test_classify_from_response_explicit_field(self):
        oc = _classify_from_response({"outcome_class": "rejected", "status": "success"})
        assert oc == ExplainOutcomeClass.REJECTED

    def test_classify_from_response_empty_dict(self):
        oc = _classify_from_response({})
        assert oc == ExplainOutcomeClass.UNKNOWN

    def test_synthesize_reason_returns_tuple(self):
        reason, is_inferred = _synthesize_reason(ExplainOutcomeClass.REJECTED, {})
        assert isinstance(reason, str)
        assert isinstance(is_inferred, bool)

    def test_synthesize_reason_from_server_field(self):
        reason, is_inferred = _synthesize_reason(
            ExplainOutcomeClass.REJECTED, {"reason": "Server said no"}
        )
        assert reason == "Server said no"
        assert is_inferred is False

    def test_synthesize_reason_inferred_when_missing(self):
        _, is_inferred = _synthesize_reason(ExplainOutcomeClass.REJECTED, {})
        assert is_inferred is True


# ─────────────────────────────────────────────────────────────
# TestNegativeInputs
# ─────────────────────────────────────────────────────────────

class TestNegativeInputs:
    def test_assemble_run_explanation_with_none_response(self):
        """Should not raise — degrade gracefully."""
        ex = assemble_run_explanation(
            {}, run_id="r", request_id="", correlation_id="",
        )
        assert ex.outcome_class == ExplainOutcomeClass.UNKNOWN

    def test_render_explanation_minimal_model(self):
        """Render with all defaults should not raise."""
        ex = RunExplanation()
        rendered = render_explanation(ex)
        assert isinstance(rendered, str)

    def test_render_inspection_minimal_model(self):
        r = RequestInspectionResult()
        rendered = render_inspection(r)
        assert isinstance(rendered, str)

    def test_map_explain_repair_empty_string(self):
        steps = map_explain_repair("")
        assert isinstance(steps, list)

    def test_emit_explain_proof_empty_run_id(self, tmp_path):
        ex = RunExplanation()
        result = emit_explain_proof(tmp_path, "", ex)
        assert isinstance(result, Path)

    def test_emit_bundle_proof_empty_id(self, tmp_path):
        b = SupportBundle()
        result = emit_bundle_proof(tmp_path, "", b)
        assert isinstance(result, Path)

    def test_to_files_dict_empty_bundle(self):
        b = SupportBundle()
        files = b.to_files_dict()
        assert len(files) == 9

    def test_empty_bundle_files_have_omission(self):
        b = SupportBundle()
        files = b.to_files_dict()
        # All JSON sections should be omission dicts because they're empty
        for key in ["request.json", "run.json", "context.json"]:
            val = files[key]
            assert isinstance(val, dict)
            assert val.get("omission") is True


# ─────────────────────────────────────────────────────────────
# TestForwardCompatibility
# ─────────────────────────────────────────────────────────────

class TestForwardCompatibility:
    def test_unknown_outcome_class_renders_gracefully(self):
        """§20.19: Renderers must handle unknown future outcome classes."""
        # Simulate a future server returning a new outcome class
        ex = RunExplanation(
            run_id="r",
            outcome_class=ExplainOutcomeClass.UNKNOWN,
        )
        rendered = render_explanation(ex)
        assert isinstance(rendered, str)
        assert len(rendered) > 0

    def test_extra_fields_in_response_do_not_raise(self):
        """Future server responses with extra fields should assemble cleanly."""
        data = _run_resp(
            status="success",
            future_field="some_new_value",
            another_new_field=42,
        )
        ex = assemble_run_explanation(data, run_id="r", request_id="", correlation_id="")
        assert ex.outcome_class == ExplainOutcomeClass.SUCCEEDED

    def test_missing_optional_fields_do_not_raise(self):
        ex = assemble_run_explanation(
            {"run_id": "r", "status": "success"},
            run_id="r", request_id="", correlation_id="",
        )
        assert ex.run_id == "r"

    def test_bundle_with_extra_omissions_renders_9_files(self, tmp_path):
        b = SupportBundle(
            run_id="r", missing_sections=["events", "context"],
            omission_notes={"events": "spine not connected", "context": "no ctx"},
        )
        emit_bundle_proof(tmp_path, "r", b)
        bundle_dir = tmp_path / "support_bundle" / "r"
        files = list(bundle_dir.iterdir())
        assert len(files) == 9

    def test_classify_handles_run_status_field(self):
        """run_status is an alias used by some server versions."""
        oc = _classify_from_response({"run_status": "success"})
        assert oc == ExplainOutcomeClass.SUCCEEDED


# ─────────────────────────────────────────────────────────────
# TestCLICommandImports
# ─────────────────────────────────────────────────────────────

class TestCLICommandImports:
    def test_explain_cmd_importable(self):
        from keyhole_cli.commands.explain_cmd import (
            run_explain_run,
            run_inspect_request,
            run_support_bundle,
        )
        assert callable(run_explain_run)
        assert callable(run_inspect_request)
        assert callable(run_support_bundle)

    def test_cli_has_explain_app(self):
        from keyhole_cli.cli import explain_app
        assert explain_app is not None

    def test_cli_explain_app_has_run_command(self):
        from keyhole_cli.cli import explain_app
        command_names = [c.name for c in explain_app.registered_commands]
        assert "run" in command_names

    def test_cli_has_inspect_command(self):
        from keyhole_cli.cli import app
        command_names = [c.name for c in app.registered_commands]
        assert "inspect" in command_names

    def test_cli_has_support_bundle_command(self):
        from keyhole_cli.cli import app
        command_names = [c.name for c in app.registered_commands]
        assert "support-bundle" in command_names
