# RIFT — IEEE Access Manuscript Blueprint

**This is a blueprint, not a drafted paper.** It specifies, for each manuscript section, what the evidence supports and what it does not. It contains no confirmatory results, because none exist. It issues no publication verdict (that belongs to the independent reviewer, see `docs/FINAL_INDEPENDENT_REVIEW_PACKAGE.md`) and records no approval by anyone.

## 0. Ground rules for the whole manuscript

### 0.1 Central contribution framing (binding for the outline)

The most honest framing is a **two-part contribution**:

1. **An empirical study of attribution limits.** On synthetic ground-truth scenarios, a pipeline built on temporal divergence, FCI and intervention checks does not demonstrably beat the trivial always-abstain policy on the preregistered-style outcome score. The study documents *why* (FCI isolates or fails to orient roots, descendants get named, CID is under-powered and drift-confounded, unobserved roots are an identifiability boundary).
2. **A conservative intervention-grounded framework.** RIFT-FULL-V3 is a better-behaved decision rule than V2: fewer wrong-root and unsafe answers, achieved largely by abstaining more, at the cost of more `do()` interventions and with no significant gain in correct-root accuracy.

RIFT must **not** be framed as a successful attribution method.

### 0.2 Hard prohibitions (apply to every section)

- Do not claim RIFT (V2 or V3) beats always-abstain. Every available comparison says otherwise or is indistinguishable (see §13).
- Do not claim real-world, production or external validity. All evidence is synthetic, from one self-authored simulator.
- Do not present dev, validation, adversarial-development or oracle numbers as held-out or confirmatory.
- Do not describe 2,000 planned scenarios as 2,000 independent observations. Do not claim generalisation beyond the 16 fixed structural motifs.
- Do not claim the independent review has occurred. Do not claim D7 (independent human review) or D12 (owner-run protected verification) is done.
- Do not call CID validated, or `DEFINITIVE_ROOT` definitive. Do not claim CI is green until the GitHub run has actually been read.
- Do not reuse numbers or claims from `docs/IEEE_PAPER_DRAFT.md` or `docs/FINAL_IEEE_SUBMISSION_READINESS.md` without reconciliation (see §0.4).

### 0.3 Evidence categories (never mix in a table or sentence)

| Tag | Meaning | Status |
|---|---|---|
| Development | dev split, 180 scenarios (V3 was designed on it) | exists |
| Validation | val split, 72 scenarios (inspected during V3 work) | exists |
| Held-out | Sprint 4.3 held-out, 108 scenarios, opened once, **V2 only** | exists, sealed, **not re-read here** |
| Adversarial | Sprint 4.4 112 hand-designed scenarios, `adv_dev` | exists; designed after seeing dev failures |
| Oracle | rows that read ground truth or an oracle graph | privileged upper bounds, not method results |
| Simulation-power | Monte-Carlo size/power runs | design arithmetic, not evidence about RIFT |
| Confirmatory | preregistered Sprint 4.5 experiment | **NOT YET RUN; no data exist** |

### 0.4 Legacy documents that conflict with the current evidence

`docs/IEEE_PAPER_DRAFT.md` (an earlier draft; targets TSE/ICSE) and `docs/FINAL_IEEE_SUBMISSION_READINESS.md` report an earlier evaluation (small dev 50 / val 18 / legacy held-out 15 splits; "0.00% FAR", "H2 CONFIRMED", Online Boutique). Sprint 4.3 found the legacy held-out contaminated (all 15 scenarios have content twins in dev/val; the 83 legacy records have 25 distinct contents; `SPRINT4_3_0_FINAL_REPORT.md` §1). **Those claims must not be carried into the manuscript.** I did not re-verify the legacy numbers; I only read the abstract, the hypothesis summary and the readiness table.

### 0.5 Sources read for this blueprint

`docs/SPRINT4_3_0_FINAL_REPORT.md`, `docs/SPRINT4_4_0_FINAL_REPORT.md`, `artifacts/sprint4_5_1/utility/utility_verification.json`, `docs/SPRINT4_5_1_FINAL_REPORT.md`, `docs/FINAL_SCIENTIFIC_VALIDITY_CLOSURE.md`, `docs/FINAL_APPROVAL_MATRIX.md`, `docs/CONFIRMATORY_INFRASTRUCTURE_PLAN.md` (headings and component status), `docs/SPRINT4_4_2_REPRODUCIBILITY_REPORT.md` (headings and selected lines). Sealed held-out files were **not** opened; held-out numbers are quoted from the committed report only.

---

## 1. Verified results table (the only numbers the manuscript may take from this blueprint)

Every row is copied from one of: `docs/SPRINT4_3_0_FINAL_REPORT.md` (S43), `docs/SPRINT4_4_0_FINAL_REPORT.md` (S44), `artifacts/sprint4_5_1/utility/utility_verification.json` (UV). Metric definitions: P1 = correct root among ATTRIBUTE scenarios; P2 = correct outcome (answer-or-abstain) over all scenarios; unsafe = unsafe answers over all scenarios; coverage = answered / all. "AA" = always-abstain. The `U` rows use the preregistered utility `U = C − 2.0·S − 1.0·(n_do/20)`, which has **never been applied to held-out data**.

| # | Category | Source | Method / contrast | n | Metric | Value | CI / p |
|---|---|---|---|---:|---|---|---|
| R1 | held-out (one-shot, V2 only) | S43 §7 | RIFT-FULL-V2 | 108 (45 ATTR / 63 ABS) | P1 | 20/45 = 0.444 | Wilson [0.31, 0.59] |
| R2 | held-out | S43 §7 | RIFT-FULL-V2 | 108 | P2 | 60/108 = 0.556 | Wilson [0.46, 0.65] |
| R3 | held-out | S43 §7 | RIFT-FULL-V2 | 108 | unsafe / coverage | 37/108 = 0.343 / 57/108 = 0.528 | — |
| R4 | held-out, **post-hoc, exploratory** | S43 §7 | always-abstain | 108 | P2 | 63/108 = 0.583 | V2 − AA = −0.028, 95% CI [−0.145, +0.102], McNemar p = 0.76 |
| R5 | held-out | S43 §7 | RIFT-FULL-LEGACY | 108 | P1 / P2 / unsafe | 21/45 / 52/108 / 49/108 | V2 vs legacy P2 +0.074, CI [−0.009, +0.159], p = 0.13, Holm 1.0 |
| R6 | held-out | S43 §7–§8 | B6/B7 (random / one-shot intervention) | 108 | P1 / P2 / unsafe | 27/45 / 33/108 / 75/108 | V2 vs B6/B7 P1 −0.156, p = 0.14 (not significant) |
| R7 | held-out | S43 §7–§8 | B5-RIFT-OBS (observational) | 108 | P1 / P2 / unsafe | 17/45 / 42/108 / 53/108 | V2 vs B5 P2 +0.167, Holm p = 0.115 (not significant) |
| R8 | held-out | S43 §8 | V2 vs 6 never-abstaining baselines | 108 | P2, P3_safe | significant | Holm p ≤ 0.0028 (12 of 24 confirmatory tests significant after Holm; driven by abstention on a benchmark where 58% of scenarios require it) |
| R9 | held-out, **post-hoc exploratory** | S43 §7, §10 | V2G (abstention-guarded variant) | 108 | P1 / P2 / unsafe / coverage | 14/45 / 63/108 / 18/108 / 32/108 | not in the confirmatory family; McNemar P1 p = 0.0312 uncorrected |
| R10 | oracle (held-out) | S43 §7 | V2-ORACLE-GRAPH | 108 | P1 / P2 / unsafe | 32/45 / 60/108 / 41/108 | privileged; shows the graph is a bottleneck |
| R11 | oracle (held-out) | S43 §7 | ORACLE:UPPER-BOUND | 108 | P1 / P2 / unsafe | 45/45 / 108/108 / 0/108 | privileged |
| R12 | development | S44 §1 | V2 / V3 / AA | 180 (68 ATTR) | P1 | 28/68 / 32/68 / 0/68 | V3 vs V2 +0.059, CI [−0.065, 0.190], exact p = 0.503, Holm 0.503 |
| R13 | development | S44 §1 | V2 / V3 / AA | 180 | P2 | 102 / 116 / **112** (of 180) | V3 vs V2 +0.078, p = 0.0488, **Holm 0.195**; V3 vs AA +0.022, CI [−0.061, 0.107], p = 0.699 |
| R14 | development | S44 §1 | V2 / V3 / AA | 180 | unsafe / coverage | 52 / 35 / **0**; 80 / 67 / 0 | V3 vs V2 P3_safe p = 0.0115, Holm 0.0575 |
| R15 | validation | S44 §1 | V2 / V3 / AA | 72 (31 ATTR) | P1 | 8/31 / 13/31 / 0/31 | V3 vs V2 +0.161, p = 0.180, Holm 0.359 (descriptive: 9 discordant pairs) |
| R16 | validation | S44 §1 | V2 / V3 / AA | 72 | P2 | 35 / 44 / **41** (of 72) | V3 vs V2 +0.125, p = 0.0490, **Holm 0.195**; V3 vs AA +0.042, CI [−0.097, 0.192], p = 0.678 |
| R17 | validation | S44 §1 | V2 / V3 / AA | 72 | unsafe / coverage | 27 / 13 / **0**; 35 / 26 / 0 | V3 vs V2 P3_safe p = 0.0026, Holm 0.0155 |
| R18 | oracle (dev / val) | S44 §1 | V2 + oracle graph | 180 / 72 | P1, P2, unsafe | dev 39/68, 104, 51; val 19/31, 41, 22 | privileged |
| R19 | adversarial (dev, designed after dev failures) | S44 §5 | V2 / V3-FULL | 112 (80 ATTR / 32 ABS) | correct on ATTR; answered; unsafe; wrong root | V2 57; 81; 24; 7 — V3 67; 74; 7; 0 | not independent validation; 8 variants per type are not independent samples |
| R20 | adversarial | S44 §5 | V3 on unobserved-root type (A12) | 7 | unsafe | 7/7 (V2 8/8) | identifiability boundary, counted as failures |
| R21 | development + validation pooled (non-confirmatory) | UV | V3-FULL | 252 | outcome partition | correct 45 / unsafe 48 / abstain 159 | answered 93; wrong-root on ATTR 10; answered on ABS 38 |
| R22 | development + validation pooled | UV | RIFT-FULL-V2 | 252 | outcome partition | correct 36 / unsafe 79 / abstain 137 | answered 115 |
| R23 | development + validation pooled | UV | V3 mean `U` (λ=2, γ=1, strict) | 252 | mean U | **−0.3377** | template pct95 [−0.461, −0.217]; template stud95 [−0.472, −0.222]; group (K=21) pct95 [−0.476, −0.202], stud95 [−0.514, −0.203] |
| R24 | development + validation pooled | UV | V2 mean `U` | 252 | mean U | −0.5619 | template pct95 [−0.712, −0.413] |
| R25 | development + validation pooled | UV | V3 − V2 | 252 | Δ mean U | +0.2242 | template pct95 [0.086, 0.366]; group stud95 [0.081, 0.429] |
| R26 | development + validation pooled | UV | V3 − AA | 252 | Δ mean U | −0.3377 | bootstrap P(mean > 0) = 0.0000 (both clusterings) |
| R27 | development + validation pooled | UV | operational-unsafe sensitivity, V3 − AA | 252 | Δ mean U | −0.1948 | template pct95 [−0.300, −0.094] |
| R28 | development + validation pooled | UV | intervention cost | 252 | mean n_do (max) | V3 2.706 (8); V2 1.556 (6) | — |
| R29 | development + validation pooled | UV | break-even λ\* (V3, κ=0, strict) | 252 | λ\* | 0.9375 | template pct95 [0.614, 1.436]; V3 − AA CI > 0 only for λ ≤ 0.61 (κ=0), λ ≤ 0.30 (κ=0.025), never for κ ≥ 0.05 |
| R30 | oracle (dev + val) | UV | oracle upper bound | 252 | correct / unsafe | 99 / 0 | used only to scale δ; prevalence π = 0.3929, δ/π = 0.2545 |
| R31 | **confirmatory** | — | **NOT YET RUN** | — | H1–H4 | **NOT YET RUN — no data exist; placeholder only** | — |

Notes on use:

- R1–R11 describe **V2** on the Sprint 4.3 held-out. V3 has **never** been run on any held-out data.
- R12–R30 are development/validation. V3 was designed on dev and val was inspected, so these p-values are **not confirmatory**; Holm was applied by the auditor across six tests as one family (S44 §3).
- UV marks 2 of its 58 internal claims as `verified: false` (V3 cost term 0.136 vs recomputed 0.1353; B0-EARLIEST break-even 0.26 vs 0.2606). Use the recomputed values (0.1353, 0.2606).
- Per-scenario `U` lies in [−3, 1], not [0, 1]. The mean is bounded above by prevalence π ≈ 0.393 (UV `per_scenario_bounds`).
- Zero-unsafe V3 would reach only +0.043 (= 0.179 − 0.135) < δ = 0.10 (arithmetic from UV values; `FINAL_SCIENTIFIC_VALIDITY_CLOSURE.md` §1.7).
- Quoted, not re-derived by me: "WEAK_SIGNAL contributes −0.166 of V3's −0.338" and "V3 answers 37% of SNR ∈ [3,4) scenarios" (PRE L2 / Dataset Protocol §5.5).
- Utility weights λ = 2.0, γ = 1.0, δ = 0.10 are normative researcher choices, not calibrated constants.

---

## 2. Section-by-section blueprint

Each section lists: **Objective · Evidence available · Repository artifacts · Reportable quantitative results · Supported claims · Claims that must NOT be made · Missing information.**

### Section 1 — Title

- **Objective:** a title that states scope and does not imply success.
- **Evidence available:** project name "RIFT: Intervention-Grounded Detection of Behavioral Divergence"; actual findings are mostly negative/limiting.
- **Repository artifacts:** `docs/FINAL_RESEARCH_DECISION.md` (read heading only), README, `docs/IEEE_PAPER_DRAFT.md` title (legacy).
- **Reportable quantitative results:** none.
- **Supported claims:** a title naming a *conservative*, *intervention-grounded* framework and/or *limits of attribution* on *synthetic* benchmarks.
- **Must NOT claim:** "accurate", "validated", "outperforms", "production", "robust", "real-world" in the title.
- **Missing:** author's final choice. Candidate shapes (not final): "Where Intervention-Grounded Root-Cause Attribution Fails: A Synthetic Study with a Conservative Abstaining Framework"; "RIFT: A Conservative Intervention-Grounded Framework for Root-Cause Attribution and an Empirical Study of Its Limits".

### Section 2 — Abstract

- **Objective:** ~200-word honest summary: problem, framework, synthetic evaluation, headline negative/mixed result, scope.
- **Evidence available:** R1–R4, R12–R17, R21–R26, R19.
- **Repository artifacts:** `SPRINT4_3_0_FINAL_REPORT.md` §1, `SPRINT4_4_0_FINAL_REPORT.md` §0/§2, `utility_verification.json`.
- **Reportable quantitative results (safe set):** (a) held-out V2: P1 20/45, P2 60/108 vs always-abstain 63/108 (post-hoc), V2 not distinguishable from AA (p = 0.76); (b) dev/val V3 vs V2: unsafe 79 → 48 of 252, wrong roots 27 → 10 (14+13 → 7+3 by split), no significant P1 gain; (c) V3 mean U −0.338 vs AA 0 on 252 non-confirmatory scenarios.
- **Supported claims:** RIFT-FULL-V3 makes fewer unsafe and wrong-root attributions than V2 on synthetic dev/val, mostly by abstaining; it does not demonstrably beat always-abstain; limits are characterised.
- **Must NOT claim:** outperforming always-abstain or baselines in general; "validated"; any confirmatory result; real-world effectiveness; "0% false attribution" (legacy, contaminated).
- **Missing:** the confirmatory result (NOT YET RUN). If the confirmatory experiment is run, the abstract must be rewritten around its preregistered interpretation state. Until then, state explicitly that no preregistered confirmatory test has been completed.

### Section 3 — Index Terms

- **Objective:** keywords for IEEE Access indexing.
- **Evidence available:** topic only.
- **Repository artifacts:** none specific.
- **Reportable quantitative results:** none.
- **Supported claims:** root cause analysis; microservices; causal discovery; FCI; interventions; abstention / selective prediction; AIOps; negative results.
- **Must NOT claim:** terms implying validated causal inference ("causal ground truth in production", "automated remediation").
- **Missing:** verify against the current IEEE Access keyword list (not checked here).

### Section 4 — Introduction

- **Objective:** motivate the attribution-versus-abstention trade-off; state contributions as (1) empirical limits study, (2) conservative framework, (3) reproducible protocol infrastructure; state scope limits up front.
- **Evidence available:** S43 §1 (failure of V2 to beat AA), S44 §2 (root causes of failure), closure doc §1–§3 (validity issues).
- **Repository artifacts:** `SPRINT4_3_0_FINAL_REPORT.md`, `SPRINT4_4_0_FINAL_REPORT.md`, `FINAL_SCIENTIFIC_VALIDITY_CLOSURE.md`.
- **Reportable quantitative results:** at most the headline: 58% of held-out scenarios require abstention (63/108) and a trivial policy scores P2 = 0.583.
- **Supported claims:** the problem (naming a descendant as the root; unsafe confident answers) is real *in the simulator*; abstention-aware metrics are necessary because a trivial abstainer is strong on prevalence-skewed benchmarks.
- **Must NOT claim:** that RIFT solves RCA; that the benchmark represents production incidents.
- **Missing:** literature positioning (Section 5); a motivating real-incident statistic (none collected). Do not invent one.

### Section 5 — Related Work

- **Objective:** position against observational RCA, causal-discovery-based RCA, intervention/chaos-based RCA, selective prediction/abstention.
- **Evidence available:** `docs/RELATED_WORK.md` exists (listed; **contents not read for this blueprint**); baselines implemented as MicroRCA-/Sieve-style analogues (B3-SIEVE-LIKE, B1-LATENCY-CORR). B4-SAGE-CHAOS was excluded as a stub (S43 §6).
- **Repository artifacts:** `docs/RELATED_WORK.md`, `src/rift/baselines/`.
- **Reportable quantitative results:** none.
- **Supported claims:** only what the cited literature supports; baselines are *"-like" re-implementations*, not the published systems.
- **Must NOT claim:** head-to-head comparison against published systems (none was run).
- **Missing:** a verified bibliography (no citation list was verified); any citation must be checked against the source. Do not generate references from memory.

### Section 6 — Problem Formulation

- **Objective:** define scenario, observation window, candidate set, ATTRIBUTE vs ABSTAIN_REQUIRED labels, strict "unsafe" definition, and the utility.
- **Evidence available:** definitions in S43 §6, S44 §3, `FINAL_SCIENTIFIC_VALIDITY_CLOSURE.md` §1.1 (label cascade), §4.1 (utility).
- **Repository artifacts:** `src/rift/scenarios/generator_v2.py` (`compute_ground_truth`, lines 390–453), `src/rift/scenarios/simulator.py`, `src/rift/evaluation/benchmark_v2.py` (`score_one`), `docs/EVALUATION_PROTOCOL_V2.md`.
- **Reportable quantitative results:** utility `U = C − 2.0·S − 1.0·(n_do/20)`, δ = 0.10; per-scenario range [−3, 1]; mean ceiling π ≈ 0.393.
- **Supported claims:** labels come from noise-free simulator state and never from a method output (no method-output leakage; closure doc §1.1/§1.5).
- **Must NOT claim:** that labels are independent of RIFT's detection vocabulary. They are **partially circular, definitionally**: θ = 3.0 with persistence 2 mirrors EBD R1; the 4.0σ gate sits one σ above it; 49 of 99 dev/val ATTRIBUTE labels rest solely on the R1-identical temporal rule. "WEAK_SIGNAL" is a normative abstain-required class, not a causal fact. Utility weights are normative.
- **Missing:** D23 decision (structural label L-struct plus SNR covariates) is **proposed, not approved** (`FINAL_APPROVAL_MATRIX.md`). Without it, the manuscript must word results as "relative to the simulator's identifiability rule".

### Section 7 — RIFT Architecture

- **Objective:** describe the pipeline: EBD → FCI/PAG → CID → MSIS → abstention/attribution; distinguish V2 and V3.
- **Evidence available:** S43 §3, S44 §2/§4, V3 design doc.
- **Repository artifacts:** `src/rift/ebd/ebd.py` (EBD, R1 θ_detect = 3.0, persistence 2); `src/rift/fci/fci_runner.py` (FCI/PAG; **frozen decoder defect D1**: `o->` mis-decoded); `src/rift/cid/cid.py`, `src/rift/cid/evidence.py` (CID, Wasserstein-1 + permutation test); `src/rift/optimizer/cost_model.py` (greedy approximation to MSIS, `MSISResult`); `src/rift/evaluation/rift_v2.py` (V2, frozen); `src/rift/attribution_v3/rift_v3.py` (V3); `docs/SPRINT4_4_0_V3_DESIGN.md`.
- **Reportable quantitative results:** V3 uses ~1.7–1.9× more interventions than V2 (2.51 vs 1.49 dev, 3.19 vs 1.71 val per scenario; pooled 2.706 vs 1.556, max 8 vs 6).
- **Supported claims:** V3 adds graph-agnostic candidates, positive control, Holm correction, symmetry check, source rule, earlier-divergence guard, explicit statuses. MSIS in the code is a **greedy approximation**, not an exact minimum.
- **Must NOT claim:** "identifiability guarantees"; that PAG edges or reachability indicate causal ancestry (97–98% of learned edges are circle-marked); `DEFINITIVE_ROOT` is definitive (about 50% unsafe, S44 §4); that MSIS is optimal.
- **Missing:** a single architecture figure verified against code; V2-versus-V3 component diff table; MSIS has no isolated held-out evaluation (ablation A7-NO-MSIS showed no significant effect in dev/val/held-out except cost direction at held-out, S43 §10, exploratory).

### Section 8 — Intervention-Grounded Attribution Methodology

- **Objective:** specify exactly how an answer or an abstention is produced, including CID, `do()` window, candidate rules R1–R4, statuses, error semantics.
- **Evidence available:** S43 §3/§6, S44 §2/§7, CID design doc, SAP §7.
- **Repository artifacts:** `src/rift/attribution_v3/rift_v3.py`, `src/rift/cid/`, `docs/SPRINT4_4_0_CID_EVIDENCE_ANALYSIS.md`, `docs/SPRINT4_5_0_CID_EXPERIMENT_DESIGN.md`, `src/rift/evaluation/benchmark_v2.py` (`_timed`, `METHOD_ERROR`, `TIMEOUT_S = 60`).
- **Reportable quantitative results:** every recorded CID check is grade CANDIDATE (555/555 dev, 314/314 val, 531/531 V2 held-out); n = 30 per arm; RELIABLE needs n ≥ 50. CID sensitivity for true-ancestor pairs ~10% below 0.25σ, ~49% at 0.5–1σ, ≥ 87% at ≥ 1σ; Monte-Carlo power at 0.5σ ~49% (m = 1) and ~29% (m = 3).
- **Supported claims:** intervention evidence is "intervention-consistent" **in the simulator's sense**; the simulated `do()` has no concurrent control arm.
- **Must NOT claim:** CID confirms causation; CID has defensible operating conditions (Phase A **not run**; `src/rift/cid_reliability/` does not exist). Drift: E0 flagged 94% (dev) and 100% (val) of non-ancestral pairs whose outcome has own-drift > 0.3σ vs 5.6%/6.7% for clean pairs, on a 17-pair stratum per split — **exploratory**, quoted, not re-derived.
- **Missing:** CID Phase A results (seven-estimator comparison E0–E6, plus E7 placebo) — **NOT YET RUN**. Without them the paper may describe CID's weakness but must not claim any estimator has defensible operating conditions.

### Section 9 — Experimental Design

- **Objective:** describe the evaluation protocol history and the preregistered confirmatory design.
- **Evidence available:** S43 §2/§6/§12 (frozen one-shot held-out protocol), S44 (dev/val only), SPRINT4_5_1 final report (preregistration, gates G0–G6).
- **Repository artifacts:** `docs/EVALUATION_PROTOCOL_V2.md`, `docs/SPRINT4_5_0_PREREGISTRATION.md`, `..._STATISTICAL_ANALYSIS_PLAN.md`, `..._DATASET_PROTOCOL.md`, `..._EXECUTION_PLAN.md`, `artifacts/sprint4_5_0/prereg/freeze_manifest.json`.
- **Reportable quantitative results:** hypotheses H1–H4 (H1 gatekeeping at one-sided α = 0.025, Holm over H2–H4); primary utility and δ = 0.10; primary baseline always-abstain. Held-out opened once at 2026-11-03T04:06:00Z after a 37-file freeze.
- **Supported claims:** the Sprint 4.3 protocol was frozen and followed; Sprint 4.4 touched only dev/val; Sprint 4.5 is a *preregistration that has not been recorded* (no `prereg.sha256`, no `decisions.json`).
- **Must NOT claim:** that a confirmatory test was run, that the preregistration is final, or that it is independently reviewed. The protocol is "corrected, internally consistent and committed, but NOT fully approved" (SPRINT4_5_1 §0); 0 of 49 matrix rows approved by anyone; D7 and D12 are open blockers.
- **Missing:** G0–G6 completion; the confirmatory runner and analysis script (do not exist); D7 reviewer name.

### Section 10 — Dataset Construction

- **Objective:** describe dev/val/held-out (Sprint 4.3) and the planned confirmatory dataset; explain independence checks.
- **Evidence available:** S43 §4–§5; SPRINT4_5_1 §5; infrastructure plan §1–§2.
- **Repository artifacts:** `datasets/rift_v2/{dev,val}.json` (committed; held-out candidate sealed — do not open), `src/rift/scenarios/{generator_v2,independence,duplicates,fingerprint,splitter}.py`, `docs/SPRINT4_3_0_DATASET_PROVENANCE_AUDIT.md`, `SPRINT4_3_0_SCENARIO_DIVERSITY_REPORT.md`, `docs/CONFIRMATORY_INFRASTRUCTURE_PLAN.md`.
- **Reportable quantitative results:** 360 scenarios (dev 180 / val 72 / held-out 108); 0 cross-split leaks on content, dynamics, topology, template and joint cell; 0 near-duplicate pairs ≥ 0.90; 35 groups, 0 integrity violations; outcome mix dev 68/112, val 31/41, held-out 45/63 (ATTRIBUTE/ABSTAIN). Planned confirmatory: ~2000 scenarios, 16 fixed structures × 16 fixed fault families = 256 template groups, 40% ATTRIBUTE; quota matrix sums to 2000 with the S13/S14 exception (90 SYMMETRIC each).
- **Supported claims:** independence is established on content hashes and design keys, not seeds; shared marginals (workload, observability, temporal pattern, intervention mode) mean the held-out does **not** test distribution shift on those axes.
- **Must NOT claim:** diversity = realism; the confirmatory dataset exists (it does **not**; `artifacts/sprint4_5_0/confirm/` does not exist; the generator `generator_confirm.py` is **missing**); the frozen generator can produce it (`build_scenario("confirm", …)` raises `KeyError`); 2000 independent observations; generalisation to unseen structures.
- **Missing:** the new generator, acceptance sampler, node-order randomisation test T10 (root was first in 489/489 prototype and 99/99 dev+val attributable scenarios: a generator-side leak), S13/S14 quota enforcement test, dataset manifest, D23 label-structural fields (if adopted).

### Section 11 — Baselines and Ablations

- **Objective:** define comparators and ablations and justify always-abstain as a primary baseline.
- **Evidence available:** S43 §6/§9; S44 §3; UV decomposition.
- **Repository artifacts:** `src/rift/baselines/`, `src/rift/evaluation/benchmark_v2.py` (13 registry entries, A1–A10), `src/rift/evaluation/rift_v2.py`.
- **Reportable quantitative results:** held-out baselines R5–R7; ablations (held-out, exploratory, uncorrected): A3-NO-EBD P2 −0.139 and not-unsafe −0.157 vs V2 (the clearest loss); A6/A8 (no interventions) P1 equal to V2 (0.444), P2 within 0.02, lower unsafe, lower coverage; A9 (oracle graph) P1 +0.267. Pooled dev/val unsafe counts: B0-EARLIEST 188, B0-HIGHEST 220, B1 199, B3 190, B5 141, B6/B7 170, legacy 114, V2 79, V3 48, of 252.
- **Supported claims:** observational variants are competitive with interventional ones on these data; the interventional component shows **no demonstrated benefit** (H4 unsupported; H5 mixed). FCI isolating the true root is the demonstrated bottleneck (oracle graph).
- **Must NOT claim:** that interventions help; that any ablation difference is confirmed (all uncorrected, exploratory); that B3/B1 are the published systems; superiority over always-abstain.
- **Missing:** a coverage-matched baseline and set-level multi-root metrics were recommended in S43 §15 but are not in the preregistered set per documents read; confirm against the preregistration before claiming "baselines are sufficient". Always-abstain on held-out is post-hoc (R4); on the confirmatory design it is preregistered as primary.

### Section 12 — Statistical Analysis

- **Objective:** describe the planned inference and its dependence structure honestly; separate what was done (Sprint 4.3/4.4/4.5.1) from what is planned.
- **Evidence available:** S43 §8; S44 §3; closure doc §2; `artifacts/sprint4_5_1/power/*.json`; UV.
- **Repository artifacts:** `src/rift/evaluation/stats_v2.py`, `artifacts/sprint4_5_1/power/{stratified_power,family_block_power,power_results,power_mc_verify}.json`, `scripts/sprint451_{utility_sensitivity,stratified_power,family_block_power}.py`, SAP.
- **Reportable quantitative results:** Sprint 4.3: exact McNemar, sign-flip permutation (10,000), scenario- and template-clustered bootstrap (B = 2000, 71 templates), Wilson CIs, Holm over 24 tests. Planned: stratified group bootstrap-t (seed 4505, B = 20,000), family-block sensitivity (seed 4506). Dev/val dependence: template ICC −0.049 (K = 105), union-find group ICC −0.054 (K = 21), family-after-structure ICC +0.016 (K = 15); all imprecise; **not** used to shrink the planning DEFF (2.0; stress 3.0). Monte-Carlo (non-confirmatory, one-sided α = 0.025, μ = +0.10, N = 2000): template-level rule ignoring a real family effect has size 0.046–0.202; family-block bootstrap controls size (≤ 0.0375 in the cells read) but power is 0.30–0.59 under a real crossed family effect. Random-structures reading (not adopted): MDE 0.184–0.245 independent of N.
- **Supported claims:** the negative conclusion (V3 mean U below 0) is defensible under both clusterings (R23/R26); a positive claim requires the family-block interval also to exclude 0; a null in the positive direction is **not** equivalence.
- **Must NOT claim:** 2000 independent observations; effective sample size; generalisation to unseen structures or families; that increasing N repairs structural dependence; that dev/val p-values are confirmatory; that borderline uncorrected p-values survive correction (P2 V3 vs V2, p ≈ 0.049 on both splits, does not: Holm 0.195).
- **Missing:** the analysis script `sprint450_analyze.py` (does not exist) implementing both bootstraps; D19 approval; the first-paragraph rule (report both intervals) is a *proposal* in the closure doc, not yet adopted. The headline CI "[−0.465, −0.219]" in the SAP differs slightly from the recomputed template intervals (accepted by UV within 0.012; procedure not traced).

### Section 13 — Results

- **Objective:** report only verified results, grouped by evidence category, with the always-abstain row in every main table.
- **Evidence available:** §1 table of this blueprint.
- **Repository artifacts:** `artifacts/sprint4_3_0/results/held_out/statistics.json` (not read here), `artifacts/sprint4_4_0/{v3_dev,v3_val,analysis,cid_audit}.json` (not re-read here), `artifacts/sprint4_5_1/utility/utility_verification.json` (read).
- **Reportable quantitative results:** R1–R30. Required presentation: separate sub-sections or panels for (a) held-out (V2 only), (b) development/validation (V2 vs V3), (c) pooled utility, (d) adversarial, (e) oracle. Confirmatory sub-section: "No confirmatory results are reported" unless R31 is later filled by the preregistered analysis.
- **Supported claims:** V3 − V2 positive on dev/val for safety (P3_safe significant on val after Holm, 0.0155; dev Holm 0.0575 is not); P1 gains not significant; P2 gains do not survive Holm; V3 and V2 are indistinguishable from or below always-abstain on P2 in every comparison available.
- **Must NOT claim:** RIFT beats always-abstain; V3 outperforms V2 in accuracy; V3 is "safe" (19% / 18% unsafe vs 0 for AA; 48 of 252 unsafe); results transfer to the held-out (V3 never run there).
- **Missing:** the confirmatory table (**NOT YET RUN**). Do not fill with dev/val numbers.

### Section 14 — Failure Analysis

- **Objective:** make the failure taxonomy a central result.
- **Evidence available:** S43 §11 and failure taxonomy; S44 §2/§6; UV decomposition.
- **Repository artifacts:** `docs/SPRINT4_3_0_FAILURE_TAXONOMY.md`, `docs/SPRINT4_4_0_ATTRIBUTION_FAILURE_ANALYSIS.md`, `docs/SPRINT4_4_0_FCI_GRAPH_QUALITY.md`, `docs/SPRINT4_4_0_CAUSAL_DIRECTIONALITY.md`, `docs/SPRINT4_4_0_CID_EVIDENCE_ANALYSIS.md`.
- **Reportable quantitative results:** V2 held-out: of 45 ATTRIBUTE scenarios, 34 answered (20 correct, 14 wrong), 11 abstained; all 14 wrong roots were downstream descendants reached by SEMI_DIRECTED paths; 23/63 unsafe on ABSTAIN_REQUIRED (WEAK_SIGNAL 12, SYMMETRIC 6, ROOT_UNOBSERVED 3, NO_DISCRIMINATING_EVIDENCE 2). Dev/val: FCI isolates the true root in 8/14 (dev) and 5/13 (val) wrong cases. FCI skeleton precision 0.675 / 0.622, recall 0.424 / 0.355, F1 0.52 / 0.45; 97.8% / 97.0% of edges circle-marked; 1 / 2 fully directed. Defect D1 (collider `X→Z←Y` mis-decoded). V3 pooled: "lucky" right-service answers on ABSTAIN_REQUIRED 18 (V2 25). Unobserved-root adversarial type: 7/7 unsafe for V3 (identifiability boundary). Lucky-by-reason for V3: WEAK_SIGNAL 14, NO_DISCRIMINATING_EVIDENCE 4.
- **Supported claims:** the dominant failure is naming a descendant; the graph is a bottleneck (A9); much of V3's safety gain is increased abstention (coverage 80 → 67 dev, 35 → 26 val); CID is under-powered and has no concurrent control.
- **Must NOT claim:** the failure mechanisms are validated beyond the simulator; "we did not determine why" items (FCI orientation) were explained.
- **Missing:** none required; optional per-structure analysis is descriptive only (cells have 3–11 scenarios; no subgroup claim is supported).

### Section 15 — Threats to Validity

- **Objective:** a complete, specific threats list.
- **Evidence available:** SPRINT4_5_1 §12; closure doc §1–§5; S43 §13; S44 §8.
- **Repository artifacts:** `docs/FINAL_SCIENTIFIC_VALIDITY_CLOSURE.md`, `docs/SPRINT4_5_0_FINAL_PREREGISTRATION_AUDIT.md`, `docs/FINAL_APPROVAL_MATRIX.md`.
- **Reportable quantitative results:** label-gate sensitivity on dev/val (diagnostic only; labels not changed): moving the SNR gate to 3.0 flips 29 ABSTAIN → ATTRIBUTE; 3.5: 12; 4.5: 8 ATTRIBUTE → ABSTAIN; 5.0: 15. 45 of 252 scenarios (18%) lie within one σ of the 4.0 gate. Break-even λ\* = 0.9375 (κ = 0).
- **Supported claims (list each):** (1) definitional label circularity; (2) crossed and hierarchical dependence with only 16 families; (3) fixed structural scope; (4) CID temporal confounding with Phase A unrun; (5) synthetic-only evaluation from one self-authored simulator; (6) partial observability by design; (7) low attribution coverage; (8) always-abstain baseline strength; (9) normative utility weights; (10) reproducibility limits (single platform, 14 transitive pin differences, 663 vs 664 unexplained, 27 tests not run for held-out parse risk, D12 open); (11) no real production telemetry; (12) internal (AI) review only; (13) researcher degrees of freedom: V3 designed on dev; adversarial set authored after seeing dev failures; designed stress set with S10–S14 variants of dev/val motifs; the 0.88 similarity threshold is a proxy.
- **Must NOT claim:** any threat is "resolved" that is only disclosed; that independent review has occurred.
- **Missing:** none for disclosure; D23 outcome changes how threat (1) is worded.

### Section 16 — Limitations

- **Objective:** state limits plainly and separately from threats.
- **Evidence available:** S43 §13; `docs/REMAINING_LIMITATIONS.md` (headings only read); closure doc §5 classification.
- **Repository artifacts:** as Section 15 plus `docs/REMAINING_LIMITATIONS.md`.
- **Reportable quantitative results:** held-out has only 4 no-fault scenarios (FPR 2/4, extremely imprecise); 71 held-out templates; per-stratum n mostly < 15; single deterministic draw, no run-to-run variance; V3 `DEFINITIVE_ROOT` about 50% unsafe.
- **Supported claims:** results hold for the 16 preregistered motifs under the preregistered simulator only; intervention fidelity is a simulator assumption; recovery time (30 s) is a model constant.
- **Must NOT claim:** external validity; production readiness; that the Stage 4 live-experiment findings (historical, separate) are confirmed or refuted by this work.
- **Missing:** whether `REMAINING_LIMITATIONS.md` §1–§3 (FCI sample density, testbed scope, leaf-service boundary, Linux-VM blockers) are consistent with the current work (not read in full).

### Section 17 — Discussion

- **Objective:** interpret honestly: what the evidence says about attribution under partial observability, what abstention buys, what interventions did and did not add.
- **Evidence available:** S43 §14, S44 §4/§8, closure doc §1.7/§4.
- **Repository artifacts:** as above.
- **Reportable quantitative results:** break-even λ\* ≈ 0.94 at κ = 0 (V3 − AA CI > 0 only for λ ≤ 0.61); zero-unsafe V3 +0.043 < δ; V3 − V2 +0.224.
- **Supported claims:** a trivial abstainer is hard to beat when ~60% of cases require abstention and unsafe answers are penalised at λ = 2; V3 is a better-behaved rule than V2; the value of an unsafe-versus-intervention trade-off is unmeasured and depends on operational costs not supplied here; benchmarks for RCA should always report an abstain-everything row.
- **Must NOT claim:** that intervention cost is "worth it"; that the conclusion is robust to the weights (it flips at low λ); that circularity does not matter (the V3 − AA sign does not hinge on the 30-scenario boundary band, per closure arithmetic, but V3 − V2 and the penalty size are more label-sensitive).
- **Missing:** a defended recommendation on deployment (none supportable).

### Section 18 — Conclusion

- **Objective:** one paragraph, scoped.
- **Evidence available:** all above.
- **Repository artifacts:** n/a.
- **Reportable quantitative results:** at most one or two headline numbers with category labels.
- **Supported claims:** RIFT-FULL-V3 is a conservative intervention-grounded framework whose gains over V2 are in safety, not accuracy; on synthetic evidence it is not shown to beat always-abstain; limits of attribution are documented; a preregistered confirmatory protocol exists but its data do not.
- **Must NOT claim:** success, validation, deployment readiness, or a confirmatory outcome.
- **Missing:** the confirmatory outcome, if run.

### Section 19 — References

- **Objective:** a verified bibliography.
- **Evidence available:** `docs/RELATED_WORK.md` (not read in full here).
- **Repository artifacts:** `docs/RELATED_WORK.md`.
- **Reportable quantitative results:** none.
- **Supported claims:** only references that have been checked against the source.
- **Must NOT claim:** any reference not verified; no auto-generated citations.
- **Missing:** the entire verified reference list (FCI, causal-learn, Wasserstein distance and permutation tests, selective prediction/abstention, microservice RCA works, bootstrap-t / cluster inference, Holm). To be collected by the authors.

---

## 3. Pre-submission checklist (blueprint-level; none is done)

| Item | Status |
|---|---|
| D7 independent *human* reviewer named and review completed | **OPEN** (blocker); an AI review (Bob) cannot satisfy it |
| D12 owner-run protected verification on the full tree | **OPEN** (blocker); 27 tests were deliberately not run |
| D23 label decision (adopt / reject) | **OPEN**; must precede generator implementation |
| Confirmatory generator, runner, analysis script | **MISSING** |
| Confirmatory data (R31) | **NOT YET RUN** |
| CID Phase A (`src/rift/cid_reliability/`) | **MISSING / NOT RUN**; blocks any CID-validity claim, not Phase B generation |
| GitHub CI result for the `requests` / protected-handling fix (N1) | Verified locally in a clean Python 3.11 clone; **not read on GitHub**; do not claim green |
| Verified bibliography | **MISSING** |
| Reconciliation or retirement of `docs/IEEE_PAPER_DRAFT.md` legacy claims | **OPEN** |

## 4. Open questions for the authors

1. Is the paper to be submitted before or after the preregistered confirmatory experiment? The blueprint supports the former only as an honest negative-results / limits paper (dev/val + one-shot V2 held-out), clearly labelled non-confirmatory for V3.
2. Is D23 adopted? This changes Sections 6, 10, 12 and 15.
3. Which results are central? Suggested: (i) the failure analysis (Section 14), (ii) the always-abstain finding (R4, R13, R16), (iii) the V3-versus-V2 safety shift with its abstention explanation, (iv) the utility break-even analysis (R29).
