# RIFT Sprint 3.1 — Metric Reconciliation & Cross-Experiment Disambiguation

**Audit Date:** 2026-11-02  
**Lead Auditor:** Mathematical Evaluation Lead  
**Authority:** Metric Consistency & Verification Task 2  

---

## 1. Metric Definitions & Formulas

Let:
- $N$ = Total Scenarios
- $A$ = Abstained Scenarios
- $P = N - A$ = Predictions Emitted (Cases receiving a diagnosis)
- $C$ = Correct Predictions
- $I = P - C$ = Incorrect Predictions (False Attributions)

```
┌─────────────────────────────────┬────────────────────────────┬────────────────────────────────────────────────────────┐
│ Metric Name                     │ Mathematical Formula       │ Meaning                                                │
├─────────────────────────────────┼────────────────────────────┼────────────────────────────────────────────────────────┤
│ Diagnostic Coverage             │ Cov = P / N = (N - A) / N  │ Fraction of incidents where a diagnosis is attempted.  │
│ Abstention Rate                 │ Abs = A / N                │ Fraction of incidents where system safely abstains.    │
│ Raw Precision@1 (Raw Accuracy)  │ RawP1 = C / N              │ Fraction of all incidents correctly diagnosed.         │
│ Conditional Precision@1         │ CondP1 = C / P = C / (N-A) │ Accuracy among incidents where a diagnosis is emitted. │
│ Overall False Attribution Rate  │ FAR = I / N                │ Fraction of all incidents with wrong diagnosis.        │
│ Selective Risk                  │ Risk = I / P = 1 - CondP1  │ Probability of error given that system emitted a claim.│
└─────────────────────────────────┴────────────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 2. Mathematical Reconciliation of Adversarial Results ($n=30$)

For `RIFT-FULL` on the Adversarial Cohort ($n=30$):
- $N = 30$
- $A = 5$ (Abstained on non-identifiable confounded cases in Family C)
- $P = 25$ (Predictions emitted)
- $C = 14$ (Correct predictions: 0 in A, 0 in B, 3 in C, 5 in D, 1 in E, 5 in F)
- $I = 11$ (Incorrect predictions)

### Direct Metric Derivations:
1. **Coverage:** $\text{Cov} = 25 / 30 = \mathbf{83.33\%}$
2. **Abstention Rate:** $\text{Abs} = 5 / 30 = \mathbf{16.67\%}$
3. **Raw Precision@1:** $\text{RawP1} = 14 / 30 = \mathbf{46.67\%}$
4. **Conditional Precision@1:** $\text{CondP1} = 14 / 25 = \mathbf{56.00\%}$
5. **Overall False Attribution Rate (FAR):** $\text{FAR} = 11 / 30 = \mathbf{36.67\%}$
6. **Selective Risk:** $\text{Risk} = 11 / 25 = \mathbf{44.00\%} = 1 - 0.56$

---

## 3. Root Cause of the 6.38% Discrepancy

- **Finding:** The $6.38\%$ figure referenced in prior discussions originated from the **Sprint 2 Development Split ($n=50$)**, where $I = 3$ and $P = 47 \implies \text{Risk} = 3 / 47 = 6.38\%$.
- **Resolution:** The adversarial stress benchmark ($n=30$) introduces challenging retry storms and inverted onsets, increasing Selective Risk to **$44.00\%$** (Selective Risk $= 1 - \text{CondP1} = 1 - 0.56 = 0.44$). The cross-experiment conflation is formally resolved and removed from all documentation.
