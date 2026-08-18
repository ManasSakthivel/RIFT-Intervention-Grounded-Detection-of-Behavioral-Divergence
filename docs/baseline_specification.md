# RIFT — Baseline Specification
**Phase 2 | Version 1.0**

---

## Part P — Baseline Specification

All baselines receive exactly the same input data as RIFT. No baseline receives less information than RIFT's observational component, and no baseline receives intervention results unless it is designed to use them. This prevents unfair comparisons in both directions.

---

### Baseline Information Protocol

**Common inputs (all baselines receive):**
- Identical trace data: all spans from all services for the duration of the incident window + 1hr pre-incident baseline
- Identical metric data: all Prometheus metrics at 1s granularity for the same window
- Identical service dependency graph: the call graph topology (edges from traces, not the FCI-learned causal graph)
- Identical ground truth: the fault injection log (withheld until evaluation; used only for scoring)

**What baselines do NOT receive:**
- RIFT's learned causal graph G_T (each baseline uses only its own internal model)
- RIFT's intervention outcomes (baselines 1–5 are observational only)
- Any information not available from the trace/metric pipeline at the time of the incident

---

### Baseline 1 — Prometheus Threshold Rules

**What it represents:** Standard production alerting — the simplest operational baseline.

**Input:** Prometheus metrics only (no traces, no logs).

**Method:**
```
For each service sᵢ and metric k:
  ALERT if Vᵢₖ[t] > μᵢₖ + 3σᵢₖ_baseline for any k ∈ {latency_p99, error_rate, throughput}
```

Root cause output: the service with the earliest alert trigger time. No attribution model.

**Receives:** Only the metric subset of the common inputs.  
**Does NOT receive:** Trace data, causal graph, intervention outcomes.

**Known limitations:** No topology awareness; no causal reasoning; high false positive rate during correlated events; attributes root cause to first-alerting service regardless of causal direction.

---

### Baseline 2 — Isolation Forest

**What it represents:** Best-practice unsupervised anomaly detection — a strong statistical baseline.

**Input:** Prometheus metrics (multivariate time-series, all services).

**Method:**
```
Train Isolation Forest on W_baseline = 7-day pre-incident metric data
Score each (service, time) pair: anomaly_score(sᵢ, t)
Root cause: argmax_{sᵢ} anomaly_score(sᵢ, t_incident)
```

**Receives:** Metric subset of common inputs.  
**Does NOT receive:** Trace data, causal graph, intervention outcomes.

**Known limitations:** No causal structure; treats all services as independent; susceptible to correlated anomalies caused by shared confounders; no temporal ordering of anomaly onset.

---

### Baseline 3 — MicroRCA-Style (Observational Causal Graph + Random Walk)

**What it represents:** The strongest observational causal-graph-based RCA baseline — closest to RIFT without intervention.

**Input:** Metrics + trace data (same window).

**Method:**
```
1. Build attributed call graph from traces: edges = service calls, weights = Pearson correlation of latency
2. Anomaly detection: flag services with latency_p99 > μ + 3σ
3. Personalized PageRank from flagged services, walking backward along call graph
4. Root cause: service with highest PageRank score
```

**Receives:** Full common inputs (metrics + traces + call graph).  
**Does NOT receive:** FCI-learned causal graph, intervention outcomes.

**Known limitations:** Correlation-based edge weights; no confounder handling; random walk scores do not correspond to causal effect sizes; backward-walk assumption breaks under hidden common causes.

---

### Baseline 4 — Sieve (Adaptive Runtime Injection Without Causal Model)

**What it represents:** The operationally closest competitor — runtime injection + adaptive hypothesis pruning, but without a formal SCM or do-calculus.

**Input:** Metrics + traces + call graph + fault injection capability.

**Method:**
```
1. Detect anomaly via metric threshold
2. Build dependency graph from call graph (edges from traces)
3. Select candidate services from graph topology
4. Inject faults adaptively to prune candidates:
   - If fault injection at sᵢ causes downstream anomaly: sᵢ confirmed as upstream cause
   - If not: remove sᵢ from candidates
5. Root cause: last remaining candidate after pruning
```

**Receives:** Full common inputs + fault injection capability.  
**Critical distinction:** Sieve receives the same injection infrastructure as RIFT, but uses binary outcome matching (did the anomaly propagate?), not CID / interventional distribution estimation.  
**Does NOT receive:** FCI-learned causal graph, SCM, identifiability checks, RIFT's CID scoring.

**Known limitations (that RIFT must show matter on the benchmark):**
- No formal causal model: cannot detect confounders
- Binary outcome matching: cannot quantify partial attribution
- No identifiability checking: may attribute to confounded candidates
- No closed-loop model update: graph is fixed throughout

---

### Baseline 5 — RIFT Without Intervention (RIFT-OBS)

**What it represents:** The ablation baseline — RIFT's full causal model without the intervention layer. This directly tests N2: "does intervention add information beyond observational SCM?"

**Input:** Full common inputs (metrics + traces + call graph).

**Method:**
```
1. Run FCI algorithm to learn G_T from observational data
2. Check identifiability for each candidate X using do-calculus on observational data
3. For identifiable queries: estimate P(Y | do(X := x_nominal)) via backdoor adjustment on observational data
4. Root cause: argmax P(cause = X | observational adjustment)
5. No interventions executed
```

**Receives:** Full common inputs.  
**Does NOT receive:** Any intervention outcome data.

**Why this baseline is critical:** If RIFT-OBS achieves the same accuracy as RIFT-FULL, the intervention layer provides no measurable benefit, and the N2/N1 claims collapse. RIFT-OBS must perform measurably worse on confounded scenarios.

---

### Baseline 6 — Statistical Debugging (Spectrum-Based, Runtime Adapted)

**What it represents:** Classic fault localization methodology (Tarantula/Ochiai family) adapted to runtime distributed traces.

**Input:** Distributed traces only.

**Method:**
```
For each service sᵢ:
  passing_rate(sᵢ) = fraction of requests through sᵢ that completed successfully
  failing_rate(sᵢ) = fraction of requests through sᵢ that failed

Ochiai_score(sᵢ) = failing_rate(sᵢ) / sqrt(total_failures × (failing_rate(sᵢ) + passing_rate(sᵢ)))

Root cause: argmax Ochiai_score(sᵢ)
```

**Receives:** Trace data (request success/failure + service path) from common inputs.  
**Does NOT receive:** Metrics, causal graph, interventions.

**Known limitations:** Correlates service participation in failing requests with fault; no causal direction; high rate of false attribution in shared-infrastructure failures.

---

### Baseline 7 — Sage + Chaos Engineering Composition

**What it represents:** The composition threat from Phase 1 — could Sage + LitmusChaos naively compose into something equivalent to RIFT?

**Input:** Full common inputs + fault injection capability (same as Sieve).

**Method:**
```
Phase A (Sage component):
  1. Build Bayesian Network from fault-labeled historical data (requires pre-training on benchmark system)
  2. At incident time: run belief propagation on BN to rank root cause candidates
  3. Output: top-3 candidates with posterior probabilities

Phase B (Chaos component):
  4. For each top-3 candidate from Sage: inject the corresponding fault type
  5. Observe: does the injection reproduce the observed anomaly pattern?
  6. Root cause: candidate whose injection best reproduces the observed pattern

No feedback: Sage BN is NOT updated by chaos injection outcomes
```

**Receives:** Full common inputs + fault injection capability + pre-trained Sage BN (trained on same benchmark system).  
**Critical distinction:** The composition does not update the causal model from intervention feedback. Sage's BN is static. Chaos injection is unguided by the BN's causal structure (it just tests the top-3 candidates). There is no closed-loop update — this is the architectural gap RIFT fills.

---

### Fair Comparison Protocol

To ensure fairness across all baselines:

1. **Same incident window:** All baselines see the same 2-hour window (1hr pre-incident + 1hr incident)
2. **Same metric resolution:** All receive 1s Prometheus data
3. **Same trace data:** All receive 100% sampled OpenTelemetry traces
4. **Same fault injection budget:** Baselines 4 and 7 receive the same T_budget = 600s as RIFT
5. **Same evaluation metric:** All are evaluated on root-cause precision@1, precision@3, and detection latency
6. **No information leakage:** Ground truth (fault injection log) is withheld until scoring; no baseline has access to RIFT's internal state or vice versa
7. **Baseline 5 (RIFT-OBS) uses RIFT's own graph:** To isolate the effect of intervention, RIFT-OBS uses the same G_T as RIFT-FULL but skips the intervention step — ensures any performance gap is attributable to the intervention, not to different graph-learning methods
