"""RIFT Complete Evaluation Metric System — Phase 4.5

Adds the missing runtime, memory, and intervention cost metrics to the
existing attribution metric suite, and provides a single unified evaluator
that runs over all required metrics.

Status: IMPLEMENTED / MAC_TESTED

Authority: docs/PHASE_3_SPEC_FREEZE.md §13-15, Phase 3.6 §13
"""
from __future__ import annotations

import time
import tracemalloc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from rift.evaluation.attribution_metrics import (
    AttributionMetricsResult,
    ScenarioResult,
    compute_attribution_metrics,
)


# ---------------------------------------------------------------------------
# Runtime and memory metrics
# ---------------------------------------------------------------------------

@dataclass
class RuntimeMetrics:
    """
    Per-run runtime and memory usage metrics.

    Collected for each pipeline execution to support RQ6 (efficiency).
    """
    method_id: str
    n_scenarios: int

    # --- Timing ---
    mean_pipeline_time_s: float          # mean wall-clock time per scenario
    median_pipeline_time_s: float        # median wall-clock time per scenario
    p95_pipeline_time_s: float           # 95th percentile
    max_pipeline_time_s: float           # worst-case

    # --- Memory (peak tracemalloc) ---
    mean_peak_memory_mb: Optional[float] = None
    max_peak_memory_mb: Optional[float] = None

    # --- Per-stage timing (dict: stage_name → mean_s) ---
    stage_timings: Dict[str, float] = field(default_factory=dict)
    bottleneck_stage: Optional[str] = None

    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "method_id": self.method_id,
            "n_scenarios": self.n_scenarios,
            "mean_pipeline_time_s": self.mean_pipeline_time_s,
            "median_pipeline_time_s": self.median_pipeline_time_s,
            "p95_pipeline_time_s": self.p95_pipeline_time_s,
            "max_pipeline_time_s": self.max_pipeline_time_s,
            "mean_peak_memory_mb": self.mean_peak_memory_mb,
            "max_peak_memory_mb": self.max_peak_memory_mb,
            "stage_timings": self.stage_timings,
            "bottleneck_stage": self.bottleneck_stage,
            "notes": self.notes,
        }


@dataclass
class InterventionCostMetrics:
    """
    Intervention cost metrics (RQ6 efficiency component).

    Tracks total execution duration of interventions across all scenarios.
    """
    method_id: str
    n_scenarios: int

    # --- Cumulative cost ---
    mean_total_ed_s: float               # mean cumulative intervention duration per scenario
    median_total_ed_s: float
    total_ed_s_across_all: float         # sum over all scenarios

    # --- Intervention count ---
    mean_n_interventions: float          # mean number of interventions per scenario
    max_n_interventions: int

    # --- Budget utilization ---
    mean_budget_utilization: float       # fraction of t_budget consumed

    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "method_id": self.method_id,
            "n_scenarios": self.n_scenarios,
            "mean_total_ed_s": self.mean_total_ed_s,
            "median_total_ed_s": self.median_total_ed_s,
            "total_ed_s_across_all": self.total_ed_s_across_all,
            "mean_n_interventions": self.mean_n_interventions,
            "max_n_interventions": self.max_n_interventions,
            "mean_budget_utilization": self.mean_budget_utilization,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Confidence intervals (bootstrap) for attribution metrics
# ---------------------------------------------------------------------------

@dataclass
class MetricCI:
    """Bootstrap 95% confidence interval for a single metric."""
    metric: str
    point_estimate: float
    ci_lower: float
    ci_upper: float
    n_bootstrap: int = 2000
    ci_level: float = 0.95


def bootstrap_metric_ci(
    scores: np.ndarray,
    metric_name: str = "metric",
    n_bootstrap: int = 2000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> MetricCI:
    """
    Bootstrap confidence interval for a metric computed as mean(scores).

    Parameters
    ----------
    scores      : per-scenario binary or float scores (e.g., 0/1 for P@1)
    metric_name : label for this metric
    n_bootstrap : number of bootstrap resamples
    ci_level    : confidence level (default 0.95 → 95%)
    seed        : RNG seed for reproducibility

    Returns
    -------
    MetricCI with point_estimate and bootstrap CI
    """
    scores = np.asarray(scores, dtype=float)
    rng = np.random.default_rng(seed)
    point = float(np.mean(scores))

    boot = np.array([
        np.mean(rng.choice(scores, size=len(scores), replace=True))
        for _ in range(n_bootstrap)
    ])
    alpha = 1.0 - ci_level
    ci_lower = float(np.percentile(boot, 100 * alpha / 2))
    ci_upper = float(np.percentile(boot, 100 * (1 - alpha / 2)))

    return MetricCI(
        metric=metric_name,
        point_estimate=point,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        n_bootstrap=n_bootstrap,
        ci_level=ci_level,
    )


# ---------------------------------------------------------------------------
# Complete evaluation result
# ---------------------------------------------------------------------------

@dataclass
class CompleteEvaluationResult:
    """
    Full evaluation result for one method over one scenario set.

    Combines all metric groups:
      - Attribution metrics (P@1, coverage, abstention, etc.)
      - Runtime metrics (wall-clock, memory)
      - Intervention cost metrics (total_ed_s, n_interventions)
      - Bootstrap CIs on primary metrics
    """
    method_id: str
    n_scenarios: int
    attribution: AttributionMetricsResult
    runtime: Optional[RuntimeMetrics] = None
    cost: Optional[InterventionCostMetrics] = None
    confidence_intervals: Dict[str, MetricCI] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict:
        result = {
            "method_id": self.method_id,
            "n_scenarios": self.n_scenarios,
            "attribution": {
                "raw_precision_at_1": self.attribution.raw_precision_at_1,
                "conditional_precision_at_1": self.attribution.conditional_precision_at_1,
                "coverage": self.attribution.coverage,
                "abstention_rate": self.attribution.abstention_rate,
                "false_attribution_rate": self.attribution.false_attribution_rate,
                "correct_attribution_rate": self.attribution.correct_attribution_rate,
                "correct_abstention_rate": self.attribution.correct_abstention_rate,
                "not_identifiable_rate": self.attribution.not_identifiable_rate,
                "insufficient_evidence_rate": self.attribution.insufficient_evidence_rate,
                "graph_discovery_failure_rate": self.attribution.graph_discovery_failure_rate,
                "intervention_failure_rate": self.attribution.intervention_failure_rate,
                "mean_detection_latency_s": self.attribution.mean_detection_latency_s,
                "median_detection_latency_s": self.attribution.median_detection_latency_s,
            },
            "confidence_intervals": {
                k: {"point": v.point_estimate, "ci_lower": v.ci_lower, "ci_upper": v.ci_upper}
                for k, v in self.confidence_intervals.items()
            },
        }
        if self.runtime:
            result["runtime"] = self.runtime.to_dict()
        if self.cost:
            result["cost"] = self.cost.to_dict()
        return result


# ---------------------------------------------------------------------------
# Unified evaluator
# ---------------------------------------------------------------------------

def compute_complete_evaluation(
    results: List[ScenarioResult],
    method_id: str,
    pipeline_times_s: Optional[List[float]] = None,
    peak_memories_mb: Optional[List[float]] = None,
    stage_timings_list: Optional[List[Dict[str, float]]] = None,
    total_ed_s_list: Optional[List[float]] = None,
    n_interventions_list: Optional[List[int]] = None,
    t_budget_s: float = 600.0,
    ci_n_bootstrap: int = 2000,
    ci_seed: int = 42,
) -> CompleteEvaluationResult:
    """
    Compute the complete evaluation metric suite for a method.

    Parameters
    ----------
    results              : per-scenario ScenarioResult objects
    method_id            : method identifier
    pipeline_times_s     : per-scenario wall-clock pipeline time (seconds)
    peak_memories_mb     : per-scenario peak memory (MB, from tracemalloc)
    stage_timings_list   : per-scenario dict of stage_name → duration_s
    total_ed_s_list      : per-scenario total intervention execution duration
    n_interventions_list : per-scenario number of interventions executed
    t_budget_s           : intervention budget for utilization calculation
    ci_n_bootstrap       : bootstrap resamples for CIs
    ci_seed              : bootstrap seed

    Returns
    -------
    CompleteEvaluationResult with all metrics filled.
    """
    # Attribution metrics
    attr = compute_attribution_metrics(results, method_id)

    # Runtime metrics
    runtime: Optional[RuntimeMetrics] = None
    if pipeline_times_s:
        times = np.array(pipeline_times_s, dtype=float)

        stage_mean: Dict[str, float] = {}
        if stage_timings_list:
            all_stages: Dict[str, List[float]] = {}
            for st in stage_timings_list:
                for stage, t in st.items():
                    all_stages.setdefault(stage, []).append(t)
            stage_mean = {s: float(np.mean(v)) for s, v in all_stages.items()}

        bottleneck = max(stage_mean, key=lambda k: stage_mean[k]) if stage_mean else None

        mem_arr = np.array(peak_memories_mb, dtype=float) if peak_memories_mb else None

        runtime = RuntimeMetrics(
            method_id=method_id,
            n_scenarios=len(pipeline_times_s),
            mean_pipeline_time_s=float(np.mean(times)),
            median_pipeline_time_s=float(np.median(times)),
            p95_pipeline_time_s=float(np.percentile(times, 95)),
            max_pipeline_time_s=float(np.max(times)),
            mean_peak_memory_mb=float(np.mean(mem_arr)) if mem_arr is not None else None,
            max_peak_memory_mb=float(np.max(mem_arr)) if mem_arr is not None else None,
            stage_timings=stage_mean,
            bottleneck_stage=bottleneck,
        )

    # Intervention cost metrics
    cost: Optional[InterventionCostMetrics] = None
    if total_ed_s_list is not None:
        ed = np.array(total_ed_s_list, dtype=float)
        n_inv = np.array(n_interventions_list or [0] * len(total_ed_s_list), dtype=int)
        cost = InterventionCostMetrics(
            method_id=method_id,
            n_scenarios=len(total_ed_s_list),
            mean_total_ed_s=float(np.mean(ed)),
            median_total_ed_s=float(np.median(ed)),
            total_ed_s_across_all=float(np.sum(ed)),
            mean_n_interventions=float(np.mean(n_inv)),
            max_n_interventions=int(np.max(n_inv)) if len(n_inv) > 0 else 0,
            mean_budget_utilization=float(np.mean(ed / t_budget_s)),
        )

    # Bootstrap CIs on primary attribution metrics
    n = len(results)
    cis: Dict[str, MetricCI] = {}

    if n > 0:
        p1_scores = np.array([
            1.0 if (not r.abstained and r.top_candidates
                    and r.top_candidates[0][0] == r.ground_truth_service) else 0.0
            for r in results
        ])
        cis["raw_precision_at_1"] = bootstrap_metric_ci(
            p1_scores, "raw_precision_at_1", ci_n_bootstrap, seed=ci_seed
        )

        non_abstained = [
            r for r in results if not r.abstained and r.top_candidates
        ]
        if non_abstained:
            cond_scores = np.array([
                1.0 if r.top_candidates[0][0] == r.ground_truth_service else 0.0
                for r in non_abstained
            ])
            cis["conditional_precision_at_1"] = bootstrap_metric_ci(
                cond_scores, "conditional_precision_at_1", ci_n_bootstrap, seed=ci_seed
            )

        abstain_scores = np.array([1.0 if r.abstained else 0.0 for r in results])
        cis["abstention_rate"] = bootstrap_metric_ci(
            abstain_scores, "abstention_rate", ci_n_bootstrap, seed=ci_seed
        )

    return CompleteEvaluationResult(
        method_id=method_id,
        n_scenarios=n,
        attribution=attr,
        runtime=runtime,
        cost=cost,
        confidence_intervals=cis,
        notes=(
            f"Complete evaluation: attribution + runtime + cost + CIs. "
            f"n={n}, ci_n_bootstrap={ci_n_bootstrap}. "
            "Status: IMPLEMENTED / MAC_TESTED"
        ),
    )
