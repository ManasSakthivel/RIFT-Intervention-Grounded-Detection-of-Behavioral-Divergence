# RIFT Sprint 3.1 — Adversarial Generator Validation & Data-Generating Integrity

**Audit Date:** 2026-11-02  
**Lead Auditor:** Data-Generating Process & Benchmark Auditor  
**Authority:** Task 5 Adversarial Generator Verification  

---

## 1. Audit of the 6 Adversarial Failure Generators

```
┌─────────────────────────────────┬────────────────────────────────────────────┬──────────────────────────────────────┐
│ Generator Family                │ Data-Generating Function                   │ Independent Ground Truth Logic       │
├─────────────────────────────────┼────────────────────────────────────────────┼──────────────────────────────────────┤
│ Family A: Inverted Onset        │ Buffer delay T_buffer=20s masks root cause │ Root = cart; Victim = frontend       │
│                                 │ Downstream victim spikes at t=60s; root    │ True causal path: cart→checkout→     │
│                                 │ spikes at t=80s.                           │ frontend.                            │
├─────────────────────────────────┼────────────────────────────────────────────┼──────────────────────────────────────┤
│ Family B: Retry Amplification   │ Client retry storm generates z=8.0 at child│ Root = payment (z=3.5);              │
│                                 │ while root cause has z=3.5.                │ Child victim = checkout (z=8.0).     │
├─────────────────────────────────┼────────────────────────────────────────────┼──────────────────────────────────────┤
│ Family C: Shared Infrastructure │ Latent hypervisor core throttle hits both  │ Confounded: recommendation and       │
│ Confounding                     │ services simultaneously with z=5.0.        │ product_catalog share latent core.   │
├─────────────────────────────────┼────────────────────────────────────────────┼──────────────────────────────────────┤
│ Family D: Multiple Simultaneous │ Two concurrent root causes inject latency  │ Dual root: shipping & email          │
│ Faults                          │ into shared checkout dependency.           │ Causal paths: shipping→checkout and  │
│                                 │                                            │ email→checkout.                      │
├─────────────────────────────────┼────────────────────────────────────────────┼──────────────────────────────────────┤
│ Family E: Noisy Telemetry &     │ 15% random dropouts, timestamp jitter, and │ Root = product_catalog;              │
│ Dropouts                        │ high-variance noise (σ=15.0).              │ Evaluates robustness to data loss.   │
├─────────────────────────────────┼────────────────────────────────────────────┼──────────────────────────────────────┤
│ Family F: Deep Cascade          │ 4-tier propagation: redis_cart→cart→       │ Root = redis_cart;                   │
│                                 │ checkout→frontend with +10s hop delays.    │ Evaluates multi-hop reachability.    │
└─────────────────────────────────┴────────────────────────────────────────────┴──────────────────────────────────────┘
```

---

## 2. Leakage and Shortcut Verification

- **No Label Leakage:** Scenario generator output contains only raw timestamped telemetry dictionaries (`metrics[svc] = DataFrame({"time": ..., "value": ...})`).
- **No Seed Sharing:** Adversarial cohort scenarios use independent seeds ($1001 \dots 1030$).
- **No Ground-Truth Leaking into Models:** Model input is strictly the `IncidentContext`, with no access to ground-truth labels.
