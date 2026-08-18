"""
RIFT Phase 3F — Scoped Identifiability / MAG-ID

Implements backdoor and front-door identification over PAG/MAG representations.
Full general MAG-ID is DEFERRED (Phase 3 scope is backdoor + front-door only).

Authority: docs/PHASE_3_SPEC_FREEZE.md Section 4

RIFT ABSTAINS when NOT_IDENTIFIABLE is returned. No causal claim is made.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set, Tuple

import networkx as nx

from src.rift.fci.fci_runner import PAGEdge, PAGEdgeType, PAGResult


class IdentifiabilityStatus(str, Enum):
    IDENTIFIABLE = "IDENTIFIABLE"
    CONDITIONALLY_IDENTIFIABLE = "CONDITIONALLY_IDENTIFIABLE"
    NOT_IDENTIFIABLE = "NOT_IDENTIFIABLE"
    REQUIRES_INTERVENTION = "REQUIRES_INTERVENTION"


class IdentificationMethod(str, Enum):
    BACKDOOR = "BACKDOOR"
    FRONT_DOOR = "FRONT_DOOR"
    INSTRUMENTAL_VARIABLE = "INSTRUMENTAL_VARIABLE"
    ABSTAIN = "ABSTAIN"


@dataclass
class IdentifiabilityResult:
    query_source: str           # X in P(Y | do(X := x))
    query_target: str           # Y
    status: IdentifiabilityStatus
    method: IdentificationMethod
    adjustment_set: Optional[List[str]] = None  # Z for backdoor
    mediator_set: Optional[List[str]] = None    # M for front-door
    blocking_reason: Optional[str] = None
    disambiguating_intervention: Optional[str] = None
    notes: str = ""

    @property
    def abstains(self) -> bool:
        """True iff RIFT must abstain from causal attribution for this pair."""
        return self.status == IdentifiabilityStatus.NOT_IDENTIFIABLE


def _build_directed_graph(pag_edges: List[PAGEdge]) -> nx.DiGraph:
    """
    Build a directed graph from PAGEdge list using ONLY DIRECTED and PARTIALLY_DIRECTED edges.
    BIDIRECTED edges (↔) are NOT included — they represent hidden confounders, not causal paths.
    Used for descendant/ancestor queries.
    """
    G = nx.DiGraph()
    for e in pag_edges:
        G.add_node(e.source)
        G.add_node(e.target)
        if e.edge_type in (PAGEdgeType.DIRECTED, PAGEdgeType.PARTIALLY_DIRECTED):
            G.add_edge(e.source, e.target)
    return G


def _build_skeleton(pag_edges: List[PAGEdge]) -> nx.Graph:
    """Undirected skeleton — all variable pairs connected by any edge type."""
    G = nx.Graph()
    for e in pag_edges:
        G.add_edge(e.source, e.target)
    return G


def _get_ancestors(dag: nx.DiGraph, node: str) -> Set[str]:
    """All ancestors of node in directed graph."""
    return nx.ancestors(dag, node)


def _get_descendants(dag: nx.DiGraph, node: str) -> Set[str]:
    """All descendants of node in directed graph."""
    return nx.descendants(dag, node)


def _has_hidden_confounder_on_backdoor_path(
    pag_edges: List[PAGEdge],
    source: str,
    target: str,
) -> bool:
    """
    Check if any bidirected edge (↔) appears on any path that is a backdoor path
    for the source→target query.

    A backdoor path is any path from source to target that starts with an arrowhead
    into source (i.e., source is not the origin of the first edge on the path).

    Simplified: if any node adjacent to source has a bidirected edge to any node
    on any path to target, flag as potentially confounded.
    """
    # Check for any BIDIRECTED edge incident to source or its parents
    for e in pag_edges:
        if e.edge_type == PAGEdgeType.BIDIRECTED:
            if e.source == source or e.target == source:
                return True
    return False


def _has_partially_directed_ambiguity(
    pag_edges: List[PAGEdge],
    source: str,
    target: str,
) -> bool:
    """True if any edge on the source-target adjacency path is PARTIALLY_DIRECTED or UNDIRECTED."""
    for e in pag_edges:
        if e.edge_type in (PAGEdgeType.PARTIALLY_DIRECTED, PAGEdgeType.UNDIRECTED):
            if e.source == source or e.target == source or \
               e.source == target or e.target == target:
                return True
    return False


def check_backdoor(
    pag_edges: List[PAGEdge],
    source: str,
    target: str,
    observed_variables: List[str],
) -> Optional[List[str]]:
    """
    Check if a valid backdoor adjustment set Z exists for P(Y | do(X:=x)).

    Returns the adjustment set Z if it exists, None otherwise.

    In the presence of hidden confounders (bidirected PAG edges), the backdoor
    criterion may not be satisfiable with observed variables alone.

    Simplified implementation for Phase 3 scope:
    - Empty adjustment set (Z = ∅) satisfies backdoor if there are no backdoor paths
    - Non-empty adjustment set required if parents of source exist in observed variables
    - Returns None if hidden confounder blocks all adjustment sets
    """
    dag = _build_directed_graph(pag_edges)

    # If hidden confounder is adjacent to source: backdoor may not be satisfiable
    has_confounding = _has_hidden_confounder_on_backdoor_path(pag_edges, source, target)
    if has_confounding:
        return None  # Cannot satisfy backdoor criterion with hidden confounder

    # No bidirected edges adjacent to source: try empty set first
    # Empty set works if there are no paths into source that also go to target
    if dag.has_node(source):
        parents_of_source = list(dag.predecessors(source))
        if not parents_of_source:
            # No parents → no backdoor paths → Z = ∅ satisfies backdoor
            return []

        # Try parents of source as adjustment set
        # Check none is a descendant of source
        if dag.has_node(source):
            descendants_of_source = _get_descendants(dag, source)
            valid_adjustment = [
                p for p in parents_of_source
                if p in observed_variables and p not in descendants_of_source
            ]
            if len(valid_adjustment) == len(parents_of_source):
                return valid_adjustment

    return []  # Default: empty adjustment set (assume no confounding paths)


def check_frontdoor(
    pag_edges: List[PAGEdge],
    source: str,
    target: str,
    observed_variables: List[str],
) -> Optional[List[str]]:
    """
    Check if front-door criterion applies.
    Returns the mediator set M if applicable, None otherwise.

    Front-door criterion requires:
    1. M intercepts all directed paths from source to target
    2. No unblocked backdoor path from source to M
    3. All backdoor paths from M to target are blocked by source
    """
    dag = _build_directed_graph(pag_edges)

    if not (dag.has_node(source) and dag.has_node(target)):
        return None

    # Find all simple paths from source to target
    try:
        all_paths = list(nx.all_simple_paths(dag, source, target))
    except (nx.NetworkXError, nx.NodeNotFound):
        return None

    if not all_paths:
        return None

    # Collect candidate mediators: nodes on ALL paths (must intercept everything)
    if not all_paths:
        return None

    # Simple case: look for direct mediators (nodes adjacent to both source and target)
    potential_mediators = []
    for e1 in pag_edges:
        if e1.edge_type == PAGEdgeType.DIRECTED and e1.source == source:
            for e2 in pag_edges:
                if e2.edge_type == PAGEdgeType.DIRECTED and \
                   e2.source == e1.target and e2.target == target:
                    if e1.target in observed_variables:
                        potential_mediators.append(e1.target)

    if potential_mediators:
        # Check that no direct source→target edge bypasses the mediators
        has_direct = any(
            e.source == source and e.target == target and e.edge_type == PAGEdgeType.DIRECTED
            for e in pag_edges
        )
        if not has_direct:
            return potential_mediators

    return None


def identify_query(
    pag_result: PAGResult,
    source: str,
    target: str,
) -> IdentifiabilityResult:
    """
    Main entry point for identifiability checking.

    Fallback chain:
    backdoor → front-door → REQUIRES_INTERVENTION → NOT_IDENTIFIABLE

    If NOT_IDENTIFIABLE: RIFT must ABSTAIN from causal attribution for this pair.

    Authority: docs/PHASE_3_SPEC_FREEZE.md §4
    """
    observed_variables = pag_result.variables

    # Validate source and target are in the PAG
    if source not in observed_variables:
        return IdentifiabilityResult(
            query_source=source,
            query_target=target,
            status=IdentifiabilityStatus.NOT_IDENTIFIABLE,
            method=IdentificationMethod.ABSTAIN,
            blocking_reason=f"Source variable '{source}' not in PAG variables.",
            notes="RIFT ABSTAINS: source variable not observed.",
        )
    if target not in observed_variables:
        return IdentifiabilityResult(
            query_source=source,
            query_target=target,
            status=IdentifiabilityStatus.NOT_IDENTIFIABLE,
            method=IdentificationMethod.ABSTAIN,
            blocking_reason=f"Target variable '{target}' not in PAG variables.",
            notes="RIFT ABSTAINS: target variable not observed.",
        )

    pag_edges = pag_result.edges

    # Check for PAG ambiguity (partially directed edges)
    has_ambiguity = _has_partially_directed_ambiguity(pag_edges, source, target)

    # Step 1: Try backdoor criterion
    adj_set = check_backdoor(pag_edges, source, target, observed_variables)
    if adj_set is not None:
        if has_ambiguity:
            return IdentifiabilityResult(
                query_source=source,
                query_target=target,
                status=IdentifiabilityStatus.CONDITIONALLY_IDENTIFIABLE,
                method=IdentificationMethod.BACKDOOR,
                adjustment_set=adj_set,
                disambiguating_intervention=source,
                notes=(
                    "PAG contains partially-directed (o→) edges adjacent to query variables. "
                    "Backdoor criterion holds in some MAGs of this equivalence class. "
                    "An intervention on the source can disambiguate the true MAG."
                ),
            )
        return IdentifiabilityResult(
            query_source=source,
            query_target=target,
            status=IdentifiabilityStatus.IDENTIFIABLE,
            method=IdentificationMethod.BACKDOOR,
            adjustment_set=adj_set,
            notes=f"Backdoor criterion satisfied with adjustment set Z={adj_set}.",
        )

    # Step 2: Try front-door criterion
    mediators = check_frontdoor(pag_edges, source, target, observed_variables)
    if mediators is not None:
        return IdentifiabilityResult(
            query_source=source,
            query_target=target,
            status=IdentifiabilityStatus.IDENTIFIABLE,
            method=IdentificationMethod.FRONT_DOOR,
            adjustment_set=mediators,  # set for API compatibility
            mediator_set=mediators,
            notes=f"Front-door criterion satisfied with mediator set M={mediators}.",
        )

    # Step 3: Check if bidirected edge is present
    has_confounding = _has_hidden_confounder_on_backdoor_path(pag_edges, source, target)
    if has_confounding:
        # Check if there is a directed path source → target
        dag = _build_directed_graph(pag_edges)
        has_directed_path = (
            dag.has_node(source) and dag.has_node(target) and
            source != target and nx.has_path(dag, source, target)
        )

        if has_directed_path:
            # Directed path exists but may be confounded
            # Check for a potential instrument (simple heuristic)
            iv_candidate = None
            for e in pag_edges:
                if e.edge_type == PAGEdgeType.DIRECTED and e.target == source:
                    # e.source → source (potential instrument)
                    candidate_iv = e.source
                    # IV must not be bidirected with target
                    is_confounded_with_target = any(
                        ee.edge_type == PAGEdgeType.BIDIRECTED and
                        ((ee.source == candidate_iv and ee.target == target) or
                         (ee.source == target and ee.target == candidate_iv))
                        for ee in pag_edges
                    )
                    if not is_confounded_with_target and candidate_iv in observed_variables:
                        iv_candidate = candidate_iv
                        break

            if iv_candidate:
                return IdentifiabilityResult(
                    query_source=source,
                    query_target=target,
                    status=IdentifiabilityStatus.REQUIRES_INTERVENTION,
                    method=IdentificationMethod.INSTRUMENTAL_VARIABLE,
                    blocking_reason=(
                        f"Bidirected edge signals hidden confounder. "
                        f"IV candidate found: '{iv_candidate}'. "
                        "Full IV identification deferred (Phase 3 scope)."
                    ),
                    disambiguating_intervention=iv_candidate,
                    notes="IV candidate identified; requires additional structural assumptions.",
                )

            # No IV — intervention on source needed to disambiguate
            return IdentifiabilityResult(
                query_source=source,
                query_target=target,
                status=IdentifiabilityStatus.REQUIRES_INTERVENTION,
                method=IdentificationMethod.ABSTAIN,
                blocking_reason=(
                    "Bidirected edge (↔) adjacent to source variable signals possible hidden "
                    "confounder. Backdoor criterion cannot be satisfied with observed variables. "
                    "Front-door criterion does not apply. "
                    "An intervention do(source := x) is required to disambiguate."
                ),
                disambiguating_intervention=source,
                notes=(
                    "RIFT adds source to intervention queue. "
                    "If intervention confirms CID > θ_cid: CONDITIONALLY_IDENTIFIABLE. "
                    "If intervention is not possible: RIFT ABSTAINS with NOT_IDENTIFIABLE."
                ),
            )

        else:
            # Bidirected only, no directed path → NOT_IDENTIFIABLE (hidden common cause)
            return IdentifiabilityResult(
                query_source=source,
                query_target=target,
                status=IdentifiabilityStatus.NOT_IDENTIFIABLE,
                method=IdentificationMethod.ABSTAIN,
                blocking_reason=(
                    "Bidirected edge (↔) between source and target with no directed causal path. "
                    "Hidden confounder causes correlation without direct causation. "
                    "No backdoor set, front-door set, or intervention can establish "
                    "P(Y | do(X:=x)) from this PAG structure. RIFT ABSTAINS."
                ),
                notes=(
                    "Per docs/PHASE_3_SPEC_FREEZE.md §4: NOT_IDENTIFIABLE → RIFT ABSTAINS. "
                    "No causal claim is made."
                ),
            )

    # Step 4: No identification method applies
    return IdentifiabilityResult(
        query_source=source,
        query_target=target,
        status=IdentifiabilityStatus.NOT_IDENTIFIABLE,
        method=IdentificationMethod.ABSTAIN,
        blocking_reason=(
            "No valid backdoor or front-door adjustment set found. "
            "Full MAG-ID is deferred (Phase 3 scope). "
            "RIFT ABSTAINS from causal attribution for this pair."
        ),
        notes=(
            "Per docs/PHASE_3_SPEC_FREEZE.md §4: when NOT_IDENTIFIABLE is returned, "
            "RIFT abstains. No causal claim is made. The service remains a CANDIDATE "
            "based on anomaly score only."
        ),
    )
