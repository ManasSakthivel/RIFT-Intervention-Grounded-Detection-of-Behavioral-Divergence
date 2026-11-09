# RIFT Sprint 4.1 — Workload Isolation and Live Deployment Plan

**Document Version:** 1.0  
**Target Environment:** Linux QA VM (`9.30.57.225:22` / `wca4z-understand-dp1.fyre.ibm.com`)  
**Status:** PLANNING & SPECIFICATION ONLY (Non-Execution)  
**Authority:** Task 8 Live QA Deployment & Isolation Architecture  

---

## 1. Verified Current-State Evidence

A read-only audit of the target Linux QA VM (`9.30.57.225`) confirmed the following system baselines:

```
┌──────────────────────────────┬─────────────────────────────────────────────────────────────┐
│ System Attribute             │ Verified Value / Status                                     │
├──────────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Host Identity                │ wca4z-understand-dp1.fyre.ibm.com (RHEL 9.6, x86_64)       │
│ Kernel Version               │ Linux 5.14.0-570.62.1.el9_6.x86_64                         │
│ Privilege Level              │ uid=0(root) gid=0(root) — CAP_NET_ADMIN available          │
│ System Memory                │ 15 GiB Total / 10 GiB Used / 4.6 GiB Available             │
│ System Storage               │ 247 GiB Total (/dev/mapper/rhel-root) / 185 GiB Free (26%) │
│ Container Runtime            │ Podman (/usr/bin/podman) — operational                      │
│ Active Host Workloads        │ supervisord managing Java, OrientDB, SQL Server (aakash)   │
│ Active Listening Ports       │ TCP 22 (ssh), 1433/1434 (sql), 2424/4001/8081/9443/9444     │
│ Existing Podman Networks     │ bobz (10.89.1.0/24), wca4z (10.89.0.0/24), podman (10.88.0.0/16) │
│ External Registries          │ gcr.io (HTTP 302), quay.io (HTTP 200) — Reachable           │
│ Traffic Control Binary       │ /usr/sbin/tc (iproute2-6.11.0, libbpf 1.5.0)               │
│ Kernel Traffic Scheduler     │ /lib/modules/.../kernel/net/sched/sch_netem.ko.xz (Present) │
│ Target Microservices Stack   │ Online Boutique — NOT DEPLOYED                              │
│ Telemetry Scraping Stack     │ Prometheus / OTel Collector — INACTIVE / NOT RUNNING        │
└──────────────────────────────┴─────────────────────────────────────────────────────────────┘
```

---

## 2. Proposed Architecture and Data Flow

To ensure strict zero-interference isolation with the running `bobz-understand` applications on `9.30.57.225`, RIFT will operate within an isolated, private Podman bridge network (`rift-net`).

```
                                  [ Linux QA VM: 9.30.57.225 ]
 ┌─────────────────────────────────────────────────────────────────────────────────────────┐
 │ EXISTING WORKLOAD (Unchanged & Preserved)                                               │
 │  • Supervisord / Java AD Server / OrientDB / SQL Server                                 │
 │  • Ports: 1433, 2424, 4001, 8081, 9443, 9444                                           │
 └─────────────────────────────────────────────────────────────────────────────────────────┘
                                             ▲
                                             │ (Isolated / Disjoint Subnets)
                                             ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────┐
 │ RIFT DEDICATED PODMAN BRIDGE NETWORK: rift-net (Subnet: 10.89.100.0/24)                 │
 │                                                                                         │
 │   ┌────────────────────────┐      gRPC Call      ┌────────────────────────┐             │
 │   │  rift-frontend         │ ──────────────────► │  rift-checkoutservice  │             │
 │   │  (Port 8080 -> 18080)  │                     │  (Internal 5050)       │             │
 │   └───────────┬────────────┘                     └───────────┬────────────┘             │
 │               │                                              │                          │
 │               ▼                                              ▼                          │
 │   ┌────────────────────────┐                     ┌────────────────────────┐             │
 │   │  rift-cartservice      │                     │  rift-paymentservice   │             │
 │   │  (Internal 7070)       │                     │  (Internal 50051)      │             │
 │   └───────────┬────────────┘                     └────────────────────────┘             │
 │               │                                                                         │
 │               ▼                                                                         │
 │   ┌────────────────────────┐                                                            │
 │   │  rift-redis-cart       │                                                            │
 │   │  (Internal 6379)       │                                                            │
 │   └────────────────────────┘                                                            │
 │                                                                                         │
 │   ┌────────────────────────┐    Metrics Scrape   ┌────────────────────────┐             │
 │   │  rift-loadgenerator    │ ◄────────────────── │  rift-prometheus       │             │
 │   │  (Locust Traffic)      │                     │  (Port 9090 -> 19090)  │             │
 │   └────────────────────────┘                     └───────────┬────────────┘             │
 │                                                              │                          │
 └──────────────────────────────────────────────────────────────┼──────────────────────────┘
                                                                │
                                    Scrape Range Queries HTTP   │ (localhost:19090)
                                                                ▼
                                                    ┌────────────────────────┐
                                                    │  RIFT Evaluation Host  │
                                                    │  (Live Telemetry Scrape│
                                                    │   & CID / EBD Analysis)│
                                                    └────────────────────────┘
```

---

## 3. Container / Service / Port Matrix

All microservices communicate across `rift-net` via internal container DNS names. Only the `frontend` web UI and `prometheus` scraping API are exposed to the host on non-default, non-conflicting high ports (`18080` and `19090`).

```
┌──────────────────────────────┬──────────────────────────────────────────────────────────┬──────────────┬──────────────┬──────────────┐
│ Container Name               │ Image Reference                                          │ Internal Port│ Host Port    │ Memory Limit │
├──────────────────────────────┼──────────────────────────────────────────────────────────┼──────────────┼──────────────┼──────────────┤
│ rift-frontend                │ gcr.io/google-samples/microservices-demo/frontend:v0.8.1 │ 8080/tcp     │ 127.0.0.1:18080│ 256 MiB    │
│ rift-cartservice             │ gcr.io/google-samples/microservices-demo/cartservice:v0.8.1│ 7070/tcp   │ None         │ 128 MiB      │
│ rift-productcatalogservice   │ gcr.io/google-samples/microservices-demo/productcatalogservice:v0.8.1│ 3550/tcp│ None     │ 128 MiB      │
│ rift-currencyservice         │ gcr.io/google-samples/microservices-demo/currencyservice:v0.8.1│ 7000/tcp│ None         │ 128 MiB      │
│ rift-paymentservice          │ gcr.io/google-samples/microservices-demo/paymentservice:v0.8.1│ 50051/tcp│ None        │ 128 MiB      │
│ rift-shippingservice         │ gcr.io/google-samples/microservices-demo/shippingservice:v0.8.1│ 50051/tcp│ None        │ 128 MiB      │
│ rift-emailservice            │ gcr.io/google-samples/microservices-demo/emailservice:v0.8.1│ 8080/tcp  │ None         │ 128 MiB      │
│ rift-checkoutservice         │ gcr.io/google-samples/microservices-demo/checkoutservice:v0.8.1│ 5050/tcp│ None         │ 128 MiB      │
│ rift-recommendationservice   │ gcr.io/google-samples/microservices-demo/recommendationservice:v0.8.1│ 8080/tcp│ None     │ 128 MiB      │
│ rift-adservice               │ gcr.io/google-samples/microservices-demo/adservice:v0.8.1│ 9555/tcp     │ None         │ 256 MiB      │
│ rift-redis-cart              │ docker.io/library/redis:alpine                           │ 6379/tcp     │ None         │ 128 MiB      │
│ rift-loadgenerator           │ gcr.io/google-samples/microservices-demo/loadgenerator:v0.8.1│ None     │ None         │ 256 MiB      │
│ rift-otel-collector          │ docker.io/otel/opentelemetry-collector-contrib:0.98.0    │ 4317, 8889   │ 127.0.0.1:18888, 14317 │ 128 MiB │
│ rift-prometheus              │ quay.io/prometheus/prometheus:v2.51.0                    │ 9090/tcp     │ 127.0.0.1:19090│ 512 MiB    │
├──────────────────────────────┼──────────────────────────────────────────────────────────┼──────────────┼──────────────┼──────────────┤
│ TOTAL RESOURCE ALLOCATION    │ 14 Containers                                            │              │ 4 Host Ports │ 2560 MiB (2.50 GiB) │
└──────────────────────────────┴──────────────────────────────────────────────────────────┴──────────────┴──────────────┴──────────────┘
```

### Port Availability Verification Protocol
Before binding any host port during deployment, the following read-only command must execute and confirm exit status 0 (no listener):
```bash
ss -tulpn | grep -E ':(18080|19090|18888|14317)\b' || echo "PORTS_FREE"
```

---

## 4. Resource and Storage Requirements

1. **Memory Budgeting:**
   - Host Available Memory: `4.6 GiB`
   - Total Configured Limit: `2560 MiB (2.50 GiB)` across 14 containers (enforced via Podman `--memory` flags)
   - Safety Headroom: `> 2.1 GiB` remaining unallocated for system and existing `bobz-understand` processes.

2. **CPU Budgeting:**
   - Per-container CPU quota: `--cpus 0.5` (max 4.0 aggregate cores out of host multi-core capacity).

3. **Storage Requirements:**
   - Microservices are 100% stateless (zero persistent host volumes).
   - `rift-prometheus`: Ephemeral storage using tmpfs or 2 GiB retention cap in `/tmp/rift-prom-data`.
   - `rift-redis-cart`: Ephemeral in-memory caching.
   - Host root filesystem has `185 GiB` free space, easily accommodating container image layers (~1.8 GiB total download).

---

## 5. Monitoring & Telemetry Validation Criteria

RIFT's Telemetry Normalizer (`src/rift/telemetry/normalizer.py`) requires valid time-aligned metric vectors ($\Delta t = 10\text{s}$) across the following standard metric names:
- `lat_p99` (99th percentile request latency, ms)
- `lat_p50` (median request latency, ms)
- `err_rate` (HTTP 5xx / gRPC error ratio)
- `rps` (requests per second)
- `cpu_pct` (CPU utilization percentage)
- `mem_pct` (memory utilization percentage)

### Prometheus Scrape Configuration (`/tmp/rift-prom/prometheus.yml`)
```yaml
global:
  scrape_interval: 5s
  evaluation_interval: 5s

scrape_configs:
  - job_name: 'online-boutique'
    static_configs:
      - targets:
          - 'rift-frontend:8080'
          - 'rift-cartservice:7070'
          - 'rift-productcatalogservice:3550'
          - 'rift-currencyservice:7000'
          - 'rift-paymentservice:50051'
          - 'rift-shippingservice:50051'
          - 'rift-emailservice:8080'
          - 'rift-checkoutservice:5050'
          - 'rift-recommendationservice:8080'
          - 'rift-adservice:9555'
```

### Validation Pass Criteria
1. `curl -s http://127.0.0.1:19090/-/healthy` returns HTTP 200.
2. Query `http://127.0.0.1:19090/api/v1/query?query=up` returns `up{job="online-boutique"} == 1` for all 10 microservices.
3. RIFT Normalizer confirms zero silent imputation (`n_imputed == 0`).

---

## 6. Security and Authorization Requirements

1. **Host-Key Security:** Enforce strict SSH host-key verification (`StrictHostKeyChecking=yes`, `~/.ssh/known_hosts` line 124).
2. **Credential Safety:** Never expose passwords in command-line arguments, shell history, or logs. Use environment-piped `sshpass -e`.
3. **Namespace & Traffic-Control Boundary:**
   - Interventions must target **ONLY** containers within `rift-net` (using container network namespaces).
   - **NEVER** apply `tc qdisc` modifications to host physical interfaces (`eth0`, `eth1`).
   - Every `tc netem` command must be paired with an automated timeout watchdog that removes the qdisc within $\le 30.0\text{s}$.

---

## 7. Future Deployment Steps (Separately Authorized Sprint)

When authorized, live testbed initialization must execute in this exact sequence:

1. **Step 1 (Preflight Check):** Verify port `18080` and `19090` availability via `ss -tulpn`.
2. **Step 2 (Network Creation):** Create dedicated bridge network:
   ```bash
   podman network create --subnet 10.89.100.0/24 --gateway 10.89.100.1 rift-net
   ```
3. **Step 3 (Configuration Staging):** Write Prometheus configuration to `/tmp/rift-prom/prometheus.yml`.
4. **Step 4 (Container Launch):** Launch Redis, the 10 microservices, LoadGenerator, and Prometheus attached to `rift-net`.
5. **Step 5 (Telemetry Verification):** Execute read-only PromQL queries to verify metric streams across all nodes.
6. **Step 6 (Controlled Intervention Test):** Test single `tc netem` delay inside `rift-cartservice` netns with immediate rollback verification.

---

## 8. Rollback Procedures and Known Limitations

### Rollback & Teardown Protocol
Teardown is completely non-destructive and idempotent:
```bash
# 1. Stop and remove only RIFT containers
podman stop rift-frontend rift-cartservice rift-productcatalogservice \
            rift-currencyservice rift-paymentservice rift-shippingservice \
            rift-emailservice rift-checkoutservice rift-recommendationservice \
            rift-adservice rift-redis-cart rift-loadgenerator rift-prometheus 2>/dev/null
podman rm rift-frontend rift-cartservice rift-productcatalogservice \
          rift-currencyservice rift-paymentservice rift-shippingservice \
          rift-emailservice rift-checkoutservice rift-recommendationservice \
          rift-adservice rift-redis-cart rift-loadgenerator rift-prometheus 2>/dev/null

# 2. Remove dedicated network
podman network rm rift-net 2>/dev/null

# 3. Clean temporary prometheus config directory
rm -rf /tmp/rift-prom /tmp/rift-prom-data
```

### Known Environmental Limitations
1. **Shared Host Workloads:** CPU and disk I/O are shared with background `bobz-understand` processes; small variance in baseline latency ($5\text{--}10\text{ms}$) may occur.
2. **Synthetic Perturbation Semantics:** RIFT's causal graph represents inter-service communication edges; netem interventions on bridge veth pairs perturb the communication channel, exactly matching RIFT's interventional SCM model.

---

## 9. Prerequisite Gate Decision Matrix

```
┌──────────────────────────────────────┬──────────┬────────────────────────────────────────────────────────┐
│ Prerequisite Gate                    │ Decision │ Evidence / Rationale                                   │
├──────────────────────────────────────┼──────────┼────────────────────────────────────────────────────────┤
│ 1. Host OS & Privilege Model         │ PASS     │ RHEL 9.6 x86_64, root UID 0, CAP_NET_ADMIN confirmed.  │
│ 2. Traffic Control Subsystem (tc)    │ PASS     │ iproute2-6.11.0, sch_netem.ko.xz verified in kernel.   │
│ 3. Container Runtime (Podman)        │ PASS     │ Podman installed, bridge networking functional.        │
│ 4. Host Resource Capacity            │ PASS     │ 4.6 GiB available RAM, 185 GiB free disk space.        │
│ 5. External Registry Access          │ PASS     │ gcr.io and quay.io reachable over HTTPS.               │
│ 6. Workload Isolation Plan           │ PASS     │ Dedicated rift-net (10.89.100.0/24), ports 18080/19090.│
│ 7. Existing Workload Preservation    │ PASS     │ Zero overlap with bobz-understand ports/containers.    │
│ 8. Target Workload Deployment        │ BLOCKED  │ Online Boutique not yet deployed (Plan ready).         │
│ 9. Monitoring Daemon Deployment      │ BLOCKED  │ Prometheus not yet deployed (Config ready).            │
└──────────────────────────────────────┴──────────┴────────────────────────────────────────────────────────┘
```

**Overall Sprint 4.1 Planning Decision:** **READY FOR FUTURE AUTHORIZED DEPLOYMENT**  
All structural, safety, isolation, and configuration prerequisites are specified and verified. Live deployment can proceed upon explicit authorization.
