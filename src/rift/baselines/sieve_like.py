"""Sieve-like Methodological Baseline — Phase 3.6 §10.

IMPORTANT: This is labeled SIEVE-LIKE, not SIEVE.
This is a methodological reimplementation based on published literature.
The exact Sieve published code is NOT reproduced here.

Authority: docs/baselines/SIEVE_LIKE.md, docs/baseline_specification.md
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
import pandas as pd

from rift.baselines import BaselineInterface, BaselineOutput, IncidentContext


class SieveLikeBaseline(BaselineInterface):
    """
    Sieve-like observational RCA baseline.

    Pipeline:
    1. Compute per-service anomaly z-scores
    2. Traverse call graph upstream from anomalous services
    3. Compute propagation-weighted score for each upstream service
    4. Rank by propagation score
    5. Return top-k candidates

    Label: SIEVE-LIKE (NOT SIEVE — this is a methodological reimplementation)
    Authority: docs/baselines/SIEVE_LIKE.md
    """

    def __init__(
        self,
        theta_detect: float = 3.0,
        propagation_decay: float = 0.5,
        max_depth: int = 5,
    ):
        self.theta_detect = theta_detect
        self.propagation_decay = propagation_decay
        self.max_depth = max_depth

    @property
    def baseline_id(self) -> str:
        return "B3-SIEVE-LIKE"

    def _compute_anomaly_scores(
        self,
        metrics: Dict[str, pd.DataFrame],
        baseline_stats: Dict[str, Dict[str, float]],
        incident_window: Tuple[float, float],
    ) -> Dict[str, float]:
        """Compute per-service max z-score within incident window."""
        scores: Dict[str, float] = {}
        t_start, t_end = incident_window
        for svc, df in metrics.items():
            sub = df[(df["time"] >= t_start) & (df["time"] <= t_end)]
            if sub.empty:
                scores[svc] = 0.0
                continue
            b = baseline_stats.get(svc, {})
            mean = b.get("mean", float(sub["value"].mean()))
            std = b.get("std", float(sub["value"].std()) + 1e-9)
            z = float((sub["value"] - mean).abs().max() / std)
            scores[svc] = z
        return scores

    def _propagation_score(
        self,
        service: str,
        anomaly_scores: Dict[str, float],
        call_graph: nx.DiGraph,
        depth: int = 0,
        visited: Optional[set] = None,
    ) -> float:
        """
        Propagation-weighted score for 'service'.

        Score = anomaly_score[service]
              + sum over successors of (decay^depth * propagation_score(successor))

        This propagates anomaly evidence from downstream services back to
        upstream candidates (root cause is typically upstream).
        """
        if visited is None:
            visited = set()
        if service in visited or depth > self.max_depth:
            return anomaly_scores.get(service, 0.0)
        visited.add(service)

        base_score = anomaly_scores.get(service, 0.0)
        downstream_score = 0.0

        if call_graph.has_node(service):
            for successor in call_graph.successors(service):
                if successor not in visited:
                    child_score = self._propagation_score(
                        successor, anomaly_scores, call_graph,
                        depth + 1, visited
                    )
                    downstream_score += (self.propagation_decay ** (depth + 1)) * child_score

        return base_score + downstream_score

    def run(self, context: IncidentContext) -> BaselineOutput:
        """Execute Sieve-like pipeline. No interventions. No PAG."""
        import time
        t0 = time.time()

        anomaly_scores = self._compute_anomaly_scores(
            context.metrics, context.baseline_stats, context.incident_window
        )

        # Candidates: services with anomaly score > threshold
        anomalous = {svc: score for svc, score in anomaly_scores.items()
                     if score > self.theta_detect}

        if not anomalous:
            return BaselineOutput(
                baseline_id=self.baseline_id,
                fault_id=context.fault_id,
                top_candidates=[],
                abstained=True,
                notes=(
                    f"SIEVE-LIKE: no services exceeded θ_detect={self.theta_detect}. "
                    "ABSTAIN. "
                    "Label: SIEVE-LIKE (methodological reimplementation)"
                ),
            )

        # Compute propagation scores for all anomalous services
        propagation_scores: Dict[str, float] = {}
        for svc in anomalous:
            propagation_scores[svc] = self._propagation_score(
                svc, anomaly_scores, context.call_graph
            )

        # Rank by propagation score descending
        ranked = sorted(propagation_scores.items(), key=lambda x: x[1], reverse=True)

        detection_latency = None
        t_start = context.incident_window[0]
        for svc, _ in ranked[:1]:
            svc_df = context.metrics.get(svc, pd.DataFrame())
            if not svc_df.empty:
                b = context.baseline_stats.get(svc, {})
                b_mean = b.get("mean", float(svc_df["value"].mean()))
                b_std = b.get("std", float(svc_df["value"].std()) + 1e-9)
                z = (svc_df["value"] - b_mean).abs() / b_std
                threshold_rows = svc_df[z > self.theta_detect]
                if not threshold_rows.empty:
                    t_detect = float(threshold_rows["time"].min())
                    detection_latency = t_detect - t_start

        return BaselineOutput(
            baseline_id=self.baseline_id,
            fault_id=context.fault_id,
            top_candidates=ranked[:5],
            abstained=False,
            detection_latency_s=detection_latency,
            total_intervention_ed_s=0.0,
            notes=(
                "SIEVE-LIKE: propagation-weighted anomaly ranking. "
                "Label: SIEVE-LIKE (NOT SIEVE — methodological reimplementation). "
                "No intervention. No PAG. No identifiability check. "
                "See docs/baselines/SIEVE_LIKE.md for citation obligations."
            ),
        )
