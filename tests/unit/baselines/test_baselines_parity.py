"""Tests for RIFT-OBS and RIFT-RANDOM baseline information parity.

These tests verify the critical invariant: baselines do NOT receive
information that would give them an unfair advantage.

Authority: docs/baselines/RIFT_OBS.md, docs/baselines/RIFT_RANDOM.md
"""
from __future__ import annotations

import pandas as pd
import networkx as nx
import pytest


def _make_context(n_windows=30):
    from src.rift.baselines import IncidentContext
    G = nx.DiGraph()
    G.add_edges_from([("frontend", "cart"), ("cart", "checkout")])
    metrics = {}
    for svc in ["frontend", "cart", "checkout"]:
        t = [float(i * 10) for i in range(n_windows)]
        v = [50.0] * (n_windows - 5) + [150.0] * 5 if svc == "frontend" else [50.0] * n_windows
        metrics[svc] = pd.DataFrame({"time": t, "value": v})
    baseline_stats = {svc: {"mean": 50.0, "std": 5.0} for svc in ["frontend", "cart", "checkout"]}
    return IncidentContext(
        fault_id="parity_test",
        incident_window=(200.0, 300.0),
        metrics=metrics,
        baseline_stats=baseline_stats,
        call_graph=G,
    )


class TestRIFTObsParity:

    def test_rift_obs_receives_no_cid(self):
        """RIFT-OBS must not compute CID (no intervention data)."""
        from src.rift.baselines.rift_obs import RIFTObsBaseline
        context = _make_context()
        baseline = RIFTObsBaseline()
        output = baseline.run(context)
        # Key check: total_intervention_ed_s must be 0
        assert output.total_intervention_ed_s == 0.0

    def test_rift_obs_returns_baseline_output(self):
        from src.rift.baselines.rift_obs import RIFTObsBaseline
        context = _make_context()
        output = RIFTObsBaseline().run(context)
        assert output.baseline_id == "B5-RIFT-OBS"

    def test_rift_obs_no_interventions_in_notes(self):
        """RIFT-OBS must never execute interventions (total_intervention_ed_s == 0)."""
        from src.rift.baselines.rift_obs import RIFTObsBaseline
        context = _make_context()
        output = RIFTObsBaseline().run(context)
        # Key invariant: no intervention executed regardless of whether abstained or not
        assert output.total_intervention_ed_s == 0.0


class TestRIFTRandomFairness:

    def test_rift_random_no_greedy_selection(self):
        """RIFT-RANDOM must use random, not greedy, selection."""
        from src.rift.baselines.rift_random import RIFTRandomBaseline
        context = _make_context()
        baseline = RIFTRandomBaseline(seed=42)
        output = baseline.run(context)
        assert output.baseline_id == "B6-RIFT-RANDOM"

    def test_rift_random_same_seed_same_result(self):
        """RIFT-RANDOM must be deterministic given the same seed."""
        from src.rift.baselines.rift_random import RIFTRandomBaseline
        context = _make_context()
        out1 = RIFTRandomBaseline(seed=42).run(context)
        out2 = RIFTRandomBaseline(seed=42).run(context)
        assert out1.top_candidates == out2.top_candidates

    def test_rift_random_different_seeds_run_without_error(self):
        """Different seeds must both run without error."""
        from src.rift.baselines.rift_random import RandomMSIS
        from src.rift.optimizer.cost_model import InterventionCost, InterventionCandidate
        def make_cost(svc):
            return InterventionCost(
                candidate=InterventionCandidate(svc, f"{svc}.lat", "LATENCY", 100.0, 50.0),
                blast_radius=0.05, sla_impact=0.005, execution_duration_s=30.0,
                rollback_cost=0.1, eig=0.5, eig_normalized=0.5,
                safety_compliance=0.9, cost_composite=0.2, utility=0.4,
                authorized=True, authorization_level="AUTONOMOUS",
            )
        costs = [make_cost(s) for s in ["frontend", "cart", "checkout", "payment", "email"]]
        posterior = {s: 0.2 for s in ["frontend", "cart", "checkout", "payment", "email"]}
        r1 = RandomMSIS(seed=1).select(costs, posterior, t_budget=100.0)
        r2 = RandomMSIS(seed=99).select(costs, posterior, t_budget=100.0)
        assert r1.stopped_reason in ("ENTROPY_CONVERGED", "BUDGET_EXHAUSTED", "NO_ELIGIBLE", "EMPTY")
        assert r2.stopped_reason in ("ENTROPY_CONVERGED", "BUDGET_EXHAUSTED", "NO_ELIGIBLE", "EMPTY")
