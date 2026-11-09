# RIFT Sprint 3.1 — Final Audit & QA Handoff Report

**Date:** 2026-11-02  
**Starting Commit:** `cbc5ae5e78f0ca37f6129a7fb50d49e5581d213b`  
**Active Branch:** `remediation/reproducible-evaluation`  
**Host Runtime:** macOS Darwin ARM64, Python 3.11.15, Pytest 9.1.1  
**Target QA VM:** Linux `9.30.57.225:22` (Authentication Verified)  

---

## 1. Executive Summary of Audit Findings

1. **Metric Reconciliation Resolved:**  
   Proved that in the Adversarial Stress Benchmark ($n=30$), Conditional Precision of $56.00\%$ mathematically implies a **Selective Risk of $44.00\%$** (since $\text{Selective Risk} = 1 - \text{CondP1} = 11/25 = 44.00\%$). The previously cited $6.38\%$ figure was from the **Sprint 2 Development Split ($n=50$)** where $I=3, P=47 \implies 3/47 = 6.38\%$.
2. **Oracle PAG Validity Dissected:**  
   `RIFT-FULL-ORACLE` aggregate accuracy (14/30 = 46.7%) matched `RIFT-FULL` due to family compensation: Oracle achieved 40% on Family B (Retry) and 100% correct abstention on Family C (Confounding), while Learned FCI missed confounding and emitted predictions. `RIFT-FULL-ORACLE` is an upper bound on **safe identifiability-conditioned diagnostic precision**, not raw prediction volume.
3. **Baseline Independence Confirmed:**  
   Unit tests (`tests/unit/baselines/test_baseline_independence.py`) confirmed that `B0-HIGHEST`, `B1-LATENCY-CORR`, `B6-RIFT-RANDOM`, and `B4-RIFT-ONE-SHOT` execute independent decision algorithms, and that their identical 22/30 scores arise because steady-state synthetic anomaly magnitude dominated top candidate selection across these 4 baselines.
4. **Adversarial Failure Families Validated:**  
   Demonstrated that earliest-onset heuristics collapse to **0% accuracy** on Inverted Onset (Family A), and amplitude heuristics collapse to **0% accuracy** on Retry Amplification (Family B), proving that simple correlation heuristics fail under realistic cloud failure dynamics.
5. **Full Regression Coverage:**  
   All 632 unit and integration tests passing cleanly.

---

## 2. Final Recommendation for Live QA Testing

**Verdict:** **`READY FOR LIVE QA EXPERIMENTS`**

All benchmark metrics are reconciled, baseline independence is verified, adversarial failure modes are validated, and deployment prerequisites for the Linux QA VM are documented and verified.
