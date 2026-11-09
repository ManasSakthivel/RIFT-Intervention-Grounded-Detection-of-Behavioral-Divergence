#!/usr/bin/env python3
"""FINAL / Agent 3: size, power and decision-rule simulation for the confirmatory inference module.   NON-CONFIRMATORY.

Uses ONLY the dev/val empirical marginal of the V3 utility (read-only, via scripts/sprint451_utility_sensitivity.load_rows,
which sha256-pins datasets/rift_v2/{dev,val}.json) and the generative model of scripts/sprint451_stratified_power.py.
It never opens the Sprint 4.3.0 held-out split, never runs any method and never generates scenarios.

What is new relative to Sprint 4.5.1: the production module src/rift/statistics/confirmatory_inference.py is exercised (not a
private re-implementation), and three decision rules are compared on identical simulated data:
    T = template-stratified bootstrap-t   (SAP 3 primary)
    F = family-block bootstrap-t          (SAP 3.1 sensitivity)
    H = hull of the two intervals         (proposed D19 option C: positive needs both, NEGATIVE-WORSE needs both)
Reported per cell: P(lo>0) [H1 rejected], P(hi<0) [NEGATIVE-WORSE], P(POSITIVE-USEFUL) [needs theta>=0.10 too].
Operational-lo is taken equal to strict lo (S_op <= S so U_op >= U; the PRE 10 guard is "practically unreachable").

Outputs (never overwrites Sprint 4.5.1 artifacts): artifacts/final_closure/statistical/{rule_comparison,n_scaling}.json
Seeds 4601 (main) / 4602 (N scaling) are simulation-only; the reserved confirmatory analysis seeds 4505/4506 are not used.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))
from scripts import sprint451_stratified_power as SP  # noqa: E402
from scripts import sprint451_utility_sensitivity as U  # noqa: E402
from src.rift.statistics.confirmatory_inference import FixedStrataDesign  # noqa: E402

OUT = REPO / "artifacts" / "final_closure" / "statistical"
S = SP.S


def marginal():
    rows = U.load_rows()
    u = U.util(rows, "V3-FULL", 2.0, 0.05)
    st = np.array([r["structure"] for r in rows])
    resid = u.copy()
    for s in np.unique(st):
        resid[st == s] -= u[st == s].mean()
    vals = np.sort(resid)
    cum = (np.arange(len(vals)) + 1.0) / len(vals)
    return vals, cum, float(resid.std(ddof=1))


def one_cell(sizes, design, fam_of_group, vals, cum, shifts, rg, rf, mus, R, B, rng):
    keys = ("T_reject", "F_reject", "H_reject", "T_neg", "F_neg", "H_neg",
            "T_useful", "F_useful", "H_useful", "F_wider_than_T")
    acc = {mu: {k: 0 for k in keys} for mu in mus}
    for _ in range(R):
        v, gi, si = SP.gen(sizes, rg, rf, vals, cum, shifts, fam_of_group, rng)
        for mu in mus:
            d = v + mu
            t = design.template_bootstrap_t(d, B=B, rng=rng)
            f = design.family_block_bootstrap_t(d, B=B, rng=rng)
            a = acc[mu]
            th = t.theta
            a["T_reject"] += t.lo > 0
            a["F_reject"] += f.lo > 0
            a["H_reject"] += min(t.lo, f.lo) > 0
            a["T_neg"] += t.hi < 0
            a["F_neg"] += f.hi < 0
            a["H_neg"] += max(t.hi, f.hi) < 0
            a["T_useful"] += (t.lo > 0) and th >= 0.10
            a["F_useful"] += (f.lo > 0) and th >= 0.10
            a["H_useful"] += (min(t.lo, f.lo) > 0) and th >= 0.10
            a["F_wider_than_T"] += (f.hi - f.lo) > (t.hi - t.lo)
    return {str(mu): {k: v / R for k, v in a.items()} for mu, a in acc.items()}


def make_design(gps, rng):
    sizes = SP.layout(gps, rng)
    fam_of_group = np.concatenate([np.arange(len(x)) % 16 for x in sizes])
    gi, si = [], []
    g0 = 0
    for s, szs in enumerate(sizes):
        for j, m in enumerate(szs):
            gi += [g0 + j] * int(m)
            si += [s] * int(m)
        g0 += len(szs)
    gi, si = np.array(gi), np.array(si)
    return sizes, fam_of_group, FixedStrataDesign(si, gi, fam_of_group[gi])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--R", type=int, default=500)
    ap.add_argument("--B", type=int, default=399)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--skip-scaling", action="store_true")
    a = ap.parse_args()
    R, B = (20, 99) if a.smoke else (a.R, a.B)
    OUT.mkdir(parents=True, exist_ok=True)
    tag = "_smoke" if a.smoke else ""
    vals, cum, sd_within = marginal()
    dev = np.array([0.263 * x for x in np.linspace(-1.5, 1.5, S)])
    shifts = dev - dev.mean()

    rng = np.random.default_rng(4601)
    SP.N_PER = 125
    sizes, fog, design = make_design(16, rng)
    mus = [0.0, 0.10, 0.15, -0.338]
    cases = []
    t0 = time.time()
    for rf in (0.0, 0.02, 0.05):
        for rg in (0.0, 0.05, 0.20):
            res = one_cell(sizes, design, fog, vals, cum, shifts, rg, rf, mus, R, B, rng)
            cases.append({"latent_within_group_rg": rg, "latent_crossed_family_rf": rf, "results_by_true_mu": res})
            print(json.dumps({"rg": rg, "rf": rf, "mu0": res["0.0"], "mu0.1": res["0.1"]}), flush=True)
    (OUT / f"rule_comparison{tag}.json").write_text(json.dumps({
        "purpose": "size/power/label-probability of T, F and hull decision rules via src/rift/statistics/confirmatory_inference.py "
                   "(NON-CONFIRMATORY, dev/val marginal only)",
        "seed": 4601, "R": R, "B": B, "N": 2000, "layout": "16 structures x 16 templates (family = template index mod 16)",
        "sd_within_structure_devval": sd_within, "mc_se_at_0.025": float(np.sqrt(0.025 * 0.975 / R)),
        "elapsed_s": round(time.time() - t0, 1), "cases": cases}, indent=1))

    if a.skip_scaling:
        return
    rng = np.random.default_rng(4602)
    scal = []
    for n_per in (63, 125, 250, 500):
        SP.N_PER = n_per
        sizes, fog, design = make_design(16, rng)
        for rf in (0.0, 0.05):
            res = one_cell(sizes, design, fog, vals, cum, shifts, 0.05, rf, [0.0, 0.10], R, B, rng)
            scal.append({"N": 16 * n_per, "rg": 0.05, "rf": rf, "results_by_true_mu": res})
            print(json.dumps({"N": 16 * n_per, "rf": rf, "mu0.1": res["0.1"]}), flush=True)
    (OUT / f"n_scaling{tag}.json").write_text(json.dumps({
        "purpose": "does N repair the family-level limitation? (NON-CONFIRMATORY)", "seed": 4602, "R": R, "B": B,
        "cases": scal}, indent=1))


if __name__ == "__main__":
    main()
