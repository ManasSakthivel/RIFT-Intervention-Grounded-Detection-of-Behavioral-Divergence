# RIFT Sprint 3 — Adversarial Benchmark Specification

**Authority:** Adversarial Benchmark Protocol Freeze  
**Date:** 2026-11-02  

---

## 1. Adversarial Failure Taxonomy

The Sprint 3 adversarial benchmark evaluates root-cause analysis systems across 6 complex failure families ($n=30$ scenarios total, 5 per family):

```
┌─────────────────────────────────┬────────────────────────────────────────────┬──────────────────────────────────────┐
│ Failure Family                  │ Degradation Dynamic & Physics              │ Target Heuristic Failure Mode        │
├─────────────────────────────────┼────────────────────────────────────────────┼──────────────────────────────────────┤
│ Family A: Inverted Onset        │ Asynchronous queue buffer masks root cause;│ Earliest-anomaly baselines blame     │
│                                 │ downstream victim service spikes first.    │ victim service (0% accuracy).        │
├─────────────────────────────────┼────────────────────────────────────────────┼──────────────────────────────────────┤
│ Family B: Retry Amplification   │ Client retry storm amplifies child latency │ Highest-anomaly & correlation blame  │
│                                 │ spike (z=8.0) beyond root cause (z=3.5).   │ child service (0% accuracy).         │
├─────────────────────────────────┼────────────────────────────────────────────┼──────────────────────────────────────┤
│ Family C: Shared Infrastructure │ Latent CPU throttling on shared hypervisor │ Call-graph propagation baselines     │
│ Confounding                     │ degrades multiple nodes simultaneously.    │ blame common caller (100% FAR).      │
├─────────────────────────────────┼────────────────────────────────────────────┼──────────────────────────────────────┤
│ Family D: Multiple Simultaneous │ Two concurrent root causes degrade         │ Tests multi-cause disambiguation     │
│ Faults                          │ overlapping downstream subgraphs.          │ without single-fault bias.           │
├─────────────────────────────────┼────────────────────────────────────────────┼──────────────────────────────────────┤
│ Family E: Noisy Telemetry &     │ 15% random metric dropouts, high noise     │ Tests robustness against telemetry   │
│ Dropouts                        │ variance (σ=15.0), and timestamp jitter.   │ corruption.                          │
├─────────────────────────────────┼────────────────────────────────────────────┼──────────────────────────────────────┤
│ Family F: Deep Cascade          │ Multi-hop degradation propagation across   │ Tests path traversal depth and hop   │
│                                 │ 4 service tiers (redis_cart→cart→checkout).│ latency accumulation.                │
└─────────────────────────────────┴────────────────────────────────────────────┴──────────────────────────────────────┘
```

---

## 2. Seed Determinism & Split Isolation
- Dataset saved to `datasets/rift_faults/adversarial_stress_cohort.json`.
- Seeds are isolated ($1000 + i$) and independent of the frozen development, validation, and held-out test splits.
