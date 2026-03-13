"""Transit and sector rotation schemas for the closed admissibility graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Node(Enum):
    """Admissibility graph nodes."""

    OBSERVE = "OBSERVE"
    INTERPRET_X = "INTERPRET_X"
    VERIFY = "VERIFY"
    ROUTE = "ROUTE"
    STOP = "STOP"


class Sector(Enum):
    """Sector rotation sectors."""

    A = "A"  # OBSERVE
    B = "B"  # INTERPRET
    C = "C"  # CONSTRAINT (blocking authority)
    D = "D"  # ROUTE


@dataclass(frozen=True)
class Transit:
    """Transition object carried between graph nodes.

    Attributes:
        source: Origin node.
        target: Destination node.
        kind: Type of transition.
        provenance: Non-empty provenance string.
        authority: Authority permitting this transition.
    """

    source: Node
    target: Node
    kind: str
    provenance: str
    authority: str

    def to_dict(self) -> dict:
        return {
            "source": self.source.value,
            "target": self.target.value,
            "kind": self.kind,
            "provenance": self.provenance,
            "authority": self.authority,
        }


@dataclass(frozen=True)
class TransitResult:
    """Result of a graph transit attempt."""

    allowed: bool
    transit: Transit
    reason: str


@dataclass
class SystemState:
    """Mutable system state for sector rotation tracking."""

    pressure: int = 0
    active_sector: Sector = Sector.A
    rotation_log: list[SectorRotationEvent] = field(default_factory=list)
    blocked: bool = False


@dataclass(frozen=True)
class SectorRotationEvent:
    """Observable event emitted during sector rotation."""

    trigger: str
    from_sector: Sector
    to_sector: Sector
    action: str
    detail: str
