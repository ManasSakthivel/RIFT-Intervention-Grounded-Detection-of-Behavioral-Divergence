# RIFT — Sprint 1: Final Handoff and Verification Summary

**Date:** 2026-11-02  
**Commit:** `cbc5ae5e78f0ca37f6129a7fb50d49e5581d213b`  
**Branch:** `remediation/reproducible-evaluation`  
**Host:** macOS Darwin ARM64, Python 3.11.15, Pytest 9.1.1  

---

## 1. Executive Summary of Completed Work

1. **Forensic Repository & Test Audit:**  
   - All 626 unit and integration tests executed and passing (0 failures).
   - Independent validation harnesses for Wasserstein-1 CID (`validation/run_cid_validation.py`) and Earliest Behavioral Divergence (`validation/validation_harness.py`) verified with `GATE: PASS`.
2. **Multi-Split Comparative Reproduction:**  
   - Evaluated all 8 baselines across Development ($n=50$), Validation ($n=18$), and strictly sealed Held-Out ($n=15$) splits under a frozen protocol.
   - Generated machine-readable artifacts in `artifacts/evaluation/`.
3. **Baseline Integrity Dissection:**  
   - Proved why `B1-LATENCY-CORR` achieves 100% P@1 on single-step synthetic faults (root cause is simultaneously earliest and highest spike).
   - Proved why `SIEVE-LIKE` suffers 20–28% False Attribution Rate on confounded faults (call-graph propagation blames innocent upstream callers).
   - Proved why `RIFT-FULL` (Learned FCI) abstains 100% of the time on $N=18$ contemporaneous samples (unoriented circle marks trigger safe abstention to guarantee 0% FAR).
   - Verified that under an Oracle PAG prior, RIFT achieves **100.00% Conditional Precision@1** on identifiable cases.
4. **Statistical Verification:**  
   - **H2 (Identifiability Abstention):** Confirmed ($p < 0.0001, \text{Cliff's } \delta = +1.000$).
   - **H4 (Cost Minimization via MSIS):** Confirmed ($p < 0.0001, \text{Cliff's } \delta = +1.000$, 50% perturbation reduction).
   - **H1 & H3:** Accurately reported as unsupported on short-window step data.

---

## 2. Sprint 2 Entry Criteria and Immediate Next Task

- **Sprint 2 Objective:** Integrate distributed tracing call-graph topology as structural background priors into `fci_runner.py` to enable edge orientation and non-zero coverage on learned graphs.
- **Entry Command for Sprint 2:**
  ```bash
  python3 -m pytest tests/causal/test_fci.py tests/causal/test_identifiability.py
  ```
