"""PAG mark semantics for RIFT (Sprint 4.4.0). NEW module: does not edit any frozen file.

causal-learn convention (verified empirically in tests/unit/test_sprint440_pag_semantics.py):
    M[x][y] is the endpoint mark AT x of the edge between x and y.   -1 = tail, 1 = arrowhead, 2 = circle.
    x --> y   : M[x][y] = -1, M[y][x] = 1
    x o-> y   : M[x][y] =  2, M[y][x] = 1
    x o-o y   : 2, 2          x <-> y : 1, 1          x --- y : -1, -1          x --o y : M[x][y]=-1, M[y][x]=2

``fci_runner._decode_pag_edges`` (frozen, Sprint 4.3.0) assumes the transposed convention for ``o->`` and therefore
reports every ``x o-> y`` as UNDIRECTED. ``decode_marks`` below reads the raw matrix with the correct convention.

Evidence hierarchy (ordered, strongest first). Nothing here upgrades a class: a relation is only ever assigned the
strongest class that the PAG marks *justify*.
    DIRECTED_ANCESTOR            every edge on some path x -> ... -> y is fully oriented (tail at the source end,
                                 arrowhead at the target end). Under the usual FCI assumptions this is an ancestor
                                 relation shared by every MAG in the equivalence class.
    POSSIBLE_ANCESTOR            some path x ~> y is *semi-directed* (no arrowhead points back toward x): x may be an
                                 ancestor of y in some member of the class. Not established.
    SEMI_DIRECTED_CONNECTION     x and y are connected, but only through paths that contain an arrowhead against the
                                 direction (e.g. bidirected hops, or arrowheads into x): x is NOT a possible ancestor.
    OBSERVATIONAL_ASSOCIATION    x and y are connected in the skeleton but no semi-directed path in either direction
                                 exists from x (only reverse / bidirected structure).
    NO_SUPPORTED_RELATIONSHIP    x, y not connected in the PAG (or node missing).
Interventional evidence is a separate axis and is never encoded here.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Set, Tuple

import numpy as np

TAIL, ARROW, CIRCLE = -1, 1, 2

DIRECTED_ANCESTOR = "DIRECTED_ANCESTOR"
POSSIBLE_ANCESTOR = "POSSIBLE_ANCESTOR"
SEMI_DIRECTED_CONNECTION = "SEMI_DIRECTED_CONNECTION"
OBSERVATIONAL_ASSOCIATION = "OBSERVATIONAL_ASSOCIATION"
NO_SUPPORTED_RELATIONSHIP = "NO_SUPPORTED_RELATIONSHIP"
HIERARCHY = (DIRECTED_ANCESTOR, POSSIBLE_ANCESTOR, SEMI_DIRECTED_CONNECTION, OBSERVATIONAL_ASSOCIATION,
             NO_SUPPORTED_RELATIONSHIP)


@dataclass(frozen=True)
class MarkedPAG:
    """PAG with explicit endpoint marks. marks[(x, y)] = mark at x for the edge x *-* y (both orders present)."""
    variables: Tuple[str, ...]
    marks: Mapping[Tuple[str, str], int]

    def adjacent(self, x: str, y: str) -> bool:
        return (x, y) in self.marks

    def edges(self) -> List[Tuple[str, str]]:
        return sorted((a, b) for (a, b) in self.marks if a < b)

    def kind(self, x: str, y: str) -> str:
        """Edge type as seen from x to y."""
        mx, my = self.marks[(x, y)], self.marks[(y, x)]
        if (mx, my) == (TAIL, ARROW):
            return "x->y"
        if (mx, my) == (ARROW, TAIL):
            return "x<-y"
        if (mx, my) == (CIRCLE, ARROW):
            return "xo->y"
        if (mx, my) == (ARROW, CIRCLE):
            return "x<-oy"
        if (mx, my) == (CIRCLE, CIRCLE):
            return "xo-oy"
        if (mx, my) == (ARROW, ARROW):
            return "x<->y"
        if (mx, my) == (TAIL, TAIL):
            return "x---y"
        if (mx, my) == (TAIL, CIRCLE):
            return "x--oy"
        if (mx, my) == (CIRCLE, TAIL):
            return "xo--y"
        return "other"

    def semi_directed_step(self, x: str, y: str) -> bool:
        """x -> y may be traversed on a semi-directed path: adjacent and the mark at x is not an arrowhead."""
        return self.adjacent(x, y) and self.marks[(x, y)] != ARROW

    def directed_step(self, x: str, y: str) -> bool:
        return self.adjacent(x, y) and self.marks[(x, y)] == TAIL and self.marks[(y, x)] == ARROW


def decode_marks(variables: List[str], matrix: np.ndarray) -> MarkedPAG:
    marks: Dict[Tuple[str, str], int] = {}
    n = len(variables)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = int(matrix[i][j]), int(matrix[j][i])
            if a == 0 and b == 0:
                continue
            marks[(variables[i], variables[j])] = a
            marks[(variables[j], variables[i])] = b
    return MarkedPAG(tuple(variables), marks)


def from_true_dag(variables: List[str], directed_edges: List[Tuple[str, str]]) -> MarkedPAG:
    """Oracle: fully oriented marks from a DAG over observed nodes (labelled privileged by every caller)."""
    marks: Dict[Tuple[str, str], int] = {}
    for a, b in directed_edges:
        if (a, b) in marks:
            continue
        marks[(a, b)] = TAIL
        marks[(b, a)] = ARROW
    return MarkedPAG(tuple(variables), marks)


def _reach(pag: MarkedPAG, x: str, step) -> Set[str]:
    seen: Set[str] = set()
    q = deque([x])
    while q:
        u = q.popleft()
        for (a, b) in pag.marks:
            if a == u and b not in seen and b != x and step(u, b):
                seen.add(b)
                q.append(b)
    return seen


def directed_descendants(pag: MarkedPAG, x: str) -> Set[str]:
    return _reach(pag, x, pag.directed_step)


def possible_descendants(pag: MarkedPAG, x: str) -> Set[str]:
    """Nodes reachable from x along semi-directed paths (no hop has an arrowhead at its tail-side end)."""
    return _reach(pag, x, pag.semi_directed_step)


def connected(pag: MarkedPAG, x: str) -> Set[str]:
    return _reach(pag, x, lambda u, v: pag.adjacent(u, v))


def classify_relation(pag: MarkedPAG, x: str, y: str) -> str:
    if x == y or x not in pag.variables or y not in pag.variables:
        return NO_SUPPORTED_RELATIONSHIP
    if y in directed_descendants(pag, x):
        return DIRECTED_ANCESTOR
    if y in possible_descendants(pag, x):
        return POSSIBLE_ANCESTOR
    if y in connected(pag, x):
        # connected but x cannot be a (possible) ancestor of y. If y -> x semi-directed it is the reverse relation.
        return OBSERVATIONAL_ASSOCIATION if x in possible_descendants(pag, y) else SEMI_DIRECTED_CONNECTION
    return NO_SUPPORTED_RELATIONSHIP


def to_pag_result(pag: MarkedPAG, template):
    """Return a frozen-API PAGResult (edges re-encoded with CORRECT types) for reuse of unmodified V2 code."""
    from src.rift.fci.fci_runner import PAGEdge, PAGEdgeType, PAGResult
    edges = []
    for a, b in pag.edges():
        k = pag.kind(a, b)
        if k == "x->y":
            edges.append(PAGEdge(a, b, PAGEdgeType.DIRECTED))
        elif k == "x<-y":
            edges.append(PAGEdge(b, a, PAGEdgeType.DIRECTED))
        elif k == "xo->y":
            edges.append(PAGEdge(a, b, PAGEdgeType.PARTIALLY_DIRECTED))
        elif k == "x<-oy":
            edges.append(PAGEdge(b, a, PAGEdgeType.PARTIALLY_DIRECTED))
        elif k == "x<->y":
            edges.append(PAGEdge(a, b, PAGEdgeType.BIDIRECTED))
        elif k == "xo-oy":
            edges.append(PAGEdge(a, b, PAGEdgeType.UNDIRECTED))
        else:
            edges.append(PAGEdge(a, b, PAGEdgeType.TAIL_TAIL))
    return PAGResult(variables=list(template.variables), edges=edges, adjacency_matrix=template.adjacency_matrix,
                     alpha=template.alpha, n_samples_used=template.n_samples_used, n_variables=template.n_variables,
                     hidden_confounder_pairs=[(a, b) for a, b in pag.edges() if pag.kind(a, b) == "x<->y"],
                     notes="PAG re-decoded with the corrected causal-learn endpoint convention (Sprint 4.4.0)")
