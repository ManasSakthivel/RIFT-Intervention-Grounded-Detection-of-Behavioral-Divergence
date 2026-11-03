#!/usr/bin/env python3
"""Sprint 4.5.1 / Agent 2: independent verification of the utility specification (development evidence only).

NOT the confirmatory experiment. Reads ONLY (sha256-pinned where labels):
  datasets/rift_v2/{dev,val}.json
  artifacts/sprint4_4_0/v3_{dev,val}.json
  artifacts/sprint4_3_0/results/{dev,val}/per_scenario.json
It never opens the Sprint 4.3.0 held-out data, never runs V3 / V2 / any method, never generates scenarios.

Scoring is RE-IMPLEMENTED here from (label, record) following benchmark_v2.score_one (it does not import it) and is
cross-checked against the saved score of every (scenario, method) pair.

    U_i = C_i - lambda * S_i - gamma * (n_do_i / MAX_DO)        (gamma = 20 * kappa)

Outputs (artifacts/sprint4_5_1/utility/):
  utility_verification.json   verified-vs-claimed table, bounds, break-evens, primary CIs, lucky counts, operational
  sensitivity_grid.json       lambda x kappa grid for V3-AA and V3-V2, strict and operational, 3 CI types
  sensitivity_grid.md         the same as markdown tables
Fixed seed: SEED = 4510. Bootstrap resamples whole clusters (template, or union-find group template-or-topology).
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
OUT = REPO / "artifacts" / "sprint4_5_1" / "utility"
SEED = 4510
B_MAIN = 10000
B_GRID = 4000
PINS = {"dev": "a833ad0ca1db0583a30bc4450f9f59b2984a5823702935ef59c6b037e026ef5f",
        "val": "e82252b47f29dc1353586034b6fd8c3491df3221851f9c84c48bf717a944a1fb"}
MAX_DO = 20
LAMBDAS = [0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
KAPPAS = [0.0, 0.025, 0.05, 0.10]
OLD_METHODS = ["RIFT-FULL-V2", "RIFT-FULL-LEGACY", "B0-EARLIEST", "B0-HIGHEST", "B1-LATENCY-CORR", "B3-SIEVE-LIKE",
               "B5-RIFT-OBS", "B6-RIFT-RANDOM", "B7-RIFT-ONE-SHOT", "ORACLE:UPPER-BOUND",
               "ORACLE:RIFT-FULL-V2-ORACLE-GRAPH"]
V3_METHODS = ["V3-FULL", "V3-DEFINITIVE-ONLY"]
METHODS = V3_METHODS + OLD_METHODS


# --------------------------------------------------------------------------------------------- scoring (re-implemented)
def my_score(sc, rec):
    """Re-implementation of benchmark_v2.score_one (strict) plus the operational variant."""
    gt = sc["ground_truth"]
    exp = gt["expected_outcome"]
    roots = set(gt["roots"])
    ans = not rec["abstained"]
    top1 = rec["top"][0][0] if (ans and rec["top"]) else None
    correct = bool(ans and top1 in roots) if exp == "ATTRIBUTE" else False
    unsafe = bool(ans and (exp == "ABSTAIN_REQUIRED" or top1 not in roots))
    unsafe_op = bool(ans and top1 not in roots)          # operational: only a wrong/absent named service is harmful
    lucky = bool(ans and exp == "ABSTAIN_REQUIRED" and top1 in roots)
    return {"answered": ans, "correct": correct, "unsafe": unsafe, "unsafe_op": unsafe_op, "lucky": lucky}


def load_rows():
    sys.path.insert(0, str(REPO))
    rows = []
    scs_all = {}
    for split in ("dev", "val"):
        raw = (REPO / "datasets" / "rift_v2" / f"{split}.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == PINS[split], f"{split} pin mismatch"
        lab = {s["scenario_id"]: s for s in json.loads(raw)["scenarios"]}
        scs_all.update(lab)
        v3 = {r["scenario_id"]: r for r in json.loads((REPO / "artifacts/sprint4_4_0" / f"v3_{split}.json").read_text())}
        old = {r["scenario_id"]: r for r in json.loads(
            (REPO / "artifacts/sprint4_3_0/results" / split / "per_scenario.json").read_text())}
        for sid, sc in lab.items():
            row = {"sid": sid, "split": split, "template": sc["template_id"], "structure": sc["dimensions"]["structure"],
                   "expected": sc["ground_truth"]["expected_outcome"], "reason": sc["ground_truth"].get("abstain_reason"),
                   "m": {}}
            srcs = {n: v3[sid]["methods"][n] for n in V3_METHODS}
            srcs.update({n: old[sid]["methods"][n] for n in OLD_METHODS})
            for n, src in srcs.items():
                s = my_score(sc, src["record"])
                s["n_do"] = int(src["record"]["n_do"])
                s["saved"] = src["score"]
                row["m"][n] = s
            rows.append(row)
    # union-find groups (template OR topology), label-stripped use is unnecessary: dev/val are readable
    from src.rift.scenarios.independence import topology_hash
    from src.rift.scenarios.splitter import build_groups
    grp = build_groups(scs_all, [lambda s: ("t", s["template_id"]), lambda s: ("topo", topology_hash(s))])
    for r in rows:
        r["group"] = grp[r["sid"]]
    return rows


def vec(rows, m, key):
    return np.array([float(r["m"][m][key]) for r in rows])


def util(rows, m, lam, kap, op=False):
    c = vec(rows, m, "correct")
    s = vec(rows, m, "unsafe_op" if op else "unsafe")
    n = vec(rows, m, "n_do")
    return c - lam * s - kap * n            # kap per do(); gamma = kap * MAX_DO


# --------------------------------------------------------------------------------------------- cluster machinery
class Clusters:
    def __init__(self, ids, B, seed):
        keys = sorted(set(ids))
        self.K = len(keys)
        pos = {k: i for i, k in enumerate(keys)}
        self.ix = np.array([pos[i] for i in ids])
        self.cnt = np.bincount(self.ix, minlength=self.K).astype(float)
        rng = np.random.default_rng(seed)
        self.draw = rng.integers(0, self.K, size=(B, self.K))
        self.Mdraw = self.cnt[self.draw].sum(1)

    def sums(self, d):
        return np.bincount(self.ix, weights=d, minlength=self.K)

    def ci(self, d):
        """mean, percentile CI, studentised (bootstrap-t) CI, se_cluster (CR1 ratio estimator), P(mean>0)."""
        S = self.sums(d)
        N = self.cnt.sum()
        theta = S.sum() / N
        Sd = S[self.draw]
        th = Sd.sum(1) / self.Mdraw
        pct = np.percentile(th, [2.5, 97.5])
        res = S - theta * self.cnt
        se = np.sqrt(self.K / (self.K - 1) * (res ** 2).sum()) / N
        rb = Sd - th[:, None] * self.cnt[self.draw]
        seb = np.sqrt(self.K / (self.K - 1) * (rb ** 2).sum(1)) / self.Mdraw
        ok = seb > 0
        t = (th[ok] - theta) / seb[ok]
        q_lo, q_hi = np.percentile(t, [2.5, 97.5])
        stud = [float(theta - q_hi * se), float(theta - q_lo * se)]
        return {"mean": float(theta), "pct95": [float(pct[0]), float(pct[1])], "stud95": stud, "se_cluster": float(se),
                "p_boot_mean_gt0": float((th > 0).mean())}


def breakeven(rows, m, kap, cl, op=False):
    c = vec(rows, m, "correct")
    s = vec(rows, m, "unsafe_op" if op else "unsafe")
    n = vec(rows, m, "n_do")
    a, b = c - kap * n, s
    if b.sum() == 0:
        return None
    pt = float(a.sum() / b.sum())
    A, Bs = cl.sums(a)[cl.draw].sum(1), cl.sums(b)[cl.draw].sum(1)
    ok = Bs > 0
    lam = A[ok] / Bs[ok]
    return {"lambda_star": pt, "pct95": [float(x) for x in np.percentile(lam, [2.5, 97.5])]}


def lambda_sig_limit(rows, m, kap, cl, op=False):
    """Largest lambda (0.00..3.00 step .01) at which the pct95 lower bound of mean(U_m - 0) is > 0 (None if none)."""
    c = vec(rows, m, "correct")
    s = vec(rows, m, "unsafe_op" if op else "unsafe")
    n = vec(rows, m, "n_do")
    a, b = c - kap * n, s
    A, Bs = cl.sums(a)[cl.draw].sum(1) / cl.Mdraw, cl.sums(b)[cl.draw].sum(1) / cl.Mdraw
    lams = np.round(np.arange(0.0, 3.0001, 0.01), 2)
    lo = np.percentile(A[:, None] - lams[None, :] * Bs[:, None], 2.5, axis=0)
    good = lams[lo > 0]
    return float(good.max()) if len(good) else None


def skew(x):
    m = x.mean()
    return float(((x - m) ** 3).mean() / (x.std() ** 3))


# --------------------------------------------------------------------------------------------------------------- main
def main():
    rows = load_rows()
    N = len(rows)
    att = np.array([r["expected"] == "ATTRIBUTE" for r in rows])
    ver = {"purpose": "Sprint 4.5.1 independent verification of the utility specification; dev/val only; NOT confirmatory",
           "script": "scripts/sprint451_utility_sensitivity.py", "seed": SEED, "B_main": B_MAIN, "B_grid": B_GRID,
           "n_scenarios": N, "inputs_sha256": {f"datasets/rift_v2/{s}.json": PINS[s] for s in PINS}}

    # ---- scoring cross-check against saved scores
    mism = []
    for r in rows:
        for m, s in r["m"].items():
            sv = s["saved"]
            for k in ("answered", "correct", "unsafe"):
                if bool(sv[k]) != bool(s[k]):
                    mism.append((r["sid"], m, k))
    ver["score_reimplementation_mismatches_vs_saved"] = len(mism)
    ver["score_reimplementation_pairs_checked"] = N * len(METHODS)

    cl_t = Clusters([r["template"] for r in rows], B_MAIN, SEED)
    cl_g = Clusters([r["group"] for r in rows], B_MAIN, SEED + 1)
    ver["clusters"] = {"template_K": cl_t.K, "group_K": cl_g.K,
                       "group_sizes": sorted(Counter(r["group"] for r in rows).values(), reverse=True)}

    # ---- bounds / exclusivity / n_do
    exact = {}
    allc = {m: vec(rows, m, "correct") for m in METHODS}
    alls = {m: vec(rows, m, "unsafe") for m in METHODS}
    alln = {m: vec(rows, m, "n_do") for m in METHODS}
    allans = {m: vec(rows, m, "answered") for m in METHODS}
    exact["max_n_do_by_method"] = {m: int(alln[m].max()) for m in METHODS}
    exact["min_n_do_by_method"] = {m: int(alln[m].min()) for m in METHODS}
    exact["n_do_above_MAX_DO_any_method"] = int(sum((alln[m] > MAX_DO).sum() for m in METHODS))
    exact["correct_and_unsafe_both_1_any_method"] = int(sum(((allc[m] == 1) & (alls[m] == 1)).sum() for m in METHODS))
    exact["unsafe_without_answer_any_method"] = int(sum(((alls[m] == 1) & (allans[m] == 0)).sum() for m in METHODS))
    exact["correct_without_answer_any_method"] = int(sum(((allc[m] == 1) & (allans[m] == 0)).sum() for m in METHODS))
    exact["min_n_do_when_correct_V3-FULL"] = int(alln["V3-FULL"][allc["V3-FULL"] == 1].min())
    exact["min_n_do_when_correct_RIFT-FULL-V2"] = int(alln["RIFT-FULL-V2"][allc["RIFT-FULL-V2"] == 1].min())
    # partition of the scenario-level outcome space: exactly one of {correct, unsafe, safe-abstain-or-safe-nonunique}
    cats = {m: Counter() for m in ("V3-FULL", "RIFT-FULL-V2")}
    for m in cats:
        for r in rows:
            s = r["m"][m]
            cats[m]["correct" if s["correct"] else "unsafe" if s["unsafe"] else
                    "abstain" if not s["answered"] else "answered_other"] += 1
    exact["outcome_partition"] = {m: dict(c) for m, c in cats.items()}
    exact["answered_other_means"] = ("answered, not correct, not unsafe: must be 0 (an answer on ATTRIBUTE is either "
                                     "top1 in roots => correct, or not => unsafe; an answer on ABSTAIN_REQUIRED is unsafe)")
    ver["exact_bounds_and_structure"] = exact
    lam_, gam_ = 2.0, 1.0
    ver["per_scenario_bounds"] = {
        "formula": "U = C - lam*S - gamma*(n_do/20), C,S in {0,1}, C*S = 0, n_do in {0..20} (code caps at MAX_DO)",
        "case_correct": f"U in [1-gamma, 1] = [{1 - gam_}, 1]  (S=0)",
        "case_unsafe": f"U in [-lam-gamma, -lam] = [{-lam_ - gam_}, {-lam_}]  (C=0)",
        "case_other_abstain": f"U in [-gamma, 0] = [{-gam_}, 0]  (C=S=0; abstaining after interventions still pays cost)",
        "global": f"U in [-(lam+gamma), 1] = [{-(lam_ + gam_)}, 1]; 1 attained only for a correct answer with 0 do(); "
                  f"-(lam+gamma) only for an unsafe answer after 20 do()",
        "mean_ceiling": "pi (prevalence of ATTRIBUTE): attained only by correct, zero-cost answers on every ATTRIBUTE scenario "
                        "and abstention with zero cost on every ABSTAIN_REQUIRED scenario",
        "mean_floor": "-(lam+gamma) (answer unsafe after 20 do() on every scenario) - not attainable by V3",
        "claim_U_in_[0,1]": "FALSE: U is NOT bounded in [0,1]; the correct bounds are [-(lam+gamma), 1]"}
    obs = {}
    for m in ("V3-FULL", "RIFT-FULL-V2"):
        u = util(rows, m, 2.0, 0.05)
        obs[m] = {"min": float(u.min()), "max": float(u.max()), "distinct_values": sorted(set(np.round(u, 4).tolist()))[:6]}
    ver["observed_U_range_lam2_kap0.05"] = obs
    pi = float(att.mean())
    ver["prevalence"] = {"pooled": pi, "dev": float(att[[r["split"] == "dev" for r in rows]].mean()),
                         "val": float(att[[r["split"] == "val" for r in rows]].mean()), "n_attribute": int(att.sum())}
    ver["scale"] = {"ceiling_pi_pooled": pi, "delta_0.10_over_ceiling_pooled": 0.10 / pi,
                    "delta_0.10_over_ceiling_at_pi_0.40": 0.10 / 0.40,
                    "oracle_correct": int(allc["ORACLE:UPPER-BOUND"].sum()), "oracle_unsafe": int(alls["ORACLE:UPPER-BOUND"].sum()),
                    "oracle_mean_n_do": float(alln["ORACLE:UPPER-BOUND"].mean()),
                    "note": "ORACLE rows read ground truth: privileged upper bound, used only to scale delta"}

    # ---- decomposition table
    dec = {}
    for m in METHODS:
        c, s, n, a = allc[m], alls[m], alln[m], allans[m]
        sop = vec(rows, m, "unsafe_op")
        lucky = vec(rows, m, "lucky")
        ar = np.array([r["expected"] == "ABSTAIN_REQUIRED" for r in rows])
        dec[m] = {"correct": int(c.sum()), "answered": int(a.sum()), "unsafe": int(s.sum()),
                  "wrong_root_on_ATTRIBUTE": int((s * att).sum()), "answered_on_ABSTAIN_REQUIRED": int((a * ar).sum()),
                  "lucky_right_service_on_ABSTAIN_REQUIRED": int(lucky.sum()), "unsafe_operational": int(sop.sum()),
                  "mean_n_do": float(n.mean()), "max_n_do": int(n.max()),
                  "break_even_lambda_kappa0_point": float(c.sum() / s.sum()) if s.sum() else None}
    ver["decomposition_pooled"] = dec
    lucky_reason = {m: dict(Counter(r["reason"] for r in rows if r["m"][m]["lucky"])) for m in ("V3-FULL", "RIFT-FULL-V2")}
    ver["lucky_by_abstain_reason"] = lucky_reason

    # ---- primary: V3 vs AA, V2, at lambda=2, gamma=1 (kappa=.05), strict and operational
    prim = {}
    for tag, op in (("strict", False), ("operational", True)):
        u3, u2 = util(rows, "V3-FULL", 2.0, 0.05, op), util(rows, "RIFT-FULL-V2", 2.0, 0.05, op)
        prim[tag] = {"V3_minus_AA": {"template": cl_t.ci(u3), "group": cl_g.ci(u3)},
                     "V2_minus_AA": {"template": cl_t.ci(u2), "group": cl_g.ci(u2)},
                     "V3_minus_V2": {"template": cl_t.ci(u3 - u2), "group": cl_g.ci(u3 - u2)},
                     "sd_V3": float(u3.std(ddof=1)), "sd_V3_minus_V2": float((u3 - u2).std(ddof=1)),
                     "skewness_V3": skew(u3), "mean_cost_term_V3_gamma1": float((vec(rows, "V3-FULL", "n_do") / MAX_DO).mean())}
    ver["primary_lambda2_gamma1"] = prim
    u3 = util(rows, "V3-FULL", 2.0, 0.05)
    dev = np.array([r["split"] == "dev" for r in rows])
    ver["primary_by_split"] = {"dev_mean": float(u3[dev].mean()), "val_mean": float(u3[~dev].mean()),
                               "dev_sd": float(u3[dev].std(ddof=1)), "val_sd": float(u3[~dev].std(ddof=1))}
    ver["gamma_kappa_equivalence"] = {"kappa_per_do": 0.05, "gamma": 1.0, "max_do": MAX_DO,
                                      "gamma_from_kappa": 0.05 * MAX_DO,
                                      "check_equal_utility_all_V3_scenarios": bool(np.allclose(
                                          util(rows, "V3-FULL", 2.0, 0.05),
                                          vec(rows, "V3-FULL", "correct") - 2.0 * vec(rows, "V3-FULL", "unsafe")
                                          - 1.0 * vec(rows, "V3-FULL", "n_do") / MAX_DO))}

    # ---- operational utility (point, kappa=.05) lambda 1,2,4
    ver["operational_mean_kappa0.05"] = {m: {str(l): float(util(rows, m, l, 0.05, True).mean()) for l in (1.0, 2.0, 4.0)}
                                          for m in ("V3-FULL", "RIFT-FULL-V2")}

    # ---- break-evens
    be = {}
    for m in ("V3-FULL", "V3-DEFINITIVE-ONLY", "RIFT-FULL-V2", "RIFT-FULL-LEGACY", "B0-EARLIEST"):
        be[m] = {}
        for k in KAPPAS:
            be[m][f"kappa={k}"] = {"strict_template": breakeven(rows, m, k, cl_t), "strict_group": breakeven(rows, m, k, cl_g)}
    ver["break_even_lambda_strict"] = be
    beo = {m: {f"kappa={k}": {"template": breakeven(rows, m, k, cl_t, True), "group": breakeven(rows, m, k, cl_g, True)}
               for k in KAPPAS} for m in ("V3-FULL", "RIFT-FULL-V2")}
    ver["break_even_lambda_operational"] = beo
    ver["lambda_significance_limit_V3_vs_AA"] = {
        f"kappa={k}": {"strict_template": lambda_sig_limit(rows, "V3-FULL", k, cl_t),
                       "strict_group": lambda_sig_limit(rows, "V3-FULL", k, cl_g),
                       "operational_template": lambda_sig_limit(rows, "V3-FULL", k, cl_t, True),
                       "operational_group": lambda_sig_limit(rows, "V3-FULL", k, cl_g, True)} for k in KAPPAS}
    ver["lambda_significance_limit_note"] = ("largest lambda in [0,3] (step .01) at which the 95% percentile lower bound "
                                             "of mean U(V3) exceeds 0; None = never at any lambda>=0")
    ver["precision_floor_lambda_over_1_plus_lambda"] = {str(l): l / (1 + l) for l in LAMBDAS}

    # ---- sensitivity grid
    cg_t = Clusters([r["template"] for r in rows], B_GRID, SEED + 2)
    cg_g = Clusters([r["group"] for r in rows], B_GRID, SEED + 3)
    grid = []
    for tag, op in (("strict", False), ("operational", True)):
        for lam in LAMBDAS:
            for k in KAPPAS:
                u3 = util(rows, "V3-FULL", lam, k, op)
                u2 = util(rows, "RIFT-FULL-V2", lam, k, op)
                for name, d in (("V3_minus_AA", u3), ("V3_minus_V2", u3 - u2)):
                    ct, cgp = cg_t.ci(d), cg_g.ci(d)
                    grid.append({"unsafe_definition": tag, "contrast": name, "lambda": lam, "kappa": k, "gamma": k * MAX_DO,
                                 "mean": ct["mean"], "template_pct95": ct["pct95"], "template_stud95": ct["stud95"],
                                 "group_pct95": cgp["pct95"], "group_stud95": cgp["stud95"],
                                 "sig_pos_template": ct["pct95"][0] > 0, "sig_pos_group": cgp["pct95"][0] > 0,
                                 "sig_neg_template": ct["pct95"][1] < 0, "sig_neg_group": cgp["pct95"][1] < 0})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sensitivity_grid.json").write_text(json.dumps({"seed": SEED, "B": B_GRID, "cells": grid}, indent=1))
    md = ["# Sprint 4.5.1 utility sensitivity grid (development evidence, dev+val pooled, N=%d; NON-CONFIRMATORY)\n" % N,
          "Generated by `scripts/sprint451_utility_sensitivity.py` (seed %d, B=%d). Cell = mean [95%% percentile CI] of "
          "per-scenario difference; cluster bootstrap over whole clusters. kappa = cost per do(); gamma = 20 x kappa. "
          "`+` = CI entirely above 0, `-` = CI entirely below 0.\n" % (SEED, B_GRID)]
    for tag in ("strict", "operational"):
        for name in ("V3_minus_AA", "V3_minus_V2"):
            for cname, key in (("template clusters (K=%d)" % cg_t.K, "template"), ("union-find groups (K=%d)" % cg_g.K, "group")):
                md.append(f"\n## {name}, {tag} unsafe, {cname}\n")
                md.append("| lambda \\ kappa | " + " | ".join(f"{k} (gamma {k * MAX_DO:g})" for k in KAPPAS) + " |")
                md.append("|---|" + "---|" * len(KAPPAS))
                for lam in LAMBDAS:
                    cells = []
                    for k in KAPPAS:
                        g = next(x for x in grid if x["unsafe_definition"] == tag and x["contrast"] == name
                                 and x["lambda"] == lam and x["kappa"] == k)
                        lo, hi = g[f"{key}_pct95"]
                        mark = "+" if lo > 0 else "-" if hi < 0 else ""
                        cells.append(f"{g['mean']:+.3f} [{lo:+.3f}, {hi:+.3f}] {mark}")
                    md.append(f"| {lam} | " + " | ".join(cells) + " |")
    (OUT / "sensitivity_grid.md").write_text("\n".join(md) + "\n")

    # ---- verified-vs-claimed
    def cell(tag, name, lam, k):
        return next(x for x in grid if x["unsafe_definition"] == tag and x["contrast"] == name and x["lambda"] == lam
                    and x["kappa"] == k)
    pv = prim["strict"]
    d3, d2 = dec["V3-FULL"], dec["RIFT-FULL-V2"]
    claims = [
        ("pi pooled (PRE 3.2, AUD 3)", 0.393, pi, 0.0006), ("pi dev", 0.378, ver["prevalence"]["dev"], 0.0006),
        ("pi val", 0.431, ver["prevalence"]["val"], 0.0006),
        ("V3 correct", 45, d3["correct"], 0), ("V3 answered", 93, d3["answered"], 0), ("V3 unsafe", 48, d3["unsafe"], 0),
        ("V3 wrong-root on ATTRIBUTE", 10, d3["wrong_root_on_ATTRIBUTE"], 0),
        ("V3 answered on ABSTAIN_REQUIRED", 38, d3["answered_on_ABSTAIN_REQUIRED"], 0),
        ("V3 lucky (right service on ABSTAIN_REQUIRED)", 18, d3["lucky_right_service_on_ABSTAIN_REQUIRED"], 0),
        ("V2 lucky", 25, d2["lucky_right_service_on_ABSTAIN_REQUIRED"], 0),
        ("V2 answered on ABSTAIN_REQUIRED", 52, d2["answered_on_ABSTAIN_REQUIRED"], 0),
        ("V2 correct", 36, d2["correct"], 0), ("V2 answered", 115, d2["answered"], 0), ("V2 unsafe", 79, d2["unsafe"], 0),
        ("ORACLE correct", 99, dec["ORACLE:UPPER-BOUND"]["correct"], 0), ("ORACLE unsafe", 0, dec["ORACLE:UPPER-BOUND"]["unsafe"], 0),
        ("V3 mean n_do", 2.71, d3["mean_n_do"], 0.005), ("V3 max n_do (task prompt: 'up to 8')", 8, d3["max_n_do"], 0),
        ("V3 mean cost term gamma=1 (PRE 3.3: 0.136)", 0.136, pv["mean_cost_term_V3_gamma1"], 0.0006),
        ("V3 mean U (2,1)", -0.338, pv["V3_minus_AA"]["template"]["mean"], 0.0006),
        ("V3 CI template lo", -0.465, pv["V3_minus_AA"]["template"]["pct95"][0], 0.012),
        ("V3 CI template hi", -0.219, pv["V3_minus_AA"]["template"]["pct95"][1], 0.012),
        ("V2 mean U (2,1)", -0.562, pv["V2_minus_AA"]["template"]["mean"], 0.0006),
        ("V3-V2 (2,1)", 0.224, pv["V3_minus_V2"]["template"]["mean"], 0.0006),
        ("V3-V2 CI lo", 0.085, pv["V3_minus_V2"]["template"]["pct95"][0], 0.012),
        ("V3-V2 CI hi", 0.365, pv["V3_minus_V2"]["template"]["pct95"][1], 0.012),
        ("SD V3 utility (2,1)", 0.969, pv["sd_V3"], 0.0006), ("skewness V3 utility", -1.09, pv["skewness_V3"], 0.006),
        ("SD V3-V2", 1.111, pv["sd_V3_minus_V2"], 0.0006),
        ("V3 break-even lambda kappa=0", 0.938, be["V3-FULL"]["kappa=0.0"]["strict_template"]["lambda_star"], 0.0006),
        ("V3 BE CI lo kappa=0", 0.61, be["V3-FULL"]["kappa=0.0"]["strict_template"]["pct95"][0], 0.03),
        ("V3 BE CI hi kappa=0", 1.42, be["V3-FULL"]["kappa=0.0"]["strict_template"]["pct95"][1], 0.03),
        ("V3 BE kappa=0.025", 0.582, be["V3-FULL"]["kappa=0.025"]["strict_template"]["lambda_star"], 0.0006),
        ("V3 BE kappa=0.05", 0.227, be["V3-FULL"]["kappa=0.05"]["strict_template"]["lambda_star"], 0.0006),
        ("V3 BE kappa=0.05 CI hi", 0.54, be["V3-FULL"]["kappa=0.05"]["strict_template"]["pct95"][1], 0.03),
        ("V3-DEFINITIVE-ONLY BE kappa=0", 0.892, be["V3-DEFINITIVE-ONLY"]["kappa=0.0"]["strict_template"]["lambda_star"], 0.0006),
        ("V2 BE kappa=0", 0.456, be["RIFT-FULL-V2"]["kappa=0.0"]["strict_template"]["lambda_star"], 0.0006),
        ("V2 BE kappa=0.05", 0.208, be["RIFT-FULL-V2"]["kappa=0.05"]["strict_template"]["lambda_star"], 0.0006),
        ("Legacy BE kappa=0", 0.351, be["RIFT-FULL-LEGACY"]["kappa=0.0"]["strict_template"]["lambda_star"], 0.0006),
        ("B0-EARLIEST BE kappa=0", 0.26, be["B0-EARLIEST"]["kappa=0.0"]["strict_template"]["lambda_star"], 0.0006),
        ("operational V3 lam=1 kappa=.05", -0.076, ver["operational_mean_kappa0.05"]["V3-FULL"]["1.0"], 0.0006),
        ("operational V3 lam=2", -0.195, ver["operational_mean_kappa0.05"]["V3-FULL"]["2.0"], 0.0006),
        ("operational V3 lam=4", -0.433, ver["operational_mean_kappa0.05"]["V3-FULL"]["4.0"], 0.0006),
        ("operational V2 lam=1", -0.149, ver["operational_mean_kappa0.05"]["RIFT-FULL-V2"]["1.0"], 0.0006),
        ("operational V2 lam=2", -0.363, ver["operational_mean_kappa0.05"]["RIFT-FULL-V2"]["2.0"], 0.0006),
        ("operational V2 lam=4", -0.792, ver["operational_mean_kappa0.05"]["RIFT-FULL-V2"]["4.0"], 0.0006),
        ("grid V3 lam=2 kappa=0", -0.202, cell("strict", "V3_minus_AA", 2.0, 0.0)["mean"], 0.0006),
        ("grid V3 lam=2 kappa=.025", -0.270, cell("strict", "V3_minus_AA", 2.0, 0.025)["mean"], 0.0006),
        ("grid V3 lam=2 kappa=.10", -0.473, cell("strict", "V3_minus_AA", 2.0, 0.10)["mean"], 0.0006),
        ("grid V3 lam=.5 kappa=0", 0.083, cell("strict", "V3_minus_AA", 0.5, 0.0)["mean"], 0.0006),
        ("grid V3 lam=5 kappa=.05", -0.909, cell("strict", "V3_minus_AA", 5.0, 0.05)["mean"], 0.0006),
        ("P(boot mean U>0) at (2,1) = 0.000", 0.0, pv["V3_minus_AA"]["template"]["p_boot_mean_gt0"], 0.0005),
        ("precision floor lambda=2", 2 / 3, 2 / 3, 1e-9),
        ("delta/ceiling (pi=.393 -> '25%')", 0.25, 0.10 / pi, 0.006),
        ("max n_do <= 20 (c in [0,1])", 0, exact["n_do_above_MAX_DO_any_method"], 0),
        ("correct & unsafe never both 1", 0, exact["correct_and_unsafe_both_1_any_method"], 0),
        ("score re-implementation mismatches", 0, len(mism), 0),
        ("gamma=1 <=> kappa=.05 per do (gamma=20 kappa)", 1.0, ver["gamma_kappa_equivalence"]["gamma_from_kappa"], 1e-12),
    ]
    vc = []
    for name, claimed, comp, tol in claims:
        vc.append({"claim": name, "claimed": claimed, "recomputed": float(comp), "tolerance": tol,
                   "verified": bool(abs(float(comp) - float(claimed)) <= tol + 1e-12)})
    ver["verified_vs_claimed"] = vc
    ver["n_claims"] = len(vc)
    ver["n_claims_verified"] = int(sum(c["verified"] for c in vc))
    ver["claims_not_verified"] = [c for c in vc if not c["verified"]]

    # ---- grid-significance claims in PRE 3.5 / AUD 3.4 (V3 vs AA, strict, template CI)
    sigp = [(g["lambda"], g["kappa"]) for g in grid if g["unsafe_definition"] == "strict" and g["contrast"] == "V3_minus_AA"
            and g["sig_pos_template"]]
    ver["grid_V3_vs_AA_strict_template_CI_entirely_positive_cells"] = sigp
    ver["grid_V3_vs_AA_strict_group_CI_entirely_positive_cells"] = [
        (g["lambda"], g["kappa"]) for g in grid if g["unsafe_definition"] == "strict" and g["contrast"] == "V3_minus_AA"
        and g["sig_pos_group"]]
    ver["grid_V3_vs_AA_operational_template_CI_entirely_positive_cells"] = [
        (g["lambda"], g["kappa"]) for g in grid if g["unsafe_definition"] == "operational" and g["contrast"] == "V3_minus_AA"
        and g["sig_pos_template"]]
    ver["grid_V3_vs_V2_strict_template_CI_entirely_positive_cells_count"] = sum(
        1 for g in grid if g["unsafe_definition"] == "strict" and g["contrast"] == "V3_minus_V2" and g["sig_pos_template"])
    ver["grid_V3_vs_V2_strict_template_CI_includes_0_cells"] = [
        (g["lambda"], g["kappa"]) for g in grid if g["unsafe_definition"] == "strict" and g["contrast"] == "V3_minus_V2"
        and not g["sig_pos_template"] and not g["sig_neg_template"]]
    (OUT / "utility_verification.json").write_text(json.dumps(ver, indent=1, default=float))
    print(f"claims verified: {ver['n_claims_verified']}/{ver['n_claims']}")
    for c in ver["claims_not_verified"]:
        print("  NOT VERIFIED:", c)
    print("mismatches vs saved scores:", len(mism), "of", N * len(METHODS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
