# Sprint 4.3.0 — Failure Taxonomy

> Evidence: `artifacts/sprint4_3_0/failure_taxonomy_evidence.json`, produced by `scripts/sprint430_failure_analysis.py` and rendered
> by `python3 scripts/sprint430_build_docs.py`. Held-out figures are read from the **saved** held-out result (the held-out set was run
> once and is not re-run). Mechanism analysis (section 3) was done by re-running the **unchanged** RIFT-FULL-V2 configuration on
> **dev and val only**; held-out mechanisms are therefore *not* claimed.
> All numbers are on **synthetic ground-truth scenarios**.

## 0. Wording correction

The request referred to "14 downstream errors among the 20 incorrect ATTRIBUTE answers". The data say something slightly different, and
the corrected statement is used throughout:

> Of the **45** held-out ATTRIBUTE scenarios, RIFT-FULL-V2 **abstained on 11**, **answered 34**, of which **20 were correct and 14 were
> wrong**. **All 14 wrong answers named a service downstream of the true root** (14/14), and all 14 carried a SEMI_DIRECTED path.

So: 14 wrong answers out of 34 answered (41 %), all downstream-of-root — not "14 of 20 incorrect". (The 20 is the number of *correct* answers.)

## 1. Taxonomy summary

Categories 2, 5-11 are defined by the scenario's declared design features and overlap (a scenario can sit in several). Categories 1, 3
and 4 are defined by the observed outcome of V2. Counts are for RIFT-FULL-V2 on the held-out set (n = 108) unless stated.

| # | Category | Held-out count (definition below) | Class |
|---|---|---|---|
| 1 | Downstream misattribution | **14** wrong answers (of 34 answered on ATTRIBUTE) | methodological limitation (R3 + FCI sparsity) |
| 2 | Earliest-divergence ambiguity | 7 scenarios; 4 unsafe | inherent identifiability limit (+ rule limitation) |
| 3 | Semi-directed graph ambiguity | 56 of 57 answers are SEMI_DIRECTED; all 14 wrong answers | methodological limitation |
| 4 | Insufficient intervention evidence | 4 abstentions `INTERVENTION_NOT_VERIFIED` + 7 lost-coverage in weak-effect cases | methodological limitation / inherent |
| 5 | Non-identifiable cases | 20 scenarios; 8 unsafe | inherent identifiability limitation |
| 6 | Confounding | 20 scenarios; 6 ATTRIBUTE, P1 2/6 | inherent + methodological |
| 7 | Multiple simultaneous causes | 36 scenarios; 15 ATTRIBUTE, P1 10/15 | methodological |
| 8 | High-variance behaviour | 13 scenarios; 3 unsafe; 0 ATTRIBUTE | benchmark design coupling + inherent |
| 9 | Weak intervention effects | 46 scenarios; 17 ATTRIBUTE, P1 3/17 | methodological limitation |
| 10 | Insufficient telemetry | 38 scenarios; 15 ATTRIBUTE, P1 7/15 | inherent identifiability limitation (+ defect candidates) |
| 11 | Recovery anomalies | 34 scenarios; 16 ATTRIBUTE, P1 7/16 | methodological limitation |

## 2. Held-out outcomes behind the numbers

### 2.1 Answered / abstained / correct / wrong on ATTRIBUTE scenarios

{{TABLE:tax_wrong}}

Held-out wrong-answer scenario ids (all downstream of the true root): {{TABLE:wrong_ids}}.

dev and val show the same pattern: **every wrong ATTRIBUTE answer in every split is downstream of the true root and SEMI_DIRECTED**
(dev 14/14, val 13/13, held-out 14/14). There are no wrong answers naming another faulted service or an unrelated service.

### 2.2 Abstentions on ATTRIBUTE scenarios (lost coverage)

{{TABLE:abstain_attr}}

Held-out ids: INSUFFICIENT_BASELINE V2H-0002, V2H-0012, V2H-0065, V2H-0097; INTERVENTION_NOT_VERIFIED V2H-0023, V2H-0055, V2H-0068,
V2H-0105; NO_CANDIDATES V2H-0015, V2H-0074; NOT_IDENTIFIABLE V2H-0031.

### 2.3 Unsafe answers on ABSTAIN_REQUIRED scenarios (by the label's abstention reason)

{{TABLE:label_reason}}

Held-out ids: WEAK_SIGNAL V2H-0003, V2H-0011, V2H-0018, V2H-0029 (+8); SYMMETRIC_MUTUAL_DEPENDENCY V2H-0005, V2H-0008, V2H-0016, V2H-0027
(+2); ROOT_UNOBSERVED V2H-0019, V2H-0076, V2H-0096; NO_DISCRIMINATING_EVIDENCE V2H-0048, V2H-0050. In 10 of the 23 held-out
unsafe answers the named service *is* a true root, yet the answer is still unsafe by definition: the label requires abstention
because the evidence cannot support the claim.

### 2.4 Path kind

{{TABLE:pathkind}}

"answered (any label)" includes answers on ABSTAIN_REQUIRED scenarios, where "correct" is always false, so this is **not** a
path-kind accuracy. It does show that essentially every V2 answer rests on a SEMI_DIRECTED (not fully oriented) PAG path (held-out 56 of 57).

## 3. Mechanisms behind wrong ATTRIBUTE answers (dev and val only)

{{TABLE:tax_mech}}

Mechanism definitions: M1 the true root never exceeds the R1 divergence rule; M2 the true root diverges (R1) but fails R3 because the
learned PAG gives it no path to a diverging service; M3 the true root was intervened but R4 did not confirm; M4 the true root was a
candidate but was never intervened or was explained away by another candidate.

**Reading.** The dominant mechanism is **M2 with the true root isolated in the learned PAG**: FCI returns no adjacent edge for it (dev 8
of 14, val 5 of 13 wrong answers). A later downstream node that does have a PAG path then passes R3 and is confirmed by a simulated
do(), because a downstream node can show interventional influence on its own descendants. That is how a downstream service gets
named even though the true root diverged *earlier* (dev 9/14, val 7/13). The oracle-graph ablation A9 raises held-out P1 from 20/45
to 32/45 (exploratory), which is consistent with a graph-quality bottleneck. It does not prove that this mechanism explains the held-out failures; that would require
re-running held-out, which is not permitted.

## 4. Per-category analysis

**Evidence status of the "Root cause" lines.** Only Category 1 (and the Category 3 statement about SEMI_DIRECTED paths) rests on a measured
mechanism analysis (section 3, dev/val). The "Root cause" lines for Categories 2 and 4-11 are **hypotheses consistent with the rule definitions and the
saved outcome counts**; they were not separately diagnosed per scenario and are not established mechanisms.

Per-category numbers (V2, held-out; categories overlap):

{{TABLE:tax_cat}}

Same table on the validation split (for consistency checking):

{{TABLE:tax_cat_val}}

### Category 1 — Downstream misattribution
* **Definition.** V2 answers with a service that is a descendant of the true root while the true root exists and the scenario's
  expected outcome is ATTRIBUTE.
* **Count.** 14 wrong answers / 34 answered ATTRIBUTE scenarios (held-out); dev 14/42; val 13/21. 14/14, 14/14, 13/13 downstream.
* **Representative ids.** V2H-0001, V2H-0010, V2H-0028, V2H-0033, V2H-0035, V2H-0051, V2H-0060, V2H-0061, V2H-0067, V2H-0078, V2H-0082,
  V2H-0084, V2H-0098, V2H-0103.
* **Root cause (dev/val evidence).** True root fails R3 (isolated or leaf-like in the learned PAG) while a downstream node passes R3 and
  R4. The interventional "explained" bookkeeping only discounts nodes confirmed from an intervened candidate, so an earlier
  divergence on an R3-failing node is silently ignored (this is the observation behind Amendment 3).
* **Type.** Methodological limitation of the R3 + FCI-sparsity combination; **not** a code defect in the sense of a wrong
  implementation of the specified rules.
* **Remediation (not done, no tuning permitted after the freeze).** (a) Treat an earlier-diverging, R3-failing service as unresolved
  evidence (this is the V2G idea: abstain, which lowered held-out unsafe from 37 to 18 but also P1 from 20/45 to 14/45 and coverage from 57 to 32 of 108);
  (b) improve graph discovery (more windows, better CI tests, domain priors) and re-evaluate on a new fresh held-out;
  (c) allow R3 to be satisfied by a *bidirected / unoriented* adjacency rather than requiring a path to a diverging service, only with new held-out evidence.
* **False-attribution risk of remediation.** Relaxing R3 would let isolated, spuriously diverging nodes become candidates: more false
  attributions. Abstaining (V2G) cuts attribution accuracy. No remedy that "forces a root cause answer" is proposed.

### Category 2 — Earliest-divergence ambiguity
* **Definition.** Scenarios with negative kinds `earliest_not_root`, `indistinguishable_onsets`, `coincidental_anomaly`, where the first
  diverging service is not the root or onsets cannot be separated.
* **Count.** 7 held-out scenarios (3 ATTRIBUTE): V2 P1 1/3, unsafe 4/7 (2 wrong root, 2 unsafe on ABSTAIN_REQUIRED). Dev 12, val 6.
* **Ids.** V2H-0028, V2H-0040, V2H-0048, V2H-0084 (failing).
* **Root cause.** V2's ordering still uses earliest t* among confirmed candidates; when the onsets are within one window or an unrelated
  anomaly precedes the fault, earliest-first yields the wrong name. Interventional confirmation does not break the tie because a
  downstream node also confirms. This is consistent with H4 being unsupported (A6/A8 are no worse), but the hypothesised mechanism itself was not diagnosed.
* **Type.** Inherent identifiability limitation for `indistinguishable_onsets` / `coincidental_anomaly`; methodological limitation for
  `earliest_not_root`.
* **Remediation.** Require a minimum onset separation (in windows) before ordering by t*, otherwise abstain; use do()-based
  *necessity* tests (does removing the candidate remove the downstream effect?) rather than influence tests only.
* **Risk.** An onset-separation threshold is a new tunable parameter; setting it on this corpus would leak. It should be fixed on fresh development data.

### Category 3 — Semi-directed graph ambiguity
* **Definition.** The path from the attributed service to the diverging services in the PAG contains circle-mark endpoints (SEMI_DIRECTED).
* **Count.** Held-out: 56 of 57 answers are SEMI_DIRECTED; all 14 wrong answers; 19 of 56 answered SEMI_DIRECTED were correct (counting
  answers on all labels; not an accuracy). dev 80 SEMI_DIRECTED answers (28 correct), val 35 (8 correct).
* **Root cause.** FCI on the short incident window usually returns partially oriented PAGs; semi-directed reachability is only
  evidence of *possible* ancestry. V2 reports confidence 0.80 for SEMI_DIRECTED, but this number is a reported constant, not a
  calibrated probability.
* **Type.** Methodological limitation (and a known property of FCI outputs).
* **Remediation.** Report confidence only as ordinal, never as a probability; require interventional confirmation (already done)
  and demote SEMI_DIRECTED answers lacking sufficient CID effect.
* **Risk.** Demotion reduces coverage; an implicit threshold would again need a fresh development set.

### Category 4 — Insufficient intervention evidence
* **Definition.** V2 abstains `INTERVENTION_NOT_VERIFIED` (no candidate confirmed by R4), or the effect is too small relative to noise.
* **Count.** 4 held-out abstentions on ATTRIBUTE (dev 15, val 5). Cases with weak/imperfect interventions: 46 scenarios, 17 ATTRIBUTE, P1 3/17, 7 lost coverage.
* **Ids.** V2H-0023, V2H-0055, V2H-0068, V2H-0105 (abstained); V2H-0002, V2H-0005, V2H-0010, V2H-0011 (weak-effect failures).
* **Root cause.** Perturbation amplitude `magnitude_sigma x sigma x delivered fraction` can be below the Bonferroni-corrected permutation
  test's detection ability. The simulator has no control arm, so non-stationary faults add spurious CID too. Every R4 check has grade
  `CANDIDATE` (held-out 531/531; dev 555/555; val 314/314); interventional evidence rests on the strict `validate_cid_for_r4` plus a corrected permutation test.
* **Type.** Methodological limitation; the abstention itself is the correct, conservative behaviour.
* **Remediation.** Longer perturbation windows or repeated perturbations within the safety budget; a control arm.
* **Risk.** More perturbations increase intervention cost; relaxing the corrected test increases false confirmation.

### Category 5 — Non-identifiable cases
* **Definition.** Labels `SYMMETRIC_MUTUAL_DEPENDENCY`, `NO_DISCRIMINATING_EVIDENCE`, negative `root_not_identifiable`.
* **Count.** 20 held-out scenarios, 0 ATTRIBUTE, 8 unsafe answers, V2 P2 12/20. Label-reason view: SYMMETRIC_MUTUAL_DEPENDENCY 6 unsafe of 13, NO_DISCRIMINATING_EVIDENCE 2 of 7.
* **Ids.** V2H-0005, V2H-0008, V2H-0016, V2H-0027, V2H-0048, V2H-0050.
* **Root cause.** Two nodes in a mutual dependency cannot be separated by temporal order or by a do() on either; the label says abstain.
  V2 does not always detect this because its identifiability check is run on one earliest-candidate -> outcome pair only.
* **Type.** Inherent identifiability limitation (not fixable without extra structural assumptions or an external intervention that breaks the symmetry).
* **Remediation.** Extend the identifiability check to all candidate pairs; abstain when two candidates are mutually reachable.
* **Risk.** Over-abstaining on genuine DAG chains if reachability is read as "mutual".

### Category 6 — Confounding
* **Definition.** Structures `confounding`, `hidden_common_cause`, negative `common_cause_several_services`.
* **Count.** 20 held-out scenarios, 6 ATTRIBUTE, P1 2/6, 1 wrong root, 5 unsafe on ABSTAIN_REQUIRED, 3 lost coverage.
* **Ids.** V2H-0002, V2H-0003, V2H-0018, V2H-0019, V2H-0031, V2H-0065.
* **Root cause.** A hidden common cause makes children co-diverge with no observed parent; the FCI PAG includes bidirected edges, and
  V2 still names an observed child (interventions on children influence only their descendants).
* **Type.** Inherent identifiability limitation when the cause is unobserved (`ROOT_UNOBSERVED`), plus a methodological limitation
  (the answer should abstain).
* **Remediation.** Reject candidates with bidirected edges to other diverging services unless a do() confirms them as source.
* **Risk.** Over-rejecting real roots that are involved in confounded pairs.
* **Note.** This benchmark does not show that RIFT "solves confounding"; held-out performance on the confounded strata is weak.

### Category 7 — Multiple simultaneous causes
* **Definition.** Scenarios with >= 2 faults, `multiple_upstream`, `overlapping_faults` temporal pattern.
* **Count.** 36 held-out scenarios, 15 ATTRIBUTE, P1 10/15 (the best P1 of any difficult stratum), 4 wrong root, 8 unsafe on ABSTAIN_REQUIRED.
* **Ids.** V2H-0010, V2H-0011, V2H-0033, V2H-0038, V2H-0040, V2H-0048.
* **Root cause.** V2 returns a single top-1 root; with several true roots only one is named and the "explained" bookkeeping may merge them.
  P1 counts any member of the root set as success, so 10/15 does not mean V2 recovers all causes.
* **Type.** Methodological limitation (single-answer output).
* **Remediation.** Evaluate and report multi-root recovery (set-level precision/recall).
* **Risk.** Adds a new metric after the freeze; must be pre-registered for the next milestone.

### Category 8 — High-variance behaviour
* **Definition.** Workload `high_baseline_variance` (sigma 20 ms) or negative `high_variance_no_fault`.
* **Count.** 13 held-out scenarios, **0 ATTRIBUTE** (by design: absolute amplitude vs larger sigma gives SNR < 4), V2 coverage 3/13, unsafe 3/13.
* **Ids.** V2H-0003, V2H-0040, V2H-0057.
* **Root cause.** WEAK_SIGNAL labels. The three unsafe cases are V2 answers on scenarios the label says should abstain.
* **Type.** Benchmark design coupling (amplitude is absolute) and an inherent SNR limitation. **It does not test a variance-aware detector.**
  The cell shows only that V2 mostly abstains; its attribution accuracy under high variance is untested (no ATTRIBUTE scenario).
* **Remediation.** A new factorial dimension crossing variance with a relative-amplitude fault, so high-variance ATTRIBUTE scenarios exist.
* **Risk.** None to existing results; new scenarios require a new freeze.

### Category 9 — Weak intervention effects
* **Definition.** Negative `weak_intervention_effects`, intervention modes `no_meaningful_effect`, `low_magnitude`, `imperfect`, observability `weak_interventional_evidence`.
* **Count.** 46 held-out scenarios, 17 ATTRIBUTE, **P1 3/17**, 7 wrong root, 6 unsafe on ABSTAIN_REQUIRED, 7 lost coverage.
* **Ids.** V2H-0002, V2H-0005, V2H-0010, V2H-0011, V2H-0023, V2H-0031.
* **Root cause.** Where perturbation has little effect, R4 cannot confirm the true root; downstream nodes whose own causal path is
  stronger can still confirm. V2 therefore loses coverage or answers downstream.
* **Type.** Methodological limitation (V2 treats absence of confirmation as evidence for the next candidate rather than as lack of power).
* **Remediation.** Power-aware R4: if a candidate's intervention was under-powered, treat it as unresolved, not rejected.
* **Risk.** Requires a power estimate; mis-specified power would let weak interventions confirm.

### Category 10 — Insufficient telemetry
* **Definition.** Observability `insufficient_samples`, `missing_windows`, `partial_service_observability`.
* **Count.** 38 held-out scenarios, 15 ATTRIBUTE, P1 7/15, 3 wrong root, 6 unsafe on ABSTAIN_REQUIRED, 5 lost coverage.
  `insufficient_samples` scenarios: 12, 0 ATTRIBUTE, V2 abstained on all 12 (**coverage 0/12**).
* **Ids.** V2H-0003, V2H-0015, V2H-0019, V2H-0031, V2H-0035, V2H-0042; abstained on ATTRIBUTE with INSUFFICIENT_BASELINE: V2H-0002, V2H-0012, V2H-0065, V2H-0097.
* **Root cause.** Too few baseline windows or rows for FCI, or the root unobserved.
* **Type.** Inherent identifiability limitation. The 12/12 result for `insufficient_samples` is correct abstention, not capability.
* **Remediation.** Not applicable for the unobserved-root case; for gaps, better imputation validated on fresh development data.
* **Risk.** Aggressive imputation would fabricate signal.

### Category 11 — Recovery anomalies
* **Definition.** Family `recovery_instability` (held-out only) and temporal patterns `partial_recovery`, `recovery_delay`, and the negative `incomplete_recovery_after_normalisation`.
* **Count.** 34 held-out scenarios, 16 ATTRIBUTE, P1 7/16, 5 wrong root, 7 unsafe on ABSTAIN_REQUIRED, 4 lost coverage; the `recovery_instability` family alone: n = 18,
  P1 5/8, P2 11/18, unsafe 6/18.
* **Ids.** V2H-0002, V2H-0012, V2H-0016, V2H-0029, V2H-0033, V2H-0040.
* **Root cause.** The persistence detector assumes a sustained excursion; rebounds and partial recoveries break R1 persistence for part of the window.
  The simulator's rollback is complete and the 30 s recovery is a model constant, so these cells do not test *real* recovery behaviour.
* **Type.** Methodological limitation, small n, unseen family.
* **Remediation.** Evaluate on recovery-aware windowing against fresh data.
* **Risk.** Over-fitting to the simulator's recovery shape.

## 5. Other attributed failure modes

* **Multiple causes / V2G.** The V2G amendment reduced held-out unsafe from 37/108 to 18/108 but P1 from 20/45 to 14/45 and coverage from 52.8 % to 29.6 %.
  This is a safety/coverage trade-off, not a fix; it is exploratory.
* **Feedback-like structures (unseen).** n = 24, P1 4/13, unsafe 8/24, coverage 12/24 (V2); legacy RIFT-FULL P1 4/13, B6 6/13. Small n; not inferential.

## 6. Defect vs limitation vs inherent

| Class | Categories | What it means for next work |
|---|---|---|
| Implementation defect | none demonstrated in this sprint | no code defect was found in V2 rules as specified |
| Methodological limitation | 1, 3, 4, 7, 9, 11 (and part of 2, 6) | design changes need fresh development data and a new freeze |
| Inherent identifiability limitation | 2 (part), 5, 6 (unobserved), 10 | correct behaviour is to abstain |
| Benchmark design coupling | 8 | needs a new dimension, not a method change |

## 7. Caveats

* The category columns overlap; summing them over-counts scenarios.
* "Root cause" statements for Categories 2 and 4-11 are hypotheses (see section 4 preface).
* Held-out mechanism claims are intentionally withheld. All mechanism evidence is from dev/val; held-out is consistent with the same pattern in the saved outcomes (all wrong answers downstream and SEMI_DIRECTED) but is not independently diagnosed.
* No remediation above has been implemented or evaluated; none may be tuned on the existing held-out set.
