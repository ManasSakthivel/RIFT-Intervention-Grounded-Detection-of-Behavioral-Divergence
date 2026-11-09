# Final Ground-Truth Independence Report (Agent 1, D23)

Branch `remediation-and-manuscript-closure`. Scope: label circularity. Read-only on every frozen dataset, result and the
frozen generator (`generator_v2.py` sha256 `5e68b223…477d37` and `simulator.py` sha256 `a93a0e42…1a8e` are unchanged and still
equal the `freeze_manifest.json` entries). Only dev/val (`datasets/rift_v2/{dev,val}.json`) were read. `heldout_candidate.json`,
all held-out results and every confirmatory path were not opened.

## 0. Bottom line

* Label circularity is **mitigated, not resolved.** A fully independent label cannot exist inside a simulator written by the same authors.
* Delivered: a threshold-free structural label **L-struct** and four continuous detectability covariates, implemented in a new module, with 16 tests that mechanically prove it does not import, call or copy the detector/label thresholds (3.0 σ onset, persistence 2, SNR 4.0, 1.0 σ effect, 30 s / 45 s timing).
* L-struct is a **co-reported sensitivity label.** It does not replace the frozen primary label and **no historical record or result was relabelled or modified.**
* Important empirical finding (dev+val, post-hoc, descriptive): **the V3-vs-always-abstain outcome-accuracy comparison reverses sign depending on which label is used** (§5). That makes the result label-dependent. It is not evidence that V3 works.
* D23 recommendation: **ADOPT-WITH-CHANGES** (§7). It still needs the owner's decision and independent human review (D7); neither has happened.

## 1. Files

| file | status | purpose |
|---|---|---|
| `src/rift/scenarios/l_struct.py` | new, untracked | `l_struct()`, `detectability_covariates()`, `annotate()` |
| `tests/unit/test_l_struct.py` | new, untracked | 16 independence and behaviour tests |
| `scripts/final_l_struct_sensitivity.py` | new, untracked | dev/val-only descriptive rescoring; writes a **new** file only |
| `artifacts/final_closure/l_struct_sensitivity_devval.json` | new, untracked | output of the script above (dev/val, non-confirmatory) |
| `docs/FINAL_GROUND_TRUTH_INDEPENDENCE_REPORT.md` | new | this report |

Nothing tracked was edited by Agent 1. `generator_v2.py` / `simulator.py` are untouched, so the existing 51-file freeze manifest remains valid. New files are not in that manifest and must be added at G3 if D23 is adopted.

## 2. Design

### 2.1 Separation of structural identifiability from observational detectability

| layer | question | form | contains thresholds? |
|---|---|---|---|
| **L-struct** (`l_struct`) | Is there a fault, an observed true root, a non-symmetric structure and a long-enough baseline? | binary + reason | none on signal, effect, persistence or timing |
| **Covariates** (`detectability_covariates`) | How strongly, how soon, how separably does the world express the root? | continuous, never folded into the label | none |
| **Frozen primary label** (`compute_ground_truth`) | Is it identifiable *by RIFT-style rules*? | binary | 3.0 σ, 2 windows, SNR 4.0, 1.0 σ, 45 s |

L-struct is exactly steps 1–4 of the frozen cascade (`FINAL_SCIENTIFIC_VALIDITY_CLOSURE.md` §1.1), and none of steps 5–6.
It is verified identical to "frozen `abstain_reason` not in {NO_FAULT, ROOT_UNOBSERVED, SYMMETRIC_MUTUAL_DEPENDENCY, INSUFFICIENT_BASELINE}" on all 252 dev/val scenarios (`test_equals_structural_steps_of_frozen_cascade`). This is a consistency check, not relabelling.

### 2.2 Covariates (all noise-free, label-only, unthresholded)

| field | definition |
|---|---|
| `root_snr_noisefree` | max over observed roots of max\|noise-free fault signal\| in σ units |
| `expected_do_effect_sigma` | best raw expected `do()` effect in the descendant's σ units, `magnitude·σ_r·delivered·Σgain/σ_d` |
| `effect_arrival_latency_s` | `delay_s + 2·min path lag / Δt` for that best effect (reported, not compared with 45 s) |
| `temporal_separation_s` | earliest *specified* appearance at other fault-affected observed services minus the best root's earliest appearance (onset + path lag + telemetry delay). Uses only fault specification and graph lags; no amplitude, noise or detector. Negative means another service shows the fault first |

`annotate(sc)` returns a deep copy with `label_structural`, `label_structural_reason`, the four covariates and `l_struct_version` written into `design`. `design` is already in `independence.LABEL_FIELDS`, so `strip_labels` removes these fields before any method sees a record (tested). Generation reads no `ground_truth` and no method output (tested).

### 2.3 Why this is not wired into the frozen datasets

`generator_v2.content_hash` hashes `design`. Adding fields to dev/val/held-out/adversarial records would change their content hashes and the frozen manifests. So D23 is applicable **only to a new, separately preregistered generator** (consistent with `FINAL_APPROVAL_MATRIX.md` D23). For existing dev/val the fields can be computed on the fly (as the script does) without touching the files.

## 3. Tests (`tests/unit/test_l_struct.py`, 16 tests, all pass)

Static (AST) independence:
1. `test_imports_exclude_detector_and_label_modules`: no import of `generator_v2`, `ebd`, `attribution_v3`, `evaluation`, `baselines`, `pipeline`, `cid`, `validators`, and no import of `detectable_onset_window` / `compute_ground_truth`.
2. `test_no_forbidden_identifiers`: those names plus `_check_r1`, `theta_detect`, `theta_persist` do not occur anywhere in the module.
3. `test_no_detector_threshold_numeric_literals`: no numeric literal 3, 4, 30 or 45 in the module.
4. `test_label_function_does_not_read_ground_truth_or_method_output`.
5. `test_module_defines_no_detector_constants` (`MIN_POST_REFERENCE_WINDOWS == 8` is the only budget constant).
6. `test_does_not_reference_sealed_split`.

Behavioural:
7. Label and covariates still compute when `detectable_onset_window` is monkeypatched to raise (detector is never called).
8. Label unchanged when `ground_truth` is deleted.
9. L-struct equals frozen steps 1–4 on all 252 dev/val scenarios.
10. Shrinking every fault amplitude ×0.05: L-struct unchanged, while the frozen label flips for at least one ATTRIBUTE scenario (demonstrates the two labels differ exactly in threshold dependence).
11. L-struct invariant to intervention magnitude.
12–14. Covariates are continuous (>50 distinct SNR values), span both sides of the old thresholds (min < 3 < max), scale linearly with amplitude, and the effect covariate reports values both below and above 1.0.
15. `annotate` does not mutate its input, leaves the primary label equal, and its fields vanish under `strip_labels`.
16. Annotating does not alter the committed dev/val files.

Results: `tests/unit/test_l_struct.py` 16 passed. Adjacent suites (`test_sprint430_independence.py`, `test_leakage.py`) 37 passed in total with it. Full `python3 -m pytest tests` (Python 3.9.6): **904 passed, 0 failed, 0 skipped**.

Limits of these tests (stated plainly): they prove there is no *code* dependence on the detector or its constants. They cannot prove conceptual independence (§6).

## 4. Dependency audit: ground-truth generator vs. detector

Method: grep/AST of `src/` and `scripts/` for imports and constant use.

| edge | finding | verdict |
|---|---|---|
| `generator_v2` → `simulator` | imports `apparent_signal`, `detectable_onset_window`, `observed_services`, `path_responses`, `_graph`, `DELTA_T`, `REF_WINDOWS` (`generator_v2.py:25`) | label uses a detector-style helper that lives in the *simulator*, with default `theta=3.0` (`simulator.py:246`) |
| detector (`ebd`, `rift_v2`, `rift_v3`) → `generator_v2` / `simulator.detectable_onset_window` | none found | **no code import from detector to label code** |
| detector constants | `theta_detect=3.0, theta_persist=2` literals in `ebd.py:298-299`, `rift_v2.py:185`, `rift_v3.py:146`; separate `INCIDENT_START = 100.0` literal in `rift_v2.py:32` vs. `simulator.INCIDENT_START = REF_WINDOWS*DELTA_T` | **shared by value, not by import.** Changing one does not change the other, which is how the dependence stays invisible |
| methods → simulator | `benchmark_v2.py`, `diagnostics.py` use `sim.observe`, `sim.intervene`, `sim.observed_services`, `sim._graph` | legitimate: the world model |
| evaluation → labels | `benchmark_v2.py:115,198-204,227`: `ground_truth` read by `score_one` and by explicit ORACLE methods only | scoring side only (as documented) |
| `attribution_v3/adversarial.py:22,179` → `compute_ground_truth` | adversarial cohort is labelled with the frozen rule | adversarial labels inherit the same circularity |
| `scripts/final_label_circularity_audit.py`, `artifacts/sprint4_5_1/review/label_margin.py` | import `detectable_onset_window` / `apparent_signal` | diagnostics only |
| generator → method output | none (reads `design`, graph, telemetry, intervention only) | **no method-output leakage** (confirms the prior verdict) |

Conclusion of the audit: circularity is **definitional (shared constants and shared vocabulary), not code-level leakage.** The only code coupling is the label calling a simulator-resident helper whose default equals RIFT's detector threshold.

## 5. Empirical consequence on dev+val (N = 252; descriptive, post-hoc, non-confirmatory)

Source: `scripts/final_l_struct_sensitivity.py` → `artifacts/final_closure/l_struct_sensitivity_devval.json`. Scores reused from existing per-scenario files (`artifacts/sprint4_3_0/results/*/per_scenario.json`, `artifacts/sprint4_4_0/v3_*.json`); nothing re-run.

Label composition: L-struct positive 163; frozen ATTRIBUTE 99. The 64 difference scenarios are frozen "ABSTAIN_REQUIRED" for signal reasons only (SNR < 3: 16, [3,4): 30, ≥ 5 with no discriminating evidence: 18).

Scoring convention for the sensitivity (new, **not** the frozen scoring): on L+ a root in `ground_truth.roots` is correct, another root is wrong, abstention is a missed attribution (neither correct nor unsafe); on L− any answer is unsafe, abstention is correct.

| | frozen label (existing reports) | L-struct sensitivity |
|---|---|---|
| Always-abstain outcome accuracy | 153/252 = 0.607 | 89/252 = 0.353 |
| RIFT V2 outcome accuracy | 137/252 = 0.544 | 120/252 = 0.476 |
| RIFT V3 outcome accuracy | 160/252 = 0.635 | 141/252 = 0.560 |
| RIFT V2 unsafe | 79/252 = 0.313 | 63/252 = 0.250 |
| RIFT V3 unsafe | 48/252 = 0.190 | 30/252 = 0.119 |
| Always-abstain unsafe | 0 | 0 |
| V2 / V3 correct root among L+ (n = 163) | n/a | 52 (0.319) / 63 (0.387) |

Frozen-column V2/V3 numbers were recomputed from the same per-scenario score files (`score.p2`, `score.unsafe`): V2 p2 = 137, unsafe = 79; V3 p2 = 160, unsafe = 48 (N = 252); they match the dev+val sums in `docs/SPRINT4_4_0_FINAL_REPORT.md` (102+35, 116+44). Always-abstain frozen accuracy = 1 − 99/252.

Reading:
* Under the frozen label V3 does not beat always-abstain materially on outcome accuracy (0.635 vs 0.607, not significant per the existing statistical audit). Under the L-struct convention V3 appears far ahead (0.560 vs 0.353). **The sign and size of the V3-vs-abstain gap depend on a labelling choice.** This is the strongest direct evidence of label-sensitivity.
* The L-struct gain for always-abstain is not a robustness result for RIFT: L-struct counts every abstention on a structurally attributable but undetectable scenario (SNR < 4, 46 scenarios) as a failure. Conversely, the frozen label counts a correct-root answer on those scenarios as unsafe. Neither convention is neutral. Among L-struct-positive scenarios with SNR < 4 (46 scenarios, all frozen ABSTAIN_REQUIRED), V3 answered 18 times and the top-1 was a true root in 14 of them; V2 answered 22 times with a true root in 12. The frozen score counts all of these as unsafe; L-struct counts the 14 and 12 as correct. Whether such hits reflect information or chance (small graphs, candidate ordering, a single root per scenario) was **not investigated** and must not be claimed as skill.
* Stratified by the SNR covariate (`strata` in the JSON), V3's frozen-correct root answers sit where SNR ≥ 5 (39 of 102 L+ scenarios in that band) and in [4,5) (6 of 15); the SNR < 4 hits above are not frozen-correct by construction.
* This analysis was run **after** seeing results, on development data; it is exploratory. Any use in a paper must be labelled post-hoc and must be accompanied by the frozen-label numbers. It cannot be used to claim superiority over always-abstain; that claim would rest on choosing the label that makes it true.

## 6. What L-struct does not fix (remaining circularity channels)

1. `structure == "ambiguous"` is a generator *dimension*, not a computed symmetry test. The symmetric-dependency abstention is true by authors' construction.
2. `INSUFFICIENT_BASELINE` uses the generator's own budget `n_windows < REF_WINDOWS + 8`; the `+8` is copied from the frozen cascade (declared as `MIN_POST_REFERENCE_WINDOWS`) and `REF_WINDOWS = 10` is the same reference length the detector assumes.
3. `expected_do_effect_sigma` is the same closed-form quantity the frozen rule thresholds; only the threshold is removed. The raw quantity is a property of the simulator's linear model, which is also what the intervention-based method estimates.
4. The simulator itself (linear-Gaussian, authors' choice of shapes, lags, noise) defines "the world". Both labels and methods live inside it. No external or real-system ground truth exists.
5. L-struct treats a root as attributable even when no finite-sample method could detect it (SNR < 3, 16 cases). It is *structural* identifiability only. **Structural truth cannot establish practical identifiability** in these cases: weak SNR, hidden or unobserved roots, `no_meaningful_effect` interventions, delayed telemetry, intermittent faults that vanish inside the 30 s `do()` window, and sub-1σ effect sizes. That is why the covariates are mandatory co-reports and L-struct must never be presented alone.
6. The adversarial cohort (112) and the spent held-out V2 run are labelled by the frozen rule; they are not independent evidence under D23 and nothing was relabelled.
7. The L-struct fields can only be produced for dev/val on the fly; frozen record files do not contain them.

## 7. D23 recommendation (explicit)

**Decision: ADOPT-WITH-CHANGES, as a co-reported sensitivity analysis only.**

Adopt:
1. Keep the frozen label as the sole primary endpoint (PRE §10 / §12 L2 unchanged).
2. Add L-struct plus the four covariates as preregistered descriptive co-reports, emitted by any *new* confirmatory generator into the label-only `design` block.
3. Report SNR bands (< 3, [3,4), [4,5), ≥ 5) per method for both labels.

Changes required before adoption (these are the conditions, not optional):
1. **Pre-specify the L-struct scoring convention** (as in §5, or an alternative) in the SAP before data exist. Report outcome accuracy under both conventions and the frozen label; do not choose the convention after seeing which flatters V3.
2. State in the manuscript that the V3-vs-always-abstain outcome comparison is **label-dependent** (§5) and that this is a limitation, not a rescue.
3. Do not describe L-struct as "independent ground truth". Call it "threshold-free structural sensitivity label".
4. Disclose §6 items 1–5 in Threats to Validity.
5. Independent human review (D7) of `l_struct.py`, the stripping of the new fields, and the scoring convention. **Not performed.** No reviewer is named; do not simulate one.
6. Add `src/rift/scenarios/l_struct.py`, `tests/unit/test_l_struct.py`, and the SAP amendment to the G3 hash set; the owner records D23 in `decisions.json`.

Reject-alternatives considered: (a) replace the primary label: rejected, would invalidate comparability with every frozen result and be post-hoc; (b) relabel dev/val and re-report: rejected, forbidden retrospective relabelling and unjustified; (c) do nothing: leaves the label-dependence of the headline comparison undisclosed.

If the owner or reviewer rejects D23, the fallback in `FINAL_SCIENTIFIC_VALIDITY_CLOSURE.md` §1.8 applies: word every conclusion as "relative to the simulator's identifiability rule", with circularity as a disclosed limitation.

## 8. Reproduction

```
python3 -m pytest tests/unit/test_l_struct.py -q -p no:cacheprovider      # 16 passed
python3 scripts/final_l_struct_sensitivity.py                               # dev/val only; writes artifacts/final_closure/l_struct_sensitivity_devval.json
python3 -m pytest tests -q -p no:cacheprovider                              # 904 passed
```

## 9. Handoffs and status

* Agent 4 (pipeline): the confirmatory generator must call `l_struct.annotate` (or equivalent) inside the label-only `design` block and the new files must be hash-registered at G3.
* Agent 3 (statistics): the SAP must pre-specify the L-struct scoring convention and treat L-struct/SNR-band tables as descriptive and uncorrected.
* Agent 7 (manuscript): cite §5 as exploratory, report both label columns, do not assert independence.
* Agent 8 (red team): please independently check §3 test strength, §4 audit, and the §5 numbers (frozen-column totals were recomputed in this task and match).
* Gate effect: D23 stays **PROPOSED, NOT APPROVED** until the owner records a decision and a real human reviewer signs. G0/G2/G3 remain BLOCKED by that.
* No claim of confirmatory validation, no relabelling of historical results, and no change to frozen files was made.
