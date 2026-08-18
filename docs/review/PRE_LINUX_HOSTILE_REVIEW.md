# Pre-Linux Hostile Review
**Phase:** Parallel Mac-Side Completion Sprint
**Reviewers:** 6 hostile ICSE reviewers (Causal / DistSys / SE / Empirical / PriorArt / Repro)
**Prior review:** docs/phase3_5/hostile_review.md (Phase 3.5 — do not duplicate; extend only)
**Authority:** docs/hypotheses.md, docs/CLAIMS_REGISTRY.yaml, docs/causal_assumptions.md,
               docs/intervention_semantics.md, experiments/REGISTRY.yaml

---

## Executive Summary

| Severity | Count | Description |
|---|---|---|
| **P0** | **5** | Paper-invalidating — must fix before submission |
| **P1** | **12** | Major concern — likely major revision |
| **P2** | **9** | Minor concern — minor revision or disclosure |
| **Total** | **26** | |

**Overall verdict: NOT READY FOR SUBMISSION.**
Linux execution is necessary but not sufficient. Several structural scientific issues
must be resolved before the paper can be submitted regardless of Linux results.

---

## P0 Issues — Paper-Invalidating

---

### ISSUE P0-01: EXP-013 (H3) Is Not Executable — Registry Claims Otherwise

**REVIEWER:** Reviewer 4 (Empirical Methodology)
**SEVERITY:** P0

**ISSUE:**
`experiments/REGISTRY.yaml` marks EXP-013 as `status: READY_FOR_LINUX`. However, the
RIFT-ONE-SHOT baseline required to run EXP-013 was, as of the start of this sprint,
`NOT_IMPLEMENTED` (confirmed in `experiments/ablations/ABLATION_REGISTRY.yaml`).
A status of `READY_FOR_LINUX` implies that when Linux is available, the experiment
can immediately run. This is false. If Linux execution started now, EXP-013 would
immediately fail with a missing module error. Reporting `READY_FOR_LINUX` on an
experiment with an unimplemented required component is a **false signal** that can
mislead the research timeline.

**WHY IT MATTERS:**
H3 (closed-loop update necessity) is a novelty claim (N5). If EXP-013 cannot run,
H3 cannot be tested, N5 cannot be supported, and a key differentiator of RIFT over
simpler intervention pipelines is unverifiable. The paper cannot claim H3 support.

**CURRENT STATUS:**
RIFT-ONE-SHOT implementation assigned to Agent 1 in this sprint. If implemented and
tested, the blocker is resolved for Mac. EXP-013 registry status must be corrected to
`PENDING_IMPLEMENTATION` until the file exists and tests pass, then `READY_FOR_LINUX`.

**REQUIRED FIX:**
1. Complete RIFT-ONE-SHOT implementation (Agent 1 scope).
2. Update `experiments/REGISTRY.yaml` EXP-013 status to reflect actual readiness.
3. Do not mark any experiment `READY_FOR_LINUX` if a required baseline is `NOT_IMPLEMENTED`.

**PAPER DISCLOSURE:**
"EXP-013 (H3 test) requires the RIFT-ONE-SHOT ablation baseline, which was implemented
during final pre-Linux preparation and has not yet been executed on live data."

---

### ISSUE P0-02: H3 Has Only n=1 Multi-Cause Scenario in Development Set

**REVIEWER:** Reviewer 4 (Empirical Methodology)
**SEVERITY:** P0

**ISSUE:**
EXP-013 uses `filter: "multi_cause_or_ambiguous"` on the development set (36 scenarios).
The scenario catalog shows exactly 1 multi-cause scenario (`MULTI_CAUSE: 1`). The tag
`ambiguous` does not exist in the scenario schema. Therefore the filtered set for H3
is n=1. The Wilcoxon signed-rank test on n=1 is mathematically undefined (you cannot
compute ranks with a single observation). H3 cannot be tested with current data.

**WHY IT MATTERS:**
H3 is a core novelty claim. Without sufficient n on multi-cause/ambiguous faults, the
Wilcoxon test cannot run, no p-value can be reported, no statistical significance can
be claimed, and the closed-loop update benefit over RIFT-ONE-SHOT is completely
unverifiable. This is not a minor power concern — it is a test that cannot execute.

**CURRENT STATUS:**
Scenario catalog documents 1 multi-cause scenario in the development set.
No `ambiguous` tag exists in the schema. No scenario expansion has been planned.

**REQUIRED FIX:**
1. Add multi-cause and ambiguous-attribution scenarios to reach n ≥ 12 for minimum
   Wilcoxon power. This requires expanding the scenario catalog — a scientific decision
   that must be made before Linux execution, not during.
2. OR: redefine H3 filter criteria to cover a larger subset (e.g., all confounded
   scenarios with ≥2 plausible candidate services), and document the new criterion.
3. Do NOT add scenarios arbitrarily to inflate sample size — each must be scientifically
   motivated (distinct causal structure from existing scenarios).

**PAPER DISCLOSURE:**
"H3 was tested on [n] multi-cause fault scenarios. The development set contains limited
multi-cause coverage; statistical power for H3 is [achieved power] at n=[actual n]."

---

### ISSUE P0-03: H2 Power Requirement Is Not Met by the Development Set

**REVIEWER:** Reviewer 4 (Empirical Methodology) + Reviewer 1 (Causal Inference)
**SEVERITY:** P0

**ISSUE:**
EXP-002 (`n_confounded_required: 48`) requires 48 confounded scenarios for 80% power
on H2 (Wilcoxon, one-sided, δ=0.30, α=0.05). The development set contains 24 confounded
scenarios (per `docs/experiments/SCENARIO_CATALOG.md`). The validation set adds further
scenarios but its confounded count is unspecified. Even with development + validation,
reaching 48 confounded scenarios is unconfirmed. Running H2 with n=24 yields achieved
power ≈ 47% (from `check_power_achieved(24)`) — barely above chance.

**WHY IT MATTERS:**
H2 is described in `docs/hypotheses.md` as "the most important hypothesis" — "the
empirical defense of N2." If H2 is tested at 47% power and fails to reach significance,
it is impossible to distinguish between "RIFT-FULL does not outperform RIFT-OBS" and
"the study was underpowered." Either way the core novelty claim N2 (intervention adds
measurable benefit) cannot be supported. This is a fundamental threat to the paper.

**CURRENT STATUS:**
Development set: 24 confounded. Required: 48. Gap: 24 confounded scenarios missing.
Power at n=24: ≈47%. Power at n=48: ≈80% (by design).

**REQUIRED FIX:**
1. Expand the confounded scenario count to ≥ 48 before Linux execution, OR
2. Lower the claimed effect size (use larger δ assumption) with justification, OR
3. Combine development + validation sets for H2 (document the statistical validity of
   this choice — it risks threshold tuning leakage if validation was used for tuning).
4. Report ACHIEVED power, never claim 80% unless n ≥ 48 confirmed at run time
   (enforced by `check_power_achieved()` — do not bypass this check).

**PAPER DISCLOSURE:**
"H2 was powered for n=48 confounded scenarios. If fewer were collected at run time,
the achieved power is reported explicitly and the 80% power claim is retracted."

---

### ISSUE P0-04: RIFT-RANDOM `run()` Does Not Dispatch Interventions — H4 Cost Metric Is Unmeasurable

**REVIEWER:** Reviewer 3 (Software Engineering) + Reviewer 4 (Empirical Methodology)
**SEVERITY:** P0

**ISSUE:**
`src/rift/baselines/rift_random.py` `RIFTRandomBaseline.run()` builds PAG + EBD and
returns candidates — but sets `total_intervention_ed_s=0.0` and passes `cid_results=None`.
The `RandomMSIS.select()` method is fully implemented but **never called** from `run()`.
No interventions are dispatched. The ABLATION_REGISTRY marks `network_intervention: true`
for RIFT-RANDOM — this is currently false in the implementation.

H4's primary metric is `total_ed_s` (cumulative execution duration of all interventions).
If RIFT-RANDOM never dispatches interventions and RIFT-FULL does, the comparison is
between a system that actually runs interventions and one that does not — making the
cost comparison meaningless. The H4 conclusion (MSIS reduces cost vs random) cannot
be drawn from a `total_ed_s = 0.0` baseline.

**WHY IT MATTERS:**
H4 is the efficiency claim. N3 (cost-optimized selection) is a stated novelty.
An unfair cost comparison where one method does nothing makes the result trivially true
but scientifically worthless. Reviewers will immediately notice that RIFT-RANDOM spends
0 intervention budget and ask why this is a valid comparison.

**CURRENT STATUS:**
`RIFTRandomBaseline.run()` = functionally identical to `RIFTObsBaseline.run()` (same
PAG+EBD+no-intervention pipeline). RandomMSIS is dead code. Both EXP-006 and EXP-014
are marked `READY_FOR_LINUX` despite this defect.

**REQUIRED FIX:**
`RIFTRandomBaseline.run()` must:
1. Call `self._random_msis.select()` with the computed posterior and cost model
2. Dispatch interventions via the intervention engine (dry-run on Mac, live on Linux)
3. Record actual `total_intervention_ed_s` from dispatched interventions
4. Update `top_candidates` using intervention results (CID scores)
This is a non-trivial implementation task that must complete before Linux execution.

**PAPER DISCLOSURE:**
"RIFT-RANDOM dispatches interventions using the same engine as RIFT-FULL, with random
rather than utility-maximizing selection. Intervention cost is measured identically."

---

### ISSUE P0-05: No Category C Evidence Exists for Any Core Performance Claim

**REVIEWER:** All six reviewers (consensus)
**SEVERITY:** P0

**ISSUE:**
`docs/CLAIMS_REGISTRY.yaml` correctly classifies claims C001–C006 as `PLANNED` and
C013 as `UNSUPPORTED`. No `live_telemetry_used=True` RIFTRunRecord exists. T1
(PrometheusClient stub), T2 (OTel Collector not wired), and T3 (tc band bug) blockers
are Mac-tested but not Linux-deployed. Any draft that presents performance numbers
(P@1, detection latency, cost reduction) without labeling them as SYNTHETIC ONLY is
making unsupported claims. The frozen historical evidence `P@1=0.50, Conditional=0.60`
from Phase 3.5 MockTelemetry is explicitly forbidden from appearing as a live result.

**WHY IT MATTERS:**
If these numbers appear in a paper draft without the SYNTHETIC label, the paper asserts
live system performance where none exists. This is a Category A scientific integrity
violation. Even if the reviewer doesn't catch it, the authors know it — and this is
exactly the kind of issue that causes post-publication retractions.

**CURRENT STATUS:**
Correctly handled in CLAIMS_REGISTRY.yaml. Risk is in paper drafting, not in code.

**REQUIRED FIX:**
1. All paper tables with P@1, latency, or cost numbers must be labeled:
   "SYNTHETIC BENCHMARK ONLY — Development Set, MockTelemetry, Phase 3.5"
   until Category C evidence exists.
2. Produce a final paper checklist that must be signed off before submission:
   "All numbers in Table N are from [experiment ID] with live_telemetry_used=[value]."
3. Do NOT upgrade any claim status until the corresponding experiment actually runs.

**PAPER DISCLOSURE:**
All performance claims must carry: "Results from synthetic benchmark evaluation.
Live system results pending Linux experimental execution."

---

## P1 Issues — Major Concerns

---

### ISSUE P1-01: tc/netem Does Not Implement do(X) — Side Effects Are Uncontrolled

**REVIEWER:** Reviewer 1 (Causal Inference)
**SEVERITY:** P1

**ISSUE:**
`docs/intervention_semantics.md` formally defines `do(X := x)` as replacing exactly
one structural mechanism with no side effects on non-descendants. `tc netem delay` adds
latency to ALL packets on a network interface (or filtered by tc u32 rules). However,
in a containerized environment, a container's network namespace may carry traffic for
multiple services (sidecars, health checks, logging). The tc rule affects ALL egress
traffic on that interface — not just the target service's application traffic. This
means non-descendants may be perturbed, violating A5 (Intervention Validity).

**CURRENT STATUS:**
A5 violation detection is documented and implemented (clean-window check, side-effect
monitor). Interventions with `side_effects != []` are discarded. However, if every
intervention has minor side effects (likely in containerized environments with shared
namespaces), the discard rate could be prohibitively high — making the experimental
throughput insufficient.

**REQUIRED FIX:**
1. Measure empirical discard rate on Linux during Phase 5.
2. If discard rate > 30%, reconsider tc u32 destination filtering as primary method.
3. Document observed side effect types and rate in the paper.

**PAPER DISCLOSURE:**
"tc netem interventions were validated for target-service isolation using per-destination
u32 filtering. Interventions with detected side effects on non-descendant services were
discarded (rate: [N]%). The remaining VALID interventions provide samples from the
interventional distribution."

---

### ISSUE P1-02: FCI with n≤36 Scenarios Is Severely Underpowered for Structure Learning

**REVIEWER:** Reviewer 1 (Causal Inference)
**SEVERITY:** P1

**ISSUE:**
FCI's reliability degrades severely with small sample sizes. With 36 development
scenarios and 15-second Prometheus windows, the number of independent time-series
observations per incident window may be 20-40. FCI with n=20-40 on 10-15 variables
produces highly uncertain PAGs with many undirected or ambiguous edges. The EXP-011
robustness experiment tests this but is classified `DRY_RUN_READY` — meaning FCI
uncertainty under real traffic conditions is completely unquantified.

**CURRENT STATUS:**
FCI fallback (empty PAGResult) is implemented. The paper must disclose FCI uncertainty.
EXP-011 (FCI on noisy/sparse data) has no execution protocol for how it selects its
n=10 scenarios.

**REQUIRED FIX:**
Run EXP-011 explicitly and report: % of scenarios where FCI produces a complete PAG
vs. falls back to empty result, average PAG edge uncertainty, and how this affects
downstream attribution accuracy.

**PAPER DISCLOSURE:**
"FCI structure learning was run on Δt=10s metric windows during incidents. PAG quality
ranged from [X]% complete to [Y]% empty/fallback. EBD was run on the available PAG
in all cases; empty-PAG abstention rate was [Z]%."

---

### ISSUE P1-03: Hypothesis Numbering Conflicts Across Documents

**REVIEWER:** Reviewer 3 (Software Engineering)
**SEVERITY:** P1

**ISSUE:**
`docs/hypotheses.md` maps H2 → "EXP-009 (Ablation: intervention necessity)" and
H5 → "EXP-011 (Cross-system generalization)". But `experiments/REGISTRY.yaml`
EXP-009 = "Performance instrumentation: stage timing" (no hypothesis) and
EXP-011 = "Robustness: FCI on noisy/sparse data" (RQ1, no H5). This is a direct
internal inconsistency in the core research documentation. A reviewer checking
cross-references will immediately find this and question the rigor of the research process.

**CURRENT STATUS:**
Documented by Agent 2 (Experiment Completeness Audit) and Agent 5 (Robustness Audit).
Not yet corrected.

**REQUIRED FIX:**
Update `docs/hypotheses.md` H2 and H5 experiment references to use the correct EXP IDs
that are actually registered in `experiments/REGISTRY.yaml`. H2 → EXP-002/EXP-005,
H5 → DEFERRED (no EXP registered). This is a documentation fix, not a science change.

**PAPER DISCLOSURE:**
None needed once corrected.

---

### ISSUE P1-04: Benchmark Was Generated by the Same Research Team

**REVIEWER:** Reviewer 4 (Empirical Methodology)
**SEVERITY:** P1

**ISSUE:**
The 69-scenario benchmark was generated by `src/rift/benchmark/synthetic_benchmark.py`
— the same codebase as RIFT. The fault scenarios, their causal structures, and the
ground truth labels were all designed by RIFT's implementers. This creates a risk
of conscious or unconscious benchmark leakage: the scenario structures may implicitly
reflect RIFT's modeling assumptions, giving RIFT an unfair advantage over baselines
that use different causal models (SIEVE-LIKE, purely observational methods).

**CURRENT STATUS:**
Acknowledged in Phase 3.5 review (P1-ES-3) but not yet addressed.
No independent benchmark or external dataset is used.

**REQUIRED FIX:**
1. Introduce at least one externally-validated benchmark scenario set (e.g., from
   public chaos engineering experiments, Alibaba microservice trace data, or
   DeathStarBench traces).
2. OR provide a detailed analysis showing that scenario design decisions do not
   favor RIFT's specific modeling choices over baselines.
3. At minimum, disclose this limitation prominently in Threats to Validity.

**PAPER DISCLOSURE:**
"The evaluation benchmark was constructed using synthetic fault injection guided by
causal assumptions consistent with RIFT's design. An independent evaluation on
externally-sourced fault traces would provide stronger external validity."

---

### ISSUE P1-05: SIEVE-LIKE Is Not SIEVE — Comparison May Be Unfair to the Prior Work

**REVIEWER:** Reviewer 5 (Prior Art)
**SEVERITY:** P1

**ISSUE:**
`src/rift/baselines/sieve_like.py` is documented as "methodological reimplementation"
not based on the original Sieve codebase. The reimplementation may not faithfully
reproduce Sieve's performance — it could be worse (strawman) or better (cherry-picked).
ICSE reviewers familiar with Sieve will ask: "Why wasn't the original Sieve code used?"
If the answer is "it's not publicly available," that must be stated. If the comparison
shows RIFT > SIEVE-LIKE, a reviewer may argue this proves nothing about RIFT vs real Sieve.

**CURRENT STATUS:**
Correctly labeled SIEVE-LIKE in all registry entries and documentation. The labeling
requirement is enforced. But the scientific justification for why SIEVE-LIKE is a
meaningful comparison has not been written up.

**REQUIRED FIX:**
1. Write a justification section for SIEVE-LIKE in the paper: "We implemented the
   core Sieve algorithm (observational causal graph + ranking) following [citation].
   The original implementation was not publicly available at time of writing.
   Our reimplementation follows the algorithm as described in [paper]."
2. Never write "RIFT outperforms Sieve" — only "RIFT outperforms SIEVE-LIKE, our
   reimplementation of the Sieve methodology."

**PAPER DISCLOSURE:**
"SIEVE-LIKE is a methodological reimplementation of the Sieve approach [cite] using the
same algorithm description. We did not use original Sieve source code. Results may
differ from the original implementation."

---

### ISSUE P1-06: Online Boutique Is a Demonstration App, Not a Production Workload

**REVIEWER:** Reviewer 2 (Distributed Systems)
**SEVERITY:** P1

**ISSUE:**
Online Boutique has 10-14 services with a largely tree-shaped call graph, uniform
service communication patterns, and no complex fan-out, event sourcing, or heterogeneous
workloads. Production microservice systems at scale (Netflix, Uber, Airbnb) have
100-500 services, complex bidirectional dependencies, async messaging, and non-uniform
load patterns. FCI's faithfulness assumption may hold for Online Boutique's simple
topology but break down in a dense, complex production graph. The RIFT paper cannot
claim applicability to production systems from results on Online Boutique alone.

**CURRENT STATUS:**
Documented as a limitation in `docs/hypotheses.md` H5. However H5 (cross-system
generalization) is DEFERRED to Phase 11. The Phase 5 paper will have single-system
results only.

**REQUIRED FIX:**
1. Scope the paper explicitly to "small-scale microservice testbeds (≤15 services)"
2. State in abstract/intro that generalization to large-scale production systems
   is future work
3. Do not use phrases like "production microservice system" — use "microservice testbed"

**PAPER DISCLOSURE:**
"Experiments were conducted on Online Boutique, a 10-14 service demonstration
application. Generalization to large-scale production systems with complex topologies
is a direction for future work."

---

### ISSUE P1-07: Cliff's Delta Is Always Reported — But Is It Interpretable for Binary Precision@1?

**REVIEWER:** Reviewer 6 (Reproducibility)
**SEVERITY:** P1

**ISSUE:**
Precision@1 is a binary outcome per scenario: 0 or 1. Cliff's delta on two binary
sequences is meaningful but has a specific interpretation: it equals `P(RIFT=1 AND
Baseline=0) - P(RIFT=0 AND Baseline=1)`. The standard Vargha-Delaney thresholds
(negligible/small/medium/large) were derived for continuous outcomes. For binary P@1
on n=36, a Cliff's delta of 0.20 (minimum "small" effect) requires approximately
3-4 more successes for RIFT than the baseline. The paper must clarify that Cliff's
delta on binary outcomes is the probability superiority measure, not the standard
continuous effect size.

**CURRENT STATUS:**
Cliff's delta is correctly implemented and always reported. Interpretation thresholds
are from Romano et al. / Vargha-Delaney and are listed in `stats.py`.

**REQUIRED FIX:**
1. In the paper, include one sentence: "For binary Precision@1 outcomes, Cliff's δ
   equals P(RIFT succeeds AND baseline fails) − P(RIFT fails AND baseline succeeds),
   interpretable as the probability superiority of RIFT over the baseline."
2. Keep existing thresholds (negligible/small/medium/large) with the note they apply
   to the probability superiority interpretation.

**PAPER DISCLOSURE:**
(Included in the fix itself — one clarifying sentence in the methodology section.)

---

### ISSUE P1-08: No External Reproducibility Path for Reviewers Without Linux + Root

**REVIEWER:** Reviewer 6 (Reproducibility)
**SEVERITY:** P1

**ISSUE:**
The full RIFT experiment requires:
- Linux (not Mac)
- Docker with CAP_NET_ADMIN / root (for tc/netem)
- Online Boutique deployed (14 containers)
- Prometheus + OTel Collector wired
- Locust load generation
A typical ICSE artifact reviewer on a Mac laptop cannot reproduce the paper's
experiments. The Tier 1 (Mac, Python-only) path only tests the non-intervention
components and does not reproduce any of the core claims.

**CURRENT STATUS:**
This is inherent to the research contribution. Acknowledged in Phase 3.5 review
(P1-RE-2). The reproduction docs distinguish Mac and Linux tiers.

**REQUIRED FIX:**
1. Provide a Docker-based one-command reproduction path that works on Linux:
   `make reproduce-experiments` that deploys Online Boutique, runs RIFT, and
   produces all result artifacts.
2. Register the artifact for ICSE artifact evaluation with explicit note:
   "Full reproduction requires Linux with CAP_NET_ADMIN. Mac reproduction covers
   unit/integration tests only."
3. Consider providing a pre-run results archive so reviewers can regenerate
   figures/tables without executing the full experiment.

**PAPER DISCLOSURE:**
"Full reproduction of experiments requires Linux with CAP_NET_ADMIN privileges for
tc/netem. A Docker-based reproduction script is provided. Pre-computed result
artifacts are archived at [URL]."

---

### ISSUE P1-09: EXP-014 Uses Non-Standard statistical_test Keys

**REVIEWER:** Reviewer 3 (Software Engineering)
**SEVERITY:** P1

**ISSUE:**
`experiments/REGISTRY.yaml` EXP-014 uses `statistical_test_cost` and
`statistical_test_accuracy` instead of the standard `statistical_test` field used by
all other experiments. This schema deviation means any automated registry parser
will fail to extract EXP-014's statistical tests. The experiment completeness auditor
(Agent 2) flagged this as an INCOMPLETE schema.

**CURRENT STATUS:**
Documented by Agent 2 (Experiment Completeness Audit). EXP-014 has two tests
(Wilcoxon for cost, TOST for accuracy) which is scientifically correct for H4 —
the schema needs to accommodate two tests, not just one.

**REQUIRED FIX:**
Update EXP-014 schema to use a list or map structure:
```yaml
statistical_tests:
  cost: wilcoxon_one_sided
  accuracy: tost_equivalence
```
Or update the parser to accept both key styles. The authoritative content is correct;
the schema representation needs standardizing.

**PAPER DISCLOSURE:**
None — internal registry issue.

---

### ISSUE P1-10: H5 Has No Registered Experiment and Is Listed as "DEFERRED" Without a Fallback

**REVIEWER:** Reviewer 5 (Prior Art)
**SEVERITY:** P1

**ISSUE:**
`docs/hypotheses.md` states H5 as a formal hypothesis with a measurement protocol.
`docs/research/RQ_EXPERIMENT_MAP.md` lists H5 as DEFERRED to Phase 11. No experiment
in `experiments/REGISTRY.yaml` covers H5. If the paper claims RIFT generalizes across
systems (even as future work), it needs either (a) preliminary evidence or (b) a clear
statement that generalization is an open question. A hypothesis that appears in
`hypotheses.md` but has no experiment and no results cannot appear in the abstract or
contributions as a supported claim.

**CURRENT STATUS:**
Correctly not claimed as supported. But if H5 appears in the paper's introduction as
a "research question we address," reviewers will look for EXP-011 results (which is
actually the FCI-noisy-data experiment, not cross-system generalization).

**REQUIRED FIX:**
1. Remove H5 from any list of "hypotheses tested in this paper."
2. Frame generalization as "future work" in the paper, not as a research question
   answered by the current evaluation.
3. Correct the EXP-011 cross-reference confusion.

**PAPER DISCLOSURE:**
"Cross-system generalization (H5) requires a second independently-designed system
(e.g., Sock Shop). This experiment is planned for future work."

---

### ISSUE P1-11: R3 Criterion Fails for Leaf-Node Services

**REVIEWER:** Reviewer 1 (Causal Inference)
**SEVERITY:** P1

**ISSUE:**
Raised in Phase 3.5 review (P1-CI-3) and not fully resolved. EBD R3 requires that
a candidate service has a downstream service showing divergence. Services that are
pure callees in the call graph (payment, product_catalog, redis-cart) have no
outgoing edges and therefore cannot satisfy R3. This means RIFT structurally cannot
attribute root causes to leaf services using R3 — even when those services are the
true root cause (e.g., redis-cart latency causing cascade upstream).

**CURRENT STATUS:**
Documented as limitation L4 (Insufficient Observability). But the R3 structural
failure for callees is a more specific, architectural issue: even if all services
are fully instrumented, a callee with no downstream edges cannot pass R3.

**REQUIRED FIX:**
1. Add a "reverse-edge fallback" for R3: if the candidate is a leaf node, accept
   that its upstream callers showing divergence satisfies a relaxed R3 criterion.
2. OR add a dedicated "R3-leaf" criterion for leaf services.
3. OR explicitly exclude leaf services from R3 and document the attribution gap.
4. Report in the paper what fraction of ground-truth root causes are leaf services
   and what the R3 failure rate is for that subset.

**PAPER DISCLOSURE:**
"RIFT's R3 criterion requires a downstream diverging service. Services at the boundary
of the call graph (leaf nodes) cannot satisfy R3 natively. We apply [relaxed criterion]
for leaf-node candidates, accepting [upstream callers / direct anomaly score] as R3
evidence."

---

### ISSUE P1-12: Bayesian Posterior Update Parameters Are Not Pre-Registered

**REVIEWER:** Reviewer 1 (Causal Inference)
**SEVERITY:** P1

**ISSUE:**
The closed-loop Bayesian posterior update uses `A_POS=3.0, B_POS=1.0, A_NEG=1.0,
B_NEG=3.0` (Beta distribution parameters) and `ALPHA_CONFIRM=0.2, ALPHA_WEAKEN=0.1`.
These are frozen in `src/rift/loop/closed_loop.py` via class-level constants. However,
there is no document explaining how these values were chosen (prior analysis, empirical
calibration, or arbitrary selection). Reviewers will ask: "Did you tune these on the
development set?" If yes, the ablation comparison (RIFT-FULL vs RIFT-ONE-SHOT) is
not fair because RIFT-FULL's update parameters were tuned on the same data used to
test H3.

**CURRENT STATUS:**
Parameters are frozen (correct practice) but their provenance is undocumented.
`docs/closed_loop_model.md` exists but may not justify the Beta parameters.

**REQUIRED FIX:**
1. Document the justification for `A_POS=3, B_POS=1, A_NEG=1, B_NEG=3` in
   `docs/closed_loop_model.md` or a dedicated methods note.
2. If these were tuned on development data: perform a sensitivity analysis showing
   results are stable across a range of Beta parameter choices.
3. If these were set by prior reasoning (high CID → more likely to be cause):
   state that explicitly.

**PAPER DISCLOSURE:**
"Bayesian update parameters (Beta prior parameters) were set by [method] and frozen
before any evaluation. Sensitivity analysis [Appendix X] shows results are stable
across a ±50% variation in these parameters."

---

## P2 Issues — Minor Concerns

---

### ISSUE P2-01: delta_t=10s Prometheus Window May Miss Sub-Window Transients

**REVIEWER:** Reviewer 2 (Distributed Systems)
**SEVERITY:** P2

**ISSUE:**
15-second Prometheus scrape intervals with 10-second analysis windows means some
transient anomalies (< 10s) are invisible to RIFT. Network blips, brief CPU spikes,
and transient queue buildups may not produce a full 10s window of anomalous data.
RIFT will miss these entirely. The paper should scope to "persistent anomalies lasting
≥ 10s" rather than "all anomalies."

**PAPER DISCLOSURE:** "RIFT detects anomalies persisting for at least Δt=10s (one analysis window). Transient anomalies shorter than Δt are not detectable."

---

### ISSUE P2-02: abstention_rate Is Not Computed the Same Way for All Baselines

**REVIEWER:** Reviewer 4 (Empirical Methodology)
**SEVERITY:** P2

**ISSUE:**
`BaselineOutput.abstained` is a boolean. Some baselines set it to True when EBD finds
no candidates; others set it to True when PAG construction fails. The semantics are
not identical. If RIFT-OBS abstains due to non-identifiability but SIEVE-LIKE abstains
due to no anomaly detected, the abstention rates are not comparable without knowing why.

**REQUIRED FIX:** Add an `abstention_reason` field to `BaselineOutput` and report it
separately in evaluation artifacts.

---

### ISSUE P2-03: Held-Out Test Set Has Only 15 Scenarios

**REVIEWER:** Reviewer 4 (Empirical Methodology)
**SEVERITY:** P2

**ISSUE:**
The final held-out evaluation uses 15 scenarios. The 95% Wilson CI for P@1=0.70 with
n=15 is approximately [0.44, 0.88]. The paper will report a single number with very
wide confidence bounds. This is not fatal but must be disclosed.

**PAPER DISCLOSURE:** "The held-out test set contains 15 scenarios. Confidence intervals for P@1 estimates on this set are wide; results should be interpreted as indicative rather than definitive."

---

### ISSUE P2-04: RIFT-NO-MSIS and RIFT-RANDOM Are Functionally Identical

**REVIEWER:** Reviewer 3 (Software Engineering)
**SEVERITY:** P2

**ISSUE:**
`experiments/ablations/ABLATION_REGISTRY.yaml` lists both RIFT-NO-MSIS and RIFT-RANDOM
with identical component configurations. The registry notes "Equivalent to RIFT-RANDOM."
Having two names for the same ablation in the paper would confuse readers and suggest
more experimental coverage than actually exists.

**REQUIRED FIX:** Use only RIFT-RANDOM in all paper tables. Remove RIFT-NO-MSIS from
any paper discussion or clearly footnote it as an alias.

---

### ISSUE P2-05: Locust Load Pattern Does Not Reflect Production Traffic Distributions

**REVIEWER:** Reviewer 2 (Distributed Systems)
**SEVERITY:** P2

**ISSUE:**
Locust generates uniform random user behavior. Real e-commerce traffic has Zipf-distributed
product popularity, time-of-day patterns, and bursty checkout flows. The uniform load may
produce artificially stable baselines that underestimate RIFT's difficulty on real traffic.

**PAPER DISCLOSURE:** "Load generation uses uniform random browsing behavior. Results under more realistic, non-uniform traffic patterns may differ."

---

### ISSUE P2-06: Confidence Intervals Are Not Reported for All Metrics

**REVIEWER:** Reviewer 4 (Empirical Methodology)
**SEVERITY:** P2

**ISSUE:**
The statistical plan reports Cliff's delta CI but does not specify confidence intervals
for Precision@1, detection latency, or abstention rate as primary metrics. ICSE papers
should report CI for all point estimates, not just effect sizes.

**REQUIRED FIX:** Report 95% Wilson CI for all binary metrics (P@1, abstention rate)
and 95% bootstrap CI for continuous metrics (latency, cost).

---

### ISSUE P2-07: BH FDR Is Listed as "Exploratory" But Exploratory Tests Are Not Defined

**REVIEWER:** Reviewer 1 (Causal Inference)
**SEVERITY:** P2

**ISSUE:**
`docs/PHASE_3_SPEC_FREEZE.md §15` states "Exploratory comparisons: BH FDR." But no
document specifies which tests are exploratory vs confirmatory. If the paper runs
additional comparisons (e.g., RIFT vs threshold-based baselines, additional fault type
subgroup analyses) without pre-registering them as exploratory, it risks inflating
Type I error even with BH FDR correction.

**REQUIRED FIX:** Create a pre-registered list of all exploratory comparisons before
Linux execution. Any comparison not on this list cannot be reported.

---

### ISSUE P2-08: H5 p_null Default May Be Wrong in binomial_one_sided()

**REVIEWER:** Reviewer 6 (Reproducibility)
**SEVERITY:** P2

**ISSUE:**
`src/rift/statistics/stats.py` `binomial_one_sided()` defaults `p_null=0.70`. H5
specifies the null as `0.70 × P@1(in-distribution)`. If in-distribution P@1 = 0.80,
the correct null is 0.56, not 0.70. The default is only correct if in-distribution P@1
= 1.0 (perfect). The evaluation harness must compute and pass the correct `p_null`
at run time. Documented by Agent 6.

**REQUIRED FIX:** Evaluation harness must pass `p_null = 0.70 * in_dist_p1` explicitly.
Add a comment to the function: "Caller must compute p_null = 0.70 * in_distribution_p1."

---

### ISSUE P2-09: No Cross-References Between claims_registry and Paper Sections

**REVIEWER:** Reviewer 3 (Software Engineering)
**SEVERITY:** P2

**ISSUE:**
`docs/CLAIMS_REGISTRY.yaml` is a rigorous internal document but has no mapping to
paper section numbers. When a reviewer asks "where in the paper is C001 supported?"
there is no fast lookup. This creates risk of claims appearing in the paper without
a corresponding entry in the registry.

**REQUIRED FIX:** Add a `paper_section` field to each claim in CLAIMS_REGISTRY.yaml
once a paper draft exists. Until then, mark all as `paper_section: DRAFT`.

---

## Per-Reviewer Summary

| Reviewer | P0 | P1 | P2 | Total |
|---|---|---|---|---|
| Reviewer 1 — Causal Inference | 1 (P0-03 co-author) | 3 (P1-01, P1-02, P1-11, P1-12) | 2 (P2-07, P2-08) | 7 |
| Reviewer 2 — Distributed Systems | 0 | 2 (P1-06, P1-08 partial) | 2 (P2-01, P2-05) | 4 |
| Reviewer 3 — Software Engineering | 1 (P0-04 co-author) | 3 (P1-03, P1-05, P1-09) | 2 (P2-04, P2-09) | 6 |
| Reviewer 4 — Empirical Methodology | 3 (P0-01, P0-02, P0-03) | 2 (P1-04, P1-07) | 3 (P2-02, P2-03, P2-06) | 8 |
| Reviewer 5 — Prior Art | 0 | 2 (P1-05, P1-10) | 0 | 2 |
| Reviewer 6 — Reproducibility | 1 (P0-05 co-author) | 1 (P1-08) | 2 (P2-08, P2-09) | 4 |

*Note: Co-author = contributed to a joint P0 issue.*

---

## Cross-Cutting Issues (Multiple Reviewers)

| Issue | Reviewers | Description |
|---|---|---|
| No live evidence | All 6 | P0-05 — no Category C data exists anywhere |
| Power shortfall | R4 + R1 | P0-02, P0-03 — H2 and H3 underpowered |
| Benchmark self-authorship | R4 + R3 | P1-04 — same team built scenarios and RIFT |
| H-to-EXP mapping inconsistency | R3 + R5 | P1-03 — hypotheses.md vs REGISTRY.yaml mismatch |
| Leaf-node attribution gap | R1 + R2 | P1-11 — R3 cannot fire for callee services |

---

## Existing Mitigations (Already Handled)

| Issue Area | Mitigation |
|---|---|
| Held-out data seal | `HeldOutGuard` implemented; token-gated; tested |
| Synthetic results labeling | CLAIMS_REGISTRY.yaml correctly classifies all claims |
| SIEVE-LIKE labeling | Enforced in registry and all docs |
| Sage+Chaos fabrication | SageChaosStub always abstains |
| Safety hard stops | 6/8 validated; 2/8 pending Linux |
| Multiple testing correction | Holm-Bonferroni for 6 tests implemented |
| Intervention validity checks | A5 runtime checks implemented |
| Causal assumption disclosure | docs/causal_assumptions.md A1-A8 documented |
| H4 cost sign-flip | Correct in run_confirmatory_tests() — verified by Agent 6 |

---

## Status

**COMPLETE**

All 26 issues documented. P0 issues require resolution before Linux execution begins.
P1 issues require resolution before paper submission. P2 issues require either fixing
or explicit paper disclosure before submission.

Next action: Integration Agent resolves conflicts across all agent outputs, then
full test suite run.
