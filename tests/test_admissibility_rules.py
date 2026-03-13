"""Test each of the 10 admissibility rules individually."""

from __future__ import annotations

import pytest

from schemas.proposal import InterpretationProposal, ConfidenceClass, ConsequenceClass
from rules.admissibility import (
    evidence_anchor_required,
    assumption_count_bound,
    ambiguity_preservation_required,
    confidence_consequence_match,
    actor_intent_attribution_ban,
    scope_drift_fail,
    temporal_drift_fail,
    prohibited_inferential_jump,
    provenance_required,
    omitted_alternative_detection,
    evaluate_proposal,
)
from schemas.verdict import VerdictResult


def _make_proposal(**overrides) -> InterpretationProposal:
    """Create a valid proposal with optional overrides."""
    defaults = {
        "proposal_id": "test-001",
        "signal_id": "sig-001",
        "actor": "test-actor",
        "source_span": "The product has a defect.",
        "claimed_object": "product defect",
        "claimed_intent": "report defect for review",
        "risk_tags": (),
        "ambiguity_markers": (),
        "assumptions_introduced": (),
        "omitted_alternatives": (),
        "confidence_class": ConfidenceClass.MEDIUM,
        "consequence_class": ConsequenceClass.LOW,
    }
    defaults.update(overrides)
    return InterpretationProposal(**defaults)


class TestEvidenceAnchorRequired:
    def test_pass_with_content(self):
        p = _make_proposal(source_span="some text")
        passed, _ = evidence_anchor_required(p)
        assert passed is True

    def test_fail_empty(self):
        p = _make_proposal(source_span="")
        passed, reason = evidence_anchor_required(p)
        assert passed is False
        assert "empty" in reason

    def test_fail_whitespace_only(self):
        p = _make_proposal(source_span="   ")
        passed, _ = evidence_anchor_required(p)
        assert passed is False


class TestAssumptionCountBound:
    def test_pass_within_threshold(self):
        p = _make_proposal(assumptions_introduced=("a1", "a2"))
        passed, _ = assumption_count_bound(p)
        assert passed is True

    def test_pass_at_threshold(self):
        p = _make_proposal(assumptions_introduced=("a1", "a2", "a3"))
        passed, _ = assumption_count_bound(p)
        assert passed is True

    def test_fail_above_threshold(self):
        p = _make_proposal(assumptions_introduced=("a1", "a2", "a3", "a4"))
        passed, reason = assumption_count_bound(p)
        assert passed is False
        assert "exceeds" in reason


class TestAmbiguityPreservationRequired:
    def test_pass_no_ambiguity(self):
        p = _make_proposal(ambiguity_markers=(), omitted_alternatives=())
        passed, _ = ambiguity_preservation_required(p)
        assert passed is True

    def test_pass_ambiguity_with_alternatives(self):
        p = _make_proposal(
            ambiguity_markers=("sarcasm",),
            omitted_alternatives=("literal reading",),
        )
        passed, _ = ambiguity_preservation_required(p)
        assert passed is True

    def test_fail_ambiguity_without_alternatives(self):
        p = _make_proposal(
            ambiguity_markers=("sarcasm",),
            omitted_alternatives=(),
        )
        passed, _ = ambiguity_preservation_required(p)
        assert passed is False


class TestConfidenceConsequenceMatch:
    def test_pass_medium_medium(self):
        p = _make_proposal(
            confidence_class=ConfidenceClass.MEDIUM,
            consequence_class=ConsequenceClass.MEDIUM,
        )
        passed, _ = confidence_consequence_match(p)
        assert passed is True

    def test_pass_high_critical(self):
        p = _make_proposal(
            confidence_class=ConfidenceClass.HIGH,
            consequence_class=ConsequenceClass.CRITICAL,
        )
        passed, _ = confidence_consequence_match(p)
        assert passed is True

    def test_fail_low_critical(self):
        p = _make_proposal(
            confidence_class=ConfidenceClass.LOW,
            consequence_class=ConsequenceClass.CRITICAL,
        )
        passed, _ = confidence_consequence_match(p)
        assert passed is False

    def test_fail_low_high(self):
        p = _make_proposal(
            confidence_class=ConfidenceClass.LOW,
            consequence_class=ConsequenceClass.HIGH,
        )
        passed, _ = confidence_consequence_match(p)
        assert passed is False


class TestActorIntentAttributionBan:
    def test_pass_no_mental_state(self):
        p = _make_proposal(claimed_intent="report defect for review")
        passed, _ = actor_intent_attribution_ban(p)
        assert passed is True

    def test_fail_mental_state_no_evidence(self):
        p = _make_proposal(
            source_span="The product has a defect.",
            claimed_intent="the user believes the product is unsafe",
        )
        passed, reason = actor_intent_attribution_ban(p)
        assert passed is False
        assert "believes" in reason

    def test_pass_mental_state_with_evidence(self):
        p = _make_proposal(
            source_span="The user believes the product is unsafe.",
            claimed_intent="the user believes the product is unsafe",
        )
        passed, _ = actor_intent_attribution_ban(p)
        assert passed is True


class TestScopeDriftFail:
    def test_pass_no_drift(self):
        p = _make_proposal(
            source_span="Product X has a defect.",
            claimed_object="Product X defect",
        )
        passed, _ = scope_drift_fail(p)
        assert passed is True

    def test_fail_universal_expansion(self):
        p = _make_proposal(
            source_span="Product X has a defect.",
            claimed_object="all products have defects",
        )
        passed, _ = scope_drift_fail(p)
        assert passed is False


class TestTemporalDriftFail:
    def test_pass_no_drift(self):
        p = _make_proposal(
            source_span="The system is currently down.",
            claimed_intent="report current outage",
        )
        passed, _ = temporal_drift_fail(p)
        assert passed is True

    def test_fail_historical_claim(self):
        p = _make_proposal(
            source_span="The system is currently down.",
            claimed_intent="historically the system has been unreliable",
        )
        passed, reason = temporal_drift_fail(p)
        assert passed is False
        assert "historically" in reason


class TestProhibitedInferentialJump:
    def test_pass_no_jump(self):
        p = _make_proposal(claimed_intent="report for review")
        passed, _ = prohibited_inferential_jump(p)
        assert passed is True

    def test_fail_absence_to_denial(self):
        p = _make_proposal(
            claimed_intent="absence of denial implies consent",
        )
        passed, _ = prohibited_inferential_jump(p)
        assert passed is False

    def test_fail_in_assumptions(self):
        p = _make_proposal(
            assumptions_introduced=("silence as consent",),
        )
        passed, _ = prohibited_inferential_jump(p)
        assert passed is False


class TestProvenanceRequired:
    def test_pass_with_signal_id(self):
        p = _make_proposal(signal_id="sig-001")
        passed, _ = provenance_required(p)
        assert passed is True

    def test_fail_empty_signal_id(self):
        p = _make_proposal(signal_id="")
        passed, _ = provenance_required(p)
        assert passed is False


class TestOmittedAlternativeDetection:
    def test_pass_no_ambiguity(self):
        p = _make_proposal(ambiguity_markers=(), omitted_alternatives=())
        passed, _ = omitted_alternative_detection(p)
        assert passed is True

    def test_pass_ambiguity_with_alternatives(self):
        p = _make_proposal(
            ambiguity_markers=("sarcasm",),
            omitted_alternatives=("literal reading",),
        )
        passed, _ = omitted_alternative_detection(p)
        assert passed is True

    def test_fail_ambiguity_without_alternatives(self):
        p = _make_proposal(
            ambiguity_markers=("ambiguous",),
            omitted_alternatives=(),
        )
        passed, _ = omitted_alternative_detection(p)
        assert passed is False


class TestEvaluateProposal:
    def test_valid_proposal_allows(self):
        p = _make_proposal()
        verdict = evaluate_proposal(p, provenance_hash="sha256:abc")
        assert verdict.result == VerdictResult.ALLOW
        assert len(verdict.failures) == 0

    def test_invalid_proposal_denies(self):
        p = _make_proposal(source_span="")
        verdict = evaluate_proposal(p, provenance_hash="sha256:abc")
        assert verdict.result == VerdictResult.DENY
        assert any(f.rule == "EVIDENCE_ANCHOR_REQUIRED" for f in verdict.failures)

    def test_empty_provenance_denies(self):
        p = _make_proposal()
        verdict = evaluate_proposal(p, provenance_hash="")
        assert verdict.result == VerdictResult.DENY
        assert any(f.rule == "PROVENANCE_REQUIRED" for f in verdict.failures)
