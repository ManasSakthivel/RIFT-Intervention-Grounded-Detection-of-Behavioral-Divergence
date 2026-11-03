#!/usr/bin/env python3
"""Sprint 4.5.0 PRE-REGISTRATION AUDIT, part 2 (development evidence only; NOT the confirmatory experiment).

Same inputs and restrictions as sprint450_prereg_audit.py (dev/val labels + saved dev/val method records only; never the
held-out data; no scenario generation; no method execution).  Adds:
  A  stratum-level utilities, break-even prevalence, post-stratified estimator
  B  alternative ("operational") unsafe definition
  C  union-find group clustering (template-or-topology connected components)
  D  (lambda, kappa) significance map for V3-AA and V3-V2 on dev/val (descriptive)
  E  generator capacity: how many design cells/templates the FROZEN generator has left (analytic, from code; no data read)
  F  Monte-Carlo operating characteristics of candidate tests on the empirical, skewed utility distribution
  G  power of H1..H4 at candidate N under Holm / gatekeeping, with shrunk dev/val effects
  H  CID unit cost (timing of one compute_cid call)
Output: artifacts/sprint4_5_0/prereg_audit/audit_part2.json
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import stats as sps

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
spec = importlib.util.spec_from_file_location("aud1", REPO / "scripts" / "sprint450_prereg_audit.py")
aud = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aud)

SEED = 4502
OUT = REPO / "artifacts" / "sprint4_5_0" / "prereg_audit"
ZB80, ZB90 = 0.841621, 1.281552


def boot_cluster(vals_by_cluster_sum, cnt, B, rng, statfn):
    K = len(cnt)
    dr = rng.integers(0, K, size=(B, K))
    return statfn(dr)


def main():
    rows = aud.load_rows()
    labs = {**aud.load_labels("dev"), **aud.load_labels("val")}
    N = len(rows)
    att = np.array([r["expected"] == "ATTRIBUTE" for r in rows])
    pi = att.mean()
    cl = aud.cluster_ids(rows, "template")
    keys = sorted(set(cl))
    idx = {k: [] for k in keys}
    for i, c in enumerate(cl):
        idx[c].append(i)
    K = len(keys)
    rng = np.random.default_rng(SEED)
    B = 4000
    draws = rng.integers(0, K, size=(B, K))
    out = {"purpose": "dev/val audit part 2; NOT confirmatory", "N": N, "pi": float(pi), "K_template_clusters": K}

    def cl_sum(x):
        return np.array([x[idx[k]].sum() for k in keys])

    def vecs(m):
        c, u, a, n = aud.vec(rows, m)
        return c, u, a, n

    # ------------------------------------------------------------------ A. strata, break-even prevalence
    A = {}
    for m in ("V3-FULL", "RIFT-FULL-V2"):
        c, u, a, n = vecs(m)
        for lam, kap in ((2.0, 0.05), (1.0, 0.05), (2.0, 0.0), (4.0, 0.05)):
            d = aud.util(c, u, n, lam, kap)
            UA, UR = float(d[att].mean()), float(d[~att].mean())
            # break-even prevalence pi* : pi*UA + (1-pi*)UR = 0  (only exists if UA>0>UR)
            pistar = (-UR / (UA - UR)) if (UA - UR) != 0 else None
            sA, sR = cl_sum(np.where(att, d, 0.0)), cl_sum(np.where(~att, d, 0.0))
            nA, nR = cl_sum(att.astype(float)), cl_sum((~att).astype(float))
            bUA = sA[draws].sum(1) / np.maximum(nA[draws].sum(1), 1)
            bUR = sR[draws].sum(1) / np.maximum(nR[draws].sum(1), 1)
            ps = {}
            for pr in (0.2, 0.4, 0.6, 0.8):
                est = pr * bUA + (1 - pr) * bUR
                ps[str(pr)] = {"point": pr * UA + (1 - pr) * UR, "ci95": [float(x) for x in np.percentile(est, [2.5, 97.5])]}
            A[f"{m}|lam={lam},kap={kap}"] = {"U_ATTRIBUTE_stratum": UA, "U_ABSTAIN_REQUIRED_stratum": UR,
                                              "break_even_prevalence": pistar, "post_stratified_at_pi_ref": ps}
    out["A_strata_and_post_stratification"] = A

    # ------------------------------------------------------------------ B. alternative unsafe definition
    B_ = {}
    for m in ("V3-FULL", "RIFT-FULL-V2"):
        wrong = np.array([float(r["m"][m][0]["answered"] and (r["m"][m][0]["top1"] not in labs[r["sid"]]["ground_truth"]["roots"]))
                          for r in rows])
        c, u, a, n = vecs(m)
        B_[m] = {"S_strict": int(u.sum()), "S_operational_wrong_named_service": int(wrong.sum()),
                 "lambda_star_kappa0_operational": float(c.sum() / wrong.sum()),
                 "lambda_star_kappa0.05_operational": float((c.sum() - 0.05 * n.sum()) / wrong.sum()),
                 "U_operational": {f"lam={l}": float((c - l * wrong - 0.05 * n).mean()) for l in (0.5, 1.0, 2.0, 4.0)}}
    out["B_operational_unsafe_definition"] = B_

    # ------------------------------------------------------------------ C. union-find group clustering
    from src.rift.scenarios.independence import topology_hash
    from src.rift.scenarios.splitter import build_groups
    grp = build_groups(labs, [lambda s: ("t", s["template_id"]), lambda s: ("topo", topology_hash(s))])
    g_ids = [grp[r["sid"]] for r in rows]
    c, u, a, n = vecs("V3-FULL")
    d = aud.util(c, u, n, 2.0, 0.05)
    r_ = aud.icc_anova(d, g_ids)
    r_["deff_empirical"] = aud.deff_empirical(d, g_ids)
    out["C_union_find_group_clustering"] = {"n_groups": len(set(g_ids)), **r_}
    # also cluster by topology hash only
    th = [topology_hash(labs[r["sid"]]) for r in rows]
    r2 = aud.icc_anova(d, th)
    r2["deff_empirical"] = aud.deff_empirical(d, th)
    out["C_topology_hash_clustering"] = {"n_topologies": len(set(th)), **r2}

    # ------------------------------------------------------------------ D. significance map (descriptive)
    LAMS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]
    KAPS = [0.0, 0.025, 0.05, 0.10]
    mp = {}
    c3, u3, a3, n3 = vecs("V3-FULL")
    c2, u2, a2, n2 = vecs("RIFT-FULL-V2")
    for lam in LAMS:
        for kap in KAPS:
            d3 = aud.util(c3, u3, n3, lam, kap)
            d2 = aud.util(c2, u2, n2, lam, kap)
            m1, ci1, _ = aud.cluster_boot_mean(d3, cl, B=2000, seed=SEED)
            m2, ci2, _ = aud.cluster_boot_mean(d3 - d2, cl, B=2000, seed=SEED)
            mp[f"lam={lam},kap={kap}"] = {"V3_minus_AA": m1, "V3_minus_AA_ci95": ci1, "V3_minus_V2": m2, "V3_minus_V2_ci95": ci2}
    out["D_lambda_kappa_map_dev_val_descriptive"] = mp

    # ------------------------------------------------------------------ E. generator capacity (analytic, from code only)
    from src.rift.scenarios import generator_v2 as g
    cells = Counter(g.cell_split(s, f) for s in g.STRUCTURES for f in g.FAMILIES)
    out["E_generator_capacity_from_code"] = {
        "n_structures": len(g.STRUCTURES), "n_families": len(g.FAMILIES), "n_templates_total": len(g.STRUCTURES) * len(g.FAMILIES),
        "templates_assigned_by_cell_split": dict(cells),
        "unassigned_templates": len(g.STRUCTURES) * len(g.FAMILIES) - sum(cells.values()),
        "size_bands_used": {k: list(v) for k, v in g._SIZE_BAND.items()},
        "split_labels_supported_by_build_scenario": sorted(g._SIZE_BAND),
        "note": "template_id=structure|family; every one of the 176 templates is already consumed by dev/val/held_out; "
                "build_scenario() raises KeyError for any split label other than dev/val/held_out (verified)."}

    # ------------------------------------------------------------------ F. operating characteristics of tests (skewed D)
    rng = np.random.default_rng(SEED + 1)
    d0 = aud.util(c3, u3, n3, 2.0, 0.05)
    tmpl = np.array([hash(x) for x in cl])
    sd_emp = float(d0.std(ddof=1))
    centred = d0 - d0.mean()
    skew = float(sps.skew(d0))
    Nn, R, nperm = 1200, 2000, 1000
    res = {"empirical_sd": sd_emp, "empirical_skewness": skew, "N": Nn, "reps": R}
    for shift_name, shift in (("null", 0.0), ("mu=+0.05", 0.05), ("mu=+0.10", 0.10)):
        rej_t = rej_sf = rej_bt = 0
        for _ in range(R):
            x = rng.choice(centred, size=Nn, replace=True) + shift
            m_ = x.mean(); se = x.std(ddof=1) / math.sqrt(Nn)
            p_t = 1 - sps.norm.cdf(m_ / se)                                           # one-sided t (normal approx)
            rej_t += p_t < 0.025
            sg = rng.choice((-1.0, 1.0), size=(nperm, Nn))                              # sign-flip, one-sided
            p_sf = (1 + int(((sg * x).mean(1) >= m_).sum())) / (nperm + 1)
            rej_sf += p_sf < 0.025
            # null-centred bootstrap-t (scenario-level here; cluster version used in the SAP)
            xc = x - m_
            bs = rng.choice(xc, size=(nperm, Nn), replace=True)
            tb = bs.mean(1) / (bs.std(1, ddof=1) / math.sqrt(Nn))
            p_bt = (1 + int((tb >= m_ / se).sum())) / (nperm + 1)
            rej_bt += p_bt < 0.025
        res[shift_name] = {"t_test": rej_t / R, "sign_flip": rej_sf / R, "bootstrap_t": rej_bt / R}
    out["F_test_operating_characteristics_skewed_utility"] = res

    # ------------------------------------------------------------------ G. power of H1..H4 at candidate N
    def pw_mean(mu, sd, Nn, deff, alpha_tail):
        z = sps.norm.ppf(1 - alpha_tail)
        return float(1 - sps.norm.cdf(z - mu / (sd * math.sqrt(deff / Nn))))

    sd1 = float(d0.std(ddof=1))
    d32 = aud.util(c3, u3, n3, 2.0, 0.05) - aud.util(c2, u2, n2, 2.0, 0.05)
    sd2 = float(d32.std(ddof=1))
    mu2 = float(d32.mean())
    ov3, ov2 = 15, 46          # unsafe: only V3 unsafe / only V2 unsafe (dev+val)
    p4a, p4b = 19, 10          # P1: only V3 / only V2 correct (dev+val, ATTRIBUTE n=99)

    def pw_mcnemar(n_pairs, p_disc, p_plus, alpha_tail):
        """approx power of one-sided exact-ish McNemar: normal approx on discordant counts.
        p_plus = P(discordant favours A | discordant)."""
        nd = n_pairs * p_disc
        z = sps.norm.ppf(1 - alpha_tail)
        mu = (2 * p_plus - 1) * math.sqrt(nd)
        sdv = 2 * math.sqrt(p_plus * (1 - p_plus))
        return float(1 - sps.norm.cdf((z - mu) / sdv)) if sdv > 0 else float("nan")

    G = {"sd_V3_utility": sd1, "sd_V3_minus_V2_utility": sd2, "dev_val_mean_V3_minus_V2": mu2}
    for Nn in (800, 1200, 1600, 2000):
        e = {}
        for deff in (1.0, 1.5, 2.0):
            e[f"deff={deff}"] = {
                "H1_mu=0.10_gate_alpha1sided0.025": pw_mean(0.10, sd1, Nn, deff, 0.025),
                "H1_mu=0.05_gate": pw_mean(0.05, sd1, Nn, deff, 0.025),
                "H2_mu=full_dev_val_(%.3f)_holm_m3(alpha=.00833)" % mu2: pw_mean(mu2, sd2, Nn, deff, 0.05 / 3 / 2),
                "H2_mu=half_dev_val_holm_m3": pw_mean(mu2 / 2, sd2, Nn, deff, 0.05 / 3 / 2),
                "H2_mu=0.10_holm_m3": pw_mean(0.10, sd2, Nn, deff, 0.05 / 3 / 2)}
        # H3 (unsafe, paired binary, all scenarios) and H4 (P1, ATTRIBUTE only)
        pd3 = (ov3 + ov2) / 252
        pd4 = (p4a + p4b) / 99
        for shrink in (1.0, 0.5):
            pp3 = 0.5 + (ov2 - ov3) / (ov2 + ov3) / 2 * shrink
            pp4 = 0.5 + (p4a - p4b) / (p4a + p4b) / 2 * shrink
            e[f"H3_shrink={shrink}_holm_m3"] = pw_mcnemar(Nn, pd3, pp3, 0.05 / 3 / 2)
            e[f"H4_shrink={shrink}_holm_m3_NATTR={int(round(0.4 * Nn))}"] = pw_mcnemar(0.4 * Nn, pd4, pp4, 0.05 / 3 / 2)
        G[f"N={Nn}"] = e
    # N required, closed form, for H1 gate
    def n_req(sd, delta, deff, alpha_tail, zb):
        return int(math.ceil(((sps.norm.ppf(1 - alpha_tail) + zb) * sd / delta) ** 2 * deff))
    G["N_required_H1_gate_alpha1sided0.025"] = {f"delta={dl},deff={df},power={pw}": n_req(sd1, dl, df, 0.025, ZB80 if pw == 0.8 else ZB90)
                                                 for dl in (0.05, 0.075, 0.10, 0.15) for df in (1.0, 1.5, 2.0) for pw in (0.8, 0.9)}
    G["N_required_H1_if_Holm_m4_alpha1sided0.00625"] = {f"delta=0.10,deff={df},power=0.8": n_req(sd1, 0.10, df, 0.00625, ZB80) for df in (1.0, 1.5, 2.0)}
    G["expected_CI_halfwidth_V3_minus_AA"] = {f"N={Nn},deff={df}": float(1.959964 * sd1 * math.sqrt(df / Nn))
                                              for Nn in (800, 1200, 1600) for df in (1.0, 1.5)}
    out["G_power"] = G

    # prior-predictive: P(H1 rejected | truth ~ dev/val empirical) via cluster bootstrap of dev/val means, at several lambda
    pp = {}
    for lam in (0.5, 0.75, 1.0, 2.0):
        d_ = aud.util(c3, u3, n3, lam, 0.05)
        s_ = cl_sum(d_)
        cnt = cl_sum(np.ones(N))
        est = s_[draws].sum(1) / cnt[draws].sum(1)
        pp[f"lam={lam},kap=0.05"] = {"P(bootstrap_mean_U>0)": float((est > 0).mean()), "P(bootstrap_mean_U>=0.10)": float((est >= 0.10).mean()),
                                     "bootstrap_mean_ci95": [float(x) for x in np.percentile(est, [2.5, 97.5])]}
    out["G_prior_predictive_from_dev_val_bootstrap"] = pp

    # ------------------------------------------------------------------ H. CID unit cost
    import warnings
    warnings.filterwarnings("ignore")
    from src.rift.cid.cid import compute_cid
    r = np.random.default_rng(1)
    a, b = r.normal(100, 8, 30), r.normal(100, 8, 30)
    t0 = time.perf_counter()
    for i in range(20):
        compute_cid(a, b, "x", "y", 0.0, n_bootstrap=100, n_permutations=1000, seed=i)
    out["H_cid_cost"] = {"seconds_per_compute_cid_n30_perm1000_boot100": (time.perf_counter() - t0) / 20}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "audit_part2.json").write_text(json.dumps(out, indent=1, default=float))
    print("written", OUT / "audit_part2.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
