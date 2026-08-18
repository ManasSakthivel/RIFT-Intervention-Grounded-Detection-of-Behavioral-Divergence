# RIFT Research Question → Experiment Map

**File:** `docs/research/RQ_EXPERIMENT_MAP.md`  
**Status:** AUTHORITATIVE  
**Phase:** 4.5 (Mac pre-Linux readiness sprint)  
**Authority:** `docs/research_alignment.md`, `docs/hypotheses.md`, `experiments/REGISTRY.yaml`

---

## Purpose

This document maps every research question to the specific experiments,
hypotheses, metrics, statistical tests, and artifacts that will answer it.
No claim may be made in the paper without an entry here that is fully populated.

**Authoritative RQ wording is from `docs/research_alignment.md`.**

---

## RQ → Experiment Map

### RQ1 — Core Detection Question

> *Can do-calculus-grounded interventions detect behavioral divergence more precisely than observational methods alone?*

| Hypothesis | Experiment | Method vs Baseline | Primary Metric | Statistical Test | Status |
|---|---|---|---|---|---|
| H1 | EXP-001 | RIFT-FULL vs RIFT-OBS, SIEVE-LIKE | Precision@1 | Wilcoxon one-sided | READY_FOR_LINUX |
| H1 | EXP-005 | RIFT-OBS vs RIFT-FULL | Precision@1 delta | Wilcoxon one-sided | READY_FOR_LINUX |
| H1 | EXP-007 | SIEVE-LIKE vs RIFT-FULL | Precision@1 | Wilcoxon one-sided | READY_FOR_LINUX |
| — | EXP-004 | CID/EBD internal validation | CID grade, EBD R1-R4 | None (descriptive) | DRY_RUN_READY |
| — | EXP-012 | Oracle upper bound reference | Precision@1 | None (upper bound) | DRY_RUN_READY |

**Input split:** `datasets/rift_faults/development.json` (36 scenarios)  
**Seed:** 42 (fixed)  
**Output artifacts:** `results/EXP-001/`, `results/EXP-005/`, `results/EXP-007/`

---

### RQ2 — Necessity Question

> *Is intervention necessary? Does removing the causal inference layer measurably degrade performance?*

| Hypothesis | Experiment | Method vs Baseline | Primary Metric | Statistical Test | Status |
|---|---|---|---|---|---|
| H2 | EXP-002 | RIFT-FULL vs RIFT-OBS on confounded subset | Conditional Precision@1 | Wilcoxon one-sided | READY_FOR_LINUX |
| H3 | EXP-013 | RIFT-FULL vs RIFT-ONE-SHOT on multi-cause | Precision@1 | Wilcoxon one-sided | READY_FOR_LINUX |

**H2 power note:** Requires n≥48 confounded scenarios for 80% power.  
`datasets/rift_faults/manifest.json` records 48 confounded scenarios in the development set.  
If <48 collected at run time, report achieved power only (see `src/rift/statistics/stats.py::check_power_achieved`).

**H3 prerequisite:** RIFT-ONE-SHOT baseline must be implemented before Linux execution.
It is a RIFT-FULL variant with the closed-loop posterior update disabled.

---

### RQ3 — Causal Assumptions Question

> *Do the causal assumptions approximately hold in the experimental setting?*

| Experiment | Description | Metric | Status |
|---|---|---|---|
| EXP-011 | FCI on noisy/sparse data | graph_discovery_failure_rate | DRY_RUN_READY |
| EXP-004 | CID/EBD validation | ebd_confidence, r1_r4_pass_rates | DRY_RUN_READY |

**Note:** RQ3 is descriptive — no hypothesis test. Report: % of learned graphs
that are DAGs, acyclicity rate, and FCI fallback rate.

---

### RQ4 — Ground Truth Question

> *Is the benchmark ground truth credible?*

| Experiment | Description | Metric | Status |
|---|---|---|---|
| EXP-010 | Repeatability: same seed → same result | result_hash_consistency | DRY_RUN_READY |
| EXP-012 | Oracle upper bound | Precision@1 ceiling | DRY_RUN_READY |

**Note:** Ground truth locked in `datasets/rift_faults/development.json` with
`ground_truth_locked: true` on each scenario. The oracle uses privileged ground
truth and must be labeled "ORACLE UPPER BOUND" in all tables.

---

### RQ5 — Generalization Question

> *Does RIFT generalize across systems and fault types not seen during development?*

| Experiment | Description | Metric | Status |
|---|---|---|---|
| H5 experiment | Cross-system transfer | Cross-system Precision@1 | DEFERRED (Phase 11) |

**Sage+Chaos baselines: DEFERRED_TO_PHASE_8** — do not fabricate results.  
H5 requires a second system (Sock Shop or similar). Not scheduled until Phase 11.

---

### RQ6 — Efficiency Question

> *What is the overhead of RIFT on the monitored system, and how quickly does it detect divergence?*

| Hypothesis | Experiment | Method vs Baseline | Primary Metric | Statistical Test | Status |
|---|---|---|---|---|---|
| H4 (cost) | EXP-014 | RIFT-FULL vs RIFT-RANDOM | total_ed_s | Wilcoxon one-sided | READY_FOR_LINUX |
| H4 (accuracy) | EXP-014 | RIFT-FULL vs RIFT-RANDOM | Precision@1 | TOST equivalence | READY_FOR_LINUX |
| — | EXP-003 | MSIS cost vs random | total_ed_s, n_interventions | Wilcoxon one-sided | READY_FOR_LINUX |
| — | EXP-009 | Stage timing | wall_time_per_stage | None (descriptive) | DRY_RUN_READY |

---

## Hypothesis → Experiment Cross-Reference

| Hypothesis | Formal Statement | Experiment | Status |
|---|---|---|---|
| H1 | Precision@1(RIFT-FULL) > Precision@1(best_observational_baseline), p<0.05, Cliff's δ>0.20 | EXP-001 | READY_FOR_LINUX |
| H2 | On C_confounded: Precision@1(RIFT-FULL) > Precision@1(RIFT-OBS), p<0.05, Cliff's δ>0.20 | EXP-002 | READY_FOR_LINUX |
| H3 | Precision@1(RIFT-FULL) > Precision@1(RIFT-ONE-SHOT) on multi-cause faults | EXP-013 | READY_FOR_LINUX |
| H4 cost | Cost(RIFT-FULL) < Cost(RIFT-RANDOM), p<0.05 | EXP-014 | READY_FOR_LINUX |
| H4 acc | |Precision@1(RIFT-FULL) - Precision@1(RIFT-RANDOM)| < 0.05 (TOST) | EXP-014 | READY_FOR_LINUX |
| H5 | Cross-system Precision@1 ≥ 0.70 × in-distribution, binomial test | DEFERRED | DEFERRED (Phase 11) |

---

## Multiple Testing Correction

All 6 confirmatory tests (H1, H2, H3, H4_acc, H4_cost, H5) are subject to
**Holm-Bonferroni correction** at α=0.05.

Implementation: `src/rift/statistics/stats.py::run_confirmatory_tests()`

Exploratory comparisons use **BH FDR** correction.

**Do NOT run these tests until Category C (live RIFT) evidence is collected.**
Running on synthetic/mock data and reporting as hypothesis test results is invalid.

---

## Missing Items (Pre-Linux Checklist)

| Item | Required For | Action Required |
|---|---|---|
| RIFT-ONE-SHOT baseline | EXP-013 (H3) | Implement in `src/rift/baselines/` |
| Live PrometheusClient data | All READY_FOR_LINUX | T1 fix deployed on Linux |
| OTel Collector wiring | All READY_FOR_LINUX | T2 fix deployed on Linux |
| tc band fix | All live interventions | T3 fix deployed on Linux |
| Held-out evaluation | Phase 5 | Phase 5 authorization required |
