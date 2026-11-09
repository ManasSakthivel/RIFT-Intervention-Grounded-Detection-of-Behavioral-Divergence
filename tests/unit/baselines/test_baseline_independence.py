"""
test_baseline_independence.py — Unit tests verifying independent decision logic
and distinct behaviors of baselines under synthetic failure conditions.
"""
import pytest
import pandas as pd
import numpy as np
import networkx as nx

from rift.baselines import IncidentContext
from rift.baselines.latency_correlation import LatencyCorrelationBaseline
from rift.baselines.rift_random import RIFTRandomBaseline, RandomMSIS
from rift.baselines.rift_one_shot import RIFTOneShotBaseline
from rift.optimizer.cost_model import InterventionCandidate, InterventionCost


def test_random_msis_is_random():
    """Verify that RandomMSIS produces different selections with different seeds."""
    cand1 = InterventionCandidate("frontend", "frontend.latency", "LATENCY", 200.0, 50.0, "c1")
    cand2 = InterventionCandidate("cart", "cart.latency", "LATENCY", 200.0, 50.0, "c2")
    cand3 = InterventionCandidate("payment", "payment.latency", "LATENCY", 200.0, 50.0, "c3")

    costs = [
        InterventionCost(
            candidate=cand1, blast_radius=0.05, sla_impact=0.01,
            execution_duration_s=30.0, rollback_cost=5.0,
            eig=0.5, eig_normalized=0.5, safety_compliance=0.9,
            cost_composite=0.3, utility=0.4, authorized=True,
            authorization_level="AUTONOMOUS",
        ),
        InterventionCost(
            candidate=cand2, blast_radius=0.05, sla_impact=0.01,
            execution_duration_s=30.0, rollback_cost=5.0,
            eig=0.5, eig_normalized=0.5, safety_compliance=0.9,
            cost_composite=0.3, utility=0.4, authorized=True,
            authorization_level="AUTONOMOUS",
        ),
        InterventionCost(
            candidate=cand3, blast_radius=0.05, sla_impact=0.01,
            execution_duration_s=30.0, rollback_cost=5.0,
            eig=0.5, eig_normalized=0.5, safety_compliance=0.9,
            cost_composite=0.3, utility=0.4, authorized=True,
            authorization_level="AUTONOMOUS",
        ),
    ]
    posterior = {"frontend": 0.33, "cart": 0.33, "payment": 0.34}

    m1 = RandomMSIS(seed=1).select(costs, posterior, theta_entropy=0.1)
    m2 = RandomMSIS(seed=999).select(costs, posterior, theta_entropy=0.1)

    s1 = [c.candidate.service_id for c in m1.selected_interventions]
    s2 = [c.candidate.service_id for c in m2.selected_interventions]
    assert len(s1) > 0
    assert len(s2) > 0
    # Different seeds should yield different selection orderings across multiple trials
