# RIFT — Independent Review Package for Bob

**Repository** `/Users/manassakthivel/Desktop/RIFT FINAL` · **branch** `sprint-4.5.1-prereg-finalization` · **HEAD** `1efc229783a4adece3c4041efb6ae8a9aa29b326` (verified with `git rev-parse HEAD` when this file was written).
**Author of this package:** an AI agent working for the project owner. It is a *briefing*, not a review. Nothing here is an approval, and nothing here is independent validation. **Bob's answers (§E) are intentionally blank.**

---

## 0. How to read this package

### 0.1 Evidence-category tags (used on every number; categories are never pooled across tags)

| tag | meaning | can it support a confirmatory claim? |
|---|---|---|
| **[DEV]** | Sprint 4.3.0 development split (n = 180). V3's design was informed by it. | No |
| **[VAL]** | Sprint 4.3.0 validation split (n = 72). V3 was "confirmed" on it by its authors, so it is development data in practice. | No |
| **[DEV+VAL]** | The two above added together (n = 252), where a document pools them. | No |
| **[HELD-OUT-SPENT]** | Sprint 4.3.0 sealed held-out (n = 108), opened **once** on 2026-11-03T04:06:00Z for RIFT-FULL-V2 (and V1/legacy/baselines). It is now spent and must not be reused. V3 was **never** run on it. | The Sprint 4.3.0 report labels its 24-test Holm family "confirmatory" **for V2 only**; see §C.3 caveats. |
| **[ADVERSARIAL-DEV]** | Sprint 4.4.0 hand-designed stress set (112 scenarios = 14 types × 8 variants). Written *after* inspecting dev failures; variants are not independent samples. | No |
| **[ORACLE]** | Rows that read ground truth (graph or root). Privileged upper bounds. | No (never compared inferentially) |
| **[EXPLORATORY]** | Post-hoc or unpreregistered (always-abstain reference in 4.3.0, V2G, ablations, strata, sensitivity grids). | No |
| **[SIM]** | Monte-Carlo size/power simulations and design arithmetic (non-confirmatory, built from dev/val marginals). | No |
| **[DESIGN]** | A property of a document or of code, not a measured result. | n/a |
| **[CONFIRMATORY]** | Preregistered, recorded, run once on fresh data. **No such result exists for V3.** The Sprint 4.5.0 preregistration is *PROPOSED*, not recorded; `artifacts/sprint4_5_0/prereg/` contains only `freeze_manifest.json`; no confirmatory data have been generated. | — |

### 0.2 Status of the whole project, in five lines

1. All empirical numbers in this package come from the **simulator**. There is no real telemetry, no live-system result in this package.
2. V3 has **never been evaluated on any unseen data.** There is no confirmatory result for V3.
3. The best-supported empirical statements are **negative or mixed**: neither V2 (held-out, spent) nor V3 (dev/val) beats the trivial always-abstain policy on the outcome score P2 or on preregistered utility.
4. The Sprint 4.5.0 confirmatory experiment is *designed and audited internally*, **not approved, not recorded and not implemented** (generator, runner and analysis script do not exist).
5. All review to date was done by AI agents. **No independent human review has occurred** (decision D7 is open). This package asks Bob to supply the first independent assessment.

### 0.3 What was and was not opened to write this package

* Read: the Sprint 4.3.0, 4.4.0, 4.4.2, 4.5.0 and 4.5.1 reports; `artifacts/sprint4_5_1/utility/utility_verification.json`; selected source files (see §F).
* **Not read, not parsed, not hashed by the author of this package:** `datasets/rift_v2/heldout_candidate.json`, `datasets/rift_v2/heldout_status.json`, `artifacts/sprint4_3_0/results/held_out/*`, `artifacts/sprint4_3_0/heldout_opened.json`, `artifacts/stage4_intervention_results.json`. Every held-out number in §C.3 is **copied from `docs/SPRINT4_3_0_FINAL_REPORT.md`** and from nothing else.
* Disclosed protected-data events from earlier sprints (not by this package): `verify_freeze()` hashes the held-out file's bytes inside registered protected test `test_dev_val_pins_and_freeze_intact` (approved Sprint 4.4.2 procedure); one **unapproved** `shasum -a 256` of the file by an agent in Sprint 4.5.1 (digest not displayed or recorded; no content read; decision X5, awaiting the researcher). See `docs/SPRINT4_5_1_REPRODUCIBILITY_REPORT.md` §1.
* No confirmatory data were generated. No existing file was edited to produce this package (this file is new).

---

# A. Research overview

## A.1 Research problem and motivation

In a microservice system, several services can show elevated latency after a fault. Observational RCA tools rank services by anomaly score or timing, which conflates cause and effect (`README.md`). RIFT asks whether **controlled interventions** (`do(x)`: perturb a service and observe what changes downstream) plus **causal-discovery structure** (FCI/PAG) give better root-cause attribution than observation alone, **and whether the system can correctly abstain** when the evidence cannot license an answer.

The research problem, in the words used in the preregistration (`docs/SPRINT4_5_0_PREREGISTRATION.md` §1): *"Does frozen RIFT-FULL-V3 provide useful and safe root-cause attribution beyond always-abstain, using intervention evidence robust to unrelated temporal changes?"*

All evaluation is on a **synthetic simulator** (`src/rift/scenarios/simulator.py`). Interventions are simulated, not applied to a live system (a historical live Stage 4 experiment exists as a separate artefact and is not used in any claim here).

## A.2 Architecture (components and where they live)

| component | role | code | note |
|---|---|---|---|
| **EBD** — Earliest Behavioural Divergence | R1: per-service deviation `> 3σ` (θ_detect = 3.0) persisting ≥ 2 windows; R2: temporal precedence; R3: causal relevance (graph path to another divergent service); R4: intervention evidence (CID). Definition: `docs/ebd_definition.md` | `src/rift/ebd/ebd.py` | Frozen. Constants `theta_detect=3.0`, `persist=2`. |
| **FCI / PAG** | Causal discovery on telemetry → Partial Ancestral Graph | `src/rift/fci/fci_runner.py` | Frozen. Defect **D1** (frozen decoder drops arrowheads on `o->`) documented in 4.4.0; fixed only inside V3's own decoding (`pag_semantics.py`). Skeleton F1 0.52 dev / 0.45 val; 97–98% of edges circle-marked [DEV][VAL]. |
| **Identifiability** | Decides whether the PAG supports a causal query | `src/rift/identifiability/identifiability.py` | Frozen. |
| **CID** — Causal Intervention Divergence | Wasserstein-1 divergence between a 30 s baseline window and a 30 s post-`do()` window, permutation p-value, effect gate `W1 > 0.1·IQR(baseline)`; grades `CANDIDATE` (n < 50) / `RELIABLE` (n ≥ 50) | `src/rift/cid/cid.py`, `evidence.py` (`validate_cid_for_r4`) | Frozen. With 30 s windows every recorded CID is **CANDIDATE** (dev 555/555, val 314/314, held-out V2 531/531). **No concurrent control arm**: baseline and post windows are consecutive, so treatment and time are perfectly confounded (design doc §2.1). |
| **MSIS** — Minimum Safe Intervention Set | Choose the smallest set of interventions that makes the attribution DEFINITIVE/BOUNDED subject to safety and budget (`docs/intervention_cost_model.md` L.1). In code, V2 uses an MSIS-based ordering of interventions (`order="msis"`) | `src/rift/evaluation/rift_v2.py` (`V2Config.order`) | Held-out evidence on MSIS is **mixed** (H5): MSIS reduced mean experiment duration by ~4–5 s versus random/alphabetical order on held-out (CI excludes 0) but gave no accuracy change [HELD-OUT-SPENT]; on dev/val it made no significant difference. V3 does not use an MSIS ordering; it intervenes on *every* divergent candidate. |
| **Abstention / attribution logic** | V2: R1–R4 chain, answers when a candidate passes R4 (`validate_cid_for_r4` + Bonferroni). V3: statuses `DEFINITIVE_ROOT`, `QUALIFIED_ROOT` (reported as attributions), `POSSIBLE_ROOT`, `INSUFFICIENT_EVIDENCE`, `NON_IDENTIFIABLE` (abstentions) | `rift_v2.py`, `src/rift/attribution_v3/rift_v3.py` | `DEFINITIVE_ROOT` means "no caveat was raised by the rule", **not** definitive causal evidence; it rests on CANDIDATE-grade CID. 25/48 dev and 12/22 val `DEFINITIVE` answers were unsafe [DEV][VAL]. |

## A.3 V2 versus V3

| | **RIFT-FULL-V2** (`rift_v2.py`) | **RIFT-FULL-V3** (`attribution_v3/rift_v3.py`) |
|---|---|---|
| Introduced | Sprint 4.3.0 | Sprint 4.4.0 (new method; V2 frozen and untouched) |
| Candidate set | Divergent services passing R3 (PAG path to another divergent service) | **Every** divergent service (no PAG filter) |
| Graph role | Selects candidates and outcomes | Diagnostic and a *contradiction* caveat only; corrected mark decoding |
| Interventions | MSIS order; skips services already "explained" | Intervenes on all candidates (symmetry check); also a positive control on `x` itself |
| Multiplicity | Bonferroni over outcomes | Holm over outcomes |
| Extra rules | — | Source rule (mutual effects ⇒ abstain), earlier-divergence guard, explicit statuses |
| Cost | mean 1.49 / 1.71 `do()` per scenario (dev/val) | 2.51 / 3.19 (≈ 1.7–1.9×) |
| Thresholds | repository defaults | **no new thresholds**; `theta_detect=3.0`, `persist=2`, `alpha=0.05` inherited |
| Origin of design | Preregistered (Protocol v2) then run once on held-out | Developed on dev; confirmed on val; **never run on held-out** |

V3's rules were each motivated by a measured V2 failure on dev (V3 design doc §2): e.g. true root isolated by FCI in 8/14 dev and 5/13 val V2 wrong-root cases; the symmetry check was chosen on dev (`V3-NO-SYMMETRY-CHECK`: unsafe 54 vs 35, dev) and "confirmed" on val.

---

# B. Empirical history

| sprint | what happened (one line) | primary source |
|---|---|---|
| 4.2.x | Legacy evaluation; the legacy held-out found contaminated (all 15 legacy held-out scenarios have content twins in dev/val; 83 records hold 25 distinct contents). Retained as legacy, unused for v2 claims. | `docs/SPRINT4_3_0_FINAL_REPORT.md` §1, §4 |
| **4.3.0** | New 360-scenario synthetic corpus (dev 180 / val 72 / held-out 108), 0 cross-split leaks; preregistered Protocol v2 (Amendments 1–3), freeze of 37 files, one-shot held-out. **PARTIAL PASS**: infrastructure and negative findings are the durable results; H4 unsupported, H5 mixed, V2 not better than always-abstain. | `docs/SPRINT4_3_0_FINAL_REPORT.md` |
| **4.4.0** | Failure analysis of V2; defect D1; V3 built and evaluated on **dev/val only**. **PARTIAL PASS**: V3 has fewer unsafe/wrong-root answers than V2; P1 gain not significant; P2 not distinguishable from always-abstain. CID found capped at CANDIDATE and drift-susceptible. | `docs/SPRINT4_4_0_FINAL_REPORT.md` |
| **4.4.1** | V3's runtime dependencies were untracked; tracked in commit `db77446`. | `docs/SPRINT4_4_2_REPRODUCIBILITY_REPORT.md` header; `docs/SPRINT4_5_0_PREREGISTRATION.md` §2.5 |
| **4.4.2** | Reproducibility hardening: canonical lock file, protected-material test classification, fresh-clone reproduction. | `docs/SPRINT4_4_2_REPRODUCIBILITY_REPORT.md` |
| **4.5.0** | Preregistration, SAP, CID Phase-A design, dataset protocol, execution plan, audit. **PROPOSED**; V3 *expected to fail* the primary endpoint. | `docs/SPRINT4_5_0_*.md` |
| **4.5.1** | Internal adversarial review → corrections (estimand/cluster unit, power, utility wording, CID eligibility, quota, node-order leak, extended freeze manifest). Two BLOCKERs remain: D7, D12. Nothing implemented. | `docs/SPRINT4_5_1_*.md` |

## B.1 Sprint 4.3.0 — held-out evaluation `[HELD-OUT-SPENT]`
Summary (details and figures in §C.3): V2 on held-out scored P1 = 20/45, P2 = 60/108, unsafe 37/108, coverage 57/108. The trivial always-abstain policy scores P2 = 63/108, so **V2 did not outperform it** (post-hoc reference; −0.028, McNemar p = 0.76). V2 beat six never-abstaining baselines on P2 and P3_safe after Holm, but not on P1 (nominally *below* B6/B7), not B5-RIFT-OBS after Holm, and not legacy RIFT-FULL on P2 (p = 0.13). H4 (interventions reduce unsafe rate on counterexample strata) was **unsupported**; H5 (MSIS lowers cost without hurting accuracy) **mixed**.

## B.2 Sprint 4.4.0 — attribution failure analysis
* **All 27 V2 wrong-root answers on dev/val were downstream descendants of the true root** (14 dev, 13 val; all SEMI_DIRECTED). Dominant mechanism: FCI isolated the true root so it never became a candidate (8/14 dev, 5/13 val).
* Held-out V2: all 14 wrong answers also named a descendant of the true root [HELD-OUT-SPENT, from the 4.3.0 report].
* **A9 oracle graph** lifts V2's held-out P1 from 0.444 to 0.711: the learned graph is the bottleneck [HELD-OUT-SPENT][ORACLE].

## B.3 FCI orientation findings `[DEV][VAL]`
* Skeleton precision 0.675 / 0.622, recall 0.424 / 0.355, F1 0.52 / 0.45, SHD 298 / 216 (dev / val; PAG available in 138/180 and 58/72 scenarios).
* 97.8% (dev) / 97.0% (val) of learned edges are circle-marked; 1 / 2 fully directed edges; of 6 / 9 oriented true edges, 0 / 1 were oriented correctly.
* Defect D1 in the frozen decoder (collider `X o-> Z` decoded UNDIRECTED); fix only in V3's own decoder; re-decoding alone changed V2 by ≤ 1 scenario.
* Conclusion in the report: the learned PAG is a poor ancestry signal; V3 *reduces dependence* on it rather than improving it.

## B.4 CID temporal-confounding findings
* CID with consecutive windows deterministically confounds treatment and time. Triangle-inequality bound: `Δ − κ ≤ ψ₀ ≤ Δ + κ` where κ is natural between-window change (CID design §2.1). No test statistic computed from that design alone can separate them.
* Empirical `[DEV][VAL]` (V2 trace pair set): CID flagged a "significant" shift for **94% (dev) / 100% (val)** of non-ancestral pairs whose outcome service has own-drift > 0.3σ, versus 5.6% / 6.7% for clean pairs. The drift stratum is **17 pairs per split** (10 dev and 6 val scenarios), entangled with oscillation/intermittent faults.
* V3's own, larger pair set: 103/110 = 94% (dev, 18 scenarios) and 64/69 = 93% (val, 10 scenarios) vs 5.6% / 3.9% for clean pairs (`artifacts/sprint4_4_0/cid_audit.json`, as quoted in PRE §1.1).
* CID power `[SIM]`: ~10% sensitivity below 0.25σ, ~49% at 0.5–1σ, ≥ 87% at ≥ 1σ; Monte-Carlo power at 0.5σ ≈ 49% (m = 1) and ≈ 29% (m = 3).
* The "94% spurious" figure is a **conditional rate on a small stratum**, not an overall false-positive rate.

## B.5 Sprint 4.4.1 / 4.4.2 reproducibility findings
Source: `docs/SPRINT4_4_2_REPRODUCIBILITY_REPORT.md`.
* A fresh clone built only from the committed lock file (`reproducibility/requirements-canonical-py39.lock.txt`, 65 pinned lines) reproduces V3 dev/val: all 252 scenarios × 6 variants, identical scores; 9 of 10 `artifacts/sprint4_4_0` files reproduce (timing fields excluded; the 10th, `trace_meta.json`, depends on the sealed file and is PROTECTED_UNAVAILABLE).
* **Three environments** were run (A canonical Py 3.9.6 / causal-learn 0.1.4.8; B `requirements.txt` Py 3.11.15 / causal-learn 0.1.3.8; C = B with only causal-learn upgraded). Scores identical in all three. FCI differs in **2 of 213** scenarios between causal-learn 0.1.3.8 and 0.1.4.8, which changes one diagnostic label (`ident_status` of V2D-0117; 6 records) and no score.
* scikit-learn 1.6.1 and causal-learn 0.1.4.8 of the original run were **inferred, not recorded**.
* Two committed integrity tests inspect protected material absent from git (sealed held-out; Stage 4 artifact). A reproducibility-aware runner (`scripts/sprint442_run_tests.py` + `reproducibility/protected_materials.py`) classifies them `PROTECTED-MATERIAL-UNAVAILABLE` rather than pass/fail. Fresh clone, env A: 664 reproducible passes, 2 unavailable, 0 failures. Owner tree: 886 reproducible + 2 protected = 888.
* Evidence is from **one platform** (macOS arm64). Linux/x86_64, Python 3.10/3.12 and other BLAS builds were not tested.

## B.6 Sprint 4.4.2 / closure — environment and CI findings
* `requirements.txt` (used by GitHub Actions, Python 3.11) omitted `requests`; the lock file had it. The GitHub Actions run on the Sprint 4.5.1 merge reported `5 failed, 661 passed, 14 warnings`: 3 `test_prometheus_client.py` failures (`ModuleNotFoundError: requests`) and the 2 protected-material tests.
* **Current state of the fix in this working tree (uncommitted):** `requirements.txt` adds `requests==2.32.5` and `.github/workflows/test.yml` runs `scripts/sprint442_run_tests.py tests --tb=short --json test_classification.json`, publishes a step summary and uploads the classification. Both files show as ` M` in `git status`. The closure session reported a successful clean-clone Python 3.11 verification; **GitHub Actions itself has not been re-run on these changes, and no document should claim CI is green.** Bob should treat CI status as unverified until a pushed run is observed.
* In CI the 2 protected checks will be reported as PROTECTED_UNAVAILABLE (integrity **not verified**), never as passed.

## B.7 Sprint 4.5 preregistration and corrections
Sources: `docs/SPRINT4_5_0_PREREGISTRATION.md`, `SPRINT4_5_0_STATISTICAL_ANALYSIS_PLAN.md`, `SPRINT4_5_0_CID_EXPERIMENT_DESIGN.md`, `SPRINT4_5_0_DATASET_PROTOCOL.md`, `SPRINT4_5_0_FINAL_PREREGISTRATION_AUDIT.md`, `SPRINT4_5_1_FINAL_REPORT.md`, `SPRINT4_5_1_SCIENTIFIC_REVIEW.md`.

Design as currently written (all **PROPOSED**; not recorded; not approved):
* **H1 (primary, confirmatory):** `E[U_V3] > 0`, where `U_i = C_i − λ·S_i − γ·(n_do,i/20)`, **λ = 2.0, γ = 1.0, δ = 0.10**, strict unsafe (`benchmark_v2.score_one`), `U_AA ≡ 0`. Always-abstain is the primary comparator.
* Secondary H2–H4 (V3 vs V2 on utility, unsafe rate, P1) only if H1 is rejected (fixed-sequence gatekeeping, Holm over H2–H4). H5 (V3 vs observational baselines) exploratory.
* **N = 2000 scenarios, 256 template groups (16 per structure), 16 fixed structures S01–S16, 16 fixed fault families**, 40% ATTRIBUTE (800), 5–9 scenarios per group (SAP also writes "gate maximum 14"; PRE/4.5.1 report write max 9: an inconsistency Bob should check), fixed quota matrix (S13/S14 at 90 SYMMETRIC each, exception X11). Estimator: stratified ratio estimator; CI: stratified group bootstrap-t (B = 20,000, seed 4505); sensitivity: family-block bootstrap (seed 4506).
* Claim restricted to the 16 motifs (fixed strata) as produced by the confirmatory generator on the simulator.
* CID Phase A: **seven core estimators E0–E6** (E0 existing CID; E1 longer windows; E2 concurrent control; E3 detrended; E4 difference-in-differences; E5 AR-aware null; E6 randomised switchback) + E7 placebo timing + negative controls; 218 cells (214 factorial + 4 mixture, 8 degenerate ⇒ 210 distinct DGPs); 468,000 replicates. Phase A **cannot change V3** and is not a precondition of Phase B (D9).
* Corrections made in 4.5.1 (selected): cluster unit changed from union-find groups (which collapse to 7–11 giant groups) to generator-assigned template; 16 structures reclassified as fixed strata (random-structures reading would have MDE ≈ 0.18–0.25 independent of N); power claims re-derived by Monte-Carlo, the earlier "90% power at DEFF 2" **retracted** (0.83); six wording errors in the utility section (E1–E6) corrected; CID eligibility rule replaced (exact-count cut-offs k ≤ 138/2000, k ≤ 557/10,000); S13/S14 quota exception; node-order leak identified (root first in 99/99 dev+val attributable scenarios with an observed root).
* Still **missing** (checked in the filesystem): `scripts/sprint450_run_confirm.py`, `scripts/sprint450_analyze.py`, the new confirmatory generator, `src/rift/cid_reliability/`, tests T1–T10; `artifacts/sprint4_5_0/prereg/prereg.sha256` and `decisions.json`.
* Pre-stated expectation: **V3 is expected to fail H1** at the preregistered exchange rates (dev/val mean U = −0.338).

---

# C. Quantitative evidence

Every table is tagged. Where a figure is computed by this package from other tabled figures, it says so ("sum of reported cells").

## C.1 Sample sizes

| set | n | ATTRIBUTE / ABSTAIN_REQUIRED | templates | tag |
|---|---:|---|---:|---|
| dev (`datasets/rift_v2/dev.json`, sha256 `a833ad0c…ef5f`) | 180 | 68 / 112 | 75 | [DEV] |
| val (`val.json`, sha256 `e82252b4…a1fb`) | 72 | 31 / 41 | 30 | [VAL] |
| dev+val | 252 | 99 / 153 (π = 0.393) | 105 | [DEV+VAL] (sum of reported cells) |
| held-out (`heldout_candidate.json`, sha256 string `97b90fa4…e69ce` copied from `independence_report.json`, not recomputed here) | 108 | 45 / 63 | 71 | [HELD-OUT-SPENT] |
| adversarial dev (`adversarial_dev.json`, sha256 `3525bc05…2472`) | 112 | 80 / 32 | — (8 variants of each of 14 types) | [ADVERSARIAL-DEV] |
| confirmatory (proposed) | 2000 | 800 / 1200 | 256 | **does not exist** |

Dev+val union-find groups K = 21; template K = 105 (`utility_verification.json`).

## C.2 Development and validation results `[DEV]` `[VAL]` — Sprint 4.4.0

Source: `docs/SPRINT4_4_0_FINAL_REPORT.md` §1 (cells reproduced from saved artifacts and, for V2, independently from the Sprint 4.3.0 saved outputs).

| metric | Dev V2 | Dev V3 | Dev always-abstain | Val V2 | Val V3 | Val always-abstain |
|---|---:|---:|---:|---:|---:|---:|
| P1 correct root (of ATTRIBUTE) | 28/68 | 32/68 | 0/68 | 8/31 | 13/31 | 0/31 |
| P2 correct outcome (all scenarios) | 102/180 | 116/180 | **112/180** | 35/72 | 44/72 | **41/72** |
| Unsafe answers | 52 | 35 | 0 | 27 | 13 | 0 |
| Coverage (answered) | 80 | 67 | 0 | 35 | 26 | 0 |
| Wrong root on ATTRIBUTE | 14 | 7 | – | 13 | 3 | – |
| Conditional accuracy, answered ATTRIBUTE | 28/42 | 32/39 | – | 8/21 | 13/16 | – |

Other configurations `[DEV]`/`[VAL]`: V3-DEFINITIVE-ONLY P1 23/68 and 10/31, P2 114 and 42, unsafe 25 and 12, coverage 48 and 22. V2 with the **oracle** graph `[ORACLE]`: P1 39/68 and 19/31, P2 104 and 41, unsafe 51 and 22. Legacy RIFT-FULL: P1 25/68 and 15/31, P2 81 and 36, unsafe 86 and 28.

Paired V3 vs V2 `[DEV]` `[VAL]` (exact McNemar; Holm applied by the 4.4.0 *auditor* across these six tests; saved artifacts contain uncorrected p-values; **exploratory** because dev informed V3 and val was inspected):

| metric | split | n | V3 − V2 | 95% CI (as saved) | only V3 / only V2 | exact p (unc.) | Holm (6) |
|---|---|---:|---:|---|---:|---:|---:|
| P1 | dev | 68 | +0.059 | [−0.065, 0.190] | 12 / 8 | 0.503 | 0.503 |
| P1 | val | 31 | +0.161 | [0.000, 0.355] | 7 / 2 | 0.180 | 0.359 (descriptive: < 10 discordant pairs) |
| P2 | dev | 180 | +0.078 | [0.006, 0.150] | 29 / 15 | 0.0488 | 0.195 |
| P2 | val | 72 | +0.125 | [0.013, 0.243] | 13 / 4 | 0.0490 | 0.195 |
| P3_safe | dev | 180 | +0.094 | [0.028, 0.166] | 29 / 12 | 0.0115 | 0.0575 |
| P3_safe | val | 72 | +0.194 | [0.069, 0.333] | 17 / 3 | 0.0026 | 0.0155 |

V3 vs always-abstain on P2 `[DEV]` `[VAL]`: dev +0.022 (CI [−0.061, 0.107], 32 / 28, p = 0.699); val +0.042 (CI [−0.097, 0.192], 13 / 10, p = 0.678). **No difference.** V2 − always-abstain on P2: −0.056 dev, −0.083 val (p = 0.27, 0.29). P1 and safety contrasts against always-abstain are significant only because that policy never answers.

Coverage-matched comparison `[DEV]` `[VAL]`: where both answered, V3 correct 26 vs V2 23 (dev, 52 scenarios) and 12 vs 7 (val, 23). V3-only answered: 15 dev (9 unsafe), 3 val (2 unsafe); V2-only answered: 28 dev (23 unsafe), 12 val (11 unsafe). The safety gain is mostly V3 **not answering** scenarios V2 answered unsafely.

Cost `[DEV]` `[VAL]`: mean `do()` per scenario V3 2.51 / 3.19 vs V2 1.49 / 1.71; mean simulated experiment time 75 s / 96 s vs 45 s / 51 s.

Dev+val pooled (sum of reported cells; used by the utility analysis) `[DEV+VAL]`: V3 correct 45 of 99 ATTRIBUTE, answered 93, unsafe 48; V2 correct 36, answered 115, unsafe 79; P2 V3 160/252, V2 137/252, always-abstain 153/252 (computed here by adding the dev and val cells above).

## C.3 Held-out results `[HELD-OUT-SPENT]` — Sprint 4.3.0, copied from `docs/SPRINT4_3_0_FINAL_REPORT.md` §7–§11

> **This held-out set is spent.** It was opened once, after the freeze, and may not be reused for model selection or any new claim. Neither V3 nor any Sprint 4.4/4.5 component was run on it. The held-out values below were **not read from the held-out files** by the author of this package; they are copied from the report.
> Caveats: (a) the held-out design shares workload, observability, temporal and intervention marginals with dev/val by declaration; (b) it contains structure `feedback_like` (24) and family `recovery_instability` (18) unseen at dev/val time; (c) the report itself cautions that the benchmark favours abstention (58% of held-out scenarios require it); (d) V2's dev-set failures informed post-freeze amendments (Amendments 1–3 were pre-freeze; V2G is post-hoc).

n = 108 (45 ATTRIBUTE, 63 ABSTAIN_REQUIRED), 71 templates. Denominators: P1 45, P2 108, unsafe 108.

| method | P1 (of 45) | P2 (of 108) [Wilson 95%] | unsafe (of 108) | coverage (of 108) | tag |
|---|---|---|---:|---:|---|
| B0-EARLIEST | 17 (0.378) | 18 (0.167) [0.11, 0.25] | 90 | 107 | held-out |
| B0-HIGHEST | 18 (0.400) | 18 (0.167) [0.11, 0.25] | 90 | 108 | held-out |
| B1-LATENCY-CORR | 17 (0.378) | 18 (0.167) [0.11, 0.25] | 90 | 107 | held-out |
| B3-SIEVE-LIKE | 18 (0.400) | 19 (0.176) [0.12, 0.26] | 89 | 107 | held-out |
| B5-RIFT-OBS | 17 (0.378) | 42 (0.389) [0.30, 0.48] | 53 | 70 | held-out |
| B6-RIFT-RANDOM | 27 (0.600) | 33 (0.306) [0.23, 0.40] | 75 | 102 | held-out |
| B7-RIFT-ONE-SHOT | 27 (0.600) | 33 (0.306) [0.23, 0.40] | 75 | 102 | held-out |
| RIFT-FULL-LEGACY | 21 (0.467) | 52 (0.481) [0.39, 0.57] | 49 | 70 | held-out |
| **RIFT-FULL-V2** | **20 (0.444) [0.31, 0.59]** | **60 (0.556) [0.46, 0.65]** | **37 (0.343)** | **57 (0.528)** | held-out |
| ORACLE legacy-PAG | 35 (0.778) | 55 (0.509) | 53 | 88 | `[ORACLE]` |
| ORACLE V2-oracle-graph | 32 (0.711) | 60 (0.556) | 41 | 73 | `[ORACLE]` |
| ORACLE UPPER-BOUND | 45 (1.000) | 108 (1.000) | 0 | 45 | `[ORACLE]` |
| RIFT-FULL-V2G | 14 (0.311) | 63 (0.583) [0.49, 0.67] | 18 | 32 | **[EXPLORATORY]** (post-hoc Amendment 3; not in the confirmatory family) |
| *Always-abstain* | 0 (0/45) | **63 (0.583)** | 0 | 0 | **[EXPLORATORY]** (post-hoc, trivial reference) |

Always-abstain vs V2 on held-out `[EXPLORATORY]`: V2 − AA on P2 = **−0.028**, 95% CI [−0.145, +0.102], McNemar p = 0.76. On dev and val V2 is also at or below it (102/180 vs 112/180; 35/72 vs 41/72) `[DEV]` `[VAL]`.

Detection (stage-1 persistence, method-independent) `[HELD-OUT-SPENT]`: TP 100, FN 4, FP 2, TN 2; precision 0.980, recall 0.962, FPR 2/4 = 0.50 (**only 4 no-fault scenarios; extremely imprecise**).

V2 failure mechanics `[HELD-OUT-SPENT]`: of 45 ATTRIBUTE scenarios V2 answered 34 (20 correct, **14 wrong**, all a downstream service of the true root, all SEMI_DIRECTED) and abstained on 11. Unsafe on ABSTAIN_REQUIRED: 23 of 63 (WEAK_SIGNAL 12, SYMMETRIC_MUTUAL_DEPENDENCY 6, ROOT_UNOBSERVED 3, NO_DISCRIMINATING_EVIDENCE 2); in 10 of the 23 the named service is a true root but the evidence cannot support the claim.

**Protocol-labelled "confirmatory" family** (Sprint 4.3.0, V2 only): 24 tests = 8 non-oracle comparators × 3 metrics (P1, P2, P3_safe), exact McNemar / permutation / template-clustered bootstrap, Holm. **12 of 24 significant after Holm.**
* Significant after Holm: P2 and P3_safe vs B0-EARLIEST, B0-HIGHEST, B1, B3, B6, B7 (Holm p ≤ 0.0028). Large advantages arise largely from abstention on a benchmark where 58% of scenarios require abstention.
* **Not significant:** P1 against every comparator (V2 vs B6/B7 −0.156, p = 0.14); P2 vs B5-RIFT-OBS (+0.167, Holm p = 0.115); P3_safe vs B5 (Holm p = 0.195); **P2 vs RIFT-FULL-LEGACY (+0.074, CI [−0.009, +0.159], p = 0.13, Holm 1.0)**; P3_safe vs legacy (McNemar p = 0.0169, Holm p = 0.186).
* Hypotheses: H1 partly met (6 of 8); **H2 not met nominally** (20/45 vs 27/45); H3 met (23/63 vs 57–63/63); **H4 unsupported**; **H5 mixed**.
* Ablations are `[EXPLORATORY]`, uncorrected. Held-out highlights: A3-NO-EBD worse on P2 (−0.139) and safety (−0.157), the clearest loss; A9 oracle graph P1 +0.267 `[ORACLE]`; A6/A8 (no interventions) P1 equal to V2, P2 within 0.02, *lower* unsafe rate, lower coverage ⇒ "observational variants are competitive; interventional evidence adds no demonstrated benefit".
* H4 table (counterexample strata, n = 12 dev / 6 val / 7 held-out): V2 unsafe 6/12, 4/6, 4/7 vs no-intervention A6 5/12, 3/6, 3/7. Not supported in any split.
* H5 (held-out): MSIS vs random ordering mean experiment duration 56.4 s vs 61.1 s (+4.7 s, template-bootstrap CI [+2.2, +7.4], uncorrected p = 0.0014); vs alphabetical 60.3 s (+3.9 s, CI [+0.8, +7.2], p = 0.0246); P1 0.444 vs 0.378 and 0.444 vs 0.444.

## C.4 Adversarial development stress tests `[ADVERSARIAL-DEV]` — Sprint 4.4.0

112 scenarios (14 failure-mode types × 8 variants; 80 ATTRIBUTE, 32 ABSTAIN_REQUIRED), labels from `compute_ground_truth`. **Designed after inspecting dev failures; variants are parameter variations of one design, not independent samples; not external validation.**

| method | correct (of 80 ATTRIBUTE) | answered | unsafe | wrong root |
|---|---:|---:|---:|---:|
| V2 | 57 | 81 | 24 | 7 |
| V3-FULL | 67 | 74 | 7 | 0 |
| V3-DEFINITIVE-ONLY | 62 | 69 | 7 | 0 |
| V3-NO-SYMMETRY-CHECK | 69 | 85 | 16 | 0 |

The 7 remaining V3 unsafe answers are all type A12 (unobserved root): an identifiability boundary for any decision rule using the observed telemetry only. These results say V3 handles failure patterns *identified on dev*; they give no estimate for unseen systems.

## C.5 Diagnostic and oracle results `[ORACLE]`

| quantity | value | source |
|---|---|---|
| V2 + oracle graph, held-out | P1 32/45 = 0.711, P2 60/108, unsafe 41, coverage 73 | 4.3.0 report §7 |
| V2 + oracle graph, dev / val | P1 39/68, 19/31; P2 104, 41; unsafe 51, 22 | 4.4.0 report §1 |
| Oracle upper bound, dev+val | correct 99, unsafe 0 | `utility_verification.json` |
| Legacy RIFT-FULL + oracle PAG, held-out | P1 35/45 = 0.778, P2 55/108, unsafe 53 | 4.3.0 report §7 |

Oracle rows read ground truth and are never compared inferentially or counted toward any "RIFT beats baselines" statement.

## C.6 Utility analysis `[DEV+VAL]` `[EXPLORATORY]` (not confirmatory)

Source: `artifacts/sprint4_5_1/utility/utility_verification.json` (`purpose`: "dev/val only; NOT confirmatory", seed 4510, B_main = 10,000, B_grid = 4,000, n = 252; independent re-implementation of the scorer agreed on 3,276 method×scenario pairs with 0 mismatches). Utility `U = C − λS − γ(n_do/20)` at **λ = 2.0, γ = 1.0 (κ = 0.05 per `do()`), strict unsafe**.

**Per-scenario facts.** Bounds `U ∈ [−(λ+γ), 1] = [−3, 1]` (not [0, 1]); observed range V3 [−2.4, 0.9], V2 [−2.25, 0.95]; `C·S = 0` and no `n_do` above `MAX_DO = 20` for any method. V3 maximum `n_do` 8, V2 6. Pooled prevalence π = 0.3929 (dev 0.378, val 0.431).

**Decomposition (counts, [DEV+VAL]):**

| method | correct | answered | unsafe | wrong root on ATTR | answered on ABSTAIN_REQ | "lucky right service" on ABSTAIN_REQ | operational unsafe | mean n_do |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V3-FULL | 45 | 93 | 48 | 10 | 38 | 18 | 30 | 2.706 |
| V2 | 36 | 115 | 79 | 27 | 52 | 25 | 54 | 1.556 |
| B0-EARLIEST | 49 | 237 | 188 | 50 | 138 | 37 | 151 | 0 |
| Oracle upper bound `[ORACLE]` | 99 | 99 | 0 | 0 | 0 | 0 | 0 | 0 |

V3-FULL outcome partition: correct 45, unsafe 48, abstain 159 (sum 252). V2: correct 36, unsafe 79, abstain 137.

**Primary-rate result `[DEV+VAL]` (λ = 2, γ = 1, strict):**

| contrast | mean | 95% CI template percentile | 95% CI template studentised | 95% CI group percentile |
|---|---:|---|---|---|
| U(V3) − U(always-abstain) = mean U(V3) | **−0.3377** | [−0.4613, −0.2172] | [−0.4724, −0.2224] | [−0.4756, −0.2019] |
| U(V2) − AA | −0.5619 | [−0.7116, −0.4133] | [−0.7209, −0.4181] | [−0.7699, −0.3699] |
| U(V3) − U(V2) | +0.2242 | [+0.0855, +0.3665] | [+0.0847, +0.3703] | [+0.0850, +0.4012] |
| operational-unsafe: mean U(V3) | −0.1948 | [−0.3000, −0.0937] | [−0.3095, −0.0967] | [−0.2992, −0.0930] |

(Split means: dev −0.3367, val −0.3403. SD of V3 per-scenario U 0.969; skewness −1.09. The preregistration quotes the seed-450, B = 4000 interval [−0.465, −0.219]; the seed-4510, B = 10,000 interval above agrees within the 0.01 tolerance of SAP §12.)

**Break-even and sensitivity.** Break-even λ\* (V3 = AA), strict, point estimate [95% template CI]: κ = 0: **0.9375** [0.614, 1.436]; κ = 0.025: 0.5823 [0.308, 0.985]; κ = 0.05: 0.2271 [−0.010, 0.550]; κ = 0.10: −0.483 (no λ ≥ 0). The CI of V3 − AA lies entirely above zero only for λ ≤ 0.61 at κ = 0 and λ ≤ 0.30 at κ = 0.025, and for no λ ≥ 0 at κ ≥ 0.05. Break-even λ\* at κ = 0 for other methods: V2 0.456, legacy 0.351, B0-EARLIEST 0.261 — none beats always-abstain at λ ≥ 1. Under the operational-unsafe definition V3's mean U at κ = 0.05 is −0.076 (λ = 1), −0.195 (λ = 2), −0.433 (λ = 4).

**Zero-unsafe ceiling.** With every unsafe penalty removed, mean U(V3) = 45/252 − 0.1353 = 0.1786 − 0.1353 = **+0.043 < δ = 0.10**. Mean V3 cost term (γ = 1) = 0.1353.

**Minimum precision implied by λ.** An answer is worth giving only if P(correct) ≥ λ/(1+λ): λ = 1 → 0.50; λ = 2 → 0.667; λ = 3 → 0.75; λ = 5 → 0.833 (before cost).

**Normative status.** λ = 2, γ = 1 and δ = 0.10 are **researcher judgements, not empirical constants**. λ = 2 was proposed by someone who had seen dev/val break-even analysis, so it is **not demonstrably independent of dev/val** (PRE §3.3). The sign of V3 − AA flips with λ and κ; the grid is secondary.

**Verification caveat.** `utility_verification.json` records 58 claims, 56 verified, 2 not verified within the 0.0006 tolerance: "V3 mean cost term γ=1 (PRE 3.3: 0.136)" recomputed 0.1353; "B0-EARLIEST BE κ=0" claimed 0.26, recomputed 0.2606. Both are rounding-level; the preregistration text now uses 0.135.

## C.7 Statistical-power evidence `[SIM]` (non-confirmatory)

Source: SAP §6.7, `artifacts/sprint4_5_1/power/*.json`. Inputs from dev/val (SD 0.969, shift μ = +0.10, N = 2000, one-sided α = 0.025, studentised bootstrap-t, B = 199, R = 400–1000).

* Pooled layout (250 groups, mean size 8): power 0.917 / **0.831** / 0.653 / 0.367 at realised DEFF 1.5 / 2 / 3 / 6. Earlier claims "90% power at DEFF 2" and "DEFF capped near 1.58–2.64" were **retracted**.
* Adopted fixed-strata layout (16 × 16 groups), no crossed family effect (rf = 0): power 0.992 / 0.987 / 0.967 / 0.942 / 0.825 / 0.738 at template ICC rg = 0 / 0.03 / 0.05 / 0.10 / 0.20 / 0.30; size 0.015–0.034.
* Crossed family dependence (rf = 0.02–0.05) ignored by the template-level bootstrap: **size 0.046–0.202 against nominal 0.025** (anti-conservative). Family-block bootstrap: controls size (≤ 0.04) but **power 0.30–0.59**.
* Variance stress (SD ×1.25): power 0.943 / 0.878 / 0.763 / 0.608 at rg = 0 / 0.05 / 0.10 / 0.20.
* H4 (P1 V3 vs V2): 0.85 at the full dev/val effect, **0.23 at half** — likely underpowered.
* Dev/val ICC estimates: template ICC 0.027 (95% CI [−0.14, 0.19], K = 105); family-after-structure ICC 0.016 (CI ≈ [−0.018, 0.041], K = 15; imprecise). Empirical DEFF on union-find groups 1.37 (K = 21).
* Statement in the preregistration: **no effective sample size is claimed; power is not adequate at higher design effects; this is a property of 16 fixed structures × 16 fixed families and cannot be repaired by raising N.**

## C.8 What is **not** in this package (no data exist)

| item | status |
|---|---|
| Confirmatory result for V3, V2 or any comparator | none |
| Confirmatory CID estimator comparison (E0–E6) | none; module `src/rift/cid_reliability/` does not exist |
| Any real-telemetry or production result | none |
| V3 on held-out | not run, by design |

---

# D. Scientific concerns

Each concern is stated with the evidence available and what is *not* known. Items 1–2 were examined in the closure phase; the analysis document is `docs/FINAL_SCIENTIFIC_VALIDITY_CLOSURE.md` (**untracked, AI-written**; its numbers should be re-derived with `scripts/final_label_circularity_audit.py`, untracked, which reads dev/val only).

### D.1 Ground-truth label circularity — **partial; definitional, not leakage**
* Labels come from `generator_v2.compute_ground_truth` (noise-free simulator state; no method output is an input). **No leakage of method output into labels.**
* But the ATTRIBUTE/WEAK_SIGNAL boundary is built from RIFT-like constants: label onset detector θ = 3.0 with 2 consecutive windows (= EBD R1); an SNR gate `≥ 4.0` (one σ above R1); an interventional criterion (expected effect ≥ 1.0σ within `30 + delay + 2·lag/Δt ≤ 45 s`) that mirrors the CID power curve and the 30 s `do()` window.
* `[DEV+VAL]` audit (AI-run, not independently re-run): ATTRIBUTE 99 (84 with root SNR ≥ 5; 15 in [4, 5)); WEAK_SIGNAL 46 (30 with SNR ∈ [3, 4); 16 with SNR < 3); NO_DISCRIMINATING_EVIDENCE 18; ROOT_UNOBSERVED 31, INSUFFICIENT_BASELINE 23, SYMMETRIC 22, NO_FAULT 13. **49 of 99 ATTRIBUTE labels rest only on the temporal rule identical to RIFT R1.** Moving the SNR gate to 3.0 / 3.5 / 4.5 / 5.0 changes 29 / 12 / 8 / 15 labels. 45 of 252 (18%) lie within 1σ of the gate.
* "Statistical significance" is **not** in the label (no test, α, or noise); the problem is that a design choice about how large an amplitude must be, and which evidence routes count, uses RIFT's own vocabulary.
* WEAK_SIGNAL is a normative *abstain-required* class, not a causal fact; "should the system answer at 3.5σ?" is a risk-appetite decision — the thing λ encodes.
* Quoted, not re-derived: V3 answers 37% of SNR ∈ [3, 4) scenarios (mean U −0.87); WEAK_SIGNAL contributes −0.166 of V3's −0.338.
* Arithmetic bound: even zeroing the whole WEAK_SIGNAL contribution leaves mean U ≈ −0.172; the zero-unsafe ceiling is +0.043 < δ. The negative V3-vs-AA result therefore does not hinge on the boundary band, but the size of the penalty and the V3-vs-V2 comparison are label-relative.
* **Open:** a proposed co-reported sensitivity label ("D23": threshold-free structural label + continuous detectability covariates) is a *proposal*; no researcher decision is recorded. The primary frozen label is unchanged and **no retrospective relabelling was done**. A fully independent label is not obtainable inside a simulator written by the same authors.

### D.2 Crossed and hierarchical dependence — **not resolved by N**
* 2000 scenarios are **not** 2000 independent observations. Hierarchy: 16 fixed structures → 256 templates (generator-assigned groups) → scenarios. The 256 groups are crossed with 16 fixed fault families.
* `[SIM]` The template-level bootstrap is anti-conservative if a real crossed family effect exists (size up to 0.20); the family-block bootstrap controls size but has power 0.30–0.59. Preregistered compromise (D19): template-level primary, family-block mandatory sensitivity, report "not robust to family-level dependence" if they disagree.
* Dev/val family-ICC (0.016) is imprecise and compatible with both worlds.

### D.3 Fixed structural scope
* Estimand is a fixed-strata mean over **16 preregistered motifs × 16 fault families**. No generalisation to unseen structures or arbitrary systems. S10–S14 are *variants* of categories V3 has components for (confounding, hidden cause, mutual dependency); "structures V3 was not tuned on" is not claimed. The set is a **designed stress set** (40% ATTRIBUTE by quota), not a sample of incidents.
* The confirmatory set shares simulator physics, family amplitude table, factor level sets and the label function with dev/val (limitation L3); it does not test a different generative mechanism.

### D.4 CID temporal confounding
See §B.4. Consecutive-window CID cannot separate intervention effects from background drift by construction; empirical drift-stratum false-confirmation 93–100% (small strata, entangled with oscillation). **All CID evidence in V3 is CANDIDATE-grade with no control arm; `DEFINITIVE_ROOT` is not definitive.** The Phase-A design (E0–E6, 218 cells) *is capable in principle* of distinguishing the estimators — E2 (concurrent control, exchangeability), E4 (parallel trends), E6 (randomised switchback, design-based) — but each rests on a stated assumption, and the design lists conditions where each fails by construction (CID design §3.4). It has not been run. Whether the simulator can supply the control arm/longer windows is itself a gate (V0).

### D.5 Synthetic-only evaluation
Telemetry, faults, interventions and recovery (a 30 s model constant) are simulator outputs. Intervention fidelity is a simulator assumption. Noise is i.i.d. in the simulator (autocorrelation not represented). Everything is "validated on synthetic ground-truth scenarios" and "intervention-consistent" only.

### D.6 Partial observability
ROOT_UNOBSERVED is an identifiability boundary: 7/7 adversarial A12 cases remain unsafe for V3; an unobserved root is indistinguishable from observed descendants with the data available. It accounts for 31/153 dev/val abstain-required scenarios and 240 of the proposed 2000.

### D.7 Low attribution coverage
V3 answers 93/252 dev+val scenarios (37%); V2 held-out coverage 57/108; roughly 42 of 113 dev and 14 of 46 val V3 non-answers come from telemetry too short to run anything (`INSUFFICIENT_BASELINE`/`INSUFFICIENT_SAMPLES`).

### D.8 Always-abstain baseline
Always-abstain scores P2 = 63/108 (held-out), 112/180 (dev), 41/72 (val). V2 is below or equal to it on all three; V3 is statistically indistinguishable on dev/val. The benchmark has 58–62% ABSTAIN_REQUIRED scenarios by design, so P2 rewards abstention; the 4.3.0 report states this. V3's only advantage over it is that it sometimes names a correct root (P1 45/99 vs 0).

### D.9 Utility-weight sensitivity
See §C.6: sign of V3 − AA flips at λ\* = 0.94 (κ = 0), 0.58 (κ = 0.025), 0.23 (κ = 0.05) and at no λ for κ = 0.10. λ, γ, δ are normative choices, not empirically calibrated. The unsafe indicator is *strict* (a correctly named root on an ABSTAIN_REQUIRED scenario counts as unsafe; 18 of V3's 38 abstain-required answers were such "lucky" answers); the operational definition is a sensitivity analysis only.

### D.10 Reproducibility limitations
* Two integrity tests cannot run on a fresh clone; **27 of 888 tests were deliberately not run** in Sprint 4.5.1 because they parse sealed held-out content (D12 BLOCKER, owner-run). `verify_heldout_sealed.py` 4/4 covers the legacy Sprint 4.2.4 set only.
* One platform (macOS arm64, CPython 3.9.6); CI uses Python 3.11 and the older `requirements.txt` stack; 14 transitive pins differ from the lock; clean-export reproducible passes 663 here vs 664 in 4.4.2 (unexplained).
* causal-learn 0.1.3.8 vs 0.1.4.8 differs on 2/213 PAGs. Original sklearn/causal-learn versions inferred, not recorded.
* `pyproject.toml` still has an invalid `build-backend` and non-PEP 440 version (`pip install -e .` fails regardless of Python); `requires-python` was changed `>=3.10 → >=3.9` in 4.5.1 (D13 awaits ratification).
* **Most Sprint 4.3.0 documents and source (listed in §F) are untracked in git**; a clean clone does not contain the sprint-4.3.0 final report, the held-out results, `scripts/sprint430_analyze.py`, or the tests `test_sprint430_*`.
* Two items noted while writing this package, for Bob to check: group size (target max 9 in PRE vs gate max 14 in SAP/Dataset Protocol); "full suite 880 passing" (4.4.0 report) vs 888 (4.4.2 report) — different dates and trees.

### D.11 No real production telemetry validation
No real-system, live-testbed or production result appears in this package. A historical Stage 4 live experiment (`artifacts/stage4_intervention_results.json`, protected, untracked) is not used in any claim.

### D.12 Review limitations (relevant to how much to trust this package)
All earlier review was by AI agents sharing the authoring team's tooling and blind spots; the only protected-data deviation was disclosed (X5). The preregistration states V3 is expected to fail H1; the study as designed may therefore be a preregistered confirmation of a known negative.

---

# E. Review questions for Bob

**Instructions.** Please inspect the repository independently (§F lists paths and git-tracking status). For every major conclusion give **evidence (file, line or command output) and reasoning**. Do not rely on this package's summaries where a primary source is available. Where you cannot verify something, say so. **The answer fields below are intentionally blank. Nobody else may fill them in on your behalf.**

| # | question | Bob's answer, evidence and reasoning |
|---|---|---|
| 1 | Is the research question publishable? | |
| 2 | Is the contribution sufficiently distinct and meaningful? | |
| 3 | Are the ground-truth labels independently valid? | |
| 4 | Is the statistical analysis defensible? | |
| 5 | Is the CID design capable of distinguishing intervention effects from temporal drift? | |
| 6 | Are the baselines sufficient? | |
| 7 | Are the conclusions appropriately scoped? | |
| 8 | Is the empirical evidence adequate for an IEEE Access submission? | |
| 9 | What are the three most serious reviewer objections? | |
| 10 | What is the smallest additional experiment needed? | |
| 11 | Which existing findings should form the central contribution? | |
| 12 | Should RIFT be presented as (a) a successful attribution method, (b) a conservative intervention-grounded framework, or (c) an empirical study of attribution limits? | |

### Verdict (select exactly one and justify; leave blank until Bob decides)

- [ ] **READY FOR MANUSCRIPT**
- [ ] **READY AFTER MINOR CORRECTIONS**
- [ ] **REQUIRES ONE ADDITIONAL EXPERIMENT**
- [ ] **NOT YET SCIENTIFICALLY DEFENSIBLE**

Justification (evidence and reasoning for every major conclusion): ______________________________

Reviewer name / affiliation / date / independence statement: ______________________________

*(This section remains unsigned. An AI-authored note must not be recorded as the human approval required by decision D7.)*

### Suggested things to verify (optional; not answers)

* Re-run `python3 scripts/final_label_circularity_audit.py` (dev/val only) and read `generator_v2.compute_ground_truth` (lines ≈ 390–453) and `simulator.detectable_onset_window` (≈ 246–250).
* Recompute dev/val utility with `python3 scripts/sprint451_utility_sensitivity.py` (reads dev/val only) and compare with `artifacts/sprint4_5_1/utility/utility_verification.json`.
* Check the always-abstain row against the P2 columns of `docs/SPRINT4_4_0_FINAL_REPORT.md` §1.
* Check that `compute_cid` has no concurrent control (`src/rift/cid/cid.py`) and read CID design §2.1 for the identification argument.
* Check whether `U_i` and `score_one` match PRE §3.1 (`src/rift/evaluation/benchmark_v2.py`).
* Do **not** open the sealed held-out paths marked `PROTECTED` in §F.

---

# F. Repository paths and git-tracking status

Method: `git ls-files` (membership) and `git status --porcelain` run on branch `sprint-4.5.1-prereg-finalization` at HEAD `1efc2297`. **Tracked = yes** means the path is in the index at HEAD. `??` = untracked (not in a clean clone); ` M` = tracked but modified in the working tree (uncommitted).

> **Consequence for review:** several Sprint 4.3.0 documents and sources are untracked. A reviewer working from a fresh `git clone` will **not** see them. Bob needs the owner's working tree or an export that includes the paths marked **no**. Held-out files marked PROTECTED are untracked on purpose and must not be opened.

### F.1 Documents

| path | tracked | note |
|---|:-:|---|
| `docs/SPRINT4_3_0_FINAL_REPORT.md` | **no** (`??`) | source of all held-out figures |
| `docs/SPRINT4_3_0_DATASET_PROVENANCE_AUDIT.md` | **no** (`??`) | |
| `docs/SPRINT4_3_0_SCENARIO_DIVERSITY_REPORT.md` | **no** (`??`) | |
| `docs/SPRINT4_3_0_STATISTICAL_VALIDATION.md` | **no** (`??`) | |
| `docs/SPRINT4_3_0_FAILURE_TAXONOMY.md` | **no** (`??`) | |
| `docs/EVALUATION_PROTOCOL_V2.md` | yes | Protocol v2, Amendments 1–3 |
| `docs/SPRINT4_4_0_FINAL_REPORT.md` | yes | |
| `docs/SPRINT4_4_0_ATTRIBUTION_FAILURE_ANALYSIS.md`, `…_FCI_GRAPH_QUALITY.md`, `…_CAUSAL_DIRECTIONALITY.md`, `…_CID_EVIDENCE_ANALYSIS.md`, `…_V3_DESIGN.md` | yes | |
| `docs/SPRINT4_4_2_REPRODUCIBILITY_REPORT.md` | yes | |
| `docs/SPRINT4_5_0_PREREGISTRATION.md` | yes | PROPOSED, revision 3 |
| `docs/SPRINT4_5_0_STATISTICAL_ANALYSIS_PLAN.md` | yes | |
| `docs/SPRINT4_5_0_CID_EXPERIMENT_DESIGN.md` | yes | |
| `docs/SPRINT4_5_0_DATASET_PROTOCOL.md` | yes | |
| `docs/SPRINT4_5_0_FINAL_PREREGISTRATION_AUDIT.md` | yes | decision register D1–D22, A1–A9, X1–X12 (§10) |
| `docs/SPRINT4_5_0_EXECUTION_PLAN.md` | yes | |
| `docs/SPRINT4_5_1_FINAL_REPORT.md`, `…_SCIENTIFIC_REVIEW.md`, `…_REPRODUCIBILITY_REPORT.md` | yes | internal AI review only |
| `docs/ebd_definition.md`, `docs/intervention_cost_model.md` | yes | EBD and MSIS definitions |
| `docs/FINAL_SCIENTIFIC_VALIDITY_CLOSURE.md` | **no** (`??`) | AI-written closure analysis (label circularity etc.) |
| `docs/FINAL_APPROVAL_MATRIX.md` | **no** (`??`) | AI-written; grants no approvals |
| `docs/CONFIRMATORY_INFRASTRUCTURE_PLAN.md` | **no** (`??`) | AI-written plan; nothing implemented |
| `docs/FINAL_INDEPENDENT_REVIEW_PACKAGE.md` | **no** (new) | this file |

### F.2 Source code

| path | tracked |
|---|:-:|
| `src/rift/attribution_v3/rift_v3.py`, `pag_semantics.py`, `adversarial.py`, `diagnostics.py` | yes |
| `src/rift/evaluation/rift_v2.py`, `benchmark_v2.py`, `stats_v2.py`, `dataset_registry_v2.py`, `dataset_registry.py`, `held_out_guard.py` | yes |
| `src/rift/ebd/ebd.py`, `src/rift/fci/fci_runner.py`, `src/rift/cid/cid.py`, `src/rift/cid/evidence.py`, `src/rift/identifiability/identifiability.py` | yes |
| `src/rift/scenarios/simulator.py`, `generator_v2.py` (+ `fingerprint`, `independence`, `duplicates`, `splitter`, `validators`) | yes |
| `src/rift/benchmark/adversarial_generator.py` | yes (committed in 4.5.1) |
| `src/rift/cid_reliability/` | **absent** (planned) |
| confirmatory generator module | **absent** (planned) |

### F.3 Scripts, tests, environment

| path | tracked | note |
|---|:-:|---|
| `scripts/sprint430_run_evaluation.py` | yes | |
| `scripts/sprint430_generate_datasets.py`, `sprint430_analyze.py`, `sprint430_freeze.py` | **no** (`??`) | |
| `scripts/sprint440_run_v3.py`, `…_analyze.py`, `…_cid_audit.py`, `…_adversarial.py` | yes | |
| `scripts/sprint442_run_tests.py`, `reproducibility/protected_materials.py`, `reproducibility/requirements-canonical-py39.lock.txt` | yes | reproducibility-aware runner |
| `scripts/sprint451_utility_sensitivity.py`, `sprint451_doc_consistency_check.py` | yes | |
| `scripts/final_label_circularity_audit.py` | **no** (`??`) | dev/val only |
| `scripts/sprint450_run_confirm.py`, `scripts/sprint450_analyze.py` | **absent** | planned; do not exist |
| `tests/unit/test_sprint440_attribution_v3.py`, `tests/unit/test_sprint442_reproducibility.py` | yes | |
| `tests/unit/test_sprint430_independence.py`, `test_sprint430_rift_v2.py`, `test_sprint430_metrics_access_stats.py` | **no** (`??`) | |
| `pyproject.toml` | yes | `requires-python >=3.9` at HEAD |
| `requirements.txt` | yes, **` M` (uncommitted: adds `requests==2.32.5`)** | CI fix, not yet committed |
| `.github/workflows/test.yml` | yes, **` M` (uncommitted: reproducibility-aware runner)** | CI fix, not yet committed |

### F.4 Data and artifacts

| path | tracked | note |
|---|:-:|---|
| `datasets/rift_v2/dev.json`, `val.json`, `manifest.json`, `independence_report.json` | yes | dev/val pins |
| `datasets/rift_v3_dev/adversarial_dev.json` | yes | |
| `datasets/rift_v2/heldout_candidate.json` | **no** (`??`) | **PROTECTED — sealed, spent; do not open** |
| `datasets/rift_v2/heldout_status.json` | **no** (`??`) | **PROTECTED** |
| `artifacts/sprint4_3_0/heldout_opened.json` | **no** (`??`) | **PROTECTED** |
| `artifacts/sprint4_3_0/results/held_out/` (incl. `statistics.json`) | **no** | **PROTECTED** — Sprint 4.3.0 held-out outputs |
| `artifacts/sprint4_3_0/results/{dev,val}/per_scenario.json` | yes | |
| `artifacts/sprint4_3_0/results/{dev,val}/` other files (`statistics.json`, `aggregate.*`, …) | **no** (`??`) | |
| `artifacts/sprint4_3_0/freeze.json` | yes | 37-file freeze |
| `artifacts/stage4_intervention_results.json` | **no** (`??`) | **PROTECTED** historical live artifact; SHA pinned `e4cf1391…` |
| `artifacts/sprint4_4_0/{analysis,v3_dev,v3_val,cid_audit,adversarial_results}.json` | yes | |
| `artifacts/sprint4_4_2/{environments_tested,cross_environment_comparison}.json` | yes | |
| `artifacts/sprint4_5_0/prereg/freeze_manifest.json` | yes | 51 files, sha256 `609bcb9d…aeb6` |
| `artifacts/sprint4_5_0/prereg_audit/audit.json` | yes | |
| `artifacts/sprint4_5_1/utility/utility_verification.json` | yes | |
| `artifacts/sprint4_5_1/freeze/extended_manifest.json` | yes | 69 files, sha256 `0e3a9262…25ec` |
| `artifacts/sprint4_5_1/power/{stratified_power,family_block_power}.json` | yes | |
| `artifacts/sprint4_5_1/nodeorder/node_order_investigation.json`, `review/adversarial_review.md`, `consistency/consistency_report.md`, `cid/cell_reconciliation.md`, `repro/tests_not_run_held_out_content_risk.txt` | yes | |
| `artifacts/final_closure/label_circularity_audit.json` | **no** | AI-run diagnostic; dev/val only |
| `artifacts/sprint4_5_0/confirm/` | **absent** | no confirmatory data exist |
| `artifacts/sprint4_5_0/prereg/prereg.sha256`, `decisions.json` | **absent** | preregistration not recorded |

---

# G. Approval status (summary only; the authoritative matrix is `docs/SPRINT4_5_0_FINAL_PREREGISTRATION_AUDIT.md` §10)

| item | state, as of HEAD `1efc2297` |
|---|---|
| **D7** independent human reviewer | **BLOCKER, open.** No reviewer named. Bob's review is **not** D7 unless Bob is a named, independent human researcher who reviews the generator, wrapper, acceptance sampler and analysis script — which do not yet exist. |
| **D12** owner-run protected full-tree test run | **BLOCKER, open.** 27 of 888 not run, not reported as passed. |
| D1–D6, D8–D11, D13–D16, D18–D22, A1–A9, X5, X6, X11, X12 | require researcher approval; none recorded (`decisions.json` absent). D17 recommended for removal. |
| X2 | MUST FIX: write, test on dev/val, and hash generator, runner and analysis script. |
| Label circularity (D23 proposal) | decision not recorded. |

Classification counts in the register: BLOCKER 2; MUST FIX 1; REQUIRES RESEARCHER APPROVAL 25; ACCEPTED LIMITATION 2; INFORMATIONAL 5.

---

## H. Language and claims guardrails for the reviewer

Throughout the repository, results are phrased "validated on synthetic ground-truth scenarios" and "intervention-consistent". The terms "causally accurate", "production-ready" and "guarantees" are not used (other than in the rule that forbids them), and a CANDIDATE-grade CID check is never called definitive. Please hold any manuscript text to the same standard.

**Claims this package does not make:** that RIFT works on real systems; that V3 beats always-abstain; that V2 beat always-abstain on held-out; that any p-value on dev/val is confirmatory; that PAG edges or reachability indicate causal ancestry; that independent review has occurred; that CI is green.
