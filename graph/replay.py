"""MeaningDriftReplay — divergence analysis across multiple interpreters."""

from __future__ import annotations

from dataclasses import dataclass, field

from schemas.proposal import InterpretationProposal
from schemas.verdict import InterpretationVerdict, VerdictResult
from rules.admissibility import evaluate_proposal


@dataclass(frozen=True)
class FieldDivergence:
    """Records divergence for a single field across proposals."""

    field_name: str
    values: tuple[tuple[str, str], ...]  # (proposal_id, value) pairs


@dataclass(frozen=True)
class DriftReport:
    """Report showing where interpretation drift entered across proposals."""

    signal_id: str
    proposal_count: int
    divergences: tuple[FieldDivergence, ...]
    verdicts: tuple[tuple[str, InterpretationVerdict], ...]  # (proposal_id, verdict)
    unsupported_steps: tuple[tuple[str, str], ...]  # (proposal_id, description)

    @property
    def admissible_count(self) -> int:
        return sum(
            1 for _, v in self.verdicts if v.result == VerdictResult.ALLOW
        )

    @property
    def inadmissible_count(self) -> int:
        return sum(
            1 for _, v in self.verdicts if v.result == VerdictResult.DENY
        )


# Fields to compare for divergence
_COMPARISON_FIELDS = (
    "claimed_object",
    "claimed_intent",
    "confidence_class",
    "consequence_class",
)


class MeaningDriftReplay:
    """Analyzes divergence across multiple interpretation proposals
    from different interpreters for the same source signal."""

    def analyze(
        self,
        proposals: list[InterpretationProposal],
        provenance_hash: str = "",
    ) -> DriftReport:
        """Produce a DriftReport for a set of proposals sharing a signal.

        Args:
            proposals: Multiple proposals for the same source signal.
            provenance_hash: Provenance hash for admissibility evaluation.

        Returns:
            DriftReport with divergences, verdicts, and unsupported steps.
        """
        if not proposals:
            raise ValueError("at least one proposal is required")

        signal_id = proposals[0].signal_id

        # Compute divergences
        divergences = self._compute_divergences(proposals)

        # Evaluate each proposal
        verdicts: list[tuple[str, InterpretationVerdict]] = []
        for p in proposals:
            verdict = evaluate_proposal(p, provenance_hash=provenance_hash)
            verdicts.append((p.proposal_id, verdict))

        # Find unsupported inferential steps
        unsupported = self._find_unsupported_steps(proposals, verdicts)

        return DriftReport(
            signal_id=signal_id,
            proposal_count=len(proposals),
            divergences=tuple(divergences),
            verdicts=tuple(verdicts),
            unsupported_steps=tuple(unsupported),
        )

    def _compute_divergences(
        self, proposals: list[InterpretationProposal],
    ) -> list[FieldDivergence]:
        """Find fields that differ across proposals."""
        divergences: list[FieldDivergence] = []

        for field_name in _COMPARISON_FIELDS:
            values: list[tuple[str, str]] = []
            for p in proposals:
                val = getattr(p, field_name)
                if hasattr(val, "value"):
                    val = val.value
                values.append((p.proposal_id, str(val)))

            # Check if all values are the same
            unique = set(v for _, v in values)
            if len(unique) > 1:
                divergences.append(FieldDivergence(
                    field_name=field_name,
                    values=tuple(values),
                ))

        return divergences

    def _find_unsupported_steps(
        self,
        proposals: list[InterpretationProposal],
        verdicts: list[tuple[str, InterpretationVerdict]],
    ) -> list[tuple[str, str]]:
        """Identify unsupported inferential steps from failed proposals."""
        unsupported: list[tuple[str, str]] = []

        for proposal_id, verdict in verdicts:
            if verdict.result == VerdictResult.DENY:
                for failure in verdict.failures:
                    unsupported.append((proposal_id, f"{failure.rule}: {failure.reason}"))

        return unsupported
