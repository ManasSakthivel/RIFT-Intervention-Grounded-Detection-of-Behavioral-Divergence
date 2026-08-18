# RIFT — Baseline Fairness Audit
**Phase 2.5 | Risk Closure Document**

> **Purpose:** Certify that each of the 7 baselines is evaluated on a comparably fair information diet. This document is a pre-registered audit that must be reviewed and signed off before Phase 10 (Full Evaluation) begins. Any STATUS of NEEDS_ADJUSTMENT or UNFAIR blocks Phase 10.

---

## Audit Scope

Seven baselines are evaluated:
1. Prometheus threshold rules
2. Isolation Forest
3. MicroRCA-style (call graph + PageRank)
4. Sieve (adaptive injection, no SCM)
5. RIFT-OBS (RIFT without intervention, uses same G_T)
6. Statistical debugging (Ochiai-adapted)
7. Sage + Chaos composition

Common input protocol is defined in `docs/baseline_specification.md` §Baseline Information Protocol. No baseline receives RIFT's CID scores, EBD outputs, intervention outcomes, or learned G_T (except Baseline 5 — see Critical Fairness Check below).

---

## BASELINE 1 — Prometheus Threshold Rules

**INPUTS:**
- trace data: NO (none)
- metric data: YES — latency_p99, error_rate, throughput per service at 1s resolution; pre-incident 1hr baseline window
- call graph topology: NO
- FCI-learned causal graph G_T: NO
- fault injection capability: NO
- pre-trained fault labels: NO
- intervention outcomes: NO
- SLO definitions: NO (thresholds derived from baseline μ ± 3σ, not from formal SLO contracts)

**TRAINING DATA:**
- What historical data does it use? The 7-day pre-incident metric window (via `baseline_specification.md`: "identical metric data … 1hr pre-incident baseline" — the 7-day window is the Isolation Forest training window; Baseline 1 uses only the 1hr pre-incident window for μ/σ estimation).
- Is training data from the evaluation period? **NO.** The 1hr pre-incident baseline strictly precedes the fault injection window. No data leakage.

**OUTPUT FORMAT:**
- Ranked list of root cause candidates: YES (ordered by earliest alert trigger time; no formal ranking beyond first-alert)
- Confidence scores: NO
- Causal explanation: NO

**EVALUATION METRICS APPLIED:**
- Precision@1: YES
- Precision@3: YES (constructed by ranking services by alert order)
- Detection latency: YES (time of first alert minus true fault onset)
- CID score: NO — RIFT-only metric; not applied to any baseline

**FAIRNESS RISKS:**
- Information advantages over RIFT: NONE. Baseline 1 receives a strict subset of RIFT's inputs.
- Information disadvantages vs RIFT: Significant. No topology, no causal graph, no trace data, no intervention. Expected to be weakest baseline by design — serves as the "current production alerting" floor.
- Training data concerns: NONE. μ/σ derived from same pre-incident window available to all baselines.

**STATUS: FAIR**

---

## BASELINE 2 — Isolation Forest

**INPUTS:**
- trace data: NO (none)
- metric data: YES — all Prometheus metrics at 1s granularity, all services, for the 7-day pre-incident training window and the incident window
- call graph topology: NO
- FCI-learned causal graph G_T: NO
- fault injection capability: NO
- pre-trained fault labels: NO
- intervention outcomes: NO
- SLO definitions: NO

**TRAINING DATA:**
- What historical data does it use? 7-day pre-incident metric data to fit the Isolation Forest model (`baseline_specification.md` Baseline 2: "Train Isolation Forest on W_baseline = 7-day pre-incident metric data").
- Is training data from the evaluation period? **NO.** Training window is `[t_incident − 7d, t_incident)` — entirely before fault injection. No data leakage.

**OUTPUT FORMAT:**
- Ranked list of root cause candidates: YES (ranked by anomaly_score(sᵢ, t_incident))
- Confidence scores: YES (anomaly score, though not a probability)
- Causal explanation: NO

**EVALUATION METRICS APPLIED:**
- Precision@1: YES
- Precision@3: YES
- Detection latency: YES
- CID score: NO

**FAIRNESS RISKS:**
- Information advantages over RIFT: NONE. Receives only metric subset.
- Information disadvantages vs RIFT: Significant. No traces, no topology, no causality, no intervention. Uses a wider metric training window (7 days) than RIFT's observational window — this is a **mild advantage** vs baselines that use only the 1hr pre-incident window, but is inherent to the algorithm's design and does not constitute a fairness violation vs RIFT (which also uses pre-incident windows for causal graph learning).
- Training data concerns: NONE. 7-day window predates all evaluation incidents.

**ACTION ITEM:** Verify that none of the 7-day training windows for any baseline overlap with any fault injection trial. The benchmark must enforce a minimum 7-day washout period between trials on the same system, or each trial must use a fresh baseline window from system-reset state.

**STATUS: FAIR** (conditional on ACTION ITEM verified at benchmark design time)

---

## BASELINE 3 — MicroRCA-Style (Call Graph + PageRank)

**INPUTS:**
- trace data: YES — full (all spans, all services, incident window + 1hr pre-incident baseline)
- metric data: YES — latency_p99, error_rate per service (used for anomaly flagging)
- call graph topology: YES — call graph edges from trace parent-child relationships
- FCI-learned causal graph G_T: NO — uses its own correlation-weighted call graph; does NOT receive RIFT's G_T
- fault injection capability: NO
- pre-trained fault labels: NO
- intervention outcomes: NO
- SLO definitions: NO

**TRAINING DATA:**
- What historical data does it use? The pre-incident baseline window (1hr) for μ/σ estimation on latency metrics; call graph topology learned from the same pre-incident trace window.
- Is training data from the evaluation period? **NO.** Pre-incident window strictly precedes fault injection. No leakage.

**OUTPUT FORMAT:**
- Ranked list of root cause candidates: YES (ranked by Personalized PageRank score)
- Confidence scores: YES (PageRank scores as relative weights; not calibrated probabilities)
- Causal explanation: PARTIAL (graph walk provides a path, but direction is correlation-based not causal)

**EVALUATION METRICS APPLIED:**
- Precision@1: YES
- Precision@3: YES
- Detection latency: YES
- CID score: NO

**FAIRNESS RISKS:**
- Information advantages over RIFT: NONE. Uses the same call graph topology that all baselines with trace access can derive. Critically, this is the *call graph*, not RIFT's FCI-learned causal PAG — the distinction is enforced by the baseline specification.
- Information disadvantages vs RIFT: Moderate. No causal graph (no FCI), no interventions, no confounder detection. This is the intended architectural gap.
- Training data concerns: NONE.

**STATUS: FAIR**

---

## BASELINE 4 — Sieve (Adaptive Injection Without Causal Model)

**INPUTS:**
- trace data: YES — full
- metric data: YES — full
- call graph topology: YES — call graph edges from traces
- FCI-learned causal graph G_T: NO — uses only the call graph as its dependency graph; does NOT receive RIFT's PAG
- fault injection capability: YES — same LitmusChaos infrastructure as RIFT; same T_budget = 600s
- pre-trained fault labels: NO
- intervention outcomes: YES — binary outcome matching (did anomaly propagate downstream after injection?)
- SLO definitions: NO

**TRAINING DATA:**
- What historical data does it use? Pre-incident window for anomaly detection thresholds only.
- Is training data from the evaluation period? **NO.**

**OUTPUT FORMAT:**
- Ranked list of root cause candidates: YES (candidate set after pruning; last remaining candidate is root cause)
- Confidence scores: NO (binary include/exclude pruning; no probabilistic output)
- Causal explanation: NO (no SCM; pruning is heuristic)

**EVALUATION METRICS APPLIED:**
- Precision@1: YES
- Precision@3: YES (if multiple candidates remain after pruning, ranked by graph position)
- Detection latency: YES
- CID score: NO

**FAIRNESS RISKS:**
- Information advantages over RIFT: **POTENTIAL CONCERN.** Sieve receives the fault injection capability — same infrastructure as RIFT. However, Sieve does NOT receive RIFT's causal graph G_T, identifiability checking, CID scoring, or closed-loop Bayesian model update. The injection capability is equally available to both; what differs is the model that guides injection and interprets outcomes.
- Does RIFT's SCM give it an unfair advantage Sieve cannot access? **This is the core scientific question H2/H3 are designed to answer.** The comparison is deliberately asymmetric by design: RIFT uses SCM-guided intervention selection and CID estimation; Sieve uses call-graph-guided binary matching. This asymmetry is the experimental treatment, not a fairness violation. Both receive the same injection *capability*.
- Information disadvantages vs RIFT: No SCM, no identifiability checking, no confounder detection, no closed-loop model update. By design.
- Training data concerns: NONE.

**CRITICAL NOTE:** Sieve's binary outcome matching (did anomaly propagate?) is not equivalent to CID scoring (how much did intervention reduce divergence?). The evaluation must confirm that no component of RIFT's CID scoring logic is exposed to Sieve. The baseline implementation must implement binary matching independently. **Enforce via code isolation: Sieve's implementation does not import any RIFT causal inference module.**

**STATUS: FAIR** (conditional on implementation isolation confirmed)

---

## BASELINE 5 — RIFT-OBS (RIFT Without Intervention)

**INPUTS:**
- trace data: YES — full
- metric data: YES — full
- call graph topology: YES
- FCI-learned causal graph G_T: **YES — RIFT-OBS uses the SAME G_T as RIFT-FULL**
- fault injection capability: NO — explicitly disabled
- pre-trained fault labels: NO
- intervention outcomes: NO — zero interventions are executed
- SLO definitions: YES — same SLO definitions available to RIFT

**TRAINING DATA:**
- What historical data does it use? Same observational windows as RIFT-FULL for FCI-based graph learning (the pre-incident window used to learn G_T is identical).
- Is training data from the evaluation period? **NO.**

**OUTPUT FORMAT:**
- Ranked list of root cause candidates: YES (ranked by observational backdoor-adjustment estimate)
- Confidence scores: YES (posterior probability estimates from observational adjustment)
- Causal explanation: YES (causal graph paths from G_T are available; no intervention confirmation)

**EVALUATION METRICS APPLIED:**
- Precision@1: YES
- Precision@3: YES
- Detection latency: YES
- CID score: NO — RIFT-OBS computes observational adjustment estimates, not CID scores (which require intervention data)

**FAIRNESS RISKS:**
- Information advantages over RIFT: NONE. RIFT-OBS is a strict ablation — it has access to the same G_T but does not execute interventions. It cannot produce CID scores.
- Information disadvantages vs RIFT: Exactly one: no intervention outcomes. This is the **intended experimental gap** for H2.
- Training data concerns: NONE.

**CRITICAL FAIRNESS CHECK — G_T SHARING:**
> `baseline_specification.md` §Fair Comparison Protocol, point 7 states: *"RIFT-OBS uses the same G_T as RIFT-FULL — ensures any performance gap is attributable to the intervention, not to different graph-learning methods."*
>
> **Enforcement mechanism:** Both RIFT-FULL and RIFT-OBS must load G_T from the **same serialized graph artifact** produced by a single FCI run on the pre-incident data. Neither should re-run FCI independently. The evaluation harness must checkpoint G_T before running either system, and both systems must load from that checkpoint. This must be verified in the experiment runner code before Phase 10.
>
> **What this means for the comparison:** Any precision gap between RIFT-FULL and RIFT-OBS is attributable **solely** to the presence/absence of intervention data — all other components (graph structure, identifiability checks, candidate ranking prior) are identical. This is the cleanest possible ablation design.

**STATUS: FAIR** (conditional on G_T sharing enforcement verified in experiment harness)

---

## BASELINE 6 — Statistical Debugging (Ochiai-Adapted)

**INPUTS:**
- trace data: YES — partial (request success/failure flags and service participation path only; no latency or timing data used)
- metric data: NO
- call graph topology: NO (Ochiai score is computed per-service without topology)
- FCI-learned causal graph G_T: NO
- fault injection capability: NO
- pre-trained fault labels: NO
- intervention outcomes: NO
- SLO definitions: NO

**TRAINING DATA:**
- What historical data does it use? NONE beyond the incident window itself. Ochiai score is computed entirely from request pass/fail outcomes within the incident window.
- Is training data from the evaluation period? N/A — no training phase.

**OUTPUT FORMAT:**
- Ranked list of root cause candidates: YES (ranked by Ochiai score)
- Confidence scores: YES (Ochiai scores as relative weights; not probabilities)
- Causal explanation: NO (spectrum-based; no causal direction)

**EVALUATION METRICS APPLIED:**
- Precision@1: YES
- Precision@3: YES
- Detection latency: YES (detection time = time Ochiai score first exceeds threshold)
- CID score: NO

**FAIRNESS RISKS:**
- Information advantages over RIFT: NONE. Receives only the trace success/failure subset.
- Information disadvantages vs RIFT: Very significant. No topology, no causal graph, no metrics, no interventions. Expected to perform poorly on faults that produce correlated failures across many services (the "all fail" scenario where Ochiai scores are uniform).
- Training data concerns: NONE.

**STATUS: FAIR**

---

## BASELINE 7 — Sage + Chaos Composition

**INPUTS:**
- trace data: YES — full
- metric data: YES — full
- call graph topology: YES
- FCI-learned causal graph G_T: NO — Sage uses a Bayesian Network (BN), not RIFT's PAG; trained independently on historical fault-labeled data
- fault injection capability: YES — same LitmusChaos infrastructure as RIFT; same T_budget = 600s
- pre-trained fault labels: YES — Sage's BN is trained on historical labeled fault data from the same benchmark system
- intervention outcomes: YES — Phase B observes whether Chaos injection reproduces the anomaly pattern; but the BN is NOT updated from these outcomes (static composition)
- SLO definitions: NO

**TRAINING DATA:**
- What historical data does it use? **Pre-labeled historical fault data for the Sage BN.** This is the most significant fairness concern for this baseline.
- Is training data from the evaluation period? **THIS IS THE CRITICAL RISK.** Sage's BN must be trained on historical fault data that does NOT include any incident from the evaluation set.
  - Required: A temporal train/test split must be defined. The Sage BN is trained on faults from `[t_start, t_split)` and evaluated on faults from `[t_split, t_end)`. The split `t_split` must be defined **before** any evaluation data is collected.
  - If the benchmark generates all faults in a single campaign, Sage cannot use any fault from that campaign for BN training. Instead, Sage's BN must be trained on a **separate pre-campaign fault injection session** on the same system, or on a publicly available prior dataset.
  - **Current status of the split definition:** NOT YET DEFINED in `baseline_specification.md`. This is an open risk item.

**OUTPUT FORMAT:**
- Ranked list of root cause candidates: YES (top-3 from Sage BN posterior propagation + best-match from Chaos phase)
- Confidence scores: YES (Sage BN posterior probabilities)
- Causal explanation: PARTIAL (BN provides Bayesian path; Chaos provides pattern matching; no integrated causal explanation)

**EVALUATION METRICS APPLIED:**
- Precision@1: YES
- Precision@3: YES
- Detection latency: YES
- CID score: NO

**FAIRNESS RISKS:**
- Information advantages over RIFT: **PRE-TRAINED FAULT LABELS.** Sage's BN is trained on labeled fault data. RIFT does NOT receive labeled fault data — it learns causal structure from unlabeled observational data. If Sage's BN is trained on data that resembles the evaluation faults, Sage has an information advantage RIFT cannot access. This is potentially UNFAIR unless strictly managed.
  - Mitigation: Sage's training data must be from a structurally independent fault injection session. The BN prior should not be calibrated on the same fault types as the evaluation set.
  - Alternative interpretation: The pre-trained BN can be considered a fair analogue to RIFT's pre-learned G_T, since both systems do offline model building before the incident. However, Sage's BN requires *labeled fault data*, whereas RIFT's G_T requires only *unlabeled observational data*. This is an inherent capability difference, not a fairness violation — but it must be disclosed.
- Information disadvantages vs RIFT: No SCM, no causal identifiability checking, no closed-loop model update. The static BN + independent Chaos injection is architecturally weaker than RIFT's adaptive closed-loop system. This is the intended experimental gap.
- Training data concerns: **HIGH RISK — SEE ABOVE.** Temporal split must be defined and enforced.

**CRITICAL FAIRNESS CHECK — TEMPORAL SPLIT FOR SAGE:**
> The temporal train/test split for Sage's BN is **not yet defined** in any Phase 2 document. This is a Phase 7 (benchmark design) dependency.
>
> **Required action before Phase 10:** Define `t_split` explicitly. Options:
> 1. **Preferred:** Run a dedicated pre-campaign fault injection session (different random seeds, different load levels) on the same system to generate Sage's training corpus. The evaluation campaign is entirely separate.
> 2. **Acceptable:** Use 50% of benchmark faults for Sage training, 50% for evaluation, with random stratified split by fault type. Pre-register the split seed before evaluation.
> 3. **Unacceptable:** Train Sage's BN on any data collected during the same campaign session as the evaluation faults.

**STATUS: NEEDS_ADJUSTMENT** — Temporal train/test split for Sage's BN must be defined and documented before Phase 10.

---

## Critical Fairness Checks — Summary

### CF-1: RIFT-OBS Uses Same G_T as RIFT-FULL
**Stated?** YES — `baseline_specification.md` §Fair Comparison Protocol point 7.
**Enforcement mechanism defined?** PARTIAL — stated in prose but not yet enforced in the experiment harness code. Requires: (a) single FCI run produces serialized G_T artifact, (b) both RIFT-FULL and RIFT-OBS load from same artifact, (c) no re-running of FCI independently in either system's evaluation path.
**Blocking for Phase 10?** YES — must be verified in experiment runner before evaluation begins.

### CF-2: Sage's Training Data Does Not Include Evaluation Period
**Defined?** NO — temporal split is not defined in any current Phase 2 document.
**Risk level:** HIGH — if Sage is trained on faults from the same campaign as the evaluation, results are invalid.
**Required action:** Define `t_split` in Phase 7 benchmark specification. Document in this file once defined.
**Blocking for Phase 10?** YES.

### CF-3: Sieve Receives Injection Capability Without SCM — Is This Fair to RIFT?
**Analysis:** Sieve receives the same injection infrastructure as RIFT. RIFT additionally has an SCM, identifiability checking, and CID scoring. This asymmetry is the intended experimental treatment (H2, H3). The comparison tests whether the SCM+CID layer adds measurable value over naive injection with binary matching. This is scientifically valid and fair — the experimental design would be meaningless if Sieve also had a full SCM. **No fairness concern.**

### CF-4: No Baseline Receives RIFT's CID Scores or EBD Outputs
**Stated?** YES — `baseline_specification.md`: "No baseline receives RIFT's CID scores or EBD outputs."
**Enforcement mechanism:** Not yet formally verified in code. Requires: (a) CID scoring module is internal to RIFT only, (b) baselines are implemented in isolated code paths that cannot import RIFT's causal inference modules, (c) evaluation harness provides only the common input protocol to each baseline.
**Blocking for Phase 10?** YES — code isolation must be verified.

---

## Missing Baselines — Reviewer Expectation Analysis

### Should an Oracle Baseline Be Reported?
**Recommendation: YES — include as an upper bound, not a competitor.**

An Oracle baseline receives the fault injection log directly (i.e., perfect knowledge of what was injected, where, and when) and outputs the correct root cause deterministically. Oracle Precision@1 = 1.0 by definition.

Reporting Oracle serves two purposes:
1. It defines the ceiling against which all methods are measured. A method that achieves 0.85 Precision@1 looks very different depending on whether Oracle is 1.0 or 0.90 (the latter would imply the benchmark has ambiguous ground truth).
2. It provides a sanity check: if any baseline exceeds Oracle's score, the evaluation protocol is broken.

Oracle is not a competitor — it is an evaluation integrity check and a reference point. **Add Oracle as a reference row in all results tables with a dagger (†) notation marking it as an upper bound, not a fair comparison.**

### Should Nearest-Neighbor Anomaly Detection Be a Baseline?
**Recommendation: OPTIONAL — low priority.**

A kNN-based baseline (e.g., k-nearest-neighbor in metric space, label = most common root cause among k neighbors) requires a labeled training corpus similar to Sage. Given that Sage+Chaos already covers the supervised/semi-supervised direction, a standalone kNN baseline would be redundant. If Sage's training data concerns are addressed, kNN adds minimal scientific value.

**Decision: Omit unless a reviewer specifically requests it. Note in the paper that kNN-style methods are subsumed by the Sage baseline.**

### Are Any 2023–2024 Published Microservice RCA Systems Missing?
**Recommendation: HIGH RISK — this is a likely reviewer objection.**

MicroRCA (Baseline 3) dates from 2020. Recent systems that a reviewer may expect to see:
- **DiagFusion / CORAL (2023):** Multi-modal fusion of metrics, traces, logs. If these are available and reproducible, one should be included.
- **RCAgent / LLM-based RCA (2024):** LLM-assisted root cause analysis using trace summarization. A reviewer from the AIOps community will ask why this is absent.
- **Nezha (2023, ASE):** Service mesh-based RCA using trace structure. Highly relevant to RIFT's setting.

**Required action:** The Phase 1 related work matrix (`docs/related_work_matrix.md`) must be checked for these systems. If any 2023–2024 system is reproducible (open-source implementation available), one should be added as Baseline 8 to avoid the "compared only against older methods" objection.

**This is a reviewer risk item, not a fairness violation. But it is a paper credibility risk that should be addressed before Phase 8 (baselines frozen).**

---

## Fairness Audit Summary Table

| Baseline | Status | Blocking Issue |
|---|---|---|
| 1 — Prometheus Threshold | FAIR | None |
| 2 — Isolation Forest | FAIR | Verify no overlap between 7-day training windows and evaluation trials |
| 3 — MicroRCA-Style | FAIR | None |
| 4 — Sieve | FAIR | Code isolation: Sieve must not import RIFT's causal inference modules |
| 5 — RIFT-OBS | FAIR (conditional) | G_T sharing enforcement must be verified in experiment harness |
| 6 — Ochiai Statistical Debugging | FAIR | None |
| 7 — Sage + Chaos | NEEDS_ADJUSTMENT | Temporal train/test split for Sage BN not yet defined |
| Oracle (reference) | — | Add as upper-bound reference row in results tables |

**Phase 10 gate condition:** All NEEDS_ADJUSTMENT items must be resolved and STATUS upgraded to FAIR before evaluation data is collected.
