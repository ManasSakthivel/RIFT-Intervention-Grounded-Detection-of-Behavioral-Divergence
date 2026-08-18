# RIFT — Intervention Semantics
**Phase 2 | Version 1.0**

---

## Critical Terminological Distinctions

The following six concepts are distinct and must never be used interchangeably.

---

### OBSERVATION

Passively recording the value of a variable without modifying the system:

```
Observe(Vᵢ[t]) → record value; system state unchanged
```

Produces an **observational conditional**: P(Y | X = x).  
Subject to confounding: P(Y | X = x) ≠ P(Y | do(X := x)) whenever unobserved confounders exist.

*Example:* Recording that s₂.latency_p99 = 800ms during an incident.

---

### MUTATION

Directly changing a system variable in an ad-hoc manner — without a formal causal model, without isolating the structural mechanism, and without intent to measure causal effects.

Properties:
- System state is modified
- Multiple variables may change simultaneously as a side effect
- No counterfactual comparison is made
- The resulting distribution is **not interpretable** as P(Y | do(X:=x)) without additional controls

*Example:* Restarting a pod during an incident as a remediation. Changes heap state, connection pool, in-flight requests, and queue depth simultaneously — not a controlled intervention.

**RIFT's position:** Mutation is not equivalent to intervention. Restart/redeploy/rollback during a live incident is mutation, not a causal experiment.

---

### FAULT INJECTION

Deliberately introducing a failure condition into a running system to observe failure propagation or test resilience:

Properties:
- Controlled, reproducible modification of a target variable
- Goal: "does the system survive?" — resilience testing
- No formal causal model governs hypothesis formation or outcome interpretation
- Multiple variables cascade from the injected fault without isolation
- Outcome interpreted as pass/fail against an SLO — binary

*Example:* LitmusChaos injecting +500ms latency on s₁ to test whether the circuit breaker in s₂ trips within 10s.

**RIFT's position:** Fault injection provides the **execution infrastructure** for RIFT's interventions. The critical difference is that RIFT wraps fault injection with a formal SCM, an identifiability check, a pre/post observational comparison, and a causal attribution step. Fault injection alone is not a causal experiment.

---

### INTERVENTION (formal definition)

A controlled, targeted modification of exactly one variable's structural mechanism, formally modeled as Pearl's do-operator on the SCM, with the explicit purpose of estimating P(Y | do(X := x)) for a target Y.

**Formal definition:**

```
do(X := x):
  Given SCM M = ⟨U, V, F, P(U)⟩ and causal graph G:

  1. Remove all incoming edges to X in G → produce mutilated graph G_{do(X:=x)}
  2. Replace structural equation fₓ ∈ F with the constant equation X := x
  3. All other fⱼ ∈ F (j ≠ X) remain unchanged
  4. Evaluate P(Y | do(X := x)) = E_{U}[ Y under M_{do(X:=x)} ]
```

Properties:
- **Exactly one** structural mechanism is replaced
- Descendants of X respond naturally through their unchanged fⱼ
- Non-descendants of X are unaffected (Causal Markov condition)
- The resulting distribution P(Y | do(X := x)) is the **interventional distribution** — strictly distinct from the observational conditional P(Y | X = x)

*Example:* do(latency_s₁ := 50ms)  
Removes all causes of s₁'s latency from the graph. Sets s₁.latency to 50ms regardless of its natural parents. Observes how s₂.latency responds through f_s₂, which remains unchanged.

---

### COUNTERFACTUAL

A statement about what the value of Y **would have been** in a specific observed execution, had X been different — while holding all exogenous variables at their actual realised values:

```
Y_{x}(u) = value of Y under do(X := x) in SCM M with exogenous realization U = u
```

**Distinction from intervention:**
- **Intervention**: P(Y | do(X := x)) averaged over all U — population-level causal effect
- **Counterfactual**: Y_{x}(u) for a specific unit with U = u — individual-level causal claim (Pearl's Layer 3)

**RIFT's use:** RIFT operates at the **intervention level** (Layer 2), not the counterfactual level (Layer 3), because:
1. Distributed systems are stochastic — U is never observed
2. Individual counterfactuals require knowledge of the actual exogenous noise realization, which is latent
3. Population-level interventional distributions are sufficient for root-cause attribution purposes

RIFT uses the phrase "counterfactual observation" to mean: the observed system behavior under do(X:=x). This is technically an interventional distribution sample, not a Layer-3 counterfactual. The paper must state this distinction explicitly.

---

### DO-CALCULUS

Pearl's three-rule formal calculus for transforming expressions involving do(·) into expressions computable from observational distributions, given G:

- **Rule 1 (Insertion/deletion of observations):** P(y | do(x), z, w) = P(y | do(x), w) if (Y ⊥⊥ Z | X, W)_{G_{X̄}}
- **Rule 2 (Action/observation exchange):** P(y | do(x), do(z), w) = P(y | do(x), z, w) if (Y ⊥⊥ Z | X, W)_{G_{X̄Z̄}}
- **Rule 3 (Insertion/deletion of actions):** P(y | do(x), do(z), w) = P(y | do(x), w) if (Y ⊥⊥ Z | X, W)_{G_{X̄Z(W)}}

**Primary identification results RIFT uses:**

```
Backdoor adjustment (when Z satisfies backdoor criterion for (X, Y) in G):
  P(Y | do(X := x)) = Σ_z P(Y | X=x, Z=z) · P(Z=z)

Front-door adjustment (when M satisfies front-door criterion):
  P(Y | do(X := x)) = Σ_m P(M|X=x) · Σ_{x'} P(Y|M,X=x') · P(X=x')

ID algorithm (Shpitser & Pearl, 2006):
  General identifiability; returns identifying functional or FAIL
```

**RIFT's use of do-calculus:** RIFT uses do-calculus to:
1. Check identifiability before deciding between observational estimation and live intervention
2. Compute observational adjustment baselines for comparison
3. Predict what the intervention *should* produce if G is correct (as a model consistency check)

RIFT does **not** rely solely on do-calculus to estimate causal effects from observational data for its primary attribution results — it executes interventions and directly observes the interventional distribution.

---

## Part E — Formal Intervention Semantics in RIFT

### E.1 What Structural Mechanism Is Replaced

`do(X := x)` replaces the structural equation for X:

```
Before:   X[t] = fₓ( PA(X[t]), Uₓ[t] )
After:    X[t] = x    ← constant; all edges into X removed in G_{do(X:=x)}
```

All other fⱼ for j ≠ X are **unchanged**.

Runtime implementation:

| Variable Type | Mechanism Replaced | Runtime Method |
|---|---|---|
| Service request latency | Natural latency distribution | `tc netem delay` on container network namespace |
| Service error rate | Natural error distribution | Fault-injection sidecar; return errors for fraction p of RPCs |
| CPU utilization | Natural CPU scheduling | `cgroup cpu.cfs_quota_us` limit |
| Memory utilization | Natural memory allocation | `cgroup memory.limit_in_bytes` |
| Network packet loss | Natural network reliability | `tc netem loss` on egress interface |

Each implementation replaces exactly one structural mechanism. RIFT documents which mechanism is replaced for each intervention type.

### E.2 Variables Held Fixed

Under `do(X := x)`:

```
Fixed:        X = x  (by construction)
Unaffected:   NonDesc(X) in G  (by Causal Markov, A1)
Responding:   Desc(X) in G  (through their unchanged fⱼ)
```

If a variable Z ∉ Desc(X) empirically changes after `do(X := x)`, RIFT infers one of:
1. G is incorrect (Z is actually a descendant of X — update graph)
2. Intervention had side effects (A5 violation — discard observation)
3. Concurrent event affected Z (clean-window check failed — discard)

This is detected by the **side-effect monitor** (E.6).

### E.3 Downstream Variables Allowed to Respond

```
Desc(X, G) = { Y : ∃ directed path X → ⋯ → Y in G }
```

All Y ∈ Desc(X, G) respond naturally through their unchanged structural equations, yielding samples from P(Y | do(X := x)).

### E.4 Runtime Execution Protocol

```
Step 1  PLAN       Select (X, x) from intervention planner
Step 2  VALIDATE   Check: safety constraints, blast-radius, SLA guard, clean window
Step 3  AUTHORIZE  Require sign-off from RIFT safety module
Step 4  BASELINE   Capture O(t₀ - 60s) through O(t₀) as pre-intervention baseline
Step 5  INJECT     Apply runtime mechanism (tc, cgroup, sidecar)
Step 6  VERIFY     Confirm X ≈ x in subsequent observations within ε_tol = 20%
Step 7  OBSERVE    Record O(t₀) through O(t₀ + Δ_int) during intervention window
Step 8  REMOVE     Remove runtime mechanism
Step 9  RECOVER    Confirm X returns to baseline within Δ_recovery = 120s
Step 10 RECORD     Write InterventionRecord to audit log
```

Intervention window Δ_int ≥ 3 × p99_request_latency (minimum duration for sufficient signal).

### E.5 InterventionRecord Schema

```
InterventionRecord {
  id:             UUID
  target:         ServiceID
  variable:       VariableName
  value:          requested value x
  t_start:        timestamp
  t_end:          timestamp
  pre_baseline:   { Vᵢ[t] for all i, t ∈ [t_start - 60s, t_start) }
  post_obs:       { Vᵢ[t] for all i, t ∈ [t_start, t_end] }
  recovery_obs:   { Vᵢ[t] for all i, t ∈ [t_end, t_end + 60s] }
  achieved_val:   measured value of X during intervention
  precision_err:  |x - achieved_val| / x
  side_effects:   list of variables outside Desc(X) that changed
  clean_window:   bool
  status:         VALID | CONFOUNDED | IMPRECISE | FAILED
}
```

### E.6 Validity Verification Checks

An intervention is marked **VALID** iff ALL of the following:

| Check | Condition | Failure Action |
|---|---|---|
| Precision | `precision_err < 0.20` | Mark IMPRECISE; retry with adjusted parameters |
| Clean window | `side_effects = []` | Mark CONFOUNDED; discard |
| Concurrent events | No K8s events / deployments in ±30s window | Mark CONFOUNDED; discard |
| Recovery | X returns to baseline within 120s | Mark FAILED; trigger rollback |
| Sufficient duration | Δ_int ≥ 3 × p99_lat | Mark INSUFFICIENT; extend duration |

Only VALID interventions contribute to causal attribution. CONFOUNDED or IMPRECISE results are discarded and the query is retried or marked UNCERTAIN.
