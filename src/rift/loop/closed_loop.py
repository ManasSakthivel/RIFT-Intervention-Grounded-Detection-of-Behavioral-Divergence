"""RIFT closed-loop state machine — Phase 3M."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
from scipy.stats import beta as beta_dist


class RIFTState(str, Enum):
    OBSERVE = "OBSERVE"
    DISCOVER = "DISCOVER"
    IDENTIFY = "IDENTIFY"
    SELECT = "SELECT"
    INTERVENE = "INTERVENE"
    VERIFY = "VERIFY"
    UPDATE = "UPDATE"
    STOP = "STOP"
    SAFE_ABORT = "SAFE_ABORT"


@dataclass
class ClosedLoopState:
    """Full state of the RIFT closed-loop at a given iteration."""
    current_state: RIFTState
    causal_graph: nx.DiGraph
    edge_confidences: Dict[Tuple[str, str], float]
    candidate_posterior: Dict[str, float]  # P(C = service_i)
    intervention_history: List[Any] = field(default_factory=list)
    cumulative_ed: float = 0.0
    budget_remaining: float = 600.0
    iteration: int = 0
    stop_reason: Optional[str] = None
    structure_changed: bool = False  # True when graph structure changed in last UPDATE
    notes: str = ""


def _entropy(posterior: Dict[str, float]) -> float:
    total = sum(posterior.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for p in posterior.values():
        pn = p / total
        if pn > 1e-12:
            h -= pn * math.log(pn)
    return h


def _clip(v: float, lo: float = 0.05, hi: float = 0.95) -> float:
    return max(lo, min(hi, v))


class ClosedLoop:
    """
    RIFT closed-loop intervention engine.

    Implements the OBSERVE→DISCOVER→IDENTIFY→SELECT→INTERVENE→VERIFY→UPDATE→STOP cycle.

    The closed-loop is the architectural novelty: each intervention outcome updates
    the causal model, which guides the next intervention selection.
    This is NOT equivalent to running observational RCA first and then adding random
    interventions — the online model update from intervention feedback is required.

    Authority: docs/PHASE_3_SPEC_FREEZE.md §13
    """

    # ── Edge confidence update parameters (frozen in spec; docs/PHASE_3_SPEC_FREEZE.md §13) ──
    ALPHA_CONFIRM = 0.2   # fractional increase when CID confirms edge
    ALPHA_WEAKEN  = 0.1   # fractional decrease when CID refutes edge
    CONF_MIN = 0.05       # minimum edge confidence (clipping floor)
    CONF_MAX = 0.95       # maximum edge confidence (clipping ceiling)

    # ── Bayesian likelihood parameters — PROVENANCE (P1-12 fix) ──────────────────────────────
    #
    # A_POS=3, B_POS=1 → Beta(3,1): right-skewed, mode=1.0, mean=0.75.
    #   Interpretation: if a service IS the root cause, its CID score tends to be HIGH.
    #   The Beta(3,1) prior reflects strong prior belief that causal interventions
    #   produce high Wasserstein divergence (CID ≈ 1.0).
    #
    # A_NEG=1, B_NEG=3 → Beta(1,3): left-skewed, mode=0.0, mean=0.25.
    #   Interpretation: if a service is NOT the root cause, CID tends to be LOW.
    #   The Beta(1,3) prior reflects strong prior belief that non-causal interventions
    #   produce low Wasserstein divergence (CID ≈ 0.0).
    #
    # These are CONJUGATE priors for Bayesian updates with Beta-distributed likelihoods.
    # Values were set by PRIOR CAUSAL REASONING (not tuned on development data):
    #   - Causal interventions on the root cause should produce measurable distributional
    #     shift in downstream metrics (W₁ >> 0), hence high CID scores.
    #   - Interventions on innocent services should not produce downstream shift (W₁ ≈ 0).
    #   - A_POS/B_POS and A_NEG/B_NEG are symmetric reflections of each other.
    # SENSITIVITY: results are stable within ±50% variation of these parameters
    #   (see docs/causal_assumptions.md A9 and analysis/bayesian_sensitivity.md).
    # TUNING POLICY: These values were set BEFORE any evaluation data was seen.
    #   They must NOT be re-tuned based on development set results to avoid
    #   invalidating the H3 ablation comparison.
    A_POS, B_POS = 3.0, 1.0  # likelihood for causal service: Beta(3,1)
    A_NEG, B_NEG = 1.0, 3.0  # likelihood for non-causal service: Beta(1,3)

    # ── Stopping parameters ────────────────────────────────────────────────────────────────
    THETA_STOP_ENTROPY = 0.5  # nats — stop when posterior entropy < 0.5

    def posterior_entropy(self, state: ClosedLoopState) -> float:
        return _entropy(state.candidate_posterior)

    def check_stopping(self, state: ClosedLoopState) -> Tuple[bool, str]:
        """
        Check all four stopping conditions.
        Returns (should_stop, reason).
        """
        # Condition 2: Budget exhausted (check FIRST — hard safety limit)
        if state.cumulative_ed >= _T_BUDGET or state.budget_remaining <= 0.0:
            return True, "BUDGET_EXHAUSTED"

        # Condition 3: Safety abort
        if state.current_state == RIFTState.SAFE_ABORT:
            return True, "SAFETY_ABORT"

        # Condition 4: All candidates non-identifiable (degenerate posterior)
        if state.candidate_posterior and all(
            p == 0.0 for p in state.candidate_posterior.values()
        ):
            return True, "ALL_CANDIDATES_NON_IDENTIFIABLE"

        # Condition 1: Entropy convergence
        # Only triggers if at least 2 candidates have non-zero posterior
        # (a single non-zero candidate with all others at 0 is not genuine convergence —
        # it may be a degenerate prior initialization)
        nonzero_count = sum(1 for p in state.candidate_posterior.values() if p > 0.0)
        h = self.posterior_entropy(state)
        if h < self.THETA_STOP_ENTROPY and nonzero_count >= 2:
            return True, "ENTROPY_CONVERGED"

        return False, ""

    def update_edge_confidence(
        self,
        state: ClosedLoopState,
        source: str,
        target: str,
        cid_value: float,
        theta_cid: float = 0.1,
    ) -> ClosedLoopState:
        """
        Component 1: Update edge confidence from CID result.

        If CID > θ_cid: strengthen source→target edge, weaken competing edges to target.
        If CID ≤ θ_cid: weaken source→target edge.

        Authority: docs/PHASE_3_SPEC_FREEZE.md §13 Component 1
        """
        key = (source, target)
        current = state.edge_confidences.get(key, 0.5)

        # Accept CIDResult object or raw float
        if hasattr(cid_value, 'exceeds_threshold'):
            exceeds = bool(cid_value.exceeds_threshold)
        else:
            exceeds = float(cid_value) > theta_cid

        if exceeds:
            new_conf = _clip(current * (1.0 + self.ALPHA_CONFIRM))
            state.edge_confidences[key] = new_conf
            # Weaken competing edges to target
            for (s, t), conf in list(state.edge_confidences.items()):
                if t == target and s != source:
                    state.edge_confidences[(s, t)] = _clip(conf * (1.0 - self.ALPHA_WEAKEN))
        else:
            state.edge_confidences[key] = _clip(current * (1.0 - self.ALPHA_WEAKEN))

        return state

    def update_candidate_posterior(
        self,
        state: ClosedLoopState,
        service: str,
        cid_value: float,
    ) -> ClosedLoopState:
        """
        Component 2: Bayesian update of root-cause posterior.

        Likelihood:
          P(cid | C=service) ~ Beta(cid; a_pos, b_pos)  [true cause → high CID]
          P(cid | C≠service) ~ Beta(cid; a_neg, b_neg)  [non-cause → low CID]

        Authority: docs/PHASE_3_SPEC_FREEZE.md §13 Component 2
        """
        # Accept CIDResult object or raw float
        if hasattr(cid_value, 'value'):
            raw_cid = float(cid_value.value)
            theta = float(getattr(cid_value, 'theta_cid', 0.05))
            # Normalize to [0,1] using 2×theta as scale
            raw_cid = raw_cid / (2.0 * theta) if theta > 0 else raw_cid
        else:
            raw_cid = float(cid_value)
        # Clip CID to (0,1) for Beta PDF evaluation
        c = float(np.clip(raw_cid, 1e-6, 1.0 - 1e-6))

        new_posterior = {}
        for svc, prior_p in state.candidate_posterior.items():
            if svc == service:
                # Likelihood under "true cause"
                likelihood = beta_dist.pdf(c, self.A_POS, self.B_POS)
            else:
                # Likelihood under "not the cause"
                likelihood = beta_dist.pdf(c, self.A_NEG, self.B_NEG)
            new_posterior[svc] = prior_p * max(1e-12, likelihood)

        # Renormalize
        total = sum(new_posterior.values())
        if total > 0:
            new_posterior = {k: v / total for k, v in new_posterior.items()}
        state.candidate_posterior = new_posterior
        return state

    def update_graph_structure(
        self,
        state: ClosedLoopState,
        source: str,
        target: str,
        cid_value: float,
        theta_cid: float = 0.1,
        theta_remove: float = 0.3,
    ) -> ClosedLoopState:
        """
        Component 3: Threshold-gated graph structure update.

        Add edge: CID > θ_cid AND no directed path X→⋯→Y in G_T
        Remove edge: CID ≤ θ_cid AND conf < threshold → remove

        Authority: docs/PHASE_3_SPEC_FREEZE.md §13 Component 3
        """
        G = state.causal_graph

        # Accept CIDResult object or raw float
        if hasattr(cid_value, 'exceeds_threshold'):
            exceeds = bool(cid_value.exceeds_threshold)
        else:
            exceeds = float(cid_value) > theta_cid

        if exceeds:
            # Check if path already exists
            if not (G.has_node(source) and G.has_node(target) and
                    nx.has_path(G, source, target)):
                # Add edge with moderate initial confidence
                G.add_edge(source, target, confidence=0.5, inferred_by="INTERVENTION")
                state.edge_confidences[(source, target)] = 0.5
                state.structure_changed = True
                if state.notes:
                    state.notes += f"; INTERVENTION_INFERRED edge {source}→{target}"
                else:
                    state.notes = f"INTERVENTION_INFERRED edge {source}→{target}"
        else:
            # Potentially remove edge if confidence is low
            if G.has_edge(source, target):
                conf = state.edge_confidences.get((source, target), 0.5)
                if conf < theta_remove:
                    G.remove_edge(source, target)
                    state.edge_confidences.pop((source, target), None)
                    state.structure_changed = True
                    if state.notes:
                        state.notes += f"; INTERVENTION_REFUTED edge {source}→{target}"
                    else:
                        state.notes = f"INTERVENTION_REFUTED edge {source}→{target}"

        state.causal_graph = G
        return state

    def step(
        self,
        state: ClosedLoopState,
        new_evidence: Optional[Dict[str, Any]] = None,
    ) -> ClosedLoopState:
        """
        Advance one step in the RIFT state machine.

        State transitions:
        OBSERVE → DISCOVER → IDENTIFY → SELECT → INTERVENE → VERIFY → UPDATE → STOP/NEXT

        new_evidence keys:
          abort: True → immediate SAFE_ABORT from any non-terminal state
          VERIFY/UPDATE state: {'source': str, 'target': str,
                                'cid_result': CIDResult or float,
                                'cid_value': float (alias),
                                'service': str,
                                'ed': float,
                                'ed_s': float (alias)}
        """
        evidence = new_evidence or {}
        current = state.current_state

        # Terminal states: no transitions (including abort)
        if current == RIFTState.STOP:
            return state  # STOP is truly terminal — even abort cannot change it
        if current == RIFTState.SAFE_ABORT:
            return state

        # Safety abort injection from any non-terminal state
        if evidence.get("abort", False):
            state.current_state = RIFTState.SAFE_ABORT
            state.stop_reason = "SAFETY_ABORT"
            return state

        if current == RIFTState.OBSERVE:
            state.current_state = RIFTState.DISCOVER

        elif current == RIFTState.DISCOVER:
            state.current_state = RIFTState.IDENTIFY

        elif current == RIFTState.IDENTIFY:
            state.current_state = RIFTState.SELECT

        elif current == RIFTState.SELECT:
            should_stop, reason = self.check_stopping(state)
            if should_stop:
                state.current_state = RIFTState.STOP
                state.stop_reason = reason
            else:
                state.current_state = RIFTState.INTERVENE

        elif current == RIFTState.INTERVENE:
            state.current_state = RIFTState.VERIFY

        elif current == RIFTState.VERIFY:
            state.current_state = RIFTState.UPDATE

        elif current == RIFTState.UPDATE:
            # Process evidence for the four update components
            source = evidence.get('source', '')
            target = evidence.get('target', '')
            cid_raw = evidence.get('cid_result', evidence.get('cid_value', 0.0))
            service = evidence.get('service', source)
            ed = float(evidence.get('ed', evidence.get('ed_s', 0.0)))

            # Accumulate execution duration
            state.cumulative_ed += ed
            state.budget_remaining = max(0.0, state.budget_remaining - ed)

            if source and target and cid_raw is not None:
                old_edges = dict(state.causal_graph.edges())
                state = self.update_edge_confidence(state, source, target, cid_raw)
                state = self.update_graph_structure(state, source, target, cid_raw)
                new_edges = dict(state.causal_graph.edges())
                state.structure_changed = (old_edges != new_edges)

            if service and cid_raw is not None:
                state = self.update_candidate_posterior(state, service, cid_raw)

            state.iteration += 1

            # Post-update stopping check
            should_stop, reason = self.check_stopping(state)
            if should_stop:
                state.current_state = RIFTState.STOP
                state.stop_reason = reason
            else:
                state.current_state = RIFTState.OBSERVE  # loop back to OBSERVE

        return state

    def run_to_completion(
        self,
        state: ClosedLoopState,
        evidence_sequence: List[Optional[Dict[str, Any]]],
        max_iterations: int = 50,
    ) -> ClosedLoopState:
        """
        Run the state machine to completion using a pre-defined evidence sequence.
        Used for testing and simulation.
        """
        ev_iter = iter(evidence_sequence)
        for _ in range(max_iterations * 8):  # 8 = max steps per iteration
            if state.current_state in (RIFTState.STOP, RIFTState.SAFE_ABORT):
                break
            evidence = None
            if state.current_state == RIFTState.VERIFY:
                evidence = next(ev_iter, None)
            state = self.step(state, new_evidence=evidence)
        return state

# ─────────────────────────────────────────────────────────────────────────────
# Compatibility shims for test_closed_loop.py (imports legacy names)
# ─────────────────────────────────────────────────────────────────────────────

# These are the frozen hyperparameter values from the spec.
# Tests import them as module-level constants.
_ALPHA_CONFIRM = 0.2
_ALPHA_WEAKEN = 0.1
_CONF_MIN = 0.05
_CONF_MAX = 0.95
_CONF_NEW_EDGE = 0.5
_CONF_REMOVE_THRESHOLD = 0.3
_T_BUDGET = 600.0
_THETA_STOP = 0.5


def _clip(value: float) -> float:
    """Clip a confidence score to [_CONF_MIN, _CONF_MAX]."""
    return max(_CONF_MIN, min(_CONF_MAX, float(value)))


@dataclass
class CIDResult:
    """
    Lightweight CID result carrier for closed-loop tests.
    value: W₁ (Wasserstein) CID score
    theta_cid: attribution threshold
    status: VALID | CONFOUNDED | INVALID | INSUFFICIENT_SAMPLES | NOT_IDENTIFIABLE
    """
    value: float
    theta_cid: float
    status: str = "VALID"

    @property
    def exceeds_threshold(self) -> bool:
        return self.value > self.theta_cid

