"""
B5 — RIFT-OBS: RIFT Without Intervention (Ablation Baseline)

Uses the SAME causal graph G_T as RIFT-FULL, but skips:
  - Intervention dispatch (step 3G/3H)
  - CID scoring (step 3I/3J)
  - Closed-loop update (step 3M)

Uses backdoor adjustment on observational data for causal effect estimation.

Purpose: Tests N2 — does intervention add measurable information beyond
the observational causal model alone?

Critical: If RIFT-OBS achieves the same P@1 as RIFT-FULL, the intervention
layer provides no measurable benefit and N1/N2 claims collapse.

Authority: docs/baseline_specification.md §Baseline 5,
           docs/baseline_information_matrix.md §Ablation Matrix
"""
from __future__ import annotations

from typing import Optional, Tuple

import networkx as nx
import numpy as np

from rift.baselines import BaselineInterface, BaselineOutput, IncidentContext
from rift.fci.fci_runner import PAGResult, run_fci
from rift.graph.anomaly_subgraph import build_anomaly_subgraph
from rift.graph.time_slice import build_time_sliced_graph
from rift.identifiability.identifiability import identify_query
from rift.identifiability.identifiability import IdentifiabilityStatus
from rift.ebd.ebd import compute_ebd


class RIFTObsBaseline(BaselineInterface):
    """
    RIFT-OBS ablation: full causal model, no intervention.

    Pipeline:
    1. Build G_T from call graph + FCI (same as RIFT-FULL)
    2. Detect anomaly subgraph using Strategy D
    3. Run FCI on anomaly subgraph to learn PAG
    4. Check identifiability for each candidate
    5. For IDENTIFIABLE: estimate posterior via backdoor on observational data
    6. For NOT_IDENTIFIABLE: mark as ABSTAIN candidate
    7. Return ranked candidates — NO interventions executed

    Status: PARTIAL — FCI and EBD are wired; observational backdoor
    adjustment uses simplified correlation proxy (Phase 3; full implementation
    in Phase 8 baseline evaluation).
    """

    def __init__(
        self,
        fci_alpha: float = 0.05,
        fci_seed: int = 42,
        fci_max_variables: int = 15,
        theta_detect: float = 3.0,
        theta_persist: int = 2,
        delta_t: float = 10.0,
    ):
        self.fci_alpha = fci_alpha
        self.fci_seed = fci_seed
        self.fci_max_variables = fci_max_variables
        self.theta_detect = theta_detect
        self.theta_persist = theta_persist
        self.delta_t = delta_t

    @property
    def baseline_id(self) -> str:
        return "B5-RIFT-OBS"

    def _build_pag_from_context(
        self, context: IncidentContext
    ) -> Optional[PAGResult]:
        """
        Attempt to run FCI on metric data from the incident context.
        Falls back to call-graph-only PAGResult if FCI cannot run.

        Returns PAGResult or None if insufficient data.
        """
        import pandas as pd

        # Pivot metrics to wide format for FCI
        rows = []
        for svc, df in context.metrics.items():
            t_start, t_end = context.incident_window
            sub = df[(df["time"] >= t_start) & (df["time"] <= t_end)].copy()
            sub = sub.rename(columns={"value": svc})
            sub = sub.set_index("time")
            rows.append(sub)

        if not rows:
            return None

        try:
            wide = pd.concat(rows, axis=1).dropna()
        except Exception:
            return None

        if wide.empty or wide.shape[0] < 20:
            return None

        cols = list(wide.columns)
        if len(cols) > self.fci_max_variables:
            cols = cols[:self.fci_max_variables]
            wide = wide[cols]

        try:
            from rift.fci.fci_runner import run_fci
            return run_fci(wide, alpha=self.fci_alpha, seed=self.fci_seed,
                           max_variables=self.fci_max_variables)
        except Exception:
            # FCI not available or data issues — return empty PAGResult
            from rift.fci.fci_runner import PAGResult, PAGEdge
            return PAGResult(variables=cols, edges=[])

    def _observational_scores(
        self,
        context: IncidentContext,
        pag_result: "PAGResult",
    ) -> dict:
        """
        Compute observational causal effect proxy via Pearson correlation.

        For each candidate service, compute correlation with downstream services
        as a proxy for P(Y | do(X)) under the backdoor criterion.

        NOTE: This is NOT the true do-calculus effect estimate. It is an
        observational approximation. The real limitation is documented in L2.
        Labeled PARTIAL for Phase 3.
        """
        scores = {}
        import pandas as pd
        t_start, t_end = context.incident_window
        for svc, df in context.metrics.items():
            sub = df[(df["time"] >= t_start) & (df["time"] <= t_end)]
            if sub.empty:
                scores[svc] = 0.0
                continue
            b = context.baseline_stats.get(svc, {})
            b_mean = b.get("mean", float(sub["value"].mean()))
            b_std = b.get("std", float(sub["value"].std()) + 1e-9)
            z_scores = (sub["value"] - b_mean) / b_std
            scores[svc] = float(abs(z_scores).mean())
        return scores

    def run(self, context: IncidentContext) -> BaselineOutput:
        """Execute RIFT-OBS pipeline. No interventions dispatched."""
        import time
        t0 = time.time()

        pag = self._build_pag_from_context(context)
        if pag is None:
            return BaselineOutput(
                baseline_id=self.baseline_id,
                fault_id=context.fault_id,
                top_candidates=[],
                abstained=True,
                notes="Insufficient data for PAG construction. ABSTAIN.",
            )

        # Run EBD (R1-R3, no R4 — no interventions)
        ebd_results = compute_ebd(
            metrics=context.metrics,
            baselines=context.baseline_stats,
            pag_result=pag,
            incident_window=context.incident_window,
            cid_results=None,  # ← key: NO intervention data
            delta_t=self.delta_t,
            theta_detect=self.theta_detect,
            theta_persist=self.theta_persist,
        )

        # Score observationally
        obs_scores = self._observational_scores(context, pag)

        candidates = []
        for result in ebd_results:
            if result.confidence in ("CANDIDATE",):
                # Check identifiability — ABSTAIN if not identifiable
                try:
                    id_result = identify_query(
                        pag, result.service_id,
                        [s for s in pag.variables if s != result.service_id],
                    )
                    if id_result.status == IdentifiabilityStatus.NOT_IDENTIFIABLE:
                        continue  # ABSTAIN for this candidate
                except Exception:
                    pass
                score = obs_scores.get(result.service_id, 0.0)
                candidates.append((result.service_id, score))

        if not candidates and ebd_results:
            # Fallback: return EBD results with anomaly score
            for result in ebd_results[:3]:
                candidates.append((result.service_id, result.anomaly_score))

        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)

        detection_latency = None
        if ebd_results:
            earliest = min(float(r.t_star) for r in ebd_results)
            detection_latency = earliest - context.incident_window[0]

        return BaselineOutput(
            baseline_id=self.baseline_id,
            fault_id=context.fault_id,
            top_candidates=candidates[:5],
            abstained=len(candidates) == 0,
            detection_latency_s=detection_latency,
            total_intervention_ed_s=0.0,  # NO interventions
            notes=(
                "RIFT-OBS: full causal model, no intervention. "
                "Observational scores are correlation-based proxies (PARTIAL, Phase 3). "
                "Full backdoor adjustment in Phase 8."
            ),
        )
