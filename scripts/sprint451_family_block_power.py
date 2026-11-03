#!/usr/bin/env python3
"""Sprint 4.5.1 (lead) size/power of a FAMILY-BLOCK cluster bootstrap-t for the fixed-strata design.   Non-confirmatory.

Why: stratified_power.py showed the template-within-structure bootstrap-t is anti-conservative if a latent fault-family effect
shared ACROSS structures (latent crossed family ICC rf) is present and the target is a population of families (size 0.05-0.2 at
rf 0.02-0.05).  This script evaluates the alternative inference that resamples the 16 family columns (each family cluster holds
its 16 templates, one per structure), with the 16 structure weights W_s = n_s/N held fixed.

Same data-generating model, layout (16 templates/structure, ~7.8 per template, 256 templates), empirical dev/val utility
marginal and seed discipline as scripts/sprint451_stratified_power.py.  R reduced to 400 and B = 199 here.
Seed 4519.  Output: artifacts/sprint4_5_1/power/family_block_power.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts import sprint451_stratified_power as SP  # noqa: E402
from scripts import sprint451_utility_sensitivity as U  # noqa: E402

SEED = 4519
R = 400
B = 199
OUT = REPO / "artifacts" / "sprint4_5_1" / "power" / "family_block_power.json"
S = SP.S


def family_block_reject(v, gi, si, fam_of_group_global, rng, B):
    """one-sided p < 0.025; clusters = families (16), structure weights fixed at n_s/N, bootstrap-t."""
    Ns = np.bincount(si, minlength=S).astype(float)
    W = Ns / Ns.sum()
    fam = fam_of_group_global[gi]
    # cell sums S_{s,f}, n_{s,f}
    Ssf = np.zeros((S, 16))
    nsf = np.zeros((S, 16))
    np.add.at(Ssf, (si, fam), v)
    np.add.at(nsf, (si, fam), 1.0)
    th_s = Ssf.sum(1) / nsf.sum(1)
    theta = float(np.sum(W * th_s))
    r_f = np.sum(W[:, None] * (Ssf - th_s[:, None] * nsf) / Ns[:, None], axis=0)
    K = 16
    se = np.sqrt(K / (K - 1) * np.sum(r_f ** 2))
    if se == 0:
        return False
    pick = rng.integers(0, 16, size=(B, 16))
    Sb = Ssf[:, pick]          # (S, B, 16)
    nb = nsf[:, pick]
    ths = Sb.sum(2) / nb.sum(2)                 # (S, B)
    thb = np.sum(W[:, None] * ths, axis=0)
    rb = np.sum(W[:, None, None] * (Sb - ths[:, :, None] * nb) / Ns[:, None, None], axis=0)   # (B, 16)
    seb = np.sqrt(K / (K - 1) * np.sum(rb ** 2, axis=1))
    ok = seb > 0
    t = (thb[ok] - theta) / seb[ok]
    return (1 + np.sum(t >= theta / se)) / (ok.sum() + 1) < 0.025


def main():
    rng = np.random.default_rng(SEED)
    rows = U.load_rows()
    _, resid, st = SP.part_a(rows, rng)
    vals = np.sort(resid)
    cum = (np.arange(len(vals)) + 1.0) / len(vals)
    dev = np.array([0.263 * x for x in np.linspace(-1.5, 1.5, S)])
    shifts = dev - dev.mean()
    sizes = SP.layout(16, rng)
    fam_of_group = np.concatenate([np.arange(len(x)) % 16 for x in sizes])
    res = []
    for rf in (0.0, 0.02, 0.05):
        for rg in (0.0, 0.05, 0.10, 0.20):
            case = {"layout": "16 templates/structure = 256", "latent_within_group": rg, "latent_crossed_family": rf}
            for mu in (0.0, 0.10):
                rej_f = rej_t = 0
                for _ in range(R):
                    v, gi, si = SP.gen(sizes, rg, rf, vals, cum, shifts, fam_of_group, rng)
                    rej_f += family_block_reject(v + mu, gi, si, fam_of_group, rng, B)
                    rej_t += SP.strat_boot_reject(v + mu, gi, si, rng, B)
                case[f"family_block_reject_mu_{mu}"] = rej_f / R
                case[f"template_strat_reject_mu_{mu}"] = rej_t / R
            res.append(case)
            print(json.dumps(case), flush=True)
    OUT.write_text(json.dumps({"purpose": "family-block bootstrap-t size/power (non-confirmatory)", "seed": SEED, "R": R, "B": B,
                               "cases": res}, indent=1))


if __name__ == "__main__":
    main()
