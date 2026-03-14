[![CI](https://github.com/LalaSkye/interpretation-boundary-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/LalaSkye/interpretation-boundary-lab/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![stdlib only](https://img.shields.io/badge/dependencies-stdlib%20only-brightgreen)](pyproject.toml)

# interpretation-boundary-lab

**Deterministic admissibility gate for interpretation proposals — the governance layer upstream of every action.**

Most governance systems evaluate whether an action may execute.
This project evaluates whether the interpretation that produced the candidate action is itself admissible — before any execution-layer question arises.

This is an interpretation admissibility layer, not a framework.
It does not contain orchestration logic, agent wrappers, or alignment policy.
It contains deterministic rules for gating meaning construction
with fail-closed control and impermissibility as the default state.

## Why This Exists

Everyone else governs whether an action may execute. This governs whether an interpretation may exist.

Between a raw signal and an executed action, there is an interpretation step. That step introduces assumptions, collapses ambiguity, expands scope, and attributes intent. None of these operations are neutral. All of them can be tested against formal rules before any execution-layer question is even asked.

Faramesh (arXiv 2601.17744) states interpretation governance is "explicitly outside the scope." Thinking OS declares "you can't govern thinking directly." This project treats that as a design choice, not a physical constraint, and builds the gate anyway.

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
| `graph/replay.py` | `MeaningDriftReplay` — divergence analysis across interpreters |
| `cli/main.py` | CLI: propose, lint, diff, certify |

## Quick Start

```bash
git clone https://github.com/LalaSkye/interpretation-boundary-lab.git
cd interpretation-boundary-lab
python demo.py
```

Expected output (abbreviated):

```
interpretation-boundary-lab — Demo
Deterministic admissibility layer for interpretation proposals

============================================================
  1. VALID PROPOSAL — ALL RULES PASS
============================================================

Proposal: prop-valid-001
Result:   ALLOW
All 10 rules passed.

============================================================
  2. INVALID PROPOSAL — RULES FAIL
============================================================

Proposal: prop-invalid-001
Result:   DENY
  FAIL: EVIDENCE_ANCHOR_REQUIRED — source_span is empty
  FAIL: ASSUMPTION_COUNT_BOUND — 4 assumptions exceed threshold of 3
  FAIL: AMBIGUITY_PRESERVATION_REQUIRED — ambiguity markers present but omitted_alternatives is empty
  FAIL: CONFIDENCE_CONSEQUENCE_MATCH — LOW confidence with CRITICAL consequence
  FAIL: ACTOR_INTENT_ATTRIBUTION_BAN — claimed_intent contains mental state attribution
  FAIL: PROVENANCE_REQUIRED — provenance_hash is empty

============================================================
  3. GRAPH TRANSIT — UNDECLARED EDGES DENIED
============================================================

OBSERVE -> INTERPRET_X: ALLOWED (declared edge, kind=signal)
OBSERVE -> ROUTE:       DENIED (undeclared edge OBSERVE->ROUTE)
INTERPRET_X -> ROUTE:   DENIED (undeclared edge INTERPRET_X->ROUTE)
OBSERVE -> INTERPRET_X (wrong kind): DENIED (kind 'execution' not permitted on this edge)
OBSERVE -> INTERPRET_X (no prov):    DENIED (missing provenance)

============================================================
  4. SECTOR ROTATION — PRESSURE-ACTIVATED BLOCKING
============================================================

Initial sector: A, pressure: 0
  Pressure event 1: sector=A, pressure=1, blocked=False
  Pressure event 2: sector=A, pressure=2, blocked=False
  Pressure event 3: sector=C, pressure=3, blocked=True

After 3 denials: sector=C, blocked=True
Transit attempt while blocked: DENIED
  Reason: sector C active — all transits blocked

============================================================
  5. MEANING DRIFT REPLAY — DIVERGENCE ANALYSIS
============================================================

Signal: sig-drift-001
Proposals analyzed: 3
Admissible: 2, Inadmissible: 1

Divergences:
  claimed_object:
    drift-human: module 7 anomaly
    drift-llm: all modules are potentially compromised
    drift-policy: module 7 anomaly event
  consequence_class:
    drift-human: MEDIUM
    drift-llm: CRITICAL
    drift-policy: LOW

Verdicts:
  drift-human: ALLOW
  drift-llm: DENY
    - ASSUMPTION_COUNT_BOUND: 4 assumptions exceed threshold of 3
    - CONFIDENCE_CONSEQUENCE_MATCH: LOW confidence with CRITICAL consequence
    - ACTOR_INTENT_ATTRIBUTION_BAN: claimed_intent contains mental state attribution
  drift-policy: ALLOW
```

### Python API

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

## The 10 Admissibility Rules

| # | Rule | What It Catches |
|---|------|-----------------|
| 1 | `EVIDENCE_ANCHOR_REQUIRED` | `source_span` is empty — no evidential backing |
| 2 | `ASSUMPTION_COUNT_BOUND` | Assumption count exceeds threshold (default: 3) |
| 3 | `AMBIGUITY_PRESERVATION_REQUIRED` | Ambiguity markers present but `omitted_alternatives` is empty |
| 4 | `CONFIDENCE_CONSEQUENCE_MATCH` | HIGH/CRITICAL consequence with LOW confidence |
| 5 | `ACTOR_INTENT_ATTRIBUTION_BAN` | Mental state attribution without evidence |
| 6 | `SCOPE_DRIFT_FAIL` | Claimed object not derivable from source span |
| 7 | `TEMPORAL_DRIFT_FAIL` | Temporal claims not present in source signal |
| 8 | `PROHIBITED_INFERENTIAL_JUMP` | Correlation→causation, absence→denial, etc. |
| 9 | `PROVENANCE_REQUIRED` | Missing or empty provenance hash |
| 10 | `OMITTED_ALTERNATIVE_DETECTION` | Multiple plausible readings without documented alternatives |

## Design Constraints

- **Deterministic**: same inputs produce same outputs; no randomness, no ML
- **Fail-closed**: all unspecified states are impermissible by default
- **Minimal**: stdlib only, zero external dependencies for core
- **Auditable**: all rules are named, all decisions are traced with rule IDs and reasons
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

## Extension

[dual-boundary-admissibility-lab](https://github.com/LalaSkye/dual-boundary-admissibility-lab) subsumes this repo and adds a downstream mutation boundary, pressure monitoring corridor, full C-sector rotation with HALT/HOLD logic, and three adversarial fixes. Start here, extend there.

## Part of the Execution Boundary Series

| Repo | Layer | What It Does |
|---|---|---|
| [interpretation-boundary-lab](https://github.com/LalaSkye/interpretation-boundary-lab) | Upstream boundary | 10-rule admissibility gate for interpretations |
| [dual-boundary-admissibility-lab](https://github.com/LalaSkye/dual-boundary-admissibility-lab) | Full corridor | Dual-boundary model with pressure monitoring and C-sector rotation |
| [execution-boundary-lab](https://github.com/LalaSkye/execution-boundary-lab) | Execution boundary | Demonstrates cascading failures without upstream governance |
| [stop-machine](https://github.com/LalaSkye/stop-machine) | Control primitive | Deterministic three-state stop controller |
| [constraint-workshop](https://github.com/LalaSkye/constraint-workshop) | Control primitives | Authority gate, invariant litmus, stop machine |
| [csgr-lab](https://github.com/LalaSkye/csgr-lab) | Measurement | Contracted stability and drift measurement |
| [invariant-lock](https://github.com/LalaSkye/invariant-lock) | Drift prevention | Refuse execution unless version increments |
| [policy-lint](https://github.com/LalaSkye/policy-lint) | Policy validation | Deterministic linter for governance statements |
| [deterministic-lexicon](https://github.com/LalaSkye/deterministic-lexicon) | Vocabulary | Fixed terms, exact matches, no inference |

## License

Apache 2.0 — see [LICENSE](LICENSE).
