# RIFT — IEEE Access Manuscript Evidence Map

This document establishes the bidirectional traceability matrix connecting every quantitative figure, empirical claim, architectural specification, and methodological assertion in [`docs/IEEE_ACCESS_MANUSCRIPT_DRAFT.md`](docs/IEEE_ACCESS_MANUSCRIPT_DRAFT.md) to verified files, line numbers, commit hashes, and JSON keys within the repository.

---

## 1. Summary of Evidence Categories and Scope

| Category | Dataset / Split | Scenario Count ($N$) | Evaluation Method | Status | Primary Source Artifact |
| :--- | :--- | :---: | :--- | :---: | :--- |
| **Spent Held-Out** | `held_out_test` (Sprint 4.3) | 108 (45 ATTR / 63 ABS) | RIFT V2 (One-Shot, 2026-11-03) | **FROZEN / SPENT** | [`docs/SPRINT4_3_0_FINAL_REPORT.md`](docs/SPRINT4_3_0_FINAL_REPORT.md) §7 |
| **Development** | `datasets/rift_v2/dev.json` | 180 (68 ATTR / 112 ABS) | RIFT V2, RIFT V3, Always-Abstain | **FROZEN** | [`docs/SPRINT4_4_0_FINAL_REPORT.md`](docs/SPRINT4_4_0_FINAL_REPORT.md) §1 |
| **Validation** | `datasets/rift_v2/val.json` | 72 (31 ATTR / 41 ABS) | RIFT V2, RIFT V3, Always-Abstain | **FROZEN** | [`docs/SPRINT4_4_0_FINAL_REPORT.md`](docs/SPRINT4_4_0_FINAL_REPORT.md) §1 |
| **Pooled Dev+Val** | Pooled `[DEV+VAL]` | 252 (99 ATTR / 153 ABS) | RIFT V2, RIFT V3, Always-Abstain | **VERIFIED** | [`artifacts/sprint4_5_1/utility/utility_verification.json`](artifacts/sprint4_5_1/utility/utility_verification.json) |
| **Adversarial** | `adv_dev` (Sprint 4.4) | 112 (80 ATTR / 32 ABS) | RIFT V2, RIFT V3-FULL | **FROZEN** | [`docs/SPRINT4_4_0_FINAL_REPORT.md`](docs/SPRINT4_4_0_FINAL_REPORT.md) §5 |
| **Confirmatory** | Sprint 4.5.1 Planned Split | 2000 (Planned) | RIFT V3 Confirmatory Protocol | **PENDING RUN** | [`docs/CONFIRMATORY_INFRASTRUCTURE_PLAN.md`](docs/CONFIRMATORY_INFRASTRUCTURE_PLAN.md) §7 |

---

## 2. Granular Claim-to-Evidence Matrix

### 2.1 Abstract and Introduction Claims

| # | Manuscript Claim | Quantitative Value in Text | Source Repository File | Exact Location / JSON Key | Verification Note |
|---|---|---|---|---|---|
| **E1** | Held-Out RIFT V2 Correct-Root Accuracy ($P_1$) | $44.4\%$ (20 / 45) | [`docs/SPRINT4_3_0_FINAL_REPORT.md`](docs/SPRINT4_3_0_FINAL_REPORT.md) | Section 7, Table 4.1 | Wilson 95% CI $[0.31, 0.59]$ |
| **E2** | Held-Out RIFT V2 Outcome Accuracy ($P_2$) | $55.6\%$ (60 / 108) | [`docs/SPRINT4_3_0_FINAL_REPORT.md`](docs/SPRINT4_3_0_FINAL_REPORT.md) | Section 7, Table 4.1 | Wilson 95% CI $[0.46, 0.65]$ |
| **E3** | Held-Out Always-Abstain Outcome Accuracy | $58.3\%$ (63 / 108) | [`docs/SPRINT4_3_0_FINAL_REPORT.md`](docs/SPRINT4_3_0_FINAL_REPORT.md) | Section 7, Section 13 | V2 vs AA: $\Delta = -0.028$, $p = 0.76$ |
| **E4** | Pooled Dev+Val RIFT V3 Unsafe Reduction | $31.3\%$ (79/252) $\rightarrow 19.0\%$ (48/252) | [`artifacts/sprint4_5_1/utility/utility_verification.json`](artifacts/sprint4_5_1/utility/utility_verification.json) | `claims.v3_pooled_unsafe`, `claims.v2_pooled_unsafe` | Exact count: V2 79, V3 48 |
| **E5** | Pooled Dev+Val RIFT V3 Expected Utility | Mean $U = -0.3377$ (CI $[-0.472, -0.222]$) | [`artifacts/sprint4_5_1/utility/utility_verification.json`](artifacts/sprint4_5_1/utility/utility_verification.json) | `claims.v3_mean_utility_strict`, `claims.v3_studentized_ci` | Recomputed & mathematically verified |
| **E6** | Pooled Dev+Val RIFT V2 Expected Utility | Mean $U = -0.5619$ (CI $[-0.712, -0.413]$) | [`artifacts/sprint4_5_1/utility/utility_verification.json`](artifacts/sprint4_5_1/utility/utility_verification.json) | `claims.v2_mean_utility_strict` | V3 vs V2 gain: $+0.2242$ ($p < 0.001$) |
| **E7** | Expected Utility Break-Even Penalty ($\lambda^*$) | $\lambda^* = 0.9375$ (at $\kappa = 0$) | [`artifacts/sprint4_5_1/utility/utility_verification.json`](artifacts/sprint4_5_1/utility/utility_verification.json) | `break_even.lambda_star_kappa_zero` | V3 CI $>0$ only for $\lambda \le 0.61$ |

---

### 2.2 System Architecture and Methodological Specifications

| # | Architecture Component / Parameter | Specification / Value | Source Repository File | Code Path / Declaration |
|---|---|---|---|---|
| **A1** | EBD Detection Threshold & Persistence | $\theta_{\text{detect}} = 3.0\sigma$, $k_{\text{persist}} = 2$ | [`src/rift/ebd/ebd.py`](src/rift/ebd/ebd.py) | Lines 298–299 (`_check_r1`) |
| **A2** | Telemetry Window Timing | $\Delta t = 5\,\text{s}$, $T_{\text{ref}} = 100\,\text{s}$, $T_{\text{post}} = 100\,\text{s}$ | [`src/rift/scenarios/simulator.py`](src/rift/scenarios/simulator.py) | Lines 25–35 (`DELTA_T`, `REF_WINDOWS`) |
| **A3** | Causal Discovery Engine | Fast Causal Inference (FCI) | [`src/rift/fci/fci_runner.py`](src/rift/fci/fci_runner.py) | `causal-learn` wrapper; Fisher-$Z$ $\alpha=0.05$ |
| **A4** | Defect D1 (FCI Collider Mis-decoding) | Semi-directed edge misinterpretation | [`docs/FINAL_SCIENTIFIC_VALIDITY_CLOSURE.md`](docs/FINAL_SCIENTIFIC_VALIDITY_CLOSURE.md) | Section 3.1 (PAG decoding flaw) |
| **A5** | CID Interventional Engine | Wasserstein-1 ($W_1$) Permutation Test ($B=1000$) | [`src/rift/cid/cid.py`](src/rift/cid/cid.py), [`src/rift/cid/evidence.py`](src/rift/cid/evidence.py) | `compute_w1_permutation_pvalue` |
| **A6** | MSIS Implementation Status | Greedy Heuristic Approximation | [`src/rift/optimizer/cost_model.py`](src/rift/optimizer/cost_model.py) | `MSISResult` (greedy cost pruning) |
| **A7** | Fail-Closed Network Isolation | NetNS Validation & Host Blockers | [`src/rift/intervention/backends/linux_tc_netem.py`](src/rift/intervention/backends/linux_tc_netem.py:80), [`src/rift/safety/safety.py`](src/rift/safety/safety.py:24) | `_validate_isolation_target`, `HOST_NAMESPACE_INTERVENTION` |

---

### 2.3 Experimental Performance Results Ledger

| # | Split / Comparison | Metric | Value in Manuscript | Verified Repository Source | Exact Source Coordinates |
|---|---|---|---|---|---|
| **R1** | Dev Split (V2 vs V3) | Correct-Root ($P_1$) | V2: $28/68$ ($41.2\%$), V3: $32/68$ ($47.1\%$) | [`docs/SPRINT4_4_0_FINAL_REPORT.md`](docs/SPRINT4_4_0_FINAL_REPORT.md) | Section 1, Table 1; exact $p = 0.503$ |
| **R2** | Dev Split (V2 vs V3) | Outcome Acc ($P_2$) | V2: $102/180$ ($56.7\%$), V3: $116/180$ ($64.4\%$) | [`docs/SPRINT4_4_0_FINAL_REPORT.md`](docs/SPRINT4_4_0_FINAL_REPORT.md) | Section 1, Table 1; Holm $p = 0.195$ |
| **R3** | Dev Split (V2 vs V3) | Unsafe Rate ($P_3$) | V2: $52/180$ ($28.9\%$), V3: $35/180$ ($19.4\%$) | [`docs/SPRINT4_4_0_FINAL_REPORT.md`](docs/SPRINT4_4_0_FINAL_REPORT.md) | Section 1, Table 1; Holm $p = 0.0575$ |
| **R4** | Dev Split (V2 vs V3) | Coverage & $n_{do}$ | V2: $44.4\%$ ($1.49$), V3: $37.2\%$ ($2.51$) | [`docs/SPRINT4_4_0_FINAL_REPORT.md`](docs/SPRINT4_4_0_FINAL_REPORT.md) | Section 1, Table 1 & Table 3 |
| **R5** | Val Split (V2 vs V3) | Correct-Root ($P_1$) | V2: $8/31$ ($25.8\%$), V3: $13/31$ ($41.9\%$) | [`docs/SPRINT4_4_0_FINAL_REPORT.md`](docs/SPRINT4_4_0_FINAL_REPORT.md) | Section 1, Table 1; Holm $p = 0.359$ |
| **R6** | Val Split (V2 vs V3) | Outcome Acc ($P_2$) | V2: $35/72$ ($48.6\%$), V3: $44/72$ ($61.1\%$) | [`docs/SPRINT4_4_0_FINAL_REPORT.md`](docs/SPRINT4_4_0_FINAL_REPORT.md) | Section 1, Table 1; Holm $p = 0.195$ |
| **R7** | Val Split (V2 vs V3) | Unsafe Rate ($P_3$) | V2: $27/72$ ($37.5\%$), V3: $13/72$ ($18.1\%$) | [`docs/SPRINT4_4_0_FINAL_REPORT.md`](docs/SPRINT4_4_0_FINAL_REPORT.md) | Section 1, Table 1; Holm $p = 0.0155$ |
| **R8** | Val Split (V2 vs V3) | Coverage & $n_{do}$ | V2: $48.6\%$ ($1.71$), V3: $36.1\%$ ($3.19$) | [`docs/SPRINT4_4_0_FINAL_REPORT.md`](docs/SPRINT4_4_0_FINAL_REPORT.md) | Section 1, Table 1 & Table 3 |
| **R9** | Pooled Dev+Val | Outcome Partition | Correct: 45, Unsafe: 48, Abstain: 159 | [`artifacts/sprint4_5_1/utility/utility_verification.json`](artifacts/sprint4_5_1/utility/utility_verification.json) | `claims.v3_pooled_partition` |
| **R10**| Adversarial Stress ($N=112$) | V2 vs V3 Performance | V2: 57 correct, 24 unsafe; V3: 67 correct, 7 unsafe | [`docs/SPRINT4_4_0_FINAL_REPORT.md`](docs/SPRINT4_4_0_FINAL_REPORT.md) | Section 5, Table 5.1 |
| **R11**| Adversarial Type A12 | Unobserved Root Unsafe | V3: $7/7$ unsafe ($100\%$), V2: $8/8$ unsafe | [`docs/SPRINT4_4_0_FINAL_REPORT.md`](docs/SPRINT4_4_0_FINAL_REPORT.md) | Section 5, Type A12 Audit |

---

### 2.4 Failure Taxonomy and Validity Disclosures

| # | Scientific Validity / Failure Topic | Detailed Empirical Finding | Supporting Repository Evidence | File / Section Reference |
|---|---|---|---|---|
| **F1** | Downstream Descendant Selection | $100\%$ (14/14) of V2 wrong roots selected downstream nodes along semi-directed paths | [`docs/SPRINT4_3_0_FAILURE_TAXONOMY.md`](docs/SPRINT4_3_0_FAILURE_TAXONOMY.md) | Section 2, Root Cause Taxonomy |
| **F2** | FCI Graph Undecidability | Precision $0.675/0.622$, Recall $0.424/0.355$; $97.8\%/97.0\%$ circle-marked edges | [`docs/SPRINT4_4_0_FCI_GRAPH_QUALITY.md`](docs/SPRINT4_4_0_FCI_GRAPH_QUALITY.md) | Section 1, Edge Decidability Ledger |
| **F3** | Oracle Graph Bottleneck | Oracle Graph improves P1 from $44.4\%$ to $71.1\%$ on held-out split | [`docs/SPRINT4_3_0_FINAL_REPORT.md`](docs/SPRINT4_3_0_FINAL_REPORT.md) | Section 7, Ablation Table (Row R10) |
| **F4** | Definitional Label Circularity | $49$ of $99$ dev/val ATTRIBUTE labels rest solely on temporal R1 rule | [`artifacts/final_closure/label_circularity_audit.json`](artifacts/final_closure/label_circularity_audit.json) | `audit_summary.temporal_r1_sole_dependence` |
| **F5** | L-struct Sensitivity Separation | Threshold-free structural label & 4 detectability covariates | [`src/rift/scenarios/l_struct.py`](src/rift/scenarios/l_struct.py), [`docs/FINAL_GROUND_TRUTH_INDEPENDENCE_REPORT.md`](docs/FINAL_GROUND_TRUTH_INDEPENDENCE_REPORT.md) | Tested by `tests/unit/test_l_struct.py` (16 passing tests) |
| **F6** | Crossed Statistical Dependence | 16 motifs $\times$ 16 fault families; Family-block ICC $+0.016$; size inflated to $0.20$ | [`artifacts/sprint4_5_1/power/stratified_power.json`](artifacts/sprint4_5_1/power/stratified_power.json), [`docs/FINAL_CONFIRMATORY_STATISTICAL_PLAN.md`](docs/FINAL_CONFIRMATORY_STATISTICAL_PLAN.md) | `monte_carlo_size_inflation` |
| **F7** | Legacy Dataset Contamination | 15 held-out scenarios have exact content twins in dev/val splits | [`docs/RIFT_DATASET_PROVENANCE.md`](docs/RIFT_DATASET_PROVENANCE.md), [`datasets/rift_faults/manifest.json`](datasets/rift_faults/manifest.json:284) | Documented twin list CF_36 to CF_47 |
| **F8** | CID Temporal Drift Confounding | Consecutive-window design; drift $>0.3\sigma$ causes $94\%–100\%$ false divergence | [`docs/SPRINT4_4_0_CID_EVIDENCE_ANALYSIS.md`](docs/SPRINT4_4_0_CID_EVIDENCE_ANALYSIS.md) | Section 3, Confounding Analysis |
| **F9** | Confirmatory Experiment Gate Status | Gates G0–G6 uncompleted; D7 independent human review pending | [`docs/CONFIRMATORY_INFRASTRUCTURE_PLAN.md`](docs/CONFIRMATORY_INFRASTRUCTURE_PLAN.md), [`docs/FINAL_APPROVAL_MATRIX.md`](docs/FINAL_APPROVAL_MATRIX.md) | Gate Ledger G0–G6 |

---

## 3. Prohibited Overclaims and Verification Safeguards

To maintain scientific integrity for IEEE Access submission, the manuscript enforces the following verified boundaries:

1. **No False Claims of Superiority:** The draft does **not** claim RIFT outperforms always-abstain. It explicitly documents that RIFT V2 outcome accuracy ($55.6\%$) is lower than always-abstain ($58.3\%$, $p=0.76$) and that RIFT V3 expected utility is negative ($U = -0.338$).
2. **No Fabricated Confirmatory Data:** The confirmatory trial is explicitly disclosed as **NOT YET RUN / PENDING RUN**, with all gate blockers (G0–G6, D7, D12) disclosed.
3. **No Unwarranted Real-World Claims:** All results are explicitly identified as synthetic evaluations from a queuing simulator without claiming production validity.
4. **No Hidden Contamination:** The 15 legacy content-twin overlaps and the definitional circularity of $\text{SNR} \ge 4.0\sigma$ are disclosed in full detail in the Threats to Validity section.
