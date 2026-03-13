"""10 named admissibility rule functions + evaluate_proposal().

Each rule function takes an InterpretationProposal and returns
(passed: bool, reason: str). A proposal must pass ALL rules to be admissible.
"""

from __future__ import annotations

from schemas.proposal import InterpretationProposal, ConfidenceClass, ConsequenceClass
from schemas.verdict import InterpretationVerdict, VerdictResult, RuleFailure

# Default configuration
ASSUMPTION_COUNT_THRESHOLD = 3

# Prohibited inferential patterns: (pattern_name, description)
PROHIBITED_PATTERNS = (
    "correlation_to_causation",
    "absence_to_denial",
    "silence_as_agreement",
    "partial_to_universal",
)

# Keywords indicating mental state attribution
MENTAL_STATE_KEYWORDS = (
    "believes",
    "intends",
    "wants",
    "desires",
    "fears",
    "hopes",
    "knows",
    "thinks",
    "feels",
    "motivated by",
    "trying to",
)


def evidence_anchor_required(proposal: InterpretationProposal) -> tuple[bool, str]:
    """RULE 1: source_span must be non-empty and present."""
    if not proposal.source_span or not proposal.source_span.strip():
        return False, "source_span is empty — no evidence anchor"
    return True, "evidence anchor present"


def assumption_count_bound(
    proposal: InterpretationProposal,
    threshold: int = ASSUMPTION_COUNT_THRESHOLD,
) -> tuple[bool, str]:
    """RULE 2: assumptions_introduced count must not exceed threshold."""
    count = len(proposal.assumptions_introduced)
    if count > threshold:
        return False, f"assumption count {count} exceeds threshold {threshold}"
    return True, f"assumption count {count} within threshold {threshold}"


def ambiguity_preservation_required(
    proposal: InterpretationProposal,
) -> tuple[bool, str]:
    """RULE 3: if ambiguity_markers exist, omitted_alternatives must document
    what was collapsed."""
    if proposal.ambiguity_markers and not proposal.omitted_alternatives:
        return (
            False,
            "ambiguity markers present but omitted_alternatives is empty — "
            "collapsed readings not documented",
        )
    return True, "ambiguity preservation satisfied"


def confidence_consequence_match(
    proposal: InterpretationProposal,
) -> tuple[bool, str]:
    """RULE 4: if consequence_class is HIGH or CRITICAL, confidence_class
    cannot be LOW."""
    high_consequence = proposal.consequence_class in (
        ConsequenceClass.HIGH,
        ConsequenceClass.CRITICAL,
    )
    if high_consequence and proposal.confidence_class == ConfidenceClass.LOW:
        return (
            False,
            f"confidence {proposal.confidence_class.value} insufficient for "
            f"consequence {proposal.consequence_class.value}",
        )
    return True, "confidence-consequence alignment satisfied"


def actor_intent_attribution_ban(
    proposal: InterpretationProposal,
) -> tuple[bool, str]:
    """RULE 5: claimed_intent must not attribute mental states to other actors
    unless evidence is cited."""
    intent_lower = proposal.claimed_intent.lower()
    for keyword in MENTAL_STATE_KEYWORDS:
        if keyword in intent_lower:
            # Check if source_span contains evidence for this attribution
            if keyword not in proposal.source_span.lower():
                return (
                    False,
                    f"claimed_intent attributes mental state '{keyword}' "
                    f"without evidence in source_span",
                )
    return True, "no unsupported mental state attribution"


def scope_drift_fail(proposal: InterpretationProposal) -> tuple[bool, str]:
    """RULE 6: claimed_object must be derivable from source_span.
    No scope expansion beyond evidence."""
    source_lower = proposal.source_span.lower()
    object_lower = proposal.claimed_object.lower()

    # Check for common scope expansion patterns
    expansion_pairs = [
        ("all ", "scope expansion to universal"),
        ("every ", "scope expansion to universal"),
        ("always ", "scope expansion to temporal universal"),
        ("never ", "scope expansion to temporal universal"),
    ]
    for marker, description in expansion_pairs:
        if marker in object_lower and marker not in source_lower:
            return False, f"{description}: '{marker.strip()}' not in source_span"

    return True, "no scope drift detected"


def temporal_drift_fail(proposal: InterpretationProposal) -> tuple[bool, str]:
    """RULE 7: interpretation must not introduce temporal claims not present
    in source signal."""
    source_lower = proposal.source_span.lower()
    intent_lower = proposal.claimed_intent.lower()
    object_lower = proposal.claimed_object.lower()
    combined = intent_lower + " " + object_lower

    temporal_markers = [
        ("historically", "historical claim"),
        ("in the past", "past temporal claim"),
        ("will always", "perpetual future claim"),
        ("has always been", "perpetual past claim"),
        ("never was", "past negation claim"),
        ("forever", "perpetual claim"),
    ]
    for marker, description in temporal_markers:
        if marker in combined and marker not in source_lower:
            return False, f"temporal drift: '{marker}' introduced without source evidence"

    return True, "no temporal drift detected"


def prohibited_inferential_jump(
    proposal: InterpretationProposal,
) -> tuple[bool, str]:
    """RULE 8: certain inferential patterns are banned."""
    intent_lower = proposal.claimed_intent.lower()
    object_lower = proposal.claimed_object.lower()
    combined = intent_lower + " " + object_lower

    pattern_indicators = {
        "correlation_to_causation": ["therefore causes", "causes", "caused by"],
        "absence_to_denial": [
            "absence of denial",
            "did not deny",
            "failure to deny",
            "lack of denial",
            "silence means",
        ],
        "silence_as_agreement": [
            "silence as consent",
            "silence implies agreement",
            "did not object",
            "failure to object",
        ],
        "partial_to_universal": [
            "some therefore all",
            "this proves all",
            "one case proves",
        ],
    }

    # Also check assumptions for prohibited patterns
    assumptions_lower = " ".join(a.lower() for a in proposal.assumptions_introduced)

    for pattern, indicators in pattern_indicators.items():
        for indicator in indicators:
            if indicator in combined or indicator in assumptions_lower:
                return (
                    False,
                    f"prohibited inferential jump: {pattern} detected via '{indicator}'",
                )

    return True, "no prohibited inferential jumps"


def provenance_required(proposal: InterpretationProposal) -> tuple[bool, str]:
    """RULE 9: signal must have non-empty provenance_hash.

    Note: This checks the proposal's signal_id as a proxy. For full provenance
    checking, the signal envelope's provenance_hash should be verified upstream.
    We accept a provenance_hash parameter for direct checking.
    """
    # This rule is evaluated with provenance_hash passed in via evaluate_proposal
    # When called directly on a proposal, we check signal_id as minimum provenance
    if not proposal.signal_id or not proposal.signal_id.strip():
        return False, "signal_id is empty — no provenance linkage"
    return True, "provenance linkage present"


def omitted_alternative_detection(
    proposal: InterpretationProposal,
) -> tuple[bool, str]:
    """RULE 10: if source_span admits multiple plausible readings,
    omitted_alternatives must be non-empty.

    Heuristic: presence of ambiguity_markers indicates multiple readings.
    """
    if proposal.ambiguity_markers and not proposal.omitted_alternatives:
        return (
            False,
            "source admits multiple readings (ambiguity markers present) "
            "but omitted_alternatives is empty",
        )
    return True, "omitted alternatives documented where needed"


# Ordered list of all rules
RULES: tuple[tuple[str, callable], ...] = (
    ("EVIDENCE_ANCHOR_REQUIRED", evidence_anchor_required),
    ("ASSUMPTION_COUNT_BOUND", assumption_count_bound),
    ("AMBIGUITY_PRESERVATION_REQUIRED", ambiguity_preservation_required),
    ("CONFIDENCE_CONSEQUENCE_MATCH", confidence_consequence_match),
    ("ACTOR_INTENT_ATTRIBUTION_BAN", actor_intent_attribution_ban),
    ("SCOPE_DRIFT_FAIL", scope_drift_fail),
    ("TEMPORAL_DRIFT_FAIL", temporal_drift_fail),
    ("PROHIBITED_INFERENTIAL_JUMP", prohibited_inferential_jump),
    ("PROVENANCE_REQUIRED", provenance_required),
    ("OMITTED_ALTERNATIVE_DETECTION", omitted_alternative_detection),
)


def evaluate_proposal(
    proposal: InterpretationProposal,
    provenance_hash: str = "",
) -> InterpretationVerdict:
    """Run all 10 admissibility rules against a proposal.

    Args:
        proposal: The interpretation proposal to evaluate.
        provenance_hash: The provenance hash from the source signal.
            If empty, PROVENANCE_REQUIRED will check signal_id instead.

    Returns:
        InterpretationVerdict with ALLOW or DENY result.
    """
    failures: list[RuleFailure] = []

    for rule_name, rule_fn in RULES:
        # Special handling for provenance rule — check actual hash
        if rule_name == "PROVENANCE_REQUIRED" and provenance_hash is not None:
            if not provenance_hash or not provenance_hash.strip():
                failures.append(RuleFailure(
                    rule=rule_name,
                    reason="provenance_hash is empty — no signal provenance",
                ))
                continue

        passed, reason = rule_fn(proposal)
        if not passed:
            failures.append(RuleFailure(rule=rule_name, reason=reason))

    if failures:
        return InterpretationVerdict(
            proposal_id=proposal.proposal_id,
            result=VerdictResult.DENY,
            failures=tuple(failures),
        )

    return InterpretationVerdict(
        proposal_id=proposal.proposal_id,
        result=VerdictResult.ALLOW,
    )
