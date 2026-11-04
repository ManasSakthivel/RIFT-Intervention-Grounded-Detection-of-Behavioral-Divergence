# RIFT — Final Pre-Publication Status

**Author:** an AI engineering agent. This is a status report, not an independent review and not an approval. No human approval exists for any item in it.
**Branch:** `sprint-4.5.1-prereg-finalization`. **Base HEAD when this phase began:** `1efc229783a4adece3c4041efb6ae8a9aa29b326` (verified with `git rev-parse HEAD`; it equals the SHA named in the task). The closing commit SHA is reported in the session message, not in this file (a commit cannot contain its own hash). **Not pushed.**
**Not claimed anywhere in this phase:** that CI is green on GitHub, that independent review has occurred, that any decision is approved, that RIFT or V3 beats always-abstain, or any real-system effectiveness.

---

## 1. Publication decision

# DECISION 2 — READY AFTER ONE FINAL CONFIRMATORY EXPERIMENT

This is my assessment as an AI agent. It is not Bob's verdict and not a human reviewer's. Bob and the human reviewer may overturn it.

**Why not Decision 1 (ready now).** V3 has never been evaluated on data independent of its own development.

| fact | evidence |
|---|---|
| V3 was designed after inspecting dev failures and val was also inspected | `docs/SPRINT4_4_0_FINAL_REPORT.md` §3 ("Dev and val are both development data, so there is no confirmatory test"), §8 |
| The only spent held-out run evaluated V2, not V3 | `docs/SPRINT4_3_0_FINAL_REPORT.md` §7 (held-out n = 108, V2 P2 60/108 vs always-abstain 63/108) |
| Zero confirmatory results exist | `artifacts/sprint4_5_0/confirm/` does not exist; `scripts/sprint450_run_confirm.py`, `scripts/sprint450_analyze.py`, the new generator and `src/rift/cid_reliability/` do not exist (checked on disk) |
| The preregistration is not recorded | `artifacts/sprint4_5_0/prereg/` holds only `freeze_manifest.json`; no `prereg.sha256`, no `decisions.json` |

**Why not Decision 3 (not ready).** No fundamental flaw prevents defensible publication. The methodology is coherent and conservative: fixed-strata estimand, bootstrap-t with a family-block sensitivity, always-abstain as primary baseline, a preregistered interpretation function that permits NEGATIVE-WORSE, and the primary label unchanged. The label circularity is partial and disclosed (§4), not method-output leakage. A negative result is defensible under either clustering (dev/val V3 − always-abstain −0.338, CIs [−0.472, −0.222] template-level studentised and [−0.514, −0.203] over 21 union-find groups, `artifacts/sprint4_5_1/utility/utility_verification.json`; these are `[DEV+VAL]`, non-confirmatory).

**What "one final experiment" means, and what it does not.**
* It is the already-preregistered confirmatory run of frozen V3 (H1–H4) on a newly generated, independently reviewed dataset, and nothing else. CID Phase A (`CID_EXPERIMENT_DESIGN`) is a separate simulation study that does not alter V3 and is not a precondition of the V3 run (PRE §8).
* **The expected outcome is negative.** The preregistration itself expects NEGATIVE-WORSE (`docs/SPRINT4_5_1_FINAL_REPORT.md` §0: dev/val V3 mean U −0.338 at λ = 2, γ = 1; zero-unsafe V3 would reach only +0.043 < δ = 0.10). The paper can be written honestly as an empirical study of attribution limits whichever way it lands.
* **No further algorithm development is recommended.** I do not recommend a new sprint. The only blockers are human decisions and writing three scripts to a frozen specification (§7).
* **Fallback if the owner declines the confirmatory run.** The paper can still be written, but then V3 must be reported as a development-stage, non-confirmatory method (`[DEV+VAL]` only), and the central contribution reduces to the Sprint 4.3–4.4 negative/limits findings (V2 not distinguishable from always-abstain on spent held-out; FCI orientation findings; CID temporal confounding; reproducibility). That is a different, weaker paper. It would not be Decision 1 for a paper about V3.

---

## 2. Work completed in this phase

| # | item | result | where |
|---|---|---|---|
| 1 | Repository state inspected and preserved | branch/HEAD verified; 165 pre-existing dirty paths untouched; no reset/clean/force | §8 |
| 2 | CI dependency failure (A: `requests`) | **fixed** (implemented, uncommitted until the commit below, verified in a clean clone) | §3 |
| 3 | CI protected-material failures (B, C) | **handled explicitly** by the Sprint 4.4.2 reproducibility-aware harness; tests not removed or weakened | §3 |
| 4 | Ground-truth label circularity | audited on dev/val (read-only); verdict PARTIALLY CIRCULAR; D23 proposed | `docs/FINAL_SCIENTIFIC_VALIDITY_CLOSURE.md` §1; `artifacts/final_closure/label_circularity_audit.json` |
| 5 | Statistical dependence / inference | reviewed; defensible for a negative conclusion, not for a positive/equivalence one | same document §2 |
| 6 | CID temporal confounding | design reviewed; zero executed evidence | same document §3 |
| 7 | Utility and baselines | preserved unchanged; normative weights stated | same document §4 |
| 8 | Approval matrix | 44 main rows + 8 secondary audit rows; 0 approved; 25 block generation | `docs/FINAL_APPROVAL_MATRIX.md` |
| 9 | Confirmatory infrastructure plan | implementation + test plan; nothing built | `docs/CONFIRMATORY_INFRASTRUCTURE_PLAN.md` |
| 10 | Independent review package for Bob | written; Bob's answers blank | `docs/FINAL_INDEPENDENT_REVIEW_PACKAGE.md` |
| 11 | IEEE Access manuscript blueprint | 19 sections, 31-row verified results table, confirmatory row marked NOT YET RUN | `docs/IEEE_ACCESS_MANUSCRIPT_BLUEPRINT.md` |
| 12 | This report | — | this file |

Five documents (items 4–7, 8–11) were drafted by parallel AI subagents from the evidence I gathered and then reconciled by me. Two subagents wrote competing versions of the infrastructure plan and the approval matrix; the unused versions are preserved unedited in `artifacts/final_closure/` (`FINAL_APPROVAL_MATRIX.earlier_draft.md`, `FINAL_CONFIRMATORY_INFRASTRUCTURE_PLAN.parallel_draft.md`). Subagents reported figures they could not verify; those are flagged inside the documents (see §9).

---

## 3. CI fixes and test counts

### 3.1 What was wrong

| failure | cause | fix |
|---|---|---|
| 3 × `ModuleNotFoundError: requests` in `tests/unit/test_prometheus_client.py` | `requirements.txt` (the only file the workflow installs) omitted `requests`. `src/rift/pipeline/e2e_runner.py` and the tests import it. The canonical py39 lock had it; CI uses Python 3.11 + `requirements.txt` | added `requests==2.32.5` to `requirements.txt` (same pin as `reproducibility/requirements-canonical-py39.lock.txt:50`); no other pin changed; no upgrade |
| 2 × protected-material tests failing as ordinary failures | the workflow ran plain `python -m pytest tests/`. The reproducibility-aware harness `scripts/sprint442_run_tests.py` (Sprint 4.4.2) was never wired into CI | `.github/workflows/test.yml` now runs `python scripts/sprint442_run_tests.py tests --tb=short --json test_classification.json`, publishes the classification to the step summary, and uploads it as an artifact |

Nothing else changed: tests are not removed, assertions not weakened, `reproducibility/protected_materials.py` and the frozen implementations untouched, no fake protected files, no sealed data in Git, no unrelated test excluded.

### 3.2 Evidence (clean clone of `1efc229`, Python 3.11.15, `pip install -r requirements.txt`)

| run | result |
|---|---|
| **Before** (plain pytest, original `requirements.txt`) — reproduces the GitHub report | **5 failed, 661 passed**, 14 warnings (the same three `requests` tests and two protected tests) |
| **After** (harness + `requests`) | **664 REPRODUCIBLE_PASS, 0 PROTECTED_PASS, 2 PROTECTED_UNAVAILABLE, 0 other skips, 0 genuine failures**, exit 0 |
| The two UNAVAILABLE | `test_dev_val_pins_and_freeze_intact` (needs `datasets/rift_v2/heldout_candidate.json`) and `test_historical_stage4_artifact_untouched` (needs `artifacts/stage4_intervention_results.json`), each labelled `PROTECTED-MATERIAL-UNAVAILABLE ... integrity NOT verified` |
| Negative control (a deliberately failing test added to the clone, then removed) | classified `FAILED`, process exit 1 |
| `--require-protected` in the clean clone | exit 3 (unavailable protected checks are not a pass) |
| Step-summary script (extracted from the workflow and run locally) | printed the 5 category counts and the "NOT verified in CI. This is not a pass." line |
| Workflow YAML | parses; step list: setup, install, harness, publish, upload, lint, secrets scan |
| Secrets scan (the workflow's own `grep`) on the clean clone | clean |

**Not verified:** this has not run on GitHub itself. I did not push. **Do not describe CI as green until a pushed run has been read.** The GitHub job will report 664 passed and 2 protected-unavailable; it will be a successful job but it will not certify the two protected integrity checks.

### 3.3 Other CI findings (pre-existing, not fixed, owner decision)

* **`make lint` is broken on a clean checkout:** `Makefile:188: *** missing separator. Stop.` (reproduced in the clone of `1efc229`). The workflow marks the lint step `continue-on-error: true`, so the failure is invisible. A separate grep for the forbidden phrases finds hits in `src/` comments that are negations ("not causally accurate"), so a literal phrase lint would also false-positive. Recorded as N2/N3 in the approval matrix.
* **Environment mismatch:** CI = Python 3.11 + `requirements.txt` (numpy 1.26.4, causal-learn 0.1.3.8). The committed results came from Python 3.9.6 + the canonical lock (causal-learn 0.1.4.8). Sprint 4.4.2 showed scores identical but one `ident_status` label differing. A passing CI therefore does not certify numerical reproduction of the committed results (N4).

### 3.4 Local verification on the owner's tree (Python 3.9.6, canonical environment)

| check | result |
|---|---|
| Reproducibility-aware safe subset (`--require-protected tests --ignore=` the 4 modules that parse legacy held-out content) | **803 passed** = 801 REPRODUCIBLE + 2 PROTECTED_PASS, 0 UNAVAILABLE, 0 other skips, **0 genuine failures**, exit 0 (46 s) |
| V3 suite `tests/unit/test_sprint440_attribution_v3.py` | **34 passed** |
| Doc-consistency checker `scripts/sprint451_doc_consistency_check.py` | FAIL 0, WARN 0, 58 numerical claims recomputed, 0 failed. (The checker rewrote two tracked `artifacts/sprint4_5_1/consistency/*` files with a new HEAD string; I restored them with `git checkout --` so no historical artifact changed.) |
| 51 original frozen files vs manifest and `HEAD` | **0 mismatches** (`artifacts/final_closure/freeze_51_reverify.json`). None of the 51 paths is sealed material |
| `requests` importable in the local env | 2.32.5 |

**27 of 888 tests were deliberately NOT run** (15 `test_sprint424_dataset_manifest`, 9 `test_sprint424_heldout_guard`, 2 `test_sprint430_independence`, 1 `test_sprint430_metrics_access_stats`), because they parse legacy held-out content. They are **not reported as passed**. D12 therefore remains OPEN. The 861-of-888 figure in the 4.5.1 report additionally relies on 48 + 10 tests run in 4.5.1 that I did not repeat.

**Disclosure (protected-material handling).** The two registered protected tests were executed by the approved Sprint 4.4.2 procedure. One of them (`verify_freeze`) SHA-256-hashes `datasets/rift_v2/heldout_candidate.json`; this is hash-only, was the same procedure used in 4.5.1, and its content was not read, displayed or recorded by me. I wrote no code that opens held-out files. My label audit reads only `datasets/rift_v2/{dev,val}.json`.

---

## 4. Scientific issues: resolved versus unresolved

Full reasoning is in `docs/FINAL_SCIENTIFIC_VALIDITY_CLOSURE.md`. Evidence tags: `[DEV+VAL]` = non-confirmatory development/validation data.

| issue | status | basis |
|---|---|---|
| **Label circularity** | **UNRESOLVED — needs researcher decision (D23); cannot be fully resolved inside a self-authored simulator** | Labels come from noise-free simulator state (`generator_v2.compute_ground_truth`, lines 390–453), never from a method output: **no leakage**. But the definition reuses RIFT's vocabulary: onset detector θ = 3.0 with 2 consecutive windows (`simulator.py:246`, same as EBD R1), an SNR ≥ 4.0 gate, a ≥ 1.0σ expected-effect threshold and a 45 s timing cut. Statistical significance is not represented in the label. `[DEV+VAL]` (N = 252): 99 ATTRIBUTE (84 with root SNR ≥ 5, 15 in [4, 5)); 46 WEAK_SIGNAL (30 in SNR [3, 4), 16 below 3); 18 NO_DISCRIMINATING_EVIDENCE; 49 of 99 ATTRIBUTE rest only on a rule identical to RIFT's R1; the label rule re-derives **163/163** stored labels that reach the SNR gate. Diagnostic gate sensitivity (not relabelling): gate 3.0 would flip 29 ABSTAIN→ATTRIBUTE, 3.5 → 12; gate 4.5 would flip 8 ATTRIBUTE→ABSTAIN, 5.0 → 15. Verdict: **partially circular, definitionally**. Existing results remain interpretable only as agreement with a simulator-defined identifiability rule |
| **Does the circularity create the negative V3 result?** | not on its own | WEAK_SIGNAL contributes −0.166 of V3's −0.338 (`[DEV+VAL]`, from PRE L2, **not recomputed by me**). Arithmetic: −0.338 + 0.166 = −0.172, still negative; and zero-unsafe V3 is +0.043 < δ |
| **Proposed remedy (D23)** | PROPOSED, NOT APPROVED | keep the primary label frozen; add a structural, threshold-free label (L-struct) and noise-free SNR / expected-effect fields as preregistered co-reported strata. It must be decided and reviewed **before G2** because the new generator has to emit the fields. If rejected: every conclusion is worded "relative to the simulator's identifiability rule" and the circularity stays a disclosed limitation. **No existing data are relabelled** |
| **Statistical dependence** | **DISCLOSED LIMITATION; analysis defensible for a negative conclusion** | 2,000 scenarios ≠ 2,000 independent observations; K = 256 templates sit in 16 fixed structures × 16 fixed fault families (crossed). No claim beyond the 16 motifs × 16 families under the preregistered simulator. Simulated power (`[SIM-POWER]`, non-confirmatory, `artifacts/sprint4_5_1/power/`): 0.83–0.99 for template ICC ≤ 0.10 with no crossed family effect; 0.65–0.83 at ICC 0.2–0.3; **0.30–0.59 under the family-block rule if a real crossed family effect exists**; a template-level test that ignores a real family effect has size 0.05–0.20. A positive conclusion is defensible only if the family-block interval also excludes 0. No change to N is recommended; raising N does not repair 16-family dependence |
| **CID temporal confounding** | **DISCLOSED; design adequate in principle; NO executed evidence** | Seven preregistered estimators E0–E6 (+ E7 placebo) over 218 cells = 214 factorial + 4 mixture, 210 distinct DGPs, 468,000 replicates; difficult drift cells (B2, B9, B7) are retained; eligibility is the exact-count rule k ≤ 138/2000 (null cells) and k ≤ 557/10,000 (mixtures), fixed before results (X12). Negative controls (sham, placebo outcome, placebo timing, every d = 0 cell) and positive controls (B1 d > 0, power-retention V4) are meaningful. **But `src/rift/cid_reliability/` and its V0 gate do not exist, so nothing in Phase A has been run and eligibility is unknown.** Dev/val evidence that E0 flags 94%/100% of non-ancestral pairs with own-drift > 0.3σ versus ≈ 5–7% for clean pairs is exploratory on a small stratum |
| **Utility and baselines** | **PRESERVED unchanged** | U = C − 2.0·S − 1.0·(n_do/20); δ = 0.10; always-abstain primary (U_AA ≡ 0). The weights are **normative researcher judgements, not empirically calibrated constants**. Per-scenario U ∈ [−3, 1]; the mean ceiling is the ATTRIBUTE prevalence π. `[DEV+VAL]`: V3 −0.338, V2 −0.562, V3 − V2 +0.224, break-even λ 0.9375 at κ = 0; V3's CI is above 0 only for λ ≤ 0.61 (κ = 0) and not at all for κ ≥ 0.05 |
| Synthetic-only evaluation; no real telemetry; low coverage; partial observability; unobserved-root identifiability boundary (A12: 7/7 unsafe, adversarial dev) | **DISCLOSED LIMITATIONS** | review package §D, blueprint §15–16 |

---

## 5. Approval matrix (summary; the full matrix is `docs/FINAL_APPROVAL_MATRIX.md`)

**Nothing is approved. 0 of the 44 main rows and 0 of the 8 secondary audit rows have been approved by anyone.** The reviewer must be a real independent human; no AI review is recorded as human approval.

| measure | count |
|---|---:|
| Main matrix rows (D1–D23, A1–A9, X5, X6, X11, X12, CID, N1–N7) | 44 |
| Secondary audit rows (X1–X4, X7–X10) | 8 |
| Rows that block confirmatory data generation | 25 (of which D10, D13, D17 only under the literal G0 wording "all D-items answered") |
| Audit-register BLOCKERs | 2 (D7, D12) |
| Rows approved by anyone | **0** |

| item the task singled out | state now | blocks generation |
|---|---|---|
| **D7** independent human scientific review | OPEN. No reviewer is named; all review so far is AI | **YES (BLOCKER)** |
| **D12** owner-run protected full-tree verification | OPEN. 27 tests not run; the safe subset passed (§3.4) | **YES (BLOCKER)** |
| **D19** cluster unit and family-block inference | NOT APPROVED. Recommended: template-level primary, family-block mandatory sensitivity; both intervals in the first paragraph | YES |
| **D20** SNR [3, 5) band | NOT APPROVED. Default: report as a stratum, do not exclude | YES |
| **D21** runner and error semantics | NOT APPROVED, **and the runner does not exist**. Finding: the preregistered "60 s timeout ⇒ abstention" is **not** a hard cutoff in `benchmark_v2._timed` (it flags `TIMEOUT` only after the call returns, lines 141–157). The new runner needs a real worker-level timeout | YES |
| **D22** pair-level robustness endpoint | NOT APPROVED; secondary and descriptive | YES |
| **Label circularity (D23)** | PROPOSED, not approved | YES (before G2) |
| **CID confounding** | design present, Phase A not run | NO for the V3 run (PRE §8); YES for any CID-reliability claim |
| **Reproducibility limitations** | X4 (14 transitive pins differ, one platform), X7 (SD/DEFF from dev/val), X8 (663 vs 664 unexplained), N4 (CI ≠ canonical environment), 27 tests not run | NO as disclosed limitations; D12 blocks |
| **X5** one unintended `shasum` of the sealed file in 4.5.1 | researcher must acknowledge or reject | YES-IF rejected |
| **X6** packaging (`pyproject.toml` invalid `build-backend`, non-PEP 440 version) | separate follow-up | NO |
| **X11** S13/S14 quota exception (90 + 90 SYMMETRIC) | NOT APPROVED | YES |
| **X12** CID eligibility cut-offs | NOT APPROVED | NO for V3 |

Seven places where documents or code disagree are listed in the matrix §2 (for example D21, and the SAP "gate maximum 14" versus "max 9"). The preregistered text was not edited.

---

## 6. Confirmatory experiment readiness

**NOT READY TO GENERATE DATA. No confirmatory data was generated; no `artifacts/sprint4_5_0/confirm/` directory exists.**

| component | state (verified on disk) |
|---|---|
| Independent confirmatory generator | **MISSING.** The frozen generator cannot be reused: `build_scenario("confirm", …)` raises `KeyError` (no `confirm` entry in `SPLIT_PREFIX`/`_SIZE_BAND`/`SPLIT_SEED`); the template inventory is exhausted. The prototype in `scripts/sprint451_dataset_protocol_checks.py` is reusable as a reference only |
| Hashed runner `scripts/sprint450_run_confirm.py` | **MISSING** |
| Analysis script `scripts/sprint450_analyze.py` | **MISSING** |
| Phase A `src/rift/cid_reliability/` + V0 gate | **MISSING** |
| Dataset manifest + integrity verification (confirm set) | MISSING (the 69-file extended manifest of the frozen code exists) |
| Preregistration recorded (`prereg.sha256`, `decisions.json`) | **NOT RECORDED** (G0, G3 not passed) |
| Quotas, S13/S14 exception, node-order invariance (T10) | specified in the protocol and in the plan; not implemented |
| "≥ 500 scenarios with unrelated temporal change" | **a target, not a guarantee**: the protocol sets a natural share ≥ 25% (≈ 500) and no sub-quota; dev/val is 52/252 = 20.6%. The realised count must be verified at QC |

The plan is `docs/CONFIRMATORY_INFRASTRUCTURE_PLAN.md` (work packages WP1–WP5, tests T1–T10 plus C1–C12, gates G0–G6). It states that new tests must run without protected files, and any test needing protected material must be registered in `reproducibility/protected_materials.py` rather than skipped silently.

---

## 7. Exact next steps (in order)

1. **Owner:** name an independent human reviewer (D7). Without this, nothing below can be approved.
2. **Owner:** decide D23 (label sensitivity strata) before any generator code is written; decide D19, D20, D21, D22, X11, X12, X5 and the rest of D1–D18, A1–A9 in the matrix.
3. **Owner:** decide whether to commit or leave untracked the Sprint 4.3.0 report and its supporting files (N6): at present a fresh clone cannot see `docs/SPRINT4_3_0_FINAL_REPORT.md` or the dev/val `per_scenario.csv`. Do not commit `artifacts/sprint4_3_0/results/held_out/` without a decision.
4. **Owner:** push the CI commit (after this report is accepted) and read the actual GitHub run; only then may anyone say CI passes, and it will show 2 protected-unavailable.
5. **Owner (D12):** on a machine where reading legacy held-out content is acceptable, run `python3 scripts/sprint442_run_tests.py --require-protected tests` on the whole tree and store the output.
6. **Engineering (after 1–2):** write the generator, runner and analysis script to the frozen specification (plan WP1–WP5), test on dev/val and pilot-tag data only, have the human reviewer sign the checklist (T9), hash at G2/G3.
7. **Bob:** perform the independent review in `docs/FINAL_INDEPENDENT_REVIEW_PACKAGE.md` §E (12 questions and a four-way verdict, answers blank).
8. **Only then** generate the confirmatory set once (≤ 3 logged attempts), run frozen V3 and comparators once, run the preregistered analysis, and write the result using only the interpretation-table wording.
9. **Manuscript:** start from `docs/IEEE_ACCESS_MANUSCRIPT_BLUEPRINT.md`. Sections that need no confirmatory result (introduction, related work, architecture, threats, limitations, the Sprint 4.3–4.4 failure analysis) can be drafted now.

---

## 8. Repository state and integrity

* The 165 pre-existing modified/untracked paths were not reset, cleaned, deleted or overwritten. Pre-existing modifications to `src/rift/pipeline/e2e_runner.py`, `src/rift/safety/safety.py`, `scripts/verify_heldout_sealed.py` and others were left as found and are **not** part of this commit.
* Committed in this phase (explicit paths only): `requirements.txt`, `.github/workflows/test.yml`, `scripts/final_label_circularity_audit.py`, `artifacts/final_closure/`, and the seven documents below.
* Historical artifacts (V2, V3, Sprint 4.3/4.4/4.5, 4.4.2) were not modified; the one tool-side rewrite of two consistency-report files was reverted.
* No confirmatory data generated. No held-out file opened, read or listed by any code I or the subagents wrote (subagents were told the sealed paths and instructed to avoid them; the approved protected tests hash one file as disclosed in §3.4).
* New documents: `docs/FINAL_SCIENTIFIC_VALIDITY_CLOSURE.md`, `docs/FINAL_APPROVAL_MATRIX.md`, `docs/CONFIRMATORY_INFRASTRUCTURE_PLAN.md`, `docs/FINAL_INDEPENDENT_REVIEW_PACKAGE.md`, `docs/IEEE_ACCESS_MANUSCRIPT_BLUEPRINT.md`, `docs/FINAL_PREPUBLICATION_STATUS.md`.
* A pre-existing, unrelated set of untracked `docs/FINAL_*.md` files (for example `FINAL_RESEARCH_DECISION.md`) from earlier phases is left untouched and uncommitted.

## 9. Figures I did not independently re-verify

* 37% / −0.87 / −0.166 (V3 behaviour in SNR [3, 4) and WEAK_SIGNAL's contribution): quoted from PRE L2 and Dataset Protocol §5.5, not recomputed.
* The CID drift-stratum rates (94%, 100%, 5.6%, 6.7%; 103/110, 64/69): quoted from PRE §1 / `SPRINT4_4_0_CID_EVIDENCE_ANALYSIS.md`, not re-read from `cid_audit.json`.
* Power-table values: quoted from the SAP and `artifacts/sprint4_5_1/power/`; not re-simulated.
* The 861-of-888 total in the 4.5.1 report (the 48 + 10 extra tests were not repeated).
* One subagent noted the gate-3.0 flip count is 29 while 30 WEAK_SIGNAL scenarios sit in SNR [3, 4); the one-scenario difference was not traced.
* The headline V3 − AA interval quoted in the 4.5.1 report ([−0.465, −0.219]) differs slightly from both studentised intervals in `utility_verification.json`; the percentile interval for the template layout is the likely source, but I did not confirm which procedure produced it.
* Whether GitHub Actions passes: **not run**.
