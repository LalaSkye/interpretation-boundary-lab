"""Test the meaning drift replay mechanism."""

from __future__ import annotations

import pytest

from schemas.proposal import InterpretationProposal, ConfidenceClass, ConsequenceClass
from schemas.verdict import VerdictResult
from graph.replay import MeaningDriftReplay


PROVENANCE = "sha256:replay-test"


def _make_proposal(pid: str, **overrides) -> InterpretationProposal:
    defaults = {
        "proposal_id": pid,
        "signal_id": "sig-replay",
        "actor": "test-actor",
        "source_span": "The system detected an anomaly.",
        "claimed_object": "anomaly event",
        "claimed_intent": "report anomaly",
        "risk_tags": (),
        "ambiguity_markers": (),
        "assumptions_introduced": (),
        "omitted_alternatives": (),
        "confidence_class": ConfidenceClass.MEDIUM,
        "consequence_class": ConsequenceClass.LOW,
    }
    defaults.update(overrides)
    return InterpretationProposal(**defaults)


@pytest.fixture
def replay():
    return MeaningDriftReplay()


class TestDriftReplayBasic:
    def test_single_proposal(self, replay):
        p = _make_proposal("p1")
        report = replay.analyze([p], provenance_hash=PROVENANCE)
        assert report.proposal_count == 1
        assert len(report.divergences) == 0

    def test_empty_proposals_raises(self, replay):
        with pytest.raises(ValueError, match="at least one"):
            replay.analyze([], provenance_hash=PROVENANCE)

    def test_identical_proposals_no_divergence(self, replay):
        p1 = _make_proposal("p1")
        p2 = _make_proposal("p2")
        report = replay.analyze([p1, p2], provenance_hash=PROVENANCE)
        assert len(report.divergences) == 0


class TestDivergenceDetection:
    def test_claimed_object_divergence(self, replay):
        p1 = _make_proposal("p1", claimed_object="anomaly event")
        p2 = _make_proposal("p2", claimed_object="system failure")
        report = replay.analyze([p1, p2], provenance_hash=PROVENANCE)
        field_names = {d.field_name for d in report.divergences}
        assert "claimed_object" in field_names

    def test_confidence_divergence(self, replay):
        p1 = _make_proposal("p1", confidence_class=ConfidenceClass.LOW)
        p2 = _make_proposal("p2", confidence_class=ConfidenceClass.HIGH)
        report = replay.analyze([p1, p2], provenance_hash=PROVENANCE)
        field_names = {d.field_name for d in report.divergences}
        assert "confidence_class" in field_names

    def test_multiple_divergences(self, replay):
        p1 = _make_proposal("p1",
            claimed_object="anomaly",
            claimed_intent="report",
            confidence_class=ConfidenceClass.LOW,
        )
        p2 = _make_proposal("p2",
            claimed_object="failure",
            claimed_intent="escalate",
            confidence_class=ConfidenceClass.HIGH,
        )
        report = replay.analyze([p1, p2], provenance_hash=PROVENANCE)
        assert len(report.divergences) >= 2


class TestVerdictTracking:
    def test_admissible_count(self, replay):
        valid = _make_proposal("valid")
        invalid = _make_proposal("invalid", source_span="")
        report = replay.analyze([valid, invalid], provenance_hash=PROVENANCE)
        assert report.admissible_count == 1
        assert report.inadmissible_count == 1

    def test_all_admissible(self, replay):
        p1 = _make_proposal("p1")
        p2 = _make_proposal("p2")
        report = replay.analyze([p1, p2], provenance_hash=PROVENANCE)
        assert report.admissible_count == 2
        assert report.inadmissible_count == 0


class TestUnsupportedSteps:
    def test_unsupported_steps_from_failures(self, replay):
        invalid = _make_proposal("invalid",
            source_span="",
            confidence_class=ConfidenceClass.LOW,
            consequence_class=ConsequenceClass.CRITICAL,
        )
        report = replay.analyze([invalid], provenance_hash=PROVENANCE)
        assert len(report.unsupported_steps) > 0
        step_rules = [desc for _, desc in report.unsupported_steps]
        assert any("EVIDENCE_ANCHOR_REQUIRED" in s for s in step_rules)

    def test_three_interpreters_divergence(self, replay):
        human = _make_proposal("human",
            claimed_object="minor anomaly",
            confidence_class=ConfidenceClass.MEDIUM,
        )
        llm = _make_proposal("llm",
            claimed_object="critical system failure",
            confidence_class=ConfidenceClass.LOW,
            consequence_class=ConsequenceClass.CRITICAL,
        )
        policy = _make_proposal("policy",
            claimed_object="anomaly event",
            confidence_class=ConfidenceClass.HIGH,
        )
        report = replay.analyze([human, llm, policy], provenance_hash=PROVENANCE)
        assert report.proposal_count == 3
        assert report.inadmissible_count >= 1  # LLM should fail confidence/consequence
        assert len(report.divergences) > 0
