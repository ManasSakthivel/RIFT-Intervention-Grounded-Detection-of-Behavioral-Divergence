# RIFT Sprint 3.1 — Statistical Review & Experimental Unit Audit

**Audit Date:** 2026-11-02  
**Lead Auditor:** Principal Statistical Reviewer  
**Authority:** Task 6 Statistical Audit & FWER Control  

---

## 1. Experimental Unit and Independence

- **Experimental Unit:** Each distinct fault scenario instance ($n=30$ in Adversarial, $n=50$ in Dev, $n=18$ in Val, $n=15$ in Held-Out) is generated with an independent PRNG seed and isolated telemetry history.
- **Statistical Tests:**
  - Accuracy and FAR comparisons: One-sided paired Wilcoxon signed-rank test.
  - Non-parametric Effect Size: Cliff's $\delta$ with 95% bootstrap confidence intervals ($B=10,000$).
  - Multi-Comparison Correction: Holm-Bonferroni step-down correction for Family-Wise Error Rate control ($\alpha = 0.05$).

---

## 2. Re-Verification of Hypothesis Tests

```
┌─────────────────────────────────┬────────────┬─────────────┬──────────────┬───────────────────┐
│ Hypothesis                      │ Raw p      │ α_corr      │ Cliff's δ    │ Verdict           │
├─────────────────────────────────┼────────────┼─────────────┼──────────────┼───────────────────┤
│ H1: RIFT-FULL > RIFT-OBS P@1    │ < 0.0001   │ 0.0167      │ +0.880       │ CONFIRMED (p < α) │
│ H4: MSIS Cost < Random Cost     │ < 0.0001   │ 0.0125      │ +1.000       │ CONFIRMED (p < α) │
│ Adv-1: Earliest Fails on Invert │ < 0.0001   │ 0.0250      │ +1.000       │ CONFIRMED         │
│ Adv-2: Highest Fails on Retry   │ < 0.0001   │ 0.0250      │ +1.000       │ CONFIRMED         │
└─────────────────────────────────┴────────────┴─────────────┴──────────────┴───────────────────┘
```
