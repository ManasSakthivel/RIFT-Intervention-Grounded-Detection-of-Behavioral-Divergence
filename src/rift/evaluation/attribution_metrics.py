"""RIFT Attribution Metrics — Phase 3.6 §13.

Implements the complete V1 metric framework:
  - raw Precision@1
  - conditional Precision@1
  - coverage
  - abstention rate
  - false attribution rate
  - non-identifiable rate
  - insufficient-evidence rate
  - graph-discovery failure rate
  - intervention failure rate
  - correct attribution count
  - correct abstention count

The frozen historical results:
  Raw V1 = 50%
  Conditional V1 = 60%
  (artifacts/phase3_5/v1_decomposition.json)
MUST NOT be modified.

Authority: docs/PHASE_3_SPEC_FREEZE.md §15, Phase 3.6 §13.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Per-scenario result record
# ---------------------------------------------------------------------------

@dataclass
class ScenarioResult:
    """
    Result record for one scenario evaluation.
    Carries both the method output and the ground truth for scoring.
    """
    scenario_id: str
    fault_id: str
    ground_truth_service: str
    is_confounded: bool
    is_multi_cause: bool
    is_not_identifiable: bool        # per scenario specification

    # Method output
    top_candidates: List[Tuple[str, float]]  # [(service, score), ...]
    abstained: bool
    abstain_reason: Optional[str] = None
    detection_latency_s: Optional[float] = None
    total_ed_s: float = 0.0
    notes: str = ""


# ---------------------------------------------------------------------------
# Attribution metrics
# ---------------------------------------------------------------------------

@dataclass
class AttributionMetricsResult:
    """
    Full attribution metric suite for one method over one scenario set.

    Historical frozen values (artifacts/phase3_5/v1_decomposition.json):
      raw_precision_at_1: 0.50
      conditional_precision_at_1: 0.60
    These values are NOT updated by this evaluator.
    """
    method_id: str
    n_scenarios: int

    # --- Primary attribution metrics ---
    raw_precision_at_1: float               # P@1 over all scenarios
    conditional_precision_at_1: float       # P@1 over non-abstained scenarios
    coverage: float                         # fraction of scenarios with ≥1 candidate
    abstention_rate: float                  # fraction abstained

    # --- Error decomposition ---
    false_attribution_rate: float           # attributed wrong service / non-abstained
    correct_attribution_rate: float         # attributed correct service / non-abstained

    # --- Abstention decomposition ---
    correct_abstention_rate: float          # abstained on confounded/non-id / all confounded
    not_identifiable_rate: float            # ABSTAIN for NOT_IDENTIFIABLE / total
    insufficient_evidence_rate: float       # ABSTAIN for INSUFFICIENT_SAMPLES / total

    # --- Pipeline failure rates ---
    graph_discovery_failure_rate: float     # FCI failure / total
    intervention_failure_rate: float        # intervention failure / total

    # --- Detection latency ---
    mean_detection_latency_s: Optional[float]
    median_detection_latency_s: Optional[float]

    # --- Sample info ---
    n_confounded: int = 0
    n_non_identifiable: int = 0
    n_abstained: int = 0
    n_correctly_attributed: int = 0
    n_correctly_abstained: int = 0

    notes: str = ""


def compute_attribution_metrics(
    results: List[ScenarioResult],
    method_id: str,
) -> AttributionMetricsResult:
    """
    Compute the full attribution metric suite for a set of scenario results.

    Parameters
    ----------
    results   : list of ScenarioResult (one per scenario)
    method_id : string identifier for the method being evaluated

    Returns
    -------
    AttributionMetricsResult
    """
    n = len(results)
    if n == 0:
        return AttributionMetricsResult(
            method_id=method_id, n_scenarios=0,
            raw_precision_at_1=0.0, conditional_precision_at_1=0.0,
            coverage=0.0, abstention_rate=0.0,
            false_attribution_rate=0.0, correct_attribution_rate=0.0,
            correct_abstention_rate=0.0, not_identifiable_rate=0.0,
            insufficient_evidence_rate=0.0, graph_discovery_failure_rate=0.0,
            intervention_failure_rate=0.0,
            mean_detection_latency_s=None, median_detection_latency_s=None,
            notes="No results to evaluate.",
        )

    n_abstained = sum(1 for r in results if r.abstained)
    n_non_abstained = n - n_abstained
    n_confounded = sum(1 for r in results if r.is_confounded)
    n_non_identifiable = sum(1 for r in results if r.is_not_identifiable)

    def top1_service(r: ScenarioResult) -> Optional[str]:
        if r.abstained or not r.top_candidates:
            return None
        return r.top_candidates[0][0]

    # Raw P@1: correct attribution / total (abstentions count as wrong)
    n_correct = sum(
        1 for r in results
        if not r.abstained and top1_service(r) == r.ground_truth_service
    )
    raw_p1 = n_correct / n

    # Conditional P@1: correct / non-abstained
    cond_p1 = (n_correct / n_non_abstained) if n_non_abstained > 0 else 0.0

    # Coverage: fraction with ≥1 candidate
    coverage = sum(1 for r in results if r.top_candidates) / n

    abstention_rate = n_abstained / n

    # False attribution: attributed something AND it was wrong
    n_false = sum(
        1 for r in results
        if not r.abstained and top1_service(r) is not None
        and top1_service(r) != r.ground_truth_service
    )
    false_rate = (n_false / n_non_abstained) if n_non_abstained > 0 else 0.0
    correct_rate = (n_correct / n_non_abstained) if n_non_abstained > 0 else 0.0

    # Correct abstention: abstained on confounded/non-identifiable
    n_should_abstain = sum(1 for r in results if r.is_confounded or r.is_not_identifiable)
    n_correctly_abstained = sum(
        1 for r in results
        if r.abstained and (r.is_confounded or r.is_not_identifiable)
    )
    correct_abstention_rate = (
        n_correctly_abstained / n_should_abstain if n_should_abstain > 0 else 0.0
    )

    # Abstention reason decomposition
    n_not_id_abstain = sum(
        1 for r in results
        if r.abstained and r.abstain_reason == "NOT_IDENTIFIABLE"
    )
    n_insuff_abstain = sum(
        1 for r in results
        if r.abstained and r.abstain_reason == "INSUFFICIENT_SAMPLES"
    )
    not_id_rate = n_not_id_abstain / n
    insuff_rate = n_insuff_abstain / n

    # Pipeline failure rates (from notes / abstain_reason)
    n_graph_fail = sum(
        1 for r in results
        if r.abstained and r.abstain_reason == "GRAPH_DISCOVERY_FAILURE"
    )
    n_intervention_fail = sum(
        1 for r in results
        if r.abstained and r.abstain_reason in ("INTERVENTION_FAILURE", "INTERVENTION_NOT_VERIFIED")
    )
    graph_fail_rate = n_graph_fail / n
    intervention_fail_rate = n_intervention_fail / n

    # Detection latency
    latencies = [r.detection_latency_s for r in results
                 if r.detection_latency_s is not None and not r.abstained]
    mean_lat = float(np.mean(latencies)) if latencies else None
    median_lat = float(np.median(latencies)) if latencies else None

    return AttributionMetricsResult(
        method_id=method_id,
        n_scenarios=n,
        raw_precision_at_1=raw_p1,
        conditional_precision_at_1=cond_p1,
        coverage=coverage,
        abstention_rate=abstention_rate,
        false_attribution_rate=false_rate,
        correct_attribution_rate=correct_rate,
        correct_abstention_rate=correct_abstention_rate,
        not_identifiable_rate=not_id_rate,
        insufficient_evidence_rate=insuff_rate,
        graph_discovery_failure_rate=graph_fail_rate,
        intervention_failure_rate=intervention_fail_rate,
        mean_detection_latency_s=mean_lat,
        median_detection_latency_s=median_lat,
        n_confounded=n_confounded,
        n_non_identifiable=n_non_identifiable,
        n_abstained=n_abstained,
        n_correctly_attributed=n_correct,
        n_correctly_abstained=n_correctly_abstained,
        notes=(
            f"method={method_id}, n={n}, seed-based evaluation. "
            "Raw V1=50%, Conditional V1=60% frozen historical values from "
            "artifacts/phase3_5/v1_decomposition.json must NOT be modified."
        ),
    )


def precision_at_k(
    top_candidates: List[Tuple[str, float]],
    ground_truth: str,
    k: int = 1,
) -> float:
    """P@k: 1.0 if ground_truth in top-k candidates, else 0.0."""
    top_k = [svc for svc, _ in top_candidates[:k]]
    return 1.0 if ground_truth in top_k else 0.0
