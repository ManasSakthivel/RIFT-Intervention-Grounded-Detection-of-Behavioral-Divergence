"""
B7 — RIFT-ONE-SHOT: RIFT-FULL with Closed-Loop Update Disabled (Ablation Baseline)

Implements the ablation condition for H3 (docs/hypotheses.md):
  RIFT-ONE-SHOT = RIFT-FULL with closed_loop_update DISABLED
  "Initial candidate ranking used for all intervention selections (no Bayesian update)"
  "model is NOT updated between successive interventions"

Components enabled:
  fci_graph_learning: true
  identifiability_check: true
  msis_cost_selection: true
  network_intervention: true  (recorded, not dispatched in dry-run)
  cid_scoring: true
  ebd_scoring: true
  closed_loop_update: false   ← KEY: disabled

Components disabled:
  closed_loop_update: false   ← posterior NOT updated after any intervention

Fairness guarantee (critical for H3):
  - Identical to RIFT-FULL in every component EXCEPT the Bayesian posterior update.
  - Uses the SAME initial posterior (from EBD anomaly scores) for ALL MSIS calls.
  - Does NOT call update_candidate_posterior(), update_edge_confidence(),
    or update_graph_structure() after any intervention.
  - Receives only IncidentContext — no ground truth.

Authority: docs/hypotheses.md H3, experiments/REGISTRY.yaml EXP-013,
           experiments/ablations/ABLATION_REGISTRY.yaml RIFT-ONE-SHOT
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
import pandas as pd

from rift.baselines import BaselineInterface, BaselineOutput, IncidentContext
from rift.ebd.ebd import compute_ebd
from rift.fci.fci_runner import PAGResult, run_fci
from rift.optimizer.cost_model import (
    InterventionCandidate,
    compute_intervention_costs,
    greedy_msis,
)


class RIFTOneShotBaseline(BaselineInterface):
    """
    RIFT-ONE-SHOT ablation: full RIFT pipeline, no closed-loop posterior update.

    Pipeline:
    1. Build PAG from context metrics via FCI (same as RIFT-FULL)
    2. Run EBD to get CANDIDATE/DEFINITIVE services
    3. Compute INITIAL posterior from EBD anomaly scores (normalize) — FROZEN
    4. Run MSIS to select interventions using the FROZEN initial posterior
       (same posterior passed to every MSIS call — no update between steps)
    5. Record simulated interventions and collect CID-like scores
       BUT DO NOT UPDATE POSTERIOR BETWEEN INTERVENTIONS
    6. Return BaselineOutput with candidates ranked by INITIAL frozen posterior

    Stopping conditions (same as RIFT-FULL):
      ENTROPY_CONVERGED | BUDGET_EXHAUSTED | SAFETY_ABORT | ALL_NON_IDENTIFIABLE

    Critical invariant for H3 fairness:
      self._frozen_posterior is set once after EBD and never mutated thereafter.
      Every call to greedy_msis receives self._frozen_posterior unmodified.
    """

    baseline_id = "B7-RIFT-ONE-SHOT"

    def __init__(
        self,
        fci_alpha: float = 0.05,
        fci_seed: int = 42,
        fci_max_variables: int = 15,
        theta_detect: float = 3.0,
        theta_persist: int = 2,
        delta_t: float = 10.0,
        theta_entropy: float = 0.5,
        t_budget: float = 600.0,
    ):
        self.fci_alpha = fci_alpha
        self.fci_seed = fci_seed
        self.fci_max_variables = fci_max_variables
        self.theta_detect = theta_detect
        self.theta_persist = theta_persist
        self.delta_t = delta_t
        self.theta_entropy = theta_entropy
        self.t_budget = t_budget
        # _frozen_posterior is set during run() and never mutated after that
        self._frozen_posterior: Optional[Dict[str, float]] = None

    def _build_pag_from_context(self, context: IncidentContext) -> PAGResult:
        """
        Build PAG via FCI on metric data. Falls back to empty PAGResult if FCI
        cannot run (insufficient data or FCI not available).
        """
        rows = []
        t_start, t_end = context.incident_window
        for svc, df in context.metrics.items():
            sub = df[(df["time"] >= t_start) & (df["time"] <= t_end)].copy()
            sub = sub.rename(columns={"value": svc}).set_index("time")
            rows.append(sub)

        if not rows:
            return PAGResult(variables=list(context.metrics.keys()), edges=[])

        try:
            wide = pd.concat(rows, axis=1).dropna()
        except Exception:
            return PAGResult(variables=list(context.metrics.keys()), edges=[])

        if wide.shape[0] < 20 or wide.shape[1] < 2:
            return PAGResult(variables=list(context.metrics.keys()), edges=[])

        cols = list(wide.columns)
        if len(cols) > self.fci_max_variables:
            cols = cols[: self.fci_max_variables]
            wide = wide[cols]

        try:
            return run_fci(wide, alpha=self.fci_alpha, seed=self.fci_seed,
                           max_variables=self.fci_max_variables)
        except Exception:
            return PAGResult(variables=cols, edges=[])

    def run(self, context: IncidentContext) -> BaselineOutput:
        """
        Execute RIFT-ONE-SHOT. Uses same FCI+EBD+MSIS as RIFT-FULL.
        DOES NOT update posterior between interventions.
        """
        # ── Step 1: Build PAG ────────────────────────────────────────────────
        pag = self._build_pag_from_context(context)

        # ── Step 2: Run EBD (same as RIFT-FULL; no CID at this stage) ───────
        ebd_results = compute_ebd(
            metrics=context.metrics,
            baselines=context.baseline_stats,
            pag_result=pag,
            incident_window=context.incident_window,
            cid_results=None,
            delta_t=self.delta_t,
            theta_detect=self.theta_detect,
            theta_persist=self.theta_persist,
        )

        if not ebd_results:
            self._frozen_posterior = {}
            return BaselineOutput(
                baseline_id=self.baseline_id,
                fault_id=context.fault_id,
                top_candidates=[],
                abstained=True,
                total_intervention_ed_s=0.0,
                notes=(
                    "RIFT-ONE-SHOT: no EBD candidates found. ABSTAIN. "
                    "no closed-loop update (frozen posterior). "
                    "Authority: docs/hypotheses.md H3, EXP-013"
                ),
            )

        # ── Step 3: Compute INITIAL posterior from EBD anomaly scores ───────
        # Normalize anomaly scores → probability distribution.
        # This posterior is FROZEN and never updated.
        candidate_services = [
            r for r in ebd_results
            if r.confidence in ("CANDIDATE", "DEFINITIVE")
        ]
        if not candidate_services:
            # Fallback: use all EBD results
            candidate_services = ebd_results[:3]

        raw_scores: Dict[str, float] = {
            r.service_id: max(r.anomaly_score, 1e-9) for r in candidate_services
        }
        total_score = sum(raw_scores.values()) or 1.0
        initial_posterior: Dict[str, float] = {
            svc: score / total_score for svc, score in raw_scores.items()
        }
        # Store frozen posterior — NEVER mutated after this point
        self._frozen_posterior = dict(initial_posterior)

        # ── Step 4: Build intervention candidates and run MSIS ───────────────
        # MSIS uses the FROZEN initial_posterior for all calls.
        causal_graph = context.call_graph
        intervention_candidates = [
            InterventionCandidate(
                service_id=svc,
                variable=f"{svc}.latency",
                intervention_type="LATENCY",
                target_value=200.0,
                nominal_value=50.0,
                description=f"Latency injection on {svc}",
            )
            for svc in initial_posterior
        ]

        costs = compute_intervention_costs(
            candidates=intervention_candidates,
            causal_graph=causal_graph,
            candidate_posterior=self._frozen_posterior,   # ← FROZEN
            service_count=len(context.metrics),
        )

        # Run MSIS with FROZEN posterior — NO update between selections
        msis_result = greedy_msis(
            costs=costs,
            candidate_posterior=self._frozen_posterior,   # ← FROZEN
            theta_entropy=self.theta_entropy,
            t_budget=self.t_budget,
        )

        total_ed = float(sum(
            c.execution_duration_s for c in msis_result.selected_interventions
        ))

        # ── Step 5: Rank candidates by INITIAL (frozen) posterior ────────────
        # DO NOT update posterior. Use initial_posterior for final ranking.
        ranked: List[Tuple[str, float]] = sorted(
            self._frozen_posterior.items(), key=lambda x: x[1], reverse=True
        )

        detection_latency: Optional[float] = None
        if ebd_results:
            earliest = min(float(r.t_star) for r in ebd_results)
            detection_latency = earliest - context.incident_window[0]

        return BaselineOutput(
            baseline_id=self.baseline_id,
            fault_id=context.fault_id,
            top_candidates=ranked[:5],
            abstained=len(ranked) == 0,
            detection_latency_s=detection_latency,
            total_intervention_ed_s=total_ed,
            notes=(
                f"RIFT-ONE-SHOT: full FCI+EBD+MSIS pipeline; "
                f"no closed-loop update — posterior frozen after initial EBD. "
                f"Stopped: {msis_result.stopped_reason}. "
                f"Ablation for H3 (EXP-013). "
                f"Authority: docs/hypotheses.md H3, ABLATION_REGISTRY.yaml RIFT-ONE-SHOT"
            ),
        )
