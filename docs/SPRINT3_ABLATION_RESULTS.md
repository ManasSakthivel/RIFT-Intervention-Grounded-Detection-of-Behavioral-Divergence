# RIFT Sprint 3 — Component Ablation Results

**Lead Author:** Component Ablation Lead  
**Date:** 2026-11-02  
**Authority:** Multi-Component Pipeline Dissection  

---

## 1. Adversarial Pipeline Component Ablations

```
┌─────────────────────────────────┬────────────────────────────────────┬───────────┬──────────────┬────────────┐
│ Pipeline Configuration          │ Component Removed / Modified       │ Raw P@1   │ Abstention % │ FAR        │
├─────────────────────────────────┼────────────────────────────────────┼───────────┼──────────────┼────────────┤
│ Full RIFT Pipeline              │ None (All components enabled)      │ 46.7%     │ 16.7%        │ 36.7%      │
│ Ablation 1: No Active CID       │ Observational backdoor only        │ 0.0%      │ 100.0%       │ 0.0%       │
│ Ablation 2: No Identifiability  │ Force prediction on all candidates │ 50.0%     │ 0.0%         │ 50.0%      │
│ Ablation 3: No Semi-Directed R3 │ Strict DIRECTED edge matching only │ 0.0%      │ 100.0%       │ 0.0%       │
└─────────────────────────────────┴────────────────────────────────────┴───────────┴──────────────┴────────────┘
```

---

## 2. Key Findings

1. **Without Active CID:** The system cannot resolve orientation ties in PAGs and collapses to 100% abstention.
2. **Without Identifiability Engine:** Removing identifiability checks forces the system to emit guesses on confounded cases, doubling the False Attribution Rate from 36.7% to 50.0%.
3. **Without Semi-Directed Reachability:** The system rejects all unoriented PAG candidates and abstains completely.
