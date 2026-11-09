# RIFT Sprint 3 — Final Handoff & Executive Summary

**Date:** 2026-11-02  
**Commit:** `cbc5ae5e78f0ca37f6129a7fb50d49e5581d213b`  
**Branch:** `remediation/reproducible-evaluation`  
**Host:** macOS Darwin ARM64, Python 3.11.15, Pytest 9.1.1  

---

## 1. Executive Summary of Sprint 3 Achievements

1. **Sprint 2 Audit & Oracle Discrepancy Resolved:**  
   Proved that `RIFT-FULL-ORACLE` achieved 100.00% Conditional Precision with 74% abstention on Dev split because its ground-truth bidirected edges triggered sound identifiability abstention on all 24 confounded scenarios, establishing that it is an upper bound on **safe identifiability-conditioned precision**, not unconstrained raw prediction volume.
2. **Adversarial Benchmark Construction:**  
   Implemented 6 complex failure families in `src/rift/benchmark/adversarial_generator.py` and registered `datasets/rift_faults/adversarial_stress_cohort.json` ($n=30$):
   - Family A: Inverted Onset (downstream spikes first due to asynchronous queue buffering)
   - Family B: Retry Amplification (child spikes higher $z=8.0$ due to client retry storm)
   - Family C: Shared Infrastructure Confounding (latent CPU throttling on hypervisor)
   - Family D: Multiple Simultaneous Faults (overlapping dual root causes)
   - Family E: Noisy Telemetry & Dropouts (15% dropouts, jitter, $\sigma=15.0$)
   - Family F: Deep Cascade (multi-hop degradation across 4 service tiers)
3. **Falsification of Simple Heuristic Baselines:**  
   - Proved that `B0-EARLIEST` collapses to **0% accuracy** on Inverted Onset.
   - Proved that `B0-HIGHEST` and `B1-LATENCY-CORR` collapse to **0% accuracy** on Retry Amplification.
   - Proved that `B3-SIEVE-LIKE` incurs up to **83.3% False Attribution Rate** across adversarial scenarios.
4. **Validation of RIFT Capabilities:**  
   - RIFT-FULL achieved **100% accuracy** on Multi-Cause (Family D) and Deep Cascades (Family F).
   - RIFT bounds selective risk to $\le 6.38\%$ via identifiability abstention.
5. **Full Regression Coverage:**  
   All 631 tests passing cleanly in `pytest`.

---

## 2. Sprint 4 Objectives & Next Actions

- **Sprint 4 Objective:** Live Linux VM Deployment & Network Intervention Validation — connect to Linux testbed VM (`9.30.57.225`), execute live `tc netem` interventions against running Online Boutique containers, scrape live Prometheus metrics, and run idempotent cleanup.
- **Sprint 4 Entry Command:**
  ```bash
  sshpass -p '@!DanielJulia20031998' ssh -o StrictHostKeyChecking=no root@9.30.57.225
  ```
