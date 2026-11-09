"""
test_sprint2_semidirected.py — Unit tests for Sprint 2 semi-directed graph semantics
and structural prior reachability in EBD and FCI.
"""
import pytest
import networkx as nx
import pandas as pd
import numpy as np

from rift.fci.fci_runner import PAGResult, PAGEdge, PAGEdgeType
from rift.ebd.ebd import _pag_to_digraph, compute_ebd, _check_r3


class TestSemiDirectedSemantics:
    def test_directed_edge_in_digraph(self):
        pag = PAGResult(
            variables=["A", "B"],
            edges=[PAGEdge("A", "B", PAGEdgeType.DIRECTED)],
        )
        g = _pag_to_digraph(pag, allow_semi_directed=True)
        assert g.has_edge("A", "B")
        assert not g.has_edge("B", "A")

    def test_partially_directed_edge(self):
        # A o-> B: B cannot be ancestor of A, so A -> B is admissible
        pag = PAGResult(
            variables=["A", "B"],
            edges=[PAGEdge("A", "B", PAGEdgeType.PARTIALLY_DIRECTED)],
        )
        g = _pag_to_digraph(pag, allow_semi_directed=True)
        assert g.has_edge("A", "B")
        assert not g.has_edge("B", "A")

    def test_undirected_edge_bidirectional_reachability(self):
        # A o-o B: both ancestral directions admissible in semi-directed path
        pag = PAGResult(
            variables=["A", "B"],
            edges=[PAGEdge("A", "B", PAGEdgeType.UNDIRECTED)],
        )
        g = _pag_to_digraph(pag, allow_semi_directed=True)
        assert g.has_edge("A", "B")
        assert g.has_edge("B", "A")

    def test_bidirected_edge_strictly_excluded_from_causal_paths(self):
        # A <-> B: unobserved confounder, neither is ancestor of the other
        pag = PAGResult(
            variables=["A", "B"],
            edges=[PAGEdge("A", "B", PAGEdgeType.BIDIRECTED)],
        )
        g = _pag_to_digraph(pag, allow_semi_directed=True)
        assert not g.has_edge("A", "B")
        assert not g.has_edge("B", "A")

    def test_r3_semi_directed_reachability(self):
        pag = PAGResult(
            variables=["frontend", "checkout", "payment"],
            edges=[
                PAGEdge("frontend", "checkout", PAGEdgeType.UNDIRECTED),
                PAGEdge("checkout", "payment", PAGEdgeType.PARTIALLY_DIRECTED),
            ],
        )
        g = _pag_to_digraph(pag, allow_semi_directed=True)
        passes, path = _check_r3("frontend", ["payment"], g)
        assert passes is True
        assert len(path) == 2
