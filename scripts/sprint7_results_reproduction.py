#!/usr/bin/env python3
"""Sprint 7 / Workstream 3: independent reproduction of the headline empirical findings (dev+val only, N=252).

    PYTHONPATH=src:. python3.11 scripts/sprint7_results_reproduction.py [--no-rerun]

Reads: datasets/rift_v2/{dev,val}.json (sha256-pinned), artifacts/sprint4_3_0/results/{dev,val}/per_scenario.json,
       artifacts/sprint4_4_0/v3_{dev,val}.json.  NEVER opens held-out data.
Scoring is re-implemented here from (label, record); it does not import benchmark_v2.score_one.
Unless --no-rerun, ALL methods (8 registered baselines, RIFT-FULL-V2, V3-FULL) are executed FRESH on the 252 scenarios
(simulator + methods, deterministic seeds) and compared field-by-field with the saved records.
Outputs: artifacts/sprint7/reproduction/{results.json, fresh_records.json}
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import warnings
from collections import Counter
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO), str(REPO / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
OUT = REPO / "artifacts" / "sprint7" / "reproduction"
PINS = {"dev": "a833ad0ca1db0583a30bc4450f9f59b2984a5823702935ef59c6b037e026ef5f",
        "val": "e82252b47f29dc1353586034b6fd8c3491df3221851f9c84c48bf717a944a1fb"}
MAX_DO = 20
LAMBDAS = [0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
KAPPAS = [0.0, 0.025, 0.05, 0.10]
BASELINES = ["B0-EARLIEST", "B0-HIGHEST", "B1-LATENCY-CORR", "B3-SIEVE-LIKE", "B5-RIFT-OBS", "B6-RIFT-RANDOM",
             "B7-RIFT-ONE-SHOT", "ORACLE:UPPER-BOUND"]
ALL_METHODS = BASELINES + ["RIFT-FULL-V2", "V3-FULL"]
SEED_MAIN, B_MAIN, B_GRID = 4510, 10000, 4000


# ------------------------------------------------------------------------------------------- independent scoring
def score(sc, rec):
    gt = sc["ground_truth"]
    exp, roots = gt["expected_outcome"], set(gt["roots"])
    ans = not rec["abstained"]
    top1 = rec["top"][0][0] if (ans and rec["top"]) else None
    correct = bool(ans and exp == "ATTRIBUTE" and top1 in roots)
    unsafe = bool(ans and (exp == "ABSTAIN_REQUIRED" or top1 not in roots))
    unsafe_op = bool(ans and top1 not in roots)
    lucky = bool(ans and exp == "ABSTAIN_REQUIRED" and top1 in roots)
    return dict(answered=ans, correct=correct, unsafe=unsafe, unsafe_op=unsafe_op, lucky=lucky, top1=top1,
                n_do=int(rec["n_do"]), ed_s=float(rec["ed_s"]), expected=exp,
                wrong_root=bool(ans and exp == "ATTRIBUTE" and top1 not in roots),
                answered_on_AR=bool(ans and exp == "ABSTAIN_REQUIRED"))


# ------------------------------------------------------------------------------------------- load / validate
def load_raw():
    val = {"files": {}, "checks": {}}
    labels, order = {}, []
    for sp in ("dev", "val"):
        raw = (REPO / "datasets/rift_v2" / f"{sp}.json").read_bytes()
        h = hashlib.sha256(raw).hexdigest()
        val["files"][f"datasets/rift_v2/{sp}.json"] = {"sha256": h, "pin": PINS[sp], "match": h == PINS[sp], "bytes": len(raw)}
        assert h == PINS[sp], f"{sp} sha mismatch"
        for s in json.loads(raw)["scenarios"]:
            s["_split"] = sp
            labels[s["scenario_id"]] = s
            order.append(s["scenario_id"])
    man = json.loads((REPO / "datasets/rift_v2/manifest.json").read_text())
    val["checks"]["manifest_sha_matches_pins"] = all(man["datasets"][k]["sha256"] == PINS[k] for k in PINS)
    val["checks"]["n_scenarios"] = len(order)
    val["checks"]["unique_scenario_ids"] = len(set(order)) == len(order)
    val["checks"]["n_by_split"] = dict(Counter(labels[i]["_split"] for i in order))
    val["checks"]["expected_outcome_counts"] = dict(Counter(labels[i]["ground_truth"]["expected_outcome"] for i in order))
    val["checks"]["n_templates"] = len({labels[i]["template_id"] for i in order})
    val["checks"]["distinct_content_hash"] = len({labels[i]["content_hash"] for i in order})
    val["checks"]["abstain_reason_counts"] = dict(Counter(labels[i]["ground_truth"].get("abstain_reason") for i in order))
    saved = {}
    for sp in ("dev", "val"):
        v3 = {r["scenario_id"]: r for r in json.loads((REPO / "artifacts/sprint4_4_0" / f"v3_{sp}.json").read_text())}
        old = {r["scenario_id"]: r for r in json.loads(
            (REPO / "artifacts/sprint4_3_0/results" / sp / "per_scenario.json").read_text())}
        for sid in (i for i in order if labels[i]["_split"] == sp):
            d = {m: old[sid]["methods"][m]["record"] for m in BASELINES + ["RIFT-FULL-V2"]}
            d["V3-FULL"] = v3[sid]["methods"]["V3-FULL"]["record"]
            saved[sid] = d
    val["checks"]["saved_records_cover_all_ids_all_methods"] = all(
        all(m in saved[i] for m in ALL_METHODS) for i in order)
    val["checks"]["heldout_status"] = json.loads((REPO / "datasets/rift_v2/heldout_status.json").read_text())["heldout_status"]
    val["checks"]["heldout_file_opened_by_this_script"] = False
    return labels, order, saved, val


def fresh_run(labels, order):
    from src.rift.attribution_v3.rift_v3 import V3_CONFIGS, run_v3
    from src.rift.evaluation import benchmark_v2 as bm
    from src.rift.evaluation.dataset_registry_v2 import load_v2
    from src.rift.evaluation.rift_v2 import SharedCache
    from src.rift.scenarios import simulator as sim
    scs = {}
    for sp in ("dev", "val"):
        for sc in load_v2(sp, purpose="selection").scenarios:
            scs[sc["scenario_id"]] = sc
    fresh, v3raw, nobs = {}, {}, {}
    t0 = time.time()
    for k, sid in enumerate(order):
        sc = scs[sid]
        rec = bm.run_methods(sc, methods=BASELINES + ["RIFT-FULL-V2"])
        o = sim.observe(sc)
        iv = lambda x, ys, s, sc=sc: sim.intervene(sc, x, ys, s)  # noqa: E731
        out = run_v3(o, iv, sid, int(sc["seed"]), V3_CONFIGS["V3-FULL"], cache=SharedCache())
        r3 = bm._out_to_rec(out, 0.0, 0.0)
        rec["V3-FULL"] = r3
        v3raw[sid] = {"candidates": out.raw_output.get("candidates", []), "diverging": out.raw_output.get("diverging", []),
                      "intervened": out.raw_output.get("intervened", []), "status": out.raw_output.get("status")}
        nobs[sid] = len(sim.observed_services(sc))
        fresh[sid] = rec
        if (k + 1) % 50 == 0:
            print(f"  fresh run {k + 1}/{len(order)}  ({time.time() - t0:.0f}s)", flush=True)
    return fresh, v3raw, nobs


# ------------------------------------------------------------------------------------------- bootstrap machinery
class Clusters:
    """Resample whole clusters with replacement; statistic = ratio-of-sums mean (same estimator as Sprint 4.5.1)."""

    def __init__(self, ids, B, seed):
        keys = sorted(set(ids))
        self.K = len(keys)
        pos = {k: i for i, k in enumerate(keys)}
        self.ix = np.array([pos[i] for i in ids])
        self.cnt = np.bincount(self.ix, minlength=self.K).astype(float)
        self.draw = np.random.default_rng(seed).integers(0, self.K, size=(B, self.K))
        self.M = self.cnt[self.draw].sum(1)

    def sums(self, d):
        return np.bincount(self.ix, weights=d, minlength=self.K)

    def boot(self, d):
        return self.sums(d)[self.draw].sum(1) / self.M

    def ci(self, d):
        th = self.boot(d)
        lo, hi = np.percentile(th, [2.5, 97.5])
        return {"mean": float(d.mean()), "lo": float(lo), "hi": float(hi)}


def iid_ci(d, B, seed):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(B, len(d)))
    th = d[idx].mean(1)
    lo, hi = np.percentile(th, [2.5, 97.5])
    return {"mean": float(d.mean()), "lo": float(lo), "hi": float(hi), "p_boot_mean_gt0": float((th > 0).mean())}


def vec(S, sids, m, key):
    return np.array([float(S[s][m][key]) for s in sids])


def util(S, sids, m, lam, kap, op=False):
    return vec(S, sids, m, "correct") - lam * vec(S, sids, m, "unsafe_op" if op else "unsafe") - kap * vec(S, sids, m, "n_do")


# ------------------------------------------------------------------------------------------------------- main
def main():
    rerun = "--no-rerun" not in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    labels, order, saved, validation = load_raw()
    R = {"validation": validation}
    print("data validation:", json.dumps(validation["checks"], default=str))

    # ---------------- records source(s)
    sources = {"saved": saved}
    if rerun:
        print("fresh re-execution of 10 methods x 252 scenarios ...", flush=True)
        fresh, v3raw, nobs = fresh_run(labels, order)
        (OUT / "fresh_records.json").write_text(json.dumps({"records": fresh, "v3_raw": v3raw, "n_observed": nobs}, default=float))
        sources["fresh"] = fresh
        cmp = {}
        for m in ALL_METHODS:
            mm = Counter()
            for sid in order:
                a, b = saved[sid][m], fresh[sid][m]
                mm["abstained"] += bool(a["abstained"]) != bool(b["abstained"])
                mm["top1"] += (a["top"][0][0] if a["top"] and not a["abstained"] else None) != \
                              (b["top"][0][0] if b["top"] and not b["abstained"] else None)
                mm["n_do"] += int(a["n_do"]) != int(b["n_do"])
                mm["reason"] += a.get("reason") != b.get("reason")
            cmp[m] = dict(mm)
        R["fresh_vs_saved_mismatch_counts"] = cmp
        R["fresh_vs_saved_total_mismatches"] = int(sum(sum(v.values()) for v in cmp.values()))

    sids = order
    S = {}   # source -> sid -> method -> score
    for name, src in sources.items():
        S[name] = {sid: {m: score(labels[sid], src[sid][m]) for m in ALL_METHODS} for sid in sids}

    # saved-score cross-check (saved score dict in artifacts vs. my scoring)
    mism = 0
    for sp in ("dev", "val"):
        old = {r["scenario_id"]: r for r in json.loads((REPO / "artifacts/sprint4_3_0/results" / sp / "per_scenario.json").read_text())}
        v3 = {r["scenario_id"]: r for r in json.loads((REPO / "artifacts/sprint4_4_0" / f"v3_{sp}.json").read_text())}
        for sid in (i for i in sids if labels[i]["_split"] == sp):
            for m in BASELINES + ["RIFT-FULL-V2"]:
                sv = old[sid]["methods"][m]["score"]
                mism += any(bool(sv[k]) != bool(S["saved"][sid][m][k]) for k in ("answered", "correct", "unsafe"))
            sv = v3[sid]["methods"]["V3-FULL"]["score"]
            mism += any(bool(sv[k]) != bool(S["saved"][sid]["V3-FULL"][k]) for k in ("answered", "correct", "unsafe"))
    R["independent_scoring_vs_saved_score_field_mismatches"] = {"mismatches": int(mism), "pairs": len(sids) * len(ALL_METHODS)}

    prim = "fresh" if rerun else "saved"
    R["primary_source"] = prim
    Sp = S[prim]

    # ======================================================================= A
    A = {}
    for name in S:
        d = {}
        for m in ("RIFT-FULL-V2", "V3-FULL"):
            c, u, uo = vec(S[name], sids, m, "correct"), vec(S[name], sids, m, "unsafe"), vec(S[name], sids, m, "unsafe_op")
            d[m] = {"unsafe": int(u.sum()), "unsafe_operational": int(uo.sum()), "correct": int(c.sum()),
                    "answered": int(vec(S[name], sids, m, "answered").sum()),
                    "wrong_root_on_ATTRIBUTE": int(vec(S[name], sids, m, "wrong_root").sum()),
                    "answered_on_ABSTAIN_REQUIRED": int(vec(S[name], sids, m, "answered_on_AR").sum()),
                    "lucky_right_service_on_AR": int(vec(S[name], sids, m, "lucky").sum())}
        u2, u3 = d["RIFT-FULL-V2"]["unsafe"], d["V3-FULL"]["unsafe"]
        o2, o3 = d["RIFT-FULL-V2"]["unsafe_operational"], d["V3-FULL"]["unsafe_operational"]
        d["strict_reduction_pct"] = 100.0 * (u2 - u3) / u2
        d["operational_reduction_pct"] = 100.0 * (o2 - o3) / o2
        a2, a3 = vec(S[name], sids, "RIFT-FULL-V2", "unsafe"), vec(S[name], sids, "V3-FULL", "unsafe")
        d["paired_unsafe_transitions"] = {"V2_unsafe_V3_safe": int(((a2 == 1) & (a3 == 0)).sum()),
                                          "V2_safe_V3_unsafe": int(((a2 == 0) & (a3 == 1)).sum()),
                                          "both_unsafe": int(((a2 == 1) & (a3 == 1)).sum()),
                                          "both_safe": int(((a2 == 0) & (a3 == 0)).sum())}
        d["by_split"] = {sp: {m: int(sum(S[name][s][m]["unsafe"] for s in sids if labels[s]["_split"] == sp))
                              for m in ("RIFT-FULL-V2", "V3-FULL")} for sp in ("dev", "val")}
        A[name] = d
    R["A_unsafe_reduction"] = A
    R["A_classification_rule"] = {
        "unsafe": "answered AND (expected_outcome == ABSTAIN_REQUIRED OR top1 not in ground_truth.roots)",
        "unsafe_operational": "answered AND top1 not in ground_truth.roots (right service on ABSTAIN_REQUIRED is not harmful)",
        "correct": "answered AND expected_outcome == ATTRIBUTE AND top1 in roots",
        "abstained": "record.abstained == True (never unsafe)"}

    from src.rift.scenarios.independence import topology_hash
    from src.rift.scenarios.splitter import build_groups
    grp = build_groups({s: labels[s] for s in sids}, [lambda s: ("t", s["template_id"]), lambda s: ("topo", topology_hash(s))])
    tmpl = [labels[s]["template_id"] for s in sids]
    grps = [grp[s] for s in sids]
    cl_t = Clusters(tmpl, B_MAIN, SEED_MAIN)
    cl_g = Clusters(grps, B_MAIN, SEED_MAIN + 1)
    cl_t_alt = Clusters(tmpl, B_MAIN, 20260711)    # different seed: Monte-Carlo stability
    cg_t = Clusters(tmpl, B_GRID, SEED_MAIN + 2)
    cg_g = Clusters(grps, B_GRID, SEED_MAIN + 3)
    R["B_utility"], R["C_sensitivity"] = {}, {}
    for srcname in S:
        Sx = S[srcname]
        B = {"K_template": cl_t.K, "K_group": cl_g.K}
        for tag, op in (("strict", False), ("operational", True)):
            d = util(Sx, sids, "V3-FULL", 2.0, 0.05, op) - util(Sx, sids, "RIFT-FULL-V2", 2.0, 0.05, op)
            B[tag] = {"V3_minus_V2_lambda2_kappa0.05": {
                "template_cluster_seed4510": cl_t.ci(d), "template_cluster_seed20260711": cl_t_alt.ci(d),
                "union_find_group_cluster": cl_g.ci(d), "scenario_level_paired_iid_seed7000": iid_ci(d, B_MAIN, 7000),
                "sd_diff": float(d.std(ddof=1))},
                "V3_mean_U": float(util(Sx, sids, "V3-FULL", 2.0, 0.05, op).mean()),
                "V2_mean_U": float(util(Sx, sids, "RIFT-FULL-V2", 2.0, 0.05, op).mean())}
        R["B_utility"][srcname] = B

        grid = []
        for tag, op in (("strict", False), ("operational", True)):
            for lam in LAMBDAS:
                for k in KAPPAS:
                    d = util(Sx, sids, "V3-FULL", lam, k, op) - util(Sx, sids, "RIFT-FULL-V2", lam, k, op)
                    ct, cgp, ci = cg_t.ci(d), cg_g.ci(d), iid_ci(d, B_GRID, 7001)
                    grid.append({"def": tag, "lambda": lam, "kappa": k, "mean": ct["mean"], "template": [ct["lo"], ct["hi"]],
                                 "group": [cgp["lo"], cgp["hi"]], "iid": [ci["lo"], ci["hi"]],
                                 "sig_pos_template": ct["lo"] > 0, "sig_pos_group": cgp["lo"] > 0, "sig_pos_iid": ci["lo"] > 0,
                                 "sig_neg_template": ct["hi"] < 0, "mean_positive": ct["mean"] > 0})
        C = {"n_cells_per_definition": len(LAMBDAS) * len(KAPPAS), "grid": grid}
        for tag in ("strict", "operational"):
            cells = [g for g in grid if g["def"] == tag]
            C[tag] = {"cells": len(cells),
                      "sig_pos_template_CI": sum(g["sig_pos_template"] for g in cells),
                      "sig_pos_group_CI": sum(g["sig_pos_group"] for g in cells),
                      "sig_pos_iid_CI": sum(g["sig_pos_iid"] for g in cells),
                      "mean_positive": sum(g["mean_positive"] for g in cells),
                      "sig_neg_template_CI": sum(g["sig_neg_template"] for g in cells),
                      "non_significant_cells_template(lambda,kappa)": [(g["lambda"], g["kappa"]) for g in cells if not g["sig_pos_template"]],
                      "significantly_negative_cells_template(lambda,kappa)": [(g["lambda"], g["kappa"]) for g in cells if g["sig_neg_template"]]}
        be = {}
        for m in ("V3-FULL", "RIFT-FULL-V2"):
            c, s, n = vec(Sx, sids, m, "correct"), vec(Sx, sids, m, "unsafe"), vec(Sx, sids, m, "n_do")
            be[m] = {}
            for k in KAPPAS:
                a, b = c - k * n, s
                A_, B_ = cl_t.sums(a)[cl_t.draw].sum(1), cl_t.sums(b)[cl_t.draw].sum(1)
                ok = B_ > 0
                be[m][f"kappa={k}"] = {"lambda_star": float(a.sum() / b.sum()),
                                       "pct95_template": [float(x) for x in np.percentile(A_[ok] / B_[ok], [2.5, 97.5])]}
        c3, s3, n3 = (vec(Sx, sids, "V3-FULL", x) for x in ("correct", "unsafe", "n_do"))
        be["V3-FULL_exact_fractions"] = {"kappa=0": f"{int(c3.sum())}/{int(s3.sum())}",
                                         "kappa=0.025": f"({int(c3.sum())} - 0.025*{int(n3.sum())})/{int(s3.sum())}"}
        C["break_even"] = be
        R["C_sensitivity"][srcname] = C

    # ======================================================================= D
    D = {}
    n_do = {m: vec(Sp, sids, m, "n_do") for m in ALL_METHODS}
    D["mean_n_do"] = {m: float(n_do[m].mean()) for m in ALL_METHODS}
    D["mean_n_do_by_split"] = {sp: {m: float(np.mean([Sp[s][m]["n_do"] for s in sids if labels[s]["_split"] == sp]))
                                    for m in ("V3-FULL", "RIFT-FULL-V2", "B6-RIFT-RANDOM")} for sp in ("dev", "val")}
    D["V3_n_do_distribution"] = {int(k): int(v) for k, v in sorted(Counter(n_do["V3-FULL"].astype(int)).items())}
    D["V3_max_n_do"] = int(n_do["V3-FULL"].max())
    D["V3_scenarios_with_zero_do"] = int((n_do["V3-FULL"] == 0).sum())
    D["V3_mean_n_do_among_scenarios_with_do>0"] = float(n_do["V3-FULL"][n_do["V3-FULL"] > 0].mean())
    if rerun:
        nobs_v = np.array([nobs[s] for s in sids], dtype=float)
        roots_v = np.array([max(1, len(labels[s]["ground_truth"]["roots"])) for s in sids], dtype=float)
        att = np.array([labels[s]["ground_truth"]["expected_outcome"] == "ATTRIBUTE" for s in sids])
        D["mean_observed_services"] = float(nobs_v.mean())
        D["comparators"] = {
            "exhaustive_do_on_every_observed_service": float(nobs_v.mean()),
            "random_order_exploration_with_ORACLE_stop_at_first_true_root(ATTRIBUTE only)": float(((nobs_v + 1) / (roots_v + 1))[att].mean()),
            "random_order_exploration_to_MAX_DO_budget(20)": float(np.minimum(nobs_v, MAX_DO).mean()),
            "B6-RIFT-RANDOM(in-repo random MSIS baseline)": D["mean_n_do"]["B6-RIFT-RANDOM"],
            "B7-RIFT-ONE-SHOT": D["mean_n_do"]["B7-RIFT-ONE-SHOT"],
            "RIFT-FULL-V2": D["mean_n_do"]["RIFT-FULL-V2"]}
        v3m = D["mean_n_do"]["V3-FULL"]
        D["V3_reduction_vs_comparator_pct"] = {k: 100.0 * (1 - v3m / v) for k, v in D["comparators"].items()}
        D["v3_number_of_diverging_candidates_mean"] = float(np.mean([len(v3raw[s]["diverging"]) for s in sids]))
        reached = [s for s in sids if len(v3raw[s]["diverging"]) >= 2 and v3raw[s]["status"] != "NON_IDENTIFIABLE"]
        D["v3_scenarios_reaching_intervention_stage"] = len(reached)
        D["v3_policy_intervenes_on_every_candidate(n_do==min(len(candidates),20) for all reaching scenarios)"] = bool(
            all(len(v3raw[s]["intervened"]) == min(len(v3raw[s]["candidates"]), MAX_DO) for s in reached))
        D["v3_uses_msis_or_entropy_stopping"] = ("no: rift_v3.run_v3 loops `for x in names` (temporal order) with only a MAX_DO cap; "
                                                 "no src.rift.optimizer / greedy_msis call")
    abl = {}
    for sp in ("dev", "val"):
        for r in json.loads((REPO / "artifacts/sprint4_3_0/results" / sp / "per_scenario.json").read_text()):
            for m in ("ABL:A10-RANDOM-INTERVENTION", "ABL:A7-NO-MSIS", "ABL:A1-FULL", "RIFT-FULL-V2"):
                if m in r["methods"]:
                    abl.setdefault(m, []).append(int(r["methods"][m]["record"]["n_do"]))
    D["saved_V2_family_mean_n_do_(Sprint4.3.0_ablation_records)"] = {m: float(np.mean(v)) for m, v in abl.items()}
    if "V3-FULL" in D["mean_n_do"] and "ABL:A10-RANDOM-INTERVENTION" in abl:
        D["V3_vs_V2_random_order_ablation_A10_pct_change"] = 100.0 * (1 - D["mean_n_do"]["V3-FULL"] / float(np.mean(abl["ABL:A10-RANDOM-INTERVENTION"])))
    src = (REPO / "scripts/run_reproducible_evaluation.py").read_text()
    D["H4_hardcoded_constants_present"] = ("np.full(len(rift_p1), 30.0)" in src and "np.full(len(rift_p1), 60.0)" in src)
    R["D_intervention_efficiency"] = D

    # ======================================================================= E
    E = {}
    for name in S:
        E[name] = {}
        for m in BASELINES + ["RIFT-FULL-V2", "V3-FULL"]:
            c, u, uo = (vec(S[name], sids, m, x) for x in ("correct", "unsafe", "unsafe_op"))
            ans = vec(S[name], sids, m, "answered")
            E[name][m] = {"correct_P1_of_99": int(c.sum()), "answered": int(ans.sum()), "unsafe_strict": int(u.sum()),
                          "unsafe_operational": int(uo.sum()),
                          "wrong_root_on_ATTRIBUTE": int(vec(S[name], sids, m, "wrong_root").sum()),
                          "answered_on_ABSTAIN_REQUIRED": int(vec(S[name], sids, m, "answered_on_AR").sum()),
                          "mean_n_do": float(vec(S[name], sids, m, "n_do").mean()),
                          "mean_ed_s": float(vec(S[name], sids, m, "ed_s").mean()),
                          "mean_U_lambda2_kappa0.05_strict": float(util(S[name], sids, m, 2.0, 0.05).mean()),
                          "break_even_lambda_kappa0": (float(c.sum() / u.sum()) if u.sum() else None)}
    R["E_baselines"] = E
    (OUT / "results.json").write_text(json.dumps(R, indent=1, default=float))
    print("wrote", OUT / "results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
