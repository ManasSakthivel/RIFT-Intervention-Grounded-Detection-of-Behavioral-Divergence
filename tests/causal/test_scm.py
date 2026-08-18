"""
tests/causal/test_scm.py
RIFT Phase 3B — Test suite for time-sliced SCM.

Covers:
  1. Each synthetic SCM has the correct edge structure.
  2. Mutilation correctly removes incoming edges and replaces equations.
  3. Sampling from observational and interventional distributions works.
  4. Acyclicity check detects cycles; feedback SCM is acyclic by construction.
  5. Confounder SCM: P(Y|X=x) ≠ P(Y|do(X:=x))  — correlation ≠ causation.
  6. Queueing SCM: queue depth increases as ρ → 1.
  7. Time-sliced feedback does NOT create cycles.

All tests are deterministic with fixed seeds.
"""

from __future__ import annotations

import math
from typing import Dict

import numpy as np
import pandas as pd
import pytest

from rift.scm.scm import (
    SCM,
    StructuralEquation,
    TimeSlicedVariable,
    make_chain_scm,
    make_collider_scm,
    make_confounder_scm,
    make_feedback_scm,
    make_fork_scm,
    make_mediated_scm,
    make_queueing_scm,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _edge_set(scm: SCM) -> set[tuple[str, str]]:
    """Return the edge set as (parent_key, child_key) tuples."""
    return set(scm.edges())


def _sample_mean(scm: SCM, var_key: str, n: int = 5000, seed: int = 0) -> float:
    df = scm.sample(n, seed=seed)
    return float(df[var_key].mean())


def _sample_interventional_mean(
    scm: SCM,
    interventions: Dict[str, float],
    var_key: str,
    n: int = 5000,
    seed: int = 0,
) -> float:
    df = scm.sample_interventional(interventions, n, seed=seed)
    return float(df[var_key].mean())


# ---------------------------------------------------------------------------
# 1. Edge structure tests
# ---------------------------------------------------------------------------

class TestEdgeStructure:

    def test_chain_edges(self):
        scm = make_chain_scm()
        edges = _edge_set(scm)
        assert ("X__t0", "Y__t1") in edges, "chain: X→Y edge missing"
        assert ("Y__t1", "Z__t2") in edges, "chain: Y→Z edge missing"
        assert len(edges) == 2, f"chain: expected exactly 2 edges, got {len(edges)}"

    def test_fork_edges(self):
        scm = make_fork_scm()
        edges = _edge_set(scm)
        assert ("X__t0", "Y__t1") in edges, "fork: X→Y edge missing"
        assert ("X__t0", "Z__t1") in edges, "fork: X→Z edge missing"
        assert len(edges) == 2, f"fork: expected exactly 2 edges, got {len(edges)}"

    def test_collider_edges(self):
        scm = make_collider_scm()
        edges = _edge_set(scm)
        assert ("X__t0", "Z__t1") in edges, "collider: X→Z edge missing"
        assert ("Y__t0", "Z__t1") in edges, "collider: Y→Z edge missing"
        # No X→Y or Y→X edge
        assert ("X__t0", "Y__t0") not in edges, "collider: spurious X→Y edge"
        assert ("Y__t0", "X__t0") not in edges, "collider: spurious Y→X edge"
        assert len(edges) == 2, f"collider: expected 2 edges, got {len(edges)}"

    def test_mediated_edges(self):
        scm = make_mediated_scm()
        edges = _edge_set(scm)
        assert ("X__t0", "M__t1") in edges, "mediated: X→M edge missing"
        assert ("M__t1", "Y__t2") in edges, "mediated: M→Y edge missing"
        # No direct X→Y edge (all effect is mediated)
        assert ("X__t0", "Y__t2") not in edges, "mediated: direct X→Y edge present"
        assert len(edges) == 2, f"mediated: expected 2 edges, got {len(edges)}"

    def test_confounder_edges(self):
        scm = make_confounder_scm()
        edges = _edge_set(scm)
        # U→X and U→Y; no X→Y or Y→X
        assert ("U__t0", "X__t0") in edges, "confounder: U→X edge missing"
        assert ("U__t0", "Y__t0") in edges, "confounder: U→Y edge missing"
        assert ("X__t0", "Y__t0") not in edges, "confounder: spurious X→Y edge"
        assert ("Y__t0", "X__t0") not in edges, "confounder: spurious Y→X edge"
        assert len(edges) == 2, f"confounder: expected 2 edges, got {len(edges)}"

    def test_feedback_edges(self):
        scm = make_feedback_scm()
        edges = _edge_set(scm)
        assert ("X__t0", "Y__t1") in edges, "feedback: X[t0]→Y[t1] missing"
        assert ("Y__t1", "X__t2") in edges, "feedback: Y[t1]→X[t2] missing"
        assert len(edges) == 2, f"feedback: expected 2 edges, got {len(edges)}"

    def test_queueing_edges(self):
        scm = make_queueing_scm()
        edges = _edge_set(scm)
        # arrival_rate and service_rate → queue_depth
        assert ("arrival_rate__t0", "queue_depth__t1") in edges, "queueing: arr→qdepth missing"
        assert ("service_rate__t0", "queue_depth__t1") in edges, "queueing: svc→qdepth missing"
        # queue_depth, arr, svc → latency
        assert ("queue_depth__t1", "latency__t1") in edges, "queueing: qdepth→lat missing"
        assert ("arrival_rate__t0", "latency__t1") in edges, "queueing: arr→lat missing"
        assert ("service_rate__t0", "latency__t1") in edges, "queueing: svc→lat missing"


# ---------------------------------------------------------------------------
# 2. Mutilation tests
# ---------------------------------------------------------------------------

class TestMutilation:

    def test_mutilate_removes_parents(self):
        """Mutilating X in chain SCM removes all parents of X's equation."""
        scm = make_chain_scm()
        mutilated = scm.mutilate({"Y__t1": 2.0})
        assert mutilated.equations["Y__t1"].parents == [], (
            "mutilated Y should have no parents"
        )
        # X should be unchanged
        assert len(mutilated.equations["X__t0"].parents) == 0  # X was already root

    def test_mutilate_sets_constant(self):
        """Mutilated variable must return its forced constant regardless of noise."""
        scm = make_chain_scm()
        mutilated = scm.mutilate({"Y__t1": 99.0})
        eq = mutilated.equations["Y__t1"]
        result = eq.equation({}, 0.0)
        assert result == pytest.approx(99.0), "mutilated equation must return forced value"

    def test_mutilate_downstream_affected(self):
        """Mutilating X in chain SCM shifts the mean of Z via Y."""
        scm = make_chain_scm()
        # Z ~ 0.7 * Y; Y fixed at 10 → Z mean ≈ 0.7*10 = 7.0
        mutilated = scm.mutilate({"Y__t1": 10.0})
        mean_z = _sample_interventional_mean(mutilated, {}, "Z__t2", n=5000, seed=1)
        assert abs(mean_z - 7.0) < 0.15, (
            f"downstream Z should have mean ≈7.0 after Y:=10, got {mean_z:.3f}"
        )

    def test_mutilate_original_unmodified(self):
        """mutilate() returns a new SCM; original must be unchanged."""
        scm = make_chain_scm()
        original_parents = list(scm.equations["Y__t1"].parents)
        _ = scm.mutilate({"Y__t1": 5.0})
        assert scm.equations["Y__t1"].parents == original_parents, (
            "mutilate() must not modify the original SCM"
        )

    def test_mutilate_non_target_equations_intact(self):
        """Non-intervened equations must be preserved exactly."""
        scm = make_chain_scm()
        mutilated = scm.mutilate({"Y__t1": 0.0})
        # Z's parents should still be [Y]
        z_parents = [p.key for p in mutilated.equations["Z__t2"].parents]
        assert z_parents == ["Y__t1"], (
            f"Z's parents should be ['Y__t1'], got {z_parents}"
        )

    def test_mutilate_fork_independence(self):
        """
        In the fork SCM, after do(X:=0), both Y and Z should have mean ≈ 0.
        do(Y:=y) should NOT affect Z.
        """
        scm = make_fork_scm()
        # do(X:=0): Y mean ≈ 0, Z mean ≈ 0
        df_x0 = scm.sample_interventional({"X__t0": 0.0}, n=5000, seed=2)
        assert abs(df_x0["Y__t1"].mean()) < 0.15, "fork: do(X:=0) should zero Y mean"
        assert abs(df_x0["Z__t1"].mean()) < 0.15, "fork: do(X:=0) should zero Z mean"

        # do(Y:=5): Z should be unaffected (no Y→Z edge)
        df_y5 = scm.sample_interventional({"Y__t1": 5.0}, n=5000, seed=3)
        # Z mean in observational ≈ 0; in do(Y:=5) should remain ≈ 0
        z_obs = _sample_mean(scm, "Z__t1", n=5000, seed=3)
        z_int = float(df_y5["Z__t1"].mean())
        assert abs(z_int - z_obs) < 0.3, (
            f"fork: do(Y:=5) should not shift Z mean; obs={z_obs:.3f}, int={z_int:.3f}"
        )


# ---------------------------------------------------------------------------
# 3. Sampling tests
# ---------------------------------------------------------------------------

class TestSampling:

    def test_observational_sample_shape(self):
        """sample() returns a DataFrame with correct shape."""
        scm = make_chain_scm()
        df = scm.sample(200, seed=0)
        assert df.shape[0] == 200, "wrong number of rows"
        assert "X__t0" in df.columns
        assert "Y__t1" in df.columns
        assert "Z__t2" in df.columns

    def test_observational_means_near_zero(self):
        """All chain SCM variables have mean ≈ 0 (zero-mean noise)."""
        scm = make_chain_scm()
        df = scm.sample(10000, seed=0)
        for col in ["X__t0", "Y__t1", "Z__t2"]:
            assert abs(df[col].mean()) < 0.1, (
                f"chain: {col} mean should be ≈0, got {df[col].mean():.4f}"
            )

    def test_observational_reproducible(self):
        """Same seed produces identical samples."""
        scm = make_chain_scm()
        df1 = scm.sample(100, seed=42)
        df2 = scm.sample(100, seed=42)
        pd.testing.assert_frame_equal(df1, df2)

    def test_interventional_sample_shape(self):
        """sample_interventional() returns correct shape."""
        scm = make_chain_scm()
        df = scm.sample_interventional({"X__t0": 1.0}, n=150, seed=0)
        assert df.shape[0] == 150

    def test_interventional_fixes_variable(self):
        """After do(X:=3), X column must be constant = 3."""
        scm = make_chain_scm()
        df = scm.sample_interventional({"X__t0": 3.0}, n=500, seed=0)
        assert np.allclose(df["X__t0"].values, 3.0), (
            "do(X:=3): X column should be constant 3.0"
        )

    def test_chain_causal_effect_direction(self):
        """do(X:=2) should give Y mean ≈ 1.6 (= 0.8×2)."""
        scm = make_chain_scm()
        df = scm.sample_interventional({"X__t0": 2.0}, n=8000, seed=0)
        y_mean = df["Y__t1"].mean()
        assert abs(y_mean - 1.6) < 0.12, (
            f"chain: do(X:=2) → E[Y] ≈ 1.6, got {y_mean:.3f}"
        )

    def test_no_nan_in_samples(self):
        """No NaN or Inf values in samples from any SCM."""
        factories = [
            make_chain_scm,
            make_fork_scm,
            make_collider_scm,
            make_mediated_scm,
            make_confounder_scm,
            make_feedback_scm,
            make_queueing_scm,
        ]
        for factory in factories:
            scm = factory()
            df = scm.sample(200, seed=7)
            assert not df.isnull().any().any(), (
                f"{factory.__name__}: NaN values in samples"
            )
            assert not np.isinf(df.values).any(), (
                f"{factory.__name__}: Inf values in samples"
            )


# ---------------------------------------------------------------------------
# 4. Acyclicity tests
# ---------------------------------------------------------------------------

class TestAcyclicity:

    def test_all_synthetic_scms_are_acyclic(self):
        """All seven synthetic SCMs must pass the acyclicity check."""
        factories = [
            make_chain_scm,
            make_fork_scm,
            make_collider_scm,
            make_mediated_scm,
            make_confounder_scm,
            make_feedback_scm,
            make_queueing_scm,
        ]
        for factory in factories:
            scm = factory()
            assert scm.is_acyclic(), (
                f"{factory.__name__}: is_acyclic() returned False"
            )

    def test_cycle_detection_raises_on_bad_scm(self):
        """
        Manually construct a cyclic SCM (A→B, B→A within same time slice)
        and verify is_acyclic() returns False and sample() raises ValueError.
        """
        A = TimeSlicedVariable(
            name="A", time_index=0, is_observable=True,
            service_id=None, description="A at t=0"
        )
        B = TimeSlicedVariable(
            name="B", time_index=0, is_observable=True,
            service_id=None, description="B at t=0"
        )

        # Build cyclic equations: A depends on B, B depends on A (same time slice)
        eq_a = StructuralEquation(
            variable=A, parents=[B],
            equation=lambda pv, noise: pv[B.key] + noise,
            equation_type="linear",
            assumption_notes="Cyclic dependency for test only — invalid SCM."
        )
        eq_b = StructuralEquation(
            variable=B, parents=[A],
            equation=lambda pv, noise: pv[A.key] + noise,
            equation_type="linear",
            assumption_notes="Cyclic dependency for test only — invalid SCM."
        )

        cyclic_scm = SCM(
            endogenous={A.key: A, B.key: B},
            exogenous={},
            equations={A.key: eq_a, B.key: eq_b},
        )
        assert not cyclic_scm.is_acyclic(), (
            "is_acyclic() should return False for a cyclic SCM"
        )
        with pytest.raises(ValueError, match="cycle"):
            cyclic_scm.sample(10)

    def test_mutilated_scm_is_still_acyclic(self):
        """Mutilating a DAG cannot introduce a cycle."""
        scm = make_chain_scm()
        mutilated = scm.mutilate({"Y__t1": 1.0})
        assert mutilated.is_acyclic()


# ---------------------------------------------------------------------------
# 5. Confounder: P(Y|X=x) ≠ P(Y|do(X:=x))
# ---------------------------------------------------------------------------

class TestConfounderCorrelationNotCausation:

    def test_observational_y_correlates_with_x(self):
        """P(Y | X is large) should have a higher mean than P(Y | X is small)."""
        scm = make_confounder_scm()
        df = scm.sample(20000, seed=0)

        high_x = df[df["X__t0"] > 1.0]["Y__t0"].mean()
        low_x  = df[df["X__t0"] < -1.0]["Y__t0"].mean()
        assert high_x > low_x + 0.5, (
            f"confounder: observational Y should be higher when X is high; "
            f"high_x_mean={high_x:.3f}, low_x_mean={low_x:.3f}"
        )

    def test_interventional_y_unaffected_by_x(self):
        """
        P(Y | do(X:=2)) ≈ P(Y | do(X:=-2)).
        Intervening on X should NOT shift Y because X is not a cause of Y.
        """
        scm = make_confounder_scm()
        df_hi = scm.sample_interventional({"X__t0": 2.0}, n=10000, seed=0)
        df_lo = scm.sample_interventional({"X__t0": -2.0}, n=10000, seed=1)

        y_hi = df_hi["Y__t0"].mean()
        y_lo = df_lo["Y__t0"].mean()

        assert abs(y_hi - y_lo) < 0.2, (
            f"confounder: do(X:=2) vs do(X:=-2) should not shift Y; "
            f"E[Y|do(X:=2)]={y_hi:.3f}, E[Y|do(X:=-2)]={y_lo:.3f}"
        )

    def test_correlation_not_equal_causation(self):
        """
        The observational difference E[Y|X>1] - E[Y|X<-1] must be substantial,
        while the interventional difference E[Y|do(X:=2)] - E[Y|do(X:=-2)] must be small.
        This directly demonstrates correlation ≠ causation.
        """
        scm = make_confounder_scm()
        df_obs = scm.sample(20000, seed=0)

        obs_diff = (
            df_obs[df_obs["X__t0"] > 1.0]["Y__t0"].mean()
            - df_obs[df_obs["X__t0"] < -1.0]["Y__t0"].mean()
        )
        df_do_hi = scm.sample_interventional({"X__t0": 2.0}, n=10000, seed=2)
        df_do_lo = scm.sample_interventional({"X__t0": -2.0}, n=10000, seed=3)
        int_diff = df_do_hi["Y__t0"].mean() - df_do_lo["Y__t0"].mean()

        assert obs_diff > 0.8, (
            f"confounder: observational difference should be large (>0.8), got {obs_diff:.3f}"
        )
        assert abs(int_diff) < 0.3, (
            f"confounder: interventional difference should be small (<0.3), got {int_diff:.3f}"
        )


# ---------------------------------------------------------------------------
# 6. Queueing: queue depth increases as ρ → 1
# ---------------------------------------------------------------------------

class TestQueueingDynamics:

    def _queue_depth_at_rho(self, rho: float, n: int = 3000, seed: int = 0) -> float:
        """
        Build a queueing SCM and fix arrival_rate/service_rate to achieve the
        given utilisation ρ = λ/μ, then measure mean queue depth.
        """
        scm = make_queueing_scm()
        # Choose μ = 10; λ = ρ × μ
        mu = 10.0
        lam = rho * mu
        df = scm.sample_interventional(
            {"arrival_rate__t0": lam, "service_rate__t0": mu},
            n=n, seed=seed,
        )
        return float(df["queue_depth__t1"].mean())

    def test_queue_depth_increases_with_rho(self):
        """
        M/M/1: E[queue_depth] = ρ/(1−ρ) is strictly increasing in ρ.
        We verify empirically at ρ = 0.3, 0.6, 0.9.
        """
        q_03 = self._queue_depth_at_rho(0.3, seed=0)
        q_06 = self._queue_depth_at_rho(0.6, seed=1)
        q_09 = self._queue_depth_at_rho(0.9, seed=2)

        assert q_03 < q_06, (
            f"queue depth at ρ=0.3 ({q_03:.3f}) should be < ρ=0.6 ({q_06:.3f})"
        )
        assert q_06 < q_09, (
            f"queue depth at ρ=0.6 ({q_06:.3f}) should be < ρ=0.9 ({q_09:.3f})"
        )

    def test_queue_depth_mm1_formula(self):
        """
        At ρ=0.5 (λ=5, μ=10): E[queue_depth] = 0.5/0.5 = 1.0.
        Sampled mean should be within ±0.3 of 1.0.
        """
        q = self._queue_depth_at_rho(0.5, n=8000, seed=0)
        assert abs(q - 1.0) < 0.3, (
            f"M/M/1 ρ=0.5: E[queue_depth] ≈ 1.0, got {q:.3f}"
        )

    def test_queue_depth_high_rho(self):
        """
        At ρ=0.9: E[queue_depth] = 0.9/0.1 = 9.0.
        Sampled mean should be within ±1.5 of 9.0.
        """
        q = self._queue_depth_at_rho(0.9, n=8000, seed=0)
        assert abs(q - 9.0) < 1.5, (
            f"M/M/1 ρ=0.9: E[queue_depth] ≈ 9.0, got {q:.3f}"
        )

    def test_latency_increases_with_rho(self):
        """
        M/M/1: E[latency] = 1/(μ−λ) is strictly increasing in ρ.
        Verify at ρ = 0.3 vs ρ = 0.8.
        """
        scm = make_queueing_scm()
        mu = 10.0
        df_03 = scm.sample_interventional(
            {"arrival_rate__t0": 3.0, "service_rate__t0": mu}, n=5000, seed=0
        )
        df_08 = scm.sample_interventional(
            {"arrival_rate__t0": 8.0, "service_rate__t0": mu}, n=5000, seed=1
        )
        lat_03 = df_03["latency__t1"].mean()
        lat_08 = df_08["latency__t1"].mean()
        assert lat_03 < lat_08, (
            f"latency at ρ=0.3 ({lat_03:.4f}) should be < ρ=0.8 ({lat_08:.4f})"
        )

    def test_queueing_scm_acyclic(self):
        """Queueing SCM must pass acyclicity check."""
        scm = make_queueing_scm()
        assert scm.is_acyclic()


# ---------------------------------------------------------------------------
# 7. Feedback SCM does NOT create a cycle
# ---------------------------------------------------------------------------

class TestFeedbackNoCycle:

    def test_feedback_scm_is_acyclic(self):
        """
        X[t0] → Y[t1] → X[t2] is a temporal DAG.
        X__t0 and X__t2 are distinct nodes; no cycle exists.
        """
        scm = make_feedback_scm()
        assert scm.is_acyclic(), (
            "feedback SCM should be acyclic (loop crosses time boundaries)"
        )

    def test_feedback_distinct_time_slices(self):
        """X[t0] and X[t2] are distinct variables with different keys."""
        scm = make_feedback_scm()
        assert "X__t0" in scm.endogenous
        assert "X__t2" in scm.endogenous
        assert "X__t0" != "X__t2"

    def test_feedback_no_self_edge(self):
        """No self-loop should exist (e.g., X__t0 → X__t0)."""
        scm = make_feedback_scm()
        for parent_key, child_key in scm.edges():
            assert parent_key != child_key, (
                f"self-loop detected: {parent_key} → {child_key}"
            )

    def test_feedback_sampling_works(self):
        """Sampling from feedback SCM should succeed without error."""
        scm = make_feedback_scm()
        df = scm.sample(500, seed=0)
        assert df.shape == (500, 3)
        assert "X__t0" in df.columns
        assert "Y__t1" in df.columns
        assert "X__t2" in df.columns

    def test_feedback_x2_depends_on_x0(self):
        """
        X[t2] is causally downstream of X[t0] via Y[t1].
        do(X[t0]:=10) should shift X[t2] upward from its default mean≈0.
        """
        scm = make_feedback_scm()
        df = scm.sample_interventional({"X__t0": 10.0}, n=5000, seed=0)
        x2_mean = df["X__t2"].mean()
        # E[X2|do(X0:=10)] = 0.6 * 0.85 * 10 = 5.1
        assert x2_mean > 3.0, (
            f"feedback: do(X0:=10) should shift X2 mean to ≈5.1, got {x2_mean:.3f}"
        )


# ---------------------------------------------------------------------------
# Additional: TimeSlicedVariable invariants
# ---------------------------------------------------------------------------

class TestTimeSlicedVariable:

    def test_key_format(self):
        v = TimeSlicedVariable(
            name="cpu_pct", time_index=3,
            is_observable=True, service_id="svc_b", description="test"
        )
        assert v.key == "cpu_pct__t3"

    def test_frozen(self):
        """TimeSlicedVariable must be immutable (frozen dataclass)."""
        v = TimeSlicedVariable(
            name="x", time_index=0,
            is_observable=True, service_id=None, description=""
        )
        with pytest.raises((AttributeError, TypeError)):
            v.name = "y"  # type: ignore[misc]

    def test_distinct_time_slices_are_not_equal(self):
        v0 = TimeSlicedVariable(
            name="X", time_index=0,
            is_observable=True, service_id=None, description=""
        )
        v1 = TimeSlicedVariable(
            name="X", time_index=1,
            is_observable=True, service_id=None, description=""
        )
        assert v0 != v1
        assert v0.key != v1.key
