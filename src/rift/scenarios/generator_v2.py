"""Scenario generator v2 (Sprint 4.3.0, Phase 3) — factorial, label-by-construction.

Dimensions (protocol §12 / task Phase 3): 16 fault families x 11 causal structures x 11 temporal
patterns x 10 workloads x 9 observability conditions x 9 intervention modes x 11 negative kinds.

Splits are assigned per *design cell* = (structure, family) -> a template is never shared across
splits. Topology instances use disjoint size bands per split. ``feedback_like`` structures and the
``recovery_instability`` family exist ONLY in the held-out candidate (distribution shift).
Seeds are never treated as evidence of independence; independence is verified on content
(``scripts/sprint430_verify_independence.py``).

The generator never looks at any method output. Ground truth is computed from the noise-free
simulator state (``compute_ground_truth``).
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import networkx as nx
import numpy as np

from . import GENERATOR_VERSION
from .fingerprint import sha256_json
from .simulator import (DELTA_T, REF_WINDOWS, _graph, apparent_signal, detectable_onset_window,
                        observed_services, path_responses)

STRUCTURES = ["linear_chain", "branching", "converging", "multiple_upstream", "diamond",
              "parallel_independent", "shared_dependency", "confounding", "hidden_common_cause",
              "ambiguous", "feedback_like"]
FAMILIES = ["latency_degradation", "resource_saturation", "cpu_contention", "memory_pressure",
            "network_degradation", "packet_loss", "service_unavailability", "dependency_failure",
            "queue_buildup", "retry_amplification", "cascading_failure", "partial_degradation",
            "intermittent", "transient", "compound", "recovery_instability"]
TEMPORAL = ["immediate_propagation", "delayed_propagation", "gradual_degradation", "abrupt_degradation",
            "intermittent_degradation", "multiple_onsets", "recovery_delay", "partial_recovery",
            "oscillation", "overlapping_faults", "delayed_downstream_effects"]
WORKLOADS = ["low_load", "moderate_load", "high_load", "bursty_traffic", "skewed_requests",
             "changing_workload", "unequal_service_rates", "high_baseline_variance",
             "low_baseline_variance", "sparse_telemetry"]
OBSERVABILITY = ["complete_telemetry", "missing_windows", "noisy_telemetry", "delayed_telemetry",
                 "partial_service_observability", "insufficient_samples", "ambiguous_pag",
                 "weak_interventional_evidence", "conflicting_observational_evidence"]
INTERVENTIONS = ["single_service", "multi_service", "low_magnitude", "high_magnitude", "reversible",
                 "imperfect", "delayed", "collateral_effects", "no_meaningful_effect"]
NEGATIVES = ["earliest_not_root", "downstream_largest_increase", "common_cause_several_services",
             "coincidental_anomaly", "root_not_identifiable", "indistinguishable_onsets",
             "weak_intervention_effects", "insufficient_telemetry", "high_variance_no_fault",
             "incomplete_recovery_after_normalisation", "no_fault_plain"]

FAMILY_SHAPE = {"intermittent": "intermittent", "transient": "pulse", "compound": "multi_onset",
                "recovery_instability": "rebound"}
TEMPORAL_SHAPE = {"gradual_degradation": "ramp", "intermittent_degradation": "intermittent",
                  "multiple_onsets": "multi_onset", "recovery_delay": "recovery_delay",
                  "partial_recovery": "partial_recovery", "oscillation": "oscillation"}
LAG_ONLY_TEMPORAL = ["immediate_propagation", "delayed_propagation", "abrupt_degradation",
                     "overlapping_faults", "delayed_downstream_effects"]
AMP_K = {"latency_degradation": 6.0, "resource_saturation": 7.0, "cpu_contention": 5.0,
         "memory_pressure": 6.0, "network_degradation": 5.0, "packet_loss": 7.0,
         "service_unavailability": 12.0, "dependency_failure": 6.0, "queue_buildup": 6.0,
         "retry_amplification": 6.0, "cascading_failure": 7.0, "partial_degradation": 3.5,
         "intermittent": 7.0, "transient": 8.0, "compound": 6.0, "recovery_instability": 7.0}
REF_SIGMA = 8.0   # amplitudes are absolute (AMP_K * REF_SIGMA ms), so high variance lowers SNR

SPLIT_N = {"dev": 180, "val": 72, "held_out": 108}
SPLIT_SEED = {"dev": 4301, "val": 4302, "held_out": 4303}
SPLIT_PREFIX = {"dev": "D", "val": "V", "held_out": "H"}
_SIZE_BAND = {"dev": (0, 1), "val": (2, 2), "held_out": (3, 3)}
_NAME_POOL = ["alder", "birch", "cedar", "dune", "elm", "fjord", "grove", "heath", "iris", "juniper",
              "kelp", "larch", "moss", "nettle", "oak", "pine", "quill", "reed", "sage", "thorn",
              "umber", "vale", "willow", "yarrow", "zinnia", "aspen", "basil", "clover", "dill",
              "fennel", "ginger", "hazel", "ivy", "jasmine", "kale", "lotus", "mint", "nutmeg",
              "olive", "poppy", "quince", "rowan", "sorrel", "tansy", "ulex", "violet", "wisteria",
              "xylia", "yucca", "zest"]
NEEDS_EDGE = {"earliest_not_root", "downstream_largest_increase", "indistinguishable_onsets",
              "weak_intervention_effects"}
NEG_STRUCT = {"common_cause_several_services": "hidden_common_cause", "root_not_identifiable": "ambiguous"}


# ------------------------------------------------------------------------------------ splits
def cell_split(structure: str, family: str) -> str:
    si, fi = STRUCTURES.index(structure), FAMILIES.index(family)
    if structure == "feedback_like" or family == "recovery_instability":
        return "held_out"
    r = (si + 2 * fi) % 10
    return "dev" if r < 5 else ("val" if r < 7 else "held_out")


def cells_for(split: str) -> List[Tuple[str, str]]:
    return [(s, f) for s in STRUCTURES for f in FAMILIES if cell_split(s, f) == split]


# ------------------------------------------------------------------------------- topologies
def _build_topology(kind: str, extra: int, names: List[str]) -> Dict[str, Any]:
    it = iter(names)
    nxt_name = lambda: next(it)  # noqa: E731
    edges: List[Tuple[str, str]] = []
    nodes: List[str] = []
    hidden: List[str] = []
    latent: List[str] = []
    roots: List[str] = []
    mutual: List[Tuple[str, str]] = []

    def chain(start: str, n: int) -> str:
        cur = start
        for _ in range(n):
            nxt = nxt_name()
            nodes.append(nxt)
            edges.append((cur, nxt))
            cur = nxt
        return cur

    if kind == "linear_chain":
        r = nxt_name(); nodes.append(r); roots = [r]; chain(r, 2 + extra)
    elif kind == "branching":
        r = nxt_name(); nodes.append(r); roots = [r]
        a, b = nxt_name(), nxt_name(); nodes += [a, b]; edges += [(r, a), (r, b)]
        chain(a, extra)
    elif kind == "converging":
        r, p, m, d = nxt_name(), nxt_name(), nxt_name(), nxt_name()
        nodes += [r, p, m, d]; roots = [r]; edges += [(r, m), (p, m), (m, d)]
        for _ in range(extra):
            q = nxt_name(); nodes.append(q); edges.append((q, m))
    elif kind == "multiple_upstream":
        r1, r2, m, d = nxt_name(), nxt_name(), nxt_name(), nxt_name()
        nodes += [r1, r2, m, d]; roots = [r1, r2]; edges += [(r1, m), (r2, m), (m, d)]
        chain(d, extra)
    elif kind == "diamond":
        r, a, b, d = nxt_name(), nxt_name(), nxt_name(), nxt_name()
        nodes += [r, a, b, d]; roots = [r]; edges += [(r, a), (r, b), (a, d), (b, d)]
        chain(d, extra)
    elif kind == "parallel_independent":
        r1, a, r2, b = nxt_name(), nxt_name(), nxt_name(), nxt_name()
        nodes += [r1, a, r2, b]; roots = [r1, r2]; edges += [(r1, a), (r2, b)]
        chain(a, extra); chain(b, extra)
    elif kind == "shared_dependency":
        s, x, y, z, p = (nxt_name() for _ in range(5))
        nodes += [s, x, y, z, p]; roots = [s]; edges += [(s, x), (s, y), (s, z), (p, x)]
        chain(z, extra)
    elif kind == "confounding":
        h, r, c = nxt_name(), nxt_name(), nxt_name()
        nodes += [r, c]; hidden = [h]; latent = [h]; roots = [r]
        edges += [(h, r), (h, c), (r, c)]
        chain(c, extra)
    elif kind == "hidden_common_cause":
        h, x, y, z = nxt_name(), nxt_name(), nxt_name(), nxt_name()
        nodes += [x, y, z]; hidden = [h]; roots = []
        edges += [(h, x), (h, y), (h, z)]
        chain(z, extra)
    elif kind == "ambiguous":
        a, b, t = nxt_name(), nxt_name(), nxt_name()
        nodes += [a, b, t]; roots = [a]; mutual = [(a, b)]
        edges += [(a, b), (b, a), (b, t)]
        chain(t, extra)
    elif kind == "feedback_like":
        r, a, b = nxt_name(), nxt_name(), nxt_name()
        nodes += [r, a, b]; roots = [r]; edges += [(r, a), (a, b), (b, r)]
        chain(b, extra)
    else:
        raise ValueError(kind)
    return {"nodes": nodes, "edges": edges, "hidden": hidden, "latent": latent, "roots": roots,
            "mutual": mutual}


# ----------------------------------------------------------------------------------- helpers
def _cyc(levels: Sequence[str], n: int, rng: np.random.Generator) -> List[str]:
    out: List[str] = []
    while len(out) < n:
        out += [levels[i] for i in rng.permutation(len(levels))]
    return out[:n]


def _derive_seed(split: str, idx: int) -> int:
    h = hashlib.sha256(f"{GENERATOR_VERSION}|{split}|{idx}".encode()).hexdigest()
    return int(h[:8], 16) & 0x7FFFFFFF


def _workload(level: str) -> Tuple[float, Dict[str, Any], bool]:
    """(base sigma, workload params, per_node_sigma)"""
    table = {"low_load": (12.0, {}, False), "moderate_load": (8.0, {}, False),
             "high_load": (8.0, {"drift_sigma": 0.5}, False), "bursty_traffic": (8.0, {"burst_p": 0.06}, False),
             "skewed_requests": (8.0, {"skew": True}, False), "changing_workload": (8.0, {"drift_sigma": 2.5}, False),
             "unequal_service_rates": (8.0, {}, True), "high_baseline_variance": (20.0, {}, False),
             "low_baseline_variance": (3.0, {}, False), "sparse_telemetry": (8.0, {}, False)}
    return table[level]


def _desc(g: nx.DiGraph, n: str) -> set:
    return nx.descendants(g, n) if n in g else set()


# ------------------------------------------------------------------------------ main builder
def build_scenario(split: str, idx: int, structure: str, family: str, temporal: str, workload: str,
                   observability: str, intervention: str, negative: Optional[str]) -> Dict[str, Any]:
    seed = _derive_seed(split, idx)
    rng = np.random.default_rng(seed)
    extra = int(rng.integers(_SIZE_BAND[split][0], _SIZE_BAND[split][1] + 1))
    pool = [_NAME_POOL[i] for i in rng.permutation(len(_NAME_POOL))]
    topo = _build_topology(structure, extra, pool)
    n_used = len(topo["nodes"]) + len(topo["hidden"])

    if negative == "high_variance_no_fault":
        workload = "high_baseline_variance"
    sigma_base, wl_params, per_node = _workload(workload)
    if negative == "high_variance_no_fault":
        wl_params = {"burst_p": 0.08, "drift_sigma": 1.5}
    if observability == "noisy_telemetry":
        sigma_base *= 1.8

    nodes: List[Dict[str, Any]] = []
    for n in topo["nodes"] + topo["hidden"]:
        if n in topo["hidden"]:
            nd: Dict[str, Any] = {"id": n, "sigma": REF_SIGMA, "hidden": True}
        else:
            nd = {"id": n, "sigma": round(float(rng.uniform(4.0, 22.0)) if per_node else sigma_base, 3)}
        if n in topo["latent"]:
            nd["latent"] = True
        nodes.append(nd)

    lag_tbl = {"immediate_propagation": (0, 0), "delayed_propagation": (2, 3),
               "delayed_downstream_effects": (4, 5)}
    lo, hi = lag_tbl.get(temporal, (1, 1))
    if family in ("network_degradation", "queue_buildup"):
        lo, hi = lo + 1, hi + 1
    if negative in ("indistinguishable_onsets", "weak_intervention_effects"):
        lo, hi = 0, 0
    if negative == "earliest_not_root":
        lo, hi = 1, 1
    gain_c = {"retry_amplification": 1.4, "cascading_failure": 0.92}.get(family, 0.8)
    if negative == "downstream_largest_increase":
        gain_c = 1.5

    mutual = {frozenset(p) for p in topo["mutual"]}
    edges: List[Dict[str, Any]] = []
    for a, b in topo["edges"]:
        if a in topo["hidden"]:
            edges.append({"src": a, "dst": b, "gain": round(float(rng.uniform(0.7, 0.9)), 3), "lag": 0})
        elif frozenset((a, b)) in mutual:
            edges.append({"src": a, "dst": b, "gain": 0.8, "lag": 0})
        else:
            edges.append({"src": a, "dst": b,
                          "gain": round(float(np.clip(gain_c + rng.uniform(-0.08, 0.08), 0.2, 2.0)), 3),
                          "lag": int(rng.integers(lo, hi + 1))})
    if structure == "feedback_like":
        back_src, back_dst = topo["nodes"][2], topo["nodes"][0]
        for e in edges:
            if e["src"] == back_src and e["dst"] == back_dst:
                e["gain"], e["lag"] = 0.3, 3

    # --- timing
    onset_w = int(rng.integers(14, 22))
    n_windows = onset_w + 26
    if negative == "insufficient_telemetry" or observability == "insufficient_samples":
        n_windows, onset_w = 16, 6

    # --- fault shape/amplitude
    shape = FAMILY_SHAPE.get(family, TEMPORAL_SHAPE.get(temporal, "step"))
    if negative == "incomplete_recovery_after_normalisation":
        shape = "partial_recovery"
    amp = AMP_K[family] * REF_SIGMA * float(rng.uniform(0.9, 1.15))
    if negative == "incomplete_recovery_after_normalisation":
        amp = 6.0 * REF_SIGMA
    sp: Dict[str, Any] = {}
    if shape == "ramp":
        sp = {"windows": 8}
    elif shape == "pulse":
        sp = {"windows": 4}
    elif shape == "recovery_delay":
        sp = {"recover_after_s": float(rng.integers(100, 160))}
    var_mult = {"cpu_contention": 2.0, "resource_saturation": 1.5, "packet_loss": 2.5}.get(family, 1.0)

    roots = list(topo["hidden"]) if structure == "hidden_common_cause" else list(topo["roots"])
    if negative in ("high_variance_no_fault", "no_fault_plain"):
        roots = []
    faults: List[Dict[str, Any]] = []
    for k, r in enumerate(roots):
        f: Dict[str, Any] = {"service": r, "onset_s": float((onset_w + 3 * k) * DELTA_T),
                             "amp_ms": round(amp, 3), "shape": shape, "shape_params": dict(sp),
                             "var_mult": var_mult}
        if family == "queue_buildup":
            f["downstream_shape"] = "ramp"
            f["shape_params"] = {"windows": 6}
        faults.append(f)

    obs_nodes = [n["id"] for n in nodes if not n.get("hidden")]
    g0 = nx.DiGraph([(e["src"], e["dst"]) for e in edges])
    g0.add_nodes_from(n["id"] for n in nodes)

    distractors: List[str] = []
    if temporal == "overlapping_faults" and roots and not negative and structure != "hidden_common_cause":
        cands = [n for n in obs_nodes if n not in roots and n not in nx.ancestors(g0, roots[0])
                 and n not in nx.descendants(g0, roots[0])]
        if cands:
            sec = cands[int(rng.integers(0, len(cands)))]
            faults.append({"service": sec, "onset_s": float((onset_w + 5) * DELTA_T),
                           "amp_ms": round(5.0 * REF_SIGMA, 3), "shape": "step", "shape_params": {},
                           "var_mult": 1.0})
            roots.append(sec)

    decoy_id = pool[n_used + 1]
    if (negative == "coincidental_anomaly" and roots) or \
            (observability == "conflicting_observational_evidence" and roots and not negative):
        nodes.append({"id": decoy_id, "sigma": sigma_base})
        faults.append({"service": decoy_id, "onset_s": float((onset_w - 4) * DELTA_T),
                       "amp_ms": round(6.0 * REF_SIGMA, 3), "shape": "pulse",
                       "shape_params": {"windows": 6}, "var_mult": 1.0})
        distractors.append(decoy_id)

    if observability == "ambiguous_pag":
        zid = pool[n_used + 2]
        nodes.append({"id": zid, "sigma": REF_SIGMA, "hidden": True, "latent": True})
        for n in [x["id"] for x in nodes if not x.get("hidden")]:
            edges.append({"src": zid, "dst": n, "gain": round(float(rng.uniform(0.75, 0.95)), 3), "lag": 0})

    # --- telemetry
    tel: Dict[str, Any] = {"n_windows": n_windows, "missing_frac": 0.0, "delay_windows": {}, "unobserved": []}
    if observability == "missing_windows":
        tel["missing_frac"] = 0.2
    if negative == "insufficient_telemetry":
        tel["missing_frac"] = 0.3
    if workload == "sparse_telemetry":
        tel["sparse_frac"] = 0.3
    if observability == "partial_service_observability":
        obs_all = [n["id"] for n in nodes if not n.get("hidden")]
        leaves = [n for n in obs_all if n not in roots and g0.out_degree(n) == 0 and n not in distractors]
        tel["unobserved"] = sorted(leaves[:2])
    if observability == "delayed_telemetry":
        for n in obs_nodes:
            if rng.random() < 0.5:
                tel["delay_windows"][n] = int(rng.integers(1, 3))
    if negative == "earliest_not_root" and roots and g0.out_degree(roots[0]) > 0:
        tel["delay_windows"][roots[0]] = 3

    # --- intervention
    iv: Dict[str, Any] = {"mode": intervention, "magnitude_sigma": 2.0, "delivered": 1.0, "delay_s": 0.0,
                          "multi_service": False, "co_target": None, "collateral": {}, "rollback_complete": True}
    if intervention == "low_magnitude":
        iv["magnitude_sigma"] = 0.8
    elif intervention == "high_magnitude":
        iv["magnitude_sigma"] = 4.0
    elif intervention == "imperfect":
        iv["delivered"] = 0.5
    elif intervention == "delayed":
        iv["delay_s"] = 15.0
    elif intervention == "no_meaningful_effect":
        iv["magnitude_sigma"] = 0.15
    elif intervention == "multi_service":
        iv["multi_service"] = True
    if observability == "weak_interventional_evidence":
        iv["magnitude_sigma"], iv["delivered"] = 0.6, 0.5
    if negative == "weak_intervention_effects":
        iv["magnitude_sigma"] = 0.2

    sc: Dict[str, Any] = {
        "scenario_id": f"V2{SPLIT_PREFIX[split]}-{idx:04d}", "split": split, "seed": seed,
        "generator_version": GENERATOR_VERSION, "parent_scenario": None,
        "dimensions": {"structure": structure, "family": family, "temporal": temporal,
                       "workload": workload, "observability": observability,
                       "intervention": intervention, "negative": negative, "size_extra": extra},
        "template_id": f"{structure}|{family}",
        "graph": {"nodes": nodes, "edges": edges, "mutual_pairs": [list(p) for p in topo["mutual"]],
                  "decoy_edges": []},
        "faults": faults, "telemetry": tel, "workload_params": wl_params, "intervention": iv,
        "design": {"onset_window": onset_w, "distractors": distractors, "true_roots": roots},
    }
    obs = observed_services(sc)
    cand_pairs = [(a, b) for a in obs for b in obs if a != b and not g0.has_edge(a, b)
                  and a not in distractors and b not in distractors]
    rng.shuffle(cand_pairs)
    sc["graph"]["decoy_edges"] = [list(p) for p in cand_pairs[:int(rng.integers(2, 4))]]

    gg = _graph(sc)
    rel: set = set()
    for r in roots:
        rel |= _desc(gg, r)
        rel |= nx.ancestors(gg, r) if r in gg else set()
    free = [n for n in obs if n not in roots and n not in rel and n not in distractors]
    if iv["multi_service"]:
        iv["co_target"] = free[0] if free else None
        iv["multi_service"] = iv["co_target"] is not None
    if intervention == "collateral_effects" and free:
        iv["collateral"] = {free[0]: 0.5}

    sc["ground_truth"] = compute_ground_truth(sc)
    sc["content_hash"] = content_hash(sc)
    return sc


# ------------------------------------------------------------------------------ ground truth
def compute_ground_truth(sc: Mapping[str, Any]) -> Dict[str, Any]:
    """Label from noise-free simulator state; never from any method (Amendment 1 §6, Amendment 2 §4)."""
    dims = sc["dimensions"]
    obs = observed_services(sc)
    true_roots = list(sc["design"]["true_roots"])
    gt: Dict[str, Any] = {"roots": [r for r in true_roots if r in obs],
                          "unobserved_roots": [r for r in true_roots if r not in obs],
                          "distractors": list(sc["design"]["distractors"])}
    n_win = int(sc["telemetry"]["n_windows"])

    def abstain(reason: str, ident: str) -> Dict[str, Any]:
        gt.update({"expected_outcome": "ABSTAIN_REQUIRED", "abstain_reason": reason,
                   "identifiability": ident, "identifiable_by": []})
        return gt

    if not true_roots:
        return abstain("NO_FAULT", "NO_FAULT")
    if not gt["roots"]:
        return abstain("ROOT_UNOBSERVED", "NOT_IDENTIFIABLE:ROOT_UNOBSERVED")
    if dims["structure"] == "ambiguous":
        return abstain("SYMMETRIC_MUTUAL_DEPENDENCY", "NOT_IDENTIFIABLE:SYMMETRIC")
    if n_win < REF_WINDOWS + 8 or dims["observability"] == "insufficient_samples" \
            or dims["negative"] == "insufficient_telemetry":
        return abstain("INSUFFICIENT_BASELINE", "NOT_IDENTIFIABLE:INSUFFICIENT_SAMPLES")

    z = {s: apparent_signal(sc, s) for s in obs}
    onset = {s: detectable_onset_window(z[s]) for s in obs}
    g = _graph(sc)
    iv = sc["intervention"]
    sig = {n["id"]: float(n["sigma"]) for n in sc["graph"]["nodes"]}
    ok_roots: List[str] = []
    by: Dict[str, List[str]] = {}
    for r in gt["roots"]:
        snr = float(np.max(np.abs(z[r]))) if len(z[r]) else 0.0
        if snr < 4.0 or onset[r] is None:
            by[r] = []
            continue
        ev: List[str] = []
        others = [s for s in obs if s != r and onset[s] is not None]
        if all(onset[s] > onset[r] for s in others):
            ev.append("TEMPORAL")
        for d in obs:
            if d == r or not nx.has_path(g, r, d):
                continue
            pr = path_responses(g, r, d)
            tot = sum(p[0] for p in pr)
            lag_s = min(p[1] for p in pr)
            if 30.0 + iv["delay_s"] + 2.0 * lag_s / DELTA_T > 45.0:
                continue
            if iv["magnitude_sigma"] * sig[r] * iv["delivered"] * tot / sig[d] >= 1.0:
                ev.append("INTERVENTIONAL")
                break
        by[r] = ev
        if ev:
            ok_roots.append(r)
    if ok_roots:
        kinds = sorted({k for r in ok_roots for k in by[r]})
        gt.update({"expected_outcome": "ATTRIBUTE", "abstain_reason": None,
                   "identifiability": "IDENTIFIABLE_BY_" + "+".join(kinds), "identifiable_by": kinds,
                   "attributable_roots": ok_roots})
        return gt
    weak = all((float(np.max(np.abs(z[r]))) < 4.0 if len(z[r]) else True) for r in gt["roots"])
    reason = "WEAK_SIGNAL" if weak else "NO_DISCRIMINATING_EVIDENCE"
    return abstain(reason, "NOT_IDENTIFIABLE:" + reason)


def content_hash(sc: Mapping[str, Any]) -> str:
    skip = {"scenario_id", "seed", "split", "content_hash", "parent_scenario"}
    return sha256_json({k: v for k, v in sc.items() if k not in skip})


# --------------------------------------------------------------------------------- the corpus
def generate_split(split: str, n: Optional[int] = None) -> List[Dict[str, Any]]:
    n = n or SPLIT_N[split]
    rng = np.random.default_rng(SPLIT_SEED[split])
    cells = cells_for(split)
    order = [cells[i] for i in rng.permutation(len(cells))]
    work = _cyc(WORKLOADS, n, rng)
    obsv = _cyc(OBSERVABILITY, n, rng)
    ivs = _cyc(INTERVENTIONS, n, rng)
    temporal_all = _cyc(TEMPORAL, n, rng)
    temporal_lag = _cyc(LAG_ONLY_TEMPORAL, n, rng)
    negs = _cyc(NEGATIVES, n, rng)
    out: List[Dict[str, Any]] = []
    ni = 0
    cell_ptr = 0
    for j in range(n):
        neg: Optional[str] = None
        cell: Optional[Tuple[str, str]] = None
        if j % 4 == 3:
            neg = negs[ni]
            ni += 1
            need = NEG_STRUCT.get(neg)
            if need:
                opts = [c for c in cells if c[0] == need]
                if opts:
                    cell = opts[(j // 4) % len(opts)]
                else:
                    neg = "indistinguishable_onsets"
        if cell is None:
            cell = order[cell_ptr % len(order)]
            cell_ptr += 1
        structure, family = cell
        if neg in NEEDS_EDGE and structure == "hidden_common_cause":
            neg = "coincidental_anomaly"
        temporal = temporal_lag[j] if family in FAMILY_SHAPE else temporal_all[j]
        out.append(build_scenario(split, j + 1, structure, family, temporal, work[j], obsv[j], ivs[j], neg))
    return out
