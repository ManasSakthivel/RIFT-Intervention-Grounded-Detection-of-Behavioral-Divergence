# Ablation Framework Audit
Phase: parallel-sprint
Auditor: Agent 4

---

## Executive Summary

```
ABLATIONS_AUDITED:  8
WELL_DEFINED:       5
ISSUES:             7
```

**Summary:** The three primary ablations (RIFT-OBS, RIFT-RANDOM, RIFT-FULL) are implemented
and scientifically well-defined. RIFT-ONE-SHOT is correctly specified but **BLOCKED** — the
required file `src/rift/baselines/rift_one_shot.py` does not exist and must be created before
EXP-013 can run. Three deferred ablations (RIFT-NO-CID, RIFT-NO-EBD, RIFT-ALT-GRAPH) are
well-specified but unimplemented; they do not block the current sprint. RIFT-NO-MSIS is a
verified duplicate of RIFT-RANDOM with no independent experiment. One cross-document
inconsistency exists in the H2 experiment mapping between `hypotheses.md` and the ablation
registry.

---

## Per-Ablation Analysis

---

### RIFT-FULL

WHAT CHANGES:
  Nothing. All 7 components enabled. Reference condition against which all
  ablations are compared.

WHAT REMAINS IDENTICAL:
  fci_graph_learning, identifiability_check, msis_cost_selection,
  network_intervention, cid_scoring, ebd_scoring, closed_loop_update — all active.

WHAT IS MEASURED:
  Primary:   Precision@1, Conditional Precision@1
  Secondary: Coverage, abstention_rate, false_attribution_rate,
             mean_detection_latency_s, total_ed_s

WHY FAIR:
  This is the reference; all ablations are defined relative to it.
  Receives the same IncidentContext as every other ablation.

IMPLEMENTATION STATUS: IMPLEMENTED
EXPERIMENT: EXP-001 (primary), also appears as comparator in EXP-005, EXP-006, EXP-013, EXP-014
HYPOTHESIS: H1 (primary), H2, H3, H4 (as comparator)
ISSUE: None.

---

### RIFT-OBS

WHAT CHANGES:
  Three components disabled relative to RIFT-FULL:
  - msis_cost_selection: false   (no candidate scoring for intervention)
  - network_intervention: false  (no intervention dispatched)
  - cid_scoring: false           (no Wasserstein divergence — no data to score)
  - closed_loop_update: false    (no posterior update — nothing to update)
  NOTE: ebd_scoring remains ENABLED; FCI graph learning remains ENABLED.

WHAT REMAINS IDENTICAL:
  fci_graph_learning, identifiability_check, ebd_scoring.
  Receives identical IncidentContext (same metrics, same call graph, same window).

WHAT IS MEASURED:
  Primary:   Precision@1, Conditional Precision@1 (on confounded subset C_confounded)
  Secondary: detection_latency_s

WHY FAIR:
  H2 asks whether ANY intervention adds value over an observational causal model.
  The four disabled components (MSIS, intervention dispatch, CID scoring,
  closed-loop update) are all causally downstream of the decision to intervene:
  there is nothing to cost-rank, execute, score, or update if no intervention
  occurs. Disabling all four together is scientifically correct because they form
  a single functional unit — the intervention layer. This is NOT a multi-component
  ablation; it is a single-layer ablation of the entire intervention mechanism.
  The causal graph (FCI) and EBD remain active so that the observational model is
  as strong as possible, making the comparison maximally conservative.

IMPLEMENTATION STATUS: IMPLEMENTED
  File: src/rift/baselines/rift_obs.py — RIFTObsBaseline
  Confirmed: network_intervention dispatches zero interventions
  (total_intervention_ed_s hardcoded to 0.0). CID scores explicitly not passed to
  EBD (cid_results=None). Closed-loop update not present in run() flow.
  NOTE: Observational backdoor scoring is marked PARTIAL (Phase 3 uses correlation
  proxy, not true do-calculus estimation). Full implementation deferred to Phase 8.
  This does not block EXP-005 but affects the strength of the H2 comparison.

EXPERIMENT: EXP-005
HYPOTHESIS: H2
ISSUE (minor): Observational score is a Pearson correlation proxy, not a true
  backdoor-adjustment estimate. The notes in rift_obs.py correctly label this
  PARTIAL. This must be resolved before the Phase 10 final evaluation.
  SEVERITY: LOW — does not block EXP-005 but weakens the H2 comparison validity.
  REQUIRED_ACTION: Implement true backdoor adjustment in Phase 8 as documented.

---

### RIFT-RANDOM

WHAT CHANGES:
  One component replaced:
  - msis_cost_selection: false → replaced with RandomMSIS (uniform random selection)
  All other components (FCI, identifiability, intervention dispatch, CID, EBD,
  closed-loop update) remain enabled.

WHAT REMAINS IDENTICAL:
  fci_graph_learning, identifiability_check, network_intervention, cid_scoring,
  ebd_scoring, closed_loop_update. Same eligibility rules, same budget, same
  entropy stopping condition (theta_entropy=0.5).

WHAT IS MEASURED:
  Primary:   total_ed_s (cumulative execution duration)
  Secondary: Precision@1, n_interventions

WHY FAIR:
  Exactly one substitution: greedy utility maximization → uniform random selection.
  RandomMSIS preserves the stopping condition and posterior update structure
  (confirmed in rift_random.py RandomMSIS.select()). The only difference is
  the selection criterion, so any cost difference is attributable solely to MSIS.

IMPLEMENTATION STATUS: IMPLEMENTED
  File: src/rift/baselines/rift_random.py — RIFTRandomBaseline / RandomMSIS
  CAVEAT: The run() method in RIFTRandomBaseline passes cid_results=None to
  compute_ebd(), meaning CID scoring is not active in this implementation despite
  the registry declaring cid_scoring: true. This is a discrepancy.
  The registry says RIFT-RANDOM has cid_scoring enabled, but the code does not
  pass real CID results into EBD. This may reflect that real interventions are
  not dispatched in the current run() stub (total_intervention_ed_s=0.0 returned),
  which means no CID data is available to pass.

EXPERIMENT: EXP-006 (ablation), EXP-014 (H4 cost model effectiveness)
HYPOTHESIS: H4
ISSUE (moderate): Implementation passes cid_results=None to compute_ebd despite
  registry declaring cid_scoring: true. If the intent is to dispatch real
  interventions with random selection, the run() method needs to actually execute
  interventions and collect CID results.
  SEVERITY: MODERATE — does not block EXP-006 P@1 comparison, but invalidates
  the total_ed_s measurement if interventions are not actually dispatched.
  REQUIRED_ACTION: Confirm whether RIFT-RANDOM should dispatch real interventions
  (with random selection) or simulate them. If real, wire CID collection into run().

---

### RIFT-ONE-SHOT

WHAT CHANGES:
  One component disabled:
  - closed_loop_update: false
  Initial candidate ranking from G_T is used for all subsequent intervention
  selections. Posterior is NOT updated after each observation.

WHAT REMAINS IDENTICAL:
  fci_graph_learning, identifiability_check, msis_cost_selection,
  network_intervention, cid_scoring, ebd_scoring. All components active.
  Interventions are still executed; MSIS still scores them — but the scoring
  uses the INITIAL posterior for every selection round.

WHAT IS MEASURED:
  Primary:   Precision@1 (on multi-cause / ambiguous fault scenarios)
  Secondary: n_interventions_to_attribution, detection_latency_s

WHY FAIR:
  Exactly one component disabled: the Bayesian posterior update between
  successive interventions. MSIS still selects interventions — it just uses
  the original prior for every round instead of the updated posterior.
  Tests whether the iterative refinement (not the intervention itself) adds value.

IMPLEMENTATION STATUS: NOT_IMPLEMENTED — BLOCKED
  Required file: src/rift/baselines/rift_one_shot.py — DOES NOT EXIST
  (confirmed: not present in src/rift/baselines/ directory)
  Agent 1 has NOT created this file as of this audit.
  EXP-013 status in REGISTRY.yaml is "READY_FOR_LINUX" — this is INCORRECT
  given the file is absent. The experiment cannot run.

EXPERIMENT: EXP-013
HYPOTHESIS: H3
ISSUE (CRITICAL): rift_one_shot.py does not exist. EXP-013 is marked
  READY_FOR_LINUX in REGISTRY.yaml but is BLOCKED. This blocks H3 validation.
  SEVERITY: CRITICAL — blocks EXP-013, prevents H3 from being tested.
  REQUIRED_ACTION: Create src/rift/baselines/rift_one_shot.py implementing
  RIFTOneShotBaseline. The class must run the full intervention pipeline but
  freeze the posterior after the first selection (use initial candidate ranking
  for all subsequent MSIS calls). Must implement BaselineInterface.run().
  Additionally, EXP-013 status in REGISTRY.yaml should be corrected from
  READY_FOR_LINUX to PENDING_IMPLEMENTATION until the file exists.

---

### RIFT-NO-CID

WHAT CHANGES:
  One component disabled:
  - cid_scoring: false (Wasserstein W1 divergence measurement skipped)
  Interventions are still dispatched; EBD R4 criterion falls back to anomaly
  score only (no distributional shift confirmation).

WHAT REMAINS IDENTICAL:
  fci_graph_learning, identifiability_check, msis_cost_selection,
  network_intervention, ebd_scoring, closed_loop_update.

WHAT IS MEASURED:
  Primary:   Precision@1 (attribution accuracy without CID confirmation)
  Secondary: false_attribution_rate, abstention_rate

WHY FAIR:
  Exactly one component removed: the Wasserstein divergence measurement.
  All other components — including intervention dispatch — remain active.
  This isolates the contribution of distributional shift confirmation to
  attribution accuracy.

COULD THREATEN MAIN CLAIMS:
  If RIFT-NO-CID ≈ RIFT-FULL: CID scoring adds no measurable value, weakening
  the N4 novelty claim. This is a real risk. However, N4 is listed as a Phase 9
  deferred claim, so it does not threaten Phase 5 paper submission claims (N1–N3,
  N5). Deferral is correctly sequenced.

IMPLEMENTATION STATUS: NOT_IMPLEMENTED — DEFERRED to Phase 9
  Required file: src/rift/baselines/rift_no_cid.py — DOES NOT EXIST
  Correctly labeled as deferred. Does not block current sprint.

EXPERIMENT: Not yet assigned (deferred; no EXP-XXX entry for Phase 9 CID ablation)
HYPOTHESIS: N/A (tests N4 novelty claim, not a named hypothesis)
ISSUE (minor): No Phase 9 experiment ID assigned in REGISTRY.yaml for RIFT-NO-CID.
  SEVERITY: LOW — deferred, but should be pre-registered before Phase 9 begins.
  REQUIRED_ACTION: Add EXP-015 (or equivalent) to REGISTRY.yaml during Phase 9
  planning.

---

### RIFT-NO-EBD

WHAT CHANGES:
  One component disabled:
  - ebd_scoring: false (behavioral divergence detection skipped)
  Attribution is based on CID scores and MSIS selection alone; no EBD
  candidate filtering applied.

WHAT REMAINS IDENTICAL:
  fci_graph_learning, identifiability_check, msis_cost_selection,
  network_intervention, cid_scoring, closed_loop_update.

WHAT IS MEASURED:
  Primary:   Precision@1 (attribution without EBD pre-filtering)
  Secondary: abstention_rate, false_attribution_rate

WHY FAIR:
  Exactly one component removed: EBD divergence detection. The intervention
  engine still runs; CID still scores; MSIS still selects. Tests whether EBD's
  candidate pre-filtering is necessary for accurate attribution.

COULD THREATEN MAIN CLAIMS:
  If RIFT-NO-EBD ≈ RIFT-FULL: EBD adds no independent value, weakening N4.
  Same sequencing argument as RIFT-NO-CID applies — deferred correctly.
  More serious risk: if RIFT-NO-EBD outperforms RIFT-FULL, EBD is net-negative
  (false candidate elimination). This would require investigating EBD thresholds.

IMPLEMENTATION STATUS: NOT_IMPLEMENTED — DEFERRED to Phase 9
  Required file: src/rift/baselines/rift_no_ebd.py — DOES NOT EXIST
  Correctly labeled as deferred.

EXPERIMENT: Not yet assigned
HYPOTHESIS: N/A (tests N4 novelty claim)
ISSUE (minor): Same as RIFT-NO-CID — no Phase 9 experiment ID assigned.
  SEVERITY: LOW — deferred.
  REQUIRED_ACTION: Add EXP-016 (or equivalent) to REGISTRY.yaml during Phase 9
  planning.

---

### RIFT-NO-MSIS

WHAT CHANGES:
  One component disabled:
  - msis_cost_selection: false → random selection (same as RIFT-RANDOM)

WHAT REMAINS IDENTICAL:
  All other components — identical to RIFT-RANDOM configuration.

WHAT IS MEASURED:
  Same metrics as RIFT-RANDOM: total_ed_s, Precision@1, n_interventions.

WHY FAIR:
  N/A — see DUPLICATION ANALYSIS below.

IMPLEMENTATION STATUS: IMPLEMENTED (via RIFT-RANDOM — no separate implementation)
  Registry notes: "Equivalent to RIFT-RANDOM. Use EXP-006 results."
  No separate EXP-XXX assigned. RIFT-RANDOM is the canonical condition.

EXPERIMENT: EXP-006 (shared with RIFT-RANDOM)
HYPOTHESIS: H4

DUPLICATION ANALYSIS:
  RIFT-NO-MSIS and RIFT-RANDOM are identical in component configuration:
  both disable only msis_cost_selection and replace it with uniform random
  selection. The registry explicitly acknowledges this ("Equivalent to
  RIFT-RANDOM. Use EXP-006 results.") and assigns no separate experiment.
  
  WHY TWO ENTRIES EXIST: The two names reflect different FRAMING intentions —
  RIFT-RANDOM was originally defined as "a standalone observational baseline
  with no interventions" (from the B-series perspective), while RIFT-NO-MSIS
  was defined as "the ablation of the MSIS cost optimization component."
  However, in the current registry, both resolve to the same configuration.
  
  RISK: Having two named conditions pointing to the same experiment creates
  citation ambiguity in the paper. Any table or figure that lists both
  RIFT-RANDOM and RIFT-NO-MSIS separately would misrepresent them as
  independent comparisons.

ISSUE (moderate): RIFT-NO-MSIS is a registry duplicate of RIFT-RANDOM.
  SEVERITY: MODERATE — naming ambiguity risk in paper tables.
  REQUIRED_ACTION: Deprecate RIFT-NO-MSIS as a distinct ablation label.
  In all paper tables, use RIFT-RANDOM exclusively. Add a footnote in the
  ablation table noting that "RIFT-NO-MSIS ≡ RIFT-RANDOM (same configuration)."
  Consider removing or collapsing the RIFT-NO-MSIS registry entry to avoid
  future confusion.

---

### RIFT-ALT-GRAPH

WHAT CHANGES:
  One component replaced:
  - fci_graph_learning: false → replaced with correlation-based DAG
  FCI-PAG is not run; a simpler correlation threshold DAG is used as G_T.
  All downstream components receive the weaker graph structure.

WHAT REMAINS IDENTICAL:
  identifiability_check, msis_cost_selection, network_intervention,
  cid_scoring, ebd_scoring, closed_loop_update.

WHAT IS MEASURED:
  Primary:   Precision@1 (attribution with simpler causal graph)
  Secondary: Conditional Precision@1, abstention_rate

WHY FAIR:
  Exactly one substitution at the graph learning stage. All downstream
  components receive the same interface (a graph G_T); they are unaware of
  how it was produced. Tests whether FCI's latent-confounder representation
  (via bidirected edges) is necessary for accurate attribution, or whether
  a simpler correlation DAG is sufficient.

COULD THREATEN MAIN CLAIMS:
  If RIFT-ALT-GRAPH ≈ RIFT-FULL: FCI adds no advantage over simple correlation,
  weakening N1 (the core algorithmic novelty claim about FCI-PAG for confounded
  microservices). This is a genuine scientific risk. However, RIFT-ALT-GRAPH is
  deferred to Phase 9, so it does not affect Phase 5 submission. If this ablation
  shows equivalence at Phase 9, the N1 claim must be reconsidered.
  NOTE: This is the highest-stakes deferred ablation for the paper's core claims.

IMPLEMENTATION STATUS: NOT_IMPLEMENTED — DEFERRED to Phase 9
  Required file: src/rift/baselines/rift_alt_graph.py — DOES NOT EXIST
  Correctly labeled as deferred.

EXPERIMENT: Not yet assigned
HYPOTHESIS: N/A (tests N1 novelty claim)
ISSUE (minor): No Phase 9 experiment ID assigned in REGISTRY.yaml.
  SEVERITY: LOW — deferred, but highest scientific risk among deferred ablations.
  REQUIRED_ACTION: Add EXP-017 (or equivalent) during Phase 9 planning.
  Ensure the correlation DAG implementation is specified in detail before Phase 9
  to avoid under-specified ablation.

---

## Component Isolation Analysis

The table below shows which of the 7 RIFT components is changed (✗) vs. unchanged (✓)
for each ablation condition. A well-isolated ablation changes exactly one component.

| Ablation        | FCI  | ID-Check | MSIS | Intervention | CID  | EBD  | Closed-Loop | # Changed |
|-----------------|------|----------|------|--------------|------|------|-------------|-----------|
| RIFT-FULL       |  ✓   |    ✓     |  ✓   |      ✓       |  ✓   |  ✓   |      ✓      |     0     |
| RIFT-OBS        |  ✓   |    ✓     |  ✗   |      ✗       |  ✗   |  ✓   |      ✗      |     4     |
| RIFT-RANDOM     |  ✓   |    ✓     |  ✗*  |      ✓       |  ✓   |  ✓   |      ✓      |     1     |
| RIFT-ONE-SHOT   |  ✓   |    ✓     |  ✓   |      ✓       |  ✓   |  ✓   |      ✗      |     1     |
| RIFT-NO-CID     |  ✓   |    ✓     |  ✓   |      ✓       |  ✗   |  ✓   |      ✓      |     1     |
| RIFT-NO-EBD     |  ✓   |    ✓     |  ✓   |      ✓       |  ✓   |  ✗   |      ✓      |     1     |
| RIFT-NO-MSIS    |  ✓   |    ✓     |  ✗*  |      ✓       |  ✓   |  ✓   |      ✓      |     1     |
| RIFT-ALT-GRAPH  |  ✗†  |    ✓     |  ✓   |      ✓       |  ✓   |  ✓   |      ✓      |     1     |

`✗*` = replaced (not simply disabled); `✗†` = replaced with correlation DAG

**Key:** FCI=fci_graph_learning, ID-Check=identifiability_check, MSIS=msis_cost_selection,
         Intervention=network_intervention, CID=cid_scoring, EBD=ebd_scoring

---

## Scientific Validity Assessment

### RIFT-OBS: 4-component change — is it a fair ablation?

RIFT-OBS disables 4 components simultaneously (MSIS, intervention, CID, closed-loop).
This is scientifically correct because these 4 components form a single functional unit:
the intervention layer. Each disabled component is causally dependent on the preceding one:
- Without intervention dispatch → no CID data exists to score
- Without CID data → closed-loop update has no signal
- Without intervention → MSIS cost-ranking serves no purpose

The 4 components are not independently meaningful when interventions are absent.
Disabling all 4 together is the minimal correct ablation for H2 (testing whether
ANY intervention adds value). Any subset ablation (e.g., "keep MSIS but disable
dispatch") would produce an incoherent system state, not a valid baseline.

**Verdict: FAIR.** The scientific justification is sound. The audit concurs with the
registry note that this tests whether the entire intervention mechanism adds value.

### All other ablations: 1-component change

RIFT-RANDOM, RIFT-ONE-SHOT, RIFT-NO-CID, RIFT-NO-EBD, RIFT-NO-MSIS, RIFT-ALT-GRAPH
each change exactly one component. These are properly isolated ablations.

---

## Implementation Readiness

| Ablation       | Status          | Blocker                                                       |
|----------------|-----------------|---------------------------------------------------------------|
| RIFT-FULL      | IMPLEMENTED     | None (awaits Linux deployment)                                |
| RIFT-OBS       | IMPLEMENTED     | Backdoor scoring is PARTIAL; full impl required for Phase 10  |
| RIFT-RANDOM    | IMPLEMENTED     | CID not wired in run(); confirm intervention dispatch intent   |
| RIFT-ONE-SHOT  | NOT_IMPLEMENTED | `rift_one_shot.py` does not exist — CRITICAL BLOCKER          |
| RIFT-NO-CID    | DEFERRED        | Deferred to Phase 9; no current blocker                       |
| RIFT-NO-EBD    | DEFERRED        | Deferred to Phase 9; no current blocker                       |
| RIFT-NO-MSIS   | IMPLEMENTED     | Duplicate of RIFT-RANDOM; no separate file needed             |
| RIFT-ALT-GRAPH | DEFERRED        | Deferred to Phase 9; correlation DAG not specified            |

---

## Issues Found

### ISSUE-1: RIFT-ONE-SHOT file missing (CRITICAL)
DESCRIPTION: `src/rift/baselines/rift_one_shot.py` does not exist. EXP-013 is
  marked READY_FOR_LINUX in REGISTRY.yaml but cannot run without this file.
  Agent 1 has not created it as of this audit.
SEVERITY: CRITICAL
REQUIRED_ACTION: Create rift_one_shot.py implementing RIFTOneShotBaseline.
  Freeze posterior after initial MSIS selection; use same posterior for all
  subsequent intervention rounds. Implement BaselineInterface.run().
  Correct EXP-013 status from READY_FOR_LINUX to PENDING_IMPLEMENTATION.

### ISSUE-2: EXP-013 status incorrectly set to READY_FOR_LINUX (HIGH)
DESCRIPTION: experiments/REGISTRY.yaml lists EXP-013 status as READY_FOR_LINUX
  but the required baseline (RIFT-ONE-SHOT) is not implemented. This is a false
  readiness signal that could cause premature Linux execution attempts.
SEVERITY: HIGH
REQUIRED_ACTION: Change EXP-013 status to PENDING_IMPLEMENTATION in REGISTRY.yaml.

### ISSUE-3: H2 experiment mapping inconsistency (HIGH)
DESCRIPTION: `docs/hypotheses.md` maps H2 to EXP-009 ("Ablation: intervention
  necessity — the critical experiment"). However, EXP-009 in `experiments/REGISTRY.yaml`
  is actually "Performance instrumentation: stage timing" — a completely different
  experiment with no hypothesis link. The ablation registry and ABLATION_PLAN.md
  correctly map H2 to EXP-005. The hypotheses.md reference to EXP-009 for H2 is
  a stale or erroneous cross-reference.
SEVERITY: HIGH — creates a misleading H2→EXP-009 link in the authoritative
  hypothesis document.
REQUIRED_ACTION: Update `docs/hypotheses.md` to map H2 to EXP-005 (and EXP-002
  for the confounded subset), consistent with ABLATION_PLAN.md.

### ISSUE-4: RIFT-RANDOM run() does not dispatch interventions (MODERATE)
DESCRIPTION: `rift_random.py` RIFTRandomBaseline.run() returns
  total_intervention_ed_s=0.0 and passes cid_results=None to compute_ebd().
  The registry defines RIFT-RANDOM with network_intervention: true and
  cid_scoring: true. If real interventions are not dispatched, the total_ed_s
  metric (primary H4 metric) will be zero for RIFT-RANDOM, making cost comparison
  with RIFT-FULL meaningless.
SEVERITY: MODERATE — primary H4 metric may be invalid
REQUIRED_ACTION: Clarify intent. If RIFT-RANDOM should dispatch real interventions
  (with random selection), wire intervention execution and CID collection into run().
  If it is a dry-run stub, update the registry to reflect network_intervention: false.

### ISSUE-5: RIFT-NO-MSIS is a registry duplicate of RIFT-RANDOM (MODERATE)
DESCRIPTION: RIFT-NO-MSIS and RIFT-RANDOM have identical component configurations.
  No separate implementation or experiment exists for RIFT-NO-MSIS. The registry
  itself notes "Equivalent to RIFT-RANDOM. Use EXP-006 results." Having both
  entries risks paper table duplication errors.
SEVERITY: MODERATE
REQUIRED_ACTION: Deprecate RIFT-NO-MSIS as a distinct ablation label. Use
  RIFT-RANDOM as the single canonical name in all paper tables. Add a registry
  note cross-referencing the equivalence explicitly. Do not present them as
  independent conditions in any results table.

### ISSUE-6: RIFT-OBS observational scoring is a proxy, not true backdoor adjustment (LOW)
DESCRIPTION: `rift_obs.py` _observational_scores() uses Pearson correlation
  (mean z-score) as a proxy for P(Y | do(X)) rather than true backdoor adjustment.
  The code correctly labels this PARTIAL and defers to Phase 8. However, this
  means H2 validation in Phase 5 will compare RIFT-FULL against a weaker RIFT-OBS
  implementation than the paper will ultimately present.
SEVERITY: LOW (deferred correctly; does not block EXP-005)
REQUIRED_ACTION: Implement true do-calculus backdoor adjustment for RIFT-OBS
  in Phase 8, before final Phase 10 evaluation. Disclose proxy scoring in any
  interim experimental results.

### ISSUE-7: Deferred ablations lack assigned Phase 9 experiment IDs (LOW)
DESCRIPTION: RIFT-NO-CID, RIFT-NO-EBD, and RIFT-ALT-GRAPH are deferred to Phase 9
  but have no corresponding EXP-XXX entries in REGISTRY.yaml. Pre-registration
  of experiments is important for preventing specification drift.
SEVERITY: LOW (deferred correctly; does not block current sprint)
REQUIRED_ACTION: During Phase 9 planning, add EXP-015, EXP-016, EXP-017
  (or next available IDs) to REGISTRY.yaml for the three deferred ablations.

---

## Status

**BLOCKED**

The parallel sprint cannot fully proceed to Linux execution for H3 because
RIFT-ONE-SHOT is not implemented (ISSUE-1) and EXP-013 is falsely marked
READY_FOR_LINUX (ISSUE-2). All other sprint-critical ablations (RIFT-OBS,
RIFT-RANDOM) are implemented and ready for Linux deployment pending T1+T2+T3 fixes.

**Conditions for PASS:**
1. Create `src/rift/baselines/rift_one_shot.py` (ISSUE-1)
2. Correct EXP-013 status in REGISTRY.yaml to PENDING_IMPLEMENTATION (ISSUE-2)
3. Fix H2 experiment reference in docs/hypotheses.md from EXP-009 to EXP-005 (ISSUE-3)
4. Clarify RIFT-RANDOM intervention dispatch intent (ISSUE-4)
