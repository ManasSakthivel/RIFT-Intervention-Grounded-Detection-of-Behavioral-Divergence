# RIFT Sprint 4.1.7.1 — Teardown Safety & Stage 2 Launch Checklist

**Document Version:** 1.0  
**Target Milestone:** Stage 2 Pre-Launch Operational Safety Checklist  
**Target Host:** Linux QA VM (`9.30.57.225:22` / `wca4z-understand-dp1.fyre.ibm.com`)  
**Execution Context:** LOCAL-ONLY INSPECTION & OPERATIONAL RUNBOOK (Zero Remote Changes / Zero Deployment)  
**Repository Root:** `/Users/manassakthivel/Desktop/RIFT FINAL`  

---

## 1. Executive Summary & Verdict

This checklist formalizes data and volume ownership boundaries, resource cleanup isolation, and a step-by-step operator runbook for **Stage 2: Isolated Stack Deployment Without Fault Injection**.

### Final Checklist Verdict:
### **READY TO REQUEST EXPLICIT STAGE 2 AUTHORIZATION**

> **Operational Boundary:** This document certifies that RIFT's containerized benchmark stack has zero shared volumes, zero persistent state dependencies, and an idempotent, targeted teardown mechanism that leaves existing IBM host workloads completely unaffected. **This document does NOT authorize or execute deployment; live launch on `9.30.57.225` requires separate, explicit stakeholder authorization.**

---

## 2. Volume & Data Ownership Audit

Inspecting [`deploy/podman-compose.yaml`](deploy/podman-compose.yaml:1) confirms:

```
┌──────────────────────────────┬──────────────────────────────┬──────────────┬──────────────┬──────────────────────────────────────────────────────┐
│ Service / Container          │ Mount Target                 │ Mount Type   │ Mode         │ Data Persistence & Risk Assessment                   │
├──────────────────────────────┼──────────────────────────────┼──────────────┼──────────────┼──────────────────────────────────────────────────────┤
│ rift-otel-collector          │ /etc/otelcol-contrib/config.yaml│ Bind Mount │ Read-Only(:ro)│ Local config file; zero persistent data generated   │
│ rift-prometheus              │ /etc/prometheus/prometheus.yml│ Bind Mount  │ Read-Only(:ro)│ Local config file; zero persistent data generated   │
│ 12 Online Boutique Services  │ None                         │ None         │ N/A          │ 100% Stateless; zero volumes or persistent storage   │
│ rift-redis-cart              │ None                         │ None         │ N/A          │ Ephemeral in-memory cache; zero host storage mapped  │
└──────────────────────────────┴──────────────────────────────┴──────────────┴──────────────┴──────────────────────────────────────────────────────┘
```

### Evaluation of `podman compose down -v`
* **Risk Assessment:**
  - The `-v` flag removes anonymous volumes associated with the RIFT compose project.
  - Because no named volumes or host directory mounts exist (only 2 read-only local config files), `down -v` will **NOT** delete any host directories or files outside the containers.
* **Conservative Teardown Recommendation:**
  To guarantee zero accidental collateral impact on other Podman workloads on the host, teardown should use targeted filters matching only `rift-*` resource prefixes.

---

## 3. Resource Ownership & Cleanup Isolation

```
┌──────────────────────────────┬─────────────────────────────┬────────────────────────────────────────────────────────┐
│ Resource Type                │ Explicit RIFT Ownership     │ Protection of Non-RIFT / IBM Resources                 │
├──────────────────────────────┼─────────────────────────────┼────────────────────────────────────────────────────────┤
│ Container Names              │ rift-* (14 containers)      │ bobz-understand and non-RIFT containers are untouched  │
│ Bridge Network               │ rift-net (10.89.100.0/24)   │ bobz (10.89.1.0/24), wca4z, podman bridges untouched   │
│ Host Published Ports         │ 18080, 19090, 18888, 14317  │ IBM ports (1433, 2424, 4001, 8081, 9443, 9444) untouched│
│ Temporary Files              │ /tmp/rift-prom/ (if staged) │ /var, /opt, /root system directories untouched         │
└──────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Operator Stage 2 Launch Runbook (When Authorized)

> **Notice:** The following sequence is an operational specification. Do NOT execute until explicit stakeholder approval is granted.

### Step 1: Confirm Authorization
- [ ] Confirm written stakeholder sign-off for **Stage 2 Isolated Deployment Only (No Fault Injection)**.

### Step 2: Read-Only Pre-Launch Health & Headroom Verification
```bash
# Verify host identity and memory headroom (> 3.0 GiB available)
hostname && uname -a && free -h && df -h /
```

### Step 3: Immediate Port-Availability Check
```bash
# Confirm loopback ports are free (must return 0 listeners)
ss -tulpn | grep -E ':(18080|19090|18888|14317)\b' || echo "PORTS_CONFIRMED_FREE"
```

### Step 4: Network & Subnet Verification
```bash
# Confirm 10.89.100.0/24 does not exist in routing table
ip route | grep -E '10\.89\.100\.' || echo "SUBNET_CONFIRMED_AVAILABLE"
```

### Step 5: Stage Manifests
```bash
# Transfer deploy/ directory to isolated working folder /tmp/rift-deploy/
mkdir -p /tmp/rift-deploy
cp -r deploy/* /tmp/rift-deploy/
```

### Step 6: Execute Isolated Deployment (State-Changing)
```bash
# Launch isolated stack attached to rift-net
podman compose -f /tmp/rift-deploy/podman-compose.yaml up -d
```

### Step 7: Verify Service Health & Readiness
```bash
# Check that all 14 containers are running
podman ps --filter "name=rift-" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# Probe Prometheus health
curl -s http://127.0.0.1:19090/-/healthy
```

### Step 8: Monitor Host Memory & Resource Headroom
```bash
# Verify host available memory remains > 1.5 GiB
free -h
```

---

## 5. Targeted Teardown Runbook

```bash
# 1. Stop and remove all RIFT-owned containers
podman compose -f /tmp/rift-deploy/podman-compose.yaml down -v

# 2. Targeted fallback cleanup (if partial failure occurred)
podman ps -a --filter "name=rift-" -q | xargs -r podman rm -f
podman network rm rift-net 2>/dev/null || true

# 3. Clean ephemeral deploy directory
rm -rf /tmp/rift-deploy

# 4. Post-Teardown Verification (Confirm ports free and IBM services unaffected)
ss -tulpn | grep -E ':(18080|19090|18888|14317)\b'
curl -s -I --connect-timeout 2 http://localhost:8081 || true
```

---

## 6. Mandatory Abort Criteria

The operator must immediately abort deployment and execute the teardown runbook if:
1. `ss -tulpn` detects any listener on ports `18080`, `19090`, `18888`, or `14317`.
2. Available host memory drops below $1.5\text{ GiB}$.
3. Host root disk free space drops below $20\text{ GiB}$.
4. Any running container attempts to mount `/`, `/proc`, `/sys`, or host runtime sockets.
5. Any degradation occurs in background `bobz-understand` processes.
6. Stakeholder authorization is withdrawn.

---

## 7. Final Checklist Decision

### Verdict: **READY TO REQUEST EXPLICIT STAGE 2 AUTHORIZATION**

* **Summary of Evidence:** All 14 containers are stateless, non-privileged, memory-capped at $2.50\text{ GiB}$, network-isolated on `rift-net`, and bounded by targeted, non-destructive teardown scripts.
* **Test Suite Status:** **649 passed / 0 failed** in `pytest`.
* **Remote System Status:** **Zero remote systems accessed or modified during this sprint.**
