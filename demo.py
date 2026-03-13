"""Runnable demo: interpretation admissibility, graph transit, sector rotation, drift replay.

Run with:
    python demo.py

Shows:
    1. A valid proposal passing all admissibility rules
    2. An invalid proposal failing rules
    3. Graph transit denials for undeclared edges
    4. Sector rotation blocking under pressure
    5. Drift replay divergence across multiple interpreters
"""

from __future__ import annotations

import sys
sys.path.insert(0, ".")

from schemas.signal import SignalEnvelope
from schemas.proposal import InterpretationProposal, ConfidenceClass, ConsequenceClass
from schemas.transit import Node, Transit
from rules.admissibility import evaluate_proposal
from graph.topology import ClosedAdmissibilityGraph
from graph.rotation import SectorEngine
from graph.replay import MeaningDriftReplay


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def demo_valid_proposal() -> None:
    """1. A valid proposal passing all rules."""
    section("1. VALID PROPOSAL — ALL RULES PASS")

    signal = SignalEnvelope(
        source_id="sig-001",
        timestamp="2025-01-15T10:00:00Z",
        content="Product X has a defect in batch 42.",
        content_type="text/report",
        provenance_hash="sha256:abc123",
    )

    proposal = InterpretationProposal(
        proposal_id="prop-valid-001",
        signal_id=signal.source_id,
        actor="analyst-human",
        source_span="Product X has a defect in batch 42.",
        claimed_object="Product X batch 42 defect",
        claimed_intent="report a specific product defect for review",
        risk_tags=("product_safety",),
        ambiguity_markers=(),
        assumptions_introduced=(),
        omitted_alternatives=(),
        confidence_class=ConfidenceClass.HIGH,
        consequence_class=ConsequenceClass.MEDIUM,
    )

    verdict = evaluate_proposal(proposal, provenance_hash=signal.provenance_hash)
    print(f"Proposal: {proposal.proposal_id}")
    print(f"Result:   {verdict.result.value}")
    assert verdict.result.value == "ALLOW", "Expected ALLOW"
    print("All 10 rules passed.")


def demo_invalid_proposal() -> None:
    """2. An invalid proposal failing multiple rules."""
    section("2. INVALID PROPOSAL — RULES FAIL")

    proposal = InterpretationProposal(
        proposal_id="prop-invalid-001",
        signal_id="sig-002",
        actor="llm-classifier",
        source_span="",  # Empty — fails EVIDENCE_ANCHOR_REQUIRED
        claimed_object="all products are dangerous",  # Scope drift
        claimed_intent="the user believes products are unsafe",  # Mental state attribution
        risk_tags=("safety",),
        ambiguity_markers=("sarcasm_possible",),
        assumptions_introduced=("a1", "a2", "a3", "a4"),  # Exceeds threshold
        omitted_alternatives=(),  # Missing despite ambiguity markers
        confidence_class=ConfidenceClass.LOW,
        consequence_class=ConsequenceClass.CRITICAL,  # Mismatch with LOW confidence
    )

    verdict = evaluate_proposal(proposal, provenance_hash="")
    print(f"Proposal: {proposal.proposal_id}")
    print(f"Result:   {verdict.result.value}")
    for f in verdict.failures:
        print(f"  FAIL: {f.rule} — {f.reason}")
    assert verdict.result.value == "DENY", "Expected DENY"


def demo_graph_transit_denial() -> None:
    """3. Graph transit denials for undeclared edges."""
    section("3. GRAPH TRANSIT — UNDECLARED EDGES DENIED")

    graph = ClosedAdmissibilityGraph()

    # Valid transit
    valid = Transit(Node.OBSERVE, Node.INTERPRET_X, "signal", "prov-001", "sensor")
    result = graph.attempt_transit(valid)
    print(f"OBSERVE -> INTERPRET_X: {'ALLOWED' if result.allowed else 'DENIED'} ({result.reason})")

    # Undeclared edge: OBSERVE -> ROUTE (not in graph)
    invalid = Transit(Node.OBSERVE, Node.ROUTE, "signal", "prov-001", "sensor")
    result = graph.attempt_transit(invalid)
    print(f"OBSERVE -> ROUTE:       {'ALLOWED' if result.allowed else 'DENIED'} ({result.reason})")

    # Undeclared edge: INTERPRET_X -> ROUTE (must go through VERIFY)
    skip = Transit(Node.INTERPRET_X, Node.ROUTE, "interpretation", "prov-001", "x_layer")
    result = graph.attempt_transit(skip)
    print(f"INTERPRET_X -> ROUTE:   {'ALLOWED' if result.allowed else 'DENIED'} ({result.reason})")

    # Wrong kind on valid edge
    wrong_kind = Transit(Node.OBSERVE, Node.INTERPRET_X, "execution", "prov-001", "sensor")
    result = graph.attempt_transit(wrong_kind)
    print(f"OBSERVE -> INTERPRET_X (wrong kind): {'ALLOWED' if result.allowed else 'DENIED'} ({result.reason})")

    # Missing provenance
    no_prov = Transit(Node.OBSERVE, Node.INTERPRET_X, "signal", "", "sensor")
    result = graph.attempt_transit(no_prov)
    print(f"OBSERVE -> INTERPRET_X (no prov):    {'ALLOWED' if result.allowed else 'DENIED'} ({result.reason})")


def demo_sector_rotation() -> None:
    """4. Sector rotation blocking under pressure."""
    section("4. SECTOR ROTATION — PRESSURE-ACTIVATED BLOCKING")

    graph = ClosedAdmissibilityGraph()
    engine = SectorEngine(graph, threshold=3)

    print(f"Initial sector: {engine.active_sector.value}, pressure: {engine.pressure}")

    # Record pressure events (simulating DENY verdicts)
    for i in range(3):
        engine.record_pressure(f"deny_verdict_{i+1}")
        print(f"  Pressure event {i+1}: sector={engine.active_sector.value}, "
              f"pressure={engine.pressure}, blocked={engine.blocked}")

    print(f"\nAfter 3 denials: sector={engine.active_sector.value}, blocked={engine.blocked}")

    # Attempt transit while blocked
    transit = Transit(Node.OBSERVE, Node.INTERPRET_X, "signal", "prov-001", "sensor")
    result = engine.attempt_transit(transit)
    print(f"Transit attempt while blocked: {'ALLOWED' if result.allowed else 'DENIED'}")
    print(f"  Reason: {result.reason}")

    # Show rotation log
    print(f"\nRotation log ({len(engine.state.rotation_log)} events):")
    for event in engine.state.rotation_log:
        print(f"  [{event.action}] {event.detail}")


def demo_drift_replay() -> None:
    """5. Drift replay divergence across multiple interpreters."""
    section("5. MEANING DRIFT REPLAY — DIVERGENCE ANALYSIS")

    signal = SignalEnvelope(
        source_id="sig-drift-001",
        timestamp="2025-01-15T10:00:00Z",
        content="The system reported an anomaly in module 7.",
        content_type="text/alert",
        provenance_hash="sha256:drift123",
    )

    # Human analyst interpretation — careful, conservative
    human = InterpretationProposal(
        proposal_id="drift-human",
        signal_id=signal.source_id,
        actor="analyst-human",
        source_span="The system reported an anomaly in module 7.",
        claimed_object="module 7 anomaly",
        claimed_intent="flag anomaly for investigation",
        risk_tags=("system_health",),
        ambiguity_markers=(),
        assumptions_introduced=(),
        omitted_alternatives=(),
        confidence_class=ConfidenceClass.MEDIUM,
        consequence_class=ConsequenceClass.MEDIUM,
    )

    # LLM interpretation — overreaches with scope and confidence
    llm = InterpretationProposal(
        proposal_id="drift-llm",
        signal_id=signal.source_id,
        actor="llm-gpt4",
        source_span="The system reported an anomaly in module 7.",
        claimed_object="all modules are potentially compromised",
        claimed_intent="the system believes there is a critical failure",
        risk_tags=("critical_failure", "system_wide"),
        ambiguity_markers=("anomaly_type_unclear",),
        assumptions_introduced=(
            "anomaly implies failure",
            "module 7 affects all modules",
            "system-wide impact assumed",
            "immediate action required",
        ),
        omitted_alternatives=(),
        confidence_class=ConfidenceClass.LOW,
        consequence_class=ConsequenceClass.CRITICAL,
    )

    # Policy engine interpretation — literal but misses context
    policy = InterpretationProposal(
        proposal_id="drift-policy",
        signal_id=signal.source_id,
        actor="policy-engine-v2",
        source_span="The system reported an anomaly in module 7.",
        claimed_object="module 7 anomaly event",
        claimed_intent="log anomaly per standard operating procedure",
        risk_tags=("monitoring",),
        ambiguity_markers=(),
        assumptions_introduced=("standard anomaly classification applies",),
        omitted_alternatives=(),
        confidence_class=ConfidenceClass.HIGH,
        consequence_class=ConsequenceClass.LOW,
    )

    replay = MeaningDriftReplay()
    report = replay.analyze(
        [human, llm, policy],
        provenance_hash=signal.provenance_hash,
    )

    print(f"Signal: {report.signal_id}")
    print(f"Proposals analyzed: {report.proposal_count}")
    print(f"Admissible: {report.admissible_count}, Inadmissible: {report.inadmissible_count}")

    print("\nDivergences:")
    for d in report.divergences:
        print(f"  {d.field_name}:")
        for pid, val in d.values:
            print(f"    {pid}: {val}")

    print("\nVerdicts:")
    for pid, v in report.verdicts:
        print(f"  {pid}: {v.result.value}")
        if v.failures:
            for f in v.failures:
                print(f"    - {f.rule}: {f.reason}")

    if report.unsupported_steps:
        print("\nUnsupported inferential steps:")
        for pid, desc in report.unsupported_steps:
            print(f"  {pid}: {desc}")


def main() -> None:
    print("interpretation-boundary-lab — Demo")
    print("Deterministic admissibility layer for interpretation proposals")

    demo_valid_proposal()
    demo_invalid_proposal()
    demo_graph_transit_denial()
    demo_sector_rotation()
    demo_drift_replay()

    section("DEMO COMPLETE")
    print("All demonstrations executed successfully.")


if __name__ == "__main__":
    main()
