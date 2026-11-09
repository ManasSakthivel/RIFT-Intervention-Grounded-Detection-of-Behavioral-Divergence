# RIFT — Sprint 1: Forensic Repository & Architecture Audit

**Audit Date:** 2026-11-02  
**Starting Commit:** `cbc5ae5e78f0ca37f6129a7fb50d49e5581d213b`  
**Active Branch:** `remediation/reproducible-evaluation`  
**Host Architecture:** macOS Darwin ARM64 (Apple Silicon)  
**Python Runtime:** Python 3.11.15  
**Test Framework:** Pytest 9.1.1  
**Target Publication Venue:** IEEE Access  

---

## 1. Repository State & Environment

- **Working Directory:** `/Users/manassakthivel/Desktop/RIFT FINAL`
- **Git Status:** Working directory on `remediation/reproducible-evaluation`.
- **Dataset Registry & Cryptographic Hashes (SHA-256):**
  - `datasets/rift_faults/development.json` (`d8960776ee3556a8b98de4767c3e8bd14f430f828983fcf50b0114dce8a1aebd`) — 50 scenarios
  - `datasets/rift_faults/validation.json` (`2363f6bbea6f86eb883525be90151655ca9ddac01aa9ad5b6e8351dc4953d0f3`) — 18 scenarios
  - `datasets/rift_faults/held_out_test.json` (`4337675b723dff1b88246216078a51e5b9aa1ffe976541739516d716ba18dd91`) — 15 scenarios (Strictly Sealed)
  - `datasets/rift_faults/manifest.json` (`8fe47d2730bf02f554e4b98c5b6fb7ed58213ee5799abf6108e1e4bed6c3fde1`) — 83 scenarios total
- **Secrets Audit:** No secrets committed to git. `.env` is ignored by `.gitignore`.

---

## 2. Component Implementation & Verification Status

```
┌────────────────────────────────────────┬──────────────────────┬────────────────────────────────────────────────────────┐
│ Subsystem / Component                 │ Implementation State │ Verification Status & Notes                            │
├────────────────────────────────────────┼──────────────────────┼────────────────────────────────────────────────────────┤
│ 1. Earliest Behavioral Divergence (EBD)│ Implemented          │ VERIFIED: R1–R4 invariants pass in validation harness. │
│ 2. Causal Discovery (FCI / PAG)       │ Implemented          │ LIMITATION: N=18 yields unoriented circle marks (o->). │
│ 3. Identifiability Engine             │ Implemented          │ VERIFIED: Backdoor/frontdoor evaluation & abstention.  │
│ 4. Oracle-Graph Handler               │ Implemented          │ VERIFIED: Diagnostic upper bound from ground truth path│
│ 5. Active Divergence (CID / W₁)       │ Implemented          │ VERIFIED: Permutation test B=10,000, W1 bootstrap CIs. │
│ 6. Cost Model & Optimizer (MSIS)      │ Implemented          │ VERIFIED: Submodular greedy selection vs random.       │
│ 7. Safety Controls & Hard-Stops       │ Implemented          │ VERIFIED: 8 deterministic guards, kill-switch, timeout.│
│ 8. Telemetry Ingestion (Prometheus)   │ Partially Implemented│ Dry-run simulated locally; live scraping requires Linux│
│ 9. Baselines (Sieve, B1, Random, etc.)│ Implemented          │ VERIFIED: 8 baselines evaluated across identical cases.│
│ 10. Statistical Analysis Harness      │ Implemented          │ VERIFIED: Wilcoxon, Cliff's δ, Holm-Bonferroni FWER.   │
└────────────────────────────────────────┴──────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 3. Test Suite Baseline Execution

Executing `pytest` from workspace root:
- **Total Tests Collected:** 626 items
- **Passed:** 626 (100%)
- **Failed:** 0
- **Execution Time:** ~14.1s
