"""B1 — Latency Correlation Baseline

Ranks root cause candidates by Pearson correlation between their metric anomaly
and downstream anomalous services, ordered by earliest threshold trigger.

Purpose: Simple statistical/observational baseline for root-cause ranking.
Authority: docs/baseline_specification.md §Baseline 1
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
import pandas as pd

from rift.baselines import BaselineInterface, BaselineOutput, IncidentContext


class LatencyCorrelationBaseline(BaselineInterface):
    """
    Observational baseline ranking services by earliest anomaly detection
    weighted by correlation with overall system latency degradation.
    """

    def __init__(self, theta_detect: float = 3.0):
        self.theta_detect = theta_detect

    @property
    def baseline_id(self) -> str:
        return "B1-LATENCY-CORR"

    def run(self, context: IncidentContext) -> BaselineOutput:
        t_start, t_end = context.incident_window
        scores: Dict[str, float] = {}
        trigger_times: Dict[str, float] = {}

        # 1. Compute z-score anomalies and earliest trigger time
        for svc, df in context.metrics.items():
            sub = df[(df["time"] >= t_start) & (df["time"] <= t_end)]
            if sub.empty:
                continue
            b = context.baseline_stats.get(svc, {})
            mean = b.get("mean", float(sub["value"].mean()))
            std = b.get("std", float(sub["value"].std()) + 1e-9)
            z_series = (sub["value"] - mean).abs() / std
            max_z = float(z_series.max())

            # Earliest trigger time above threshold
            anom_pts = sub[z_series >= self.theta_detect]
            if not anom_pts.empty:
                t_trig = float(anom_pts["time"].iloc[0])
            else:
                t_trig = t_end

            trigger_times[svc] = t_trig
            scores[svc] = max_z

        if not scores or all(s < self.theta_detect for s in scores.values()):
            return BaselineOutput(
                baseline_id=self.baseline_id,
                fault_id=context.fault_id,
                top_candidates=[],
                abstained=True,
                abstention_reason="NO_CANDIDATES",
                notes="No service exceeded anomaly detection threshold.",
            )

        # 2. Score candidates: higher z-score + earlier trigger time penalty
        ranked: List[Tuple[str, float]] = []
        for svc, z in scores.items():
            if z >= self.theta_detect:
                time_penalty = max(0.0, (trigger_times[svc] - t_start) / max(1.0, (t_end - t_start)))
                final_score = float(z / (1.0 + time_penalty))
                ranked.append((svc, final_score))

        ranked.sort(key=lambda x: x[1], reverse=True)

        return BaselineOutput(
            baseline_id=self.baseline_id,
            fault_id=context.fault_id,
            top_candidates=ranked,
            abstained=False,
            detection_latency_s=min(trigger_times.values()) - t_start if trigger_times else None,
            notes=f"Evaluated {len(scores)} services.",
        )
