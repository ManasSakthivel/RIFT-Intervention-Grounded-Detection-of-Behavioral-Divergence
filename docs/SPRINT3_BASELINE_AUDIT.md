# RIFT Sprint 3 — Adversarial Baseline Audit

**Lead Auditor:** Baseline Evaluation Lead  
**Date:** 2026-11-02  
**Authority:** Multi-Baseline Fair Comparison Protocol  

---

## 1. Audited Baselines Summary

```
┌─────────────────────────────────┬────────────────────────────────────────────┬──────────────────────────────────────┐
│ Baseline                        │ Implementation Mechanism                   │ Adversarial Vulnerability            │
├─────────────────────────────────┼────────────────────────────────────────────┼──────────────────────────────────────┤
│ B0-EARLIEST                     │ Earliest threshold crossing time           │ Fails on Family A (Inverted Onset)   │
│ B0-HIGHEST                      │ Maximum z-score amplitude                  │ Fails on Family B (Retry Storm)      │
│ B1-LATENCY-CORR                 │ z-score amplitude / trigger time penalty   │ Fails on Family B (Retry Storm)      │
│ B3-SIEVE-LIKE                   │ Call-graph propagation score               │ Fails on Family C (Confounding)      │
│ B6-RIFT-RANDOM                  │ Random MSIS selection                      │ Fails on Family B (Retry Storm)      │
│ B4-RIFT-ONE-SHOT                │ EBD anomaly score prior                    │ Fails on Family B (Retry Storm)      │
│ RIFT-OBS                        │ Learned FCI backdoor adjustment            │ Abstains on unoriented PAGs          │
│ RIFT-FULL                       │ Semi-directed PAG + Active CID             │ Robust on C, D, F; active in testing │
│ RIFT-FULL-ORACLE                │ Ground-truth PAG + Active CID              │ Safe abstention on confounded cases  │
└─────────────────────────────────┴────────────────────────────────────────────┴──────────────────────────────────────┘
```
