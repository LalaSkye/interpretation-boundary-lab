"""12 adversarial test cases as specified in the design document."""

from __future__ import annotations

import pytest

from schemas.proposal import InterpretationProposal, ConfidenceClass, ConsequenceClass
from schemas.transit import Node, Transit
from schemas.verdict import VerdictResult
from rules.admissibility import evaluate_proposal
from graph.topology import ClosedAdmissibilityGraph


PROVENANCE = "sha256:adversarial-test"


class TestAdversarialCases:
    """All 12 adversarial test cases from the specification."""

    def test_01_collapse_without_justification(self):
        """Same text, two plausible readings — collapses without justification → DENY."""
        p = InterpretationProposal(
            proposal_id="adv-01",
            signal_id="sig-adv",
            actor="tester",
            source_span="The bank was steep.",
            claimed_object="financial institution",
            claimed_intent="reference to banking sector",
            ambiguity_markers=("bank: financial vs. riverbank",),
            omitted_alternatives=(),  # Missing — should document collapse
            confidence_class=ConfidenceClass.HIGH,
            consequence_class=ConsequenceClass.LOW,
        )
        verdict = evaluate_proposal(p, provenance_hash=PROVENANCE)
        assert verdict.result == VerdictResult.DENY
        failed_rules = {f.rule for f in verdict.failures}
        assert "AMBIGUITY_PRESERVATION_REQUIRED" in failed_rules

    def test_02_collapse_with_documentation(self):
        """Same text, two plausible readings — documents collapse → ALLOW."""
        p = InterpretationProposal(
            proposal_id="adv-02",
            signal_id="sig-adv",
            actor="tester",
            source_span="The bank was steep.",
            claimed_object="riverbank geography",
            claimed_intent="describe terrain feature",
            ambiguity_markers=("bank: financial vs. riverbank",),
            omitted_alternatives=("financial institution reading discarded due to 'steep'",),
            confidence_class=ConfidenceClass.HIGH,
            consequence_class=ConsequenceClass.LOW,
        )
        verdict = evaluate_proposal(p, provenance_hash=PROVENANCE)
        assert verdict.result == VerdictResult.ALLOW

    def test_03_sarcasm_literal_no_marker(self):
        """Sarcastic/indirect language — literal meaning without ambiguity marker → DENY.

        Note: This tests the rule that if source admits multiple readings
        (we encode this via ambiguity_markers), omitted_alternatives must be present.
        The sarcasm case fails because the proposal has ambiguity markers
        but doesn't document alternatives.
        """
        p = InterpretationProposal(
            proposal_id="adv-03",
            signal_id="sig-adv",
            actor="tester",
            source_span="Oh great, another meeting.",
            claimed_object="positive meeting sentiment",
            claimed_intent="express enthusiasm about meeting",
            ambiguity_markers=("sarcasm_possible",),
            omitted_alternatives=(),  # Doesn't document sarcastic reading
            confidence_class=ConfidenceClass.HIGH,
            consequence_class=ConsequenceClass.LOW,
        )
        verdict = evaluate_proposal(p, provenance_hash=PROVENANCE)
        assert verdict.result == VerdictResult.DENY

    def test_04_incomplete_regulatory_excessive_assumptions(self):
        """Incomplete regulatory clause — fills gaps with too many assumptions → DENY."""
        p = InterpretationProposal(
            proposal_id="adv-04",
            signal_id="sig-adv",
            actor="tester",
            source_span="Section 4.2(a): implement appropriate measures.",
            claimed_object="full encryption and access control mandate",
            claimed_intent="require specific technical implementations",
            assumptions_introduced=(
                "appropriate means encryption",
                "measures include access control",
                "applies to all data types",
                "retroactive compliance required",
            ),
            confidence_class=ConfidenceClass.MEDIUM,
            consequence_class=ConsequenceClass.HIGH,
        )
        verdict = evaluate_proposal(p, provenance_hash=PROVENANCE)
        assert verdict.result == VerdictResult.DENY
        failed_rules = {f.rule for f in verdict.failures}
        assert "ASSUMPTION_COUNT_BOUND" in failed_rules

    def test_05_probabilistic_as_certain(self):
        """Probabilistic classifier output as certain — LOW confidence + CRITICAL consequence → DENY."""
        p = InterpretationProposal(
            proposal_id="adv-05",
            signal_id="sig-adv",
            actor="ml-classifier",
            source_span="Model output: 0.52 probability of risk.",
            claimed_object="confirmed risk",
            claimed_intent="flag as critical risk requiring immediate action",
            confidence_class=ConfidenceClass.LOW,
            consequence_class=ConsequenceClass.CRITICAL,
        )
        verdict = evaluate_proposal(p, provenance_hash=PROVENANCE)
        assert verdict.result == VerdictResult.DENY
        failed_rules = {f.rule for f in verdict.failures}
        assert "CONFIDENCE_CONSEQUENCE_MATCH" in failed_rules

    def test_06_human_review_excessive_assumptions(self):
        """Human review note that introduces unstated assumptions → DENY."""
        p = InterpretationProposal(
            proposal_id="adv-06",
            signal_id="sig-adv",
            actor="human-reviewer",
            source_span="System reported a warning.",
            claimed_object="system failure event",
            claimed_intent="escalate to incident response",
            assumptions_introduced=(
                "warnings always precede failures",
                "this system has history of failures",
                "immediate escalation is warranted",
                "downstream systems are also affected",
            ),
            confidence_class=ConfidenceClass.MEDIUM,
            consequence_class=ConsequenceClass.MEDIUM,
        )
        verdict = evaluate_proposal(p, provenance_hash=PROVENANCE)
        assert verdict.result == VerdictResult.DENY
        failed_rules = {f.rule for f in verdict.failures}
        assert "ASSUMPTION_COUNT_BOUND" in failed_rules

    def test_07_scope_expansion(self):
        """Source says 'product X' but interpretation covers 'all products' → DENY."""
        p = InterpretationProposal(
            proposal_id="adv-07",
            signal_id="sig-adv",
            actor="tester",
            source_span="Product X has a defect in batch 42.",
            claimed_object="all products have defects",
            claimed_intent="recall all products",
            confidence_class=ConfidenceClass.HIGH,
            consequence_class=ConsequenceClass.MEDIUM,
        )
        verdict = evaluate_proposal(p, provenance_hash=PROVENANCE)
        assert verdict.result == VerdictResult.DENY
        failed_rules = {f.rule for f in verdict.failures}
        assert "SCOPE_DRIFT_FAIL" in failed_rules

    def test_08_temporal_drift(self):
        """Source says 'currently' but interpretation claims 'historically' → DENY."""
        p = InterpretationProposal(
            proposal_id="adv-08",
            signal_id="sig-adv",
            actor="tester",
            source_span="The system is currently experiencing load.",
            claimed_object="system load event",
            claimed_intent="historically the system has been overloaded",
            confidence_class=ConfidenceClass.MEDIUM,
            consequence_class=ConsequenceClass.MEDIUM,
        )
        verdict = evaluate_proposal(p, provenance_hash=PROVENANCE)
        assert verdict.result == VerdictResult.DENY
        failed_rules = {f.rule for f in verdict.failures}
        assert "TEMPORAL_DRIFT_FAIL" in failed_rules

    def test_09_prohibited_inferential_jump(self):
        """Absence of denial interpreted as consent → DENY."""
        p = InterpretationProposal(
            proposal_id="adv-09",
            signal_id="sig-adv",
            actor="tester",
            source_span="The user did not respond to the notification.",
            claimed_object="user consent",
            claimed_intent="absence of denial implies consent",
            confidence_class=ConfidenceClass.MEDIUM,
            consequence_class=ConsequenceClass.MEDIUM,
        )
        verdict = evaluate_proposal(p, provenance_hash=PROVENANCE)
        assert verdict.result == VerdictResult.DENY
        failed_rules = {f.rule for f in verdict.failures}
        assert "PROHIBITED_INFERENTIAL_JUMP" in failed_rules

    def test_10_missing_provenance(self):
        """Signal with empty provenance_hash → DENY."""
        p = InterpretationProposal(
            proposal_id="adv-10",
            signal_id="sig-adv",
            actor="tester",
            source_span="Some valid content.",
            claimed_object="content item",
            claimed_intent="process content",
            confidence_class=ConfidenceClass.MEDIUM,
            consequence_class=ConsequenceClass.LOW,
        )
        verdict = evaluate_proposal(p, provenance_hash="")
        assert verdict.result == VerdictResult.DENY
        failed_rules = {f.rule for f in verdict.failures}
        assert "PROVENANCE_REQUIRED" in failed_rules

    def test_11_valid_proposal(self):
        """Valid proposal: all fields present, all rules pass → ALLOW."""
        p = InterpretationProposal(
            proposal_id="adv-11",
            signal_id="sig-adv",
            actor="analyst",
            source_span="Product X has a defect in batch 42.",
            claimed_object="Product X batch 42 defect",
            claimed_intent="report specific defect for quality review",
            risk_tags=("product_safety",),
            ambiguity_markers=(),
            assumptions_introduced=(),
            omitted_alternatives=(),
            confidence_class=ConfidenceClass.HIGH,
            consequence_class=ConsequenceClass.MEDIUM,
        )
        verdict = evaluate_proposal(p, provenance_hash=PROVENANCE)
        assert verdict.result == VerdictResult.ALLOW
        assert len(verdict.failures) == 0

    def test_12_graph_transit_undeclared_edge(self):
        """Valid proposal attempts undeclared edge → DENY by topology."""
        graph = ClosedAdmissibilityGraph()

        # Attempt to skip VERIFY and go directly from INTERPRET_X to ROUTE
        t = Transit(
            source=Node.INTERPRET_X,
            target=Node.ROUTE,
            kind="interpretation",
            provenance="prov-001",
            authority="x_layer",
        )
        result = graph.attempt_transit(t)
        assert result.allowed is False
        assert "no declared edge" in result.reason
