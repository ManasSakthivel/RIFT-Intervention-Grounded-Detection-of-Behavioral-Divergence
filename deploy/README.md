# RIFT Live Testbed Deployment Guide

**Authority:** `docs/SPRINT4_1_1_INDEPENDENT_PLAN_AUDIT.md` (Findings F-01, F-03, F-05, F-06)  
**Status:** SPECIFICATION & REPRODUCIBLE MANIFESTS  

---

## 1. Prerequisites

- **Host OS:** Linux (RHEL 9.6 x86_64, Kernel $\ge 5.14$).
- **Container Engine:** Podman ($\ge 4.4$) with `podman-compose` or native `podman` CLI.
- **Privileges:** Non-root or root with `CAP_NET_ADMIN` capability inside container network namespaces.
- **Port Availability:** Ports `18080`, `19090`, `18888`, `14317` on `127.0.0.1` must be verified free.

---

## 2. Resource Budgeting

```
┌──────────────────────────────┬──────────────┬──────────────┐
│ Component / Service          │ Memory Cap   │ CPU Quota    │
├──────────────────────────────┼──────────────┼──────────────┤
│ 8 Microservices (128M each)  │ 1024 MiB     │ 2.0 Cores    │
│ 3 Frontend/Ad/Loadgen (256M) │ 768 MiB      │ 1.5 Cores    │
│ Redis Cart (128M)            │ 128 MiB      │ 0.25 Cores   │
│ OTel Collector (128M)        │ 128 MiB      │ 0.25 Cores   │
│ Prometheus (512M)            │ 512 MiB      │ 0.5 Cores    │
├──────────────────────────────┼──────────────┼──────────────┤
│ TOTAL CONFIGURED LIMITS      │ 2560 MiB     │ 4.5 Cores    │
│                              │ (2.50 GiB)   │ (burst cap)  │
└──────────────────────────────┴──────────────┴──────────────┘
```

---

## 3. Manifest Validation (Local, Non-Privileged)

To validate the YAML syntax without executing:
```bash
python3 -c "import yaml; yaml.safe_load(open('deploy/podman-compose.yaml')); yaml.safe_load(open('deploy/prometheus.yml')); yaml.safe_load(open('deploy/otel-collector.yaml')); print('YAML_SYNTAX_VALID')"
```

---

## 4. Teardown & Idempotent Cleanup

```bash
podman compose -f deploy/podman-compose.yaml down -v
```
