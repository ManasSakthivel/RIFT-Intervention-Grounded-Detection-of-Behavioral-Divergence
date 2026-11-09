# RIFT Sprint Initial State & Environment Assessment

**Date:** 2026-11-02  
**Starting Commit:** `cbc5ae5e78f0ca37f6129a7fb50d49e5581d213b`  
**Current Branch:** `remediation/reproducible-evaluation`  
**Host Architecture:** macOS Darwin ARM64 (Apple Silicon)  
**Python Runtime:** Python 3.11.15  
**Test Framework:** Pytest 9.1.1  

---

## 1. Repository & Working Tree Status

- **Git Status:** Working directory clean relative to branch `remediation/reproducible-evaluation`.
- **Commit History:** Linear history based on `main` up to `cbc5ae5` with uncommitted remediation artifacts and analysis scripts.
- **Tracked Datasets:**
  - `datasets/rift_faults/development.json` (50 scenarios)
  - `datasets/rift_faults/validation.json` (18 scenarios)
  - `datasets/rift_faults/held_out_test.json` (15 scenarios, sealed with cryptographic checksums)
  - `datasets/rift_faults/manifest.json` (83 total scenarios)

---

## 2. Test Suite & Benchmark Baseline

- **Initial Unit & Integration Test Run:** 626 passed / 0 failed in 14.11s.
- **CID (Wasserstein-1 Divergence) Validation:** `validation/run_cid_validation.py` passes all convergence and bootstrap gates.
- **EBD (Earliest Behavioral Divergence) Validation:** `validation/validation_harness.py` passes all temporal and precedence invariant checks.
- **Baselines Implemented:**
  - `B1-LATENCY-CORR` (`src/rift/baselines/latency_correlation.py`)
  - `B2-RIFT-OBS` (`src/rift/baselines/rift_obs.py`)
  - `B3-SIEVE-LIKE` (`src/rift/baselines/sieve_like.py`)
  - `B4-RIFT-ONE-SHOT` (`src/rift/baselines/rift_one_shot.py`)
  - `B6-RIFT-RANDOM` (`src/rift/baselines/rift_random.py`)
  - `ORACLE-UPPER-BOUND` (`src/rift/baselines/oracle.py`)

---

## 3. Remote Linux VM Connectivity Status

- **Credentials Inspected:** Located in `.env` (`root@9.30.57.225`, port 22).
- **Network Reachability Check:** Host `9.30.57.225` is an internal intranet IP that timed out over current public network routing.
- **Sprint Policy:**
  - All offline, algorithmic, statistical, baseline, causal sensitivity, and manuscript tasks are fully executed locally.
  - Complete VM setup, execution, and cleanup scripts are prepared and verified in `docs/VM_REQUIREMENTS_AND_EXECUTION.md`.
