#!/usr/bin/env python3
"""Sprint 4.4.0 aggregate analysis (Phases 1-4 and 6) on DEV and VAL only.

    python3 scripts/sprint440_analyze.py     # requires failure_traces_*.json and v3_*.json (run the two scripts first)

Reads: artifacts/sprint4_4_0/{failure_traces,v3}_{dev,val}.json, artifacts/sprint4_3_0/results/{dev,val}/per_scenario.json.
Never opens the held-out split. Writes artifacts/sprint4_4_0/analysis.json and graph_quality.csv.
"""
from __future__ import annotations

import csv
import json
import sys
import warnings
from collections import Counter, defaultdict
from pathlib import Path

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO), str(REPO / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402

from src.rift.attribution_v3 import pag_semantics as ps  # noqa: E402
from src.rift.attribution_v3.diagnostics import true_structure  # noqa: E402
from src.rift.evaluation import benchmark_v2 as bm  # noqa: E402
from src.rift.evaluation import stats_v2 as st  # noqa: E402
from src.rift.evaluation.dataset_registry_v2 import load_v2  # noqa: E402
from src.rift.scenarios import simulator as sim  # noqa: E402

A = REPO / "artifacts" / "sprint4_4_0"
SPLITS = ("dev", "val")
FOCAL = ["RIFT-FULL-LEGACY", "RIFT-FULL-V2", "V3-FULL", "V3-DEFINITIVE-ONLY", "B5-RIFT-OBS", "B0-EARLIEST", "B0-HIGHEST",
         "B1-LATENCY-CORR", "B3-SIEVE-LIKE", "B6-RIFT-RANDOM", "B7-RIFT-ONE-SHOT", "ORACLE:RIFT-FULL-V2-ORACLE-GRAPH",
         "ORACLE:RIFT-FULL-LEGACY-ORACLE-PAG", "ORACLE:UPPER-BOUND"]


def rate(k, n):
    lo, hi = bm._wilson(k, n)
    return {"k": int(k), "n": int(n), "value": (k / n) if n else None, "wilson95": [lo, hi]}


def load(split):
    scs = load_v2(split).scenarios
    legacy = json.loads((REPO / "artifacts/sprint4_3_0/results" / split / "per_scenario.json").read_text())
    v3 = json.loads((A / f"v3_{split}.json").read_text())
    tr = json.loads((A / f"failure_traces_{split}.json").read_text())
    ids = [s["scenario_id"] for s in scs]
    assert ids == [p["scenario_id"] for p in legacy] == [p["scenario_id"] for p in v3] == [t["scenario_id"] for t in tr]
    methods = defaultdict(dict)
    for p in legacy:
        for m, v in p["methods"].items():
            methods[m][p["scenario_id"]] = v
    for p in v3:
        for m, v in p["methods"].items():
            methods[m][p["scenario_id"]] = v
    return scs, ids, methods, tr


def always_abstain(scs):
    scores = [{"scenario_id": s["scenario_id"], "split": s["split"], "expected": s["ground_truth"]["expected_outcome"],
               "answered": False, "top1": None, "correct": False,
               "p2": s["ground_truth"]["expected_outcome"] != "ATTRIBUTE", "unsafe": False, "wrong_root": False,
               "distractor_hit": False, "top3_hit": False if s["ground_truth"]["expected_outcome"] == "ATTRIBUTE" else None,
               "alarm": False, "top_score": None, "reason": "ALWAYS_ABSTAIN"} for s in scs]
    recs = [{"abstained": True, "reason": "ALWAYS_ABSTAIN", "top": [], "ed_s": 0.0, "n_do": 0, "evidence_type": "OBSERVATIONAL",
             "path_kind": "NONE", "cid_grades": [], "ident_status": None, "detect_latency_s": None, "runtime_s": 0.0,
             "mem_kb": 0.0, "error": None} for _ in scs]
    return scores, recs


def method_table(scs, ids, methods):
    out, S = {}, {}
    for m in FOCAL:
        scores = [methods[m][i]["score"] for i in ids]
        recs = [methods[m][i]["record"] for i in ids]
        ag = bm.aggregate(scores, recs)
        S[m] = scores
        out[m] = {k: ag[k] for k in ("P1_attribution_accuracy", "conditional_accuracy_on_answered_attribute",
                                      "P2_outcome_correct", "P3_unsafe_attribution_overall", "unsafe_on_abstain_required",
                                      "wrong_root_on_attribute", "false_attribution_among_answered", "coverage_overall",
                                      "coverage_on_attribute", "abstention_rate", "selective_risk", "top3_on_attribute",
                                      "runtime_s", "intervention", "evidence")}
    sc, rc = always_abstain(scs)
    S["ALWAYS-ABSTAIN"] = sc
    ag = bm.aggregate(sc, rc)
    out["ALWAYS-ABSTAIN"] = {k: ag[k] for k in ("P1_attribution_accuracy", "P2_outcome_correct", "P3_unsafe_attribution_overall",
                                                 "coverage_overall", "abstention_rate")}
    return out, S


def paired(S, scs):
    tid = [s["template_id"] for s in scs]
    res = {}
    for a, b in (("V3-FULL", "RIFT-FULL-V2"), ("V3-FULL", "ALWAYS-ABSTAIN"), ("RIFT-FULL-V2", "ALWAYS-ABSTAIN"),
                 ("V3-FULL", "B0-EARLIEST"), ("V3-FULL", "RIFT-FULL-LEGACY"), ("V3-DEFINITIVE-ONLY", "RIFT-FULL-V2"),
                 ("V3-DEFINITIVE-ONLY", "ALWAYS-ABSTAIN")):
        for metric in ("P1", "P2", "P3_safe"):
            r = st.compare_pair(S[a], S[b], metric, tid)
            res[f"{a}|{b}|{metric}"] = {k: r[k] for k in ("n", "p_a", "p_b", "risk_difference", "paired_table", "mcnemar_exact_p",
                                                           "ci95_quoted_widest", "descriptive_only")}
    return res


def coverage_matched(S, split_n):
    """V3 vs V2 restricted to scenarios where BOTH answer, and risk at equal coverage."""
    a, b = S["V3-FULL"], S["RIFT-FULL-V2"]
    both = [(x, y) for x, y in zip(a, b) if x["answered"] and y["answered"]]
    return {"both_answered": len(both),
            "v3_correct_among_both": sum(1 for x, _ in both if not x["unsafe"]),
            "v2_correct_among_both": sum(1 for _, y in both if not y["unsafe"]),
            "v3_only_answered": sum(1 for x, y in zip(a, b) if x["answered"] and not y["answered"]),
            "v2_only_answered": sum(1 for x, y in zip(a, b) if y["answered"] and not x["answered"]),
            "v3_only_answered_unsafe": sum(1 for x, y in zip(a, b) if x["answered"] and not y["answered"] and x["unsafe"]),
            "v2_only_answered_unsafe": sum(1 for x, y in zip(a, b) if y["answered"] and not x["answered"] and y["unsafe"])}


# ----------------------------------------------------------------------------------------- phase 1
def failure_summary(tr):
    kinds = Counter(t["failure_kind"] for t in tr)
    cats = defaultdict(Counter)
    for t in tr:
        for c in t["categories"]:
            cats[t["failure_kind"]][c] += 1
    wrong = [t for t in tr if t["failure_kind"] == "WRONG_ROOT"]
    chain = Counter()
    for t in wrong:
        ri = t["root_info"][0] if t["root_info"] else {}
        if not ri:
            chain["root_unobserved"] += 1
        elif not ri["diverges"]:
            chain["root_never_diverges"] += 1
        elif ri.get("isolated"):
            chain["root_diverges_but_isolated_in_PAG"] += 1
        elif not ri["is_candidate"]:
            chain["root_diverges_connected_but_fails_R3"] += 1
        elif not ri["intervened"]:
            chain["root_candidate_not_intervened_or_explained_away"] += 1
        elif not ri["confirmed"]:
            chain["root_intervened_effect_not_confirmed"] += 1
        else:
            chain["root_confirmed_but_not_selected_as_source"] += 1
    return {"kinds": dict(kinds), "categories_by_kind": {k: dict(v) for k, v in cats.items()},
            "wrong_root_chain": dict(chain), "n_wrong": len(wrong),
            "wrong_named_is_descendant_of_root": sum(t["named_is_descendant_of_true_root"] for t in wrong),
            "wrong_path_kind": dict(Counter(t["v2_path_kind"] for t in wrong)),
            "wrong_root_earlier_than_named": sum(
                1 for t in wrong if t["root_info"] and t["root_info"][0].get("t_star") is not None and t["top1"] in t["diverging"]
                and t["root_info"][0]["t_star"] < t["diverging"][t["top1"]]["t_star"]),
            "wrong_root_anomaly_smaller_than_named": sum(
                1 for t in wrong if t["root_info"] and t["root_info"][0].get("anomaly") is not None and t["top1"] in t["diverging"]
                and t["root_info"][0]["anomaly"] < t["diverging"][t["top1"]]["anomaly"])}


# ----------------------------------------------------------------------------------------- phase 2
def graph_summary(scs, tr, methods, ids):
    rows = []
    for sc, t in zip(scs, tr):
        g = t["graph_quality"]
        rows.append({"scenario_id": t["scenario_id"], "structure": sc["dimensions"]["structure"], "family": sc["dimensions"]["family"],
                     "observability": sc["dimensions"]["observability"], "workload": sc["dimensions"]["workload"],
                     "intervention": sc["dimensions"]["intervention"], "pag": t["pag_status"],
                     "n_obs": len(sim.observed_services(sc)), "n_true_direct": g.get("n_true_direct_edges"),
                     "n_pag_edges": g.get("n_pag_edges"), "tp": g.get("tp"), "fp": g.get("fp"), "fn": g.get("fn"),
                     "circle": g.get("circle_marked_edges"), "directed": g.get("fully_directed_edges"),
                     "bidirected": g.get("bidirected_edges"), "dir_correct": g.get("orientation_on_true_edges", {}).get("directed_correct"),
                     "dir_wrong": g.get("orientation_on_true_edges", {}).get("directed_wrong")})
    ok = [r for r in rows if r["pag"] == "OK"]
    tp, fp, fn = (sum(r[k] for r in ok) for k in ("tp", "fp", "fn"))
    ne = sum(r["n_pag_edges"] for r in ok)
    out = {"scenarios": len(rows), "pag_status": dict(Counter(r["pag"] for r in rows)),
           "micro_precision": tp / (tp + fp) if tp + fp else None, "micro_recall": tp / (tp + fn) if tp + fn else None,
           "tp": tp, "fp": fp, "fn": fn, "shd_total": fp + fn, "edges_total": ne,
           "circle_marked_edges": sum(r["circle"] for r in ok), "fully_directed_edges": sum(r["directed"] for r in ok),
           "bidirected_edges": sum(r["bidirected"] for r in ok),
           "circle_frac": sum(r["circle"] for r in ok) / ne if ne else None,
           "orientation_on_true_edges": {"correct": sum(r["dir_correct"] for r in ok), "wrong": sum(r["dir_wrong"] for r in ok),
                                         "scored": tp}}
    p, r_ = out["micro_precision"], out["micro_recall"]
    out["micro_f1"] = 2 * p * r_ / (p + r_) if p and r_ else None
    # root relevance (ATTRIBUTE scenarios, observed roots)
    rel = Counter()
    cand_sizes, cand_incl = [], []
    for t in tr:
        if t["expected"] != "ATTRIBUTE" or t["pag_status"] != "OK":
            continue
        for ri in t["root_info"]:
            rel["roots"] += 1
            rel["diverges"] += ri["diverges"]
            rel["isolated"] += bool(ri.get("isolated"))
            rel["candidate"] += ri["is_candidate"]
            rel["intervened"] += ri["intervened"]
            rel["confirmed"] += ri["confirmed"]
        cand_sizes.append(len(t["candidates"]))
        cand_incl.append(any(r["is_candidate"] for r in t["root_info"]))
    out["root_relevance"] = dict(rel)
    out["candidate_set_size_mean"] = float(np.mean(cand_sizes)) if cand_sizes else None
    out["root_in_candidate_set"] = rate(sum(cand_incl), len(cand_incl))
    out["attribute_without_pag"] = sum(1 for t in tr if t["expected"] == "ATTRIBUTE" and t["pag_status"] != "OK")
    # breakdowns (P1 of V2 and V3 and oracle by dimension)
    bd = {}
    for dim in ("structure", "family", "observability", "workload", "intervention"):
        d = defaultdict(lambda: Counter())
        for sc, i in zip(scs, ids):
            key = sc["dimensions"][dim]
            row = next(r for r in rows if r["scenario_id"] == i)
            d[key]["n"] += 1
            d[key]["pag_ok"] += row["pag"] == "OK"
            if row["pag"] == "OK":
                d[key]["tp"] += row["tp"]; d[key]["fp"] += row["fp"]; d[key]["fn"] += row["fn"]
                d[key]["circle"] += row["circle"]; d[key]["edges"] += row["n_pag_edges"]
            if sc["ground_truth"]["expected_outcome"] == "ATTRIBUTE":
                d[key]["attr"] += 1
                for m, tag in (("RIFT-FULL-V2", "v2"), ("ORACLE:RIFT-FULL-V2-ORACLE-GRAPH", "oracle"), ("V3-FULL", "v3")):
                    d[key]["p1_" + tag] += methods[m][i]["score"]["correct"]
        bd[dim] = {k: dict(v) for k, v in sorted(d.items())}
    out["breakdowns"] = bd
    return out, rows


# ----------------------------------------------------------------------------------------- phase 3
def directionality(scs, tr):
    conf = Counter()          # (class, truth) over ordered observed pairs, learned-PAG scenarios
    sym = Counter()
    rel_named = Counter()
    for sc, t in zip(scs, tr):
        if t["pag_status"] != "OK":
            continue
        T = true_structure(sc)
        obs = sorted(T["obs"])
        marks = {}
        for a, b, ma, mb in t["pag_edges"]:
            marks[(a, b)] = ma; marks[(b, a)] = mb
        mp = ps.MarkedPAG(tuple(obs), marks)
        for x in obs:
            for y in obs:
                if x == y:
                    continue
                c = ps.classify_relation(mp, x, y)
                truth = y in T["anc"].get(x, set())
                conf[(c, truth)] += 1
        for a, b in mp.edges():
            sym[mp.kind(a, b)] += 1
        if t["failure_kind"] == "WRONG_ROOT" and t["root_info"] and t["top1"]:
            ri = t["root_info"][0]
            rel_named[(ri.get("pag_relation_root_to_named"), ri.get("pag_relation_named_to_root"))] += 1
    tab = {}
    for c in ps.HIERARCHY:
        pos, neg = conf.get((c, True), 0), conf.get((c, False), 0)
        tab[c] = {"true_ancestor_pairs": pos, "not_ancestor_pairs": neg, "precision_as_ancestor": pos / (pos + neg) if pos + neg else None}
    total_anc = sum(v for (c, tr_), v in conf.items() if tr_)
    # reverse-direction symmetry: pairs classed POSSIBLE_ANCESTOR in BOTH directions
    sym_pairs = 0
    tot_pairs = 0
    for sc, t in zip(scs, tr):
        if t["pag_status"] != "OK":
            continue
        marks = {}
        for a, b, ma, mb in t["pag_edges"]:
            marks[(a, b)] = ma; marks[(b, a)] = mb
        vs = sorted({v for e in t["pag_edges"] for v in e[:2]})
        mp = ps.MarkedPAG(tuple(vs), marks)
        for i, x in enumerate(vs):
            for y in vs[i + 1:]:
                cxy, cyx = ps.classify_relation(mp, x, y), ps.classify_relation(mp, y, x)
                if cxy in (ps.POSSIBLE_ANCESTOR, ps.DIRECTED_ANCESTOR) or cyx in (ps.POSSIBLE_ANCESTOR, ps.DIRECTED_ANCESTOR):
                    tot_pairs += 1
                    sym_pairs += cxy == ps.POSSIBLE_ANCESTOR and cyx == ps.POSSIBLE_ANCESTOR
    return {"class_vs_truth": tab, "true_ancestor_pairs_total": total_anc, "edge_kinds": dict(sym),
            "connected_pairs_possible_both_directions": rate(sym_pairs, tot_pairs),
            "wrong_root_pag_relation_root_to_named__named_to_root": {str(k): v for k, v in rel_named.items()}}


# ----------------------------------------------------------------------------------------- phase 4
def cid_analysis(scs, tr):
    scd = {s["scenario_id"]: s for s in scs}
    rows = []
    for t in tr:
        s = scd[t["scenario_id"]]; g = sim._graph(s); iv = s["intervention"]
        n = s["telemetry"]["n_windows"]; te = (n - 1) * 10.0
        ts = np.concatenate([te + np.arange(30.0), te + 30 + np.arange(30.0)])
        for r in t["cid_rows"]:
            sy = sim.sigma_of(s, r["y"])
            amp = iv["magnitude_sigma"] * sim.sigma_of(s, r["x"]) * iv["delivered"]
            eff = sum(gn for gn, lg, h in sim.path_responses(g, r["x"], r["y"])) * amp
            fs = sim.fault_series(s, g, r["y"], ts)
            rows.append({"mode": iv["mode"], "anc": r["true_ancestor"], "grade": r["grade"], "n": min(r["n_base"], r["n_post"]),
                         "sig": bool(r["p"] is not None and r["p"] < 0.05), "w1_gate": bool(r["w1"] is not None and r["w1"] > r["theta_cid"]),
                         "d": eff / sy, "fault_drift_sigma": float((fs[30:].mean() - fs[:30].mean()) / sy),
                         "baseline_sigma": sy, "wl": s["dimensions"]["workload"]})
    out = {"n_rows": len(rows), "grades": dict(Counter(r["grade"] for r in rows)), "n_min": dict(Counter(r["n"] for r in rows))}
    out["w1_gate_binding"] = {"sig_but_w1_gate_fails": sum(1 for r in rows if r["sig"] and not r["w1_gate"]),
                              "sig": sum(r["sig"] for r in rows)}
    bins = [(0, 0.25), (0.25, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 99)]
    sens = {}
    for lo, hi in bins:
        sel = [r for r in rows if r["anc"] and lo <= r["d"] < hi]
        sens[f"{lo}-{hi}"] = rate(sum(r["sig"] for r in sel), len(sel))
    out["sensitivity_true_ancestor_by_effect_sigma_y"] = sens
    non = [r for r in rows if not r["anc"]]
    drifted = [r for r in non if abs(r["fault_drift_sigma"]) > 0.3]
    still = [r for r in non if abs(r["fault_drift_sigma"]) <= 0.3]
    out["false_positive_rate_nonancestral"] = {
        "no_fault_drift_between_windows": rate(sum(r["sig"] for r in still), len(still)),
        "fault_drift_gt_0.3sigma": rate(sum(r["sig"] for r in drifted), len(drifted))}
    byd = {}
    for m in sorted({r["mode"] for r in rows}):
        sel = [r for r in rows if r["anc"] and r["mode"] == m]
        byd[m] = {"sensitivity": rate(sum(r["sig"] for r in sel), len(sel)),
                  "median_effect_sigma_y": float(np.median([r["d"] for r in sel])) if sel else None}
    out["by_intervention_mode"] = byd
    return out


def power_curve():
    """Monte-Carlo power of the exact CID gate (permutation p < alpha/m) for Gaussian shifts d*sigma at n=30 vs n=60 per arm."""
    from src.rift.cid.cid import compute_cid
    rng = np.random.default_rng(440)
    res = {}
    for n in (30, 60):
        for m in (1, 3):
            row = {}
            for d in (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0):
                hit = 0
                reps = 150
                for k in range(reps):
                    b = rng.normal(0, 1, n); p = rng.normal(d, 1, n)
                    c = compute_cid(b, p, "x", "y", 0.0, alpha=0.05, n_bootstrap=5, n_permutations=400, seed=int(rng.integers(1 << 30)))
                    hit += c.permutation_pvalue < 0.05 / m
                row[str(d)] = hit / reps
            res[f"n={n},m={m}"] = row
    return res


def main() -> int:
    out = {"note": "DEV/VAL ONLY. Oracle rows are privileged upper bounds."}
    csv_rows = []
    for split in SPLITS:
        scs, ids, methods, tr = load(split)
        tab, S = method_table(scs, ids, methods)
        gs, rows = graph_summary(scs, tr, methods, ids)
        for r in rows:
            r["split"] = split
            csv_rows.append(r)
        out[split] = {"n": len(scs), "methods": tab, "paired": paired(S, scs), "coverage_matched_v3_vs_v2": coverage_matched(S, len(scs)),
                      "failure_summary": failure_summary(tr), "graph": gs, "directionality": directionality(scs, tr),
                      "cid": cid_analysis(scs, tr),
                      "v3_status_counts": dict(Counter(methods["V3-FULL"][i]["record"]["status"] for i in ids)),
                      "v3_answered_by_status": dict(Counter(methods["V3-FULL"][i]["record"]["status"] for i in ids
                                                            if methods["V3-FULL"][i]["score"]["answered"])),
                      "v3_unsafe_by_status": dict(Counter(methods["V3-FULL"][i]["record"]["status"] for i in ids
                                                          if methods["V3-FULL"][i]["score"]["unsafe"])),
                      "v3_caveats_answered": {str(k): v for k, v in Counter(
                          tuple(methods["V3-FULL"][i]["record"]["caveats"]) for i in ids
                          if methods["V3-FULL"][i]["score"]["answered"]).items()}}
    out["cid_power_monte_carlo"] = power_curve()
    (A / "analysis.json").write_text(json.dumps(out, indent=1, default=float))
    with open(A / "graph_quality.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(csv_rows[0]))
        w.writeheader(); w.writerows(csv_rows)
    print("wrote analysis.json, graph_quality.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
