# RIFT — Causal Assumptions
**Phase 2 | Version 1.0**

---

## Overview

Every causal claim RIFT makes is conditional on a set of assumptions. This document states every assumption explicitly, assesses its realism in microservice systems, and defines RIFT's policy when the assumption is violated or unverifiable.

**Testability labels:**
- **GUARANTEED** — holds by construction (e.g., time-sliced DAG acyclicity)
- **TESTABLE** — RIFT can check this empirically at runtime
- **PARTIAL** — partially checkable; residual uncertainty documented
- **ASSUMPTION-ONLY** — cannot be verified; stated as prior; disclosed as limitation

---

## A1 — Causal Markov Condition

**Statement:**
Each endogenous variable Vᵢ is independent of all its non-descendants, conditional on its direct parents PA(Vᵢ):

```
Vᵢ  ⊥⊥  NonDesc(Vᵢ)  |  PA(Vᵢ)
```

**Required for:** Structure learning, backdoor/front-door adjustment, all do-calculus identification.

**Realism:** MODERATE. Holds when the graph is correctly specified. Violated by unobserved shared-infrastructure effects (noisy-neighbor CPU, shared network switch).

**RIFT policy:**
- Stated as a required modeling assumption; disclosed in every causal result.
- Violations are partially detectable by residual correlation tests after conditioning on PA(Vᵢ).
- Phase 11 sensitivity analysis tests robustness to violations.

**Testability:** PARTIAL

---

## A2 — Faithfulness

**Statement:**
Every conditional independence in the observed distribution corresponds to a d-separation in the true causal graph G. No cancellations across paths produce spurious independencies.

**Required for:** Correct edge orientation by constraint-based discovery (PC / FCI algorithms).

**Realism:** LOW-MODERATE. Violated when two causal paths have equal-and-opposite effects, or when sparse data creates apparent independence.

**RIFT policy:**
- Faithfulness is a required assumption for observational graph learning.
- RIFT uses **interventions to test suspected faithfulness violations**: if observational data suggests X ⊥⊥ Y | Z but do(X:=x) causes Y to change, a violation is confirmed.
- Edges involved in confirmed faithfulness violations are marked UNRELIABLE in G_T.

**Testability:** PARTIAL (interventionally testable for specific edge pairs)

---

## A3 — Causal Sufficiency

**Statement:**
There are no unobserved common causes of any two variables in V. Formally: for all Vᵢ, Vⱼ ∈ V, any common cause C of both satisfies C ∈ V.

**Required for:** PC algorithm to produce a correct DAG (not just a partial ancestral graph).

**Realism:** LOW. Almost certainly violated in real systems:
- Co-located services share host CPUs (common cause of correlated CPU spikes)
- Services sharing a database exhibit correlated latency (common cause: DB contention)
- Simultaneous deployments affect multiple services (common cause: deployment event)

**RIFT policy — critical:**
- **DO NOT assume causal sufficiency by default.**
- Use **FCI algorithm** instead of PC for initial graph learning. FCI produces a Maximal Ancestral Graph (MAG) / Partial Ancestral Graph (PAG) that explicitly represents possible hidden confounders as bidirected edges (↔).
- When a bidirected edge Vᵢ ↔ Vⱼ appears, RIFT reports: *"Possible hidden confounder between Vᵢ and Vⱼ; causal direction uncertain."*
- Use interventions to partially disambiguate: if do(Vᵢ := x) changes Vⱼ but do(Vⱼ := y) does not change Vᵢ, this is evidence for Vᵢ → Vⱼ (though not conclusive with hidden confounders).
- If bidirectional interventional evidence is ambiguous: report the pair as POTENTIALLY_CONFOUNDED and abstain from definitive single-cause attribution.

**Testability:** PARTIAL (interventions reduce uncertainty; cannot fully resolve hidden confounders)

---

## A4 — Acyclicity (DAG)

**Statement:**
The causal graph G_T over time-sliced variables is a Directed Acyclic Graph.

**Required for:** Pearl's do-calculus (defined over DAGs).

**Realism:** VIOLATED for static graphs of microservice systems (retries, circuit breakers, back-pressure). GUARANTEED for time-sliced graphs.

**RIFT resolution:** Time-sliced DAG formulation (see `formal_model.md` Part C). All edges are strictly forward in time or within-step with verified acyclic orientation. Acyclicity guaranteed by construction.

**Testability:** GUARANTEED by construction.

---

## A5 — Intervention Validity

**Statement:**
When RIFT executes do(X := x):
1. X is successfully set to x
2. No variables outside Desc(X) are perturbed by the intervention mechanism
3. The observed post-intervention outcome is attributable to the intervention, not concurrent events

**Required for:** Interpreting post-intervention observations as samples from P(Y | do(X:=x)).

**Realism:** MODERATE-LOW. Side effects occur when injection mechanisms perturb shared infrastructure. Concurrent events are unavoidable in production-like settings.

**RIFT policy:**
- Precision check: |x_achieved − x_requested| / x_requested < 0.20
- Clean window check: no anomalies detected in non-descendants of X during intervention
- Concurrent event check: no K8s events, deployments, or other injections within ±30s
- Recovery check: system returns to pre-baseline for X within 120s
- Intervention marked CONFOUNDED or INVALID if any check fails; result discarded

**Testability:** TESTABLE at runtime.

---

## A6 — Stationarity Within Learning Window

**Statement:**
The causal graph G_T is approximately stationary during the observation window used for causal discovery. Structural equations F do not change significantly between windows.

**Required for:** Validity of a single consistent causal structure learned from windowed data.

**Realism:** MODERATE. Violated during deployments, configuration changes, autoscaling events.

**RIFT policy:**
- BOCPD (Bayesian Online Change Point Detection) monitors for structural breaks.
- Detected break → reset causal discovery window; version and timestamp G_T.
- Attribution requests using an expired G_T return STALE_MODEL status.

**Testability:** TESTABLE via change-point detection.

---

## A7 — Temporal Resolution Sufficiency

**Statement:**
Window size Δt satisfies: Δt ≥ 2 × p99_inter_service_latency (causal propagation captured) and Δt ≤ min_anomaly_duration (EBD resolution preserved).

**RIFT policy:** Δt = 10s default; validated at startup against observed trace latencies; configurable.

**Testability:** TESTABLE via trace analysis at initialization.

---

## A8 — Positivity

**Statement:**
Every intervention value x lies within the physically achievable support of variable X in the target system.

**RIFT policy:** Achievability range checked by intervention planner before dispatch. Out-of-range interventions rejected with INVALID_INTERVENTION.

**Testability:** TESTABLE — enforced by intervention engine.

---

## Assumption Summary

| ID | Assumption | Holds in Microservices | Policy | Testable |
|---|---|---|---|---|
| A1 | Causal Markov | MODERATE | Disclosed; sensitivity analysis | PARTIAL |
| A2 | Faithfulness | LOW-MODERATE | Interventional testing; flag violations | PARTIAL |
| A3 | Causal Sufficiency | LOW | FCI algorithm; bidirected edges; interventional disambiguation | PARTIAL |
| A4 | Acyclicity | VIOLATED (static) / GUARANTEED (time-sliced) | Time-sliced DAG | GUARANTEED |
| A5 | Intervention Validity | MODERATE-LOW | Precision + clean-window + recovery checks | TESTABLE |
| A6 | Stationarity | MODERATE | Change-point detection; versioned graphs | TESTABLE |
| A7 | Temporal Resolution | Context-dependent | Calibrated Δt; startup validation | TESTABLE |
| A8 | Positivity | Mostly holds | Range checking | TESTABLE |

---

## Mandatory Paper Disclosure

Every causal result reported by RIFT must carry the following qualifier:

> *"This attribution holds under: Causal Markov (A1), Faithfulness (A2, partially tested by intervention), FCI-based hidden confounder detection (A3), time-sliced acyclicity (A4), intervention validity (A5, verified at runtime), and stationarity (A6, monitored by BOCPD). Results may not hold if additional unmeasured confounders exist beyond those detectable by FCI and interventional disambiguation. Sensitivity analysis is reported in Section 5."*
