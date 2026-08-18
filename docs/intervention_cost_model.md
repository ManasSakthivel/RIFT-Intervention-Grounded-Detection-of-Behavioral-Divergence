# RIFT — Intervention Cost Model and Minimum Safe Intervention Set
**Phase 2 | Version 1.0**

---

## Part K — Systems-Aware Intervention Cost Model

### K.1 Framing

Phase 1 established that generic minimization theory (Golovin & Krause 2011; Eberhardt & Scheines 2007) is **not novel**. RIFT's contribution is a **systems-specific cost model** that accounts for operational constraints absent from the theoretical literature: blast radius, SLA impact, rollback cost, and safety budgets.

RIFT frames intervention selection as **adaptive experimental design under operational constraints** — an extension of active learning / active causal inference adapted to the live distributed systems context.

---

### K.2 Measurable Cost Factors

Each factor is included only if it can be measured at runtime. Unmeasurable factors are excluded.

**Factor 1 — Blast Radius (BR)**

```
BR(I) = fraction of downstream services expected to be observably affected by intervention I

BR(I) = |Desc(X, G_T) ∩ S| / |S|

where X is the target variable of I and Desc(X, G_T) is the set of descendants of X in G_T.
```

Measurement: computed analytically from G_T before execution.  
Range: [0, 1]. Acceptable threshold: BR(I) < 0.30 (default; configurable).

**Factor 2 — SLA Impact (SLAI)**

```
SLAI(I) = expected fractional degradation in user-visible SLO metrics during intervention

SLAI(I) = Σ_k w_k · P(SLO_k violated | do(X := x))
```

where w_k is the business weight of SLO k (e.g., checkout_availability weighted higher than recommendation_latency).

Measurement: estimated from historical data — how much does a +X% change in the target variable historically degrade SLO k? Uses a pre-computed **impact lookup table** calibrated during system initialization.  
Range: [0, 1]. Acceptable threshold: SLAI(I) < 0.05 (5% SLO degradation budget).

**Factor 3 — Execution Duration (ED)**

```
ED(I) = expected wall-clock time consumed by intervention I

ED(I) = Δ_int_required + Δ_recovery_expected
Δ_int_required = 3 × p99_lat_target_service
Δ_recovery_expected = historical mean recovery time for this intervention type
```

Measurement: directly from historical InterventionRecords and current system p99 latency.  
Range: [0, ∞) seconds. Budget constraint: cumulative ED across all interventions in an incident ≤ T_budget (configurable; default 600s).

**Factor 4 — Rollback Cost (RC)**

```
RC(I) = cost of undoing intervention I if it cannot be cleanly removed

RC(I) = P(recovery_failure | I) × (manual_recovery_time_estimate)
```

P(recovery_failure | I) is estimated from historical InterventionRecords for this intervention type.  
Measurement: empirical from intervention history. Zero for purely additive interventions (latency injection via tc netem). Non-zero for state-modifying interventions (e.g., database configuration changes).  
Default: RC = 0 for network/latency interventions; RC = HIGH for any data-state intervention (blocked by default).

**Factor 5 — Expected Information Gain (EIG)**

```
EIG(I) = H(C) − E_Y[ H(C | Y = y) ]

where:
  C = current probability distribution over root cause candidates
  H(C) = entropy of candidate distribution before intervention
  Y = expected observable outcome variable under intervention I
  H(C | Y = y) = posterior entropy after observing Y = y
```

Measurement: computed from current candidate posterior and the causal graph. EIG is the Bayesian expected reduction in uncertainty about the root cause, analogous to Expected Information Gain in active learning.

This is the **only theoretical component** of the cost model. RIFT uses the standard EIG formula; no novel minimization theory is claimed.

**Factor 6 — Service Criticality (SC)**

```
SC(I) = criticality weight of the target service

SC(s_A) = predefined tier: { CRITICAL=1.0, HIGH=0.7, MEDIUM=0.4, LOW=0.1 }
```

Criticality is operator-defined at system setup. RIFT will not execute an intervention on a CRITICAL-tier service during peak traffic windows without elevated authorization.

**Factors excluded (unmeasurable):**
- Data sensitivity: not measurable from metrics; handled by authorization rules
- Intervention confidence: folded into EIG (lower-confidence graph → lower EIG)

---

### K.3 Composite Cost Function

```
Cost(I) = α·BR(I) + β·SLAI(I) + γ·ED(I) + δ·RC(I) + ε·SC(I)
```

Where α, β, γ, δ, ε are non-negative weights summing to 1, configured per deployment.  
Default: α=0.3, β=0.3, γ=0.15, δ=0.15, ε=0.10.

---

### K.4 Utility Function

```
Utility(I) = EIG(I) / Cost(I)
```

RIFT selects the next intervention as:

```
I* = argmax_{I ∈ Feasible(C)} Utility(I)

subject to:
  BR(I) < BR_max
  SLAI(I) < SLAI_max
  cumulative ED < T_budget
  RC(I) < RC_max
  authorization(SC(I)) granted
```

Feasible(C) = set of interventions on the current candidate set C that satisfy all safety constraints.

---

### K.5 Adaptive Greedy Selection

RIFT uses **greedy adaptive selection** (one intervention at a time, recomputing Utility after each observation):

```
while confidence(top_candidate) < θ_confidence AND budget_remaining > 0:
  I* = argmax Utility(I)  over feasible interventions
  execute(I*)
  observe outcome Y
  update candidate posterior (see closed_loop_model.md)
  recompute Utility for remaining candidate interventions
```

This greedy policy achieves a (1 − 1/e)-approximation to the optimal adaptive policy when EIG satisfies submodularity — a condition that holds when candidate hypotheses are mutually exclusive (Golovin & Krause 2011). RIFT cites this theoretical bound but notes that the distributed systems setting may not always satisfy strict submodularity (multi-cause scenarios). The paper will discuss this limitation explicitly.

---

## Part L — Minimum Safe Intervention Set

### L.1 Definition

The **Minimum Safe Intervention Set (MSIS)** for incident I_c with candidate cause set C = {X₁, …, Xₘ} is the smallest set of interventions IS = {I₁, I₂, …, Iₖ} such that:

```
MSIS(C, Y) = argmin_{IS} |IS|

subject to:
  (1) After executing IS, the causal attribution for Y is DEFINITIVE or BOUNDED_UNCERTAIN
  (2) ∀ Iⱼ ∈ IS: safety constraints satisfied (BR, SLAI, RC, SC)
  (3) ∀ Iⱼ ∈ IS: cumulative cost ≤ T_budget
  (4) IS is informationally sufficient: H(C | observations from IS) < θ_entropy
```

**Clause (1):** Attribution is DEFINITIVE when CID(X → Y) > θ_cid for a single X, or BOUNDED_UNCERTAIN when the joint CID of a multi-cause set covers ≥ 90% of observed divergence.

**Clause (4):** Informational sufficiency requires the posterior entropy over candidates to drop below θ_entropy = log(1/θ_confidence) nats (default: requires posterior probability > 0.80 on top candidate).

### L.2 Why MSIS Is Not a Novel Algorithm

The theoretical problem of finding minimum intervention sets has been solved (Eberhardt & Scheines 2007 for causal structure learning; Golovin & Krause 2011 for adaptive testing). RIFT **does not claim novel algorithm theory**.

RIFT's contribution in this space is:
1. The **systems constraints** (clauses 2, 3) that transform the theoretical minimization into a practical operational problem
2. The **DEFINITIVE/BOUNDED_UNCERTAIN attribution criterion** (clause 1) that replaces the theoretical "full graph identification" criterion with an operationally useful partial identification goal
3. The **online, adaptive execution** of MSIS in a live system where observations take real time and cost real SLA budget

### L.3 MSIS Computation

RIFT computes MSIS via **greedy forward selection**:

```
IS = {}
while not sufficient(IS) and budget_remaining:
    I* = argmax Utility(I) over (C \ IS) with safety constraints
    IS = IS ∪ { I* }
    execute(I*)
    observe, update posterior
return IS
```

This greedy policy is near-optimal under the submodularity assumption (see K.5).  
Worst-case IS size: |C| (all candidates). Expected IS size: O(log(1/θ_entropy)) under submodularity.

### L.4 Causal Identifiability and MSIS

RIFT checks identifiability before computing MSIS:

```
Query: P(Y | do(X := x_nominal))  for each X ∈ C

If identifiable via backdoor/front-door/ID algorithm:
  → Compute estimate from observational data
  → Intervention may not be needed for this X
  → Remove X from intervention candidate set

If not identifiable from observational data:
  → Add X to intervention candidate set (must be experimentally verified)
```

This reduces the MSIS size by eliminating candidates that can be attributed observationally.  
See `causal_assumptions.md` A3 for identifiability conditions.
