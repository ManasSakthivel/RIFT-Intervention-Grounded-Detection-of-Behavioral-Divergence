# Sprint 7 / Workstream 3 — Independent Scientific Results Reproduction

**Scope:** dev + val pooled (N = 252). The held-out file was never opened.
**Git commit:** `ebad911087942f257ba434f69816ed6d692be170` (working tree has the uncommitted recovery-phase edits listed in `docs/recovery/BASELINE.md`; none touch the evaluation, scoring, V2/V3 or baseline code used below).
**Environment:** Python 3.11.15, numpy 1.25.2, scipy 1.16.3, pandas 2.1.0, networkx 3.6.1, causal-learn 0.1.3.8, macOS arm64.
The saved Sprint 4.3.0 artifacts were produced under Python 3.9.6 / numpy 2.0.2 (`artifacts/sprint4_3_0/results/dev/run_metadata.json`).

## 0. Verdict

| # | Headline finding | Result |
|---|---|---|
| A | Unsafe attributions 79 → 48 (−39.2 %) on 252 scenarios | **REPRODUCED exactly.** Fresh re-execution and saved records agree: 79 → 48, 39.24 %. |
| B | Strict ΔU = +0.224 [+0.085, +0.365]; operational ΔU = +0.169 [+0.031, +0.309] | **REPRODUCED.** Saved records give +0.2242 [0.0855, 0.3665] and +0.1687 [0.0307, 0.3088]. A fresh re-run gives +0.2246 [0.0858, 0.3671] and +0.1690 [0.0311, 0.3092]. The 2 extra V2 interventions explain the difference (§B.2). Both CIs exclude 0 under four resampling schemes. |
| C | 25/32 strict and 22/32 operational cells improve on V2. λ* = 0.938 (κ = 0), 0.582 (κ = 0.025) | **REPRODUCED.** 25/32 strict and 22/32 operational (template-cluster 95 % CI > 0), identical cells in saved and fresh runs. λ* = 0.9375 and 0.5823 exactly. See the §C.3 caveat on what λ* means. |
| D | Mean 2.71 interventions; > 50 % overhead reduction vs random exploration | **2.71 REPRODUCED (2.706). The "> 50 % reduction vs random exploration" is NOT reproduced.** V3 uses more interventions than every random or one-shot comparator in the repo. Against exhaustive do() on every observed service the reduction is 39.4 %. The 50 % figure traces to hard-coded constants (30 s vs 60 s). See §D. |
| E | All 8 registered baselines execute | **REPRODUCED.** All 8 ran fresh on 252 scenarios with 0 errors. Outputs match the saved records, with zero mismatches in abstention, top-1, reason and n_do. |

Overall, A, B, C and E reproduce. The first half of D (2.71) reproduces. The second half of D (> 50 % vs random) does not, and the claim should not be published as worded.

## 1. Reproduction commands

```bash
cd "RIFT FINAL"
# 1. existing read-only verifiers (no artifact written by the first)
PYTHONPATH=src:. python3.11 scripts/recovery_ledger_verify.py          # 34 PASS / 0 FAIL / 0 SKIP
python3.11 scripts/sprint451_utility_sensitivity.py                    # "claims verified: 56/58", "mismatches vs saved scores: 0 of 3276"
# 2. new independent reproduction (≈ 35 s fresh execution of 10 methods × 252 scenarios, plus bootstraps)
PYTHONPATH=src:. python3.11 scripts/sprint7_results_reproduction.py   # writes artifacts/sprint7/reproduction/{results.json,fresh_records.json}
PYTHONPATH=src:. python3.11 scripts/sprint7_results_reproduction.py --no-rerun   # saved-records-only mode (≈ 10 s)
# 3. baseline unit tests
python3.11 -m pytest tests -q -k "baseline or oracle or sieve or latency or random or one_shot" -p no:cacheprovider   # 83 passed
```

[`scripts/sprint7_results_reproduction.py`](../../scripts/sprint7_results_reproduction.py) contains these parts:
- It re-implements scoring from `(label, record)`. It does **not** import `benchmark_v2.score_one`.
- It checks the SHA-256 pins of the dataset files.
- It re-executes all 8 registered baselines, `RIFT-FULL-V2` and `V3-FULL` through `benchmark_v2.run_methods`, `simulator.observe` and `run_v3`.
- It compares the fresh records with the saved ones.
- It runs the bootstraps.

Seeds: 4510 (primary), 4511 (group), 4512 and 4513 (grid), 20260711 (Monte-Carlo stability check), 7000 and 7001 (scenario-level iid). B = 10 000 for the primary CIs and 4 000 for the grid.
Both fresh runs of the script were compared record by record (abstained, reason, top-k, n_do, ed_s) over 2 520 records, and the results were identical (0 differences).
Output SHA-256: `results.json` = `329ab681…3849f3`, script = `28d32377…e87ee16`.

## 2. Raw data validation

| Check | Result |
|---|---|
| `datasets/rift_v2/dev.json` SHA-256 | `a833ad0ca1db0583a30bc4450f9f59b2984a5823702935ef59c6b037e026ef5f` matches pin and manifest (447 520 B, 180 scenarios) |
| `datasets/rift_v2/val.json` SHA-256 | `e82252b47f29dc1353586034b6fd8c3491df3221851f9c84c48bf717a944a1fb` matches pin and manifest (198 802 B, 72 scenarios) |
| N | 252 total (dev 180, val 72); scenario ids unique; 252 distinct `content_hash` |
| Ground truth | ATTRIBUTE 99 (π = 0.3929), ABSTAIN_REQUIRED 153 |
| Abstain-reason breakdown (153) | WEAK_SIGNAL 46, ROOT_UNOBSERVED 31, INSUFFICIENT_BASELINE 23, SYMMETRIC_MUTUAL_DEPENDENCY 22, NO_DISCRIMINATING_EVIDENCE 18, NO_FAULT 13 |
| Clusters | 105 templates (K_template = 105); 21 union-find groups (template OR topology) |
| Saved records | V3: `artifacts/sprint4_4_0/v3_{dev,val}.json`; baselines and V2: `artifacts/sprint4_3_0/results/{dev,val}/per_scenario.json`; all 252 ids × 10 methods present |
| Independent scorer vs saved `score` fields | 0 mismatches over 2 520 (scenario, method) pairs on `answered`, `correct` and `unsafe` (the Sprint 4.5.1 script matched 3 276 of 3 276) |
| Held-out | `heldout_status.json` = FINAL_FROZEN; the script never opens `heldout_candidate.json` |
| Fresh vs saved records (10 methods × 252 = 2 520) | 2 differences, both `RIFT-FULL-V2`, field `n_do` only: V2D-0117 (saved 4, fresh 5) and V2V-0022 (saved 4, fresh 5). Abstention, reason and top-1 are identical in both. Neither changes any unsafe or correct label. Likely cause: a numerical difference between numpy 2.0.2 / Python 3.9 and numpy 1.25.2 / Python 3.11 in the FCI or CID step. This was not investigated further. |

## 3. A — Unsafe diagnostic attribution reduction

### A.1 Exact classification rules (used by the independent scorer)

```
answered           = not record.abstained
top1               = record.top[0][0] if answered and record.top else None
correct            = answered AND expected_outcome == ATTRIBUTE AND top1 in ground_truth.roots
unsafe (strict)    = answered AND (expected_outcome == ABSTAIN_REQUIRED OR top1 not in roots)
unsafe_operational = answered AND top1 not in roots     # a right service named on an ABSTAIN_REQUIRED case is not harmful
lucky              = answered AND expected_outcome == ABSTAIN_REQUIRED AND top1 in roots
```

An abstention is never unsafe. `correct` and `unsafe` are never both 1 (checked in `sprint451_utility_sensitivity.py`).

### A.2 Counts (identical in the saved and the fresh-execution sources)

| | V2 | V3 | Δ |
|---|---|---|---|
| Answered | 115 | 93 | −22 |
| Correct (P@1 of 99) | 36 | 45 | +9 |
| **Unsafe, strict** | **79** | **48** | **−31 (−39.24 %)** |
| – wrong root on ATTRIBUTE | 27 | 10 | −17 |
| – answered on ABSTAIN_REQUIRED | 52 | 38 | −14 |
| – of which "lucky" (right service anyway) | 25 | 18 | −7 |
| **Unsafe, operational** | **54** | **30** | **−24 (−44.44 %)** |
| Unsafe by split (dev / val) | 52 / 27 | 35 / 13 | −17 / −14 |

Check: strict = wrong_root + answered_on_AR (27 + 52 = 79; 10 + 38 = 48). Operational = strict − lucky (79 − 25 = 54; 48 − 18 = 30).
Paired transitions: 46 scenarios were V2-unsafe and V3-safe, 15 were V2-safe and V3-unsafe, 33 were unsafe in both, and 158 were safe in both. Net change is −31 (46 − 15).

**Caveats.**
- V3 was designed after inspecting dev/val failures, so this is development evidence and not confirmatory (see `docs/recovery/CLAIMS_EVIDENCE_LEDGER.md`).
- 15 scenarios became unsafe under V3.
- V3's reduction comes largely from abstaining more (answered 115 → 93).
- The always-abstain policy has 0 unsafe, so "fewer unsafe attributions" does not by itself imply a better method.

## 4. B — Utility, paired bootstrap from raw scores

U_i = C_i − λ·S_i − κ·n_do_i, with λ = 2 and κ = 0.05 (γ = 20κ = 1; MAX_DO = 20). Strict uses S = unsafe, operational uses S = unsafe_op.
The paired difference is d_i = U_i(V3) − U_i(V2). Whole clusters (templates) are resampled with replacement, and the statistic is the mean over the resample. The interval is the 95 % percentile CI. `mean_V3 = −0.3377` strict and `−0.1948` operational; `mean_V2 = −0.5619` / `−0.3635`.

### B.1 From saved raw records (same inputs as the claim)

| Resampling | Strict ΔU | Operational ΔU |
|---|---|---|
| Template clusters, seed 4510, B = 10 000 | **+0.2242 [+0.0855, +0.3665]** | **+0.1687 [+0.0307, +0.3088]** |
| Template clusters, seed 20260711 | +0.2242 [+0.0833, +0.3687] | +0.1687 [+0.0329, +0.3085] |
| Union-find groups (K = 21) | +0.2242 [+0.0850, +0.4012] | +0.1687 [+0.0266, +0.3311] |
| Scenario-level paired iid, seed 7000 | +0.2242 [+0.0835, +0.3627] | +0.1687 [+0.0349, +0.3028] |
| Bootstrap P(mean > 0), iid | 0.999 | 0.9934 |
| SD of paired difference | 1.1112 | 1.0772 |

Claimed values: strict +0.224 [+0.085, +0.365] and operational +0.169 [+0.031, +0.309]. All reproduce at three-decimal rounding. The lower bounds match to 0.001 or better. The upper bounds are within 0.002 (strict 0.3665 vs 0.365, operational 0.3088 vs 0.309). The Monte-Carlo difference between two seeds is 0.002–0.003.

### B.2 From a fresh re-execution of V2 and V3 (this run)

| Resampling | Strict ΔU | Operational ΔU |
|---|---|---|
| Template clusters, seed 4510 | +0.2246 [+0.0858, +0.3671] | +0.1690 [+0.0311, +0.3092] |
| Union-find groups | +0.2246 [+0.0853, +0.4019] | +0.1690 [+0.0270, +0.3314] |
| Scenario-level iid | +0.2246 [+0.0843, +0.3631] | +0.1690 [+0.0359, +0.3032] |

The ≈ 0.0004 shift in the mean comes from the two V2 scenarios whose fresh `n_do` is 5 instead of 4 (2 × 0.05 / 252 = 0.0004). V2 unsafe and correct counts are unchanged.

Both CIs exclude 0 under every scheme. The claim is reproduced.
Note that V3's absolute utility at (λ = 2, κ = 0.05) is negative: −0.338 strict and −0.195 operational. V3 beats V2, but it does not beat always-abstain (U = 0) at this operating point.

## 5. C — Sensitivity grid (λ ∈ {0.25, 0.5, 1, 1.5, 2, 3, 4, 5} × κ ∈ {0, 0.025, 0.05, 0.10}, 32 cells)

### C.1 Counts of cells where V3 − V2 has a 95 % CI entirely above 0

| Definition | Template-cluster CI (claim basis) | Union-find group CI | Scenario-level iid CI | Point estimate > 0 |
|---|---|---|---|---|
| Strict | **25 / 32** | 26 / 32 | 26 / 32 | 30 / 32 |
| Operational | **22 / 32** | 22 / 32 | 23 / 32 | 30 / 32 |

The saved-record run and the fresh run agree on the counts and on the identity of every significant cell. The largest difference between the two runs in any grid-cell mean or CI bound is 0.0012. Saved-record grid vs the archived `artifacts/sprint4_5_1/utility/sensitivity_grid.json` differs by at most 1.1e-16 (bit-identical).

Template-cluster non-significant strict cells (7): (λ, κ) = (0.25, 0.025), (0.25, 0.05), (0.25, 0.10), (0.5, 0.05), (0.5, 0.10), (1.0, 0.10), (1.5, 0.10).
Template-cluster non-significant operational cells (10): (0.25, 0.025), (0.25, 0.05), (0.25, 0.10), (0.5, 0.025), (0.5, 0.05), (0.5, 0.10), (1.0, 0.05), (1.0, 0.10), (1.5, 0.10), (2.0, 0.10).
V3 is significantly *worse* than V2 in one cell, operational (0.25, 0.10). In the archived and saved-record strict grid, (0.25, 0.10) is also significantly negative, with an upper CI bound of −0.000. In the fresh run its upper bound is +0.001, so it falls just inside the non-significant set.

### C.2 Full fresh grid (V3 − V2, mean [95 % template-cluster CI]; `+` = CI entirely > 0, `-` = CI entirely < 0)

Strict:

| λ \ κ | 0 | 0.025 | 0.05 | 0.10 |
|---|---|---|---|---|
| 0.25 | +0.066 [+0.018, +0.116] + | +0.038 [−0.010, +0.087] | +0.009 [−0.038, +0.058] | −0.048 [−0.094, +0.001] |
| 0.5 | +0.097 [+0.038, +0.159] + | +0.069 [+0.011, +0.128] + | +0.040 [−0.017, +0.098] | −0.017 [−0.074, +0.040] |
| 1.0 | +0.159 [+0.075, +0.245] + | +0.130 [+0.047, +0.214] + | +0.102 [+0.020, +0.184] + | +0.044 [−0.036, +0.124] |
| 1.5 | +0.220 [+0.108, +0.334] + | +0.192 [+0.080, +0.304] + | +0.163 [+0.053, +0.275] + | +0.106 [−0.000, +0.215] |
| 2.0 | +0.282 [+0.141, +0.424] + | +0.253 [+0.114, +0.394] + | +0.225 [+0.086, +0.365] + | +0.167 [+0.031, +0.306] + |
| 3.0 | +0.405 [+0.207, +0.607] + | +0.376 [+0.182, +0.576] + | +0.348 [+0.155, +0.548] + | +0.290 [+0.099, +0.491] + |
| 4.0 | +0.528 [+0.272, +0.789] + | +0.499 [+0.245, +0.759] + | +0.471 [+0.219, +0.730] + | +0.413 [+0.163, +0.672] + |
| 5.0 | +0.651 [+0.337, +0.972] + | +0.622 [+0.309, +0.941] + | +0.594 [+0.282, +0.910] + | +0.537 [+0.226, +0.856] + |

Operational:

| λ \ κ | 0 | 0.025 | 0.05 | 0.10 |
|---|---|---|---|---|
| 0.25 | +0.060 [+0.010, +0.111] + | +0.031 [−0.018, +0.082] | +0.002 [−0.045, +0.052] | −0.055 [−0.103, −0.005] − |
| 0.5 | +0.083 [+0.024, +0.145] + | +0.055 [−0.003, +0.115] | +0.026 [−0.031, +0.086] | −0.031 [−0.088, +0.029] |
| 1.0 | +0.131 [+0.048, +0.218] + | +0.102 [+0.020, +0.188] + | +0.074 [−0.007, +0.159] | +0.017 [−0.064, +0.100] |
| 1.5 | +0.179 [+0.068, +0.294] + | +0.150 [+0.042, +0.263] + | +0.121 [+0.014, +0.233] + | +0.064 [−0.041, +0.174] |
| 2.0 | +0.226 [+0.088, +0.368] + | +0.198 [+0.063, +0.337] + | +0.169 [+0.036, +0.308] + | +0.112 [−0.021, +0.250] |
| 3.0 | +0.321 [+0.127, +0.521] + | +0.293 [+0.099, +0.491] + | +0.264 [+0.072, +0.463] + | +0.207 [+0.019, +0.404] + |
| 4.0 | +0.417 [+0.168, +0.679] + | +0.388 [+0.140, +0.649] + | +0.360 [+0.114, +0.618] + | +0.302 [+0.058, +0.558] + |
| 5.0 | +0.512 [+0.206, +0.832] + | +0.483 [+0.180, +0.802] + | +0.455 [+0.152, +0.771] + | +0.398 [+0.096, +0.710] + |

### C.3 Break-even boundaries (V3 vs always-abstain; solve mean(C − κ·n_do) − λ·mean(S) = 0 ⇒ λ* = Σ(C − κ·n_do) / ΣS)

| κ | V3 λ* (point) | 95 % template-cluster CI | V2 λ* (point) |
|---|---|---|---|
| **0** | **0.9375** (= 45/48) | [0.614, 1.436] | 0.4557 |
| **0.025** | **0.5823** (= (45 − 0.025 × 682)/48) | [0.308, 0.985] | 0.3310 (fresh) / 0.3316 (saved) |
| 0.05 | 0.2271 | [−0.010, 0.550] | 0.2063 (fresh) / 0.2076 (saved) |
| 0.10 | −0.4833 | [−0.715, −0.255] | −0.0430 (fresh) / −0.0405 (saved) |

The claimed 0.938 and 0.582 reproduce exactly. V3's total n_do is 682 (mean 2.706 × 252).

**Important interpretation caveat.** λ* is the break-even against *always-abstain* (U = 0), not against V2.
- V3 − V2 is positive at the point estimate for 30/32 cells in each definition.
- V3 has positive absolute utility only for λ < λ*. The 95 % CI for V3 − AA excludes 0 only up to λ ≈ 0.61 at κ = 0 (`artifacts/sprint4_5_1/utility/utility_verification.json`, `lambda_significance_limit_V3_vs_AA`).
- The V3-vs-V2 equal-utility λ (where V3 and V2 tie) is negative at κ ≤ 0.025 (−0.290 and −0.058). V3 is better than V2 for every λ ≥ 0 at those κ, and the V3 > V2 advantage disappears only at large κ with small λ.

## 6. D — Active intervention efficiency

### D.1 What reproduces

| Quantity | Value |
|---|---|
| V3-FULL mean n_do (252 scenarios) | **2.7063** (= 682/252); claim 2.71 reproduced |
| By split | dev 2.511, val 3.194 |
| Max n_do | 8 (the claim "up to 8" holds; MAX_DO budget = 20) |
| Distribution of n_do | 0: 77, 2: 19, 3: 52, 4: 55, 5: 32, 6: 13, 7: 2, 8: 2 |
| Mean n_do among scenarios with ≥ 1 do() | 3.897 (175 of 252 scenarios reach the intervention stage) |
| Mean number of divergent candidate services per scenario | 2.81 |
| Mean observed services per scenario | 4.47 |

### D.2 Comparison with other strategies (all fresh, same 252 scenarios)

| Comparator | Mean n_do | V3 change vs comparator |
|---|---|---|
| Exhaustive do() on every observed service | 4.468 | **−39.4 % (V3 uses fewer)** |
| Random-order exploration, oracle stop at first true root (ATTRIBUTE scenarios only; analytic expectation (n + 1)/(r + 1)) | 2.521 | +7.4 % (V3 uses more) |
| B6-RIFT-RANDOM (in-repo random MSIS baseline) | 1.206 | +124 % (V3 uses 2.2× more) |
| B7-RIFT-ONE-SHOT | 1.202 | +125 % |
| RIFT-FULL-V2 | 1.563 | +73 % |
| V2 random-order ablation A10 (saved Sprint 4.3.0) | 1.591 | +70 % |

### D.3 Finding on the ">50 % overhead reduction vs random exploration" claim

It does **not** reproduce. Against every random-ordering comparator available in the repo, V3 uses more interventions, not fewer.
- B6-RIFT-RANDOM and the A10 ablation run 1.2 and 1.6 do() per scenario on average. The 2.71 V3 figure is higher.
- The only comparator V3 beats is the naive "intervene on everything" policy, at −39.4 %, which is below 50 %. The 4.47 figure counts observed services; the budget cap is 20.
- `rift_v3.run_v3` (`src/rift/attribution_v3/rift_v3.py:182-212`) loops `for x in names` in temporal order. It intervenes on every divergent candidate until the MAX_DO cap, and in all 175 scenarios that reach the intervention stage `n_do == min(len(candidates), 20)`. It does not call MSIS or `greedy_msis`, and it has no entropy-based stopping. The ledger's C10 wording ("Closed-loop Greedy MSIS … halts when posterior converges") does not describe the V3 code path that produced 2.71.
- The "50 % / 30 s vs 60 s" in `docs/FINAL_RESEARCH_DECISION.md` and the IEEE draft is produced by `scripts/run_reproducible_evaluation.py:450-451`: `ed_rift = np.full(len(rift_p1), 30.0)`, `ed_rand = np.full(len(rift_p1), 60.0)`. These are hard-coded constants and not measurements (confirmed by `recovery_ledger_verify.py`, check "H4 inputs are hard-coded constants").
- The 2.71 figure is a higher cost than V2's. V3 reduces unsafe answers at the price of 1.14 extra do() per scenario (682 vs 394 total do()). This extra cost is already priced into the κ axis of §5.

Recommended wording: "V3 averages 2.71 simulated interventions per scenario (max 8, budget 20), 39 % fewer than intervening on every observed service." Do **not** claim a 50 % reduction versus random exploration.

## 7. E — All 8 registered baselines executed

All 8 ran fresh on 252 scenarios with 0 method errors, and their records match the saved ones (0 differences in abstention, reason, top-1 and n_do). `RIFT-FULL-V2` and `V3-FULL` are shown for reference. P@1 is out of the 99 ATTRIBUTE scenarios.

| Method | Answered | Correct (P@1/99) | Unsafe strict | Unsafe op. | Wrong root | Answered on AR | Mean n_do | Mean U (λ = 2, κ = 0.05) | λ* (κ = 0) |
|---|---|---|---|---|---|---|---|---|---|
| B0-EARLIEST | 237 | 49 | 188 | 151 | 50 | 138 | 0 | −1.298 | 0.261 |
| B0-HIGHEST | 252 | 32 | 220 | 192 | 67 | 153 | 0 | −1.619 | 0.145 |
| B1-LATENCY-CORR | 236 | 37 | 199 | 168 | 62 | 137 | 0 | −1.433 | 0.186 |
| B3-SIEVE-LIKE | 236 | 46 | 190 | 159 | 53 | 137 | 0 | −1.325 | 0.242 |
| B5-RIFT-OBS | 171 | 30 | 141 | 120 | 49 | 92 | 0 | −1.000 | 0.213 |
| B6-RIFT-RANDOM | 221 | 51 | 170 | 138 | 48 | 122 | 1.206 | −1.207 | 0.300 |
| B7-RIFT-ONE-SHOT | 221 | 51 | 170 | 138 | 48 | 122 | 1.202 | −1.207 | 0.300 |
| ORACLE:UPPER-BOUND (privileged; reads ground truth) | 99 | 99 | 0 | 0 | 0 | 0 | 0 | +0.393 | n/a (no unsafe) |
| *RIFT-FULL-V2* | 115 | 36 | 79 | 54 | 27 | 52 | 1.563 | −0.562 | 0.456 |
| *V3-FULL* | 93 | 45 | 48 | 30 | 10 | 38 | 2.706 | −0.338 | 0.938 |

Observations:
- The Oracle result is a ceiling: P@1 of 99/99 and 0 unsafe. It abstains on every ABSTAIN_REQUIRED scenario by construction (`ORACLE_ABSTAIN_REQUIRED`).
- B6 and B7 give identical outcomes (51 correct, 170 unsafe). Their n_do differs by 0.004 (1.206 vs 1.202).
- B0-EARLIEST has the highest P@1 (49) among the non-RIFT baselines. B0-EARLIEST and B3 beat V2 and V3 on raw P@1 (49 and 46 vs 36 and 45, with B6 and B7 at 51), but have 188–190 unsafe answers against V3's 48. V3 has the best safety profile among all non-oracle methods.
- The ledger names 8 baselines (7 plus the oracle). The registry also contains `RIFT-FULL-LEGACY`, `RIFT-FULL-V2G` and two further oracle variants, which are outside the 8 requested here. `B4-SAGE-CHAOS` is excluded as a stub.
- The 83 baseline-related unit tests pass.

## 8. Existing verifiers re-run during this reproduction

| Script | Result |
|---|---|
| `scripts/recovery_ledger_verify.py` | **34 PASS, 0 FAIL, 0 SKIP**. Includes V2/V3 counts 79/48, 45/36, P2 160/137, and utility means. |
| `scripts/sprint451_utility_sensitivity.py` | 56/58 pre-registered claims verified; 0 of 3 276 score mismatches. The 2 unverified are rounding-level (cost term 0.1353 vs 0.136; B0-EARLIEST λ* 0.2606 vs 0.26). Both are outside the headline claims reproduced here. |
| `pytest tests -k "baseline or oracle or sieve or latency or random or one_shot"` | 83 passed, 942 deselected |

Re-running `sprint451_utility_sensitivity.py` rewrites `artifacts/sprint4_5_1/utility/*` (it is seeded, so contents are expected to be unchanged; I compared the saved-record grid from the new script against the archived `sensitivity_grid.json` before the rewrite: max difference 1.1e-16).

## 9. Open items and limits

1. **Claim D (> 50 % vs random) is unsupported** (§6.3). `CLAIMS_EVIDENCE_LEDGER.md` C10 and `PERFORMANCE_REPORT.md:32` should be revised before any publication use.
2. **Environment sensitivity.** Two RIFT-FULL-V2 records differ in `n_do` between the saved Python 3.9 / numpy 2.0.2 run and this Python 3.11 / numpy 1.25.2 run (§2). The cause is not investigated. Headline counts are unaffected.
3. **Dev/val are development data.** V3 was tuned on them (Sprint 4.4.0). These results are not confirmatory evidence; the held-out set was not used.
4. **V3 does not beat always-abstain** at the standard penalty (λ = 2, κ = 0.05). V3's absolute utility is negative everywhere except low λ (§5.3).
5. **Cell-count claims depend on the CI scheme.** Template-cluster CIs give 25/32 and 22/32. Group CIs give 26/32 and 22/32. iid CIs give 26/32 and 23/32.
6. The Monte-Carlo noise of a 95 % CI bound is about ±0.003 at B = 10 000. Cells at the edge of significance are not stable across seeds. Examples: strict (0.25, 0.10) has an upper bound of −2e-17 in the archived grid and +0.001 in the fresh run, and strict (1.5, 0.10) has a lower bound of −0.001 (archived) or −0.000 (fresh).

## 10. Files produced

- [`scripts/sprint7_results_reproduction.py`](../../scripts/sprint7_results_reproduction.py): the reproduction script.
- `artifacts/sprint7/reproduction/results.json`: all numerical outputs, including the full 64-cell grids for both sources.
- `artifacts/sprint7/reproduction/fresh_records.json`: fresh per-scenario records for the 10 methods, plus V3 raw candidate and intervention lists and observed-service counts.
