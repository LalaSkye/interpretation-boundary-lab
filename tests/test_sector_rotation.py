"""Test pressure detection and sector rotation blocking."""

from __future__ import annotations

import pytest

from schemas.transit import Node, Transit, Sector
from graph.topology import ClosedAdmissibilityGraph
from graph.rotation import SectorEngine


@pytest.fixture
def engine():
    graph = ClosedAdmissibilityGraph()
    return SectorEngine(graph, threshold=3)


class TestPressureAccumulation:
    def test_initial_state(self, engine):
        assert engine.pressure == 0
        assert engine.blocked is False
        assert engine.active_sector == Sector.A

    def test_pressure_increments(self, engine):
        engine.record_pressure("test")
        assert engine.pressure == 1
        assert engine.blocked is False

    def test_below_threshold_no_block(self, engine):
        engine.record_pressure("test1")
        engine.record_pressure("test2")
        assert engine.pressure == 2
        assert engine.blocked is False


class TestSectorRotation:
    def test_rotation_at_threshold(self, engine):
        for i in range(3):
            engine.record_pressure(f"deny_{i}")
        assert engine.blocked is True
        assert engine.active_sector == Sector.C

    def test_rotation_emits_four_events(self, engine):
        for i in range(3):
            engine.record_pressure(f"deny_{i}")
        log = engine.state.rotation_log
        assert len(log) == 4
        actions = [e.action for e in log]
        assert actions == [
            "pressure_detected",
            "constraint_sector_rotation",
            "transition_block",
            "receipt_emitted",
        ]

    def test_rotation_only_once(self, engine):
        for i in range(5):
            engine.record_pressure(f"deny_{i}")
        # Should still only have 4 rotation events (rotated once at threshold)
        assert len(engine.state.rotation_log) == 4


class TestBlockedTransits:
    def test_valid_transit_blocked_after_rotation(self, engine):
        for i in range(3):
            engine.record_pressure(f"deny_{i}")

        t = Transit(Node.OBSERVE, Node.INTERPRET_X, "signal", "prov-1", "sensor")
        result = engine.attempt_transit(t)
        assert result.allowed is False
        assert "sector C" in result.reason

    def test_transit_allowed_before_rotation(self, engine):
        t = Transit(Node.OBSERVE, Node.INTERPRET_X, "signal", "prov-1", "sensor")
        result = engine.attempt_transit(t)
        assert result.allowed is True


class TestReset:
    def test_reset_clears_state(self, engine):
        for i in range(3):
            engine.record_pressure(f"deny_{i}")
        assert engine.blocked is True

        engine.reset()
        assert engine.pressure == 0
        assert engine.blocked is False
        assert engine.active_sector == Sector.A

    def test_transit_allowed_after_reset(self, engine):
        for i in range(3):
            engine.record_pressure(f"deny_{i}")
        engine.reset()

        t = Transit(Node.OBSERVE, Node.INTERPRET_X, "signal", "prov-1", "sensor")
        result = engine.attempt_transit(t)
        assert result.allowed is True
