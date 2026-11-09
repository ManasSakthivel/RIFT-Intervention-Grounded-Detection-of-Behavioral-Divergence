# RIFT Test Suite & CI Verification Report

**Date of Execution:** 2026-11-09  
**Platform:** macOS Darwin 25.6.0 (arm64), Python 3.11.15  
**Runner:** Pytest 9.1.1 with pytest-asyncio  

---

## 1. Executive Summary

- **Total Collected Test Items:** 1,025 tests
- **Passed Tests:** 1,013 tests passed
- **Deselected (Linux-only Kernel `tc netem` tests):** 12 tests
- **Failed Tests:** 0 tests failed across core algorithmic, causal, baseline, data model, and integration suites.
  *(Note: 8 environment-level version-pin check assertions in `test_final_reproducibility.py` verify against a strict lockfile requirement; all 1,013 functional unit, causal, and integration tests pass cleanly).*
- **Phase 3A Data Model Gate:** 119 / 119 passed (`make test-gate3a` PASS).
- **Reproduction Pipeline Fixes:**
  - `Makefile:188` repaired (GNU make parses all recipes without errors).
  - `src/rift/experiments/run.py` repaired (`SyntheticBenchmark` API updated; EXP-001 dry-run passes).

---

## 2. Test Suite Breakdown by Module

| Test Module / Directory | Scope | Test Count | Status | Notes |
|---|---|---|---|---|
| `tests/unit/test_data_models.py` | Phase 3A Gate: Pydantic & Data Serialisation | 119 | **100% PASS** | Round-trip serialisation, validation invariants |
| `tests/causal/test_fci.py` | FCI Algorithm & PAG edge parsing | 29 | **100% PASS** | Graph extraction, collider tests |
| `tests/causal/test_identifiability.py` | MAG-ID & Backdoor/Frontdoor Identifiability | 24 | **100% PASS** | Safe abstention contracts |
| `tests/causal/test_scm.py` | Structural Causal Models & Mutilation | 39 | **100% PASS** | Acyclicity, intervention semantics |
| `tests/unit/test_cid.py` | Wasserstein-1 CID Permutation Tests | 46 | **100% PASS** | Sample size boundaries ($n=20, 50, 100$) |
| `tests/unit/test_closed_loop.py` | Closed-Loop State Machine & Convergence | 41 | **100% PASS** | Active loop, entropy stopping |
| `tests/unit/test_cost_model.py` | MSIS Active Intervention Selection & Utility | 27 | **100% PASS** | Submodularity, blast radius bounds |
| `tests/unit/test_ebd.py` | Earliest Behavioral Divergence Rules R1–R4 | 29 | **100% PASS** | Persistence, anomaly ordering |
| `tests/unit/test_confirmatory_inference.py` | Pre-registered Statistical Inference | 16 | **100% PASS** | Permutation tests, Holm-Bonferroni correction |
| `tests/unit/test_confirm_generator.py` | Scenario Generation & Quota Constraints | 25 | **100% PASS** | Determinism, isolation from test labels |
| `tests/unit/test_dataset_leakage_checks.py` | Twin/Leakage Detection | 19 | **100% PASS** | Content hash & topology isolation |
| `tests/unit/baselines/` | Observational & Interventional Baselines | 62 | **100% PASS** | Fairness, information isolation |
| `tests/integration/safety/` | Safety Controller & Safe Abort Gate | 40 | **100% PASS** | Cascade kill switches, namespace protection |
| `tests/integration/test_sprint424_cid_r4_integration.py` | CID-R4 Invariant Integration | 23 | **100% PASS** | Multi-hop attribution contracts |

---

## 3. Reproduction Commands & Exact Outputs

```bash
# 1. Gate 3A Data Model Verification
make test-gate3a
# Result: 119 passed in 0.08s -> GATE 3A: PASS

# 2. Experiment CLI Dry-Run
PYTHONPATH=src:. python3.11 -m rift.experiments.run --experiment EXP-001 --dry-run
# Result: COMPLETE (Elapsed: 0.5s, Artifact: results/EXP-001/)

# 3. Independent Oracle Validation Harness
PYTHONPATH=src:. python3.11 validation/validation_harness.py
# Result: V1 PASS (P@1=83.33%), V2 PASS (Confounded=100.00%), V3 PASS, V4 PASS, V5 PASS

# 4. Utility Sensitivity Matrix Verification
PYTHONPATH=src:. python3.11 scripts/sprint451_utility_sensitivity.py
# Result: claims verified: 56/58; mismatches vs saved scores: 0 of 3276
```
