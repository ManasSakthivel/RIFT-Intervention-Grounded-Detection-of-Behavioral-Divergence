# RIFT Live Telemetry Data Path

**Status: IMPLEMENTED / MAC_TESTABLE / READY_FOR_LINUX**  
**Authority: docs/PHASE_3_SPEC_FREEZE.md §1, Phase 3.6 §3**  
**Phase: 4.5 (Mac pre-Linux readiness)**

---

## Overview

This document describes the exact data path from Online Boutique microservice
telemetry to the RIFT causal graph construction pipeline.  Every step is
implemented and testable; live validation requires a Linux testbed with
Online Boutique deployed.

---

## Complete Data Path

```
Online Boutique services (10 microservices, v0.9.0)
│
│   OTLP gRPC (port 4317)
│   env: OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
│        DISABLE_TRACING=0
│
▼
OpenTelemetry Collector  (docker/otel-collector-config.yaml)
│   receiver: otlp (grpc + http)
│   receiver: prometheus (cadvisor container metrics)
│   processor: batch, resource (env=rift-eval label)
│   exporter: prometheus → port 8889  (boutique_* namespace)
│   exporter: otlp/jaeger → jaeger:14250
│
▼
Prometheus  (docker/prometheus.yml)
│   job: otel-collector → scrapes otel-collector:8889
│   scrape_interval: 15s
│   honor_labels: true (preserves service label from collector)
│   HTTP API: http://prometheus:9090/api/v1/query_range
│
▼
PrometheusClient  (src/rift/pipeline/e2e_runner.py)
│   collect(services, window_s=300)
│   _query_range(query, t_end, window_s, step_s=15s)
│   _result_to_dataframe(result) → DataFrame(time, value)
│   Returns: {service_id: DataFrame(columns=['time','value'])}
│
▼
TelemetryNormalizer  (src/rift/telemetry/normalizer.py)
│   normalize_telemetry_batch()
│   forward-fill: max 1 consecutive window
│   NaN policy: never replaced with 0.0
│
▼
TimeSliceConfig + build_time_sliced_graph()
│   delta_t = 10s  (SPEC_FREEZE §2)
│   max_lag = 1
│
▼
G_T (time-sliced causal graph)
│
▼
RIFT pipeline stages 2–17
```

---

## Component Configuration

### Online Boutique Services

| Service | Image Tag | OTLP Endpoint Variable |
|---|---|---|
| frontend | v0.9.0 | `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317` |
| cartservice | v0.9.0 | same |
| productcatalogservice | v0.9.0 | same |
| checkoutservice | v0.9.0 | same |
| recommendationservice | v0.9.0 | same |
| paymentservice | v0.9.0 | same |
| emailservice | v0.9.0 | same |
| shippingservice | v0.9.0 | same |
| currencyservice | v0.9.0 | same |
| adservice | v0.9.0 | same |

All services have `DISABLE_TRACING: "0"` to enable OTLP export.

### OTel Collector (docker/otel-collector-config.yaml)

| Parameter | Value | Purpose |
|---|---|---|
| OTLP gRPC receiver | `0.0.0.0:4317` | Accepts telemetry from boutique |
| OTLP HTTP receiver | `0.0.0.0:4318` | Accepts telemetry from boutique (HTTP) |
| Prometheus exporter | `0.0.0.0:8889` | Exposes metrics for Prometheus scrape |
| Metric namespace | `boutique` | Prefix on all exported metrics |
| resource_to_telemetry | enabled | Promotes `service.name` to label |
| Jaeger exporter | `jaeger:14250` | Forwards traces |

### Prometheus (docker/prometheus.yml)

| Parameter | Value | Purpose |
|---|---|---|
| scrape_interval | 15s | Matches RIFT delta_t minimum |
| otel-collector target | `otel-collector:8889` | Single scrape point for all boutique metrics |
| honor_labels | true | Preserves collector-set `service` label |

### PrometheusClient (src/rift/pipeline/e2e_runner.py)

| Parameter | Value | Purpose |
|---|---|---|
| endpoint | `http://prometheus:9090` | Set via `RIFT_PROMETHEUS_URL` env var |
| scrape_interval_s | 15.0 | Matches Prometheus scrape interval |
| timeout_s | 10.0 | HTTP request timeout |
| primary_metric | `lat_p99` | Default metric: gRPC P99 latency |
| step | max(10, scrape_interval_s) | Aligned to Δt=10s minimum |

---

## Metrics Available After Full Pipeline

| Metric Key | Prometheus Query | Unit |
|---|---|---|
| `lat_p99` | `histogram_quantile(0.99, sum(rate(grpc_server_handling_seconds_bucket{job=~"<svc>"}[1m])) by (le))` | seconds |
| `rps` | `sum(rate(grpc_server_started_total{job=~"<svc>"}[1m]))` | req/s |
| `err_rate` | `sum(rate(...grpc_code!="OK"...)) / sum(rate(...total...))` | fraction |

The metric key is exposed via the `boutique_` namespace on the collector side:
`boutique_grpc_server_handling_seconds_bucket`, etc.

---

## Scope Boundaries

| Evidence Type | Status | Source |
|---|---|---|
| Configuration complete | ✅ DONE | This document + docker/ files |
| Mac testability (mock) | ✅ DONE | MockTelemetry in e2e_runner.py |
| PrometheusClient implemented | ✅ DONE | T1 fix (IMPLEMENTED/MAC_TESTED) |
| OTel Collector config | ✅ DONE | docker/otel-collector-config.yaml |
| Docker Compose wired | ✅ DONE | docker/docker-compose.yml |
| Live E2E validation | ⏳ PENDING_LINUX | Requires deployed Online Boutique |

**Do NOT mark as LIVE_VALIDATED until:**
1. Online Boutique is deployed on Linux testbed
2. At least one `PrometheusClient.collect()` call returns non-empty DataFrames
3. A `RIFTRunRecord` with `live_telemetry_used=True` is produced

---

## Known Constraints

1. **gRPC vs Prometheus scrape**: Online Boutique v0.9.0 services export metrics
   via OTLP gRPC, not Prometheus text format.  Direct scraping of boutique ports
   (8080, 7070, etc.) will return empty or 404.  The OTel Collector is the
   correct intermediary.

2. **Metric latency**: OTel Collector batches metrics with a 10s timeout.
   Combined with Prometheus 15s scrape interval, the effective lag is ≤25s.
   This is within the Δt=10s alignment tolerance (≤1 forward-fill window).

3. **cadvisor**: Container resource metrics (CPU, memory) require a cadvisor
   sidecar.  The OTel Collector is configured to scrape `cadvisor:8080` if
   deployed.  Not required for latency/error-rate RIFT experiments.

4. **Service label mapping**: The collector sets `service` label from
   `service.name` OTLP resource attribute.  The PrometheusClient uses this
   label as the `job` selector in queries.  Service names must match between
   boutique OTEL_SERVICE_NAME and the RIFT `services` list.
