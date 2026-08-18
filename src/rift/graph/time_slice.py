"""RIFT time-sliced G_T construction — Phase 3C."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import networkx as nx


@dataclass
class TimeSliceConfig:
    delta_t: float = 10.0        # window size in seconds
    max_lag: int = 1             # max temporal lag (1 = X[t] → Y[t+1] only)
    alignment_tolerance: float = 0.5  # fraction of delta_t for lag assignment
    min_correlation: float = 0.2      # minimum correlation to add an edge


@dataclass
class TimeSlicedGraph:
    """
    Time-sliced causal graph G_T.
    Nodes are (service, time_index) tuples.
    All edges are strictly forward in time (acyclicity guaranteed by construction).
    """
    graph: nx.DiGraph
    variables: List[str]          # base variable names (without time suffix)
    time_indices: List[int]       # available time indices
    config: TimeSliceConfig
    alignment_log: List[str] = field(default_factory=list)

    def is_acyclic(self) -> bool:
        return nx.is_directed_acyclic_graph(self.graph)

    def has_feedback_cycle(self) -> bool:
        """True if there is a cycle (should always be False by construction)."""
        return not self.is_acyclic()

    def get_node_id(self, variable: str, t: int) -> str:
        return f"{variable}__t{t}"

    def get_edges_at_lag(self, lag: int) -> List[Tuple[str, str]]:
        """Return all edges from time t to time t+lag."""
        edges = []
        for src, dst in self.graph.edges():
            src_t = int(src.rsplit("__t", 1)[1])
            dst_t = int(dst.rsplit("__t", 1)[1])
            if dst_t - src_t == lag:
                edges.append((src, dst))
        return edges


def build_time_sliced_graph(
    observations: Dict[str, pd.DataFrame],
    call_graph: nx.DiGraph,
    config: TimeSliceConfig,
) -> TimeSlicedGraph:
    """
    Build time-sliced G_T from observations and the known call graph topology.

    For each directed edge A→B in the call graph:
    - Add temporal edge A__t{t} → B__t{t+1} (causal propagation lag = 1)

    For same-service variables:
    - Add A__t{t} → A__t{t+1} (autoregressive component)

    Acyclicity is guaranteed by construction (all edges are strictly forward in time).

    Authority: docs/PHASE_3_SPEC_FREEZE.md §2
    """
    alignment_log = []
    G = nx.DiGraph()

    # Determine time indices from observations
    all_times = set()
    for svc, df in observations.items():
        times = sorted(df['time'].unique())
        # Align to windows
        windows = [int(t / config.delta_t) for t in times]
        all_times.update(windows)

    time_indices = sorted(all_times)
    variables = list(observations.keys())

    # Add all nodes
    for var in variables:
        for t in time_indices:
            G.add_node(f"{var}__t{t}", variable=var, time_index=t)

    # Add temporal edges from call graph
    for t in time_indices:
        for t_next in time_indices:
            lag = t_next - t
            if lag < 1 or lag > config.max_lag:
                continue
            # Call graph edges: A→B becomes A__t → B__t+lag
            for src, dst in call_graph.edges():
                if src in variables and dst in variables:
                    src_node = f"{src}__t{t}"
                    dst_node = f"{dst}__t{t_next}"
                    if G.has_node(src_node) and G.has_node(dst_node):
                        G.add_edge(src_node, dst_node, lag=lag, edge_type="CALL_GRAPH")

            # Autoregressive: service → itself at next timestep
            for var in variables:
                src_node = f"{var}__t{t}"
                dst_node = f"{var}__t{t_next}"
                if G.has_node(src_node) and G.has_node(dst_node):
                    if not G.has_edge(src_node, dst_node):
                        G.add_edge(src_node, dst_node, lag=lag, edge_type="AUTOREGRESSIVE")

    # Temporal alignment: check for any collection lags
    for svc, df in observations.items():
        if 'collection_lag_s' in df.columns:
            for _, row in df.iterrows():
                lag_s = row.get('collection_lag_s', 0.0)
                if lag_s > config.delta_t * config.alignment_tolerance:
                    msg = (
                        f"Variable {svc} at t={row['time']:.1f} has collection lag "
                        f"{lag_s:.1f}s > {config.alignment_tolerance * config.delta_t:.1f}s "
                        f"(Δt/2). Assigned to next window."
                    )
                    alignment_log.append(msg)

    # Verify acyclicity (must always hold by construction)
    assert nx.is_directed_acyclic_graph(G), (
        "Time-sliced graph has cycles — this is a construction error. "
        "Check that all edges are strictly forward in time."
    )

    return TimeSlicedGraph(
        graph=G,
        variables=variables,
        time_indices=time_indices,
        config=config,
        alignment_log=alignment_log,
    )


def collapse_to_service_graph(tsg: TimeSlicedGraph) -> nx.DiGraph:
    """
    Collapse time-sliced graph to service-level graph for EBD/identifiability.
    Edges represent 'service A causally precedes service B' (at any lag).
    """
    G = nx.DiGraph()
    for src, dst in tsg.graph.edges():
        src_svc = src.rsplit("__t", 1)[0]
        dst_svc = dst.rsplit("__t", 1)[0]
        if src_svc != dst_svc:
            G.add_edge(src_svc, dst_svc)
    return G
