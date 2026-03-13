"""Test closed graph: deny undeclared edges, invalid kinds, missing provenance."""

from __future__ import annotations

import pytest

from schemas.transit import Node, Transit
from graph.topology import ClosedAdmissibilityGraph


@pytest.fixture
def graph():
    return ClosedAdmissibilityGraph()


class TestEdgeExistence:
    def test_declared_edges_exist(self, graph):
        assert graph.edge_exists(Node.OBSERVE, Node.INTERPRET_X)
        assert graph.edge_exists(Node.INTERPRET_X, Node.VERIFY)
        assert graph.edge_exists(Node.VERIFY, Node.ROUTE)
        assert graph.edge_exists(Node.VERIFY, Node.STOP)

    def test_undeclared_edges_do_not_exist(self, graph):
        assert not graph.edge_exists(Node.OBSERVE, Node.ROUTE)
        assert not graph.edge_exists(Node.OBSERVE, Node.VERIFY)
        assert not graph.edge_exists(Node.OBSERVE, Node.STOP)
        assert not graph.edge_exists(Node.INTERPRET_X, Node.ROUTE)
        assert not graph.edge_exists(Node.INTERPRET_X, Node.STOP)
        assert not graph.edge_exists(Node.ROUTE, Node.OBSERVE)
        assert not graph.edge_exists(Node.STOP, Node.OBSERVE)

    def test_self_loops_denied(self, graph):
        for node in Node:
            assert not graph.edge_exists(node, node)

    def test_reverse_edges_denied(self, graph):
        assert not graph.edge_exists(Node.INTERPRET_X, Node.OBSERVE)
        assert not graph.edge_exists(Node.VERIFY, Node.INTERPRET_X)
        assert not graph.edge_exists(Node.ROUTE, Node.VERIFY)


class TestTransitAttempt:
    def test_valid_transit_observe_to_interpret(self, graph):
        t = Transit(Node.OBSERVE, Node.INTERPRET_X, "signal", "prov-1", "sensor")
        result = graph.attempt_transit(t)
        assert result.allowed is True

    def test_valid_transit_interpret_to_verify(self, graph):
        t = Transit(Node.INTERPRET_X, Node.VERIFY, "interpretation", "prov-1", "x_layer")
        result = graph.attempt_transit(t)
        assert result.allowed is True

    def test_valid_transit_verify_to_route(self, graph):
        t = Transit(Node.VERIFY, Node.ROUTE, "verified_transition", "prov-1", "verifier")
        result = graph.attempt_transit(t)
        assert result.allowed is True

    def test_valid_transit_verify_to_stop(self, graph):
        t = Transit(Node.VERIFY, Node.STOP, "rejection", "prov-1", "verifier")
        result = graph.attempt_transit(t)
        assert result.allowed is True

    def test_undeclared_edge_denied(self, graph):
        t = Transit(Node.OBSERVE, Node.ROUTE, "signal", "prov-1", "sensor")
        result = graph.attempt_transit(t)
        assert result.allowed is False
        assert "no declared edge" in result.reason

    def test_wrong_kind_denied(self, graph):
        t = Transit(Node.OBSERVE, Node.INTERPRET_X, "execution", "prov-1", "sensor")
        result = graph.attempt_transit(t)
        assert result.allowed is False
        assert "kind" in result.reason

    def test_wrong_authority_denied(self, graph):
        t = Transit(Node.OBSERVE, Node.INTERPRET_X, "signal", "prov-1", "admin")
        result = graph.attempt_transit(t)
        assert result.allowed is False
        assert "authority" in result.reason

    def test_empty_provenance_denied(self, graph):
        t = Transit(Node.OBSERVE, Node.INTERPRET_X, "signal", "", "sensor")
        result = graph.attempt_transit(t)
        assert result.allowed is False
        assert "provenance" in result.reason

    def test_whitespace_provenance_denied(self, graph):
        t = Transit(Node.OBSERVE, Node.INTERPRET_X, "signal", "   ", "sensor")
        result = graph.attempt_transit(t)
        assert result.allowed is False
        assert "provenance" in result.reason
