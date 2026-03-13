"""CLI entry point: interp propose | lint | diff | certify.

Usage:
    python -m cli.main propose input.json
    python -m cli.main lint proposal.json
    python -m cli.main diff proposal_a.json proposal_b.json
    python -m cli.main certify proposal.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from schemas.signal import SignalEnvelope
from schemas.proposal import InterpretationProposal
from schemas.transit import Node, Transit
from rules.admissibility import evaluate_proposal, RULES
from graph.topology import ClosedAdmissibilityGraph


def _load_json(path: str) -> dict:
    """Load and return parsed JSON from a file path."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _print_json(data: dict) -> None:
    """Pretty-print a dict as JSON."""
    print(json.dumps(data, indent=2))


def cmd_propose(args: list[str]) -> int:
    """Generate an InterpretationProposal scaffold from a signal."""
    if not args:
        print("Usage: propose <signal.json>", file=sys.stderr)
        return 1

    data = _load_json(args[0])
    signal = SignalEnvelope.from_dict(data)

    scaffold = {
        "proposal_id": f"proposal-for-{signal.source_id}",
        "signal_id": signal.source_id,
        "actor": "<actor>",
        "source_span": signal.content,
        "claimed_object": "<what the signal refers to>",
        "claimed_intent": "<attributed purpose>",
        "risk_tags": [],
        "ambiguity_markers": [],
        "assumptions_introduced": [],
        "omitted_alternatives": [],
        "confidence_class": "MEDIUM",
        "consequence_class": "LOW",
    }

    _print_json(scaffold)
    return 0


def cmd_lint(args: list[str]) -> int:
    """Run all 10 admissibility rules on a proposal, report pass/fail per rule."""
    if not args:
        print("Usage: lint <proposal.json>", file=sys.stderr)
        return 1

    data = _load_json(args[0])
    proposal = InterpretationProposal.from_dict(data)
    provenance_hash = data.get("provenance_hash", "")

    verdict = evaluate_proposal(proposal, provenance_hash=provenance_hash)

    print(f"Proposal: {proposal.proposal_id}")
    print(f"Result:   {verdict.result.value}")
    print()

    # Run each rule individually for detailed report
    for rule_name, rule_fn in RULES:
        if rule_name == "PROVENANCE_REQUIRED":
            if provenance_hash and provenance_hash.strip():
                passed, reason = True, "provenance present"
            else:
                passed, reason = False, "provenance_hash is empty"
        else:
            passed, reason = rule_fn(proposal)
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {rule_name}: {reason}")

    if verdict.failures:
        print(f"\n{len(verdict.failures)} rule(s) failed.")
        return 1

    print("\nAll rules passed.")
    return 0


def cmd_diff(args: list[str]) -> int:
    """Compare two proposals and show divergence."""
    if len(args) < 2:
        print("Usage: diff <proposal_a.json> <proposal_b.json>", file=sys.stderr)
        return 1

    data_a = _load_json(args[0])
    data_b = _load_json(args[1])
    proposal_a = InterpretationProposal.from_dict(data_a)
    proposal_b = InterpretationProposal.from_dict(data_b)

    from graph.replay import MeaningDriftReplay

    replay = MeaningDriftReplay()
    provenance = data_a.get("provenance_hash", "") or data_b.get("provenance_hash", "")
    report = replay.analyze([proposal_a, proposal_b], provenance_hash=provenance)

    print(f"Signal: {report.signal_id}")
    print(f"Proposals compared: {report.proposal_count}")
    print()

    if report.divergences:
        print("Divergences:")
        for d in report.divergences:
            print(f"  {d.field_name}:")
            for pid, val in d.values:
                print(f"    {pid}: {val}")
    else:
        print("No divergences found.")

    print()
    print("Verdicts:")
    for pid, v in report.verdicts:
        print(f"  {pid}: {v.result.value}")
        if v.failures:
            for f in v.failures:
                print(f"    - {f.rule}: {f.reason}")

    return 0


def cmd_certify(args: list[str]) -> int:
    """Run full pipeline: admissibility + graph transit, emit verdict receipt."""
    if not args:
        print("Usage: certify <proposal.json>", file=sys.stderr)
        return 1

    data = _load_json(args[0])
    proposal = InterpretationProposal.from_dict(data)
    provenance_hash = data.get("provenance_hash", "")

    # Step 1: Admissibility
    verdict = evaluate_proposal(proposal, provenance_hash=provenance_hash)

    print(f"Proposal: {proposal.proposal_id}")
    print(f"Admissibility: {verdict.result.value}")

    if verdict.failures:
        for f in verdict.failures:
            print(f"  - {f.rule}: {f.reason}")

    # Step 2: Graph transit (only if admissible)
    graph = ClosedAdmissibilityGraph()

    if verdict.result.value == "ALLOW":
        # Simulate full transit: OBSERVE → INTERPRET_X → VERIFY → ROUTE
        transits = [
            Transit(Node.OBSERVE, Node.INTERPRET_X, "signal", provenance_hash, "sensor"),
            Transit(Node.INTERPRET_X, Node.VERIFY, "interpretation", provenance_hash, "x_layer"),
            Transit(Node.VERIFY, Node.ROUTE, "verified_transition", provenance_hash, "verifier"),
        ]
    else:
        # Route to STOP
        transits = [
            Transit(Node.OBSERVE, Node.INTERPRET_X, "signal", provenance_hash, "sensor"),
            Transit(Node.INTERPRET_X, Node.VERIFY, "interpretation", provenance_hash, "x_layer"),
            Transit(Node.VERIFY, Node.STOP, "rejection", provenance_hash, "verifier"),
        ]

    print("\nGraph Transit:")
    all_ok = True
    for t in transits:
        result = graph.attempt_transit(t)
        status = "OK" if result.allowed else "DENIED"
        print(f"  {t.source.value} -> {t.target.value}: [{status}] {result.reason}")
        if not result.allowed:
            all_ok = False

    # Emit receipt
    receipt = {
        "proposal_id": proposal.proposal_id,
        "admissibility": verdict.result.value,
        "graph_transit": "COMPLETE" if all_ok else "BLOCKED",
        "final_verdict": "CERTIFIED" if (verdict.result.value == "ALLOW" and all_ok) else "REJECTED",
    }

    print("\nVerdict Receipt:")
    _print_json(receipt)

    return 0 if receipt["final_verdict"] == "CERTIFIED" else 1


COMMANDS = {
    "propose": cmd_propose,
    "lint": cmd_lint,
    "diff": cmd_diff,
    "certify": cmd_certify,
}


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print("Usage: python -m cli.main <command> [args...]", file=sys.stderr)
        print(f"Commands: {', '.join(COMMANDS)}", file=sys.stderr)
        return 1

    command = argv[0]
    if command not in COMMANDS:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(f"Commands: {', '.join(COMMANDS)}", file=sys.stderr)
        return 1

    return COMMANDS[command](argv[1:])


if __name__ == "__main__":
    sys.exit(main())
