# RIFT — Pre-Registered Exploratory Comparisons
**Status:** PRE-REGISTERED BEFORE LINUX EXECUTION
**Authority:** docs/PHASE_3_SPEC_FREEZE.md §15, P2-07 resolution
**Freeze date:** Pre-Linux sprint (this document)

---

## Purpose

This document pre-registers all exploratory statistical comparisons permitted after
Linux execution. Any comparison NOT listed here cannot be reported without
explicitly labeling it as an unregistered post-hoc analysis.

**Confirmatory vs Exploratory:**
- **Confirmatory:** H1–H4 (6 tests, Holm-Bonferroni corrected). These are the primary
  hypotheses. Results here support/refute the paper's core claims.
- **Exploratory:** All other comparisons below. BH FDR correction applied.
  Exploratory results are hypothesis-generating, not hypothesis-confirming.

---

## Confirmatory Tests (pre-registered in docs/PHASE_3_SPEC_FREEZE.md §15)

| Test ID | Hypothesis | Test | Metric | Baseline |
|---------|-----------|------|--------|---------|
| CONF-1 | H1 | Wilcoxon one-sided | precision_at_1 | RIFT-OBS |
| CONF-2 | H2 | Wilcoxon one-sided | conditional_precision_at_1 on C_confounded | RIFT-OBS |
| CONF-3 | H3 | Wilcoxon one-sided | precision_at_1 on multi_cause_or_ambiguous | RIFT-ONE-SHOT |
| CONF-4 | H4-cost | Wilcoxon one-sided | total_ed_s (cost, RIFT < RANDOM) | RIFT-RANDOM |
| CONF-5 | H4-acc | TOST equivalence | precision_at_1 (RIFT ≈ RANDOM) | RIFT-RANDOM |
| CONF-6 | H5 | Binomial one-sided | P@1 transfer | in-distribution | DEFERRED |

Correction: Holm-Bonferroni across CONF-1 through CONF-5 (5 active tests; H5 deferred).

---

## Pre-Registered Exploratory Comparisons

### EXP-E01: Fault-type subgroup analysis (RIFT-FULL)

**Description:** Stratify P@1 by fault type (NETWORK_LATENCY, PACKET_LOSS,
SERVICE_DEGRADATION, RESOURCE_CONTENTION, QUEUEING, DEPENDENCY_FAILURE).
Report P@1 per fault type with 95% Wilson CI.

**Test:** Descriptive only (no significance test). Report point estimates + CIs.
**Correction:** None (descriptive analysis).
**Justification:** Understand which fault types RIFT handles well vs poorly.

---

### EXP-E02: Leaf-node R3 fallback effectiveness

**Description:** For scenarios where the ground-truth root cause is a leaf node
(out-degree = 0 in call graph), compare P@1 with and without R3-leaf fallback.

**Test:** McNemar's test (paired binary outcomes, n = leaf-node scenarios).
**Correction:** BH FDR (part of exploratory family).
**Justification:** P1-11 resolution — quantify R3-leaf fallback contribution.

---

### EXP-E03: Intervention count vs attribution accuracy (RIFT-FULL)

**Description:** Scatter plot of n_interventions vs P@1 outcome per scenario.
Spearman correlation between n_interventions and detection_latency_s.

**Test:** Spearman rank correlation (one-tailed, H₁: fewer interventions → lower latency).
**Correction:** BH FDR.
**Justification:** Understand MSIS efficiency curve.

---

### EXP-E04: RIFT-FULL vs SIEVE-LIKE by scenario type

**Description:** Stratify RIFT-FULL vs SIEVE-LIKE comparison by:
  (a) confounded vs non-confounded, (b) leaf-node vs non-leaf root cause.

**Test:** Chi-squared test on 2×2 contingency table (correct/incorrect attribution).
**Correction:** BH FDR.
**Justification:** Understand where SIEVE-LIKE fails relative to RIFT-FULL.
**Critical:** SIEVE-LIKE must be labeled as such in all tables. Never "Sieve".

---

### EXP-E05: Abstention rate breakdown by abstention_reason

**Description:** Report frequency of each abstention_reason code
(NOT_IDENTIFIABLE, INSUFFICIENT_SAMPLES, GRAPH_DISCOVERY_FAILURE, NO_CANDIDATES,
MULTI_CAUSE_AMBIGUOUS) for each baseline.

**Test:** Descriptive only. Chi-squared test if comparing abstention profiles between
RIFT-FULL and RIFT-OBS (BH FDR corrected).
**Justification:** P2-02 resolution — abstention semantics differ by baseline.

---

### EXP-E06: Budget utilization (RIFT-FULL vs RIFT-RANDOM)

**Description:** Compare mean_budget_utilization (total_ed_s / t_budget) between
RIFT-FULL and RIFT-RANDOM. Expected: RIFT-FULL uses less of the budget.

**Test:** Paired Wilcoxon (one-sided, RIFT < RANDOM) on budget_utilization.
**Correction:** BH FDR (not confirmatory — H4-cost is already confirmatory).
**Justification:** Supplementary H4 evidence.

---

### EXP-E07: EBD candidate set quality vs attribution outcome

**Description:** Correlation between EBD candidate count and P@1.
Does a larger candidate set hurt precision?

**Test:** Logistic regression (P@1 binary ~ n_candidates). Report odds ratio + CI.
**Correction:** BH FDR.
**Justification:** Understand EBD filter quality.

---

## Prohibited Post-Hoc Comparisons

The following comparisons are PROHIBITED (not pre-registered, cannot be reported):

- Any comparison involving held-out test set labels before Phase 5 authorization
- Any comparison that selects a specific fault type subset to make results look better
- Any re-running with modified thresholds after seeing results
- H5 cross-system comparisons (no second system; DEFERRED)
- Any comparison involving Sage+Chaos (DEFERRED_TO_PHASE_8)

---

## Application of BH FDR

The exploratory family is: EXP-E01 through EXP-E07.
When reporting exploratory results, apply BH FDR across all exploratory tests that
were actually run. Use `bh_fdr_correction()` from `src/rift/statistics/stats.py`.

Any exploratory test not in this registry that is run after Linux execution MUST be
labeled as "UNREGISTERED POST-HOC" and cannot be used to support any claim.

---

## Status

**PRE-REGISTERED:** This document was frozen before Linux execution.
After Linux execution, exploratory results will be annotated with
`status: EXPLORATORY_REGISTERED` in the results artifacts.
