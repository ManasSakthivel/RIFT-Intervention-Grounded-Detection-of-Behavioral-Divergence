"""Sprint 4.4.0 diagnostics: per-scenario failure tracing and FCI/PAG graph-quality metrics.

POST-HOC and DESCRIPTIVE. Ground truth is read here (and only here) to *explain* what an unchanged RIFT-FULL-V2 did.
Nothing in this module feeds back into any method. It must only be called on dev/val scenarios.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

import networkx as nx

from src.rift.attribution_v3 import pag_semantics as ps
from src.rift.ebd.ebd import compute_ebd
from src.rift.evaluation import benchmark_v2 as bm
from src.rift.evaluation import rift_v2 as r2
from src.rift.scenarios import simulator as sim

CATEGORIES = (
    "ROOT_NOT_OBSERVED", "ROOT_NOT_DIVERGING", "ROOT_OMITTED_FROM_LEARNED_GRAPH", "ROOT_ISOLATED_BY_FCI",
    "FALSE_POSITIVE_EDGE", "FALSE_NEGATIVE_EDGE", "INCORRECT_ORIENTATION", "SEMI_DIRECTED_MISTAKEN_FOR_EVIDENCE",
    "EBD_TIMING_AMBIGUITY", "DOWNSTREAM_STRONGER_ANOMALY", "INSUFFICIENT_INTERVENTION_EVIDENCE", "CONFOUNDING",
    "MULTIPLE_CAUSES", "NON_IDENTIFIABLE", "CANDIDATE_RANKING_DEFECT", "GROUND_TRUTH_AMBIGUITY", "OTHER")


# ------------------------------------------------------------------------------------------ truth helpers
def true_structure(sc: Mapping[str, Any]) -> Dict[str, Any]:
    g = sim._graph(sc)
    obs = set(sim.observed_services(sc))
    direct = {(a, b) for a, b in g.edges if a in obs and b in obs}
    anc = {x: (nx.descendants(g, x) & obs) for x in obs}               # ancestry in the FULL graph, observed pairs
    hidden = {n for n in g.nodes if n not in obs}
    latent_pairs: Set[frozenset] = set()
    for h in hidden:
        kids = [k for k in (nx.descendants(g, h) & obs)]
        for i, a in enumerate(kids):
            for b in kids[i + 1:]:
                latent_pairs.add(frozenset((a, b)))
    mutual = {frozenset(p) for p in sc["graph"].get("mutual_pairs", [])}
    return {"g": g, "obs": obs, "direct": direct, "anc": anc, "hidden": hidden, "latent_pairs": latent_pairs,
            "mutual": mutual}


def _edge_truth_class(T: Mapping[str, Any], a: str, b: str) -> str:
    if (a, b) in T["direct"] or (b, a) in T["direct"]:
        return "DIRECT"
    if b in T["anc"].get(a, set()) or a in T["anc"].get(b, set()):
        return "INDIRECT_ANCESTRAL"
    if frozenset((a, b)) in T["latent_pairs"]:
        return "HIDDEN_COMMON_CAUSE"
    return "UNRELATED"


def graph_quality(sc: Mapping[str, Any], mp: Optional[ps.MarkedPAG]) -> Dict[str, Any]:
    """Skeleton / orientation quality of a learned PAG against the observed-node true graph."""
    T = true_structure(sc)
    out: Dict[str, Any] = {"available": mp is not None}
    true_direct = {frozenset(e) for e in T["direct"]}
    out["n_true_direct_edges"] = len(true_direct)
    if mp is None:
        out.update(n_pag_edges=0, tp=0, fp=0, fn=len(true_direct))
        return out
    pag_edges = [(a, b) for a, b in mp.edges()]
    pairs = {frozenset(e) for e in pag_edges}
    cls = {fs: _edge_truth_class(T, *sorted(fs)) for fs in pairs}
    tp = {fs for fs in pairs if cls[fs] == "DIRECT"}
    fn = true_direct - pairs
    fp_classes = {k: sum(1 for fs in pairs if cls[fs] == k) for k in ("INDIRECT_ANCESTRAL", "HIDDEN_COMMON_CAUSE", "UNRELATED")}
    fp = {fs for fs in pairs if cls[fs] in ("INDIRECT_ANCESTRAL", "UNRELATED")}   # hidden-common-cause adjacency is expected
    prec = len(tp) / (len(tp) + len(fp)) if (tp or fp) else None
    rec = len(tp) / len(true_direct) if true_direct else None
    f1 = (2 * prec * rec / (prec + rec)) if (prec and rec) else (0.0 if (prec is not None and rec is not None) else None)
    out.update(n_pag_edges=len(pairs), tp=len(tp), fp=len(fp), fn=len(fn), fp_by_truth_class=fp_classes,
               precision=prec, recall=rec, f1=f1, skeleton_shd=len(fp) + len(fn))
    # orientation: only on true-direct edges (and indirect-ancestral for ancestry orientation)
    o = {"directed_correct": 0, "directed_wrong": 0, "circle_or_undirected": 0, "bidirected_on_direct": 0,
         "tail_tail": 0, "n_scored": 0}
    allm = {"circle_marked_edges": 0, "fully_directed_edges": 0, "bidirected_edges": 0}
    for a, b in pag_edges:
        ma, mb = mp.marks[(a, b)], mp.marks[(b, a)]
        if ps.CIRCLE in (ma, mb):
            allm["circle_marked_edges"] += 1
        if (ma, mb) in ((ps.TAIL, ps.ARROW), (ps.ARROW, ps.TAIL)):
            allm["fully_directed_edges"] += 1
        if (ma, mb) == (ps.ARROW, ps.ARROW):
            allm["bidirected_edges"] += 1
    for fs in tp:
        a, b = sorted(fs)
        src, dst = (a, b) if (a, b) in T["direct"] else (b, a)
        ms, md = mp.marks[(src, dst)], mp.marks[(dst, src)]
        o["n_scored"] += 1
        if (ms, md) == (ps.TAIL, ps.ARROW):
            o["directed_correct"] += 1
        elif (ms, md) == (ps.ARROW, ps.ARROW):
            o["bidirected_on_direct"] += 1
        elif ms == ps.ARROW:                       # arrowhead at the true source: reversed (or reverse-circle)
            o["directed_wrong"] += 1
        elif (ms, md) == (ps.TAIL, ps.TAIL):
            o["tail_tail"] += 1
        else:                                      # circle at either end, no contradicting arrowhead
            o["circle_or_undirected"] += 1
    out["orientation_on_true_edges"] = o
    out.update(allm)
    out["n_edges_total"] = len(pairs)
    return out


# --------------------------------------------------------------------------------------- V2 re-run + trace
def _ebd_all(o: Mapping[str, Any], pag_result) -> Dict[str, Any]:
    usable = {s: df for s, df in o["metrics"].items() if s in o["baseline_stats"]}
    return {e.service_id: e for e in compute_ebd(metrics=usable, baselines=o["baseline_stats"], pag_result=pag_result,
                                                 incident_window=o["incident_window"], delta_t=10.0, theta_detect=3.0,
                                                 theta_persist=2, max_gap_windows=1)}


def run_v2_traced(sc: Mapping[str, Any]) -> Dict[str, Any]:
    """Re-run unchanged V2 (A1) and V2-oracle-graph (A9, privileged) with caches, return outputs + internals."""
    o = sim.observe(sc)
    fid, seed = sc["scenario_id"], int(sc["seed"])
    iv = lambda x, ys, s: sim.intervene(sc, x, ys, s)  # noqa: E731
    cache = r2.SharedCache()
    out = r2.run_v2(o, iv, fid, seed, r2.CONFIGS["A1-FULL"], cache=cache)
    rec = bm._out_to_rec(out, 0.0, 0.0)
    return {"obs": o, "cache": cache, "out": out, "rec": rec, "score": bm.score_one(sc, rec)}


def trace_scenario(sc: Mapping[str, Any]) -> Dict[str, Any]:
    gt = sc["ground_truth"]
    T = true_structure(sc)
    R = run_v2_traced(sc)
    o, cache, out, rec, score = R["obs"], R["cache"], R["out"], R["rec"], R["score"]
    raw = out.raw_output
    tag, pagr = cache.pag.get("fci", ("NONE", None))
    pag_ok = tag == "OK"
    mp = ps.decode_marks(pagr.variables, pagr.adjacency_matrix) if pag_ok else None
    ebd = _ebd_all(o, pagr) if pag_ok else {}
    roots_all = list(gt["roots"])
    roots_obs = [r for r in roots_all if r in T["obs"]]
    top = score["top1"]
    # frozen decoder vs corrected decoder
    frozen_types: Dict[str, int] = {}
    if pag_ok:
        for e in pagr.edges:
            frozen_types[e.edge_type.value] = frozen_types.get(e.edge_type.value, 0) + 1
    corrected_kinds: Dict[str, int] = {}
    if mp:
        for a, b in mp.edges():
            corrected_kinds[mp.kind(a, b)] = corrected_kinds.get(mp.kind(a, b), 0) + 1

    div = {s: {"t_star": e.t_star, "anomaly": e.anomaly_score, "r1": e.r1_pass, "r2": e.r2_pass, "r3": e.r3_pass,
               "path_kind": e.causal_path_kind} for s, e in ebd.items() if e.r1_pass}
    cands = raw.get("candidates", [])
    root_info: List[Dict[str, Any]] = []
    for r in roots_obs:
        info: Dict[str, Any] = {"root": r, "in_learned_graph": bool(mp and r in mp.variables),
                                "diverges": r in div, "t_star": div.get(r, {}).get("t_star"),
                                "anomaly": div.get(r, {}).get("anomaly"), "is_candidate": r in cands,
                                "intervened": r in raw.get("intervened", []), "confirmed": r in raw.get("confirmed", {})}
        if mp and r in mp.variables:
            info["pag_degree"] = sum(1 for (a, b) in mp.marks if a == r)
            info["isolated"] = info["pag_degree"] == 0
            if top and top in mp.variables and top != r:
                info["pag_relation_root_to_named"] = ps.classify_relation(mp, r, top)
                info["pag_relation_named_to_root"] = ps.classify_relation(mp, top, r)
        info["true_root_ancestor_of_named"] = bool(top and top in T["anc"].get(r, set()))
        root_info.append(info)

    # --- CID rows
    cid_rows = []
    for (key, mode), res in cache.cid.items():
        x, y = key.split("\u2192")
        cid_rows.append({"x": x, "y": y, "grade": getattr(res.grade, "value", str(res.grade)),
                         "w1": res.w1_estimate, "theta_cid": res.theta_cid, "p": res.permutation_pvalue,
                         "n_base": res.n_baseline, "n_post": res.n_post,
                         "true_ancestor": y in T["anc"].get(x, set())})

    # --- failure classification (only for failures)
    kind = ("WRONG_ROOT" if score["wrong_root"] else
            "UNSAFE_ON_ABSTAIN_REQUIRED" if (score["unsafe"] and score["expected"] == "ABSTAIN_REQUIRED") else
            "LOST_ATTRIBUTE" if (score["expected"] == "ATTRIBUTE" and not score["answered"]) else
            "CORRECT" if score["expected"] == "ATTRIBUTE" and score["correct"] else
            "CORRECT_ABSTENTION")
    cats: List[str] = []
    if kind not in ("CORRECT", "CORRECT_ABSTENTION"):
        gq = graph_quality(sc, mp)
        d = sc["dimensions"]
        if score["expected"] == "ATTRIBUTE":
            for ri in root_info:
                if not ri["diverges"]:
                    cats.append("ROOT_NOT_DIVERGING")
                if ri["diverges"] and ri["in_learned_graph"] is False:
                    cats.append("ROOT_OMITTED_FROM_LEARNED_GRAPH")
                if ri.get("isolated"):
                    cats.append("ROOT_ISOLATED_BY_FCI")
                if top and ri["diverges"] and div.get(top) and ri["t_star"] is not None:
                    if abs(div[top]["t_star"] - ri["t_star"]) <= 10.0:
                        cats.append("EBD_TIMING_AMBIGUITY")
                    if div[top]["anomaly"] > (ri["anomaly"] or 0):
                        cats.append("DOWNSTREAM_STRONGER_ANOMALY")
                if ri["is_candidate"] and not ri["confirmed"]:
                    cats.append("INSUFFICIENT_INTERVENTION_EVIDENCE")
                if ri["confirmed"] and top != ri["root"]:
                    cats.append("CANDIDATE_RANKING_DEFECT")
            if not roots_obs:
                cats.append("ROOT_NOT_OBSERVED")
            if mp and top:
                # relevant false negative: a true direct edge on the root->named ancestry is missing
                if any(frozenset(e) not in {frozenset(x) for x in mp.edges()} for e in T["direct"]
                       if any(e[0] == r or e[1] == top for r in roots_obs)):
                    cats.append("FALSE_NEGATIVE_EDGE")
        if gq.get("fp", 0) > 0 and kind != "LOST_ATTRIBUTE":
            cats.append("FALSE_POSITIVE_EDGE")
        o_ = gq.get("orientation_on_true_edges", {})
        if o_.get("directed_wrong", 0) > 0:
            cats.append("INCORRECT_ORIENTATION")
        if kind == "WRONG_ROOT" and raw.get("path_kind") == "SEMI_DIRECTED":
            cats.append("SEMI_DIRECTED_MISTAKEN_FOR_EVIDENCE")
        if d.get("structure") in ("confounding", "hidden_common_cause") or d.get("negative") == "common_cause_several_services":
            cats.append("CONFOUNDING")
        if len(sc["faults"]) >= 2 or d.get("structure") == "multiple_upstream":
            cats.append("MULTIPLE_CAUSES")
        if gt["abstain_reason"] in ("SYMMETRIC_MUTUAL_DEPENDENCY", "NO_DISCRIMINATING_EVIDENCE", "ROOT_UNOBSERVED") \
                or str(gt["identifiability"]).startswith("NOT_IDENTIFIABLE"):
            cats.append("NON_IDENTIFIABLE")
        if d.get("negative") in ("indistinguishable_onsets", "coincidental_anomaly"):
            cats.append("GROUND_TRUTH_AMBIGUITY")
        if not cats:
            cats.append("OTHER")
    cats = sorted(set(cats))
    return {"scenario_id": sc["scenario_id"], "split": sc["split"], "dimensions": sc["dimensions"],
            "expected": score["expected"], "abstain_reason_gt": gt["abstain_reason"],
            "true_roots": roots_all, "true_roots_observed": roots_obs, "unobserved_roots": gt["unobserved_roots"],
            "answered": score["answered"], "top1": top, "correct": score["correct"], "unsafe": score["unsafe"],
            "reason": score["reason"], "failure_kind": kind, "categories": cats,
            "v2_path_kind": raw.get("path_kind"), "candidates": cands, "diverging": div,
            "intervened": raw.get("intervened", []), "confirmed": raw.get("confirmed", {}),
            "ident_status": raw.get("ident_status"), "root_info": root_info,
            "named_is_descendant_of_true_root": bool(top and any(top in T["anc"].get(r, set()) for r in roots_obs)),
            "pag_status": tag if not pag_ok else "OK",
            "pag_edge_kinds_corrected": corrected_kinds, "pag_edge_types_frozen_decoder": frozen_types,
            "pag_edges": ([(a, b, mp.marks[(a, b)], mp.marks[(b, a)]) for a, b in mp.edges()] if mp else []),
            "true_direct_edges": sorted(T["direct"]), "cid_rows": cid_rows,
            "graph_quality": graph_quality(sc, mp)}
