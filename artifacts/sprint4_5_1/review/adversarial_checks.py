#!/usr/bin/env python3
"""Sprint 4.5.1 AGENT 7 (internal adversarial review) - analysis-only scratch checks.

Reads ONLY: artifacts/sprint4_4_0/v3_{dev,val}.json (saved V3 records) and datasets/rift_v2/{dev,val}.json
(readable development / validation sets). Never touches held-out material. Runs no RIFT method.
Writes artifacts/sprint4_5_1/review/adversarial_checks.json.   Seed 4510.
"""
import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
rng = np.random.default_rng(4510)
LAM, GAM = 2.0, 1.0


def load(split):
    runs = json.loads((REPO / f"artifacts/sprint4_4_0/v3_{split}.json").read_text())
    ds = json.loads((REPO / f"datasets/rift_v2/{split}.json").read_text())
    ds = ds if isinstance(ds, list) else ds.get("scenarios", ds)
    byid = {s["scenario_id"]: s for s in ds}
    rows = []
    for r in runs:
        sc = byid[r["scenario_id"]]
        m = r["methods"]["V3-FULL"]
        s, rec = m["score"], m["record"]
        c, u = int(s["correct"]), int(s["unsafe"])
        # operational unsafe: answered and named service not a true root
        gt = sc["ground_truth"]
        roots = set(gt["roots"])
        ans = s["answered"]
        uop = int(bool(ans and s["top1"] not in roots))
        rows.append(dict(sid=r["scenario_id"], tmpl=r["template_id"], struct=sc["dimensions"]["structure"],
                         fam=sc["dimensions"]["family"], exp=s["expected"], reason=gt.get("abstain_reason"),
                         ans=int(ans), c=c, u=u, uop=uop, ndo=rec["n_do"],
                         U=c - LAM * u - GAM * rec["n_do"] / 20.0,
                         Uop=c - LAM * uop - GAM * rec["n_do"] / 20.0,
                         lucky=int(bool(ans and s["expected"] == "ABSTAIN_REQUIRED" and s["top1"] in roots))))
    return rows


rows = load("dev") + load("val")
N = len(rows)
U = np.array([r["U"] for r in rows])
res = {"N": N, "mean_U": float(U.mean()), "sd_U": float(U.std(ddof=1))}

# ---- 1. structure-level ICC, design effect, bootstrap CI over structures (K = 11 frozen structures)
by_s = defaultdict(list)
for r in rows:
    by_s[r["struct"]].append(r["U"])


def anova_icc(groups):
    k = len(groups)
    n = np.array([len(g) for g in groups], float)
    tot = n.sum()
    gm = sum(sum(g) for g in groups) / tot
    msb = sum(len(g) * (np.mean(g) - gm) ** 2 for g in groups) / (k - 1)
    msw = sum(((np.array(g) - np.mean(g)) ** 2).sum() for g in groups) / (tot - k)
    n0 = (tot - (n ** 2).sum() / tot) / (k - 1)
    return float(max(0.0, (msb - msw) / (msb + (n0 - 1) * msw))), float(n0)


gl = list(by_s.values())
icc_s, n0 = anova_icc(gl)
boots = []
keys = list(by_s)
for _ in range(4000):
    pick = rng.choice(len(keys), len(keys))
    boots.append(anova_icc([by_s[keys[i]] for i in pick])[0])
res["structure_icc"] = {"K": len(keys), "icc": icc_s, "n0": n0, "boot95": [float(np.percentile(boots, 2.5)),
                        float(np.percentile(boots, 97.5))], "boot_median": float(np.median(boots)),
                        "structure_means": {k: float(np.mean(v)) for k, v in by_s.items()},
                        "structure_n": {k: len(v) for k, v in by_s.items()}}
means = np.array([np.mean(v) for v in by_s.values()])
res["structure_means_sd"] = float(means.std(ddof=1))

# design effect if structures were a random sample: DEFF = 1 + (m-1) rho, m = 2000/16 = 125
m = 2000 / 16
res["deff_structure_random"] = {}
for rho in [icc_s, 0.01, 0.02, 0.04, 0.07]:
    res["deff_structure_random"][f"rho={rho:.3f}"] = 1 + (m - 1) * rho


def power(mu, sd, n, deff, alpha=0.025):
    se = sd * math.sqrt(deff / n)
    return float(stats.norm.cdf(mu / se - stats.norm.ppf(1 - alpha)))


res["power_N2000_mu0.10_sd0.969"] = {f"deff={d:.2f}": power(0.10, 0.969, 2000, d)
                                     for d in [1, 1.37, 2, 3, 4, 6.2, 8, 10]}
# N needed for 80/90 % at large DEFF
res["N_needed_mu0.10"] = {f"deff={d}": {"80": int(d * ((stats.norm.ppf(.975) + stats.norm.ppf(.8)) * .969 / .1) ** 2),
                                         "90": int(d * ((stats.norm.ppf(.975) + stats.norm.ppf(.9)) * .969 / .1) ** 2)}
                          for d in [2, 3, 4, 6.2]}
# effective #independent units if structure-level dependence: SE of mean from K=16 structure means
res["superpop_structure_inference"] = {
    "between_structure_sd_dev_val": float(means.std(ddof=1)),
    "se_mean_if_K16_structures_random": float(means.std(ddof=1) / math.sqrt(16)),
    "t_crit_df15": float(stats.t.ppf(.975, 15)),
    "min_detectable_one_sided_80pct": float((stats.t.ppf(.975, 15) + .865) * means.std(ddof=1) / 4)}

# ---- 2. stratified (fixed-quota) variance vs. pooled SD used for power
att = np.array([r["U"] for r in rows if r["exp"] == "ATTRIBUTE"])
abs_ = np.array([r["U"] for r in rows if r["exp"] != "ATTRIBUTE"])
pi = 0.40
var_strat = (pi ** 2) * att.var(ddof=1) / (800) + ((1 - pi) ** 2) * abs_.var(ddof=1) / 1200
res["stratified"] = {"mean_U_attribute": float(att.mean()), "sd_U_attribute": float(att.std(ddof=1)),
                     "mean_U_abstain": float(abs_.mean()), "sd_U_abstain": float(abs_.std(ddof=1)),
                     "expected_mean_U_at_quota_pi0.40": float(pi * att.mean() + (1 - pi) * abs_.mean()),
                     "se_fixed_quota_N2000_noCluster": float(math.sqrt(var_strat)),
                     "se_pooled_sd_N2000_noCluster": float(0.969 / math.sqrt(2000))}

# ---- 3. per-abstain-reason mean utility; effect of the preregistered reason quota on expected U
reasons = defaultdict(list)
for r in rows:
    if r["exp"] != "ATTRIBUTE":
        reasons[r["reason"]].append(r)
quota = {"WEAK_SIGNAL": 360, "ROOT_UNOBSERVED": 240, "SYMMETRIC_MUTUAL_DEPENDENCY": 180,
         "INSUFFICIENT_BASELINE": 180, "NO_DISCRIMINATING_EVIDENCE": 140, "NO_FAULT": 100}
tab = {}
expU = 0.0
for k, v in reasons.items():
    tab[k] = {"n": len(v), "answer_rate": float(np.mean([x["ans"] for x in v])), "mean_U": float(np.mean([x["U"] for x in v])),
              "lucky_correct_rate": float(np.mean([x["lucky"] for x in v])), "quota": quota.get(k)}
    expU += quota.get(k, 0) * np.mean([x["U"] for x in v])
expU = (expU + 800 * att.mean()) / 2000
res["per_reason"] = tab
res["expected_mean_U_under_preregistered_quota_using_devval_stratum_means"] = float(expU)
res["lucky_correct_total"] = int(sum(r["lucky"] for r in rows))
res["abstain_required_answered_total"] = int(sum(r["ans"] for r in rows if r["exp"] != "ATTRIBUTE"))

# ---- 4. the operational-unsafe 'robustness condition' is implied by the strict result
res["Uop_ge_U_pointwise"] = bool(all(r["Uop"] >= r["U"] - 1e-12 for r in rows))
res["mean_U"] = float(U.mean())
res["mean_Uop"] = float(np.mean([r["Uop"] for r in rows]))
res["frac_scenarios_Uop_gt_U"] = float(np.mean([r["Uop"] > r["U"] + 1e-12 for r in rows]))

# ---- 5. 'borderline = within 2 SE of threshold => NOT eligible' for a perfectly valid estimator
R = 2000
se = math.sqrt(0.05 * 0.95 / R)
thr = 0.07 - 2 * se
p_cell_flag = 1 - stats.binom.cdf(math.ceil(thr * R) - 1, R, 0.05)
p_cell_exceed = 1 - stats.binom.cdf(math.floor(0.07 * R), R, 0.05)
res["borderline_rule"] = {"R": R, "se_at_0.05": se, "flag_threshold_rate": thr, "p_flag_per_null_cell_true_size_0.05": float(p_cell_flag),
                          "p_exceed_0.07_per_cell": float(p_cell_exceed)}
for ncells in (20, 50, 100, 120):
    res["borderline_rule"][f"p_at_least_one_flag_{ncells}_null_cells"] = float(1 - (1 - p_cell_flag) ** ncells)
    res["borderline_rule"][f"p_at_least_one_exceed_{ncells}_null_cells"] = float(1 - (1 - p_cell_exceed) ** ncells)
# sham window [0.03,0.07]: P(rate<0.03) for valid size 0.05
res["borderline_rule"]["p_sham_below_0.03_size0.05"] = float(stats.binom.cdf(math.floor(0.03 * R) - 1, R, 0.05))
# E6: exact p-value granularity
res["E6_attainable_size_alpha0.05"] = math.floor(0.05 * 252) / 252

# ---- 6. CID grid: duplicate DGP cells (canonical spec -> count distinct)
cells = []
base = dict(d=0, delay=0, m=1, own=None, shared=None, rho=0, v=1, om=None, trig=None, sel=1, onset=None, rep=None)


def add(block, **kw):
    spec = dict(base); spec.update(kw); cells.append((block, tuple(sorted((k, str(v)) for k, v in spec.items()))))


for d, de, m_ in itertools.product([0, .25, .5, .75, 1, 2], [0, 5, 10], [1, 3, 6]):
    add("B1", d=d, delay=de, m=m_)
for sh, mg, d in itertools.product(["ramp", "step", "osc", "inter", "pulse", "recdelay"], [.3, 1, 3], [0, 1]):
    add("B2", own=(sh, mg), d=d)
for sh, mg, ph, d in itertools.product(["ramp", "osc"], [.3, 1, 3], [0, .5, 1], [0, 1]):
    # phi = share NOT present in control. phi=1 => y's drift absent in control == own-drift cell for any estimator
    # without a control (E0,E1,E3,E5); we canonicalise phi=1 to the B2 spec for those estimators.
    add("B3", shared=(sh, mg, ph), d=d)
for rho, dr, d in itertools.product([0, .5, .8], [None, ("ramp", 1)], [0, 1]):
    add("B4", rho=rho, own=dr, d=d)
for v, d in itertools.product([1, 2, 4], [0, 1]):
    add("B5", v=v, d=d)
for om, tau, d in itertools.product([0, .25, .5], [10, 30], [0, 1]):
    add("B6", om=(om, tau) if om else None, d=d)
for tr, rho, d in itertools.product([None, 2, 3], [0, .5, .8], [0, 1]):
    add("B7", trig=tr, rho=rho, d=d)
for k, dr in itertools.product([1, 5, 10], [None, ("ramp", 1)]):
    add("B8a", sel=k, own=dr, d=0)
for per in [30, 50, 80, 120]:
    add("B8b", own=("osc_period", per), d=0)
for on, sh, d in itertools.product(["A", "boundary", "B"], ["step", "ramp", "pulse"], [0, 1]):
    add("B9", onset=(on, sh), d=d)
for lr, sh, d in itertools.product([1, .5, 0], ["ramp", "osc"], [0, 1]):
    add("B10", rep=(lr, sh), d=d)
for _ in range(4):
    add("B11", d=0)
tot = len(cells)
distinct = len(set(c[1] for c in cells[:-4])) + 4
res["cid_cells"] = {"total_listed": tot, "distinct_dgp_specs_excluding_mixtures_plus4": distinct,
                    "exact_duplicates_among_factorial": 214 - len(set(c[1] for c in cells[:-4])),
                    "note": "duplicates computed on a canonical spec; B3 phi=1/B2 and B9/B2 overlaps for no-control estimators are NOT counted here (so true redundancy is larger)"}

# ---- 7. alpha-spending forks: grid (8 lambda x 4 kappa) - how many cells could be 'significantly positive' by chance
res["grid"] = {"cells": 8 * 4, "note": "secondary, descriptive; label function uses only primary"}

(OUT / "adversarial_checks.json").write_text(json.dumps(res, indent=1, default=float))
print(json.dumps(res, indent=1, default=float))
