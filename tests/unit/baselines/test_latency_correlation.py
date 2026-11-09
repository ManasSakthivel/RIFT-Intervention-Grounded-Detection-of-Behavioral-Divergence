"""Unit tests for LatencyCorrelationBaseline."""
import networkx as nx
import numpy as np
import pandas as pd
import pytest

from rift.baselines import IncidentContext
from rift.baselines.latency_correlation import LatencyCorrelationBaseline


def test_latency_correlation_baseline_basic():
    baseline = LatencyCorrelationBaseline(theta_detect=3.0)
    assert baseline.baseline_id == "B1-LATENCY-CORR"

    # Create synthetic incident context with 3 services
    # svc_a (root cause): spikes at t=20
    # svc_b (downstream): spikes at t=40
    # svc_c (normal): no spike
    times = [float(t) for t in range(0, 100, 10)]
    metrics = {
        "svc_a": pd.DataFrame({"time": times, "value": [10.0 if t < 20 else 50.0 for t in times]}),
        "svc_b": pd.DataFrame({"time": times, "value": [10.0 if t < 40 else 45.0 for t in times]}),
        "svc_c": pd.DataFrame({"time": times, "value": [10.0 for t in times]}),
    }
    baseline_stats = {
        "svc_a": {"mean": 10.0, "std": 2.0},
        "svc_b": {"mean": 10.0, "std": 2.0},
        "svc_c": {"mean": 10.0, "std": 2.0},
    }
    call_graph = nx.DiGraph([("svc_a", "svc_b"), ("svc_b", "svc_c")])

    ctx = IncidentContext(
        fault_id="TEST-001",
        incident_window=(0.0, 90.0),
        metrics=metrics,
        baseline_stats=baseline_stats,
        call_graph=call_graph,
    )

    out = baseline.run(ctx)
    assert not out.abstained
    assert len(out.top_candidates) >= 2
    # svc_a triggered earlier than svc_b, so it should rank higher
    top_svc, score = out.top_candidates[0]
    assert top_svc == "svc_a"


def test_latency_correlation_baseline_no_anomaly():
    baseline = LatencyCorrelationBaseline(theta_detect=3.0)
    times = [float(t) for t in range(0, 50, 10)]
    metrics = {
        "svc_a": pd.DataFrame({"time": times, "value": [10.0 for t in times]}),
    }
    baseline_stats = {"svc_a": {"mean": 10.0, "std": 2.0}}
    call_graph = nx.DiGraph()

    ctx = IncidentContext(
        fault_id="TEST-002",
        incident_window=(0.0, 40.0),
        metrics=metrics,
        baseline_stats=baseline_stats,
        call_graph=call_graph,
    )

    out = baseline.run(ctx)
    assert out.abstained
    assert out.abstention_reason == "NO_CANDIDATES"
