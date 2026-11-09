# SPRINT 7 — Final Research Report: RIFT Contributions, Empirical Boundaries, Epistemic Tiers and Application Evidence

**Date:** 2026-11-09 · **Author:** Sprint 7 agent (AI) · **Status:** synthesis of existing evidence plus the Sprint 7 re-derivations in [`sprint7_probes/`](sprint7_probes/). **Not independently reviewed by a human (D7 `PENDING`).**
**Companion:** [`SPRINT7_FINAL_CLAIMS_LEDGER.md`](SPRINT7_FINAL_CLAIMS_LEDGER.md) (claim-by-claim statuses; every number here is traceable to a row there).

---

## 1. One-paragraph summary

RIFT is a research prototype for root-cause localisation in microservices that combines an observational shortlist (Earliest Behavioural Divergence), constraint-based causal discovery (FCI → PAG), an identifiability gate that can abstain, cost-aware selection of `tc netem` latency interventions, and a Wasserstein-1 permutation test of interventional divergence (CID). Its most defensible outcome is a **negative-result characterisation**: on a simulator benchmark of 252 development/validation scenarios (plus one spent, V2-only held-out set of 108), the system's later version (V3) answers less often and makes fewer unsafe attributions than its earlier version (79 → 48, −39%), yet at the normative penalty weights it still scores **below a trivial always-abstain policy** (mean utility −0.338 vs 0). Learned FCI graphs are 97–98% circle-marked, every wrong V2 root was a downstream descendant of the true root, interventions have no demonstrated accuracy benefit over observation-only variants, and one live N=1 feasibility trial shows that the injection mechanism works but did not produce a pipeline-level attribution. No confirmatory data exist, no independent human has reviewed the work, and several informally circulated numbers (0.875 P@1, 3 testbeds, 25/25) have no source and are withdrawn.

## 2. What RIFT contributes (and at what strength)

| # | Contribution | Strength of evidence | Where it lives |
|---|---|---|---|
| C-1 | **An evaluation discipline that most AIOps RCA papers lack:** a four-way outcome partition (correct / correct-abstain / unsafe / benign-miss), an explicit `ABSTAIN_REQUIRED` label derived from noise-free simulator physics, a mandatory **always-abstain baseline**, a utility function U = C − λS − κ·n_do with exact bounds [−(λ+γ), 1] and ceiling π, and a break-even analysis over a 4×8 (κ,λ) grid with cluster bootstrap. | **Strong** (re-implemented scorer matches 3,276/3,276 saved scores; 56/58 preregistered numbers reproduce, 2 are rounding). | `scripts/sprint451_utility_sensitivity.py`, `artifacts/sprint4_5_1/utility/` |
| C-2 | **A reproducible negative result:** a published-style system with causal discovery + interventions does **not** beat always-abstain on a held-out set (V2: 60/108 vs 63/108, McNemar p=0.76) nor, for V3, on dev/val utility. | **Strong for the stated simulator**; one-shot, spent, V2 only. | `docs/SPRINT4_3_0_FINAL_REPORT.md`, `…SPRINT4_4_0_FINAL_REPORT.md` |
| C-3 | **Failure taxonomy of interventional RCA:** (i) descendant trap (14/14 V2 held-out wrong roots, 14/14 dev, 13/13 val were descendants of the true root), (ii) FCI undecidability (97.8% / 97.0% circle-marked; 0/162 and 1/89 correct orientations on true edges), (iii) window-drift confounding of CID (≈94% spurious confirmation in the drift stratum vs 4–7% in the clean stratum), (iv) unobserved-root boundary (A12: 7/7 unsafe for V3, 8/8 for V2). | **Strong, descriptive** (independent re-derivation of the 94% in `scripts/sprint440_cid_audit.py`). | `SPRINT4_4_0_*`, `CAUSAL_VALIDITY_AUDIT.md` |
| C-4 | **V3: a conservative attribution layer** (PAG used only for contradiction checks, manipulation check, symmetry check, earlier-divergence guard, Holm correction) that cuts unsafe answers 79→48 and beats V2 on utility in 25/32 strict grid cells. | **Moderate, adaptive:** designed on dev, "confirmed" on val, same pool used for the headline. Not confirmatory. | `src/rift/attribution_v3/`, `SPRINT4_4_0_V3_DESIGN.md` |
| C-5 | **Self-audit methodology:** the project found and documented its own defects — decoder bug D1 (collider arrowheads lost), label echo in the oracle harness (L1–L7), R4 circularity, live-backend handle bug, dataset contamination (15/15 legacy held-out twins; 36 "confounded" records = 4 contents), unsupported headline numbers. | **Strong** (code-level probes in `docs/recovery/algorithm_audit_probes/`). | `ALGORITHM_AUDIT.md`, `DATASET_AUDIT.md`, `REPORT_LOCAL.md` |
| C-6 | **A working (N=1) live `tc netem` + Prometheus pipeline on a 14-container stack** with verified rollback to the initial qdisc. | **Weak/feasibility only** (see §4.3). | `docs/SPRINT4_2_1_…`, `EXTERNAL_VALIDATION_PLAN.md` |

**Not contributions (do not claim):** a method that improves root-cause accuracy through intervention; a method that detects confounding from telemetry; cross-system generalisation; superiority over Sieve/MicroRCA/RCD/Sage (only a "Sieve-like" re-implementation was run); a deployable safety-bounded system.

## 3. Empirical boundaries

### 3.1 The evidence that exists

| Tier of data | Size | Used for | Independence | Verdict |
|---|---|---|---|---|
| Legacy `rift_faults` (dev 50 / val 18 / held-out 15; 36-scenario oracle harness) | 83 | Phase 3 harness, thresholds | Held-out has 15/15 content twins in dev∪val; 36 confounded records = 4 contents | Not independent evidence |
| `rift_v2` dev + val | 180 + 72 = **252** | V2/V3 development, Sprint 4.5.1 utility analysis | 21 union-find groups, 105 templates; label rule shares RIFT constants (49/99 ATTRIBUTE labels rest on a rule identical to R1) | Development evidence (adaptive) |
| `rift_v2` held-out | 108 | One-shot V2 evaluation (Sprint 4.3); **re-opened once for frozen V3 in Sprint 7 WS1** | Independent of dev/val by stored report; **spent**; V3's design had seen the published V2 held-out failure analysis; contains deliberate distribution shift | V2: valid one-shot. V3: exploratory re-opening, registry-flagged not valid for final claims |
| `rift_v3_dev` adversarial | 112 (14 types × 8 variants) | V3 stress | Shares 7 topology hashes with dev | Development stress, variants not independent |
| Confirmatory (N≈2,000, 16×16 cells) | **0 generated** | — | Generator locked (no `prereg.sha256`; D7 `PENDING`) | **No confirmatory data exist** |
| Live testbed | **1 trial** | Feasibility | Experimenter-chosen target | Feasibility only |

### 3.2 Numbers inside the boundary (pooled dev+val, N=252, π = 99/252 = 0.393)

| Method | Correct | Unsafe (strict) | Answered | Mean n_do | U (λ=2, κ=.05) strict / operational |
|---|---:|---:|---:|---:|---|
| Always-abstain | 0 | 0 | 0 | 0 | 0 / 0 |
| **RIFT V3-FULL** | 45 | 48 | 93 | 2.71 | **−0.338 / −0.195** |
| RIFT V2 | 36 | 79 | 115 | 1.56 | −0.562 / −0.363 |
| B5-RIFT-OBS (no intervention) | 30 | 141 | 171 | 0 | −1.000 / −0.833 |
| B3-SIEVE-LIKE (re-implementation) | 46 | 190 | 236 | 0 | −1.325 / −1.079 |
| B0-EARLIEST | 49 | 188 | 237 | 0 | −1.298 / −1.004 |
| B6 = B7 (random / one-shot; identical outcomes) | 51 | 170 | 221 | 1.2 | −1.207 / −0.953 |
| ORACLE (privileged) | 99 | 0 | 99 | 0 | +0.393 / +0.393 |

(Utilities recomputed from `utility_verification.json → decomposition_pooled`; paired CIs in [`sprint7_probes/v3_vs_all_baselines.out.txt`](sprint7_probes/v3_vs_all_baselines.out.txt).) Observations that bound any statement about V3:

* **V3 is better than every deployable comparator and worse than doing nothing.** Its advantage over the baselines is almost entirely that it abstains on 63% of scenarios; the baselines answer 85–100%.
* **Precision on answers is 45/93 = 48%.** To reach U=0 at λ=2 with V3's coverage and cost the precision would need to be ≈0.79 (`recommended_doc_edits.md` E1).
* **V3's dev/val gain over V2 did not reappear on the re-opened held-out set** (Sprint 7 WS1): V3 U = −0.664 vs V2 −0.594 (V3−V2 −0.070, CI [−0.336, +0.194]); P3_safe +0.037 (p=0.585); wrong-root 12/45 vs 3/31 on val (exploratory p=0.084; partly confounded with a deliberate distribution shift and larger graphs). The only transferable statement is therefore "V3 ≥ V2 on development/validation"; there is no out-of-sample evidence that V3 is safer than V2.
* **V3 is not safe.** 48 strict-unsafe answers, of which 18 are "lucky right-service on an abstain-required scenario" and 10 wrong roots on attributable cases; 25/48 dev and 12/22 val "DEFINITIVE" answers were unsafe, so the confidence label is uncalibrated.
* **The "intervention overhead is >50% lower than random exploration" claim is false as worded**: V3 averages 2.71 do() vs 1.21 for the random MSIS baseline (WS3 §D.3); the circulated 30 s vs 60 s are hard-coded constants.
* **Interventions have no demonstrated benefit.** Ablations A6/A8 (no interventions) equal V2's P1 (0.444) exactly; random-intervention A10 shows no difference; B5 (observation-only RIFT) is worse than V2 but its gap is not attributed to intervention in the held-out ablations; B6≡B7 means closed-loop update changed no outcome. RQ1, RQ3 and RQ4 are therefore **undemonstrated** (not refuted: the benchmark's intervention windows are short and CID is capped at the CANDIDATE tier, n=30 < 50).
* **The graph is the bottleneck, not the intervention.** Oracle graph raises held-out P1 from 20/45 to 32/45 (exploratory, p≈0.0005), but with the oracle graph V3 is not better in utility (−0.133 operational, V3 worse).
* **Utility weights are normative.** λ=2, κ=0.05 are not calibrated to any SLA or incident-cost data; V3 beats always-abstain significantly only at λ≤0.25 (κ≤0.025) and λ=0.5 (κ=0), i.e. when an unsafe attribution is cheaper than a quarter of a correct one.

### 3.3 What the work cannot say

1. Anything about **real** microservice systems, production incidents, or other topologies/benchmarks.
2. That RIFT **detects** unobserved confounding from telemetry (learned abstention on legacy "confounded" scenarios = 0/24; those scenarios contain no confounding in their data).
3. That intervention improves **accuracy** (see above).
4. That V3's gains are **out-of-sample** (V3 was designed on the same 252 scenarios, and the one out-of-sample look — the re-opened held-out — showed no advantage over V2).
5. That the live trial **validates** `LinuxTcNetemBackend`, the safety controller, or per-destination isolation.
6. Any statement requiring the confirmatory run, which does not exist.

## 4. Epistemic tiers

### 4.1 Causal-evidence tiers (what an attribution can mean)

From [`CAUSAL_VALIDITY_AUDIT.md`](CAUSAL_VALIDITY_AUDIT.md) §7, with this sprint's empirical anchors:

| Tier | Criterion | Licenses | Does not license | Empirical anchor |
|---|---|---|---|---|
| T1 Correlation | EBD R1: z ≥ 3 for 2 windows | "metric shifted" | cause, direction | Stage-2 null alarm rate 13.8% per service at n=30 (probe 12) |
| T2 Temporal precedence | earliest onset | "not excluded as early mover" | cause | B0-EARLIEST: 188/237 answers unsafe; descendants alert first |
| T3 Causal discovery | PAG semi-directed reachability | "not excluded as ancestor" | root-cause status | 97–98% circle marks; 0/162 correct orientations; PAG learned on incident-regime data (C2) |
| T4 Active perturbation | CID p_Holm<0.05, CANDIDATE tier | "do(X) is consistent with shifting Y in this window" | proof; Pearl-style do(X:=x) | 94% spurious in drift stratum, 53.5% under AR(1 φ=0.8) null (probe 4); tc-netem is a mechanism perturbation with backpressure channels |

No RIFT output can exceed T4 and none has been validated beyond a simulator.

### 4.2 Evidence-class tiers (how much a number can be trusted)

| Class | Definition | Items |
|---|---|---|
| **E0 – Confirmatory** | Frozen method, pre-recorded analysis, independent review, untouched data | **None exist.** |
| **E1 – One-shot held-out** | Opened once, frozen method | V2 on 108 held-out (spent). |
| **E2 – Adaptive development** | Method/analysis designed on or after viewing these data | V2/V3 on 252 dev/val; 39% reduction; utility grid; all V3 results. |
| **E3 – Upper-bound / oracle** | Privileged information in the pipeline | 10/12 and 24/24 legacy harness; oracle-graph ablations; ORACLE rows. |
| **E4 – Live feasibility** | Real system, N=1 | cartservice 50 ms trial: p99 6.25→236.15 ms; rollback verified; offline RIFT inference abstains. |
| **E5 – Withdrawn / unsupported** | No artifact, or contradicted | 0.875/35-40, 3 testbeds, 25/25, "100% live top-1", PAPER_DRAFT Table 2/abstract. |

### 4.3 The live trial, precisely

Real: 14 containers up on RHEL 9.6 under Podman; OTel spanmetrics → Prometheus p99 series; `tc prio` + `netem delay 50ms 5ms` applied in cartservice's network namespace; qdisc restored to `noqueue`; cartservice p99 6.25→236.15 ms (Z=143), frontend 230.62→446.25 ms (recomputed from the artifact by the external-validation audit). Limitations: N=1; no noise floor; series have 2–4 distinct values per phase (rate windows overlap) so Z=143 is not 143 independent σ; the "intervention" window is 110 s but the rule was active ~30 s; windows were back-filled after the run; report and artifact timestamps differ by ≈6 min; "cartservice p99" may include client spans; the target was chosen by the experimenter; commands were inline (not the library backend, whose band-1 handle collides with the root handle); the filter matched all TCP rather than one destination. Offline inference on the saved data yields `ABSTAINED / NOT_IDENTIFIABLE` with CID `INSUFFICIENT` (n=15/12 < 20), flipping with FCI α. The earlier "100% top-1" is a hard-coded literal.

## 5. Quality of the repository as a research artifact

| Dimension | State |
|---|---|
| Tests | Sprint 7 local run: **1,017 passed, 8 failed, 0 other**. The 8 failures are `test_final_reproducibility.py` checks that the installed numpy/scipy/scikit-learn/networkx/pandas/causal-learn match a Python-3.9 canonical lock (and one bit-reproducibility check that depends on it); this checkout runs Python 3.11 with other versions. Environment mismatch, not a functional failure. CI additionally reports 2 protected-material tests as UNAVAILABLE (never as pass). |
| Reproducibility | Utility analysis reproduces from hash-pinned dev/val (`PINS` asserted); WS3 independently re-executed V2, V3 and 8 baselines and matched saved records (2 `n_do` differences on V2 only, no label changes). `python -m rift.experiments.run` fails without `PYTHONPATH=src` (WS5). `make reproduce-all` and the EXP-001 dry-run were repaired in the recovery sprint. Historical results were produced on Python 3.9.6 / causal-learn 0.1.4.8; edge orientation varies slightly on 3.11. |
| Version control | **Citable on GitHub today:** `scripts/sprint451_utility_sensitivity.py`, `artifacts/sprint4_5_1/utility/*`, `datasets/rift_v2/*`, V3 dev/val records. **Not yet citable (untracked or modified):** everything in `docs/recovery/`, `REPORT_LOCAL.md`, `artifacts/stage4_intervention_results.json`, `artifacts/sprint4_3_0/` parts, `artifacts/final_closure/`, `artifacts/phase3/independent_validation_report.json` (modified). |
| Figures / tables | All circulated figures (`analysis/figures/fig1–4`, `fig_precision_comparison.svg`) and `analysis/tables/*` are empty templates. `fig_h2_power.svg` is a planning power curve, not a result, and its hard-coded "n=48" marker disagrees with its own curve (80% at n≈23) and with the 4-distinct-scenario reality of the legacy confounded set. Architecture / topology / obs-vs-intervention SVGs are diagrams (topology SVG shows Jaeger and "Docker", which does not match the executed Podman stack — flagged in the ledger). |
| Known open defects (from audits) | R4 circular in the e2e runner (C1); PAG learned on incident-regime data (C2); safety controller not on e2e path (SF-1); `LinuxTcNetemBackend` band-1 handle collision (D-1); frozen decoder D1; label echo in legacy harness (L1–L7); `generator_confirm` lock schema mismatch. V3 (simulated path) avoids C1/C2/D1 by design; the e2e runner does not. |

## 6. Human decisions still open (cannot be closed by an agent)

D7 independent human reviewer; D12 owner-run protected full-tree test run; D23 label-circularity decision; recording the preregistration hash; authorising the confirmatory generation (max 3 attempts, D15); committing the untracked evidence files.

## 7. Graduate-application resume evidence

### 7.1 Verdict

**CONDITIONALLY READY — as a rigorous negative-result / evaluation-methodology and systems project, not as an "RCA that works" project.** The Recovery Dashboard's verdict is retained; its resume bullet is replaced because it (a) said the 39.2% was "over heuristic baselines" (it is over V2), and (b) said the work "proved formal break-even boundaries" (they are bootstrap estimates on normative weights).

### 7.2 Resume bullets (choose by space)

**Short (2 lines):**
> **RIFT — causal root-cause localisation with abstention for microservices** *(research prototype, Python)*. Built FCI/PAG + Wasserstein-permutation + `tc netem` pipeline and a utility-based evaluation harness; on 252 simulated incidents the tuned V3 cut unsafe attributions 79→48 vs. its predecessor (not reproduced on a re-opened held-out set) and still scored below an always-abstain baseline — reported as a negative result with exact bounds.

**Standard (4 lines):**
> **RIFT: Intervention-grounded root-cause analysis with abstention** — *independent research project*
> • Designed an abstaining RCA pipeline (EBD → FCI/PAG → identifiability gate → cost-aware `tc netem` selection → W₁ permutation test) and ran a one-trial feasibility test on a 14-container Online Boutique stack (RHEL 9.6, Podman, verified qdisc rollback).
> • Built a simulator benchmark (360 labelled scenarios + 112 adversarial) with explicit abstain-required labels and a mandatory always-abstain comparator; derived exact utility bounds and break-even penalties (λ\*=0.94 at zero cost; significant only for λ≤0.61) with cluster bootstrap over 105 templates.
> • Found that interventions gave no measurable accuracy gain, that 97–98% of learned FCI edges stay unoriented, and that every wrong V2 root was a downstream descendant; reduced unsafe attributions 39% (79→48/252) vs. V2 on development data by abstaining more — a gain that did not reappear on a re-opened held-out set — and still below always-abstain (U=−0.34).
> • Audited my own results: traced unsupported figures and oracle label-echo, fixed a PAG mark-decoder bug, and withdrew claims that did not reproduce.

### 7.3 Statements that are safe, with their evidence

| Statement | Evidence |
|---|---|
| "Implemented FCI/PAG-based pipeline with Wasserstein-1 permutation testing and netem interventions" | `src/rift/{fci,cid,ebd,intervention,attribution_v3}`; 1,017 passing tests |
| "Verified `tc netem` injection and clean rollback once on a 14-container Online Boutique deployment on RHEL 9.6" | Stage 4 artifact (untracked; commit before citing); N=1 |
| "Evaluated on 252 simulated dev/val scenarios and one spent held-out set of 108" | `datasets/rift_v2/*`, `utility_verification.json` |
| "Reduced unsafe attributions from 79 to 48 (−39%) relative to the earlier version" | §3.2; ledger H6 |
| "Showed the system does not beat an always-abstain baseline at the chosen penalty weights; characterised break-even boundaries" | ledger H7 |
| "Identified and documented failure modes (descendant trap, FCI undecidability, window-drift confounding, unobserved-root boundary)" | §2 C-3 |
| "Independently audited and corrected the project's own claims" | `REPORT_LOCAL.md`, `docs/recovery/*` |

### 7.4 Statements that must never appear

"87.5% / 0.875 / 35 of 40 precision"; "three testbeds"; "25/25"; "100% abstention on confounded faults" (without the oracle caveat); "outperforms baselines / state of the art / Sieve"; "proved"; "validated on production/real systems"; "preregistered" (not recorded); "peer-reviewed / independently reviewed"; any use of the Agent-7 resume bullet ("over heuristic baselines", "proving formal break-even boundaries").

### 7.5 Interview-ready framing

* *Thesis:* "I tried to show that interventions improve root-cause attribution under confounding. In my simulator they did not; the best I could show is that a more conservative version makes fewer unsafe calls, and that nothing I built beats doing nothing unless a wrong answer is cheap."
* *What I would do next with data access:* a confirmatory run on frozen V3; the learned-graph abstention test on data that actually contains latent confounding; repeated live trials with concurrent controls to remove window drift; calibrate λ,κ against real incident-cost data.
* *Likely hostile questions and honest answers:* "Why not claim a win?" — the label rule shares RIFT's thresholds, V3 was tuned on the same scenarios, and on a re-opened held-out set it was no better than V2. "Is 39% significant?" — cluster CI 23–54%, but adaptive and relative to V2. "Does the live test prove it works?" — it shows the mechanism, not the inference.

## 8. Recommended next actions (ordered by value ÷ effort)

1. Commit the untracked evidence (`docs/recovery/`, Stage 4 artifact, Sprint 4.3.0/final_closure artifacts, modified validation report) so every cited number is checkable on GitHub.
2. Resolve the 8 environment-lock test failures by documenting `reproducibility/requirements-canonical-py39.lock.txt` as the required environment (or add a 3.11 lock) — otherwise the full suite does not pass on a clean 3.11 setup.
3. Decide the human gates D7/D12/D23 before any further experiment.
4. Fix `LinuxTcNetemBackend` handle collision and wire `SafetyController` before any further live run (ALGORITHM_AUDIT P0-3, P0-5).
5. Replace the empty figures with real, labelled plots from `utility_verification.json` (V3-vs-baselines utility with CIs; λ–κ break-even map) or delete the templates.
