# RIFT End-to-End Pipeline — Phase 3.5E Validation

**Phase 3.5E | Integration Specification**
**Status: INTEGRATION_SPECIFIED_EXECUTION_PENDING**

> **Honest status:** End-to-end pipeline integration is specified and the runner code is
> complete. Live execution is pending Online Boutique deployment on Linux.
> The `do(X)` stage (tc u32 + netem) requires `CAP_NET_ADMIN` and a Linux kernel.
> All stages have been individually validated on synthetic ground-truth data in Phase 3.
> This document specifies what a successful E2E run looks like and what must hold for
> the run to be valid for Gate 3.5E.

---

## 1. Pipeline Architecture

The RIFT pipeline executes 17 stages in a closed loop. The `closed_loop.py` state
machine already implements the full OBSERVE→STOP cycle; this document describes the
complete integration with live telemetry, network intervention, and attribution.

```
OBSERVE (1)
   │  Prometheus/Jaeger telemetry
   ▼
ANOMALY_DETECTION (2)
   │  Z-score detection, Δt=10s windows, θ=3.0σ
   ▼
TIME_SLICED_GT (3)
   │  G_T acyclic by construction, Δt=10s
   ▼
ANOMALY_SUBGRAPH (4)
   │  Strategy D: seed → 1-hop ancestor → bidirected expansion; k≤15
   ▼
FCI (5) ──────────────────────────────────────────────────────────────────┐
   │  FCI Fisher-Z, α=0.05, max_variables=15                             │
   ▼                                                                      │
PAG (6)                                                                   │
   │  DIRECTED / BIDIRECTED / PARTIALLY_DIRECTED edges                   │ PAGResult
   ▼                                                                      │
IDENTIFIABILITY (7) ◄─────────────────────────────────────────────────────┘
   │  backdoor → front-door → REQUIRES_INTERVENTION → NOT_IDENTIFIABLE
   │  RIFT abstains on NOT_IDENTIFIABLE pairs
   ▼
INTERVENTION_CANDIDATES (8)
   │  InterventionCandidate per identifiable service
   ▼
COST_SELECTION (9)
   │  Greedy MSIS: min cumulative cost, θ_entropy=0.5 nats, T_budget=600s
   ▼
DO_X (10)
   │  tc u32 + per-destination netem [dry_run=True on macOS]
   ▼
INTERVENTION_VALIDATION (11)
   │  5 validity checks (precision, clean_window, concurrent_event_free,
   │  recovery_confirmed, isolation_verified)
   ▼
POST_OBSERVE (12)
   │  Post-intervention Prometheus metrics; n≥20 for CANDIDATE, n≥50 for RELIABLE
   ▼
CID (13)
   │  W1 Wasserstein; permutation test B=10000 α=0.05; θ_cid=0.1×IQR_baseline
   ▼
EBD (14)
   │  R1-R4 evaluation; DEFINITIVE iff all four pass; CANDIDATE iff R1-R3
   ▼
GRAPH_UPDATE (15)
   │  Edge confidence update (α_confirm=0.2, α_weaken=0.1)
   │  Bayesian posterior update (Beta(3,1) / Beta(1,3))
   │  Threshold-gated structure update
   ▼
ATTRIBUTION/ABSTENTION (16)
   │  Top EBD candidate → attribution or None
   │  RIFT abstains if confidence=NONE or boundary_limited without R4
   ▼
STOP (17)
   │  H(posterior) < 0.5 nats → ENTROPY_CONVERGED
   │  cumulative_ed ≥ 600s   → BUDGET_EXHAUSTED   [checked FIRST]
   │  SAFE_ABORT state       → SAFETY_ABORT
   │  all posterior = 0      → ALL_CANDIDATES_NON_IDENTIFIABLE
   ▼
   Loop back to OBSERVE (if not stopped) ──────────────────────────────► END
```

### Key architectural note

The `closed_loop.py` state machine already implements the full OBSERVE→STOP cycle
(`ClosedLoop.step()`, `run_to_completion()`). The `RIFTEndToEndRunner` wraps it by
wiring real telemetry and network intervention into each state transition. The loop
is not a simulation — it is a live experiment controller once the Linux testbed is
deployed.

---

## 2. Critical Invariant: Live vs Synthetic Telemetry

### Definition

| Field | Meaning |
|---|---|
| `live_telemetry_used=True` | All metric data sourced from a running Prometheus endpoint scraping a real cluster |
| `synthetic_substitution=False` | No MockTelemetry data was substituted at any stage |

### Gate 3.5E Validity Rule

```
valid_for_gate := live_telemetry_used == True AND synthetic_substitution == False
```

A run where `synthetic_substitution=True` is **not valid** for Gate 3.5E evaluation.
It is still recorded in `RIFTRunRecord` for audit and regression purposes, but
cannot be used to claim live pipeline execution.

### How synthetic substitution is detected

The runner sets `synthetic_substitution=True` in any of the following circumstances:
1. `telemetry_source` is a `MockTelemetry` instance (the `is_live` property returns `False`)
2. The `POST_OBSERVE` stage falls back to synthetic data because `PrometheusClient.collect()` raised `NotImplementedError`
3. Any stage manually injects a synthetic fallback due to a data collection failure

### What constitutes live telemetry

- **Live:** `PrometheusClient(endpoint="http://prometheus:9090")` connected to an Online Boutique cluster scraping `lat_p99`, `lat_p50`, `err_rate`, `rps`, `cpu_pct`, `mem_pct` from the six Online Boutique services (`frontend`, `cartservice`, `productcatalogservice`, `currencyservice`, `checkoutservice`, `paymentservice`)
- **Synthetic:** `MockTelemetry(seed=42)` generating Gaussian noise from `np.random.default_rng(seed).normal(50.0, 5.0, n)`

---

## 3. Provenance Tracing Requirement

Every variable in the final attribution must be traceable to its source telemetry.
The `RIFTRunRecord.provenance` field is a dict mapping each stage name to a
`ProvenanceEntry`:

```json
{
  "source":       "which Python function produced this stage output",
  "upstream":     "which stage(s) fed this stage",
  "telemetry_ref": "PrometheusClient:http://prometheus:9090 or MockTelemetry:seed=42"
}
```

### Tracing example: W1 estimate in CID → raw telemetry

```
attribution="frontend" confidence="DEFINITIVE"
  ← EBD.r4_pass=True
     ← CID.w1_estimate=0.42 exceeds_threshold=True
        ← provenance["CID"].upstream = "POST_OBSERVE"
           ← provenance["POST_OBSERVE"].upstream = "DO_X + INTERVENTION_VALIDATION"
              ← provenance["DO_X"].upstream = "COST_SELECTION"
                 ...
                    ← provenance["OBSERVE"].telemetry_ref = "PrometheusClient:http://prometheus:9090"
```

A researcher receiving a `RIFTRunRecord` can follow this chain to confirm that
every number in the attribution was derived from actual cluster telemetry and not
from synthetic data.

---

## 4. Latency Targets

| Phase | Criteria | Target Latency | CID Grade Required |
|---|---|---|---|
| CANDIDATE | R1-R3 satisfied (no intervention) | ~30 seconds | CANDIDATE (n≥20) |
| DEFINITIVE | R1-R4 satisfied (intervention confirmed) | ~120–300 seconds | RELIABLE (n≥50) |

### Per-stage latency budget (indicative)

| Stage | Indicative Latency |
|---|---|
| OBSERVE (1) | ~2–5s |
| ANOMALY_DETECTION (2) | <1s |
| TIME_SLICED_GT (3) | <1s |
| ANOMALY_SUBGRAPH (4) | <1s |
| FCI (5) | <30s for k≤15 |
| PAG (6) | <0.1s |
| IDENTIFIABILITY (7) | <1s per pair |
| INTERVENTION_CANDIDATES (8) | <0.5s |
| COST_SELECTION (9) | <1s |
| DO_X (10) | <2s per intervention |
| INTERVENTION_VALIDATION (11) | <5s |
| POST_OBSERVE (12) | ~5s |
| CID (13) — CANDIDATE | ~30s (B=1000) |
| CID (13) — RELIABLE | ~120–300s (B=10000) |
| EBD (14) | <5s |
| GRAPH_UPDATE (15) | <0.5s |
| ATTRIBUTION/ABSTENTION (16) | <0.1s |
| STOP (17) | <0.1s |

The `PipelineStageRecord.duration_s` field records the actual wall-clock duration
of each stage and is the measurement instrument for Gate 3.5M latency evaluation.

---

## 5. What a Successful E2E Run Looks Like

A `RIFTRunRecord` from a successful Gate 3.5E run has:

```python
record.live_telemetry_used     == True
record.synthetic_substitution  == False
record.final_state             in ("PASS", "ABSTAINED")   # FAILED means pipeline error
record.attribution_confidence  in ("DEFINITIVE", "CANDIDATE", "NONE")
record.is_valid_for_gate       == True
```

### PASS + DEFINITIVE run
- All 17 stages completed with status=COMPLETE
- At least one EBD candidate with `confidence="DEFINITIVE"` (R1-R4 all True)
- `attribution` is a non-null service ID
- CID W1 exceeds θ_cid with RELIABLE grade (n≥50)
- `total_duration_s` in [120, 300] seconds

### PASS + CANDIDATE run
- All stages through EBD completed
- At least one EBD candidate with `confidence="CANDIDATE"` (R1-R3 True, R4 not required)
- `attribution` is a non-null service ID
- `total_duration_s` ≈ 30 seconds

### ABSTAINED run (valid outcome)
- RIFT abstains when no EBD candidate satisfies R1-R3, or when identifiability returns NOT_IDENTIFIABLE, or when CID grade is INSUFFICIENT (n<20)
- `attribution=None`, `attribution_confidence="NONE"`, `final_state="ABSTAINED"`
- This is a correct and expected outcome — RIFT must abstain rather than make false claims

### FAILED run (pipeline error, not an abstention)
- A stage returned status=FAILED or ABORTED unexpectedly
- `final_state="FAILED"` — not an abstention, but a runtime error
- Examine `pipeline_stages[i].notes` for the failure reason

---

## 6. Stopping Conditions

The `ClosedLoop.check_stopping()` method evaluates four conditions on each
`GRAPH_UPDATE → STOP` transition. Condition 2 (budget) is checked **first** as
a hard safety limit:

| Priority | Condition | Trigger |
|---|---|---|
| 1 (FIRST) | BUDGET_EXHAUSTED | cumulative_ed ≥ 600s OR budget_remaining ≤ 0 |
| 2 | SAFETY_ABORT | SAFE_ABORT state (injected by safety checker) |
| 3 | ALL_CANDIDATES_NON_IDENTIFIABLE | All posterior values = 0.0 |
| 4 | ENTROPY_CONVERGED | H(posterior) < 0.5 nats AND non-zero candidates ≥ 2 |

If no stopping condition is met, the loop returns to `OBSERVE` for the next iteration.
The `max_iterations` parameter provides an outer safety bound.

---

## 7. Current Gap: macOS / No Linux Testbed

The following capabilities are **not executable** on macOS or without an Online
Boutique Kubernetes cluster:

| Capability | Gap |
|---|---|
| `PrometheusClient.collect()` | Raises `NotImplementedError` — no live Prometheus endpoint |
| `NetworkInterventionEngine.apply()` (not dry_run) | Requires `CAP_NET_ADMIN` + Linux `tc` binary |
| Per-destination `tc u32 + netem` | Linux kernel only; macOS `pfctl` has different semantics |
| Post-intervention Prometheus metrics | Requires a running service mesh under controlled fault injection |
| n≥50 RELIABLE CID samples | Requires ≥50s of 1-sample-per-second Prometheus scraping post-intervention |

### Workaround for CI / integration testing

Use `MockTelemetry` with `dry_run=True`:

```python
runner = RIFTEndToEndRunner(
    telemetry_source=MockTelemetry(seed=42),
    services=["frontend", "cartservice", "productcatalogservice"],
    call_graph=call_graph,
    dry_run=True,
)
record = runner.run()
assert record.synthetic_substitution == True    # expected
assert not record.is_valid_for_gate             # correctly rejected for Gate 3.5E
```

This exercises the full pipeline code path without requiring a running cluster.
It does not constitute live execution.

---

## 8. Files

| File | Description |
|---|---|
| `src/rift/pipeline/e2e_runner.py` | `RIFTEndToEndRunner`, `RIFTRunRecord`, `PipelineStageRecord`, `PrometheusClient`, `MockTelemetry` |
| `src/rift/pipeline/__init__.py` | Package exports |
| `artifacts/phase3_5/e2e/e2e_pipeline_spec.json` | Machine-readable pipeline spec (17 stages with input/output/latency/validation) |
| `artifacts/phase3_5/e2e/rift_run_record_schema.json` | JSON Schema for `RIFTRunRecord` |
| `docs/phase3_5/e2e_validation.md` | This document |

---

## 9. Summary Status

| Item | Status |
|---|---|
| Pipeline runner code | COMPLETE |
| All 17 stage records | COMPLETE |
| Provenance tracing | SPECIFIED (per-stage provenance_map implemented) |
| Live telemetry integration | PENDING (PrometheusClient.collect() stub) |
| tc intervention execution | PENDING (dry_run=True until Linux testbed) |
| RIFTRunRecord schema | COMPLETE |
| Pipeline spec JSON | COMPLETE |
| Gate 3.5E live run | PENDING_LINUX_DEPLOYMENT |

> **Critical invariant:** `live_telemetry_used=True AND synthetic_substitution=False`
> is the only condition under which a `RIFTRunRecord` is valid for Gate 3.5E evaluation.
> All other combinations must be explicitly rejected.
