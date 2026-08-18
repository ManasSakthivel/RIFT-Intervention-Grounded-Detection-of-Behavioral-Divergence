# RIFT — Experimental Hypotheses and Limitations
**Phase 2 | Version 1.0**

---

## Part Q — Experimental Hypotheses

Each hypothesis is formally stated, mapped to a specific experiment, metric, and baseline comparison. No hypothesis may appear in the paper without a corresponding entry in this table.

---

### H1 — RIFT Improves Root-Cause Attribution Over Observational RCA

**Formal statement:**
```
H1: Precision@1(RIFT-FULL) > Precision@1(best_observational_baseline)
    on the primary evaluation benchmark (frozen before evaluation)
    with statistical significance p < 0.05 (Mann-Whitney U test)
    and effect size Cliff's δ > 0.20 (small effect minimum)
```

**Operationalization:**
- Precision@1 = fraction of incidents where RIFT's top-attributed cause matches the ground-truth injected fault
- best_observational_baseline = max(MicroRCA-style, RIFT-OBS, Isolation Forest)
- Benchmark: ≥2 systems, ≥4 fault types, ≥3 trials per fault (see `benchmark_specification.md`, Phase 7)

**Experiment:** EXP-001 (Detection accuracy vs. all baselines)  
**Mapping in research_alignment.md:** RQ1  
**Dependent on:** Phase 7 (benchmark frozen), Phase 8 (baselines implemented), Phase 10 (evaluation)

**Directional prediction:** H1 is expected to hold most strongly on fault scenarios involving shared-infrastructure confounders (where observational methods cannot distinguish cause from co-effect).

---

### H2 — Interventions Provide Information Unavailable to Observational Methods Under Confounding

**Formal statement:**
```
H2: On the confounded fault subset C_confounded ⊆ benchmark:
    Precision@1(RIFT-FULL) > Precision@1(RIFT-OBS)
    with p < 0.05 and Cliff's δ > 0.20

where C_confounded = fault scenarios with ≥1 unobserved common cause
(defined at benchmark design time; confirmed by FCI bidirected edges in G_T)
```

**Operationalization:**
- C_confounded is a pre-designated subset of the benchmark containing at least one fault type where a shared physical host or shared database causes correlated anomalies across multiple services
- RIFT-OBS = RIFT without intervention (Baseline 5)

**Critical note:** H2 is the empirical defense of N2. If this hypothesis is not confirmed, the intervention layer provides no measurable benefit and the N1/N2 claims must be substantially weakened. This is the most important hypothesis.

**Experiment:** EXP-002 (Identifiability-conditioned attribution on confounded scenarios) + EXP-005 (RIFT-OBS ablation)
**Mapping in research_alignment.md:** RQ2
**Dependent on:** Benchmark design including confounded fault scenarios (n≥48 required for 80% power)

> **P1-03 fix:** H2 previously referenced EXP-009 (performance instrumentation — wrong).
> Correct mapping: EXP-002 (confounded scenario evaluation) and EXP-005 (RIFT-OBS ablation).

---

### H3 — Closed-Loop Model Update Improves Attribution Over One-Shot Intervention

**Formal statement:**
```
H3: Precision@1(RIFT-FULL-CLOSED-LOOP) > Precision@1(RIFT-ONE-SHOT)
    on multi-cause or ambiguous fault scenarios

where RIFT-ONE-SHOT = RIFT-FULL with closed-loop update disabled
    (model is NOT updated between successive interventions)
```

**Operationalization:**
- RIFT-ONE-SHOT: runs interventions in sequence but uses the initial candidate ranking from the original G_T for all subsequent selections — no Bayesian update of posterior
- RIFT-FULL-CLOSED-LOOP: updates candidate posterior and edge confidence after each intervention
- Expected benefit: closed-loop version converges to correct attribution in fewer interventions on multi-cause faults

**Experiment:** EXP-013 (Ablation: closed-loop update necessity)  
**Mapping in research_alignment.md:** RQ2 (sub-component: N5 contribution)  
**Dependent on:** Phase 9 (ablations)

---

### H4 — Systems-Aware Intervention Selection Reduces Cost While Preserving Accuracy

**Formal statement:**
```
H4: Cost(RIFT-FULL) < Cost(RIFT-RANDOM-SELECTION)
    with no statistically significant difference in Precision@1
    (i.e., accuracy preserved at p > 0.10, cost reduced at p < 0.05)

where RIFT-RANDOM-SELECTION = RIFT with interventions selected uniformly at random
    from the safety-feasible set (ignoring EIG and Utility)
Cost = cumulative ED (execution duration) across all interventions to reach attribution
```

**Operationalization:**
- The Utility-guided selection is expected to reach confident attribution with fewer/cheaper interventions than random selection
- "Same accuracy" is the null hypothesis for the accuracy comparison — we want to show cost improves without harming precision

**Experiment:** EXP-014 (Cost model effectiveness — N3 contribution)  
**Mapping in research_alignment.md:** RQ6  
**Dependent on:** Phase 9 (ablations)

---

### H5 — RIFT Generalizes Across Independent Microservice Systems

**Formal statement:**
```
H5: Precision@1(RIFT_train_on_A_test_on_B) ≥ 0.70 × Precision@1(RIFT_train_on_A_test_on_A)

for at least one pair (A, B) of independently designed benchmark systems
```

**Operationalization:**
- Train set: Online Boutique (system A) — learn causal graph, calibrate thresholds
- Test set: Sock Shop (system B) — evaluate with learned parameters transferred
- The 0.70 threshold means: out-of-distribution performance is no worse than 30% of in-distribution performance
- Stronger result: show RIFT transfers better than the best observational baseline (H5 extension)

**Experiment:** EXP-011 (Cross-system generalization)  
**Mapping in research_alignment.md:** RQ5  
**Dependent on:** Phase 11 (generalization)

---

### H1–H5 Experiment Map

| Hypothesis | Experiment | Phase | Metric | Baseline |
|---|---|---|---|---|
| H1 | EXP-001 | 10 | Precision@1, F1, AUROC | MicroRCA, IF, RIFT-OBS, Sieve |
| H2 | EXP-002 + EXP-005 | Linux | Precision@1 on C_confounded | RIFT-OBS |
| H3 | EXP-013 | Linux | Precision@1 on multi-cause faults | RIFT-ONE-SHOT |
| H4 | EXP-014 | Linux | Cost (ED) at same Precision@1 | RIFT-RANDOM |
| H5 | DEFERRED — no experiment registered | Future | Cross-system Precision@1 | N/A |

> **P1-03 fix:** EXP-009 = "Performance instrumentation" (no hypothesis). Corrected to EXP-002/EXP-005 for H2.
> **P1-10 fix:** H5 has no registered experiment in experiments/REGISTRY.yaml.
> H5 is explicitly DEFERRED to future work and must NOT appear in paper contributions.
> EXP-011 = "FCI robustness on noisy data" (not cross-system generalization).

---

## Part R — Explicit Limitations

RIFT cannot guarantee causal attribution in the following scenarios. These must appear in the paper's Threats to Validity section.

---

### L1 — Unobserved Confounding

**When:** Two candidate services are both affected by a latent common cause (e.g., shared host hardware contention) not captured in the metric pipeline.

**Effect:** FCI may produce a bidirected edge between both services. Interventions may produce inconclusive CID scores. RIFT will output ATTRIBUTION_UNCERTAIN or MULTI_CAUSE with HIDDEN_CONFOUNDER_SUSPECTED.

**What RIFT does:** Reports explicitly that hidden confounders are suspected. Does not force attribution.

---

### L2 — Invalid Intervention

**When:** The intervention mechanism fails to set X to the target value (precision_err ≥ 0.20), or produces side effects on non-descendants.

**Effect:** The InterventionRecord is marked INVALID or CONFOUNDED. The observation is discarded.

**What RIFT does:** Retries with adjusted parameters (up to 2 retries per intervention). If all retries fail, skips to next candidate. If no valid interventions can be executed, reports ATTRIBUTION_UNCERTAIN.

---

### L3 — Non-Replayable System State

**When:** The incident involves a non-deterministic race condition or a transient state that cannot be reproduced by re-executing the same request pattern under the same load.

**Effect:** Intervention may not reproduce the original failure. CID scores will be near zero even for the true root cause.

**What RIFT does:** Detects this via low CID scores across all candidates. Reports NON_REPRODUCIBLE_INCIDENT. Cannot provide intervention-based attribution; falls back to observational RIFT-OBS estimate with elevated uncertainty.

---

### L4 — Insufficient Observability

**When:** The root cause service is not instrumented (not in S), or critical metrics (e.g., DB row-level state) are not exposed to RIFT.

**Effect:** The true root cause is in L(t), not V. All attributed causes are ancestors of the true cause within RIFT's instrumentation boundary.

**What RIFT does:** Reports EBD with boundary_limited = TRUE. Explicitly notes that the true root cause may be upstream of the earliest instrumented divergence point.

---

### L5 — Non-Identifiable Query

**When:** The ID algorithm (Shpitser & Pearl) returns FAIL for the causal query P(Y | do(X := x)) due to the graph structure (e.g., complete bipartite hidden confounder pattern).

**Effect:** The causal effect cannot be estimated from observational data or disambiguated by a single intervention.

**What RIFT does:** Reports NON_IDENTIFIABLE for this candidate. Requires a different intervention type (e.g., instrumental variable) or falls back to ranking by anomaly score with no causal guarantee.

---

### L6 — Simultaneous Causal Events

**When:** Two independent faults occur within the same time window, creating confounded observations in G_T.

**Effect:** Both faults appear as candidate EBDs. The causal graph may incorrectly merge their effects. Attribution may be assigned to the wrong fault or reported as MULTI_CAUSE with incorrect component decomposition.

**What RIFT does:** Detects simultaneous events via the fault injection log (in the testbed) or via BOCPD detecting multiple structural breaks. Reports SIMULTANEOUS_FAULTS with caveat that attribution confidence is reduced.

---

### L7 — External Dependencies

**When:** The root cause is in a third-party service (external payment gateway, external CDN, cloud provider outage) outside RIFT's instrumentation and intervention boundaries.

**Effect:** All internal services appear downstream of an uninstrumented node. RIFT will attribute to the first internal service that receives errors from the external dependency.

**What RIFT does:** Reports boundary_limited = TRUE, noting that external services are outside the intervention scope. If the external service's health endpoint is observable, RIFT adds it as an unintervenable observation node in G_T.

---

### L8 — Causal Graph Staleness

**When:** A deployment, auto-scaling event, or configuration change occurs between graph learning and incident attribution, making G_T incorrect.

**Effect:** Intervention target selection may be based on a stale causal structure. Interventions on the correct service may not show the expected effect.

**What RIFT does:** BOCPD detects structural breaks; timestamps G_T with a validity window. Reports STALE_MODEL if attribution is requested outside the validity window. Triggers an emergency graph re-learning cycle.
