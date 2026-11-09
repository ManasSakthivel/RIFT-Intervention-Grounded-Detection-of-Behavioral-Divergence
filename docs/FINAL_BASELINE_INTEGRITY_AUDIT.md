# RIFT: Final Baseline Integrity Audit

**Lead Investigator:** Agent B (Baseline & Benchmark Integrity Auditor)  
**Date:** 2026-11-02  
**Authority:** Final Scientific Verification Gate §2  

---

## 1. Baseline Performance Summary (Development Split, $n=50$)

```
┌─────────────────────────┬───────────┬──────────────┬───────────────┬────────────┐
│ Method                  │ Raw P@1   │ Cond. P@1    │ Abstention %  │ FAR        │
├─────────────────────────┼───────────┼──────────────┼───────────────┼────────────┤
│ B1-LATENCY-CORR         │ 100.00%   │ 100.00%      │ 0.00%         │ 0.00%      │
│ RIFT-RANDOM             │ 98.00%    │ 98.00%       │ 0.00%         │ 2.00%      │
│ RIFT-ONE-SHOT           │ 98.00%    │ 98.00%       │ 0.00%         │ 2.00%      │
│ SIEVE-LIKE              │ 72.00%    │ 72.00%       │ 0.00%         │ 28.00%     │
│ RIFT-FULL (Learned FCI) │ 0.00%     │ 0.00%        │ 100.00%       │ 0.00%      │
│ RIFT-FULL (Oracle PAG)  │ 26.00%    │ 100.00%      │ 74.00%        │ 0.00%      │
└─────────────────────────┴───────────┴──────────────┴───────────────┴────────────┘
```

---

## 2. In-Depth Root Cause Verification

### 2.1 B1-LATENCY-CORR: 100% Precision
- **Source File:** `src/rift/baselines/latency_correlation.py:34-86`
- **Mechanism:** Combines earliest threshold crossing time $t_{\text{trig}}$ and $z$-score amplitude.
- **Root Cause:** In synthetic step faults (`generate_scenario_metrics()`), the root cause exhibits instantaneous latency jumps at $t_{\text{inject}}$, while downstream effects are delayed by propagation hops ($+10\text{s}, +20\text{s}$). The root cause is both the earliest and highest anomaly. This is not label leakage; it reflects the idealized nature of step synthetic data.

### 2.2 RIFT-RANDOM & RIFT-ONE-SHOT: 98% Precision
- **Source Files:** `src/rift/baselines/rift_random.py:163-280`, `src/rift/baselines/rift_one_shot.py:22-68`
- **Mechanism:** Initial candidates and priors are populated by EBD anomaly detection.
- **Root Cause:** Because EBD anomaly ranking puts the root cause at rank 1 in 98% of synthetic step scenarios, random selection reaches the same top-1 diagnosis while consuming twice the intervention duration (60s vs 30s).

### 2.3 SIEVE-LIKE: 28% False Attribution Rate
- **Source File:** `src/rift/baselines/sieve_like.py:21-118`
- **Mechanism:** Propagation score recursively aggregates downstream child anomaly scores.
- **Root Cause:** On confounded scenarios ($n=24$), unobserved shared resource degradation propagates upward into innocent callers (e.g., `frontend`), causing false attributions in 28% of cases.

### 2.4 RIFT-FULL (Learned FCI): 100% Abstention
- **Source File:** `src/rift/fci/fci_runner.py:195-245`, `src/rift/ebd/ebd.py:154-210`
- **Mechanism:** Criterion R3 requires directed or semi-directed paths in the learned PAG.
- **Root Cause:** With $N=18$ contemporaneous samples, FCI outputs unoriented circle marks (`o->`, `o-o`) on tree graphs without unshielded colliders. RIFT's identifiability engine safely abstains (FAR = 0.00%) rather than guessing. Under Oracle PAG, conditional precision is 100.00%.
