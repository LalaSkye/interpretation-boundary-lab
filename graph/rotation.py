"""SectorEngine — pressure-activated sector rotation with synchronized blocking."""

from __future__ import annotations

from schemas.transit import (
    Sector,
    SystemState,
    SectorRotationEvent,
    Transit,
    TransitResult,
)
from graph.topology import ClosedAdmissibilityGraph


DEFAULT_PRESSURE_THRESHOLD = 3


class SectorEngine:
    """Manages sector rotation for the closed admissibility graph.

    Sectors:
        A = OBSERVE
        B = INTERPRET
        C = CONSTRAINT (blocking authority)
        D = ROUTE

    When pressure accumulates beyond threshold, control rotates to Sector C,
    which blocks all transitions without explicit constraint-sector approval.
    """

    def __init__(
        self,
        graph: ClosedAdmissibilityGraph,
        threshold: int = DEFAULT_PRESSURE_THRESHOLD,
    ) -> None:
        self._graph = graph
        self._threshold = threshold
        self._state = SystemState()

    @property
    def state(self) -> SystemState:
        return self._state

    @property
    def pressure(self) -> int:
        return self._state.pressure

    @property
    def blocked(self) -> bool:
        return self._state.blocked

    @property
    def active_sector(self) -> Sector:
        return self._state.active_sector

    def record_pressure(self, reason: str = "deny_verdict") -> None:
        """Record a pressure event (e.g., a DENY verdict).

        If pressure exceeds threshold, triggers sector rotation to C.
        """
        self._state.pressure += 1

        if self._state.pressure >= self._threshold and not self._state.blocked:
            self._rotate_to_constraint(reason)

    def _rotate_to_constraint(self, trigger: str) -> None:
        """Rotate control to Sector C (CONSTRAINT)."""
        prev_sector = self._state.active_sector

        event_detect = SectorRotationEvent(
            trigger=trigger,
            from_sector=prev_sector,
            to_sector=Sector.C,
            action="pressure_detected",
            detail=f"pressure {self._state.pressure} >= threshold {self._threshold}",
        )

        event_rotate = SectorRotationEvent(
            trigger=trigger,
            from_sector=prev_sector,
            to_sector=Sector.C,
            action="constraint_sector_rotation",
            detail="control transferred to constraint sector",
        )

        event_block = SectorRotationEvent(
            trigger=trigger,
            from_sector=Sector.C,
            to_sector=Sector.C,
            action="transition_block",
            detail="all non-approved transitions blocked",
        )

        event_receipt = SectorRotationEvent(
            trigger=trigger,
            from_sector=Sector.C,
            to_sector=Sector.C,
            action="receipt_emitted",
            detail="rotation receipt emitted for audit",
        )

        self._state.active_sector = Sector.C
        self._state.blocked = True
        self._state.rotation_log.extend([
            event_detect, event_rotate, event_block, event_receipt,
        ])

    def attempt_transit(self, transit: Transit) -> TransitResult:
        """Attempt a transit through the sector-aware graph.

        If the system is in blocked state (Sector C active), all transits
        are denied unless they carry constraint-sector authority.
        """
        if self._state.blocked:
            return TransitResult(
                allowed=False,
                transit=transit,
                reason="blocked by sector C — constraint rotation active",
            )

        return self._graph.attempt_transit(transit)

    def reset(self) -> None:
        """Reset pressure and unblock the system."""
        self._state.pressure = 0
        self._state.blocked = False
        self._state.active_sector = Sector.A
