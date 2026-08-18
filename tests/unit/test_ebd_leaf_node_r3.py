"""
Tests for P1-11 fix: R3 leaf-node fallback in EBD.

Verifies that the _check_r3() function correctly handles leaf-node services
(services with out-degree = 0 in the causal graph) via the upstream propagation fallback.

Formally defensible criterion:
  Primary R3: ∃ downstream service Vⱼ diverging s.t. Vᵢ →…→ Vⱼ
  R3-leaf:    if out_degree(Vᵢ) = 0, accept: ∃ upstream Vⱼ diverging s.t. Vⱼ →…→ Vᵢ

Authority: P1-11 resolution, src/rift/ebd/ebd.py _check_r3()
"""
from __future__ import annotations

import networkx as nx
import pytest


class TestR3LeafNodeFallback:
    """P1-11: R3 criterion must fire for leaf-node services via upstream propagation."""

    def _build_dag_with_leaf(self):
        """
        Build a simple call graph where redis_cart is a pure callee (leaf):
          frontend → cart → redis_cart
          cart is a mid-graph node (can reach redis_cart downstream)
          redis_cart has out-degree = 0 (leaf node)
        """
        G = nx.DiGraph()
        G.add_edges_from([
            ("frontend", "cart"),
            ("cart", "redis_cart"),
        ])
        return G

    def _build_dag_non_leaf(self):
        """
        Standard graph where checkout is NOT a leaf:
          frontend → checkout → payment
        """
        G = nx.DiGraph()
        G.add_edges_from([
            ("frontend", "checkout"),
            ("checkout", "payment"),
        ])
        return G

    def test_r3_fires_for_standard_non_leaf(self):
        """
        Standard R3: non-leaf service with downstream diverging service.
        checkout is not a leaf; payment diverges downstream.
        """
        from rift.ebd.ebd import _check_r3
        dag = self._build_dag_non_leaf()
        # frontend and payment both diverge
        divs = ["payment", "frontend"]
        pass_r3, path = _check_r3("checkout", divs, dag)
        assert pass_r3, "R3 must pass for checkout (has downstream diverging: payment)"
        assert len(path) > 0, "R3 path must be non-empty"

    def test_r3_leaf_fallback_fires_for_redis_cart(self):
        """
        P1-11: redis_cart is a leaf node (out-degree=0).
        Primary R3 fails (no downstream diverging service).
        R3-leaf must fire when upstream caller (cart) diverges.
        """
        from rift.ebd.ebd import _check_r3
        dag = self._build_dag_with_leaf()
        # cart diverges (upstream of redis_cart); no downstream services of redis_cart
        divs = ["cart", "frontend"]
        pass_r3, path = _check_r3("redis_cart", divs, dag)
        assert pass_r3, (
            "R3-leaf fallback must fire for redis_cart (leaf node) "
            "when upstream caller (cart) diverges"
        )
        assert len(path) > 0, "R3-leaf path must be non-empty"

    def test_r3_fails_for_leaf_with_no_upstream_divergence(self):
        """
        If redis_cart is a leaf node AND no upstream services diverge,
        R3 must still fail.
        """
        from rift.ebd.ebd import _check_r3
        dag = self._build_dag_with_leaf()
        # Only redis_cart itself is diverging — no upstream
        divs = []  # no other diverging services
        pass_r3, path = _check_r3("redis_cart", divs, dag)
        assert not pass_r3, "R3 must fail for leaf node with no diverging services"

    def test_r3_non_leaf_does_not_use_fallback(self):
        """
        Non-leaf services (out_degree > 0) must NOT use the R3-leaf fallback.
        Even if upstream services diverge, R3 for non-leaf requires downstream.
        """
        from rift.ebd.ebd import _check_r3
        dag = self._build_dag_non_leaf()
        # Only frontend diverges (upstream of checkout) — no downstream divergence
        divs = ["frontend"]  # frontend is upstream, not downstream
        pass_r3, path = _check_r3("checkout", divs, dag)
        # checkout has out-degree=1 (→ payment), so R3-leaf does NOT apply.
        # Primary R3 fails since no downstream divergence.
        assert not pass_r3, (
            "checkout is non-leaf; R3-leaf fallback must NOT apply. "
            "Only downstream divergence should trigger R3 for non-leaf."
        )

    def test_r3_leaf_node_in_isolated_graph(self):
        """
        Isolated graph: node not connected to anything.
        R3 must fail gracefully.
        """
        from rift.ebd.ebd import _check_r3
        dag = nx.DiGraph()
        dag.add_node("isolated_service")  # no edges
        pass_r3, path = _check_r3("isolated_service", ["other_service"], dag)
        # "other_service" is not in dag — R3 cannot resolve
        assert not pass_r3, "R3 must fail for isolated node with no causal connections"

    def test_r3_path_returned_for_leaf(self):
        """
        When R3-leaf fires, the returned path must be edges from upstream caller to leaf.
        """
        from rift.ebd.ebd import _check_r3
        dag = self._build_dag_with_leaf()
        divs = ["cart"]
        pass_r3, path = _check_r3("redis_cart", divs, dag)
        assert pass_r3
        # Path should contain the edge (cart, redis_cart)
        assert len(path) >= 1, "R3-leaf path must contain at least one edge"
        # Verify path represents a valid causal chain
        for src, tgt in path:
            assert dag.has_node(src) or dag.has_node(tgt), (
                f"Path edge ({src}, {tgt}) not in dag"
            )

    def test_r3_multi_hop_leaf(self):
        """
        Multi-hop: redis_cart is leaf but its upstream chain is frontend → cart → redis_cart.
        R3-leaf must fire when frontend diverges (reachable path exists).
        """
        from rift.ebd.ebd import _check_r3
        dag = self._build_dag_with_leaf()
        # Only frontend diverges (2 hops upstream of redis_cart)
        divs = ["frontend"]
        pass_r3, path = _check_r3("redis_cart", divs, dag)
        assert pass_r3, (
            "R3-leaf must fire for multi-hop upstream divergence (frontend→cart→redis_cart)"
        )

    def test_r3_payment_is_leaf_in_checkout_graph(self):
        """
        payment is a leaf in the checkout→payment graph.
        When only checkout diverges (upstream of payment), R3-leaf must fire.
        """
        from rift.ebd.ebd import _check_r3
        dag = nx.DiGraph()
        dag.add_edges_from([("checkout", "payment"), ("frontend", "checkout")])
        # payment has out-degree=0 (leaf), checkout diverges
        divs = ["checkout"]
        pass_r3, path = _check_r3("payment", divs, dag)
        assert pass_r3, (
            "R3-leaf must fire for payment (leaf) when checkout (upstream) diverges"
        )

    def test_r3_not_in_graph_returns_false(self):
        """
        Service not in dag at all must return False.
        """
        from rift.ebd.ebd import _check_r3
        dag = nx.DiGraph()
        dag.add_edges_from([("frontend", "cart")])
        pass_r3, path = _check_r3("unknown_service", ["cart"], dag)
        assert not pass_r3, "Service not in dag must return R3=False"


class TestR3LeafIntegration:
    """Integration: EBD correctly attributes root cause to leaf-node service."""

    def _make_leaf_context(self):
        """Build context where redis_cart (leaf node) is the anomalous service."""
        import pandas as pd
        import numpy as np
        from rift.baselines import IncidentContext
        from rift.fci.fci_runner import PAGResult

        services = ["frontend", "cart", "redis_cart"]
        t_start, t_end = 60.0, 360.0
        n_points = 31

        metrics = {}
        baseline_stats = {}
        rng = np.random.default_rng(42)
        for svc in services:
            times = [t_start + j * 10.0 for j in range(n_points)]
            values = list(rng.normal(50.0, 3.0, n_points))
            # redis_cart is anomalous — strong persistent deviation
            if svc == "redis_cart":
                for k in range(n_points - 10, n_points):
                    values[k] = 200.0 + rng.normal(0, 5.0)
            # cart shows secondary anomaly (later, downstream)
            elif svc == "cart":
                for k in range(n_points - 7, n_points):
                    values[k] = 120.0 + rng.normal(0, 3.0)
            metrics[svc] = pd.DataFrame({"time": times, "value": values})
            baseline_stats[svc] = {"mean": 50.0, "std": 5.0}

        G = nx.DiGraph()
        G.add_edges_from([("frontend", "cart"), ("cart", "redis_cart")])

        # Build minimal PAGResult with directed edges
        from rift.fci.fci_runner import PAGEdge, PAGEdgeType
        pag = PAGResult(
            variables=services,
            edges=[
                PAGEdge("frontend", "cart", PAGEdgeType.DIRECTED),
                PAGEdge("cart", "redis_cart", PAGEdgeType.DIRECTED),
            ]
        )

        return metrics, baseline_stats, pag, G, (t_start, t_end)

    def test_ebd_finds_redis_cart_as_candidate(self):
        """
        With R3-leaf fallback, EBD must find redis_cart as a CANDIDATE
        even though it has no downstream services.
        Without R3-leaf, redis_cart would be NONE confidence (P1-11 bug).
        """
        from rift.ebd.ebd import compute_ebd

        metrics, baseline_stats, pag, G, incident_window = self._make_leaf_context()

        results = compute_ebd(
            metrics=metrics,
            baselines=baseline_stats,
            pag_result=pag,
            incident_window=incident_window,
            cid_results=None,
            delta_t=10.0,
            theta_detect=3.0,
            theta_persist=2,
        )

        # Find redis_cart in results
        redis_result = next((r for r in results if r.service_id == "redis_cart"), None)

        # With R3-leaf fallback: redis_cart should be found as CANDIDATE
        assert redis_result is not None, (
            "EBD must return a result for redis_cart"
        )
        assert redis_result.confidence in ("CANDIDATE", "DEFINITIVE"), (
            f"redis_cart (leaf node) should be CANDIDATE or DEFINITIVE with R3-leaf. "
            f"Got: {redis_result.confidence}. "
            "If NONE: R3-leaf fallback is not working (P1-11 regression)."
        )
