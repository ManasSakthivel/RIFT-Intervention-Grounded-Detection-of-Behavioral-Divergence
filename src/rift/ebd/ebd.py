"""RIFT EBD — Earliest Behavioral Divergence — Phase 3K."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import networkx as nx

from src.rift.fci.fci_runner import PAGResult, PAGEdgeType
from src.rift.cid.evidence import CIDEvidenceStore, grade_name, validate_cid_for_r4


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
    # Sprint 4.2.3: evidence provenance.
    #   causal_path_kind: "DIRECTED" (every path edge oriented i->j in the PAG),
    #   "SEMI_DIRECTED" (at least one edge is o-> / o-o / --, i.e. orientation not
    #   established; reachability only), or "NONE".
    #   evidence_type: "INTERVENTIONAL" only when R4 passed, otherwise "OBSERVATIONAL".
    causal_path_kind: str = "NONE"
    evidence_type: str = "OBSERVATIONAL"


# ─────────────────────────────────────────────────────────────────────────────
# Helper: build causal graph from PAG (directed edges only)
# ─────────────────────────────────────────────────────────────────────────────

def _pag_to_digraph(pag: PAGResult, allow_semi_directed: bool = True) -> nx.DiGraph:
    """Build directed reachability graph from PAG (directed + semi-directed paths)."""
    G = nx.DiGraph()
    for v in pag.variables:
        G.add_node(v)
    for e in pag.edges:
        if e.edge_type.value == "DIRECTED":
            G.add_edge(e.source, e.target)
        elif allow_semi_directed:
            if e.edge_type.value == "PARTIALLY_DIRECTED":
                # source o-> target: target cannot be ancestor of source
                G.add_edge(e.source, e.target)
            elif e.edge_type.value in ("UNDIRECTED", "TAIL_TAIL"):
                # source o-o target: both directions admissible in semi-directed reachability
                G.add_edge(e.source, e.target)
                G.add_edge(e.target, e.source)
    return G


def _path_kind(path: List[Tuple[str, str]], pag: PAGResult) -> str:
    """Classify a reachability path: DIRECTED only if every hop is an oriented i -> j PAG edge."""
    if not path:
        return "NONE"
    directed = {(e.source, e.target) for e in pag.edges if e.edge_type.value == "DIRECTED"}
    return "DIRECTED" if all(hop in directed for hop in path) else "SEMI_DIRECTED"


def _cid_supports_r4(cid: Any, theta_cid: float) -> bool:
    """
    R4 evidence gate. Strict as of Sprint 4.2.4 (see ``rift.cid.evidence.validate_cid_for_r4``):
    finite W1 > theta_cid, grade in {CANDIDATE, RELIABLE}, permutation_significant is True and
    exceeds_threshold is True. Absent attributes are NOT treated as passing.
    """
    return validate_cid_for_r4(cid, theta_cid)[0]


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
    direction: str = "both",
    max_gap_windows: int = 0,
) -> Tuple[bool, float, float]:
    """
    R1: Δᵢₖ(t) > θ_detect for some k, persisting ≥ 2Δt.
    Returns (passes, t_star, anomaly_score).
    t_star = first time window where persistent divergence begins.

    direction:
        "both"     (default, historical behaviour) |z| > θ_detect
        "increase" z > θ_detect only (latency-degradation semantics)
        "decrease" z < -θ_detect only
    max_gap_windows:
        Number of consecutive *missing* telemetry windows tolerated inside a
        persistence run (default 0 = historical strict behaviour). An observed,
        non-exceeding window always terminates a run; only absent samples are bridged.
    anomaly_score is the maximum |z| from t_star onward (not over the whole window).
    """
    if baseline_std <= 0 or metrics.empty:
        return False, float('inf'), 0.0

    z = (metrics['value'] - baseline_mean) / baseline_std
    if direction == "increase":
        exceeds = z > theta_detect
    elif direction == "decrease":
        exceeds = z < -theta_detect
    elif direction == "both":
        exceeds = z.abs() > theta_detect
    else:
        raise ValueError(f"direction must be 'both'|'increase'|'decrease', got {direction!r}")

    per_t = (
        pd.DataFrame({'time': metrics['time'].values,
                      'ex': exceeds.values,
                      'absz': z.abs().values})
        .groupby('time', sort=True)
        .agg(ex=('ex', 'any'), absz=('absz', 'max'))
    )
    times = per_t.index.to_numpy(dtype=float)
    ex = per_t['ex'].to_numpy()
    absz = per_t['absz'].to_numpy()

    max_step = delta_t * (1 + max(0, max_gap_windows)) + delta_t * 0.1
    run_start_idx = -1
    run_len = 0
    prev_t = None
    for idx, (t, e) in enumerate(zip(times, ex)):
        if not e:
            run_len = 0
            prev_t = None
            continue
        if run_len > 0 and prev_t is not None and (t - prev_t) <= max_step:
            run_len += 1
        else:
            run_start_idx = idx
            run_len = 1
        prev_t = t
        if run_len >= theta_persist_windows:
            score = float(absz[run_start_idx:].max())
            return True, float(times[run_start_idx]), score

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
    cid_results: Optional[Any] = None,
    delta_t: float = 10.0,
    theta_detect: float = 3.0,
    theta_persist: int = 2,
    theta_cid: float = 0.1,
    direction: str = "both",
    max_gap_windows: int = 0,
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
    cid_store = CIDEvidenceStore.from_mapping(cid_results) if cid_results is not None else None

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
            incident_df, b_mean, b_std, theta_detect, theta_persist, delta_t, t_start,
            direction=direction, max_gap_windows=max_gap_windows,
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

        # NOTE (Sprint 4.2.3): a previous "tie-resolution" block here could flip a
        # strict-earlier R2 failure to True when the service was a graph ancestor of
        # the earlier service. _check_r2 already passes ties (same window), so that
        # block was reachable ONLY for strictly-earlier divergences and silently
        # overrode R2. Removed; strict precedence now stands.

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

        r4_reasons: Dict[str, str] = {}
        if cid_store is not None and r3_pass:
            # R4: CID(Vi -> Vj) must be an INTERVENTION on Vi (the candidate itself) observed on
            # some Vj in its causal path. Evidence for do(Vk), k != i, does not confirm Vi.
            outcomes = sorted({n for edge in causal_path for n in edge} - {service_id})
            for outcome in outcomes:
                cid = cid_store.get(service_id, outcome)
                if cid is None:
                    continue
                ok, reason = validate_cid_for_r4(cid, theta_cid)
                key = f"{service_id}\u2192{outcome}"
                r4_reasons[key] = reason
                if ok:
                    r4_pass = True
                cid_score_data[key] = (
                    getattr(cid, 'w1_estimate', None),
                    getattr(cid, 'w1_ci_lower', None),
                    getattr(cid, 'w1_ci_upper', None),
                    getattr(cid, 'n_post', 0),
                    grade_name(cid) or "INSUFFICIENT",
                )
            if cid_store.rejected:
                warnings.append(
                    "CID evidence rejected at boundary: "
                    + "; ".join(f"{k} ({r})" for k, r in cid_store.rejected)
                )
            if not r4_pass and r4_reasons:
                warnings.append("R4 not satisfied: " + "; ".join(f"{k}: {r}" for k, r in r4_reasons.items()))

        path_kind = _path_kind(causal_path, pag_result) if r3_pass else "NONE"
        if r3_pass and path_kind == "SEMI_DIRECTED":
            warnings.append(
                f"Causal path for {service_id} includes non-oriented PAG edges "
                "(o->, o-o or undirected). This is semi-directed reachability, "
                "not established causal ancestry."
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
            causal_path_kind=path_kind,
            evidence_type="INTERVENTIONAL" if r4_pass else "OBSERVATIONAL",
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
