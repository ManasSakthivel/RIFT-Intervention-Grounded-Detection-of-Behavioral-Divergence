# RIFT Phase 4.5 Mac Readiness Report

**File:** `docs/PHASE_4_5_MAC_READINESS_REPORT.md`  
**Generated:** Phase 4.5 Mac Development Sprint  
**Status:** COMPLETE  
**Authority:** Tasks T1–T18 completion records

---

## Executive Summary

Phase 4 Linux execution achieved CONDITIONAL PASS (513/513 tests, all infrastructure gates).
Three implementation blockers prevented full live E2E execution.
This phase 4.5 sprint resolved all three blockers on Mac and built the complete
research infrastructure. The system is now READY_FOR_LINUX final execution.

---

## Gate Checklist

### Infrastructure Gates

| Gate | Description | Status | Evidence |
|---|---|---|---|
| 4A | Linux environment verified | ✅ PASS (frozen) | `artifacts/phase4/environment/linux_environment.json` |
| 4B | 513/513 tests pass on Linux | ✅ PASS (frozen) | `artifacts/phase4/PHASE_4_MANIFEST.json` |
| 4C | Online Boutique 14 containers | ✅ PASS (frozen) | `artifacts/phase4/testbed/health.json` |
| 4D | Live telemetry ingestion | ⚠️ CONDITIONAL (T1 fixed) | T1 fix deployed; NOT_LIVE_VALIDATED |
| 4E | tc/netem verified | ✅ PASS (frozen) | `artifacts/phase4/intervention/net1_latency.json` |
| 4F | Fault injection | ⚠️ CONDITIONAL (T3 fixed) | T3 fix deployed; READY_FOR_LINUX |
| 4G | First E2E run | ⚠️ CONDITIONAL | T1+T2+T3 needed; fixes now deployed |
| 4H | Baselines implemented | ✅ PASS | All baselines + fairness checks (T7) |
| 4I | Development benchmark | ✅ PASS | 36 scenarios, all splits defined |
| 4J | Oracle vs FCI | ✅ PASS (frozen) | `artifacts/phase4/oracle_vs_fci/comparison.json` |
| 4K | Confounding scenarios | ✅ PASS | 48 confounded scenarios available |
| 4L | Repeatability | ✅ PASS (frozen) | Same seed → same result (mock) |
| 4M | Performance | ✅ PASS | Stage timings implemented |
| 4N | Safety 8/8 | ✅ PASS (frozen) | `artifacts/phase4/safety/live_safety_results.json` |

### Mac Development Sprint Gates (Phase 4.5)

| Task | Description | Status | Artifact |
|---|---|---|---|
| T1 | PrometheusClient.collect() implemented | ✅ COMPLETE | `src/rift/pipeline/e2e_runner.py` |
| T1 | Unit tests: 16 tests, all PASS | ✅ COMPLETE | `tests/unit/test_prometheus_client.py` |
| T2 | OTel Collector wired to docker-compose | ✅ COMPLETE | `docker/docker-compose.yml` |
| T2 | Prometheus scrapes OTel (not boutique direct) | ✅ COMPLETE | `docker/prometheus.yml` |
| T2 | LIVE_DATA_PATH.md created | ✅ COMPLETE | `docs/telemetry/LIVE_DATA_PATH.md` |
| T3 | tc band bug fixed (10: → 1:, 2:, 3:) | ✅ COMPLETE | `src/rift/intervention/network_intervention.py` |
| T3 | NetworkInterventionSpec added | ✅ COMPLETE | same file |
| T3 | Unit tests: 33 tests, all PASS | ✅ COMPLETE | `tests/unit/test_network_intervention.py` |
| T4 | Phase 4 evidence reconciliation | ✅ COMPLETE | `docs/phase4/PHASE4_EVIDENCE_RECONCILIATION.md` |
| T5 | Experiment registry audited (14 experiments, EXP-013/014 added) | ✅ COMPLETE | `experiments/REGISTRY.yaml` |
| T6 | RQ → Experiment map | ✅ COMPLETE | `docs/research/RQ_EXPERIMENT_MAP.md` |
| T7 | Baseline fairness audit + 22 automated checks | ✅ COMPLETE | `tests/unit/baselines/test_baseline_fairness.py` |
| T8 | Ablation framework (8 conditions, ABLATION_PLAN.md) | ✅ COMPLETE | `experiments/ablations/`, `docs/experiments/ABLATION_PLAN.md` |
| T9 | Robustness plan (7 fault classes + 5 telemetry modes) | ✅ COMPLETE | `docs/experiments/ROBUSTNESS_PLAN.md` |
| T10 | Complete evaluator (attribution + runtime + cost + CIs) | ✅ COMPLETE | `src/rift/evaluation/complete_evaluator.py` |
| T11 | Statistical analysis pipeline (Category C guard) | ✅ COMPLETE | `analysis/run_analysis.py` |
| T12 | Figure generators (5 figures, placeholder-safe) | ✅ COMPLETE | `analysis/figures/generate_figures.py` |
| T13 | Table generators (4 tables, CSV+JSON+LaTeX) | ✅ COMPLETE | `analysis/tables/generate_tables.py` |
| T14 | Claims registry audited (13 claims, C011-C013 added) | ✅ COMPLETE | `docs/CLAIMS_REGISTRY.yaml` |
| T15 | Scenario catalog | ✅ COMPLETE | `docs/experiments/SCENARIO_CATALOG.md` |
| T16 | Held-out gate (4/4 checks PASS) | ✅ COMPLETE | `scripts/verify_heldout_sealed.py` |
| T17 | Full Mac test suite: **584 PASS, 0 FAIL, 0 SKIP** | ✅ COMPLETE | pytest results |
| T18 | This report | ✅ COMPLETE | this file |

---

## Test Suite Summary (T17)

```
Platform: macOS (darwin 25.6.0, arm64)
Python: 3.9
Test runner: pytest

Results:
  Total: 584 tests
  PASS:  584
  FAIL:  0
  SKIP:  0
  ERROR: 0

Test collections:
  tests/causal/         — 67 tests (FCI, identifiability, SCM)
  tests/integration/    — 12 tests (safety, fault injection)
  tests/unit/           — 505 tests (all unit tests)
    ├── test_cid.py
    ├── test_closed_loop.py
    ├── test_cost_model.py
    ├── test_data_models.py
    ├── test_ebd.py
    ├── test_leakage.py
    ├── test_network_intervention.py     ← new (T3)
    ├── test_phase36_new_modules.py      ← tc_handle bug fixed
    ├── test_prometheus_client.py        ← new (T1)
    ├── test_statistics.py
    ├── artifacts/
    ├── baselines/
    │   ├── test_baseline_fairness.py    ← new (T7)
    │   ├── test_baselines.py
    │   └── test_baselines_parity.py
    ├── evaluation/
    ├── fault_injection/
    ├── provenance/
    └── telemetry/
```

---

## Three Blocker Resolution Summary

| Blocker | Root Cause | Fix | Status |
|---|---|---|---|
| B1: PrometheusClient.collect() stub | NotImplementedError raised | Implemented HTTP query_range call in `e2e_runner.py` | IMPLEMENTED / MAC_TESTED / NOT_LIVE_VALIDATED |
| B2: Boutique telemetry not wired through OTEL | docker-compose had no OTel Collector; prometheus.yml scraped gRPC ports | Added `otel-collector` service to docker-compose; updated prometheus.yml to scrape OTel on port 8889 | IMPLEMENTED / MAC_TESTABLE / READY_FOR_LINUX |
| B3: tc band bug (1:10 invalid) | `tc_handle="10:"` generated `parent 1:10` (invalid prio band) | `NetworkInterventionRecord.__post_init__` validates band ∈ {1,2,3}; e2e_runner uses `prio_band = (i % 3) + 1` | IMPLEMENTED / MAC_TESTED / READY_FOR_LINUX |

---

## Research Infrastructure Built (Phase 4.5)

| Component | File(s) | Status |
|---|---|---|
| Experiment registry | `experiments/REGISTRY.yaml` | 14 experiments, complete fields |
| Ablation registry | `experiments/ablations/ABLATION_REGISTRY.yaml` | 8 conditions |
| Statistical pipeline | `analysis/run_analysis.py` | H1–H5 + Holm-Bonferroni |
| Figure generators | `analysis/figures/generate_figures.py` | 5 figures |
| Table generators | `analysis/tables/generate_tables.py` | 4 tables (CSV+JSON+LaTeX) |
| Complete evaluator | `src/rift/evaluation/complete_evaluator.py` | All required metrics |
| Claims registry | `docs/CLAIMS_REGISTRY.yaml` | 13 claims, correct statuses |
| Baseline fairness checks | `tests/unit/baselines/test_baseline_fairness.py` | 22 automated tests |
| Held-out gate | `scripts/verify_heldout_sealed.py` | 4/4 checks PASS |
| Scenario catalog | `docs/experiments/SCENARIO_CATALOG.md` | 69 scenarios documented |
| RQ→Experiment map | `docs/research/RQ_EXPERIMENT_MAP.md` | H1–H5 all mapped |
| Robustness plan | `docs/experiments/ROBUSTNESS_PLAN.md` | 12 conditions |
| Ablation plan | `docs/experiments/ABLATION_PLAN.md` | 8 conditions |
| Evidence reconciliation | `docs/phase4/PHASE4_EVIDENCE_RECONCILIATION.md` | A/B/C categories strict |
| Live data path | `docs/telemetry/LIVE_DATA_PATH.md` | Full pipeline documented |

---

## Pre-Linux Checklist for Phase 5

Before deploying to Linux for final execution:

- [ ] `PYTHONPATH=src python3 scripts/verify_heldout_sealed.py` returns GATE PASS
- [ ] `python3 -m pytest tests/ -q` returns 584+ passed, 0 failed
- [ ] `docker-compose up -d` deploys OTel Collector, Prometheus, boutique, jaeger
- [ ] `RIFT_PROMETHEUS_URL=http://prometheus:9090 python3 -c "from src.rift.pipeline.e2e_runner import PrometheusClient; c = PrometheusClient('http://prometheus:9090'); print(c.collect(['frontend'], window_s=60))"` returns non-empty DataFrames
- [ ] One RIFTRunRecord with `live_telemetry_used=True` is produced
- [ ] EXP-001 run on real telemetry; results written to `results/EXP-001/`
- [ ] Phase 5 authorization granted by checking above

---

## Evidence Category Summary

| Category | What It Is | Status |
|---|---|---|
| **A: Linux Infrastructure** | tc/netem, boutique health, safety gates | COMPLETE (frozen) |
| **B: Synthetic/Mock Pipeline** | P@1=0.50/0.60, baselines, repeatability | COMPLETE (frozen) |
| **C: Live RIFT E2E** | live_telemetry_used=True, real P@1 | PENDING_LINUX (after T1+T2+T3 on Linux) |

**ABSOLUTE RULE:** Claims C001–C006, C013 require Category C evidence.
C011–C012 are SUPPORTED by Category A. C007–C010 are PARTIALLY_SUPPORTED by Category B.

---

## RIFT-ONE-SHOT Outstanding Action

EXP-013 (H3 ablation) requires a `RIFT-ONE-SHOT` baseline not yet implemented.

**Required before Phase 5:** Create `src/rift/baselines/rift_one_shot.py`  
This is a RIFT-FULL variant with the closed-loop posterior update disabled.
Tests whether iterative Bayesian update provides benefit on multi-cause faults.
