# RIFT: Final Statistical Audit & Verification Report

**Lead Investigator:** Agent D (Statistical Analysis & Hypothesis Testing Owner)  
**Date:** 2026-11-02  
**Authority:** Final Scientific Verification Gate §5  

---

## 1. Confirmatory Hypothesis Results Summary

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                             Confirmatory Hypothesis Results                                 │
├───────────────────────────────┬────────────┬─────────────┬──────────────┬───────────────────┤
│ Hypothesis                    │ Raw p      │ α_corr      │ Cliff's δ    │ Verdict           │
├───────────────────────────────┼────────────┼─────────────┼──────────────┼───────────────────┤
│ H1: RIFT-FULL > RIFT-OBS P@1  │ 0.5000     │ 0.0250      │ 0.000        │ NOT SUPPORTED     │
│ H2: Confounded Abstention     │ < 0.0001   │ 0.0167      │ +1.000       │ CONFIRMED (p < α) │
│ H3: Closed-Loop > One-Shot    │ 1.0000     │ 0.0500      │ -0.917       │ NOT SUPPORTED     │
│ H4: MSIS Cost < Random Cost   │ < 0.0001   │ 0.0125      │ +1.000       │ CONFIRMED (p < α) │
└───────────────────────────────┴────────────┴─────────────┴──────────────┴───────────────────┘
```

---

## 2. Hypothesis-by-Hypothesis Verification

### 2.1 H1: Interventional vs. Observational Root-Cause Accuracy
- **Primary Endpoint:** Paired difference in Precision@1 between RIFT-FULL and RIFT-OBS.
- **Statistical Test:** One-sided Wilcoxon signed-rank test.
- **Result:** $W = 0.0, p = 0.5000, \text{Cliff's } \delta = 0.000 \, [0.000, 0.000]$.
- **Verdict:** **NOT SUPPORTED on contemporaneous short-window traces**. When FCI produces unoriented PAGs, both variants safely abstain.

### 2.2 H2: Identifiability-Conditioned Abstention on Confounded Systems
- **Primary Endpoint:** Correct abstention rate on confounded non-identifiable scenarios.
- **Statistical Test:** One-sided paired Wilcoxon signed-rank test against heuristic baselines.
- **Result:** $W = 300.0, p < 0.0001, \alpha_{\text{corr}} = 0.0167, \text{Cliff's } \delta = +1.000 \, [+1.000, +1.000]$.
- **Verdict:** **CONFIRMED**. RIFT eliminates false root-cause attributions on confounded systems (0% FAR vs 28% FAR in Sieve-like).

### 2.3 H3: Closed-Loop Bayesian Adaptation on Multi-Cause Faults
- **Primary Endpoint:** Precision@1 comparison between RIFT-FULL and RIFT-ONE-SHOT on multi-cause faults.
- **Statistical Test:** One-sided paired Wilcoxon signed-rank test.
- **Result:** $p = 1.0000, \text{Cliff's } \delta = -0.917$.
- **Verdict:** **NOT SUPPORTED on static synthetic step faults**.

### 2.4 H4: Cost-Aware Multi-Stage Intervention Selection (MSIS)
- **Primary Endpoint:** Total execution duration (seconds) under greedy MSIS vs uniform random selection.
- **Statistical Test:** One-sided paired Wilcoxon signed-rank test.
- **Result:** $W = 1275.0, p < 0.0001, \alpha_{\text{corr}} = 0.0125, \text{Cliff's } \delta = +1.000 \, [+1.000, +1.000]$.
- **Verdict:** **CONFIRMED**. MSIS reduces cumulative perturbation duration by 50.0% (30.0s vs 60.0s).
