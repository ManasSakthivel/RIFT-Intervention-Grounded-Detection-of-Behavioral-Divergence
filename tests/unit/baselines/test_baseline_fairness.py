"""Baseline Fairness Automated Checks — Phase 4.5

Verifies that all baselines satisfy the fairness requirements:
  1. Same IncidentContext input (no extra information to any baseline)
  2. No information leakage from ground truth to baselines
  3. All baselines produce BaselineOutput (same schema)
  4. Sage+Chaos is DEFERRED and never produces real results
  5. ORACLE-UPPER-BOUND is correctly labeled

Authority: docs/baseline_information_matrix.md, docs/baseline_specification.md
"""
from __future__ import annotations

import inspect
import warnings
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
import pandas as pd
import pytest

from rift.baselines import BaselineInterface, BaselineOutput, IncidentContext
from rift.baselines.oracle import OracleUpperBound, OracleGroundTruth
from rift.baselines.rift_obs import RIFTObsBaseline
from rift.baselines.rift_random import RIFTRandomBaseline
from rift.baselines.sieve_like import SieveLikeBaseline
from rift.baselines.sage_chaos import SageChaosStub


# ---------------------------------------------------------------------------
# Shared test fixture: identical IncidentContext for all baselines
# ---------------------------------------------------------------------------

def _make_incident_context(seed: int = 42) -> IncidentContext:
    """Build a minimal but realistic IncidentContext usable by all baselines."""
    rng = np.random.default_rng(seed)
    services = ["frontend", "cart", "checkout", "payment"]
    t_start, t_end = 60.0, 360.0
    n_points = 31

    metrics: Dict[str, pd.DataFrame] = {}
    baseline_stats: Dict[str, Dict[str, float]] = {}

    for i, svc in enumerate(services):
        times = [t_start + j * 10.0 for j in range(n_points)]
        values = list(rng.normal(50.0, 5.0, n_points))
        # Inject anomaly on frontend (index 0)
        if i == 0:
            for k in range(n_points - 5, n_points):
                values[k] = 80.0 + rng.normal(0, 2.0)
        metrics[svc] = pd.DataFrame({"time": times, "value": values})
        baseline_stats[svc] = {"mean": 50.0, "std": 5.0}

    call_graph = nx.DiGraph()
    call_graph.add_edges_from([
        ("frontend", "cart"),
        ("frontend", "checkout"),
        ("checkout", "payment"),
    ])

    return IncidentContext(
        fault_id="NL_01",
        incident_window=(t_start, t_end),
        metrics=metrics,
        baseline_stats=baseline_stats,
        call_graph=call_graph,
        scenario_seed=seed,
    )


# ---------------------------------------------------------------------------
# F1: All baselines use the same IncidentContext (interface check)
# ---------------------------------------------------------------------------

class TestSharedInputInterface:
    """F1: All baselines receive the same IncidentContext, nothing more."""

    BASELINE_CLASSES = [
        RIFTObsBaseline,
        RIFTRandomBaseline,
        SieveLikeBaseline,
        SageChaosStub,
    ]

    def test_all_baselines_implement_baseline_interface(self):
        for cls in self.BASELINE_CLASSES:
            assert issubclass(cls, BaselineInterface), (
                f"{cls.__name__} does not implement BaselineInterface"
            )

    def test_all_baselines_run_accepts_only_incident_context(self):
        """run() must accept exactly (self, context: IncidentContext) — no extra required params."""
        for cls in self.BASELINE_CLASSES:
            sig = inspect.signature(cls.run)
            params = list(sig.parameters.keys())
            # Must have 'self' and 'context' as the only required params
            required = [
                p for p in params
                if p != "self"
                and sig.parameters[p].default is inspect.Parameter.empty
            ]
            assert required == ["context"], (
                f"{cls.__name__}.run() has unexpected required parameters: {required}. "
                "All baselines must accept only IncidentContext."
            )

    def test_oracle_run_accepts_only_incident_context(self):
        sig = inspect.signature(OracleUpperBound.run)
        params = list(sig.parameters.keys())
        required = [
            p for p in params
            if p != "self"
            and sig.parameters[p].default is inspect.Parameter.empty
        ]
        assert required == ["context"]


# ---------------------------------------------------------------------------
# F2: All baselines produce BaselineOutput with correct schema
# ---------------------------------------------------------------------------

class TestOutputSchema:
    """F2: All baselines return BaselineOutput with required fields."""

    def _run_baseline(self, baseline: BaselineInterface) -> BaselineOutput:
        ctx = _make_incident_context()
        return baseline.run(ctx)

    def test_rift_obs_output_schema(self):
        out = self._run_baseline(RIFTObsBaseline())
        assert isinstance(out, BaselineOutput)
        assert out.baseline_id == "B5-RIFT-OBS"
        assert isinstance(out.fault_id, str)
        assert isinstance(out.top_candidates, list)
        assert isinstance(out.abstained, bool)

    def test_rift_random_output_schema(self):
        out = self._run_baseline(RIFTRandomBaseline())
        assert isinstance(out, BaselineOutput)
        assert "RIFT-RANDOM" in out.baseline_id or "B6" in out.baseline_id

    def test_sieve_like_output_schema(self):
        out = self._run_baseline(SieveLikeBaseline())
        assert isinstance(out, BaselineOutput)
        assert "SIEVE-LIKE" in out.baseline_id or "B3" in out.baseline_id

    def test_sage_chaos_output_schema(self):
        out = self._run_baseline(SageChaosStub())
        assert isinstance(out, BaselineOutput)
        assert out.baseline_id == "B4-SAGE-CHAOS"

    def test_oracle_output_schema(self):
        gt = OracleGroundTruth(
            ground_truth_service="frontend",
            ground_truth_fault_type="NETWORK_LATENCY",
            ground_truth_causal_path=[("frontend", "cart")],
        )
        out = OracleUpperBound(ground_truth=gt).run(_make_incident_context())
        assert isinstance(out, BaselineOutput)
        assert "ORACLE" in out.baseline_id

    def test_all_candidates_are_tuples(self):
        for cls in [RIFTObsBaseline, RIFTRandomBaseline, SieveLikeBaseline]:
            out = cls().run(_make_incident_context())
            for item in out.top_candidates:
                assert isinstance(item, tuple) and len(item) == 2, (
                    f"{cls.__name__} candidate {item} is not (service_id, score) tuple"
                )

    def test_scores_are_floats(self):
        for cls in [RIFTObsBaseline, RIFTRandomBaseline, SieveLikeBaseline]:
            out = cls().run(_make_incident_context())
            for svc, score in out.top_candidates:
                assert isinstance(score, (int, float)), (
                    f"{cls.__name__} score {score!r} is not numeric"
                )


# ---------------------------------------------------------------------------
# F3: No information leakage (ground truth not in IncidentContext)
# ---------------------------------------------------------------------------

class TestNoInformationLeakage:
    """F3: IncidentContext must not contain ground_truth_service."""

    def test_incident_context_has_no_ground_truth_field(self):
        ctx = _make_incident_context()
        assert not hasattr(ctx, "ground_truth_service"), (
            "IncidentContext must not expose ground_truth_service. "
            "Ground truth is in OracleGroundTruth only."
        )
        assert not hasattr(ctx, "root_cause_service"), (
            "IncidentContext must not expose root_cause_service."
        )

    def test_baseline_run_does_not_receive_ground_truth(self):
        """Verify run() signature does not accept a ground_truth parameter."""
        for cls in [RIFTObsBaseline, RIFTRandomBaseline, SieveLikeBaseline, SageChaosStub]:
            sig = inspect.signature(cls.run)
            param_names = set(sig.parameters.keys())
            assert "ground_truth" not in param_names, (
                f"{cls.__name__}.run() has a 'ground_truth' parameter — this is leakage."
            )
            assert "true_root_cause" not in param_names
            assert "label" not in param_names

    def test_oracle_ground_truth_is_separate_struct(self):
        """OracleGroundTruth is a separate struct; baselines cannot access it."""
        gt = OracleGroundTruth(
            ground_truth_service="cart",
            ground_truth_fault_type="PACKET_LOSS",
            ground_truth_causal_path=[("cart", "redis")],
        )
        # Non-oracle baselines do not have this struct
        rift_obs = RIFTObsBaseline()
        assert not hasattr(rift_obs, "_gt"), (
            "RIFTObs must not have access to ground truth struct."
        )
        sieve = SieveLikeBaseline()
        assert not hasattr(sieve, "_gt")


# ---------------------------------------------------------------------------
# F4: Sage+Chaos is DEFERRED and never produces real attributions
# ---------------------------------------------------------------------------

class TestSageChaosDeferred:
    """F4: Sage+Chaos must always abstain."""

    def test_sage_chaos_always_abstains(self):
        stub = SageChaosStub()
        for seed in (42, 99, 0, 1234):
            ctx = _make_incident_context(seed=seed)
            out = stub.run(ctx)
            assert out.abstained is True, (
                f"SageChaosStub must always abstain (seed={seed}). "
                "Do NOT fabricate Sage+Chaos results."
            )

    def test_sage_chaos_empty_candidates(self):
        out = SageChaosStub().run(_make_incident_context())
        assert out.top_candidates == []

    def test_sage_chaos_notes_say_deferred(self):
        out = SageChaosStub().run(_make_incident_context())
        assert "DEFERRED" in out.notes.upper()


# ---------------------------------------------------------------------------
# F5: Oracle is labeled ORACLE UPPER BOUND and not a fair baseline
# ---------------------------------------------------------------------------

class TestOracleLabeling:
    """F5: Oracle must be clearly labeled and only serves as an upper bound reference."""

    def test_oracle_baseline_id_contains_oracle(self):
        gt = OracleGroundTruth(
            ground_truth_service="frontend",
            ground_truth_fault_type="NETWORK_LATENCY",
            ground_truth_causal_path=[],
        )
        oracle = OracleUpperBound(ground_truth=gt)
        assert "ORACLE" in oracle.baseline_id.upper()

    def test_oracle_notes_say_upper_bound(self):
        gt = OracleGroundTruth(
            ground_truth_service="frontend",
            ground_truth_fault_type="NETWORK_LATENCY",
            ground_truth_causal_path=[],
        )
        out = OracleUpperBound(ground_truth=gt).run(_make_incident_context())
        assert "UPPER BOUND" in out.notes.upper() or "UPPER BOUND" in out.baseline_id.upper()

    def test_oracle_attributes_ground_truth_service(self):
        gt = OracleGroundTruth(
            ground_truth_service="frontend",
            ground_truth_fault_type="NETWORK_LATENCY",
            ground_truth_causal_path=[],
        )
        out = OracleUpperBound(ground_truth=gt).run(_make_incident_context())
        assert not out.abstained
        if out.top_candidates:
            assert out.top_candidates[0][0] == "frontend"


# ---------------------------------------------------------------------------
# F6: Same evaluation metrics available from all baselines
# ---------------------------------------------------------------------------

class TestSameEvaluationMetrics:
    """F6: All baselines produce outputs compatible with compute_attribution_metrics."""

    def test_output_fields_support_precision_at_1(self):
        """All baselines must have top_candidates and abstained fields for P@1."""
        for cls in [RIFTObsBaseline, RIFTRandomBaseline, SieveLikeBaseline]:
            out = cls().run(_make_incident_context())
            # P@1 needs: top_candidates and abstained
            assert hasattr(out, "top_candidates")
            assert hasattr(out, "abstained")

    def test_output_fields_support_detection_latency(self):
        """detection_latency_s may be None if not detected, but field must exist."""
        for cls in [RIFTObsBaseline, RIFTRandomBaseline, SieveLikeBaseline]:
            out = cls().run(_make_incident_context())
            assert hasattr(out, "detection_latency_s")

    def test_output_fields_support_intervention_cost(self):
        """total_intervention_ed_s must be 0 for non-intervening baselines."""
        for cls in [RIFTObsBaseline, SieveLikeBaseline, SageChaosStub]:
            out = cls().run(_make_incident_context())
            assert out.total_intervention_ed_s == 0.0, (
                f"{cls.__name__} should report 0 intervention cost."
            )
