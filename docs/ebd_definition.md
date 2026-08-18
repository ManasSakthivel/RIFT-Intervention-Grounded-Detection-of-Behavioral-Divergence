# RIFT — Earliest Behavioral Divergence (EBD)
**Phase 2 | Version 1.0**

---

## Part I — EBD Definition

### I.1 What EBD Is Not

EBD is **not** simply "the first anomaly." Defining EBD as the first time any metric exceeds a threshold would produce a trivially noisy detector — network jitter, GC pauses, and load spikes routinely cause brief threshold exceedances that have no causal connection to any failure.

EBD is also **not** "the first service to show divergence" without qualification. In a cascade failure, symptom services downstream of the root cause will show divergence after the root cause — but they do so because of it. The first symptom is often not the root cause.

---

### I.2 Requirements for EBD

A divergence event at variable Vᵢ[t] qualifies as EBD only if **all** of the following hold:

**Requirement 1 — Observed Behavioral Deviation:**

```
Δᵢₖ(t) > θ_detect    for at least one metric k of service sᵢ
```

Δᵢₖ(t) = (Vᵢₖ[t] − E[Vᵢₖ[t]]) / σᵢₖ_baseline > 3σ (default).

The deviation must persist for at least Δt_persist ≥ 2 × Δt (two consecutive windows), ruling out transient fluctuations.

**Requirement 2 — Temporal Precedence:**

```
t_Vᵢ < t_Vⱼ    for all j such that Vⱼ also shows divergence
```

Vᵢ must exhibit divergence strictly before all other diverging variables Vⱼ in the current incident window. Ties are handled by Requirement 4.

**Requirement 3 — Causal Relevance:**

```
∃ directed path  Vᵢ → ⋯ → Vⱼ  in G_T
for at least one downstream diverging variable Vⱼ
```

Vᵢ must be ancestral to at least one downstream diverging variable in the causal graph G_T. A diverging service with no causal descendants among the other diverging services is not a root cause candidate — it may be a co-effect of a hidden cause.

**Requirement 4 — Intervention Evidence (required for definitive EBD):**

```
CID(Vᵢ → Vⱼ, t) > θ_cid
for at least one downstream Vⱼ ∈ Desc(Vᵢ, G_T) that is diverging
```

An intervention do(Vᵢ := x_nominal) must measurably reduce divergence at some downstream Vⱼ. Without this, temporal precedence + causal relevance is necessary but not sufficient — the correlation may be explained by a shared confounder.

**Requirement 5 — Downstream Outcome Effect (for severity qualification only):**

```
∃ Vⱼ ∈ Desc(Vᵢ, G_T) s.t. Vⱼ is a user-visible SLO metric and Δⱼₖ(t) > θ_detect
```

EBD at Vᵢ is classified as **impactful** only if the causal cascade reaches at least one SLO-relevant metric (e.g., checkout_latency, payment_error_rate). This requirement is used for severity ranking, not for EBD detection itself.

---

### I.3 Formal EBD Definition

```
EBD(Vᵢ, t*, incident_window W) is TRUE iff:

  R1: Δᵢₖ(t) > θ_detect  for some k,  persisting for ≥ 2Δt  starting at t = t*
  R2: t* < tⱼ  for all j ≠ i s.t. divergence(Vⱼ) in W  (temporal precedence)
  R3: ∃ j s.t. Vⱼ diverges in W  AND  Vᵢ → ⋯ → Vⱼ in G_T  (causal relevance)
  R4: CID(Vᵢ → Vⱼ, t*) > θ_cid  for some such j  (intervention evidence)
```

EBD is **definitive** when all four requirements are met.  
EBD is **candidate** (lower confidence) when R1–R3 are met but R4 has not yet been executed (intervention pending).

---

### I.4 Handling Ties in Temporal Precedence (R2)

**Case: Multiple services diverge in the same time window t**

When two or more variables {Vᵢ, Vⱼ} first exhibit divergence at the same timestep t*, temporal precedence (R2) cannot resolve them.

Resolution procedure:

1. **Sub-window analysis:** Narrow to sub-windows of Δt/2. If one diverges first at the finer granularity, apply R2 at the finer scale.
2. **Causal graph analysis:** If Vᵢ → Vⱼ in G_T (Vᵢ is an ancestor of Vⱼ), attribute EBD to Vᵢ regardless of tie — the causal structure resolves the temporal ambiguity.
3. **Intervention disambiguation:** Execute do(Vᵢ := x_nominal) and do(Vⱼ := x_nominal) independently. The intervention that more completely restores the full set of downstream diverging variables to baseline identifies the EBD.
4. **Unresolvable tie:** If neither intervention resolves the downstream divergences fully, report **MULTIPLE_EBD = {Vᵢ, Vⱼ}** — a co-causal or hidden-confounder scenario.

---

### I.5 Handling Multiple Causes

**Scenario:** Services A, B, and C all show divergence. Interventions show:
- do(A := nominal) restores 60% of downstream divergence
- do(B := nominal) restores 40% of downstream divergence
- do(A := nominal) ∧ do(B := nominal) restores 100%

**Result:** RIFT reports:

```
EBD_set = { A, B }
CID(A → downstream) = 0.6
CID(B → downstream) = 0.4
Attribution: MULTI_CAUSE
Joint_CID = 1.0  (full attribution achieved by joint intervention)
```

Neither A nor B alone is the EBD. The EBD is the set {A, B} as joint causes.

**Key property:** RIFT uses **joint interventional attribution** for multi-cause scenarios, not additive decomposition (which can double-count shared causal paths).

---

### I.6 EBD vs. Root Cause

EBD is the earliest identifiable causal divergence point **within RIFT's observability boundary**.

The **true root cause** may be:
1. Equal to EBD: if the EBD variable has no instrumented ancestors and its divergence is confirmed by intervention
2. Upstream of EBD: if the EBD variable has a non-instrumented upstream cause (in L(t)) — RIFT reports EBD as the **earliest instrumentable ancestor** of the failure, not necessarily the ultimate root cause
3. An unobserved confounder: if FCI detects a bidirected edge and no intervention fully resolves the downstream divergences

**RIFT must always report whether the EBD is an instrumentation boundary (boundary_limited = TRUE) or a fully confirmed root cause (boundary_limited = FALSE).** This is a mandatory output field.

---

### I.7 EBD Output Schema

```
EBDResult {
  incident_id:        UUID
  ebd_variables:      list of VariableID  (singleton or set for multi-cause)
  t_ebd:              timestamp of first divergence
  confidence:         DEFINITIVE | CANDIDATE | UNCERTAIN
  cid_scores:         { var_id → CID score }
  boundary_limited:   bool  (true if uninstrumented upstream services exist)
  multi_cause:        bool
  unresolved_confounders: list of suspected hidden confounders (FCI bidirected edges)
  interventions_used: list of InterventionRecord.id
  causal_path:        [ EBD → mediators → downstream SLO metrics ]
  limitations:        list of active assumption warnings (A1-A8)
}
```
