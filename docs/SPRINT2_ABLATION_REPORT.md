# RIFT Sprint 2 — Ablation and Robustness Analysis

**Lead Investigator:** Experimental Ablation Lead  
**Date:** 2026-11-02  
**Authority:** Information Source & Component Ablation  

---

## 1. Information Source Ablation

```
┌─────────────────────────────────┬──────────────────────┬───────────┬──────────────┬───────────────┬────────────┐
│ Pipeline Variant                │ Information Used     │ Raw P@1   │ Cond. P@1    │ Abstention %  │ FAR        │
├─────────────────────────────────┼──────────────────────┼───────────┼──────────────┼───────────────┼────────────┤
│ Variant 1: Pure Observational   │ Telemetry only       │ 0.00%     │ 0.00%        │ 100.00%       │ 0.00%      │
│ (RIFT-OBS)                      │ (Backdoor adjustment)│           │              │               │            │
├─────────────────────────────────┼──────────────────────┼───────────┼──────────────┼───────────────┼────────────┤
│ Variant 2: Strict Directed Only │ Telemetry + FCI      │ 0.00%     │ 0.00%        │ 100.00%       │ 0.00%      │
│ (Sprint 1 RIFT-FULL)            │ (Strict DIRECTED R3) │           │              │               │            │
├─────────────────────────────────┼──────────────────────┼───────────┼──────────────┼───────────────┼────────────┤
│ Variant 3: Semi-Directed Active │ Telemetry + FCI      │ 88.00%    │ 93.62%       │ 6.00%         │ 6.38%      │
│ (Sprint 2 RIFT-FULL)            │ + Semi-directed R3   │           │              │               │            │
├─────────────────────────────────┼──────────────────────┼───────────┼──────────────┼───────────────┼────────────┤
│ Variant 4: Oracle Graph Bound   │ Ground Truth Causal  │ 26.00%    │ 100.00%      │ 74.00%        │ 0.00%      │
│ (RIFT-FULL-ORACLE)              │ Path (Upper Bound)   │           │              │               │            │
└─────────────────────────────────┴──────────────────────┴───────────┴──────────────┴───────────────┴────────────┘
```

---

## 2. Key Ablation Insights

1. **Semi-Directed Path Reachability is Essential for Non-Zero Coverage:**  
   Without semi-directed path handling, contemporaneous constraint-based discovery discards ambiguous orientations, resulting in 0% coverage.
2. **Active Intervention is the Engine of Disambiguation:**  
   Under semi-directed reachability, observational methods cannot resolve edge directions ($X \circ\!\!-\!\!\circ Y$). Active network intervention ($do(X)$) evaluates downstream Wasserstein-1 divergence ($W_1$), isolating the true root cause with 93.62% conditional precision.
