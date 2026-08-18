"""
RIFT — Time-Sliced Structural Causal Model
Phase 3B | Authority: docs/PHASE_3_SPEC_FREEZE.md §1 and §2

SCM M = ⟨ U, V, F, P(U) ⟩

  V = finite set of observable endogenous variables (time-sliced)
  U = unobserved exogenous noise + latent common causes
  F = {fᵢ : PA(Vᵢ) × Uᵢ → Vᵢ}  — structural equations (NOT assumed linear)
  P(U) = joint distribution over exogenous noise

Feedback loops: represented as temporal edges X[t] → Y[t+1], never as
static cycles. Acyclicity is GUARANTEED BY CONSTRUCTION in the time-sliced
representation, but is verified explicitly.

IMPORTANT: This SCM is INTERVENTION-CONSISTENT, not "causally accurate".
It represents a model consistent with observed interventions on synthetic
ground-truth scenarios. Not validated for real distributed systems.

Queueing approximation: M/M/1.
  E[queue_depth] = ρ/(1−ρ),  ρ = arrival_rate / service_rate
  E[latency]     = 1 / (service_rate − arrival_rate)
The M/M/1 assumption WILL be violated by bursty traffic.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Optional

import networkx as nx
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# TimeSlicedVariable
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TimeSlicedVariable:
    """
    A single variable in a time-sliced causal model.

    Vᵢ[t] is represented as TimeSlicedVariable(name="Vi", time_index=t).
    Vᵢ[t] and Vᵢ[t+1] are DISTINCT variables.

    The unique identifier used in SCM dictionaries is ``key`` = ``name__t{time_index}``.
    Exogenous noise variables use is_observable=False.
    """

    name: str
    time_index: int  # t, t+1, t+2, …
    is_observable: bool
    service_id: Optional[str]
    description: str

    @property
    def key(self) -> str:
        """Canonical dict key: ``name__t{time_index}``."""
        return f"{self.name}__t{self.time_index}"

    def __repr__(self) -> str:
        obs = "obs" if self.is_observable else "exo"
        return f"<{self.name}[t{self.time_index}] {obs}>"


# ---------------------------------------------------------------------------
# StructuralEquation
# ---------------------------------------------------------------------------

@dataclass
class StructuralEquation:
    """
    Structural equation for one endogenous variable:

        Vᵢ = fᵢ(PA(Vᵢ), Uᵢ)

    The callable ``equation`` receives:
        - parent_values: Dict[str, float]  — key = parent.key
        - noise: float                      — single scalar exogenous noise draw

    It must return a float (the value of ``variable``).

    equation_type is a documentation tag; the implementation does NOT assume
    linearity unless type is "linear".

    assumption_notes must document any linearity, M/M/1, or other approximation
    assumptions that affect the validity of downstream causal inference.
    """

    variable: TimeSlicedVariable
    parents: List[TimeSlicedVariable]
    equation: Callable[[Dict[str, float], float], float]
    equation_type: Literal["linear", "nonlinear", "queueing_mm1", "custom"]
    assumption_notes: str


# ---------------------------------------------------------------------------
# SCM
# ---------------------------------------------------------------------------

class SCM:
    """
    Structural Causal Model M = ⟨U, V, F, P(U)⟩

    V = observable endogenous variables (time-sliced)
    U = exogenous noise variables
    F = structural equations

    IMPORTANT: This SCM is INTERVENTION-CONSISTENT, not "causally accurate".
    It represents a model that is consistent with observed interventions on
    synthetic ground-truth scenarios.
    """

    def __init__(
        self,
        endogenous: Dict[str, TimeSlicedVariable],
        exogenous: Dict[str, TimeSlicedVariable],
        equations: Dict[str, StructuralEquation],
    ) -> None:
        """
        Parameters
        ----------
        endogenous:
            Mapping key → TimeSlicedVariable for all observable V variables.
            key must match var.key.
        exogenous:
            Mapping key → TimeSlicedVariable for all noise U variables.
        equations:
            Mapping key → StructuralEquation for each endogenous variable.
            key must match the variable's .key attribute.
        """
        self.endogenous = endogenous
        self.exogenous = exogenous
        self.equations = equations
        self._validate_keys()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_keys(self) -> None:
        for k, v in self.endogenous.items():
            if k != v.key:
                raise ValueError(
                    f"endogenous key mismatch: dict key '{k}' ≠ var.key '{v.key}'"
                )
        for k, v in self.exogenous.items():
            if k != v.key:
                raise ValueError(
                    f"exogenous key mismatch: dict key '{k}' ≠ var.key '{v.key}'"
                )
        for k, eq in self.equations.items():
            if k != eq.variable.key:
                raise ValueError(
                    f"equation key mismatch: dict key '{k}' ≠ eq.variable.key '{eq.variable.key}'"
                )
            if k not in self.endogenous:
                raise ValueError(
                    f"equation '{k}' references variable not in endogenous set"
                )

    # ------------------------------------------------------------------
    # Graph utilities
    # ------------------------------------------------------------------

    def _build_static_dag(self) -> nx.DiGraph:
        """
        Build a static directed graph over *base names* (ignoring time index).

        Used for acyclicity checking.  Time-sliced variables with the same
        base name but different time indices are collapsed to a single node,
        so a temporal edge X[t] → X[t+1] becomes a self-loop X→X, which we
        treat as a cycle ONLY if it is a within-timestep dependency.

        Concretely: we build the graph over (name, time_index) pairs.  A
        cycle only exists if there is a directed path from (name, t) back to
        (name, t) with no time-index increase — i.e., a true static cycle.

        The canonical approach for time-sliced SCMs: build graph on the full
        (name, time_index) key and check for directed cycles.  Temporal edges
        t → t+1 form a DAG naturally.  Only cycles that stay within the same
        time slice are forbidden.
        """
        G = nx.DiGraph()
        for key, eq in self.equations.items():
            G.add_node(key)
            for parent in eq.parents:
                # exogenous parents are not in the endogenous graph
                if parent.key in self.endogenous:
                    G.add_edge(parent.key, key)
        return G

    def is_acyclic(self) -> bool:
        """
        Verify no cycles exist in the static graph projection.

        Returns True if and only if the directed graph over all endogenous
        (name, time_index) variable keys is acyclic.

        A correctly constructed time-sliced SCM (where feedback only crosses
        time boundaries) will always pass this check.  Any cycle here
        represents a modelling error.
        """
        G = self._build_static_dag()
        return nx.is_directed_acyclic_graph(G)

    def _topological_order(self) -> List[str]:
        """Return endogenous variable keys in topological order."""
        G = self._build_static_dag()
        if not nx.is_directed_acyclic_graph(G):
            raise ValueError(
                "SCM contains a cycle — sampling is undefined. "
                "Verify that feedback loops cross time boundaries."
            )
        return list(nx.topological_sort(G))

    def edges(self) -> List[tuple[str, str]]:
        """
        Return list of directed edges (parent_key, child_key) over endogenous
        variables only.
        """
        result = []
        for key, eq in self.equations.items():
            for parent in eq.parents:
                if parent.key in self.endogenous:
                    result.append((parent.key, key))
        return result

    # ------------------------------------------------------------------
    # do-operator / mutilation
    # ------------------------------------------------------------------

    def mutilate(self, interventions: Dict[str, float]) -> "SCM":
        """
        Apply do(X := x) for each intervention.

        Returns a new SCM with:
        - All incoming edges to each intervened variable removed (mutilated graph).
        - Each intervened variable's equation replaced with a constant: X := x.

        This implements the formal do-operator (Pearl 2009, Definition 3.1.1).

        Parameters
        ----------
        interventions:
            Dict mapping variable key (e.g. ``"X__t0"``) to its forced value.

        Returns
        -------
        SCM
            A new SCM object.  The original SCM is not modified.
        """
        new_equations: Dict[str, StructuralEquation] = {}

        for key, eq in self.equations.items():
            if key in interventions:
                forced_value = interventions[key]
                # Replace equation with constant; remove all parents.
                new_eq = StructuralEquation(
                    variable=eq.variable,
                    parents=[],  # incoming edges removed
                    equation=lambda pv, noise, v=forced_value: v,
                    equation_type="custom",
                    assumption_notes=(
                        f"do-operator: variable set to constant {forced_value}. "
                        "All incoming edges removed (mutilated graph)."
                    ),
                )
            else:
                new_eq = copy.copy(eq)
            new_equations[key] = new_eq

        return SCM(
            endogenous=dict(self.endogenous),
            exogenous=dict(self.exogenous),
            equations=new_equations,
        )

    # ------------------------------------------------------------------
    # Sampling
    # ------------------------------------------------------------------

    def _sample_once(self, rng: np.random.Generator) -> Dict[str, float]:
        """
        Draw one sample from P(V) by evaluating structural equations in
        topological order.

        Exogenous noise is drawn as U ~ N(0, 1) for each equation
        (independent, unit-variance Gaussian).
        """
        order = self._topological_order()
        values: Dict[str, float] = {}

        for key in order:
            eq = self.equations[key]
            # Build parent value dict
            parent_values: Dict[str, float] = {}
            for parent in eq.parents:
                if parent.key in values:
                    parent_values[parent.key] = values[parent.key]
                elif parent.key in self.exogenous:
                    # Exogenous parents that are not yet drawn: draw N(0,1)
                    parent_values[parent.key] = float(rng.standard_normal())
                else:
                    raise ValueError(
                        f"Parent '{parent.key}' of '{key}' has no value. "
                        "Check topological ordering or variable registration."
                    )
            # Draw this variable's own noise term
            noise = float(rng.standard_normal())
            values[key] = float(eq.equation(parent_values, noise))

        return values

    def sample(
        self,
        n: int,
        seed: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Sample n observations from the observational distribution P(V).

        Parameters
        ----------
        n:    Number of samples.
        seed: Optional integer seed for reproducibility.

        Returns
        -------
        pd.DataFrame with one column per endogenous variable (key as column name).
        """
        rng = np.random.default_rng(seed)
        rows = [self._sample_once(rng) for _ in range(n)]
        df = pd.DataFrame(rows)
        # Return only endogenous variable columns in topological order
        topo_cols = [k for k in self._topological_order() if k in df.columns]
        extra_cols = [c for c in df.columns if c not in topo_cols]
        return df[topo_cols + extra_cols]

    def sample_interventional(
        self,
        interventions: Dict[str, float],
        n: int,
        seed: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Sample n observations from P(V | do(X := x)) for given interventions.

        Applies the do-operator (mutilates the SCM) then samples from the
        resulting mutilated model.

        Parameters
        ----------
        interventions:
            Dict mapping variable key to forced value.
        n:
            Number of samples.
        seed:
            Optional integer seed for reproducibility.

        Returns
        -------
        pd.DataFrame — same schema as ``sample()``.
        """
        mutilated = self.mutilate(interventions)
        return mutilated.sample(n, seed=seed)

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"SCM("
            f"V={len(self.endogenous)}, "
            f"U={len(self.exogenous)}, "
            f"F={len(self.equations)}, "
            f"acyclic={self.is_acyclic()}"
            f")"
        )


# ---------------------------------------------------------------------------
# Helper: variable factory
# ---------------------------------------------------------------------------

def _var(
    name: str,
    t: int,
    observable: bool = True,
    service_id: Optional[str] = None,
    description: str = "",
) -> TimeSlicedVariable:
    return TimeSlicedVariable(
        name=name,
        time_index=t,
        is_observable=observable,
        service_id=service_id,
        description=description,
    )


def _noise_var(name: str, t: int, description: str = "") -> TimeSlicedVariable:
    return _var(name, t, observable=False, description=description)


# ---------------------------------------------------------------------------
# Synthetic SCM 1 — Chain
# ---------------------------------------------------------------------------

def make_chain_scm() -> SCM:
    """
    X[t0] → Y[t1] → Z[t2]. Simple linear chain across time slices.

    Ground truth:
      - X causes Y (directly).
      - Y causes Z (directly).
      - X causes Z (indirectly, mediated by Y).
      - Interventions on X shift Y and Z; interventions on Y shift Z but not X.
    """
    X = _var("X", 0, description="Root variable at t=0")
    Y = _var("Y", 1, description="Middle variable at t=1")
    Z = _var("Z", 2, description="Leaf variable at t=2")

    Ux = _noise_var("U_X", 0, "Exogenous noise for X")
    Uy = _noise_var("U_Y", 1, "Exogenous noise for Y")
    Uz = _noise_var("U_Z", 2, "Exogenous noise for Z")

    endogenous = {v.key: v for v in [X, Y, Z]}
    exogenous = {v.key: v for v in [Ux, Uy, Uz]}

    equations = {
        X.key: StructuralEquation(
            variable=X,
            parents=[],
            equation=lambda pv, noise: noise,  # X ~ N(0,1)
            equation_type="linear",
            assumption_notes="X is an exogenous root; drawn from N(0,1).",
        ),
        Y.key: StructuralEquation(
            variable=Y,
            parents=[X],
            equation=lambda pv, noise: 0.8 * pv[X.key] + 0.6 * noise,
            equation_type="linear",
            assumption_notes=(
                "Linear: Y = 0.8·X[t0] + 0.6·U_Y. "
                "Coefficient 0.8 chosen for strong but not deterministic effect."
            ),
        ),
        Z.key: StructuralEquation(
            variable=Z,
            parents=[Y],
            equation=lambda pv, noise: 0.7 * pv[Y.key] + 0.7 * noise,
            equation_type="linear",
            assumption_notes=(
                "Linear: Z = 0.7·Y[t1] + 0.7·U_Z. "
                "Residual noise coefficient 0.7 preserves unit variance approximately."
            ),
        ),
    }

    return SCM(endogenous=endogenous, exogenous=exogenous, equations=equations)


# ---------------------------------------------------------------------------
# Synthetic SCM 2 — Fork
# ---------------------------------------------------------------------------

def make_fork_scm() -> SCM:
    """
    X[t0] → Y[t1], X[t0] → Z[t1].

    X causes both Y and Z independently.

    Ground truth:
      - Y and Z are marginally correlated (both caused by X).
      - Conditioning on X renders Y ⊥ Z (no direct Y→Z edge).
      - do(X:=x) shifts both Y and Z.
      - do(Y:=y) does NOT shift Z (no X→Z path through Y).
    """
    X = _var("X", 0, description="Common cause at t=0")
    Y = _var("Y", 1, description="Effect 1 at t=1")
    Z = _var("Z", 1, description="Effect 2 at t=1")

    endogenous = {v.key: v for v in [X, Y, Z]}
    exogenous = {}

    equations = {
        X.key: StructuralEquation(
            variable=X,
            parents=[],
            equation=lambda pv, noise: noise,
            equation_type="linear",
            assumption_notes="X ~ N(0,1); root variable.",
        ),
        Y.key: StructuralEquation(
            variable=Y,
            parents=[X],
            equation=lambda pv, noise: 0.9 * pv[X.key] + 0.44 * noise,
            equation_type="linear",
            assumption_notes="Linear: Y = 0.9·X + 0.44·U_Y.  Var(Y)≈1.",
        ),
        Z.key: StructuralEquation(
            variable=Z,
            parents=[X],
            equation=lambda pv, noise: -0.7 * pv[X.key] + 0.71 * noise,
            equation_type="linear",
            assumption_notes=(
                "Linear: Z = -0.7·X + 0.71·U_Z.  "
                "Negative coefficient for testable sign of effect."
            ),
        ),
    }

    return SCM(endogenous=endogenous, exogenous=exogenous, equations=equations)


# ---------------------------------------------------------------------------
# Synthetic SCM 3 — Collider
# ---------------------------------------------------------------------------

def make_collider_scm() -> SCM:
    """
    X[t0] → Z[t1] ← Y[t0].

    Z is a collider. X and Y are independent in P(X, Y, Z) (marginally).
    Conditioning on Z induces spurious correlation between X and Y
    (Berkson's paradox / collider bias).

    Ground truth:
      - X ⊥ Y in P(X, Y, Z).
      - X ⊬⊥ Y in P(X, Y | Z=z)  — conditioning on Z opens the X-Z-Y path.
      - Intervening do(X:=x) does NOT affect Y (no causal path X→Y).
    """
    X = _var("X", 0, description="Cause 1 of collider at t=0")
    Y = _var("Y", 0, description="Cause 2 of collider at t=0")
    Z = _var("Z", 1, description="Collider at t=1; caused by both X and Y")

    endogenous = {v.key: v for v in [X, Y, Z]}
    exogenous = {}

    equations = {
        X.key: StructuralEquation(
            variable=X,
            parents=[],
            equation=lambda pv, noise: noise,
            equation_type="linear",
            assumption_notes="X ~ N(0,1); root.",
        ),
        Y.key: StructuralEquation(
            variable=Y,
            parents=[],
            equation=lambda pv, noise: noise,
            equation_type="linear",
            assumption_notes="Y ~ N(0,1); root; independent of X.",
        ),
        Z.key: StructuralEquation(
            variable=Z,
            parents=[X, Y],
            equation=lambda pv, noise: (
                0.6 * pv[X.key] + 0.6 * pv[Y.key] + 0.53 * noise
            ),
            equation_type="linear",
            assumption_notes=(
                "Linear: Z = 0.6·X + 0.6·Y + 0.53·U_Z. "
                "Z is a collider. Conditioning on Z opens the X-Z-Y path."
            ),
        ),
    }

    return SCM(endogenous=endogenous, exogenous=exogenous, equations=equations)


# ---------------------------------------------------------------------------
# Synthetic SCM 4 — Mediation
# ---------------------------------------------------------------------------

def make_mediated_scm() -> SCM:
    """
    X[t0] → M[t1] → Y[t2]. M is the sole mediator.

    Ground truth:
      - Total causal effect X→Y = 0.8 × 0.75 = 0.60.
      - Natural direct effect X→Y (bypassing M) = 0 (no direct X→Y edge).
      - do(M:=m) affects Y but breaks the X→Y effect.
    """
    X = _var("X", 0, description="Treatment / cause at t=0")
    M = _var("M", 1, description="Mediator at t=1")
    Y = _var("Y", 2, description="Outcome at t=2")

    endogenous = {v.key: v for v in [X, M, Y]}
    exogenous = {}

    equations = {
        X.key: StructuralEquation(
            variable=X,
            parents=[],
            equation=lambda pv, noise: noise,
            equation_type="linear",
            assumption_notes="X ~ N(0,1); root.",
        ),
        M.key: StructuralEquation(
            variable=M,
            parents=[X],
            equation=lambda pv, noise: 0.8 * pv[X.key] + 0.6 * noise,
            equation_type="linear",
            assumption_notes="Linear: M = 0.8·X + 0.6·U_M.",
        ),
        Y.key: StructuralEquation(
            variable=Y,
            parents=[M],
            equation=lambda pv, noise: 0.75 * pv[M.key] + 0.66 * noise,
            equation_type="linear",
            assumption_notes=(
                "Linear: Y = 0.75·M + 0.66·U_Y. "
                "Total effect X→Y ≈ 0.60 via chain rule."
            ),
        ),
    }

    return SCM(endogenous=endogenous, exogenous=exogenous, equations=equations)


# ---------------------------------------------------------------------------
# Synthetic SCM 5 — Hidden Confounder
# ---------------------------------------------------------------------------

def make_confounder_scm() -> SCM:
    """
    U (hidden) → X[t0], U → Y[t0].

    U is an unobserved common cause. X and Y are marginally correlated but
    neither causes the other.

    Ground truth:
      - P(Y | X=x) ≠ P(Y)  — X and Y are correlated.
      - P(Y | do(X:=x)) = P(Y)  — intervention on X does NOT shift Y.
      - This is the fundamental distinction: correlation ≠ causation.
    """
    # U is latent — modelled as exogenous noise injected into both X and Y.
    # We use a shared noise term by sampling U once and passing it to both.
    # Implementation: both equations share the same noise key via a pre-draw.
    #
    # Architecture: we add a "virtual" endogenous U variable at t=0 whose
    # equation draws its own noise.  X and Y then use U as a parent.
    # This lets the SCM machinery handle U correctly without special-casing.
    #
    # U is NOT observable (is_observable=False).

    U = _var("U", 0, observable=False, description="Hidden confounder at t=0")
    X = _var("X", 0, description="Observable variable correlated with Y via U")
    Y = _var("Y", 0, description="Observable variable correlated with X via U")

    endogenous = {v.key: v for v in [U, X, Y]}
    exogenous = {}

    equations = {
        U.key: StructuralEquation(
            variable=U,
            parents=[],
            equation=lambda pv, noise: noise,
            equation_type="linear",
            assumption_notes=(
                "U is the hidden confounder. U ~ N(0,1). "
                "In real inference U is not observed; here we model it explicitly "
                "for synthetic ground-truth validation only."
            ),
        ),
        X.key: StructuralEquation(
            variable=X,
            parents=[U],
            equation=lambda pv, noise: 0.8 * pv[U.key] + 0.6 * noise,
            equation_type="linear",
            assumption_notes=(
                "X = 0.8·U + 0.6·U_X. "
                "No causal path X→Y; correlation arises entirely from U."
            ),
        ),
        Y.key: StructuralEquation(
            variable=Y,
            parents=[U],
            equation=lambda pv, noise: 0.8 * pv[U.key] + 0.6 * noise,
            equation_type="linear",
            assumption_notes=(
                "Y = 0.8·U + 0.6·U_Y. "
                "Intervening on X leaves Y unchanged because X is not a cause of Y."
            ),
        ),
    }

    return SCM(endogenous=endogenous, exogenous=exogenous, equations=equations)


# ---------------------------------------------------------------------------
# Synthetic SCM 6 — Feedback (temporal)
# ---------------------------------------------------------------------------

def make_feedback_scm() -> SCM:
    """
    X[t0] → Y[t1] → X[t2]. Feedback loop represented across time slices.

    Because the loop crosses time boundaries (t0→t1→t2), the static DAG
    over time-indexed variables is acyclic.  This is the correct representation:
    X[t0] and X[t2] are DISTINCT variables.

    Ground truth:
      - X[t0] causes Y[t1] (direct).
      - Y[t1] causes X[t2] (feedback).
      - No static cycle — is_acyclic() must return True.
    """
    X0 = _var("X", 0, description="X at initial time t=0")
    Y1 = _var("Y", 1, description="Y at t=1; caused by X[t0]")
    X2 = _var("X", 2, description="X at t=2; caused by Y[t1] (feedback)")

    endogenous = {v.key: v for v in [X0, Y1, X2]}
    exogenous = {}

    equations = {
        X0.key: StructuralEquation(
            variable=X0,
            parents=[],
            equation=lambda pv, noise: noise,
            equation_type="linear",
            assumption_notes="X[t0] ~ N(0,1); initial condition.",
        ),
        Y1.key: StructuralEquation(
            variable=Y1,
            parents=[X0],
            equation=lambda pv, noise: 0.85 * pv[X0.key] + 0.53 * noise,
            equation_type="linear",
            assumption_notes=(
                "Y[t1] = 0.85·X[t0] + 0.53·U_Y. "
                "Forward path of the feedback loop."
            ),
        ),
        X2.key: StructuralEquation(
            variable=X2,
            parents=[Y1],
            equation=lambda pv, noise: 0.6 * pv[Y1.key] + 0.8 * noise,
            equation_type="linear",
            assumption_notes=(
                "X[t2] = 0.6·Y[t1] + 0.8·U_X2. "
                "Feedback path.  X[t2] ≠ X[t0]; no cycle in static DAG."
            ),
        ),
    }

    return SCM(endogenous=endogenous, exogenous=exogenous, equations=equations)


# ---------------------------------------------------------------------------
# Synthetic SCM 7 — Queueing (M/M/1)
# ---------------------------------------------------------------------------

def make_queueing_scm() -> SCM:
    """
    M/M/1 queueing dynamics:

        arrival_rate[t0], service_rate[t0]
            → queue_depth[t1]
                → latency[t1]

    Structural equations use the M/M/1 approximation:

        ρ = arrival_rate / service_rate
        E[queue_depth] = ρ / (1 − ρ)          (valid for ρ < 1)
        E[latency]     = 1 / (service_rate − arrival_rate)

    ASSUMPTIONS (must appear in paper):
    - Poisson arrivals (memoryless inter-arrival times).
    - Exponential service times.
    - Single server.
    - ρ < 1 required for stability; behaviour undefined at ρ ≥ 1.
    - This approximation is violated by bursty (non-Poisson) traffic.
    - queue_depth and latency are clipped at zero to remain physical.
    """
    arr = _var(
        "arrival_rate", 0,
        service_id="svc_a",
        description="Request arrival rate λ at t=0 (requests/sec)",
    )
    svc = _var(
        "service_rate", 0,
        service_id="svc_a",
        description="Service rate μ at t=0 (requests/sec)",
    )
    qdepth = _var(
        "queue_depth", 1,
        service_id="svc_a",
        description="M/M/1 queue depth at t=1 = ρ/(1−ρ) + noise",
    )
    lat = _var(
        "latency", 1,
        service_id="svc_a",
        description="Expected latency at t=1 = 1/(μ−λ) + noise (sec)",
    )

    endogenous = {v.key: v for v in [arr, svc, qdepth, lat]}
    exogenous = {}

    def _queue_eq(pv: Dict[str, Any], noise: float) -> float:
        """
        queue_depth[t1] = f_queue(arrival_rate[t0], service_rate[t0], U_queue)

        M/M/1: E[queue_depth] = ρ/(1−ρ).
        Clipped to [0, ∞).  ρ is clipped to [0, 0.999] to avoid division by zero.
        Noise term: additive N(0, σ²) with σ=0.2 representing stochastic variability
        around the M/M/1 expectation (e.g., variance of actual queue length distribution).
        """
        lam = max(pv[arr.key], 0.0)
        mu = max(pv[svc.key], lam + 1e-6)  # ensure μ > λ for stability
        rho = lam / mu
        rho = min(rho, 0.999)
        e_queue = rho / (1.0 - rho)
        return max(0.0, e_queue + 0.2 * noise)

    def _latency_eq(pv: Dict[str, Any], noise: float) -> float:
        """
        latency[t1] = f_lat(queue_depth[t1], arrival_rate[t0], service_rate[t0], U_lat)

        M/M/1: E[latency] = 1/(μ−λ).
        Uses queue_depth as a proxy for the queueing component, plus a noise term.
        Clipped to [0, ∞).
        """
        lam = max(pv[arr.key], 0.0)
        mu = max(pv[svc.key], lam + 1e-6)
        e_latency = 1.0 / (mu - lam)
        return max(0.0, e_latency + 0.05 * noise)

    equations = {
        arr.key: StructuralEquation(
            variable=arr,
            parents=[],
            equation=lambda pv, noise: max(0.5, 5.0 + 1.0 * noise),
            equation_type="nonlinear",
            assumption_notes=(
                "arrival_rate ~ N(5, 1) clipped to [0.5, ∞). "
                "Represents requests/sec in a lightly-loaded service."
            ),
        ),
        svc.key: StructuralEquation(
            variable=svc,
            parents=[],
            equation=lambda pv, noise: max(0.5, 10.0 + 0.5 * noise),
            equation_type="nonlinear",
            assumption_notes=(
                "service_rate ~ N(10, 0.5) clipped to [0.5, ∞). "
                "Nominal μ=10 means ρ≈0.5 under default arrival_rate."
            ),
        ),
        qdepth.key: StructuralEquation(
            variable=qdepth,
            parents=[arr, svc],
            equation=_queue_eq,
            equation_type="queueing_mm1",
            assumption_notes=(
                "M/M/1 approximation: queue_depth = ρ/(1−ρ) + N(0,0.04). "
                "Assumes Poisson arrivals, exponential service times, single server. "
                "VIOLATED by bursty traffic. Paper must state this assumption."
            ),
        ),
        lat.key: StructuralEquation(
            variable=lat,
            parents=[qdepth, arr, svc],
            equation=_latency_eq,
            equation_type="queueing_mm1",
            assumption_notes=(
                "M/M/1 approximation: latency = 1/(μ−λ) + N(0,0.0025). "
                "Latency grows as ρ→1. Assumes exponential service times. "
                "Paper must state the M/M/1 assumption and note violations."
            ),
        ),
    }

    return SCM(endogenous=endogenous, exogenous=exogenous, equations=equations)
