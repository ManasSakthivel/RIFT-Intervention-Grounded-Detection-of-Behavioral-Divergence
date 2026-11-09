# RIFT Sprint 4.1.2 — Live Infrastructure Remediation & Verification Report

**Document Version:** 1.0  
**Authority:** Remediation of Findings F-01 through F-06 from `docs/SPRINT4_1_1_INDEPENDENT_PLAN_AUDIT.md`  
**Execution Environment:** macOS darwin arm64 (Implementation & Non-Privileged Unit Verification Only)  
**Status:** IMPLEMENTED AND LOCALLY VERIFIED (No Remote VM Modifications)  
**Repository:** `/Users/manassakthivel/Desktop/RIFT FINAL`  

---

## 1. Finding-by-Finding Remediation Matrix

```
┌──────┬──────────┬─────────────────────────────────────────────────────────────────┬─────────────────────────────────┐
│ ID   │ Severity │ Root Problem Identified in Audit                                │ Remediation Status & Verdict    │
├──────┼──────────┼─────────────────────────────────────────────────────────────────┼─────────────────────────────────┤
│ F-01 │ CRITICAL │ ip netns exec failed on default Podman /proc/<pid>/ns/net netns │ FIXED AND LOCALLY VERIFIED      │
│ F-02 │ CRITICAL │ configs/live.yaml eth0 created host-interface hazard            │ FIXED AND LOCALLY VERIFIED      │
│ F-03 │ HIGH     │ Direct HTTP scrape of Online Boutique gRPC ports fails          │ FIXED AND LOCALLY VERIFIED      │
│ F-04 │ HIGH     │ In-process Python watchdog leaves orphaned qdiscs on crash      │ FIXED AND LOCALLY VERIFIED      │
│ F-05 │ MEDIUM   │ Manifests and configs existed only as Markdown doc text         │ FIXED AND LOCALLY VERIFIED      │
│ F-06 │ LOW      │ Memory sum arithmetic rounding (2.375 GiB reported as ~2.30)    │ FIXED AND LOCALLY VERIFIED      │
└──────┴──────────┴─────────────────────────────────────────────────────────────────┴─────────────────────────────────┘
```

---

## 2. Summary of Implementation Changes

### 1. Fix F-01: Explicit Network Namespace Targeting (`src/rift/intervention/backends/linux_tc_netem.py`)
- **Modification:** Refactored `LinuxTcNetemBackend` to accept explicit `container_pid: Optional[int]` or `netns_path: Optional[str]` alongside `sandbox_namespace`.
- **Mechanism:** Invocations are now wrapped with `["nsenter", "-t", str(container_pid), "-n"] + cmd` or `["nsenter", f"--net={netns_path}"] + cmd`, completely bypassing reliance on `/var/run/netns` named symlinks.
- **Fail-Closed Boundary:** Added `_validate_isolation_target()` which immediately raises `ValueError` if `container_pid in (0, 1)`, `sandbox_namespace in ("host", "root", "default")`, or if no container namespace target is supplied.

### 2. Fix F-02: Host-Namespace and Interface Safety Guard (`src/rift/safety/safety.py` & `configs/live.yaml`)
- **Modification:** Enhanced `SafetyController.is_production_namespace()` and `assess_pre_intervention()` to strictly reject host namespace indicators (`"host"`, `"root"`, `"default"`, `"/proc/1/ns/net"`, or empty strings) with `HardStopReason.PRODUCTION_NAMESPACE`.
- **Configuration:** Updated `configs/live.yaml` to explicitly document that `interface: "eth0"` refers strictly to the container-internal virtual interface inside the validated NetNS and never the host's physical network adapter.

### 3. Fix F-03: OpenTelemetry Spanmetrics Telemetry Bridge (`deploy/otel-collector.yaml`, `deploy/prometheus.yml`)
- **Modification:** Added a dedicated OpenTelemetry Collector service (`rift-otel-collector`) configured with the `spanmetrics` connector.
- **Mechanism:** Boutique microservices stream standard OTLP gRPC telemetry on port `4317`. The collector aggregates span durations into histogram buckets and exports Prometheus-compatible time series on `:8889` for scraping by `rift-prometheus`.

### 4. Fix F-04: Independent Detached Rollback Watchdog (`src/rift/intervention/watchdog.py`)
- **Modification:** Implemented `DetachedRollbackWatchdog` and `WatchdogSpec`.
- **Mechanism:** Before applying any `tc netem` command, a detached watchdog process is spawned using `subprocess.Popen(..., start_new_session=True)`. The detached script executes `sleep {timeout_s} && nsenter -t {pid} -n tc qdisc del ...`.
- **Resilience:** The watchdog runs in an independent session and triggers cleanup even if the parent Python process is killed (`SIGKILL`/OOM) or the SSH session drops.

### 5. Fix F-05: Version-Controlled Deployment Manifests (`deploy/`)
- **Added:**
  - `deploy/podman-compose.yaml`: Full 14-container specification with `rift-net` private bridge subnet (`10.89.100.0/24`), per-container resource limits, and strict loopback port bindings.
  - `deploy/prometheus.yml`: Prometheus scraper configuration targeting `rift-otel-collector:8889` and `rift-frontend:8080`.
  - `deploy/otel-collector.yaml`: OpenTelemetry Collector configuration.
  - `deploy/README.md`: Step-by-step deployment and validation documentation.

### 6. Fix F-06: Precise Resource Budget Accounting (`docs/SPRINT4_1_ISOLATION_AND_DEPLOYMENT_PLAN.md`)
- **Recalculation:** Exact mathematical sum across all 14 containers:
  $$\text{Total Memory} = 256 + (8 \times 128) + 256 + 128 + 256 + 128\text{ (OTel)} + 512\text{ (Prom)} = 2560\text{ MiB} = 2.50\text{ GiB}$$
- Preserves $>2.1\text{ GiB}$ of the host's $4.6\text{ GiB}$ available RAM for background `bobz-understand` processes.

---

## 3. Telemetry Metric-Source Matrix

```
┌──────────┬──────────────────────┬──────────────────────────────────┬────────────┬─────────────────────────────┬───────────────────────────┐
│ Metric   │ Source Component     │ Ingestion / Exporter Path        │ Units      │ Aggregation Semantics       │ Missing Data Policy       │
├──────────┼──────────────────────┼──────────────────────────────────┼────────────┼─────────────────────────────┼───────────────────────────┤
│ lat_p99  │ Boutique gRPC Spans  │ OTel spanmetrics -> Prometheus   │ ms         │ histogram_quantile(0.99)    │ NaN (No silent imputation)│
│ lat_p50  │ Boutique gRPC Spans  │ OTel spanmetrics -> Prometheus   │ ms         │ histogram_quantile(0.50)    │ NaN (No silent imputation)│
│ err_rate │ Boutique gRPC Spans  │ OTel spanmetrics -> Prometheus   │ ratio [0,1]│ error_calls / total_calls   │ NaN (No silent imputation)│
│ rps      │ Boutique gRPC Spans  │ OTel spanmetrics -> Prometheus   │ req/sec    │ rate(calls_total[1m])       │ NaN (No silent imputation)│
│ cpu_pct  │ Container Runtime    │ Podman Stats / cAdvisor Exporter │ % [0,100]  │ rate(cpu_usage_seconds[1m]) │ NaN (No silent imputation)│
│ mem_pct  │ Container Runtime    │ Podman Stats / cAdvisor Exporter │ % [0,100]  │ memory_usage / memory_limit │ NaN (No silent imputation)│
└──────────┴──────────────────────┴──────────────────────────────────┴────────────┴─────────────────────────────┴───────────────────────────┘
```

---

## 4. Test Execution & Verification

### Executed Tests (649/649 Passed)
- `tests/unit/test_safety_namespace_remediation.py`: 9/9 passed.
  - Verifies missing namespace, host namespace (`host`, `root`, `/proc/1/ns/net`), and PID 1 rejections.
  - Verifies `_wrap_ns` with `container_pid` and `netns_path`.
- `tests/unit/test_watchdog_remediation.py`: 4/4 passed.
  - Verifies `WatchdogSpec` validation (PID $\le 1$ and timeout $>30\text{s}$ rejected).
  - Verifies dry-run arm/disarm and detached subprocess spawning with `start_new_session=True`.
- `tests/unit/test_telemetry_manifest_remediation.py`: 4/4 passed.
  - Verifies `VALID_METRIC_NAMES` completeness.
  - Verifies `align_metric_to_windows` never silently imputes missing windows.
  - Verifies YAML parsing and loopback port bindings for all `deploy/` manifests.
- **Full Regression Suite:** 649 unit and integration tests executed cleanly with zero failures.

### Non-Executed Tests (Explicitly Documented)
- **Live Linux Kernel `tc netem` Injections:** NOT EXECUTED. Modifying live kernel network schedulers is prohibited in this remediation sprint and requires future authorized execution on the Linux QA VM.
- **Live Container Deployment:** NOT EXECUTED. Manifests were validated syntactically via local YAML parsers without starting containers on the QA VM.

---

## 5. Git Working-Tree & Branch Status

```
Branch: remediation/reproducible-evaluation
Untracked Artifacts Added:
  deploy/podman-compose.yaml
  deploy/prometheus.yml
  deploy/otel-collector.yaml
  deploy/README.md
  src/rift/intervention/watchdog.py
  tests/unit/test_safety_namespace_remediation.py
  tests/unit/test_watchdog_remediation.py
  tests/unit/test_telemetry_manifest_remediation.py
  docs/SPRINT4_1_2_REMEDIATION_REPORT.md
Modified Code Files:
  src/rift/intervention/backends/linux_tc_netem.py
  src/rift/safety/safety.py
  configs/live.yaml
  docs/SPRINT4_1_ISOLATION_AND_DEPLOYMENT_PLAN.md
```
Zero commits or pushes were made; all existing research and evaluation artifacts remain strictly preserved.

---

## 6. Final Sprint Verdict

### Status: **READY FOR INDEPENDENT REVIEW**

All identified audit blockers (F-01 through F-06) have been addressed with fail-closed safety guards, independent watchdog architecture, OpenTelemetry spanmetrics bridge, reproducible manifests, and verified unit tests. Live deployment to the QA VM remains pending explicit authorization.
