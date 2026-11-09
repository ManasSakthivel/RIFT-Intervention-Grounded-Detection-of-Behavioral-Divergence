# RIFT — Sprint 1: Scientific Gap Register & Risk Prioritization

**Audit Date:** 2026-11-02  
**Authority:** Technical Gap Analysis and Remediation Prioritization  

---

## 1. Prioritized Scientific Gaps Matrix

```
┌────┬──────────────────────────────────────┬──────────┬───────────────────┬──────────────────────────────────────┬──────────────┐
│ ID │ Scientific / Empirical Gap           │ Severity │ Scientific Impact │ Required Remediation / Action        │ Target Sprint│
├────┼──────────────────────────────────────┼──────────┼───────────────────┼──────────────────────────────────────┼──────────────┤
│ G1 │ Small-Sample FCI Unoriented PAGs     │ HIGH     │ 0% Coverage in FCI│ Integrate static tracing graph priors│ Sprint 2     │
│    │ ($N=18$ yields unoriented circle marks)│          │ on learned graphs │ and increase time-series scrape rate │              │
├────┼──────────────────────────────────────┼──────────┼───────────────────┼──────────────────────────────────────┼──────────────┤
│ G2 │ Synthetic Step Anomaly Triviality    │ HIGH     │ Latency baseline  │ Implement non-linear delays, retry   │ Sprint 3     │
│    │ (Earliest onset = root cause in step)│          │ scores 100% P@1   │ storms, and asynchronous buffers     │              │
├────┼──────────────────────────────────────┼──────────┼───────────────────┼──────────────────────────────────────┼──────────────┤
│ G3 │ Live Linux Kernel Netem Validation   │ MEDIUM   │ Live vs synthetic │ Deploy testbed on Linux VM with      │ Sprint 4     │
│    │ (Currently dry-run simulated on Mac) │          │ provenance check  │ Docker & CAP_NET_ADMIN capabilities  │              │
├────┼──────────────────────────────────────┼──────────┼───────────────────┼──────────────────────────────────────┼──────────────┤
│ G4 │ Leaf-Service Topology Boundary       │ LOW      │ Sink nodes fail R3│ Characterize leaf-service boundary as│ Sprint 2     │
│    │ (No downstream interventional effect)│          │ downstream test   │ fundamental causal limitation in doc │              │
├────┼──────────────────────────────────────┼──────────┼───────────────────┼──────────────────────────────────────┼──────────────┤
│ G5 │ Static Multi-Cause Benchmark Signal  │ LOW      │ H3 unsupported on │ Generate temporal multi-stage fault  │ Sprint 3     │
│    │ (Initial EBD anomaly dominates prior)│          │ static step data  │ cascades to exercise Bayesian loop   │              │
└────┴──────────────────────────────────────┴──────────┴───────────────────┴──────────────────────────────────────┴──────────────┘
```

---

## 2. Detailed Gap Descriptions and Exit Criteria

### G1: Small-Sample FCI Edge Orientation Ambiguity
- **Root Cause:** Contemporaneous conditional independence testing (Fisher's Z) on tree topologies without unshielded colliders cannot orient edges from observational data alone.
- **Exit Criteria for Sprint 2:** Incorporate distributed tracing call-graph topology as a structural prior in FCI, achieving $\ge 50\%$ coverage on non-confounded scenarios.

### G2: Idealized Step Telemetry in Synthetic Benchmark
- **Root Cause:** Instantaneous step jumps allow simple onset-time heuristics (`B1-LATENCY-CORR`) to achieve 100% accuracy.
- **Exit Criteria for Sprint 3:** Generate stress-test cohorts with inverted onset (asynchronous buffer masking) and retry amplification where simple correlation fails.

### G3: Live Linux Netem Validation
- **Root Cause:** macOS lacks Linux kernel netem queuing disciplines (`sch_netem`, `cls_u32`).
- **Exit Criteria for Sprint 4:** Execute end-to-end interventional runs against live Online Boutique containers on Linux VM and record live Prometheus histogram metrics.
