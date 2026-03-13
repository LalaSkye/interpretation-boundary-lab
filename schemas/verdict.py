"""InterpretationVerdict — admissibility decision with traced rule results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class VerdictResult(Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass(frozen=True)
class RuleFailure:
    """A single rule failure with the rule name and reason."""

    rule: str
    reason: str


@dataclass(frozen=True)
class InterpretationVerdict:
    """Stage 4 of the interpretation pipeline.

    ALLOW: all 10 rules passed.
    DENY: at least one rule failed (failures lists which ones and why).
    """

    proposal_id: str
    result: VerdictResult
    failures: tuple[RuleFailure, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "result": self.result.value,
            "failures": [
                {"rule": f.rule, "reason": f.reason} for f in self.failures
            ],
        }
