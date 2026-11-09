# RIFT: Multi-Sprint Research Programme Plan (IEEE Access Track)

**Lead Architect:** Principal Research Scientist  
**Date:** 2026-11-02  
**Target Publication:** IEEE Access (Software Engineering / Distributed Systems Track)  

---

## 1. Multi-Sprint Programme Roadmap

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                             RIFT Multi-Sprint Research Roadmap                              │
├──────────┬──────────────────────────────────────┬───────────────────────────────────────────┤
│ Sprint   │ Focus Area                           │ Core Deliverables                         │
├──────────┼──────────────────────────────────────┼───────────────────────────────────────────┤
│ Sprint 1 │ Forensic Audit & Reproducible Base   │ 626 tests green, baseline dissection,     │
│          │ (Current Sprint)                     │ multi-split evaluation, gap register.     │
├──────────┼──────────────────────────────────────┼───────────────────────────────────────────┤
│ Sprint 2 │ Causal Discovery & Prior Integration │ Tracing-graph prior integration in FCI,   │
│          │                                      │ semi-directed path handling in EBD (R3).  │
├──────────┼──────────────────────────────────────┼───────────────────────────────────────────┤
│ Sprint 3 │ Advanced Benchmark Stress-Testing    │ Inverted onsets, retry storms, non-linear │
│          │                                      │ cascading failures, noisy telemetry.      │
├──────────┼──────────────────────────────────────┼───────────────────────────────────────────┤
│ Sprint 4 │ Live Linux VM & Infrastructure Run   │ tc netem execution on Online Boutique,    │
│          │                                      │ live Prometheus scraping & safe cleanup.  │
├──────────┼──────────────────────────────────────┼───────────────────────────────────────────┤
│ Sprint 5 │ Final Manuscript & IEEE Submission   │ Complete paper refactoring, camera-ready  │
│          │ Package                              │ artifacts, replication package freeze.    │
└──────────┴──────────────────────────────────────┴───────────────────────────────────────────┘
```

---

## 2. Detailed Sprint Specifications

### Sprint 2: Causal Discovery & Prior Integration
- **Objective:** Enable non-zero coverage on learned graphs by integrating static distributed tracing topology as structural priors for FCI edge orientation.
- **Tasks:**
  1. Add prior knowledge constraint matrix to `fci_runner.py`.
  2. Update EBD Criterion R3 to evaluate semi-directed paths over background-constrained PAGs.
  3. Validate coverage increase without inflating False Attribution Rate.

### Sprint 3: Advanced Benchmark Stress-Testing
- **Objective:** Evaluate RIFT on failure scenarios where simple onset-time correlation fails.
- **Tasks:**
  1. Implement `stress_test_cohort.json` based on `docs/BENCHMARK_STRESS_TEST_PLAN.md`.
  2. Implement asynchronous buffering and client retry amplification models.
  3. Compare RIFT vs `B1-LATENCY-CORR` and `SIEVE-LIKE` on non-trivial topologies.

### Sprint 4: Live Linux VM Deployment & Validation
- **Objective:** Execute live network interventions and Prometheus metric scraping on Linux kernel.
- **Tasks:**
  1. Connect to Linux VM via SSH (`9.30.57.225`).
  2. Execute `scripts/start_testbed.sh` and run live experiment suite (`--live`).
  3. Execute safe, idempotent container and network cleanup script.

### Sprint 5: Final Submission Package & Artifact Freeze
- **Objective:** Finalize IEEE Access submission package.
- **Tasks:**
  1. Refactor manuscript around confirmed contributions and empirical boundaries.
  2. Package all data, code, and runner scripts into an archival replication bundle.
