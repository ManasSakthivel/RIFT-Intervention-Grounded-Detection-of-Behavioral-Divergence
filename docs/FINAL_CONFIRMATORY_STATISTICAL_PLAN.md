# RIFT — Final Confirmatory Statistical Plan (Agent 3)

**Status: PROPOSED. Not frozen. Not preregistered.** Binding only after the owner answers D19–D22 and the files below are hashed at Gate G2/G3 (`docs/CONFIRMATORY_INFRASTRUCTURE_PLAN.md` §7). No external reviewer has seen this document. All numbers here are **non-confirmatory** simulations driven by the dev/val marginal (N = 252); no confirmatory or held-out data was opened, generated or analysed. Historical artifacts (`artifacts/sprint4_5_1/power/*`, `docs/SPRINT4_5_0_*`) were **not modified**; this plan supplements `docs/SPRINT4_5_0_STATISTICAL_ANALYSIS_PLAN.md` (the SAP) and where it differs says so explicitly (§9).

---

## 1. What was implemented

| Path | Role | sha256 |
|---|---|---|
| `src/rift/statistics/confirmatory_inference.py` | Production inference module: stratified ratio estimator, **template-stratified bootstrap-t** (SAP §3, seed 4505), **family-block bootstrap-t** (SAP §3.1, seed 4506), `interpret()` (PRE §10 as a pure function), `interpret_two_key()` (hull rule, proposed), Holm, fixed-sequence gate, exact McNemar + mid-p, closed-form power, utility and PRE §3.1 invariant checks. Pure array computation; **no file I/O** (a test greps the source for data access). | `d61b3914…995e4e` |
| `tests/unit/test_confirmatory_inference.py` | 16 tests (all pass): hand-computed CR1 SE, `θ̂ = pooled mean`, seeded reproducibility, degenerate/invalid input, size/power sanity with and without a crossed family effect, exhaustive equivalence of `interpret()` with the PRE §10 label function in `scripts/sprint451_doc_consistency_check.py::label_of` (>1000 grid points), Holm/gate, McNemar, closed-form power vs the SAP table, dev/val reproduction. | `6ba63a32…9d00af` |
| `scripts/final_stat_rule_simulation.py` | Size/power/label-probability simulation of three decision rules through the production module. Seeds 4601/4602 (simulation only; 4505/4506 stay reserved). | `2b153bbe…8a20` |
| `artifacts/final_closure/statistical/rule_comparison.json` | R = 800, B = 399, N = 2000, 9 dependence cells × 4 true effects. | `1ffe6369…1e4de6` |
| `artifacts/final_closure/statistical/n_scaling.json` | N ∈ {1008, 2000, 4000, 8000} × rf ∈ {0, 0.05}. | `870c3d73…ad81` |
| `artifacts/final_closure/statistical/devval_application.json` | The module applied to dev/val (exploratory, descriptive). | `5e1a0c0b…731e5b` |
| `artifacts/final_closure/statistical_sim.log` | Raw log of the main simulation. | — |

Tests: `python3 -m pytest tests/unit/test_confirmatory_inference.py tests/unit/test_statistics.py -q` → **62 passed, 0 failed, 0 skipped** (Python 3.9.6, numpy 2.0.2, scipy 1.13.1). pyflakes clean on the three new Python files.

This module is **not** `scripts/sprint450_analyze.py` (Agent 4's deliverable). It is the library that script must call. **Not implemented here:** the table-loading/report layer, the D22 pair-level endpoint, the missing-data sensitivity wrappers (they are three one-line substitutions of `d`, §6), and the SAP §8–9 descriptive subgroup machinery.

---

## 2. Design audit: what is the independent sampling unit?

Established from data, not assumed (dev/val, `scripts/sprint451_utility_sensitivity.load_rows`): 252 scenarios, 10 structures, **105 templates, 15 families, and 105 distinct (structure, family) cells = templates** — i.e. a template *is* a structure × family cell. The confirmatory layout is the full 16 × 16 grid with 5–9 scenarios per cell.

| Candidate unit | Verdict |
|---|---|
| Scenario | **Rejected.** Scenarios in a template share generator parameters. |
| Telemetry window / do() window / service pair / method row | **Rejected** (SAP §1). |
| Template (= structure × family cell), resampled *within* structure | Independent **only if there is no shared family effect across structures**. This is the SAP's primary unit. It is exact for the claim "the 16 structures, each with *these* 16 templates' DGP". |
| Structure | Fixed strata, not a sample. Using it as a cluster would give 16 clusters and an MDE of 0.18–0.25 regardless of N (SAP §6.1); that reading is not adopted. |
| **Fault family (16 columns)** | The unit of independence **if** the claim is meant to extend beyond the 16 chosen families, **or** if a family effect shared across structures exists. Cannot be repaired by N. |

**Conclusion.** There is no single unit that is simultaneously (a) justified by the generator and (b) powered. The template is the honest unit for the narrow estimand; the family is the honest unit for any wider claim. The data cannot tell which is needed: the dev/val family-after-structure ICC is 0.016 (95% CI ≈ [−0.018, 0.041], K = 15). The question is therefore handled by a **decision rule**, not by an assumption (§3).

## 3. Inference methods and operating characteristics

Estimator (all rules): θ̂ = Σ_s W_s θ̂_s, W_s = n_s/N fixed; per-structure CR1 variance; studentised bootstrap; one-sided p = (1 + #{t\* ≥ θ̂/se})/(B_valid + 1); 95 % CI = [θ̂ − q.975·se, θ̂ − q.025·se]. B = 20,000 in the confirmatory run (SAP §3). A test verifies θ̂ equals the pooled mean exactly and that the SE equals a hand computation to 1e-10.

Rules compared on **identical simulated tables** (N = 2000, 16 × 16 cells, 5–9/cell, V3 dev/val utility marginal, latent crossed-family ICC rf *ignored by the template bootstrap*, within-template ICC rg):

* **T** template-stratified bootstrap-t (SAP primary, D19 option A);
* **F** family-block bootstrap-t (D19 option B);
* **H** hull of both 95 % intervals — lo = min, hi = max; a positive label requires **both** lo > 0, NEGATIVE-WORSE requires **both** hi < 0 (**new D19 option C**).

R = 800, B = 399 ⇒ Monte-Carlo SE at 0.025 is **0.0055**. "Size" = P(lo > 0 | μ = 0). Values from `rule_comparison.json`.

| rg | rf | size T | size F | size H | power(μ = 0.10) T | F | H | P(POSITIVE-USEFUL \| μ = 0.15) T | F | H |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 0.031 | 0.033 | 0.024 | 1.000 | 0.985 | 0.985 | 0.991 | 0.991 | 0.991 |
| 0.05 | 0 | 0.021 | 0.024 | 0.013 | 0.979 | 0.950 | 0.946 | 0.979 | 0.979 | 0.979 |
| 0.20 | 0 | 0.033 | 0.024 | 0.019 | 0.876 | 0.814 | 0.800 | 0.944 | 0.941 | 0.941 |
| 0 | 0.02 | **0.138** | 0.034 | 0.034 | 0.939 | 0.674 | 0.674 | 0.911 | 0.889 | 0.889 |
| 0.05 | 0.02 | **0.098** | 0.033 | 0.030 | 0.870 | 0.616 | 0.616 | 0.875 | 0.851 | 0.851 |
| 0.20 | 0.02 | **0.080** | 0.043 | 0.039 | 0.759 | 0.504 | 0.500 | 0.858 | 0.806 | 0.806 |
| 0 | 0.05 | **0.195** | 0.033 | 0.033 | 0.830 | 0.403 | 0.403 | 0.819 | 0.689 | 0.689 |
| 0.05 | 0.05 | **0.177** | 0.030 | 0.030 | 0.806 | 0.422 | 0.422 | 0.821 | 0.695 | 0.695 |
| 0.20 | 0.05 | **0.131** | 0.029 | 0.029 | 0.706 | 0.341 | 0.341 | 0.797 | 0.606 | 0.606 |

Findings (verified here, consistent with Sprint 4.5.1):

1. **T is anti-conservative under a crossed family effect**: size 0.08–0.20 against nominal 0.025, far outside MC error. Its apparent power at rf > 0 is partly false rejection and must not be quoted as power.
2. **F controls size** in all nine cells (largest 0.043, rg = 0.20, rf = 0.02, i.e. 3.3 MC-SE above 0.025; every other cell ≤ 0.034) at the cost of power **0.34–0.67 when rf ≥ 0.02**.
3. **H is never worse than F on size** (≤ 0.039) and its power is within ≈ 0.015 of F when rf = 0 (e.g. 0.946 vs 0.950). Because the family interval was wider than the template interval in 100 % of replicates with rf ≥ 0.02 (`F_wider_than_T` = 1.0) H ≈ F there; with rf = 0 the two intervals are about equally wide (`F_wider_than_T` ≈ 0.65), so H costs a few points relative to either alone. H adds exactly one thing: it can never be *more* permissive than F.
4. **The dependence cannot be repaired by sample size** (`n_scaling.json`, rg = 0.05):

| N | rf = 0: size T / F / H | power(0.10) T / F / H | rf = 0.05: size T / F / H | power(0.10) T / F / H |
|---|---|---|---|---|
| 1008 | 0.033 / 0.025 / 0.016 | 0.851 / 0.796 / 0.779 | 0.145 / 0.039 / 0.037 | 0.716 / 0.360 / 0.360 |
| 2000 | 0.024 / 0.026 / 0.016 | 0.988 / 0.956 / 0.954 | 0.163 / 0.024 / 0.024 | 0.801 / 0.372 / 0.372 |
| 4000 | 0.019 / 0.026 / 0.013 | 1.000 / 0.994 / 0.994 | 0.182 / 0.033 / 0.033 | 0.860 / 0.414 / 0.414 |
| 8000 | 0.031 / 0.029 / 0.022 | 1.000 / 1.000 / 1.000 | **0.209** / 0.028 / 0.028 | 0.875 / **0.395** / **0.395** |

With rf = 0.05, quadrupling N from 2000 to 8000 moves F/H power from 0.37 to 0.40 and *increases* T's size to 0.21. This is the central structural limitation: information about the family effect scales with 16 families, not with N.

5. **The likely outcome is insensitive to this choice.** If V3 behaves as on dev/val (μ ≈ −0.34), P(NEGATIVE-WORSE) is 1.00 under T, F and H in every cell but one (0.999 for F/H at rg = 0.2, rf = 0.05). Rule choice matters only for a *positive* result.

## 4. Dev/val application (exploratory; not evidence for the confirmatory hypothesis)

`devval_application.json`, B = 20,000, strata = 10 structures, groups = 105 templates, families = 15. Utility at λ = 2, γ = 1 (κ = 0.05 per do()).

| Contrast | θ̂ | Template-stratified 95 % CI | Family-block 95 % CI | PRE §10 label (T / F / H) |
|---|---|---|---|---|
| V3 − always-abstain (strict) | −0.338 | [−0.467, −0.223] | [−0.506, −0.203] | NEGATIVE-WORSE / NEGATIVE-WORSE / NEGATIVE-WORSE |
| V3 − always-abstain (operational) | −0.195 | [−0.305, −0.100] | [−0.302, −0.096] | NEGATIVE-WORSE |
| V3 − V2 (strict) | +0.224 | [0.088, 0.371], p = 0.0006 | [0.064, 0.407], p = 0.0062 | (not a PRE §10 contrast) |

The template-level interval reproduces the documented value ([−0.472, −0.222], `utility_verification.json`) to within bootstrap error; the family interval matches the documented group-level interval ([−0.514, −0.203]) closely. The V3 − V2 gain survives the family-block interval on dev/val (lower bound 0.064 > 0), but dev/val is exploratory: V3 was developed on it.

## 5. Endpoints and decision rules

Unchanged from PRE/SAP, restated so the plan is self-contained. All utilities use λ = 2.0, γ = 1.0, c = n_do/20 (κ = 0.05); U ∈ [−3, 1]; **always-abstain U ≡ 0**.

* **Primary H1 (the only confirmatory test at full α = 0.025):** d_i = U_V3,i − U_AA,i = U_V3,i. Reject iff the *decision interval's* lo > 0 (equivalently one-sided p < 0.025).
* **Intervention-cost comparison with always-abstain** is inside H1 by construction (U_AA has no cost and no harm). The cost term is reported separately as mean n_do, total do() seconds (n_do × 30 s), and U_if_zero_unsafe = C̄ − γ c̄ (SAP §8.6; dev/val +0.043 < δ, so POSITIVE-USEFUL needs V3 to be almost never unsafe).
* **Secondary, only after H1 is rejected, Holm at total α = 0.025 (fixed-sequence gate, implemented in `gatekeep`):** H2 U_V3 − U_V2; H3 unsafe-rate difference S_V2 − S_V3; H4 P1 difference on ATTRIBUTE scenarios (stratified estimator over the ATTRIBUTE subset; structures without ATTRIBUTE scenarios drop out automatically, each remaining stratum needs ≥ 2 groups or the constructor raises). If H1 is not rejected H2–H4 are printed as *descriptive, not confirmatory*.
* **Exploratory H5** (V3 vs each observational baseline, ORACLE rows labelled "privileged upper bound"): no multiplicity correction, no claims. Baseline comparisons are paired on the same scenarios and seeds, so the paired-difference machinery is identical.
* **P2 (outcome accuracy vs always-abstain)** is descriptive and unpowered (McNemar N ≈ 3,300 at dev/val discordance); on dev/val V3 does not beat always-abstain on P2.
* **Binary paired outcomes:** exact McNemar + mid-p are reported as supporting evidence only; they ignore clustering and never decide (SAP §4).
* **Interpretation:** `interpret(lo, hi, θ̂, op_lo)` returns one of five labels; the report prints the function's output verbatim. Tested identical to the PRE §10 truth table.

### 5.1 Proposed D19 resolution (requires owner approval — **not made by this agent**)

**Recommendation: option C (hull rule).** *Reasoning fixed by principle, before looking at any confirmatory data:* a positive claim about V3 is the claim that can embarrass the authors, so it is made only if it survives the more demanding of two defensible readings of the independent unit; a negative claim is likewise made only if both readings agree; otherwise the label is the more cautious (wider-interval) one. This is chosen because it is the only option whose *size is bounded by the family-block size under both readings*; it was not chosen for power (it has the lowest power of the three in some rf = 0 cells — see §3 finding 3). Consequences the owner must accept in advance:

* Power for a true μ = +0.10 is 0.95 at (rg 0.05, rf 0) but 0.34–0.67 if rf ≥ 0.02 (same as F).
* A result with template lo > 0 and family lo ≤ 0 is reported **INCONCLUSIVE**, with the first-paragraph sentence "not robust to family-level dependence" (SAP §3.1). Under the SAP's option A the same data would be POSITIVE-USEFUL/SUBSTANDARD.
* This **changes SAP §3.1's recommended default** (option A + sensitivity). It is an amendment of an unapproved, unfrozen proposal, not of a frozen protocol.

Alternatives for the owner: A (SAP default; higher power; size up to 0.20 if a family effect exists) or B (family-block primary; equivalent to C on size, slightly higher power at rf = 0). Any of the three is defensible if chosen **before** G3 and applied without exception; choosing after seeing confirmatory outcomes is prohibited (see §8).

## 6. Missing data and failures (restating SAP §7 / PRE §9 with the Sprint 4.5.1 discrepancy)

* No imputation, no exclusion of scenarios after generation. QC happens before methods run.
* Primary analysis treats an error/timeout row as a **record**: `answered = 0` (abstention), `error_flag = 1`, n_do consumed up to failure charged. Completion ≥ 95 % per method after one logged re-run of harness-attributable failures, else integrity stop for that method; H1 depends only on V3's completeness (always-abstain cannot fail).
* Sensitivity (secondary; cannot overturn the label): (i) missing → unsafe (U = −2 − cost), (ii) missing → safe abstention (U = 0), (iii) complete-case. Prior simulation (SAP §6.7(f)) shows (i) at 2–5 % missing removes most power, so method failures must be rare.
* **Unresolved discrepancy (D21, restated, not fixed here):** the frozen harness `benchmark_v2._timed` keeps a slow answer as an answer and charges n_do = 0 on exception, while PRE §9 says abstention with n_do charged. The owner must confirm which governs; Agent 4's runner must implement the choice explicitly and be tested (plan test C6). The statistical code accepts whatever rows it is given; it cannot detect this mismatch.
* Pre-analysis abort (PRE §3.1): `check_utility_invariants` verifies U_AA ≡ 0 and U ∈ [−(λ+γ), 1] on every scenario; a violation aborts and is reported, the scenario is not dropped.

## 7. Go / no-go for N = 2000

| Question | Answer | Evidence |
|---|---|---|
| Is N = 2000 adequate for the narrow estimand if no crossed family effect exists? | **GO.** Power(μ = 0.10) 0.88–1.00 (T), 0.80–0.99 (F/H); size 0.013–0.033. | §3 table, rf = 0 rows |
| Is N = 2000 adequate to *establish a positive V3 effect* if a modest family effect exists (rf ≥ 0.02)? | **NO-GO for that purpose, and no N fixes it.** F/H power 0.34–0.67; T would reject falsely 8–20 % of the time. | §3 table; n_scaling (rf = 0.05, N = 8000 → 0.395) |
| Is N = 2000 adequate to establish "V3 is worse than always-abstain" if that is the truth? | **GO.** P(NEGATIVE-WORSE) = 1.00 at μ = −0.338 under T, F and H in 8/9 cells (0.999 in the ninth). | `rule_comparison.json` |
| Should N be reduced to ≈ 1000? | **No.** rf = 0 power falls to 0.78–0.85 (n_scaling), saving little while leaving the same family limitation. | n_scaling N = 1008 |
| Should N be raised? | **No.** Returns vanish; dependence is bounded by 16 families. More *families* would help, which requires a new generator design (new preregistration). | n_scaling |

**Overall: CONDITIONAL GO for N = 2000.** It is a sound sample size for a confirmatory test that will most probably return a decisive NEGATIVE-WORSE and can return a valid, if cautious, positive result only if there is little family-level dependence. It must not be sold as a high-power test of a positive effect. The conditions are: owner records D19 (and D20–D22) before G3; Agent 4's generator realises the 16 × 16 layout with 5–9/cell; the sample size and the analysis are not revised after any confirmatory outcome is visible.

## 8. Anti-"fishing" guardrails

1. Rule (A, B or C) is chosen in `decisions.json` before G3 and hashed with the module. The code cannot choose it from data; `interpret_two_key` reports all three labels so a reader can audit the choice, but only the preregistered one is the headline.
2. Seeds 4505/4506 and B = 20,000 are constants in the module (tested). The single permitted rerun (B = 100,000, same seed rule) applies only when p and the CI disagree at Monte-Carlo resolution (SAP §3).
3. No sample-size re-estimation, no interim analyses, no change of λ, γ, δ, α, comparator or labels after data exist (PRE §10, SAP §13).
4. Any bug fix to the analysis after data exist is a listed deviation with its effect on each conclusion.
5. The simulation seeds used here (4601, 4602) differ from every dataset and analysis seed.
6. This plan reports rule performance in cells **where each rule looks bad**, including the hull rule's power loss; the choice is argued from size control, not from the most favourable column.

## 9. Differences from the SAP, and open items

| # | Item | Status |
|---|---|---|
| 1 | Option C (hull rule) is new; SAP §3.1 proposes A + sensitivity. | Needs owner decision (D19). |
| 2 | SAP §6.7 used R = 400 for family-block cells; here R = 800, B = 399. Results agree with `family_block_power.json` within MC error (e.g. rf = 0.05, rg = 0: F size 0.033 vs 0.0175; power 0.40 vs 0.30; T size 0.195 vs 0.128, power 0.83 vs 0.82 — differences are larger than MC SE for some cells and are attributed to a different layout draw and B; the qualitative conclusions are unchanged). | Disclosed; Sprint 4.5.1 artifacts untouched. |
| 3 | In this simulation family = template index mod 16 within each structure, so every family appears once per structure, as in the planned 16 × 16 grid. | Matches the plan, not yet checked against Agent 4's generator. |
| 4 | Operational lo is set equal to strict lo in the simulation (S_op ≤ S, so U_op ≥ U); the production code takes it as an explicit argument. | As in PRE §10 note. |
| 5 | Dev/val has 10 structures and 15 families, not 16 × 16, so dev/val application and reproduction tests use `FixedStrataDesign` with S = 10. | Descriptive only. |
| 6 | Not implemented: D22 pair table, subgroup/stratified analysis layer, `sprint450_analyze.py`, hashing into `prereg.sha256`. | Handoff to Agent 4 / lead. |
| 7 | SAP §12.5 requires the *final analysis script* to be size-tested on simulated tables; this has been done for the library, not the script. | Agent 4 must repeat on the script. |
| 8 | The Sprint 4.5.0 `docs/FINAL_STATISTICAL_AUDIT.md` (H1–H4 results with Wilcoxon/Cliff's δ) concerns the **earlier Phase-3 hypotheses**, not the Sprint 4.5.0 confirmatory H1–H4; the labels coincide but they are different tests. Do not mix them in the manuscript. | Flagged for Agent 7/8. |

## 10. Handoffs

* **Agent 4 (pipeline):** `scripts/sprint450_analyze.py` must call `FixedStrataDesign.template_bootstrap_t` / `family_block_bootstrap_t` / `interpret` / `gatekeep` and add file loading, the D21 error-row logic and the §8–9 descriptive layer; repeat the SAP §12.5 simulated-table size check on the script; hash the module together with the script at G2.
* **Agent 2 (datasets):** the generator must emit `structure`, `template_id` (= structure | family) and a `family` field for every scenario; the family-block rule is unusable without it. Group sizes 5–9, maximum 14.
* **Lead (decisions):** proposed `decisions.json` entries — D19: *choose A, B or C before G3; recommended C; external approval: yes*. D20: default *report SNR [3,5), do not exclude*. D21: confirm abstention + n_do charged, runner implements it. D22: specify pair-table fields before the generator is finalised. None of these has been recorded as decided.
* **Agent 8 (red team):** please attack (i) the hull rule's justification, (ii) the rf values simulated (0–0.05; larger values were not examined), (iii) the claim that the template is the correct unit for the narrow estimand.

## 11. Reproduction

```bash
python3 -m pytest tests/unit/test_confirmatory_inference.py tests/unit/test_statistics.py -q   # 62 passed
python3 scripts/final_stat_rule_simulation.py --R 800 --B 399                                  # ≈ 75 s + scaling, writes artifacts/final_closure/statistical/
python3 scripts/final_stat_rule_simulation.py --smoke --skip-scaling                           # 2 s smoke run
```

Only `datasets/rift_v2/{dev,val}.json` (sha256-pinned in `scripts/sprint451_utility_sensitivity.py`) and Sprint 4.3.0/4.4.0 dev/val result files are read. The sealed Sprint 4.3.0 held-out split is never opened.
