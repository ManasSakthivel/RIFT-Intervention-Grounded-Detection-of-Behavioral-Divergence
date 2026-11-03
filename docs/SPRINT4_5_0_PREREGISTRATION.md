# Sprint 4.5.0 — Preregistration of the Confirmatory Evaluation of Frozen RIFT-FULL-V3

**Status: PROPOSED (revision 3, Sprint 4.5.1). Not binding until the researcher approves the items in §14 and the document is hashed and recorded (§13) before any confirmatory scenario is generated.**
Prepared 2026-11-03 on branch `sprint-4.4.2-reproducibility-hardening`, commit `be5e0318fcd9cb17285ce6b8dff632cb68274b65`; finalised on branch `sprint-4.5.1-prereg-finalization`.

> **Sprint 4.5.1 status (read first).**
> * **This preregistration is NOT fully approved.** It cannot be recorded (§13) or used to generate data until the open BLOCKER items are resolved by the researcher: **D7** (no independent reviewer of the generator and analysis script has been named) and **D12** (the protected full-tree verification is incomplete: 27 of 888 tests were deliberately not run because they would parse sealed held-out content, and are not reported as passed).
> * **Review so far is internal only.** The Sprint 4.5.1 checks were done by seven internal agents working in parallel plus a lead. That is not external independent validation, and no document here claims it.
> * **Claim restriction (researcher decision, Sprint 4.5.1).** The 16 scenario structures S01–S16 are **fixed experimental strata**. Any conclusion is restricted to those 16 motifs as produced by the confirmatory generator. It does not generalise to unseen structures or to arbitrary production environments (§1.1, SAP §1).
> * Decision-register classification counts (single register: audit [`§10`](SPRINT4_5_0_FINAL_PREREGISTRATION_AUDIT.md); 35 rows = D1–D22, one row for A1–A9, X1–X12): BLOCKER: 2; MUST FIX: 1; REQUIRES RESEARCHER APPROVAL: 25; ACCEPTED LIMITATION: 2; INFORMATIONAL: 5. The classification of each item is held in the audit register only, so it cannot drift between documents; the checker verifies these counts.
> * Consistency of this document with its companions is machine-checked by `scripts/sprint451_doc_consistency_check.py` (paths, hashes, key numbers, wording); output in `artifacts/sprint4_5_1/consistency/`.
> * Evidence base is unchanged: every empirical number is from dev/val (N = 252), is non-confirmatory, and informed V3.
Companion documents: [`SPRINT4_5_0_STATISTICAL_ANALYSIS_PLAN.md`](SPRINT4_5_0_STATISTICAL_ANALYSIS_PLAN.md) (SAP), [`SPRINT4_5_0_CID_EXPERIMENT_DESIGN.md`](SPRINT4_5_0_CID_EXPERIMENT_DESIGN.md), [`SPRINT4_5_0_DATASET_PROTOCOL.md`](SPRINT4_5_0_DATASET_PROTOCOL.md), [`SPRINT4_5_0_FINAL_PREREGISTRATION_AUDIT.md`](SPRINT4_5_0_FINAL_PREREGISTRATION_AUDIT.md), [`SPRINT4_5_0_EXECUTION_PLAN.md`](SPRINT4_5_0_EXECUTION_PLAN.md).

Nothing in this work so far implements the experiment, generates confirmatory data, runs a method on new data, or modifies a frozen file. No analysis here opened, parsed or read the contents of the Sprint 4.3.0 held-out file. Two SHA-256 computations over its bytes did occur in Sprint 4.5.1 and are disclosed rather than omitted: (i) the existing approved integrity check, `verify_freeze()`, which runs inside the registered protected test `test_dev_val_pins_and_freeze_intact`; (ii) one **unintended** `shasum` of the file by an agent (the digest was not displayed or recorded; `artifacts/sprint4_5_1/repro/REPRO_FINDINGS.md` §0; decision X5). The SHA-256 string quoted below was copied from `datasets/rift_v2/independence_report.json`, not computed here.

**Language rule.** Results are described as "validated on synthetic ground-truth scenarios" and "intervention-consistent". The terms "causally accurate", "production-ready" and "guarantees" are not used. A CANDIDATE-grade CID check is never called definitive.

**Provenance of all numbers in this document.** Every empirical number quoted here comes from Sprint 4.3.0/4.4.0 dev and val data (N = 252). Those data informed V3's design, so the numbers are **non-confirmatory**. They are used only to calibrate sample size and to pre-state expectations. Source: `artifacts/sprint4_5_0/prereg_audit/audit.json`, `audit_part2.json` (scripts `scripts/sprint450_prereg_audit*.py`, seeds 450 and 4502).

---

## 1. Research question and hypotheses

**Primary question.** Does frozen RIFT-FULL-V3 provide useful and safe root-cause attribution beyond always-abstain, using intervention evidence robust to unrelated temporal changes?

### 1.1 Estimand and claim restriction (researcher decision, Sprint 4.5.1)
* The confirmatory estimand is the **fixed-strata** mean θ = Σ_s W_s μ_s over the 16 fixed structures S01–S16 with the preregistered quota weights W_s (SAP §1). It is not a mean over a population of structures.
* Three levels are distinguished: **structure** (one of 16 fixed strata), **scenario group** (an independently generated group within a structure; one group = one template, K = 256 groups, 16 per structure) and **scenario** (one observation). 256 groups are not 256 independent structural clusters, and no effective sample size is claimed beyond what the design-effect analysis supports.
* A conclusion applies to these 16 motifs as produced by the confirmatory generator on the simulator. It does not extend to unseen structures or to arbitrary production environments. A random-structures reading would have a minimum detectable effect of about 0.18–0.25 that does not shrink with N (SAP §6.1); that reading is **not** adopted.

The question has two parts, which the design treats differently:

* **"Useful and safe beyond always-abstain"** is tested confirmatorily by H1 (§5).
* **"Robust to unrelated temporal changes"** cannot be established by a single end-to-end utility. The frozen V3 uses the unchanged E0 CID. On dev/val, E0 reports a "significant" shift for 94% (dev) and 100% (val) of non-ancestral pairs whose outcome service has own-drift > 0.3σ, versus 5.6% and 6.7% for clean pairs. Those rates are for the V2 trace pair set, whose drift stratum has 17 pairs per split (from 10 dev and 6 val scenarios). V3's own, larger pair set gives 103/110 = 94% (dev, 18 scenarios) and 64/69 = 93% (val, 10 scenarios) against 5.6% and 3.9% for clean pairs (`artifacts/sprint4_4_0/cid_audit.json`; `docs/SPRINT4_4_0_CID_EVIDENCE_ANALYSIS.md` §3.3). Either way the dev/val drift stratum is small (28 scenarios in the V3 trace set) and entangled with oscillation and intermittent faults. The preregistration therefore (a) pre-specifies a temporal-confound stratum and reports V3 within it (SAP §8), and (b) answers the identification question separately and without touching V3 in the CID reliability experiment (Phase A).

| id | hypothesis (all about frozen V3 on the confirmatory dataset) | role | comparator |
|---|---|---|---|
| H1 | E[U_V3] > 0 (mean utility beats always-abstain, U_AA ≡ 0) | **primary, confirmatory** | ALWAYS-ABSTAIN |
| H2 | E[U_V3 − U_V2] > 0 | secondary, confirmatory only if H1 is rejected | RIFT-FULL-V2 |
| H3 | unsafe-answer rate of V3 < that of V2 (paired) | secondary, same gate | RIFT-FULL-V2 |
| H4 | P1 (correct root among ATTRIBUTE scenarios) of V3 > V2 (paired) | secondary, same gate | RIFT-FULL-V2 |
| H5 | V3 vs existing observational baselines (utility, paired) | exploratory, no inferential claim | B0-EARLIEST, B0-HIGHEST, B1-LATENCY-CORR, B3-SIEVE-LIKE, B5-RIFT-OBS, RIFT-RANDOM, RIFT-ONE-SHOT, RIFT-FULL-LEGACY |
| — | ORACLE rows | **privileged upper bound**, never compared inferentially, labelled "ORACLE (privileged upper bound)" in every table | — |

Null hypotheses are "no improvement". Failure to reject is a reportable result.

---

## 2. Freeze of V3

V3 is an immutable experimental candidate from this point on. The full machine-readable manifest is `artifacts/sprint4_5_0/prereg/freeze_manifest.json` (written by `scripts/sprint450_freeze_manifest.py`; manifest SHA-256 at the time of writing: `609bcb9d8a9786492f045e4fe13e10e1d17518f3111814a91e5ca73b6902aeb6`). It covers 51 files, and all 51 had the same SHA-256 in the working tree and in git HEAD (re-verified in Sprint 4.5.1: 51 files, 0 mismatches, `artifacts/sprint4_5_1/repro/manifest_verification.json`). The manifest hash is recorded in this document only. The manifest does not contain its own hash, and this document does not contain its own hash (the document hashes go into `prereg.sha256`, §13).

**Extended freeze manifest (researcher decision, Sprint 4.5.1; X10).** The closure analysis (`artifacts/sprint4_5_1/freeze/closure_analysis.json`) found 18 additional files that the comparators or the dataset-generation path import but the 51-file manifest did not list. They are recorded in a **separate** manifest, `artifacts/sprint4_5_1/freeze/extended_manifest.json` (69 files = the 51 original + 18 added; written by `scripts/sprint451_extended_manifest.py`), which assigns each file a role: `v3_frozen_implementation` 5, `v2_frozen_implementation` 1, `comparator_implementation_dependencies` 14, `shared_method_dependencies` 14, `dataset_generation_dependencies` 8, `evaluation_framework` 7, `evaluation_scripts` 6, `development_data` 7, `test_suite` 5, `environment_and_lock` 1, `protocol` 1. The 18 added files are 16 tracked files and two files (`src/rift/evaluation/dataset_registry.py`, `src/rift/benchmark/adversarial_generator.py`) that were untracked before Sprint 4.5.1 and are committed with it. The original 51-file manifest and its hash above are **unchanged**; the extended manifest's own hash is recorded in the Sprint 4.5.1 reports, not here. The freeze rule (§2.6) applies to all 69 files.

### 2.1 Identity
* Branch `sprint-4.4.2-reproducibility-hardening`, commit `be5e0318fcd9cb17285ce6b8dff632cb68274b65`.
* V3 configuration `V3-FULL`: `name=RIFT-FULL-V3`, `manipulation_check=True`, `earlier_guard=True`, `answer_statuses=(DEFINITIVE_ROOT, QUALIFIED_ROOT)`, `divergent_candidates=True`, `test_explained=True`.

### 2.2 Source files (SHA-256)
| file | SHA-256 |
|---|---|
| `src/rift/attribution_v3/rift_v3.py` | `03e84568702a6f9da8c5ea09cadf4ee794eb5553b8c1fc1cc89b1f662f6d0bf8` |
| `src/rift/attribution_v3/pag_semantics.py` | `f9ffd15dbbfb0ec5c6ea2f707a39d6705fe895294b010eaea65b4a9310a04282` |
| `src/rift/attribution_v3/diagnostics.py` | `bc89410af64a71b2bd4a44eed8a320c3ed4d097a4fe1277ae50b5afccabcff14` |
| `src/rift/attribution_v3/adversarial.py` | `b9fa6b5eb6476436e1890cc75a3a1078b676faf8da77cd12f461aa16f7cd8e55` |
| `src/rift/attribution_v3/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty file) |
| `src/rift/evaluation/rift_v2.py` | `9eeb80dad46d62bab35c5bc73fefaa9a1137c3b6d6f1dec7ba85a56734fb80bf` |
| `src/rift/evaluation/benchmark_v2.py` (scorer `score_one`) | `efc5fcf4a947e12f608aa173f5f4f7d0d7b03f0a04120213c6f503e09eafce92` |
| `src/rift/evaluation/stats_v2.py` | `762962f1664e9d79ebc4082279a6aa6833dcc7f46957588bc8a19da8d89e9d0e` |
| `src/rift/evaluation/dataset_registry_v2.py` | `db8319ef3851d4d6448f36a9832db3309fe999837289fb81d240da1da5782820` |
| `src/rift/evaluation/held_out_guard.py` | `6d964fce022f8d6cb1496f4bbb55ac325628c3710cf4050962b4976b354171a3` |
| `src/rift/ebd/ebd.py` | `43f0ad7cdda11fc4de4546b9c84263a64a2e34b76963ba8750ea56d574d7394b` |
| `src/rift/fci/fci_runner.py` | `39c300156dfc6011771e4d30d21a1e155e096c23da445b13dcb85d075a3411f6` |
| `src/rift/cid/cid.py` | `8282c6758614f6422ba835b2851746f3099887d8458a7049a57bd93a26027f32` |
| `src/rift/cid/evidence.py` | `d8b8edc8cbcdb32ae115eed27026fd4440fa74a262911c069786bd0fb199f82b` |
| `src/rift/identifiability/identifiability.py` | `8eff5f06eca2b20f7e06023bf278ed99b9de2130fe1909d2360af58be258d454` |
| baselines: `__init__` `8986097f…`, `latency_correlation` `fdde208f…`, `oracle` `0825b825…`, `rift_obs` `df5a5ce6…`, `rift_one_shot` `b8529a36…`, `rift_random` `4883025b…`, `sieve_like` `2e5e07d0…`, `sage_chaos` `5d3b8fe3…` | full hashes in the manifest |

### 2.3 Evaluation scripts and dataset-generation code
| file | SHA-256 |
|---|---|
| `scripts/sprint440_run_v3.py` | `629bee0e44f7f2d556326fb1b17a8b232180e39c32b1b69247f883e944c8237c` |
| `scripts/sprint440_analyze.py` | `0de11ae4456ef163e52c4604458c3cf8e3402aaca10f7de22b4ad942e387e740` |
| `scripts/sprint440_cid_audit.py` | `57159646799241653d564fb93f777a196a513c8e8341da2042409d40df2f65b8` |
| `scripts/sprint440_adversarial.py` | `d2c0a55482d2bf1b6ea4dbfe96e4771a1cbd7a81bbfd8c3aed07a9fd5394f3df` |
| `scripts/sprint440_trace_failures.py` | `dfca0c3c635fb9208301e62bcfcc06227731076f5dbdb2c7372a8a0d1c2eb6e7` |
| `scripts/sprint430_run_evaluation.py` | `519eb6e2369789f764c46daacd795f734d3d656d7975c0984df68d349459443d` |
| `src/rift/scenarios/simulator.py` (frozen, reused unchanged by the confirmatory generator) | `a93a0e4214abd1a81311ab64d83c7d7770981bdd634084748673a1264b3c1a8e` |
| `src/rift/scenarios/generator_v2.py` (frozen; supplies `compute_ground_truth`) | `5e68b223066ce1ce01326e2ccf6c88f7d0680220f0ae432779cd5ea5c6477d37` |
| `src/rift/scenarios/fingerprint.py` | `4f730ef75721c897ed01cd849e01f7c8df5dcef65bbebb6cd9fb4e70590e5778` |
| `src/rift/scenarios/independence.py` | `ac15a12a0d0f3c5cf945191f3c280485c0e5f746426bc7ace28a8808e922b0f7` |
| `src/rift/scenarios/duplicates.py` | `4e8b5d7da37058b0394198e36163b451b88fb891d35abb6b98c4af80cdea7caa` |
| `src/rift/scenarios/splitter.py` | `6f25ef902264bdf464866941576ab387a1bae4c725cbccfd20ba5b9a5cc67fa8` |
| `src/rift/scenarios/validators.py` | `a46910c41c9d3d2f7f2d2a981f862c820556fd1fc9b7e1de5caed81465493395` |
| `src/rift/scenarios/__init__.py` | `2f7e7c79db0608dfafe852ca4a7344d23599314e5a7852c9b8e86163bb834440` |

### 2.4 Datasets, lock file, tests
| item | value |
|---|---|
| `datasets/rift_v2/dev.json` | `a833ad0ca1db0583a30bc4450f9f59b2984a5823702935ef59c6b037e026ef5f` |
| `datasets/rift_v2/val.json` | `e82252b47f29dc1353586034b6fd8c3491df3221851f9c84c48bf717a944a1fb` |
| `datasets/rift_v2/manifest.json` | `e698dd51c116c7e937fad103f837a4fb1b9335fd9152031dd961ae455f501cef` |
| `datasets/rift_v2/independence_report.json` | `793389fb896cd70fce1ac55aa5f2cf0f935ee2793fb14fbfc6c2c537d05b7e19` |
| `datasets/rift_v3_dev/adversarial_dev.json` | `3525bc05ed8b9dd21dcc888181005af09e75f43396fb27a0ad6732588ea3c472` |
| `datasets/rift_v3_dev/provenance.json` | `d7e1d40dcbae4a360b15e3229408042b697c3875d922923c07a7d2d2aca4efff` |
| `artifacts/sprint4_3_0/freeze.json` | `f2b0997cfa700fa4378488d503f3b42022fee849dbf16359a6d418d4a772b806` |
| held-out SHA-256 (string only, **not recomputed**) | `97b90fa424c3a7c0654d2fd8cde417f094c58931a527c8ce5023bafe5e8e69ce` |
| dependency lock `reproducibility/requirements-canonical-py39.lock.txt` (65 lines) | `121304edcc036611eca354c23c6910882965bfa835822c78354c3f19a32e3fae` |
| `reproducibility/protected_materials.py` | `02df5a392cb04b760c2459b2298b118d535e399a75da1f6a4f47f83986110111` |
| `scripts/sprint442_run_tests.py` | `c5584044c9164438b9462de4d4127676966c7961a138b5355dee7307bc778e19` |
| `scripts/sprint442_compare_artifacts.py` | `f4c0d6f46c5a0666b748a68254c54801b349e18965b7042551d00d681d900cf2` |
| `scripts/sprint442_capture_environment.py` | `ce10b13cd1439039862152e7e458bd958adb721a598c32ed96c9715e7808a78c` |
| `tests/unit/test_sprint440_attribution_v3.py` | `4c52164b4ed1fe9bef00cecc450764cd64e23eb168fd4040a358edc60ace0a58` |
| `docs/EVALUATION_PROTOCOL_V2.md` | `745d3c7fb894395a4cebc17addd460d7b356258cd7bc438a5d4fd16de78bd8a5` |

### 2.5 Environment, constants, seeds, test suite
* **Python 3.9.6.** Canonical packages: numpy 2.0.2, scipy 1.13.1, scikit-learn 1.6.1, networkx 3.2.1, pandas 2.3.3, causal-learn 0.1.4.8, statsmodels 0.14.6, joblib 1.5.3, pytest 8.4.2, requests 2.32.5, momentchi2 0.1.8. The installed **direct scientific pins match the lock**; 14 transitive or utility pins differ (for example attrs, packaging, six, tzdata; `artifacts/sprint4_5_1/repro/lock_vs_installed.txt`). The installed environment therefore does not match the whole lock, and results are not claimed to be independent of those packages (not tested). `pyproject.toml` at HEAD declares `requires-python >=3.10`, which excludes the 3.9.6 canonical interpreter (D13). In Sprint 4.5.1 a one-line working-tree edit to `>=3.9` was made on the evidence in `artifacts/sprint4_5_1/repro/REPRO_FINDINGS.md` §5 (all 185 Python files parse under 3.9; the suite ran on 3.9.6 on one platform). It is not committed, it is not a frozen file, and it is not in the manifest. Nothing is claimed about other Python versions or platforms by this document.
* **Decision thresholds and constants (inherited, unchanged).** `DELTA_T=10 s`, `ED_PER_DO_S=30 s`, `MAX_DO=20`, `CID_PERMUTATIONS=1000`, `CID_BOOTSTRAP=100`, `ALPHA=0.05`, EBD `theta_detect=3.0` with `persist=2`, FCI `max_variables=15`, CID significance threshold θ_CID = 0.1 × IQR(baseline), CID grade CANDIDATE for n < 50 (RELIABLE needs n ≥ 50 and is unreachable with 30 s windows), Holm over outcomes inside V3 (`holm_reject`, α = 0.05), V3 answer rule = DEFINITIVE_ROOT or QUALIFIED_ROOT.
* **Seed rules.** do-seed = `(seed·7919 + crc32(x + "|v3")) & 0x7FFFFFFF`. CID seed = `(seed·1000003 + crc32("x->y")) & 0x7FFFFFFF`. Existing generator seed = `sha256(f"{GENERATOR_VERSION}|{split}|{idx}")[:8]` with `GENERATOR_VERSION = "rift-scenario-gen/2.0.0"`. Existing analysis seed 430 (B = 2000, 10,000 permutations). Audit seeds 450 and 4502. New confirmatory seeds are defined in the Dataset Protocol §4.
* **Test-suite version.** pytest 8.4.2. The Sprint 4.4.2 reproducibility harness (`scripts/sprint442_run_tests.py`) reported 888 passes on the full tree (886 reproducible + 2 protected-material). This audit re-ran it on a clean `git archive HEAD` export with no held-out file present and got 663 reproducible passes, 2 protected checks UNAVAILABLE (not passed) and 0 failures. The 4.4.2 report quotes 664 for the same configuration; the one-test difference is recorded in the audit and is not a failure. Sprint 4.5.1 re-ran the harness on the owner's tree with the protected files present, but **only the subset that cannot parse held-out content**: V3 tests 34/34; harness 861 of 888 executed and passed (801 + 48 + 10 reproducible, 2 protected passes), 0 failures. The other **27 tests were deliberately not run** because they `json.loads` a sealed held-out file (list: `artifacts/sprint4_5_1/repro/tests_not_run_held_out_content_risk.txt`) and are therefore **not reported as passed**. At freeze time the owner must decide whether to run the full harness with `--require-protected` and store the output as `artifacts/sprint4_5_0/prereg/freeze_verification.json` (D12). `scripts/verify_heldout_sealed.py` was run (4/4 PASS) but it concerns the legacy Sprint 4.2.4 set `datasets/rift_faults/held_out_test.json`, not the Sprint 4.3.0 `rift_v2` held-out file; the latter is covered only by `verify_freeze()`.
* **Tracking state.** The execution plan's §1.5 concern (untracked V3 dependencies) no longer applies to the 51-file manifest. Sprint 4.4.1 (commit `db77446`) tracked `rift_v2.py`, `benchmark_v2.py`, `stats_v2.py`, the scenarios package, `cid/evidence.py`, `datasets/rift_v2/{dev,val}` and the modified `ebd.py` / `fci_runner.py`. All 51 manifest files are tracked and identical to HEAD. The two files that were still untracked (`dataset_registry.py`, `adversarial_generator.py`) are covered by the extended manifest above.

### 2.6 Freeze rule
After preregistration (§13), none of the files in §2.2–§2.4 may change. Any change voids the confirmatory claim for V3 and requires a new, named system version, a new preregistration and fresh data. The verification procedure in SAP §12 is run before and after the confirmatory run.

---

## 3. Primary estimand and utility function (decision D2, with audit evidence)

The full audit is in [`SPRINT4_5_0_FINAL_PREREGISTRATION_AUDIT.md`](SPRINT4_5_0_FINAL_PREREGISTRATION_AUDIT.md) §3. The preregistered definition is below.

### 3.1 Definitions (per scenario i, per method)
* **Correct** C_i = 1 iff the method answers, the scenario's expected outcome is ATTRIBUTE, and the named top-1 service is a ground-truth observed root. This is `score_one(...)["correct"]`, unchanged.
* **Unsafe answer** S_i = 1 iff the method answers **and** (expected outcome is ABSTAIN_REQUIRED **or** the named top-1 service is not a ground-truth root). This is `score_one(...)["unsafe"]`, unchanged. In words: an answer is unsafe if the evidence in the scenario does not license any answer, or if the named service is wrong. A correct service named when the scenario's labelled evidence cannot identify it counts as unsafe ("right answer, unwarranted"); see §3.4.
* **Intervention cost** c_i = (ED_PER_DO_S × n_do,i) / T_budget, with T_budget = MAX_DO × ED_PER_DO_S = 600 s. So c_i = n_do,i / 20 ∈ [0, 1], where n_do is the recorded number of executed do() interventions. A cost of 1 means the whole per-incident intervention budget was consumed. The 600 s value is the default cumulative-exposure budget in `docs/intervention_cost_model.md` §K.2 and equals the code's `MAX_DO` × `ED_PER_DO_S`; it was fixed in the code before this analysis and is not fitted. Blast radius, SLA impact and rollback cost from that model are **not** represented in the simulator and are therefore not in U (limitation L4).
* **Utility** U_i = C_i − λ · S_i − γ · c_i, with **λ = 2.0** and **γ = 1.0** (equivalent to the previously proposed κ = 0.05 per do()).
* ALWAYS-ABSTAIN has C = S = c = 0, so U_AA ≡ 0 exactly.

### 3.2 Interpretation of the scale
* Unit: "correct-attribution equivalents per scenario". A value of +0.10 means that, per 1000 incidents, the system yields a net 100 correct attributions after subtracting two correct attributions per unsafe answer and one per fully consumed intervention budget.
* Ceiling: with prevalence π of ATTRIBUTE scenarios the maximum achievable mean U is π (perfect, zero-cost attribution, which no method that uses interventions reaches). Dev/val π = 0.393 (99/252). The confirmatory design fixes π = 0.40 by stratified quota (Dataset Protocol §5), so the ceiling is 0.40 by design and not a random variable.
* **Bounds.** For every scenario U_i ∈ [−(λ+γ), 1] = [−3, 1] at the primary values: a correct answer gives U ∈ [1−γ, 1] = [0, 1]; an unsafe answer gives U ∈ [−λ−γ, −λ] = [−3, −2]; an abstention after k do() gives U = −γk/20 ∈ [−1, 0]; C_i · S_i = 0 always. U is **not** confined to [0, 1]. It is discrete (a 0.05 lattice at integer λ), bounded and negatively skewed (−1.09 on dev/val). Source: `artifacts/sprint4_5_1/utility/utility_verification.json`.
* λ = 2 implies an answer is worth giving only if its chance of being correct is at least λ/(1+λ) = 2/3 (before intervention cost). Reference points: λ = 1 → 0.50, λ = 3 → 0.75, λ = 5 → 0.83.
* The scale is reported next to a normalised form U/π (net value per attributable scenario; ceiling 1.0).

### 3.3 Justification of λ, γ and δ, and what is *not* claimed
* **λ = 2.** An automated attribution may trigger remediation. A wrong or unwarranted answer wastes responder time and risks acting on the wrong service. Requiring at least 2/3 precision at zero intervention cost (about 0.79 once V3's dev/val answer rate and mean cost term are included, and about 0.88 for U = δ; V2: 0.72 and 0.80) is a conservative-but-not-extreme operating point in a system whose stated design principle is to abstain when evidence is insufficient. It is a **judgement**, not a derived constant. The previously proposed λ = 2 appears in the execution plan next to the dev/val break-even analysis, and the proposer had seen dev/val results; it is therefore **not demonstrably independent of dev/val**, and this document does not claim that it is. It is retained because moving it would require either an application-level argument (none available that favours another single value) or a data-driven choice, which is exactly what must be avoided. The full λ grid is a pre-specified sensitivity analysis (SAP §9), and the break-even λ is a reported outcome.
* **γ = 1.0 (κ = 0.05 per do()).** Anchored to the 600 s default exposure budget. It is also a judgement. With V3's dev/val mean of 2.71 do() per scenario, the cost term averages 0.135 (2.71/20), i.e. smaller than the unsafe term (λ · 48/252 = 0.381). Intervention cost alone does not decide the result at the primary value; it does decide it at κ = 0.10 (see §3.5).
* **δ = 0.10 (minimum practically useful effect).** Equals 25% of the ceiling π = 0.40 (the ceiling is not reachable by a method that uses interventions, so the share of what is attainable is larger). It is large. The same value would require, with perfect precision and zero cost, answering 25% of all attributable incidents. It is used for two things only: the design alternative that sample size is powered against, and the "useful" label in §10. It is a judgement (D2). Because a statistically significant improvement can be smaller than δ, the interpretation table (§10) separates "superior" from "useful".
* Missed attributions score 0, so ALWAYS-ABSTAIN is never charged for them. This is conservative for the claim (it makes the comparator harder to beat) and is stated openly. Coverage, P1 and the normalised U/π are reported so the foregone value stays visible.

### 3.4 Why the strict unsafe definition is primary
Of V3's 38 answers on ABSTAIN_REQUIRED scenarios in dev/val, 18 named a service that is in fact a true observed root (V2: 25 of 52; 9 of V2's 25 are SYMMETRIC_MUTUAL_DEPENDENCY cases, where the label says the root is not identifiable and naming one of the pair is a coin flip, which is the clearest case for the strict definition). Counting these as unsafe is debatable. The strict definition is primary because the scenario label ABSTAIN_REQUIRED means the evidence available to the method cannot identify the root; a method that cannot tell that cannot be trusted to be right next time. The **operational** definition (unsafe only if the named service is not a true root; abstain-required scenarios with a lucky correct name are not penalised) is pre-specified as a sensitivity analysis and as a robustness condition on a positive conclusion (§10). Under the operational definition V3's dev/val mean utility at κ = 0.05 is still negative: −0.076 (λ = 1), −0.195 (λ = 2), −0.433 (λ = 4).

### 3.5 Expected outcome stated in advance
On dev/val (non-confirmatory):
* V3 mean U = **−0.338**, 95% template-cluster percentile bootstrap CI [−0.465, −0.219] (B = 4000, seed 450). V2 mean U = −0.562. V3 − V2 = +0.224, CI [+0.085, +0.365]. An independent recomputation (seed 4510, B = 10,000) gives [−0.461, −0.217], within the 0.01 tolerance of SAP §12.
* As a point estimate V3 beats ALWAYS-ABSTAIN only when λ is below the break-even λ\* (0.94 at κ = 0; 0.58 at κ = 0.025; 0.23 at κ = 0.05; none at κ = 0.10). Break-even λ for V3-FULL by κ, with 95% template-cluster CI: κ = 0: 0.938 [0.61, 1.42]; κ = 0.025: 0.582 [0.31, 0.97]; κ = 0.05: 0.227 [0.00, 0.54]; κ = 0.10: negative. With a 95% cluster CI, V3 − AA is entirely above zero only for λ ≤ 0.61 at κ = 0 and λ ≤ 0.30 at κ = 0.025, and for no λ ≥ 0 at κ ≥ 0.05.
* In the λ × κ grid, V3 − AA is significantly positive (CI above zero) only at λ = 0.25 (κ ≤ 0.025) and λ = 0.5 with κ = 0 (full grid in the Final Preregistration Audit §3.4; identical under union-find-group CIs and under the operational definition).
* A bootstrap of dev/val gives P(mean U > 0 at λ = 2, κ = 0.05) = 0.000 in 4000 draws.

**Consequence: if the confirmatory data resemble dev/val, V3 is expected to fail H1.** The design is built so that this is reported as a result. The protocol deliberately does not tune λ, κ or δ in either direction.

### 3.6 Immutability of the primary utility definition
The following are frozen by this preregistration and cannot be altered, supplemented or re-selected once any confirmatory outcome (V3, V2, a baseline or always-abstain) has been computed on the confirmatory dataset:
1. the formula U_i = C_i − λ·S_i − γ·(n_do,i / 20);
2. λ = 2.0, γ = 1.0 (≡ κ = 0.05 per do()), δ = 0.10;
3. C_i and S_i exactly as returned by `benchmark_v2.score_one(...)["correct"]` and `["unsafe"]` (strict unsafe), computed from `src/rift/evaluation/benchmark_v2.py` with SHA-256 `efc5fcf4a947e12f608aa173f5f4f7d0d7b03f0a04120213c6f503e09eafce92`;
4. n_do,i as the integer `n_do` recorded by the method; the normalisation constant 20 = `MAX_DO`; U_AA ≡ 0;
5. the comparator set and the unit of analysis (scenario, clustered by union-find group).

The operational-unsafe definition, the (λ, κ) grid, break-even λ\*, U/π, coverage, P1 and the unsafe rate are **secondary**. They are always computed and reported, are labelled "sensitivity (not confirmatory)", and cannot change the primary label except where §10 makes the operational result a condition of POSITIVE-USEFUL. Any other λ or γ may appear only as a labelled secondary sensitivity; the report may not describe the grid by its most favourable cell, and any statement that V3 is "useful", "safe" or "not useful" must be followed by "at the preregistered exchange rates λ = 2, γ = 1 (minimum precision 2/3 at zero cost), δ = 0.10". A different utility requires a new preregistration, new data and is reported as a different study. Before any confirmatory result is computed the analysis script checks U_AA ≡ 0, C·S = 0 and U ∈ [−(λ+γ), 1] on every scenario; a violation aborts the analysis and is reported (the scenario is not dropped).

---

## 4. Sample size (decision D4)

Full derivation in SAP §6 and the audit §4.

| item | value |
|---|---|
| statistical unit | scenario, analysed in **generator-assigned groups** (one group = one template; Dataset Protocol §2) within **16 fixed structural strata** (estimand: SAP §1) |
| **target N** | **2000 scenarios** in K = 256 groups (16 per structure, 5–9 scenarios per group, maximum 9; gate K ≥ 250). The earlier planning layout of 250 groups with maximum size 25 is superseded |
| fixed quota | 800 ATTRIBUTE (π = 0.40), 1200 ABSTAIN_REQUIRED |
| N = 800 | **insufficient** (see below) |

N = 800 gives, for H1 with δ = 0.10, one-sided α = 0.025 and V3 utility SD 0.969 (dev/val): power 0.83 at design effect (DEFF) 1.0, **0.66 at DEFF 1.5 and 0.54 at DEFF 2.0**. With a plausible SD of 1.17 and DEFF 2, power is 0.4. Dev/val clustering (union-find groups, K = 21) gave an empirical DEFF of 1.37, with a template-level ICC of 0.027 whose 95% CI is [−0.14, 0.19] (K = 105), so DEFF 2.0 is a planning assumption set between the union-find-group estimate (1.37) and the structure-level estimate (2.21), not an estimate for the new design; DEFF 3.0 is the stress value (power 0.76 at N = 2000), and a few dominant structures could push the realised DEFF higher (SAP §6).

N = 2000, DEFF 2.0, SD 0.969, δ = 0.10 (closed-form normal approximation, optimistic; corrected below): power **0.90** (DEFF 1.5: 0.96; DEFF 3.0: 0.76; with SD 1.17 and DEFF 2.0: 0.77). Minimum detectable effect at 80% power, DEFF 2.0: 0.086; at DEFF 3.0: 0.105. Secondary hypotheses under the H1 gate, Holm m = 3 (α = 0.00833 one-sided each), DEFF 2: H2 power 1.00 if the dev/val effect (+0.224) is real, 0.79 at half that, 0.67 at +0.10. H3 power ≈ 1.00 at the full dev/val discordance and 0.95 at half (DEFF 2, McNemar normal approximation on effective discordant pairs). H4 (800 ATTRIBUTE scenarios; dev/val discordance 19 vs 10) has power 0.85 at the full effect and **0.23 at half**: H4 is likely underpowered if the V3–V2 P1 advantage shrinks, which is stated in advance.

**Corrected power evidence (Sprint 4.5.1; SAP §6.7).** The closed-form figures above (0.90, 0.76, …) are a **normal approximation and are optimistic**. They assume the dev/val SD and a pooled design effect. A Monte-Carlo check with the studentised bootstrap-t that SAP §3 prescribes gives, for a pooled layout of 250 groups of mean size 8: power 0.917 at DEFF 1.5, **0.83 at DEFF 2.0**, 0.65 at DEFF 3.0 and 0.37 at DEFF 6. Under the adopted fixed-strata layout (16 structures × 16 groups) power for μ = +0.10 is about 0.83–0.99 when within-group dependence is moderate (template ICC ≤ 0.10) and there is no crossed fault-family effect, about 0.65–0.83 at ICC 0.2–0.3, and **0.30–0.59 if the family-block bootstrap (D19) governs under a real crossed family effect**; ignoring a real family effect makes the template-level test anti-conservative (size 0.05–0.20). **Power is not adequate at higher design effects.** The 16-structure limitation is a property of the design and cannot be removed by increasing N. No effective sample size is claimed. Because the expected V3 effect is negative (dev/val −0.338), the likely outcome is a decisive negative result; the powers describe the unlikely positive case.

The power calculation does not use telemetry windows. It uses scenarios, clustered into groups, within fixed strata.

---

## 5. Multiplicity and decision structure

Confirmatory structure: **fixed-sequence gatekeeping**.
1. H1 is tested alone at one-sided α = 0.025 (equivalently, the lower bound of a two-sided 95% CI must exceed 0).
2. Only if H1 is rejected, {H2, H3, H4} are tested as a Holm family at a total one-sided α = 0.025 (thresholds 0.00833, 0.0125, 0.025 in step-down order).
3. If H1 is not rejected, H2–H4 are still computed and shown with unadjusted CIs and Holm-adjusted p-values, but labelled **"descriptive, not confirmatory"**. Statements about V3 relative to V2 are then comparisons of two systems that both fail to beat always-abstain; they do not establish usefulness.
4. H5, subgroup analyses and the sensitivity grid carry no inferential claim.

The previous plan's use of α = 0.025 as the family-wise level and a one-sided Holm-adjusted p < 0.05 in §6 were inconsistent; both are replaced by this structure. V3-CIDx is **not** in the confirmatory family (§8).

---

## 6. Comparators
* **Primary:** ALWAYS-ABSTAIN (U ≡ 0). In the main table, not an appendix.
* **Secondary:** RIFT-FULL-V2 (frozen, in `src/rift/evaluation/rift_v2.py`).
* **Other:** RIFT-FULL-LEGACY, B0-EARLIEST, B0-HIGHEST, B1-LATENCY-CORR, B3-SIEVE-LIKE, B5-RIFT-OBS, RIFT-RANDOM, RIFT-ONE-SHOT.
* **ORACLE:** privileged upper bound, labelled as such in every table and never given a p-value.

On dev/val, an at-a-glance pooled comparison at λ = 2, κ = 0.05 (non-confirmatory): V3-FULL answered 93/252 with 45 correct and 48 unsafe; V2 answered 115 with 36 correct and 79 unsafe; B0-EARLIEST answered 237 with 49 correct and 188 unsafe. Of these four, none has a break-even λ (κ = 0) above 1 on that data (0.94, 0.46, 0.35, 0.26), so none beats always-abstain at λ = 2.

---

## 7. Procedure (one pass, no iteration)

| step | action | gate |
|---|---|---|
| G0 | researcher approves §14 decisions; approval recorded in `artifacts/sprint4_5_0/prereg/decisions.json` | all D-items answered |
| G1 | freeze verification (SAP §12): re-hash, tests, seal, environment | all match |
| G2 | write and test `scripts/sprint450_analyze.py` and the new generator on **dev/val and synthetic pilot skeletons only**; record their hashes | hashes recorded |
| G3 | hash this document and its companions; record timestamp (§13) | ledger row exists |
| A | Phase A, the CID reliability experiment (CID design document); independent of Phase B; may run before or after; **cannot alter V3 or Phase B** | n/a |
| G4 | generate the confirmatory dataset once; run the independence checks; hash the dataset; strip labels | Dataset Protocol §8 passes |
| G5 | run all methods once on identical observed windows and seeds | no integrity stop |
| G6 | run the preregistered analysis script; write the report using only the interpretation table in §10 | n/a |

Each method is run once on the confirmatory data. Re-runs are allowed only for infrastructure failure (process crash, disk), with the reason logged; the first complete run is the reported one.

---

## 8. Relationship to the CID reliability experiment (Phase A)
Phase A (CID design document) characterises when CID-style intervention checks are valid under temporal change, using synthetic data generated by a **new** module and a **separate** seed namespace. Its outputs are an estimator-by-condition validity map. Phase A:
* never changes V3, its CID call, or its thresholds;
* is not a precondition of the V3 confirmatory run;
* if an estimator qualifies, it defines a **new system (V3-CIDx), which needs its own preregistration and fresh confirmatory data in a later sprint** (D9). This differs from the earlier plan, which put V3-CIDx in the same Holm family on the same data. That earlier approach would let the confirmatory dataset test a system selected with knowledge of the same design, and would have enlarged the family.

---

## 9. Missing data and failures
No imputation; no exclusion of scenarios. **Error semantics (corrected in Sprint 4.5.1).** The mapping of exceptions and timeouts to abstentions is *not* a behaviour of frozen V3 or of `scripts/sprint440_run_v3.py`; it lives in the frozen harness function `benchmark_v2._timed` (`METHOD_ERROR`, `TIMEOUT_S = 60`). A confirmatory runner, `scripts/sprint450_run_confirm.py`, must be written before generation, tested only on dev/val and pilot data, and **hashed at G2**; it reproduces those semantics: an exception or a call over 60 s is recorded as an abstention with `error_flag = 1`, and the n_do consumed up to the failure is charged as intervention cost (D21). Error rows are tabulated per method and structure. Harness-level failures (not the method) are re-run once and logged. If fewer than 95% of scenarios produce a complete record for a method after re-runs, that method's run is an integrity stop (§11) and the completed fraction is reported; H1 depends on V3's completeness only. Sensitivity: missing scored as unsafe, missing scored as safe abstention, and complete-case (SAP §7).

---

## 10. Preregistered interpretation

Let θ̂ = mean utility of V3 (U_V3), with the studentised group-clustered two-sided 95% CI [lo, hi] defined in SAP §3 (decision rules in SAP §5). "H1 rejected" means lo > 0 (equivalent to the preregistered one-sided test at α = 0.025). θ̂ ≥ δ is a statement about the **point estimate**; lo may be well below δ. "Operational lo" is the lower bound of the same CI computed with the operational-unsafe utility (SAP §9 item 3).

| outcome | condition | wording that must be used |
|---|---|---|
| **POSITIVE-USEFUL** | lo > 0, θ̂ ≥ δ = 0.10, **and** the operational-unsafe sensitivity (SAP §9) also has lo > 0 | "On these synthetic ground-truth scenarios, frozen V3 exceeded always-abstain on the preregistered utility, and the point estimate of the margin was at least the preregistered minimum useful effect (the CI lower bound may be smaller)." Not external validity. |
| **POSITIVE-SUBSTANDARD** | lo > 0, but θ̂ < δ = 0.10, or operational lo ≤ 0 (which is practically unreachable: S^op ≤ S by definition, so the operational utility is never below the strict utility for any scenario, and the clause is kept as a guard against bootstrap-t differences) | "V3 exceeded always-abstain on the preregistered utility, but the point estimate was below the preregistered minimum useful effect (or the operational-unsafe check was not positive)." |
| **NEGATIVE-WORSE** | hi < 0 | "V3 was worse than always-abstain on the preregistered utility." |
| **NEGATIVE-NO-USEFUL-EFFECT** | lo ≤ 0 ≤ hi and hi < δ | "No useful improvement over always-abstain; an effect of at least 0.10 is excluded, but a benefit of zero (or a small harm) is not." |
| **INCONCLUSIVE** | lo ≤ 0 and hi ≥ δ | "The data are compatible with both no benefit and a useful benefit." |

The rows are exhaustive and mutually exclusive (verified by enumeration in `scripts/sprint451_doc_consistency_check.py`): hi < 0 → NEGATIVE-WORSE; lo > 0 → POSITIVE-USEFUL or POSITIVE-SUBSTANDARD, split by θ̂ ≥ δ together with operational lo > 0; otherwise lo ≤ 0 ≤ hi, split by whether hi < δ into NEGATIVE-NO-USEFUL-EFFECT or INCONCLUSIVE. A CI that straddles 0 but has θ̂ ≥ δ is INCONCLUSIVE, never positive. Because hi < 0 and lo > 0 each use one 2.5% tail of the 95% CI, they are consistent with the one-sided α = 0.025 test.

Rules that apply to every outcome:
* The result is stated with the same prominence if it is negative.
* The λ and κ at which the sign flips (break-even) and the prevalence at which V3 would break even are reported.
* Positive results never use "causally accurate", "production-ready" or "guarantees", and do not describe QUALIFIED or CANDIDATE-grade answers as definitive. The status label `DEFINITIVE_ROOT` is an internal V3 label that rests on CANDIDATE-grade CID; reports call such answers "intervention-consistent", never "definitive".
* "Safe" means only that the preregistered unsafe indicator S_i = 0. It says nothing about any deployment. "Robust to unrelated temporal changes" is not inferred from scenario-level unsafe rates (SAP §8.2); the pair-level endpoint of D22 addresses it descriptively.
* The confirmatory set is a **designed stress set** (quota-balanced, 40% ATTRIBUTE), not a sample of operational incidents. A novel-versus-variant table (Dataset Protocol §3) is reported, because structures S10–S14 are variants of dev/val motifs, not unseen types.
* The ATTRIBUTE/ABSTAIN_REQUIRED labels, the label function and the thresholds are not changed under any circumstance.
* A positive result applies to synthetic scenarios generated by the confirmatory generator only.

---

## 11. Decision criteria, stopping and prohibited actions
* **Fixed sample.** No interim analysis; no early stopping for efficacy or futility; no sample-size re-estimation after generation.
* **Integrity stops** (the run halts and is reported, not patched): any frozen-hash mismatch; any independence-check failure (Dataset Protocol §8); any ground-truth field reaching a method; held-out seal check failure; < 95% completion (§9).
* **Prohibited after any confirmatory result is seen:** changing λ, γ, δ, N, α, the primary analysis method, any threshold or label; removing, filtering or re-labelling scenarios; reclassifying failed outcomes; redesigning V3 (or any comparator) against the new dataset; re-running to obtain a different result; replacing the primary test because another gives a smaller p-value.
* **Failure analyses** are descriptive. Any V3 variant motivated by them is named, hashed, and validated on fresh data in a later sprint.
* **Allowed deviations** are limited to those listed as amendments (§13), which are appended after a hash line and timestamp and never edit this text.

---

## 12. Limitations (stated before the data exist)
* **L1. Simulator-only evidence.** No live-system, no real-telemetry claim.
* **L2. Label provenance and circularity.** Ground truth is computed by the frozen noise-free label function; "ABSTAIN_REQUIRED" means the simulator state does not license an answer under that function's rules (`compute_ground_truth`: SNR ≥ 4 and an INTERVENTIONAL or TEMPORAL evidence criterion). That function mirrors RIFT's own detection rule (3σ, persistence 2) and the CID power criterion, so the label and the method are not independent. For SNR ∈ [3, 4) no scenario is labelled ATTRIBUTE while V3 answers 37% of them (dev/val mean U −0.87); WEAK_SIGNAL scenarios contribute −0.166 of V3's −0.338. The SNR [3, 5) band is reported as a stratum (D20; default: report, not exclude). The conclusion is relative to this labelling.
* **L3. Structures not present in the dev/val/held-out generators.** The confirmatory set uses motifs that do not appear in the dev/val/held-out generators (Dataset Protocol §3), but several (S10–S14) are variants of motifs V3 was developed against; "V3 was not tuned on them" is not claimed. Results are not directly comparable with dev/val.
* **L8. Fixed motifs and families.** The 16 structures and 16 fault families are fixed experimental strata. Conclusions are restricted to them (§1.1). Crossed family dependence cannot be removed by increasing N (§4).
* **L9. Single platform.** All reproducibility evidence is from one macOS arm64 machine with CPython 3.9.6; no cross-platform claim is made.
* **L4. Cost model.** Intervention cost is a count of 30 s do() windows. Blast radius, SLA impact and rollback are not simulated.
* **L5. Clustering.** DEFF is planned, not known. Groups are chosen so that they are small (Dataset Protocol §6).
* **L6. Held-out already spent.** The Sprint 4.3.0 held-out file was opened once (`heldout_opened.json`, 2026-11-03T04:06:00Z) for the Sprint 4.3.0 evaluation and is not used here.
* **L7. CANDIDATE-grade CID.** The 30 s windows cannot yield RELIABLE-grade CID. V3's interventional answers are intervention-consistent and are not definitive.

---

## 13. Recording this preregistration
Before generating any confirmatory scenario:
1. Researcher approves §14. Copy this document and the four companions to `artifacts/sprint4_5_0/prereg/` with final values.
2. Compute the SHA-256 of each; write `artifacts/sprint4_5_0/prereg/prereg.sha256`, including the freeze manifest hash, git commit, analysis-script and generator-module hashes, and an RFC 3339 UTC timestamp.
3. Append a ledger row and, if the owner agrees (D14), create a signed git tag (suggested `prereg-4.5.0`) on the commit that contains these files. No commit or push is made without owner approval.
4. Amendments follow the pattern of `docs/EVALUATION_PROTOCOL_V2.md` §16: appended after a hash line and timestamp, never edited in place. An amendment made after the confirmatory data are generated must say so and cannot change §3, §5, §10 or §11.

---

## 14. Decisions requiring researcher approval

| id | decision | recommended | alternatives / consequence |
|---|---|---|---|
| D1 | Freeze commit: approve `be5e031…` plus a commit of the new documents and scripts as the preregistration base; approve a git tag | yes | nothing is committed without approval |
| D2 | Utility parameters: λ = 2.0, γ = 1.0 (κ = 0.05), δ = 0.10, strict unsafe as primary and operational as robustness | as stated | any change must be made now; λ = 1 or κ = 0 would favour V3 and need a stated application reason, not a data reason |
| D3 | Prevalence quota: 40% ATTRIBUTE, 60% ABSTAIN_REQUIRED, with abstain-reason quotas as in the Dataset Protocol §5 | as stated | other mixes change the ceiling and break-even |
| D4 | N = 2000 in K = 256 groups (16 structures × 16 templates; gate K ≥ 250, replaces the earlier 250-group planning layout), fixed-strata estimand | 2000 | 1600 (closed-form power 0.83 at DEFF 2); 3000 (0.98); the Monte-Carlo power (SAP §6.7) is lower than the closed form and is inadequate at higher DEFF; compute is cheap, generation QC is the limit |
| D5 | Gatekeeping structure and one-sided α = 0.025 | as stated | a single Holm over {H1…H4} (m = 4) cuts H1 power to ≈ 0.78 at N = 2000, DEFF 2 |
| D6 | Generator route: new module with new structures and new families (Route A), not reuse of the frozen generator | Route A | Route B (reuse the frozen generator with a patched split label) fails template-disjointness (Dataset Protocol §2) |
| D7 | Independent code review of the new generator and of the analysis script before G3 (who, and under what checklist). **BLOCKER**: no external reviewer is named; Sprint 4.5.1 review was internal only | yes | an un-reviewed generator is a risk (R4) |
| D8 | Held-out independence handled by exclusion by construction, with **no** read of the held-out file | yes | a custodian-run hash-only comparison reads the sealed file and is not recommended |
| D9 | Phase A may not alter V3; any qualified estimator defines a future V3-CIDx with its own preregistration and fresh data | yes | including V3-CIDx in this family enlarges Holm and compromises independence |
| D10 | Approve the new `src/rift/cid_reliability/` module for Phase A, and the switchback arm E6 | yes | |
| D11 | Missing data and failure handling (§9) | yes | |
| D12 | Owner decides on and, if approved, runs `scripts/sprint442_run_tests.py --require-protected` on the full tree before G3 and stores the output. **BLOCKER**: 27 tests that would parse sealed held-out content were deliberately not run in Sprint 4.5.1 and are not reported as passed. `verify_heldout_sealed.py` (run, 4/4) covers the legacy set only | required | cannot be done in a clean checkout; protected checks are UNAVAILABLE there |
| D13 | `pyproject.toml` said `requires-python >=3.10`; canonical environment is Python 3.9.6. Sprint 4.5.1 **committed** `>=3.9` (one platform; invalid build-backend and non-PEP 440 version unchanged; CI targets 3.11) | ratify or revert | affects installability only; not part of V3 |
| D14 | External timestamp anchoring (signed tag, or a third-party timestamp) | signed tag | |
| D15 | Number of permitted generation attempts if design-QC fails before any method run (Dataset Protocol §9.2): max 3, all logged | 3 | |
| D16 | Language rules in §10 accepted as binding | yes | |
| D17 | Execution smoke test of the V3 runner on ≤ 20 pilot-tag scenarios, output discarded (Dataset Protocol §9.1) | **recommend drop** (forking-path risk; the runner can be tested on dev/val) | skipping carries no scientific cost |
| D18 | Structure set S01–S16 and the 0.88 similarity proxy threshold (Dataset Protocol §3, §8.3) | as stated | changes must precede hashing |
| D19 | Cluster unit and dependence rule: stratified group bootstrap (template level) is primary; family-block bootstrap (seed 4506) is a preregistered sensitivity; the divergence between them is reported (SAP §3.1). Power is 0.30–0.59 under the family-block rule if a crossed family effect exists | as stated | alternatives: family-block primary (low power) or template-level only (possibly anti-conservative) |
| D20 | SNR [3, 5) band: report as a stratum, do not exclude (SAP §8.3, Dataset Protocol §5.5) | report | excluding it is a researcher decision and must precede generation |
| D21 | Confirmatory runner and error semantics (§9): exception or timeout ⇒ abstention with `error_flag = 1`, n_do consumed charged, timeout 60 s; runner hashed at G2 | as stated | |
| D22 | Pair-level robustness endpoint: false-confirmation rate of non-ancestral pairs by drift stratum (SAP §8.2); secondary, descriptive | as stated | |
| A1–A9 | CID Phase A decisions (CID design §9) | as stated there | |
| X1–X12 | Sprint 4.5.1 additions: cross-document fixes (resolved), registry dependency (resolved), disclosed unintended hash, lock and packaging findings, label-robustness clause, accepted limitations, extended freeze manifest (X10), S13/S14 quota exception (X11), revised CID eligibility cut-offs (X12) (audit §10) | see audit §10 | |
