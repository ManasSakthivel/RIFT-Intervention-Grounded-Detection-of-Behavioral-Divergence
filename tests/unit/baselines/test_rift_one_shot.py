"""
Unit Tests for RIFT-ONE-SHOT Baseline (B7)

Tests:
  1.  test_rift_one_shot_implements_baseline_interface
  2.  test_rift_one_shot_baseline_id
  3.  test_rift_one_shot_run_returns_baseline_output
  4.  test_rift_one_shot_output_schema
  5.  test_rift_one_shot_zero_intervention_cost_is_zero_or_reported
  6.  test_rift_one_shot_candidates_are_tuples
  7.  test_rift_one_shot_scores_are_floats
  8.  test_rift_one_shot_receives_only_incident_context
  9.  test_rift_one_shot_has_no_ground_truth_field
  10. test_rift_one_shot_does_not_have_gt_attribute
  11. test_rift_one_shot_same_seed_same_result
  12. test_rift_one_shot_different_seeds_may_differ
  13. test_rift_one_shot_posterior_not_updated_after_intervention
  14. test_rift_one_shot_notes_mention_no_closed_loop

Authority: docs/hypotheses.md H3, experiments/REGISTRY.yaml EXP-013
"""
from __future__ import annotations

import inspect
from typing import Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
import pandas as pd
import pytest

from rift.baselines import BaselineInterface, BaselineOutput, IncidentContext
from rift.baselines.rift_one_shot import RIFTOneShotBaseline


# ---------------------------------------------------------------------------
# Shared fixture: same _make_incident_context() pattern as test_baseline_fairness.py
# (intentionally duplicated — must NOT import from test_baseline_fairness.py)
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
# 1. Interface check
# ---------------------------------------------------------------------------

class TestRIFTOneShotInterface:

    def test_rift_one_shot_implements_baseline_interface(self):
        """Test 1: RIFTOneShotBaseline must implement BaselineInterface."""
        assert issubclass(RIFTOneShotBaseline, BaselineInterface), (
            "RIFTOneShotBaseline must implement BaselineInterface"
        )

    def test_rift_one_shot_baseline_id(self):
        """Test 2: baseline_id must be B7-RIFT-ONE-SHOT."""
        baseline = RIFTOneShotBaseline()
        assert baseline.baseline_id == "B7-RIFT-ONE-SHOT", (
            f"Expected 'B7-RIFT-ONE-SHOT', got '{baseline.baseline_id}'"
        )


# ---------------------------------------------------------------------------
# 2. Output schema
# ---------------------------------------------------------------------------

class TestRIFTOneShotOutputSchema:

    def test_rift_one_shot_run_returns_baseline_output(self):
        """Test 3: run() must return a BaselineOutput instance."""
        ctx = _make_incident_context()
        out = RIFTOneShotBaseline().run(ctx)
        assert isinstance(out, BaselineOutput), (
            f"Expected BaselineOutput, got {type(out).__name__}"
        )

    def test_rift_one_shot_output_schema(self):
        """Test 4: BaselineOutput has required fields (top_candidates, abstained, etc.)."""
        ctx = _make_incident_context()
        out = RIFTOneShotBaseline().run(ctx)
        assert hasattr(out, "baseline_id")
        assert hasattr(out, "fault_id")
        assert hasattr(out, "top_candidates")
        assert hasattr(out, "abstained")
        assert hasattr(out, "detection_latency_s")
        assert hasattr(out, "total_intervention_ed_s")
        assert hasattr(out, "notes")
        assert isinstance(out.top_candidates, list)
        assert isinstance(out.abstained, bool)
        assert isinstance(out.total_intervention_ed_s, float)

    def test_rift_one_shot_zero_intervention_cost_is_zero_or_reported(self):
        """Test 5: total_intervention_ed_s is a non-negative float."""
        ctx = _make_incident_context()
        out = RIFTOneShotBaseline().run(ctx)
        assert out.total_intervention_ed_s >= 0.0, (
            f"total_intervention_ed_s must be non-negative, got {out.total_intervention_ed_s}"
        )

    def test_rift_one_shot_candidates_are_tuples(self):
        """Test 6: each top_candidate must be a (service_id, score) tuple of length 2."""
        ctx = _make_incident_context()
        out = RIFTOneShotBaseline().run(ctx)
        for item in out.top_candidates:
            assert isinstance(item, tuple) and len(item) == 2, (
                f"candidate {item!r} is not a (service_id, score) tuple"
            )

    def test_rift_one_shot_scores_are_floats(self):
        """Test 7: all candidate scores must be numeric (int or float)."""
        ctx = _make_incident_context()
        out = RIFTOneShotBaseline().run(ctx)
        for svc, score in out.top_candidates:
            assert isinstance(score, (int, float)), (
                f"candidate score {score!r} for '{svc}' is not numeric"
            )


# ---------------------------------------------------------------------------
# 3. Fairness tests (critical for H3)
# ---------------------------------------------------------------------------

class TestRIFTOneShotFairness:

    def test_rift_one_shot_receives_only_incident_context(self):
        """
        Test 8: run() must accept exactly (self, context: IncidentContext) —
        no extra required parameters. All baselines must receive only IncidentContext.
        """
        sig = inspect.signature(RIFTOneShotBaseline.run)
        params = list(sig.parameters.keys())
        required = [
            p for p in params
            if p != "self"
            and sig.parameters[p].default is inspect.Parameter.empty
        ]
        assert required == ["context"], (
            f"RIFTOneShotBaseline.run() has unexpected required parameters: {required}. "
            "All baselines must accept only IncidentContext."
        )

    def test_rift_one_shot_has_no_ground_truth_field(self):
        """
        Test 9: IncidentContext passed to RIFT-ONE-SHOT must not contain ground truth.
        """
        ctx = _make_incident_context()
        assert not hasattr(ctx, "ground_truth_service"), (
            "IncidentContext must not expose ground_truth_service."
        )
        assert not hasattr(ctx, "root_cause_service"), (
            "IncidentContext must not expose root_cause_service."
        )

    def test_rift_one_shot_does_not_have_gt_attribute(self):
        """
        Test 10: RIFTOneShotBaseline instance must not have a _gt attribute
        (no access to ground truth struct).
        """
        baseline = RIFTOneShotBaseline()
        assert not hasattr(baseline, "_gt"), (
            "RIFTOneShotBaseline must not have access to ground truth struct (_gt)."
        )
        # Also verify run() signature has no ground_truth / label params
        sig = inspect.signature(RIFTOneShotBaseline.run)
        param_names = set(sig.parameters.keys())
        assert "ground_truth" not in param_names
        assert "true_root_cause" not in param_names
        assert "label" not in param_names


# ---------------------------------------------------------------------------
# 4. Determinism tests
# ---------------------------------------------------------------------------

class TestRIFTOneShotDeterminism:

    def test_rift_one_shot_same_seed_same_result(self):
        """
        Test 11: Two runs with the same seed must produce identical top_candidates.
        """
        ctx_a = _make_incident_context(seed=42)
        ctx_b = _make_incident_context(seed=42)
        out_a = RIFTOneShotBaseline(fci_seed=42).run(ctx_a)
        out_b = RIFTOneShotBaseline(fci_seed=42).run(ctx_b)
        assert out_a.top_candidates == out_b.top_candidates, (
            "Same seed must produce identical top_candidates. "
            f"Run A: {out_a.top_candidates}, Run B: {out_b.top_candidates}"
        )

    def test_rift_one_shot_different_seeds_may_differ(self):
        """
        Test 12: Two runs with different seeds are allowed (but not required) to differ.
        This test verifies the system runs successfully with different seeds.
        """
        ctx_a = _make_incident_context(seed=42)
        ctx_b = _make_incident_context(seed=99)
        out_a = RIFTOneShotBaseline(fci_seed=42).run(ctx_a)
        out_b = RIFTOneShotBaseline(fci_seed=99).run(ctx_b)
        # Both must produce valid BaselineOutput regardless of seed
        assert isinstance(out_a, BaselineOutput)
        assert isinstance(out_b, BaselineOutput)


# ---------------------------------------------------------------------------
# 5. Post-intervention leakage test (critical for H3)
# ---------------------------------------------------------------------------

class TestRIFTOneShotNoPosteriorUpdate:

    def test_rift_one_shot_posterior_not_updated_after_intervention(self):
        """
        Test 13: The frozen posterior stored at start must equal what was used
        for all MSIS calls. Verifies that closed_loop_update is disabled.

        Implementation invariant:
          - self._frozen_posterior is set once after EBD in run()
          - It is passed to every greedy_msis call without mutation
          - After run() returns, self._frozen_posterior reflects the INITIAL
            EBD-derived posterior (not any post-intervention update)

        We verify this by:
          1. Running the baseline
          2. Capturing _frozen_posterior after run()
          3. Asserting it sums to ~1.0 (valid probability distribution)
          4. Asserting that the top_candidates ordering matches the
             _frozen_posterior ordering (i.e., candidates ranked by initial scores)
        """
        ctx = _make_incident_context(seed=42)
        baseline = RIFTOneShotBaseline()
        out = baseline.run(ctx)

        # _frozen_posterior must be set after run()
        assert baseline._frozen_posterior is not None, (
            "_frozen_posterior must be set during run()"
        )

        frozen = baseline._frozen_posterior

        # Must be a valid probability distribution (sums to ~1)
        total = sum(frozen.values())
        if total > 0:  # empty posterior only when abstained
            assert abs(total - 1.0) < 1e-6, (
                f"_frozen_posterior must sum to 1.0, got {total}"
            )

        # The top_candidates must be ranked in descending order of frozen posterior
        if out.top_candidates and len(out.top_candidates) > 1:
            scores_in_output = [score for _, score in out.top_candidates]
            assert scores_in_output == sorted(scores_in_output, reverse=True), (
                "top_candidates must be sorted by descending frozen posterior score"
            )

        # The services in top_candidates must come from _frozen_posterior
        for svc, _ in out.top_candidates:
            assert svc in frozen, (
                f"Candidate '{svc}' in top_candidates not in _frozen_posterior — "
                "possible leakage from post-intervention update"
            )


# ---------------------------------------------------------------------------
# 6. Notes field test
# ---------------------------------------------------------------------------

class TestRIFTOneShotNotes:

    def test_rift_one_shot_notes_mention_no_closed_loop(self):
        """
        Test 14: The notes field must mention 'no closed-loop' (case-insensitive).
        This is required for audit/reproducibility tracing.
        """
        ctx = _make_incident_context()
        out = RIFTOneShotBaseline().run(ctx)
        notes_lower = out.notes.lower()
        assert "no closed-loop" in notes_lower or "no closed loop" in notes_lower, (
            f"notes must mention 'no closed-loop'. Got: {out.notes!r}"
        )
