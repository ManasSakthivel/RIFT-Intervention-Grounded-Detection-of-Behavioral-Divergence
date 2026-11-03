#!/usr/bin/env python3
"""Sprint 4.5.0 PRE-REGISTRATION AUDIT (development evidence only; NOT the confirmatory experiment).

Reads ONLY committed development artifacts:
  datasets/rift_v2/{dev,val}.json                      (labels; sha256-pinned)
  artifacts/sprint4_4_0/v3_{dev,val}.json              (V3 records/scores)
  artifacts/sprint4_3_0/results/{dev,val}/per_scenario.json   (V2 + baselines + oracle records/scores)

It never opens the Sprint 4.3.0 held-out data, never runs V3/V2 or any method, never generates scenarios.
Output: artifacts/sprint4_5_0/prereg_audit/audit.json   (all numbers quoted in the Sprint 4.5.0 preregistration documents)

Everything computed here is a property of DEV/VAL (which informed V3's design). None of it is confirmatory.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "artifacts" / "sprint4_5_0" / "prereg_audit"
SEED = 450
PINS = {"dev": "a833ad0ca1db0583a30bc4450f9f59b2984a5823702935ef59c6b037e026ef5f",
        "val": "e82252b47f29dc1353586034b6fd8c3491df3221851f9c84c48bf717a944a1fb"}
MAX_DO = 20
LAMBDAS = [0.5, 1.0, 2.0, 3.0, 5.0, 9.0, 19.0]
KAPPAS = [0.0, 0.025, 0.05, 0.10]
Z = {0.025: 1.959964, 0.05: 1.644854, 0.0125: 2.241403, 0.00833: 2.394, 0.00625: 2.498, 0.005: 2.5758}
ZB80, ZB90 = 0.841621, 1.281552


def load_labels(split):
    p = REPO / "datasets" / "rift_v2" / f"{split}.json"
    raw = p.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PINS[split], f"{split} pin mismatch"
    return {s["scenario_id"]: s for s in json.loads(raw)["scenarios"]}


def load_rows():
    """scenario-level table: per-method (answered, correct, unsafe, n_do) + labels."""
    rows = []
    for split in ("dev", "val"):
        lab = load_labels(split)
        v3 = {r["scenario_id"]: r for r in json.loads((REPO / "artifacts/sprint4_4_0" / f"v3_{split}.json").read_text())}
        old = {r["scenario_id"]: r for r in json.loads(
            (REPO / "artifacts/sprint4_3_0/results" / split / "per_scenario.json").read_text())}
        for sid, sc in lab.items():
            gt = sc["ground_truth"]
            row = {"sid": sid, "split": split, "template": sc["template_id"], "structure": sc["dimensions"]["structure"],
                   "family": sc["dimensions"]["family"], "expected": gt["expected_outcome"],
                   "abstain_reason": gt.get("abstain_reason"), "negative": sc["dimensions"]["negative"], "m": {}}
            for name, src in (("V3-FULL", v3[sid]["methods"]["V3-FULL"]),
                              ("V3-DEFINITIVE-ONLY", v3[sid]["methods"]["V3-DEFINITIVE-ONLY"])):
                row["m"][name] = (src["score"], src["record"])
            for name, src in old[sid]["methods"].items():
                if name in ("RIFT-FULL-V2", "B0-EARLIEST", "B0-HIGHEST", "B1-LATENCY-CORR", "B3-SIEVE-LIKE", "B5-RIFT-OBS",
                            "B6-RIFT-RANDOM", "B7-RIFT-ONE-SHOT", "RIFT-FULL-LEGACY", "ORACLE:UPPER-BOUND",
                            "ORACLE:RIFT-FULL-V2-ORACLE-GRAPH"):
                    row["m"][name] = (src["score"], src["record"])
            rows.append(row)
    return rows


def vec(rows, method):
    c = np.array([int(r["m"][method][0]["correct"]) for r in rows], float)
    u = np.array([int(r["m"][method][0]["unsafe"]) for r in rows], float)
    a = np.array([int(r["m"][method][0]["answered"]) for r in rows], float)
    n = np.array([float(r["m"][method][1]["n_do"]) for r in rows], float)
    return c, u, a, n


def util(c, u, n, lam, kap):
    return c - lam * u - kap * n


def cluster_ids(rows, kind):
    if kind == "template":
        return [r["template"] for r in rows]
    if kind == "structure":
        return [r["structure"] for r in rows]
    if kind == "family":
        return [r["family"] for r in rows]
    raise ValueError(kind)


def cluster_boot_mean(d, cl, B=4000, seed=SEED):
    keys = sorted(set(cl))
    idx = {k: [] for k in keys}
    for i, c in enumerate(cl):
        idx[c].append(i)
    sums = np.array([d[idx[k]].sum() for k in keys])
    cnt = np.array([len(idx[k]) for k in keys], float)
    rng = np.random.default_rng(seed)
    dr = rng.integers(0, len(keys), size=(B, len(keys)))
    est = sums[dr].sum(1) / cnt[dr].sum(1)
    return float(d.mean()), [float(x) for x in np.percentile(est, [2.5, 97.5])], len(keys)


def icc_anova(d, cl):
    keys = sorted(set(cl))
    idx = {k: [] for k in keys}
    for i, c in enumerate(cl):
        idx[c].append(i)
    N, K = len(d), len(keys)
    ni = np.array([len(idx[k]) for k in keys], float)
    means = np.array([d[idx[k]].mean() for k in keys])
    gm = d.mean()
    ssb = float((ni * (means - gm) ** 2).sum())
    ssw = float(sum(((d[idx[k]] - d[idx[k]].mean()) ** 2).sum() for k in keys))
    msb, msw = ssb / (K - 1), ssw / (N - K)
    m0 = (N - (ni ** 2).sum() / N) / (K - 1)
    rho = (msb - msw) / (msb + (m0 - 1) * msw)
    return {"icc": float(rho), "K": K, "N": N, "m0": float(m0), "msb": msb, "msw": msw}


def deff_empirical(d, cl):
    """Var(cluster-robust mean)/Var(iid mean), CR0 ratio estimator."""
    keys = sorted(set(cl))
    idx = {k: [] for k in keys}
    for i, c in enumerate(cl):
        idx[c].append(i)
    N, K = len(d), len(keys)
    mu = d.mean()
    v_cl = sum(((d[idx[k]] - mu).sum()) ** 2 for k in keys) / N ** 2 * K / (K - 1)
    v_iid = d.var(ddof=1) / N
    return float(v_cl / v_iid)


def n_required(sd, delta, alpha_tail, power=0.80, deff=1.0):
    zb = ZB80 if power == 0.80 else ZB90
    za = Z[alpha_tail]
    return int(math.ceil(((za + zb) * sd / delta) ** 2 * deff))


def power_normal(mu, sd, N, alpha_tail, deff=1.0):
    se = sd * math.sqrt(deff / N)
    za = Z[alpha_tail]
    from scipy.stats import norm
    return float(1 - norm.cdf(za - mu / se) + norm.cdf(-za - mu / se))  # two-sided total rejection


def main():
    rows = load_rows()
    N = len(rows)
    out = {"purpose": "development-evidence audit for Sprint 4.5.0 preregistration; NOT confirmatory",
           "n_scenarios": N, "n_dev": sum(r["split"] == "dev" for r in rows), "n_val": sum(r["split"] == "val" for r in rows),
           "inputs_sha256": {f"datasets/rift_v2/{s}.json": PINS[s] for s in PINS}}
    pi = np.mean([r["expected"] == "ATTRIBUTE" for r in rows])
    out["prevalence_attribute"] = {"pooled": float(pi), "dev": float(np.mean([r["expected"] == "ATTRIBUTE" for r in rows if r["split"] == "dev"])),
                                   "val": float(np.mean([r["expected"] == "ATTRIBUTE" for r in rows if r["split"] == "val"]))}
    cl_t = cluster_ids(rows, "template")

    # ---------------- 1. decomposition of V3 / V2 / baselines --------------------------------------
    methods = ["V3-FULL", "V3-DEFINITIVE-ONLY", "RIFT-FULL-V2", "RIFT-FULL-LEGACY", "B0-EARLIEST", "B0-HIGHEST",
               "B1-LATENCY-CORR", "B3-SIEVE-LIKE", "B5-RIFT-OBS", "B6-RIFT-RANDOM", "B7-RIFT-ONE-SHOT",
               "ORACLE:UPPER-BOUND", "ORACLE:RIFT-FULL-V2-ORACLE-GRAPH"]
    dec = {}
    for mth in methods:
        c, u, a, n = vec(rows, mth)
        att = np.array([r["expected"] == "ATTRIBUTE" for r in rows])
        sc = [r["m"][mth][0] for r in rows]
        u_wrong = sum(1 for s in sc if s["wrong_root"])
        u_abs = sum(1 for s in sc if s["unsafe"] and s["expected"] == "ABSTAIN_REQUIRED")
        # lucky: answered an ABSTAIN_REQUIRED scenario but the named service IS a true root
        lucky = 0
        by_reason = Counter()
        for r, s in zip(rows, sc):
            if s["unsafe"] and s["expected"] == "ABSTAIN_REQUIRED":
                by_reason[r["abstain_reason"]] += 1
        dec[mth] = {"correct": int(c.sum()), "answered": int(a.sum()), "unsafe": int(u.sum()),
                    "unsafe_wrong_root_on_ATTRIBUTE": u_wrong, "unsafe_answer_on_ABSTAIN_REQUIRED": u_abs,
                    "unsafe_abstain_required_by_reason": dict(by_reason),
                    "answered_on_attribute": int((a * att).sum()), "mean_n_do": float(n.mean()),
                    "precision_among_answered": float(c.sum() / a.sum()) if a.sum() else None,
                    "lambda_star_kappa0": float(c.sum() / u.sum()) if u.sum() else None}
    out["decomposition_pooled_dev_val"] = dec

    # ---------------- 2. utility grid (point estimates) and break-even -----------------------------
    grid = {}
    for mth in methods:
        c, u, a, n = vec(rows, mth)
        g = {}
        for lam in LAMBDAS:
            for kap in KAPPAS:
                g[f"lam={lam},kap={kap}"] = float(util(c, u, n, lam, kap).mean())
        grid[mth] = g
    out["mean_utility_grid"] = grid

    # break-even lambda* = (E[C]-kappa E[N]) / E[U]  with cluster-bootstrap CI (template clusters)
    be = {}
    rng = np.random.default_rng(SEED)
    keys = sorted(set(cl_t))
    idx = {k: [] for k in keys}
    for i, c in enumerate(cl_t):
        idx[c].append(i)
    draws = rng.integers(0, len(keys), size=(4000, len(keys)))
    for mth in ("V3-FULL", "V3-DEFINITIVE-ONLY", "RIFT-FULL-V2"):
        c, u, a, n = vec(rows, mth)
        sc_, su_, sn_, cnt = (np.array([x[idx[k]].sum() for k in keys]) for x in (c, u, n, np.ones(N)))
        be[mth] = {}
        for kap in KAPPAS:
            point = float((c.sum() - kap * n.sum()) / u.sum())
            num = sc_[draws].sum(1) - kap * sn_[draws].sum(1)
            den = su_[draws].sum(1)
            ok = den > 0
            lam = num[ok] / den[ok]
            be[mth][f"kappa={kap}"] = {"lambda_star": point, "ci95_template_cluster": [float(x) for x in np.percentile(lam, [2.5, 97.5])]}
    out["break_even_lambda"] = be

    # precision threshold implied by lambda
    out["lambda_to_required_precision"] = {str(l): float(l / (1 + l)) for l in LAMBDAS}

    # ---------------- 3. primary-endpoint distribution at candidate parameters -----------------------
    prim = {}
    for lam, kap in ((2.0, 0.05), (1.0, 0.05), (2.0, 0.0), (4.0, 0.05)):
        c, u, a, n = vec(rows, "V3-FULL")
        d = util(c, u, n, lam, kap)
        m_, ci, K = cluster_boot_mean(d, cl_t)
        prim[f"lam={lam},kap={kap}"] = {"mean": m_, "sd": float(d.std(ddof=1)), "ci95_template_cluster": ci, "K_clusters": K,
                                        "dev_mean": float(d[[r["split"] == "dev" for r in rows]].mean()),
                                        "val_mean": float(d[[r["split"] == "val" for r in rows]].mean()),
                                        "dev_sd": float(d[[r["split"] == "dev" for r in rows]].std(ddof=1)),
                                        "val_sd": float(d[[r["split"] == "val" for r in rows]].std(ddof=1)),
                                        "min": float(d.min()), "max": float(d.max())}
        cv, uv, av, nv = vec(rows, "RIFT-FULL-V2")
        dv = util(cv, uv, nv, lam, kap)
        prim[f"lam={lam},kap={kap}"]["V2_mean"] = float(dv.mean())
        prim[f"lam={lam},kap={kap}"]["V3_minus_V2"] = cluster_boot_mean(d - dv, cl_t)[:2]
    out["primary_candidate_parameters"] = prim

    # ---------------- 4. oracle ceiling for the scale of delta ---------------------------------------
    co, uo, ao, no = vec(rows, "ORACLE:UPPER-BOUND")
    out["scale"] = {"max_possible_mean_utility_perfect_attribution": float(pi),
                    "oracle_upper_bound_mean_utility_kappa0": float(co.mean()),
                    "delta_0.10_as_fraction_of_ceiling": float(0.10 / pi),
                    "note": "ORACLE rows are privileged upper bounds (read ground truth); shown only to scale delta"}

    # ---------------- 5. clustering: ICC / design effect --------------------------------------------
    c, u, a, n = vec(rows, "V3-FULL")
    d = util(c, u, n, 2.0, 0.05)
    clust = {}
    for kind in ("template", "structure", "family"):
        cl = cluster_ids(rows, kind)
        r_ = icc_anova(d, cl)
        r_["deff_empirical_at_observed_cluster_sizes"] = deff_empirical(d, cl)
        rng2 = np.random.default_rng(SEED)
        ks = sorted(set(cl))
        ix = {k: [] for k in ks}
        for i, x in enumerate(cl):
            ix[x].append(i)
        boots = []
        for _ in range(1500):
            pick = rng2.integers(0, len(ks), len(ks))
            sel = np.concatenate([ix[ks[p]] for p in pick])
            labels = np.concatenate([[j] * len(ix[ks[p]]) for j, p in enumerate(pick)])
            try:
                boots.append(icc_anova(d[sel], list(labels))["icc"])
            except Exception:
                pass
        r_["icc_boot95"] = [float(x) for x in np.percentile(boots, [2.5, 97.5])]
        clust[kind] = r_
    # union-find groups on template + topology (what independence.py calls "group")
    sys.path.insert(0, str(REPO))
    from src.rift.scenarios.independence import topology_hash
    from src.rift.scenarios.splitter import build_groups
    scs = {**load_labels("dev"), **load_labels("val")}
    grp = build_groups(scs, [lambda s: ("t", s["template_id"]), lambda s: ("topo", topology_hash(s))])
    out["union_find_groups_template_or_topology"] = {"n_groups": len(set(grp.values())), "sizes": sorted(Counter(grp.values()).values(), reverse=True)}
    out["clustering_at_V3_lam2_kap0.05"] = clust
    # per-structure means of D (heterogeneity)
    per_struct = defaultdict(list)
    for r, x in zip(rows, d):
        per_struct[r["structure"]].append(x)
    out["mean_D_by_structure"] = {k: {"n": len(v), "mean": float(np.mean(v))} for k, v in sorted(per_struct.items())}
    per_neg = defaultdict(list)
    for r, x in zip(rows, d):
        per_neg[str(r["abstain_reason"])].append(x)
    out["mean_D_by_label_reason"] = {k: {"n": len(v), "mean": float(np.mean(v))} for k, v in sorted(per_neg.items(), key=str)}

    # ---------------- 6. closed-form parameterisation (coverage / accuracy / unsafe) --------------------
    att = np.array([r["expected"] == "ATTRIBUTE" for r in rows])
    c, u, a, n = vec(rows, "V3-FULL")
    cov_A = float(a[att].mean())
    acc_A = float(c[att].sum() / a[att].sum())
    cov_R = float(a[~att].mean())
    out["v3_operating_point"] = {"pi_attribute": float(pi), "coverage_on_attribute": cov_A, "accuracy_given_answered_on_attribute": acc_A,
                                 "answer_rate_on_abstain_required": cov_R, "mean_n_do": float(n.mean()),
                                 "abstention_rate_overall": float(1 - a.mean()),
                                 "formula": "U = pi*covA*accA - lam*(pi*covA*(1-accA) + (1-pi)*covR) - kappa*nbar"}
    # required answer-rate on ABSTAIN_REQUIRED to break even, holding everything else fixed
    req = {}
    for lam in (1.0, 2.0, 4.0):
        for kap in (0.0, 0.05):
            val = (pi * cov_A * acc_A - lam * pi * cov_A * (1 - acc_A) - kap * n.mean()) / (lam * (1 - pi))
            req[f"lam={lam},kap={kap}"] = float(val)
    out["answer_rate_on_abstain_required_needed_for_U_zero"] = req

    # ---------------- 7. power / sample size ---------------------------------------------------------
    sd = float(d.std(ddof=1))
    rho_t = clust["template"]["icc"]
    pw = {"sd_pooled_V3_lam2_kap0.05": sd, "icc_template": rho_t, "assumed_cluster_sizes": {}}
    for Nn in (600, 800, 1200, 1600, 2000, 3000):
        K = min(176, Nn)
        mbar = Nn / K
        pw["assumed_cluster_sizes"][str(Nn)] = {"K": K, "m": mbar, "deff_if_icc_point": 1 + (mbar - 1) * max(rho_t, 0.0)}
    tab = []
    for delta in (0.05, 0.075, 0.10, 0.15):
        for deff in (1.0, 1.25, 1.5, 2.0):
            tab.append({"delta": delta, "deff": deff,
                        "N_two_sided_0.05_power80": n_required(sd, delta, 0.025, 0.80, deff),
                        "N_two_sided_0.05_power90": n_required(sd, delta, 0.025, 0.90, deff),
                        "N_alpha_0.0125_power80": n_required(sd, delta, 0.0125, 0.80, deff),
                        "N_one_sided_0.05_power80_(plan_sec6)": n_required(sd, delta, 0.05, 0.80, deff)})
    pw["n_required_table"] = tab
    curve = {}
    for Nn in (300, 600, 800, 1200, 1600, 2000, 3000):
        for deff in (1.0, 1.5, 2.0):
            curve[f"N={Nn},deff={deff}"] = {f"mu={mu}": power_normal(mu, sd, Nn, 0.025, deff)
                                           for mu in (-0.34, -0.20, -0.10, 0.0, 0.05, 0.10, 0.15, 0.20)}
    pw["power_two_sided_alpha0.05_by_true_mean_utility"] = curve
    # N needed to conclude NEGATIVE (CI upper < delta) if the truth equals dev/val
    mu_dv = float(d.mean())
    pw["dev_val_point_estimate_mean_utility_V3_lam2_kap0.05"] = mu_dv
    pw["N_to_exclude_delta0.10_if_truth_equals_devval"] = int(math.ceil(((Z[0.025] + ZB80) * sd / (0.10 - mu_dv)) ** 2))
    out["power"] = pw

    # ---------------- 8. discordance rates for the secondary endpoints -----------------------------------
    c3, u3, a3, n3 = vec(rows, "V3-FULL")
    c2, u2, a2, n2 = vec(rows, "RIFT-FULL-V2")
    sec = {"H3_unsafe_V3_vs_V2": {"only_V3_unsafe": int(((u3 == 1) & (u2 == 0)).sum()), "only_V2_unsafe": int(((u3 == 0) & (u2 == 1)).sum()),
                                  "n": N},
           "H4_P1_V3_vs_V2": {"only_V3_correct": int(((c3 == 1) & (c2 == 0) & att).sum()),
                              "only_V2_correct": int(((c3 == 0) & (c2 == 1) & att).sum()), "n": int(att.sum())}}
    d32 = util(c3, u3, n3, 2.0, 0.05) - util(c2, u2, n2, 2.0, 0.05)
    sec["H2_utility_V3_minus_V2"] = {"mean": float(d32.mean()), "sd": float(d32.std(ddof=1)),
                                     "N_two_sided_0.05_power80_delta0.10_deff1.5": n_required(float(d32.std(ddof=1)), 0.10, 0.025, 0.80, 1.5),
                                     "N_alpha_0.0125_power80_delta0.10_deff1.5": n_required(float(d32.std(ddof=1)), 0.10, 0.0125, 0.80, 1.5)}
    # unsafe-rate difference power (paired binary): sd of paired difference
    du = (u3 - u2)
    sec["H3_paired_sd"] = float(du.std(ddof=1))
    sec["H3_diff_in_unsafe_rate"] = float(du.mean())
    out["secondary_endpoint_inputs"] = sec

    # ---------------- 9. multiplicity worst cases ---------------------------------------------------------
    out["multiplicity_notes"] = {
        "plan_sec2.5_alpha": "0.025 (two-sided 0.05 / one-sided 0.025) -> z=1.96",
        "plan_sec6_alpha": "one-sided Holm-adjusted p<0.05 -> z=1.645 (inconsistent with sec2.5)",
        "plan_family_size": "H1..H4 = 4 (plus V3-CIDx H1' = 5), but sec2.5 'Holm worst case' used 3"}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "audit.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("prevalence_attribute", "break_even_lambda", "primary_candidate_parameters",
                                           "v3_operating_point", "scale")}, indent=1, default=float)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
