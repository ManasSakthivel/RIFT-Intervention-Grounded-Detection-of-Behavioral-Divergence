# RIFT Sprint 4.1.1 — Independent Deployment & Isolation Plan Audit

**Document Version:** 1.0  
**Audit Target:** `docs/SPRINT4_1_ISOLATION_AND_DEPLOYMENT_PLAN.md`  
**Target Environment:** Linux QA VM (`9.30.57.225:22` / `wca4z-understand-dp1.fyre.ibm.com`)  
**Audit Status:** COMPLETE — INDEPENDENT SAFETY & METHODOLOGICAL AUDIT  
**Repository:** `/Users/manassakthivel/Desktop/RIFT FINAL`  

---

## 1. Executive Summary & Verdict

An independent forensic audit of the proposed workload isolation and live deployment plan ([`docs/SPRINT4_1_ISOLATION_AND_DEPLOYMENT_PLAN.md`](docs/SPRINT4_1_ISOLATION_AND_DEPLOYMENT_PLAN.md)) was performed prior to any potential execution on the Linux QA VM (`9.30.57.225`).

### Executive Verdict: **CONDITIONAL PASS — DEPLOYMENT NOT AUTHORIZED UNTIL REMEDIATION**

While the plan correctly identifies host resource headroom ($4.6\text{ GiB}$ free RAM, $185\text{ GiB}$ free disk), verifies disjoint network subnets (`10.89.100.0/24`), and avoids port conflicts with active `bobz-understand` services (ports 18080 and 19090 are verified free), **critical technical gaps in network namespace resolution, traffic-control safety fallbacks, telemetry scrape architecture, and watchdog process independence must be remediated before live execution can be safely authorized.**

---

## 2. Classification of Findings

```
┌───────────┬──────────┬────────────────────────────────────────────────────────────────────────────────────────┐
│ ID        │ Severity │ Summary                                                                                │
├───────────┼──────────┼────────────────────────────────────────────────────────────────────────────────────────┤
│ F-01      │ CRITICAL │ ip netns exec namespace wrapping fails on default Podman network namespaces            │
│ F-02      │ CRITICAL │ configs/live.yaml defaults interface: eth0, creating host-level traffic hazard         │
│ F-03      │ HIGH     │ Direct Prometheus HTTP scraping fails against Online Boutique gRPC service ports       │
│ F-04      │ HIGH     │ Rollback watchdog is in-process only; orphaned qdiscs occur if SSH/Python crashes      │
│ F-05      │ MEDIUM   │ Deployment manifests and configs are not version-controlled in repository tree         │
│ F-06      │ LOW      │ Minor arithmetic rounding discrepancy in memory budget (2432 MiB = 2.375 GiB vs 2.30)  │
└───────────┴──────────┴────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Audit Area Analyses

### Audit 1 — Network Isolation
- **Subnet Collision Verification:**
  - Remote host routing table (`ip route`) inspection confirmed active subnets: `9.30.56.0/23` (`eth1`), `10.11.0.0/16`–`10.19.0.0/16` (`eth0`), and `172.16.0.0/16` (`eth0`).
  - Existing Podman networks: `bobz` (`10.89.1.0/24`), `wca4z` (`10.89.0.0/24`), `podman` (`10.88.0.0/16`).
  - Proposed `rift-net` subnet (`10.89.100.0/24`) is **verified completely disjoint** from all host and container routes.
- **Port Exposure:**
  - Published ports bind strictly to loopback (`127.0.0.1:18080`, `127.0.0.1:19090`).
  - No external listeners (`0.0.0.0` or public interface `eth1`) are exposed.
- **Verdict:** **CONDITIONAL PASS** (Subnet and port isolation sound; netns execution path requires F-01/F-02 remediation).

---

### Audit 2 — Traffic-Control (`tc netem`) Safety
- **Namespace Resolution Defect (F-01):**
  - In [`src/rift/intervention/backends/linux_tc_netem.py:96`](src/rift/intervention/backends/linux_tc_netem.py:96), commands are prefixed with `ip netns exec {self.sandbox_namespace}`.
  - Podman does not maintain named network namespaces in `/var/run/netns` by default. Executing `ip netns exec rift-eval-default` will fail with `Cannot open network namespace: No such file or directory` unless container PID netns descriptors (`/proc/<pid>/ns/net`) are explicitly symlinked.
- **Host Interface Fallback Hazard (F-02):**
  - In [`configs/live.yaml:64`](configs/live.yaml:64), `interface: "eth0"` is configured. If namespace execution is bypassed or omitted, `tc qdisc add dev eth0 root ...` will execute on the host's primary corporate network interface, replacing the default `fq_codel` scheduler and disrupting internal `10.11.x.x` traffic.
- **Watchdog Independence Defect (F-04):**
  - Rollback is executed synchronously in Python ([`src/rift/intervention/backends/linux_tc_netem.py:176-200`](src/rift/intervention/backends/linux_tc_netem.py:176)). If the Python process is abruptly terminated (OOM killer, SIGKILL) or the SSH session drops, the `netem` qdiscs remain in the Linux kernel indefinitely.
- **Verdict:** **FAIL** (Blockers F-01, F-02, and F-04 must be resolved).

---

### Audit 3 — Resource Budget
- **Mathematical Reconstruction:**
  $$\text{Budget} = 256\text{ (frontend)} + 8 \times 128\text{ (microservices)} + 256\text{ (adservice)} + 128\text{ (redis)} + 256\text{ (loadgen)} + 512\text{ (prom)} = 2432\text{ MiB} = 2.375\text{ GiB}$$
- **Host Headroom Assessment:**
  - Total RAM: $15\text{ GiB}$, Used: $10\text{ GiB}$, Available: $4.6\text{ GiB}$.
  - Post-allocation headroom: $>2.2\text{ GiB}$ free RAM remaining for background `bobz-understand` processes.
  - Disk storage: $185\text{ GiB}$ free ($26\%$ used of $247\text{ GiB}$). Ephemeral container storage requires $<2\text{ GiB}$.
- **Verdict:** **PASS**

---

### Audit 4 — Service and Port Conflicts
- **Port Conflict Inspection:**
  - Read-only probe executed on target VM: `ss -tulpn | grep -E ':(18080|19090)'`.
  - Ports `18080` (Frontend) and `19090` (Prometheus) are **VERIFIED FREE** (exit status 0, zero active listeners).
  - Existing workload ports (`1433`, `2424`, `4001`, `8081`, `9443`, `9444`) are entirely unaffected.
- **Verdict:** **PASS**

---

### Audit 5 — Telemetry Validity
- **gRPC Scrape Protocol Incompatibility (F-03):**
  - The plan configures Prometheus to scrape `rift-cartservice:7070`, `rift-paymentservice:50051`, etc. via HTTP GET `/metrics`.
  - Standard Google Online Boutique images (`gcr.io/google-samples/microservices-demo/*:v0.8.1`) run gRPC servers on these ports without built-in Prometheus HTTP metric exporters.
  - Direct HTTP scraping will yield HTTP parse errors and 100% missing metric vectors.
- **Telemetry Requirement for Normalizer:**
  - [`src/rift/telemetry/normalizer.py:32-34`](src/rift/telemetry/normalizer.py:32) strictly mandates non-imputed `lat_p99`, `lat_p50`, `err_rate`, `rps`, `cpu_pct`, `mem_pct`.
  - An OpenTelemetry Collector with `otlp` receiver and `prometheus` exporter / `spanmetrics` connector is required to translate microservice gRPC spans into scrapeable Prometheus time-series metrics.
- **Verdict:** **FAIL** (Blocker F-03 must be resolved).

---

### Audit 6 — Deployment Provenance & Authorization
- **Image Provenance:**
  - Plan references official Google Cloud demo images (`gcr.io/google-samples/microservices-demo/*:v0.8.1`) and Quay Prometheus (`quay.io/prometheus/prometheus:v2.51.0`).
  - Immutable SHA256 digest pinning should be applied to prevent supply-chain drift.
- **Authorization Gate:**
  - Deployment must be governed by an explicit multi-step checklist with human sign-off.
- **Verdict:** **CONDITIONAL PASS**

---

### Audit 7 — Independent Reproducibility & Repository Artifacts
- **Repository Manifest Audit:**
  - Inspected repository structure: No version-controlled `deploy/podman-compose.yaml` or `deploy/prometheus.yml` files currently exist.
  - Manifests must be checked into the repository under `deploy/` rather than relying solely on ephemeral `/tmp` file generation.
- **Verdict:** **CONDITIONAL PASS**

---

## 4. Verification Matrix

```
┌────────────────────────────────────────┬──────────────────┬───────────────┬──────────────────────────────────┐
│ Audit Area                             │ Subsystem        │ Status        │ Primary Blocker / Note           │
├────────────────────────────────────────┼──────────────────┼───────────────┼──────────────────────────────────┤
│ 1. Network Isolation                   │ Podman / Bridge  │ CONDITIONAL   │ Subnet & loopback verified free  │
│ 2. Traffic-Control Safety              │ Linux tc / NetNS │ FAIL          │ F-01, F-02, F-04 netns & safety  │
│ 3. Resource Capacity & Headroom        │ RAM / CPU / Disk │ PASS          │ 2.375 GiB fits in 4.6 GiB RAM    │
│ 4. Service & Port Conflict Avoidance   │ Ports & Daemons  │ PASS          │ 18080 and 19090 verified free    │
│ 5. Telemetry & Normalizer Validity     │ Prometheus / gRPC│ FAIL          │ F-03 gRPC spanmetrics pipeline   │
│ 6. Deployment Provenance               │ Images & Digests │ CONDITIONAL   │ Digest pinning required          │
│ 7. Repository Manifest Reproducibility │ Version Control  │ CONDITIONAL   │ Manifests need check-in under deploy/ │
└────────────────────────────────────────┴──────────────────┴───────────────┴──────────────────────────────────┘
```

---

## 5. Required Remediation Actions

Prior to authorizing any deployment or live fault injection:

1. **Remediate NetNS Resolution (F-01):**
   Update `LinuxTcNetemBackend` or provide a pre-flight helper to execute `tc` via `nsenter -t <container_pid> -n tc ...` or explicitly symlink `/proc/<pid>/ns/net` into `/var/run/netns/rift-eval-<service>`.
2. **Enforce Host Interface Guard (F-02):**
   Add a hard safety check in `SafetyController` ([`src/rift/safety/safety.py`](src/rift/safety/safety.py)) that raises a fatal `SafetyViolation` if any `tc` command targets host interfaces (`eth0`, `eth1`, `lo`) without an active container NetNS wrapper.
3. **Implement OTel Spanmetrics Bridge (F-03):**
   Include an OpenTelemetry Collector container configured with `spanmetrics` connector to ingest gRPC traces from Boutique microservices and expose valid Prometheus metrics for RIFT's `Normalizer`.
4. **Deploy Detached Watchdog Daemon (F-04):**
   Provide a standalone detached shell watchdog (`nohup` / `systemd-run`) that automatically executes `tc qdisc del` inside the target NetNS upon a 30-second timeout expiration.
5. **Check In Version-Controlled Manifests (F-05):**
   Create `deploy/podman-compose.yaml` and `deploy/prometheus.yml` in the Git repository tree.

---

## 6. Final Deployment Decision

### Decision: **AUTHORIZATION MAY BE CONSIDERED AFTER REMEDIATION**

The isolation architecture is fundamentally sound and compatible with the QA VM's resources. However, live deployment is **NOT AUTHORIZED** until the 5 remediation items above are implemented and verified.
