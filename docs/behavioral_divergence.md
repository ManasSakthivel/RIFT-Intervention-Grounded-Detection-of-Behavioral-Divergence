# RIFT — Behavioral Divergence and Confounding Model
**Phase 2 | Version 1.0**

---

## Part G — Confounding in Microservice Systems

### G.1 Definitions

**Observed confounder:**  
A variable Z ∈ V that is a common cause of both X and Y, and is observed by RIFT:

```
Z → X,  Z → Y
```

An observed confounder can be controlled for via backdoor adjustment:
```
P(Y | do(X := x)) = Σ_z P(Y | X = x, Z = z) · P(Z = z)
```

*Microservice example:* External load (requests_per_second) drives both frontend_CPU and checkout_latency simultaneously. If external load is observed (via ingress metrics), it is an observed confounder and can be adjusted away.

---

**Unobserved confounder:**  
A variable U ∈ L(t) (latent) that is a common cause of both X and Y:

```
U → X,  U → Y    where U ∉ V (not observed)
```

An unobserved confounder means P(Y | X = x) ≠ P(Y | do(X := x)) and the backdoor criterion cannot be applied with available data. The causal effect of X on Y is **not identifiable from observational data alone**.

*Microservice example:*

```
U (shared host CPU contention, unobserved)
  ↓          ↓
s_A.cpu    s_B.cpu
  ↓          ↓
s_A.lat    s_B.lat
```

A noisy-neighbor workload on the physical host drives both s_A.cpu and s_B.cpu up simultaneously. The observational correlation between s_A.lat and s_B.lat does not reflect a direct causal link — it is induced by U. An observational RCA system will incorrectly attribute s_A as causing s_B's latency spike.

RIFT's response: Execute do(s_A.lat := 50ms) — forcibly set s_A's latency to nominal. If s_B.lat remains elevated, U (not s_A) is the cause. FCI detects the bidirected edge s_A.lat ↔ s_B.lat as a signal of possible hidden confounding.

---

**Mediator:**  
A variable M on a directed causal path between X and Y:

```
X → M → Y
```

Conditioning on M blocks the indirect path and should **not** be done when estimating the total causal effect of X on Y.

*Microservice example:* `auth_service.lat → token_cache.depth → checkout.lat`  
auth_service latency increases token cache contention (mediator) which then increases checkout latency. Conditioning on cache depth when estimating auth's effect on checkout would block the causal path and underestimate auth's contribution.

**RIFT's handling:** RIFT identifies mediators from the graph structure and excludes them from adjustment sets when estimating total effects. For direct-effect estimation only, conditioning on mediators is intentional.

---

**Collider:**  
A variable C with two or more causes in V:

```
X → C ← Y
```

Conditioning on a collider C **opens** a spurious path between X and Y that is otherwise blocked.

*Microservice example:* `payment_error` is caused by both `payment_service.crash` and `fraud_detection.reject`. Conditioning on payment_error = TRUE induces a spurious correlation between crashes and fraud rejections — even if they are independent in reality.

**RIFT's handling:** The FCI algorithm identifies colliders via v-structure detection. RIFT avoids conditioning on colliders unless necessary for a specific query. If a collider is included in an adjustment set, RIFT flags the result as COLLIDER_CONDITIONED and reports elevated uncertainty.

---

**Common cause:**  
Equivalent to a confounder — a variable that is a cause of multiple downstream variables:

```
Z → X,  Z → Y
```

At the service level, the most common common causes are:
1. Shared database: `db_contention → s_A.lat, s_B.lat`
2. Shared network switch: `switch_congestion → net_lat_A, net_lat_B`
3. Deployment event: `deploy_event → error_rate_A, error_rate_B, error_rate_C`

---

### G.2 Concrete Confounding Example

Consider three services: API Gateway (G), Payment Service (P), Database (DB).

**True causal structure:**

```
U (shared DB host memory pressure, unobserved)
  ↓               ↓
db_conn_wait     db_repl_lag
  ↓               ↓
P.latency        G.error_rate
```

**What an observational RCA sees:**

```
G.error_rate ↑  correlates with  P.latency ↑
Call graph: G → P (G calls P)
→ Observational RCA ranks P as root cause of G's errors
```

**What is actually happening:**

```
U (host memory pressure) causes both db_conn_wait and db_repl_lag
db_conn_wait → P.latency → G.error_rate (cascade, correctly attributed)
db_repl_lag → G.error_rate (direct path via stale reads, G's own errors)
True root cause: U (host memory pressure), not P
```

**RIFT's response:**

1. FCI detects bidirected edge: `P.latency ↔ db_conn_wait` (possible hidden confounder)
2. Intervention planner selects: `do(P.latency := 50ms)` — force P to nominal latency
3. Result: G.error_rate drops partially but not fully → P is a partial cause; something else (db_repl_lag path) persists
4. Second intervention: `do(db_repl_lag := 0ms)` → G.error_rate drops to baseline
5. Attribution: P is a causal contributor; db_repl_lag is a co-causal contributor; U is the root unobserved cause
6. Report: MULTI_CAUSE attribution with HIDDEN_CONFOUNDER_SUSPECTED note

---

### G.3 RIFT's Confounding Response Policy

| Scenario | Detection | RIFT Action |
|---|---|---|
| Observed confounder Z | Backdoor criterion satisfied | Adjust: Σ_z P(Y\|X,Z=z)P(Z=z) |
| Suspected unobserved confounder (FCI bidirected edge) | FCI outputs ↔ edge | Report CONFOUNDED; plan intervention to disambiguate |
| Intervention confirms confounder | do(X:=x) does not change Y | Remove X from candidate set; escalate search |
| Intervention inconclusive | do(X:=x) partially changes Y | Report PARTIAL_CAUSE; plan second intervention |
| Confounder unresolvable | Intervention infeasible or CONFOUNDED | Report ATTRIBUTION_UNCERTAIN; abstain |
| Collider in adjustment set | Detected by graph analysis | Flag COLLIDER_CONDITIONED; report elevated uncertainty |

**RIFT does not claim to resolve all confounding.** Its primary advantage over purely observational systems is that it can use interventions to *partially* disambiguate confounded scenarios, and it explicitly reports when ambiguity remains.

---

## Part H — Behavioral Divergence

### H.1 Basic Behavioral Divergence

Let `E_t` be the **expected behavioral state** of the system at time t:

```
E_t = { E[Vᵢₖ[t]] : ∀ sᵢ ∈ S, ∀ k ∈ MetricTypes }
```

where E[Vᵢₖ[t]] is the expected value of metric k for service sᵢ at time t under normal (non-fault) operation, estimated from a rolling baseline window of length W_baseline (default: 7 days, excluding known incident windows).

Let `O_t` be the **observed behavioral state**:

```
O_t = { Vᵢₖ[t] : ∀ sᵢ ∈ S, ∀ k ∈ MetricTypes }
```

**Basic divergence function** for a single service metric:

```
Δᵢₖ(t) = | Vᵢₖ[t] − E[Vᵢₖ[t]] |  /  σᵢₖ_baseline
```

where σᵢₖ_baseline is the rolling standard deviation of Vᵢₖ under normal operation.

Δᵢₖ(t) > θ_detect (default: 3σ) signals an anomaly at (sᵢ, k, t).

**System-level divergence:**

```
Δ_system(t) = max_{i,k} Δᵢₖ(t)
```

**Important:** Basic behavioral divergence Δ is NOT RIFT's novelty claim. It is the detection trigger. Any anomaly detection system can compute this. RIFT's contribution is the *causal indexing* of divergence defined below.

---

### H.2 Causally-Indexed Behavioral Divergence

**Motivation:** Ordinary divergence Δᵢₖ(t) > θ indicates "something changed" at service sᵢ. It does not tell us *why* — whether the change is:
- Causally induced by an upstream failure
- Independently caused at sᵢ
- An artefact of an unobserved confounder
- A measurement noise spike

**Definition — Causally-Indexed Behavioral Divergence (CID):**

Let X be a candidate root-cause variable and Y be an observed divergence at service sⱼ.

```
CID(X → Y, t) is defined as:

CID(X → Y, t) = TV( P(Y[t] | baseline), P(Y[t] | do(X := x_nominal)) )

where:
  P(Y[t] | baseline)          = distribution of Y[t] in the pre-fault baseline window
  P(Y[t] | do(X := x_nominal)) = distribution of Y[t] after intervention restoring X to nominal
  TV(P, Q)                    = Total Variation distance: (1/2) Σ_y |P(y) - Q(y)|
  x_nominal                   = baseline expected value of X: E[X] under normal operation
```

**Interpretation:** CID(X → Y, t) measures how much of Y's divergence is attributable to X's causal effect. If setting X to its nominal value (via intervention) restores Y to its baseline distribution, the divergence at Y is causally indexed to X.

**Decision threshold:**

```
CID(X → Y, t) > θ_cid    →    attribute divergence at Y to X
CID(X → Y, t) ≤ θ_cid    →    X is not causally responsible for Y's divergence
```

Default θ_cid = 0.1 (TV distance; to be calibrated on benchmark data in Phase 10).

**Properties of CID:**

1. CID is **non-negative** (TV distance ≥ 0)
2. CID = 0 when do(X := x_nominal) fully restores Y → X is the sole attributable cause
3. CID = TV(P(Y|baseline), P(Y|obs)) when do(X := x_nominal) has no effect → X is not a cause of Y's divergence
4. 0 < CID < TV_max when X is a **partial cause** of Y's divergence (multi-cause scenario)

**Mathematical precision note:** CID is computable from observable data as follows:
- P(Y[t] | baseline): estimated from the rolling baseline window using kernel density estimation or empirical CDF over observed Vⱼₖ values
- P(Y[t] | do(X := x_nominal)): estimated from post-intervention observations of Vⱼₖ during the VALID intervention window

Both distributions are observable. CID is empirically estimable. No unobserved quantities are required in its computation, given a VALID intervention.

---

### H.3 Multi-Service Causally-Indexed Divergence

For a set of candidate causes C = {X₁, X₂, …, Xₘ} and observed divergence at Y:

```
CID_set(C, Y, t) = TV( P(Y[t] | baseline), P(Y[t] | do(X₁ := x₁_nominal, X₂ := x₂_nominal, …)) )
```

Joint intervention on all candidates recovers what fraction of Y's divergence is attributable to the candidate set as a whole. Residual divergence after the joint intervention corresponds to causes outside C (unobserved confounders or uninstrumented services).

---

### H.4 Relationship to Standard Anomaly Detection

| Method | What it measures | Confound-robust? | Causal? |
|---|---|---|---|
| Threshold alerting (Prometheus) | Δᵢₖ(t) > fixed threshold | No | No |
| Isolation Forest | Statistical anomaly score | No | No |
| Basic divergence Δᵢₖ(t) | Normalized deviation from baseline | No | No |
| **CID(X → Y, t)** | TV reduction when X is restored to nominal | **Partially** (requires VALID intervention) | **Yes** |
