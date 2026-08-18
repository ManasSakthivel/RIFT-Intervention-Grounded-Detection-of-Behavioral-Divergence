# RIFT — Statistical Analysis Plan
**Phase 2.5 | Risk Closure Document**

> **Purpose:** Pre-register all statistical decisions before any evaluation data is collected. No statistical test, correction scheme, or effect size threshold may be changed after Phase 10 data collection begins. Changes after data collection must be reported as post-hoc analysis, clearly labelled as such, and not used as primary evidence for any hypothesis.

---

## Benchmark Structure (Reference)

| Parameter | Value | Source |
|---|---|---|
| Systems | Online Boutique (A), Sock Shop (B) | `research_charter.md` §5 |
| Fault types | ≥ 4 per system | `research_charter.md` §5 |
| Trials per fault | ≥ 3 (planned 3) | `hypotheses.md` H1 operationalization |
| Incidents per system | 24 faults × 3 trials = **72** | Derived |
| Total incidents | 72 × 2 systems = **144** | Derived |
| Primary evaluation metric | Precision@1 | `hypotheses.md` H1 |
| Secondary metric | Precision@3, detection latency | `hypotheses.md` H1–H5 table |
| Ablation metric (H4) | Cost = cumulative ED (seconds) | `hypotheses.md` H4 |

---

## HYPOTHESIS H1

**Claim:** RIFT-FULL outperforms the best observational baseline on root-cause Precision@1.

---

**FORMAL NULL:**
H₀: Precision@1(RIFT-FULL) ≤ Precision@1(best_observational_baseline)
where best_observational_baseline = max{MicroRCA-style, RIFT-OBS, Isolation Forest}
at the per-incident level across the primary evaluation benchmark.

**FORMAL ALTERNATIVE:**
H₁: Precision@1(RIFT-FULL) > Precision@1(best_observational_baseline)
with effect size Cliff's δ > 0.20 (small effect minimum; one-sided).

**UNIT OF ANALYSIS:** Per-incident. Each incident = one fault-injection trial on one system. An incident is the fundamental observation.

**DEPENDENT VARIABLE:** Binary per-incident indicator: `correct_top1(method, incident) ∈ {0, 1}`. Precision@1 is the sample mean of this indicator.

**INDEPENDENT VARIABLE:** Method identity (RIFT-FULL vs. each observational baseline). Methods are evaluated on the same incidents (same benchmark), making this a **within-subjects / paired design**.

---

**INDEPENDENCE CHECK:**
- Are observations independent? **PARTIAL**
- Dependence structure: Multiple incidents run on the same system (Online Boutique or Sock Shop). Incidents from the same system share the causal graph structure, the service topology, and potentially the same background load pattern. Observations are not i.i.d. — they are clustered within systems.
- Additional within-incident correlation: multiple metrics from the same incident are correlated (latency, error rate, CPU are causally related), but since the dependent variable is the binary correctness indicator (not the raw metrics), this is not a first-order concern for H1. The clustering within system is the primary dependence.
- Recommended correction: **Paired permutation test** (pair = same incident, compare correct_top1 across methods). This naturally handles the within-system clustering by keeping incident identity constant across the comparison. For the between-system generalization question, see H5.

---

**STATISTICAL TEST:**
- **Primary test:** Wilcoxon signed-rank test on the per-incident correctness difference (RIFT-FULL correct_top1 − best_baseline correct_top1). This is appropriate because:
  - The dependent variable is binary (0/1), making the distribution non-normal; Wilcoxon does not assume normality.
  - Incidents are paired (same incident seen by both RIFT-FULL and the best baseline); signed-rank respects this pairing.
  - Sample size (144 total; 72 per system) is adequate for the signed-rank test without a large-n normal approximation for most effect sizes of interest.
- **One-sided test** (H₁ is directional: RIFT-FULL > baseline).
- **Significance threshold:** α = 0.05 (before multiple comparison correction — see below).
- **Alternative if primary is inappropriate:** If the difference vector is too sparse (many ties at 0, a few 1s), use a McNemar test on the 2×2 confusion table (RIFT correct/incorrect × baseline correct/incorrect). McNemar is more powerful than Wilcoxon for sparse binary paired data.
- **Is this appropriate?** YES. Wilcoxon signed-rank on binary differences is equivalent to the sign test with additional weight on the magnitude of differences; for 0/1 data it reduces to counting concordant/discordant pairs, which is appropriate.

---

**EFFECT SIZE:**
- Metric: **Cliff's δ** (non-parametric effect size for ordinal/binary data; equivalent to the probability that a randomly selected RIFT-FULL observation exceeds a randomly selected baseline observation minus the reverse probability).
- Formula: δ = (# incidents where RIFT > baseline − # incidents where baseline > RIFT) / total incidents
- **Minimum meaningful effect:** Cliff's δ > 0.20 (small effect; Cohen's d ≈ 0.41 equivalent). Justification: a δ of 0.20 corresponds to RIFT correctly attributing root cause on ~10 more incidents per 100 than the best baseline. Below this threshold the improvement is operationally marginal.
- Report Cliff's δ with 95% CI regardless of p-value significance. A statistically significant but tiny effect (δ < 0.10) must be acknowledged as practically insignificant.

---

**CONFIDENCE INTERVAL:**
- Method: **Percentile bootstrap** (B = 10,000 resamples at the incident level; resample within each system separately to preserve system-level structure, then pool).
- Level: 95% (two-sided CI on δ; one-sided for directional claim).

---

**SAMPLE SIZE:**
- Minimum incidents for 80% power at Cliff's δ = 0.20 (Wilcoxon signed-rank, one-sided α = 0.05):
  Using the approximation n ≈ (z_α + z_β)² / (6 × δ²) for the signed-rank test on continuous data (conservative for binary): n ≈ (1.645 + 0.842)² / (6 × 0.04) ≈ 6.18 / 0.24 ≈ **26 paired incidents minimum**.
  For binary outcomes (less variance), the McNemar power calculation with expected P(RIFT correct, baseline wrong) = 0.15 and P(RIFT wrong, baseline correct) = 0.05 gives n ≈ (z_α + z_β)² / (√p₁₂ − √p₂₁)² × ... which for these parameters yields approximately **40 discordant pairs needed** for 80% power.
- Does the benchmark provide enough? **YES.** 144 total incidents provide well above the minimum. Even if only 30% of incidents are discordant (RIFT and baseline disagree), that is ~43 discordant pairs, which meets the threshold. This assumes discordance rate ≥ 0.30.
- **Sensitivity check required:** If the best observational baseline performs very well (e.g., RIFT-OBS already achieves 0.80 Precision@1), the discordance rate may be lower than expected. Report achieved power post-hoc using observed discordance.

---

**MULTIPLE COMPARISONS:**
- RIFT-FULL is compared against: MicroRCA-Style, RIFT-OBS, Isolation Forest, Sieve, Ochiai, Sage+Chaos = **6 pairwise comparisons** for H1.
- Additionally, H1 is one of 5 hypotheses, each with up to 6 comparisons = **up to 30 tests total** across H1–H5 (see family-wise error rate analysis in §Specific Concerns below).
- For H1 specifically: **Benjamini-Hochberg (BH) procedure** applied at FDR = 0.05 across the 6 baseline comparisons within H1.
- Primary confirmatory comparison for H1: **RIFT-FULL vs. best_observational_baseline** (pre-registered). This is the single comparison for which H1 is confirmed or rejected.
- The 5 other baseline comparisons within H1 are **exploratory** and reported with BH-corrected p-values.

**REPORTING:**
- Paper table: Precision@1 (mean ± 95% CI) for all methods; Cliff's δ with 95% CI for each RIFT-FULL vs. baseline comparison; corrected p-values.
- If H₁ is not confirmed: Report the point estimate and CI of the difference. If Precision@1(RIFT-FULL) ≈ Precision@1(best_baseline) with δ < 0.10, report this as null result and downgrade N1/N2 claims accordingly. If there is a positive trend but underpowered, report the achieved power and the sample size needed.

---

## HYPOTHESIS H2

**Claim:** On the confounded fault subset, interventions provide information unavailable to observational methods.

---

**FORMAL NULL:**
H₀: Precision@1(RIFT-FULL) ≤ Precision@1(RIFT-OBS) on C_confounded.

**FORMAL ALTERNATIVE:**
H₁: Precision@1(RIFT-FULL) > Precision@1(RIFT-OBS) on C_confounded
with Cliff's δ > 0.20 (same minimum effect threshold as H1).

**UNIT OF ANALYSIS:** Per-incident, restricted to incidents in C_confounded.

**DEPENDENT VARIABLE:** Binary per-incident correctness indicator, same definition as H1, restricted to C_confounded ⊆ benchmark.

**INDEPENDENT VARIABLE:** Method: RIFT-FULL vs. RIFT-OBS. Both use the same G_T (enforced by CF-1); the only difference is the presence/absence of intervention data.

---

**INDEPENDENCE CHECK:**
- Are observations independent? **PARTIAL** — same system-level clustering issue as H1, plus an additional concern: C_confounded incidents are selected by a pre-defined structural criterion (FCI produces bidirected edges in G_T for these scenarios). Selection is pre-registered and not outcome-dependent.
- Recommended correction: Paired Wilcoxon signed-rank or McNemar (same paired incident structure as H1).

---

**STATISTICAL TEST:**
- **Primary test:** Wilcoxon signed-rank (paired on incidents, one-sided) on the correctness difference vector within C_confounded.
- **If C_confounded is very small:** McNemar test (see sample size concerns below). McNemar requires only the count of discordant pairs; it is more powerful for sparse binary data.
- Significance threshold: α = 0.05 (post-BH correction across the H2 family).
- **Alternative:** If C_confounded has fewer than 20 incidents, use an exact binomial test on the proportion of incidents where RIFT-FULL is correct and RIFT-OBS is not.

---

**EFFECT SIZE:**
- Cliff's δ > 0.20, same as H1. For H2, a larger effect is expected (δ > 0.35) because confounded scenarios are specifically where interventions provide causal information that observational adjustment cannot recover.
- Report the effect size separately for C_confounded and for the full benchmark, to show that the intervention benefit is concentrated in the confounded subset (supporting the causal interpretation).

---

**CONFIDENCE INTERVAL:**
- Bootstrap, B = 10,000, resampled within C_confounded.
- Report 95% CI on Cliff's δ and on the Precision@1 difference.

---

**SAMPLE SIZE:**
- **This is the highest-stakes power concern in the entire plan.**
- How large is C_confounded? From the benchmark design: confounded scenarios = faults involving shared-infrastructure confounders (shared host, shared database). Typical microservice benchmarks (Online Boutique, Sock Shop) have 2–4 fault types that reliably produce shared-confounder patterns (e.g., noisy-neighbor CPU contention, shared database saturation).
- Estimated C_confounded: 3 confounded fault types × 3 trials × 2 systems = **18 incidents minimum**. This is a small subset.
- Power at n=18, McNemar test, one-sided α=0.05, assuming P(RIFT correct, RIFT-OBS wrong) = 0.25 and P(RIFT wrong, RIFT-OBS correct) = 0.05: n_discordant ≈ 18 × 0.30 = ~5–6 discordant pairs. McNemar with 5–6 discordant pairs gives power ≈ 40–55% for a one-sided test — **substantially underpowered**.
- **Required action:** Increase confounded fault trials. Options:
  1. Increase trials per confounded fault type from 3 to **6**, yielding 36 incidents in C_confounded.
  2. Increase the number of confounded fault types from 3 to **6**, yielding 36 incidents.
  3. At 36 incidents with ~30% discordance (~11 discordant pairs), McNemar power ≈ 72% — approaching 80%.
  4. At 48 incidents (~14 discordant pairs), McNemar power ≈ 80%.
- **Recommendation:** Pre-register C_confounded with a minimum size of 48 incidents (4 confounded fault types × 4 trials × 3 systems, or 4 × 6 trials × 2 systems). This is a benchmark design requirement, not a statistical analysis choice.
- If the benchmark cannot be expanded: report H2 as **exploratory** (not confirmatory) due to underpowering, and compute the minimum effect size detectable at 80% power given the available n.

---

**MULTIPLE COMPARISONS:**
- H2 has a single primary comparison (RIFT-FULL vs. RIFT-OBS on C_confounded). This is a **confirmatory, pre-registered comparison**.
- No BH correction needed within H2 (single test). It is part of the family-wide correction across all 5 hypotheses.

**REPORTING:**
- Report Precision@1 on C_confounded separately from Precision@1 on the full benchmark.
- Report the FCI bidirected-edge criterion used to define C_confounded — this must be defined before evaluation data is collected.
- If H₁ is not confirmed on H2: explicitly state that the intervention layer does not provide measurably better performance than observational adjustment on the confounded subset. This requires substantially weakening N2 in the paper. Report the confidence interval on the null effect to distinguish "no effect found" from "effect ruled out."

---

## HYPOTHESIS H3

**Claim:** Closed-loop model update improves attribution over one-shot intervention on multi-cause or ambiguous fault scenarios.

---

**FORMAL NULL:**
H₀: Precision@1(RIFT-FULL-CLOSED-LOOP) ≤ Precision@1(RIFT-ONE-SHOT) on multi-cause/ambiguous incidents.

**FORMAL ALTERNATIVE:**
H₁: Precision@1(RIFT-FULL-CLOSED-LOOP) > Precision@1(RIFT-ONE-SHOT) on multi-cause/ambiguous incidents
with Cliff's δ > 0.20.

**UNIT OF ANALYSIS:** Per-incident, restricted to multi-cause or ambiguous fault scenarios (pre-defined subset, analogous to C_confounded for H2).

**DEPENDENT VARIABLE:** Binary per-incident correctness indicator (same definition).

**INDEPENDENT VARIABLE:** Closed-loop update ENABLED vs. DISABLED. Both variants use the same G_T and the same candidate selection logic; only the Bayesian posterior update between successive interventions is toggled.

---

**INDEPENDENCE CHECK:**
- Are observations independent? **NO — this is explicitly PAIRED data.**
- The same incident is run by RIFT-FULL-CLOSED-LOOP and RIFT-ONE-SHOT under **identical conditions** (same injected fault, same G_T, same initial candidate set). They are run on the same incidents.
- This is a paired design by construction. A paired test is mandatory.

---

**STATISTICAL TEST:**
- **Primary test: Wilcoxon signed-rank (paired), one-sided.**
  - Justification: RIFT-FULL-CLOSED-LOOP and RIFT-ONE-SHOT are evaluated on the same incidents; the natural comparison is the per-incident correctness difference. Signed-rank is appropriate for ordinal/binary paired data.
  - The paired structure is not just preferred — it is required. Using an unpaired test on paired data discards the pairing information and inflates variance, reducing power.
- **Why not paired t-test?** The outcome is binary (0/1 correctness), making the normality assumption of a paired t-test inappropriate for small n. Wilcoxon signed-rank makes no distributional assumption.
- Significance threshold: α = 0.05 (post-correction).

---

**EFFECT SIZE:**
- Cliff's δ > 0.20, same minimum threshold.
- Additionally report the **number of interventions required** to reach attribution threshold (if available): RIFT-FULL-CLOSED-LOOP should require fewer total interventions on multi-cause faults. This is a secondary outcome supporting the efficiency claim.

---

**CONFIDENCE INTERVAL:**
- Bootstrap on the paired difference distribution. B = 10,000, stratified by fault type.

---

**SAMPLE SIZE:**
- Multi-cause incidents in the benchmark: estimated 3–4 fault types with known multi-cause patterns × 3 trials × 2 systems = ~18–24 incidents. Subject to the same power concerns as H2.
- Recommendation: same as H2 — pre-register a minimum of 24 multi-cause incidents, ideally 36.

---

**MULTIPLE COMPARISONS:**
- Single confirmatory comparison for H3. Part of the family-wide correction.

**REPORTING:**
- Report both Precision@1 and mean number of interventions per incident for both variants.
- If H₁ is not confirmed: explicitly report that the closed-loop update does not provide measurable accuracy improvement on multi-cause scenarios. Discuss whether this is a power issue (n too small) or a null result. If the closed-loop variant reduces the number of interventions without improving precision, report this as a secondary positive finding.

---

## HYPOTHESIS H4

**Claim:** Systems-aware intervention selection (Utility-guided) reduces cost without harming accuracy, compared to random selection.

---

**FORMAL NULL (cost):**
H₀_cost: Cost(RIFT-FULL) ≥ Cost(RIFT-RANDOM-SELECTION)

**FORMAL ALTERNATIVE (cost):**
H₁_cost: Cost(RIFT-FULL) < Cost(RIFT-RANDOM-SELECTION)
with Cliff's δ > 0.20 on Cost(ED).

**FORMAL NULL (accuracy preservation):**
H₀_acc: Precision@1(RIFT-FULL) ≠ Precision@1(RIFT-RANDOM-SELECTION)
*(we wish to FAIL to reject this null — i.e., show no significant difference in accuracy)*

**UNIT OF ANALYSIS:** Per-incident. Cost = cumulative execution duration (ED in seconds) across all interventions to reach attribution.

**DEPENDENT VARIABLE:**
- Primary: Cost = cumulative ED (continuous, non-negative).
- Secondary: Precision@1 (binary) — used to verify accuracy is preserved.

**INDEPENDENT VARIABLE:** Intervention selection policy: Utility-guided (EIG/Cost) vs. uniform random from safety-feasible set.

---

**INDEPENDENCE CHECK:**
- Are observations independent? **NO — paired data.** Same incident evaluated by both policies. RIFT-FULL and RIFT-RANDOM should ideally be run on the same incident under the same conditions.
- If running both variants on the same incident is operationally infeasible (interference concern), use matched pairs: match RIFT-FULL and RIFT-RANDOM incidents by fault type and system.
- Recommended: run both variants on each incident independently (cost = extra benchmark trials); this gives true paired data.

---

**STATISTICAL TEST:**
- **Primary test (cost): Wilcoxon signed-rank (paired), one-sided** on per-incident Cost(RIFT-FULL) − Cost(RIFT-RANDOM).
  - Justification: Cost is continuous and right-skewed (some incidents may hit the budget ceiling); Wilcoxon is appropriate without normality assumption.
- **Secondary test (accuracy preservation): Paired t-test** on the correctness difference (or McNemar if binary). Here we are testing for equivalence, not superiority. The null hypothesis H₀_acc is what we want to fail to reject.
  - **Equivalence testing approach:** If the 95% CI on the Precision@1 difference is entirely within (−0.05, +0.05), report as "accuracy preserved." This is a TOST (Two One-Sided Tests) equivalence design for the accuracy component, with an equivalence margin of ±5 percentage points.
- Significance threshold: α = 0.05 for the cost test; equivalence margin (−0.05, +0.05) for the accuracy test.

---

**EFFECT SIZE:**
- For cost: Cliff's δ > 0.20 on Cost(ED); also report the mean cost reduction in absolute seconds and as a percentage.
- For accuracy: Cohen's d < 0.20 (trivially small effect) as evidence of accuracy preservation.

---

**CONFIDENCE INTERVAL:**
- Bootstrap CI on mean cost difference and on Precision@1 difference. B = 10,000.

---

**SAMPLE SIZE:**
- Cost is a continuous variable with higher variance than binary correctness. Power calculation for Wilcoxon signed-rank on continuous data at δ = 0.20: approximately 26–30 paired incidents (same as H1 binary case, but cost data may have lower variance relative to effect size if the utility selection is consistently better).
- Benchmark provides 144 incidents (or the subset allocated to ablations). Ablation trials should be pre-planned to ensure ≥ 40 paired incidents for H4.

---

**MULTIPLE COMPARISONS:**
- H4 has two components (cost reduction and accuracy preservation). Both are pre-registered and confirmatory. These are two tests for one hypothesis; apply Bonferroni within H4 (α = 0.025 each). Both must pass for H4 to be confirmed.

**REPORTING:**
- Report mean cost (ED in seconds) ± SD for RIFT-FULL and RIFT-RANDOM; p-value and CI on the difference.
- Report Precision@1 for both variants and the 95% CI on the difference; TOST equivalence bounds.
- If cost is reduced but accuracy is NOT preserved: H4 is rejected. Report as a partial finding.
- If accuracy is preserved but cost is NOT reduced: H4 is rejected. Report as "Utility selection does not provide cost savings over random feasible selection."

---

## HYPOTHESIS H5

**Claim:** RIFT generalizes across independent microservice systems.

---

**FORMAL NULL:**
H₀: Precision@1(RIFT_train_A_test_B) < 0.70 × Precision@1(RIFT_train_A_test_A)

**FORMAL ALTERNATIVE:**
H₁: Precision@1(RIFT_train_A_test_B) ≥ 0.70 × Precision@1(RIFT_train_A_test_A)

**UNIT OF ANALYSIS:** Per-incident on system B (Sock Shop). The threshold ratio (0.70) is evaluated at the aggregate level (mean Precision@1 across all B incidents), not per-incident.

**DEPENDENT VARIABLE:** Precision@1 on system B (Sock Shop) when RIFT's parameters are transferred from system A (Online Boutique), divided by Precision@1 on system A.

**INDEPENDENT VARIABLE:** System identity (A vs. B); whether the causal graph was learned in-distribution (train=test=A or train=test=B) or cross-system (train=A, test=B).

---

**INDEPENDENCE CHECK:**
- Are observations independent? **YES** — system A and system B incidents are from independent systems with independent deployments. No within-pair correlation across systems. Incidents within system B may be correlated (same system-level clustering), but this affects the variance of the Precision@1 estimate on B.
- Recommended correction: Bootstrap CI that respects within-system clustering (resample incident blocks, not individual incidents).

---

**STATISTICAL TEST:**
- **Primary test:** One-sided binomial test on Precision@1(RIFT_train_A_test_B).
  - H₀: p ≤ 0.70 × Precision@1(in_distribution), treated as a fixed threshold derived from the in-distribution result.
  - H₁: p > 0.70 × Precision@1(in_distribution).
  - Significance threshold: α = 0.05.
  - Justification: H5 is not a direct two-group comparison — it is a performance threshold test. The natural test is whether the observed Precision@1 on B is significantly above a pre-specified fraction of the in-distribution performance.
- **Alternative:** If in-distribution performance on A is also uncertain (itself estimated from 72 incidents), use a bootstrap ratio test: construct 10,000 bootstrap samples of (Precision@1_B / Precision@1_A) and compute the probability that the ratio ≥ 0.70.

---

**EFFECT SIZE:**
- Report the transfer ratio R = Precision@1_B / Precision@1_A (mean ± 95% CI via bootstrap). An R > 0.70 confirms H5; an R close to 1.0 would be a very strong result.
- Also report: does RIFT generalize better than the best observational baseline (H5 extension)? This is exploratory.

---

**CONFIDENCE INTERVAL:**
- Bootstrap CI on the transfer ratio R and on absolute Precision@1 values for both systems. B = 10,000.

---

**SAMPLE SIZE:**
- 72 incidents on system B. For a binomial test with expected Precision@1 ≈ 0.65 (70% of in-distribution 0.93): power at n=72 with one-sided α=0.05, p₀=0.65 vs. p₁=0.70: power ≈ 35%. For p₁=0.75: power ≈ 65%. For p₁=0.80: power ≈ 85%.
- **Implication:** H5 has adequate power only if the actual out-of-distribution performance is substantially above the 0.70 threshold. If performance lands right at 0.70, 72 incidents may not provide 80% power to confirm H5. This is acceptable — H5 is a generalization claim, and marginal performance at threshold should not be over-interpreted.
- At 144 total incidents evenly split: power at p₁=0.75 is ~85% — well-powered for a moderate generalization advantage.

---

**MULTIPLE COMPARISONS:**
- H5 is a single confirmatory test (RIFT_train_A_test_B vs. threshold). No multiple comparison correction needed within H5.

**REPORTING:**
- Report Precision@1 and 95% CI for: RIFT in-distribution (A→A), RIFT transfer (A→B), best observational baseline in-distribution (A→A), best observational baseline transfer (A→B).
- If H₁ is not confirmed: report the transfer ratio with CI. If R ∈ [0.60, 0.70], discuss whether the benchmark is too small to detect the true generalization ability. Recommend reporting as "promising but inconclusive."

---

## Specific Concerns

### SC-1: Dependence Structure — Within-System Correlation

**Problem:** Multiple fault scenarios are run on the same system (e.g., Online Boutique). The causal graph G_T is shared across all incidents on that system. The system's baseline behavior (inter-service latencies, resource utilization patterns) is constant across incidents. This induces within-system correlation: if RIFT's G_T is well-calibrated for Online Boutique, it will tend to succeed on all Online Boutique incidents together, and fail on all Sock Shop incidents together.

**Effect on inference:** Standard tests assuming i.i.d. observations will underestimate variance, producing artificially narrow confidence intervals and inflated significance.

**How this plan addresses it:**
1. **Bootstrap that respects clustering:** All bootstrap confidence intervals are computed by resampling at the *system level* (block bootstrap: all incidents from Online Boutique are resampled as a block, all from Sock Shop as a block). This gives variance estimates that reflect between-system variability, not just within-system variability.
2. **Separate reporting by system:** All primary metrics are reported separately for Online Boutique and Sock Shop, not only as pooled estimates. If RIFT's advantage holds on both systems individually, the within-system correlation is not confounding the conclusion.
3. **Mixed-effects model as sensitivity check:** A logistic mixed-effects model with a random intercept per system may be run as a sensitivity analysis to confirm that the fixed-effect estimate of the RIFT advantage is stable across systems. This is secondary/exploratory.
4. **Within-system correlation is partially mitigated by the paired design:** Because RIFT-FULL and each baseline are evaluated on the *same* incidents, the within-system correlation affects both arms equally, partially canceling in the paired difference.

---

### SC-2: Multiple Testing — Family-Wise Error Rate

**Structure of all planned tests:**

| | H1 | H2 | H3 | H4 | H5 | Total |
|---|---|---|---|---|---|---|
| Confirmatory pairwise tests | 1 (vs. best baseline) | 1 (RIFT-FULL vs. RIFT-OBS on C_confounded) | 1 (CLOSED-LOOP vs. ONE-SHOT) | 2 (cost + accuracy) | 1 (threshold test) | **6 confirmatory** |
| Exploratory pairwise tests | 5 (vs. each other baseline) | 0 | 0 | 0 | 1 (extension: vs. best baseline) | **6 exploratory** |
| **Total per hypothesis** | 6 | 1 | 1 | 2 | 2 | **12 total** |

Note: If RIFT-FULL is additionally compared against all 6 baselines for each of H1–H5 metrics (Precision@1, Precision@3, detection latency), the test count could reach 5 metrics × 6 baselines = 30 tests. This plan treats the **primary confirmatory tests (6)** and **secondary exploratory tests (6)** separately.

**Family-wise error rate without correction:**
For k independent tests at α = 0.05: FWER = 1 − (1 − 0.05)^k.
- 6 confirmatory tests: FWER = 1 − 0.95^6 ≈ **0.26** (26% chance of at least one false positive)
- 12 total tests: FWER = 1 − 0.95^12 ≈ **0.46**
- 30 tests: FWER ≈ **0.79**

Without correction, the false positive risk for the exploratory comparisons is severe.

**Correction scheme applied:**

| Test category | Correction | Rationale |
|---|---|---|
| 6 confirmatory tests (one per hypothesis or sub-hypothesis) | **Holm-Bonferroni** (step-down, controls FWER at 0.05) | Confirmatory tests require strong FWER control; Holm is uniformly more powerful than Bonferroni |
| 6 exploratory tests (additional baseline comparisons within H1, H5 extension) | **Benjamini-Hochberg** (controls FDR at 0.05) | Exploratory results are hypothesis-generating; FDR control is appropriate; reported as exploratory in the paper |
| Within-H4 (2 sub-tests) | **Bonferroni** (α = 0.025 each) | Small family; Bonferroni is adequate and conceptually clean |

**Summary:** Confirmatory claims (H1–H5) require all Holm-adjusted p-values < 0.05. Exploratory comparisons are reported with BH-adjusted p-values and clearly labelled as exploratory.

---

### SC-3: Sample Size — Sufficiency for 80% Power at Cliff's δ = 0.20

**Global power analysis:**

For Wilcoxon signed-rank on paired binary data (correctness indicator), the key parameter is the proportion of discordant pairs — incidents where RIFT and the comparison method disagree. Let p₊ = P(RIFT correct, baseline wrong) and p₋ = P(RIFT wrong, baseline correct).

Assume: p₊ = 0.20, p₋ = 0.05 (plausible if RIFT improves on ~15% of incidents). Discordant pair rate π = p₊ + p₋ = 0.25. Under McNemar: effective n = 144 × 0.25 = **36 discordant pairs**.

McNemar power at n_d = 36 discordant pairs, p₊/(p₊+p₋) = 0.80, one-sided α = 0.05:
z = (n_d × (p₊ − p₋) − 0.5) / √(n_d × (p₊ + p₋)) ≈ (36 × 0.15 − 0.5) / √(36 × 0.25) ≈ 4.9 / 3.0 ≈ 1.63

Power = Φ(1.63 − 1.645) + ... ≈ Φ(−0.015) ≈ **0.49** — this is underpowered.

The shortfall comes from a conservative estimate of p₊. If RIFT's advantage is larger (p₊ = 0.30, p₋ = 0.05, π = 0.35):
n_d = 144 × 0.35 = 50; test statistic ≈ (50 × 0.25 − 0.5) / √(50 × 0.35) ≈ 12 / 4.18 ≈ 2.87 → Power ≈ 0.85. **Adequately powered.**

**Conclusion:** 144 incidents provides 80% power IF RIFT's advantage (p₊) is at least 0.25–0.30 (RIFT correctly attributes 25–30 more incidents per 100 than the best baseline). If the advantage is smaller (p₊ ≈ 0.15), the benchmark is underpowered. This is the fundamental sample size risk of the evaluation.

**Mitigation:**
1. Pre-specify the minimum detectable effect (MDE) as p₊ ≥ 0.20 at 80% power given n = 144. Report this as the power guarantee.
2. Compute achieved power post-hoc using observed discordance, and report it in the paper.
3. If the benchmark can be expanded to 200+ total incidents, do so — each additional 20 incidents adds meaningful power.

---

### SC-4: Confounded Subset C_confounded — Power Analysis

**The H2 power problem is the most acute in the plan.** As computed above:

| C_confounded size | Estimated discordant pairs | McNemar power (p₊=0.25, p₋=0.05) |
|---|---|---|
| 18 incidents | ~5 | ~40% |
| 36 incidents | ~9 | ~65% |
| 48 incidents | ~12 | ~75% |
| 60 incidents | ~15 | ~82% |

**To achieve 80% power on H2, C_confounded must contain at least 50–60 incidents.**

Current benchmark design (24 faults × 3 trials × 2 systems = 144 total) may allocate only 18–24 incidents to confounded scenarios if 25–33% of faults involve shared-infrastructure confounders.

**Required benchmark design action (Phase 7):**
- Pre-register C_confounded as a designated subset of the benchmark.
- Explicitly design ≥ 4 confounded fault types (shared host CPU contention, shared database saturation, shared message queue congestion, shared network switch packet loss).
- Run ≥ 4 trials per confounded fault type per system.
- Minimum C_confounded = 4 types × 4 trials × 2 systems = **32 incidents minimum**; target **48+ incidents**.
- If the benchmark cannot accommodate this, H2 must be pre-registered as **exploratory** (not confirmatory) with an explicit power disclosure.

---

### SC-5: Paired vs. Unpaired for H3

**H3 compares RIFT-FULL-CLOSED-LOOP vs. RIFT-ONE-SHOT on the same incidents. This is paired data. A paired test is mandatory.**

Rationale for the pairing requirement:
- The same incident (same injected fault, same system state, same G_T) is evaluated by both variants. The within-incident correlation is very high — both variants start from the same initial state and diverge only at the point of the Bayesian update decision.
- An unpaired test would treat the two observations from the same incident as independent, artificially inflating variance. This would reduce power and produce wider CIs than the true paired variance.
- The expected benefit of closed-loop vs. one-shot is modest for simple single-cause faults (where both variants converge on the same answer in the first intervention). The benefit concentrates on multi-cause and ambiguous scenarios. The pairing is especially important here because the paired design controls for fault difficulty — we compare how much the closed-loop update helps on the *same hard incidents*, not across a mixture of easy and hard incidents.

**Implementation requirement:** For every multi-cause/ambiguous incident in the ablation study, RIFT must be run in both CLOSED-LOOP and ONE-SHOT modes. The two runs must be logged with the same incident ID. The analysis must use the per-incident (CLOSED-LOOP score − ONE-SHOT score) vector as the input to the Wilcoxon signed-rank test.

**If running both variants on each incident is operationally infeasible** (e.g., one run consumes the system's injection budget and affects the state for the second run): use matched-pair randomization. Randomly assign each trial to either CLOSED-LOOP or ONE-SHOT mode, with each fault type represented equally in both groups. Apply the signed-rank test on fault-type-matched pairs. This is a weaker design but still substantially better than an unpaired test.

---

## Pre-Registration Checklist

Before Phase 10 data collection begins, the following must be locked and signed:

| Item | Status | Required By |
|---|---|---|
| C_confounded definition (fault types, structural criterion) | OPEN | Phase 7 |
| C_confounded minimum size (≥ 48 incidents) | OPEN | Phase 7 |
| Multi-cause/ambiguous subset definition (for H3) | OPEN | Phase 7 |
| Sage BN temporal train/test split (t_split) | OPEN | Phase 7 |
| G_T sharing enforcement in experiment harness | OPEN | Phase 8 |
| Bootstrap block structure (per-system blocks) | DEFINED HERE | Phase 10 |
| Holm-Bonferroni application to 6 confirmatory tests | DEFINED HERE | Phase 10 |
| BH application to 6 exploratory tests | DEFINED HERE | Phase 10 |
| Equivalence margin for H4 accuracy test (±5 pp) | DEFINED HERE | Phase 10 |
| Minimum detectable effect: Cliff's δ = 0.20 | DEFINED HERE | Phase 10 |
| Power disclosure (achieved power reported post-hoc) | DEFINED HERE | Phase 12 |
| Oracle baseline as upper-bound reference | OPEN | Phase 8 |

**Gate condition for Phase 10:** All OPEN items must be resolved. The statistical analysis plan is frozen at that point. Any deviation after data collection begins must be labelled as post-hoc analysis.
