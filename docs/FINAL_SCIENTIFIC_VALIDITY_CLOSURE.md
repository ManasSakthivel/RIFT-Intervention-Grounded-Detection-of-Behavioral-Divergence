# RIFT — Final Scientific Validity Closure (Part 3)

**Status: ANALYSIS DOCUMENT. It changes no label, threshold, utility definition, preregistered endpoint or frozen artifact.** It generates no confirmatory data and opens no sealed held-out material. Every proposal below that would alter the preregistered design is a *proposal requiring researcher approval and independent human review*; nothing here is an approval.

**Evidence tags** (used on every quantitative statement):
`[DEV]` dev split · `[VAL]` validation split · `[DEV+VAL]` pooled N = 252 (non-confirmatory) · `[HELD-OUT-V2]` Sprint 4.3 held-out (not re-opened here) · `[ADVERSARIAL-DEV]` synthetic stress tests · `[SIM-POWER]` Monte-Carlo size/power simulation (non-confirmatory) · `[DESIGN]` a property of a document or of code, not a measured result.

**There are no confirmatory results.** The preregistration has not been recorded: `artifacts/sprint4_5_0/prereg/` contains only `freeze_manifest.json` (gate G3 not passed). All empirical numbers below are dev/val, simulation, or design arithmetic.

**Numbers I did not independently re-derive** (quoted from documents, flagged where used): "V3 answers 37 % of SNR ∈ [3,4) scenarios, mean U −0.87" and "WEAK_SIGNAL contributes −0.166 of V3's −0.338" (source: `docs/SPRINT4_5_0_DATASET_PROTOCOL.md` §5.5 and `docs/SPRINT4_5_0_PREREGISTRATION.md` L2; not recomputed in this document); the CID-audit rates 94 %/100 %/5.6 %/6.7 %, 103/110, 64/69 (source: `docs/SPRINT4_5_0_PREREGISTRATION.md` line 35, citing `artifacts/sprint4_4_0/cid_audit.json`; that JSON was not re-read here).

---

## 1. Ground-truth label circularity (task item 3.1)

### 1.1 How labels are actually generated  `[DESIGN]`

Source: `src/rift/scenarios/generator_v2.py`, `compute_ground_truth` (lines 390–453); `src/rift/scenarios/simulator.py`, `detectable_onset_window` (lines 246–250).

The docstring says: *"Label from noise-free simulator state; never from any method."* That is accurate: the function reads `design.true_roots`, `observed_services(sc)`, the graph, the telemetry configuration, the intervention block and `apparent_signal(sc, s)` (the noise-free fault contribution divided by σ). **No method output is an input. There is no method-output leakage.**

Decision cascade (first match wins):

| step | condition (code) | label |
|---|---|---|
| 1 | no true roots | ABSTAIN_REQUIRED / NO_FAULT |
| 2 | no true root is in the observed set | ABSTAIN_REQUIRED / ROOT_UNOBSERVED |
| 3 | `dims["structure"] == "ambiguous"` | ABSTAIN_REQUIRED / SYMMETRIC_MUTUAL_DEPENDENCY |
| 4 | `n_win < REF_WINDOWS + 8`, or observability/negative level = insufficient | ABSTAIN_REQUIRED / INSUFFICIENT_BASELINE |
| 5 | per observed root r: **noise-free `max|z_r| ≥ 4.0`** *and* `detectable_onset_window(z_r)` not `None` (θ = 3.0, two consecutive windows) *and* (TEMPORAL: every other detectable service has a strictly later onset, *or* INTERVENTIONAL: some descendant d with `30 + delay + 2·lag/Δt ≤ 45` s and expected effect `magnitude_σ · σ_r · delivered · Σpath-gain / σ_d ≥ 1.0`) | ATTRIBUTE |
| 6 | otherwise: if every observed root has `max|z| < 4.0` → WEAK_SIGNAL, else NO_DISCRIMINATING_EVIDENCE | ABSTAIN_REQUIRED |

Steps 1–4 are structural facts about the simulated world (fault present, root observed, symmetric structure, enough baseline). Steps 5–6 are where thresholds enter.

### 1.2 Dependence on RIFT's own constants  `[DESIGN]`

| label constant | value in `compute_ground_truth` | RIFT constant it mirrors | source of the RIFT constant |
|---|---|---|---|
| onset detector θ, persistence | `detectable_onset_window(theta=3.0)`, 2 consecutive windows (`simulator.py:246`) | EBD R1 `theta_detect = 3.0`, `theta_persist = 2` | `src/rift/attribution_v3/rift_v3.py:26,146`; `src/rift/evaluation/rift_v2.py:185` |
| SNR gate | `snr < 4.0` (`generator_v2.py:424`), and `< 4.0` again for WEAK_SIGNAL (`:451`) | sits 1.0 σ above the 3.0 σ detector; not itself a RIFT constant | — |
| INTERVENTIONAL expected-effect threshold | `≥ 1.0` σ | CID power criterion (design reasoning: 0.49/0.82/0.95 power at 0.5/0.75/1.0 σ, n = 30 — a 150-draw pilot per `docs/SPRINT4_5_0_CID_EXPERIMENT_DESIGN.md` §4.2) | CID design doc |
| timing cut | `30 + delay + 2·lag/Δt ≤ 45` s | 30 s `do()` window | V3 design |
| TEMPORAL rule | "root's onset strictly earliest among detectable services" | EBD earliest-divergence logic | `src/rift/ebd/ebd.py` |

Consequence: the label's *definition of identifiable* is built from the same detection vocabulary (3σ, persistence 2, 30 s do()) that RIFT uses to *decide*. The preregistration already records this as limitation L2 (`docs/SPRINT4_5_0_PREREGISTRATION.md` line 286).

### 1.3 Audit on dev+val (diagnostic; **not relabelling**)  `[DEV+VAL]`

Source: `artifacts/final_closure/label_circularity_audit.json` (N = 252, dev/val only; never touches held-out).

| quantity | value |
|---|---|
| ATTRIBUTE | 99 (84 with root SNR ≥ 5; 15 in [4, 5); minimum 4.0) |
| WEAK_SIGNAL | 46 (**30** with SNR ∈ [3, 4); **16** with SNR < 3, never reach the 3σ detector) |
| NO_DISCRIMINATING_EVIDENCE | 18 (all SNR ≥ 5) |
| other ABSTAIN_REQUIRED | ROOT_UNOBSERVED 31, INSUFFICIENT_BASELINE 23, SYMMETRIC_MUTUAL_DEPENDENCY 22, NO_FAULT 13 |
| ATTRIBUTE evidence kind | TEMPORAL-only 49; INTERVENTIONAL-only 17; both 33 |
| ATTRIBUTE labels resting only on the TEMPORAL rule that is **identical to RIFT R1** | 49 of 99 |
| label re-derivation | 163/163 stored labels reproduced among the 163 scenarios that reach the SNR gate (99 + 46 + 18 = 163) |

Gate-sensitivity (diagnostic only; labels were **not** changed):

| SNR gate | ABSTAIN → ATTRIBUTE | ATTRIBUTE → ABSTAIN |
|---|---:|---:|
| 3.0 | 29 | 0 |
| 3.5 | 12 | 0 |
| 4.5 | 0 | 8 |
| 5.0 | 0 | 15 |

Note on "30 vs 29": 30 WEAK_SIGNAL scenarios have SNR ∈ [3, 4), but 29 ABSTAIN labels become ATTRIBUTE at gate 3.0. I did not trace which scenarios account for the difference; a plausible reason (inference, not verified) is that `max|z| ≥ 3` does not guarantee the two consecutive windows or an evidence criterion that the label also requires. Either way, "RIFT's 3σ rule can detect these" is a statement about *noise-free* amplitude, not about RIFT's realised behaviour under noise.

Behavioural footprint (quoted, not re-derived): V3 answers 37 % of SNR ∈ [3, 4) scenarios with mean U −0.87, and WEAK_SIGNAL contributes −0.166 of V3's −0.338 (49 %). `[DEV+VAL]`, sources: Dataset Protocol §5.5, PRE L2. Cross-check that is arithmetic only: 0.166 / 0.338 = 0.49. ✔

### 1.4 The five questions

**Q1 — How are labels generated?** Section 1.1: deterministic function of noise-free simulator state; no method output.

**Q2 — Do labels depend on RIFT's internal thresholds?** **Yes, definitionally.** θ = 3.0 with persistence 2 is identical to EBD R1; the 4.0 gate is one σ above that detector; the 1.0 σ / 45 s interventional criterion mirrors CID power and the 30 s do() design. Evidence that this matters in the data: 49/99 ATTRIBUTE labels rest solely on the R1-identical temporal rule; 30 scenarios sit in the SNR gap between RIFT's detector (3) and the label gate (4). `[DEV+VAL]`

**Q3 — Are the concepts distinct?** Partly.

| concept | represented? | where |
|---|---|---|
| causal origin | **Yes, cleanly** | `design.true_roots` (simulator input) |
| observability | **Yes, cleanly** | `observed_services` → ROOT_UNOBSERVED (step 2) |
| structural identifiability | **Yes** | SYMMETRIC (step 3) |
| baseline adequacy | **Yes** | INSUFFICIENT_BASELINE (step 4) |
| detectability | **Yes, but folded into the label**, as a *noise-free amplitude* threshold (SNR ≥ 4) | step 5 |
| identifiability by an evidence route | Yes, via TEMPORAL/INTERVENTIONAL criteria, which carry the 3σ/1σ/45 s constants | step 5 |
| **statistical significance** | **No.** Nothing in the label involves a test, an α, noise or a sampling distribution. The 4.0 gate is a deterministic amplitude threshold on the *noise-free* signal; it is not a significance level and was not derived from one. | — |

So the problem is *not* that the label silently embeds a significance test; it is that a **design choice about how large an amplitude must be** (4.0 σ) and **which evidence routes count** has been written into the label, using constants copied from the method under test.

**Q4 — Does the definition reflect the simulated mechanism independently?** Steps 1–4 do: they are properties of the generator. Steps 5–6 only partly: "fault amplitude relative to noise" is a real mechanistic quantity, but *where to draw the line* (4.0 vs 3.0 vs 5.0) is not given by the mechanism. Sensitivity in 1.3 shows the line moves 8–29 labels (3–12 % of N = 252; arithmetic from the table). `[DEV+VAL]`

**Q5 — Are weak-signal scenarios valid attributable ground truth?** **WEAK_SIGNAL is not "attributable" by definition.** It is a normative *abstain-required* class. The right question is therefore not "is a weak-signal root attributable?" but "**is abstention REQUIRED there?**" That is a **design choice, not a causal fact**: a 3.5 σ signal with a true observed root is, in the simulator, causally attributable in principle; whether a method *should* answer is a risk-appetite decision (it is what the utility weights encode). For the 16 scenarios with SNR < 3 the abstain-required judgement is easy to defend (the signal never crosses the detector noise-free). For the 30 in [3, 4) it is the contested band.

### 1.5 Verdict

> **PARTIALLY CIRCULAR — definitional dependence on RIFT constants; not method-output leakage.**

* Not circular in the leakage sense: labels never read a method output (`generator_v2.py:391`; Dataset Protocol §1 item 3).
* Circular in the definitional sense: the identifiability rule is assembled from RIFT's own detection constants, so "agreement with the labels" partly measures agreement with RIFT's own notion of detectability.

### 1.6 Which scenarios are affected  `[DEV+VAL]`

* Directly threshold-determined: **30** (WEAK_SIGNAL, SNR ∈ [3, 4)) + **15** (ATTRIBUTE, SNR ∈ [4, 5)) = 45 of 252 (18 %) lie within one σ of the 4.0 gate (arithmetic from §1.3).
* Resting only on the R1-identical temporal rule: **49** ATTRIBUTE.
* Not affected by the SNR gate (steps 1–4 of §1.1, which precede it): ROOT_UNOBSERVED 31 + INSUFFICIENT_BASELINE 23 + SYMMETRIC 22 + NO_FAULT 13 = **89** scenarios (arithmetic). The 18 NO_DISCRIMINATING_EVIDENCE all have SNR ≥ 5 and so do not flip at any tested gate, but they do depend on the evidence-route constants (§1.2). Of the 99 ATTRIBUTE, the 84 with SNR ≥ 5 did not flip at any tested gate; the 15 in [4, 5) flip at gate 5.0 (the audit shows 15 flips at 5.0 and 8 at 4.5).
* The held-out set (`[HELD-OUT-V2]`) was **not** audited here (sealed); I make no quantitative claim about it.

### 1.7 What can still be interpreted

* Results are **agreement with a simulator-defined identifiability criterion, relative to that criterion**. They are not agreement with "true attributability".
* **The negative V3-vs-always-abstain result is not created by the circularity alone.** Arithmetic from verified figures (not a new result):
  * Zero-unsafe decomposition: Ū_zero-unsafe = C̄ − γ·c̄ = 0.179 − 0.135 = **+0.043 < δ = 0.10** (SAP §8.6; 45/252 = 0.1786 and `mean_cost_term_V3_gamma1` = 0.1353 in `utility_verification.json`). Even with every unsafe penalty removed V3 does not reach δ. `[DEV+VAL]`
  * If the entire WEAK_SIGNAL contribution (−0.166, quoted) were set to zero, mean U would be −0.338 + 0.166 = **−0.172** — still negative. This is arithmetic on a quoted contribution, **not** an experiment or a relabelling, and it is only an illustration of order of magnitude. `[DEV+VAL]`
* The sign and rough magnitude of the V3 − always-abstain gap therefore do not hinge on the 30-scenario boundary band. The *size* of the penalty and the V3 − V2 comparison are more label-sensitive and should be read as relative to the labelling rule.

### 1.8 Proposed independently defined criterion — **D23 (new; proposal only)**

**The primary frozen label is NOT changed.** No retrospective relabelling of dev, val or held-out. Existing Sprint 4.3 / 4.4 / 4.5.1 results are unchanged.

Proposal: a **two-tier, co-reported sensitivity scheme**, derived from the simulator's causal mechanism and intervention semantics rather than from RIFT's detector:

| tier | definition | role |
|---|---|---|
| **L-struct** (threshold-free) | fault present ∧ ≥ 1 true root observed ∧ not a symmetric mutual-dependency structure ∧ adequate baseline (steps 1–4 of §1.1 only) | binary sensitivity label: "structurally attributable" vs "structurally not" |
| **Detectability covariates** (continuous, *not* folded into any label) | noise-free root SNR (max\|z\|); noise-free expected `do()` effect in σ units for the best descendant; timing margin vs 45 s | design-block fields used for **stratification** (SNR bands, e.g. < 3, [3,4), [4,5), ≥ 5) |

Why this removes the dependency: L-struct uses only facts the simulator already fixes (roots, observability, symmetry, baseline length). Detectability becomes a *measured covariate* reported by stratum, so a reader can see performance as a function of SNR without anyone deciding where "attributable" starts.

What D23 cannot do (stated plainly):
* It does not make the primary endpoint independent; the preregistered U still uses the frozen label.
* A **fully independent label cannot be obtained inside a simulator that the same authors wrote** (inherent limit). Even L-struct reflects the authors' choice of what to simulate and what counts as observable.
* Under L-struct, "WEAK_SIGNAL" scenarios become structurally attributable, so an answer there is not "unsafe" in L-struct terms; this will change the penalty accounting and must be reported as a sensitivity, not as a replacement.

**Required before confirmatory generation** (all preregistration changes; none of this is done):
1. Researcher records a D23 decision (adopt / adopt-with-changes / reject). Currently unrecorded: a search of `docs/` finds no D23.
2. If adopted: the new generator's label-only `design` block gains `label_structural` (L-struct), `root_snr_noisefree`, `expected_do_effect_sigma`, `timing_margin_s`. These are stripped from method-facing records like the rest of `design`.
3. SAP §8 is extended with the L-struct and SNR-band tables (descriptive, uncorrected, cannot change the primary label).
4. The independent human reviewer (D7) checks the D23 fields and the stripping of them (test T8).
5. All of this is hashed at G3 together with PRE/SAP/protocol; the preregistration is not yet recorded, so the window to add D23 is still open.

**If the researcher or reviewer rejects D23:** the conclusion must be worded as *relative to the simulator's identifiability rule*, and label circularity remains a **disclosed limitation** (PRE L2). Nothing else changes.

**Does this require redesigning the experiment?** No. It adds fields and a report section. If, however, the reviewer concludes that the primary label itself must change, that **is** an experiment redesign and must happen before generation; I do not recommend it, and I have not tested it.

---

## 2. Statistical dependence and inference (task item 3.2)

### 2.1 The design as written  `[DESIGN]`

Sources: `docs/SPRINT4_5_0_STATISTICAL_ANALYSIS_PLAN.md` §1, §3, §3.1, §6.7; `docs/SPRINT4_5_0_DATASET_PROTOCOL.md`.

* 16 fixed structural motifs (S01–S16) × 16 fixed fault families = 256 templates ("groups"), N ≈ 2000, 5–9 scenarios per group, max 14.
* Estimand θ = Σ_s W_s μ_s over **the 16 motifs**; claim restricted to those motifs crossed with those 16 families. **No claim about unseen structures, families or production.**
* Primary inference: stratified template-level group bootstrap-t, B = 20 000, seed 4505. Mandatory sensitivity: family-block bootstrap (resampling unit = fault-family column), seed 4506. If family-block lower bound ≤ 0 while the primary is > 0, the report must say "not robust to family-level dependence" in its first paragraph (SAP §3.1).
* The 256 templates are **not 256 independent clusters**: structures are fixed strata and families are crossed with them (SAP §1). 2,000 scenarios are **not 2,000 independent observations**.

### 2.2 Dev/val dependence estimates (imprecise)  `[DEV+VAL]`

Source: `artifacts/sprint4_5_1/power/stratified_power.json`, block `A_devval_dependence`.

| clustering level | K | ICC | implied DEFF | ICC 95 % bootstrap |
|---|---:|---:|---:|---|
| template | 105 | −0.049 | 0.93 | [−0.223, 0.135] |
| union-find group | 21 | −0.054 | 0.23 | [−0.086, −0.025] |
| family after structure | 15 | **+0.016** | 1.25 | [−0.018, 0.041] |

Between-structure share of variance: 0.072 (SD total 0.969 vs 0.933 within structure; 10 structures in dev/val). With only ~25 scenarios per structure these ICCs are imprecise and, as the SAP says, **are not used to shrink the planning DEFF** (planning DEFF 2.0, stress 3.0 — assumptions, not estimates).

### 2.3 Monte-Carlo size and power  `[SIM-POWER]`

All simulations are non-confirmatory, one-sided α = 0.025, true shift μ = +0.10, N = 2000, marginal distribution of U_V3 from dev/val.

**(a) Template-stratified bootstrap-t, ignoring crossed family effect rf** — `stratified_power.json` (R = 1000, B = 199, seed 4518), 256 groups:

| template ICC rg | rf = 0: size / power | rf = 0.02: size / power | rf = 0.05: size / power |
|---|---|---|---|
| 0 | 0.015 / 0.992 | 0.108 / 0.922 | 0.202 / 0.813 |
| 0.05 | 0.024 / 0.967 | 0.097 / 0.875 | 0.137 / 0.787 |
| 0.10 | 0.019 / 0.942 | 0.070 / 0.830 | 0.152 / 0.740 |
| 0.20 | 0.020 / 0.825 | 0.060 / 0.740 | 0.114 / 0.665 |
| 0.30 | 0.020 / 0.738 | 0.046 / 0.662 | 0.096 / 0.615 |

With a real crossed family effect and the template-level rule, **size is 0.046–0.202 against a nominal 0.025** (anti-conservative).

**(b) Family-block bootstrap-t** — `family_block_power.json` (R = 400, B = 199, seed 4519; Monte-Carlo SE ≈ 0.012):

| rg (within) | rf = 0: family-block size / power | rf = 0.02: size / power | rf = 0.05: size / power |
|---|---|---|---|
| 0 | 0.015 / 0.9825 | 0.0175 / 0.5875 | 0.0175 / 0.2975 |
| 0.05 | 0.015 / 0.91 | 0.0375 / 0.5725 | 0.03 / 0.3625 |
| 0.10 | 0.015 / 0.865 | 0.0175 / 0.5125 | 0.0275 / 0.3475 |
| 0.20 | 0.02 / 0.73 | 0.005 / 0.4675 | 0.02 / 0.30 |

The family-block bootstrap controls size (≤ 0.0375 in every case read above) but, **under a real crossed family effect (rf 0.02–0.05), power for μ = +0.10 is 0.30–0.59.** (Range read directly from the table: min 0.2975, max 0.5875; SAP §6.7(c) states "0.30–0.59".)

**(c) Why the 16-cluster limit cannot be bought off with N**  `[SIM-POWER]`: `stratified_power.json` block `C_random_structure_limitation`: if the 16 motifs were read as a random sample of structures (reading **not adopted**), SE = 0.066–0.088 and the one-sided 80 %-power minimum detectable effect is 0.184–0.245 *independent of N*. Fixed-strata SE with no clustering at N = 2000 is 0.0209.

### 2.4 Is the analysis defensible?

| conclusion type | defensible? | reasoning |
|---|---|---|
| **Negative** (V3 mean U below 0, or not above δ) — the expected outcome | **Yes** | Dev/val V3 − always-abstain: mean **−0.338**; studentised 95 % CI **[−0.472, −0.222]** (template clustering, K = 105) and **[−0.514, −0.203]** (21 union-find groups); percentile CIs [−0.461, −0.217] / [−0.476, −0.202]; bootstrap P(mean > 0) = 0.0 under both. The interval is far from 0 under either clustering. `[DEV+VAL]` — `utility_verification.json` `primary_lambda2_gamma1.strict.V3_minus_AA`. (The docs' headline "[−0.465, −0.219]" differs slightly from both template intervals above; `utility_verification.json` accepts it within a tolerance of 0.012 and records it as verified. I did not trace which procedure produced it.) A negative effect of this size is detectable with ≈ 130 scenarios (SAP §6.5), so the crossed-dependence problem does not threaten it at N = 2000. |
| **Positive** (H1 rejected, V3 useful) | **Only if the family-block interval also excludes 0** | Under a real family effect the template-level rule over-rejects (size up to 0.20) and the family-block rule has power 0.30–0.59. A positive claim resting on the template rule alone is not safe; the SAP already forces the "not robust to family-level dependence" statement. |
| **Null / inconclusive in the positive direction** | **Must not be read as equivalence** | Power is only 0.30–0.59 under a real crossed effect; failure to reject is uninformative about V3 ≈ AA. |

### 2.5 Smallest justified adjustment

* **No change to N. Do not inflate N** — the limiting number is 16 families × 16 structures, not N (SAP §3.1, §6.7(c)).
* **Keep D19 as written** (template-level primary, family-block mandatory sensitivity).
* Add to the reporting rule: the **first paragraph of every report states both intervals** (template-level and family-block) **and the fixed-strata scope** ("16 preregistered motifs × 16 fault families, under the preregistered simulator"). SAP §3.1 requires this only when the two disagree on sign; I recommend always, since a reader needs both numbers (proposal requiring researcher approval).
* **Honest limit:** with 16 families, the crossed dimension has only 16 clusters; family-block CIs will be unstable and conservative. This is inherent and is a disclosed limitation.
* Do not describe 2,000 scenarios as 2,000 independent observations, and do not claim generalisation to unseen structures.

---

## 3. CID temporal confounding (task item 3.3)

Source: `docs/SPRINT4_5_0_CID_EXPERIMENT_DESIGN.md` (Phase A), `artifacts/sprint4_5_1/cid/cell_list.csv`. **Phase A is separate from H1, does not alter V3, and its outputs are not inputs to Phase B** (design doc, line 4).

### 3.1 The estimators  `[DESIGN]`

| id | estimator | target / assumption | identification vs detection |
|---|---|---|---|
| E0 | current CID: 30 s vs 30 s, label permutation | ψ₀ = W₁(F_A⁽⁰⁾, F_B⁽¹⁾); valid only if κ_y = 0 | detection of between-window change |
| E1 | E0 with n ∈ {45, 60, 90} | same ψ₀; trends grow with horizon | detection; *expected to increase* false confirmation when κ_y > 0 |
| E2 | concurrent control replica arm, block permutation | arms exchangeable, no interference | identification under exchangeability |
| E3 | detrended (linear fit on A, extrapolate) | D_y + S linear over A∪B | identification only inside the linear class |
| E4 | difference-in-differences with control service (oracle and data-only) | generalised parallel trends | identification under parallel trends; cannot remove unshared own-drift |
| E5 | AR-aware circular block permutation | stationarity within windows | null calibration only; **no drift correction** |
| E6 | randomised switchback, 10 segments × 15 s, exact 252-assignment randomisation | randomisation executed, no carryover | design-based identification |
| E7 | placebo timing (pre–pre), diagnostic | — | diagnostic, not one of the seven |

Key structure: the design proves ψ₀ is bounded by Δ_y ± κ_y (triangle inequality, §2.1 of the design doc), i.e. **in any consecutive-window design treatment is deterministically confounded with time**; a better test statistic alone cannot separate Δ_y from κ_y. That is the correct framing of the problem.

### 3.2 Do blocks B1–B11 genuinely separate effect from drift?

Null/effect cell counts, recomputed from `cell_list.csv` (218 cells total; matches the design doc: 96 null, 122 alternative; 214 factorial + 4 mixture; 210 distinct DGPs; 468 000 replicates): `[DESIGN]`

| block | what it varies | null (d = 0) | effect (d > 0) |
|---|---|---:|---:|
| B1 | genuine effect, delay, multiplicity | 9 | 45 |
| B2 | independent own-drift of y | 18 | 18 |
| B3 | shared drift with control | 18 | 18 |
| B4 | autocorrelation | 6 | 6 |
| B5 | variance change | 3 | 3 |
| B6 | carryover / recovery instability | 6 | 6 |
| B7 | regression to the mean | 9 | 9 |
| B8 | window-selection artefacts | 10 | 0 |
| B9 | time-varying faults inside windows | 9 | 9 |
| B10 | control-arm exchangeability | 6 | 6 |
| B11 | operating mixtures M₁, M₂ | 2 | 2 |
| total | | 96 | 122 |

Assessment:
* **Yes, in principle.** Every drift block (B2, B3, B9, B10, B11) is crossed with d ∈ {0, 1}, so each drift condition has a matched null cell where any rejection is by construction a false confirmation. This is the structure needed to separate "y changed" from "x changed y". B8 is null-only by design (selection artefacts have no effect arm).
* **Negative controls are meaningful:** NC-sham (every d = 0 cell), NC-outcome (non-descendant y′), NC-exposure (perturb a non-ancestor x′), NC-timing = E7, plus gated rule G(E, NC-exposure) (design doc §3.2). **Positive controls:** B1 d > 0 cells and the V4 power-retention criterion (d = 1σ, delay 0, m = 3, power ≥ E0 − 0.05).
* **Difficult conditions are retained:** B2 own-drift (all six shapes, three magnitudes), B9 time-varying faults, B7 regression to the mean, B6 carryover, B10 imperfect replica.
* **Several estimators are expected to fail in some conditions by design** (design doc §3.4): E0/E1/E5 under any drift; E3 under non-linear drift; E4 under unshared drift (B2, B3 with φ > 0, B10 with λ_rep < 1); E2 under imperfect replica; E0–E5 under carryover and regression to the mean; all but E6 under window-selection. These are *designed-in* limits, stated before any run, and Phase A is a map of operating conditions, not a pass/fail contest for CID.
* **Eligibility is a fixed exact-count rule**, derived from binomial arithmetic only: a factorial null cell is eligible iff k ≤ 138/2000 (p̂ ≤ 0.069); a mixture cell iff k ≤ 557/10 000 (p̂ ≤ 0.0557) (X12; design doc §6). It rejects a calibrated (true size 0.05) estimator with probability 0.0082 over the 96 factorial null cells, and a size-0.06 estimator with probability 0.985. The criteria V1–V7 are not to be changed after results are seen; new estimators require a separately preregistered Phase A′. `[DESIGN]`

### 3.3 Criticisms (honest)

1. **Nothing in Phase A has been run.** `src/rift/cid_reliability/` does not exist, so the V0 gate (byte-level/distributional reproduction of the frozen simulator, high-replicate E0 reference, reproduction of dev/val false-positive rates) cannot have passed. **Eligibility is entirely unknown.** Every statement about which estimator is valid where is currently a prediction (P1–P11), not a finding.
2. **Simulator realism.** The frozen simulator draws i.i.d. noise. Autocorrelation (B4, B7, B10) and variance changes (B5) are introduced by the Phase A DGP and lie outside the dev/val simulator envelope (design doc §10.1 item 11); results there describe a harsher simulated world and make no statement about real telemetry.
3. **E2 and E6 are different experiments, not like-for-like estimators.** E2 needs a second simultaneous system arm; E6 needs 150 s of observation (5× E0's exposure) and a fast reversible perturbation. Replicates are *not* paired with E0 (only E0, E3, E4, E5, E7 are). The design says they must never be ranked as if equal (design doc §7).
4. **E4-oracle uses ground-truth non-descendants** — a privileged upper bound; E4-data-only uses the V3 skeleton, which may itself be wrong.
5. **Supporting dev/val evidence is exploratory and the drift stratum is small.** E0 flagged 94 % (dev) and 100 % (val) of non-ancestral pairs whose outcome has own-drift > 0.3 σ, versus 5.6 % and 6.7 % for clean pairs (V2 trace pair set, only 17 pairs per split from 10 dev and 6 val scenarios); on V3's own pair set 103/110 (94 %, dev; 18 scenarios) and 64/69 (93 %, val; 10 scenarios) versus 5.6 % and 3.9 %. `[DEV]` `[VAL]` (quoted from PRE line 35; not re-derived here.) The entire V3 trace drift stratum is 28 scenarios and entangled with oscillation/intermittent faults.
6. **Pilot power numbers used as anchors are weak:** the 0.49/0.82/0.95 figures come from a 150-draw pilot (SE up to ≈ 0.04); the design therefore does not use them as V0 targets (design doc §4.2). `[DESIGN]`

### 3.4 Verdict

> The design **is capable in principle** of distinguishing intervention effects from background drift (E4, E6 and E2 with explicit, tested assumptions; matched null cells; negative and positive controls; hard conditions retained; eligibility rule fixed in advance).
> **Currently there is zero executed evidence.** CID's defensible operating conditions (a stationary outcome, or a declared domain) are a **hypothesis until Phase A runs**. Phase A does not alter frozen V3 and is separate from H1.

The dev/val rates in 3.3(5) support an exploratory concern that E0 confounds drift with effect; they do not demonstrate it at confirmatory strength.

---

## 4. Utility and baselines (task item 3.4)

### 4.1 Preserved definitions (unchanged)

* **U = C − 2.0·S − 1.0·(n_do/20)** (λ = 2.0, γ = 1.0 ≡ κ = 0.05 per do()); **δ = 0.10**; always-abstain (U_AA ≡ 0) retained as a primary baseline. Strict unsafe (`score_one`) is primary; operational unsafe is a sensitivity (SAP §9.3). `[DESIGN]`
* **The utility weights are normative researcher judgements, not empirically calibrated constants** (`docs/SPRINT4_5_1_FINAL_REPORT.md` line 25). λ = 2 states that one unsafe attribution is as bad as two missed correct ones; it was not estimated from any operational cost data. The (λ, κ) grid (SAP §9.1) is a sensitivity analysis, not a justification.
* Per-scenario U ∈ [−(λ+γ), 1] = **[−3, 1]**; 1 only for a correct answer with 0 do(); the claim "U ∈ [0, 1]" is false (`utility_verification.json` `per_scenario_bounds`). The **mean** is bounded above by prevalence π: pooled π = 0.3929 (dev 0.3778, val 0.4306). δ/ceiling = 0.2545. `[DEV+VAL]`
* Observed per-scenario U range for V3 at (λ=2, κ=0.05): min −2.4, max 0.9. `[DEV+VAL]`

### 4.2 Verified dev/val numbers (non-confirmatory)

Source for all rows: `artifacts/sprint4_5_1/utility/utility_verification.json` (seed 4510; N = 252; inputs `dev.json` a833ad0c…, `val.json` e82252b4…; 0 mismatches in 3 276 score re-implementation pairs). Tag: `[DEV+VAL]`.

| quantity | value | CI / note |
|---|---|---|
| V3 mean U (λ=2, γ=1), strict | **−0.3377** | template pct95 [−0.461, −0.217]; template stud95 [−0.472, −0.222]; group (K = 21) pct95 [−0.476, −0.202]; stud95 [−0.514, −0.203] |
| V3 − V2 | **+0.2242** | template pct95 [0.086, 0.366]; group stud95 [0.081, 0.429] |
| V2 − always-abstain | **−0.5619** | template pct95 [−0.712, −0.413] |
| V3 mean U, dev / val | −0.3367 / −0.3403 | SD 0.976 / 0.959 |
| V3 operational-unsafe V3 − AA | −0.1948 | template pct95 [−0.300, −0.094] |
| V3 − V2 operational | +0.1687 | template pct95 [0.031, 0.309] |
| V3 outcomes | correct 45, unsafe 48, abstain 159 of 252 | answered 93; wrong-root on ATTRIBUTE 10; answered on ABSTAIN_REQUIRED 38; "lucky" 18 |
| V2 outcomes | correct 36, unsafe 79, abstain 137 | answered 115 |
| V3 mean n_do | 2.706 (max 8) | V2 1.556 (max 6) |
| ORACLE upper bound | correct 99, unsafe 0 | privileged; scales δ only |
| **break-even λ\*, κ = 0 (V3)** | **0.9375** | pct95 [0.614, 1.436] (template) |
| break-even λ\*, κ = 0.025 / 0.05 (V3, strict) | 0.5823 / 0.2271 | κ = 0.05 CI [−0.010, 0.55] |
| **zero-unsafe V3** | **+0.043** | = 0.179 − 0.135 < δ = 0.10 (arithmetic from 45/252 and cost term 0.1353) |

**Significance limits (V3 vs always-abstain)** `lambda_significance_limit_V3_vs_AA`: the V3 lower CI bound exceeds 0 only for λ ≤ 0.61 (κ = 0, strict template), λ ≤ 0.60 (group), λ ≤ 0.30 / 0.27 at κ = 0.025, and at **no** λ ≥ 0 when κ ≥ 0.05. The grid cells where the V3 − AA CI is entirely positive are only (λ, κ) ∈ {(0.25, 0), (0.25, 0.025), (0.5, 0)}. So the V3 > always-abstain conclusion exists only under very low unsafe penalties — i.e. only when unsafe answers are barely penalised.

**Corrected claims E1–E6** (`docs/SPRINT4_5_1_FINAL_REPORT.md` line 25): E1 precision needed for U = 0 / U = δ is ≈ 0.79 / 0.88 (V2 0.72 / 0.80), not "≥ 2/3"; E2 CI above zero only for λ ≤ 0.61 at κ = 0 and λ ≤ 0.30 at κ = 0.025, and for no λ ≥ 0 at κ ≥ 0.05; E3 0.135 not 0.136; E4 break-even ordering holds at κ = 0 only; E5 at κ = 0.10 the V3 − V2 CI includes 0 for 0.5 ≤ λ ≤ 1.5; E6 mean ceiling is π, per-scenario U ∈ [−3, 1].

**The two claims `utility_verification.json` marks "verified: false"** (58 claims, 56 verified): (i) V3 mean cost term 0.136 vs recomputed 0.1353; (ii) B0-EARLIEST break-even λ at κ = 0: 0.26 vs 0.2606. Both are **rounding differences inside the 0.0006 tolerance's stricter reading**, not substantive errors; (i) is the correction E3 and is already in the documents. I did not check whether (ii) was edited in every document; the JSON itself records `verified: false`.

### 4.3 Baselines

* **Always-abstain is a primary baseline** and is not removed. On dev/val it **outperforms V3 and V2** (V3 − AA = −0.338; V2 − AA = −0.562). The paper must not claim RIFT beats always-abstain on this evidence.
* Observational comparators (B0-EARLIEST, B0-HIGHEST, B1-LATENCY-CORR, B3-SIEVE-LIKE, B5-RIFT-OBS) and intervention ablations (B6-RIFT-RANDOM, B7-RIFT-ONE-SHOT) are descriptive exploratory comparators (H5); ORACLE rows are labelled privileged upper bounds. Unsafe counts at pooled N = 252: B0-EARLIEST 188, B0-HIGHEST 220, B1 199, B3 190, B5 141, B6/B7 170, V2 79, V3 48. `[DEV+VAL]`
* No weight, threshold, endpoint or comparator definition may be altered after confirmatory data are observed (PRE §3, §10).

### 4.4 Evidence category warning

Everything in §4.2 is **[DEV+VAL]**: V3 was developed and iterated on dev/val (Sprint 4.4), so these are **non-confirmatory** and, for V3, not an unbiased held-out estimate. The held-out Sprint 4.3 result `[HELD-OUT-V2]` concerns V2, is not re-opened here and must not be mixed into this table.

---

## 5. Classification

| # | issue | classification | one-line reason |
|---|---|---|---|
| 1 | Label circularity (definitional) | **NEEDS-RESEARCHER-DECISION (D23)**; cannot be fully resolved inside a self-authored simulator | Labels mirror RIFT's 3σ/persistence-2 and a 4.0 gate; no method leakage. Proposed L-struct + SNR covariates as co-reported sensitivity, requires approval + human review before G3; primary label unchanged. If rejected → DISCLOSED-LIMITATION (PRE L2) |
| 2 | Label-method leakage (labels from method output) | **RESOLVED (no issue found)** | `compute_ground_truth` reads only simulator state |
| 3 | WEAK_SIGNAL validity | **NEEDS-RESEARCHER-DECISION** (part of D20/D23) | "Abstention required" is a normative class, not a causal fact; the [3,4) band (30 scenarios) is the contested zone |
| 4 | Scenario-level independence (2 000 ≠ 2 000) | **DISCLOSED-LIMITATION** | 16 fixed structures × 16 families; no effective-N claim |
| 5 | Crossed family dependence (D19) | **DISCLOSED-LIMITATION** | Template rule anti-conservative (size 0.046–0.202 under rf); family-block power 0.30–0.59; inherent to 16 families; not fixable by N |
| 6 | Generalisation beyond the 16 motifs | **DISCLOSED-LIMITATION** | Claim restricted to fixed strata; any wider claim is not allowed |
| 7 | Negative conclusion inference | **RESOLVED (defensible)** | Dev/val V3 − AA CI far below 0 under both clusterings; ≈ 130 scenarios suffice |
| 8 | Positive / null-as-equivalence inference | **DISCLOSED-LIMITATION** | Positive claim requires family-block CI > 0; null in positive direction ≠ equivalence |
| 9 | CID temporal confounding | **DISCLOSED-LIMITATION; Phase A NOT RUN** | Design adequate in principle; V0 module absent; zero executed evidence; eligibility unknown |
| 10 | CID Phase A module and V0 gate | **DISCLOSED-LIMITATION (does not block Phase B generation; blocks any CID-validity claim)** | Phase A is independent of Phase B; without it the paper may not claim CID has defensible operating conditions |
| 11 | D23 decision record and label-structural fields | **CLASSIFIED-BLOCKING-FOR-GENERATION (if adopted)** | Fields must exist in the new generator's `design` block before any candidate is drawn |
| 12 | Utility weights | **DISCLOSED-LIMITATION (normative)** | λ, γ, δ are researcher choices, not calibrated; V3 > AA only at λ ≤ 0.61 (κ = 0) |
| 13 | Always-abstain beats V3/V2 on dev/val | **DISCLOSED (finding, not a defect)** | `[DEV+VAL]` V3 − AA = −0.338; retained as primary baseline |
| 14 | Utility "bounded in [0,1]" wording | **RESOLVED** | Corrected to [−3, 1] (E6) |

**Bottom line.** The label-circularity concern is real but of the *definitional* kind; it does not by itself produce the negative V3-vs-always-abstain result (zero-unsafe V3 is only +0.043, and even deleting the quoted WEAK_SIGNAL contribution leaves roughly −0.17 — arithmetic, not a result). Fixing it fully is impossible inside a simulator the authors also wrote, so it must be **disclosed**, with the D23 co-reported sensitivity as the strongest mitigation available *if* the researcher and an independent human reviewer approve it before the preregistration is hashed. The statistical design is defensible for the expected negative conclusion and not defensible as evidence of equivalence or of generalisation. CID's defensible operating conditions remain unestablished because Phase A has not been run.
