# RIFT Sprint 7 — Final Research Dashboard & Release Acceptance

**Date:** 2026-11-09  
**Lead Research Engineer:** Bob  
**Objective:** Final research closure, non-oracle evaluation, independent validation, reproducibility gate, and Git release.  
**Target Milestone:** Stanford MS CS Autumn 2027 Research Evidence Portfolio  

---

## 1. Master Workstream Status Dashboard

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 RIFT SPRINT 7 FINAL WORKSTREAM DASHBOARD                               │
├───────────────────────────────────┬───────────────────┬──────────────┬─────────────────────────────────┤
│ Workstream                        │ Scope             │ Status       │ Key Deliverable                 │
├───────────────────────────────────┼───────────────────┼──────────────┼─────────────────────────────────┤
│ 1. Independent Held-Out Eval      │ Spent Split Audit │ COMPLETE     │ SPRINT7_HELDOUT_EVALUATION.md   │
│ 2. Non-Oracle Causal Eval         │ Learned FCI vs PAG│ COMPLETE     │ SPRINT7_NON_ORACLE_EVALUATION.md│
│ 3. Results Reproduction           │ 39.2% Unsafe, U   │ COMPLETE     │ SPRINT7_RESULTS_REPRODUCTION.md │
│ 4. Live Intervention Validation   │ RHEL 9.6 Netem    │ COMPLETE     │ SPRINT7_LIVE_VALIDATION.md      │
│ 5. Engineering & Repro Gate       │ 1,017 Tests, CLI  │ COMPLETE     │ SPRINT7_ENGINEERING_GATE.md     │
│ 6. Claims & Final Research Report │ Master Ledger     │ COMPLETE     │ SPRINT7_FINAL_CLAIMS_LEDGER.md  │
│ 7. Integration & Git Release      │ Clean Commit/Push │ COMPLETE     │ SPRINT7_FINAL_DASHBOARD.md      │
└───────────────────────────────────┴───────────────────┴──────────────┴─────────────────────────────────┘
```

---

## 2. Executive Synthesis of Final Findings

### A. Non-Oracle vs. Oracle Causal Performance
- **The Oracle Reality:** The widely cited figures (10/12 P@1 and 24/24 confounded abstention) occurred solely when ground-truth causal paths and latent flags were directly injected into the oracle PAG.
- **Learned FCI on Telemetry:** Without oracle information, **97.8% (dev) and 97.0% (val) of learned edges remain circle-marked (`o-o`)**. The learned pipeline abstains on 0/24 confounded faults because orientation ambiguities prevent MAG-ID identifiability checks from proving non-identifiability.
- **Active Interventions:** RIFT's active network perturbations (`tc netem`) successfully disambiguate downstream propagation from correlation when minimum sample sizes ($N \ge 20$) are met.

### B. Scientific Reproduction of Key Claims
- **Unsafe Attribution Reduction:** **VERIFIED**. V3 reduces unsafe attributions from 79 (V2) to 48 (V3) on the 252 dev+val benchmark corpus — an exact **39.24% reduction** (and 44.4% under operational scoring).
- **Utility Advantage over V2:** **VERIFIED**. V3 achieves a mean utility advantage of **+0.2242** (strict, 95% CI $[+0.0855, +0.3665]$) and **+0.1687** (operational, 95% CI $[+0.0307, +0.3088]$) over V2.
- **Utility vs. Always-Abstain (AA):** V3 mean utility is negative ($-0.338$ strict) at $\lambda=2, \kappa=0.05$ due to prevalence limits ($\pi = 0.393$). V3 outperforms AA with statistical significance strictly when false-attribution penalties are low ($\lambda \le 0.61$ at $\kappa=0$, $\lambda \le 0.30$ at $\kappa=0.025$).
- **Intervention Overhead:** V3 executes an average of **2.71 interventions** per scenario. The historical claim of ">50% overhead reduction vs random" was based on hard-coded time constants and is **WITHDRAWN**.

### C. Live Infrastructure Feasibility
- **Real vs. Synthetic:** Live validation on RHEL 9.6 (`9.30.57.225`) successfully verified a single ($N=1$) live controlled $50\text{ms}$ delay injection on `cartservice` across 14 containers on Google Online Boutique with clean NetNS rollback. All multi-scenario quantitative datasets ($N=252$) originate from high-fidelity synthetic benchmark generation.

---

## 3. Engineering Gate & Test Execution

- **Gate 3A Data Model Round-Trip:** 119 / 119 passed (`GATE 3A: PASS`).
- **Core Test Suite:** 1,017 tests passed across all functional unit, causal, baseline, closed-loop, and integration modules.
- **Experiment CLI Runner:** `PYTHONPATH=src python3.11 -m rift.experiments.run -e EXP-001 --dry-run` executes in 0.54s and outputs structured provenance artifacts.
- **Validation Harness:** `PYTHONPATH=src:. python3.11 validation/validation_harness.py` passes all V1–V5 invariant checks.
- **Sensitivity Matrix:** `PYTHONPATH=src:. python3.11 scripts/sprint451_utility_sensitivity.py` passes with 0 score mismatches across 3,276 pairs.

---

## 4. Final Research-Readiness Verdict

**Verdict:** **CONDITIONALLY READY**

### Strongest Truthful Graduate Admissions Formulation:
> **RIFT: Causal Inference & Active Fault Localization Engine for Microservices**  
> *Engineered an active root-cause localization system combining causal discovery (FCI / Partial Ancestral Graphs), non-parametric Wasserstein-1 divergence testing, and Linux kernel traffic control (`tc netem`) interventions. Evaluated across 252 benchmark scenarios, reducing unsafe diagnostic attributions by 39.2% (79 → 48) over previous iterations and formalizing break-even economic utility boundaries across 32 cost-penalty regimes.*

---

## 5. Authoritative Artifact Paths

- **Held-Out Evaluation:** [`docs/recovery/SPRINT7_HELDOUT_EVALUATION.md`](docs/recovery/SPRINT7_HELDOUT_EVALUATION.md:1)
- **Non-Oracle Evaluation:** [`docs/recovery/SPRINT7_NON_ORACLE_EVALUATION.md`](docs/recovery/SPRINT7_NON_ORACLE_EVALUATION.md:1)
- **Results Reproduction:** [`docs/recovery/SPRINT7_RESULTS_REPRODUCTION.md`](docs/recovery/SPRINT7_RESULTS_REPRODUCTION.md:1)
- **Live Testbed Validation:** [`docs/recovery/SPRINT7_LIVE_VALIDATION.md`](docs/recovery/SPRINT7_LIVE_VALIDATION.md:1)
- **Engineering Gate Report:** [`docs/recovery/SPRINT7_ENGINEERING_GATE.md`](docs/recovery/SPRINT7_ENGINEERING_GATE.md:1)
- **Final Claims Ledger:** [`docs/recovery/SPRINT7_FINAL_CLAIMS_LEDGER.md`](docs/recovery/SPRINT7_FINAL_CLAIMS_LEDGER.md:1)
- **Final Research Report:** [`docs/recovery/SPRINT7_FINAL_RESEARCH_REPORT.md`](docs/recovery/SPRINT7_FINAL_RESEARCH_REPORT.md:1)
