#!/usr/bin/env python3
"""Sprint 4.5.1 (lead) power for the FIXED-STRATA hierarchical design (Decision 1).   Non-confirmatory; dev/val marginals only.

Design:  16 fixed structures (strata) > 16 template-groups per structure (structure x family; generator-assigned group unit,
         ~7.8 scenarios each) > scenarios.   N = 2000 (125 per structure; 16 groups of 5..9 per structure => 256 groups).
Estimand: theta = sum_s W_s * mean_s  (W_s = design quota share 1/16; mean over the finite family of scenarios of structure s that the
         generator can produce under the pre-committed acceptance rules).  NO inference to unseen structures.
Estimator/inference (SAP 3 revised): stratified ratio estimator, per-structure CR1 cluster variance, studentised STRATIFIED cluster
         bootstrap (groups resampled with replacement WITHIN each structure; structure sizes/weights fixed).  B = 199 here (20000 in the plan).

Part A  within-structure dependence in dev/val: ICC of structure-demeaned V3 utility at template level and union-find-group level,
        with a group-bootstrap CI;  family-level ICC after removing structure means (crossed factor).
Part B  Monte-Carlo size/power: latent Gaussian-copula model  Z = sqrt(rg) G_group + sqrt(rf) F_family + sqrt(1-rg-rf) e,
        mapped through the empirical structure-demeaned dev/val utility distribution (skew/discreteness kept), plus fixed structure shifts.
        Cases: within-group ICC rg in {0,.03,.05,.1,.2,.3}; ignored crossed family ICC rf in {0,.02,.05}; layouts 16x16(~8), 16x8(~16), 16x32(~4).
        Reports realised within-structure DEFF = ANOVA-based, size at mu=0 and power at mu=+0.10 (SD of marginal fixed; effect not changed).
Part C  random-structure limitation, quantified analytically (NOT an effective-sample-size claim).
Seed 4518.  Output: artifacts/sprint4_5_1/power/stratified_power.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import scipy.stats as sps

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts import sprint451_utility_sensitivity as U  # noqa: E402

SEED = 4518
S = 16
N_PER = 125
R = 1000
B = 199
OUT = REPO / "artifacts" / "sprint4_5_1" / "power" / "stratified_power.json"


# ------------------------------------------------------------------------------------------ ANOVA ICC (unbalanced)
def anova_icc(v, g):
    ids, inv = np.unique(g, return_inverse=True)
    K, N = len(ids), len(v)
    n = np.bincount(inv).astype(float)
    cs = np.bincount(inv, weights=v)
    gm = v.mean()
    ssb = np.sum(cs ** 2 / n) - N * gm ** 2
    ssw = np.sum(v ** 2) - np.sum(cs ** 2 / n)
    n0 = (N - np.sum(n ** 2) / N) / (K - 1)
    msb, msw = ssb / (K - 1), ssw / (N - K)
    return float((msb - msw) / (msb + (n0 - 1) * msw)), K, float(n0), float(np.sum(n ** 2) / N)


def part_a(rows, rng):
    u = U.util(rows, "V3-FULL", 2.0, 0.05)
    st = np.array([r["structure"] for r in rows])
    tpl = np.array([r["template"] for r in rows])
    grp = np.array([r["group"] for r in rows])
    fam = np.array([r["template"].split("|")[1] for r in rows])
    resid = u.copy()
    for s in np.unique(st):
        resid[st == s] -= u[st == s].mean()
    out = {"n": len(u), "n_structures": int(len(np.unique(st))), "sd_total": float(u.std(ddof=1)),
           "sd_within_structure": float(resid.std(ddof=1)),
           "share_of_variance_between_structures": float(1 - resid.var() / u.var())}
    for name, g in (("template", tpl), ("unionfind_group", grp), ("family_after_structure", fam)):
        icc, K, n0, mw = anova_icc(resid, g)
        boots = []
        ug = np.unique(g)
        idx_by = {k: np.where(g == k)[0] for k in ug}
        for _ in range(1000):
            pick = rng.choice(ug, size=len(ug))
            ii = np.concatenate([idx_by[k] for k in pick])
            gg = np.concatenate([[j] * len(idx_by[k]) for j, k in enumerate(pick)])
            if len(np.unique(gg)) > 2:
                try:
                    boots.append(anova_icc(resid[ii], gg)[0])
                except Exception:  # noqa: BLE001
                    pass
        out[name] = {"icc": icc, "K": K, "mean_size_n0": n0, "m_w": mw, "deff_implied": 1 + (mw - 1) * icc,
                     "icc_boot_95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]}
    # sample-size note: dev/val has ~23 scenarios per structure; ICC CIs are wide and are NOT used to shrink the planning DEFF
    return out, resid, st


# ------------------------------------------------------------------------------------------ simulation
def layout(gps, rng):
    """sizes[s] = array of group sizes summing to N_PER for each of S structures."""
    out = []
    for _ in range(S):
        base = N_PER / gps
        lo, hi = max(1, int(base * 0.6)), int(np.ceil(base * 1.4))
        s = rng.integers(lo, hi + 1, size=gps)
        while s.sum() != N_PER:
            i = rng.integers(0, gps)
            if s.sum() < N_PER and s[i] < hi + 3:
                s[i] += 1
            elif s.sum() > N_PER and s[i] > 1:
                s[i] -= 1
        out.append(s)
    return out


def gen(sizes, rg, rf, vals, cum, shifts, fam_of_group, rng):
    """returns v (N,), gidx (N,) global group index, sidx (N,) structure index"""
    Gtot = sum(len(x) for x in sizes)
    Gz = rng.normal(size=Gtot)
    Fz = rng.normal(size=16)
    v, gi, si = [], [], []
    g0 = 0
    for s, szs in enumerate(sizes):
        for j, m in enumerate(szs):
            z = np.sqrt(rg) * Gz[g0 + j] + np.sqrt(rf) * Fz[fam_of_group[g0 + j]] + np.sqrt(max(1 - rg - rf, 1e-9)) * rng.normal(size=m)
            z = z / np.sqrt(rg + rf + max(1 - rg - rf, 1e-9))
            idx = np.minimum(np.searchsorted(cum, sps.norm.cdf(z)), len(vals) - 1)
            v.append(vals[idx] + shifts[s])
            gi += [g0 + j] * m
            si += [s] * m
        g0 += len(szs)
    return np.concatenate(v), np.array(gi), np.array(si)


def strat_boot_reject(v, gi, si, rng, B):
    """one-sided p<0.025 for theta>0; stratified ratio estimator, equal weights W_s=n_s/N, stratified cluster bootstrap-t."""
    Ns = np.bincount(si, minlength=S).astype(float)
    W = Ns / Ns.sum()
    # per structure group sums
    ug, inv = np.unique(gi, return_inverse=True)
    Sg = np.bincount(inv, weights=v)
    ng = np.bincount(inv).astype(float)
    sg = np.zeros(len(ug), int)
    sg[inv] = si
    members = [np.where(sg == s)[0] for s in range(S)]
    th_s = np.array([Sg[m].sum() / ng[m].sum() for m in members])
    theta = float(np.sum(W * th_s))
    var = 0.0
    for s, m in enumerate(members):
        G = len(m)
        r = Sg[m] - th_s[s] * ng[m]
        var += W[s] ** 2 * (G / (G - 1)) * np.sum(r ** 2) / ng[m].sum() ** 2
    se = np.sqrt(var)
    if se == 0:
        return False
    thb = np.zeros(B)
    varb = np.zeros(B)
    for s, m in enumerate(members):
        G = len(m)
        pick = m[rng.integers(0, G, size=(B, G))]
        Sb, nb = Sg[pick], ng[pick]
        ths = Sb.sum(1) / nb.sum(1)
        thb += W[s] * ths
        rb = Sb - ths[:, None] * nb
        varb += W[s] ** 2 * (G / (G - 1)) * np.sum(rb ** 2, axis=1) / nb.sum(1) ** 2
    seb = np.sqrt(varb)
    ok = seb > 0
    t = (thb[ok] - theta) / seb[ok]
    return (1 + np.sum(t >= theta / se)) / (ok.sum() + 1) < 0.025


def realised_deff_within(sizes, rg, rf, vals, cum, shifts, fam_of_group, rng, reps=30):
    out = []
    for _ in range(reps):
        v, gi, si = gen(sizes, rg, rf, vals, cum, shifts, fam_of_group, rng)
        r = v.copy()
        for s in range(S):
            r[si == s] -= r[si == s].mean()
        icc, K, n0, mw = anova_icc(r, gi)
        out.append(1 + (mw - 1) * icc)
    return float(np.mean(out))


def part_b(resid, st, rng):
    vals = np.sort(resid)
    cum = (np.arange(len(vals)) + 1.0) / len(vals)
    # fixed structure shifts: dev/val structure-mean deviations (cycled to 16), centred; they cancel in the stratified estimator
    sm = np.array([resid.mean()] * 1)
    dev = np.array([0.263 * x for x in np.linspace(-1.5, 1.5, S)])
    shifts = dev - dev.mean()
    res = []
    for gps, name in ((16, "16 groups/structure (~7.8 per group) = 256 groups"), (8, "8 groups/structure (~15.6) = 128 groups"),
                      (32, "32 groups/structure (~3.9) = 512 groups")):
        sizes = layout(gps, rng)
        fam_of_group = np.concatenate([np.arange(len(x)) % 16 for x in sizes])
        for rf in (0.0, 0.02, 0.05):
            for rg in (0.0, 0.03, 0.05, 0.10, 0.20, 0.30):
                if rg + rf >= 0.95:
                    continue
                if gps != 16 and rf > 0:
                    continue
                d = realised_deff_within(sizes, rg, rf, vals, cum, shifts, fam_of_group, rng)
                case = {"layout": name, "G_total": int(sum(len(x) for x in sizes)), "max_group": int(max(x.max() for x in sizes)),
                        "latent_within_group": rg, "latent_crossed_family_ignored": rf, "realised_within_deff": round(d, 3)}
                for mu in (0.0, 0.10):
                    rej = 0
                    for _ in range(R):
                        v, gi, si = gen(sizes, rg, rf, vals, cum, shifts, fam_of_group, rng)
                        rej += strat_boot_reject(v + mu, gi, si, rng, B)
                    case[f"reject_mu_{mu}"] = rej / R
                res.append(case)
                print(json.dumps(case), flush=True)
    return res


def part_c(sd_total, sd_within):
    """Random-structure reading (NOT adopted): SE of the mean over K=16 structure means = sd_between/sqrt(16); MDE_80 one-sided alpha .025."""
    z = sps.norm.ppf(0.975) + sps.norm.ppf(0.8)
    out = {}
    for sd_b in (0.263, 0.35):
        se = sd_b / np.sqrt(16)
        out[f"sd_between_structures_{sd_b}"] = {"se": float(se), "mde80_one_sided": float(z * se),
                                                  "note": "independent of N; only more structures reduce it"}
    out["fixed_strata_se_no_clustering_N2000"] = float(sd_within / np.sqrt(2000))
    return out


def main():
    rng = np.random.default_rng(SEED)
    rows = U.load_rows()
    a, resid, st = part_a(rows, rng)
    print(json.dumps(a, indent=1), flush=True)
    b = part_b(resid, st, rng)
    c = part_c(a["sd_total"], a["sd_within_structure"])
    OUT.write_text(json.dumps({"purpose": "fixed-strata hierarchical power; non-confirmatory marginals from dev/val", "seed": SEED,
                               "R": R, "B": B, "N": S * N_PER, "A_devval_dependence": a, "B_mc": b, "C_random_structure_limitation": c},
                              indent=1))


if __name__ == "__main__":
    main()
