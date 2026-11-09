# RIFT Sprint 4 — Linux QA VM Preflight Inspection Report

**Date:** 2026-11-02  
**Target Host:** Linux QA VM (`9.30.57.225:22`)  
**Inspection Type:** Non-destructive, read-only preflight audit  
**Repository:** `/Users/manassakthivel/Desktop/RIFT FINAL`  

---

## 1. Executive Summary

A non-destructive, read-only preflight inspection of the remote Linux QA testbed VM at `9.30.57.225` was conducted to determine its readiness for live RIFT telemetry scraping and traffic-control network interventions.

The inspection verified that the host is a dedicated RHEL 9.6 x86_64 environment with full root privileges (`CAP_NET_ADMIN`), active `sch_netem` kernel module support, and the `tc` traffic-control utility installed. However, the target benchmark microservice suite (Google Online Boutique) and live monitoring daemons (Prometheus / OpenTelemetry Collector) are not currently deployed or active. Existing user workloads (`bobz-understand` AD / OrientDB services) are running on the host and must remain preserved.

---

## 2. Area-by-Area Inspection Findings

### Task 1 — Host Identity & Authentication Status
- **Hostname:** `wca4z-understand-dp1.fyre.ibm.com`
- **Operating System / Kernel:** `Linux 5.14.0-570.62.1.el9_6.x86_64 #1 SMP PREEMPT_DYNAMIC (RHEL 9.6 x86_64)`
- **User Identity:** `uid=0(root) gid=0(root) groups=0(root)`
- **Uptime & System Load:** `up 7 days, 17:15, 0 users, load average: 0.15, 0.17, 0.16`
- **Host-Key Verification:** **VERIFIED** (`StrictHostKeyChecking=yes` matched trusted `ssh-ed25519` record in `~/.ssh/known_hosts` line 124).
- **Authentication:** **SUCCESS** (`sshpass -e` authenticated as `root@9.30.57.225` without command-line exposure).
- **Verdict:** **PASS**

### Task 2 — Container Environment
- **Runtime Availability:**
  - `docker`: Not installed in PATH (`/usr/bin/which: no docker`).
  - `podman`: Installed and operational (`/usr/bin/podman`).
- **Container Inventory:**
  - Root Podman running containers: `0` active.
  - Stopped container: `2e4729383ca5` (`ibm.com/bobz-understand:3.1.0`), exited 6 days ago.
- **Active Workloads on Host:**
  - Supervisord managing Java/OrientDB/SQLServer applications for user `aakash` (ports `1433`, `2424`, `4001`, `8081`, `9443`, `9444`).
- **Online Boutique Status:** **NOT PRESENT**. No Online Boutique containers or images are loaded.
- **Verdict:** **CONDITIONAL PASS** (Podman runtime is functional, but target benchmark workload requires containerized deployment).

### Task 3 — Monitoring Infrastructure
- **Prometheus Endpoint (`http://localhost:9090`):** `Inactive / Connection Refused`.
- **OpenTelemetry Collector (`http://localhost:8888` / `4317`):** `Inactive / Connection Refused`.
- **Systemd Services:** `systemctl is-active prometheus` -> `inactive`; `systemctl is-active otelcol` -> `inactive`.
- **Verdict:** **BLOCKED** (Monitoring daemons are not running; live scraping requires Prometheus/OTel setup on non-conflicting ports).

### Task 4 — Traffic Control (`tc netem`) Capability
- **`tc` Utility:** Installed (`/usr/sbin/tc`, iproute2-6.11.0, libbpf 1.5.0).
- **Kernel Module:** `sch_netem.ko.xz` present in kernel tree (`/lib/modules/5.14.0-570.62.1.el9_6.x86_64/kernel/net/sched/sch_netem.ko.xz`).
- **Privilege Level:** `uid=0(root)` (`CAP_NET_ADMIN` capability present).
- **Network Interfaces:** `lo`, `eth0`, `eth1` active with default `fq_codel` root qdiscs.
- **Execution Capability:** **CONFIRMED** (Kernel and binary support for netem latency, packet loss, and jitter are fully present).
- **Verdict:** **PASS**

---

## 3. Dependency & Access Matrix

| Component | Path / Spec | Present | Status / Notes |
|---|---|---|---|
| **SSH Daemon** | `sshd:22` (RHEL 9.6) | Yes | Authenticated with strict host-key verification |
| **Linux Kernel** | `5.14.0-570.62.1.el9_6` | Yes | RHEL 9.6 kernel with netem scheduler modules |
| **`tc` binary** | `/usr/sbin/tc` | Yes | iproute2-6.11.0 |
| **Kernel module** | `sch_netem.ko.xz` | Yes | In-tree kernel scheduler module |
| **Container Engine**| `/usr/bin/podman` | Yes | Podman 4.x / 5.x available |
| **Docker Engine** | `docker` | No | Podman available as drop-in alternative |
| **Python** | `/usr/bin/python3` | Yes | Python 3.9.25 (RHEL default) |
| **Online Boutique**| Microservice stack | No | Not deployed on target host |
| **Prometheus** | `localhost:9090` | No | Inactive / not running |
| **Existing Workload**| `bobz-understand` | Yes | Must be protected from port & resource collision |

---

## 4. Overall Readiness Verdict & Recommendation

| Area | Status |
|---|---|
| **Host Identity & SSH** | **PASS** |
| **Container Engine** | **CONDITIONAL PASS** (Podman ready, Boutique absent) |
| **Monitoring Pipeline** | **BLOCKED** (Prometheus daemon absent) |
| **`tc netem` Capability** | **PASS** |

### Final Recommendation: **NEEDS REMEDIATION**

The Linux QA testbed host at `9.30.57.225` has all requisite operating system, kernel, and privilege capabilities (`tc netem`, `podman`, `CAP_NET_ADMIN`) to support live RIFT validation. However, before live fault injection and metrics collection can begin, the testbed requires:
1. Deployment of the 10 Online Boutique microservice containers using `podman` on isolated non-conflicting network namespaces/ports.
2. Deployment of a lightweight Prometheus instance scraping container gRPC/HTTP metrics.
3. Verification that non-RIFT services on the host (`bobz-understand`, ports 1433/2424/4001/8081/9443/9444) remain undisturbed.
