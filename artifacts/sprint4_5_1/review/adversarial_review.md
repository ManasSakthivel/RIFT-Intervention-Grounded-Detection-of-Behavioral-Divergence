# Sprint 4.5.1 — Internal Adversarial Review of the Sprint 4.5.0 Preregistration (Agent 7)

> **This is an INTERNAL adversarial review performed by an AI agent. It is NOT external independent validation, NOT peer review, and does not satisfy decision D7 (named independent human reviewer).**
> Read-only with respect to all existing files. Allowed outputs: this file and the scratch scripts/JSON beside it.
> Never touched: `datasets/rift_v2/heldout_candidate.json`, `heldout_status.json`, `artifacts/sprint4_3_0/results/held_out/`. No frozen file edited. V3, V2 and RIFT methods were **not run** on any data. The only method executed was the cheap B0-EARLIEST baseline on dev/val (§P1-4, shuffled-order check). `compute_cid` was timed on synthetic Gaussian arrays.
> All empirical numbers are dev/val (N = 252) and therefore **non-confirmatory**.

Documents reviewed (current versions at review time): `docs/SPRINT4_5_0_PREREGISTRATION.md` (PRE), `..._STATISTICAL_ANALYSIS_PLAN.md` (SAP), `..._CID_EXPERIMENT_DESIGN.md` (CID), `..._DATASET_PROTOCOL.md` (DSP), `..._FINAL_PREREGISTRATION_AUDIT.md` (AUD), `..._EXECUTION_PLAN.md`. Code: `benchmark_v2.score_one`, `rift_v3.py`, `rift_v2.py`, `scenarios/{simulator,generator_v2,independence,splitter}.py`, `cid/cid.py`, `scripts/sprint440_run_v3.py`, `scripts/sprint440_cid_audit.py`.

Evidence scripts (all reproducible; seeds 4510–4513): `adversarial_checks.py/.json`, `adversarial_checks2.py/.json`, `t5_feasibility.py/.json`, `geometry_feasibility.py/.json`, `geometry_bound.py/.json`, `label_margin.py/.json`, `lucky_by_family.py/.json`, `node_order_leak.py/.json` (same directory).

---

## VERDICT

**The preregistration must NOT be described as "fully approved", and in its current form it should not be recorded/hashed (PRE §13).**

* Two **P0** defects: (1) the dataset-geometry acceptance gates in DSP §6/§8.5/T5 are unattainable under DSP §3.1–3.2, so the planned clustering unit, the K ≥ 250 assumption and hence the SAP power argument do not hold; (2) the "freeze" manifest omits runtime-imported files, two of which are untracked, so the comparator set cannot be reproduced from git.
* Eight **P1** defects (estimand/DEFF, un-frozen runner and weak leakage test, node-order leak, label-function circularity, quota inconsistency, robustness-clause validity, CID eligibility rule, error→abstain mapping).
* The 18 researcher decisions D1–D18 and A1–A9 remain open, D7 (independent reviewer) and D12 (protected verification) are unmet, and no external review exists.
* H1 is testable and the stated power arithmetic is arithmetically right (I re-derived it), but **H1 is expected to fail**, and the study as designed is mostly an expensive confirmation of a known negative unless the changes in P1-6 are adopted.

---

## TOP-10 (ranked)

| # | Pri | Issue | Where |
|---|---|---|---|
| 1 | P0 | Group-geometry gates (K ≥ 250, max group ≤ 25, ≥ 90 % unique topology) and T5 non-isomorphism are infeasible under the stated generator; union-find groups collapse to ≈ 10 | DSP §3.2, §6, §7 T5, §8.5, §9.2 |
| 2 | P0 | Freeze manifest incomplete; comparators fail to import on a clean export; two imported files untracked | PRE §2, AUD §2 |
| 3 | P1 | Inference population/DEFF mis-specified: structure-level DEFF is ≈ 6.2 at m = 125, not 2.2; N = 2000 power ≈ 0.46 if structures are random; estimand not stated | SAP §6.1, PRE §4, DSP §3 |
| 4 | P1 | Confirmatory runner is not frozen/specified; "V3's existing behaviour" for errors is false; T8 leak test is too weak; node order leaks the root | PRE §7/§9, DSP T8, SAP §7 |
| 5 | P1 | Label function mirrors RIFT's own evidence thresholds; 3σ-vs-4σ boundary drives ≈ 49 % of V3's deficit; `δ = 0.10` + `γ = 1` make POSITIVE-USEFUL nearly unreachable | PRE §3, §12 L2, SAP §2 |
| 6 | P1 | H1 is a known negative; "robustness" clause is not tested and the stratum contrast can produce a misleading *favourable* signal; drift-stratum premise is mis-stated | PRE §1, SAP §8.2, DSP §5.3 |
| 7 | P1 | Quota table contradicts "125 ± 15 per structure" (S13/S14); "structures V3 was not tuned on" is overstated | DSP §3, §5.2 |
| 8 | P1 | CID "borderline ⇒ ineligible" rule rejects a perfectly valid estimator with 63–87 % probability; "same replicate data" is false for E1/E2/E6 | CID §6, §7 |
| 9 | P2 | POSITIVE-USEFUL uses a point-estimate threshold; "DEFINITIVE_ROOT" is built on CANDIDATE-grade CID; forking paths in 3 attempts / D17 / "first complete run" | PRE §10, §7; DSP §9 |
| 10 | P2 | Reproducibility is evidenced on one macOS-arm64 machine only; CI/py-version/pyproject inconsistencies; 663 vs 664 unexplained | PRE §2.5, AUD §2 |

---

## P0 — BLOCKERS

### P0-1. Dataset geometry gates are infeasible; the clustering unit collapses

**Where.** DSP §3.2 (periphery: "0–3 extra observed nodes … target of ≥ 90 % of scenarios with a topology hash unique within CONFIRM, and no topology hash shared by more than 3"), §6 ("planned geometry: 256 templates, ≥ 250 groups, mean size 8, maximum 25"), §7 T5 ("zero isomorphic pairs"), §8.5, §9.2 ("at most 3 attempts"); SAP §1 and §6.3 ("Preregistered N = 2000, from 250 groups").

**Argument.**

1. *Pigeonhole bound, independent of any simulation.* I enumerated every graph reachable from the 16 motifs in DSP §3.1 with 0–3 periphery nodes (each attached by an edge from a non-root node, optional second acyclic edge; ≤ 12 nodes) and hashed each with the frozen `independence.topology_hash`. The design space has **only 2,354 distinct hashes in total** (`geometry_bound.json`), and very few for several motifs: S14 = 51, S12 = 68, S11 = 73, S13 = 89, S08 = 95, S09 = 95, S02 = 106, S06 = 111, S07 = 120.
   DSP §5.2 requires 125 ± 15 scenarios per structure. Even at the 110 minimum, S11–S14 alone need ≥ 440 scenarios on 281 hashes (≥ 159 non-unique). With 125 each, ≥ 219 scenarios cannot be unique, already above the ≤ 200 non-unique allowed by "≥ 90 % unique" in a 2000-scenario set, before counting S02/S06–S09.
2. *Group collapse.* The unit is the union-find component over `template_id` **or** `topology_hash`. Within a motif, the 16 family-templates share a small hash set, so they merge. Monte-Carlo with the protocol's own periphery rule (2,048 scenarios, 8 per template; `geometry_feasibility.json`):

   | periphery | unique-hash share | max scenarios on one hash | **K groups** | **max group size** |
   |---|---|---|---|---|
   | uniform 0–3 | 0.37 | 41 | **9** | **512** |
   | 1–3 only | 0.43 | 14 | **11** | **384** |

   All four gates (≥ 0.90 unique; no hash > 3; K ≥ 250; max group ≤ 25) fail in both. (dev/val already showed the same phenomenon: 21 groups for 252 scenarios.)
3. *T5 fails as written.* Skeleton-isomorphism of the new motifs against the frozen `_build_topology` library (11 kinds × extra 0–4 = 55 graphs, hidden flag + fault-root flag as nodes attributes): **S07 (hub_with_feeders, 0 periphery) ≡ `converging`/extra1** and **S13 (mutual_pair_chain) ≡ `ambiguous`/extra1–4** (5 isomorphic variants; `t5_feasibility.json`). With the root flag dropped (the DSP wording is "hidden flag only") more would collide. DSP says "a failing motif is redesigned before confirmatory generation", which is fine, but the document currently asserts "satisfies every criterion in §1 by construction" (DSP §2 route A row), which is false for S07/S13.

**Consequence.** As specified, every generation attempt fails QC (3 attempts → "the sprint stops", DSP §9.2) or the gates are rewritten after seeing the generator's output (a post-hoc degree of freedom). More importantly, the realised analysis unit would be K ≈ 10 giant groups, so (a) the SAP's studentised group bootstrap is unreliable at K < 20, (b) the DEFF = 2 planning value is unsupported (see P1-3), and (c) SAP §12.5's validity simulation (mean group size 8) does not test the geometry that will actually occur.

**Fix.**
* Redefine the independent unit **before** generation. Either (i) template-level groups only (and drop topology-hash merging), or (ii) a **generator-assigned design group** (e.g. "instance block" = motif × periphery spec × family) that is a deterministic function of the pre-committed master order, or (iii) accept K ≈ 16 structures as the clustering unit and re-power accordingly (see P1-3).
* Rewrite the §8.5 gates so they are satisfiable by the design space: e.g. enlarge the periphery space (more nodes/edge types) to ≥ 5× the scenarios per motif, or drop the "90 % unique" rule and instead cap max hash multiplicity and group size by construction.
* Add T5′: run T5 on the actual 16 motif definitions **now** (code in `t5_feasibility.py`; design space only, no scenario data) and amend S07/S13 before hashing.
* Pre-specify the fallback analysis (minimum K for the bootstrap-t to be valid; what is used otherwise).

### P0-2. The freeze is incomplete; comparators cannot run from the committed tree

**Where.** PRE §2 ("It covers 51 files … all 51 had the same SHA-256 in the working tree and in git HEAD"), §2.6 freeze rule; AUD §2 ("hashes 51 files (V3 source, evaluation scripts, evaluation/EBD/FCI/CID dependencies, baselines …)"); PRE §1 H5 and §6 (comparators and ORACLE).

**Argument.** I computed the static import closure of `scripts/sprint440_run_v3.py`, `benchmark_v2.py`, `scripts/run_adversarial_benchmark.py`, `scripts/run_reproducible_evaluation.py` (34 files; `ast` walk). **Not in the manifest:**
`scripts/run_adversarial_benchmark.py` (defines **B0-EARLIEST and B0-HIGHEST**), `scripts/run_reproducible_evaluation.py` (`run_rift_full_scenario` = RIFT-FULL-LEGACY and its ORACLE), `src/rift/optimizer/cost_model.py` (imported at module load by `rift_v2.py` line 30, hence by V3), `src/rift/evaluation/__init__.py`, `attribution_metrics.py`, `complete_evaluator.py`, `src/rift/statistics/stats.py`, `src/rift/graph/{anomaly_subgraph,time_slice}.py`, `src/rift/benchmark/synthetic_benchmark.py`, plus two **untracked** files: `src/rift/evaluation/dataset_registry.py` and `src/rift/benchmark/adversarial_generator.py` (both `??` in `git status`).
Executed check on the clean `git archive HEAD` export (`/tmp/rift_export`): `benchmark_v2._legacy()` raises **`ModuleNotFoundError: No module named 'rift.benchmark.adversarial_generator'`**. So B0-EARLIEST/B0-HIGHEST/B1/B3/B5–B7/LEGACY/ORACLE rows (PRE §1 H5, §6, "Other comparators") cannot be produced from the committed tree. V3 and V2 themselves import without `_legacy()` (V3 path: `run_v3` + `SharedCache` + `_out_to_rec` + `score_one`), so the V3 verdict is not affected, but the *"freeze" claim and the "Other comparators"* are.

**Fix.** Extend the manifest to the full closure (the `ast` script is easy to re-run), commit/track the two untracked modules, re-hash, and add a clean-export "import all comparators" check (no data) to SAP §12. State explicitly in PRE §2 which files are *excluded* from the freeze and why (e.g. pyproject).

---

## P1 — MUST FIX BEFORE RECORDING

### P1-3. Inference population, DEFF and N = 2000 are not coherent

**Where.** SAP §6.1 ("DEFF = 2.0 is the planning value; 3.0 is the stress value"; structure-level ICC 0.042, DEFF 2.21 at K = 10), SAP §6.3, PRE §4 ("DEFF 2 is a justified planning value rather than a pessimistic one"), PRE §12 L3, DSP §3.4.

**Argument (arithmetic I re-checked).**
* Your power formula is right: N = 2000, μ = 0.10, SD 0.969, α = 0.025 one-sided: DEFF 2 → **0.904**, DEFF 3 → **0.759**, MDE₈₀ at DEFF 2 = 0.0858. I reproduce SAP §6.3 (`adversarial_checks.json`).
* But the structure-level DEFF of **2.21 was measured with ≈ 25 scenarios per structure** (dev/val; ANOVA n₀ = 25.1). DEFF = 1 + (m − 1)ρ **scales with cluster size**. CONFIRM puts **m = 125 per structure** (2000/16). With the dev/val point estimate ρ = 0.042 (my bootstrap 95 % CI over 10 structures: [0.000, 0.093]):

  | ρ | DEFF at m = 125 | H1 power N=2000, μ=0.10 |
  |---|---|---|
  | 0.042 | **6.19** | **0.46** |
  | 0.020 | 3.48 | ≈ 0.70 |
  | 0.010 | 2.24 | ≈ 0.88 |

  N for 80 % power at DEFF 6.2 ≈ **4,569**.
* If instead the 16 structures are treated as **random draws** (the only reading under which "generalisation to new structures" is a claim), the SE is dominated by between-structure variance: dev/val between-structure SD of means = 0.263 → SE ≈ 0.066 with K = 16, one-sided 80 %-power MDE ≈ **0.197**, **independent of N**. Adding scenarios does nothing; only more structures help.
* If the 16 structures are **fixed strata** (design-based inference over a finite quota mix), structure heterogeneity is not a variance source; only within-structure clustering matters, and N = 2000 is ample (fixed-quota SE ≈ 0.020, no clustering). But then the estimand is "mean utility over *these* 16 motifs at *these* quotas", and the PRE's "generalisation to new structures" (L3) is **not** a claim the data can support.
* The documents never say which. SAP §3 resamples *groups* with replacement (random-effects logic); SAP §6.1 justifies DEFF by between-structure heterogeneity; PRE L3 claims generalisation. These are three different inferential worlds.

**Fix.** State the estimand explicitly in PRE §1/§4: "design-based mean of U over the finite quota mix of the 16 specified motifs; structures are fixed; no inference to unseen structures" (recommended, because it is what the design can deliver), set the cluster unit to within-structure groups, report the structure-level spread descriptively, and delete the sentence that N = 2000 supports DEFF 2 by reference to the structure-level ICC. If a generalisation claim is wanted, preregister K_structures (≥ 30–40) instead of N.

Also: SAP §12.5's size/power validation should include K ≈ 10–20 clusters with unequal sizes; bootstrap-t is known to be unreliable there.

### P1-4. The confirmatory runner is not frozen, "V3's existing behaviour" is mis-stated, the leakage test is too weak, and node order leaks the root

**Where.** PRE §7 (G2 lists only "`scripts/sprint450_analyze.py` and the new generator"), PRE §9 ("Method errors and timeouts are mapped to abstentions (V3's existing behaviour)"), SAP §7, DSP §7 T8, DSP §9.3.

**Arguments / evidence.**

1. *No runner is preregistered.* `scripts/sprint440_run_v3.py` (frozen) hard-refuses anything but dev/val ("this runner is restricted to dev/val") and loads via `load_v2(split)`, which only knows pinned dev/val/held_out. So G5 needs a **new** runner for CONFIRM: loading, seeds, which V2/V3/baseline configs, scoring, timing, error handling. None is specified or hashed in PRE §7/§13. That is an unfrozen component with freedom over exactly the quantities that decide H1 (what counts as an answer, what happens on exceptions).
2. *Error semantics are not "V3's existing behaviour".* `rift_v3.py` has a single `try/except` (line 96–98, FCI only). `sprint440_run_v3.run_scenario` has **no** `try/except` and no timeout; the "METHOD_ERROR → abstain" mapping and `TIMEOUT_S = 60` live in `benchmark_v2._timed`, used by `run_methods`, which does not run V3. A V3 exception would crash the frozen runner, not abstain. Mapping errors to abstentions is also the choice that favours V3 (U = 0 instead of a penalty) and must be fixed *and tested* in advance. (n_do consumed before an exception is also lost.)
3. *T8 would pass while labels leak.* `independence.LABEL_FIELDS = ("ground_truth", "design")`. `strip_labels(sc)` therefore leaves `faults` (true root services, onset, amplitude), `dimensions` (structure/family/negative), `graph` (hidden flags, true edges), `template_id`, `telemetry`, `intervention`. T8 as written ("no `ground_truth` or `design` key reaches a method") is satisfied by `strip_labels` output even though `faults` is the root list. Structurally, the existing code is safe, `run_v3(o, iv, fid, seed, …)` receives only `observe()` output, an `intervene` closure, `scenario_id` and `seed`, but the preregistered *test* does not establish that, and the frozen runners never call `strip_labels` at all (they pass the full `sc` to `sim.observe/intervene`). Fix T8 to assert the method-facing signature, the key set of `o`, and the closure's outputs; and require that `scenario_id` carries no design information (the DSP's `V3C-` prefix is fine; an id containing the structure token such as `S11` would reveal ROOT_UNOBSERVED).
4. *Node order leaks the root in the frozen generator, and the new motifs would inherit it.* In dev/val the true observed root is the **first node** in `graph.nodes`/`observe()["metrics"]` in **148/148 (dev) and 60/60 (val)** attributable-root scenarios (the generator's name pool is shuffled, but the root is created first by `_build_topology`). Any code that relies on dict-insertion order for ties leaks this. Evidence: B0-EARLIEST uses a stable `sorted` on trigger time; re-running **only B0-EARLIEST** with the metric dict shuffled (single shuffle per scenario, seed 4512; `node_order_leak.json`): correct answers dev 38 → 33, val 11 → 10; unsafe 130 → 135, 58 → 59. A single shuffle, so direction only, but the mechanism is real. Whether V2/V3 are affected (FCI variable order comes from `metrics` insertion order via `_wide_for_fci`) is **not verified**, because I may not run V3; V3's own candidate sort uses `(t_star, −anomaly, service_id)`, i.e. alphabetical, not order. The DSP lists the new motifs with roots first ("r→a→b→c") and never states node ordering.

**Fix.**
* Preregister the runner (new script, e.g. `scripts/sprint450_run_confirm.py`) in G2, hash it, and specify: exception ⇒ record `error_flag=1` and treat as abstention **including** the n_do consumed up to the failure; timeout value; seeds; stripped inputs.
* Replace T8 by an interface test as above.
* Add a generator acceptance test **T10: the position of every root in `graph.nodes` and in the observed dict is uniform** (χ² / permutation test), and shuffle node order in the emitted scenario. This is a generator property, so it does not touch frozen code.
* Optionally, a pre-run check on the dev/val outputs only: shuffle the `metrics` dict for V2/V3 and compare to saved records. That is a V3 run on dev/val and is the lead's call.

### P1-5. Label function mirrors RIFT's evidence logic; boundary artefact drives half the deficit; δ and γ make "useful" nearly unreachable

**Where.** PRE §3.1 (strict unsafe), §3.3–3.4, §12 L2; SAP §2.1; `generator_v2.compute_ground_truth`.

**Arguments / evidence (dev/val; scripts `label_margin.py`, `adversarial_checks.py`, `lucky_by_family.py`).**

1. *Circularity.* The TEMPORAL branch of `compute_ground_truth` is "the root's first sustained (|z| ≥ 3, two consecutive windows) divergence precedes all others". That is literally EBD R1 (`theta_detect = 3.0`, `persist = 2`) and the B0-EARLIEST rule applied to noise-free signals. The INTERVENTIONAL branch requires effect/σ ≥ 1 within 45 s, the regime where the n = 30 CID has ≈ 95 % power (CID §3 / Sprint 4.4.0 pilot: 0.95 at 1σ, 0.49 at 0.5σ). So ATTRIBUTE ≈ "RIFT's own evidence criteria are satisfiable" and ABSTAIN_REQUIRED ≈ "they are not". High and low utility are both partly definitional, and a method that used longer windows would be scored *unsafe* for correct answers. L2 mentions the label rule but not this.
2. *Boundary artefact.* The label threshold is SNR ≥ 4 while the methods' detection threshold is 3. Among scenarios whose true observed root has SNR in [3, 4): n = 30, **0 % labelled ATTRIBUTE**, V3 answers 37 %, 30 % of them are "lucky-correct", mean U = **−0.87**; SNR < 3: n = 16, answer 44 %, lucky 31 %, mean U −0.99. WEAK_SIGNAL overall: n = 46, 18 V3 answers, **14 name the true root**, 9 of those with SNR ≥ 3. WEAK_SIGNAL alone contributes **−0.166 of V3's −0.338** (49 %). The sign of H1 is robust (operational definition still −0.195; `adversarial_checks.json`), but the *magnitude* and all "break-even λ" statements depend on an arbitrary 1σ margin with no indifference zone.
3. *Variance-inflation faults.* The SNR in the label is a mean-shift SNR; `cpu_contention`/`resource_saturation`/`packet_loss` faults carry `var_mult > 1` (visible to a z-score detector). In WEAK_SIGNAL/NO_DISCRIMINATING dev/val scenarios: var_mult > 1: 6 of 14 lucky-correct (43 %), var_mult = 1: 12 of 50 (24 %). Small n, hypothesis-generating only, but consistent with a labelling blind spot.
4. *`δ = 0.10` and `γ = 1` jointly nearly exclude POSITIVE-USEFUL.* Decomposition of V3 at dev/val coverage/cost: mean C = 0.179, mean cost c = 0.135. **Even with zero unsafe answers**, U = 0.179 − 0.135 = **+0.043 < δ**. To reach U ≥ 0.10 with zero unsafe, V3 would need to answer ≈ 0.235 correct per scenario, i.e. ≈ 59 % of the 40 % attributable scenarios (dev/val: 45 %), and 33 % of scenarios abstain *after* probing (mean 0.056 of cost) with no benefit. So the "useful" label is, practically, unreachable by any method with V3's cost profile, regardless of safety. That may be intended, but the documents describe δ as "25 % of the ceiling" and never state that, with γ = 1, the *cost* alone consumes 76 % of V3's gross correct value.

**Fix.** (a) Add to L2 the explicit statement that the label uses RIFT's own detection and CID-power criteria. (b) Pre-specify a **label-margin band** as a state-derived design field and report it as a stratum (SNR ∈ [3, 5)); consider *excluding that band at generation time* as a design rule fixed now (this is not post-hoc removal); mark it a researcher decision. (c) Report the `U_if_zero_unsafe` and cost decomposition in the final report so readers see how much of the deficit is safety vs cost vs label. (d) State openly that POSITIVE-USEFUL at δ = 0.10, γ = 1 requires coverage far above anything observed.

### P1-6. H1 is a known negative; the robustness clause is untested and the stratum contrast can mislead; the drift-stratum premise is mis-stated

**Where.** PRE §1 (question, "Robust to unrelated temporal changes"), PRE §3.5, SAP §6.5, §8.2, DSP §5.3.

**(a) Is H1 testable and sensible? Is this an expensive confirmation of a known negative?**
H1 (E[U_V3] > 0 vs U_AA ≡ 0) is testable (it is a one-sample test; "paired" is trivial since AA has zero variance) and well-posed. But on dev/val V3 has U = −0.338 with CI [−0.46, −0.22], P(U > 0) = 0 in 4,000 bootstrap draws, and a mean-at-quota projection of **−0.332** (`adversarial_checks.json`, stratum means × DSP quotas). SAP §6.5 itself notes ≈ 130 scenarios suffice to show hi < 0. A 2,000-scenario, new-generator, 218-cell programme to re-establish that is poor value unless the report is framed as such. It is acceptable only if (i) it is described openly as a pre-registered confirmation of an anticipated negative, and (ii) it also answers a question that dev/val could not. Suggested informative additions (descriptive or secondary, not changing H1): the break-even λ\* with CI at the preregistered γ as a named co-reported estimand; a pre-specified **decomposition** of the deficit (unsafe on ABSTAIN_REQUIRED, wrong-root, cost, lucky-correct); and the stratum contrast below, redefined.

**(b) The robustness clause is not tested by scenario utility and the planned contrast can mislead.** SAP §8.2 compares V3's unsafe rate and utility in the substantial-drift stratum with the none stratum. In dev/val (stratum by the DSP §5.3 definition, computed on frozen `fault_series`; `adversarial_checks2.json`): none n = 193, answer rate 0.425, unsafe 0.202, U −0.324; substantial n = 52, **answer rate 0.115**, unsafe **0.115**, U −0.332. V3 mostly *abstains* in the drift stratum, so its unsafe rate is *lower* there. A reader (or a press release) could read that as "robust to temporal change". It measures answer suppression, not CID validity. The identification question is pair-level (false-confirmation of non-ancestral pairs), which is exactly what the audit measured and what the confirmatory run could also record without any change to V3 (record per-pair CID outcomes and score them against the graph).
**Fix:** pre-specify a pair-level secondary endpoint (false-confirmation rate of non-ancestral (x, y) pairs by drift stratum, cluster CI) and a wording rule forbidding "robust" from being inferred from scenario-level unsafe rates. PRE §1 already hedges; SAP §8.2 should say it explicitly.

**(c) Premise error.** DSP §5.3 / SAP §8.2 / AUD: "dev/val only 17 non-ancestral pairs per split had |drift| > 0.3σ". That is a *pair* count (clean pairs). At **scenario level, using the DSP's own definition**, dev/val already has **37/180 (20.6 %) and 15/72 (20.8 %) = 52/252 scenarios in the "substantial" stratum** (7 mild, 193 none). The new target (≥ 25 %) is thus +4 pp, not a step change, and the stated justification ("dev/val had an inadequate stratum") is unsupported at the unit the design uses. Also, power in the stratum is low: n ≈ 500, DEFF 2 → power for μ = 0.10 is **0.37**, MDE₈₀ = **0.17** (DEFF 3: 0.27 / 0.21), so any stratum contrast is descriptive at best. Fix the wording and state this.

### P1-7. Quota table vs per-structure rule; "structures V3 was not tuned on"

**Where.** DSP §5.2 (quota 125 ± 15 per structure; SYMMETRIC 180; NO_FAULT 100), §3.3 (label wrapper), §3.1; PRE L3; DSP §3.

* `compute_ground_truth` precedence: NO_FAULT → ROOT_UNOBSERVED → SYMMETRIC (when `structure == "ambiguous"`) → INSUFFICIENT_BASELINE → … S13/S14 are forced to `"ambiguous"` by the wrapper, so every S13/S14 scenario with an observed root is SYMMETRIC (INSUFFICIENT_BASELINE is checked *after* SYMMETRIC). The SYMMETRIC quota is **180**, but two structures at ≥ 110 each need ≥ 220 scenarios; at most ≈ 12 more can come from NO_FAULT. The table is internally inconsistent (shortfall ≈ 30–40 even before S11/S12). Acceptance sampling will either under-fill structures or breach the SYMMETRIC quota. T6 (quota feasibility) is designed to catch this, but with the P0-1 infeasibilities it consumes attempts.
* PRE L3 / DSP §3: "structures V3 was not tuned on". S10–S14 (5 of 16) are hidden-confounder and mutual-dependency analogues of structures for which V3 has dedicated components (`pag_semantics`, symmetry check config `V3-NO-SYMMETRY-CHECK`, `attribution_v3/adversarial.py`, `datasets/rift_v3_dev/adversarial_dev.json`). Motifs were authored in this sprint by a team that had read V3's per-structure dev/val results (SAP §6.1 lists them) and failure traces. The protocol documents no procedure showing motif choice was independent of V3's failure analysis. The 16-motif set, ≥ 25 % drift stratum and 40 % quota are *by design* an adversarial, hand-built stress set, not a sample of any incident population.

**Fix.** (a) Rebalance the table (e.g. per-structure bands per *label* class, or relax the per-structure rule for S11–S14) and run T6 on paper first. (b) Reword to "structures not present in the dev/val/held-out generators" and add that S10–S14 are variants of categories V3 was engineered for; classify the 16 motifs *before* generation as "novel" vs "variant of a tuned category" (SAP §8.4 already wants this; make the classification a preregistered table). (c) Label the study as a designed stress evaluation, not an estimate of deployment performance.

### P1-8. CID design: eligibility rule mis-calibrated; "same data" claim false; resource asymmetry

**Where.** CID §6 (V1–V7, "borderline … within 2 SE … treated as not eligible"), §7 ("all estimators see the same replicate data … McNemar CI"), §3 table, §4.3, §3.1.

* *Borderline rule.* Rule: rates "within 2 SE" of 0.07 are borderline ⇒ **not eligible**. At R = 2000 the SE at p = 0.05 is 0.0049, so the flag line is 0.0603. For a *perfectly calibrated* estimator (true size 0.05): P(a given null cell is flagged) = **1.99 %**; P(≥ 1 flag) over 20 null cells = 33 %, over 50 = **63 %**, over 100 = **87 %**, over 120 = 91 % (`adversarial_checks.json`, `borderline_rule`). The plain threshold (rate > 0.07) fires with prob 4×10⁻⁵ per cell, so the borderline rule, not the threshold, decides. An ideal estimator would be declared ineligible most of the time. Replace by a one-sided exact-binomial test of H0: size ≥ 0.07 at a pre-set level, or simply remove "borderline ⇒ ineligible" and report the CI.
* *"Same replicate data".* Valid for E0/E3/E4/E5 (same two windows). E1 uses longer windows (shares the first 30 s at best); E2 needs a second, independent arm; E6 is a different assignment schedule (on/off segments, 75 s exposure) that cannot be evaluated on the E0 draw. The McNemar-paired comparison against E0 therefore only applies to a subset. Say so, and for the others compare marginal rates with independent-sample CIs.
* *Resource asymmetry.* E1/E2/E6 receive more observation time or an extra arm that E0 does not. The doc reports per-second power for time but not for the second arm (E2) or the 5× observation time (E6); E4-oracle control is already marked privileged. E2's replica and E6's randomisation are design capabilities, not estimators: label E2/E6 as "different experimental designs; costs reported", not "estimators competing on equal information".
* *Duplicate cells.* The "218 cells" are not 218 distinct DGPs: canonicalising the cell specs, **18 factorial cells are exact duplicates** of others (e.g. B4 ρ = 0/no-drift/d, B5 v = 1, B6 ω = 0 × two τ, B7 trigger-none/ρ = 0 duplicate B1 d,delay 0,m=1), so ≤ 200 distinct DGPs for the 214 factorial + 4 mixtures; for estimators without a control arm B3 φ = 1 ≡ B2 own-drift (further redundancy not counted). Not harmful, but the "468,000 replicates" and "218 cells" headline overstates diversity.
* *Gate V0 tolerance.* V0 requires matching a power target (0.49/0.82/0.95) that comes from a **150-draw** pilot (SE ≈ 0.04) to within ±0.05 at R = 2000: the pass/fail is largely sampling noise in the *reference*. Use the closed-form/high-R E0 power from the frozen `compute_cid` (R ≥ 10⁴ run once on validation seeds) as the target.
* *Simulator mismatch.* Frozen `simulator.intervene` has iid noise (autocorrelation absent), so B4 (ρ = 0.5/0.8), B7 and B10 are outside V3's operating envelope; conclusions "eligible for V3-CIDx" are about a richer DGP than the one V3-CIDx would later be tested on. State it.
* Identification caveats stated well in CID §2/§8 (triangle inequality Δ − κ ≤ ψ₀ ≤ Δ + κ; E0/E1/E5 detection-only; E3 only in the linear class; E4 only under parallel trends) and I found no flaw there. In particular E6 (randomised switchback) is the only design-based one; its exact p-value granularity is fine (max attainable size 12/252 = 0.0476 ≤ 0.05). Residual concern: E6 requires a reversible 5 s-washout perturbation, which V3's interventions are not shown to satisfy (CID §8 notes this).

---

## P2 — SHOULD FIX

* **P2-a. POSITIVE-USEFUL uses a point-estimate threshold.** PRE §10: "lo > 0, θ̂ ≥ δ = 0.10" ⇒ "exceeded always-abstain … by a margin at least as large as the preregistered minimum useful effect". With lo = 0.001 and θ̂ = 0.10 the CI contains values < δ; the wording overstates. Use "lo ≥ δ" for "useful with confidence" or reword "point estimate". Also the NEGATIVE-NO-USEFUL-EFFECT row relies on `hi < δ` — consistent. The operational-sensitivity requirement for POSITIVE-USEFUL is sound; its CI should use the same studentised procedure (SAP §9.3 does not say so).
* **P2-b. Language.** PRE §10 forbids calling "QUALIFIED or CANDIDATE-grade answers … definitive", yet V3's own status label `DEFINITIVE_ROOT` is assigned from CANDIDATE-grade CID in every saved record I inspected (e.g. `v3_dev.json` first scenario: `status: DEFINITIVE_ROOT`, all `cid_grades: CANDIDATE`). The ablation `V3-DEFINITIVE-ONLY` and SAP §9.5 use that name. Add a rule: "the V3 status `DEFINITIVE_ROOT` is an internal label; reports must write 'DEFINITIVE_ROOT status (CANDIDATE-grade CID)' and never 'definitive attribution'." Also "safe" in the research question is the simulator's unsafe indicator only; add "(as defined by the preregistered unsafe indicator)" wherever "safe" is used in conclusions. The forbidden phrases appear only inside prohibitions in all five documents (grep verified).
* **P2-c. Forking paths.** (i) DSP §9.2: three generation attempts, code may be corrected for "defects unrelated to any method outcome" — subjective; quotas/QC use labels, so each attempt changes the label distribution. Require every attempt's dataset hash, the code diff, and independent-reviewer sign-off before re-generation; forbid changing quotas or motifs (as opposed to bugs). (ii) D17 smoke test: running V3 on ≤ 20 pilot-tag scenarios whose generator may then change is a (mild) forking path; the same assurance is available by running `observe()/intervene()/validators` only, or by testing the new runner on frozen dev/val. Recommend dropping D17. (iii) "first complete run is reported" (PRE §7): define "complete" (all methods × all scenarios with a record; error rows count as records). (iv) Bootstrap rerun at B = 100,000 "with the same seed rule" (SAP §3): specify the seed and that only the p-vs-CI disagreement triggers it; B = 20,000 and seed 4505 are fixed — fine. (v) `drift_stat`: DSP §5.3 says "observed non-ancestor x ≠ y" but does not say whether ancestry is computed on the full true graph (including hidden nodes) as in `sprint440_cid_audit.py` or the observed subgraph; specify, and specify handling when no such x exists.
* **P2-d. Seed-collision wording** (DSP §4): 2000 × 252 / 2³¹ ≈ 2×10⁻⁴ is right; fine, but the candidate-skip rule is not applied against dynamics/content hashes of readable sets in the QC order. Minor.
* **P2-e. PRE §9 vs SAP §7 thresholds** (95 % completeness, per-method "integrity stop") are consistent; the stop for *one comparator* shouldn't void the V3 vs AA result. State that H1 is evaluated on V3 completeness only.
* **P2-f. SAP §3 percentile/CR1 sensitivity**: with K ≈ 10–16 the CR1 t(K−1) interval is wide and the percentile bootstrap undercovers; decide in advance which governs if they conflict (the SAP says the studentised result governs; keep).

---

## P3 — MINOR

* PRE §3.5 / AUD §3.4: "V3 − AA significant only at λ = 0.25 (κ ≤ 0.025) and λ = 0.5 with κ = 0" is consistent with the grid, but "V3 beats AA only when λ ≲ 0.9 and κ ≈ 0" (PRE §3.5) conflates the point break-even (0.938 at κ = 0) with significance (CI of V3−AA at λ = 1, κ = 0: [−0.08, 0.06]). Say "point estimate positive for λ < 0.94 at κ = 0".
* AUD §3.4 notes the method ordering "was computed at κ = 0 only"; fine.
* The sensitivity grid is 8 × 4 = 32 cells; the claim "label function takes the primary only" is the right protection; add that no cell outside the primary may be described as "significant".
* CID §7 compute estimate (≈ 20 CPU-hours): my timing of `compute_cid` (n = 30, 1000 perms, 100 boots) is 5.8 ms/call, consistent with the doc's 6.2 ms; fine.
* DSP §8.2 argues sealed-set independence from "template ids disjoint by the public rule in `cell_split`". This is sound for template/structure/joint-cell keys; the near-duplicate argument ("categorical component capped at 0.514 …") depends on `spec_similarity`'s structure; the doc is honest that it is argued, not measured (PRE L6 fine).
* AUD §4.2: "Abstention rate … variance of D depends on this rate": the per-reason stratum SDs are 0.88 (ATTRIBUTE) and 0.93 (ABSTAIN); a pooled 0.969 slightly overestimates the fixed-quota SD (SE 0.0204 vs 0.0217, ≈ 6 %): harmless conservatism.

---

## Answers to the lead's questions (a)–(j)

**(a)** H1 is testable; the estimand (mean U over the quota mix vs AA = 0) is clean but entirely normative (λ, γ, δ) and dev/val say it fails; see P1-6a. Informative additions listed there.

**(b)** Utility: strict-unsafe counting lucky-correct answers as unsafe is defensible as a precaution but is partly an artefact of an arbitrary 4σ-vs-3σ label margin (P1-5); the label function reuses RIFT's own R1 (3σ, persist 2) and CID-power (≥ 1σ at n = 30) criteria, so ABSTAIN_REQUIRED is partly definitional. Simulator-derived labels are not an independent notion of "evidence insufficient".

**(c)** Power: formula correct and reproduced; DEFF argument invalid at m = 125 (P1-3); N = 2000 is neither obviously too small (fixed structures) nor adequate (random structures: MDE 0.197 regardless of N). The inference is **design-based over a fixed set of structures only if stated**; it is not stated.

**(d)** Independence/generalisability: P0-1 (hash space, T5), P1-7 (V3-tuned categories, author knowledge), P1-6c (≥ 25 % drift stratum is only +4 pp over dev/val at scenario level). Not generalisable beyond a designed stress set.

**(e)** Label leakage: `strip_labels` removes only `ground_truth` and `design`; `faults`, `dimensions`, `graph`, `template_id` survive, but **are not passed to V3/V2/baselines** in the existing call paths (`run_v3(o, iv, fid, seed)`; `make_context` uses `scenario_id` and `seed` only; ORACLE rows use `ground_truth` by design). So no direct leak in the current code, but T8 doesn't prove it, and node order leaks (P1-4).

**(f)** CID: identification caveats are correctly stated; unequal information/exposure for E1/E2/E6; eligibility rule mis-calibrated; V0 target noisy; duplicate cells; B4/B7/B10 outside simulator (P1-8).

**(g)** Misleading POSITIVE paths: none looks likely for H1 (V3 would need precision > 2/3 and low cost). Plausible *wrong-reason* paths: a generator bug that makes WEAK_SIGNAL/NO_DISCRIMINATING scenarios trivially abstainable; drift-stratum contrast read as "robustness" (P1-6b); trivial abstain scenarios dilute the mean (INSUFFICIENT_BASELINE 180 + NO_FAULT 100 ≈ 14 % of N with V3 answer rate 0–8 %); NEGATIVE-WORSE can be driven by the label margin (P1-5). Grid forking cannot change the primary label.

**(h)** Post-hoc degrees of freedom remaining: runner and error mapping (P1-4), unit definition/fallback when K is small (P0-1), motif/quota edits between attempts (P2-c), `drift_stat` ancestry definition, "complete run", D17. Stopping rules and amendment pattern are otherwise good.

**(i)** Reproducibility: evidence is **one machine** (Darwin arm64, Python 3.9.6, local venv). CI (`.github/workflows/test.yml`) runs ubuntu + Python 3.11 + `pip install -r requirements.txt` (not the canonical lock), comment "Expected: 624 passed". `pyproject.toml` in the working tree read `requires-python = ">=3.9"` at review time (uncommitted modification, presumably by Agent 5 during this sprint; not my edit) whereas HEAD says `>=3.10`, and PRE §2.5/D13 describe the `>=3.10` state. The 663 vs 664 discrepancy is "recorded and not a failure" but unexplained. Numerical results involving BLAS-backed FCI/linear algebra were not shown to be bit-identical across platforms. "Reproducible" claims should read "reproduced on one macOS-arm64 environment".

**(j)** Language: forbidden phrases occur only inside prohibitions (grep verified in all five docs + plan). Caveat P2-b (DEFINITIVE_ROOT, "safe"). The prereg correctly uses "intervention-consistent" and "validated on synthetic ground-truth scenarios".

---

## Items I could not verify (honest limits)

* Whether node insertion order changes V2/V3 outputs (requires running them; out of scope).
* Whether the final generator's periphery rule matches my enumeration (DSP §3.2 is under-specified); the pigeonhole bound depends on the 0–3-node periphery wording.
* Dev/val numbers are used throughout; no confirmatory inference follows from any of them.
* No external reviewer exists; this review has the same blind spots as the authoring team's tooling.

## Suggested minimum changes before PRE §13 (recording)

1. Resolve P0-1 and P0-2 (geometry/unit; full freeze closure and tracked files).
2. State the estimand and the cluster unit (P1-3); re-power accordingly.
3. Preregister and hash the runner; fix error semantics; strengthen T8; add T10 (node order) (P1-4).
4. Document label circularity and margin; decide on the SNR band (P1-5).
5. Add pair-level robustness endpoint and fix the drift-stratum premise (P1-6).
6. Make the quota table consistent (P1-7).
7. Recalibrate the CID eligibility rule; correct the "same data" claim (P1-8).
8. Researcher approval of D1–D18, A1–A9; name the independent reviewer (D7); owner-run protected verification (D12).
