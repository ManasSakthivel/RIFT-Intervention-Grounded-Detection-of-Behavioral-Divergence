# Sprint 4.5.0 — Execution Plan
## Preregistered Confirmatory Evaluation and Intervention Evidence Reliability
> **REVISION 3 (Sprint 4.5.1, branch `sprint-4.5.1-prereg-finalization`).** Corrections since revision 2: (i) the 16 structures are fixed experimental strata and the claim is restricted to those 16 motifs, with a three-level hierarchy (structure / generator-assigned group / scenario) and K = 256 groups (PRE §1.1, Dataset Protocol §2); (ii) power was re-verified by Monte-Carlo and the closed-form figures are labelled optimistic (SAP §6.7); (iii) the freeze was extended to a 69-file manifest with roles (PRE §2; `artifacts/sprint4_5_1/freeze/extended_manifest.json`); (iv) error semantics belong to `benchmark_v2._timed`, and a hashed runner `scripts/sprint450_run_confirm.py` is required (SAP §7); (v) seven core estimators E0–E6 and 218 design cells (214 factorial + 4 mixture) = 210 distinct DGPs (CID design); (vi) new decisions D19–D22. The preregistration is **not fully approved** (D7 and D12 are BLOCKERs). Revision 2 follows.
>


> **REVISION 2 (2026-11-03, checkpoint `be5e0318fcd9cb17285ce6b8dff632cb68274b65`).** This plan was audited. The binding design now lives in `SPRINT4_5_0_PREREGISTRATION.md`, `SPRINT4_5_0_STATISTICAL_ANALYSIS_PLAN.md`, `SPRINT4_5_0_CID_EXPERIMENT_DESIGN.md`, `SPRINT4_5_0_DATASET_PROTOCOL.md` and `SPRINT4_5_0_FINAL_PREREGISTRATION_AUDIT.md`. **Where this document differs from them, they govern.** The text below is kept for history, and the superseded passages are marked **[SUPERSEDED]** with the replacement. Changes:
>
> | section | change |
> |---|---|
> | §1.5 | **[SUPERSEDED]** The untracked-dependency gap no longer exists: commit `db77446` (Sprint 4.4.1) tracked the dependencies. All 51 manifest files match HEAD (`artifacts/sprint4_5_0/prereg/freeze_manifest.json`). |
> | §1.4 | test baseline is 886 reproducible + 2 protected on the full tree (4.4.2); 663 reproducible + 2 unavailable on a clean export; the "880" figure is outdated |
> | §2.2–§2.3 | **[SUPERSEDED]** utility is U = C − λS − γ·c with c = n_do/20, λ = 2, γ = 1 (= κ 0.05), δ = 0.10 (judgements; audit §3) |
> | §2.5 | **[SUPERSEDED]** N = 800 is insufficient (54% power at DEFF 2); N = 2000 from ≥ 250 groups (SAP §6) |
> | §2.6 / §6 | **[SUPERSEDED]** H1 first at one-sided 0.025, then Holm over {H2, H3, H4}; studentised group bootstrap; labels in PRE §10 |
> | §3 | **[SUPERSEDED]** by the CID experiment design (218 cells, seven core estimators E0–E6 plus a placebo-timing layer E7, acceptance criteria) |
> | §4.2 | **[SUPERSEDED]** the frozen generator cannot be reused (176/176 templates consumed; `KeyError: 'confirm'`): new generator module, new structures (Dataset Protocol §2–§3) |
> | §4.3 | **[SUPERSEDED]** no membership-only held-out check exists; independence by construction (Dataset Protocol §8) |
> | §5.1 | **[SUPERSEDED]** V3-CIDx is outside this sprint's confirmatory family (PRE §8) |
> | §9 | replaced by the decision register in the audit §10 (D1–D18, A1–A9) |

**Status: PLAN ONLY (audited, not executed). No Sprint 4.5.0 code, data generation or evaluation has been started.**
This document is a draft preregistration. It becomes binding only when it is hashed and recorded (§2.8) *before* any confirmatory scenario is generated or any frozen method is run on one. Until then, items marked **[DECISION]** need the project owner's approval.

Prepared on branch `sprint-4.4.0-v3-attribution` (checkpoint commit `b33ad64`, "Sprint 4.4.0: add V3 attribution and evaluation"). Everything below is offline and synthetic. No live intervention is planned, and the Sprint 4.3.0 held-out set is never reopened.

**Research question.** Does frozen RIFT-FULL-V3 provide useful and safe root-cause attribution beyond always-abstain, using intervention evidence robust to unrelated temporal changes?

**Language rule.** Results will be described as "validated on synthetic ground-truth scenarios" and "intervention-consistent". The words "causally accurate", "production-ready" and "guarantees" are not used, and a CANDIDATE-grade CID check is never called definitive evidence.

---

## 0. Where we start (from Sprint 4.4.0, dev/val only)

These numbers motivate the design. They are not evidence for the confirmatory hypotheses, because they come from data that informed V3's design.

| quantity | dev (n=180) | val (n=72) | source |
|---|---|---|---|
| V3 P1 (correct root, of ATTRIBUTE) | 32/68 | 13/31 | `artifacts/sprint4_4_0/analysis.json` |
| V3 unsafe answers | 35 | 13 | same |
| V3 P2 minus always-abstain P2 | +0.022 (p=0.70) | +0.042 (p=0.68) | same |
| mean interventions per scenario (V3 / V2) | 2.51 / 1.49 | 3.19 / 1.71 | same |
| non-ancestral CID false-positive rate, no drift / drift > 0.3σ | 5.6% / 94% | 6.7% / 100% | `cid_audit.json` |

**Consequence for the expected outcome.** Pooled dev+val, V3 has 45 correct attributions and 48 unsafe answers (10 on ATTRIBUTE scenarios, 38 on ABSTAIN_REQUIRED). With unsafe cost λ and per-scenario utility U = 1[correct] − λ·1[unsafe] − κ·n_interventions, V3's utility is positive only when λ is small. The break-even is λ ≈ 0.94 (45 correct / 48 unsafe) with κ = 0 (λ = 0.91 dev, 1.00 val). At λ = 2 and κ = 0.05, mean utility is −0.338 for V3 and −0.562 for V2, against 0 for always-abstain. **If the confirmatory data resemble dev/val, V3 is expected to fail the primary endpoint at any λ ≳ 1.** The plan is built so that this outcome is reported as a result, not treated as a defect to repair.

---

## 1. Freeze V3

### 1.1 What is frozen
V3 (`V3-FULL`) as committed in `b33ad64`, with the configuration in §1.3, its inherited constants, and its dependencies. After the preregistration hash is recorded (§2.8), no change is permitted to any file in §1.2. A needed change means a new, separately named method that is reported as post-hoc and exploratory.

### 1.2 Hashes at the time of writing (SHA-256)
Re-compute and re-record these at preregistration time. Any difference from this table, caused by anything other than the explicit steps in §1.5, stops the sprint.

**V3 source (committed in `b33ad64`)**

| path | sha256 | git state |
|---|---|---|
| `src/rift/attribution_v3/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | committed |
| `src/rift/attribution_v3/rift_v3.py` | `03e84568702a6f9da8c5ea09cadf4ee794eb5553b8c1fc1cc89b1f662f6d0bf8` | committed |
| `src/rift/attribution_v3/pag_semantics.py` | `f9ffd15dbbfb0ec5c6ea2f707a39d6705fe895294b010eaea65b4a9310a04282` | committed |
| `src/rift/attribution_v3/diagnostics.py` | `bc89410af64a71b2bd4a44eed8a320c3ed4d097a4fe1277ae50b5afccabcff14` | committed |
| `src/rift/attribution_v3/adversarial.py` | `b9fa6b5eb6476436e1890cc75a3a1078b676faf8da77cd12f461aa16f7cd8e55` | committed |

**V3 evaluation scripts and tests (committed in `b33ad64`)**

| path | sha256 |
|---|---|
| `scripts/sprint440_run_v3.py` | `629bee0e44f7f2d556326fb1b17a8b232180e39c32b1b69247f883e944c8237c` |
| `scripts/sprint440_analyze.py` | `0de11ae4456ef163e52c4604458c3cf8e3402aaca10f7de22b4ad942e387e740` |
| `scripts/sprint440_cid_audit.py` | `57159646799241653d564fb93f777a196a513c8e8341da2042409d40df2f65b8` |
| `scripts/sprint440_adversarial.py` | `d2c0a55482d2bf1b6ea4dbfe96e4771a1cbd7a81bbfd8c3aed07a9fd5394f3df` |
| `scripts/sprint440_trace_failures.py` | `dfca0c3c635fb9208301e62bcfcc06227731076f5dbdb2c7372a8a0d1c2eb6e7` |
| `tests/unit/test_sprint440_attribution_v3.py` | `4c52164b4ed1fe9bef00cecc450764cd64e23eb168fd4040a358edc60ace0a58` |

**Frozen dependencies V3 imports. These are NOT in `b33ad64`; see §1.5.**

| path | sha256 | git state |
|---|---|---|
| `src/rift/evaluation/rift_v2.py` | `9eeb80dad46d62bab35c5bc73fefaa9a1137c3b6d6f1dec7ba85a56734fb80bf` | untracked |
| `src/rift/evaluation/benchmark_v2.py` | `efc5fcf4a947e12f608aa173f5f4f7d0d7b03f0a04120213c6f503e09eafce92` | untracked |
| `src/rift/evaluation/stats_v2.py` | `762962f1664e9d79ebc4082279a6aa6833dcc7f46957588bc8a19da8d89e9d0e` | untracked |
| `src/rift/evaluation/dataset_registry_v2.py` | `db8319ef3851d4d6448f36a9832db3309fe999837289fb81d240da1da5782820` | untracked |
| `src/rift/ebd/ebd.py` | `43f0ad7cdda11fc4de4546b9c84263a64a2e34b76963ba8750ea56d574d7394b` | tracked, **modified, uncommitted** |
| `src/rift/fci/fci_runner.py` | `39c300156dfc6011771e4d30d21a1e155e096c23da445b13dcb85d075a3411f6` | tracked, **modified, uncommitted** |
| `src/rift/cid/cid.py` | `8282c6758614f6422ba835b2851746f3099887d8458a7049a57bd93a26027f32` | committed |
| `src/rift/cid/evidence.py` | `d8b8edc8cbcdb32ae115eed27026fd4440fa74a262911c069786bd0fb199f82b` | untracked |
| `src/rift/identifiability/identifiability.py` | `8eff5f06eca2b20f7e06023bf278ed99b9de2130fe1909d2360af58be258d454` | committed |
| `src/rift/baselines/__init__.py` | `8986097f416a6d015391006cff95f11a456ec5f3959aec0e366948c83dfbf3e0` | committed |
| `src/rift/scenarios/{__init__,simulator,generator_v2,fingerprint}.py` | `2f7e7c79…440` / `a93a0e42…a8e` / `5e68b223…d37` / `4f730ef7…778` | untracked |
| `datasets/rift_v2/dev.json` / `val.json` | `a833ad0c…ef5f` / `e82252b4…a1fb` | untracked |
| `artifacts/sprint4_3_0/freeze.json` | `f2b0997cfa700fa4378488d503f3b42022fee849dbf16359a6d418d4a772b806` | untracked |
| `artifacts/stage4_intervention_results.json` (historical; not a V3 input) | `e4cf1391c83bcb33070e8bc4ae3f8b792df2e0d1970df14524fc6c8d5d1dcffe` | untracked |

The 8-hex abbreviations in the scenario rows are for readability only. The preregistration record must hold full 64-character hashes. `verify_freeze()` currently returns `(True, 'ok')` over the 37-file Sprint 4.3.0 freeze list.

### 1.3 Configuration and decision rules (as in the code; nothing here may change)
* Config `V3-FULL`: `manipulation_check=True`, `earlier_guard=True`, `answer_statuses=(DEFINITIVE_ROOT, QUALIFIED_ROOT)`, `divergent_candidates=True`, `test_explained=True`.
* Inherited constants (`rift_v2.py`): `DELTA_T=10.0 s`, `ED_PER_DO_S=30.0 s`, `MAX_DO=20`, `CID_PERMUTATIONS=1000`, `CID_BOOTSTRAP=100`, `ALPHA=0.05`. EBD: `theta_detect=3.0`, `persist=2`.
* Decision rules: candidates = all EBD-R1 divergent services; outcomes = all other divergent services; Holm correction over outcomes; `validate_cid_for_r4` gate; a source has a confirmed effect and no confirmed effect from another intervened service; an unresolved earlier divergence blocks attribution; only `DEFINITIVE_ROOT` and `QUALIFIED_ROOT` are attributions. Confidence is ordinal, not a probability.
* Environment: Python 3.9.6, numpy 2.0.2, scipy 1.13.1, pandas 2.3.3, networkx 3.2.1, scikit-learn 1.6.1, causal-learn 0.1.4.8. Record `pip freeze` into the preregistration artifact.

### 1.4 Freeze verification at execution time
1. Re-hash every file in §1.2 and compare.
2. Run `python3 scripts/sprint442_run_tests.py --require-protected` on the owner's full tree (886 reproducible + 2 protected at Sprint 4.4.2); on a clean export 663 reproducible + 2 unavailable + 0 failures. **[REVISION 2]** (the earlier figure of 880 is outdated)
3. Run `verify_freeze()` and `scripts/verify_heldout_sealed.py` (4/4).
4. Store the output as `artifacts/sprint4_5_0/prereg/freeze_verification.json`.

### 1.5 Reproducibility gap in the checkpoint **[SUPERSEDED — resolved in Sprint 4.4.1, commit `db77446`]**
Commit `b33ad64` contains V3's own files only. V3 imports `rift_v2`, `benchmark_v2`, the scenario simulator and generator, `cid/evidence.py` and `datasets/rift_v2/{dev,val}.json`, and these are all still **untracked**. It also depends on `ebd.py` and `fci_runner.py` in their **uncommitted modified** form. A fresh clone of the branch therefore cannot run V3 or reproduce the Sprint 4.4.0 numbers, and git history does not record which `ebd.py` / `fci_runner.py` produced them. Only the SHA-256 values above currently do.

Recommended before preregistration: a separate, reviewed commit on its own branch (suggested `sprint-4.5.0-freeze-dependencies`) that adds exactly the Sprint 4.3.0 freeze list (37 files), the dev/val datasets and their registry, with the held-out file excluded or handled under the existing guard. The two modified tracked files need a per-hunk review to decide whether those edits are Sprint 4.2.3 / 4.3.0 work. Nothing is committed without explicit approval, and nothing is pushed.

---

## 2. Preregistration of the confirmatory experiment

### 2.1 Hypotheses
All hypotheses are about frozen V3 on the confirmatory dataset (§4).

* **H1 (primary, superiority on utility).** Mean per-scenario utility of V3 exceeds that of always-abstain: E[U_V3 − U_AA] > 0, with U_AA = 0 by construction. Directional, one-sided.
* **H2 (secondary, versus V2).** Mean utility of V3 exceeds that of RIFT-FULL-V2: E[U_V3 − U_V2] > 0.
* **H3 (secondary, safety).** The unsafe-attribution rate of V3 is lower than V2's (paired).
* **H4 (secondary, accuracy).** P1 of V3 exceeds V2's (paired, ATTRIBUTE scenarios).
* **H5 (diagnostic, not confirmatory).** V3 outperforms the observational baselines (B0-EARLIEST, B0-HIGHEST, B1-LATENCY-CORR, B3-SIEVE-LIKE, B5-RIFT-OBS) on utility.

The null for each is "no improvement", and failure to reject is a reportable result. H1 is a gatekeeper: if H1 fails, H2 to H5 are reported descriptively and not as confirmatory successes.

### 2.2 Primary endpoint
Per-scenario utility difference D_i = U_V3,i − U_AA,i = U_V3,i, analysed with the paired mean over N scenarios at **λ = 2, κ = 0.05** (defined in §2.3). The estimate, its 95% scenario-clustered bootstrap CI and the one-sided test are reported.

### 2.3 Utility function and costs **[SUPERSEDED by PRE §3: normalised cost; see audit §3]**
For scenario i answered by a method:

U_i = 1 · [answered ∧ correct root] − λ · [unsafe] − κ · (number of do() interventions)

* "Correct" and "unsafe" use the Sprint 4.3.0 / 4.4.0 scoring (`benchmark_v2.score_one`), unchanged: correct = named service is a ground-truth observed root on an ATTRIBUTE scenario; unsafe = any answer on an ABSTAIN_REQUIRED scenario, or a wrong root on an ATTRIBUTE scenario.
* A correct abstention scores 0, and a missed attribution (abstaining on an ATTRIBUTE scenario) scores 0. Always-abstain therefore scores exactly 0. This choice favours always-abstain by not charging it for missed attributions. That is conservative for the claim and is stated openly.
* **λ = 2** (an unsafe attribution costs twice what a correct one earns) and **κ = 0.05** (20 interventions equal one correct root) are preregistered primary values chosen before seeing confirmatory data. They are a judgement about operator cost and not derived from data. The break-even analysis in §0 shows the conclusion depends strongly on λ, so the primary result will be accompanied by a full sensitivity grid λ ∈ {0.5, 1, 2, 5}, κ ∈ {0, 0.05, 0.1}, labelled secondary.
* Modelled recovery overhead (30 s per rollback) is reported as a model constant, not a measurement, and is not part of U.
* Prevalence matters: U depends on the share of ATTRIBUTE scenarios. The confirmatory set uses the Sprint 4.3.0 mix of about 40% ATTRIBUTE and 60% ABSTAIN_REQUIRED (dev 68/180 = 38%, val 31/72 = 43%). Break-even prevalence at λ=1 / λ=2 from dev+val is about 41% / 66%. Utility is reported stratified by expected outcome and the break-even prevalence is reported alongside.

### 2.4 Secondary and descriptive outcomes
P1 (correct root of ATTRIBUTE), P2 (answer-or-abstain correct), unsafe rate, coverage, abstention rate, wrong-root rate, conditional accuracy on answered ATTRIBUTE, unobserved-root handling (unsafe rate on unobserved-root ABSTAIN scenarios), mean intervention count, mean intervention duration (30 s each), modelled recovery overhead, decision latency (EBD detection latency plus intervention time), runtime. P2 versus always-abstain is reported but not powered (see §2.5).

### 2.5 Sample size **[SUPERSEDED: N = 2000; see SAP §6]**
Normal approximation for the paired mean, one-sided, power 0.80, using the V3 utility SD observed on dev+val (SD ≈ 0.98 on dev and 0.96 on val at λ=2, κ=0.05, so 0.976 is used; to be re-estimated on the CID-calibration data of §3, which is independent of the confirmatory data):

N = ((z₁₋α + z₀.₈₀) · SD / δ)²

| minimum effect δ (utility units) | α = 0.025 (H1 alone) | α = 0.025/3 (Holm worst case, 3 tests) |
|---|---:|---:|
| 0.10 | 748 | 997 |
| 0.15 | 332 | 443 |

* **Target N = 800 scenarios** (minimum 600 as required; below about 750 the design cannot detect δ = 0.10). This is the preregistered size unless the CID-calibration SD estimate changes it, in which case N is recomputed with the same formula, before generation, and recorded.
* Note the dev+val point estimate for V3 − AA at the primary values is *negative* (−0.338), so H1 rejecting is not expected unless the confirmatory data differ from dev/val or the evidence-reliability work (§3) matters. δ = 0.10 is the smallest improvement considered practically useful and is a judgement **[DECISION]**.
* P2 versus always-abstain is not an adequate primary because it is badly underpowered: with dev+val discordance (only-V3 45, only-AA 38 of 252; paired difference +0.028), about 3,300 scenarios would be needed for 80% power. This justifies utility as the primary and P2 as descriptive.
* Minimum detectable paired risk-difference for N = 800 (discordance 0.33): about 0.057.

### 2.6 Statistical analysis **[SUPERSEDED: see SAP §3–§5]**
* **Paired scenario-level analysis.** Same scenarios, same observed windows, same seeds for all methods.
* H1, H2: paired mean utility difference. Test = one-sided paired permutation (sign-flip, 20,000 resamples, fixed seed) with a paired t statistic as a sensitivity check. CI = 95% percentile bootstrap, resampling at the scenario-**group** level (the template/group IDs from the generator), because scenarios within a template are not independent.
* H3: exact McNemar on safe/unsafe discordant pairs. H4: exact McNemar on P1 (ATTRIBUTE only).
* Effect sizes: risk differences with 95% CIs; discordant-pair odds ratios; utility difference in absolute units.
* **Multiplicity.** Confirmatory family = {H1, H2, H3, H4}, Holm-corrected at 0.05 with the gatekeeping rule in §2.1. H5 and the sensitivity grid are exploratory and carry no inferential claim. Uncorrected p-values are always shown next to corrected ones.
* No subgroup claims: structure/family cells at N = 800 contain few scenarios. They are descriptive only.
* No imputation. Errors and timeouts count as abstentions and are tabulated (V3 maps errors to abstention).

### 2.7 Stopping rules
* Fixed sample, **no interim analysis, no early stopping for efficacy or futility**, and no sample-size re-estimation after confirmatory generation.
* **Integrity stops** (the run halts and is reported, not patched): any frozen-hash mismatch; any cross-split leak found by the grouped checks (§4.3); any ground-truth field reaching a method (leakage tests fail); held-out seal check fails; fewer than 95% of scenarios completing (the remainder reported).
* Each method is run once on the confirmatory data. Re-runs are allowed only for infrastructure failure, with the reason logged. Results from the first complete run are the reported ones.

### 2.8 Recording the preregistration
Before generating any confirmatory scenario:
1. Create `artifacts/sprint4_5_0/prereg/PREREGISTRATION.md` as a copy of this plan, completed with the [DECISION] values and final N.
2. Record its SHA-256, the §1.2 hashes, the git commit and an RFC 3339 UTC timestamp in `artifacts/sprint4_5_0/prereg/prereg.sha256` and in a ledger row.
3. Any later change is an amendment appended after a hash line and timestamp, never an edit, following the pattern of `docs/EVALUATION_PROTOCOL_V2.md` §16.

---

## 3. CID reliability experiment (Phase A) **[SUPERSEDED by `SPRINT4_5_0_CID_EXPERIMENT_DESIGN.md`; Phase A is independent of Phase B and cannot alter V3]**

### 3.1 Why a separate phase
Sprint 4.4.0 showed that, in the simulator, a CID "confirmation" is mostly uninformative when the outcome service has its own temporal change (94–100% significant among non-ancestral pairs with drift greater than 0.3σ, 17 pairs per split; 4–7% otherwise). The cause is plausible but untested: the 30 s baseline and 30 s post windows are consecutive, with no concurrent control. This phase tests it directly on purpose-built data. It does **not** assume that raising n from 30 to 50 fixes it. Longer windows might also include more drift.

Phase A produces an estimator selection under preregistered acceptance criteria. It never touches V3 or the confirmatory data.

### 3.2 Estimators compared
| id | estimator | note |
|---|---|---|
| E0 | existing CID (30 vs 30, permutation + W1 gate) | the baseline; unchanged `cid.py` |
| E1 | existing CID with longer windows (n = 45, 60, 90 per arm) | tests whether samples alone help |
| E2 | concurrent-control CID: compare change in y under do(x) with change in y in a simultaneous no-intervention control arm | needs a sham arm |
| E3 | detrended CID: fit and remove a pre-intervention trend (linear and seasonal terms fit on the baseline only) before testing | no control arm needed, but extrapolation risk |
| E4 | difference-in-differences: (post − pre)_treated-service-y − (post − pre)_control-service-y | needs a valid control series; also parallel-trends diagnostics |
| E5 | AR-aware test: block / circular-shift permutation preserving autocorrelation | addresses non-i.i.d. noise |
| E6 | a justified alternative proposed after E0–E5 diagnostics (e.g. E4 with a pre-trend placebo test), declared in writing before Phase A data are scored | optional |

All estimators use the same multiplicity treatment (Holm over outcomes) so that differences are due to the effect estimate, not the correction. Whether a given estimator is feasible in the current simulator is determined in §3.5.

### 3.3 Factorial simulation design
Factors, crossed where feasible. The effect is a true x→y shift of size d σ_y, or zero:
* **Genuine effect size** d ∈ {0, 0.25, 0.5, 0.75, 1, 2} σ_y, and delay of response ∈ {0, 5, 10 s}.
* **Independent outcome-service drift** (y's own fault contribution): none; linear ramp; step; oscillation (periods short and long relative to 60 s); intermittent pulses; recovery transient. Magnitude ∈ {0, 0.3, 1, 3} σ_y between windows.
* **Shared temporal drift** affecting both x's and the control service's series: none, common ramp, common oscillation (this is the case where DiD's parallel-trends assumption should hold).
* **Differential drift** between treated and control series (parallel-trends violation).
* **Autocorrelation** AR(1) ρ ∈ {0, 0.5, 0.8}.
* **Baseline variance change** between windows: variance ratio ∈ {1, 2, 4}.
* **Recovery instability** after rollback: overshoot / slow decay of x's own effect when the intervention ends.
* **Outcome count** m ∈ {1, 3, 6} for the multiplicity burden.

### 3.4 Negative and positive controls
* **Sham intervention:** run the full procedure with no perturbation of x (d = 0). The rejection rate must be at the nominal level.
* **Placebo outcome:** test a service that is not a descendant of x.
* **Placebo timing:** apply the estimator at a window pair where no intervention occurred.
* **Positive control:** x's own series (manipulation check), as in V3.
* **Pre-trend placebo** for E3 and E4: apply the estimator to two pre-intervention windows.

### 3.5 Required capability and the frozen simulator **[DECISION]**
`simulator.intervene()` returns one 30 s baseline and one 30 s post series per outcome and no control arm. `simulator.py` is frozen. Phase A therefore needs a **new module** (suggested `src/rift/cid_reliability/`) that wraps or re-implements the data-generating process to produce longer windows, a sham/control arm and controlled drift, without editing frozen files. It must itself be validated against `simulator.intervene()` in the E0 / n = 30 / no-control configuration: the reproduced E0 size and power must match the Sprint 4.4.0 figures (power ≈ 49% at 0.5σ, m = 1, i.i.d.) within Monte-Carlo error, or the new generator is not trusted. Real telemetry would also need a control arm; whether a concurrent control exists in a live system is outside this sprint's remit.

### 3.6 Power analysis for Phase A (declared before running)
For each cell of §3.3 × estimator, Monte-Carlo with **R = 2,000** replications (binomial SE ≤ 0.011 near 0.5), seeds derived from a Phase-A-specific hash tag, independent of all scenario seeds. Report type-I error (d = 0) and power (d > 0) with Wilson 95% CIs. Window length and sample size are chosen from these results, not from a rule of thumb. The Sprint 4.4.0 Monte-Carlo for E0 (n=30 vs n=60, i.i.d. noise, 150 draws per cell) is only a pilot: it shows n=60 raises power at 0.5σ from about 49% to about 75% (m = 1) but says nothing about drift.

### 3.7 Preregistered acceptance criteria for an estimator to be eligible
An estimator (E1 to E6) is eligible to define a pre-specified V3 variant (V3-CIDx) only if, on Phase A data:
1. Type-I error ≤ 0.07 (upper 95% Wilson ≤ 0.10) in **every** drift/autocorrelation/variance cell with d = 0, and in the sham and placebo controls.
2. Power at d = 1σ, m = 3 is at least that of E0 minus 0.05 in clean (no-drift) cells; power at d = 0.5σ is reported and not gated.
3. Added cost (samples, seconds per do()) is quantified, and the scenario time budget `MAX_DO × window` is not exceeded under the budget rule used by V3.
4. Its assumptions have a diagnostic and the diagnostic is reported (for DiD: parallel-trends test).
If none qualifies, the result is "no tested estimator restored validity", reported as a finding, and Phase B proceeds with E0 only.

### 3.8 Output
`docs/SPRINT4_5_0_CID_RELIABILITY_REPORT.md`; `artifacts/sprint4_5_0/cid_reliability/` (per-cell results, seeds, code hashes). If an estimator is eligible, its V3 integration is a **plug-in at a single interface** (the `compute_cid` call), written and frozen (hash recorded) *before* Phase B scenarios are generated.

---

## 4. Independent confirmatory dataset

### 4.1 Independence requirements
Confirmatory scenarios must be independent of: Sprint 4.3.0 dev, val and held-out; Sprint 4.4.0 adversarial dev set (`datasets/rift_v3_dev/`); Phase A data. Independence means no shared scenario ID, seed, content hash, dynamics hash, topology hash, template ID, near-duplicate (similarity < 0.90) or joint design cell, and not just different random seeds.

### 4.2 Generation **[SUPERSEDED: frozen generator has no free templates; see Dataset Protocol §2–§3]**
* Reuse the **frozen** generator (`generator_v2.py`, `compute_ground_truth`) unchanged, with a new split label (`confirm`) and a new seed-derivation tag, in a new script `scripts/sprint450_generate_confirmatory.py`. Seeds come from `sha256(<new tag>|confirm|idx)`; the tag is fixed in the preregistration.
* Targeted size N = 800 (≥ 600 required; §2.5), about 40% ATTRIBUTE / 60% ABSTAIN_REQUIRED, with the factorial design (families, structures, temporal, workload, observability, intervention, negative kinds) used in Sprint 4.3.0 so results are comparable, and with additional **unseen** template combinations so that the dataset is not a re-sampling of the same templates. The number of unobserved-root scenarios is fixed by design and reported.
* Ground-truth labels are generated by the simulator state and stripped before any method runs (the `labels_stripped_before_analysis` pattern from `independence_report.json`).
* Generation is performed once; the data hash is recorded in the preregistration addendum *before* any method is run on it.

### 4.3 Leakage checks **[SUPERSEDED: see Dataset Protocol §8]**
* Grouped checks using `src/rift/scenarios/independence.py` / `duplicates.py` against dev, val, the adversarial set and Phase A data: 0 shared keys on content, dynamics, topology, template and joint cell; 0 near-duplicates ≥ 0.90; 0 group-integrity violations; QC failures 0.
* **Held-out sealing [DECISION].** The old held-out file must not be opened. Independence from it should be verified by a *membership-only* check run through `HeldOutGuard`, which reports only counts of shared keys and never scenario content. If the existing guard cannot provide that without exposing content, the check is replaced by (i) exclusion by construction (new seed tag; no template overlap with the published template ID list) and (ii) this limitation stated in the report. The seal verification (`scripts/verify_heldout_sealed.py`) is run before and after.
* Any failure is an integrity stop (§2.7).

---

## 5. Frozen evaluation (Phase B)

### 5.1 Methods
* **V3-FULL** (frozen, E0 CID), the primary subject.
* **V3-CIDx**, only if Phase A qualified an estimator; pre-specified, frozen before generation, and added to the confirmatory family in place of nothing (it is tested as an additional hypothesis H1′ with the Holm family enlarged accordingly, N re-checked with the Holm worst case m = 4).
* **ALWAYS-ABSTAIN** (primary comparator), **RIFT-FULL-V2** (secondary), RIFT-FULL-LEGACY, and observational baselines (B0-EARLIEST, B0-HIGHEST, B1-LATENCY-CORR, B3-SIEVE-LIKE, B5-RIFT-OBS).
* B6/B7 (RIFT-RANDOM / ONE-SHOT) as interventional baselines.
* **Oracle rows are privileged upper bounds**, never compared inferentially, and labelled "ORACLE (privileged upper bound)" in every table.

### 5.2 Procedure
1. Verify §1.4 and §4.3. 2. Generate (once) and strip labels. 3. Run each method on each scenario with identical observed windows and seeds, one run. 4. Score with the frozen scorer. 5. Compute the preregistered analysis with a script whose hash was recorded in advance (`scripts/sprint450_analyze.py`, written *before* the data exist and tested only on dev/val). 6. Write the report.

### 5.3 Reporting (all with paired scenario-level statistics where a comparator exists)
Correct attribution (P1), unsafe attribution, coverage, abstention, unobserved-root handling, intervention count, intervention duration, modelled recovery overhead, decision latency, utility. The always-abstain row is in the main table and not an appendix. Every comparison reports the estimate, the uncorrected and Holm-corrected p-values, the CI, discordant counts, and the exact N.

---

## 6. Scientific decision

* **H1 is decided by one rule written in advance:** reject the null and report "V3 exceeded always-abstain on preregistered utility on these synthetic scenarios" only if the Holm-adjusted one-sided p < 0.05 **and** the lower bound of the 95% CI > 0. Otherwise the report states that V3 did not beat always-abstain.
* **The experiment may fail and that is an acceptable outcome.** A negative H1 is reported with the same prominence as a positive one, including the λ at which the result flips and the prevalence at which V3 would break even.
* No redesign of V3 against confirmatory results. Failure analyses are descriptive. Any new V3 variant motivated by them is named, hashed, and must be validated on fresh data in a later sprint.
* A positive result would still be restricted to the simulator: not external validity, no live-system claim, not evidence that DEFINITIVE-labelled answers are definitive.
* If Phase A finds that drift invalidates CID in the drift cells and no estimator is eligible, the sprint's main conclusion is that the intervention evidence is unreliable under temporal change in this model, which is itself the finding.

---

## 7. Work breakdown and gates

| step | work | gate to pass | artifacts |
|---|---|---|---|
| 0 | resolve §1.5 (dependency commit) and [DECISION] items | owner approval recorded | decisions log |
| 1 | re-verify freeze (§1.4) | all hashes match (the 51-file manifest and the 69-file extended manifest), tests at the 4.4.2 baseline pass (the earlier "880" figure is outdated; 886 reproducible + 2 protected), seal 4/4 | `prereg/freeze_verification.json` |
| 2 | build `cid_reliability` simulator wrapper; validate against frozen `intervene()` | E0 reproduces known size/power | tests, validation report |
| 3 | Phase A power analysis then run | §3.7 criteria evaluated | `SPRINT4_5_0_CID_RELIABILITY_REPORT.md` |
| 4 | fix N, write analysis script and test on dev/val only | N recomputed if needed, script hash recorded | script, tests |
| 5 | write and hash the preregistration | hash + timestamp recorded | `prereg/PREREGISTRATION.md` |
| 6 | generate confirmatory data once; leakage checks | all §4.3 checks pass | dataset, independence report |
| 7 | run all methods once; analyse | integrity checks pass | `artifacts/sprint4_5_0/results/` |
| 8 | final report and ledger row | claims reviewed against §6 | `SPRINT4_5_0_FINAL_REPORT.md` |

Hard constraints throughout: no live intervention; no edit to `src/rift/intervention/**`, `src/rift/safety/**`, the Stage 4 orchestrator, RIFT-FULL-V2, the Sprint 4.3.0 freeze list or any historical artifact; no change to V3 after step 5; dev/val may be used only to test code, never to tune anything evaluated confirmatorily; tests must pass before and after each step.

## 8. Risks

| risk | effect | mitigation |
|---|---|---|
| Dependencies of V3 are untracked and `ebd.py` / `fci_runner.py` carry uncommitted edits (§1.5) | the checkpoint is not reproducible from git alone | dependency commit approved first; hashes in §1.2 meanwhile |
| λ and κ are judgement calls and H1's outcome depends on them (§0) | a "win" or "loss" could be an artefact of the chosen costs | primary values fixed in advance; full grid reported; break-even λ reported |
| Utility favours always-abstain by charging no cost for missed attributions | the comparator is hard to beat | stated in §2.3; P1 and coverage reported so missed value is visible |
| Simulator-only evidence | no external validity | claims restricted per §6; a real-telemetry study is a separate future decision |
| Phase A depends on a new generator | a generator bug could manufacture or hide the drift effect | validation against frozen `intervene()` (step 2); independent test review |
| Held-out independence check could expose content | breaks the seal | membership-only check or exclusion by construction (§4.3) |
| N = 800 only just powers δ = 0.10 | a small true effect is likely to be missed | stated; result reported as inconclusive if CI spans 0 and includes δ |
| Template overlap with earlier splits | optimistic results | unseen-template quota, grouped bootstrap, grouped leakage checks |

## 9. Items needing the owner's decision before step 5 **[SUPERSEDED: see the decision register, audit §10]**
1. Approve a separate dependency-freeze commit (§1.5) and the handling of the two modified tracked files.
2. Confirm λ = 2, κ = 0.05, δ = 0.10 (or replace them *before* data generation).
3. Approve the new `cid_reliability` module (§3.5).
4. Choose the held-out independence handling (§4.3).
5. Confirm N = 800 (or ≥ 600 with the stated loss of power).

*Nothing in this plan has been executed. Sprint 4.5.0 implementation has not been started. Revision 2 changed documents only.*
