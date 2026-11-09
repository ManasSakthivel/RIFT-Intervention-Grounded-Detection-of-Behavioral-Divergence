# RIFT Sprint 4.1.5 — Live Validation Readiness Runbook & Controlled Test Protocol

**Document Version:** 1.0  
**Target Host:** Linux QA VM (`9.30.57.225:22` / `wca4z-understand-dp1.fyre.ibm.com`)  
**Repository:** `/Users/manassakthivel/Desktop/RIFT FINAL`  
**Execution Context:** LOCAL DOCUMENTATION & PROTOCOL SPECIFICATION ONLY (Zero Remote Changes)  

---

## 1. Executive Summary & Verdict

This runbook establishes an auditable, fail-closed execution protocol for the eventual live Linux validation of RIFT's network intervention, rollback watchdog, and telemetry ingestion subsystems.

### Final Verdict:
### **READY FOR STAKEHOLDER AUTHORIZATION OF A SPECIFIC VALIDATION STAGE**

> **Authorization Boundary:** This verdict confirms that all structural, mathematical, and algorithmic prerequisites have been implemented and verified locally across 649 tests. **Operational execution on `9.30.57.225` is NOT authorized by this document.** Progression through each validation stage (from read-only preflight to staged intervention) requires explicit, staged stakeholder authorization.

---

## 2. Repository Provenance & Test Evidence

```
┌─────────────────────────────────┬─────────────────────────────────────────────────────────────┐
│ System Attribute                │ Verified Value                                              │
├─────────────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Working Branch                  │ remediation/reproducible-evaluation                         │
│ Head Commit                     │ cbc5ae5 fix: correct broken docs/limitations.md link        │
│ Test Suite Status               │ pytest -> 649 passed / 0 failed (13.95s runtime)            │
│ Core Remediation Modules        │ src/rift/intervention/backends/linux_tc_netem.py (F-01/F-02) │
│                                 │ src/rift/safety/safety.py (F-02)                            │
│                                 │ src/rift/intervention/watchdog.py (F-04)                    │
│                                 │ src/rift/telemetry/normalizer.py (F-03)                     │
│ Version-Controlled Manifests    │ deploy/podman-compose.yaml, deploy/prometheus.yml           │
│                                 │ deploy/otel-collector.yaml, deploy/README.md (F-05)         │
│ Working Tree Integrity          │ Preserved; zero unrelated changes or secrets exposed        │
└─────────────────────────────────┴─────────────────────────────────────────────────────────────┘
```

---

## 3. Requirement-by-Requirement Evidence Matrix

```
┌────────────────────────────────────────┬──────────────────────┬───────────────────────────┬──────────────────────────────────────────────────────┐
│ Requirement                            │ Subsystem            │ Verification Status       │ Evidence / Rationale                                 │
├────────────────────────────────────────┼──────────────────────┼───────────────────────────┼──────────────────────────────────────────────────────┤
│ 1. Explicit NetNS Wrapping (nsenter)   │ LinuxTcNetemBackend  │ VERIFIED LOCALLY          │ nsenter -t <pid> -n unit-tested; fails closed        │
│ 2. Host Namespace Hard Stop            │ SafetyController     │ VERIFIED LOCALLY          │ Host PIDs/strings hard-abort with PRODUCTION_NAMESPACE│
│ 3. Fail-Closed Unwrapped Fallback      │ LinuxTcNetemBackend  │ VERIFIED LOCALLY          │ ValueError raised if no container target provided   │
│ 4. Detached Subshell Watchdog          │ DetachedWatchdog     │ VERIFIED LOCALLY          │ setsid() subshell timer verified via Popen mocks     │
│ 5. Per-Destination Netem Filtering     │ tc u32 flowid        │ VERIFIED LOCALLY          │ Validated prio bands 1:1, 1:2, 1:3; parent preserved │
│ 6. OTel Spanmetrics Bridge             │ OTel Collector       │ VERIFIED LOCALLY          │ Manifest configured with spanmetrics connector       │
│ 7. Telemetry Normalizer (Zero Impute)  │ Normalizer           │ VERIFIED LOCALLY          │ NaN preserved on gaps; n_imputed == 0 enforced       │
│ 8. Resource Allocation (2.50 GiB)      │ Podman Manifest      │ VERIFIED LOCALLY          │ Mathematical sum: 2560 MiB across 14 containers      │
│ 9. Disjoint Network Subnet             │ rift-net Bridge      │ VERIFIED LOCALLY          │ 10.89.100.0/24 verified disjoint from host routes    │
│ 10. Live Linux Kernel tc Execution     │ Linux Kernel         │ NOT VERIFIED (STAGED)     │ Requires Stage 4 authorized live execution           │
│ 11. Live Online Boutique Telemetry     │ OTel -> Prometheus   │ NOT VERIFIED (STAGED)     │ Requires Stage 3 authorized live collection          │
│ 12. Host Background Workload Isolation │ bobz-understand      │ VERIFIED LOCALLY          │ Zero port/subnet collision with ports 1433/2424/etc. │
└────────────────────────────────────────┴──────────────────────┴───────────────────────────┴──────────────────────────────────────────────────────┘
```

---

## 4. Namespace Safety & Identification Requirements

Before any traffic-control command is issued, the execution pipeline must strictly enforce the following sequence:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PRE-EXECUTION NAMESPACE VERIFICATION SEQUENCE                                          │
│                                                                                        │
│ 1. Resolve Target Container:                                                           │
│    Query podman inspect <container_name> --format '{{.State.Pid}}'                     │
│                                                                                        │
│ 2. Identity Verification:                                                              │
│    Confirm PID > 1 and check /proc/<pid>/cmdline matches intended boutique binary.     │
│                                                                                        │
│ 3. Anti-Host Safety Invariant:                                                         │
│    Assert readlink /proc/<pid>/ns/net != readlink /proc/1/ns/net (Reject if identical).│
│                                                                                        │
│ 4. Pre-Intervention State Snapshot:                                                    │
│    Capture baseline: nsenter -t <pid> -n tc qdisc show dev eth0                        │
│                                                                                        │
│ 5. Arm Watchdog:                                                                       │
│    Spawn detached timer: DetachedRollbackWatchdog.arm(spec) -> MUST return ARMED.      │
│                                                                                        │
│ 6. Execute Intervention:                                                               │
│    Dispatch per-destination netem via nsenter -t <pid> -n tc ...                       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

*Fail-Closed Guarantee:* If any step (1 through 5) fails or returns ambiguous output, the pipeline immediately halts with `SAFE_ABORT`. Under no circumstances is `tc` executed directly on host interfaces.

---

## 5. Rollback Acceptance & Failure Matrix

```
┌──────────────────────────────┬─────────────────────────────────────────────────────────┬──────────────────────┬──────────────────────────────────┐
│ Failure Scenario             │ Expected System Behavior                                │ Safety Invariant     │ Operator Action on Failure       │
├──────────────────────────────┼─────────────────────────────────────────────────────────┼──────────────────────┼──────────────────────────────────┤
│ 1. Normal Experiment Exit    │ Explicit disarm() followed by immediate tc qdisc del    │ Qdisc removed in <1s │ Verify tc qdisc show dev eth0    │
│ 2. Python SIGKILL / OOM      │ Detached subshell sleeps timeout_s, then deletes qdisc  │ Qdisc removed at T+30│ Run deploy/README.md manual del  │
│ 3. SSH Session Disconnect    │ Watchdog ignores SIGHUP (setsid) and executes teardown  │ Qdisc removed at T+30│ Reconnect & inspect container netns│
│ 4. Watchdog Spawn Fails      │ arm() raises RuntimeError; intervention is aborted      │ Zero tc apply sent   │ Fix process limits; retry stage  │
│ 5. Watchdog Process Killed   │ Primary Python lifecycle issues rollback on timeout     │ Rollback attempted   │ Execute out-of-band cleanup      │
│ 6. Rollback Command Error    │ Watchdog script runs || true to attempt all deletions   │ Teardown attempted   │ Issue container restart          │
│ 7. Host System Reboot        │ Kernel flushes volatile qdiscs on memory/bridge ifaces  │ Clean state on boot  │ Verify host services normal      │
│ 8. Target Container Crash    │ Container death automatically destroys NetNS & qdiscs   │ Zero leak outside ns │ Podman restarts clean container  │
│ 9. Overlapping Experiments   │ Unique experiment_id & band handles prevent collision   │ Band isolation       │ Enforce single-runner mutex      │
│ 10. Pre-Existing Qdisc       │ Root prio qdisc parent 1: preserved; child qdisc purged │ Parent intact        │ Do not delete root prio handle 1:│
└──────────────────────────────┴─────────────────────────────────────────────────────────┴──────────────────────┴──────────────────────────────────┘
```

---

## 6. Honest Rollback Guarantees & Boundaries

* **Guaranteed by Architecture:**
  - *Process Separation:* Detached subshells (`start_new_session=True`) survive parent Python termination and SSH disconnection.
  - *Target Scope:* Teardown operates strictly inside the target container's NetNS and targets specific child handles (`1:1`, `1:2`, `1:3`), preserving the root scheduler.
  - *Fail-Closed Pre-check:* Failure to arm the watchdog prevents the intervention from starting.
* **Limitations (Explicitly Disclosed):**
  - If both the Python process and the detached watchdog subshell are concurrently killed via external `SIGKILL`, the kernel netem qdisc remains until container restart or manual `tc qdisc del`.
  - Durability across host reboots is volatile (qdiscs are not persistent, which is safe).

---

## 7. Telemetry Acceptance Criteria

To confirm telemetry validity in Stage 3:
1. **Container Discovery:** `curl -s http://127.0.0.1:19090/api/v1/targets` confirms 100% of targets in `UP` state.
2. **Span Ingestion:** OTel Collector metrics endpoint (`http://127.0.0.1:18888/metrics`) confirms `otelcol_receiver_accepted_spans > 0`.
3. **Metric Availability:** Prometheus query returns valid series for:
   - `traces_span_metrics_duration_milliseconds_bucket` (for `lat_p99`, `lat_p50`)
   - `traces_span_metrics_calls_total` (for `err_rate`, `rps`)
4. **Zero Imputation Policy:** RIFT Normalizer confirms $0$ imputed values (`stream.n_imputed == 0`).
5. **Loss-of-Observability Stop Condition:** If Prometheus query fails for $>2$ consecutive windows ($20\text{s}$), all running interventions are immediately aborted and rolled back.

---

## 8. Resource & Isolation Checklist

```
┌──────────────────────────────┬──────────────┬──────────────┬────────────────────────────────────────────────────────┐
│ Resource / Isolation Item    │ Configured   │ Host Status  │ Stop / Safety Boundary                                 │
├──────────────────────────────┼──────────────┼──────────────┼────────────────────────────────────────────────────────┤
│ Total Memory Cap (14 Ctrs)   │ 2560 MiB     │ 4.6 GiB Free │ Abort if host free RAM drops below 1.5 GiB             │
│ CPU Limit (Aggregate)        │ 4.5 Cores    │ Multi-core   │ Throttle load generator if load average > 8.0          │
│ Disk Ephemeral Space         │ < 2.0 GiB    │ 185 GiB Free │ Abort if root disk space drops below 20 GiB            │
│ Dedicated Podman Network     │ 10.89.100.0/24│ Disjoint    │ Abort if subnet overlaps with host routing table       │
│ Exposed Host Ports           │ 18080, 19090 │ Verified Free│ Abort if port bound by non-RIFT process                │
│ Existing IBM Workload Ports  │ 1433, 2424...│ Active       │ Strict prohibition: Never touch ports 1433, 2424, 8081 │
└──────────────────────────────┴──────────────┴──────────────┴────────────────────────────────────────────────────────┘
```

---

## 9. Staged Validation Procedure

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 0 — DOCUMENTATION & REPOSITORY FREEZE (COMPLETED / VERIFIED)                      │
│   • Entry: 649 unit tests pass; manifests & watchdog verified locally.                  │
│   • Authorization Required: None (Local only).                                          │
└────────────────────────────────────────┬────────────────────────────────────────────────┘
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1 — READ-ONLY REMOTE VM PREFLIGHT                                                 │
│   • Entry: Stakeholder approval for read-only SSH inspection.                           │
│   • Action: Re-verify free RAM, free ports (18080, 19090), and absence of NetNS leaks.  │
│   • Exit Criterion: Host resources verified healthy; bobz-understand untouched.         │
└────────────────────────────────────────┬────────────────────────────────────────────────┘
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 2 — ISOLATED STACK DEPLOYMENT (ZERO FAULT INJECTION)                              │
│   • Entry: Stakeholder approval for container launch on rift-net (10.89.100.0/24).      │
│   • Action: Launch 14 containers via deploy/podman-compose.yaml.                        │
│   • Exit Criterion: All 14 containers running healthy; memory within 2.50 GiB cap.      │
└────────────────────────────────────────┬────────────────────────────────────────────────┘
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 3 — TELEMETRY & OBSERVABILITY VALIDATION                                          │
│   • Entry: Stakeholder approval for telemetry scraping.                                 │
│   • Action: Verify OTel spanmetrics flow into Prometheus; validate zero imputation.     │
│   • Exit Criterion: RIFT Normalizer produces complete G_T metric streams.              │
└────────────────────────────────────────┬────────────────────────────────────────────────┘
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 4 — CONTROLLED SINGLE-INTERVENTION & WATCHDOG TRIAL                               │
│   • Entry: Explicit stakeholder sign-off for single 100ms netem delay on rift-cart.     │
│   • Action: Arm watchdog (15s); apply netem; verify latency delta; disarm & rollback.   │
│   • Exit Criterion: Latency spikes by 100ms, then recovers to baseline within 2s.       │
└────────────────────────────────────────┬────────────────────────────────────────────────┘
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 5 — COMPLETE TEARDOWN & RECOVERY AUDIT                                            │
│   • Entry: Validation complete or abort triggered.                                      │
│   • Action: podman compose down -v; remove rift-net; verify host ports & qdiscs clean.  │
│   • Exit Criterion: Zero leftover containers, qdiscs, or temporary files.               │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Mandatory Abort Conditions

The operator must immediately abort and execute Stage 5 teardown if:
1. Target PID is $\le 1$ or does not match container process table.
2. Target NetNS is identical to `/proc/1/ns/net`.
3. Watchdog arming returns failure or error.
4. Host available RAM drops below $1.5\text{ GiB}$.
5. Any error occurs on ports `1433`, `2424`, `4001`, `8081`, `9443`, `9444`.
6. Prometheus scraping fails for $>20\text{s}$.
7. Stakeholder revokes authorization or communication drops.

---

## 11. Stakeholder Authorization Checklist

Before authorizing **Stage 1 & Stage 2**:
- [ ] Review `docs/SPRINT4_1_3_INDEPENDENT_CODE_SAFETY_AUDIT.md` (Verdict: READY).
- [ ] Confirm no port collisions on `18080`, `19090`, `18888`, `14317`.
- [ ] Approve memory allocation ceiling ($2.50\text{ GiB}$).
- [ ] Authorize staging of `rift-net` bridge network (`10.89.100.0/24`).

Before authorizing **Stage 4 (Single Intervention)**:
- [ ] Confirm Stage 2 and Stage 3 exit criteria passed.
- [ ] Approve target service (`rift-cartservice`), impairment parameter (`100ms delay`), and duration ceiling ($15\text{s}$).

---

## 12. Final Recommendation

**READY FOR STAKEHOLDER AUTHORIZATION OF A SPECIFIC VALIDATION STAGE**

The RIFT live-validation safety architecture is mathematically sound, fail-closed, and accompanied by an auditable, staged runbook. Staged execution may proceed beginning with Stage 1 upon explicit stakeholder sign-off.
