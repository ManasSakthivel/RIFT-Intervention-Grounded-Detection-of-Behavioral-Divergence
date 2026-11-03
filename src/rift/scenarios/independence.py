"""Held-out independence verifier for v2 scenarios (Sprint 4.3.0, Phase 2/4).

Independence is verified on CONTENT, never inferred from seeds, ids or file separation.
Keys compared across splits (any shared key is a leak unless explicitly declared as a marginal dimension):

  content_hash     full scenario content (excluding id/seed/split)
  dynamics_hash    name-agnostic generative spec (graph structure with sigma/gain/lag, faults, telemetry,
                   workload, intervention) -> two scenarios with equal value differ only in node names/seed
  topology_hash    name-agnostic WL hash of the true causal graph (+hidden/observed roles)
  template_id      structure|family
  joint_cell       (structure, family, temporal, workload, observability, intervention)
  group            connected component over template_id and topology_hash (union-find)
  near-duplicate   spec_similarity >= threshold across splits

Marginal dimensions (workload, observability, intervention, temporal on their own) are DELIBERATELY shared
across splits so the evaluation covers every level in every split; this is a declared dependency, not an
oversight, and it is reported.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import networkx as nx
import numpy as np

from .fingerprint import sha256_json
from .splitter import build_groups, group_integrity_violations


def _wl(sc: Mapping[str, Any], attrs: bool) -> str:
    g = nx.DiGraph()
    roots = {f["service"] for f in sc["faults"]}      # structural role only; no label fields are read
    for n in sc["graph"]["nodes"]:
        role = ("H" if n.get("hidden") else "O") + ("R" if n["id"] in roots else "-")
        if attrs:
            role += f"|s{round(n['sigma'], 1)}"
        g.add_node(n["id"], role=role)
    for e in sc["graph"]["edges"]:
        g.add_edge(e["src"], e["dst"], w=(f"{round(e['gain'], 2)}/{e['lag']}" if attrs else ""))
    return nx.weisfeiler_lehman_graph_hash(g, node_attr="role", edge_attr="w", iterations=3)


def topology_hash(sc: Mapping[str, Any]) -> str:
    return sha256_json({"wl": _wl(sc, False), "n": len(sc["graph"]["nodes"]),
                        "m": len(sc["graph"]["edges"])})


def dynamics_hash(sc: Mapping[str, Any]) -> str:
    faults = sorted([(f["shape"], f["shape_params"].get("windows"), round(f["amp_ms"], 1), f["onset_s"],
                      f.get("var_mult", 1.0), f.get("downstream_shape")) for f in sc["faults"]], key=str)
    return sha256_json({"wl": _wl(sc, True), "faults": faults,
                        "tel": {k: v for k, v in sc["telemetry"].items() if k not in ("unobserved", "delay_windows")},
                        "n_unobs": len(sc["telemetry"]["unobserved"]),
                        "wl_params": sc["workload_params"],
                        "iv": {k: v for k, v in sc["intervention"].items() if k not in ("co_target", "collateral")},
                        "n_coll": len(sc["intervention"]["collateral"])})


def joint_cell(sc: Mapping[str, Any]) -> Tuple[str, ...]:
    d = sc["dimensions"]
    return (d["structure"], d["family"], d["temporal"], d["workload"], d["observability"], d["intervention"])


def spec_vector(sc: Mapping[str, Any]) -> np.ndarray:
    nodes, edges = sc["graph"]["nodes"], sc["graph"]["edges"]
    f0 = sc["faults"][0] if sc["faults"] else {"amp_ms": 0.0, "onset_s": 0.0}
    return np.array([len(nodes) / 14.0, len(edges) / 18.0, np.mean([n["sigma"] for n in nodes]) / 25.0,
                     (np.mean([e["gain"] for e in edges]) if edges else 0.0) / 2.0,
                     (np.mean([e["lag"] for e in edges]) if edges else 0.0) / 6.0,
                     f0["amp_ms"] / 100.0, f0["onset_s"] / 250.0, sc["telemetry"]["n_windows"] / 60.0,
                     sc["telemetry"]["missing_frac"], sc["intervention"]["magnitude_sigma"] / 4.0])


def spec_similarity(a: Mapping[str, Any], b: Mapping[str, Any]) -> float:
    cat = sum(a["dimensions"][k] == b["dimensions"][k] for k in
              ("structure", "family", "temporal", "workload", "observability", "intervention", "negative"))
    num = 1.0 - float(np.mean(np.abs(spec_vector(a) - spec_vector(b))))
    return 0.6 * cat / 7.0 + 0.4 * num


def verify_independence(splits: Mapping[str, Sequence[Mapping[str, Any]]], protected: str = "held_out",
                        near_threshold: float = 0.90) -> Dict[str, Any]:
    keyfns = {"content_hash": lambda s: s["content_hash"], "dynamics_hash": dynamics_hash,
              "topology_hash": topology_hash, "template_id": lambda s: s["template_id"],
              "joint_cell": joint_cell}
    keys = {name: {sp: {fn(s) for s in scs} for sp, scs in splits.items()} for name, fn in keyfns.items()}
    shared: Dict[str, Dict[str, int]] = {}
    for name, per in keys.items():
        shared[name] = {f"{a}&{b}": len(per[a] & per[b]) for a, b in combinations(per, 2)}
    leaks_for_protected = {name: sum(n for pair, n in sh.items() if protected in pair.split("&"))
                           for name, sh in shared.items()}

    items = {s["scenario_id"]: s for scs in splits.values() for s in scs}
    split_of = {s["scenario_id"]: sp for sp, scs in splits.items() for s in scs}
    grp = build_groups(items, [lambda s: ("t", s["template_id"]), lambda s: ("topo", topology_hash(s))])
    viol = group_integrity_violations(split_of, grp)

    near: List[Tuple[str, str, float]] = []
    for a, b in combinations(list(splits), 2):
        for x in splits[a]:
            for y in splits[b]:
                sim = spec_similarity(x, y)
                if sim >= near_threshold:
                    near.append((x["scenario_id"], y["scenario_id"], round(sim, 4)))

    distinct = {sp: {name: len({fn(s) for s in scs}) for name, fn in keyfns.items()}
                for sp, scs in splits.items()}
    marginals = {dim: {sp: sorted({s["dimensions"][dim] for s in scs}) for sp, scs in splits.items()}
                 for dim in ("workload", "observability", "intervention", "temporal")}
    unseen = {}
    for dim in ("structure", "family"):
        seen = {sp: {s["dimensions"][dim] for s in scs} for sp, scs in splits.items()}
        others = set().union(*[v for k, v in seen.items() if k != protected]) if len(splits) > 1 else set()
        unseen[dim] = sorted(seen.get(protected, set()) - others)
    ok = all(v == 0 for v in leaks_for_protected.values()) and not viol and not near
    return {"ok": bool(ok), "protected_split": protected, "shared_keys_by_pair": shared,
            "leaks_for_protected": leaks_for_protected, "n_groups": len(set(grp.values())),
            "group_integrity_violations": viol, "near_duplicate_pairs_cross_split": near,
            "near_threshold": near_threshold, "distinct_keys_per_split": distinct,
            "declared_shared_marginal_dimensions": marginals,
            "unseen_in_protected_vs_other_splits": unseen,
            "n_scenarios": {sp: len(v) for sp, v in splits.items()}}


LABEL_FIELDS = ("ground_truth", "design")


def strip_labels(sc: Mapping[str, Any]) -> Dict[str, Any]:
    """Copy of a scenario without outcome labels (used when verifying independence on a sealed split)."""
    return {k: v for k, v in sc.items() if k not in LABEL_FIELDS}
