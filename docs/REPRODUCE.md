# RIFT: Complete Reproduction Guide

This document describes how to reproduce all tests, validation harnesses, baseline comparisons, and statistical analyses locally.

---

## 1. Environment Requirements

- **Platform:** macOS (darwin arm64/x86_64) or Linux (x86_64)
- **Python Version:** Python 3.11 (tested with 3.11.15)
- **Dependencies:** `pip install -r requirements.txt`

---

## 2. Fast Verification (Test Suite)

Run the full local unit and integration test suite:

```bash
# Run pytest (626 tests)
python3.11 -m pytest tests/ -v

# Run targeted test suites
make test-unit          # Unit tests
make test-causal        # Causal & Identifiability tests
make test-safety        # Safety hard-stops
make test-baselines     # Baseline implementations
```

Expected output: `626 passed in ~14s`.

---

## 3. Independent Component Validations

```bash
# 1. CID (Wasserstein-1 Distributional Divergence & Permutation Test)
python3.11 validation/run_cid_validation.py

# 2. Independent EBD Validation Harness
python3.11 validation/validation_harness.py

# 3. Held-Out Test Set Integrity Verification
python3.11 scripts/verify_heldout_sealed.py
```

Expected output: All validation harnesses report `GATE: PASS`.

---

## 4. End-to-End Comparative Evaluation

To execute all baselines (`RIFT-FULL`, `RIFT-FULL-ORACLE`, `RIFT-OBS`, `SIEVE-LIKE`, `RIFT-RANDOM`, `RIFT-ONE-SHOT`, `B1-LATENCY-CORR`, `ORACLE-UPPER-BOUND`) on both Development ($n=50$) and Validation ($n=18$) splits and compute statistical hypothesis tests with Holm-Bonferroni correction:

```bash
python3.11 scripts/run_reproducible_evaluation.py
```

Generated artifacts:
- `artifacts/evaluation/comparative_results_development.json`
- `artifacts/evaluation/comparative_results_validation.json`
- `artifacts/evaluation/statistical_test_results.json`

---

## 5. Live Linux Testbed Execution (When VM Provisioned)

When the Linux VM with Docker and `CAP_NET_ADMIN` is available:

```bash
# 1. Start Online Boutique microservices testbed
./scripts/start_testbed.sh

# 2. Verify health and Prometheus connectivity
./scripts/health_check_testbed.sh

# 3. Run live interventional experiments
python3.11 -m rift.experiments.run --experiment EXP-001 --live
```
