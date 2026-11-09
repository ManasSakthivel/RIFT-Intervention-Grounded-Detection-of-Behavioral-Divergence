# Sprint 4.2.4 — Critical Defect Resolution Report

**Date:** 2026-11-03. **Interpreter:** `python3` 3.9.6. **Scope:** offline repair; no live experiment, no IBM QA VM contact, no commit/push/reset/clean.

**Result summary**

| Issue | Severity | Outcome |
|---|---|---|
| 1. Hard-coded Stage 4 attribution | CRITICAL | Removed. Real learned-graph inference now runs on the saved telemetry. **Honest result: the pipeline abstains (`NOT_IDENTIFIABLE`); no top-1 accuracy exists for the single trial.** |
| 2. CID key mismatch, R4 unreachable | CRITICAL | Fixed. R4 and DEFINITIVE are reachable through the integrated runner with real `compute_cid` results; invalid evidence is rejected. |
| 3. Held-out guard | HIGH | Replaced by a registry with repo-root-relative resolution, pinned SHA-256/identity checks, and fail-closed purpose gating. `verify_heldout_sealed.py` reports 4/4. |
| 4. Manifest 69 vs 50 | MEDIUM | Reconciled and documented (69 generator output + 14 hand-added = 83 deployed). Historical manifest preserved byte-for-byte. |

Tests: **782 passed** (700 at the end of Sprint 4.2.3; +82 this sprint: 23 + 19 + 15 + 25). A test count is not the evidence for correctness; the integrated runs in each section below are.

One additional defect was found while working on Issue 1 and fixed (§1.7).

---

## 1. Issue 1 — Stage 4 attribution was a literal, not an inference

### 1.1 Original failure
`scripts/stage4_intervention_analysis.py` set `attributed = "cartservice"`, `record["ground_truth"] = "cartservice"` and `record["attribution_accuracy_top1"] = 1.0`. The "100 % Top-1" figure in the Sprint 4.2.1 report and in `artifacts/stage4_intervention_results.json` was never computed. (Sprint 4.2.3 had flagged this as C3 but could not fix it without an adapter.)

### 1.2 Root cause
There was no representation conversion from saved Stage 4 telemetry (Prometheus p99 lists, seconds) to the pipeline input (`metrics: Dict[str, DataFrame(time, value)]`, baselines, PAG, CID evidence). Without one, the script wrote the answer directly.

### 1.3 Changed files
- **New** `src/rift/pipeline/stage4_attribution.py` — evidence adapter, CID construction, learned-graph inference, post-hoc evaluation.
- **New** `scripts/sprint424_stage4_offline_attribution.py` — runs it on the saved artifact; refuses to overwrite its input.
- `scripts/stage4_intervention_analysis.py` — the live-fetch and summary-table code is untouched. The hard-coded attribution block is replaced by a call to `analyze_saved_record`; the label lives in an `EVALUATION_ONLY` constant that is passed only to the evaluation step.
- `scripts/run_reproducible_evaluation.py` — see §1.7.
- **New** `tests/unit/test_sprint424_stage4_attribution.py` (25 tests).
- **New** `docs/SPRINT4_2_4_STAGE4_ATTRIBUTION_ANALYSIS.md` — the Stage 4 attribution report with predictions and ground truth separated. The Sprint 4.2.1 report is historical and was not edited.

### 1.4 Exact correction
- `build_evidence` reads only `pre_baseline`, `intervention`, `target_service`. Baselines come from the pre phase only. The incident window is the active phase. The applied intervention (the experiment's input) becomes an `InterventionRecord`.
- `build_cid_store` computes real `compute_cid(X→Y)` for the intervened service X against every other service Y (baseline = Y's pre phase, post = Y's active phase).
- `infer` runs `run_fci` → `compute_ebd` (with the CID store) → `identify_query` → abstention. It has no label parameter. A failed FCI is an abstention (`GRAPH_DISCOVERY_FAILURE`), never an oracle fallback.
- `evaluate_prediction(prediction, ground_truth_root)` is the only place a label is compared, and it takes an already-built prediction. An abstention is scored `ABSTAINED`, not correct and not incorrect.
- Output fields: `predicted_root`, `ground_truth_root`, `confidence`, `abstained`, `ebd_candidate`, `causal_path_kind`, `evidence_type`, `cid_grade`, `detection_timestamp`, `prediction_timestamp` (plus `abstention_reason`, tied candidates, identifiability, PAG edges, parameters).

### 1.5 Regression tests (`test_sprint424_stage4_attribution.py`)
| Requirement | Test(s) |
|---|---|
| Changing ground-truth labels does not change predictions | `test_changing_ground_truth_labels_does_not_change_prediction`, `test_evaluation_only_argument_does_not_change_prediction`, `test_inference_never_reads_label_keys` (a record that raises on any label-key access) |
| Changing evidence can change predictions | `test_removing_the_cartservice_divergence_changes_the_ebd_candidate`, `test_prediction_follows_evidence_not_the_declared_target` |
| Unidentifiable case abstains | `test_bidirected_pair_is_unidentifiable_and_abstains`, `test_too_little_evidence_abstains`, `test_graph_discovery_failure_abstains_without_oracle_fallback` |
| Correct prediction is computed from inference output | `test_correct_prediction_is_computed_after_inference`, `test_sufficient_real_cid_evidence_yields_definitive_interventional_attribution` |
| Cannot report 1/1 from the known target | `test_known_injected_target_alone_cannot_produce_an_attribution`, `test_analysis_script_cannot_report_one_of_one_from_the_target_alone`, `test_analysis_script_has_no_hardcoded_attribution_or_accuracy` |
| Historical artifact untouched | `test_historical_stage4_artifact_is_unchanged`, `test_offline_script_writes_new_artifact_and_leaves_historical_input_alone` |

### 1.6 Before / after and integrated execution
Command: `python3 scripts/sprint424_stage4_offline_attribution.py` (output `artifacts/sprint4_2_4/stage4_attribution_result.json`; deterministic, tested).

| | Before | After (actual pipeline output) |
|---|---|---|
| Prediction | `cartservice` (literal) | **abstained**, `NOT_IDENTIFIABLE`; `predicted_root = null`, `confidence = 0.0` |
| EBD candidate | not computed | `cartservice`, tied at the first active window with `frontend`, `shippingservice`, `adservice` |
| `causal_path_kind` / `evidence_type` | not computed | `SEMI_DIRECTED` / `OBSERVATIONAL` |
| `cid_grade` | not computed | `INSUFFICIENT` (n = 15 baseline / 12 active; floor is 20) |
| Accuracy | `1.0` (literal) | none: 1 trial, abstained. The EBD candidate matched the injected service. |
| Timestamps | none | detection 1793642335.0, prediction 1793642445.0 |

The historical artifact's SHA-256 is `e4cf1391…dcffe` before and after.

Interpretation (qualified):
- The abstention follows from two properties of the saved data. R4 is impossible (fewer than 20 samples per side), and FCI on 27 plateau-constant rows over 10 variables yields a PAG with a spurious `cartservice ↔ emailservice` bidirected edge at the default α = 0.05.
- A sensitivity probe over α (run after the default was fixed, not used to choose it) shows the commit/abstain outcome is **fragile**: α = 0.01, 0.10 and 0.20 produce a CANDIDATE `cartservice` prediction (still observational, never DEFINITIVE), while 0.02–0.07 abstains. The EBD candidate is `cartservice` in every case. Details are in `docs/SPRINT4_2_4_STAGE4_ATTRIBUTION_ANALYSIS.md` §5.
- The experiment's own design (a known applied intervention on cartservice) is the strongest support that cartservice is the origin of the divergence; the algorithm does not add independent confirmation from this dataset.

### 1.7 Additional defect found: oracle fallback in the learned variant
`run_rift_full_scenario(use_oracle_pag=False)` fell back to `build_oracle_pag(scenario_dict)` — a PAG built from ground-truth `causal_path` — when FCI raised. That is label leakage into a "learned" prediction. It was reachable but **never fired** in the dev/validation runs (instrumented: 68 learned runs, 0 fallbacks), so existing results are unaffected. Now FCI failure returns an abstention (`FCI_FAILED:<ExceptionType>`); test `test_learned_rift_full_does_not_fall_back_to_oracle_pag_on_fci_failure`.

Dev and validation were re-run through the changed code and compared with `artifacts/evaluation/comparative_results_{development,validation}.json`: all 8 methods are identical on both splits once timing fields are excluded.

---

## 2. Issue 2 — CID key mismatch made R4 unreachable

### 2.1 Original failure
No run could ever reach R4 or DEFINITIVE through the integrated pipeline, regardless of evidence quality.

### 2.2 Root cause
Producer and consumer used disjoint key spaces. E2E Stage 13 stored CID under `"{svc}→{svc}.downstream"` with `target_variable = "{svc}.downstream"`; `compute_ebd` R4 looked up `"{src}→{tgt}"` for edges in the candidate's causal path. Those strings can never be equal. Stage 13 also compared a service's incident-window data to itself, which is not an outcome-on-another-service comparison. The R4 gate also accepted a CID object that lacked the significance/threshold attributes.

### 2.3 Changed files
- **New** `src/rift/cid/evidence.py` — `CIDKey(intervened, outcome)`, `CIDEvidenceStore`, `validate_cid_for_r4`, schema `rift.cid_evidence/1`.
- `src/rift/ebd/ebd.py` — R4 looks up `(candidate, outcome)` for each outcome on the candidate's causal path; requires R3; uses the strict validator; records `cid_scores`, rejection reasons and warnings. Legacy `"X→Y"` strings are still accepted at the boundary and validated against the identity inside the CID result.
- `src/rift/pipeline/e2e_runner.py` — Stage 13 computes real `compute_cid` for every verified intervention X × every other outcome Y; Stages 14/15 consume the same store. New constructor arguments `post_window_s` and `observe_window_s`.
- `tests/unit/test_ebd.py` (the `tc_e6` mock now carries the evidence fields R4 requires) and `tests/unit/test_sprint423_ebd_attribution.py` (the "bare mock keeps historical behaviour" test now asserts rejection).
- **New** `tests/integration/test_sprint424_cid_r4_integration.py` (23 tests).

### 2.4 Exact correction
R4 passes only if the CID result is for an intervention on the candidate itself, observed on an outcome in its causal path, with finite `w1 > θ_cid`, grade CANDIDATE or RELIABLE, `permutation_significant is True` and `exceeds_threshold is True`. Evidence for `do(Vk)`, k ≠ candidate, never confirms the candidate. R4 cannot rescue a failed R1 or R3.

### 2.5 Regression tests
Valid evidence; wrong key; wrong direction; the legacy self-`.downstream` key; missing/`None`/empty; malformed key; key disagreeing with result identity; INSUFFICIENT; insignificant permutation; below threshold; θ override; missing attributes; NaN W1; other-intervention evidence; R4 not rescuing a failed R1/R3; and three integrated-runner tests (valid → DEFINITIVE; exact-replay null post → not DEFINITIVE; 60 s window → INSUFFICIENT → not DEFINITIVE). A source check asserts the runner builds no string CID keys.

### 2.6 Before / after and integrated execution
- **Before** (from the code and by test `test_legacy_self_downstream_key_never_matches`): zero lookups could succeed; `r4_pass` was `False` for every input.
- **After** (integrated `RIFTEndToEndRunner.run()` on a deterministic fixture whose `do(A)` shifts B): the CID stage computes 6 pairs (3 services × 2 outcomes); `A` ends `r4_pass = True`, `confidence = DEFINITIVE`, `evidence_type = INTERVENTIONAL`; `attribution = A`, `final_state = PASS`; provenance records the CID schema. The null-post and 60 s variants correctly stay below DEFINITIVE.
- The fixture is deterministic synthetic telemetry. It shows the code path is reachable and selective; it is not evidence about real systems.

---

## 3. Issue 3 — Held-out guard

### 3.1 Original failure
`scripts/run_reproducible_evaluation.py` passed a quoted held-out filename literal to the evaluator, which built the path from a fixed directory with no hash or identity check. A wrong file, a swapped file or a mis-sited call would be read silently; the source scanner in `verify_heldout_sealed.py` flagged the literal (4/4 could not be reached without a workaround).

### 3.2 Root cause
Path resolution, integrity and access policy were scattered across callers; there was no single loader.

### 3.3 Changed files
- **New** `src/rift/evaluation/dataset_registry.py` — repo-root-relative resolution from `__file__`; pinned SHA-256, size, scenario count, declared split and id uniqueness per file; `load_split(split, purpose, guard, root)`; `verify_all_files`.
- `scripts/run_reproducible_evaluation.py` — `evaluate_dataset_split` takes a registry split identity; held-out requires `purpose="final"`, a `HeldOutGuard` and an active token.
- `scripts/sprint423_detector_comparison.py` — loads only via the registry; the held-out read is confined to `build_final()`. `tests/unit/test_sprint423_detectors.py` static checks were adjusted to the new names.
- `scripts/verify_heldout_sealed.py` — check 4 now also verifies every registered file's hash/size and the preserved historical manifest, and resolves the repo root with `.resolve()` (works from any CWD).
- **New** `tests/unit/test_sprint424_heldout_guard.py` (19 tests).

### 3.4 Exact correction
Failure modes are all fail-closed: missing file; wrong SHA-256 or size; wrong declared split; wrong scenario count; per-scenario split label mismatch; duplicate ids; held-out requested for `purpose="selection"` (even with an active guard); held-out without a guard or without an active token. The pins live in source rather than in the manifest, so editing a data file and its manifest together is still detected.

### 3.5 Regression tests
Correct location; different CWD (also the sealed script run as a subprocess from a temp directory); missing development and missing held-out file; wrong hash on both; wrong identity with a matching hash; dev bytes substituted into the held-out slot and vice versa; unknown split/purpose; held-out for selection with an active guard; no guard; registered-but-inactive token; authorised final access logged; `evaluate_dataset_split` without a guard raises; static checks that the selection path (`build_dev`, `stage_select`, adversarial loader) contains no held-out reference; and no sealed-file literal in either script.

### 3.6 Before / after and integrated execution
- `python3 scripts/verify_heldout_sealed.py` → **4/4 PASS** (also from another CWD). Observation during the sprint: the scanner flagged my own first draft of a new test file that named the sealed file literally, which confirms the gate is active; the tests now derive the name from the registry.
- Sprint 4.2.3 frozen-threshold regression: re-scoring all 7 detectors on the development series through the registry reproduces `thresholds_frozen.json`'s stored TP/FP/FN/TN exactly (1246 series).
- **Disclosure:** the new tests load the sealed file with an active guard to assert count/identity (15 scenarios). No label from it was used for any selection, and this sprint did not re-run the held-out detector evaluation.

---

## 4. Issue 4 — Dataset manifest 69 vs 50

### 4.1 Original failure
`manifest.json` declared 69 scenarios (36/18/15) while `development.json` contains 50 and the deployed corpus is 83 (50/18/15).

### 4.2 Root cause (established by re-running the generator and diffing)
`SyntheticBenchmark().generate_all_faults(42)` yields exactly 69 (36/18/15; 48 confounded) — the manifest is the generator's output. `development.json` holds those 36 plus **14 hand-added** scenarios (`MC_02`–`MC_12`, `AA_01`–`AA_03`) from the P0-02 remediation, which expanded the H3 multi-cause filter to n = 15. The manifest was not regenerated. Full provenance is in `docs/RIFT_DATASET_PROVENANCE.md`.

### 4.3 Changed files
- `datasets/rift_faults/manifest.json` — now schema `rift.dataset_manifest/2`: legacy keys with deployed values (83; 50/18/15) plus `generator_output`, `files` (counts, unique ids, SHA-256, split, hand-added ids, selection flag), `reconciliation`, `fault_id_collisions_across_files`, `held_out_scenarios_with_content_twin_in_other_split`.
- **New** `datasets/rift_faults/manifest.v1_generator_69.json` — byte-identical copy of the original (SHA-256 `8fe47d27…1fde1`, equal to the `HEAD` version).
- **New** `scripts/sprint424_build_dataset_manifest.py` (`--write` / `--check`).
- `src/rift/fault_injection/fault_injector.py` — import-time check constant `MANIFEST_SPLIT_DEVELOPMENT` 36 → 50 (the check would otherwise have rejected the corrected manifest).
- **New** `tests/unit/test_sprint424_dataset_manifest.py` (15 tests); **new** `docs/RIFT_DATASET_PROVENANCE.md`.
- No scenario file was modified. The dataset-version hash taken by `src/rift/provenance/logger.py` changes with the manifest (expected). `analysis/tables/table4_scenarios.py` reads counts from the split files and ran against the new manifest.

### 4.4 Findings that go beyond the reconciliation
- **Fault-id collisions:** `MC_02` (development vs validation) and `MC_03` (development vs held-out) denote different scenarios. 83 scenarios, 81 unique ids. Join on `(split, fault_id)`.
- **Content duplication:** the 83 scenarios contain 25 distinct contents. Every one of the 15 held-out scenarios has a content-identical twin (differing in id, name, seed) in development or validation. Held-out is separated by file and seed but is not content-independent. This is a pre-existing property of the generator, not changed here, and it limits what held-out results can support.
- Held-out was read in earlier stages (`docs/FINAL_HELD_OUT_EVALUATION.md`, Sprint 4.2.3 once).

### 4.5 Regression tests
Builder output equals the committed manifest; counts and hashes match the files and the registry pins; unique-id counts; historical manifest hash and its 69; regeneration yields 69 = 36+18+15; difference is exactly the 14 named ids; generator scenarios are field-identical in the deployed files; id collisions and held-out content twins are recorded; adversarial cohort listed separately and excluded from 83; the fault-injector import check accepts the canonical manifest and rejects the stale one.

### 4.6 Integrated execution
`python3 scripts/sprint424_build_dataset_manifest.py --check` → "manifest.json is current". The fault injector imports. Dataset hashes: development `d8960776…`, validation `2363f6bb…`, held-out `4337675b…`, adversarial `46e769c6…` — all unchanged.

---

## 5. Final integration validation

| Check | Result |
|---|---|
| Full suite `python3 -m pytest -q -p no:cacheprovider tests` | **782 passed** |
| Sprint 4.2.4 test files | 23 + 19 + 15 + 25, all passing |
| Real E2E RIFT-FULL inference | Stage 4 saved telemetry → FCI → EBD → identifiability → abstention (§1.6); batch evaluator re-run on dev and validation |
| Valid and invalid R4 CID through the integrated runner | §2.6 (DEFINITIVE reachable; null-post, 60 s, wrong-key, insufficient evidence rejected) |
| Four guard checks | `verify_heldout_sealed.py` 4/4 |
| Dev/validation reproduction vs `artifacts/evaluation/*` | all 8 methods identical on both splits, timing excluded |
| Sprint 4.2.3 dev detector scores | identical to frozen artifact (§3.6) |
| Manifest counts and hashes | verified by builder `--check` and tests |
| Historical Stage 4 data | `artifacts/stage4_intervention_results.json` SHA-256 `e4cf1391…dcffe` unchanged |
| Protected components | No edits by this sprint to `src/rift/intervention/**`, `src/rift/safety/**` or `scripts/stage4_intervention_orchestrator.py`. (Working-tree modifications to `linux_tc_netem.py` and `safety.py` pre-date this sprint and were not touched.) |

## 6. Remaining limitations

1. **Stage 4 is a single trial.** No accuracy can be estimated; the pipeline abstains on it, and the abstention is sensitive to the FCI α. A defensible attribution result needs repeated trials with ≥ 20 samples per phase and non-plateau series.
2. **R4 on live data is out of reach with the current Stage 4 sampling** (15/12 samples).
3. **Held-out is not content-independent** of development/validation and has been read before; held-out results must be described as generalisation to new seeds of known templates.
4. **Per-id joins across splits are unsafe** (`MC_02`, `MC_03`); the ids were not renamed to avoid altering pinned data.
5. The `CF_xx` and template repetition means effective scenario counts are lower than 83 for any statistical test.
6. The E2E CID fixture is synthetic.
7. Findings are validated on synthetic ground-truth scenarios and intervention-consistent evidence only.

## 7. Reproduction

```bash
python3 -m pytest -q -p no:cacheprovider                                   # 782 passed
python3 scripts/verify_heldout_sealed.py                                    # 4/4
python3 scripts/sprint424_build_dataset_manifest.py --check
python3 scripts/sprint424_stage4_offline_attribution.py
shasum -a 256 artifacts/stage4_intervention_results.json                    # e4cf1391…dcffe
python3 -m pytest -q -p no:cacheprovider tests/unit/test_sprint424_*.py tests/integration/test_sprint424_cid_r4_integration.py
```
