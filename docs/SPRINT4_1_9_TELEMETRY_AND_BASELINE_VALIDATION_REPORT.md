# RIFT Sprint 4.1.9 — Telemetry Pipeline and Baseline Validation Report

**Date:** 2026-11-02  
**Target Host:** Linux QA VM (`9.30.57.225:22` / `wca4z-understand-dp1.fyre.ibm.com`)  
**Sprint / Stage:** Sprint 4.1.9 / Stage 3 — Live Telemetry and Baseline Validation  
**Lead Authority:** Primary Integration Agent  
**Final Verdict:** **PARTIALLY VALIDATED**

---

## 1. Executive Summary & Verdict

In accordance with the Sprint 4.1.9 Mandate and the Staged Live-Validation Readiness Runbook ([`docs/SPRINT4_1_5_LIVE_VALIDATION_READINESS_RUNBOOK.md`](docs/SPRINT4_1_5_LIVE_VALIDATION_READINESS_RUNBOOK.md)), a non-invasive, read-only telemetry audit and baseline verification of the Stage 2 deployed benchmark stack was executed on the remote Linux QA host (`9.30.57.225`).

### Summary of Audit Findings
1. **Infrastructure Health & Safety:** All 14 containers are running and healthy on isolated bridge network `rift-net` (`10.89.100.0/24`). All published ports are strictly bound to `127.0.0.1`. Host resources remain stable ($4.19\text{ GiB}$ available RAM), and existing IBM workloads (`bobz-understand`, user `aakash` processes) remain completely unaffected.
2. **Traffic Generation:** `rift-loadgenerator` is generating continuous synthetic user requests against `rift-frontend:8080`, achieving an aggregated throughput of $\sim 1.9\text{ req/s}$ with $0.00\%$ HTTP errors.
3. **Telemetry Pipeline Root-Cause Blockers:**
   - **Missing Environment Variable (`ENABLE_TRACING=1`):** Google Online Boutique v0.8.1 microservices require `ENABLE_TRACING=1` to activate their OpenTelemetry gRPC / OTLP trace exporters. In the current deployment manifest ([`deploy/podman-compose.yaml`](deploy/podman-compose.yaml)), `COLLECTOR_SERVICE_ADDR` was configured but `ENABLE_TRACING=1` was omitted. Microservice container logs confirm `Tracing disabled.`, resulting in $0$ spans arriving at the OpenTelemetry Collector receiver (`rift-otel-collector:4317`).
   - **Spanmetrics Empty Output:** Because zero spans are received by the Collector, the `spanmetrics` connector generates $0$ time-series samples to its Prometheus exporter (`0.0.0.0:8889`).
   - **Prometheus Scraping Status:** `job: rift-otel-spanmetrics` is `health: "up"` but scrapes $0$ metric samples. `job: rift-frontend` is `health: "down"` (HTTP 404) because the Go frontend binary in v0.8.1 does not expose a native `/metrics` endpoint.
   - **Ingestion Query Schema Mismatch:** RIFT's [`PrometheusClient`](src/rift/pipeline/e2e_runner.py:86) expects metric names formatted as `grpc_server_handling_seconds_bucket{job=~"<service>"}`, whereas the OTel `spanmetrics` connector exports metrics as `rift_latency_bucket{service_name=~"<service>"}`.

In accordance with the operational safety mandate ("If telemetry cannot be validated with the existing configuration, document the blocker. Do not automatically change the live configuration to make the checks pass"), no containers were reconfigured or restarted.

**Final Verdict:** **PARTIALLY VALIDATED** (Infrastructure and monitoring topology validated; telemetry flow and baseline capture blocked by microservice tracing configuration and query schema reconciliation).

---

## 2. Authorization and Scope Boundary

- **Operational Mode:** Read-only observation, telemetry inspection, and diagnostic validation.
- **Safety Policy Compliance:**
  - Fault Injections: **0 (Strictly prohibited & none executed)**.
  - `tc netem` / Traffic Impairments: **0 (Strictly prohibited & none executed)**.
  - Host Interface / Network Alterations: **0 (None executed)**.
  - Coexisting IBM Workloads (`bobz-understand`, `aakash`): **Preserved & undisturbed**.
  - Container / Volume / Network Deletions: **0 (None executed)**.
  - Secret Exposure: **0 (Zero credentials or tokens leaked)**.

---

## 3. Repository Provenance & Git Status

- **Current Commit:** `cbc5ae5e78f0ca37f6129a7fb50d49e5581d213b`
- **Current Branch:** `remediation/reproducible-evaluation`
- **Working Tree State:** Clean preservation of all untracked artifacts and working files.
- **Unit Test Baseline:** 649 / 649 passed (`pytest tests/`).

---

## 4. Live Stack Health & Isolation Audit

### Container Inventory Verification
All 14 containers were verified via `podman ps -a --filter name=rift-`:

| Container Name | Image | Status | Published Ports (Loopback Only) | NetNS PID |
| :--- | :--- | :--- | :--- | :--- |
| `rift-redis-cart` | `docker.io/library/redis:alpine` | **Up 11 min** | `6379/tcp` | `1104693` |
| `rift-otel-collector` | `docker.io/otel/opentelemetry-collector-contrib:0.98.0` | **Up 11 min** | `127.0.0.1:14317->4317/tcp`, `127.0.0.1:18888->8888/tcp` | `1104771` |
| `rift-prometheus` | `quay.io/prometheus/prometheus:v2.51.0` | **Up 11 min** | `127.0.0.1:19090->9090/tcp` | `1104859` |
| `rift-emailservice` | `gcr.io/google-samples/microservices-demo/emailservice:v0.8.1` | **Up 7 min** | `8080/tcp` | `1105221` |
| `rift-paymentservice` | `gcr.io/google-samples/microservices-demo/paymentservice:v0.8.1` | **Up 7 min** | `50051/tcp` | `1105297` |
| `rift-shippingservice` | `gcr.io/google-samples/microservices-demo/shippingservice:v0.8.1` | **Up 7 min** | `50051/tcp` | `1105370` |
| `rift-currencyservice` | `gcr.io/google-samples/microservices-demo/currencyservice:v0.8.1` | **Up 7 min** | `7000/tcp` | `1105442` |
| `rift-productcatalogservice` | `gcr.io/google-samples/microservices-demo/productcatalogservice:v0.8.1` | **Up 7 min** | `3550/tcp` | `1105513` |
| `rift-cartservice` | `gcr.io/google-samples/microservices-demo/cartservice:v0.8.1` | **Up 7 min** | `7070/tcp` | `1105581` |
| `rift-recommendationservice` | `gcr.io/google-samples/microservices-demo/recommendationservice:v0.8.1` | **Up 7 min** | `8080/tcp` | `1105649` |
| `rift-checkoutservice` | `gcr.io/google-samples/microservices-demo/checkoutservice:v0.8.1` | **Up 7 min** | `5050/tcp` | `1105716` |
| `rift-adservice` | `gcr.io/google-samples/microservices-demo/adservice:v0.8.1` | **Up 7 min** | `9555/tcp` | `1105791` |
| `rift-frontend` | `gcr.io/google-samples/microservices-demo/frontend:v0.8.1` | **Up 7 min** | `127.0.0.1:18080->8080/tcp` | `1105908` |
| `rift-loadgenerator` | `gcr.io/google-samples/microservices-demo/loadgenerator:v0.8.1` | **Up 7 min** | Internal traffic generator | `1105979` |

### Host Resource Headroom
- **Total Memory:** $15.7\text{ GiB}$
- **Used Memory:** $11.5\text{ GiB}$ (Container stack overhead $\approx 310\text{ MiB}$)
- **Available RAM:** $4.19\text{ GiB}$ ($\ge 2.0\text{ GiB}$ safety threshold satisfied)
- **Host Load Average:** $0.39, 0.53, 0.50$ ($\le 4.0$ safety threshold satisfied)
- **Disk Free:** $182\text{ GiB}$ ($\ge 20\text{ GiB}$ safety threshold satisfied)

### Existing Workload Coexistence
- `bobz-understand` container: Healthy (conmon PID `78648`).
- `supervisord` / `aakash` Java/OrientDB/SQL Server processes: Unaltered and operational.

---

## 5. Telemetry Pipeline Deep-Dive & Root-Cause Diagnosis

### A. Trace Reception Audit (Microservice $\rightarrow$ OTel Collector)
Direct inspection of container logs and source strings revealed that Google Online Boutique v0.8.1 microservices gate OTLP trace initialization behind an explicit environment check:

```javascript
// paymentservice/index.js
if (process.env.ENABLE_TRACING == "1") {
  console.log("Tracing enabled.");
  const provider = new NodeTracerProvider(...);
  provider.addSpanProcessor(new SimpleSpanProcessor(new OTLPTraceExporter({url: collectorUrl})));
} else {
  console.log("Tracing disabled.");
}
```

```python
# emailservice/email_server.py
if os.environ.get("ENABLE_TRACING") == "1":
  otel_endpoint = os.getenv("COLLECTOR_SERVICE_ADDR", "localhost:4317")
  trace.set_tracer_provider(TracerProvider())
  ...
else:
  logger.info("Tracing disabled.")
```

**Diagnostic Finding:** Because `ENABLE_TRACING=1` is not set in the active container environment definitions, all microservices run with tracing disabled. The OpenTelemetry Collector OTLP gRPC receiver (`0.0.0.0:4317`) received $0$ span packets.

### B. Spanmetrics Generation Audit
The Collector configuration ([`deploy/otel-collector.yaml`](deploy/otel-collector.yaml)) specifies:
```yaml
connectors:
  spanmetrics:
    histogram:
      explicit:
        buckets: [2ms, 5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1000ms, 2500ms, 5000ms]
    dimensions:
      - name: http.status_code
      - name: rpc.grpc.status_code
```
Because $0$ spans pass through the `traces` pipeline, the `spanmetrics` connector produces $0$ time-series metrics to the Prometheus exporter on port `8889`.

### C. Prometheus Scrape Target Audit
Prometheus `/api/v1/targets` returned:
1. `job: rift-otel-spanmetrics` (`http://rift-otel-collector:8889/metrics`):
   - **Health:** `UP`
   - **Scrape Status:** Success ($0.0015\text{s}$ duration)
   - **Samples Scraped:** `0` (Exposing only standard scrape metadata: `up`, `scrape_duration_seconds`, etc.)
2. `job: rift-frontend` (`http://rift-frontend:8080/metrics`):
   - **Health:** `DOWN`
   - **Error:** `server returned HTTP status 404 Not Found` (Online Boutique frontend v0.8.1 does not serve a Prometheus `/metrics` endpoint on port 8080).

### D. Per-Service Telemetry Coverage Matrix

| Service Name | Container Running | Trace Exporter Configured | Telemetry Emitted | Prometheus Series | Observability Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `frontend` | **Yes** | `ENABLE_TRACING` missing | No | 0 | **UNOBSERVED** |
| `cartservice` | **Yes** | `ENABLE_TRACING` missing | No | 0 | **UNOBSERVED** |
| `productcatalogservice` | **Yes** | `ENABLE_TRACING` missing | No | 0 | **UNOBSERVED** |
| `currencyservice` | **Yes** | `ENABLE_TRACING` missing | No | 0 | **UNOBSERVED** |
| `paymentservice` | **Yes** | `ENABLE_TRACING` missing | No | 0 | **UNOBSERVED** |
| `shippingservice` | **Yes** | `ENABLE_TRACING` missing | No | 0 | **UNOBSERVED** |
| `emailservice` | **Yes** | `ENABLE_TRACING` missing | No | 0 | **UNOBSERVED** |
| `checkoutservice` | **Yes** | `ENABLE_TRACING` missing | No | 0 | **UNOBSERVED** |
| `recommendationservice` | **Yes** | `ENABLE_TRACING` missing | No | 0 | **UNOBSERVED** |
| `adservice` | **Yes** | `ENABLE_TRACING` missing | No | 0 | **UNOBSERVED** |
| `redis-cart` | **Yes** | Standalone Redis | N/A | 0 | **UNOBSERVED** |

---

## 6. RIFT Ingestion Compatibility Analysis

Inspection of [`src/rift/pipeline/e2e_runner.py`](src/rift/pipeline/e2e_runner.py:101) identified the active PromQL queries used by RIFT:
```python
_METRIC_QUERIES = {
    "lat_p99": (
        "histogram_quantile(0.99, "
        "sum(rate(grpc_server_handling_seconds_bucket"
        '{{job=~"{service}"}}[1m])) by (le))'
    ),
    "rps": (
        "sum(rate(grpc_server_started_total"
        '{{job=~"{service}"}}[1m]))'
    ),
    "err_rate": (
        "sum(rate(grpc_server_handled_total"
        '{{job=~"{service}",grpc_code!="OK"}}[1m])) / '
        "sum(rate(grpc_server_handled_total"
        '{{job=~"{service}"}}[1m]))'
    ),
}
```

### Incompatibility Summary:
1. **Metric Name Mismatch:** The queries reference direct gRPC server metrics (`grpc_server_handling_seconds_bucket`), whereas OTel Collector `spanmetrics` produces metrics prefixed with `rift_` (e.g., `rift_latency_bucket`, `rift_calls_total`).
2. **Label Selector Mismatch:** The queries select on `{job=~"{service}"}`, whereas OTel `spanmetrics` labels time series with `{service_name=~"{service}"}`.
3. **Ingestion Behavior:** When queried, `PrometheusClient.collect()` returns empty DataFrames for all services without throwing an exception, as designed, preventing pipeline crashes but confirming zero live metric ingestion.

---

## 7. Baseline Observation Status

- **Observation Window:** 10 minutes of active benchmark execution under `rift-loadgenerator` (10 concurrent users).
- **Traffic Observed:** $> 900$ completed HTTP transactions at frontend ($100\%$ HTTP 200/302 responses, $0\%$ HTTP 5xx errors).
- **Metric Time-Series Captured:** $0$ Prometheus time-series samples recorded due to the upstream tracing flag blocker.
- **Data Quality Assessment:** Cannot compute statistical stability or latency distribution metrics until the telemetry pipeline emits genuine spanmetrics.

---

## 8. Prescribed Remediation Requirements (For Future Authorized Sprint)

To transition from **PARTIALLY VALIDATED** to **STAGE 3 COMPLETE**, the following targeted remediations must be approved and executed:

1. **Manifest Environment Update:** Add `ENABLE_TRACING: "1"` to all 10 Online Boutique microservice service definitions in [`deploy/podman-compose.yaml`](deploy/podman-compose.yaml).
2. **Prometheus Scrape Configuration:** Remove the non-existent direct `rift-frontend:8080/metrics` target from [`deploy/prometheus.yml`](deploy/prometheus.yml).
3. **RIFT PromQL Reconciliation:** Update [`src/rift/pipeline/e2e_runner.py`](src/rift/pipeline/e2e_runner.py:101) `PrometheusClient._METRIC_QUERIES` to query OTel spanmetrics format:
   ```python
   "lat_p99": (
       "histogram_quantile(0.99, "
       "sum(rate(rift_latency_bucket"
       '{{service_name=~"{service}"}}[1m])) by (le))'
   ),
   "rps": (
       "sum(rate(rift_calls_total"
       '{{service_name=~"{service}"}}[1m]))'
   ),
   ```
4. **Baseline Re-Run:** Execute a 30-minute observational capture to record genuine multi-service latency distributions under fault-free load.

---

## 9. Final Decision & Stage 4 Eligibility

```
===============================================================================
                     STAGE 3 VALIDATION DECISION
===============================================================================
  Target Host & Infrastructure:             VERIFIED & HEALTHY
  Container Stack (14 containers):          UP (0 FAULTS, 0 IMPAIRMENTS)
  Host Resource Safety:                     COMPLIANT (4.19 GiB AVAILABLE RAM)
  Existing IBM Workloads:                   COMPLIANT (ZERO INTERFERENCE)
  Telemetry Flow:                           BLOCKED (ENABLE_TRACING=1 REQUIRED)
  Prometheus Ingestion:                     BLOCKED (METRIC SCHEMA RECONCILIATION)
-------------------------------------------------------------------------------
  FINAL VERDICT:                            PARTIALLY VALIDATED
  STAGE 4 ELIGIBILITY:                      NOT ELIGIBLE UNTIL REMEDIATION APPROVED
===============================================================================
```
