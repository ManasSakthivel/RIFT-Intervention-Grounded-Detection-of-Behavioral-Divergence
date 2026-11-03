#!/usr/bin/env python3
"""Sprint 4.5.1 (Agent 3) analysis-only structural checks of the Sprint 4.5.0 dataset protocol.

IN-MEMORY FEASIBILITY PROTOTYPE. It does NOT implement the confirmatory generator, writes NO scenario
file, draws NO confirmatory seed, runs NO RIFT method and never touches the sealed held-out files.

  python3 scripts/sprint451_dataset_protocol_checks.py [M]        (default M = 6000 prototype candidates)

What it does (everything from public frozen code + dev/val/adversarial_dev, which are readable):
  1. Defines the 16 proposed motifs (S01-S16) with exact edge lists and a periphery rule (protocol §3).
  2. Builds prototype scenarios by calling the FROZEN ``generator_v2.build_scenario`` with its private
     ``_build_topology`` swapped IN MEMORY (process-local monkeypatch; no file is edited). Prototype indices
     start at 100000 so no prototype seed equals any dev/val/held-out seed (and none is a CONFIRM seed).
  3. Labels via the frozen ``compute_ground_truth`` (with the S13/S14 shallow-copy wrapper) and measures
     label x structure x family feasibility, node counts, FCI cap, drift-stratum capacity, topology-hash
     diversity, union-find group geometry, overlap with the frozen generator's design space, cross-set
     similarity to dev/val/adversarial_dev, and what the frozen validators/strip_labels expose.
Writes artifacts/sprint4_5_1/dataset/protocol_checks.json (aggregate statistics only).
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import warnings
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO), str(REPO / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402

from src.rift.scenarios import generator_v2 as gv2  # noqa: E402
from src.rift.scenarios import independence as ind  # noqa: E402
from src.rift.scenarios import simulator as sim  # noqa: E402
from src.rift.scenarios import validators as val  # noqa: E402
from src.rift.scenarios.splitter import build_groups  # noqa: E402

OUT = REPO / "artifacts" / "sprint4_5_1" / "dataset"
AUDIT_SEED = 451301          # analysis seed (not a generation seed)
IDX0 = 100000                # prototype scenario indices (never equal to dev/val indices 1..252)

# ------------------------------------------------------------------------------------ motifs
# name -> (ordered node list (topological order), hidden, latent, edges, roots, mutual)
MOTIFS = {
    "S01_spine_with_leaves": (["r", "a", "b", "c", "la", "lb"], [], [], [("r", "a"), ("a", "b"), ("b", "c"), ("a", "la"), ("b", "lb")], ["r"], []),
    "S02_two_level_fanout": (["r", "a", "b", "c", "a2", "b2", "c2"], [], [], [("r", "a"), ("r", "b"), ("r", "c"), ("a", "a2"), ("b", "b2"), ("c", "c2")], ["r"], []),
    "S03_ladder": (["r", "p", "a", "c", "b", "d"], [], [], [("r", "a"), ("a", "b"), ("p", "c"), ("c", "d"), ("a", "c"), ("b", "d")], ["r"], []),
    "S04_double_diamond": (["r", "a", "b", "d", "e", "f", "g"], [], [], [("r", "a"), ("r", "b"), ("a", "d"), ("b", "d"), ("d", "e"), ("d", "f"), ("e", "g"), ("f", "g")], ["r"], []),
    "S05_late_merge": (["r", "p", "a", "q", "m", "d"], [], [], [("r", "a"), ("a", "m"), ("p", "q"), ("q", "m"), ("m", "d")], ["r"], []),
    "S06_bypass_chain": (["r", "a", "b", "c"], [], [], [("r", "a"), ("a", "b"), ("b", "c"), ("r", "c")], ["r"], []),
    "S07_two_stage_hub": (["f1", "f2", "f3", "h1", "h2", "d"], [], [], [("f1", "h1"), ("f2", "h1"), ("h1", "h2"), ("f3", "h2"), ("h2", "d")], ["f1"], []),
    "S08_triangle_with_tail": (["r", "a", "b", "c"], [], [], [("r", "a"), ("r", "b"), ("a", "b"), ("b", "c")], ["r"], []),
    "S09_staggered_roots": (["r1", "r2", "a", "b", "c"], [], [], [("r1", "a"), ("a", "b"), ("r2", "b"), ("b", "c")], ["r1", "r2"], []),
    "S10_latent_confounded_diamond": (["r", "a", "b", "c"], ["h"], ["h"], [("h", "r"), ("h", "c"), ("r", "a"), ("r", "b"), ("a", "c"), ("b", "c")], ["r"], []),
    "S11_hidden_driver_chain": (["x", "y", "z"], ["h"], [], [("h", "x"), ("x", "y"), ("h", "z")], ["h"], []),
    "S12_hidden_driver_diamond": (["a", "b", "c"], ["h"], [], [("h", "a"), ("h", "b"), ("a", "c"), ("b", "c")], ["h"], []),
    "S13_mutual_pair_merge": (["a", "b", "p", "c", "d"], [], [], [("a", "b"), ("b", "a"), ("b", "c"), ("p", "c"), ("c", "d")], ["a"], [("a", "b")]),
    "S14_mutual_pair_fanout": (["a", "b", "c", "d"], [], [], [("a", "b"), ("b", "a"), ("b", "c"), ("b", "d")], ["a"], [("a", "b")]),
    "S15_sink_with_two_chains": (["r", "p", "a", "q", "s"], [], [], [("r", "a"), ("a", "s"), ("p", "q"), ("q", "s")], ["r"], []),
    "S16_pendant_cluster": (["r", "a", "b", "c", "d"], [], [], [("r", "a"), ("a", "b"), ("a", "c"), ("b", "c"), ("c", "d")], ["r"], []),
}
NEW_STRUCTS = list(MOTIFS)
MUTUAL_STRUCTS = {"S13_mutual_pair_merge", "S14_mutual_pair_fanout"}
HIDDEN_ROOT_STRUCTS = {"S11_hidden_driver_chain", "S12_hidden_driver_diamond"}
FAMS = gv2.FAMILIES


def _proto_topology(kind, extra, names):
    """Prototype of the new topology builder. Periphery rng is derived from the pool names (deterministic)."""
    if kind in gv2.STRUCTURES:
        return _ORIG_TOPO(kind, extra, names)
    order, hidden0, latent0, edges0, roots0, mutual0 = MOTIFS[kind]
    rng = np.random.default_rng(int(hashlib.sha256("|".join(names[:6]).encode()).hexdigest()[:8], 16))
    nm = {}
    it = iter(names)
    for lab in order + hidden0:
        nm[lab] = next(it)
    nodes = [nm[x] for x in order]
    hidden = [nm[x] for x in hidden0]
    latent = [nm[x] for x in latent0]
    roots = [nm[x] for x in roots0]
    edges = [(nm[a], nm[b]) for a, b in edges0]
    mutual = [(nm[a], nm[b]) for a, b in mutual0]
    rank = {nm[x]: i for i, x in enumerate(order)}
    k = int(rng.integers(0, 4))                    # periphery size 0..3 (uniform)
    for _ in range(k):
        u = next(it)
        parents = [n for n in nodes if n not in roots]
        parents = [n for n in parents if not (kind in MUTUAL_STRUCTS and n in {nm[a] for a, _ in mutual0} | {nm[b] for _, b in mutual0})]
        if not parents:
            parents = [n for n in nodes if n not in roots] or nodes
        p = parents[int(rng.integers(0, len(parents)))]
        nodes.append(u)
        edges.append((p, u))
        rank[u] = rank[p] + 0.5
        if rng.random() < 0.5:
            later = [n for n in nodes if n not in roots and rank[n] > rank[u] and n != u
                     and (u, n) not in edges and n not in [x for x in mutual_nodes(mutual)]]
            if later:
                edges.append((u, later[int(rng.integers(0, len(later)))]))
    return {"nodes": nodes, "edges": edges, "hidden": hidden, "latent": latent, "roots": roots, "mutual": mutual}


def mutual_nodes(mutual):
    return [x for p in mutual for x in p]


_ORIG_TOPO = gv2._build_topology
gv2._build_topology = _proto_topology            # in-memory swap only; reverted in main() finally


def label_with_wrapper(sc):
    """Frozen compute_ground_truth with the proposed S13/S14 shallow-copy wrapper (protocol §3.3)."""
    view = dict(sc)
    view["dimensions"] = dict(sc["dimensions"])
    if sc["dimensions"]["structure"] in MUTUAL_STRUCTS:
        view["dimensions"]["structure"] = "ambiguous"
    return gv2.compute_ground_truth(view)


def drift_stat(sc):
    """Protocol §5.3: max over observed y that have >=1 observed non-ancestor x!=y of |d(y)|/sigma_y."""
    g = sim._graph(sc)
    n = int(sc["telemetry"]["n_windows"])
    t_end = (n - 1) * 10.0
    ts = np.concatenate([t_end + np.arange(30.0), t_end + 30.0 + np.arange(30.0)])
    obs = sim.observed_services(sc)
    best = 0.0
    for y in obs:
        if not any(x != y and not nx.has_path(g, x, y) for x in obs):
            continue
        fs = sim.fault_series(sc, g, y, ts)
        best = max(best, abs(float((fs[30:].mean() - fs[:30].mean()) / sim.sigma_of(sc, y))))
    return best


def make_candidates(M, rng):
    """Mimic generate_split's schedule over 16x16 = 256 cells."""
    cells = [(s, f) for s in NEW_STRUCTS for f in FAMS]
    order = [cells[i] for i in rng.permutation(len(cells))]
    work = gv2._cyc(gv2.WORKLOADS, M, rng)
    obsv = gv2._cyc(gv2.OBSERVABILITY, M, rng)
    ivs = gv2._cyc(gv2.INTERVENTIONS, M, rng)
    tall = gv2._cyc(gv2.TEMPORAL, M, rng)
    tlag = gv2._cyc(gv2.LAG_ONLY_TEMPORAL, M, rng)
    negs = gv2._cyc(gv2.NEGATIVES, M, rng)
    out, ni, ptr = [], 0, 0
    for j in range(M):
        neg, cell = None, None
        if j % 4 == 3:
            neg = negs[ni]; ni += 1
            need = {"common_cause_several_services": sorted(HIDDEN_ROOT_STRUCTS),
                    "root_not_identifiable": sorted(MUTUAL_STRUCTS)}.get(neg)
            if need:
                opts = [c for c in cells if c[0] in need]
                cell = opts[(j // 4) % len(opts)]
        if cell is None:
            cell = order[ptr % len(order)]; ptr += 1
        s, f = cell
        if neg in gv2.NEEDS_EDGE and s in HIDDEN_ROOT_STRUCTS:
            neg = "coincidental_anomaly"
        temporal = tlag[j] if f in gv2.FAMILY_SHAPE else tall[j]
        out.append((j, s, f, temporal, work[j], obsv[j], ivs[j], neg))
    return out


def build_proto(c):
    j, s, f, t, w, o, i, n = c
    sc = gv2.build_scenario("dev", IDX0 + j, s, f, t, w, o, i, n)
    sc["ground_truth"] = label_with_wrapper(sc)
    sc["content_hash"] = gv2.content_hash(sc)
    return sc


def shape_of(sc):
    return sorted({f["shape"] for f in sc["faults"]})


def main():
    M = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 6000
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rng = np.random.default_rng(AUDIT_SEED)
    res = {"purpose": "analysis-only structural prototype; no confirmatory data; no held-out access",
           "audit_seed": AUDIT_SEED, "prototype_indices": f"{IDX0}..{IDX0 + M - 1}", "M": M}
    try:
        cands = make_candidates(M, rng)
        scs = [build_proto(c) for c in cands]
        res["build_seconds"] = round(time.time() - t0, 1)

        # ---------------------------------------------------------------- 1. structure / size checks
        n_tot = [len(s["graph"]["nodes"]) for s in scs]
        n_obs = [len(sim.observed_services(s)) for s in scs]
        res["node_counts"] = {"total_incl_hidden_max": int(max(n_tot)), "observed_max": int(max(n_obs)),
                              "observed_mean": float(np.mean(n_obs)), "gt_12_total": int(sum(x > 12 for x in n_tot)),
                              "fci_cap_15_exceeded": int(sum(x > 15 for x in n_obs))}
        dag_bad = []
        for s in scs:
            g = nx.DiGraph([(e["src"], e["dst"]) for e in s["graph"]["edges"]])
            cyc = not nx.is_directed_acyclic_graph(g)
            want = s["dimensions"]["structure"] in MUTUAL_STRUCTS
            if cyc != want:
                dag_bad.append(s["scenario_id"])
        res["cycle_consistency_violations"] = len(dag_bad)
        mut_cycle_sizes = Counter()
        for s in scs:
            if s["dimensions"]["structure"] in MUTUAL_STRUCTS:
                g = nx.DiGraph([(e["src"], e["dst"]) for e in s["graph"]["edges"]])
                mut_cycle_sizes[max(len(c) for c in nx.strongly_connected_components(g))] += 1
        res["mutual_scc_sizes"] = {str(k): v for k, v in mut_cycle_sizes.items()}

        # ---------------------------------------------------------------- 2. label feasibility
        lab = lambda s: (s["ground_truth"]["expected_outcome"] if s["ground_truth"]["expected_outcome"] == "ATTRIBUTE"
                         else s["ground_truth"]["abstain_reason"])
        L = [lab(s) for s in scs]
        res["natural_label_share"] = {k: round(v / M, 4) for k, v in sorted(Counter(L).items())}
        by_struct = defaultdict(Counter)
        by_fam = defaultdict(Counter)
        for s, l in zip(scs, L):
            by_struct[s["dimensions"]["structure"]][l] += 1
            by_fam[s["dimensions"]["family"]][l] += 1
        res["label_share_by_structure"] = {k: {a: round(b / sum(c.values()), 3) for a, b in sorted(c.items())} for k, c in sorted(by_struct.items())}
        res["attribute_share_by_family"] = {k: round(c["ATTRIBUTE"] / sum(c.values()), 3) for k, c in sorted(by_fam.items())}
        res["attribute_share_by_structure"] = {k: round(c["ATTRIBUTE"] / sum(c.values()), 3) for k, c in sorted(by_struct.items())}
        sym_ok = all(l == "SYMMETRIC_MUTUAL_DEPENDENCY" or s["ground_truth"]["abstain_reason"] in ("NO_FAULT", "ROOT_UNOBSERVED")
                     for s, l in zip(scs, L) if s["dimensions"]["structure"] in MUTUAL_STRUCTS)
        unobs_ok = all(l in ("ROOT_UNOBSERVED", "NO_FAULT") for s, l in zip(scs, L) if s["dimensions"]["structure"] in HIDDEN_ROOT_STRUCTS)
        nonroute = [l for s, l in zip(scs, L) if s["dimensions"]["structure"] not in MUTUAL_STRUCTS | HIDDEN_ROOT_STRUCTS and l in ("SYMMETRIC_MUTUAL_DEPENDENCY", "ROOT_UNOBSERVED")]
        res["label_routes"] = {"S13_S14_only_SYMMETRIC_or_NOFAULT_or_UNOBS": bool(sym_ok), "S11_S12_only_UNOBS_or_NOFAULT": bool(unobs_ok),
                               "other_structures_producing_SYMMETRIC_or_UNOBS": len(nonroute)}
        # unwrapped (what the frozen label function does with the real new name)
        unw = Counter()
        for s in scs:
            if s["dimensions"]["structure"] in MUTUAL_STRUCTS:
                unw[gv2.compute_ground_truth(s)["abstain_reason"] or "ATTRIBUTE"] += 1
        res["S13_S14_labels_WITHOUT_wrapper"] = dict(unw)

        # quota feasibility vs the protocol §5.2 targets, given the per-structure counts the schedule yields
        quotas = {"ATTRIBUTE": 800, "WEAK_SIGNAL": 360, "ROOT_UNOBSERVED": 240, "SYMMETRIC_MUTUAL_DEPENDENCY": 180,
                  "INSUFFICIENT_BASELINE": 180, "NO_DISCRIMINATING_EVIDENCE": 140, "NO_FAULT": 100}
        res["quota_vs_natural_in_12000"] = {k: {"quota": q, "natural_share": res["natural_label_share"].get(k, 0.0),
                                                 "expected_in_12000": int(res["natural_label_share"].get(k, 0.0) * 12000),
                                                 "ratio_available_over_quota": round(res["natural_label_share"].get(k, 0.0) * 12000 / q, 2)}
                                            for k, q in quotas.items()}
        # structure supply of ATTRIBUTE (non-route structures only)
        supply = {s: res["attribute_share_by_structure"].get(s, 0.0) for s in NEW_STRUCTS}
        res["structures_able_to_supply_ATTRIBUTE"] = [s for s, v in supply.items() if v > 0.0]
        # ATTRIBUTE needed per family if per-family count 125 and attribute 40%: families whose natural share < 0.40 cannot meet it
        res["families_with_attribute_share_below_0.40"] = [f for f, v in res["attribute_share_by_family"].items() if v < 0.40]

        # ---------------------------------------------------------------- 3. drift stratum
        t1 = time.time()
        subset = scs[: min(M, 3000)]
        ds = [drift_stat(s) for s in subset]
        res["drift_stratum_natural"] = {"n": len(ds), "none_lt_0.1": round(float(np.mean([d < 0.1 for d in ds])), 4),
                                        "mild_0.1_0.3": round(float(np.mean([0.1 <= d < 0.3 for d in ds])), 4),
                                        "substantial_ge_0.3": round(float(np.mean([d >= 0.3 for d in ds])), 4),
                                        "seconds": round(time.time() - t1, 1)}
        shp = defaultdict(list)
        for s, d in zip(subset, ds):
            shp["+".join(shape_of(s))].append(d)
        res["drift_by_fault_shape"] = {k: {"n": len(v), "share_substantial": round(float(np.mean([x >= 0.3 for x in v])), 3),
                                           "max": round(float(max(v)), 2)} for k, v in sorted(shp.items())}
        sub_att = [d >= 0.3 for s, d in zip(subset, ds) if s["ground_truth"]["expected_outcome"] == "ATTRIBUTE"]
        sub_abs = [d >= 0.3 for s, d in zip(subset, ds) if s["ground_truth"]["expected_outcome"] != "ATTRIBUTE"]
        res["drift_substantial_share_by_outcome"] = {"ATTRIBUTE": round(float(np.mean(sub_att)), 3), "ABSTAIN_REQUIRED": round(float(np.mean(sub_abs)), 3)}
        res["drift_note"] = ("In frozen sim.intervene() the only source of change between the baseline and post 30 s windows that "
                             "does not come from do(x) is fault_series (workload drift_sigma and AR(1) latent are NOT applied to the do() windows). "
                             "The drift stratum is therefore a function of fault shape/temporal level, by construction.")

        # ---------------------------------------------------------------- 4. topology diversity / groups
        topo = [ind.topology_hash(s) for s in scs]
        tid = [s["template_id"] for s in scs]
        for N in (2000, 4000, 6000):
            if N > M:
                continue
            sub = scs[:N]
            th = topo[:N]
            cnt = Counter(th)
            uniq_share = sum(1 for t in th if cnt[t] == 1) / N
            items = {s["scenario_id"]: s for s in sub}
            grp = build_groups(items, [lambda s: ("t", s["template_id"]), lambda s: ("topo", ind.topology_hash(s))])
            gs = Counter(grp.values())
            grp_topo_only = build_groups(items, [lambda s: ("topo", ind.topology_hash(s))])
            gs2 = Counter(grp_topo_only.values())
            res[f"geometry_first_{N}_candidates"] = {
                "distinct_topology_hashes": len(cnt), "share_scenarios_with_unique_topology": round(uniq_share, 4),
                "max_scenarios_per_topology": int(max(cnt.values())), "n_topologies_shared_by_gt3": int(sum(v > 3 for v in cnt.values())),
                "union_find_groups_template_or_topology": len(gs), "max_group_size": int(max(gs.values())),
                "group_size_quantiles_50_90_99": [int(np.quantile(list(gs.values()), q)) for q in (0.5, 0.9, 0.99)],
                "groups_topology_only": len(gs2), "max_group_size_topology_only": int(max(gs2.values()))}
        # topology hashes per structure (diversity ceiling)
        per_struct_topo = defaultdict(set)
        for s, t in zip(scs, topo):
            per_struct_topo[s["dimensions"]["structure"]].add(t)
        res["distinct_topology_hashes_per_structure_in_M"] = {k: len(v) for k, v in sorted(per_struct_topo.items())}
        shared_across_struct = defaultdict(set)
        for s, t in zip(scs, topo):
            shared_across_struct[t].add(s["dimensions"]["structure"])
        res["topology_hashes_shared_by_>=2_structures"] = int(sum(len(v) > 1 for v in shared_across_struct.values()))

        # ---------------------------------------------------------------- 5. overlap with frozen design space (T5 proxy)
        lib = set()
        for kind in gv2.STRUCTURES:
            for extra in range(0, 5):
                names = [f"n{i}" for i in range(40)]
                tp = _ORIG_TOPO(kind, extra, names)
                base_nodes = [{"id": n, "hidden": False} for n in tp["nodes"]] + [{"id": n, "hidden": True} for n in tp["hidden"]]
                edges = [{"src": a, "dst": b} for a, b in tp["edges"]]
                obs_ids = [n["id"] for n in base_nodes if not n["hidden"]]
                root_sets = [list(tp["hidden"]) if kind == "hidden_common_cause" else list(tp["roots"]), []]
                for roots in root_sets:
                    variants = [(base_nodes, edges, roots)]
                    dn = base_nodes + [{"id": "decoy", "hidden": False}]
                    variants.append((dn, edges, roots + ["decoy"] if roots else roots))
                    for bn, ed, rts in list(variants):
                        z = {"id": "zz", "hidden": True}
                        ed2 = ed + [{"src": "zz", "dst": n["id"]} for n in bn if not n["hidden"]]
                        variants.append((bn + [z], ed2, rts))
                    # secondary overlapping fault on any non-root observed node
                    for n in obs_ids:
                        if n not in roots:
                            variants.append((base_nodes, edges, roots + [n]))
                    for bn, ed, rts in variants:
                        scx = {"graph": {"nodes": bn, "edges": ed}, "faults": [{"service": r} for r in rts]}
                        lib.add(ind.topology_hash(scx))
        res["frozen_design_space_topology_hashes"] = len(lib)
        res["prototype_topology_hashes_in_frozen_design_space"] = int(sum(t in lib for t in topo))
        res["prototype_topology_hashes_in_frozen_design_space_distinct"] = len(set(t for t in topo if t in lib))
        in_lib_by_struct = Counter(s["dimensions"]["structure"] for s, t in zip(scs, topo) if t in lib)
        res["in_frozen_design_space_by_new_structure"] = dict(in_lib_by_struct)

        # ---------------------------------------------------------------- 6. readable protected sets
        dev = json.load(open(REPO / "datasets/rift_v2/dev.json"))["scenarios"]
        valid = json.load(open(REPO / "datasets/rift_v2/val.json"))["scenarios"]
        adv = json.load(open(REPO / "datasets/rift_v3_dev/adversarial_dev.json"))["scenarios"]
        readable = {"dev": dev, "val": valid, "adv": adv}
        rtop = {k: {ind.topology_hash(s) for s in v} for k, v in readable.items()}
        res["prototype_topology_hash_overlap_with_readable"] = {k: int(sum(t in rtop[k] for t in topo)) for k in readable}
        prot_t = set().union(*rtop.values())
        res["prototype_scenarios_whose_topology_hash_in_dev_val_adv"] = int(sum(t in prot_t for t in topo))
        # cross-set max spec similarity (vectorised replication of independence.spec_similarity)
        allp = [s for sets in readable.values() for s in sets]
        cats = ("structure", "family", "temporal", "workload", "observability", "intervention", "negative")
        Pv = np.array([ind.spec_vector(s) for s in allp])
        Pc = np.array([[hash_cat(s["dimensions"][k]) for k in cats] for s in allp])
        sub = scs[:2000]
        Cv = np.array([ind.spec_vector(s) for s in sub])
        Cc = np.array([[hash_cat(s["dimensions"][k]) for k in cats] for s in sub])
        mx, cnt90, cnt88 = [], 0, 0
        for i in range(len(sub)):
            cat = (Pc == Cc[i]).sum(axis=1)
            num = 1.0 - np.mean(np.abs(Pv - Cv[i]), axis=1)
            sim_ = 0.6 * cat / 7.0 + 0.4 * num
            mx.append(float(sim_.max()))
        mx = np.array(mx)
        res["cross_set_max_spec_similarity_first_2000"] = {"max": round(float(mx.max()), 4), "p99": round(float(np.quantile(mx, 0.99)), 4),
                                                           "p50": round(float(np.quantile(mx, 0.5)), 4),
                                                           "n_ge_0.88": int((mx >= 0.88).sum()), "n_ge_0.90": int((mx >= 0.90).sum())}
        # within-set near duplicates
        Cn = Cv
        within90 = within88 = 0
        pairs_cat7 = 0
        for i in range(len(sub)):
            cat = (Cc[i + 1:] == Cc[i]).sum(axis=1)
            num = 1.0 - np.mean(np.abs(Cv[i + 1:] - Cv[i]), axis=1)
            s_ = 0.6 * cat / 7.0 + 0.4 * num
            within90 += int((s_ >= 0.90).sum())
            within88 += int((s_ >= 0.88).sum())
        res["within_set_pairs_first_2000"] = {"spec_sim_ge_0.90": within90, "spec_sim_ge_0.88": within88, "total_pairs": len(sub) * (len(sub) - 1) // 2}
        res["max_possible_cross_structure_similarity"] = round(0.6 * 6 / 7 + 0.4, 4)
        res["cross_structure_numeric_part_needed_for_0.90"] = round((0.90 - 0.6 * 6 / 7) / 0.4, 4)

        # ---------------------------------------------------------------- 7. what the frozen interfaces expose
        sample = scs[0]
        stripped = ind.strip_labels(sample)
        res["strip_labels_keys_that_survive"] = sorted(stripped)
        res["strip_labels_removed"] = list(ind.LABEL_FIELDS)
        res["leak_surface_in_strip_labels"] = {
            "faults[].service == true root ids": bool(stripped["faults"]),
            "dimensions.structure (reveals S11-S14 label route)": "structure" in stripped["dimensions"],
            "graph.nodes[].hidden flags": any("hidden" in n for n in stripped["graph"]["nodes"]) or True,
            "telemetry.unobserved": "unobserved" in stripped["telemetry"],
            "intervention (co_target/collateral)": "intervention" in stripped,
        }
        o = sim.observe(sample)
        res["observe_output_keys"] = sorted(o)
        res["observe_call_graph_includes_decoy_edges"] = True
        first_is_root = 0
        n_with_root = 0
        for s in scs[:600]:
            gtr = s["ground_truth"]["roots"]
            if not gtr:
                continue
            n_with_root += 1
            first_is_root += int(sim.observed_services(s)[0] == gtr[0])
        res["PROTOTYPE_observed_node_order_root_first"] = {"root_is_first_observed_service": first_is_root, "of": n_with_root}
        fo = f_dev = 0
        for s in dev + valid:
            gtr = s["ground_truth"]["roots"]
            if gtr:
                f_dev += 1
                fo += int(sim.observed_services(s)[0] == gtr[0])
        res["FROZEN_dev_val_observed_node_order_root_first"] = {"root_is_first_observed_service": fo, "of": f_dev}

        # ---------------------------------------------------------------- 8. frozen validators on new structures
        vres = {}
        for tag, struct in (("S01", "S01_spine_with_leaves"), ("S13", "S13_mutual_pair_merge")):
            s = next(x for x in scs if x["dimensions"]["structure"] == struct)
            r = val.validate_scenario(s, reproducibility=False)
            vres[tag] = {k: v[:3] for k, v in r.items() if v}
            try:
                val.check_reproducible(s)
                vres[tag + "_reproducible_check"] = "ran"
            except Exception as exc:  # noqa: BLE001
                vres[tag + "_reproducible_check"] = f"raises {type(exc).__name__}"
        res["frozen_validators_on_new_structures"] = vres

        # ---------------------------------------------------------------- 9. T1 (replication) realisability on dev/val
        gv2._build_topology = _ORIG_TOPO
        ok = tot = 0
        for s in dev[:60] + valid[:30]:
            d = s["dimensions"]
            idx = int(s["scenario_id"].rsplit("-", 1)[1])
            again = gv2.build_scenario(s["split"], idx, d["structure"], d["family"], d["temporal"], d["workload"],
                                       d["observability"], d["intervention"], d["negative"])
            tot += 1
            ok += int(again["content_hash"] == s["content_hash"])
        res["T1_frozen_builder_reproduces_stored_dev_val_content_hash"] = {"match": ok, "of": tot}
        keys_in_hash = sorted(k for k in dev[0] if k not in {"scenario_id", "seed", "split", "content_hash", "parent_scenario"})
        res["content_hash_covers_keys"] = keys_in_hash
        res["T1_requires"] = ("same rng draw order, same seed value (= sha256 of the FROZEN tag|split|idx), same generator_version string "
                              "(it is INSIDE content_hash), same dimensions incl. size_extra; the scenario_id/seed/split fields are excluded from the hash")
    finally:
        gv2._build_topology = _ORIG_TOPO
    res["total_seconds"] = round(time.time() - t0, 1)
    (OUT / "protocol_checks.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str)[:6000])
    return 0


def hash_cat(x):
    return int(hashlib.md5(str(x).encode()).hexdigest()[:8], 16)


# ======================================================================================= extra modes
def build_library():
    """Topology hashes reachable by the FROZEN design space (topology only; no seeds, no scenario files):
    11 kinds x extra 0..4 x {true roots | no roots} x all combinations of {decoy node, hidden zz-confounder,
    secondary overlapping fault on any non-root observed node}."""
    from itertools import product
    lib = set()
    for kind in gv2.STRUCTURES:
        for extra in range(0, 5):
            tp = _ORIG_TOPO(kind, extra, [f"n{i}" for i in range(40)])
            base = [{"id": n, "hidden": False} for n in tp["nodes"]] + [{"id": n, "hidden": True} for n in tp["hidden"]]
            edges = [{"src": a, "dst": b} for a, b in tp["edges"]]
            obs_ids = [n["id"] for n in base if not n["hidden"]]
            for roots0 in (list(tp["hidden"]) if kind == "hidden_common_cause" else list(tp["roots"]), []):
                for decoy, zz, sec in product((0, 1), (0, 1), [None] + [n for n in obs_ids if n not in roots0]):
                    nodes, ed, roots = list(base), list(edges), list(roots0)
                    if decoy:
                        nodes.append({"id": "decoy", "hidden": False})
                        if roots:
                            roots.append("decoy")
                    if zz:
                        ed = ed + [{"src": "zz", "dst": n["id"]} for n in nodes if not n["hidden"]]
                        nodes.append({"id": "zz", "hidden": True})
                    if sec is not None:
                        roots.append(sec)
                    lib.add(ind.topology_hash({"graph": {"nodes": nodes, "edges": ed}, "faults": [{"service": r} for r in roots]}))
    return lib


def _readable():
    dev = json.load(open(REPO / "datasets/rift_v2/dev.json"))["scenarios"]
    val_ = json.load(open(REPO / "datasets/rift_v2/val.json"))["scenarios"]
    adv = json.load(open(REPO / "datasets/rift_v3_dev/adversarial_dev.json"))["scenarios"]
    return dev, val_, adv


CATS = ("structure", "family", "temporal", "workload", "observability", "intervention", "negative")


def _catvec(s):
    return np.array([hash_cat(s["dimensions"][k]) for k in CATS])


# explicit integer quota matrix proposed for protocol section 5.2 (structure -> label -> n)
A_STRUCTS = ["S01_spine_with_leaves", "S02_two_level_fanout", "S03_ladder", "S04_double_diamond", "S05_late_merge",
             "S06_bypass_chain", "S07_two_stage_hub", "S08_triangle_with_tail", "S09_staggered_roots",
             "S10_latent_confounded_diamond", "S15_sink_with_two_chains", "S16_pendant_cluster"]


def quota_matrix():
    """Proposed integer quota table (structure x label). Row sums: 12 attributable-capable structures 131-132, S11/S12 125,
    S13/S14 90 (declared exception: only SYMMETRIC_MUTUAL_DEPENDENCY is reachable there). Column sums: ATTRIBUTE 800,
    WEAK_SIGNAL 360, ROOT_UNOBSERVED 240, SYMMETRIC 180, INSUFFICIENT_BASELINE 180, NO_DISCRIMINATING_EVIDENCE 140, NO_FAULT 100."""
    q = {}
    for i, s in enumerate(A_STRUCTS):
        q[s] = {"ATTRIBUTE": 67 if i < 8 else 66, "WEAK_SIGNAL": 30, "INSUFFICIENT_BASELINE": 15,
                "NO_DISCRIMINATING_EVIDENCE": 12 if i < 8 else 11, "NO_FAULT": 8 if i % 2 == 0 else 7}
    for s in ("S11_hidden_driver_chain", "S12_hidden_driver_diamond"):
        q[s] = {"ROOT_UNOBSERVED": 120, "NO_FAULT": 5}
    for s in ("S13_mutual_pair_merge", "S14_mutual_pair_fanout"):
        q[s] = {"SYMMETRIC_MUTUAL_DEPENDENCY": 90}
    return q


def _label(sc):
    gt = sc["ground_truth"]
    return "ATTRIBUTE" if gt["expected_outcome"] == "ATTRIBUTE" else gt["abstain_reason"]


CAP = int(__import__("os").environ.get("CONFIRM_CAP", "3"))
OWN = __import__("os").environ.get("CONFIRM_OWN", "1") == "1"
DRIFT_SUBQ = None   # fraction of each cell reserved for 'substantial' drift (None = natural, no drift rule)


def accept_once(off, budget, lib, readable_topos, rv, rcat, use_dup=True):
    """One simulated generation attempt of the proposed acceptance process (label/state-only rules)."""
    Q = quota_matrix()
    rng_master = np.random.default_rng(900000 + off)
    owner, per_hash = {}, Counter()
    acc, rej = [], Counter()
    av, ac = [], []
    for si, s in enumerate(NEW_STRUCTS):
        rng = np.random.default_rng(int(rng_master.integers(1, 2**31)))
        R = sum(Q[s].values())
        fam_perm = [FAMS[i] for i in rng.permutation(16)]
        cap = {f: R // 16 + (1 if i < R % 16 else 0) for i, f in enumerate(fam_perm)}
        cnt_t, cnt_lab, cnt_sub = Counter(), Counter(), Counter()
        fam_cycle = gv2._cyc(FAMS, budget, rng)
        work = gv2._cyc(gv2.WORKLOADS, budget, rng); obsv = gv2._cyc(gv2.OBSERVABILITY, budget, rng)
        ivs = gv2._cyc(gv2.INTERVENTIONS, budget, rng); tall = gv2._cyc(gv2.TEMPORAL, budget, rng)
        tlag = gv2._cyc(gv2.LAG_ONLY_TEMPORAL, budget, rng); negs = gv2._cyc(gv2.NEGATIVES, budget, rng)
        ni = 0
        for k in range(budget):
            neg = None
            if k % 4 == 3:
                neg = negs[ni]; ni += 1
                if neg == "common_cause_several_services" and s not in HIDDEN_ROOT_STRUCTS:
                    neg = "coincidental_anomaly"
                if neg == "root_not_identifiable" and s not in MUTUAL_STRUCTS:
                    neg = "indistinguishable_onsets"
                if neg in gv2.NEEDS_EDGE and s in HIDDEN_ROOT_STRUCTS:
                    neg = "coincidental_anomaly"
            f = fam_cycle[k]
            t = tlag[k] if f in gv2.FAMILY_SHAPE else tall[k]
            sc = gv2.build_scenario("dev", 200000 + off * 20000 + si * 1000 + k, s, f, t, work[k], obsv[k], ivs[k], neg)
            sc["ground_truth"] = label_with_wrapper(sc)
            lab = _label(sc)
            tid = sc["template_id"]; th = ind.topology_hash(sc)
            if cnt_lab[lab] >= Q[s].get(lab, 0):
                rej["cell_full_or_label_not_in_quota"] += 1; continue
            dstat = None
            if DRIFT_SUBQ is not None:
                dstat = drift_stat(sc)
                is_sub = dstat >= 0.3
                nsub = cnt_sub[lab]; ncell = cnt_lab[lab]
                capsub = int(np.ceil(DRIFT_SUBQ * Q[s][lab]))
                if is_sub and nsub >= capsub:
                    rej["drift_sub_cap"] += 1; continue
                if (not is_sub) and (ncell - nsub) >= Q[s][lab] - capsub:
                    rej["drift_nonsub_cap"] += 1; continue
            if cnt_t[tid] >= cap[f]:
                rej["template_full"] += 1; continue
            if th in lib or th in readable_topos:
                rej["R-NOVEL"] += 1; continue
            if OWN and th in owner and owner[th] != tid:
                rej["R-OWN"] += 1; continue
            if per_hash[th] >= CAP:
                rej[f"R-CAP{CAP}"] += 1; continue
            if use_dup:
                v, c = ind.spec_vector(sc), _catvec(sc)
                bad = False
                for (V, C, thr, tag) in ((rv, rcat, 0.88, "R-DUP-readable"),
                                          (np.array(av) if av else None, np.array(ac) if ac else None, 0.90, "R-DUP-within")):
                    if V is None or len(V) == 0:
                        continue
                    simv = 0.6 * (C == c).sum(axis=1) / 7.0 + 0.4 * (1.0 - np.mean(np.abs(V - v), axis=1))
                    if simv.max() >= thr:
                        rej[tag] += 1; bad = True; break
                if bad:
                    continue
                av.append(v); ac.append(c)
            owner.setdefault(th, tid); per_hash[th] += 1; cnt_t[tid] += 1; cnt_lab[lab] += 1
            if DRIFT_SUBQ is not None and dstat >= 0.3:
                cnt_sub[lab] += 1
            acc.append((s, f, lab, tid, th, sc["ground_truth"]["expected_outcome"], drift_stat(sc), sc["dimensions"]["temporal"], sc))
    return acc, rej, Q


def acceptance_mode():
    global DRIFT_SUBQ
    nseeds = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    DRIFT_SUBQ = float(sys.argv[4]) if len(sys.argv) > 4 else None
    budget = int(sys.argv[3]) if len(sys.argv) > 3 else 750
    lib = build_library()
    dev, val_, adv = _readable()
    readable_topos = {ind.topology_hash(s) for sets in (dev, val_, adv) for s in sets}
    rall = dev + val_ + adv
    rv = np.array([ind.spec_vector(s) for s in rall]); rcat = np.array([_catvec(s) for s in rall])
    out = {"purpose": "simulated acceptance process (prototype indices >= 200000; no CONFIRM seed; no method run)",
           "budget_per_structure": budget, "topology_cap": CAP, "ownership_rule": OWN, "drift_subquota": DRIFT_SUBQ, "attempts": []}
    gv2._build_topology = _proto_topology
    try:
        for off in range(nseeds):
            t0 = time.time()
            acc, rej, Q = accept_once(off, budget, lib, readable_topos, rv, rcat)
            n = len(acc)
            labs = Counter(a[2] for a in acc)
            qtot = Counter()
            for s, d in Q.items():
                for l, v in d.items():
                    qtot[l] += v
            short = {f"{s}:{l}": Q[s][l] - sum(1 for a in acc if a[0] == s and a[2] == l) for s in Q for l in Q[s]
                     if sum(1 for a in acc if a[0] == s and a[2] == l) < Q[s][l]}
            tcount = Counter(a[3] for a in acc)
            items = {f"x{i}": {"template_id": a[3], "graph": None, "th": a[4]} for i, a in enumerate(acc)}
            grp = build_groups(items, [lambda s: ("t", s["template_id"]), lambda s: ("topo", s["th"])])
            gs = Counter(grp.values())
            th_counts = Counter(a[4] for a in acc)
            famc = Counter(a[1] for a in acc)
            out["attempts"].append({
                "offset": off, "accepted": n, "target": sum(qtot.values()), "labels": dict(labs),
                "unfilled_cells": short, "n_unfilled_cells": len(short), "unfilled_total": sum(short.values()),
                "templates_populated": len(tcount), "template_size_min_max": [min(tcount.values()), max(tcount.values())],
                "union_find_groups": len(gs), "max_group_size": max(gs.values()),
                "groups_equal_templates": len(gs) == len(tcount),
                "unique_topology_share": round(sum(1 for a in acc if th_counts[a[4]] == 1) / max(n, 1), 3),
                "distinct_topologies": len(th_counts), "max_scen_per_topology": max(th_counts.values()),
                "family_count_min_max": [min(famc.values()), max(famc.values())],
                "rejections": dict(rej), "seconds": round(time.time() - t0, 1),
                "drift_substantial_n": int(sum(a[6] >= 0.3 for a in acc)),
                "drift_substantial_share": round(sum(a[6] >= 0.3 for a in acc) / max(n, 1), 3),
                "drift_substantial_share_ATTRIBUTE": round(sum(a[6] >= 0.3 for a in acc if a[5] == "ATTRIBUTE") / max(sum(a[5] == "ATTRIBUTE" for a in acc), 1), 3),
                "drift_substantial_share_ABSTAIN": round(sum(a[6] >= 0.3 for a in acc if a[5] != "ATTRIBUTE") / max(sum(a[5] != "ATTRIBUTE" for a in acc), 1), 3),
                "drift_none_share": round(sum(a[6] < 0.1 for a in acc) / max(n, 1), 3),
                "drift_mild_share": round(sum(0.1 <= a[6] < 0.3 for a in acc) / max(n, 1), 3),
                "substantial_groups(templates)": len({a[3] for a in acc if a[6] >= 0.3}),
                "attribute_per_family_min_max": [min(Counter(a[1] for a in acc if a[5] == "ATTRIBUTE").values()),
                                                 max(Counter(a[1] for a in acc if a[5] == "ATTRIBUTE").values())],
                "attribute_in_partial_degradation": sum(1 for a in acc if a[5] == "ATTRIBUTE" and a[1] == "partial_degradation"),
                "templates_with_zero_ATTRIBUTE": len({a[3] for a in acc}) - len({a[3] for a in acc if a[5] == "ATTRIBUTE"}),
                "structure_counts": dict(Counter(a[0] for a in acc))})
            print(off, out["attempts"][-1]["accepted"], out["attempts"][-1]["n_unfilled_cells"], out["attempts"][-1]["union_find_groups"], flush=True)
        # natural supply per (structure, label) at the budget, from the last attempt's rejections is not enough: measure directly
    finally:
        gv2._build_topology = _ORIG_TOPO
    (OUT / (f"acceptance_sim_cap{CAP}_own{int(OWN)}_b{budget}.json" if DRIFT_SUBQ is None else "acceptance_sim_driftquota.json")).write_text(json.dumps(out, indent=1, default=str))
    return 0


def devval_mode():
    dev, val_, adv = _readable()
    lib = build_library()
    res = {"purpose": "readable-set properties (dev, val): drift stratum prevalence, library completeness"}
    for name, sets in (("dev", dev), ("val", val_), ("adv", adv)):
        ds = []
        for sc in sets:
            try:
                ds.append(drift_stat(sc))
            except Exception:  # noqa: BLE001
                ds.append(float("nan"))
        ds = np.array(ds)
        res[f"{name}_drift_stratum_scenarios"] = {"n": int(len(ds)), "none_lt_0.1": round(float(np.nanmean(ds < 0.1)), 3),
                                                  "mild": round(float(np.nanmean((ds >= 0.1) & (ds < 0.3))), 3),
                                                  "substantial_ge_0.3": round(float(np.nanmean(ds >= 0.3)), 3),
                                                  "n_substantial": int(np.nansum(ds >= 0.3))}
    th_dv = [ind.topology_hash(s) for s in dev + val_]
    res["frozen_library_size"] = len(lib)
    res["library_completeness_on_dev_val"] = {"dev_val_scenarios_with_topology_in_library": int(sum(t in lib for t in th_dv)), "of": len(th_dv),
                                              "note": "dev/val use extra 0..2; completeness of the extra=3 (sealed) band is by identical code path, not measured"}
    miss = [s["template_id"] for s, t in zip(dev + val_, th_dv) if t not in lib]
    res["library_misses_by_structure"] = dict(Counter(m.split("|")[0] for m in miss))
    (OUT / "devval_checks.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1))
    return 0


def order_mode():
    """Does the root-first insertion order of observe()['metrics'] change any method's output? (dev only, readable)"""
    from src.rift.attribution_v3.rift_v3 import V3_CONFIGS, run_v3
    from src.rift.evaluation import benchmark_v2 as bm
    from src.rift.evaluation.rift_v2 import SharedCache
    dev, val_, _ = _readable()
    L = bm._legacy()
    keys = ["B0E", "B0H", "B1", "B3", "B5", "B7"]
    diff = Counter(); n = 0; first_root = 0
    for sc in dev[:int(sys.argv[2]) if len(sys.argv) > 2 else 180]:
        o = sim.observe(sc)
        ks = list(o["metrics"])
        rev = dict(o, metrics={k: o["metrics"][k] for k in reversed(ks)})
        shuf_keys = list(np.random.default_rng(7).permutation(len(ks)))
        n += 1
        if sc["ground_truth"]["roots"] and ks[0] == sc["ground_truth"]["roots"][0]:
            first_root += 1
        for k in keys:
            outs = []
            for oo in (o, rev):
                ctx = bm.make_context(sc, oo)
                try:
                    r = L[k]().run(ctx)
                    outs.append((bool(r.abstained), r.top_candidates[0][0] if r.top_candidates else None))
                except Exception as exc:  # noqa: BLE001
                    outs.append(("ERR", type(exc).__name__))
            diff[k] += int(outs[0] != outs[1])
        iv = lambda x, ys, sd: sim.intervene(sc, x, ys, sd)  # noqa: E731
        outs = []
        for oo in (o, rev):
            r = run_v3(oo, iv, sc["scenario_id"], int(sc["seed"]), V3_CONFIGS["V3-FULL"], cache=SharedCache())
            outs.append((bool(r.abstained), r.top_candidates[0][0] if r.top_candidates else None, r.abstention_reason))
        diff["V3-FULL"] += int(outs[0] != outs[1])
    res = {"purpose": "sensitivity of method outputs to the insertion order of observe()['metrics'] (dev only)",
           "n_dev_scenarios": n, "first_metric_key_is_true_root": first_root,
           "n_scenarios_where_output_changed_after_reversing_order": dict(diff)}
    (OUT / "order_leak_check.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return 0


def indep_mode():
    """Full independence.verify_independence on one SIMULATED accepted set vs dev/val/adv (label-stripped), plus the CONFIRM-restricted pass rule."""
    dev, val_, adv = _readable()
    lib = build_library()
    readable_topos = {ind.topology_hash(s) for sets in (dev, val_, adv) for s in sets}
    rall = dev + val_ + adv
    rv = np.array([ind.spec_vector(s) for s in rall]); rcat = np.array([_catvec(s) for s in rall])
    gv2._build_topology = _proto_topology
    try:
        acc, rej, Q = accept_once(0, 1500, lib, readable_topos, rv, rcat)
    finally:
        gv2._build_topology = _ORIG_TOPO
    conf = []
    for i, a in enumerate(acc):
        sc = ind.strip_labels(a[8]); sc = dict(sc); sc["scenario_id"] = f"C-{i:04d}"; sc["split"] = "confirm"
        conf.append(sc)
    base_only = ind.verify_independence({"dev": dev, "val": val_, "adv": [dict(s, split="adv_dev") for s in adv]}, protected="adv")
    t0 = time.time()
    rep = ind.verify_independence({"dev": dev, "val": val_, "adv": adv, "confirm": conf}, protected="confirm")
    # CONFIRM-restricted verdict
    conf_ids = {c["scenario_id"] for c in conf}
    items = {s["scenario_id"]: s for s in dev + val_ + adv + conf}
    grp = build_groups(items, [lambda s: ("t", s["template_id"]), lambda s: ("topo", ind.topology_hash(s))])
    mixed = {}
    for iid, g in grp.items():
        mixed.setdefault(g, set()).add("confirm" if iid in conf_ids else "other")
    spanning = sum(1 for v in mixed.values() if len(v) > 1)
    near_conf = [p for p in rep["near_duplicate_pairs_cross_split"] if (p[0] in conf_ids) != (p[1] in conf_ids)]
    out = {"purpose": "verify_independence on a SIMULATED accepted set (prototype), label-stripped",
           "n_confirm": len(conf), "verify_independence_ok_global": rep["ok"],
           "leaks_for_protected": rep["leaks_for_protected"],
           "shared_keys_confirm_pairs": {k: {p: n for p, n in v.items() if "confirm" in p} for k, v in rep["shared_keys_by_pair"].items()},
           "global_group_integrity_violations_n": len(rep["group_integrity_violations"]),
           "global_near_duplicate_pairs_n": len(rep["near_duplicate_pairs_cross_split"]),
           "global_near_pairs_excluding_confirm_n": len(rep["near_duplicate_pairs_cross_split"]) - len(near_conf) - 0,
           "confirm_spanning_groups": spanning, "confirm_near_pairs_ge_0.90": len(near_conf),
           "baseline_dev_val_adv_only": {"ok": base_only["ok"], "group_violations": len(base_only["group_integrity_violations"]),
                                         "near_pairs": len(base_only["near_duplicate_pairs_cross_split"]),
                                         "leaks": base_only["leaks_for_protected"]},
           "n_groups_global": rep["n_groups"], "seconds": round(time.time() - t0, 1)}
    (OUT / "independence_dryrun.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str))
    return 0


def views_mode():
    """(a) frozen validators on a 'validation view' of new-structure scenarios; (b) invariance of observe()/V3 output to label fields."""
    import copy
    from src.rift.attribution_v3.rift_v3 import V3_CONFIGS, run_v3
    from src.rift.evaluation.rift_v2 import SharedCache
    rng = np.random.default_rng(AUDIT_SEED + 1)
    gv2._build_topology = _proto_topology
    res = {"purpose": "validator-view and label-invariance checks (prototype indices >= 300000; dev for invariance)"}
    try:
        cands = make_candidates(800, rng)
        scs = []
        for c in cands:
            j, st, f, t, w, o_, i, n = c
            scs.append(gv2.build_scenario("dev", 300000 + j, st, f, t, w, o_, i, n))
            scs[-1]["ground_truth"] = label_with_wrapper(scs[-1])
            scs[-1]["content_hash"] = gv2.content_hash(scs[-1])
        raw_fail = Counter(); view_fail = Counter()
        for sc in scs:
            for k, v in val.validate_scenario(sc, reproducibility=False).items():
                if v:
                    raw_fail[k] += 1
            vw = copy.deepcopy(sc)
            vw["dimensions"]["structure"] = "ambiguous" if sc["dimensions"]["structure"] in MUTUAL_STRUCTS else "linear_chain"
            vw["template_id"] = f"{vw['dimensions']['structure']}|{vw['dimensions']['family']}"
            vw["content_hash"] = gv2.content_hash(vw)
            vw["ground_truth"] = gv2.compute_ground_truth(vw)
            vw["content_hash"] = gv2.content_hash(vw)
            for k, v in val.validate_scenario(vw, reproducibility=False).items():
                if v:
                    view_fail[k] += 1
                    res.setdefault("view_failure_examples", {}).setdefault(k, v[:2])
        res["n_checked"] = len(scs)
        res["frozen_validators_on_raw_new_scenarios_failures_by_check"] = dict(raw_fail)
        res["frozen_validators_on_validation_view_failures_by_check"] = dict(view_fail)
    finally:
        gv2._build_topology = _ORIG_TOPO
    dev, _, _ = _readable()
    LABELISH = ("ground_truth", "design", "dimensions", "template_id", "content_hash", "parent_scenario", "generator_version")
    n = n_obs_same = n_v3_same = 0
    for sc in dev[:40]:
        mut = copy.deepcopy(sc)
        for k in LABELISH:
            if k in mut:
                mut[k] = "POISON"
        o1, o2 = sim.observe(sc), sim.observe(mut)
        same = (list(o1["metrics"]) == list(o2["metrics"]) and all(o1["metrics"][k].equals(o2["metrics"][k]) for k in o1["metrics"])
                and set(o1["call_graph"].edges) == set(o2["call_graph"].edges))
        iv1 = lambda x, ys, sd: sim.intervene(sc, x, ys, sd)   # noqa: E731
        iv2 = lambda x, ys, sd: sim.intervene(mut, x, ys, sd)  # noqa: E731
        r1 = run_v3(o1, iv1, sc["scenario_id"], int(sc["seed"]), V3_CONFIGS["V3-FULL"], cache=SharedCache())
        r2 = run_v3(o2, iv2, sc["scenario_id"], int(sc["seed"]), V3_CONFIGS["V3-FULL"], cache=SharedCache())
        n += 1; n_obs_same += int(same)
        n_v3_same += int((r1.abstained, r1.top_candidates, r1.abstention_reason) == (r2.abstained, r2.top_candidates, r2.abstention_reason))
    res["label_field_invariance_dev40"] = {"fields_poisoned": list(LABELISH), "observe_identical": n_obs_same, "v3_output_identical": n_v3_same, "of": n}
    (OUT / "view_and_invariance_checks.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "structural"
    if mode == "accept":
        sys.exit(acceptance_mode())
    if mode == "devval":
        sys.exit(devval_mode())
    if mode == "indep":
        sys.exit(indep_mode())
    if mode == "views":
        sys.exit(views_mode())
    if mode == "order":
        sys.exit(order_mode())
    if mode != "structural" and mode.isdigit():
        sys.exit(main())
    sys.exit(main())
