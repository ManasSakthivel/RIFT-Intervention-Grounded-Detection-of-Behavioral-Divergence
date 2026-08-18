# RIFT — Formal System Model
**Phase 2 | Version 1.0**

---

## Part A — Distributed Microservice Execution

### A.1 Services

Let **S = {s₁, s₂, …, sₙ}** be a finite set of *services*.  
Each service sᵢ is a stateful, addressable process unit with a stable logical identity.  
A service may run as multiple *replicas*; replica sᵢ,ⱼ is the j-th instance of service sᵢ.  
RIFT models at the logical-service level; replica-level attribution is a refinement applied only when replica-level metrics are available.

---

### A.2 Operations

Each service sᵢ exposes a finite set of typed operations:

```
Ops(sᵢ) = { opᵢ₁, opᵢ₂, … }
opᵢₖ : InputType → OutputType
```

Operations are observable only through their request/response signatures and execution traces.  
RIFT does not require source code access to service operations.

---

### A.3 Requests

A **request** r is the atomic unit of inter-service communication:

```
r = ⟨ id_r, s_src, s_dst, op, t_sent, t_recv, t_done, status, lat ⟩
```

| Field | Type | Description |
|---|---|---|
| `id_r` | UUID | Globally unique; trace context propagated via W3C TraceContext |
| `s_src` | ServiceID ∪ {⊥} | Originating service; ⊥ for external clients |
| `s_dst` | ServiceID | Destination service |
| `op` | OperationID | Operation invoked |
| `t_sent` | ℝ≥0 | Logical timestamp at dispatch (Lamport/hybrid logical clock) |
| `t_recv` | ℝ≥0 | Timestamp at receipt by s_dst |
| `t_done` | ℝ≥0 | Timestamp at response completion |
| `status` | {OK, ERROR, TIMEOUT, DROPPED} | Terminal status |
| `lat` | ℝ≥0 | `t_done − t_sent` |

---

### A.4 Transactions

A **transaction** T is a directed acyclic partial order over requests:

```
T = ⟨ R_T, ≺_T ⟩
```

where R_T ⊆ {all requests} and rᵢ ≺_T rⱼ iff rᵢ causally precedes rⱼ within T (span-parent relationship in OpenTelemetry).

Transactions correspond to a single user-visible operation (e.g., a checkout, a search).  
RIFT reconstructs T from distributed trace data using trace-ID and parent-span-ID fields.  
**Note:** T is a partial order, not a total order. Concurrent branches are permitted.

---

### A.5 Service State

The **true internal state** of service sᵢ at time t:

```
σᵢ(t) = ⟨ heap_mb(t), cpu_pct(t), threads(t), conn_open(t), q_depth(t), custom(t) ⟩
```

`custom(t)` is a service-specific key-value map (e.g., in-memory cache hit rate, active sessions).

The **observable state proxy** (what RIFT actually observes):

```
Σᵢ(t) = ⟨ lat_p50(t), lat_p99(t), err_rate(t), rps(t), cpu_pct(t), mem_pct(t) ⟩
```

The mapping σᵢ(t) → Σᵢ(t) is a many-to-one aggregation and is **irreversible in general**.  
The gap σᵢ(t) \ Σᵢ(t) is **latent**.

---

### A.6 Database State

Let **D = {d₁, …, dₖ}** be a finite set of data stores (relational, cache, document, event store).

```
δⱼ(t) = ⟨ repl_lag_ms(t), qps(t), conn_count(t), cache_hit_rate(t) ⟩
```

Full row-level state is **latent** unless application-level instrumentation exposes it.  
RIFT only observes aggregate database metrics.

---

### A.7 Message/Event State

Let **Q = {q₁, …, qₘ}** be a finite set of message queues or event streams.

```
φₗ(t) = ⟨ depth(t), consumer_lag_ms(t), produce_rate(t), consume_rate(t), dlq_size(t) ⟩
```

`dlq_size(t)`: dead-letter queue size — a signal for failed message processing.  
Individual message contents are **latent**.

---

### A.8 Resource State

```
ρ(t) = ⟨ net_lat[i,j](t), pkt_loss[i,j](t), disk_io[i](t), host_cpu[h](t), host_mem[h](t) ⟩
```

- `net_lat[i,j](t)`: round-trip latency between sᵢ and sⱼ
- `pkt_loss[i,j](t)`: packet loss fraction on path sᵢ → sⱼ
- `host_cpu[h](t)`, `host_mem[h](t)`: host-level resource consumption (potential cross-service confounders)

Resource state captures **infrastructure-level confounders** that affect multiple services without appearing in the service call graph.

---

### A.9 Failure State

A **failure event** fₑ at time t:

```
fₑ = ⟨ type, target, t_onset, t_recovery, magnitude, observable ⟩
```

| Field | Domain | Description |
|---|---|---|
| `type` | {CRASH, LATENCY, ERROR_RATE, RESOURCE_EXHAUST, NET_PARTITION, LOGIC_ERROR, TIMING} | Failure mode |
| `target` | ServiceID ∪ ResourceID | Affected component |
| `t_onset` | ℝ≥0 | Time failure began |
| `t_recovery` | ℝ≥0 ∪ {∞} | Time failure resolved |
| `magnitude` | ℝ | Quantitative severity |
| `observable` | {TRUE, FALSE} | Whether the fault directly produces observable signals |

Failures with `observable = FALSE` are **silent faults** — a primary source of attribution difficulty.

---

### A.10 Observable Variables

The **complete observable state** at time t:

```
O(t) = ⋃ᵢ Σᵢ(t)  ∪  ⋃ⱼ δⱼ(t)  ∪  ⋃ₗ φₗ(t)  ∪  ρ(t)  ∪  ActiveRequests(t)
```

RIFT's observation is a **sampled, delayed, incomplete** projection of O(t):

| Property | Description |
|---|---|
| **Sampled** | Metrics collected at intervals Δt_scrape (1s for Prometheus; span-level for traces) |
| **Delayed** | Collection pipeline introduces lag ε ∈ [1s, 5s] |
| **Incomplete** | Some services uninstrumented; some metrics unavailable during incidents |

---

### A.11 Latent Variables

```
L(t) = σᵢ(t) \ Σᵢ(t)          ← unobservable internal service state
     ∪ row_level_db_state        ← individual database records
     ∪ message_contents          ← individual message payloads
     ∪ shared_host_contention    ← hardware state below metric resolution
     ∪ external_service_state    ← third-party services outside instrumentation
     ∪ unlogged_operator_actions ← manual interventions not recorded
```

**Latent variables are the primary source of unobserved confounding in RIFT's causal model.**

---

### A.12 System State at Time t

Complete system state:

```
Ω(t) = ⟨ S, D, Q, σ(t), δ(t), φ(t), ρ(t), R(t), L(t) ⟩
```

RIFT operates on:

```
Ω̂(t) = O(t)  ⊊  Ω(t)
```

The gap `Ω(t) \ Ω̂(t) = L(t)` is non-empty in all realistic deployments.  
Every causal claim RIFT makes is conditioned on Ω̂(t), not Ω(t).

---

## Part B — Structural Causal Model

### B.1 Formal Definition

```
M = ⟨ U, V, F, P(U) ⟩
```

**U — Exogenous Variables:**

```
U = { Uᵢ : i ∈ 1…n }
```

Each Uᵢ represents unobserved factors affecting service sᵢ that are not caused by any variable in V.  
Examples: hardware wear, operator actions, external load spikes, unreachable third-party services, software bugs introduced at deployment.

`P(U)` is the joint distribution over exogenous noise.  
**Under the causal sufficiency assumption**, P(U) = ∏ᵢ P(Uᵢ) (mutually independent).  
When causal sufficiency is suspected to be violated, RIFT uses the FCI algorithm and reports hidden-confounder uncertainty (see `causal_assumptions.md`).

**V — Endogenous Variables (time-indexed):**

```
V = { Vᵢₖ[t] : sᵢ ∈ S, k ∈ MetricTypes, t ∈ T_window }
```

Primary endogenous variables per service sᵢ:

```
V_sᵢ = { latency_sᵢ, err_rate_sᵢ, throughput_sᵢ, cpu_sᵢ, mem_sᵢ, queue_depth_sᵢ }
```

Secondary (shared-resource) endogenous variables:

```
V_shared = { net_lat_sᵢ_sⱼ, db_repl_lag_dⱼ, queue_lag_qₗ, host_cpu_h }
```

**F — Structural Mechanisms:**

```
F = { fᵢ : Vᵢ[t] = fᵢ( PA(Vᵢ[t]), Uᵢ[t] ) }
```

For each endogenous variable Vᵢ[t], fᵢ is the structural equation determining its value from its direct parents PA(Vᵢ[t]) in the causal graph and its exogenous noise Uᵢ[t].

*Example* (linear, for illustration; RIFT does not require linearity):

```
latency_s₂[t+1] = α·latency_s₁[t] + β·cpu_s₂[t] + γ·queue_depth_s₂[t] + U_s₂[t+1]
```

**P(U) — Exogenous Distribution:**

```
P(U) = ∏ᵢ P(Uᵢ)    [under causal sufficiency assumption]
```

---

### B.2 SCM-to-Observations Mapping

The SCM M is an idealization. Its connection to Ω̂(t) requires:

1. **Aggregation:** Vᵢₖ corresponds to a windowed aggregate (e.g., p99 latency over Δt = 10s)
2. **Discretization:** Continuous time discretized into windows of length Δt
3. **Alignment:** All variables within a window treated as jointly observed at epoch t
4. **Missing value policy:** Variables with missing observations are treated as latent; no silent imputation

---

## Part C — Time-Sliced DAG

### C.1 Why Static DAGs Fail for Distributed Systems

Real distributed systems contain structural cycles:

| Cycle Type | Example |
|---|---|
| Retry loop | s_A calls s_B; on failure s_B signals s_A to retry → A→B→A |
| Circuit breaker | s_B detects s_A failure; sends fallback to s_A → B→A |
| Auto-scaler | High latency triggers scale-out → latency→replicas→latency |
| Back-pressure | Consumer lag causes producer to slow → consumer→producer |

A static DAG over undifferentiated variables cannot represent these without cycles, violating Pearl's do-calculus (which is defined over DAGs).

### C.2 Time-Sliced (DBN-Style) DAG

RIFT resolves this by indexing all variables by discrete time step t:

```
V[t] = { Vᵢₖ[t] : ∀ sᵢ, ∀ k }    at time step t
V[t+1] = { Vᵢₖ[t+1] : ∀ sᵢ, ∀ k }  at time step t+1
```

**Edges are restricted to:**

```
Vᵢ[t] → Vⱼ[t+1]   ← cross-step causal effects (strictly forward in time)
Vᵢ[t] → Vⱼ[t]     ← same-step effects (allowed only where causal order is verifiable within Δt)
```

**Acyclicity proof:**  
Any directed cycle in G_T would require a directed path from some Vᵢ[t] back to Vᵢ[t]. All cross-step edges are strictly forward (t → t+1). All within-step edges must be acyclically oriented (verified during graph learning). Therefore no directed cycle exists. G_T is a DAG by construction.

### C.3 Cross-Service Dependency Representation

For s_A calling s_B (A depends on B's response):

```
latency_s_B[t] → latency_s_A[t+1]
```

For feedback (auto-scaler):

```
latency_s_A[t] → replica_count_s_A[t+1] → latency_s_A[t+2]
```

Feedback loops appear as multi-hop paths through time — not as cycles.

### C.4 Window Size Δt

Δt must satisfy:

```
Δt  ≥  2 × p99_inter_service_latency    (ensures causal propagation captured across windows)
Δt  ≤  min_anomaly_duration             (ensures EBD resolution is finer than typical fault onset)
```

**Default:** Δt = 10s. Configurable per system at initialization. RIFT validates this at startup by checking that the p99 inter-service call latency < Δt/2.

### C.5 Full Notation

```
G_T = directed acyclic graph over { Vᵢ[t] : ∀ i, t ∈ T_window }
PA(Vᵢ[t]) = direct parents of Vᵢ[t] in G_T
M_T = ⟨ U_T, V_T, F_T, P(U_T) ⟩   — time-indexed SCM
```

---

## Part D — Observation Model

### D.1 Observable Variables by Source

| Source | Observed Variables | Granularity | Pipeline Lag |
|---|---|---|---|
| Distributed traces (OpenTelemetry) | per-request latency, span duration, error flags, parent-child span graph | Per-request | 1–3s |
| Prometheus metrics | cpu_pct, mem_pct, err_rate, throughput, latency histograms | 1s scrape | 1–5s |
| Structured logs | error events, warning counts, exception types, slow-query events | Per-event (async) | 0–30s |
| Service mesh (Istio/Envoy) | retry counts, circuit-breaker state, request volume | 1s | 1–3s |
| Database metrics | repl_lag, qps, conn_count | 10s | 5–10s |
| Queue metrics | depth, consumer_lag, dlq_size | 1–10s | 1–5s |
| Kubernetes events | pod restarts, OOM kills, scheduling failures | Per-event | 1–5s |

### D.2 Latent Variables

| Latent Variable | Cause of Unobservability | Effect on RIFT |
|---|---|---|
| Shared host hardware state | Not exposed via service metrics | Primary unobserved confounder |
| Operator manual actions | May not appear in change logs | Spurious correlation; confounds causal graph |
| Application in-memory state | Not exported to telemetry | Cannot verify structural mechanism |
| External service internals | Outside instrumentation boundary | Edge cannot be verified |
| Individual message payloads | Privacy/security | Cannot attribute logic errors |
| Network buffer state | Below application layer | Unexplained transient latency |

### D.3 Missing Observation Policy

```
If Vᵢ[t] is absent from Ω̂(t):
  → Tag Vᵢ[t] as MISSING
  → Do not impute silently
  → Reduce identifiability confidence for all queries involving Vᵢ
  → If Vᵢ is a required parent in a critical causal path: report QUERY_UNCERTAIN
```

RIFT never imputes missing values for causal queries without explicit disclosure.
