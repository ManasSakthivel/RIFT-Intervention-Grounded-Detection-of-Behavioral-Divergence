# Sprint 4.5.0 — Statistical Analysis Plan (SAP)

**Status: PROPOSED (revised in Sprint 4.5.1, fixed-strata design); binding only when recorded under [`SPRINT4_5_0_PREREGISTRATION.md`](SPRINT4_5_0_PREREGISTRATION.md) §13.**
Companion to the preregistration (referred to below as PRE). Section numbers in PRE are cited as "PRE §n".
All empirical numbers below come from dev/val (N = 252) and are **non-confirmatory** calibration values (sources: `artifacts/sprint4_5_0/prereg_audit/audit.json`, `audit_part2.json`).

The analysis script is `scripts/sprint450_analyze.py` (to be written *before* confirmatory generation, tested only on dev/val and on simulated placeholder tables, hashed at G2). **This SAP does not implement it.** Wherever this SAP gives a formula, the script must follow it exactly; any difference is a deviation and must be listed in the report.

---

## 1. Data structure, hierarchy and the estimand (Sprint 4.5.1 decision 1)

**Three levels** (Dataset Protocol §1):

1. **Structure** s = one of **16 fixed causal-graph motifs** (S01–S16). The structures are **fixed experimental strata**, not a random sample from a population of structures.
2. **Scenario group** g = one generator-assigned **template** (`template_id` = structure | fault-family; Dataset Protocol §6). The target layout is 16 templates per structure = **256 groups** (nominal), 5–9 scenarios per group, gate maximum 14. A group is a *within-structure* cluster. **256 groups are not 256 independent structural clusters**; there are only 16 structures, and the 16 fault families are also fixed and crossed with the structures.
3. **Scenario** i = one observation (one row per method).

* **Row** = one scenario × one method: `answered`, `top1`, `correct`, `unsafe`, `n_do`, `expected_outcome`, `abstain_reason`, `error_flag`, plus design labels.
* **Independent unit for the primary analysis** = the group g(i) (template) **within** its structure. Under the acceptance rules R-CAP1 and R-OWN the union-find component of (shared template, shared topology hash) equals the template, so this is also the union-find group (verified on the prototype; Dataset Protocol §6). Scenarios in one group are treated as correlated; groups within a structure are treated as independent.
* **Never** used as units: telemetry windows, do() windows, per-service pairs, per-method rows.
* **Pairing.** All methods are run on exactly the same scenarios with identical observed windows and seeds, so every comparison is a within-scenario paired difference d_i.
* N scenarios, structures s = 1…16 with n_s scenarios and K_s groups, group sum S_g = Σ_{i∈g} d_i.

**Estimand (fixed strata).** θ = Σ_s W_s · μ_s with **W_s = 1/16** (equal structure weights, i.e. the target structure quota 125 of N = 2000; the realised weights n_s/N are used in estimation and reported), where μ_s is the mean paired difference in structure s over the data-generating process of the confirmatory generator restricted to structure s. The claim is **restricted to the 16 preregistered motifs (crossed with the 16 preregistered fault families)** under the preregistered simulator. There is **no claim** about unseen structures, unseen fault families, or arbitrary production environments. Because S13/S14 are quota exceptions (Dataset Protocol §9), the realised n_s are not all equal; θ is defined with W_s = n_s/N (the realised design weights) and the equal-weight value is reported as a macro-average sensitivity (§9.6).

## 2. Endpoints

### 2.1 Primary endpoint (H1)
d_i = U_V3,i − U_AA,i = U_V3,i, where U_i = C_i − λ·S_i − γ·c_i with **λ = 2.0, γ = 1.0, c_i = n_do,i / 20** (PRE §3.1). Estimand θ₁ = Σ_s W_s μ_s (fixed-strata mean over the 16 motifs, §1), estimated by the stratified ratio estimator of §3. Per-scenario U_i ∈ [−3, 1]; the *mean* U is bounded by prevalence (≤ π), a single scenario is not.

### 2.2 Secondary endpoints (confirmatory only after H1 is rejected, PRE §5)
* **H2:** d_i = U_V3,i − U_V2,i at the same λ, γ.
* **H3:** d_i = S_V2,i − S_V3,i (positive favours V3; S = unsafe indicator). Estimand: risk difference in unsafe-answer rate.
* **H4:** d_i = C_V3,i − C_V2,i on ATTRIBUTE scenarios only. The estimator is the stratified ratio mean over ATTRIBUTE scenarios (weights n_s^{att}/N_att; structures S11–S14 have no ATTRIBUTE scenarios and drop out). Estimand: difference in P1 over the 12 attributable-capable motifs.

### 2.3 Descriptive outcomes (no inference claim)
Coverage (answered rate); answer rate on ATTRIBUTE and on ABSTAIN_REQUIRED scenarios; conditional accuracy among answered ATTRIBUTE; wrong-root rate; "lucky-correct" answers on ABSTAIN_REQUIRED scenarios (named service is a true observed root); unobserved-root unsafe rate; mean n_do and total do() seconds (n_do × 30 s); modelled recovery overhead (reported, not in U); decision latency; runtime; normalised utility U/π; P2 (answer-or-abstain correct) versus always-abstain (descriptive, **not powered** — McNemar N ≈ 3,300 at dev/val discordance); break-even λ and break-even prevalence.

### 2.4 Exploratory H5
V3 − each observational baseline, paired utility, cluster bootstrap CI, no multiplicity correction and no claims. ORACLE rows appear in tables as "ORACLE (privileged upper bound)" and have no CI-based comparison.

## 3. Estimation and inference for a generic paired mean

For a set of d_i, structures s = 1…16 with groups g = 1…K_s:

* **Stratified ratio estimator:** θ̂ = Σ_s W_s · θ̂_s, θ̂_s = Σ_{g∈s} S_g / n_s, with W_s = n_s/N (realised design weights, fixed, not resampled).
* **Variance (stratified CR1):** v̂ = Σ_s W_s² · K_s/(K_s−1) · Σ_{g∈s} (S_g − n_g θ̂_s)² / n_s²; ŝe = √v̂. (Equivalent to the pooled formula of the earlier draft when all n_s are equal.)
* **Stratified group bootstrap (primary):** draw B = **20,000** samples; in each draw, within every structure s resample its K_s groups with replacement, **keeping structure weights fixed**; compute θ*_b, ŝe*_b with the same formulas and t*_b = (θ*_b − θ̂)/ŝe*_b. Seed **4505** (independent of all dataset seeds). Implementation: `numpy.random.default_rng(4505)`, a single generator used for all tests in the order H1, H2, H3, H4, H5…, so the stream is reproducible.
* **Family-block bootstrap (mandatory sensitivity, §3.1).** Same estimator, but the resampling unit is the fault-family column (16 families, each with its templates in all structures), with structure weights fixed. Seed **4506**.
* **One-sided p-value** for H0: μ ≤ 0: p = (1 + #{b : t*_b ≥ θ̂/ŝe}) / (B + 1).
* **95% CI (bootstrap-t / studentised):** [θ̂ − q₀.₉₇₅(t*)·ŝe, θ̂ − q₀.₀₂₅(t*)·ŝe].
* **Why studentised cluster bootstrap and not a sign-flip test.** The utility distribution is bounded, discrete and negatively skewed (empirical skewness −1.09, SD 0.969 on dev/val). Operating characteristics of candidate tests were checked by Monte-Carlo from the empirical dev/val distribution by scenario-level resampling at N = 1200 (R = 2000 repetitions, one-sided α = 0.025; script `sprint450_prereg_audit_part2.py`, section F): size under H0: t-test 0.029, sign-flip 0.0315, bootstrap-t 0.0255. Power at μ = +0.10: t 0.942, sign-flip 0.938, bootstrap-t 0.930. A sign-flip (symmetry) test over-rejects under skewness and does not respect clustering. The bootstrap-t holds nominal size best at a small cost in power. These simulations had no clustering; clustering is checked in the pre-run dry run (§12 step 6).
* **Percentile cluster bootstrap CI** (95%, 2.5/97.5 percentiles of θ*_b) and the **plain stratified CR1 t-interval** (Satterthwaite-type d.f. reported; conservative d.f. = K − 16 as the fallback) are reported alongside as sensitivity. If either disagrees with the primary on the sign of the decision, that is reported, but the primary decision is the studentised stratified bootstrap result.

### 3.1 Cluster-unit rule and the family-dependence caveat (new decision D19)
Scenarios from the same fault family but different structures may be correlated through the family (a "crossed" dependence that the template-level resampling ignores). Monte-Carlo evidence (§6.7, `family_block_power.json`) shows: if a latent family effect with ICC rf ≥ 0.02 exists and is ignored, the template-stratified bootstrap-t is anti-conservative (size 0.07–0.20 against a nominal 0.025); the family-block bootstrap controls size but power falls to 0.30–0.59. The dev/val estimate of the family-after-structure ICC is 0.016 (95% CI ≈ [−0.018, 0.041], K = 15; imprecise) and is compatible with 0–0.04. **Recommended preregistered rule (requires researcher approval, D19):** the **primary decision** uses the template-stratified bootstrap-t (the estimand is the fixed 16 × 16 grid and groups within structures are the generator-assigned independent units); the **family-block bootstrap is a mandatory sensitivity analysis**. If the family-block interval's lower bound is ≤ 0 while the primary is > 0, the report must state "**not robust to family-level dependence**" in the first paragraph, next to the label. Alternative offered for the researcher: make the family-block result the decision rule (conservative; lower power). No larger N can repair this: the family-level information is limited by 16 families × 16 structures, not by N.
* **Decision rule equivalence.** "H1 rejected" ⇔ p < 0.025 ⇔ lower bound of the studentised 95% CI > 0, up to Monte-Carlo resolution. If they disagree because of Monte-Carlo error, the p-value rule governs and B is increased to 100,000 once with the same seed rule; this is the only permitted rerun of the bootstrap.

## 4. Exact paired tests (where appropriate)
* For binary paired outcomes (H3: unsafe; H4: correct), report an **exact McNemar test** (two-sided exact binomial on discordant pairs, plus mid-p) using scenario-level discordant counts n₁₀, n₀₁, together with the Newcombe/Wilson paired CI for the risk difference. These tests **ignore clustering** and are therefore reported as supporting evidence only. **Decisions use the cluster-bootstrap-t p-values in §3.** If the exact McNemar test rejects but the cluster test does not, that is reported as "not robust to clustering"; the reverse is reported as observed.
* For the primary and H2, no exact test exists for a skewed, multi-valued utility; the **exact sign test** on the sign of d_i (ties removed) is reported as a descriptive robustness check, since it is distribution-free but ignores magnitude and clustering.

## 5. Decision rules (restated from PRE §5, §10)
1. H1 rejected iff one-sided p₁ < 0.025. Report lo, hi from §3.
2. If H1 rejected: Holm over {H2, H3, H4} with total one-sided α = 0.025. Order p-values ascending p₍₁₎ ≤ p₍₂₎ ≤ p₍₃₎; reject p₍ⱼ₎ iff p₍ⱼ₎ < 0.025/(3−j+1) for all steps up to j (stop at first non-rejection). The Holm-adjusted p-value of p₍ⱼ₎ is p̃₍ⱼ₎ = min(1, max_{k≤j} (3−k+1)·p₍ₖ₎), and hypothesis (j) is rejected iff p̃₍ⱼ₎ < 0.025.
3. If H1 not rejected: H2–H4 raw and Holm-adjusted p-values are shown with the label **"descriptive, not confirmatory"**; no hypothesis claim is made.
4. The interpretation label (POSITIVE-USEFUL, POSITIVE-SUBSTANDARD, NEGATIVE-WORSE, NEGATIVE-NO-USEFUL-EFFECT, INCONCLUSIVE) is computed by a pure function of (lo, hi, θ̂, operational-sensitivity lo) and printed in the report header. No other wording of the conclusion is permitted.

## 6. Sample size and power

### 6.1 Inputs (all from dev/val; non-confirmatory)
| quantity | value | source |
|---|---|---|
| SD of U_V3 (λ=2, γ=1) | 0.969 (dev 0.976, val 0.959) | audit |
| SD of U_V3 − U_V2 | 1.111 | audit |
| mean U_V3 (dev/val) | −0.338 | audit |
| mean U_V3 − U_V2 | +0.224 | audit |
| prevalence π | 0.393 (dev 0.378, val 0.431) | audit |
| empirical DEFF: union-find groups (K = 21, m̄ ≈ 12) | 1.37 | audit part 2 §C |
| ICC at template level (K = 105) | 0.027, 95% CI [−0.14, 0.19]; DEFF ≈ 1.06 | audit §clustering |
| ICC at structure level (K = 10) | 0.042; DEFF ≈ 2.21 | audit |
| ICC at topology-hash level (K = 86) | 0.047; DEFF ≈ 1.07 | audit part 2 §C |
| mean D by structure | linear_chain +0.14; diamond −0.73; hidden_common_cause −0.64; shared_dependency −0.49 | audit |

The design effect of the confirmatory layout is unknown. Mean utility differs by structure (−0.73 to +0.14 on dev/val), but under the **fixed-strata estimand** (§1) between-structure differences are *not* a source of sampling variance: the stratified estimator removes them (dev/val: between-structure share of variance 7.2%, SD 0.969 total vs 0.933 within structure). What remains is within-structure dependence between scenarios of the same template (group) and any crossed fault-family dependence (§3.1). Dev/val has only ≈ 23–25 scenarios per structure, so these ICCs (template −0.049, union-find −0.054, family-after-structure 0.016) are imprecise and are **not used to shrink the planning DEFF**. **DEFF = 2.0 is the planning value; 3.0 is the stress value.** They are assumptions, not estimates.

**What 16 structures imply (limitation, not an effective sample size).** Under the fixed-strata reading with no clustering, the standard error at N = 2000 is ≈ 0.021. *If* the 16 motifs were instead read as a random sample from a population of structures, the standard error would be dominated by the between-structure SD (0.26–0.35 assumed) divided by √16, i.e. SE 0.066–0.088 and a one-sided 80%-power minimum detectable effect of **0.18–0.25 regardless of N**. That reading is **not adopted** (decision 1 of Sprint 4.5.1): the claim is restricted to the 16 preregistered motifs. Consequently no statement about V3 on structures outside these 16 is supported by this study, and no effective sample size of "250 independent clusters" is claimed.

### 6.2 Formula
Normal approximation for a one-sided test of a paired mean with cluster inflation:
N = DEFF · ((z₁₋α + z₁₋β) · SD / δ)²,  power = 1 − Φ( z₁₋α − μ / (SD·sqrt(DEFF/N)) ).
This is an approximation; the final feasibility check is the dry-run simulation in §12.

### 6.3 Results for H1 (one-sided α = 0.025, δ = μ alternative) — closed-form normal approximation
**This table is optimistic.** It uses the normal approximation with a pooled design effect. The studentised bootstrap-t used for the decision is more conservative (§6.7: at DEFF 2.0 the simulated power is 0.83, not 0.90). Treat the table as an upper bound on power and use §6.7 for the preregistered power statement.

Required N for 80% power at SD 0.969: DEFF 1.0 → 738; DEFF 1.5 → 1,106; DEFF 2.0 → 1,475; DEFF 3.0 → 2,212. For 90%: 987 / 1,481 / 1,974 at DEFF 1.0 / 1.5 / 2.0.

| N | μ | DEFF 1.5 | DEFF 2.0 | DEFF 3.0 |
|---|---|---|---|---|
| **800** | 0.10 | 0.66 | 0.54 | 0.39 |
| 1200 | 0.10 | 0.83 | 0.71 | 0.54 |
| 1600 | 0.10 | 0.92 | 0.83 | 0.66 |
| **2000** | 0.10 | **0.965** | **0.90** | 0.76 |
| 2400 | 0.10 | 0.985 | 0.947 | 0.83 |
| 3000 | 0.10 | 0.996 | 0.979 | 0.90 |
| 2000 | 0.075 | 0.81 | 0.69 | 0.52 |
| 2000 | 0.05 | 0.47 | 0.37 | 0.27 |

* SD sensitivity: with SD 1.17 (20% larger) at N = 2000, μ = 0.10: 0.88 (DEFF 1.5), 0.77 (2.0), 0.60 (3.0).
* Minimum detectable effect (80% power), N = 2000: 0.086 (DEFF 2.0), 0.105 (DEFF 3.0); N = 800: 0.135 (DEFF 2.0).
* **N = 800 is not adequate**: at the planning DEFF it gives 54% power for δ = 0.10 (normal approximation, and lower under the bootstrap-t).
* **Proposed N = 2000** (decision D4 in PRE §14). The layout is 16 structures × 16 templates = **256 groups** (nominal), 5–9 scenarios per group, maximum 14 (the earlier planning layout of 250 groups, mean size 8, maximum 25, is superseded by the fixed-strata layout; the Monte-Carlo results below use the new layout). A smaller N would be defensible only with a smaller δ requirement or a lower power tolerance.

### 6.4 Multiple comparisons and the H1 gate
* H1 is tested alone (full α = 0.025); the gate makes the family-wise error rate for the confirmatory claims ≤ 0.025 (fixed-sequence procedure). Under a single Holm over m = 4 hypotheses the H1 threshold would be 0.00625, and power at N = 2000, DEFF 2.0, μ = 0.10 would be **0.78** (0.90 at DEFF 1.5). The gate is therefore preferred because H1 is logically prior (H2–H4 are only meaningful if V3 is useful at all).
* Secondary power at the Holm first-step threshold 0.025/3 = 0.00833, N = 2000, normal approximation:

| hypothesis | effect assumed | DEFF 2.0 | DEFF 3.0 |
|---|---|---|---|
| H2 (SD 1.111) | +0.224 (dev/val) | 1.00 | 1.00 |
| H2 | +0.112 (half) | 0.79 | 0.58 |
| H2 | +0.10 | 0.67 | 0.47 |
| H2 | +0.05 | 0.17 | 0.11 |
| H3 (discordant 15 vs 46) | dev/val | ≈1.00 | — |
| H3 | half effect | 0.95 | — |
| H4 (800 ATTRIBUTE; discordant 19 vs 10) | dev/val | 0.85 | — |
| H4 | half effect | **0.23** | — |

These secondary powers are **normal approximations** with a pooled DEFF; the bootstrap-t is more conservative and the powers fall further under higher DEFF or family-level dependence (§6.7). H4 is expected to be underpowered if the V3–V2 P1 advantage is half its dev/val value. This is stated in advance; a non-significant H4 in that circumstance is **inconclusive** and not evidence of equal P1.

### 6.5 Expected result and the negative case
At dev/val μ = −0.338, the CI upper bound is below 0 with about 130 scenarios (N for 80% power to show hi < 0, DEFF 2) and below δ = 0.10 with about 77. So if V3 behaves as in dev/val, N = 2000 will establish NEGATIVE-WORSE decisively, and 2000 is not a "wasted" sample for that outcome; the study is nonetheless sized so that a *positive* result is detectable.

### 6.6 What is not re-estimated
No sample-size re-estimation after seeing any confirmatory data. The SD and DEFF are not re-estimated from confirmatory data for the purpose of changing N; they are reported for transparency.

### 6.7 Sprint 4.5.1 Monte-Carlo verification (supersedes the earlier §6.7 text)
All simulations below are **non-confirmatory**, use the dev/val marginal distribution of U_V3 (SD 0.969, μ = +0.10 shift), N = 2000, one-sided α = 0.025, and the **studentised bootstrap-t** that §3 prescribes (B = 199 inside the simulation, R = 1000 unless stated; Monte-Carlo SE ≈ 0.005 at a rate of 0.025, ≈ 0.012 at R = 400). Scripts: [`scripts/sprint451_power_mc_verify.py`](../scripts/sprint451_power_mc_verify.py), [`scripts/sprint451_stratified_power.py`](../scripts/sprint451_stratified_power.py), [`scripts/sprint451_family_block_power.py`](../scripts/sprint451_family_block_power.py), [`scripts/sprint451_stratified_power_sd.py`](../scripts/sprint451_stratified_power_sd.py). Results: `artifacts/sprint4_5_1/power/{power_mc_verify,stratified_power,family_block_power,stratified_power_sd125}.json`.

**Retraction.** An earlier Sprint 4.5.1 draft stated (a) that the realised design effect is mathematically capped near 1.58–2.64 and (b) that "90% power at DEFF 2" was robust. **Both statements are unsupported and are removed.** The replacement simulations realise DEFF up to 6 and show that power at DEFF 2 under the bootstrap-t is 0.83, not 0.90. The earlier script `sprint451_power_analysis.py` saturated and is not used for any power claim.

**(a) Pooled-DEFF layouts (random-effects reading, not the adopted estimand; shown for comparison with §6.3).** Column "layout" is the group layout; K = number of groups.

| layout | target DEFF | realised DEFF | power |
|---|---|---|---|
| K = 250, mean size 8 | 1.5 | 1.51 | 0.917 |
| K = 250, mean size 8 | 2.0 | 2.05 | 0.831 |
| K = 250, mean size 8 | 3.0 | 3.00 | 0.653 |
| K = 250, mean size 8 | 6.0 | 5.90 | 0.367 |
| K = 100, mean size 20 | 2.0 | 1.92 | 0.828 |
| K = 100, mean size 20 | 3.0 | 3.04 | 0.642 |

Size under the null was ≤ 0.031 in every row. **Power is inadequate at higher design effects:** at DEFF 3 it is about 0.65 and at DEFF 6 about 0.36.

**(b) Adopted fixed-strata layout** (16 structures × 16 groups, 256 groups, maximum group size 14, stratified ratio estimator with fixed weights, per-structure CR1 variance, stratified group bootstrap-t; R = 1000, B = 199, seed 4518). Within-group dependence is a latent template-level intra-class correlation rg; "rf" is a crossed fault-family ICC that this bootstrap *ignores*.

| rg (template ICC) | rf = 0: DEFF / size / power | rf = 0.02: DEFF / size / power | rf = 0.05: DEFF / size / power |
|---|---|---|---|
| 0 | 0.95 / 0.015 / 0.992 | 1.08 / 0.108 / 0.922 | 1.23 / 0.202 / 0.813 |
| 0.03 | 1.11 / 0.034 / 0.987 | 1.24 / 0.081 / 0.892 | 1.46 / 0.138 / 0.766 |
| 0.05 | 1.28 / 0.024 / 0.967 | 1.40 / 0.097 / 0.875 | 1.57 / 0.137 / 0.787 |
| 0.10 | 1.59 / 0.019 / 0.942 | 1.71 / 0.070 / 0.830 | 1.87 / 0.152 / 0.740 |
| 0.20 | 2.17 / 0.020 / 0.825 | 2.27 / 0.060 / 0.740 | 2.45 / 0.114 / 0.665 |
| 0.30 | 2.84 / 0.020 / 0.738 | 2.91 / 0.046 / 0.662 | 3.17 / 0.096 / 0.615 |

Other layouts (rf = 0): 8 groups per structure (128 groups, maximum size 25) gives power 0.993 / 0.950 / 0.926 / 0.821 / 0.638 / 0.506 at rg = 0 / 0.03 / 0.05 / 0.10 / 0.20 / 0.30; 32 groups per structure (512 groups, maximum size 8) gives 0.991 / 0.985 / 0.986 / 0.968 / 0.946 / 0.894. More, smaller groups help when dependence is at the template level.

**(c) Crossed fault-family dependence (D19).** Family-block bootstrap (seed 4519, R = 400): when rf = 0 the family-block bootstrap controls size (≤ 0.02) with power 0.73–0.98 (rg 0.20–0); when rf = 0.02–0.05 it controls size (≤ 0.04) but **power falls to 0.30–0.59**. The template-stratified bootstrap ignoring a real family effect has size 0.05–0.20 (nominal 0.025) at rf = 0.02–0.05 (table in (b)). This is the central methodological weakness of the design: either the test may be anti-conservative (template-level rule) or the study may be badly under-powered (family-block rule). It is a property of having only 16 fixed families and cannot be fixed by increasing N. The dev/val family-after-structure ICC (0.016, imprecise) is compatible with both.

**(d) Variance stress.** With the within-structure SD inflated by 25% (SD 1.167), template-stratified bootstrap-t, rf = 0 (R = 400): power 0.943 / 0.878 / 0.763 / 0.608 at rg = 0 / 0.05 / 0.10 / 0.20 (DEFF 0.94 / 1.28 / 1.54 / 2.10; size 0.015–0.025).

**(e) Statement of what is and is not claimed.** At N = 2000 with the adopted layout, power for a true μ = +0.10 is about 0.83–0.99 if within-group dependence is moderate (rg ≤ 0.10) and no crossed family effect exists; about 0.65–0.83 if rg is 0.2–0.3; and about 0.30–0.59 if the family-block bootstrap governs under a real family effect. **Power is not adequate at higher design effects**, and **no effective sample size is claimed**. Because V3's expected effect (dev/val mean −0.338) is far below +0.10, the study is likely to produce a decisive negative result; the powers above concern the unlikely positive case.

**(f) Missingness sensitivity** (from the earlier draft, retained as qualitative evidence only because it does not depend on the retracted claims): treating 2% / 5% missing scenarios as safe abstentions barely changes power; treating them as unsafe answers (U = −2) destroys it. Hence method failures must be rare and are handled by §7.


## 7. Missing data, failures and the confirmatory runner
* **Error semantics (corrected in Sprint 4.5.1).** The mapping "exception or timeout ⇒ abstention" is **not** a behaviour of frozen V3 and is **not** in `scripts/sprint440_run_v3.py`. It is implemented in the frozen harness function `benchmark_v2._timed` (`METHOD_ERROR`, `TIMEOUT_S = 60`; `src/rift/evaluation/benchmark_v2.py` lines ≈ 141–158). The confirmatory runner `scripts/sprint450_run_confirm.py` (to be written *before* generation, tested only on dev/val and a pilot tag, **hashed at G2**; `sprint440_run_v3.py` refuses anything but dev/val and cannot be reused) must reproduce exactly these semantics: any exception or a call exceeding 60 s ⇒ record with `error_flag = 1`, `answered = 0` (abstention), **and the n_do consumed up to the failure counted in the intervention cost**; the row is a record, not a missing row. Error rows are tabulated per method and per structure (decision D21).
* **"Complete run"** means: every method × every scenario has a record (error rows count as records). **H1 is evaluated on V3's completeness only**; an integrity stop for one comparator does not void V3 vs always-abstain (always-abstain cannot fail).
* Harness failure (crash not attributable to the method, e.g. out-of-memory): re-run the affected scenario once with the same seeds; log the reason. If a method still lacks a record for > 5% of scenarios, that method's primary analysis is not interpretable: integrity stop for that method, reported with the completion fraction.
* Scenarios are never excluded after generation, for any reason, including "QC failure" discovered after methods have run. QC happens before methods run (Dataset Protocol §8).
* **Sensitivity analyses for missingness:** (i) missing = unsafe answer; (ii) missing = safe abstention; (iii) complete-case.

## 8. Subgroup and stratified analyses (descriptive; no hypothesis tests; no claims of difference)
For each, report n scenarios, K groups, mean U_V3 with studentised cluster CI, mean U_V3 − U_V2, answer rate, unsafe rate.
1. **Expected outcome:** ATTRIBUTE vs ABSTAIN_REQUIRED, and by abstain reason (WEAK_SIGNAL, NO_DISCRIMINATING_EVIDENCE, ROOT_UNOBSERVED, SYMMETRIC_MUTUAL_DEPENDENCY, NO_FAULT, INSUFFICIENT_BASELINE).
2. **Temporal-confound stratum (pre-specified, central to the research question).** Defined at generation time from the simulator state, *not* from any method output, for each scenario: the maximum over non-ancestor observed services y of |d(y)|, where "ancestor" is evaluated on the **full true graph including hidden nodes** (as in `sprint440_cid_audit.py`), d(y) is the noise-free change in the fault contribution to y between the two 30 s do() windows, divided by σ_y; a scenario with no non-ancestor observed service has stratum "none" by convention and is flagged. Computed by the generator module and stored under `design`. Strata: **none** (< 0.1σ), **mild** (0.1–0.3σ), **substantial** (≥ 0.3σ). In dev/val 52 of 252 scenarios (20.6%) are in the substantial stratum (37/180 and 15/72); the generator's *natural* share is 26–28% in the prototype and the target is ≥ 25% (a modest +4 pp increase, not a major expansion; a drift sub-quota is infeasible because drift is a deterministic function of fault shape). Expected stratum size at N = 2000 ≈ 500 scenarios in about 100+ groups. **Stratum contrasts are descriptive:** with n ≈ 500 and DEFF 2 the power of a stratum contrast is ≈ 0.37 and its 80%-power MDE ≈ 0.17.
   * **Wording rule ("robust").** The scenario-level contrast between the substantial and none strata measures *answer suppression* as much as robustness (dev/val: none n = 193, answer rate 0.425, unsafe 0.202, mean U about −0.32; substantial n = 52, answer rate 0.115, unsafe 0.115, mean U about −0.33 (same within rounding)). Therefore "robust to unrelated temporal changes" **must not be inferred from scenario-level unsafe rates**. The robustness question is addressed by the **pair-level secondary endpoint (D22):** among (x, y) pairs where x is a non-ancestor of y, the false-confirmation rate (V3 asserts an intervention-confirmed edge/root for a non-ancestral pair) by drift stratum, with a stratified cluster CI. This endpoint is secondary, descriptive, uncorrected.
3. **Structure, family, temporal pattern, observability, intervention mode, workload.** Reported as forest plots with cluster CIs. With 40+ cells and K = 256 groups, these are descriptive and not corrected; nothing in them can change the primary conclusion or the label. **SNR band:** the stratum SNR ∈ [3, 5) is reported separately (label SNR ≥ 4 versus V3's 3σ rule creates a boundary artefact; whether to exclude the band at generation is decision D20, default: report, do not exclude).
4. **Structure novelty:** structures that are "new" in the sense of Dataset Protocol §3 versus structures that match a dev/val structure type.
5. **Heterogeneity statistic:** ICC and DEFF of D at the group level, reported with CIs, as input for future studies.
6. **Zero-unsafe decomposition:** report U_if_zero_unsafe = C̄ − γ·c̄ (V3's correct-answer and cost terms with every unsafe penalty removed). On dev/val this is +0.043 (= 0.179 − 0.135), i.e. below δ = 0.10; POSITIVE-USEFUL therefore requires that V3 be unsafe on almost no scenarios *and* answer more than it did on dev/val. This is stated in advance so the label is not mis-read.

## 9. Sensitivity analyses (all labelled secondary; none can overturn the primary label)
1. **(λ, κ) grid:** λ ∈ {0.25, 0.5, 1, 1.5, 2, 3, 4, 5}, κ per do() ∈ {0, 0.025, 0.05, 0.10}. κ and γ are related by γ = 20κ. For each cell: θ̂ and studentised CI for V3 − AA and V3 − V2. Display as a heat map with the sign of the CI.
2. **Break-even λ\*** (the λ at which mean U_V3 = 0 for each κ) and **break-even prevalence** π\* with cluster bootstrap CIs. Dev/val reference values: λ\* = 0.938 [0.61, 1.42] at κ = 0; 0.227 [−0.00, 0.54] at κ = 0.05.
3. **Operational unsafe:** S_i^op = answered ∧ (top1 ∉ roots) (a lucky-correct answer on ABSTAIN_REQUIRED is not unsafe; an answer on NO_FAULT scenarios is always unsafe since no root exists). Recompute U^op and H1; this is the robustness condition in the POSITIVE-USEFUL label (PRE §10).
4. **Post-stratification:** re-weight the ATTRIBUTE and ABSTAIN_REQUIRED strata to π_ref ∈ {0.2, 0.4, 0.6, 0.8}. Report U(π) and the crossing point.
5. **Normalised utility** U/π and **coverage-risk curves** (selective accuracy vs coverage as the V3 status threshold varies over DEFINITIVE-only vs DEFINITIVE+QUALIFIED), computed from the frozen `V3-DEFINITIVE-ONLY` configuration. This is an ablation of an existing frozen config, not a re-tuning.
6. **Estimator robustness:** CR1 t-interval, percentile cluster bootstrap, **family-block bootstrap (mandatory, §3.1)**, scenario-level (unclustered) bootstrap, leave-one-group-out maximum influence, leave-structure-out, mean over structures (macro-average, equal weights 1/16).
7. **Variance components:** a random-intercept model of D by group (statsmodels `MixedLM`, available in the canonical environment), reported for the ICC only; not used for any test.
8. **Failure-handling sensitivity** (§7).
9. **Multiplicity-free variant** of H2–H4 (raw, unadjusted) in a separate column.

## 10. Reporting requirements
**Wording rules (binding).** (1) "Safe" and "unsafe" are used only "as defined by the preregistered unsafe indicator" (PRE §3). (2) "Robust to unrelated temporal changes" is never inferred from scenario-level unsafe rates (§8.2). (3) V3's `DEFINITIVE_ROOT` status is always written "DEFINITIVE_ROOT status (CANDIDATE-grade CID)"; no CID check is described as definitive. (4) The study is described as a *designed stress set*, not a deployment estimate; results are "validated on synthetic ground-truth scenarios" and restricted to the 16 preregistered motifs × 16 fault families. (5) The POSITIVE-USEFUL label is a function of the point estimate θ̂ ≥ δ **and** lo > 0 **and** the operational-sensitivity condition (PRE §10); the report must state the actual lo next to the label because lo may be barely above 0.

Every table gives: exact N, K, estimate, studentised 95% CI, raw one-sided p, Holm-adjusted p where applicable, discordant counts for binary outcomes, and the name of the comparator. ALWAYS-ABSTAIN is in the main table. ORACLE rows carry the privileged-upper-bound label. Negative and null results are reported in the same table position and typography as positive ones. The report quotes the label function's output verbatim in its first paragraph.

## 11. Stopping rules
None for efficacy or futility. No interim analyses. Integrity stops are those in PRE §11.

## 12. Pre-run verification (no confirmatory data)
1. **Freeze verification:** re-hash all files in PRE §2.2–§2.4 and compare with the manifest; zero mismatches.
2. **Tests:** `scripts/sprint442_run_tests.py --require-protected` on the owner's full tree: ≥ the 4.4.2 baseline (886 reproducible + 2 protected); on a clean export: ≥ 663 reproducible + 2 unavailable + 0 failures.
3. **Seal:** `scripts/verify_heldout_sealed.py` before and after, owner-run.
4. **Analysis-script test on dev/val** (not as evidence): the script must reproduce this SAP's dev/val numbers: V3 mean U = −0.338 exactly (to three decimals) and V3 − V2 = +0.224 exactly; the template-cluster percentile CI [−0.465, −0.219] within 0.01 (bootstrap seed differs).
5. **Analysis-script test on simulated tables** with known truth, using the **stratified** estimator of §3 on the 16 × 16-group layout: simulate group-structured d_i with template ICC ∈ {0, 0.05, 0.1} and effect {0, 0.1} (R = 2000 each); confirm the script's size ≤ 0.03 at α = 0.025 and power consistent with §6.7(b) (about 0.97 at rg = 0.05, rf = 0). Failure means the script is wrong, not the plan. The tests must also cover the stratified group bootstrap, the family-block bootstrap (D19), the error-row semantics of §7 and the interpretation function of PRE §10.
6. **Hash record** of the analysis script, the confirmatory runner `scripts/sprint450_run_confirm.py` (hashed at G2, before any generation), the generator, the report template and the interpretation function, written to `prereg.sha256` (PRE §13). The extended 69-file freeze manifest (PRE §2) is re-verified at the same time.

## 13. Deviations
Any deviation from this SAP (including a script bug fixed after confirmatory data exist) is reported in the final report with its reason and effect on every confirmatory conclusion; a deviation that could change a conclusion is stated as such. A deviation cannot change the primary estimand, utility, comparator, α, δ, N, or decision labels.
