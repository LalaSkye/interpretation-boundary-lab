[![CI](https://github.com/LalaSkye/interpretation-boundary-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/LalaSkye/interpretation-boundary-lab/actions/workflows/ci.yml)

# interpretation-boundary-lab

A deterministic admissibility layer for interpretation proposals before verdict and execution.

Most governance systems evaluate actions.
This project evaluates whether the interpretation that produced the candidate action is itself admissible.

This is an interpretation admissibility layer, not a framework.
It does not contain orchestration logic, agent wrappers, or alignment policy.
It contains deterministic rules for gating meaning construction
with fail-closed control and impermissibility as the default state.

## Why This Exists

Governance should not begin at action selection.
It should begin at admissible meaning construction.

Between a raw signal and an executed action, there is an interpretation step.
That interpretation step introduces assumptions, collapses ambiguity, expands scope, and attributes intent.
None of these operations are neutral. All of them should be testable.

This project provides:
- 10 named admissibility rules that gate interpretation proposals
- A closed graph topology where only declared edges are permitted
- Pressure-activated sector rotation for synchronized defensive blocking
- Meaning drift replay to show divergence across interpreters

## Architecture

```
signal → interpretation proposal → interpretation admissibility test → verdict/execution boundary
                                          │
                                    10 deterministic rules
                                          │
                                   ┌──────┴──────┐
                                   │             │
                                 ALLOW          DENY
                                   │         (rule IDs + reasons)
                                   │
                          closed admissibility graph
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                 OBSERVE → INTERPRET_X → VERIFY → ROUTE
                                                    │
                                                   STOP
                                                    │
                                          sector rotation (C)
```

## Modules

| Module | Description |
|--------|-------------|
| `schemas/signal.py` | `SignalEnvelope` — raw input schema |
| `schemas/proposal.py` | `InterpretationProposal` — structured candidate meaning |
| `schemas/verdict.py` | `InterpretationVerdict` — admissibility decision |
| `schemas/transit.py` | `Transit`, `Sector`, `SystemState` — graph transit schemas |
| `rules/admissibility.py` | 10 named rule functions + `evaluate_proposal()` |
| `graph/topology.py` | `ClosedAdmissibilityGraph` — fail-closed graph model |
| `graph/rotation.py` | `SectorEngine` — pressure detection + sector rotation |
| `graph/replay.py` | `MeaningDriftReplay` — divergence analysis |
| `cli/main.py` | CLI: propose, lint, diff, certify |

## Quickstart

### Python

```python
from schemas.signal import SignalEnvelope
from schemas.proposal import InterpretationProposal, ConfidenceClass, ConsequenceClass
from rules.admissibility import evaluate_proposal

signal = SignalEnvelope(
    source_id="sig-001",
    timestamp="2025-01-15T10:00:00Z",
    content="Product X has a defect in batch 42.",
    content_type="text/report",
    provenance_hash="sha256:abc123",
)

proposal = InterpretationProposal(
    proposal_id="prop-001",
    signal_id=signal.source_id,
    actor="analyst",
    source_span=signal.content,
    claimed_object="Product X batch 42 defect",
    claimed_intent="report defect for review",
    confidence_class=ConfidenceClass.HIGH,
    consequence_class=ConsequenceClass.MEDIUM,
)

verdict = evaluate_proposal(proposal, provenance_hash=signal.provenance_hash)
print(verdict.result.value)  # ALLOW
```

### CLI

```bash
# Generate a proposal scaffold from a signal
python -m cli.main propose examples/ai_moderation.json

# Lint a proposal against all 10 rules
python -m cli.main lint proposal.json

# Compare two proposals for divergence
python -m cli.main diff proposal_a.json proposal_b.json

# Full pipeline: admissibility + graph transit
python -m cli.main certify proposal.json
```

### Demo

```bash
python demo.py
```

## The 10 Admissibility Rules

| # | Rule | Description |
|---|------|-------------|
| 1 | `EVIDENCE_ANCHOR_REQUIRED` | source_span must be non-empty |
| 2 | `ASSUMPTION_COUNT_BOUND` | assumptions count must not exceed threshold (default: 3) |
| 3 | `AMBIGUITY_PRESERVATION_REQUIRED` | if ambiguity markers exist, omitted alternatives must document collapse |
| 4 | `CONFIDENCE_CONSEQUENCE_MATCH` | HIGH/CRITICAL consequence cannot pair with LOW confidence |
| 5 | `ACTOR_INTENT_ATTRIBUTION_BAN` | no mental state attribution without evidence |
| 6 | `SCOPE_DRIFT_FAIL` | claimed object must be derivable from source span |
| 7 | `TEMPORAL_DRIFT_FAIL` | no temporal claims not present in source |
| 8 | `PROHIBITED_INFERENTIAL_JUMP` | banned patterns: correlation→causation, absence→denial, etc. |
| 9 | `PROVENANCE_REQUIRED` | signal must have non-empty provenance hash |
| 10 | `OMITTED_ALTERNATIVE_DETECTION` | multiple plausible readings require documented alternatives |

## Design Constraints

- **Deterministic**: same inputs → same outputs, no randomness, no ML
- **Fail-closed**: all unspecified states are impermissible by default
- **Minimal**: stdlib only, zero external dependencies for core
- **Auditable**: all rules are named, all decisions are traced
- **Small**: each module ≤ 200 LOC where practical

## Key Invariants

1. X (INTERPRET_X) is a non-executing relay. It cannot create authority.
2. All unspecified states are impermissible by default.
3. Connectivity does not grant admissibility.
4. Interpretation does not grant authority.
5. Transition requires explicit constitutional permission.
6. Sector C rotation is pressure-activated, not failure-activated.
7. Every DENY includes the specific rule(s) that failed.

## Non-Goals

- This is not an agent framework
- This is not an alignment policy engine
- This is not an orchestration layer
- This does not make decisions — it gates whether interpretations are admissible for decision-making

## License

Apache 2.0 — see [LICENSE](LICENSE).
