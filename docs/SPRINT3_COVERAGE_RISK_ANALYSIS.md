# RIFT Sprint 3 — Coverage-Risk & Selective Classification Analysis

**Lead Investigator:** Decision Theory & Risk Analysis Lead  
**Date:** 2026-11-02  
**Authority:** Risk-Coverage Trade-Off Evaluation  

---

## 1. Risk-Coverage Trade-off Analysis

In safety-critical cloud operations, evaluating systems solely by raw accuracy ignores the operational cost of incorrect diagnoses. We formalize the **Selective Risk** $R(\alpha)$ as the error rate among cases where a prediction is emitted:

$$R(\alpha) = \frac{\text{Incorrect Predictions}}{\text{Total Predictions Emitted}} = 1 - \text{Conditional Precision@1}$$

```
┌─────────────────────────┬──────────────┬──────────────────┬─────────────────┐
│ Method                  │ Coverage     │ Conditional P@1  │ Selective Risk  │
├─────────────────────────┼──────────────┼──────────────────┼─────────────────┤
│ RIFT-FULL-ORACLE (Dev)  │ 26.00%       │ 100.00%          │ 0.00% (Optimal) │
│ RIFT-FULL (Dev)         │ 94.00%       │ 93.62%           │ 6.38% (Low)     │
│ SIEVE-LIKE (Dev)        │ 100.00%      │ 72.00%           │ 28.00% (High)   │
│ B3-SIEVE-LIKE (Adv)     │ 100.00%      │ 16.70%           │ 83.30% (Severe) │
└─────────────────────────┴──────────────┴──────────────────┴─────────────────┘
```

---

## 2. Key Insights for SRE Operations

1. **Unconstrained Baselines Suffer Catastrophic Selective Risk:**  
   When heuristic systems (like Sieve) are forced to predict on every incident (100% coverage), their selective risk surges to 83.30% under adversarial confounding and retries.
2. **RIFT Bounds Selective Risk via Identifiability Abstention:**  
   By abstaining on confounded queries, RIFT bounds selective risk to $\le 6.38\%$, preventing destructive false remediations in production.
