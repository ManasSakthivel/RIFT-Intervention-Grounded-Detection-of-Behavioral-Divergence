# Phase 3.5 — Telemetry Pipeline Validation
**Gate 3.5C | Status: SPECIFICATION_COMPLETE_LIVE_VALIDATION_PENDING**

---

## 1. Telemetry Architecture

```
Online Boutique Services
        │ gRPC + OpenTelemetry
        ▼
    Jaeger (14268)          ←── traces, spans, service dependencies
        │
    Prometheus (9090)       ←── container/infrastructure metrics (if cadvisor added)
        │
    RIFT Collector          ←── queries /api/v1/query_range + Jaeger /api/traces
        │
    Normalization           ←── raw metric → RIFT variable (lat_p99, err_rate, rps, ...)
        │
    Time-Slice Alignment    ←── window_id = floor(timestamp / 10s)
        │
    G_T (CausalVariables)   ←── var_id = "service.metric.tN"
```

---

## 2. P1 Risk: Prometheus gRPC Port Mismatch

**This is the most critical telemetry risk for Phase 3.5.**

The current `docker/prometheus.yml` scrapes boutique services at their **gRPC ports**:

| Service | Scrape target | Actual port role |
|---|---|---|
| boutique-cart | `:7070` | gRPC server port |
| boutique-product | `:3550` | gRPC server port |
| boutique-checkout | `:5050` | gRPC server port |
| boutique-payment | `:50051` | gRPC server port |
| boutique-shipping | `:50051` | gRPC server port |
| boutique-currency | `:7000` | gRPC server port |
| boutique-ad | `:9555` | gRPC server port |

**None of these ports serve Prometheus `/metrics` endpoints.** Online Boutique v0.9.0 uses OpenTelemetry → Jaeger for observability. Prometheus will return `connection refused` or HTTP errors on these ports.

### Resolution Options (must be selected before live deployment)

| Option | Description | Complexity |
|---|---|---|
| **A** (recommended) | Add OpenTelemetry Collector with `prometheusexporter` receiver | Medium |
| B | Add cadvisor container for container-level metrics | Low (but no service-level metrics) |
| C | Use Jaeger trace data to derive latency/error metrics | Medium |
| D | Add Prometheus SDK to each boutique service | High |

**Option A** is recommended: deploy `otelcol` as a sidecar, configure it to receive OTLP from boutique services and export Prometheus metrics at a dedicated `/metrics` endpoint.

---

## 3. Metric Mapping

| RIFT Variable | Prometheus Query | Source |
|---|---|---|
| `lat_p99` | `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[10s]))` | Service metrics / Jaeger |
| `lat_p50` | `histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[10s]))` | Service metrics / Jaeger |
| `err_rate` | `rate(http_requests_total{code=~"5.."}[10s]) / rate(http_requests_total[10s])` | Service metrics |
| `rps` | `rate(http_requests_total[10s])` | Service metrics |
| `cpu_pct` | `rate(container_cpu_usage_seconds_total[10s]) * 100` | cadvisor |
| `mem_pct` | `container_memory_usage_bytes / container_spec_memory_limit_bytes * 100` | cadvisor |

---

## 4. G_T Provenance Requirement

Every `CausalVariable` in G_T must be traceable to its source telemetry:

```
CausalVariable.var_id = "frontend.lat_p99.t3"
    │
    ├── service_id: "frontend"
    │       → scrape job: "boutique-frontend"
    │       → endpoint: boutique-frontend:8080
    │
    ├── metric_name: "lat_p99"
    │       → prometheus query: histogram_quantile(0.99, ...)
    │       → raw metric: http_request_duration_seconds_bucket
    │
    └── time_index: 3
            → TimeWindow: [30s, 40s) from experiment start
            → aligned to: window_id = floor(timestamp / delta_t)
```

Implementation: [`src/rift/models/data_models.py`](../../src/rift/models/data_models.py) `CausalVariable`

---

## 5. Edge Case Validation Tests

| Test | Condition | Expected Behavior | Gap? |
|---|---|---|---|
| TEL-1 | Missing telemetry | No nodes in G_T for that service | No gap |
| TEL-2 | Delayed (lag > 5s) | Assigned to window N+1 | No gap |
| TEL-3 | NaN/Inf values | **KNOWN GAP**: propagates silently | P2 gap: add NaN guard to `Metric.value` |
| TEL-4 | Clock skew > 5s | Wrong window_id assignment | Mitigation: NTP or Docker clock sync |
| TEL-5 | Service restart | Missing windows; AUTOREGRESSIVE edges skip | No gap |
| TEL-6 | 30s telemetry loss | 3 empty windows; RIFT should abstain | No gap |

### Known Gap: NaN Propagation
[`src/rift/models/data_models.py`](../../src/rift/models/data_models.py) `Metric.value: float` has no NaN guard. If Prometheus returns NaN (common during service startup), the value propagates to anomaly detection and may cause false anomaly scores. **Recommended fix**: add a `@validator` that raises on NaN/Inf.

---

## 6. Latency Budget

| Stage | Budget |
|---|---|
| Raw collection | ≤ 5s (Δt/2) |
| Normalization | ≤ 1s |
| Time-slice alignment | ≤ 1s |
| G_T construction | ≤ 1s |
| **Total telemetry processing** | **≤ 5s** |

Δt = 10s (frozen in spec). Collection lag > 5s causes temporal misassignment.

---

## 7. Gate Status

**SPECIFICATION_COMPLETE — LIVE_VALIDATION_PENDING**

Blocking issues:
1. **P1**: Prometheus scrape targets at gRPC ports will not return metrics → must add OTEL Collector or cadvisor
2. **Live deployment**: Online Boutique must be running on Linux

Artifact: [`artifacts/phase3_5/telemetry_validation.json`](../../artifacts/phase3_5/telemetry_validation.json)
