# RIFT: Experimental Protocol and Data-Leakage Audit

**Lead Investigator:** Agent C (Experimental Design & Data-Leakage Auditor)  
**Date:** 2026-11-02  
**Authority:** Evaluation Protocol Freeze and Split Integrity Verification  

---

## 1. Scenario Split Definitions and Provenance

The RIFT evaluation benchmark consists of 83 formally registered fault scenarios divided into three disjoint splits:

```
┌───────────────────────────┬──────────────┬──────────────────────┬────────────────────────┐
│ Split                     │ Scenarios    │ Location             │ Cryptographic Status   │
├───────────────────────────┼──────────────┼──────────────────────┼────────────────────────┤
│ Development Split         │ n = 50       │ development.json     │ Unlocked for Dev       │
│ Validation Split          │ n = 18       │ validation.json      │ Frozen for Tuning      │
│ Held-Out Test Split       │ n = 15       │ held_out_test.json   │ Strictly Sealed        │
├───────────────────────────┼──────────────┼──────────────────────┼────────────────────────┤
│ Total Registered          │ n = 83       │ manifest.json        │ Complete Benchmark     │
└───────────────────────────┴──────────────┴──────────────────────┴────────────────────────┘
```

### 1.1 Split Independence and Scenario Composition
- **Development Split ($n=50$):**
  - 26 Non-confounded scenarios (Network latency, Packet loss, Queueing, Service degradation)
  - 24 Confounded scenarios (Unobserved shared CPU, shared DB locks, noisy neighbor switches)
- **Validation Split ($n=18$):**
  - 10 Non-confounded scenarios
  - 8 Confounded scenarios
- **Held-Out Test Split ($n=15$):**
  - 8 Non-confounded scenarios
  - 7 Confounded scenarios
  - Access is guarded by `HeldOutGuard` exception triggers to prevent threshold tuning contamination.

---

## 2. Leakage and Contamination Verification

### 2.1 Seed and Random State Isolation
- Every scenario has an explicit, immutable integer seed ($42 + \text{scenario\_index}$).
- Telemetry generation uses isolated instances of `np.random.default_rng(seed)`.
- No global RNG state is shared between scenarios or baselines.

### 2.2 Feature Construction Boundaries
- Incident time windows $(t_{\text{start}}, t_{\text{end}})$ are bounded strictly by $[t_{\text{inject}} - 60\text{s}, t_{\text{inject}} + 120\text{s}]$.
- Pre-incident baselines are computed from normal operations ($t < t_{\text{inject}}$).
- Post-recovery data ($t > t_{\text{recovery}}$) is excluded from root-cause candidate evaluation.

### 2.3 Frozen Evaluation Protocol
1. **Primary Metrics:**
   - Raw Precision@1: $\frac{\text{Correct Top-1 Predictions}}{\text{Total Scenarios}}$
   - Conditional Precision@1: $\frac{\text{Correct Top-1 Predictions}}{\text{Attributed Scenarios}}$
   - Coverage: $\frac{\text{Attributed Scenarios}}{\text{Total Scenarios}} = 1 - \text{Abstention Rate}$
   - False Attribution Rate (FAR): $\frac{\text{Incorrect Attributions}}{\text{Total Scenarios}}$
2. **Statistical Plan Authority:**
   - Paired Wilcoxon Signed-Rank tests for accuracy and cost comparisons.
   - Cliff's non-parametric effect size ($\delta$) with 95% bootstrap confidence intervals.
   - Family-Wise Error Rate (FWER) control via Holm-Bonferroni step-down correction at $\alpha = 0.05$.
