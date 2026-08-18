"""RIFT EBD — Earliest Behavioral Divergence — Phase 3K."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import networkx as nx

from src.rift.fci.fci_runner import PAGResult, PAGEdgeType


# ─────────────────────────────────────────────────────────────────────────────
# EBD Result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EBDResult:
    """
    Result of Earliest Behavioral Divergence analysis.

    CANDIDATE: R1-R3 satisfied (fast, ~30s, no intervention required)
    DEFINITIVE: R1-R4 satisfied (slower, ~120-300s, intervention confirmed)

    Authority: docs/PHASE_3_SPEC_FREEZE.md §9
    """
    result_id: str
    service_id: str
    variable_id: str
    t_star: float
    confidence: str  # "CANDIDATE" | "DEFINITIVE" | "NONE"
    r1_pass: bool = False
    r2_pass: bool = False
    r3_pass: bool = False
    r4_pass: bool = False
    # var_id → (W1_estimate, CI_lower, CI_upper, n_samples, grade)
    cid_scores: Dict[str, Any] = field(default_factory=dict)
    boundary_limited: bool = False
    assumption_warnings: List[str] = field(default_factory=list)
    identifiability_state: str = "IDENTIFIABLE"
    intervention_record_ref: Optional[str] = None
    causal_path: List[Tuple[str, str]] = field(default_factory=list)
    anomaly_score: float = 0.0
    notes: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Helper: build causal graph from PAG (directed edges only)
# ─────────────────────────────────────────────────────────────────────────────

def _pag_to_digraph(pag: PAGResult) -> nx.DiGraph:
    G = nx.DiGraph()
    for v in pag.variables:
        G.add_node(v)
    for e in pag.edges:
        if e.edge_type.value == "DIRECTED":
            G.add_edge(e.source, e.target)
    return G


# ─────────────────────────────────────────────────────────────────────────────
# R1 — Observed behavioral deviation
# ─────────────────────────────────────────────────────────────────────────────

def _check_r1(
    metrics: pd.DataFrame,
    baseline_mean: float,
    baseline_std: float,
    theta_detect: float,
    theta_persist_windows: int,
    delta_t: float,
    t_start: float,
) -> Tuple[bool, float, float]:
    """
    R1: Δᵢₖ(t) > θ_detect for some k, persisting ≥ 2Δt.
    Returns (passes, t_star, anomaly_score).
    t_star = first time window where persistent divergence begins.
    """
    if baseline_std <= 0:
        return False, float('inf'), 0.0

    # Compute per-row deviation (z-score)
    deviations = (metrics['value'] - baseline_mean) / baseline_std

    # Find windows where deviation exceeds threshold
    exceeds = deviations.abs() > theta_detect

    # Find first run of theta_persist_windows consecutive exceedances
    window_times = sorted(metrics['time'].unique())
    t_windows_exceed = [t for t in window_times if any(
        (metrics['time'] == t) & exceeds
    )]

    if not t_windows_exceed:
        return False, float('inf'), 0.0

    # Check for persistence (consecutive windows)
    for i, t in enumerate(t_windows_exceed):
        # Check if there are theta_persist_windows consecutive windows
        run_length = 1
        for j in range(i + 1, len(t_windows_exceed)):
            if abs(t_windows_exceed[j] - (t + run_length * delta_t)) < delta_t * 0.1:
                run_length += 1
                if run_length >= theta_persist_windows:
                    # Compute max anomaly score in this run
                    score = float(deviations.abs().max())
                    return True, t, score
            else:
                break

    # Single window only (no persistence) — not enough
    return False, float('inf'), 0.0


# ─────────────────────────────────────────────────────────────────────────────
# R2 — Temporal precedence
# ─────────────────────────────────────────────────────────────────────────────

def _check_r2(
    t_star_candidate: float,
    all_divergence_times: Dict[str, float],
    service_id: str,
    delta_t: float,
) -> Tuple[bool, List[str]]:
    """
    R2: t* < tⱼ for all j ≠ i diverging.
    Ties (same window) are resolved by R3 (causal ancestry).
    Returns (passes, list_of_services_with_earlier_or_tied_divergence).
    """
    earlier_services = []
    tied_services = []

    for svc, t in all_divergence_times.items():
        if svc == service_id:
            continue
        if t < t_star_candidate - delta_t * 0.01:  # strictly earlier (with tolerance)
            earlier_services.append(svc)
        elif abs(t - t_star_candidate) <= delta_t * 0.5:  # same window (tie)
            tied_services.append(svc)

    # R2 fails if there are strictly earlier divergences
    # Ties are resolved by R3 — so R2 is True if no strict precedence
    if earlier_services:
        return False, earlier_services

    return True, tied_services  # True (may have ties, resolved by R3)


# ─────────────────────────────────────────────────────────────────────────────
# R3 — Causal relevance
# ─────────────────────────────────────────────────────────────────────────────

def _check_r3(
    service_id: str,
    diverging_services: List[str],
    dag: nx.DiGraph,
    t_star_self: Optional[float] = None,
    all_divergence_times: Optional[Dict[str, float]] = None,
) -> Tuple[bool, List[Tuple[str, str]]]:
    """
    R3: Causal relevance criterion.

    Primary rule (non-leaf):
        ∃ j s.t. Vⱼ diverges AND Vᵢ →⋯→ Vⱼ in G_T.
        (There is a downstream diverging service reachable from Vᵢ)

    Leaf-node fallback (P1-11 fix):
        If Vᵢ is a leaf node (in-degree ≥ 1, out-degree = 0 in the causal graph),
        then R3 is satisfied if any upstream caller Vⱼ diverges AND Vⱼ →⋯→ Vᵢ in G_T
        AND t*(Vⱼ) >= t*(Vᵢ) (upstream divergence is same-time or later).

        Safety criterion: if Vⱼ diverges STRICTLY BEFORE Vᵢ and the causal arrow is
        Vⱼ →⋯→ Vᵢ, then Vⱼ is likely the root cause and Vᵢ is the downstream effect.
        In that case, R3-leaf must NOT fire for Vᵢ (it would be a false attribution).

        R3-leaf fires only when the upstream caller diverges AFTER the leaf node,
        consistent with fault propagation from the leaf upward to the caller.

    Formally defensible criterion (P1-11, docs/causal_assumptions.md A9):
        Pure callee services (leaf nodes) cannot propagate divergence downstream.
        Their causal effect manifests as upstream caller degradation AFTER the leaf
        shows anomaly. R3-leaf accepts this temporal ordering as causal evidence.

    Authority: docs/hypotheses.md L4, P1-11 resolution.
    Returns (passes, causal_path_edges).
    """
    if not dag.has_node(service_id):
        return False, []

    # Primary R3: downstream diverging path exists
    for svc in diverging_services:
        if svc == service_id:
            continue
        if not dag.has_node(svc):
            continue
        try:
            if nx.has_path(dag, service_id, svc):
                path = nx.shortest_path(dag, service_id, svc)
                edges = [(path[i], path[i+1]) for i in range(len(path)-1)]
                return True, edges
        except (nx.NodeNotFound, nx.NetworkXError):
            continue

    # R3-leaf fallback: apply when Vᵢ is a leaf node (out-degree = 0)
    # Only fires when upstream callers diverge SAME-TIME OR AFTER Vᵢ (fault propagates up).
    out_deg = dag.out_degree(service_id) if dag.has_node(service_id) else 0
    if out_deg == 0:
        for svc in diverging_services:
            if svc == service_id:
                continue
            if not dag.has_node(svc):
                continue
            # Temporal safety constraint: upstream Vⱼ must NOT diverge strictly before Vᵢ.
            # If Vⱼ diverges before Vᵢ (Vⱼ's t* < Vᵢ's t*), Vⱼ is the root cause, not Vᵢ.
            if (t_star_self is not None and all_divergence_times is not None):
                t_j = all_divergence_times.get(svc)
                if t_j is not None and t_j < t_star_self - 0.01:
                    continue  # upstream diverged before leaf → skip (not leaf root cause)
            try:
                if nx.has_path(dag, svc, service_id):
                    path = nx.shortest_path(dag, svc, service_id)
                    edges = [(path[i], path[i+1]) for i in range(len(path)-1)]
                    return True, edges  # upstream evidence accepted for leaf node
            except (nx.NodeNotFound, nx.NetworkXError):
                continue

    return False, []


# ─────────────────────────────────────────────────────────────────────────────
# Main EBD computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_ebd(
    metrics: Dict[str, pd.DataFrame],
    baselines: Dict[str, Dict[str, float]],
    pag_result: PAGResult,
    incident_window: Tuple[float, float],
    cid_results: Optional[Dict[str, Any]] = None,
    delta_t: float = 10.0,
    theta_detect: float = 3.0,
    theta_persist: int = 2,
    theta_cid: float = 0.1,
) -> List[EBDResult]:
    """
    Compute Earliest Behavioral Divergence candidates.

    Returns a ranked list of EBDResult objects (CANDIDATE first, then DEFINITIVE if
    cid_results are provided).

    CANDIDATE EBDs: R1-R3 satisfied (no intervention required)
    DEFINITIVE EBDs: R1-R4 satisfied (intervention confirmed via cid_results)

    CRITICAL GUARANTEE: A later large anomaly does NOT override an earlier causal
    divergence. Temporal precedence (R2) is checked strictly before anomaly score.

    Authority: docs/PHASE_3_SPEC_FREEZE.md §9
    """
    dag = _pag_to_digraph(pag_result)

    # Phase 1: Check R1 for all services
    r1_results: Dict[str, Tuple[bool, float, float]] = {}  # service → (pass, t_star, score)

    for service_id, df in metrics.items():
        baseline = baselines.get(service_id, {})
        b_mean = baseline.get('mean', float(df['value'].mean()))
        b_std = baseline.get('std', float(df['value'].std()) + 1e-9)

        t_start = incident_window[0]
        # Filter to incident window
        incident_df = df[(df['time'] >= incident_window[0]) & (df['time'] <= incident_window[1])]
        if incident_df.empty:
            r1_results[service_id] = (False, float('inf'), 0.0)
            continue

        passes, t_star, score = _check_r1(
            incident_df, b_mean, b_std, theta_detect, theta_persist, delta_t, t_start
        )
        r1_results[service_id] = (passes, t_star, score)

    # Services that diverge (R1 passes)
    diverging: Dict[str, float] = {
        svc: t for svc, (passes, t, _) in r1_results.items() if passes
    }

    if not diverging:
        return []

    candidates: List[EBDResult] = []
    result_counter = 0

    for service_id in diverging:
        r1_pass, t_star, anomaly_score = r1_results[service_id]
        all_divergence_times = {s: t for s, t in diverging.items() if s != service_id}

        # R2: Temporal precedence
        r2_pass, earlier_or_tied = _check_r2(t_star, diverging, service_id, delta_t)

        # R3: Causal relevance (pass t_star and divergence times for leaf-node safety check)
        diverging_others = [s for s in diverging if s != service_id]
        r3_pass, causal_path = _check_r3(
            service_id, diverging_others, dag,
            t_star_self=t_star,
            all_divergence_times=diverging,
        )

        # If R2 failed but there are ties, try to resolve by R3
        if not r2_pass and earlier_or_tied:
            # All "earlier" services — check if current service is their ancestor
            # If current service is ancestor of all "earlier" services, R2 tie resolved
            all_are_descendants = all(
                dag.has_node(service_id) and dag.has_node(svc) and
                nx.has_path(dag, service_id, svc)
                for svc in earlier_or_tied
                if dag.has_node(svc)
            )
            if all_are_descendants:
                r2_pass = True  # R3 resolves the tie in favor of this service

        # Collect assumption warnings
        warnings = []
        has_bidirected = any(
            (e.source == service_id or e.target == service_id) and
            e.edge_type.value == "BIDIRECTED"
            for e in pag_result.edges
        )
        if has_bidirected:
            warnings.append(
                f"Bidirected edge adjacent to {service_id} — possible hidden confounder. "
                "EBD confidence may be overstated. RIFT may abstain on identifiability."
            )

        if not dag.has_node(service_id):
            warnings.append(
                f"Service {service_id} not in causal graph G_T. "
                "Causal ancestry cannot be verified. boundary_limited=TRUE."
            )

        # Determine confidence level
        r4_pass = False
        cid_score_data = {}

        if cid_results is not None:
            # Check R4: CID(Vᵢ → Vⱼ, t*) > θ_cid for some downstream Vⱼ
            for path_source, path_target in causal_path:
                key = f"{path_source}→{path_target}"
                if key in cid_results:
                    cid = cid_results[key]
                    w1 = getattr(cid, 'w1_estimate', None)
                    if w1 is not None and w1 > theta_cid:
                        r4_pass = True
                    cid_score_data[key] = (
                        getattr(cid, 'w1_estimate', None),
                        getattr(cid, 'w1_ci_lower', None),
                        getattr(cid, 'w1_ci_upper', None),
                        getattr(cid, 'n_post', 0),
                        getattr(cid, 'grade', 'INSUFFICIENT').value
                        if hasattr(getattr(cid, 'grade', 'INSUFFICIENT'), 'value')
                        else str(getattr(cid, 'grade', 'INSUFFICIENT')),
                    )

        if r1_pass and r2_pass and r3_pass and r4_pass:
            confidence = "DEFINITIVE"
        elif r1_pass and r2_pass and r3_pass:
            confidence = "CANDIDATE"
        else:
            confidence = "NONE"

        # boundary_limited: service not in graph or path goes outside subgraph
        boundary_limited = not dag.has_node(service_id)

        result_counter += 1
        candidates.append(EBDResult(
            result_id=f"ebd_{result_counter:04d}",
            service_id=service_id,
            variable_id=f"{service_id}.divergence",
            t_star=t_star,
            confidence=confidence,
            r1_pass=r1_pass,
            r2_pass=r2_pass,
            r3_pass=r3_pass,
            r4_pass=r4_pass,
            cid_scores=cid_score_data,
            boundary_limited=boundary_limited,
            assumption_warnings=warnings,
            identifiability_state="NOT_IDENTIFIABLE" if has_bidirected else "IDENTIFIABLE",
            intervention_record_ref=None,
            causal_path=causal_path,
            anomaly_score=anomaly_score,
            notes="Validated on synthetic ground-truth scenarios only.",
        ))

    # Sort: DEFINITIVE first, then CANDIDATE; within each tier: earliest t_star,
    # then highest anomaly score.
    # CRITICAL: temporal precedence is primary sort key. Anomaly score is secondary.
    def sort_key(r: EBDResult) -> Tuple[int, float, float]:
        tier = 0 if r.confidence == "DEFINITIVE" else (1 if r.confidence == "CANDIDATE" else 2)
        return (tier, r.t_star, -r.anomaly_score)

    candidates.sort(key=sort_key)
    return candidates
