"""RIFT EBD Evaluation Metrics — Phase 3.6 §14.

Reusable evaluators for EBD results:
  - Per-requirement pass rates (R1/R2/R3/R4)
  - CANDIDATE vs DEFINITIVE ratios
  - Boundary-limited rate
  - Multi-cause attribution
  - Mean detection latency

Authority: docs/PHASE_3_SPEC_FREEZE.md §9, Phase 3.6 §14.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class EBDEvalSummary:
    """
    Summary of EBD result quality over a set of scenarios.
    """
    method_id: str
    n_scenarios: int
    n_candidates: int          # total EBD candidates emitted
    n_definitive: int
    n_candidate_conf: int      # CANDIDATE confidence (not DEFINITIVE)
    n_none_confidence: int     # no confidence (NONE)
    n_boundary_limited: int
    r1_pass_rate: float
    r2_pass_rate: float
    r3_pass_rate: float
    r4_pass_rate: float
    mean_detection_latency_s: Optional[float]
    median_detection_latency_s: Optional[float]
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "method_id": self.method_id,
            "n_scenarios": self.n_scenarios,
            "n_candidates": self.n_candidates,
            "n_definitive": self.n_definitive,
            "n_candidate_conf": self.n_candidate_conf,
            "n_none_confidence": self.n_none_confidence,
            "n_boundary_limited": self.n_boundary_limited,
            "r1_pass_rate": self.r1_pass_rate,
            "r2_pass_rate": self.r2_pass_rate,
            "r3_pass_rate": self.r3_pass_rate,
            "r4_pass_rate": self.r4_pass_rate,
            "mean_detection_latency_s": self.mean_detection_latency_s,
            "median_detection_latency_s": self.median_detection_latency_s,
            "notes": self.notes,
        }


def evaluate_ebd_results(
    ebd_results_per_scenario: List[List[Any]],
    method_id: str,
    incident_windows: Optional[List] = None,
) -> EBDEvalSummary:
    """
    Evaluate EBD result quality across multiple scenarios.

    Parameters
    ----------
    ebd_results_per_scenario : list of (list of EBDResult per scenario)
    method_id : evaluating method name
    incident_windows : optional list of (t_start, t_end) per scenario for latency

    Returns
    -------
    EBDEvalSummary
    """
    n_scenarios = len(ebd_results_per_scenario)
    all_results = [r for scenario in ebd_results_per_scenario for r in scenario]
    n_total = len(all_results)

    if n_total == 0:
        return EBDEvalSummary(
            method_id=method_id,
            n_scenarios=n_scenarios,
            n_candidates=0,
            n_definitive=0,
            n_candidate_conf=0,
            n_none_confidence=0,
            n_boundary_limited=0,
            r1_pass_rate=0.0,
            r2_pass_rate=0.0,
            r3_pass_rate=0.0,
            r4_pass_rate=0.0,
            mean_detection_latency_s=None,
            median_detection_latency_s=None,
            notes="No EBD results to evaluate.",
        )

    n_def = sum(1 for r in all_results if getattr(r, "confidence", "") == "DEFINITIVE")
    n_cand = sum(1 for r in all_results if getattr(r, "confidence", "") == "CANDIDATE")
    n_none = sum(1 for r in all_results if getattr(r, "confidence", "") == "NONE")
    n_bl = sum(1 for r in all_results if getattr(r, "boundary_limited", False))

    r1_pass = sum(1 for r in all_results if getattr(r, "r1_pass", False)) / n_total
    r2_pass = sum(1 for r in all_results if getattr(r, "r2_pass", False)) / n_total
    r3_pass = sum(1 for r in all_results if getattr(r, "r3_pass", False)) / n_total
    r4_pass = sum(1 for r in all_results if getattr(r, "r4_pass", False)) / n_total

    # Detection latency: t_star - t_incident_start
    latencies = []
    for i, scenario_results in enumerate(ebd_results_per_scenario):
        if scenario_results and incident_windows and i < len(incident_windows):
            t_start = incident_windows[i][0]
            earliest = min(getattr(r, "t_star", float("inf")) for r in scenario_results)
            if earliest != float("inf"):
                latencies.append(earliest - t_start)

    mean_lat = float(np.mean(latencies)) if latencies else None
    median_lat = float(np.median(latencies)) if latencies else None

    return EBDEvalSummary(
        method_id=method_id,
        n_scenarios=n_scenarios,
        n_candidates=n_total,
        n_definitive=n_def,
        n_candidate_conf=n_cand,
        n_none_confidence=n_none,
        n_boundary_limited=n_bl,
        r1_pass_rate=r1_pass,
        r2_pass_rate=r2_pass,
        r3_pass_rate=r3_pass,
        r4_pass_rate=r4_pass,
        mean_detection_latency_s=mean_lat,
        median_detection_latency_s=median_lat,
        notes=f"method={method_id}, n_scenarios={n_scenarios}, n_candidates={n_total}",
    )
