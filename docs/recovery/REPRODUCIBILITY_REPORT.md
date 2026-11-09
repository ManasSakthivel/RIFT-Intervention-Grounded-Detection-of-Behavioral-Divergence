# RIFT Reproducibility & Orchestration Recovery Report

**Date:** 2026-11-09  
**Engineer:** Agent 1 (Experiment Runner & Reproducibility)  

---

## 1. Issues Identified and Repaired

1. **Makefile Syntax Error (`Makefile:188`):**
   - **Diagnosis:** Recipe `pre-linux-check:` contained an inline Python block with unescaped newline indentation, triggering GNU `make` parse failures (`Makefile:188: *** missing separator. Stop.`).
   - **Fix Applied:** Refactored the multiline check into semicolon-chained escaped lines preserving recipe tabs.
   - **Verification:** `make test-gate3a` executes smoothly, returning `GATE 3A: PASS`.

2. **Experiment CLI Runner API Mismatch (`src/rift/experiments/run.py:185`):**
   - **Diagnosis:** `SyntheticBenchmark(seed=seed)` was invoked with a keyword argument `seed`, but `SyntheticBenchmark.__init__` accepts zero arguments (seeds are passed to `generate_all_faults(seed=seed)`). Additionally, `generate_scenarios()` did not exist, and scenario IDs were accessed via dictionary `.get()` instead of dataclass attributes.
   - **Fix Applied:** Updated `_run_synthetic()` in `src/rift/experiments/run.py` to instantiate `SyntheticBenchmark()`, invoke `generate_all_faults(seed=seed)`, filter scenarios by split (`SPLIT_DEVELOPMENT`, `SPLIT_VALIDATION`, `SPLIT_HELD_OUT_TEST`), and access `scenario.fault_id`.
   - **Verification:** `PYTHONPATH=src:. python3.11 -m rift.experiments.run --experiment EXP-001 --dry-run` now executes in 0.5s and outputs structured artifact bundles into `results/EXP-001/`.

3. **Missing Log & Artifact Directories:**
   - **Diagnosis:** Targets running `tee artifacts/logs/<target>.log` failed when `artifacts/logs/` was absent.
   - **Fix Applied:** Ensured `mkdir -p artifacts/logs artifacts/coverage artifacts/phase3 artifacts/phase3_5` is part of standard setup.

---

## 2. Standardized Reproduction Runbook

### Step 1: Environment Setup
```bash
# macOS with Homebrew Python 3.11
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Gate 3A Invariant Validation
```bash
make test-gate3a
```

### Step 3: Fast Core Test Suite
```bash
python3.11 -m pytest tests/unit/ tests/causal/ -v
```

### Step 4: Independent Validation Harness
```bash
PYTHONPATH=src:. python3.11 validation/validation_harness.py
```

### Step 5: Economic Utility & Sensitivity Verification
```bash
PYTHONPATH=src:. python3.11 scripts/sprint451_utility_sensitivity.py
```

### Step 6: End-to-End Experiment Smoke Test
```bash
PYTHONPATH=src:. python3.11 -m rift.experiments.run --experiment EXP-001 --dry-run
```
