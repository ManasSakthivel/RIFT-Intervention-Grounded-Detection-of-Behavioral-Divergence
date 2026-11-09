# RIFT Sprint 3.1 — Reproducibility & Reconciliation Report

**Audit Date:** 2026-11-02  
**Lead Auditor:** Reproducibility Verification Lead  
**Authority:** Task 7 Benchmark Reconciliation  

---

## 1. Metric Reconciliation Table Across Evaluation Cohorts

```
┌─────────────────────────┬───────────────────────┬───────────────────────┬───────────────────────┬───────────────────────┐
│ Method                  │ Dev Split (n=50)      │ Val Split (n=18)      │ Held-Out (n=15)       │ Adversarial (n=30)    │
│                         │ Raw | Cond | Risk     │ Raw | Cond | Risk     │ Raw | Cond | Risk     │ Raw | Cond | Risk     │
├─────────────────────────┼───────────────────────┼───────────────────────┼───────────────────────┼───────────────────────┤
│ RIFT-FULL (Sprint 2)    │ 88.0% | 93.6% | 6.4%  │ 88.9% | 94.1% | 5.9%  │ 93.3% | 93.3% | 6.7%  │ 46.7% | 56.0% | 44.0% │
│ RIFT-FULL-ORACLE        │ 26.0% | 100.0%| 0.0%  │ 22.2% | 100.0%| 0.0%  │ 13.3% | 100.0%| 0.0%  │ 46.7% | 56.0% | 44.0% │
│ RIFT-OBS                │ 0.0%  | 0.0%  | 0.0%  │ 0.0%  | 0.0%  | 0.0%  │ 0.0%  | 0.0%  | 0.0%  │ 0.0%  | 0.0%  | 0.0%  │
│ B1-LATENCY-CORR         │ 100.0%| 100.0%| 0.0%  │ 100.0%| 100.0%| 0.0%  │ 100.0%| 100.0%| 0.0%  │ 73.3% | 73.3% | 26.7% │
│ B3-SIEVE-LIKE           │ 72.0% | 72.0% | 28.0% │ 72.2% | 72.2% | 27.8% │ 80.0% | 80.0% | 20.0% │ 16.7% | 16.7% | 83.3% │
│ B0-EARLIEST             │ 100.0%| 100.0%| 0.0%  │ 100.0%| 100.0%| 0.0%  │ 100.0%| 100.0%| 0.0%  │ 36.7% | 36.7% | 63.3% │
│ B0-HIGHEST              │ 100.0%| 100.0%| 0.0%  │ 100.0%| 100.0%| 0.0%  │ 100.0%| 100.0%| 0.0%  │ 73.3% | 73.3% | 26.7% │
└─────────────────────────┴───────────────────────┴───────────────────────┴───────────────────────┴───────────────────────┘
```

---

## 2. Reproduction Verification

- **Pytest Suite:** 632 / 632 passed in 14.1s.
- **Adversarial Benchmark Runner:** `python3 scripts/run_adversarial_benchmark.py` reproduces exact table metrics from underlying `artifacts/evaluation/adversarial_scenario_predictions.json`.
- **Multi-Split Comparative Runner:** `python3 scripts/run_reproducible_evaluation.py` reproduces exact Dev, Val, and Held-out tables from `artifacts/evaluation/comparative_results_*.json`.
