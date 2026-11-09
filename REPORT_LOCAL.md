# RIFT Local Repository Verification Report

**Date of Verification:** 2026-11-09  
**Target Repository:** `/Users/manassakthivel/Desktop/RIFT FINAL`  
**Execution Environment:** macOS Darwin 25.6.0 (arm64), Python 3.11.15  

---

## 1. Code State Identification

### 1.1 Git Commit & Branch Information
- **Local HEAD Commit Hash:** `ebad911087942f257ba434f69816ed6d692be170`
- **Active Branch:** `remediation-and-manuscript-closure`
- **Last Commit:** `ebad911087942f257ba434f69816ed6d692be170 2026-11-04 09:36:45 +0530 Merge pull request #3 from ManasSakthivel/readme-status-update`
- **First 3 Commits:**
  - `2026-08-18 research: prepare RIFT research artifact for public release`
  - `2026-08-18 docs: add public repository release report`
  - `2026-08-21 docs: rewrite README — drop formal paper tone, keep status honesty`

### 1.2 Remote Comparison with origin/main
- `git fetch origin` was executed.
- `git rev-parse HEAD`: `ebad911087942f257ba434f69816ed6d692be170`
- `git rev-parse origin/main`: `ebad911087942f257ba434f69816ed6d692be170`
- **Comparison Result:** Local HEAD matches `origin/main` exactly (0 commits ahead, 0 commits behind).

### 1.3 Python Runtime & Virtual Environment
- **Python Executable:** `/opt/homebrew/opt/python@3.11/bin/python3.11`
- **Python Version:** `3.11.15 (main, Mar  3 2026, 00:52:57) [Clang 17.0.0 (clang-1700.6.4.2)]`
- **System Default Python (`/usr/bin/python3`):** `3.9.6`
- **Virtual Environment Path in Use:** None active (`sys.prefix == sys.base_prefix`: `/opt/homebrew/opt/python@3.11/Frameworks/Python.framework/Versions/3.11`).

### 1.4 Git Status (`git status --short`)
```text
 M .github/workflows/test.yml
 M README.md
 M analysis/tables/table4_scenarios.py
 M artifacts/phase3/cid_validation.json
 M artifacts/phase3/independent_validation_report.json
 M configs/live.yaml
 M datasets/rift_faults/manifest.json
 M requirements.txt
 M scripts/verify_heldout_sealed.py
 M src/rift/fault_injection/fault_injector.py
 M src/rift/intervention/backends/linux_tc_netem.py
 M src/rift/intervention/network_intervention.py
 M src/rift/pipeline/e2e_runner.py
 M src/rift/safety/safety.py
 M tests/unit/test_network_intervention.py
 M validation/run_cid_validation.py
?? artifacts/evaluation/
?? artifacts/final_closure/dataset_independence_report.json
?? artifacts/final_closure/l_struct_sensitivity_devval.json
?? artifacts/final_closure/repro/
?? artifacts/final_closure/statistical/
?? artifacts/sprint4_2_3/
?? artifacts/sprint4_2_4/
?? artifacts/sprint4_3_0/baseline/
?? artifacts/sprint4_3_0/failure_taxonomy_evidence.json
?? artifacts/sprint4_3_0/heldout_opened.json
?? artifacts/sprint4_3_0/protocol_v2_amendments_history.txt
?? artifacts/sprint4_3_0/provenance/
?? artifacts/sprint4_3_0/pytest_after.txt
?? artifacts/sprint4_3_0/results/dev/aggregate.csv
?? artifacts/sprint4_3_0/results/dev/aggregate.json
?? artifacts/sprint4_3_0/results/dev/analysis.json
?? artifacts/sprint4_3_0/results/dev/breakdowns.json
?? artifacts/sprint4_3_0/results/dev/detection.json
?? artifacts/sprint4_3_0/results/dev/failures.json
?? artifacts/sprint4_3_0/results/dev/per_scenario.csv
?? artifacts/sprint4_3_0/results/dev/run_metadata.json
?? artifacts/sprint4_3_0/results/dev/statistics.csv
?? artifacts/sprint4_3_0/results/dev/statistics.json
?? artifacts/sprint4_3_0/results/held_out/
?? artifacts/sprint4_3_0/results/val/aggregate.csv
?? artifacts/sprint4_3_0/results/val/aggregate.json
?? artifacts/sprint4_3_0/results/val/analysis.json
?? artifacts/sprint4_3_0/results/val/breakdowns.json
?? artifacts/sprint4_3_0/results/val/detection.json
?? artifacts/sprint4_3_0/results/val/failures.json
?? artifacts/sprint4_3_0/results/val/per_scenario.csv
?? artifacts/sprint4_3_0/results/val/run_metadata.json
?? artifacts/sprint4_3_0/results/val/statistics.csv
?? artifacts/sprint4_3_0/results/val/statistics.json
?? artifacts/sprint4_3_0/run_metadata.json
?? artifacts/stage4_intervention_results.json
?? datasets/rift_faults/adversarial_stress_cohort.json
?? datasets/rift_faults/manifest.v1_generator_69.json
?? datasets/rift_v2/heldout_candidate.json
?? datasets/rift_v2/heldout_status.json
?? decisions.json
?? deploy/
?? docs/BASELINE_INTEGRITY_AUDIT.md
?? docs/BENCHMARK_STRESS_TEST_PLAN.md
?? docs/D7_EXTERNAL_REVIEW_INVITATION.md
?? docs/D7_REVIEWER_CANDIDATE_SHORTLIST.md
?? docs/D7_REVIEWER_EVIDENCE_PACKAGE.md
?? docs/D7_REVIEW_CHECKLIST.md
?? docs/D7_REVIEW_SHA256SUMS.txt
?? docs/D7_REVIEW_TRACKER.md
?? docs/EXPERIMENTAL_PROTOCOL_AUDIT.md
?? docs/FINAL_BASELINE_INTEGRITY_AUDIT.md
?? docs/FINAL_CONFIRMATORY_PIPELINE_REPORT.md
?? docs/FINAL_CONFIRMATORY_STATISTICAL_PLAN.md
?? docs/FINAL_DATASET_INDEPENDENCE_REPORT.md
?? docs/FINAL_EVALUATION_REPORT.md
?? docs/FINAL_EXECUTION_LEDGER.md
?? docs/FINAL_GATE_INITIAL_STATE.md
?? docs/FINAL_GATE_WORK_LEDGER.md
?? docs/FINAL_GROUND_TRUTH_INDEPENDENCE_REPORT.md
?? docs/FINAL_HELD_OUT_EVALUATION.md
?? docs/FINAL_IEEE_SUBMISSION_READINESS.md
?? docs/FINAL_INDEPENDENT_RED_TEAM_REPORT.md
?? docs/FINAL_INTERVENTION_AUDIT.md
?? docs/FINAL_MANUSCRIPT_EVIDENCE_MAP.md
?? docs/FINAL_PAPER_READINESS_AUDIT.md
?? docs/FINAL_REPRODUCIBILITY_REPORT.md
?? docs/FINAL_RESEARCH_DECISION.md
?? docs/FINAL_SAFETY_AND_CODE_QUALITY_REPORT.md
?? docs/FINAL_SCIENTIFIC_RED_TEAM_REVIEW.md
?? docs/FINAL_STATISTICAL_AUDIT.md
?? docs/IEEE_ACCESS_MANUSCRIPT_DRAFT.md
?? docs/IEEE_PAPER_DRAFT.md
?? docs/RELATED_WORK.md
?? docs/REMAINING_LIMITATIONS.md
?? docs/REMEDIATION_STATUS.md
?? docs/REPRODUCE.md
?? docs/RESEARCH_CONTRIBUTION_AUDIT.md
?? docs/RIFT_DATASET_PROVENANCE.md
?? docs/RIFT_MULTI_SPRINT_PLAN.md
?? docs/SCIENTIFIC_RED_TEAM_REVIEW.md
?? docs/SPRINT1_CLAIM_EVIDENCE_MATRIX.md
?? docs/SPRINT1_FINAL_HANDOFF.md
?? docs/SPRINT1_REPOSITORY_AUDIT.md
?? docs/SPRINT1_REPRODUCIBILITY_REPORT.md
?? docs/SPRINT1_SCIENTIFIC_GAP_REGISTER.md
?? docs/SPRINT2_ABLATION_REPORT.md
?? docs/SPRINT2_EXPERIMENTAL_RESULTS.md
?? docs/SPRINT2_FINAL_HANDOFF.md
?? docs/SPRINT2_GRAPH_SEMANTICS.md
?? docs/SPRINT2_IDENTIFIABILITY_THEORY.md
?? docs/SPRINT2_IMPLEMENTATION_REPORT.md
?? docs/SPRINT2_STRUCTURAL_PRIOR_DESIGN.md
?? docs/SPRINT3_1_BASELINE_INDEPENDENCE_AUDIT.md
?? docs/SPRINT3_1_CAUSAL_CLAIMS_AUDIT.md
?? docs/SPRINT3_1_DEPLOYMENT_READINESS.md
?? docs/SPRINT3_1_FINAL_HANDOFF.md
?? docs/SPRINT3_1_GENERATOR_VALIDATION.md
?? docs/SPRINT3_1_METRIC_RECONCILIATION.md
?? docs/SPRINT3_1_ORACLE_VALIDITY_AUDIT.md
?? docs/SPRINT3_1_REPRODUCIBILITY_REPORT.md
?? docs/SPRINT3_1_SCENARIO_LEVEL_RECONSTRUCTION.md
?? docs/SPRINT3_1_STATISTICAL_REVIEW.md
?? docs/SPRINT3_ABLATION_RESULTS.md
?? docs/SPRINT3_BASELINE_AUDIT.md
?? docs/SPRINT3_BENCHMARK_SPECIFICATION.md
?? docs/SPRINT3_COVERAGE_RISK_ANALYSIS.md
?? docs/SPRINT3_FINAL_HANDOFF.md
?? docs/SPRINT3_SCENARIO_GENERATORS.md
?? docs/SPRINT3_SPRINT2_RESULTS_AUDIT.md
?? docs/SPRINT3_STATISTICAL_REPORT.md
?? docs/SPRINT3_STRESS_TEST_RESULTS.md
?? docs/SPRINT4_1_1_INDEPENDENT_PLAN_AUDIT.md
?? docs/SPRINT4_1_2_REMEDIATION_REPORT.md
?? docs/SPRINT4_1_3_INDEPENDENT_CODE_SAFETY_AUDIT.md
?? docs/SPRINT4_1_4_FINAL_SAFETY_GATE.md
?? docs/SPRINT4_1_5_LIVE_VALIDATION_READINESS_RUNBOOK.md
?? docs/SPRINT4_1_6_READ_ONLY_PREFLIGHT_REPORT.md
?? docs/SPRINT4_1_7_1_TEARDOWN_AND_LAUNCH_CHECKLIST.md
?? docs/SPRINT4_1_7_DEPLOYMENT_SAFETY_REVIEW.md
?? docs/SPRINT4_1_8_STAGE2_DEPLOYMENT_REPORT.md
?? docs/SPRINT4_1_9_1_TELEMETRY_REMEDIATION_REPORT.md
?? docs/SPRINT4_1_9_TELEMETRY_AND_BASELINE_VALIDATION_REPORT.md
?? docs/SPRINT4_1_ISOLATION_AND_DEPLOYMENT_PLAN.md
?? docs/SPRINT4_2_0_1_FINAL_ROLLBACK_SAFETY_REPORT.md
?? docs/SPRINT4_2_0_STAGE4_INTERVENTION_READINESS_REPORT.md
?? docs/SPRINT4_2_1_STAGE4_INTERVENTION_EXECUTION_REPORT.md
?? docs/SPRINT4_2_2_STAGE4_EVIDENCE_AUDIT.md
?? docs/SPRINT4_2_3_SCIENTIFIC_REPAIR_REPORT.md
?? docs/SPRINT4_2_4_CRITICAL_REPAIR_REPORT.md
?? docs/SPRINT4_2_4_STAGE4_ATTRIBUTION_ANALYSIS.md
?? docs/SPRINT4_3_0_DATASET_PROVENANCE_AUDIT.md
?? docs/SPRINT4_3_0_FAILURE_TAXONOMY.md
?? docs/SPRINT4_3_0_FINAL_REPORT.md
?? docs/SPRINT4_3_0_SCENARIO_DIVERSITY_REPORT.md
?? docs/SPRINT4_3_0_STATISTICAL_VALIDATION.md
?? docs/SPRINT4_QA_PREFLIGHT_REPORT.md
?? docs/SPRINT_INITIAL_STATE.md
?? docs/SPRINT_WORK_LEDGER.md
?? docs/STATISTICAL_VALIDATION_REPORT.md
?? docs/VM_REQUIREMENTS_AND_EXECUTION.md
?? docs/templates_sprint430/
?? results/
?? scripts/final_dataset_independence_report.py
?? scripts/final_l_struct_sensitivity.py
?? scripts/final_repro_check.py
?? scripts/final_stat_rule_simulation.py
?? scripts/sprint423_detector_comparison.py
?? scripts/sprint423_stage4_gap_analysis.py
?? scripts/sprint424_build_dataset_manifest.py
?? scripts/sprint424_stage4_offline_attribution.py
?? scripts/sprint430_analyze.py
?? scripts/sprint430_build_docs.py
?? scripts/sprint430_failure_analysis.py
?? scripts/sprint430_freeze.py
?? scripts/sprint430_generate_datasets.py
?? scripts/sprint430_provenance_audit.py
?? scripts/sprint430_run_pipeline.py
?? scripts/sprint430_verify_independence.py
?? scripts/sprint450_analyze.py
?? scripts/sprint450_run_confirm.py
?? scripts/stage4_intervention_analysis.py
?? scripts/stage4_intervention_orchestrator.py
?? scripts/verify_confirm_integrity.py
?? src/rift/intervention/watchdog.py
?? src/rift/pipeline/stage4_attribution.py
?? src/rift/scenarios/generator_confirm.py
?? src/rift/scenarios/l_struct.py
?? src/rift/scenarios/leakage_checks.py
?? src/rift/statistics/confirmatory_inference.py
?? src/rift/statistics/divergence_detectors.py
?? tests/integration/test_sprint424_cid_r4_integration.py
?? tests/unit/baselines/test_baseline_independence.py
?? tests/unit/baselines/test_latency_correlation.py
?? tests/unit/test_confirm_analyze.py
?? tests/unit/test_confirm_generator.py
?? tests/unit/test_confirm_integrity.py
?? tests/unit/test_confirm_runner.py
?? tests/unit/test_confirmatory_inference.py
?? tests/unit/test_dataset_leakage_checks.py
?? tests/unit/test_final_reproducibility.py
?? tests/unit/test_l_struct.py
?? tests/unit/test_safety_namespace_remediation.py
?? tests/unit/test_sprint2_semidirected.py
?? tests/unit/test_sprint423_detectors.py
?? tests/unit/test_sprint423_ebd_attribution.py
?? tests/unit/test_sprint424_dataset_manifest.py
?? tests/unit/test_sprint424_heldout_guard.py
?? tests/unit/test_sprint424_stage4_attribution.py
?? tests/unit/test_sprint430_independence.py
?? tests/unit/test_sprint430_metrics_access_stats.py
?? tests/unit/test_sprint430_rift_v2.py
?? tests/unit/test_telemetry_manifest_remediation.py
?? tests/unit/test_telemetry_remediation_419.py
?? tests/unit/test_watchdog_remediation.py
```

---

## 2. Commands Executed and Results

| Command | Exit Code | Log Path | Status / Error Summary |
|---|---|---|---|
| `make reproduce-all` | `2` | `results/local_verify/reproduce_all.log` | **COMMAND FAILED** (`Makefile:188: *** missing separator. Stop.`) |
| `PYTHONPATH=src:. python3.11 validation/validation_harness.py` | `0` | `results/local_verify/validation_harness.log` | **SUCCESS** (V1–V5 validation checks passed) |
| `PYTHONPATH=src:. python3.11 scripts/sprint451_utility_sensitivity.py` | `0` | `results/local_verify/sprint451_utility_sensitivity.log` | **SUCCESS** (56/58 claims verified; 0 mismatches across 3276 pairs) |
| `PYTHONPATH=src:. python3.11 -m rift.experiments.run --experiment EXP-001 --dry-run` | `1` | `results/local_verify/exp001_dry_run.log` | **COMMAND FAILED** (`TypeError: SyntheticBenchmark() takes no arguments` at `src/rift/experiments/run.py:185`) |
| `make test-intervention` | `2` | `results/local_verify/test_intervention.log` | **COMMAND FAILED** (`Makefile:188: *** missing separator. Stop.`) |

---

## 3. Verification of Research Claims

### Claim 1: Precision@1 = 0.875 (35/40)
- **Status:** NOT PRODUCED
- **Saved Log:** `results/local_verify/validation_harness.log`, `results/local_verify/sprint451_utility_sensitivity.log`
- **Output Line:** No executed command outputs `Precision@1 = 0.875` or `35/40`.
- **Repository Search:** A full repository search (`grep -rn "35/40"`) returned 0 matches across the entire codebase, docs, results, and artifacts.
- **Source & Citability:** N/A (figure does not exist in code or results).

### Claim 2: Number of testbeds = 3
- **Status:** NOT PRINTED
- **Saved Log:** None of the executed logs print "Number of testbeds = 3".
- **Repository Finding:** The codebase only configures and deploys 1 microservice benchmark testbed: Google Cloud Online Boutique (`deploy/podman-compose.yaml`, `configs/live.yaml`). Other testbeds (e.g. Sock Shop, TrainTicket) are only mentioned in design docs as future work.
- **Source & Citability:** N/A (unsupported claim).

### Claim 3: Number of baselines compared = 7
- **Status:** NOT PRINTED
- **Saved Log:** `results/local_verify/sprint451_utility_sensitivity.log`
- **Output Line:** The log mentions baseline `'B0-EARLIEST'` in a verification tolerance line, but does not print "Number of baselines compared = 7".
- **Repository Finding:** In `scripts/sprint451_utility_sensitivity.py` lines 42–44, 8 baseline/comparator methods are defined:
  1. `B0-EARLIEST`
  2. `B0-HIGHEST`
  3. `B1-LATENCY-CORR`
  4. `B3-SIEVE-LIKE`
  5. `B5-RIFT-OBS`
  6. `B6-RIFT-RANDOM`
  7. `B7-RIFT-ONE-SHOT`
  8. `ORACLE:UPPER-BOUND`
- **Source & Citability:** Depends on committed code (`scripts/sprint451_utility_sensitivity.py`).

### Claim 4: Negative-control abstentions = 25/25
- **Status:** NOT PRODUCED
- **Saved Log:** None.
- **Repository Search:** String `25/25` has 0 matches across the entire repository.
- **Related Development Figure:** `validation/validation_harness.py` evaluated 24 confounded scenarios (`n_confounded=24`) with 100.00% correct abstention/warning rate (`24/24`), not `25/25`.
- **Source & Citability:** N/A (figure does not exist).

### Claim 5: Live evaluation status: is it complete or pending?
- **Status:** PRINTED (Status is **PENDING**)
- **Saved Log:** `results/local_verify/validation_harness.log`
- **Exact Quoted Output Line (Line 10):**
  > `Caveat: Validation uses oracle PAG (direct from ground truth causal path), not FCI-estimated PAG. Results are upper-bound estimates. Live testbed validation is Phase 10.`
- **Makefile Quoted Status Line (`Makefile:167`):**
  > `Status: PENDING_LINUX`
- **Source & Citability:** Depends on committed code in `validation/validation_harness.py` and `Makefile`.

### Claim 6: Precision@1 on the synthetic development set, with its denominator
- **Status:** PRINTED
- **Saved Log:** `results/local_verify/validation_harness.log`
- **Exact Quoted Output Lines (Lines 3 & 9):**
  > `  V1 PASS: P@1=83.33% ≥ 70% target`  
  > `  n_scenarios=36, non_conf=12, conf=24`
- **Figure:** `83.33%` (`0.8333` in `artifacts/phase3/independent_validation_report.json`).
- **Denominator:** `12` non-confounded development scenarios (10 / 12 = 83.333%). Total development scenarios: `36`.
- **Source & Citability:** Depends on committed script `validation/validation_harness.py` and modified artifact `artifacts/phase3/independent_validation_report.json`.

### Claim 7: Abstention on confounded scenarios, with its denominator
- **Status:** PRINTED
- **Saved Log:** `results/local_verify/validation_harness.log`
- **Exact Quoted Output Lines (Lines 4 & 9):**
  > `  V2 PASS: confounded_correct_rate=100.00% ≥ 80%`  
  > `  n_scenarios=36, non_conf=12, conf=24`
- **Figure:** `100.00%` (`1.0` in `artifacts/phase3/independent_validation_report.json`).
- **Denominator:** `24` confounded development scenarios (24 / 24 = 100.00%).
- **Source & Citability:** Depends on committed script `validation/validation_harness.py` and modified artifact `artifacts/phase3/independent_validation_report.json`.

### Claim 8: V3 and V2 mean utility against always-abstain, as printed
- **Status:** NOT PRINTED (Calculated and asserted internally; not printed on stdout)
- **Saved Log:** `results/local_verify/sprint451_utility_sensitivity.log`
- **Exact Output Lines:**
  ```text
  claims verified: 56/58
    NOT VERIFIED: {'claim': 'V3 mean cost term gamma=1 (PRE 3.3: 0.136)', 'claimed': 0.136, 'recomputed': 0.13531746031746034, 'tolerance': 0.0006, 'verified': False}
    NOT VERIFIED: {'claim': 'B0-EARLIEST BE kappa=0', 'claimed': 0.26, 'recomputed': 0.26063829787234044, 'tolerance': 0.0006, 'verified': False}
  mismatches vs saved scores: 0 of 3276
  ```
- **Internal / Artifact Values (`artifacts/sprint4_5_1/utility/utility_verification.json`):**
  - **Strict Template (λ=2, γ=1 / κ=0.05):**
    - V3 mean utility against Always-Abstain: `-0.337698412698413` (verified against `-0.338`)
    - V2 mean utility against Always-Abstain: `-0.561904761904762` (verified against `-0.562`)
  - **Operational Template (λ=2, γ=1 / κ=0.05):**
    - V3 mean utility against Always-Abstain: `-0.19484126984127` (verified against `-0.195`)
    - V2 mean utility against Always-Abstain: `-0.363492063492063` (verified against `-0.363`)
- **Source & Citability:** Depends on committed code `scripts/sprint451_utility_sensitivity.py` and committed artifact `artifacts/sprint4_5_1/utility/utility_verification.json`.

### Claim 9: Result files containing `0.875`, `35/40`, or `25/25`
- **Command:** `grep -rn "0.875\|35/40\|25/25" results artifacts docs 2>/dev/null`
- **Results:**
  - `35/40`: 0 occurrences.
  - `25/25`: 0 occurrences.
  - `0.875`: 204 matches found across statistical power calculations, confidence intervals, coverage ratios, and breakdown files (none representing Precision@1 = 0.875):
    - `artifacts/sprint4_5_1/power/stratified_power.json:136`: `"reject_mu_0.1": 0.875`
    - `artifacts/sprint4_5_1/power/stratified_power.log:49`: `..., "reject_mu_0.1": 0.875}`
    - `artifacts/evaluation/statistical_test_results.json:30`: `"p_value_raw": 0.875,`
    - `artifacts/final_closure/statistical/n_scaling.json:242`: `"T_reject": 0.875,`
    - `artifacts/final_closure/statistical/rule_comparison.json:263`: `"T_useful": 0.875,`
    - `artifacts/final_closure/statistical_sim.log:17`: `{"N": 8000, "rf": 0.05, "mu0.1": {"T_reject": 0.875, ...`
    - `artifacts/sprint4_3_0/results/val/aggregate.csv:19`: `... 0.8750 ...`
    - `artifacts/sprint4_3_0/results/val/aggregate.json:733, 1293, 1838, 2693, 3073`: `"coverage": 0.875,`
    - `artifacts/sprint4_3_0/results/held_out/breakdowns.json:3484, 6256, 6620, 9756, 15997, 16028, 16130, 18689, 19133, 19164, 19266, 21825, 25445, 26584, 28097, 28217, 38082, 39570, 40641`: `"value": 0.875,`
    - `artifacts/sprint4_3_0/results/held_out/analysis.json:9392, 11262, 11943, 11983, 12001, 12112, 15238, 15821, 15839, 19659, 19677, 23557, 24060, 24238, 24256, 24287, 24305`: `"value": 0.875,`
    - `artifacts/sprint4_3_0/results/dev/breakdowns.json:2018, 2942, 6804, 8992, 15972, 18169, 18222, 19028, 21225, 21278, 36722`: `"value": 0.875,`
    - `artifacts/sprint4_3_0/results/dev/analysis.json:2110, 2406, 2455, 7673, 12114, 14797, 14868, 19594, 22268, 24908`: `"value": 0.875,`
    - `docs/FINAL_CONFIRMATORY_STATISTICAL_PLAN.md:57, 75`
    - `docs/SPRINT4_5_0_STATISTICAL_ANALYSIS_PLAN.md:163`
    - `docs/FINAL_SCIENTIFIC_VALIDITY_CLOSURE.md:183`

---

## 4. Local vs GitHub Citability Audit

| Claim | Citability Status | Dependencies / Notes |
|---|---|---|
| **Claim 1 (P@1 = 0.875 / 35/40)** | **Uncitable** | Figure does not exist in any file. |
| **Claim 2 (3 testbeds)** | **Uncitable** | Codebase only implements 1 testbed (Online Boutique). |
| **Claim 3 (7 baselines)** | **Safe to cite publicly (with script push)** | Defined in `scripts/sprint451_utility_sensitivity.py` (committed). 8 baseline variants implemented. |
| **Claim 4 (Negative-control 25/25)** | **Uncitable** | Figure does not exist (actual dev benchmark is 24/24). |
| **Claim 5 (Live eval PENDING)** | **Safe to cite publicly** | Explicitly stated in committed `validation/validation_harness.py` and `Makefile`. |
| **Claim 6 (Dev P@1 = 83.33%, denom=12)** | **Uncommitted results** | Generated by committed `validation/validation_harness.py`; result artifact `artifacts/phase3/independent_validation_report.json` is modified locally. |
| **Claim 7 (Dev Confounded Abstention = 100%, denom=24)** | **Uncommitted results** | Generated by committed `validation/validation_harness.py`; result artifact `artifacts/phase3/independent_validation_report.json` is modified locally. |
| **Claim 8 (V3/V2 Mean Utility vs AA)** | **Safe to cite publicly** | Script `scripts/sprint451_utility_sensitivity.py` and artifact `artifacts/sprint4_5_1/utility/utility_verification.json` are committed and tracked. |
| **Claim 9 (File matches for 0.875)** | **Partially uncommitted** | Some matching artifacts (`artifacts/sprint4_3_0/`, `artifacts/final_closure/`) are currently untracked (`??`). |

---

## 5. Required Actions for GitHub Citability

To make all valid claims and reproduction commands fully verifiable on GitHub:

1. **Commit and Push Modified Artifacts:**
   - `artifacts/phase3/independent_validation_report.json` (contains Dev P@1 = 0.8333 and Confounded = 1.0).
   - Any modified scripts in `validation/`, `src/rift/`, and `analysis/`.

2. **Commit Untracked Results / Artifacts (if citing Sprint 4.3.0 or Final Closure):**
   - Untracked directories `artifacts/sprint4_3_0/`, `artifacts/final_closure/`, `artifacts/sprint4_5_1/` must be staged and committed.

3. **Fix Makefile Syntax Error:**
   - In `Makefile` line 188 (`pre-linux-check` target), add a tab character preceding the Python code block to allow GNU `make` targets (`reproduce-all`, `test`, `test-intervention`) to parse and execute.

4. **Fix CLI Runner Argument in `src/rift/experiments/run.py`:**
   - In `src/rift/experiments/run.py:185`, update `SyntheticBenchmark(seed=seed)` to instantiate `SyntheticBenchmark()` (which takes no `seed` parameter in `__init__`), enabling `make experiment EXP-001` and `python -m rift.experiments.run --experiment EXP-001 --dry-run` to succeed.
