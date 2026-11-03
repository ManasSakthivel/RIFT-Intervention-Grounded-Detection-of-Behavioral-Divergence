#!/usr/bin/env python3
"""Sprint 4.5.1 (lead): SD-stress for the fixed-strata power (scales the empirical structure-demeaned utility distribution by 1.25).
Non-confirmatory.  Seed 4520.  R=400, B=199.  Output artifacts/sprint4_5_1/power/stratified_power_sd125.json"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts import sprint451_stratified_power as SP  # noqa: E402
from scripts import sprint451_utility_sensitivity as U  # noqa: E402
SEED, R, B, SCALE = 4520, 400, 199, 1.25
OUT = REPO / "artifacts" / "sprint4_5_1" / "power" / "stratified_power_sd125.json"
rng = np.random.default_rng(SEED)
rows = U.load_rows()
_, resid, st = SP.part_a(rows, rng)
vals = np.sort(resid) * SCALE
cum = (np.arange(len(vals)) + 1.0) / len(vals)
dev = np.array([0.263 * x for x in np.linspace(-1.5, 1.5, SP.S)]); shifts = dev - dev.mean()
sizes = SP.layout(16, rng)
fam = np.concatenate([np.arange(len(x)) % 16 for x in sizes])
res = []
for rg in (0.0, 0.05, 0.10, 0.20):
    case = {"scale": SCALE, "sd_within": float(vals.std(ddof=1)), "latent_within_group": rg,
            "realised_within_deff": round(SP.realised_deff_within(sizes, rg, 0.0, vals, cum, shifts, fam, rng), 3)}
    for mu in (0.0, 0.10):
        case[f"reject_mu_{mu}"] = sum(SP.strat_boot_reject(*(lambda g: (g[0] + mu, g[1], g[2]))(SP.gen(sizes, rg, 0.0, vals, cum, shifts, fam, rng)), rng, B) for _ in range(R)) / R
    res.append(case); print(json.dumps(case), flush=True)
OUT.write_text(json.dumps({"seed": SEED, "R": R, "B": B, "cases": res}, indent=1))
