"""InterpretationProposal — structured candidate meaning, NOT yet trusted."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ConfidenceClass(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ConsequenceClass(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class InterpretationProposal:
    """Structured candidate meaning. Stage 2 of the interpretation pipeline.

    This is a proposal, not a trusted interpretation. It must pass all
    admissibility rules before it can proceed to verdict/execution.
    """

    proposal_id: str
    signal_id: str
    actor: str
    source_span: str
    claimed_object: str
    claimed_intent: str
    risk_tags: tuple[str, ...] = field(default_factory=tuple)
    ambiguity_markers: tuple[str, ...] = field(default_factory=tuple)
    assumptions_introduced: tuple[str, ...] = field(default_factory=tuple)
    omitted_alternatives: tuple[str, ...] = field(default_factory=tuple)
    confidence_class: ConfidenceClass = ConfidenceClass.MEDIUM
    consequence_class: ConsequenceClass = ConsequenceClass.LOW

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "signal_id": self.signal_id,
            "actor": self.actor,
            "source_span": self.source_span,
            "claimed_object": self.claimed_object,
            "claimed_intent": self.claimed_intent,
            "risk_tags": list(self.risk_tags),
            "ambiguity_markers": list(self.ambiguity_markers),
            "assumptions_introduced": list(self.assumptions_introduced),
            "omitted_alternatives": list(self.omitted_alternatives),
            "confidence_class": self.confidence_class.value,
            "consequence_class": self.consequence_class.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> InterpretationProposal:
        return cls(
            proposal_id=data["proposal_id"],
            signal_id=data["signal_id"],
            actor=data["actor"],
            source_span=data.get("source_span", ""),
            claimed_object=data.get("claimed_object", ""),
            claimed_intent=data.get("claimed_intent", ""),
            risk_tags=tuple(data.get("risk_tags", ())),
            ambiguity_markers=tuple(data.get("ambiguity_markers", ())),
            assumptions_introduced=tuple(data.get("assumptions_introduced", ())),
            omitted_alternatives=tuple(data.get("omitted_alternatives", ())),
            confidence_class=ConfidenceClass(data.get("confidence_class", "MEDIUM")),
            consequence_class=ConsequenceClass(data.get("consequence_class", "LOW")),
        )
