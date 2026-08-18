# RIFT — Closed-Loop Model and Online Operation
**Phase 2 | Version 1.0**

---

## Part M — Closed-Loop Model Update

### M.1 Why Closed-Loop Is RIFT's Core Contribution (N5)

Existing systems either:
- Build a causal model offline (Sage: static BN, no live update)
- Inject faults without a causal model (Sieve: adaptive injection, no SCM update)

RIFT's architectural contribution is the **closed feedback loop**: each intervention outcome updates the causal model, which in turn guides the next intervention selection. This is not achievable by naively composing Sage + LitmusChaos because:

1. Sage's BN is trained on historical fault-labeled data and cannot be updated from live intervention outcomes without retraining
2. LitmusChaos provides no feedback channel to a causal model
3. The joint decision of *which intervention to run next* requires a live causal model that incorporates prior intervention outcomes — this integration is the architectural novelty

---

### M.2 What "Update" Means — Precisely

RIFT updates **four distinct components** of the causal model. These are tracked separately and must not be conflated.

**Component 1 — Edge Confidence Scores (updated most frequently)**

```
G_T has edges Eᵢⱼ ∈ {0,1} with associated confidence scores conf(Eᵢⱼ) ∈ [0,1]
```

After observing intervention I = do(X := x_nominal) with outcome Y:

```
If CID(X → Y) > θ_cid:
  conf(E_{X→Y}) ← conf(E_{X→Y}) × (1 + α_confirm)   ← strengthen edge
  conf(E_{Z→Y}) ← conf(E_{Z→Y}) × (1 − α_weaken)     ← weaken competing edges to Y (if applicable)

If CID(X → Y) ≤ θ_cid:
  conf(E_{X→Y}) ← conf(E_{X→Y}) × (1 − α_weaken)     ← weaken edge
```

α_confirm = 0.2, α_weaken = 0.1 (hyperparameters, tuned in Phase 9).  
Edge confidence clipped to [ε_min, 1−ε_min] to prevent absorbing states.

**Component 2 — Candidate Root Cause Posterior (updated after every intervention)**

```
Prior over candidates: P(C = Xᵢ) ∝ anomaly_score(Xᵢ) × conf(path Xᵢ → Y in G_T)

After intervention do(Xᵢ := x_nominal) with observed CID score cᵢ:
  P(C = Xᵢ | cᵢ) ∝ P(C = Xᵢ) × P(cᵢ | C = Xᵢ)
```

Likelihood model P(cᵢ | C = Xᵢ):
- If C = Xᵢ (Xᵢ is the true cause): CID should be high → P(cᵢ | C = Xᵢ) ∝ Beta(cᵢ; a_pos, b_pos) with a_pos > b_pos
- If C ≠ Xᵢ: CID should be low → P(cᵢ | C ≠ Xᵢ) ∝ Beta(cᵢ; a_neg, b_neg) with a_neg < b_neg

Parameters (a_pos, b_pos, a_neg, b_neg) are calibrated from benchmark data (Phase 9).

**Component 3 — Graph Structure (updated least frequently; requires evidence threshold)**

Graph structure (the presence/absence of edges) is updated only when:
- Intervention evidence contradicts the current graph structure with high confidence
- Specifically: if do(X := x) causes Y to change, but there is no path X → ⋯ → Y in G_T, a new edge or path must be added

```
If CID(X → Y) > θ_cid  AND  there is no directed path X → ⋯ → Y in G_T:
  → Add edge X → Y to G_T with conf = 0.5 (moderate initial confidence)
  → Flag as INTERVENTION_INFERRED edge (distinct from observationally-learned edges)

If CID(X → Y) ≤ θ_cid  AND  edge X → Y ∈ G_T with conf < 0.3:
  → Remove edge from G_T
  → Flag as INTERVENTION_REFUTED
```

Graph structure updates trigger a re-check of all pending identifiability queries that depend on the modified subgraph.

**Component 4 — Causal Parameters (updated when parameter estimation is feasible)**

Structural equation parameters (e.g., the coefficient α in `latency_s₂ = α·latency_s₁ + …`) are updated from intervention data using regression:

```
After do(latency_s₁ := x):
  Observe latency_s₂ across multiple values of x
  Update α estimate via OLS or Bayesian regression
```

Parameter updates are deferred to the post-incident analysis phase unless the current α estimate causes attribution errors (large residual between predicted and observed CID).

---

### M.3 The Closed-Loop State Machine

```
State: ( G_T, conf_edges, P_candidates, params, history )

┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  OBSERVE:  Collect O(t) from telemetry pipeline             │
│     ↓                                                       │
│  DETECT:   Compute Δᵢₖ(t); trigger if Δ > θ_detect         │
│     ↓                                                       │
│  MODEL:    Run FCI on recent windows → update G_T           │
│            Compute P_candidates from anomaly scores + G_T   │
│     ↓                                                       │
│  CHECK_ID: For each candidate X, run identifiability check  │
│            Identifiable → estimate from observational data  │
│            Not identifiable → add to intervention queue     │
│     ↓                                                       │
│  SELECT:   Compute Utility(I) for each queued intervention  │
│            Select I* = argmax Utility subject to safety     │
│     ↓                                                       │
│  EXECUTE:  Run intervention I*; record InterventionRecord   │
│     ↓                                                       │
│  OBSERVE:  Collect post-intervention O(t) for Δ_int         │
│     ↓                                                       │
│  UPDATE:   Update conf_edges, P_candidates, params, G_T     │
│     ↓                                                       │
│  ATTRIBUTE: If confidence threshold reached → output EBD    │
│             If budget exhausted → output best-effort result │
│             If stopping condition met → terminate loop      │
│     ↓                                                       │
│  Loop back to SELECT if attribution not yet definitive      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Part N — Online Operation

### N.1 Latency Constraints

| Step | Target Latency | Hard Limit |
|---|---|---|
| OBSERVE (telemetry collection) | ≤ 5s pipeline lag | ≤ 10s |
| DETECT (anomaly scoring) | ≤ 1s | ≤ 3s |
| MODEL (FCI / graph update) | ≤ 10s | ≤ 30s |
| CHECK_ID (identifiability) | ≤ 2s | ≤ 5s |
| SELECT (intervention planner) | ≤ 1s | ≤ 5s |
| EXECUTE (intervention injection) | ≤ 5s setup | — |
| OBSERVE post-intervention | ≥ 3 × p99_lat | ≤ Δ_int_max |
| UPDATE (model update) | ≤ 5s | ≤ 10s |
| ATTRIBUTE (output EBD result) | ≤ 2s | ≤ 5s |

**Total target latency from anomaly detection to first attribution output:**  
< 120s (2 minutes) for incidents requiring a single intervention.  
< 300s (5 minutes) for incidents requiring up to 3 interventions.

---

### N.2 Safety Constraints (Runtime)

The following safety constraints are hard limits enforced by the safety module:

```
BR(I) < BR_max_global = 0.30            ← blast radius limit
SLAI(I) < SLAI_max_global = 0.05        ← max SLA degradation
cumulative ED ≤ T_budget = 600s         ← total intervention time budget per incident
RC(I) = 0 required for auto-execution   ← data-state interventions require manual auth
SC(target) ≠ CRITICAL unless elevated   ← critical services require operator approval
```

---

### N.3 Intervention Budget

```
Budget_per_incident = T_budget = 600s (default, configurable)
Max_interventions_per_incident = 5 (default, configurable)
Interventions_remaining = Max_interventions − len(history)
Budget_remaining = T_budget − Σ ED(executed interventions)
```

If budget is exhausted before DEFINITIVE attribution:
- Output CANDIDATE_EBD with top-1 candidate by posterior probability
- Attach confidence interval and budget_exhausted flag

---

### N.4 Stopping Conditions

RIFT stops the attribution loop when ANY of the following:

1. **Confidence threshold met:** `max P(C = Xᵢ) > θ_confidence` (default: 0.80) → output DEFINITIVE
2. **Budget exhausted:** `Budget_remaining ≤ 0` → output CANDIDATE with confidence
3. **Intervention queue empty:** All safe interventions have been executed → output best-effort
4. **Attribution infeasible:** All candidates marked CONFOUNDED or UNCERTAIN → output ATTRIBUTION_UNCERTAIN with explanation
5. **Kill switch activated:** Safety module forces termination → output ABORTED

---

### N.5 Confidence Threshold

```
θ_confidence = 0.80 (default)
```

Interpretation: RIFT attributes the failure to Xᵢ when the posterior probability P(C = Xᵢ | all intervention observations) > 0.80.

For multi-cause scenarios: attribution is output when the joint posterior of the top-k candidates exceeds 0.80 AND their joint CID covers ≥ 90% of observed divergence.

---

### N.6 Abstention Condition

RIFT **abstains** (outputs ATTRIBUTION_UNCERTAIN) when:

1. All candidates show CID ≤ θ_cid after their respective interventions (root cause outside instrumentation boundary)
2. FCI detects a bidirected edge between all candidate pairs (unresolvable hidden confounders)
3. All interventions during the incident were marked CONFOUNDED or INVALID
4. No variable satisfies R3 (causal relevance) — no connected causal path to downstream divergence

**Abstention is a valid, honest output.** RIFT must not fabricate attribution when the evidence is insufficient.
