"""
RIFT Phase 3E — FCI / PAG Runner

Uses the causal-learn library's FCI implementation to produce PAGs.
The PAG is INTERVENTION-CONSISTENT — it represents the Markov equivalence class
consistent with observed conditional independencies. It is NOT the true causal graph.

Authority: docs/PHASE_3_SPEC_FREEZE.md Section 3
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional

import numpy as np
import pandas as pd

try:
    from causallearn.search.ConstraintBased.FCI import fci
    from causallearn.utils.cit import fisherz
    CAUSALLEARN_AVAILABLE = True
except ImportError:
    CAUSALLEARN_AVAILABLE = False


class PAGEdgeType(str, Enum):
    DIRECTED = "DIRECTED"            # Vᵢ → Vⱼ
    BIDIRECTED = "BIDIRECTED"        # Vᵢ ↔ Vⱼ  (hidden confounder signal)
    PARTIALLY_DIRECTED = "PARTIALLY_DIRECTED"  # Vᵢ o→ Vⱼ
    UNDIRECTED = "UNDIRECTED"        # Vᵢ o-o Vⱼ
    TAIL_TAIL = "TAIL_TAIL"          # Vᵢ — Vⱼ (rare in FCI output)


@dataclass(frozen=True)
class PAGEdge:
    source: str
    target: str
    edge_type: PAGEdgeType
    confidence: float = 0.5  # 0–1 heuristic proxy; default 0.5


@dataclass
class PAGResult:
    variables: List[str]
    edges: List[PAGEdge]
    adjacency_matrix: Optional[np.ndarray] = None
    fci_algorithm: str = "FCI"
    ci_test: str = "fisherz"
    alpha: float = 0.05
    n_samples_used: int = 0
    n_variables: int = 0
    runtime_seconds: float = 0.0
    hidden_confounder_pairs: List[Tuple[str, str]] = field(default_factory=list)
    notes: str = ""
    # Alias: some callers use observed_variables (legacy name)
    observed_variables: Optional[List[str]] = None

    def __post_init__(self):
        # Unify observed_variables / variables naming
        if self.observed_variables is None:
            self.observed_variables = self.variables
        elif not self.variables:
            self.variables = self.observed_variables
        if self.adjacency_matrix is None:
            n = len(self.variables)
            self.adjacency_matrix = np.zeros((n, n))

    def has_edge(self, source: str, target: str) -> bool:
        """True if any edge (in either direction) exists between source and target."""
        for e in self.edges:
            if (e.source == source and e.target == target) or \
               (e.source == target and e.target == source):
                return True
        return False

    def get_edge(self, source: str, target: str) -> Optional[PAGEdge]:
        for e in self.edges:
            if e.source == source and e.target == target:
                return e
        return None

    def is_hidden_confounder_pair(self, a: str, b: str) -> bool:
        return (a, b) in self.hidden_confounder_pairs or \
               (b, a) in self.hidden_confounder_pairs


class SubgraphTooLargeError(Exception):
    """Raised when k > max_variables. FCI is not run online for large subgraphs."""
    def __init__(self, k: int, max_k: int):
        super().__init__(
            f"Subgraph has {k} variables, exceeds max_variables={max_k}. "
            f"Per docs/PHASE_3_SPEC_FREEZE.md §3: FCI is not run online for k > {max_k}. "
            f"Fallback: anomaly ranking only (no PAG). Set boundary_limited=TRUE."
        )
        self.k = k
        self.max_k = max_k


class FCIUnavailableError(Exception):
    """Raised when causal-learn is not installed."""


def _decode_pag_edges(
    graph_matrix: np.ndarray,
    variables: List[str],
) -> Tuple[List[PAGEdge], List[Tuple[str, str]]]:
    """
    Decode causal-learn PAG adjacency matrix into PAGEdge objects.

    causal-learn PAG matrix encoding:
      graph[i][j] = -1, graph[j][i] = 1  →  i → j   (DIRECTED)
      graph[i][j] =  1, graph[j][i] = 1  →  i ↔ j   (BIDIRECTED)
      graph[i][j] =  1, graph[j][i] = -1 →  j → i   (DIRECTED, reverse)
      graph[i][j] =  2, graph[j][i] = -1 →  i o→ j  (PARTIALLY_DIRECTED, circle on tail)
      graph[i][j] = -1, graph[j][i] =  2 →  j o→ i  (PARTIALLY_DIRECTED, reverse)
      graph[i][j] =  2, graph[j][i] =  2 →  i o-o j (UNDIRECTED)
      graph[i][j] = -1, graph[j][i] = -1 →  i — j   (TAIL_TAIL)

    Note: causal-learn uses 2 for circle mark (not 3).
    """
    edges: List[PAGEdge] = []
    hidden_confounders: List[Tuple[str, str]] = []
    n = len(variables)

    for i in range(n):
        for j in range(i + 1, n):
            aij = int(graph_matrix[i][j])
            aji = int(graph_matrix[j][i])

            if aij == 0 and aji == 0:
                continue  # no edge

            edge_type: Optional[PAGEdgeType] = None
            canonical_source = variables[i]
            canonical_target = variables[j]

            if aij == -1 and aji == 1:
                # i → j
                edge_type = PAGEdgeType.DIRECTED
            elif aij == 1 and aji == -1:
                # j → i  (report as j→i)
                edge_type = PAGEdgeType.DIRECTED
                canonical_source = variables[j]
                canonical_target = variables[i]
            elif aij == 1 and aji == 1:
                # i ↔ j
                edge_type = PAGEdgeType.BIDIRECTED
                hidden_confounders.append((variables[i], variables[j]))
            elif aij == 2 and aji == -1:
                # i o→ j
                edge_type = PAGEdgeType.PARTIALLY_DIRECTED
            elif aij == -1 and aji == 2:
                # j o→ i
                edge_type = PAGEdgeType.PARTIALLY_DIRECTED
                canonical_source = variables[j]
                canonical_target = variables[i]
            elif aij == 2 and aji == 2:
                # i o-o j
                edge_type = PAGEdgeType.UNDIRECTED
            elif aij == -1 and aji == -1:
                edge_type = PAGEdgeType.TAIL_TAIL
            else:
                # Unknown encoding — treat as undirected
                edge_type = PAGEdgeType.UNDIRECTED

            if edge_type is not None:
                edges.append(PAGEdge(
                    source=canonical_source,
                    target=canonical_target,
                    edge_type=edge_type,
                    confidence=0.5,  # placeholder; refined below
                ))

    return edges, hidden_confounders


def run_fci(
    data: pd.DataFrame,
    alpha: float = 0.05,
    seed: int = 42,
    max_variables: int = 15,
) -> PAGResult:
    """
    Run FCI on data and return a PAGResult.

    Raises SubgraphTooLargeError if data.shape[1] > max_variables.
    Raises FCIUnavailableError if causal-learn is not installed.

    The PAG is INTERVENTION-CONSISTENT, not causally accurate.
    It represents the equivalence class consistent with observed CI relationships.

    Authority: docs/PHASE_3_SPEC_FREEZE.md §3
    """
    if not CAUSALLEARN_AVAILABLE:
        raise FCIUnavailableError(
            "causal-learn is not installed. Install with: pip install causal-learn"
        )

    variables = list(data.columns)
    k = len(variables)

    if k > max_variables:
        raise SubgraphTooLargeError(k, max_variables)

    if k < 2:
        return PAGResult(
            variables=variables,
            edges=[],
            adjacency_matrix=np.zeros((k, k)),
            n_samples_used=len(data),
            n_variables=k,
            notes="Fewer than 2 variables; no edges possible.",
        )

    # Deterministic: set numpy seed before FCI (causal-learn uses np.random internally)
    np.random.seed(seed)

    data_array = data.values.astype(float)
    t_start = time.time()

    # Run FCI with Fisher's Z CI test
    g, edges_raw = fci(data_array, fisherz, alpha, verbose=False)
    elapsed = time.time() - t_start

    # Decode the PAG
    graph_matrix = g.graph
    pag_edges, hidden_confounders = _decode_pag_edges(graph_matrix, variables)

    return PAGResult(
        variables=variables,
        edges=pag_edges,
        adjacency_matrix=graph_matrix,
        fci_algorithm="FCI",
        ci_test="fisherz",
        alpha=alpha,
        n_samples_used=len(data),
        n_variables=k,
        runtime_seconds=elapsed,
        hidden_confounder_pairs=hidden_confounders,
        notes=(
            "PAG is intervention-consistent; not the true causal graph. "
            "Bidirected edges signal potential hidden confounders. "
            "Validated on synthetic ground-truth scenarios only."
        ),
    )


# ─────────────────────────────────────────────
# Synthetic graph generators for validation
# ─────────────────────────────────────────────

def generate_chain_data(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """X → Y → Z. No confounding. FCI should recover directed edges."""
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, n)
    Y = 0.8 * X + rng.normal(0, 0.5, n)
    Z = 0.8 * Y + rng.normal(0, 0.5, n)
    return pd.DataFrame({"X": X, "Y": Y, "Z": Z})


def generate_latent_confounder_data(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """X ← U → Y (U hidden). FCI should show bidirected X ↔ Y."""
    rng = np.random.default_rng(seed)
    U = rng.normal(0, 1, n)
    X = 0.8 * U + rng.normal(0, 0.5, n)
    Y = 0.8 * U + rng.normal(0, 0.5, n)
    # U is NOT included in returned DataFrame (simulates latent variable)
    return pd.DataFrame({"X": X, "Y": Y})


def generate_collider_data(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """X → Z ← Y. Z is a collider. X and Y are independent."""
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, n)
    Y = rng.normal(0, 1, n)
    Z = 0.8 * X + 0.8 * Y + rng.normal(0, 0.5, n)
    return pd.DataFrame({"X": X, "Y": Y, "Z": Z})


def generate_mediated_data(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """X → M → Y. M mediates the X→Y relationship."""
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, n)
    M = 0.8 * X + rng.normal(0, 0.5, n)
    Y = 0.8 * M + rng.normal(0, 0.5, n)
    return pd.DataFrame({"X": X, "M": M, "Y": Y})


def generate_ambiguous_orientation_data(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """4-node structure where FCI leaves some marks as circles (orientation ambiguous)."""
    rng = np.random.default_rng(seed)
    A = rng.normal(0, 1, n)
    B = 0.7 * A + rng.normal(0, 0.5, n)
    C = 0.7 * A + rng.normal(0, 0.5, n)
    D = 0.7 * B + 0.7 * C + rng.normal(0, 0.5, n)
    return pd.DataFrame({"A": A, "B": B, "C": C, "D": D})
