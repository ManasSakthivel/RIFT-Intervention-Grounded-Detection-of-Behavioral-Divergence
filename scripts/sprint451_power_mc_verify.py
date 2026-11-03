#!/usr/bin/env python3
"""Sprint 4.5.1 (lead) independent Monte-Carlo check of H1 size/power with REALISED design effects.

Why this exists: scripts/sprint451_power_analysis.py reports the same realised DEFF (1.58) for target DEFF 1.5, 2.0 and 3.0,
i.e. its latent-correlation calibration saturates, and its claim that "DEFF is capped near 1.58-2.64" is not supported.
This script calibrates the Gaussian-copula latent correlation by bisection to hit a target *realised* DEFF
(DEFF = 1 + (m_w - 1) * ICC_anova with m_w = sum n_g^2 / N) and then estimates, for the studentised cluster bootstrap-t of SAP 3,
the size (mu = 0) and power (mu = +0.10) at N = 2000.

Inputs: dev/val V3 utility vector at lambda = 2, gamma = 1 (N = 252, non-confirmatory marginal distribution only).
No confirmatory data. No held-out access. Seed 4516.   Output: artifacts/sprint4_5_1/power/power_mc_verify.json
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

SEED = 4516
N = 2000
R = 1000
B = 199
OUT = REPO / "artifacts" / "sprint4_5_1" / "power" / "power_mc_verify.json"


def sizes_for(K, N, rng, maxsize=None):
    """Unequal cluster sizes with mean N/K (truncated geometric-like), summing to N."""
    s = rng.geometric(1.0 / (N / K), size=K).astype(int)
    if maxsize:
        s = np.minimum(s, maxsize)
    s = np.maximum(s, 1)
    while s.sum() != N:
        i = rng.integers(0, K)
        if s.sum() < N:
            s[i] += 1
        elif s[i] > 1:
            s[i] -= 1
    return s


def draw_vals(sizes, r, vals, cum, rng):
    N = sizes.sum()
    g = np.repeat(np.arange(len(sizes)), sizes)
    X = rng.normal(size=len(sizes))[g]
    Y = rng.normal(size=N)
    Z = np.sqrt(r) * X + np.sqrt(1 - r) * Y
    idx = np.minimum(np.searchsorted(cum, sps.norm.cdf(Z)), len(vals) - 1)
    return vals[idx], g


def realised_deff(sizes, r, vals, cum, rng, reps=40):
    out = []
    for _ in range(reps):
        v, g = draw_vals(sizes, r, vals, cum, rng)
        K = len(sizes)
        N = len(v)
        gm = v.mean()
        cs = np.bincount(g, weights=v, minlength=K)
        ssb = np.sum(cs ** 2 / sizes) - N * gm ** 2
        ssw = np.sum(v ** 2) - np.sum(cs ** 2 / sizes)
        n0 = (N - np.sum(sizes ** 2) / N) / (K - 1)
        msb = ssb / (K - 1)
        msw = ssw / (N - K)
        rho = (msb - msw) / (msb + (n0 - 1) * msw)
        mw = np.sum(sizes ** 2) / N
        out.append(1 + (mw - 1) * rho)
    return float(np.mean(out))


def calibrate(sizes, target, vals, cum, rng):
    lo, hi = 0.0, 0.999
    for _ in range(14):
        mid = (lo + hi) / 2
        d = realised_deff(sizes, mid, vals, cum, rng)
        if d < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2, realised_deff(sizes, (lo + hi) / 2, vals, cum, rng, 80)


def boot_t_reject(v, g, K, rng, B):
    """One-sided studentised cluster bootstrap-t p < 0.025 (SAP 3)."""
    N = len(v)
    n = np.bincount(g, minlength=K).astype(float)
    S = np.bincount(g, weights=v, minlength=K)
    th = S.sum() / N
    se = np.sqrt(K / (K - 1) * np.sum((S - th * n) ** 2)) / N
    if se == 0:
        return False
    ix = rng.integers(0, K, size=(B, K))
    Sb, nb = S[ix], n[ix]
    thb = Sb.sum(1) / nb.sum(1)
    seb = np.sqrt(K / (K - 1) * np.sum((Sb - thb[:, None] * nb) ** 2, axis=1)) / nb.sum(1)
    ok = seb > 0
    t = (thb[ok] - th) / seb[ok]
    p = (1 + np.sum(t >= th / se)) / (ok.sum() + 1)
    return p < 0.025


def main():
    rng = np.random.default_rng(SEED)
    rows = U.load_rows()
    u = np.sort(U.util(rows, "V3-FULL", 2.0, 0.05))
    cum = (np.arange(len(u)) + 1.0) / len(u)
    vals0 = u - u.mean()                          # centred: mu = 0
    res = {"purpose": "independent MC check of H1 with calibrated REALISED DEFF (non-confirmatory marginal from dev/val)",
           "seed": SEED, "N": N, "R": R, "B": B, "marginal_sd": float(u.std(ddof=1)), "cases": []}
    designs = [("K250_mean8_max25", 250, 25), ("K100_mean20_max50", 100, 50), ("K16_structures_mean125", 16, None)]
    for name, K, mx in designs:
        sizes = sizes_for(K, N, rng, mx)
        sizes = sizes if sizes.sum() == N else sizes
        for target in (1.5, 2.0, 3.0, 6.0):
            r, dreal = calibrate(sizes, target, vals0, cum, rng)
            case = {"design": name, "K": int(K), "max_size": int(sizes.max()), "m_w": float(np.sum(sizes ** 2) / N),
                    "target_deff": target, "latent_r": float(r), "realised_deff": dreal}
            for mu in (0.0, 0.10):
                rej = 0
                for _ in range(R):
                    v, g = draw_vals(sizes, r, vals0, cum, rng)
                    rej += boot_t_reject(v + mu, g, K, rng, B)
                case[f"reject_mu_{mu}"] = rej / R
            case["mc_se_at_0.025"] = float(np.sqrt(0.025 * 0.975 / R))
            res["cases"].append(case)
            print(json.dumps(case), flush=True)
    OUT.write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
