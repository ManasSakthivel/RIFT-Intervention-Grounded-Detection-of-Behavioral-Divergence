# RIFT Telemetry Architecture
# Phase 3.6 — Complete Specification
# Status: READY_FOR_LINUX
# Authority: docs/PHASE_3_SPEC_FREEZE.md §1, Phase 3.6 §3

## Overview

The RIFT telemetry layer converts live microservice observability signals into
aligned, normalized time-window DataFrames for causal graph construction (G_T).

**Status: READY_FOR_LINUX**
This document and the corresponding implementation are complete.
Live execution requires a deployed Online Boutique cluster on Linux.

---

## Architecture

```
Online Boutique services
        |
        | gRPC / HTTP metrics
        v
   OTEL Collector (docker/otel-collector-config.yaml)
        |
        | Prometheus remote-write
        v
   Prometheus (docker/prometheus.yml)
        |
        | HTTP range query /api/v1/query_range
        v
   PrometheusClient (src/rift/pipeline/e2e_runner.py)
        |
        | RawPrometheusMetric[]
        v
   TelemetryNormalizer (src/rift/telemetry/normalizer.py)
        |
        | normalize_telemetry_batch()
        v
   AlignedMetricStream {service → {metric → DataFrame}}
        |
        | to_pipeline_dataframes()
        v
   {service_id: DataFrame(time, value)}
        |
        v
   TimeSliceConfig + build_time_sliced_graph()
        |
        v
   G_T (time-sliced causal graph, Δt=10s)
```

---

## Supported Metrics

| Metric | Prometheus Query | Unit | Notes |
|---|---|---|---|
| `lat_p99` | `histogram_quantile(0.99, rate(...)_bucket[1m])` | ms | P99 latency |
| `lat_p50` | `histogram_quantile(0.50, rate(...)_bucket[1m])` | ms | P50 latency |
| `err_rate` | `rate(..._errors_total[1m]) / rate(..._requests_total[1m])` | fraction | Error rate |
| `rps` | `rate(..._requests_total[1m])` | req/s | Request rate |
| `cpu_pct` | `rate(container_cpu_usage_seconds_total[1m]) * 100` | % | CPU usage |
| `mem_pct` | `container_memory_working_set_bytes / limit * 100` | % | Memory usage |

---

## Data Collection Configuration

### Scrape interval
- Prometheus scrape interval: **15s**
- RIFT window size: **Δt=10s** (SPEC_FREEZE §2)
- Collection lag tolerance: **≤1 window** (forward-fill only)

### Service identity
Each metric series includes labels:
- `service`: Online Boutique service name (e.g., `frontend`, `cartservice`)
- `namespace`: Must match `rift-eval-*` pattern
- `job`: prometheus job label for filtering

### Trace correlation
Jaeger spans provide:
- Service dependency graph (call graph topology for G_T)
- Request-level trace IDs for correlation
- Span timing for latency ground truth

---

## OTEL Collector Configuration

File: `docker/otel-collector-config.yaml`

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
  prometheus:
    config:
      scrape_configs:
        - job_name: 'boutique'
          scrape_interval: 15s
          static_configs:
            - targets:
              - boutique-frontend:8080
              - boutique-cart:7070
              - boutique-product:3550
              - boutique-checkout:5050
              - boutique-recommend:8080
              - boutique-currency:7000
              - boutique-payment:50051
              - boutique-email:8080
              - boutique-shipping:50051
              - boutique-ad:9555

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"
  jaeger:
    endpoint: jaeger:14250

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [jaeger]
    metrics:
      receivers: [prometheus]
      exporters: [prometheus]
```

---

## Normalization Rules (docs/formal_model.md §D)

1. **Missing data policy**: NaN is NEVER replaced with 0.0.
   Missing windows are tagged and excluded from statistical analysis.

2. **Forward-fill limit**: At most 1 consecutive window may be forward-filled.
   If 2+ consecutive windows are missing, they remain NaN.

3. **Infinite / NaN Prometheus values**: `+Inf`, `-Inf`, `NaN` strings are
   parsed as Python `None` and recorded as missing.

4. **Time alignment**: Each window uses the LAST observation within
   `[t_start, t_start + Δt)` (Prometheus step-query semantics).

---

## Known Issues (Resolved)

### Previous: Prometheus/gRPC incompatibility
**Status: RESOLVED in Phase 3.6**

The OTEL Collector intermediates between gRPC-instrumented boutique services
and Prometheus. Services export OTLP gRPC → Collector → Prometheus remote-write.
This eliminates the direct gRPC-to-Prometheus scrape issue from Phase 3.5.

### Configuration file added
`docker/otel-collector-config.yaml` provides the complete collector pipeline.

---

## Linux Execution Requirements

| Requirement | Purpose |
|---|---|
| Linux kernel ≥ 4.19 | `tc netem` per-destination support |
| Docker Engine ≥ 24 | Container networking |
| CAP_NET_ADMIN | `tc` command execution |
| `kubectl` ≥ 1.27 | Pod-level fault injection |
| Python 3.11 | Runtime |

---

## Status

- **Software / configuration**: COMPLETE
- **Testing on macOS (mock telemetry)**: READY
- **Live execution**: PENDING_LINUX

Do NOT mark as LIVE_VALIDATED until Online Boutique is deployed and
at least one full E2E run with `live_telemetry_used=True` completes.
