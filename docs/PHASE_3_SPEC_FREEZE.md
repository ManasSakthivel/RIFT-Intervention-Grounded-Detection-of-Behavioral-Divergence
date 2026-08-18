# RIFT — Phase 3 Specification Freeze
**Phase 3 | Implementation Authority Document**
**Version 1.0 — Frozen before any Phase 3 code is written**

> **Purpose:** This document is the single authoritative reference for every implementation decision in Phase 3. Any Phase 3 component that deviates from this specification without a written amendment signed here is in violation of the RIFT research protocol. Sub-agents and implementation modules must read this document before writing any code. Discrepancies between this document and Phase 0–2.5 source documents are resolved here, with justification.

---

## FREEZE STATEMENT

All Phase 0, 1, 2, and 2.5 documents have been read in full. The decisions below reflect the authoritative, reconciled specification. No implementation detail may be changed after this freeze without creating a SPEC_AMENDMENT entry at the bottom of this file with:
- Amendment ID
- Affected component
- Original decision
- New decision
- Justification
- Reviewer sign-off

---

## 1. SCM Definition

**Authority:** `docs/formal_model.md` Part B, corrected by `docs/formal_review.md` R1.1, R4.1

### Frozen definition:

```
SCM M = ⟨ U, V, F, P(U) ⟩

V = finite set of observable endogenous variables (V ≡ O(t) variables)
U = unobserved exogenous noise + unobserved common causes (latent variables)
F = {fᵢ : PA(Vᵢ) × Uᵢ → Vᵢ}  — structural equations
P(U) = joint distribution over exogenous noise
```

**Structural equations are NOT assumed linear.** OLS is a configurable fast approximation only; the default parameter estimator is **kernel regression** (or GP regression for small samples). The paper must state the approximate local linearity assumption when OLS is used.

**V notation:** V is explicitly the set of **observable endogenous variables** = O(t). Latent variables are absorbed into U.

**Queueing dynamics — explicitly frozen:**

For any service sᵢ with a request queue, the structural equations must explicitly model:

```
queue_depth_sᵢ[t] = f_queue(arrival_rate[t], service_rate[t], queue_depth[t-1], U_queue)

latency_sᵢ[t] = f_lat(queue_depth_sᵢ[t], cpu_pct_sᵢ[t], upstream_lat[t], U_lat)
```

Where the queue is an M/M/1 approximation:
```
E[queue_depth] = ρ / (1 − ρ)   where ρ = arrival_rate / service_rate
E[latency]     = 1 / (service_rate − arrival_rate)
```

This is an approximation. The paper must state the M/M/1 assumption and note violations for bursty traffic.

---

## 2. Time-Sliced Graph

**Authority:** `docs/formal_model.md` Part C, `docs/causal_assumptions.md` A4

### Frozen definition:

- All feedback loops are represented as **temporal edges**: X[t] → Y[t+1], never X[t] → Y[t] if that would create a cycle.
- Window size Δt = **10 seconds** (default). Configurable. Validated at startup against observed trace latencies.
- Constraint: Δt ≥ 2 × p99_inter_service_latency AND Δt ≤ min_anomaly_duration.
- Δt_min = 1s (bounded below by observability stack scrape resolution).
- Variables are time-indexed: Vᵢ[t] is distinct from Vᵢ[t+1].
- Temporal alignment: Variables with collection-time lag > Δt/2 are assigned to window t+1.
- Acyclicity is **GUARANTEED BY CONSTRUCTION** in the time-sliced representation.

---

## 3. FCI → PAG

**Authority:** `docs/causal_assumptions.md` A3, `docs/formal_review.md` R1.2, R5.2

### Frozen decisions:

- **Algorithm: FCI** (Fast Causal Inference). NOT PC. PC cannot handle hidden confounders.
- **Output: PAG** (Partial Ancestral Graph) — a Markov equivalence class of MAGs.
- **Constraint: anomaly-subgraph FCI only.** Full-graph FCI is forbidden online.
- **k ≤ 15 services** in the anomaly subgraph for online FCI. Runtime O(k^d) where d = max degree.
- If the subgraph exceeds k = 15: apply documented fallback (anomaly ranking only; no FCI; report SUBGRAPH_TOO_LARGE).
- PAG edges encode: directed (→), bidirected (↔), partially directed (o→), undirected (o-o).
- Bidirected edge Vᵢ ↔ Vⱼ signals possible hidden confounder between Vᵢ and Vⱼ.
- FCI must use a deterministic conditional independence test. Default: **Fisher's Z-test** with significance level α_CI = 0.05. Alternative for small samples: **permutation-based CI test**.
- FCI must produce a deterministic PAG given a fixed seed for all stochastic procedures.

---

## 4. Identifiability Policy

**Authority:** `docs/formal_review.md` R1.2, `docs/hypotheses.md` L5

### Frozen policy:

**MAG-ID is scoped.** Full general MAG-ID is deferred. Phase 3 implements:
1. Backdoor identification (primary)
2. Front-door identification (secondary, where applicable)

Return values:
- `IDENTIFIABLE` — backdoor or front-door criterion confirmed; proceed with estimation.
- `CONDITIONALLY_IDENTIFIABLE` — identifiability depends on which MAG is true; intervention needed to disambiguate.
- `NOT_IDENTIFIABLE` — no observed adjustment set satisfies any criterion; RIFT **ABSTAINS**.

**When NOT_IDENTIFIABLE:** RIFT returns `NON_IDENTIFIABLE` attribution status. No causal claim is made. The service remains a CANDIDATE based on anomaly score only.

**When bidirected edge blocks backdoor path:** Falls back to front-door → then instrumental variable → then REQUIRES_INTERVENTION → then NOT_IDENTIFIABLE.

---

## 5. Intervention Semantics

**Authority:** `docs/intervention_semantics.md`, `docs/formal_review.md` R2.3, `docs/causal_assumptions.md` A5

### Frozen definition:

```
do(X := x):
  1. Remove all incoming edges to X in G → mutilated graph G_{do(X:=x)}
  2. Replace structural equation fₓ ∈ F with constant equation X := x
  3. All other fⱼ ∈ F (j ≠ X) remain unchanged
  4. Evaluate P(Y | do(X := x)) = E_U[ Y under M_{do(X:=x)} ]
```

**Five-check validity protocol (all must pass for VALID intervention):**
1. **Precision check:** |x_achieved − x_requested| / x_requested < 0.20
2. **Clean window check:** No anomalies in non-descendants of X during intervention; K8s events: ±60s window; Network events: ±30s window.
3. **Concurrent event check:** No K8s events, deployments, or other injections within ±60s.
4. **Recovery check:** System returns to pre-baseline for X within 120s after rollback.
5. **Isolation check:** Non-target services show no statistically significant metric changes during intervention.

Intervention fails all five: marked INVALID, result discarded.
Intervention fails 1–4 of five: marked CONFOUNDED, result discarded.

**InterventionRecord schema (frozen):**
```
target_service, target_variable, nominal_value, intervention_value,
t_start, t_end, pre_state_snapshot, post_state_snapshot,
precision_achieved, precision_check_pass,
clean_window_pass, concurrent_event_pass, recovery_pass, isolation_pass,
validity_status,  # VALID | CONFOUNDED | INVALID
rollback_status,  # SUCCESS | PARTIAL | FAILED
safety_authorization,  # AUTONOMOUS | SUPERVISED | DENIED
affected_destinations,  # list of (service, ip)
n_samples_collected,  # actual post-intervention sample count
cid_result_ref        # FK to CIDResult
```

---

## 6. CID Definition

**Authority:** `docs/behavioral_divergence.md` H.2, `docs/formal_review.md` R1.3, Phase 3 spec (Wasserstein upgrade)

### Frozen definition:

```
CID(X → Y, t) = W₁( P(Y | baseline), P(Y | do(X := x_nominal)) )
```

where W₁ is the **first Wasserstein distance** (Earth Mover's Distance), computed empirically from samples using the 1D sorted-arrays formula.

**Wasserstein is primary.** TV distance is retained as a secondary diagnostic only. The reason: TV is inappropriate for bimodal latency distributions (Phase 2.5 adversarial finding). Wasserstein correctly handles multi-modal and heavy-tailed distributions.

**KDE is not used for W₁.** W₁ can be computed exactly from sorted empirical samples:
```
W₁(P, Q) = (1/n) Σᵢ |sort(P)[i] − sort(Q)[i]|   (equal-size samples)
```
For unequal sample sizes, use linear interpolation or the scipy.stats.wasserstein_distance implementation.

**θ_cid threshold:** The threshold for CID attribution must be calibrated against the baseline distribution's interquartile range (IQR-normalized Wasserstein). Default θ_cid_W = 0.1 × IQR_baseline. This replaces the TV-based θ_cid = 0.1 for Wasserstein.

**TV is retained as:** `CID_TV_diagnostic` — a secondary diagnostic field in CIDResult. It is never used as the primary attribution criterion.

---

## 7. Sample Thresholds — Frozen

**Authority:** `docs/risk_closure/sample_requirements.md` Section 6.2

```
n_min        = 20    Hard floor. No CID output of any kind below this value.
n_candidate  = 30    CANDIDATE CID. Directional claim. Wide CI.
n_reliable   = 50    DEFINITIVE CID. Reliable effect-size estimation.
```

**Δ_int formula (robust, bursty-corrected):**
```
Δ_int = max( 3 × p99_lat,  ceil(n_reliable + 2√n_reliable) / rps_baseline )
      = max( 3 × p99_lat,  64 / rps_baseline )   ← DEFINITIVE target

Fallback to CANDIDATE if Δ_int_definitive > T_budget / 4:
Δ_int = max( 3 × p99_lat,  ceil(n_candidate + 2√n_candidate) / rps_baseline )
      = max( 3 × p99_lat,  41 / rps_baseline )   ← CANDIDATE target

Abstain entirely if Δ_int_candidate > T_budget / 2 (>300s by default)
```

---

## 8. Distributional Significance Test — Frozen

**Authority:** Phase 3 spec (permutation test as primary), Phase 2.5 adversarial review

**Primary significance test:** **Permutation test** (label-permutation test on paired {baseline, post-intervention} sample sets). B = 10,000 permutations.

**Bootstrap CI:** Retained only for effect-size confidence intervals (CI on W₁ point estimate). NOT used as primary significance test. NOT used as Type I error control.

**Justification:** Bootstrap CI on TV distance is statistically invalid for CID significance testing (Phase 2.5 adversarial finding). Permutation test is distribution-free and valid for any divergence measure.

**Significance threshold:** α = 0.05 for CID attribution claim.

---

## 9. EBD Definition — Frozen

**Authority:** `docs/ebd_definition.md` I.2, I.3, corrected by `docs/formal_review.md` R3.1, R4.4

### EBD requirements:

```
EBD(Vᵢ, t*, W) is TRUE iff:

R1: Δᵢₖ(t) > θ_detect for some k, persisting ≥ 2Δt starting at t = t*
    Δᵢₖ(t) = (Vᵢₖ[t] − E[Vᵢₖ[t]]) / σᵢₖ_baseline > 3σ (default)

R2: t* < tⱼ for all j ≠ i s.t. divergence(Vⱼ) in W (temporal precedence)
    Ties resolved by: R3 (causal ancestry) first, then R4 (intervention)
    Sub-window tie-breaking available via trace span timestamps (~1ms resolution)

R3: ∃ j s.t. Vⱼ diverges in W AND Vᵢ →⋯→ Vⱼ in G_T (causal relevance)

R4: CID(Vᵢ → Vⱼ, t*) > θ_cid for some Vⱼ ∈ Desc(Vᵢ, G_T) (intervention evidence)
```

**Two confidence levels:**
- `CANDIDATE EBD`: R1–R3 met; R4 pending. Output within ~30s.
- `DEFINITIVE EBD`: R1–R4 met. Output within ~120–300s.

**EBDResult schema (frozen):**
```
service_id, variable_id, t_star, confidence,  # CANDIDATE | DEFINITIVE
r1_pass, r2_pass, r3_pass, r4_pass,
cid_scores,  # { var_id → (W1_estimate, CI_lower, CI_upper, n_samples, grade) }
boundary_limited,  # TRUE if root cause may be outside instrumentation boundary
assumption_warnings,  # list of violated/uncertain assumptions
identifiability_state,  # IDENTIFIABLE | CONDITIONALLY_IDENTIFIABLE | NOT_IDENTIFIABLE
intervention_record_ref,  # FK to InterventionRecord
causal_path,  # list of edges in G_T from EBD to diverging descendants
```

---

## 10. Adaptive Anomaly Subgraph — Strategy D — Frozen

**Authority:** Phase 2.5 validation (gate PASSED), `docs/formal_review.md` R5.2

### Construction algorithm (Strategy D):

```
STEP 1 — Seed:
  seed = {sᵢ ∈ S : Δᵢₖ(t) > θ_detect for some k}  (all anomalous services)

STEP 2 — 1-hop ancestor closure:
  for each sᵢ in seed:
    add all direct parents of sᵢ in G_T (1-hop ancestors)

STEP 3 — Dynamic bidirected edge expansion:
  for each bidirected edge sᵢ ↔ sⱼ in G_T (potential hidden confounder):
    if sᵢ ∈ subgraph OR sⱼ ∈ subgraph:
      add both sᵢ and sⱼ to subgraph

STEP 4 — k ≤ 15 enforcement:
  if |subgraph| > 15:
    prune by anomaly score (keep top-15 by max_k Δᵢₖ)
    set boundary_limited = TRUE for all pruned services
    report SUBGRAPH_PRUNED with count

STEP 5 — Output:
  return (subgraph, boundary_limited, pruned_services)
```

**Previously validated synthetic cases (must reproduce):**
- Case A: Root cause inside → false attribution = 0.00 ✓
- Case B: 1 hop outside → boundary_limited=TRUE ✓
- Case C: multiple hops outside → boundary_limited=TRUE ✓
- Case D: root cause not anomalous → expansion captures via ancestor closure ✓
- Case E: multiple causal paths → all paths captured ✓
- Case F: hidden confounder → bidirected expansion captures ✓

---

## 11. tc u32 + Per-Destination netem — Frozen

**Authority:** `docs/formal_review.md` R2.3, Phase 2.5 network PoC analysis

### Network intervention mechanism:

```
Implementation: tc u32 classifier + per-destination netem (NOT global eth0 netem)
Platform requirement: CAP_NET_ADMIN capability
Container topology: container-per-service (one Linux network namespace per service)
Overlay network: per-destination approach handles VXLAN/Cilium overlays via destination IP filter

tc filter add dev eth0 parent 1: protocol ip u32 \
    match ip dst <target_service_ip>/32 \
    flowid 1:10

tc qdisc add dev eth0 parent 1:10 handle 10: netem \
    delay <latency_ms>ms <jitter_ms>ms distribution normal
```

**Rollback mechanism:**
```
tc qdisc del dev eth0 parent 1:10 handle 10:
tc filter del dev eth0 parent 1: protocol ip u32 ...
```

**Side-effect monitor:** During each intervention, monitor all non-target service metrics. If any non-target service shows Δᵢₖ > 2σ, mark intervention CONFOUNDED.

**eBPF is NOT required** for the Phase 3 implementation. tc u32 is sufficient for the container-per-service topology and is scientifically valid.

---

## 12. Intervention Cost Model — Frozen

**Authority:** `docs/intervention_cost_model.md` K.1–K.4, corrected by `docs/formal_review.md` R4.2, R4.3

### Frozen cost factors:

```
BR(I)   = |Desc(X, G_T) ∩ S| / |S|            Blast Radius ∈ [0,1]
SLAI(I) = Σ_k w_k · P(SLO_k violated | do(X:=x))  SLA Impact ∈ [0,1]
ED(I)   = Δ_int_required + Δ_recovery_expected  Execution Duration (seconds)
RC(I)   = P(rollback_success < 1.0) × rollback_complexity  Rollback Cost ∈ [0,1]
EIG(I)  = H(C | obs_so_far) − E[H(C | obs_so_far ∪ {I})]  Info Gain (nats; normalized)
SC(I)   = safety_constraint_score ∈ [0,1]       Safety Compliance
```

**Utility function (frozen, dimensionless):**
```
Utility(I) = EIG_normalized(I) / (1 + Cost_composite(I))

EIG_normalized(I) = EIG(I) / H_max  where H_max = log(|C|)
Cost_composite(I) = w_BR·BR(I) + w_SLAI·SLAI(I) + w_RC·RC(I) + w_SC·(1−SC(I))
                    where weights sum to 1.0 (default equal weights)
```

**MSIS objective (frozen):**
```
MSIS = argmin_{IS} Σ_{I∈IS} Cost_composite(I)
subject to: H(C | observations from IS) < θ_entropy
            AND all safety constraints satisfied
```

**Greedy approximation:** At each step, select I* = argmax Utility(I). Valid as approximate optimizer for the MSIS objective.

**Submodularity:** The EIG term is submodular under the assumption of conditionally independent intervention outcomes (given C). This assumption must be **verified** in the implementation, not claimed. If violated, the (1−1/e) guarantee does not hold and must not be claimed.

---

## 13. Closed-Loop Update — Frozen

**Authority:** `docs/closed_loop_model.md` M.2

### Four update components (frozen):

**Component 1 — Edge Confidence (updated after every intervention):**
```
α_confirm = 0.2,  α_weaken = 0.1
conf(E) clipped to [ε_min=0.05, 1−ε_min=0.95]
```

**Component 2 — Candidate Posterior (Bayesian update):**
```
Likelihood: P(cᵢ | C=Xᵢ) ~ Beta(a_pos=3, b_pos=1)   # true cause produces high CID
             P(cᵢ | C≠Xᵢ) ~ Beta(a_neg=1, b_neg=3)   # non-cause produces low CID
Parameters calibrated from Phase 9 benchmark data. Values above are initialization defaults.
```

**Component 3 — Graph Structure (threshold-gated):**
```
Add edge:    CID > θ_cid AND no path X→⋯→Y in G_T
Remove edge: CID ≤ θ_cid AND conf(E_{X→Y}) < 0.3
Trigger: re-check all pending identifiability queries
```

**Component 4 — Causal Parameters:**
Default: kernel regression. OLS: configurable fast approximation only.

### State machine (frozen):
```
OBSERVE → DISCOVER → IDENTIFY → SELECT → INTERVENE → VERIFY → UPDATE → STOP/NEXT
```

**Stopping conditions:**
1. Posterior entropy H(C) < θ_stop (default 0.5 nats)
2. Budget exhausted: cumulative ED > T_budget = 600s
3. All candidates return NOT_IDENTIFIABLE or INSUFFICIENT_SAMPLES
4. Safety ABORT triggered

---

## 14. Safety Rules — Frozen

**Authority:** `docs/intervention_semantics.md` E, `docs/safety_model.md`, Phase 3 spec

### Hard stops (all cause SAFE_ABORT):

1. Production namespace detected (namespace ≠ rift-eval-*)
2. Unauthorized target (target not in approved_targets registry)
3. Cumulative ED > T_budget (default 600s)
4. Rollback failure (rollback_status = FAILED after 2 retries)
5. Unexpected blast radius: non-descendants show significant metric change
6. Data mutation attempt (write operation detected on production data store)
7. Error rate > 50% system-wide for > 30s (cascade failure detection)
8. Kill-switch activated (external signal or manual override)

### Authorization levels:
- `AUTONOMOUS`: allowed for low-cost, low-blast-radius interventions (BR < 0.1, SLAI < 0.01)
- `SUPERVISED`: requires human confirmation (BR ≥ 0.1 OR SLAI ≥ 0.01 OR ED > 60s)
- `DENIED`: never executed (targets outside approved set, production detection)

---

## 15. Statistical Correction Plan — Frozen

**Authority:** `docs/risk_closure/statistical_plan.md`, Phase 2.5 adversarial review

| Hypothesis | Test | Direction | α |
|---|---|---|---|
| H1 | Wilcoxon signed-rank | one-sided (RIFT > baseline) | 0.05 |
| H2 | Wilcoxon signed-rank | one-sided | 0.05 |
| H3 | Wilcoxon signed-rank | one-sided | 0.05 |
| H4 | TOST equivalence (accuracy) + one-sided Wilcoxon (cost) | — | 0.05 |
| H5 | one-sided binomial test | — | 0.05 |

**Multiple testing:** Holm-Bonferroni for 6 confirmatory tests.
**Exploratory comparisons:** BH FDR.
**Effect size:** Cliff's δ (always reported regardless of p-value).
**C_confounded sample requirement:** ≥ 48 incidents for 80% power. If fewer collected, report achieved power only; do not claim 80%.
**Clustering:** Incidents are NOT i.i.d. (clustered within systems). Paired signed-rank test respects this by treating per-incident differences as the unit.

---

## 16. Baseline Definitions — Frozen

**Authority:** `docs/baseline_specification.md`, `docs/risk_closure/baseline_fairness.md`

| ID | Baseline | Status |
|---|---|---|
| B1 | Prometheus threshold rules | ACTIVE Phase 3 |
| B2 | Isolation Forest | ACTIVE Phase 3 |
| B3 | MicroRCA-style (call graph + PageRank) | ACTIVE Phase 3 |
| B4 | Sieve-like (adaptive injection, no SCM) | ACTIVE Phase 3 |
| B5 | RIFT-OBS (RIFT without intervention, shared G_T) | ACTIVE Phase 3 |
| B6 | Statistical debugging (Ochiai-adapted) | ACTIVE Phase 3 |
| B7 | Sage + Chaos composition | DEFERRED to Phase 8 |
| B8 | Oracle upper bound | REFERENCE row only |

**Critical fairness rule:** B5 (RIFT-OBS) MUST use a single serialized G_T artifact shared with RIFT-FULL. No information advantage.

**Sage+Chaos (B7) temporal split:** Training set = separate time period. RIFT evaluation set has no access to B7 training labels.

---

## 17. Known Limitations — Frozen (must appear in paper)

| ID | Limitation | Scope |
|---|---|---|
| L1 | Unobserved confounding (FCI bidirected → abstain) | Documented; not solved |
| L2 | Invalid intervention (precision/isolation failure) | Retry policy; abstain if all fail |
| L3 | Non-replayable system state | NON_REPRODUCIBLE output |
| L4 | Insufficient observability (boundary_limited) | boundary_limited=TRUE |
| L5 | Non-identifiable query | ABSTAIN |
| L6 | Simultaneous causal events | SIMULTANEOUS_FAULTS output |
| L7 | External dependencies | boundary_limited=TRUE |
| L8 | Graph staleness | BOCPD + STALE_MODEL |
| L9 | Online Boutique is not enterprise-scale | Stated in all evaluation sections |
| L10 | Sub-millisecond systems out of scope | Δt_min = 1s |
| L11 | Silent logic errors out of scope | Performance/availability faults only |

---

## 18. Causal Claim Language — Frozen

**FORBIDDEN phrases in any artifact or code comment:**
- "causally accurate"
- "correct causal graph"
- "solves confounding"
- "production-ready"
- "enterprise-scale"
- "real-world proven"
- "guarantees causal attribution"

**REQUIRED phrases:**
- "intervention-consistent" (not "causally accurate")
- "validated on synthetic ground-truth scenarios"
- "evaluated on Online Boutique" (not "validated for distributed systems generally")
- "RIFT abstains when..." (not "RIFT cannot handle...")

---

## DISCREPANCY LOG

### D1 — TV vs. Wasserstein for CID

**Documents in conflict:**
- `docs/behavioral_divergence.md` H.2: defines CID using TV distance
- `docs/formal_review.md` R1.3: approves continuous TV with KDE/Silverman
- `docs/risk_closure/sample_requirements.md`: all analysis uses TV
- Phase 3 spec (this project): requires Wasserstein as primary (bimodal issue)

**Resolution:** Wasserstein is adopted as the primary CID metric for Phase 3 implementation. TV is retained as a secondary diagnostic. All existing Phase 2 documents are superseded on this point. The rationale (bimodal latency distributions) is documented in the Phase 2.5 adversarial review. The n_min/n_candidate/n_reliable thresholds remain numerically valid as W₁ shares similar asymptotic sample-size behavior to TV for the relevant scenarios.

**Amendment ID:** SPEC-AMEND-001

---

### D2 — Bootstrap CI vs. Permutation Test

**Documents in conflict:**
- `docs/risk_closure/sample_requirements.md`: uses bootstrap CI throughout
- Phase 3 spec: requires permutation test as primary significance test

**Resolution:** Permutation test is primary for significance (p-value). Bootstrap CI is retained for effect-size confidence intervals only (CI on W₁ point estimate). This is the correct statistical separation: permutation test for null hypothesis testing, bootstrap for uncertainty quantification of the effect size.

**Amendment ID:** SPEC-AMEND-002

---

### D3 — n_min = 20 vs. n_min = 30

**Documents in conflict:**
- `docs/risk_closure/sample_requirements.md` Section 6.2: n_min = 20 (hard floor), n_candidate = 30
- Phase 3 spec table: "20 ≤ n < 30: CANDIDATE"

**Resolution:** Three-tier policy from sample_requirements.md Section 6.2 is authoritative:
- n < 20: INSUFFICIENT (no CID output)
- 20 ≤ n < 30: CANDIDATE (wide CI warning; marginal)  
- 30 ≤ n < 50: CANDIDATE/LOW_CONFIDENCE → mapped to existing CANDIDATE grade with warning
- n ≥ 50: RELIABLE → DEFINITIVE

The Phase 3 spec table collapses 20–30 and 30–50 into two CANDIDATE sub-tiers. Implementation uses these four bands.

**Amendment ID:** SPEC-AMEND-003

---

## SPEC FREEZE ATTESTATION

This document was created by reviewing all Phase 0, 1, 2, and 2.5 source documents in sequence before any Phase 3 implementation code was written. All discrepancies have been identified and resolved above. Implementation modules must cite the section of this document that authorizes their design choices.

**Frozen: Phase 3 implementation may begin.**
