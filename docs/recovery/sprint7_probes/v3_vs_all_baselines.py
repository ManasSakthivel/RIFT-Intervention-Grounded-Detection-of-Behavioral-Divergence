#!/usr/bin/env python3
"""Sprint 7 / Workstream 6 probe: paired V3-FULL minus every other method, pooled dev+val (N=252).

Reuses the scoring and loaders of scripts/sprint451_utility_sensitivity.py (hash-pinned dev/val inputs; never opens
held-out data, never runs a method). Adds only a template-cluster percentile bootstrap of the paired utility difference
at lambda = 2, kappa = 0.05 (gamma = 1), strict and operational scoring, for EVERY method in that script.

Why: the circulated "7/8 baselines" wording needs a per-comparator basis. This is a Sprint 7 re-derivation, NOT a stored
Sprint 4.5.1 artifact. B = 4000, seed = 7 (the Sprint 4.5.1 grid used seed 4510); CIs therefore differ from
sensitivity_grid.md by bootstrap noise only.

Run from repo root:  PYTHONPATH=src:. python3.11 docs/recovery/sprint7_probes/v3_vs_all_baselines.py
"""
import importlib.util
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("s", REPO / "scripts" / "sprint451_utility_sensitivity.py")
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)

LAM, KAP, B, SEED = 2.0, 0.05, 4000, 7
rows = s.load_rows()
tpl = [r["template"] for r in rows]
keys = sorted(set(tpl))
pos = {k: i for i, k in enumerate(keys)}
ix = np.array([pos[t] for t in tpl])
K = len(keys)
draws = np.random.default_rng(SEED).integers(0, K, size=(B, K))
cnt = np.bincount(ix, minlength=K).astype(float)


def boot(d):
    sums = np.bincount(ix, weights=d, minlength=K)
    m = sums[draws].sum(1) / cnt[draws].sum(1)
    return float(d.mean()), np.percentile(m, [2.5, 97.5])


print(f"N={len(rows)} template clusters K={K} lambda={LAM} kappa={KAP} B={B} seed={SEED}")
for mode, op in (("strict", False), ("operational", True)):
    print(f"\n[{mode}] mean U (V3-FULL) = {s.util(rows, 'V3-FULL', LAM, KAP, op).mean():+.4f}; always-abstain U = +0.0000")
    v3 = s.util(rows, "V3-FULL", LAM, KAP, op)
    # always-abstain is U == 0 for every scenario
    m, ci = boot(v3 - 0.0)
    print(f"  V3 - ALWAYS-ABSTAIN{'':20s} {m:+.3f} [{ci[0]:+.3f},{ci[1]:+.3f}]")
    for name in s.METHODS:
        if name == "V3-FULL":
            continue
        m, ci = boot(v3 - s.util(rows, name, LAM, KAP, op))
        print(f"  V3 - {name:36s} {m:+.3f} [{ci[0]:+.3f},{ci[1]:+.3f}]")

# ---------------------------------------------------------------------------------------------------------------
# Headline "39.2% unsafe-attribution reduction" (V2 -> V3), pooled dev+val, strict unsafe. Sprint 7 re-derivation.
from math import comb

u2 = s.vec(rows, "RIFT-FULL-V2", "unsafe")
u3 = s.vec(rows, "V3-FULL", "unsafe")
print(f"\nunsafe V2={int(u2.sum())} V3={int(u3.sum())}  relative reduction={(u2.sum() - u3.sum()) / u2.sum():.4f}")
rel = []
for dr in draws:
    w = cnt[dr]
    a = np.bincount(ix, weights=u2, minlength=K)[dr].sum()
    b = np.bincount(ix, weights=u3, minlength=K)[dr].sum()
    rel.append((a - b) / a)
print("template-cluster 95% CI of relative reduction:", np.percentile(rel, [2.5, 97.5]).round(3))
d_only = int(((u2 == 1) & (u3 == 0)).sum())
e_only = int(((u2 == 0) & (u3 == 1)).sum())
n = d_only + e_only
p = min(1.0, 2 * sum(comb(n, k) for k in range(0, min(d_only, e_only) + 1)) / 2 ** n)
print(f"McNemar discordant: V2-only-unsafe={d_only} V3-only-unsafe={e_only} exact two-sided p={p:.4g} (unclustered, uncorrected)")
for sp in ("dev", "val"):
    m = np.array([r["split"] == sp for r in rows])
    print(f"  {sp}: V2 unsafe {int(u2[m].sum())} -> V3 {int(u3[m].sum())}")
cov2 = 1 - s.vec(rows, "RIFT-FULL-V2", "answered").mean() if False else s.vec(rows, "RIFT-FULL-V2", "answered").mean()
cov3 = s.vec(rows, "V3-FULL", "answered").mean()
print(f"coverage (answered rate) V2={cov2:.3f} V3={cov3:.3f}")

# B6 vs B7: aggregate-identical? scenario-level identical?
for key in ("answered", "correct", "unsafe"):
    same = int((s.vec(rows, "B6-RIFT-RANDOM", key) == s.vec(rows, "B7-RIFT-ONE-SHOT", key)).sum())
    print(f"B6 vs B7 identical on '{key}': {same}/{len(rows)}")
print("n_do identical:", int((s.vec(rows, "B6-RIFT-RANDOM", "n_do") == s.vec(rows, "B7-RIFT-ONE-SHOT", "n_do")).sum()), "/", len(rows))
