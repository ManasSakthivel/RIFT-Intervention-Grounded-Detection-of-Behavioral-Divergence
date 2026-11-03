# Sprint 4.4.0 — Root-Cause Attribution Failure Investigation and Causal Directionality: Final Report

## Verdict: **PARTIAL PASS**

Sprint 4.4.0 produced real engineering and diagnostic results and a new method (RIFT-FULL-V3) that makes **fewer unsafe and fewer wrong-root
answers than RIFT-FULL-V2 on the dev and val splits**. It did **not** establish that V3 attributes root causes better than a trivial policy:
V3's gain in correct-root accuracy (P1) is not statistically significant on either split, V3's overall outcome score (P2) is **not
significantly better than the always-abstain baseline**, and V3 remains less safe than always-abstain (35/180 and 13/72 unsafe answers
versus 0). Most of V3's safety gain comes from declining to answer. Nothing here validates RIFT for real systems or for any held-out data,
and RIFT must **not** be described as validated, production-ready, or causally accurate.

Companion documents:
`docs/SPRINT4_4_0_ATTRIBUTION_FAILURE_ANALYSIS.md`, `docs/SPRINT4_4_0_FCI_GRAPH_QUALITY.md`, `docs/SPRINT4_4_0_CAUSAL_DIRECTIONALITY.md`,
`docs/SPRINT4_4_0_CID_EVIDENCE_ANALYSIS.md`, `docs/SPRINT4_4_0_V3_DESIGN.md`. Artifacts: `artifacts/sprint4_4_0/`.

Scope: offline, synthetic, **dev (180) and val (72) only**. The Sprint 4.3.0 held-out set was not opened, read or run. No live intervention.
Everything below is "validated on synthetic ground-truth scenarios" and "intervention-consistent" in the simulator's sense only.

## 1. Headline result (always-abstain baseline included)

Reproduced from the saved artifacts (`artifacts/sprint4_4_0/v3_{dev,val}.json`, `analysis.json`) **and independently** from the Sprint 4.3.0
saved V2 outputs (`artifacts/sprint4_3_0/results/{dev,val}/per_scenario.json`) — see §3.

| | Dev V2 | Dev V3 | **Dev always-abstain** | Val V2 | Val V3 | **Val always-abstain** |
|---|---:|---:|---:|---:|---:|---:|
| P1 correct root (of ATTRIBUTE) | 28/68 | 32/68 | 0/68 | 8/31 | 13/31 | 0/31 |
| P2 correct outcome (answer-or-abstain) | 102/180 | 116/180 | **112/180** | 35/72 | 44/72 | **41/72** |
| Unsafe answers | 52 | 35 | **0** | 27 | 13 | **0** |
| Coverage (answered) | 80 | 67 | 0 | 35 | 26 | 0 |
| Wrong root on ATTRIBUTE | 14 | 7 | – | 13 | 3 | – |
| Conditional accuracy on answered ATTRIBUTE | 28/42 | 32/39 | – | 8/21 | 13/16 | – |

This is exactly the table requested for audit; every cell matches. The always-abstain row is not an appendix item: it scores P2 = 112/180 (62.2%)
on dev and 41/72 (56.9%) on val, **above V2 on both splits** and within a few points of V3.

Other V3 configurations (dev / val): V3-DEFINITIVE-ONLY P1 23/68 and 10/31, P2 114 and 42, unsafe 25 and 12, coverage 48 and 22, wrong root 4 and 3.
V2 with the **oracle** graph: P1 39/68 and 19/31, P2 104 and 41, unsafe 51 and 22. Legacy RIFT-FULL: P1 25/68 and 15/31, P2 81 and 36, unsafe 86 and 28.

## 2. Summary of what was found

1. **Defect D1 (confirmed, V2 frozen, fixed only in V3).** `fci_runner._decode_pag_edges` mis-decodes `o->`; a collider `X→Z←Y` is reported UNDIRECTED and `_pag_to_digraph` then lets Z "reach" X and Y. Test: `test_mark_convention_matches_causal_learn_on_a_collider`.
2. **The learned graph is a poor ancestry signal.** Skeleton F1 0.52 (dev) / 0.45 (val); 97–98% of edges circle-marked; 1–2 fully directed edges across both splits.
3. **V2's wrong roots were all downstream descendants** of the true root (14/14 dev, 13/13 val), via semi-directed evidence. The dominant cause (8/14 dev, 5/13 val): FCI isolated the true root so it was never a candidate.
4. **V3** (graph-agnostic candidates, positive control, Holm, symmetry check, source rule, earlier-divergence guard, explicit statuses) reduces unsafe and wrong roots and raises P1/P2 modestly. It costs ~1.7× more interventions.
5. **CID** is capped at CANDIDATE (30 samples per arm) and has no concurrent control arm. The "94% spurious" figure reproduces (16/17 dev, 17/17 val) but is a **conditional rate on a 17-pair drift stratum**; clean non-ancestral pairs show 4–7%.
6. **Adversarial development evaluation** (112 scenarios, 14 types): V3 unsafe 7 vs V2 24; wrong root 0 vs 7. 7 unsafe answers remain, all on the unobserved-root type.

## 3. Audit of the statistics

**Denominators.** Dev: 180 scenarios = 68 ATTRIBUTE + 112 ABSTAIN_REQUIRED. Val: 72 = 31 + 41. P1's denominator is ATTRIBUTE scenarios only;
P2 and unsafe use all scenarios; coverage = answered / all.

**Independent reproduction.** The V2 scores re-computed from Sprint 4.3.0's saved `per_scenario.json` — not from the Sprint 4.4.0 run — give the same V2 cells
(dev P1 28/68, P2 102, unsafe 52, coverage 80; val 8/31, 35, 27, 35). Re-deriving the discordant counts from those two files gives the numbers below, identical to `analysis.json`.
The saved Sprint 4.3.0 V2 outputs were also re-run on three scenarios by `test_v2_reproduces_saved_sprint430_outputs` and match.

**Paired V3-FULL vs V2 (same scenarios; exact two-sided McNemar on discordant pairs).** `only_V3` / `only_V2` = scenarios where only that method is correct (or safe).

| metric | split | n | V3 | V2 | diff (V3−V2) | 95% CI (as saved) | only V3 / only V2 | exact p (uncorrected) | Holm (6 tests) |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|
| P1 | dev | 68 | 32 | 28 | +0.059 | [−0.065, 0.190] | 12 / 8 | 0.503 | 0.503 |
| P1 | val | 31 | 13 | 8 | +0.161 | [0.000, 0.355] | 7 / 2 | 0.180 | 0.359 |
| P2 | dev | 180 | 116 | 102 | +0.078 | [0.006, 0.150] | 29 / 15 | 0.0488 | 0.195 |
| P2 | val | 72 | 44 | 35 | +0.125 | [0.013, 0.243] | 13 / 4 | 0.0490 | 0.195 |
| P3_safe (not unsafe) | dev | 180 | 145 | 128 | +0.094 | [0.028, 0.166] | 29 / 12 | 0.0115 | 0.0575 |
| P3_safe | val | 72 | 59 | 45 | +0.194 | [0.069, 0.333] | 17 / 3 | 0.0026 | 0.0155 |

(Holm applied here by the auditor across these six V3-vs-V2 tests as one family; the saved artifacts contain the uncorrected p-values. Because
the six tests are not independent — three metrics on the same scenarios — Holm is a reasonable but not exact correction. The CIs are `ci95_quoted_widest` from `stats_v2.compare_pair`: the wider of the scenario-clustered and template-clustered bootstrap intervals for the risk difference.
The saved `descriptive_only` flag (fewer than 10 discordant pairs) is set for val P1 (9 discordant pairs); that cell is descriptive.)
Effect sizes as discordant-pair odds ratios: P2 dev 29/15 = 1.9, val 13/4 = 3.3; P3_safe dev 29/12 = 2.4, val 17/3 = 5.7; P1 dev 1.5, val 3.5 (CIs include 1).

**Dev and val agree in direction on every metric** (V3 ≥ V2), and in significance only for safety: P3_safe significant on both splits uncorrected, and after
Holm only on val (0.0155; dev 0.0575 is not below 0.05). P2 sits at p ≈ 0.049 on both splits, and **does not survive correction** (0.195). P1 is not significant on either.

**What the p-values mean:** under the null that discordant pairs are equally likely in each direction, the chance of a split at least this lopsided.
They describe these 180 and 72 synthetic scenarios. They do **not** show a general improvement, do not account for the researchers' freedom
(V3's components were developed on dev and V3 was looked at on val), and the scenarios within a template/structure family are not fully independent.
Dev and val are both development data, so there is **no confirmatory test**.

**Paired V3-FULL vs always-abstain:**

| metric | split | V3 − AA | 95% CI | only V3 / only AA | exact p |
|---|---|---:|---|---:|---:|
| P2 | dev | +0.022 | [−0.061, 0.107] | 32 / 28 | **0.699** |
| P2 | val | +0.042 | [−0.097, 0.192] | 13 / 10 | **0.678** |
| P1 | dev / val | +0.471 / +0.419 | – | 32/0, 13/0 | <0.001 / 0.0002 (trivial: AA has no attributions) |
| P3_safe | dev / val | −0.194 / −0.181 | [−0.256, −0.137] / [−0.286, −0.087] | 0/35, 0/13 | 5.8e-11 / 0.0002 (AA is safer by construction) |

**V3 does not beat always-abstain on P2**; the two are statistically indistinguishable and the point estimates favour V3 by only 4 (dev) and 3 (val) scenarios
in net discordant count. V2 is *below* always-abstain on P2 on both splits (−0.056 dev, −0.083 val; p = 0.27, 0.29). The P1 and safety contrasts
against always-abstain are significant only because that policy never answers.

**Coverage-matched comparison (both V2 and V3 answered):** dev 52 scenarios, V3 correct 26 vs V2 23; val 23 scenarios, V3 12 vs V2 7. V3-only answered: dev 15 (9 unsafe), val 3 (2 unsafe);
V2-only answered: dev 28 (23 unsafe), val 12 (11 unsafe). So the safety gain is mostly V3 **not answering** scenarios that V2 answered unsafely, not V3 answering better.

**V3-DEFINITIVE-ONLY vs V2:** safety +0.150 (dev, p = 1.4e-5) and +0.208 (val, p = 0.0015); P2 +0.067 / +0.097 (p = 0.096 / 0.14); P1 −0.074 / +0.065 (p = 0.36 / 0.73).

**Subgroups.** Per-structure P1 (dev; V2 / V3 / oracle graph): diamond 3/6/4, multiple_upstream 1/4/4, shared_dependency 5/6/7, branching 5/3/7, converging 3/2/3,
linear_chain 6/6/7, parallel_independent 3/3/5, confounding 2/2/2. Val: confounding 2/4/4, linear_chain 1/3/4, converging 1/0/2, branching 3/2/3. V3 is mixed by structure and cells have 3–11 scenarios; no
subgroup claim is supported.

## 4. Candid assessment: are V3's extra interventions and complexity justified?

**Partly, as a research artefact; not established as a deployment improvement.**

For: fewer wrong roots (14→7 dev, 13→3 val); unsafe answers 52→35 and 27→13; P3_safe significant on both splits uncorrected and on val after Holm;
conditional accuracy on answered ATTRIBUTE scenarios 32/39 and 13/16 vs 28/42 and 8/21; all-divergent candidates repair the "root isolated by FCI" failure; the design
is leakage-tested and isolated from the frozen pipeline.

Against: P1 not significant; P2 not distinguishable from doing nothing; V3 does not match the oracle-graph P1 (32/68 vs 39/68; 13/31 vs 19/31) so
graph error still costs accuracy; unsafe rate still 19% (35/180) and 18% (13/72) while a trivial policy has none; the `DEFINITIVE_ROOT` label is ~50% unsafe; 1.7–1.9× more interventions
(2.51 vs 1.49 dev, 3.19 vs 1.71 val per scenario) and 1.7–1.9× more experiment time (75 s vs 45 s, 96 s vs 51 s); in a real system each is an intervention on a live service. Whether the safety gain is worth
the added intervention cost depends on the (unmeasured) cost of an unsafe attribution versus an intervention, which this sprint cannot supply.

The honest reading: V3 is a **better-behaved decision rule** (it abstains more appropriately and avoids the specific descendants-as-roots failure) with unproven accuracy benefits.

## 5. Adversarial development evaluation (not independent external validation)

112 hand-designed scenarios = 14 failure-mode types × 8 variants (80 ATTRIBUTE, 32 ABSTAIN_REQUIRED), generated with `split="adv_dev"`, new seeds from a distinct hash tag,
labels from `generator_v2.compute_ground_truth` (noise-free simulator state, never from a method). `datasets/rift_v3_dev/adversarial_dev.json`, sha256 `3525bc05…2472`.

| method | correct | answered | unsafe | wrong root |
|---|---:|---:|---:|---:|
| V2 | 57 | 81 | **24** | **7** |
| V3-FULL | 67 | 74 | **7** | **0** |
| V3-DEFINITIVE-ONLY | 62 | 69 | 7 | 0 |
| V3-NO-SYMMETRY-CHECK | 69 | 85 | 16 | 0 |

Correct root named on the 80 ATTRIBUTE scenarios: V3 67 (83.8%), V2 57 (71.3%); ABSTAIN_REQUIRED scenarios cannot be "correct" by answering, so the "correct" column counts ATTRIBUTE scenarios only.
Per type: A01, A02, A04 both 8/8; A03 (delayed propagation) V2 3/7 (4 wrong) vs V3 8/8; A05 (confounding) V2 7/8 vs V3 8/8; A06 V3 8/8; A07 (weak intervention) both answer none (0/8 lost);
A08, A10 V3 7/7 (V2 7/8 with 1 unsafe); A09 both abstain; A11 (isolated root) V2 1/1 answered vs V3 5/5; A13 (mutual dependency) V2 8/8 unsafe vs V3 0; A14 (strong anomalies, hidden common cause) V2 1 unsafe vs V3 0.

**The 7 remaining unobserved-root cases (A12, 7/7 unsafe for V3, 8/8 for V2)** are an **identifiability boundary**: the true root has no telemetry, so every observed
service is a descendant, and an observed descendant that is an interventional source among the observed services is indistinguishable, in the data available, from the root.
The unit test `test_unobserved_root_cannot_be_distinguished_is_documented_limitation` pins this behaviour. A decision rule cannot resolve it; only a different observation (e.g. coverage of the hidden service) or an external
prior could. Reporting these as V3 failures understates the distinction — but reporting them as success would be wrong, so they are counted as unsafe.

**What the adversarial set does and does not establish.** It shows that V3's rules handle specific failure patterns *that were identified on dev*, and that V3 is not worse than V2 on them.
Structural overlap with dev: the adversarial scenarios use the same simulator, noise model, fault generator and a subset of the same graph families (small chains, branches, diamonds); they were designed *after* inspecting dev failures; the 8 variants per type are
parameter variations of one design and are **not independent samples**. It is therefore **adversarial development evaluation, not independent external validation**, and it provides no estimate of performance on unseen systems.

## 6. Answers to the ten questions

1. **Did we improve skeleton recovery?** No. FCI was not changed. We *measured* it: precision 0.675 / 0.622, recall 0.424 / 0.355, F1 0.52 / 0.45, SHD 298 / 216 (dev / val; 138/180 and 58/72 scenarios with a PAG). V3 reduces the *dependence* on the skeleton rather than improving it.
2. **Can FCI reliably orient edges?** No, not on these data: 97.8% (dev) / 97.0% (val) of learned edges are circle-marked; 1 / 2 are fully directed; of 6 / 9 oriented true edges, 0 / 1 were oriented correctly. We did not determine why.
3. **Why did V2 select downstream services?** V2 selected a descendant in every one of its 27 wrong-root cases. Mechanisms: FCI isolated the true root (8 dev, 5 val), so only descendants were candidates; descendants have real confirmed effects on further descendants; semi-directed reachability was symmetric and carried no direction; the root's anomaly was smaller than the descendant's in 6/14 and 9/13; and V2 had no check that an upstream cause existed. A decoding defect (D1) aggravated reachability but, when removed alone, changed V2 by ≤ 1 scenario.
4. **Does V3 reduce unsafe attribution?** Yes on dev/val relative to V2: 52→35 and 27→13 unsafe; wrong roots 14→7 and 13→3; adversarial 24→7. Significant uncorrected on both splits; after Holm, on val only. But unsafe stays far above always-abstain's zero, and much of the reduction is increased abstention (coverage 80→67, 35→26).
5. **Does V3 significantly improve correct root attribution?** No. P1 +4/68 (p = 0.50) and +5/31 (p = 0.18). P2 improvements are at the 0.05 boundary uncorrected and do not survive Holm (0.195). V3 improves accuracy among answered cases (32/39 vs 28/42), which is a selective-prediction effect, not a P1 gain.
6. **Does V3 beat always-abstain?** On P2: **no** (dev +0.022, p = 0.70; val +0.042, p = 0.68). On P1: trivially yes. On safety: no (always-abstain is safer by construction). The only sense in which V3 is better is that it sometimes names a correct root, which always-abstain never does.
7. **Is CID powered enough for causal confirmation?** No. All 555 + 314 CID rows are CANDIDATE with 30 samples per arm; RELIABLE needs n ≥ 50 and is unreachable with the 30 s do() window. Sensitivity for true-ancestor pairs is ~10% below 0.25σ, ~49% at 0.5–1σ and ≥ 87% at ≥ 1σ; MC power at 0.5σ is ~49% (m = 1) and ~29% (m = 3). There is no concurrent control arm, so drift in an outcome service yields spurious confirmations (§3.2 of the CID doc).
8. **What does the adversarial evaluation establish?** That V3 avoids the specific failure patterns (downstream-largest anomaly, delayed propagation, mutual dependency, hidden common cause) which were identified on dev, better than V2, on 112 constructed variants — and that unobserved roots are beyond what the decision rule can resolve. It does not provide independent evidence of generalisation.
9. **What claims can legitimately be made today?** See §7.
10. **What is the next scientifically justified experiment?** See §9.

## 7. Claims that can and cannot be made

**Supported (qualified):**
* "On 252 synthetic ground-truth development scenarios (dev + val), the V3 decision rule made fewer unsafe and fewer wrong-root attributions than V2, with no significant gain in correct-root accuracy."
* "The frozen FCI decoder drops arrowheads on `o->` edges (defect D1, demonstrated on a collider test); corrected decoding is in the V3 module only."
* "On these data the learned PAG is sparse (recall 0.35–0.42), almost entirely unoriented (97–98% circle edges) and its semi-directed reachability is not a reliable ancestry signal."
* "The simulated CID check, with 30 samples per arm and no concurrent control, can only reach the CANDIDATE grade, has ~50% power at 0.5σ, and is susceptible to drift-induced false confirmations in the subset of scenarios whose outcome service has time-varying fault contribution."
* "V3 outputs are intervention-consistent for the simulator's interventions; its status names do not denote causal certainty."

**Not supported:** that RIFT or V3 is validated, production-ready or causally accurate; that V3 beats always-abstain; that p-values on dev/val are confirmatory; that PAG edges or reachability indicate causal ancestry;
that `DEFINITIVE_ROOT` is definitive; that results transfer to real telemetry, other topologies, or the held-out set; that the Stage 4 live-experiment findings (a separate, historical result) are affected one way or the other.

## 8. Separation of concerns

| dimension | status |
|---|---|
| **Engineering correctness** | Good. D1 diagnosed and demonstrated; V3 isolated; 34 new tests; full suite 880 passing; V2 and 37 frozen files unmodified (`verify_freeze` OK). |
| **Evaluation integrity** | Good, bounded. Dev/val only; held-out seal 4/4; no thresholds tuned; leakage tests; V2 reproduced from saved outputs. But dev informed V3's design and val was inspected, so dev/val are not confirmatory; uncorrected p-values in `analysis.json`; the adversarial set was authored after seeing dev failures. |
| **Attribution performance** | Modest. P1 28→32/68, 8→13/31, not significant; P2 not distinguishable from always-abstain; below oracle-graph P1. |
| **Safety performance** | Improved but insufficient. Unsafe 52→35 and 27→13; adversarial 24→7; 19% / 18% unsafe versus 0 for abstaining; DEFINITIVE answers ~50% unsafe; unobserved-root cases remain. |
| **Causal evidence quality** | Weak. All CID grades CANDIDATE; ~50% power at 0.5σ; no control arm; drift contamination; graph barely oriented. |
| **External validity** | None demonstrated. One simulator and generator; no held-out run of V3; no real traces. |

## 9. Remaining blockers and the next research step

**Blockers:** (a) no unbiased confirmatory evaluation of V3; (b) CID design limits (n = 30, no control arm); (c) FCI orientation; (d) unobserved roots; (e) V3's `DEFINITIVE_ROOT` naming; (f) intervention cost.

**Next scientifically justified step.** A **pre-registered confirmatory experiment on new, independently generated synthetic data** (not the closed Sprint 4.3.0 held-out set, whose
seal this sprint left intact): freeze V3 and the analysis plan (including the always-abstain baseline as the primary comparator, P2 and unsafe as co-primary metrics, a Holm family and the number of scenarios chosen by power analysis from the discordant-pair rates above); then
in a separate, pre-registered *design* sub-experiment test (i) a longer simulated do() window (n ≥ 50 so RELIABLE is reachable) and (ii) a concurrent control arm or detrended CID to see whether the drift-stratum false-positive rate falls from ~94% toward ~5% without losing power. Only after
those would a live Stage 4 follow-up be justified.

## 10. Reproducibility
```
python3 scripts/sprint440_trace_failures.py     # failure_traces_{dev,val}.json
python3 scripts/sprint440_run_v3.py             # v3_{dev,val}.json (dev/val only)
python3 scripts/sprint440_analyze.py            # analysis.json, graph_quality.csv
python3 scripts/sprint440_cid_audit.py          # cid_audit.json
python3 scripts/sprint440_adversarial.py        # adversarial dataset + results
python3 -m pytest -q -p no:cacheprovider -W ignore
python3 scripts/verify_heldout_sealed.py
```
Dev/val pins: `dev.json` a833ad0c…ef5f (180), `val.json` e82252b4…a1fb (72). All seeds are fixed; V3 is deterministic (`test_v3_deterministic`).
