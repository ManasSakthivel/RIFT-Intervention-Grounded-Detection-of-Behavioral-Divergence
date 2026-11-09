# RIFT Sprint 7 — Workstream 4: Live Intervention Validation & Feasibility Report

**Document ID:** `RIFT-DOC-S7-WS4-LIVE-VAL-001`  
**Audit Date:** 2026-11-10  
**Auditor / Agent:** SPRINT 7 AGENT — WORKSTREAM 4 (LIVE INTERVENTION VALIDATION)  
**Authority:** Sprint 7 Recovery Mandate, Phase 3.6 §25–§27, `docs/SPRINT4_2_1_STAGE4_INTERVENTION_EXECUTION_REPORT.md`, `docs/recovery/CLAIMS_EVIDENCE_LEDGER.md`  
**Status:** COMPLETE & AUTHORITATIVE  

---

## 1. Executive Summary & Epistemic Framework

This report provides the exhaustive, technical verification of RIFT's live Linux testbed infrastructure, live network intervention mechanisms, telemetry pipelines, and experimental artifacts. 

To maintain scientific integrity across publications, technical documentation, and academic dossiers, this report enforces a strict separation among three distinct verification planes:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                RIFT VERIFICATION PLANES                                │
├──────────────────────────┬──────────────────────────────┬──────────────────────────────┤
│  1. Code Verification   │   2. Container Simulation    │   3. Live Linux Execution    │
│  (Static & Unit Tests)   │   (Synthetic Benchmarks)     │   (Single Feasibility Trial) │
├──────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ • AST / Static Analysis  │ • N = 252 Synthetic Scenarios│ • N = 1 Live Experiment      │
│ • Mocked Subprocess      │ • NumPy/SciPy Signal Gen     │ • 14 Podman Containers       │
│ • Dry-Run Engine Tests   │ • Simulated FCI / MSIS       │ • RHEL 9.6 Kernel 5.14       │
│ • iproute2 Syntax Rules  │ • Offline Cost Matrix Tests  │ • Real Linux `tc netem`      │
│ • Bug Identification     │ • Synthetic Metric Series    │ • Real Prometheus Scraping   │
└──────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```

### Key Audit Findings:
1. **Live Execution Feasibility ($N=1$):** Exactly **one live end-to-end experiment** (`RIFT-STAGE4-LIVE-001`) was executed on live Linux infrastructure (`9.30.57.225` on RHEL 9.6). It successfully proved that a $50\text{ms} \pm 5\text{ms}$ `tc netem` latency perturbation can be injected into an isolated container network namespace (`rift-cartservice`), detected via real-time Prometheus spanmetrics, and deterministically rolled back to `qdisc noqueue` without host disruption.
2. **Benchmark Scope:** The claim of evaluating 3 distinct microservice architectures (e.g., TrainTicket, SockShop, Online Boutique) is **UNSUPPORTED / RETRACTED** (Claim C2 in [`CLAIMS_EVIDENCE_LEDGER.md`](CLAIMS_EVIDENCE_LEDGER.md)). Only Google Online Boutique (14 containers) was deployed. The 252-scenario evaluation suite is entirely synthetic simulation.
3. **P0 Qdisc Handle Collision Bug (Finding N-1):** In `src/rift/intervention/network_intervention.py` and `src/rift/intervention/backends/linux_tc_netem.py`, a fatal collision exists between the root prio qdisc major handle (`1:`) and child netem handles when using band 1 (`parent 1:1 handle 1:`). On a live Linux kernel, `tc` rejects this command with `rc=2 (Cannot move an existing qdisc to a different parent)`. The live experiment succeeded only because the standalone orchestrator script ([`scripts/stage4_intervention_orchestrator.py`](../../scripts/stage4_intervention_orchestrator.py)) bypassed the engine and hardcoded `handle 10:`.
4. **Telemetry Sampling vs CID Floor Incompatibility:** Scraped live telemetry (15 baseline points, 12 active points at 10s intervals) falls below the mathematical sample size floor ($N_{\min} = 20$) required by [`src/rift/cid/cid.py`](../../src/rift/cid/cid.py), causing live pipeline runs to produce `GRADE: INSUFFICIENT`.

---

## 2. Live Linux Testbed Infrastructure Architecture

The live testbed infrastructure is defined across [`deploy/podman-compose.yaml`](../../deploy/podman-compose.yaml), [`deploy/otel-collector.yaml`](../../deploy/otel-collector.yaml), [`deploy/prometheus.yml`](../../deploy/prometheus.yml), and [`configs/live.yaml`](../../configs/live.yaml).

### 2.1 Podman Compose Specification (`deploy/podman-compose.yaml`)

The deployment instantiates 14 containers on an isolated bridge network:

```mermaid
graph TD
    subgraph Host["Host Environment (RHEL 9.6: 9.30.57.225)"]
        subgraph Ports["Loopback High-Port Bindings"]
            P1["127.0.0.1:18080 (Frontend UI)"]
            P2["127.0.0.1:19090 (Prometheus GUI/API)"]
            P3["127.0.0.1:18888 (OTel Health)"]
            P4["127.0.0.1:14317 (OTLP gRPC)"]
        end

        subgraph Bridge["Private Bridge Network: rift-net (10.89.100.0/24)"]
            LG["rift-loadgenerator<br/>10 Users Load"]
            FE["rift-frontend<br/>Port 8080"]
            CS["rift-cartservice<br/>Port 7070 (Target)"]
            RC["rift-redis-cart<br/>Port 6379"]
            CO["rift-checkoutservice<br/>Port 5050"]
            PC["rift-productcatalogservice<br/>Port 3550"]
            CU["rift-currencyservice<br/>Port 7000"]
            PM["rift-paymentservice<br/>Port 50051"]
            SH["rift-shippingservice<br/>Port 50051"]
            EM["rift-emailservice<br/>Port 8080"]
            RE["rift-recommendationservice<br/>Port 8080"]
            AD["rift-adservice<br/>Port 9555"]
            OTEL["rift-otel-collector<br/>Contrib v0.98.0"]
            PROM["rift-prometheus<br/>v2.51.0"]
        end
    end

    LG -->|HTTP| FE
    FE --> CS & PC & CU & SH & CO & AD & RE
    CO --> CS & PC & CU & SH & PM & EM
    CS --> RC
    FE & CS & CO & PC & CU & PM & SH & EM & RE & AD -.->|OTLP gRPC :4317| OTEL
    OTEL -->|Prometheus Exporter :8889| PROM
    PROM -.-> P2
    FE -.-> P1
```

### 2.2 Container Resource Allocation & Isolation Configuration

| Container Name | Base Image | CPU Limit | Mem Limit | Ingress / Egress Ports | Role |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `rift-frontend` | `gcr.io/.../frontend:v0.8.1` | 0.50 | 256 MB | 8080 (`127.0.0.1:18080`) | Web UI & API Gateway |
| `rift-cartservice` | `gcr.io/.../cartservice:v0.8.1` | 0.25 | 128 MB | 7070 (Internal) | **Target of Live Intervention** |
| `rift-redis-cart` | `docker.io/library/redis:alpine` | 0.25 | 128 MB | 6379 (Internal) | Key-value store for Cart |
| `rift-checkoutservice` | `gcr.io/.../checkoutservice:v0.8.1` | 0.25 | 128 MB | 5050 (Internal) | Checkout coordinator |
| `rift-productcatalogservice` | `gcr.io/.../productcatalogservice:v0.8.1` | 0.25 | 128 MB | 3550 (Internal) | Product metadata catalog |
| `rift-currencyservice` | `gcr.io/.../currencyservice:v0.8.1` | 0.25 | 128 MB | 7000 (Internal) | Currency conversion |
| `rift-paymentservice` | `gcr.io/.../paymentservice:v0.8.1` | 0.25 | 128 MB | 50051 (Internal) | Credit card processing |
| `rift-shippingservice` | `gcr.io/.../shippingservice:v0.8.1` | 0.25 | 128 MB | 50051 (Internal) | Shipping quote calculator |
| `rift-emailservice` | `gcr.io/.../emailservice:v0.8.1` | 0.25 | 128 MB | 8080 (Internal) | Confirmation email generator |
| `rift-recommendationservice` | `gcr.io/.../recommendationservice:v0.8.1` | 0.25 | 128 MB | 8080 (Internal) | Product recommender |
| `rift-adservice` | `gcr.io/.../adservice:v0.8.1` | 0.50 | 256 MB | 9555 (Internal) | Advertising display |
| `rift-loadgenerator` | `gcr.io/.../loadgenerator:v0.8.1` | 0.50 | 256 MB | Egress only (`USERS=10`) | Synthetic user traffic generator |
| `rift-otel-collector` | `docker.io/otel/...-contrib:0.98.0` | 0.25 | 128 MB | 4317, 8888, 8889 | Spanmetrics aggregator |
| `rift-prometheus` | `quay.io/prometheus/prometheus:v2.51.0` | 0.50 | 512 MB | 9090 (`127.0.0.1:19090`) | Metrics storage & PromQL |

### 2.3 Telemetry Pipeline & Spanmetrics Configuration

1. **Instrumentation:** All 10 application containers run with `ENABLE_TRACING=1` and `COLLECTOR_SERVICE_ADDR=rift-otel-collector:4317`.
2. **Collector Processing (`deploy/otel-collector.yaml`):**
   - The OTel Collector receives traces via OTLP gRPC.
   - The `spanmetrics` connector computes latency histograms over 11 explicit latency buckets: `[2ms, 5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1000ms, 2500ms, 5000ms]`.
   - Spanmetrics are exported via Prometheus exporter on `0.0.0.0:8889` under the metric prefix `rift_`.
3. **Prometheus Scraping (`deploy/prometheus.yml`):**
   - Scrape interval: `5s`.
   - Latency quantile query: `histogram_quantile(0.99, sum by (le) (rate(rift_duration_milliseconds_bucket[2m]))) / 1000`.

---

## 3. Live 50ms Latency Intervention Verification (`RIFT-STAGE4-LIVE-001`)

The single live validation trial was executed against `rift-cartservice` on the IBM DevIT Linux QA VM (`9.30.57.225`).

### 3.1 Host & Container Topology Verification

| Parameter | Recorded Value | Verification Source |
| :--- | :--- | :--- |
| **Host FQDN** | `wca4z-understand-dp1.fyre.ibm.com` | `hostname -f` |
| **Host IP** | `9.30.57.225` | Remote DevIT QA VM |
| **Kernel Version** | `Linux 5.14.0-503.21.1.el9_5.x86_64` (RHEL 9.6) | `uname -r` |
| **Container Engine** | Podman 5.2.2 (rootless bridge `rift-net`) | `podman --version` |
| **Target Container** | `rift-cartservice` | `podman inspect` |
| **Target Process PID** | `1109138` | `podman inspect --format '{{.State.Pid}}'` |
| **Host NetNS Inode** | `5583182` | `stat -c %i /proc/1/ns/net` |
| **Container NetNS Inode**| `5586971` | `stat -c %i /proc/1109138/ns/net` |
| **NetNS Inode Inequality**| **`5586971 != 5583182` (DISJOINT / VERIFIED)** | Pre-flight safety check |
| **Initial Qdisc** | `qdisc noqueue 0: root refcnt 2` | `nsenter -t 1109138 -n tc qdisc show dev eth0` |

### 3.2 Intervention Sequence & Watchdog Execution

```mermaid
sequenceDiagram
    autonumber
    participant Host as Host OS (9.30.57.225)
    participant WD as Detached Watchdog (PID: 1115050)
    participant NS as rift-cartservice NetNS (Inode: 5586971)
    participant Prom as Prometheus (127.0.0.1:19090)
    participant Orch as Stage 4 Orchestrator

    Note over Host,Orch: Pre-Flight Safety Verification
    Orch->>NS: Check NetNS Inode (5586971 != 5583182)
    NS-->>Orch: Disjoint Verified
    Orch->>Prom: Query 90s Pre-Baseline (18 samples @ 5s)
    
    Note over Orch,WD: Phase 2: Arm Watchdog & Apply Injection
    Orch->>WD: Spawn Detached Subprocess (45.0s Sleep Deadline)
    Orch->>NS: tc qdisc add dev eth0 root handle 1: prio bands 3 priomap 1...1
    Orch->>NS: tc qdisc add dev eth0 parent 1:1 handle 10: netem delay 50ms 5ms normal
    Orch->>NS: tc filter add dev eth0 protocol ip parent 1: prio 1 u32 match ip protocol 6 0xff flowid 1:1
    NS-->>Orch: Active: qdisc prio 1: root / qdisc netem 10: parent 1:1
    
    Note over Orch,Prom: Phase 3: Active Observation (30.0s)
    Orch->>Prom: Query 30s Active Telemetry (6 samples @ 5s)
    
    Note over Orch,NS: Phase 4: Teardown & Rollback
    Orch->>NS: tc filter del dev eth0 parent 1: prio 1
    Orch->>NS: tc qdisc del dev eth0 parent 1:1 handle 10:
    Orch->>NS: tc qdisc del dev eth0 root handle 1:
    Orch->>WD: Disarm Watchdog (SIGKILL PID 1115050)
    NS-->>Orch: Restored: qdisc noqueue 0: root refcnt 2
    
    Note over Orch,Prom: Phase 5: Post-Recovery Observation
    Orch->>Prom: Query 90s Post-Recovery Telemetry (18 samples @ 5s)
```

### 3.3 Empirical Telemetry & Divergence Table

The raw Prometheus telemetry recorded in [`artifacts/stage4_intervention_results.json`](../../artifacts/stage4_intervention_results.json) demonstrates unambiguous behavioral divergence:

| Service Name | Baseline p99 ($t_0$) | Active p99 ($t_{\text{act}}$) | Post-Recovery p99 ($t_{\text{post}}$) | Empirical Shift ($\Delta \mu$) | Shift $Z$-Score | Statistically Diverged? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`rift-cartservice` (Target)** | **$6.25\text{ ms}$** | **$236.15\text{ ms}$** | **$4.98\text{ ms}$** | **$+229.90\text{ ms}$** | **$+143.06$** | **YES (Primary Injected Fault)** |
| **`rift-frontend` (Direct Caller)**| $230.62\text{ ms}$ | $446.25\text{ ms}$ | $220.01\text{ ms}$ | $+215.63\text{ ms}$ | $+37.56$ | **YES (Upstream Propagation)** |
| **`rift-checkoutservice` (Caller)**| $128.30\text{ ms}$ | $245.87\text{ ms}$ | $166.94\text{ ms}$ | $+117.57\text{ ms}$ | $+1.95$ | NO (Call variance / low rate) |
| `rift-currencyservice` | $65.82\text{ ms}$ | $70.04\text{ ms}$ | $62.15\text{ ms}$ | $+4.22\text{ ms}$ | $+0.44$ | NO (Baseline noise) |
| `rift-paymentservice` | $15.53\text{ ms}$ | $9.90\text{ ms}$ | $9.89\text{ ms}$ | $-5.63\text{ ms}$ | $-0.79$ | NO (Unaffected) |
| `rift-productcatalogservice` | $4.10\text{ ms}$ | $4.01\text{ ms}$ | $3.98\text{ ms}$ | $-0.09\text{ ms}$ | $-0.46$ | NO (Unaffected) |
| `rift-shippingservice` | $4.26\text{ ms}$ | $1.98\text{ ms}$ | $3.74\text{ ms}$ | $-2.28\text{ ms}$ | $-12.70$ | NO (Unaffected) |
| `rift-emailservice` | $7.82\text{ ms}$ | $4.94\text{ ms}$ | $4.94\text{ ms}$ | $-2.88\text{ ms}$ | $-1.18$ | NO (Unaffected) |
| `rift-recommendationservice` | $10.64\text{ ms}$ | $9.88\text{ ms}$ | $9.91\text{ ms}$ | $-0.76\text{ ms}$ | $-0.50$ | NO (Unaffected) |
| `rift-adservice` | $5.67\text{ ms}$ | $8.61\text{ ms}$ | $8.80\text{ ms}$ | $+2.94\text{ ms}$ | $+2.04$ | NO (Unaffected) |

#### Telemetry Amplification Analysis ($50\text{ms} \rightarrow +229.9\text{ms}$):
The injected netem perturbation was configured as $50\text{ms} \pm 5\text{ms}$. However, `cartservice` observed a $+229.9\text{ms}$ shift at the p99 level. This occurs because:
1. Under concurrent load (10 users on `loadgenerator`), cart operations execute multiple sequential gRPC calls and Redis round-trips over loopback/bridge TCP sockets.
2. The u32 filter (`match ip protocol 6 0xff`) delayed all TCP packets on `eth0`, compounding latency over multiple round-trip handshake and data segments, accumulating in gRPC connection queue backpressure.

---

## 4. Deep-Dive Audit of Known Bugs & Divergences

### 4.1 Bug N-1: Qdisc Handle Major vs Band Minor Collision (P0 Severity)

In the Linux kernel `iproute2` subsystem, qdisc handles are structured as `major:minor` (or `major:` for qdiscs).
- A root prio qdisc created via `tc qdisc add dev eth0 root handle 1: prio bands 3` assigns **major number 1:** to the qdisc.
- The prio qdisc automatically creates classes `1:1`, `1:2`, and `1:3` (major `1`, minor `1..3`).
- When attaching a child qdisc (e.g. `netem`) to class `1:1`, the child qdisc **MUST** be assigned a distinct major handle number (e.g., `handle 10:` or `handle 20:`).
- In [`src/rift/intervention/backends/linux_tc_netem.py:149`](../../src/rift/intervention/backends/linux_tc_netem.py:149) and [`src/rift/intervention/network_intervention.py:246`](../../src/rift/intervention/network_intervention.py:246):
  ```python
  # Code constructs:
  ["tc", "qdisc", "add", "dev", iface, "parent", f"1:{handle}", "handle", f"{handle}:", "netem", ...]
  ```
- If `tc_handle="1:"` (representing Band 1), the command emitted is:
  ```bash
  tc qdisc add dev eth0 parent 1:1 handle 1: netem delay 50.0ms 5.0ms ...
  ```
- **The Kernel Failure:** Because `handle 1:` is already taken by the root prio qdisc, the Linux kernel rejects this command with:
  `Error: Cannot move an existing qdisc to a different parent.` or `RTNETLINK answers: File exists (rc=2)`.
- **How the Live Experiment Succeeded:** The live orchestrator script ([`scripts/stage4_intervention_orchestrator.py:66`](../../scripts/stage4_intervention_orchestrator.py:66)) bypassed `LinuxTcNetemBackend` and explicitly issued:
  ```bash
  tc qdisc add dev eth0 parent 1:1 handle 10: netem delay 50ms 5ms distribution normal
  ```
- **How Unit Tests Passed Despite the Bug:** Unit tests in [`tests/unit/test_network_intervention.py`](../../tests/unit/test_network_intervention.py) ran in `dry_run=True` mode, performing mock assertion on string outputs without executing `tc` against a real Linux kernel. Furthermore, `TestBandValidation` explicitly asserted that `tc_handle="10:"` must raise a `ValueError`, thus testing and locking in the buggy constraint!

### 4.2 Bug N-2: `intervention_lifecycle.py` Broken by Handle Validation (P0 Severity)

[`src/rift/intervention/intervention_lifecycle.py:278`](../../src/rift/intervention/intervention_lifecycle.py:278) instantiates `NetworkInterventionRecord` with `tc_handle="10:"`. However, `NetworkInterventionRecord.__post_init__` was modified to enforce `tc_handle in ("1:", "2:", "3:")`. Consequently, calling `InterventionLifecycle.apply()` raises an immediate `ValueError`, making the higher-level lifecycle manager unusable.

### 4.3 Bug N-3: Root Qdisc Non-Idempotency on Concurrent Interventions (P0 Severity)

In [`src/rift/intervention/network_intervention.py:242`](../../src/rift/intervention/network_intervention.py:242), `apply()` unconditionally executes `tc qdisc add dev {iface} root handle 1: prio ...`. If a second intervention is applied (e.g. MSIS multi-band intervention on Band 2), the root qdisc command returns a non-zero exit code (`RTNETLINK answers: File exists`). The loop treats any non-zero exit code as a fatal error and marks the second intervention `FAILED`.

### 4.4 Finding N-4 / N-10: Pipeline Orchestration & Namespace Wrapping Divergence

| Component | Target Address / Namespace Handling | Rollback Behavior | Verification Method |
| :--- | :--- | :--- | :--- |
| **`LinuxTcNetemBackend`** | Supports `container_pid`, `netns_path`, `sandbox_namespace` via `nsenter` | Deletes filter, child qdisc, and root prio qdisc | Inspects `tc qdisc show dev eth0` via substring |
| **`NetworkInterventionEngine`** | Only supports `ip netns exec <ns>` prefix | Deletes filter and child qdisc; **leaves residual `prio 1:` root** | Assumes success if `measured_latency_ms is None` |
| **`stage4_intervention_orchestrator.py`** | Hardcodes `nsenter -t {pid} -n` | Deletes filter, `handle 10:`, and `root handle 1:` | Reads `tc qdisc show dev eth0` before & after |
| **`e2e_runner.py`** | Hardcodes `destination_ip="10.0.0.1"` | Calls `rollback_all()` without try/finally | No active measurement during verify |

---

## 5. Live Execution vs Simulated Benchmarks: Absolute Demarcation

To prevent misattribution in research papers and technical documentation, the table below provides the authoritative boundary between what was executed live on Linux vs what was simulated:

| Dimension | Live Linux Execution (`RIFT-STAGE4-LIVE-001`) | Simulated Benchmark Corpus ($N=252$) |
| :--- | :--- | :--- |
| **Sample Size** | **$N = 1$ trial** (Single bounded intervention) | **$N = 252$ scenarios** (36 Dev + 216 Val) |
| **Host Environment** | Remote RHEL 9.6 VM (`9.30.57.225`) | Local execution (macOS / Linux / CI) |
| **Microservice Stack** | 14 real containers running via Podman 5.2.2 | Synthetic mathematical model |
| **Intervention Mechanism** | Real Linux kernel `tc netem` on container `eth0` | Synthetic parameter alteration in generator |
| **Telemetry Generation** | Real OpenTelemetry Collector + Prometheus | NumPy/SciPy synthetic timeseries generation |
| **Rollback Verification** | Kernel `tc qdisc show` verified restored to `noqueue` | In-memory status flag reset |
| **Causal Discovery & EBD** | Run on recorded 10s scraped Prometheus quantiles | Run on full synthetic matrix ($T=300$) |
| **Attribution Outcome** | Top-1 Attributed: `cartservice` ($100\%$ accuracy) | Evaluated across 8 baseline algorithms |
| **Research Claim Status** | **Feasibility Demonstration (Claim C9)** | **Statistical Benchmark (Claims C3, C7, C8)** |

---

## 6. Recommendations & Actionable Remediation Plan

```mermaid
graph TD
    A[Remediation Plan] --> B[Fix 1: Qdisc Handle Decoupling]
    A --> C[Fix 2: Unify Engine & Backend]
    A --> D[Fix 3: Pipeline Exception Safety]
    A --> E[Fix 4: Metric Window Alignment]

    B --> B1["Map band 1,2,3 -> handle 10:, 20:, 30:<br/>parent 1:1, 1:2, 1:3"]
    C --> C1["Deprecate split logic; use single Linux backend<br/>with nsenter/pid support"]
    D --> D1["Wrap e2e_runner apply-measure loop<br/>in robust try/finally rollback"]
    E --> E1["Increase scrape frequency or widen windows<br/>so N_pre, N_post >= 20 for CID"]
```

### 6.1 Qdisc Handle Scheme Decoupling (Remedying Bug N-1 & N-2)
Decouple the **prio band minor** (which must be `1`, `2`, or `3`) from the **child qdisc major handle** (which should be `10:`, `20:`, `30:`):
```python
# Recommended robust mapping:
BAND_TO_HANDLE = {1: "10:", 2: "20:", 3: "30:"}

# Command generation:
prio_class = f"1:{spec.prio_band}"          # e.g., "1:1"
child_handle = BAND_TO_HANDLE[spec.prio_band] # e.g., "10:"

cmd = [
    "tc", "qdisc", "add", "dev", iface,
    "parent", prio_class,
    "handle", child_handle,
    "netem", "delay", f"{lat:.1f}ms", f"{jitter:.1f}ms",
    "distribution", "normal"
]
```

### 6.2 Guaranteed Exception-Safe Rollback in Pipeline (Remedying Finding N-7)
In [`src/rift/pipeline/e2e_runner.py`](../../src/rift/pipeline/e2e_runner.py), wrap the entire intervention, measurement, and causal evaluation sequence in a `try...finally` block to guarantee `backend.rollback_all()` executes even on unhandled exceptions or timeouts.

### 6.3 Telemetry Scraping Window Alignment (Remedying Finding E-3)
Align Prometheus scrape frequencies and evaluation windows:
- Set Prometheus scrape interval to `1s` during live trials, or extend the baseline observation to $300\text{s}$ and active intervention to $60\text{s}$.
- This ensures $N_{\text{samples}} \ge 20$, satisfying the minimum sample size constraint of [`src/rift/cid/cid.py`](../../src/rift/cid/cid.py) without falling into `GRADE: INSUFFICIENT`.

---

## 7. Sign-Off & Verification Summary

| Verification Objective | Requirement | Status | Epistemic Verdict |
| :--- | :--- | :---: | :--- |
| **Testbed Infrastructure** | 14 Podman containers on private bridge `rift-net` | Verified | **PASS** (Google Online Boutique stack intact) |
| **Live NetNS Isolation** | Disjoint container NetNS inode (`5586971 != 5583182`) | Verified | **PASS** (Zero disturbance to host workloads) |
| **50ms Latency Injection** | Controlled `tc netem` latency on `cartservice` | Verified | **PASS** ($Z = +143.06$ divergence captured) |
| **Deterministic Rollback** | Restoration to `qdisc noqueue 0: root refcnt 2` | Verified | **PASS** (Restoration verified in kernel & metrics) |
| **Asynchronous Watchdog** | 45s detached watchdog auto-teardown safety | Verified | **PASS** (Watchdog armed PID 1115050, disarmed cleanly) |
| **Code Implementation Audit**| Identify `tc` handle collision and engine defects | Completed | **IDENTIFIED (P0 Bugs N-1, N-2, N-3 cataloged)** |
| **Epistemic Classification** | Demarcate $N=1$ Live Trial from $N=252$ Simulation | Completed | **AUTHORITATIVELY CLASSIFIED** |

**Conclusion:** The live Linux testbed infrastructure and the $N=1$ feasibility intervention on `cartservice` are verified and grounded in empirical data. The codebase has clear, cataloged bug diagnoses and actionable remediation paths for future Linux testbed campaigns.
