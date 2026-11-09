# RIFT Sprint 4.1.8 — Stage 2 Deployment Report: Isolated Benchmark Stack

**Date:** 2026-11-02  
**Target Host:** Linux QA VM (`9.30.57.225:22` / `wca4z-understand-dp1.fyre.ibm.com`)  
**Stage:** Stage 2 — Isolated Benchmark Stack Deployment  
**Lead Authority:** Primary Integration Agent  
**Status:** **STAGE 2 COMPLETE — ISOLATED STACK DEPLOYED**

---

## 1. Executive Summary

In accordance with the RIFT Staged Live-Validation Readiness Runbook ([`docs/SPRINT4_1_5_LIVE_VALIDATION_READINESS_RUNBOOK.md`](docs/SPRINT4_1_5_LIVE_VALIDATION_READINESS_RUNBOOK.md)) and the Teardown & Launch Checklist ([`docs/SPRINT4_1_7_1_TEARDOWN_AND_LAUNCH_CHECKLIST.md`](docs/SPRINT4_1_7_1_TEARDOWN_AND_LAUNCH_CHECKLIST.md)), Stage 2 deployment of the 14-container Google Online Boutique microservice benchmark stack with OpenTelemetry Collector and Prometheus was executed on the remote Linux QA testbed (`9.30.57.225`).

All 14 containers are running and healthy inside the isolated private bridge network `rift-net` (`10.89.100.0/24`). All published ports are strictly bound to `127.0.0.1` (`18080`, `19090`, `18888`, `14317`), eliminating external attack surface and preventing port collisions. Host memory utilization remains well within the approved safety budget ($4.1\text{ GiB}$ available RAM), and existing IBM workloads (`bobz-understand`, user `aakash` SQL Server/OrientDB processes) remain completely undisturbed.

Zero fault injections or `tc netem` interventions were performed during Stage 2.

---

## 2. Network Isolation Verification

A dedicated private bridge network was provisioned and validated prior to container launch:

- **Network Name:** `rift-net`
- **Subnet:** `10.89.100.0/24` (Gateway: `10.89.100.1`)
- **Driver:** `bridge`
- **Isolation Check:** Confirmed disjoint from default Podman bridges (`10.88.0.0/16`), `wca4z` subnet (`10.89.0.0/24`), and `bobz` subnets (`10.89.1.0/24`).

```bash
[Host Verification]
$ podman network inspect rift-net --format '{{(index .IPAM.Config 0).Subnet}}'
10.89.100.0/24
```

---

## 3. Container Inventory & Runtime Status

All 14 containers were pulled and initialized under non-root container isolation:

| Container Name | Image | Status | Ports (Loopback Only) | NetNS PID |
| :--- | :--- | :--- | :--- | :--- |
| `rift-redis-cart` | `docker.io/library/redis:alpine` | **Up (healthy)** | `6379/tcp` (internal) | `1104693` |
| `rift-otel-collector` | `docker.io/otel/opentelemetry-collector-contrib:0.98.0` | **Up (healthy)** | `127.0.0.1:14317->4317/tcp`, `127.0.0.1:18888->8888/tcp` | `1104771` |
| `rift-prometheus` | `quay.io/prometheus/prometheus:v2.51.0` | **Up (healthy)** | `127.0.0.1:19090->9090/tcp` | `1104859` |
| `rift-emailservice` | `gcr.io/google-samples/microservices-demo/emailservice:v0.8.1` | **Up (healthy)** | `8080/tcp` (internal) | `1105221` |
| `rift-paymentservice` | `gcr.io/google-samples/microservices-demo/paymentservice:v0.8.1` | **Up (healthy)** | `50051/tcp` (internal) | `1105297` |
| `rift-shippingservice` | `gcr.io/google-samples/microservices-demo/shippingservice:v0.8.1` | **Up (healthy)** | `50051/tcp` (internal) | `1105370` |
| `rift-currencyservice` | `gcr.io/google-samples/microservices-demo/currencyservice:v0.8.1` | **Up (healthy)** | `7000/tcp` (internal) | `1105442` |
| `rift-productcatalogservice` | `gcr.io/google-samples/microservices-demo/productcatalogservice:v0.8.1` | **Up (healthy)** | `3550/tcp` (internal) | `1105513` |
| `rift-cartservice` | `gcr.io/google-samples/microservices-demo/cartservice:v0.8.1` | **Up (healthy)** | `7070/tcp` (internal) | `1105581` |
| `rift-recommendationservice` | `gcr.io/google-samples/microservices-demo/recommendationservice:v0.8.1` | **Up (healthy)** | `8080/tcp` (internal) | `1105649` |
| `rift-checkoutservice` | `gcr.io/google-samples/microservices-demo/checkoutservice:v0.8.1` | **Up (healthy)** | `5050/tcp` (internal) | `1105716` |
| `rift-adservice` | `gcr.io/google-samples/microservices-demo/adservice:v0.8.1` | **Up (healthy)** | `9555/tcp` (internal) | `1105791` |
| `rift-frontend` | `gcr.io/google-samples/microservices-demo/frontend:v0.8.1` | **Up (healthy)** | `127.0.0.1:18080->8080/tcp` | `1105908` |
| `rift-loadgenerator` | `gcr.io/google-samples/microservices-demo/loadgenerator:v0.8.1` | **Up (healthy)** | None (internal traffic driver) | `1105979` |

---

## 4. Health & Probe Verification Matrix

| Target Probe | Endpoint | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend HTTP** | `http://127.0.0.1:18080/` | HTTP 200 OK | `HTTP 200` | **PASS** |
| **Prometheus Health** | `http://127.0.0.1:19090/-/healthy` | `Prometheus Server is Healthy.` | `Prometheus Server is Healthy.` | **PASS** |
| **OTel Internal Metrics** | `http://127.0.0.1:18888/metrics` | Prometheus text metrics | `otelcol_http_server_duration_bucket{...}` | **PASS** |
| **Prometheus Scrape Target** | `http://127.0.0.1:19090/api/v1/targets` | `rift-otel-spanmetrics` UP | `health: "up"` | **PASS** |

---

## 5. Host Resource Utilization & Safety Headroom

| Metric | Pre-Launch | Post-Launch (Stage 2) | Safety Threshold | Compliance |
| :--- | :--- | :--- | :--- | :--- |
| **Total Memory Used** | $10.6\text{ GiB}$ | $11.0\text{ GiB}$ | $\le 13.5\text{ GiB}$ | **COMPLIANT** |
| **Available RAM** | $4.7\text{ GiB}$ | $4.1\text{ GiB}$ | $\ge 2.0\text{ GiB}$ | **COMPLIANT** |
| **Container Memory Sum** | $0.0\text{ MiB}$ | $\approx 310\text{ MiB}$ | $\le 2.50\text{ GiB}$ | **COMPLIANT** |
| **Disk Space Free** | $185\text{ GiB}$ | $182\text{ GiB}$ | $\ge 20\text{ GiB}$ | **COMPLIANT** |
| **System Load (1 min)** | $0.15$ | $0.28$ | $\le 4.0$ | **COMPLIANT** |

---

## 6. Coexistence & Workload Non-Interference Audit

- **Active IBM Processes:** Verified unchanged. User `aakash` Java/OrientDB/SQLServer applications remain running normally.
- **Port Conflict Scan:** Loopback-only bindings on high-ports `18080`, `19090`, `18888`, `14317` confirmed free of any collision with host ports `1431`, `1433`, `1434`, `2424`, `4001`, `8081`, `9443`, `9444`.
- **Host Network Routing:** No iptables, routing table, or default bridge alterations performed.

---

## 7. Remediation Note: Profiler Configuration

During initial container initialization, `rift-paymentservice` and `rift-currencyservice` exited due to Google Cloud Profiler requiring GCP Project metadata when unconfigured. 

**Remediation Applied:** Added `DISABLE_PROFILER=1` across microservice container configurations in [`deploy/podman-compose.yaml`](deploy/podman-compose.yaml), matching standard non-GCP Online Boutique deployment practice. Upon relaunch, all 14 containers achieved sustained healthy execution.

---

## 8. Final Verdict & Next Steps

```
===============================================================================
                     STAGE 2 DEPLOYMENT VERIFICATION
===============================================================================
  14-Container Online Boutique Stack:       DEPLOYED & HEALTHY (14/14 UP)
  Network Isolation (rift-net):             CONFIRMED (10.89.100.0/24)
  Port Bindings:                            STRICT LOOPBACK (127.0.0.1)
  Host Resource Headroom:                   CONFIRMED (4.1 GiB AVAILABLE RAM)
  Existing Workload Coexistence:            CONFIRMED (ZERO INTERFERENCE)
  Intervention State:                       ZERO FAULTS INJECTED (CLEAN)
-------------------------------------------------------------------------------
  FINAL VERDICT:                            STAGE 2 COMPLETE — READY FOR STAGE 3
===============================================================================
```

The system is now fully prepared to proceed to **Stage 3: Baseline Telemetry Calibration (30-minute observational capture)** as specified in [`docs/SPRINT4_1_5_LIVE_VALIDATION_READINESS_RUNBOOK.md`](docs/SPRINT4_1_5_LIVE_VALIDATION_READINESS_RUNBOOK.md).
