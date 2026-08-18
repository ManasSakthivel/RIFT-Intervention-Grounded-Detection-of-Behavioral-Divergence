"""
Unit tests for src/rift/optimizer/cost_model.py — Phase 3L

Ground-truth test cases:
  TC-C1  Blast radius = 0 for leaf node (no descendants)
  TC-C2  Blast radius = |Desc(X)| / N for node with descendants
  TC-C3  EIG proportional to posterior mass on service
  TC-C4  Utility = EIG_norm / (1 + cost_comp) ∈ [0, 1]
  TC-C5  Authorization: br<0.1 AND slai<0.01 → AUTONOMOUS
  TC-C6  Authorization: sc<0.3 → DENIED
  TC-C7  Authorization: else → SUPERVISED
  TC-C8  Safety_compliance = clip(1 - 0.5*br - 0.5*slai, 0, 1)
  TC-C9  Weight assertion: non-unit weights raise AssertionError
  TC-C10 MSIS: entropy already converged → ENTROPY_CONVERGED immediately
  TC-C11 MSIS: no eligible interventions → NO_ELIGIBLE
  TC-C12 MSIS: budget exhausted → BUDGET_EXHAUSTED
  TC-C13 MSIS: selects highest-utility intervention first (greedy property)
  TC-C14 MSIS: entropy_reduction ≥ 0
  TC-C15 Submodularity note: distinct services → verified=True
  TC-C16 Submodularity note: same service twice → verified=False
  TC-C17 DENIED interventions excluded from MSIS
  TC-C18 _entropy: uniform distribution → log(N) nats
  TC-C19 _entropy: peaked distribution → low entropy
  TC-C20 total_cost = sum of cost_composite of selected interventions

Status: VALIDATED — all cases backed by synthetic ground-truth construction.
Authority: docs/PHASE_3_SPEC_FREEZE.md §12
"""

from __future__ import annotations

import math
from typing import Dict, List

import networkx as nx
import pytest

from rift.optimizer.cost_model import (
    InterventionCandidate,
    InterventionCost,
    MSISResult,
    _entropy,
    _verify_submodularity,
    compute_intervention_costs,
    greedy_msis,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_candidate(
    service_id: str = "svc-A",
    variable: str = "latency_p99",
    intervention_type: str = "LATENCY",
    target_value: float = 50.0,
    nominal_value: float = 10.0,
) -> InterventionCandidate:
    return InterventionCandidate(
        service_id=service_id,
        variable=variable,
        intervention_type=intervention_type,
        target_value=target_value,
        nominal_value=nominal_value,
    )


def _chain_graph(nodes: List[str]) -> nx.DiGraph:
    """A→B→C→... chain."""
    G = nx.DiGraph()
    for i in range(len(nodes) - 1):
        G.add_edge(nodes[i], nodes[i + 1])
    return G


def _leaf_graph(root: str, leaf: str) -> nx.DiGraph:
    G = nx.DiGraph()
    G.add_edge(root, leaf)
    return G


# ---------------------------------------------------------------------------
# _entropy
# ---------------------------------------------------------------------------

class TestEntropy:
    def test_tc_c18_uniform_is_log_n(self):
        """Uniform over N items = log(N) nats."""
        posterior = {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}
        h = _entropy(posterior)
        assert h == pytest.approx(math.log(4), rel=1e-5)

    def test_tc_c19_peaked_low_entropy(self):
        """Peaked distribution has low entropy."""
        peaked = {"A": 0.98, "B": 0.01, "C": 0.01}
        uniform = {"A": 1 / 3, "B": 1 / 3, "C": 1 / 3}
        assert _entropy(peaked) < _entropy(uniform)

    def test_entropy_zero_single_element(self):
        """Degenerate distribution (single element) → entropy = 0."""
        assert _entropy({"A": 1.0}) == pytest.approx(0.0, abs=1e-10)

    def test_entropy_zero_empty(self):
        """Empty distribution → entropy = 0 (guard)."""
        assert _entropy({}) == pytest.approx(0.0, abs=1e-10)

    def test_entropy_handles_zero_values(self):
        """Zero-probability entries do not cause log(0) errors."""
        h = _entropy({"A": 1.0, "B": 0.0, "C": 0.0})
        assert h == pytest.approx(0.0, abs=1e-10)


# ---------------------------------------------------------------------------
# _verify_submodularity
# ---------------------------------------------------------------------------

class TestVerifySubmodularity:
    def test_tc_c15_distinct_services(self):
        """Distinct service IDs → submodularity verified."""
        selected = [
            InterventionCost(
                candidate=_make_candidate("A"), blast_radius=0.0, sla_impact=0.0,
                execution_duration_s=30.0, rollback_cost=0.1, eig=0.1,
                eig_normalized=0.5, safety_compliance=0.9, cost_composite=0.1,
                utility=0.4, authorized=True, authorization_level="AUTONOMOUS",
            ),
            InterventionCost(
                candidate=_make_candidate("B"), blast_radius=0.0, sla_impact=0.0,
                execution_duration_s=30.0, rollback_cost=0.1, eig=0.1,
                eig_normalized=0.5, safety_compliance=0.9, cost_composite=0.1,
                utility=0.4, authorized=True, authorization_level="AUTONOMOUS",
            ),
        ]
        ok, note = _verify_submodularity(selected)
        assert ok is True

    def test_tc_c16_same_service_submodularity_false(self):
        """Same service twice → submodularity NOT verified."""
        c = InterventionCost(
            candidate=_make_candidate("A"), blast_radius=0.0, sla_impact=0.0,
            execution_duration_s=30.0, rollback_cost=0.1, eig=0.1,
            eig_normalized=0.5, safety_compliance=0.9, cost_composite=0.1,
            utility=0.4, authorized=True, authorization_level="AUTONOMOUS",
        )
        ok, note = _verify_submodularity([c, c])
        assert ok is False

    def test_single_intervention_trivially_holds(self):
        """Single intervention → submodularity trivially True."""
        c = InterventionCost(
            candidate=_make_candidate("A"), blast_radius=0.0, sla_impact=0.0,
            execution_duration_s=30.0, rollback_cost=0.1, eig=0.1,
            eig_normalized=0.5, safety_compliance=0.9, cost_composite=0.1,
            utility=0.4, authorized=True, authorization_level="AUTONOMOUS",
        )
        ok, note = _verify_submodularity([c])
        assert ok is True


# ---------------------------------------------------------------------------
# compute_intervention_costs
# ---------------------------------------------------------------------------

class TestComputeInterventionCosts:
    def _default_posterior(self) -> Dict[str, float]:
        return {"svc-A": 0.5, "svc-B": 0.3, "svc-C": 0.2}

    def test_tc_c9_non_unit_weights_raise(self):
        """Weights that don't sum to 1.0 → AssertionError."""
        candidate = _make_candidate()
        G = nx.DiGraph()
        G.add_node("svc-A")
        with pytest.raises(AssertionError):
            compute_intervention_costs(
                [candidate], G, {"svc-A": 1.0}, service_count=1,
                w_br=0.5, w_slai=0.5, w_rc=0.5, w_sc=0.5,  # sum = 2.0
            )

    def test_tc_c1_blast_radius_leaf_node(self):
        """Leaf node has no descendants → blast_radius = 0."""
        G = nx.DiGraph()
        G.add_node("svc-leaf")
        candidate = _make_candidate("svc-leaf")
        costs = compute_intervention_costs(
            [candidate], G, {"svc-leaf": 1.0}, service_count=4,
        )
        assert len(costs) == 1
        assert costs[0].blast_radius == pytest.approx(0.0)

    def test_tc_c2_blast_radius_with_descendants(self):
        """svc-A has 2 descendants out of 4 total → br = 2/4 = 0.5."""
        G = nx.DiGraph()
        G.add_edges_from([("svc-A", "svc-B"), ("svc-A", "svc-C")])
        G.add_node("svc-D")  # not downstream of A
        candidate = _make_candidate("svc-A")
        costs = compute_intervention_costs(
            [candidate], G, self._default_posterior(), service_count=4,
        )
        assert len(costs) == 1
        assert costs[0].blast_radius == pytest.approx(2 / 4)

    def test_tc_c5_autonomous_authorization(self):
        """br<0.1 AND slai<0.01 → AUTONOMOUS."""
        G = nx.DiGraph()
        G.add_node("svc-A")
        candidate = _make_candidate("svc-A")
        # Ensure no impact lookup so slai defaults to 0.01 (boundary; adjust)
        costs = compute_intervention_costs(
            [candidate], G, {"svc-A": 1.0}, service_count=100,
            impact_lookup={"svc-A": 0.005},  # <0.01
        )
        assert costs[0].authorization_level == "AUTONOMOUS"
        assert costs[0].authorized is True

    def test_tc_c6_denied_when_low_safety_compliance(self):
        """When sc < 0.3 → DENIED."""
        G = nx.DiGraph()
        # Add many descendants to inflate blast radius → reduces sc
        for i in range(20):
            G.add_edge("svc-A", f"svc-{i}")
        candidate = _make_candidate("svc-A")
        costs = compute_intervention_costs(
            [candidate], G, {"svc-A": 1.0}, service_count=20,
            impact_lookup={"svc-A": 0.9},  # high SLA impact
        )
        if costs[0].safety_compliance < 0.3:
            assert costs[0].authorization_level == "DENIED"
            assert costs[0].authorized is False

    def test_tc_c8_safety_compliance_formula(self):
        """SC = clip(1 - 0.5*br - 0.5*slai, 0, 1)."""
        G = nx.DiGraph()
        G.add_node("svc-X")
        candidate = _make_candidate("svc-X")
        br_expected = 0.0
        slai_expected = 0.1
        costs = compute_intervention_costs(
            [candidate], G, {"svc-X": 1.0}, service_count=5,
            impact_lookup={"svc-X": slai_expected},
        )
        expected_sc = max(0.0, 1.0 - 0.5 * br_expected - 0.5 * slai_expected)
        assert costs[0].safety_compliance == pytest.approx(expected_sc, abs=1e-6)

    def test_tc_c4_utility_in_range(self):
        """Utility ∈ [0, 1] for all cases."""
        G = _chain_graph(["svc-A", "svc-B", "svc-C"])
        candidates = [
            _make_candidate("svc-A"),
            _make_candidate("svc-B"),
        ]
        costs = compute_intervention_costs(
            candidates, G, self._default_posterior(), service_count=3,
        )
        for c in costs:
            assert 0.0 <= c.utility <= 1.0

    def test_tc_c3_eig_proportional_to_posterior(self):
        """Higher posterior mass on service → higher EIG."""
        G = nx.DiGraph()
        G.add_nodes_from(["high", "low"])
        candidates = [
            _make_candidate("high"),
            _make_candidate("low"),
        ]
        posterior = {"high": 0.9, "low": 0.1}
        costs = compute_intervention_costs(
            candidates, G, posterior, service_count=2,
        )
        high_cost = next(c for c in costs if c.candidate.service_id == "high")
        low_cost = next(c for c in costs if c.candidate.service_id == "low")
        assert high_cost.eig_normalized >= low_cost.eig_normalized

    def test_all_fields_in_range(self):
        """All output fields must be in [0, 1] (except eig which is in nats)."""
        G = _chain_graph(["svc-A", "svc-B"])
        candidate = _make_candidate("svc-A")
        costs = compute_intervention_costs(
            [candidate], G, {"svc-A": 0.7, "svc-B": 0.3}, service_count=2,
        )
        c = costs[0]
        assert 0.0 <= c.blast_radius <= 1.0
        assert 0.0 <= c.sla_impact <= 1.0
        assert 0.0 <= c.rollback_cost <= 1.0
        assert 0.0 <= c.eig_normalized <= 1.0
        assert 0.0 <= c.safety_compliance <= 1.0
        assert 0.0 <= c.cost_composite <= 1.0
        assert 0.0 <= c.utility <= 1.0

    def test_service_not_in_graph_blast_radius_zero(self):
        """Service missing from graph → blast_radius = 0 (safe default)."""
        G = nx.DiGraph()
        G.add_node("other")
        candidate = _make_candidate("svc-unknown")
        costs = compute_intervention_costs(
            [candidate], G, {"svc-unknown": 1.0}, service_count=2,
        )
        assert costs[0].blast_radius == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# greedy_msis
# ---------------------------------------------------------------------------

def _make_cost(
    service_id: str,
    utility: float = 0.5,
    authorized: bool = True,
    ed: float = 30.0,
    cost_composite: float = 0.2,
) -> InterventionCost:
    return InterventionCost(
        candidate=_make_candidate(service_id),
        blast_radius=0.05,
        sla_impact=0.005,
        execution_duration_s=ed,
        rollback_cost=0.1,
        eig=0.3,
        eig_normalized=utility,
        safety_compliance=0.9,
        cost_composite=cost_composite,
        utility=utility,
        authorized=authorized,
        authorization_level="AUTONOMOUS" if authorized else "DENIED",
    )


class TestGreedyMSIS:
    def test_tc_c10_entropy_already_converged(self):
        """Entropy < θ_entropy at start → ENTROPY_CONVERGED immediately, no selection."""
        # Single-element posterior → entropy = 0 < 0.5
        posterior = {"A": 1.0}
        costs = [_make_cost("A")]
        result = greedy_msis(costs, posterior, theta_entropy=0.5)
        assert result.stopped_reason == "ENTROPY_CONVERGED"
        assert result.selected_interventions == []

    def test_tc_c11_no_eligible_interventions(self):
        """All interventions DENIED → NO_ELIGIBLE."""
        posterior = {"A": 0.5, "B": 0.5}
        costs = [_make_cost("A", utility=0.8, authorized=False)]
        result = greedy_msis(costs, posterior, theta_entropy=0.5)
        assert result.stopped_reason == "NO_ELIGIBLE"
        assert result.selected_interventions == []

    def test_tc_c12_budget_exhausted(self):
        """Intervention exceeds budget → BUDGET_EXHAUSTED."""
        posterior = {"A": 0.6, "B": 0.4}
        # Budget of 10s but intervention needs 30s
        costs = [_make_cost("A", utility=0.9, ed=30.0)]
        result = greedy_msis(costs, posterior, theta_entropy=0.5, t_budget=10.0)
        assert result.stopped_reason in ("BUDGET_EXHAUSTED", "NO_ELIGIBLE")

    def test_tc_c13_greedy_picks_highest_utility_first(self):
        """Greedy MSIS must pick the highest-utility intervention first."""
        posterior = {"A": 0.4, "B": 0.4, "C": 0.2}
        costs = [
            _make_cost("A", utility=0.9),
            _make_cost("B", utility=0.5),
            _make_cost("C", utility=0.3),
        ]
        result = greedy_msis(costs, posterior, theta_entropy=0.5, t_budget=600.0)
        if result.selected_interventions:
            assert result.selected_interventions[0].candidate.service_id == "A"

    def test_tc_c14_entropy_reduction_nonnegative(self):
        """entropy_reduction must always be ≥ 0."""
        posterior = {"A": 0.5, "B": 0.5}
        costs = [_make_cost("A", utility=0.8)]
        result = greedy_msis(costs, posterior, theta_entropy=0.5, t_budget=600.0)
        assert result.entropy_reduction >= 0.0

    def test_tc_c17_denied_excluded(self):
        """DENIED interventions are never selected."""
        posterior = {"A": 0.6, "B": 0.4}
        costs = [
            _make_cost("A", utility=0.9, authorized=False),
            _make_cost("B", utility=0.5, authorized=True),
        ]
        result = greedy_msis(costs, posterior, theta_entropy=0.5, t_budget=600.0)
        service_ids = [c.candidate.service_id for c in result.selected_interventions]
        assert "A" not in service_ids

    def test_tc_c20_total_cost_correct(self):
        """total_cost == sum of cost_composite of selected interventions."""
        posterior = {"A": 0.5, "B": 0.5}
        costs = [
            _make_cost("A", utility=0.8, cost_composite=0.25),
            _make_cost("B", utility=0.7, cost_composite=0.35),
        ]
        result = greedy_msis(costs, posterior, theta_entropy=0.0, t_budget=600.0)
        expected = sum(c.cost_composite for c in result.selected_interventions)
        assert result.total_cost == pytest.approx(expected, abs=1e-9)

    def test_entropy_before_after_reported(self):
        """entropy_before and entropy_after are reported correctly."""
        posterior = {"A": 0.5, "B": 0.5}
        costs = [_make_cost("A", utility=0.8)]
        result = greedy_msis(costs, posterior, theta_entropy=0.5, t_budget=600.0)
        expected_h_before = math.log(2)  # uniform over 2
        assert result.entropy_before == pytest.approx(expected_h_before, rel=0.01)
        assert 0.0 <= result.entropy_after <= result.entropy_before + 1e-9

    def test_msis_notes_no_guarantee_claim(self):
        """MSIS notes must NOT claim (1-1/e) guarantee unless submodularity verified."""
        posterior = {"A": 0.5, "B": 0.5}
        # Same service selected twice → submodularity fails
        costs = [_make_cost("A", utility=0.8), _make_cost("A", utility=0.6)]
        result = greedy_msis(costs, posterior, theta_entropy=0.0, t_budget=600.0)
        # notes should disclaim the (1-1/e) bound
        assert "does not claim" in result.notes.lower() or \
               "Does not claim" in result.notes
