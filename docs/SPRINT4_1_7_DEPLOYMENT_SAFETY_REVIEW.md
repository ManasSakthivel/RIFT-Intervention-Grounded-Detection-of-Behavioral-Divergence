# RIFT Sprint 4.1.7 — Deployment Safety & Workload Isolation Review

**Review Date:** 2026-11-02  
**Target Milestone:** Stage 2 Isolated Stack Deployment Safety Audit  
**Target Host:** Linux QA VM (`9.30.57.225:22` / `wca4z-understand-dp1.fyre.ibm.com`)  
**Execution Context:** LOCAL-ONLY AUDIT & MANIFEST INSPECTION (Zero Remote VM Access / Zero State Changes)  
**Repository Root:** `/Users/manassakthivel/Desktop/RIFT FINAL`  

---

## 1. Executive Summary & Verdict

An independent, evidence-driven deployment safety review of RIFT's containerized infrastructure was conducted prior to requesting stakeholder authorization for **Stage 2: Isolated Stack Deployment Without Fault Injection**.

### Final Audit Verdict:
### **READY TO REQUEST EXPLICIT STAGE 2 AUTHORIZATION**

> **Authorization Boundary:** This verdict confirms that the proposed container stack in `deploy/podman-compose.yaml` is non-privileged, strictly bound to loopback interfaces (`127.0.0.1`), network-isolated on a private bridge (`rift-net`), and capped at $2560\text{ MiB}$ ($2.50\text{ GiB}$) RAM, leaving ample headroom for host workloads. **This document does NOT authorize deployment or remote connection; operational execution requires explicit stakeholder sign-off.**

---

## 2. Exact Repository Provenance & Test Verification

```
┌─────────────────────────────────┬─────────────────────────────────────────────────────────────┐
│ Repository Property             │ Verified Value                                              │
├─────────────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Current Working Branch          │ remediation/reproducible-evaluation                         │
│ Head Commit                     │ cbc5ae5 fix: correct broken docs/limitations.md link in ... │
│ Modified Tracked Files          │ 9 files (EBD, FCI, Linux tc backend, Safety, live config)   │
│ Staged Changes                  │ None (git diff --cached is empty)                           │
│ Test Suite Execution            │ pytest -> 649 passed / 0 failed (13.96s execution time)     │
└─────────────────────────────────┴─────────────────────────────────────────────────────────────┘
```

### Audit of Untracked Test Files
1. [`tests/unit/test_sprint2_semidirected.py`](tests/unit/test_sprint2_semidirected.py): 5/5 passed. Validates semi-directed reachability (`allow_semi_directed=True`) for PAG graphs and EBD Criterion R3.
2. [`tests/unit/test_telemetry_manifest_remediation.py`](tests/unit/test_telemetry_manifest_remediation.py): 4/4 passed. Validates YAML syntax of manifests in `deploy/`, loopback bindings, and zero silent data imputation in the Normalizer.
3. [`tests/unit/test_watchdog_remediation.py`](tests/unit/test_watchdog_remediation.py): 4/4 passed. Validates `DetachedRollbackWatchdog`, `setsid()` process detachment (`start_new_session=True`), and safety limits ($\le 30.0\text{s}$, PID $>1$).

---

## 3. Complete Service & Container Inventory

Inspecting [`deploy/podman-compose.yaml`](deploy/podman-compose.yaml:1) confirms an inventory of **exactly 14 containers**:

```
┌──────────────────────────────┬──────────────────────────────────────────────────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ Container Name               │ Image Reference                                          │ Internal Port│ Host Port    │ Memory Limit │ CPU Quota    │
├──────────────────────────────┼──────────────────────────────────────────────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ rift-frontend                │ gcr.io/google-samples/microservices-demo/frontend:v0.8.1 │ 8080/tcp     │ 127.0.0.1:18080│ 256 MiB    │ 0.5 Cores    │
│ rift-cartservice             │ gcr.io/google-samples/microservices-demo/cartservice:v0.8.1│ 7070/tcp   │ None         │ 128 MiB      │ 0.25 Cores   │
│ rift-productcatalogservice   │ gcr.io/google-samples/microservices-demo/productcatalogservice:v0.8.1│ 3550/tcp│ None     │ 128 MiB      │ 0.25 Cores   │
│ rift-currencyservice         │ gcr.io/google-samples/microservices-demo/currencyservice:v0.8.1│ 7000/tcp│ None         │ 128 MiB      │ 0.25 Cores   │
│ rift-paymentservice          │ gcr.io/google-samples/microservices-demo/paymentservice:v0.8.1│ 50051/tcp│ None        │ 128 MiB      │ 0.25 Cores   │
│ rift-shippingservice         │ gcr.io/google-samples/microservices-demo/shippingservice:v0.8.1│ 50051/tcp│ None        │ 128 MiB      │ 0.25 Cores   │
│ rift-emailservice            │ gcr.io/google-samples/microservices-demo/emailservice:v0.8.1│ 8080/tcp  │ None         │ 128 MiB      │ 0.25 Cores   │
│ rift-checkoutservice         │ gcr.io/google-samples/microservices-demo/checkoutservice:v0.8.1│ 5050/tcp│ None         │ 128 MiB      │ 0.25 Cores   │
│ rift-recommendationservice   │ gcr.io/google-samples/microservices-demo/recommendationservice:v0.8.1│ 8080/tcp│ None     │ 128 MiB      │ 0.25 Cores   │
│ rift-adservice               │ gcr.io/google-samples/microservices-demo/adservice:v0.8.1│ 9555/tcp     │ None         │ 256 MiB      │ 0.5 Cores    │
│ rift-redis-cart              │ docker.io/library/redis:alpine                           │ 6379/tcp     │ None         │ 128 MiB      │ 0.25 Cores   │
│ rift-loadgenerator           │ gcr.io/google-samples/microservices-demo/loadgenerator:v0.8.1│ None     │ None         │ 256 MiB      │ 0.5 Cores    │
│ rift-otel-collector          │ docker.io/otel/opentelemetry-collector-contrib:0.98.0    │ 4317, 8889   │ 127.0.0.1:18888, 14317 │ 128 MiB │ 0.25 Cores │
│ rift-prometheus              │ quay.io/prometheus/prometheus:v2.51.0                    │ 9090/tcp     │ 127.0.0.1:19090│ 512 MiB    │ 0.5 Cores    │
├──────────────────────────────┼──────────────────────────────────────────────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ TOTAL RESOURCE ALLOCATION    │ 14 Containers                                            │              │ 4 Host Ports │ 2560 MiB (2.50 GiB) │ 4.5 Cores    │
└──────────────────────────────┴──────────────────────────────────────────────────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

---

## 4. Network Exposure & Isolation Analysis

1. **Private Subnet:** Dedicated bridge network `rift-net` (`10.89.100.0/24`, gateway `10.89.100.1`).
2. **Subnet Conflict Audit:** Disjoint from existing Podman networks (`bobz` 10.89.1.0/24, `wca4z` 10.89.0.0/24, `podman` 10.88.0.0/16) and host routes (`10.11.x.x`–`10.19.x.x`, `9.30.56.0/23`).
3. **Loopback Port Binding:** All 4 exposed host ports bind strictly to `127.0.0.1:`:
   - `127.0.0.1:18080:8080` (Frontend Web UI)
   - `127.0.0.1:19090:9090` (Prometheus Web & API)
   - `127.0.0.1:18888:8888` (OTel Collector Health)
   - `127.0.0.1:14317:4317` (OTel Collector gRPC receiver)
4. **Zero Public Interface Binding:** No ports bind to `0.0.0.0` or public interface `eth1` (`9.30.57.225`).
5. **Zero Interference with Host Workloads:** No overlap with active `bobz-understand` ports (`1433`, `1434`, `1431`, `2424`, `4001`, `8081`, `9443`, `9444`).

---

## 5. Privilege & Mount Audit

* **`privileged: true`:** **0 of 14 containers**. No container runs in privileged mode.
* **Linux Capabilities:** No elevated capabilities (`CAP_SYS_ADMIN`, `CAP_NET_ADMIN`, etc.) are granted to any container in Stage 2.
* **Host Namespace Sharing:** `pid: host`, `network_mode: host`, and `ipc: host` are **strictly omitted**.
* **Host Volume Mounts:**
  - `deploy/otel-collector.yaml -> /etc/otelcol-contrib/config.yaml:ro` (Read-only configuration file)
  - `deploy/prometheus.yml -> /etc/prometheus/prometheus.yml:ro` (Read-only configuration file)
  - Zero mounts of `/`, `/proc`, `/sys`, `/dev`, or Podman/Docker runtime sockets.

---

## 6. Image Provenance & Supply-Chain Assessment

* **Images Referenced:**
  - Google Online Boutique demo: `gcr.io/google-samples/microservices-demo/*:v0.8.1`
  - OpenTelemetry Collector Contrib: `docker.io/otel/opentelemetry-collector-contrib:0.98.0`
  - Prometheus: `quay.io/prometheus/prometheus:v2.51.0`
  - Redis: `docker.io/library/redis:alpine`
* **Provenance Status:** All images originate from official, well-maintained public repositories (Google Cloud, OpenTelemetry, Prometheus, Docker Official Library).
* **Supply-Chain Recommendation:** While version tags are fixed, SHA256 immutable digest pinning should be applied as an operational best-practice prior to air-gapped staging.

---

## 7. Resource Budget & Abort Thresholds

```
┌──────────────────────────────┬─────────────────────────────┬────────────────────────────────────────────────────────┐
│ Resource Attribute           │ Value / Limit               │ Abort Threshold Condition                              │
├──────────────────────────────┼─────────────────────────────┼────────────────────────────────────────────────────────┤
│ Total Memory Cap             │ 2560 MiB (2.50 GiB)         │ Abort if host free RAM drops below 1.5 GiB             │
│ CPU Limit (Aggregate)        │ 4.5 Cores (burst cap)       │ Abort if host load average exceeds 8.0                 │
│ Ephemeral Disk Space         │ < 2.0 GiB                   │ Abort if host free disk drops below 20.0 GiB           │
│ Background Host Headroom     │ > 2.1 GiB preserved         │ Abort if bobz-understand ports report connection error │
└──────────────────────────────┴─────────────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 8. Rollback & Teardown Protocol

Stage 2 rollback operates strictly on RIFT-owned resources:
```bash
# 1. Stop and remove RIFT containers
podman compose -f deploy/podman-compose.yaml down -v

# 2. Verify complete teardown (Must return 0 listeners)
ss -tulpn | grep -E ':(18080|19090|18888|14317)\b'
```
*Isolation Guarantee:* Teardown leaves all non-RIFT containers (`bobz-understand`) and networks (`bobz`, `wca4z`, `podman`) completely untouched.

---

## 9. Stage 2 Acceptance Gate Matrix

```
┌──────────────────────────────────────┬────────────────────────────────────────┬──────────────────────────────────┐
│ Acceptance Gate                      │ Status                                 │ Evaluation Rationale             │
├──────────────────────────────────────┼────────────────────────────────────────┼──────────────────────────────────┤
│ 1. Repository Provenance             │ PASS — VERIFIED LOCALLY                │ Commit cbc5ae5, 649 tests pass   │
│ 2. Manifest Completeness             │ PASS — VERIFIED LOCALLY                │ 14 containers fully inventoried  │
│ 3. Image Provenance                  │ PASS — VERIFIED LOCALLY                │ Official repos, version tags     │
│ 4. Network Isolation                 │ PASS — VERIFIED LOCALLY                │ rift-net (10.89.100.0/24)        │
│ 5. Port Safety                       │ PASS — VERIFIED BY ENV EVIDENCE        │ 18080/19090 loopback verified    │
│ 6. Privileges & Mounts               │ PASS — VERIFIED LOCALLY                │ Zero privileged, 2 :ro mounts    │
│ 7. Resource Budget & Headroom        │ PASS — VERIFIED LOCALLY                │ 2.50 GiB cap vs 4.6 GiB free     │
│ 8. Telemetry Consistency             │ PASS — VERIFIED LOCALLY                │ OTel spanmetrics -> Prometheus   │
│ 9. Rollback & Teardown               │ PASS — VERIFIED LOCALLY                │ Targeted podman compose down -v  │
│ 10. Existing Workload Protection     │ PASS — VERIFIED BY ENV EVIDENCE        │ Zero port/subnet collisions      │
│ 11. Stakeholder Authorization        │ NOT APPLICABLE                         │ Awaiting stakeholder review      │
│ 12. Runtime Verification             │ NOT VERIFIED (PENDING STAGE 2)         │ Requires authorized deployment   │
└──────────────────────────────────────┴────────────────────────────────────────┴──────────────────────────────────┘
```

---

## 10. Final Assessment & Next Steps

### Verdict: **READY TO REQUEST EXPLICIT STAGE 2 AUTHORIZATION**

* **Audit Conclusion:** The deployment manifests in `deploy/` satisfy all isolation, safety, resource, and privilege boundaries.
* **Next Action:** Present this report and [`docs/SPRINT4_1_5_LIVE_VALIDATION_READINESS_RUNBOOK.md`](docs/SPRINT4_1_5_LIVE_VALIDATION_READINESS_RUNBOOK.md) to the project stakeholder for explicit authorization of Stage 2 (Isolated Stack Deployment Without Fault Injection).
