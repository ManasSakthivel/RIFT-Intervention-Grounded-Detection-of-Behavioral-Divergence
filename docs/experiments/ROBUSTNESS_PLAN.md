# RIFT Robustness Experiment Plan

**File:** `docs/experiments/ROBUSTNESS_PLAN.md`  
**Status:** SPECIFIED / READY_FOR_LINUX  
**Phase:** 4.5 (Mac pre-Linux readiness sprint)  
**Authority:** `docs/hypotheses.md`, `experiments/REGISTRY.yaml`, `docs/PHASE_3_SPEC_FREEZE.md §14`

---

## Purpose

This plan specifies robustness experiments covering all fault classes and
telemetry failure modes. Robustness results do not test H1–H5 directly;
they characterize system behavior under adverse conditions and support
the "Threats to Validity" section of the paper.

---

## Fault Class Coverage

### R1 — Network Latency
**Fault:** Added latency on service-to-service TCP/gRPC connections  
**Injected via:** `tc netem delay {N}ms` on designated interface  
**Parameters:** 50ms, 100ms, 200ms, 500ms (three trials each)  
**Expected RIFT behavior:** EBD detects divergence at root-cause service; attribution DEFINITIVE  
**Key metric:** Rate of correct attribution vs. latency magnitude  
**Dataset:** `datasets/rift_faults/development.json` scenarios NL_*  
**Status:** READY_FOR_LINUX

---

### R2 — Packet Loss
**Fault:** Packet loss on service-to-service link  
**Injected via:** `tc netem loss {P}%`  
**Parameters:** 1%, 5%, 10% (three trials each)  
**Expected RIFT behavior:** EBD R3 (temporal precedence) still holds; attribution possible  
**Key metric:** Precision@1 vs. loss percentage; CONFOUNDED rate at high loss  
**Dataset:** `datasets/rift_faults/development.json` scenarios PL_*  
**Status:** READY_FOR_LINUX

---

### R3 — Dependency Failures
**Fault:** A downstream service stops responding (SIGSTOP or network black-hole)  
**Parameters:** Each of the 10 boutique services, 3 trials  
**Expected RIFT behavior:** Attribution to service that first stops responding;  
  boundary_limited=True if the stopped service is not instrumented  
**Key metric:** Precision@1; boundary_limited rate  
**Dataset:** `datasets/rift_faults/development.json` scenarios SD_*  
**Status:** READY_FOR_LINUX

---

### R4 — Resource Contention
**Fault:** CPU stress on a container (`stress-ng --cpu 4`)  
**Parameters:** 50%, 80%, 100% CPU load; 3 trials each  
**Expected RIFT behavior:** Attribution to stressed container; anomaly subgraph  
  contains container service; CID confirms behavioral divergence post-intervention  
**Key metric:** Precision@1; false attribution rate on non-stressed services  
**Dataset:** `datasets/rift_faults/development.json` scenarios RC_*  
**Status:** READY_FOR_LINUX

---

### R5 — Queueing
**Fault:** Shared resource queueing (single-thread service with high request rate)  
**Parameters:** 2×, 5×, 10× normal request rate  
**Expected RIFT behavior:** Attribution to bottleneck service;  
  RIFT-OBS may attribute to caller instead of callee (H2 test scenario)  
**Key metric:** Precision@1; RIFT-FULL vs RIFT-OBS gap under queueing  
**Dataset:** `datasets/rift_faults/development.json` scenarios QU_*  
**Status:** READY_FOR_LINUX

---

### R6 — Confounding (Shared Infrastructure)
**Fault:** Two independent services share a host experiencing CPU contention  
**Parameters:** 8 confounded scenario pairs from `datasets/rift_faults/`  
**Expected RIFT behavior:** FCI produces bidirected edge; RIFT abstains or returns  
  multi-cause attribution; RIFT-OBS cannot distinguish (H2 critical test)  
**Key metric:** Correct abstention rate; not_identifiable_rate  
**Dataset:** confounded scenarios in `datasets/rift_faults/development.json`  
**Status:** READY_FOR_LINUX

---

### R7 — Multi-Cause Faults
**Fault:** Two independent faults injected simultaneously (different services)  
**Parameters:** 3 multi-cause scenario pairs  
**Expected RIFT behavior:** Multi-cause attribution; closed-loop iterates to find both  
**Key metric:** Precision@1 on MULTI_CAUSE scenarios; closed-loop iteration count  
**Dataset:** `datasets/rift_faults/development.json` scenarios MC_*  
**Status:** READY_FOR_LINUX

---

## Telemetry Failure Modes

### TF1 — Missing Telemetry (Service Not Instrumented)
**Scenario:** A root-cause service has no metrics in `PrometheusClient.collect()`  
**Expected RIFT behavior:** `boundary_limited=True`; attribution to earliest  
  instrumented ancestor; notes explain instrumentation gap  
**Key metric:** boundary_limited_rate; notes accuracy  
**Test:** `tests/unit/test_phase36_new_modules.py` (dry-run)  
**Status:** DRY_RUN_READY

---

### TF2 — Delayed Telemetry (High Prometheus Lag)
**Scenario:** Prometheus scrape lag > 2×Δt (30s lag on 15s scrape interval)  
**Expected RIFT behavior:** Forward-fill at most 1 consecutive window;  
  second+ consecutive gap left as NaN; EBD R3 may degrade  
**Key metric:** Attribution accuracy with 1 vs 2+ consecutive missing windows  
**Test:** Inject NaN values in MockTelemetry  
**Status:** DRY_RUN_READY

---

### TF3 — Noisy Telemetry (High Variance Baseline)
**Scenario:** Prometheus metric has high baseline variance (σ/μ > 0.5)  
**Expected RIFT behavior:** RIFT adjusts θ_detect dynamically; anomaly subgraph  
  may be empty; RIFT abstains rather than attributing spuriously  
**Key metric:** False attribution rate under high-variance conditions  
**Test:** Inject high-variance values in MockTelemetry  
**Status:** DRY_RUN_READY

---

### TF4 — Prometheus Unavailable
**Scenario:** Prometheus HTTP API returns connection error  
**Expected RIFT behavior:** `PrometheusClient.collect()` raises ConnectionError;  
  pipeline stage OBSERVE recorded as ABORTED; run returns FAILED with proper notes  
**Key metric:** Error propagation correctness; no silent failures  
**Test:** `tests/unit/test_prometheus_client.py::TestPrometheusUnavailable`  
**Status:** IMPLEMENTED / MAC_TESTED

---

### TF5 — Malformed Prometheus Response
**Scenario:** Prometheus returns invalid JSON or non-success status  
**Expected RIFT behavior:** `ValueError` raised; pipeline ABORTED; no partial attribution  
**Key metric:** Correct error type; no silent data corruption  
**Test:** `tests/unit/test_prometheus_client.py::TestMalformedJSON`  
**Status:** IMPLEMENTED / MAC_TESTED

---

## Robustness Summary Table

| Category | Test ID | Fault | Status | Experiment |
|---|---|---|---|---|
| Network | R1 | Latency 50–500ms | READY_FOR_LINUX | EXP-011 |
| Network | R2 | Packet loss 1–10% | READY_FOR_LINUX | EXP-011 |
| Service | R3 | Dependency failure | READY_FOR_LINUX | EXP-011 |
| Resource | R4 | CPU contention | READY_FOR_LINUX | EXP-011 |
| Load | R5 | Queue saturation | READY_FOR_LINUX | EXP-011 |
| Causal | R6 | Shared-infra confounding | READY_FOR_LINUX | EXP-002 |
| Multi | R7 | Simultaneous faults | READY_FOR_LINUX | EXP-013 |
| Telemetry | TF1 | Missing instrumentation | DRY_RUN_READY | descriptive |
| Telemetry | TF2 | Delayed/lagged metrics | DRY_RUN_READY | descriptive |
| Telemetry | TF3 | High-variance baseline | DRY_RUN_READY | descriptive |
| Telemetry | TF4 | Prometheus unavailable | IMPLEMENTED | test suite |
| Telemetry | TF5 | Malformed response | IMPLEMENTED | test suite |

---

## Limitations to Report (from Robustness)

The following limitations MUST appear in the paper's Threats to Validity section.
References are to `docs/hypotheses.md` Parts R:

| Limitation | Code | When It Applies |
|---|---|---|
| Unobserved confounding | L1 | Two services share latent common cause |
| Invalid intervention | L2 | tc netem precision error ≥ 20% |
| Non-replayable state | L3 | Race conditions; CID scores near zero |
| Insufficient observability | L4 | Root cause not instrumented |
| Non-identifiable query | L5 | Complete bipartite confounder pattern |
| Simultaneous causal events | L6 | Two faults in same time window |
| External dependency | L7 | Third-party service as root cause |
| Stale causal graph | L8 | Deployment/scale event between G_T and incident |
