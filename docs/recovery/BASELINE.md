# RIFT Recovery — Baseline Snapshot

**Snapshot Timestamp:** 2026-11-09T05:01:00Z  
**Repository Path:** `/Users/manassakthivel/Desktop/RIFT FINAL`  
**Host Platform:** macOS Darwin 25.6.0 (arm64), Python 3.11.15  
**Current HEAD Commit:** `ebad911087942f257ba434f69816ed6d692be170`  
**Active Git Branch:** `remediation-and-manuscript-closure` (synchronized with `origin/main` at `ebad911087942f257ba434f69816ed6d692be170`)  

---

## 1. Working Tree & Git Status

At baseline establishment, the local repository contains:
- **Tracked Modified Files (16):**
  - `.github/workflows/test.yml`
  - `README.md`
  - `analysis/tables/table4_scenarios.py`
  - `artifacts/phase3/cid_validation.json`
  - `artifacts/phase3/independent_validation_report.json`
  - `configs/live.yaml`
  - `datasets/rift_faults/manifest.json`
  - `requirements.txt`
  - `scripts/verify_heldout_sealed.py`
  - `src/rift/fault_injection/fault_injector.py`
  - `src/rift/intervention/backends/linux_tc_netem.py`
  - `src/rift/intervention/network_intervention.py`
  - `src/rift/pipeline/e2e_runner.py`
  - `src/rift/safety/safety.py`
  - `tests/unit/test_network_intervention.py`
  - `validation/run_cid_validation.py`
- **Untracked Directories and Files (over 100 items):**
  - Sprint 4.2.x, 4.3.0, 4.4.x, 4.5.x audit documents, test suites, and scripts in `docs/`, `scripts/`, `tests/`
  - Result artifacts in `artifacts/sprint4_3_0/`, `artifacts/final_closure/`, `artifacts/evaluation/`
  - Generated verification outputs in `results/local_verify/`

---

## 2. Baseline Test Results & Failures

Initial command execution across standard entry points revealed the following baseline status:

| Entry Point / Command | Result | Root Cause / Diagnosis |
|---|---|---|
| `make reproduce-all` / `make test` | **FAILED (Exit 2)** | Syntax error in `Makefile:188` (`pre-linux-check` target python multiline string lacks leading tab separator). |
| `python3.11 validation/validation_harness.py` | **PASSED (Exit 0)** | Development set independent validation passes V1 (P@1=83.33%, 10/12), V2 (Confounded abstention=100%, 24/24), V3, V4, V5. Note: Oracle PAG upper bound. |
| `python3.11 scripts/sprint451_utility_sensitivity.py` | **PASSED (Exit 0)** | 56/58 sensitivity claims verified against saved score matrix across 3,276 pairs. |
| `python3.11 -m rift.experiments.run --experiment EXP-001 --dry-run` | **FAILED (Exit 1)** | `TypeError: SyntheticBenchmark() takes no arguments` at `src/rift/experiments/run.py:185`. |
| `make test-intervention` | **FAILED (Exit 2)** | Makefile syntax error parsing at line 188. |

---

## 3. Dataset Lineage & Roles

1. **Synthetic Development Benchmark (`datasets/rift_faults/manifest.json` / `src/rift/benchmark/synthetic_benchmark.py`):**
   - 36 development scenarios (12 non-confounded, 24 confounded).
   - Used for exploratory tuning and oracle validation harness.
2. **RIFT v2 / Sprint 4.3.0 Generated Scenarios (`datasets/rift_v2/`, `datasets/rift_faults/`):**
   - Held-out candidate sets and adversarial stress cohorts generated in Sprint 4.3.0.
   - Contains 50 dev, 18 val, and legacy/sealed held-out evaluation splits.
3. **Live Linux Microservice Testbed (`deploy/podman-compose.yaml`):**
   - 14-container Google Online Boutique microservice stack with OpenTelemetry Collector and Prometheus on RHEL 9.6 (`9.30.57.225`).
   - Single real testbed target with historical Stage 4 live netem trace (`artifacts/stage4_intervention_results.json`).

---

## 4. Current Claimed Metrics Origin & Provenance

- **Precision@1 = 83.33% (10/12 non-confounded development scenarios):** From `validation/validation_harness.py` using oracle PAG.
- **Confounded Abstention = 100.00% (24/24 development scenarios):** From `validation/validation_harness.py`.
- **Pre-registered V3 vs AA Mean Utility:** Strict template = `-0.338` (V3) vs `-0.562` (V2); Operational template = `-0.195` (V3) vs `-0.363` (V2) at λ=2, γ=1 from `artifacts/sprint4_5_1/utility/utility_verification.json`.
- **Unsupported / Unverifiable Claims in circulation:**
  - `P@1 = 0.875 (35/40)`: Does not exist in any file.
  - `3 Testbeds`: Only 1 testbed (Online Boutique) is implemented.
  - `25/25 Negative-control abstentions`: Unproduced (actual dev split has 24 confounded scenarios).

---

## 5. Current Reproduction Instructions & Known Blockers

1. **Reproduction Blocker 1:** GNU `make` targets cannot parse `Makefile` due to space indentation on line 188.
2. **Reproduction Blocker 2:** Experiment runner `src/rift/experiments/run.py` passes `seed` keyword argument to `SyntheticBenchmark()`, raising `TypeError`.
3. **Reproduction Blocker 3:** `SyntheticBenchmark` scenario extraction assumes dict semantics in parts of runner whereas `FaultScenario` is a Pydantic/dataclass object.
4. **Environment Blocker:** Native `tc netem` network kernel interventions require Linux `CAP_NET_ADMIN` and cannot execute natively on macOS Darwin host (must be mocked, containerized, or skipped with `pytest -k "not linux_only"`).
