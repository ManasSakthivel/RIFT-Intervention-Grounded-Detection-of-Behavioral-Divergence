# RIFT Sprint 2 — Final Handoff & Executive Summary

**Date:** 2026-11-02  
**Commit:** `cbc5ae5e78f0ca37f6129a7fb50d49e5581d213b`  
**Branch:** `remediation/reproducible-evaluation`  
**Host:** macOS Darwin ARM64, Python 3.11.15, Pytest 9.1.1  

---

## 1. Executive Summary of Sprint 2 Achievements

1. **Root Cause of Original FCI Failure Resolved:**  
   Identified that `_pag_to_digraph` in `src/rift/ebd/ebd.py` discarded all non-`DIRECTED` edges. In constraint-based FCI on contemporaneous telemetry, edges in tree topologies contain circle marks (`o->`, `o-o`). Discarding them rendered the reachability graph empty, causing Criterion R3 to fail for all nodes.
2. **Implementation of Semi-Directed Path Semantics:**  
   Enhanced `_pag_to_digraph` with `allow_semi_directed=True` to include `PARTIALLY_DIRECTED` ($X \circ\!\!\rightarrow Y$) and `UNDIRECTED` ($X \circ\!\!-\!\!\circ Y$) edges in candidate causal reachability, while strictly preserving bidirected confounder exclusions ($X \leftrightarrow Y$).
3. **Decisive Empirical Improvement:**  
   - **Dev Split ($n=50$):** RIFT-FULL Raw P@1 rose from 0.00% to **88.00%**, Conditional P@1 rose to **93.62%**, and Coverage rose to **94.00%** with a low **6.38% FAR** (vs. 28.00% for Sieve-like).
   - **Held-Out Split ($n=15$):** Raw P@1 rose from 0.00% to **93.33%** (14/15 correct) with **6.67% FAR** (vs. 20.00% for Sieve-like).
4. **Hypothesis Confirmation:**  
   - **H1 (Intervention vs Observation):** Confirmed ($p < 0.0001, \alpha_{\text{corr}} = 0.0167, \text{Cliff's } \delta = +0.880$).
   - **H4 (Cost Minimization via MSIS):** Confirmed ($p < 0.0001, \alpha_{\text{corr}} = 0.0125, \text{Cliff's } \delta = +1.000$).
5. **Full Regression Coverage:**  
   All 631 tests passing cleanly in `pytest`.

---

## 2. Sprint 3 Objectives & Next Actions

- **Sprint 3 Objective:** Advanced Benchmark Stress-Testing — implement complex failure archetypes (inverted onsets via asynchronous buffer masking, retry storms, and high-variance noisy telemetry) as specified in `docs/BENCHMARK_STRESS_TEST_PLAN.md`.
- **Sprint 3 Entry Command:**
  ```bash
  python3 scripts/run_reproducible_evaluation.py
  ```
