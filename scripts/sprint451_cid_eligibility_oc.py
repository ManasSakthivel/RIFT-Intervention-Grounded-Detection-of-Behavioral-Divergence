#!/usr/bin/env python3
"""Sprint 4.5.1 (lead): exact operating characteristics of the Phase A eligibility rule (CID design §6) versus the rule it replaces.

Pure binomial arithmetic.  No data, no simulation, no method run.   Output: artifacts/sprint4_5_1/cid/eligibility_oc.json
Replaced rule (Sprint 4.5.0 draft):  every in-domain null cell must have p_hat <= 0.070 AND Wilson-95 upper <= 0.080, and any rate within
2 SE of a threshold is 'borderline' and therefore NOT eligible.
Replacement rule (Sprint 4.5.1):  one exact cut-off per cell type, k <= K_MAX, chosen so that a perfectly calibrated estimator
(true size 0.05) is eligible with probability >= 0.99 over ALL its null cells, and an estimator with true size 0.10 fails any single cell with probability >= 0.99.
"""
import json
from pathlib import Path

import numpy as np
from scipy import stats

OUT = Path(__file__).resolve().parents[1] / "artifacts" / "sprint4_5_1" / "cid" / "eligibility_oc.json"
N_NULL_CELLS = 96            # d = 0 cells (reconciled; includes out-of-domain cells where the gated rule is used)
N_NULL_MIX = 2               # M1, M2 at d = 0


def wilson_upper(k, n, z=1.96):
    p = k / n
    return (p + z * z / (2 * n) + z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


res = {"n_null_cells": N_NULL_CELLS, "R_cell": 2000, "R_mix": 10000}
# ---- old rule
R = 2000
se = lambda p: np.sqrt(p * (1 - p) / R)
old = {}
for p in (0.05, 0.055, 0.06):
    # borderline: p_hat within 2 SE of the 0.070 threshold  =>  p_hat > 0.07 - 2*SE(p_hat)  (SE evaluated at 0.07 as the checker would at the threshold)
    thr = 0.07 - 2 * se(0.07)
    kb = int(np.floor(thr * R))
    p_cell_borderline = float(stats.binom.sf(kb, R, p))
    # Wilson upper <= 0.080  <=>  k <= kw
    kw = max(k for k in range(0, 400) if wilson_upper(k, R) <= 0.080)
    p_cell_wilson = float(stats.binom.sf(kw, R, p))
    old[str(p)] = {"borderline_threshold_phat": thr, "P_cell_flagged_borderline": p_cell_borderline,
                   "P_all_96_cells_pass_old_rule_incl_borderline": float((1 - p_cell_borderline) ** N_NULL_CELLS),
                   "P_ever_ineligible_old_rule": float(1 - (1 - p_cell_borderline) ** N_NULL_CELLS),
                   "wilson_cutoff_k": kw, "P_cell_fail_wilson": p_cell_wilson,
                   "P_ever_fail_wilson_96cells": float(1 - (1 - p_cell_wilson) ** N_NULL_CELLS)}
res["old_rule"] = old
# ---- new rule: choose k_max
def pick_k(Rn, n_cells):
    for k in range(int(0.05 * Rn), int(0.12 * Rn)):
        if 1 - (1 - stats.binom.sf(k, Rn, 0.05)) ** n_cells <= 0.01:
            return k
K2000 = pick_k(2000, N_NULL_CELLS)
K10000 = pick_k(10000, N_NULL_MIX)
new = {"K_MAX_cell_R2000": K2000, "phat_cutoff_cell": K2000 / 2000, "K_MAX_mixture_R10000": K10000, "phat_cutoff_mixture": K10000 / 10000, "table": {}}
for p in (0.04, 0.05, 0.055, 0.06, 0.065, 0.07, 0.08, 0.09, 0.10, 0.15):
    pc = float(stats.binom.sf(K2000, 2000, p))
    pm = float(stats.binom.sf(K10000, 10000, p))
    new["table"][str(p)] = {"P_single_cell_fails": pc, "P_ineligible_any_of_96_cells": float(1 - (1 - pc) ** N_NULL_CELLS),
                            "P_mixture_cell_fails": pm, "P_ineligible_any_of_2_mixture_cells": float(1 - (1 - pm) ** N_NULL_MIX)}
res["new_rule"] = new
OUT.write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
