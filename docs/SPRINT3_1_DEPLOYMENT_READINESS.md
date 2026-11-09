# RIFT Sprint 3.1 — Live QA Deployment Readiness Checklist

**Audit Date:** 2026-11-02  
**Target Host:** Linux QA VM (`9.30.57.225:22`)  
**Authority:** Task 8 Live QA Deployment Specification  

---

## 1. QA VM Environment Verification

- **Host Reachability:** Verified over TCP port 22 (`wca4z-understand-dp1.fyre.ibm.com`).
- **Operating System:** Linux 5.14.0 (RHEL 9.6 x86_64).
- **Environment Integrity Policy:**
  - **Do NOT shutdown, reset, rebuild, or reconfigure the VM.**
  - **Do NOT interfere with existing QuickBuild or non-RIFT containers.**
  - Preserve all existing infrastructure and services.

---

## 2. Live QA Experiment Deployment Checklist

```
┌─────────────────────────────────┬──────────┬────────────────────────────────────────────────────────┐
│ Deployment Step                 │ Status   │ Verification Command & Notes                           │
├─────────────────────────────────┼──────────┼────────────────────────────────────────────────────────┤
│ 1. SSH Authentication           │ VERIFIED │ Password auth verified; non-interactive session ready. │
│ 2. Docker & Container Runtime   │ READY    │ Verified Docker available on host.                     │
│ 3. Online Boutique Verification │ READY    │ Inspect running boutique containers on host.           │
│ 4. Prometheus Metric Scraping   │ READY    │ Scrape gRPC bucket metrics via localhost:9090.         │
│ 5. tc netem Linux Kernel Check  │ READY    │ Verify sch_netem and cls_u32 modules in kernel.        │
│ 6. Rollback & Idempotent Cleanup│ READY    │ tc qdisc del script ready for instant teardown.        │
└─────────────────────────────────┴──────────┴────────────────────────────────────────────────────────┘
```

---

## 3. Idempotent Rollback & Cleanup Plan

Upon completion of live testing, execute strictly targeted cleanup:
1. Delete only `tc qdisc` rules added to `eth0` / container `veth` interfaces.
2. Remove only temporary experiment result logs in `/tmp/rift-live/`.
3. Do NOT stop or restart core VM system services.
