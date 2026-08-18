# Experiment Completeness Audit
Phase: Phase 4.5 (Mac pre-Linux readiness sprint)
Date: October 24, 2024
Auditor: Agent 2

## Executive Summary
- Total experiments: 14 (EXP-001 to EXP-014)
- COMPLETE: 13
- INCOMPLETE: 1 (EXP-014 deviates from standard `statistical_test` key schema)
- ISSUES: 5 major discrepancies, mapping confusions, or numbering conflicts

This audit evaluates the completeness and integrity of the RIFT experiment registry (`experiments/REGISTRY.yaml`), ablation framework (`experiments/ablations/ABLATION_REGISTRY.yaml`), experimental hypotheses (`docs/hypotheses.md`), research question mapping (`docs/research/RQ_EXPERIMENT_MAP.md`), and claims registry (`docs/CLAIMS_REGISTRY.yaml`).

---

## Per-Experiment Audit

### EXP-001: Causal attribution on synthetic fault scenarios (dev split)
- **RQ:** `["RQ1", "RQ2"]` (Valid)
- **Hypothesis:** `["H1", "H2"]` (Valid)
- **Input Dataset:** `"datasets/rift_faults/development.json"` (Valid)
- **Split:** `DEVELOPMENT` (Valid)
- **Method:** `RIFT-FULL` (Valid)
- **Baselines:** `["RIFT-OBS", "RIFT-RANDOM", "SIEVE-LIKE", "ORACLE-UPPER-BOUND"]` (Valid)
- **Metrics:** `[precision_at_1, conditional_precision_at_1, coverage, abstention_rate, false_attribution_rate, correct_attribution_rate, mean_detection_latency_s]` (Valid)
- **Statistical Test:** `"wilcoxon_one_sided"` (Valid)
- **Seed:** 42 (Valid)
- **n_scenarios:** 36 (Valid)
- **Status:** `"READY_FOR_LINUX"` (Valid)
- **Output Artifact:** `"results/EXP-001/"` (Valid)
- **Overall Completeness:** **COMPLETE**

### EXP-002: Identifiability-conditioned attribution on confounded scenarios
- **RQ:** `["RQ2"]` (Valid)
- **Hypothesis:** `["H2"]` (Valid)
- **Input Dataset:** `"datasets/rift_faults/development.json"` (Valid)
- **Split:** `DEVELOPMENT` (Valid)
- **Method:** `RIFT-FULL` (Valid)
- **Baselines:** `["RIFT-OBS", "SIEVE-LIKE"]` (Valid)
- **Metrics:** `[conditional_precision_at_1, correct_abstention_rate, not_identifiable_rate]` (Valid)
- **Statistical Test:** `"wilcoxon_one_sided"` (Valid)
- **Seed:** 42 (Valid)
- **n_scenarios:** 36 (Valid)
- **Status:** `"READY_FOR_LINUX"` (Valid)
- **Output Artifact:** `"results/EXP-002/"` (Valid)
- **Overall Completeness:** **COMPLETE (with count discrepancy)**
- **Discrepancy:** Specifies `n_confounded_required: 48` for 80% statistical power. However, the `DEVELOPMENT` split contains only 24 confounded scenarios (CF_00 through CF_23). Attempting to meet this requirement using only the development split is impossible without utilizing scenarios from validation or held-out test splits, which would violate the strict split boundaries and cause label/test set leakage.

### EXP-003: Intervention efficiency: MSIS cost vs random selection
- **RQ:** `["RQ3"]` (Mismatch: Mapped to RQ3 in registry, but belongs in RQ6 per `RQ_EXPERIMENT_MAP.md`)
- **Hypothesis:** `["H4"]` (Duplicate mapping: H4 officially maps to EXP-014 in `hypotheses.md` and `RQ_EXPERIMENT_MAP.md`)
- **Input Dataset:** `"datasets/rift_faults/development.json"` (Valid)
- **Split:** `DEVELOPMENT` (Valid)
- **Method:** `RIFT-FULL` (Valid)
- **Baselines:** `["RIFT-RANDOM"]` (Valid)
- **Metrics:** `[total_ed_s, n_interventions, detection_latency_s]` (Valid)
- **Statistical Test:** `"wilcoxon_one_sided"` (Valid)
- **Seed:** 42 (Valid)
- **n_scenarios:** 36 (Valid)
- **Status:** `"READY_FOR_LINUX"` (Valid)
- **Output Artifact:** `"results/EXP-003/"` (Valid)
- **Overall Completeness:** **COMPLETE (with mapping discrepancies)**

### EXP-004: CID/EBD validation on synthetic ground truth
- **RQ:** `["RQ1"]` (Valid, though listed under both RQ1 and RQ3 in `RQ_EXPERIMENT_MAP.md`)
- **Hypothesis:** `["H1"]` (Mismatch: Mapped to H1 in registry, but is a descriptive/internal validation with no hypothesis testing in `RQ_EXPERIMENT_MAP.md`)
- **Input Dataset:** `"datasets/rift_faults/development.json"` (Valid)
- **Split:** `DEVELOPMENT` (Valid)
- **Method:** `RIFT-FULL` (Valid)
- **Baselines:** `[]` (Valid, explicitly empty)
- **Metrics:** `[cid_grade, ebd_confidence, r1_r4_pass_rates]` (Valid)
- **Statistical Test:** `"none"` (Valid, descriptive validation)
- **Seed:** 42 (Valid)
- **n_scenarios:** 36 (Valid)
- **Status:** `"DRY_RUN_READY"` (Valid)
- **Output Artifact:** `"results/EXP-004/"` (Valid)
- **Overall Completeness:** **COMPLETE (with hypothesis mismatch)**

### EXP-005: RIFT-OBS ablation: observation-only vs interventional
- **RQ:** `["RQ1", "RQ2"]` (Valid)
- **Hypothesis:** `["H1", "H2"]` (Valid)
- **Input Dataset:** `"datasets/rift_faults/development.json"` (Valid)
- **Split:** `DEVELOPMENT` (Valid)
- **Method:** `RIFT-OBS` (Valid)
- **Baselines:** `["RIFT-FULL"]` (Valid)
- **Metrics:** `[precision_at_1, conditional_precision_at_1, detection_latency_s]` (Valid)
- **Statistical Test:** `"wilcoxon_one_sided"` (Valid)
- **Seed:** 42 (Valid)
- **n_scenarios:** 36 (Valid)
- **Status:** `"READY_FOR_LINUX"` (Valid)
- **Output Artifact:** `"results/EXP-005/"` (Valid)
- **Overall Completeness:** **COMPLETE**

### EXP-006: RIFT-RANDOM ablation: cost-optimization benefit
- **RQ:** `["RQ3"]` (Mismatch: Mapped to RQ3 in registry, but belongs in RQ6 per `RQ_EXPERIMENT_MAP.md`)
- **Hypothesis:** `["H4"]` (Duplicate mapping: H4 officially maps to EXP-014 in `hypotheses.md` and `RQ_EXPERIMENT_MAP.md`)
- **Input Dataset:** `"datasets/rift_faults/development.json"` (Valid)
- **Split:** `DEVELOPMENT` (Valid)
- **Method:** `RIFT-RANDOM` (Valid)
- **Baselines:** `["RIFT-FULL"]` (Valid)
- **Metrics:** `[total_ed_s, precision_at_1, n_interventions]` (Valid)
- **Statistical Test:** `"wilcoxon_one_sided"` (Valid)
- **Seed:** 42 (Valid)
- **n_scenarios:** 36 (Valid)
- **Status:** `"READY_FOR_LINUX"` (Valid)
- **Output Artifact:** `"results/EXP-006/"` (Valid)
- **Overall Completeness:** **COMPLETE (with mapping discrepancies)**

### EXP-007: Sieve-like methodological comparison
- **RQ:** `["RQ1"]` (Valid)
- **Hypothesis:** `["H1"]` (Valid)
- **Input Dataset:** `"datasets/rift_faults/development.json"` (Valid)
- **Split:** `DEVELOPMENT` (Valid)
- **Method:** `SIEVE-LIKE` (Valid)
- **Baselines:** `["RIFT-FULL"]` (Valid)
- **Metrics:** `[precision_at_1, detection_latency_s, abstention_rate]` (Valid)
- **Statistical Test:** `"wilcoxon_one_sided"` (Valid)
- **Seed:** 42 (Valid)
- **n_scenarios:** 36 (Valid)
- **Status:** `"READY_FOR_LINUX"` (Valid)
- **Output Artifact:** `"results/EXP-007/"` (Valid)
- **Overall Completeness:** **COMPLETE**

### EXP-008: Safety hard-stops adversarial test
- **RQ:** `[]` (Valid: infrastructure test, not mapped in `RQ_EXPERIMENT_MAP.md`)
- **Hypothesis:** `[]` (Valid: explicitly none for infrastructure test)
- **Input Dataset:** `"tests/integration/safety/"` (Valid reference path)
- **Split:** `DEVELOPMENT` (Valid)
- **Method:** `RIFT-FULL` (Valid)
- **Baselines:** `[]` (Valid, explicitly empty)
- **Metrics:** `[safety_abort_rate, rollback_success_rate]` (Valid)
- **Statistical Test:** `"none"` (Valid)
- **Seed:** 42 (Valid)
- **n_scenarios:** 10 (Valid)
- **Status:** `"DRY_RUN_READY"` (Valid)
- **Output Artifact:** `"results/EXP-008/"` (Valid)
- **Overall Completeness:** **COMPLETE**

### EXP-009: Performance instrumentation: stage timing
- **RQ:** `[]` (Mismatch: Mapped to empty list in registry, but belongs to RQ6 per `RQ_EXPERIMENT_MAP.md`)
- **Hypothesis:** `[]` (Mismatch: Mapped to empty list in registry, but H2 maps to EXP-009 in `hypotheses.md`)
- **Input Dataset:** `"datasets/rift_faults/development.json"` (Valid)
- **Split:** `DEVELOPMENT` (Valid)
- **Method:** `RIFT-FULL` (Valid)
- **Baselines:** `[]` (Valid, explicitly empty)
- **Metrics:** `[wall_time_per_stage, bottleneck_stage, total_pipeline_time]` (Valid)
- **Statistical Test:** `"none"` (Valid)
- **Seed:** 42 (Valid)
- **n_scenarios:** 5 (Valid)
- **Status:** `"DRY_RUN_READY"` (Valid)
- **Output Artifact:** `"results/EXP-009/"` (Valid)
- **Overall Completeness:** **COMPLETE (with severe mapping and numbering conflicts)**

### EXP-010: Repeatability: same seed same result
- **RQ:** `[]` (Mismatch: Mapped to empty list in registry, but belongs to RQ4 per `RQ_EXPERIMENT_MAP.md`)
- **Hypothesis:** `[]` (Valid: explicitly empty/none for repeatability test)
- **Input Dataset:** `"datasets/rift_faults/development.json"` (Valid)
- **Split:** `DEVELOPMENT` (Valid)
- **Method:** `RIFT-FULL` (Valid)
- **Baselines:** `[]` (Valid, explicitly empty)
- **Metrics:** `[result_hash_consistency]` (Valid)
- **Statistical Test:** `"none"` (Valid)
- **Seed:** 42 (Valid)
- **n_scenarios:** 5 (Valid)
- **Status:** `"DRY_RUN_READY"` (Valid)
- **Output Artifact:** `"results/EXP-010/"` (Valid)
- **Overall Completeness:** **COMPLETE (with missing RQ mapping)**

### EXP-011: Robustness: FCI on noisy/sparse data
- **RQ:** `["RQ1"]` (Mismatch: Mapped to RQ1 in registry, but belongs to RQ3 per `RQ_EXPERIMENT_MAP.md`)
- **Hypothesis:** `[]` (Mismatch: Mapped to empty list in registry, but H5 maps to EXP-011 in `hypotheses.md`)
- **Input Dataset:** `"datasets/rift_faults/development.json"` (Valid)
- **Split:** `DEVELOPMENT` (Valid)
- **Method:** `RIFT-FULL` (Valid)
- **Baselines:** `[]` (Valid, explicitly empty)
- **Metrics:** `[graph_discovery_failure_rate, ebd_candidate_rate]` (Valid)
- **Statistical Test:** `"none"` (Valid)
- **Seed:** 42 (Valid)
- **n_scenarios:** 10 (Valid)
- **Status:** `"DRY_RUN_READY"` (Valid)
- **Output Artifact:** `"results/EXP-011/"` (Valid)
- **Overall Completeness:** **COMPLETE (with severe mapping and numbering conflicts)**

### EXP-012: Oracle upper bound reference
- **RQ:** `["RQ1"]` (Valid, though listed under both RQ1 and RQ4 in `RQ_EXPERIMENT_MAP.md`)
- **Hypothesis:** `[]` (Valid: explicitly none for upper bound baseline reference)
- **Input Dataset:** `"datasets/rift_faults/development.json"` (Valid)
- **Split:** `DEVELOPMENT` (Valid)
- **Method:** `ORACLE-UPPER-BOUND` (Valid)
- **Baselines:** `[]` (Valid, explicitly empty)
- **Metrics:** `[precision_at_1, detection_latency_s]` (Valid)
- **Statistical Test:** `"none"` (Valid)
- **Seed:** 42 (Valid)
- **n_scenarios:** 36 (Valid)
- **Status:** `"DRY_RUN_READY"` (Valid)
- **Output Artifact:** `"results/EXP-012/"` (Valid)
- **Overall Completeness:** **COMPLETE**

### EXP-013: Ablation: closed-loop update vs one-shot intervention (H3)
- **RQ:** `["RQ2"]` (Valid)
- **Hypothesis:** `["H3"]` (Valid)
- **Input Dataset:** `"datasets/rift_faults/development.json"` (Valid)
- **Split:** `DEVELOPMENT` (Valid)
- **Method:** `RIFT-FULL` (Valid)
- **Baselines:** `["RIFT-ONE-SHOT"]` (Valid)
- **Metrics:** `[precision_at_1, n_interventions_to_attribution, detection_latency_s]` (Valid)
- **Statistical Test:** `"wilcoxon_one_sided"` (Valid)
- **Seed:** 42 (Valid)
- **n_scenarios:** 36 (Valid)
- **Status:** `"READY_FOR_LINUX"` (Valid)
- **Output Artifact:** `"results/EXP-013/"` (Valid)
- **Overall Completeness:** **COMPLETE**

### EXP-014: Cost model effectiveness: MSIS selection vs random (H4)
- **RQ:** `["RQ6"]` (Valid)
- **Hypothesis:** `["H4"]` (Valid)
- **Input Dataset:** `"datasets/rift_faults/development.json"` (Valid)
- **Split:** `DEVELOPMENT` (Valid)
- **Method:** `RIFT-FULL` (Valid)
- **Baselines:** `["RIFT-RANDOM"]` (Valid)
- **Metrics:** `[total_ed_s, precision_at_1, n_interventions]` (Valid)
- **Statistical Test:** Missing standard `statistical_test` key. Instead, uses `statistical_test_cost: "wilcoxon_one_sided"` and `statistical_test_accuracy: "tost_equivalence"`.
- **Seed:** 42 (Valid)
- **n_scenarios:** 36 (Valid)
- **Status:** `"READY_FOR_LINUX"` (Valid)
- **Output Artifact:** `"results/EXP-014/"` (Valid)
- **Overall Completeness:** **INCOMPLETE** due to deviations from the standard experiment registry schema (missing standard `statistical_test` field name).

---

## RQ Coverage

For each research question defined in `docs/research/RQ_EXPERIMENT_MAP.md`, we audited whether it is covered by at least one experiment and if any mapped experiment has an invalid status:

- **RQ1 (Core Detection Question):** Covered by EXP-001, EXP-004, EXP-005, EXP-007, and EXP-012. Coverage is strong; no experiments are in `"PLANNED"` status.
- **RQ2 (Necessity Question):** Covered by EXP-002 and EXP-013. Coverage is complete; no experiments are `"PLANNED"`.
- **RQ3 (Causal Assumptions Question):** Covered by EXP-011 and EXP-004. However, in `REGISTRY.yaml`, neither experiment has `"RQ3"` in its `rq` field (EXP-011 lists `"RQ1"`, EXP-004 lists `"RQ1"`). This represents a registry mapping gap. No experiments are `"PLANNED"`.
- **RQ4 (Ground Truth Question):** Covered by EXP-010 and EXP-012. However, in `REGISTRY.yaml`, neither experiment has `"RQ4"` in its `rq` field (EXP-010 lists `[]`, EXP-012 lists `"RQ1"`). This represents a registry mapping gap. No experiments are `"PLANNED"`.
- **RQ5 (Generalization Question):** Mapped to the "H5 experiment" (Cross-system transfer). However, there is no corresponding experiment ID (e.g., EXP-015) in `REGISTRY.yaml` for H5. The status is marked as `DEFERRED (Phase 11)` in `RQ_EXPERIMENT_MAP.md`.
- **RQ6 (Efficiency Question):** Covered by EXP-014, EXP-003, and EXP-009. However, in `REGISTRY.yaml`, only EXP-014 has `"RQ6"` in its `rq` field (EXP-003 lists `"RQ3"`, EXP-009 lists `[]`). This represents a registry mapping gap. No experiments are `"PLANNED"`.

---

## Issues Found

### MISSING items
1. **Experiment for H5 (Cross-System Generalization) in `REGISTRY.yaml`:** No active or deferred experiment block is allocated in the registry for H5, leaving the RQ5 / H5 chain unpopulated in `REGISTRY.yaml` (though correctly documented as deferred to Phase 11 in `RQ_EXPERIMENT_MAP.md`).
2. **Standard `statistical_test` field in EXP-014:** The registry schema requires `statistical_test` (or "none" with reason). EXP-014 utilizes `statistical_test_cost` and `statistical_test_accuracy` instead, violating standard registry parsers expecting the uniform `statistical_test` field.

### DUPLICATE items
1. **Hypothesis H4 Duplication:** H4 is mapped to both EXP-003 and EXP-006 in `REGISTRY.yaml`, even though H4 is the primary hypothesis for EXP-014. This duplicates hypothesis mapping and clutters the registry.
2. **Ablation Registry Equivalence:** `RIFT-NO-MSIS` is mapped to H4 and EXP-006, which is identical to the `RIFT-RANDOM` ablation mapping. This duplicate is redundant and uses identical experiment configurations.

### UNSUPPORTED items
1. **Hypothesis mapping on descriptive validation EXP-004:** EXP-004 maps to `hypotheses: ["H1"]` in `REGISTRY.yaml`, but `RQ_EXPERIMENT_MAP.md` identifies EXP-004 as a descriptive/internal validation with no hypothesis testing.
2. **Unsound Power Requirement in EXP-002:** EXP-002 requires `n_confounded_required: 48` for H2. However, the `DEVELOPMENT` split contains only 24 confounded scenarios. To satisfy the power requirement of 48 confounded scenarios during algorithm development or ablation trials, one would have to access validation and test sets, violating the strict benchmark split integrity and introducing label leakage.

### INCOMPLETE items
1. **EXP-014 Schema Deviation:** EXP-014 lacks the standard `statistical_test` field, introducing schema inconsistency.

### NUMBERING CONFLICTS
1. **H2 to EXP-009 Numbering Mismatch:** `hypotheses.md` maps H2 to "EXP-009" (Abstention / Intervention necessity). However, in `REGISTRY.yaml`, EXP-009 is "Performance instrumentation: stage timing" with `hypotheses: []`, and H2 is actually covered by EXP-002 and EXP-005.
2. **H5 to EXP-011 Numbering Mismatch:** `hypotheses.md` maps H5 to "EXP-011" (Cross-system generalization). However, in `REGISTRY.yaml`, EXP-011 is "Robustness: FCI on noisy/sparse data" with `hypotheses: []`.

---

## Registry Changes Required

To align all documents perfectly and guarantee robust schema compliance, the following modifications to `experiments/REGISTRY.yaml` are required:

1. **Fix EXP-014 Statistical Test Key:**
   Add a standard `statistical_test` entry mapping to `"joint_wilcoxon_tost"` (or similar unified designation) or `"none"` to preserve schema validity, while leaving detailed sub-test attributes in notes.
2. **Align RQ mappings in `experiments/REGISTRY.yaml`:**
   - Map EXP-003 and EXP-006 to `rq: ["RQ6"]` instead of `"RQ3"`.
   - Map EXP-010 to `rq: ["RQ4"]` instead of `[]`.
   - Map EXP-011 to `rq: ["RQ3"]` instead of `"RQ1"`.
   - Map EXP-009 to `rq: ["RQ6"]` instead of `[]`.
3. **Align Hypotheses mappings in `experiments/REGISTRY.yaml`:**
   - Remove `H4` from EXP-003 and EXP-006 (they are baselines/ablations, not the primary confirmatory tests for H4).
   - Remove `H1` from EXP-004 (it is descriptive validation, not a confirmatory test).

---

## Status
**BLOCKED**

*Reason for Blocked Status:* 
There is an insurmountable structural discrepancy between the power analysis requirement for EXP-002 (`n_confounded_required: 48` for H2) and the benchmark data split boundaries. The `DEVELOPMENT` split contains only 24 confounded scenarios. To achieve 80% power (48 confounded scenarios), a developer would be forced to pull confounded scenarios from the `VALIDATION` (12 scenarios) and `HELD_OUT_TEST` (12 scenarios) splits, causing fatal leakage and violating scientific integrity. Until the development dataset is expanded or the power requirement is scaled to fit the 24 development scenarios, the chain cannot be executed with full scientific integrity on development data.
