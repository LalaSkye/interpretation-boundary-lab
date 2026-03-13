"""ClosedAdmissibilityGraph — closed graph model where undeclared edges are denied."""

from __future__ import annotations

from dataclasses import dataclass, field

from schemas.transit import Node, Transit, TransitResult


@dataclass(frozen=True)
class EdgeSpec:
    """Specification of an allowed edge in the graph."""

    source: Node
    target: Node
    allowed_kinds: frozenset[str]
    allowed_authorities: frozenset[str]


# The four declared edges in the closed admissibility graph.
DECLARED_EDGES: tuple[EdgeSpec, ...] = (
    EdgeSpec(
        source=Node.OBSERVE,
        target=Node.INTERPRET_X,
        allowed_kinds=frozenset({"signal"}),
        allowed_authorities=frozenset({"sensor"}),
    ),
    EdgeSpec(
        source=Node.INTERPRET_X,
        target=Node.VERIFY,
        allowed_kinds=frozenset({"interpretation"}),
        allowed_authorities=frozenset({"x_layer"}),
    ),
    EdgeSpec(
        source=Node.VERIFY,
        target=Node.ROUTE,
        allowed_kinds=frozenset({"verified_transition"}),
        allowed_authorities=frozenset({"verifier"}),
    ),
    EdgeSpec(
        source=Node.VERIFY,
        target=Node.STOP,
        allowed_kinds=frozenset({"rejection"}),
        allowed_authorities=frozenset({"verifier"}),
    ),
)


class ClosedAdmissibilityGraph:
    """A closed graph where only explicitly declared edges are permitted.

    All undeclared edges are DENIED by default (fail-closed).
    Each transit must match edge existence, kind, authority, and provenance.
    """

    def __init__(self, edges: tuple[EdgeSpec, ...] = DECLARED_EDGES) -> None:
        self._edges: dict[tuple[Node, Node], EdgeSpec] = {
            (e.source, e.target): e for e in edges
        }

    def edge_exists(self, source: Node, target: Node) -> bool:
        """Check if an edge is declared between source and target."""
        return (source, target) in self._edges

    def attempt_transit(self, transit: Transit) -> TransitResult:
        """Attempt a transit through the graph.

        Checks:
        1. Edge exists between source and target.
        2. Kind is allowed for that edge.
        3. Authority is allowed for that edge.
        4. Provenance is non-empty.

        Returns:
            TransitResult with allowed=True/False and reason.
        """
        # Check edge existence
        key = (transit.source, transit.target)
        if key not in self._edges:
            return TransitResult(
                allowed=False,
                transit=transit,
                reason=f"no declared edge from {transit.source.value} "
                       f"to {transit.target.value}",
            )

        edge = self._edges[key]

        # Check provenance
        if not transit.provenance or not transit.provenance.strip():
            return TransitResult(
                allowed=False,
                transit=transit,
                reason="empty provenance",
            )

        # Check kind
        if transit.kind not in edge.allowed_kinds:
            return TransitResult(
                allowed=False,
                transit=transit,
                reason=f"kind '{transit.kind}' not in allowed kinds "
                       f"{sorted(edge.allowed_kinds)}",
            )

        # Check authority
        if transit.authority not in edge.allowed_authorities:
            return TransitResult(
                allowed=False,
                transit=transit,
                reason=f"authority '{transit.authority}' not in allowed authorities "
                       f"{sorted(edge.allowed_authorities)}",
            )

        return TransitResult(
            allowed=True,
            transit=transit,
            reason="transit permitted",
        )

    @property
    def declared_edges(self) -> tuple[EdgeSpec, ...]:
        """Return all declared edges."""
        return tuple(self._edges.values())
