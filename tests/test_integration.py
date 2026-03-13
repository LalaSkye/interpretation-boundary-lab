"""End-to-end: signal → proposal → admissibility → graph transit → verdict."""

from __future__ import annotations

import pytest

from schemas.signal import SignalEnvelope
from schemas.proposal import InterpretationProposal, ConfidenceClass, ConsequenceClass
from schemas.transit import Node, Transit
from schemas.verdict import VerdictResult
from rules.admissibility import evaluate_proposal
from graph.topology import ClosedAdmissibilityGraph
from graph.rotation import SectorEngine
from graph.replay import MeaningDriftReplay


class TestFullPipeline:
    """End-to-end integration tests."""

    def test_valid_signal_to_verdict_allow(self):
        """Valid signal → valid proposal → ALLOW → full graph transit."""
        signal = SignalEnvelope(
            source_id="sig-int-001",
            timestamp="2025-01-15T10:00:00Z",
            content="Product X has a defect in batch 42.",
            content_type="text/report",
            provenance_hash="sha256:integration1",
        )

        proposal = InterpretationProposal(
            proposal_id="prop-int-001",
            signal_id=signal.source_id,
            actor="analyst",
            source_span=signal.content,
            claimed_object="Product X batch 42 defect",
            claimed_intent="report defect for quality review",
            confidence_class=ConfidenceClass.HIGH,
            consequence_class=ConsequenceClass.MEDIUM,
        )

        # Admissibility check
        verdict = evaluate_proposal(proposal, provenance_hash=signal.provenance_hash)
        assert verdict.result == VerdictResult.ALLOW

        # Graph transit
        graph = ClosedAdmissibilityGraph()
        prov = signal.provenance_hash

        r1 = graph.attempt_transit(
            Transit(Node.OBSERVE, Node.INTERPRET_X, "signal", prov, "sensor"))
        assert r1.allowed

        r2 = graph.attempt_transit(
            Transit(Node.INTERPRET_X, Node.VERIFY, "interpretation", prov, "x_layer"))
        assert r2.allowed

        r3 = graph.attempt_transit(
            Transit(Node.VERIFY, Node.ROUTE, "verified_transition", prov, "verifier"))
        assert r3.allowed

    def test_invalid_proposal_to_stop(self):
        """Invalid proposal → DENY → route to STOP."""
        signal = SignalEnvelope(
            source_id="sig-int-002",
            timestamp="2025-01-15T10:00:00Z",
            content="Something happened.",
            content_type="text/alert",
            provenance_hash="sha256:integration2",
        )

        proposal = InterpretationProposal(
            proposal_id="prop-int-002",
            signal_id=signal.source_id,
            actor="bad-interpreter",
            source_span="",  # Missing evidence
            claimed_object="critical system failure",
            claimed_intent="shutdown everything",
            confidence_class=ConfidenceClass.LOW,
            consequence_class=ConsequenceClass.CRITICAL,
        )

        verdict = evaluate_proposal(proposal, provenance_hash=signal.provenance_hash)
        assert verdict.result == VerdictResult.DENY

        # Route to STOP
        graph = ClosedAdmissibilityGraph()
        prov = signal.provenance_hash

        r = graph.attempt_transit(
            Transit(Node.VERIFY, Node.STOP, "rejection", prov, "verifier"))
        assert r.allowed

    def test_pressure_builds_to_rotation(self):
        """Multiple denials build pressure and trigger sector rotation."""
        graph = ClosedAdmissibilityGraph()
        engine = SectorEngine(graph, threshold=2)

        signal = SignalEnvelope(
            source_id="sig-int-003",
            timestamp="2025-01-15T10:00:00Z",
            content="Test signal.",
            content_type="text/test",
            provenance_hash="sha256:integration3",
        )

        # Submit bad proposals
        for i in range(2):
            bad = InterpretationProposal(
                proposal_id=f"prop-bad-{i}",
                signal_id=signal.source_id,
                actor="bad-actor",
                source_span="",
                claimed_object="something",
                claimed_intent="something",
                confidence_class=ConfidenceClass.LOW,
                consequence_class=ConsequenceClass.CRITICAL,
            )
            verdict = evaluate_proposal(bad, provenance_hash=signal.provenance_hash)
            assert verdict.result == VerdictResult.DENY
            engine.record_pressure("deny_verdict")

        # System should be blocked
        assert engine.blocked

        # Even valid transits are blocked
        t = Transit(Node.OBSERVE, Node.INTERPRET_X, "signal", "prov-1", "sensor")
        result = engine.attempt_transit(t)
        assert result.allowed is False

    def test_drift_replay_integration(self):
        """Drift replay with signal → multiple proposals → divergence report."""
        signal = SignalEnvelope(
            source_id="sig-int-004",
            timestamp="2025-01-15T10:00:00Z",
            content="The policy requires compliance.",
            content_type="text/policy",
            provenance_hash="sha256:integration4",
        )

        human = InterpretationProposal(
            proposal_id="human-int",
            signal_id=signal.source_id,
            actor="human",
            source_span=signal.content,
            claimed_object="compliance requirement",
            claimed_intent="enforce policy compliance",
            confidence_class=ConfidenceClass.HIGH,
            consequence_class=ConsequenceClass.MEDIUM,
        )

        llm = InterpretationProposal(
            proposal_id="llm-int",
            signal_id=signal.source_id,
            actor="llm",
            source_span=signal.content,
            claimed_object="all policies require immediate enforcement",
            claimed_intent="mandate universal compliance",
            confidence_class=ConfidenceClass.LOW,
            consequence_class=ConsequenceClass.CRITICAL,
        )

        replay = MeaningDriftReplay()
        report = replay.analyze(
            [human, llm],
            provenance_hash=signal.provenance_hash,
        )

        assert report.proposal_count == 2
        assert report.admissible_count >= 1
        assert report.inadmissible_count >= 1
        assert len(report.divergences) > 0

    def test_serialization_roundtrip(self):
        """Signal and proposal serialize/deserialize correctly."""
        signal = SignalEnvelope(
            source_id="sig-rt",
            timestamp="2025-01-15T10:00:00Z",
            content="Test content.",
            content_type="text/plain",
            provenance_hash="sha256:roundtrip",
        )
        signal_dict = signal.to_dict()
        signal2 = SignalEnvelope.from_dict(signal_dict)
        assert signal == signal2

        proposal = InterpretationProposal(
            proposal_id="prop-rt",
            signal_id="sig-rt",
            actor="test",
            source_span="Test content.",
            claimed_object="test object",
            claimed_intent="test intent",
            risk_tags=("tag1",),
            ambiguity_markers=("amb1",),
            assumptions_introduced=("asm1",),
            omitted_alternatives=("alt1",),
            confidence_class=ConfidenceClass.HIGH,
            consequence_class=ConsequenceClass.MEDIUM,
        )
        prop_dict = proposal.to_dict()
        proposal2 = InterpretationProposal.from_dict(prop_dict)
        assert proposal == proposal2
