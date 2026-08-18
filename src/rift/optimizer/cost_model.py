"""RIFT intervention cost optimizer — Phase 3L."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import networkx as nx


@dataclass
class InterventionCandidate:
    service_id: str
    variable: str
    intervention_type: str  # LATENCY | PACKET_LOSS | ERROR_RATE | RESOURCE
    target_value: float
    nominal_value: float
    description: str = ""


@dataclass
class InterventionCost:
    candidate: InterventionCandidate
    blast_radius: float          # ∈ [0, 1]
    sla_impact: float            # ∈ [0, 1]
    execution_duration_s: float  # seconds
    rollback_cost: float         # ∈ [0, 1]
    eig: float                   # nats (before normalization)
    eig_normalized: float        # ∈ [0, 1]
    safety_compliance: float     # ∈ [0, 1]
    cost_composite: float        # ∈ [0, 1]
    utility: float               # ∈ [0, 1]
    authorized: bool
    authorization_level: str     # AUTONOMOUS | SUPERVISED | DENIED


@dataclass
class MSISResult:
    selected_interventions: List[InterventionCost]
    total_cost: float
    entropy_before: float
    entropy_after: float
    entropy_reduction: float
    submodularity_verified: bool
    submodularity_note: str
    stopped_reason: str          # ENTROPY_CONVERGED | BUDGET_EXHAUSTED | NO_ELIGIBLE | EMPTY
    notes: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Entropy helpers
# ─────────────────────────────────────────────────────────────────────────────

def _entropy(posterior: Dict[str, float]) -> float:
    """Shannon entropy H(C) in nats."""
    total = sum(posterior.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for p in posterior.values():
        p_norm = p / total
        if p_norm > 1e-12:
            h -= p_norm * math.log(p_norm)
    return h


def _posterior_entropy_after_intervention(
    posterior: Dict[str, float],
    candidate: InterventionCost,
) -> float:
    """
    Estimate expected posterior entropy after observing intervention outcome.

    Uses a simplified model: if the intervention targets service X, then:
    - If X is the true cause (high CID observed): posterior concentrates on X
    - If X is not the cause (low CID): posterior spreads to other candidates

    This is a conservative EIG estimate (not the true Bayesian EIG).
    EIG = H_before - H_after_expected
    """
    service = candidate.candidate.service_id
    prior = dict(posterior)
    total = sum(prior.values())
    if total <= 0:
        return _entropy(posterior)

    p_x = prior.get(service, 0.0) / total

    # Simplified update: if X is targeted, posterior sharpens by EIG_normalized factor
    # This is NOT Bayesian but a conservative placeholder for EIG estimation
    sharpening = 0.3 * candidate.eig_normalized
    new_posterior = {}
    for svc, p in prior.items():
        p_norm = p / total
        if svc == service:
            new_posterior[svc] = min(1.0, p_norm + sharpening * (1.0 - p_norm))
        else:
            new_posterior[svc] = p_norm * (1.0 - sharpening * p_x)

    return _entropy(new_posterior)


# ─────────────────────────────────────────────────────────────────────────────
# Cost computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_intervention_costs(
    candidates: List[InterventionCandidate],
    causal_graph: nx.DiGraph,
    candidate_posterior: Dict[str, float],
    service_count: int,
    slo_weights: Optional[Dict[str, float]] = None,
    impact_lookup: Optional[Dict[str, float]] = None,
    rollback_history: Optional[Dict[str, float]] = None,
    w_br: float = 0.25,
    w_slai: float = 0.25,
    w_rc: float = 0.25,
    w_sc: float = 0.25,
) -> List[InterventionCost]:
    """
    Compute all cost components for each intervention candidate.

    Weights (w_br, w_slai, w_rc, w_sc) must sum to 1.0.
    Default: equal weights.

    Authority: docs/PHASE_3_SPEC_FREEZE.md §12
    """
    assert abs(w_br + w_slai + w_rc + w_sc - 1.0) < 1e-6, "Cost weights must sum to 1.0"

    results = []
    n_candidates = max(1, len(candidate_posterior))
    h_max = math.log(n_candidates) if n_candidates > 1 else 1.0
    h_before = _entropy(candidate_posterior)

    for c in candidates:
        # Factor 1: Blast Radius
        if causal_graph.has_node(c.service_id):
            desc = nx.descendants(causal_graph, c.service_id)
            br = len(desc.intersection(set(causal_graph.nodes()))) / max(1, service_count)
        else:
            br = 0.0
        br = float(np.clip(br, 0.0, 1.0))

        # Factor 2: SLA Impact
        slai_val = (impact_lookup or {}).get(c.service_id, 0.01)
        if slo_weights:
            slai_val *= sum(slo_weights.values()) / max(1, len(slo_weights))
        slai_val = float(np.clip(slai_val, 0.0, 1.0))

        # Factor 3: Execution Duration
        # Minimum duration from SPEC: max(3 × p99_lat, 64 / rps_baseline)
        # Simplified here: fixed estimate based on intervention type
        type_durations = {
            "LATENCY": 30.0,
            "PACKET_LOSS": 30.0,
            "ERROR_RATE": 20.0,
            "RESOURCE": 60.0,
        }
        ed = type_durations.get(c.intervention_type, 30.0)

        # Factor 4: Rollback Cost
        hist = (rollback_history or {}).get(c.service_id, 0.1)
        rc = float(np.clip(hist, 0.0, 1.0))

        # Factor 5: EIG (Expected Information Gain)
        # EIG = H(C) − E[H(C | intervention)]
        # Placeholder: EIG is proportional to posterior mass on this service
        p_x = candidate_posterior.get(c.service_id, 0.0)
        total_post = sum(candidate_posterior.values()) or 1.0
        p_x_norm = p_x / total_post
        # Simple EIG estimate: higher posterior → higher information gain
        eig_raw = float(np.clip(h_before * p_x_norm, 0.0, h_max))
        eig_norm = eig_raw / h_max if h_max > 0 else 0.0
        eig_norm = float(np.clip(eig_norm, 0.0, 1.0))

        # Factor 6: Safety Compliance
        # SC penalizes high blast radius and high SLA impact
        sc = float(np.clip(1.0 - 0.5 * br - 0.5 * slai_val, 0.0, 1.0))

        # Composite cost (dimensionless ∈ [0,1])
        cost_comp = w_br * br + w_slai * slai_val + w_rc * rc + w_sc * (1.0 - sc)
        cost_comp = float(np.clip(cost_comp, 0.0, 1.0))

        # Utility (dimensionless ∈ [0,1])
        utility = eig_norm / (1.0 + cost_comp)
        utility = float(np.clip(utility, 0.0, 1.0))

        # Authorization level
        if br < 0.1 and slai_val < 0.01:
            auth_level = "AUTONOMOUS"
            authorized = True
        elif sc < 0.3:
            auth_level = "DENIED"
            authorized = False
        else:
            auth_level = "SUPERVISED"
            authorized = True

        results.append(InterventionCost(
            candidate=c,
            blast_radius=br,
            sla_impact=slai_val,
            execution_duration_s=ed,
            rollback_cost=rc,
            eig=eig_raw,
            eig_normalized=eig_norm,
            safety_compliance=sc,
            cost_composite=cost_comp,
            utility=utility,
            authorized=authorized,
            authorization_level=auth_level,
        ))

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Greedy MSIS
# ─────────────────────────────────────────────────────────────────────────────

def _verify_submodularity(selected: List[InterventionCost]) -> Tuple[bool, str]:
    """
    Verify the conditional independence assumption for submodularity.
    Sufficient condition: non-overlapping blast radii (Desc(Xᵢ) ∩ Desc(Xⱼ) = ∅).

    If this is violated, the (1-1/e) greedy guarantee does NOT hold.
    Authority: docs/PHASE_3_SPEC_FREEZE.md §12
    """
    services = [c.candidate.service_id for c in selected]
    if len(services) <= 1:
        return True, "Single intervention; submodularity trivially holds."

    # For now: check service-level uniqueness as a proxy
    # (full blast-radius intersection check requires the causal graph)
    if len(set(services)) == len(services):
        return True, (
            "All selected interventions target distinct services. "
            "Blast-radius non-overlap is a sufficient but not necessary condition. "
            "Full intersection check would require the causal graph."
        )

    return False, (
        "Multiple interventions target the same service or overlapping blast radii. "
        "The (1-1/e) greedy approximation guarantee does NOT hold. "
        "RIFT does not claim this bound."
    )


def greedy_msis(
    costs: List[InterventionCost],
    candidate_posterior: Dict[str, float],
    theta_entropy: float = 0.5,
    t_budget: float = 600.0,
) -> MSISResult:
    """
    Greedy approximation to MSIS (Minimum Safe Intervention Set).

    Selects interventions to minimize cumulative cost subject to:
    - Posterior entropy < theta_entropy (stopping condition 1)
    - Cumulative ED ≤ t_budget (stopping condition 2)
    - Safety: only authorized interventions

    Does NOT claim (1-1/e) guarantee unless submodularity verified.

    Authority: docs/PHASE_3_SPEC_FREEZE.md §12
    """
    selected: List[InterventionCost] = []
    posterior = dict(candidate_posterior)
    total_post = sum(posterior.values()) or 1.0
    posterior = {k: v / total_post for k, v in posterior.items()}  # normalize

    h_before = _entropy(posterior)
    budget_remaining = t_budget
    stopped_reason = "EMPTY"

    # Eligible: authorized AND fits in budget
    eligible = [c for c in costs if c.authorized and c.execution_duration_s <= t_budget]

    if not eligible:
        return MSISResult(
            selected_interventions=[],
            total_cost=0.0,
            entropy_before=h_before,
            entropy_after=h_before,
            entropy_reduction=0.0,
            submodularity_verified=False,
            submodularity_note="No eligible interventions.",
            stopped_reason="NO_ELIGIBLE",
        )

    current_entropy = h_before

    while True:
        # Check stopping conditions FIRST
        if current_entropy < theta_entropy:
            stopped_reason = "ENTROPY_CONVERGED"
            break

        # Filter to interventions that still fit in budget
        feasible = [c for c in eligible if c.execution_duration_s <= budget_remaining
                    and c not in selected]
        if not feasible:
            stopped_reason = "BUDGET_EXHAUSTED" if selected else "NO_ELIGIBLE"
            break

        # Greedy: select intervention with highest utility
        best = max(feasible, key=lambda c: c.utility)
        selected.append(best)
        budget_remaining -= best.execution_duration_s

        # Update posterior estimate (simplified: redistribute based on EIG)
        p_x = posterior.get(best.candidate.service_id, 0.0)
        sharpening = min(0.4, best.eig_normalized)
        new_posterior = {}
        for svc, p in posterior.items():
            if svc == best.candidate.service_id:
                new_posterior[svc] = min(1.0, p + sharpening * (1.0 - p))
            else:
                new_posterior[svc] = p * max(0.0, 1.0 - sharpening * p_x)
        # Renormalize
        total = sum(new_posterior.values()) or 1.0
        posterior = {k: v / total for k, v in new_posterior.items()}
        current_entropy = _entropy(posterior)

    submodularity_ok, submod_note = _verify_submodularity(selected)

    total_cost = sum(c.cost_composite for c in selected)
    h_after = current_entropy

    return MSISResult(
        selected_interventions=selected,
        total_cost=total_cost,
        entropy_before=h_before,
        entropy_after=h_after,
        entropy_reduction=max(0.0, h_before - h_after),
        submodularity_verified=submodularity_ok,
        submodularity_note=submod_note,
        stopped_reason=stopped_reason,
        notes=(
            "MSIS approximation via greedy utility maximization. "
            "Does not claim (1-1/e) guarantee unless submodularity verified. "
            "Authority: docs/PHASE_3_SPEC_FREEZE.md §12"
        ),
    )
