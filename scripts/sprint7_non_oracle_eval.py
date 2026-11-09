#!/usr/bin/env python3
"""Sprint 7 / Workstream 2: NON-ORACLE end-to-end causal evaluation (DEV + VAL only; held-out is never opened).

    PYTHONPATH=src:. python3.11 scripts/sprint7_non_oracle_eval.py <part>

parts
  legacy     : A1 validation-harness (36 dev scenarios, 12 non-conf / 24 conf) and A2 run_reproducible_evaluation path
               (datasets/rift_faults dev 50 / val 18), each with ORACLE PAG vs LEARNED (FCI) PAG, + learned-PAG mark census.
  v2graph    : B  rift_v2 dev+val (252): FCI mark census from the RAW causal-learn matrix, graph quality vs the true DAG.
  v2attr     : C  rift_v2 dev+val (252): V2 / V3 with LEARNED PAG vs ORACLE-DAG (true observed DAG, fully oriented).
  v2poppag   : C' same, but the oracle is the POPULATION PAG (FCI + perfect d-separation oracle; keeps circles). Acyclic only.
  popceiling : FCI with a perfect CI oracle on every acyclic scenario DAG (hidden nodes included): structural ceiling on orientation.
  interv     : D  does a pairwise do(x)->y test disambiguate circle-marked edges? (simulated do(); tc/netem is not available here)
  placebo    : D' null calibration of the D test (perturbation zeroed).
  toy        : population PAGs of textbook structures (chain / fork / collider / hub / latent).
  legacywarn : validation_harness with learned PAG: warning types on confounded vs non-confounded; does the flag change the data?

Writes artifacts/sprint7/ws2_non_oracle/<part>.json (the committed copies carry a _cl0138 / _cl0148 suffix = causal-learn version
used; select the 0.1.4.8 pin with PYTHONPATH=/tmp/cl048:src:. after `pip install --no-deps --target /tmp/cl048 causal-learn==0.1.4.8 momentchi2`). Read-only w.r.t. every other file. No ground truth reaches a method: labels are read
only by the scorers / oracle constructors, which are explicitly labelled ORACLE.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import warnings
from collections import Counter, defaultdict
from pathlib import Path

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO), str(REPO / "src"), str(REPO / "validation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

OUT = REPO / "artifacts" / "sprint7" / "ws2_non_oracle"
OUT.mkdir(parents=True, exist_ok=True)


def dump(name, obj):
    (OUT / f"{name}.json").write_text(json.dumps(obj, indent=1, default=float))


def kind_census(mp):
    """Edge-kind census of a ps.MarkedPAG using the CORRECT causal-learn endpoint convention."""
    from src.rift.attribution_v3 import pag_semantics as ps
    c = Counter()
    for a, b in mp.edges():
        ma, mb = mp.marks[(a, b)], mp.marks[(b, a)]
        c[mp.kind(a, b)] += 1
        c["_circle_any"] += int(ps.CIRCLE in (ma, mb))
        c["_circle_both"] += int((ma, mb) == (ps.CIRCLE, ps.CIRCLE))
        c["_fully_directed"] += int((ma, mb) in ((ps.TAIL, ps.ARROW), (ps.ARROW, ps.TAIL)))
        c["_bidirected"] += int((ma, mb) == (ps.ARROW, ps.ARROW))
        c["_edges"] += 1
    return c


def merge(counters):
    t = Counter()
    for c in counters:
        t.update(c)
    return dict(t)


# ===================================================================================================== legacy parts
def part_legacy():
    import validation_harness as hv
    from src.rift.attribution_v3 import pag_semantics as ps
    from src.rift.fci.fci_runner import run_fci

    services = hv.SyntheticBenchmark.SERVICES
    res = {}

    # ---------------------------------------------------------------- A1: validation harness, 36 dev scenarios
    scs = [s for s in hv.SyntheticBenchmark().generate_all_faults(seed=42) if s.split == hv.SPLIT_DEVELOPMENT]
    orig_build = hv.build_oracle_pag
    census_a1 = []

    def learned_pag(scenario):
        m = hv.generate_oracle_metrics(scenario, services, delta_t=10.0)
        wide = pd.concat({s: df.set_index("time")["value"] for s, df in m.items()}, axis=1).dropna()
        pag = run_fci(wide, alpha=0.05, max_variables=15, seed=scenario.seed)
        census_a1.append(kind_census(ps.decode_marks(pag.variables, pag.adjacency_matrix)))
        return pag

    def run_mode(mode):
        hv.build_oracle_pag = orig_build if mode == "oracle" else learned_pag
        try:
            return [hv.validate_scenario(s, services) for s in scs]
        finally:
            hv.build_oracle_pag = orig_build

    a1 = {}
    for mode in ("oracle", "learned"):
        rs = run_mode(mode)
        nc = [r for r in rs if not r.confounded]
        cf = [r for r in rs if r.confounded]
        a1[mode] = {
            "n_nonconf": len(nc), "n_conf": len(cf),
            "nonconf_root_found_any_rank_CAND_or_DEF": sum(r.root_cause_found for r in nc),
            "nonconf_top1_correct": sum(r.top_candidate == r.root_cause for r in nc),
            "nonconf_abstained_empty_ebd": sum(r.abstained for r in nc),
            "nonconf_wrong_top1": sum((not r.abstained) and r.top_candidate != r.root_cause for r in nc),
            "conf_abstained_empty_ebd": sum(r.abstained for r in cf),
            "conf_warning_only": sum((not r.abstained) and r.has_assumption_warning for r in cf),
            "conf_neither_abstain_nor_warning": sum((not r.abstained) and (not r.has_assumption_warning) for r in cf),
            "conf_top1_is_true_root": sum(r.top_candidate == r.root_cause for r in cf),
            "harness_V2_metric_abstain_or_warning": sum(r.abstained or r.has_assumption_warning for r in cf),
            "far_wrong_top1_over_nonconf": sum((not r.abstained) and r.top_candidate != r.root_cause for r in nc) / len(nc),
        }
    a1["learned_pag_mark_census"] = merge(census_a1)
    a1["learned_pag_n_scenarios_with_zero_edges"] = sum(1 for c in census_a1 if c.get("_edges", 0) == 0)
    res["A1_validation_harness_36dev"] = a1

    # ---------------------------------------------------------------- A2: run_reproducible_evaluation path (rift_faults)
    spec = importlib.util.spec_from_file_location("rre", REPO / "scripts" / "run_reproducible_evaluation.py")
    rre = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rre)
    from rift.baselines import IncidentContext
    svc = rre.SyntheticBenchmark.SERVICES
    cg = rre.build_call_graph()
    bs = {s: {"mean": 0.0, "std": 10.0} for s in svc}

    def ctx_of(sc):
        m = rre.generate_scenario_metrics(sc, svc, 10.0, sc.get("seed", 42))
        ia = sc.get("injected_at_t", 60.0)
        return IncidentContext(fault_id=sc["fault_id"], incident_window=(max(0, ia - 60), ia + 120), metrics=m,
                               baseline_stats=bs, call_graph=cg, scenario_seed=sc.get("seed", 42))

    a2 = {}
    for split_name, fname in (("dev50", "development.json"), ("val18", "validation.json")):
        data = json.load(open(REPO / "datasets" / "rift_faults" / fname))["scenarios"]
        per = {"oracle": [], "learned": []}
        cen = []
        for sc in data:
            ctx = ctx_of(sc)
            for mode in ("oracle", "learned"):
                o = rre.run_rift_full_scenario(sc, ctx, use_oracle_pag=(mode == "oracle"))
                if o.abstained:
                    outcome = "ABSTAIN:" + str(o.abstention_reason).split(":")[0]
                else:
                    outcome = "ATTR_OK" if o.top_candidates[0][0] == sc["root_cause_service"] else "ATTR_WRONG"
                per[mode].append({"id": sc["fault_id"], "conf": bool(sc["confounded"]), "outcome": outcome,
                                  "fault_type": sc["fault_type"]})
            t0, t1 = ctx.incident_window
            wide = pd.concat([df[(df["time"] >= t0) & (df["time"] <= t1)].rename(columns={"value": s}).set_index("time")
                              for s, df in ctx.metrics.items()], axis=1).dropna()
            try:
                p = run_fci(wide, alpha=0.05, max_variables=15, seed=ctx.scenario_seed)
                cen.append(kind_census(ps.decode_marks(p.variables, p.adjacency_matrix)))
            except Exception:  # noqa: BLE001
                cen.append(Counter({"_fci_error": 1}))
        block = {"n": len(data)}
        for mode in ("oracle", "learned"):
            rows = per[mode]
            cm = {"NONCONF": Counter(), "CONF": Counter()}
            for r in rows:
                cm["CONF" if r["conf"] else "NONCONF"][r["outcome"]] += 1
            block[mode] = {k: dict(v) for k, v in cm.items()}
            nc = [r for r in rows if not r["conf"]]
            cf = [r for r in rows if r["conf"]]
            ans = [r for r in rows if not r["outcome"].startswith("ABSTAIN")]
            block[mode]["summary"] = {
                "nonconf_P1_over_all_nonconf": sum(r["outcome"] == "ATTR_OK" for r in nc) / max(1, len(nc)),
                "nonconf_P1_k": sum(r["outcome"] == "ATTR_OK" for r in nc), "nonconf_n": len(nc),
                "conf_abstained_k": sum(r["outcome"].startswith("ABSTAIN") for r in cf), "conf_n": len(cf),
                "conf_answered_k": sum(not r["outcome"].startswith("ABSTAIN") for r in cf),
                "answered_total": len(ans),
                "wrong_answers_total": sum(r["outcome"] == "ATTR_WRONG" for r in rows),
                "FAR_wrong_over_answered": (sum(r["outcome"] == "ATTR_WRONG" for r in rows) / len(ans)) if ans else None,
                "FAR_answers_on_conf_over_conf": sum(not r["outcome"].startswith("ABSTAIN") for r in cf) / max(1, len(cf)),
            }
        block["learned_pag_mark_census"] = merge(cen)
        block["learned_pag_scenarios_with_zero_edges"] = sum(1 for c in cen if c.get("_edges", 0) == 0)
        block["per_scenario"] = per
        a2[split_name] = block
    res["A2_reproducible_eval_path"] = a2
    dump("legacy", res)
    print(json.dumps({k: (v if k != "A2_reproducible_eval_path" else {s: {m: b[m] for m in ("n", "oracle", "learned", "learned_pag_mark_census")}
                                                                         for s, b in v.items()}) for k, v in res.items()}, indent=1, default=float))


# ===================================================================================================== v2 graph census
def _learn(sc):
    from src.rift.evaluation.rift_v2 import _wide_for_fci
    from src.rift.fci.fci_runner import run_fci
    from src.rift.scenarios import simulator as sim
    o = sim.observe(sc)
    wide = _wide_for_fci(o["metrics"])
    if wide is None:
        return o, ("ERR", "INSUFFICIENT_SAMPLES")
    try:
        return o, ("OK", run_fci(wide, alpha=0.05, max_variables=15, seed=int(sc["seed"])))
    except Exception as exc:  # noqa: BLE001
        return o, ("ERR", f"{type(exc).__name__}")


def part_v2graph():
    from src.rift.attribution_v3 import pag_semantics as ps
    from src.rift.attribution_v3.diagnostics import graph_quality
    from src.rift.evaluation.dataset_registry_v2 import load_v2
    out = {}
    pooled = Counter()
    gq_pooled = Counter()
    for split in ("dev", "val"):
        scs = load_v2(split).scenarios
        census, status, gq_sum = [], Counter(), Counter()
        per_scen_circle = []
        for sc in scs:
            o, (tag, val) = _learn(sc)
            status[tag if tag == "OK" else val] += 1
            if tag != "OK":
                continue
            mp = ps.decode_marks(val.variables, val.adjacency_matrix)
            c = kind_census(mp)
            census.append(c)
            # frozen decoder view (what V2 / the legacy pipeline actually consumes)
            for e in val.edges:
                c["frozen_" + e.edge_type.value] += 1
            g = graph_quality(sc, mp)
            for k in ("tp", "fp", "fn", "n_true_direct_edges"):
                gq_sum[k] += g.get(k, 0)
            for k, v in g.get("orientation_on_true_edges", {}).items():
                gq_sum["or_" + k] += v
            if c.get("_edges", 0):
                per_scen_circle.append((c["_circle_any"], c["_edges"]))
        cen = merge(census)
        n_zero = sum(1 for c in census if c.get("_edges", 0) == 0)
        n_all_circle = sum(1 for a, b in per_scen_circle if a == b)
        n_any_oriented = sum(1 for a, b in per_scen_circle if a < b)
        out[split] = {"n": len(scs), "pag_status": dict(status), "census": cen, "gq": dict(gq_sum),
                      "scenarios_with_zero_edges": n_zero, "scenarios_with_edges": len(per_scen_circle),
                      "scenarios_every_edge_circle_marked": n_all_circle, "scenarios_with_any_non_circle_edge": n_any_oriented}
        pooled.update(cen)
        gq_pooled.update(gq_sum)
    out["pooled"] = {"census": dict(pooled), "gq": dict(gq_pooled)}
    E = pooled["_edges"]
    out["pooled"]["share_circle_any"] = pooled["_circle_any"] / E
    out["pooled"]["share_o_o_both_circle"] = pooled["_circle_both"] / E
    out["pooled"]["share_fully_directed"] = pooled["_fully_directed"] / E
    out["pooled"]["share_bidirected"] = pooled["_bidirected"] / E
    dump("v2graph", out)
    print(json.dumps(out, indent=1, default=float))


# ===================================================================================================== v2 attribution
def _score(sc, out, bm):
    rec = bm._out_to_rec(out, 0.0, 0.0)
    return rec, bm.score_one(sc, rec)


def part_v2attr():
    import networkx as nx  # noqa: F401
    from src.rift.attribution_v3 import pag_semantics as ps
    from src.rift.attribution_v3.diagnostics import true_structure
    from src.rift.attribution_v3.rift_v3 import V3_CONFIGS, run_v3
    from src.rift.evaluation import benchmark_v2 as bm
    from src.rift.evaluation.dataset_registry_v2 import load_v2
    from src.rift.evaluation.rift_v2 import CONFIGS, SharedCache, run_v2
    from src.rift.scenarios import simulator as sim

    rows = []
    for split in ("dev", "val"):
        for sc in load_v2(split).scenarios:
            o = sim.observe(sc)
            fid, seed = sc["scenario_id"], int(sc["seed"])
            iv = lambda x, ys, s, sc=sc: sim.intervene(sc, x, ys, s)  # noqa: E731
            T = true_structure(sc)
            obs = sorted(T["obs"])
            oracle_mp = ps.from_true_dag(obs, sorted(T["direct"]))
            oracle_pag_res = bm._true_pag(sc)
            r = {"id": fid, "split": split, "structure": sc["dimensions"]["structure"],
                 "expected": sc["ground_truth"]["expected_outcome"], "abstain_reason_gt": sc["ground_truth"]["abstain_reason"]}
            cache = SharedCache()
            r["V2_learned"] = _score(sc, run_v2(o, iv, fid, seed, CONFIGS["A1-FULL"], cache=cache), bm)
            r["V2_oracle"] = _score(sc, run_v2(o, iv, fid, seed, CONFIGS["A9-ORACLE-GRAPH"], cache=SharedCache(),
                                              pag_override=oracle_pag_res), bm)
            c3 = SharedCache()
            r["V3_learned"] = _score(sc, run_v3(o, iv, fid, seed, V3_CONFIGS["V3-FULL"], cache=c3), bm)
            r["V3_oracle"] = _score(sc, run_v3(o, iv, fid, seed, V3_CONFIGS["V3-FULL"], cache=SharedCache(), pag_override=oracle_mp), bm)
            rows.append(r)
    methods = ("V2_learned", "V2_oracle", "V3_learned", "V3_oracle")

    def agg(sub, m):
        S = [r[m][1] for r in sub]
        att = [s for s in S if s["expected"] == "ATTRIBUTE"]
        ab = [s for s in S if s["expected"] == "ABSTAIN_REQUIRED"]
        ans = [s for s in S if s["answered"]]
        return {"N": len(S), "n_attribute": len(att), "n_abstain_required": len(ab),
                "P1_k": sum(s["correct"] for s in att), "answered_k": len(ans),
                "answered_on_attribute": sum(s["answered"] for s in att),
                "wrong_root_k": sum(s["wrong_root"] for s in att),
                "abstained_on_attribute": sum(not s["answered"] for s in att),
                "abstain_required_correctly_abstained_k": sum(not s["answered"] for s in ab),
                "abstain_required_answered_k": sum(s["answered"] for s in ab),
                "unsafe_k": sum(s["unsafe"] for s in S),
                "FAR_unsafe_over_answered": (sum(s["unsafe"] for s in S) / len(ans)) if ans else None,
                "unsafe_over_N": sum(s["unsafe"] for s in S) / len(S),
                "P2_k": sum(s["p2"] for s in S)}

    out = {"n": len(rows), "methods": {}}
    subsets = {
        "ALL": rows,
        "dev": [r for r in rows if r["split"] == "dev"],
        "val": [r for r in rows if r["split"] == "val"],
        "CONFOUNDING_FAMILY(confounding+hidden_common_cause)": [r for r in rows if r["structure"] in ("confounding", "hidden_common_cause")],
        "hidden_common_cause(ROOT_UNOBSERVED,abstain_required)": [r for r in rows if r["structure"] == "hidden_common_cause"],
        "confounding(structure label)": [r for r in rows if r["structure"] == "confounding"],
        "ABSTAIN_REQUIRED_all": [r for r in rows if r["expected"] == "ABSTAIN_REQUIRED"],
    }
    for name, sub in subsets.items():
        out["methods"][name] = {m: agg(sub, m) for m in methods}
    # confusion (expected x outcome) per method over ALL
    conf = {}
    for m in methods:
        cm = {"ATTRIBUTE": Counter(), "ABSTAIN_REQUIRED": Counter()}
        for r in rows:
            s = r[m][1]
            o_ = ("CORRECT_ROOT" if s["correct"] else "WRONG_ROOT" if s["wrong_root"] else
                  "ANSWERED_WHEN_ABSTAIN_REQUIRED" if (s["answered"] and s["expected"] == "ABSTAIN_REQUIRED") else "ABSTAINED")
            cm[s["expected"]][o_] += 1
        conf[m] = {k: dict(v) for k, v in cm.items()}
    out["confusion_ALL"] = conf
    # abstain reason census for learned vs oracle V2
    rc = {}
    for m in methods:
        c = Counter()
        for r in rows:
            c[(r[m][0].get("reason") or "ANSWERED")] += 1
        rc[m] = dict(c)
    out["reason_census"] = rc
    out["per_scenario"] = [{"id": r["id"], "split": r["split"], "structure": r["structure"], "expected": r["expected"],
                            **{m: {"abstained": r[m][0]["abstained"], "reason": r[m][0]["reason"],
                                   "top1": r[m][1]["top1"], "correct": r[m][1]["correct"], "unsafe": r[m][1]["unsafe"]} for m in methods}}
                           for r in rows]
    dump("v2attr", out)
    print(json.dumps({k: v for k, v in out.items() if k != "per_scenario"}, indent=1, default=float))


# ===================================================================================================== interventions
def part_interv():
    import zlib
    from src.rift.attribution_v3 import pag_semantics as ps
    from src.rift.attribution_v3.diagnostics import _edge_truth_class, true_structure
    from src.rift.cid.cid import compute_cid
    from src.rift.cid.evidence import validate_cid_for_r4
    from src.rift.evaluation.dataset_registry_v2 import load_v2
    from src.rift.scenarios import simulator as sim

    def test(sc, x, y, tag):
        s = (int(sc["seed"]) * 7919 + zlib.crc32(f"{x}->{y}|{tag}".encode())) & 0x7FFFFFFF
        have = sim.intervene(sc, x, [y], s)
        base, post = have[y]
        r = compute_cid(base, post, x, y, t_intervention=0.0, alpha=0.05, n_bootstrap=100, n_permutations=1000, seed=s)
        ok, _ = validate_cid_for_r4(r, r.theta_cid)
        return bool(ok)

    rows = []
    do_counts = []
    for split in ("dev", "val"):
        for sc in load_v2(split).scenarios:
            o, (tag, val) = _learn(sc)
            if tag != "OK":
                continue
            mp = ps.decode_marks(val.variables, val.adjacency_matrix)
            T = true_structure(sc)
            nodes_needed = set()
            for a, b in mp.edges():
                ma, mb = mp.marks[(a, b)], mp.marks[(b, a)]
                circle = ps.CIRCLE in (ma, mb)
                if circle:
                    nodes_needed.update((a, b))
                fa, fb = test(sc, a, b, "f"), test(sc, b, a, "b")
                verdict = ("A->B" if fa and not fb else "B->A" if fb and not fa else "BOTH" if fa and fb else "NONE")
                a_anc_b = b in T["anc"].get(a, set())
                b_anc_a = a in T["anc"].get(b, set())
                truth_dir = "A->B" if a_anc_b and not b_anc_a else "B->A" if b_anc_a and not a_anc_b else "BOTH" if a_anc_b and b_anc_a else "NONE"
                rows.append({"split": split, "sid": sc["scenario_id"], "kind": mp.kind(a, b), "circle": circle,
                             "truth_class": _edge_truth_class(T, a, b), "verdict": verdict, "truth_dir": truth_dir,
                             "iv_dim": sc["dimensions"]["observability"] if sc["dimensions"]["observability"] == "weak_interventional_evidence" else "other",
                             "intervention_mode": sc["intervention"]["mode"],
                             "has_collateral": bool(sc["intervention"].get("collateral"))})
            if nodes_needed:
                do_counts.append(len(nodes_needed))

    def summ(sub):
        n = len(sub)
        c = Counter(r["verdict"] for r in sub)
        oriented = [r for r in sub if r["verdict"] in ("A->B", "B->A")]
        correct = [r for r in oriented if r["verdict"] == r["truth_dir"]]
        truth_dir_known = [r for r in sub if r["truth_dir"] in ("A->B", "B->A")]
        rec_ = [r for r in truth_dir_known if r["verdict"] == r["truth_dir"]]
        non_anc = [r for r in sub if r["truth_dir"] == "NONE"]
        return {"n_edges": n, "verdicts": dict(c), "oriented_k": len(oriented),
                "oriented_correct_k": len(correct), "oriented_wrong_k": len(oriented) - len(correct),
                "edges_with_true_ancestral_direction_k": len(truth_dir_known), "of_which_recovered_correctly_k": len(rec_),
                "edges_with_no_ancestry_k": len(non_anc),
                "of_which_correctly_NONE_k": sum(r["verdict"] == "NONE" for r in non_anc),
                "of_which_falsely_oriented_k": sum(r["verdict"] in ("A->B", "B->A") for r in non_anc),
                "by_truth_class": {k: dict(Counter(r["verdict"] for r in sub if r["truth_class"] == k))
                                   for k in ("DIRECT", "INDIRECT_ANCESTRAL", "HIDDEN_COMMON_CAUSE", "UNRELATED")}}

    out = {"all_edges": summ(rows), "circle_marked_edges": summ([r for r in rows if r["circle"]]),
           "non_circle_edges": summ([r for r in rows if not r["circle"]]),
           "circle_marked_by_split": {s: summ([r for r in rows if r["circle"] and r["split"] == s]) for s in ("dev", "val")},
           "circle_marked_weak_interventional_evidence": summ([r for r in rows if r["circle"] and r["iv_dim"] != "other"]),
           "circle_marked_other_observability": summ([r for r in rows if r["circle"] and r["iv_dim"] == "other"]),
           "circle_marked_with_collateral_leakage": summ([r for r in rows if r["circle"] and r["has_collateral"]]),
           "circle_marked_without_collateral_leakage": summ([r for r in rows if r["circle"] and not r["has_collateral"]]),
           "do_nodes_needed_per_scenario": {"n_scenarios": len(do_counts), "mean": float(np.mean(do_counts)) if do_counts else None,
                                            "max": int(max(do_counts)) if do_counts else None,
                                            "n_over_MAX_DO_20": int(sum(c > 20 for c in do_counts))}}
    # PAG-only orientation (no interventions) on the same circle edges, for comparison: share of ancestry-known edges FCI orients
    dump("interv", out)
    dump("interv_rows", rows)
    print(json.dumps(out, indent=1, default=float))


# ===================================================================================================== population PAG ceiling
def part_popceiling():
    """FCI with a PERFECT conditional-independence oracle (d-separation on the true DAG incl. hidden nodes).
    Gives the best PAG any sample size could yield for each scenario's graph => structural ceiling on orientation."""
    import networkx as nx
    from causallearn.search.ConstraintBased.FCI import fci
    from causallearn.utils.cit import d_separation
    from src.rift.attribution_v3 import pag_semantics as ps
    from src.rift.evaluation.dataset_registry_v2 import load_v2
    from src.rift.scenarios import simulator as sim
    if not hasattr(nx, "d_separated"):          # causal-learn 0.1.3.8 calls the pre-3.3 networkx name
        nx.d_separated = nx.is_d_separator
    agg = {}
    tot = Counter()
    for split in ("dev", "val"):
        c = Counter()
        n_ok = 0
        for sc in load_v2(split).scenarios:
            g = sim._graph(sc)
            obs = sorted(sim.observed_services(sc))
            if len(obs) < 2:
                continue
            idx = {s: i for i, s in enumerate(obs)}
            G = nx.DiGraph()
            G.add_nodes_from(range(len(obs)))
            for a, b in g.edges:
                na = idx.get(a, f"h::{a}")
                nb = idx.get(b, f"h::{b}")
                G.add_edge(na, nb)
            if not nx.is_directed_acyclic_graph(G):      # SYMMETRIC_MUTUAL_DEPENDENCY: d-separation undefined
                c["skipped_cyclic"] += 1
                continue
            res = fci(np.zeros((5, len(obs))), d_separation, 0.05, verbose=False, show_progress=False, true_dag=G)
            mp = ps.decode_marks(obs, res[0].graph)
            k = kind_census(mp)
            c.update(k)
            n_ok += 1
            tdirect = {frozenset(e) for e in g.edges if e[0] in idx and e[1] in idx}
            c["true_direct_observed"] += len(tdirect)
            c["pop_adjacent_true_direct"] += sum(1 for a, b in mp.edges() if frozenset((a, b)) in tdirect)
        agg[split] = {"n_scenarios": n_ok, **dict(c)}
        tot.update(c)
    agg["pooled"] = dict(tot)
    E = tot["_edges"]
    agg["pooled_shares"] = {"circle_any": tot["_circle_any"] / E, "o-o": tot["_circle_both"] / E,
                            "fully_directed": tot["_fully_directed"] / E, "bidirected": tot["_bidirected"] / E}
    dump("popceiling", agg)
    print(json.dumps(agg, indent=1, default=float))


# ===================================================================================================== population-PAG attribution
def part_v2poppag():
    """V2/V3 run with the POPULATION PAG (FCI + perfect d-separation oracle on the true DAG incl. hidden nodes) vs the learned PAG.
    This is the honest 'oracle PAG' (it keeps circles and bidirected edges), as opposed to the oracle-DAG used by the benchmark."""
    import networkx as nx
    from causallearn.search.ConstraintBased.FCI import fci
    from causallearn.utils.cit import d_separation
    from src.rift.attribution_v3 import pag_semantics as ps
    from src.rift.attribution_v3.rift_v3 import V3_CONFIGS, run_v3
    from src.rift.evaluation import benchmark_v2 as bm
    from src.rift.evaluation.dataset_registry_v2 import load_v2
    from src.rift.evaluation.rift_v2 import CONFIGS, SharedCache, run_v2
    from src.rift.scenarios import simulator as sim
    if not hasattr(nx, "d_separated"):
        nx.d_separated = nx.is_d_separator

    class T:  # template for ps.to_pag_result
        def __init__(self, vs, m):
            self.variables, self.adjacency_matrix, self.alpha = list(vs), m, 0.05
            self.n_samples_used, self.n_variables = 0, len(vs)

    rows = []
    n_cyclic = 0
    for split in ("dev", "val"):
        for sc in load_v2(split).scenarios:
            g = sim._graph(sc)
            obs = sorted(sim.observed_services(sc))
            idx = {x: i for i, x in enumerate(obs)}
            G = nx.DiGraph()
            G.add_nodes_from(range(len(obs)))
            for a, b in g.edges:
                G.add_edge(idx.get(a, f"h::{a}"), idx.get(b, f"h::{b}"))
            if len(obs) < 2 or not nx.is_directed_acyclic_graph(G):
                n_cyclic += 1
                continue
            m = fci(np.zeros((5, len(obs))), d_separation, 0.05, verbose=False, show_progress=False, true_dag=G)[0].graph
            mp = ps.decode_marks(obs, m)
            pagres = ps.to_pag_result(mp, T(obs, m))
            o = sim.observe(sc)
            fid, seed = sc["scenario_id"], int(sc["seed"])
            iv = lambda x, ys, sd, sc=sc: sim.intervene(sc, x, ys, sd)  # noqa: E731
            r = {"id": fid, "split": split, "structure": sc["dimensions"]["structure"],
                 "expected": sc["ground_truth"]["expected_outcome"]}
            r["V2_learned"] = _score(sc, run_v2(o, iv, fid, seed, CONFIGS["A1-FULL"], cache=SharedCache()), bm)
            r["V2_popPAG"] = _score(sc, run_v2(o, iv, fid, seed, CONFIGS["A9-ORACLE-GRAPH"], cache=SharedCache(), pag_override=pagres), bm)
            r["V3_learned"] = _score(sc, run_v3(o, iv, fid, seed, V3_CONFIGS["V3-FULL"], cache=SharedCache()), bm)
            r["V3_popPAG"] = _score(sc, run_v3(o, iv, fid, seed, V3_CONFIGS["V3-FULL"], cache=SharedCache(), pag_override=mp), bm)
            rows.append(r)
    methods = ("V2_learned", "V2_popPAG", "V3_learned", "V3_popPAG")

    def agg(sub, mth):
        S = [r[mth][1] for r in sub]
        att = [x for x in S if x["expected"] == "ATTRIBUTE"]
        ab = [x for x in S if x["expected"] == "ABSTAIN_REQUIRED"]
        ans = [x for x in S if x["answered"]]
        return {"N": len(S), "n_attribute": len(att), "n_abstain_required": len(ab), "P1_k": sum(x["correct"] for x in att),
                "wrong_root_k": sum(x["wrong_root"] for x in att), "answered_k": len(ans),
                "abstain_required_correct_k": sum(not x["answered"] for x in ab),
                "abstain_required_answered_k": sum(x["answered"] for x in ab), "unsafe_k": sum(x["unsafe"] for x in S),
                "P2_k": sum(x["p2"] for x in S)}
    subs = {"ALL_acyclic": rows, "dev": [r for r in rows if r["split"] == "dev"], "val": [r for r in rows if r["split"] == "val"],
            "confounding+hidden_common_cause": [r for r in rows if r["structure"] in ("confounding", "hidden_common_cause")],
            "hidden_common_cause": [r for r in rows if r["structure"] == "hidden_common_cause"]}
    out = {"n_acyclic_scored": len(rows), "n_cyclic_skipped": n_cyclic,
           "agg": {k: {m: agg(v, m) for m in methods} for k, v in subs.items()}}
    dump("v2poppag", out)
    print(json.dumps(out, indent=1, default=float))


# ===================================================================================================== placebo for the do() edge test
def part_placebo():
    """Null calibration of the pairwise do(x)->y test used in part_interv: same circle-marked edges, but the perturbation is
    zeroed (magnitude_sigma=0, no collateral). Any 'pass' is then NOT caused by the intervention (fault drift / chance)."""
    import copy
    import zlib
    from src.rift.attribution_v3 import pag_semantics as ps
    from src.rift.cid.cid import compute_cid
    from src.rift.cid.evidence import validate_cid_for_r4
    from src.rift.evaluation.dataset_registry_v2 import load_v2
    from src.rift.scenarios import simulator as sim

    def gate(sc, x, y, tag):
        sd = (int(sc["seed"]) * 7919 + zlib.crc32(f"{x}->{y}|{tag}".encode())) & 0x7FFFFFFF
        base, post = sim.intervene(sc, x, [y], sd)[y]
        r = compute_cid(base, post, x, y, t_intervention=0.0, alpha=0.05, n_bootstrap=100, n_permutations=1000, seed=sd)
        return bool(validate_cid_for_r4(r, r.theta_cid)[0])

    n = k = 0
    kf = Counter()
    for split in ("dev", "val"):
        for sc in load_v2(split).scenarios:
            o, (tag, val) = _learn(sc)
            if tag != "OK":
                continue
            mp = ps.decode_marks(val.variables, val.adjacency_matrix)
            z = copy.deepcopy(sc)
            z["intervention"]["magnitude_sigma"] = 0.0
            z["intervention"]["collateral"] = {}
            z["intervention"]["multi_service"] = False
            has_fault_shape = Counter(f["shape"] for f in sc["faults"])
            for a, b in mp.edges():
                if ps.CIRCLE not in (mp.marks[(a, b)], mp.marks[(b, a)]):
                    continue
                for x, y in ((a, b), (b, a)):
                    n += 1
                    g = gate(z, x, y, "placebo")
                    k += g
                    kf["pass" if g else "fail"] += 1
    out = {"n_directed_tests": n, "placebo_passes": k, "placebo_pass_rate": k / n}
    dump("placebo", out)
    print(json.dumps(out, indent=1))


# ===================================================================================================== toy population PAGs
def part_toy():
    """Population-level FCI (perfect d-separation oracle) on 4 textbook structures: what marks FCI CAN commit to at all."""
    import networkx as nx
    from causallearn.search.ConstraintBased.FCI import fci
    from causallearn.utils.cit import d_separation
    from src.rift.attribution_v3 import pag_semantics as ps
    if not hasattr(nx, "d_separated"):
        nx.d_separated = nx.is_d_separator
    cases = {
        "chain A->B->C": ([("A", "B"), ("B", "C")], ["A", "B", "C"]),
        "fork A<-B->C": ([("B", "A"), ("B", "C")], ["A", "B", "C"]),
        "collider A->C<-B": ([("A", "C"), ("B", "C")], ["A", "B", "C"]),
        "hub root->{x,y,z}": ([("R", "X"), ("R", "Y"), ("R", "Z")], ["R", "X", "Y", "Z"]),
        "latent  A<-H->B (H hidden)": ([("H", "A"), ("H", "B")], ["A", "B"]),
        "latent + collider A<-H->B->C<-D": ([("H", "A"), ("H", "B"), ("B", "C"), ("D", "C")], ["A", "B", "C", "D"]),
    }
    out = {}
    for name, (edges, obs) in cases.items():
        nodes = sorted({x for e in edges for x in e} | set(obs))
        idx = {n: i for i, n in enumerate(obs)}
        G = nx.DiGraph()
        G.add_nodes_from(range(len(obs)))
        for a, b in edges:
            G.add_edge(idx.get(a, f"h::{a}"), idx.get(b, f"h::{b}"))
        m = fci(np.zeros((5, len(obs))), d_separation, 0.05, verbose=False, show_progress=False, true_dag=G)[0].graph
        mp = ps.decode_marks(obs, m)
        out[name] = {f"{a}-{b}": mp.kind(a, b) for a, b in mp.edges()}
    dump("toy", out)
    print(json.dumps(out, indent=1))


# ===================================================================================================== legacy harness: what do the warnings say
def part_legacywarn():
    """validation_harness with the LEARNED PAG: which kind of assumption_warning do confounded vs non-confounded scenarios raise,
    and is the confounded flag visible in the generated data at all (it is not)."""
    import validation_harness as hv
    from src.rift.fci.fci_runner import run_fci
    services = hv.SyntheticBenchmark.SERVICES
    scs = [s for s in hv.SyntheticBenchmark().generate_all_faults(seed=42) if s.split == hv.SPLIT_DEVELOPMENT]
    orig = hv.build_oracle_pag

    def learned(sc):
        m = hv.generate_oracle_metrics(sc, services, delta_t=10.0)
        wide = pd.concat({s: df.set_index("time")["value"] for s, df in m.items()}, axis=1).dropna()
        return run_fci(wide, alpha=0.05, max_variables=15, seed=sc.seed)

    def has_bi(r):
        return any(("idirected" in w or "hidden" in w.lower()) for e in r.ebd_results for w in e.assumption_warnings)

    def has_semi(r):
        return any("non-oriented" in w for e in r.ebd_results for w in e.assumption_warnings)
    out = {}
    for mode in ("oracle", "learned"):
        hv.build_oracle_pag = orig if mode == "oracle" else learned
        try:
            rs = [hv.validate_scenario(s, services) for s in scs]
        finally:
            hv.build_oracle_pag = orig
        o = {}
        for lab, flag in (("confounded", True), ("non_confounded", False)):
            g = [r for r in rs if r.confounded == flag]
            o[lab] = {"n": len(g), "any_warning": sum(r.has_assumption_warning for r in g), "bidirected_warning": sum(map(has_bi, g)),
                      "semi_directed_warning": sum(map(has_semi, g)),
                      "top_ebd_identifiability_NOT_IDENTIFIABLE": sum(bool(r.ebd_results) and r.ebd_results[0].identifiability_state == "NOT_IDENTIFIABLE" for r in g),
                      "abstained_empty_ebd": sum(r.abstained for r in g)}
        out[mode] = o
    # does the confounded flag change the generated data?
    chg = 0
    for sc in scs:
        if not sc.confounded:
            continue
        import dataclasses
        m1 = hv.generate_oracle_metrics(sc, services)
        m2 = hv.generate_oracle_metrics(dataclasses.replace(sc, confounded=False), services)
        chg += any(not m1[s].equals(m2[s]) for s in services)
    out["confounded_scenarios_whose_data_change_when_flag_flipped"] = chg
    from scipy.stats import fisher_exact
    lc, ln = out["learned"]["confounded"], out["learned"]["non_confounded"]
    out["fisher_p_bidirected_warning_conf_vs_nonconf_learned"] = fisher_exact([[lc["bidirected_warning"], lc["n"] - lc["bidirected_warning"]],
                                                                               [ln["bidirected_warning"], ln["n"] - ln["bidirected_warning"]]])[1]
    out["fisher_p_any_warning_conf_vs_nonconf_learned"] = fisher_exact([[lc["any_warning"], lc["n"] - lc["any_warning"]],
                                                                        [ln["any_warning"], ln["n"] - ln["any_warning"]]])[1]
    dump("legacywarn", out)
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    part = sys.argv[1] if len(sys.argv) > 1 else ""
    {"legacy": part_legacy, "v2graph": part_v2graph, "v2attr": part_v2attr, "interv": part_interv, "popceiling": part_popceiling, "v2poppag": part_v2poppag, "placebo": part_placebo, "toy": part_toy, "legacywarn": part_legacywarn}[part]()
