"""
RIFT Baselines — Shared Interface and Evaluation Protocol

All baselines and ablations implement BaselineInterface.
This ensures fair comparison: same inputs, same scoring harness, same output schema.

Authority: docs/baseline_information_matrix.md, docs/baseline_specification.md
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import networkx as nx


# ─────────────────────────────────────────────────────────────────────────────
# Shared input schema (all baselines receive)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class IncidentContext:
    """
    Shared input structure given to ALL baselines and RIFT-FULL.
    Ground truth is withheld here; the scoring harness adds it separately.

    Authority: docs/baseline_information_matrix.md §Shared Input Serialization
    """
    fault_id: str
    incident_window: Tuple[float, float]          # (t_start, t_end) seconds
    metrics: Dict[str, pd.DataFrame]              # service → DataFrame(time, value)
    baseline_stats: Dict[str, Dict[str, float]]   # service → {mean, std}
    call_graph: nx.DiGraph                        # static topology from traces
    traces: Optional[List[Dict[str, Any]]] = None # OTel spans (optional for obs-only)
    scenario_seed: int = 42


# ─────────────────────────────────────────────────────────────────────────────
# Baseline output schema
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BaselineOutput:
    """
    Standardized output from any baseline or RIFT ablation.

    top_candidates: ranked list of (service_id, confidence_score)
    abstained: True if baseline produced no attribution (e.g., insufficient evidence)
    abstention_reason: machine-readable reason code when abstained=True.
        Allowed values:
          NOT_IDENTIFIABLE        — causal query P(Y|do(X)) not identifiable from G_T
          INSUFFICIENT_SAMPLES    — not enough data for reliable estimate
          GRAPH_DISCOVERY_FAILURE — FCI failed to produce usable PAG
          INTERVENTION_FAILURE    — all interventions failed validation/rollback
          NO_CANDIDATES           — EBD found no anomaly candidates (R1 fails for all)
          MULTI_CAUSE_AMBIGUOUS   — multiple equally-likely root causes; no single top-1
          None                    — abstained=False (attribution was produced)
        P2-02: abstention reasons are now reported separately per baseline so that
        abstention_rate comparisons across baselines use identical semantics.
    detection_latency_s: seconds from incident_window[0] to first candidate
    notes: free-form; used for audit/reproducibility
    """
    baseline_id: str
    fault_id: str
    top_candidates: List[Tuple[str, float]]       # [(service_id, score), ...]
    abstained: bool = False
    abstention_reason: Optional[str] = None       # P2-02: reason code when abstained=True
    detection_latency_s: Optional[float] = None
    total_intervention_ed_s: float = 0.0          # non-zero only for active baselines
    notes: str = ""
    raw_output: Dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Abstract baseline interface
# ─────────────────────────────────────────────────────────────────────────────

class BaselineInterface(ABC):
    """
    All baselines and ablations must implement this interface.

    Guarantees:
    - All instances receive the same IncidentContext (no extra info)
    - Outputs are comparable via BaselineOutput schema
    - run() is the only entry point — no side channels
    """

    @property
    @abstractmethod
    def baseline_id(self) -> str:
        """Short identifier, e.g. 'B1-THRESHOLD', 'B5-RIFT-OBS', 'RIFT-FULL'."""

    @abstractmethod
    def run(self, context: IncidentContext) -> BaselineOutput:
        """
        Execute the baseline on the given incident context.
        Must NOT access ground truth labels.
        Must NOT call evaluate_*() or scoring functions internally.
        """


# ─────────────────────────────────────────────────────────────────────────────
# Scoring helpers (used by evaluation harness only, not baselines)
# ─────────────────────────────────────────────────────────────────────────────

def precision_at_k(output: BaselineOutput, ground_truth_service: str, k: int = 1) -> float:
    """Precision@k: 1.0 if ground_truth_service appears in top-k candidates."""
    if output.abstained:
        return 0.0
    top_k = [svc for svc, _ in output.top_candidates[:k]]
    return 1.0 if ground_truth_service in top_k else 0.0


def abstention_correct(output: BaselineOutput, scenario_is_confounded: bool) -> bool:
    """
    For H2: RIFT should abstain on confounded scenarios.
    Returns True if (abstained AND confounded) OR (not abstained AND not confounded).
    """
    if scenario_is_confounded:
        return output.abstained
    return not output.abstained
