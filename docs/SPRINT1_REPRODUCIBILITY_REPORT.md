# RIFT — Sprint 1: Forensic Reproducibility & Benchmark Report

**Audit Date:** 2026-11-02  
**Authority:** Clean-Room Verification & Machine-Readable Artifact Generation  

---

## 1. Reproduction Commands & Execution Log

All tests, validation gates, and comparative evaluations were executed from workspace root:

```bash
# 1. Run Complete Test Suite
pytest
# Outcome: 626 passed in 14.11s (Exit Code: 0)

# 2. Run CID Wasserstein-1 Divergence Validation Harness
python3 validation/run_cid_validation.py
# Outcome: GATE: PASS (Exit Code: 0)

# 3. Run Independent EBD Validation Harness
python3 validation/validation_harness.py
# Outcome: GATE: PASS (P@1=83.33%, FAR=0.00%, Exit Code: 0)

# 4. Run Full Comparative Baseline Evaluation (Dev, Val, Held-Out)
python3 scripts/run_reproducible_evaluation.py
# Outcome: Generated artifacts in artifacts/evaluation/ (Exit Code: 0)
```

---

## 2. Multi-Split Comparative Evaluation Table

```
┌─────────────────────────┬───────────────────────┬───────────────────────┬───────────────────────┐
│ Method                  │ Dev Split (n=50)      │ Val Split (n=18)      │ Held-Out (n=15)       │
│                         │ Raw P@1 | Cond | FAR  │ Raw P@1 | Cond | FAR  │ Raw P@1 | Cond | FAR  │
├─────────────────────────┼───────────────────────┼───────────────────────┼───────────────────────┤
│ RIFT-FULL (Learned FCI) │ 0.0%  | 0.0%  | 0.0%  │ 0.0%  | 0.0%  | 0.0%  │ 0.0%  | 0.0%  | 0.0%  │
│ RIFT-FULL (Oracle PAG)  │ 26.0% | 100.0%| 0.0%  │ 22.2% | 100.0%| 0.0%  │ 13.3% | 100.0%| 0.0%  │
│ RIFT-OBS                │ 0.0%  | 0.0%  | 0.0%  │ 0.0%  | 0.0%  | 0.0%  │ 0.0%  | 0.0%  | 0.0%  │
│ SIEVE-LIKE              │ 72.0% | 72.0% | 28.0% │ 72.2% | 72.2% | 27.8% │ 80.0% | 80.0% | 20.0% │
│ RIFT-RANDOM             │ 98.0% | 98.0% | 2.0%  │ 100.0%| 100.0%| 0.0%  │ 100.0%| 100.0%| 0.0%  │
│ RIFT-ONE-SHOT           │ 98.0% | 98.0% | 2.0%  │ 100.0%| 100.0%| 0.0%  │ 100.0%| 100.0%| 0.0%  │
│ B1-LATENCY-CORR         │ 100.0%| 100.0%| 0.0%  │ 100.0%| 100.0%| 0.0%  │ 100.0%| 100.0%| 0.0%  │
│ ORACLE UPPER BOUND      │ 100.0%| 100.0%| 0.0%  │ 100.0%| 100.0%| 0.0%  │ 100.0%| 100.0%| 0.0%  │
└─────────────────────────┴───────────────────────┴───────────────────────┴───────────────────────┘
```

---

## 3. Dissection of Baseline Performance

1. **`B1-LATENCY-CORR` (100% P@1):**  
   In single-step synthetic faults, the root cause is simultaneously the earliest threshold trigger and the highest amplitude anomaly.
2. **`SIEVE-LIKE` (20–28% False Attribution Rate):**  
   Call-graph propagation falsely aggregates downstream child anomalies into innocent callers under unmeasured confounding.
3. **`RIFT-RANDOM` (98–100% P@1):**  
   Inherits the top candidate from EBD anomaly scoring, but consumes twice the perturbation time ($60\text{s}$ vs $30\text{s}$).
4. **`RIFT-FULL` (Learned FCI) Abstention:**  
   Conservative abstention prevents false attributions (0.00% FAR) when contemporaneous FCI yields unoriented circle marks.
