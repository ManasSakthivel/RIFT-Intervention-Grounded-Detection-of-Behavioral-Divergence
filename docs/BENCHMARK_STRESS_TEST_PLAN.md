# RIFT: Benchmark Stress-Testing & Complex Failure Protocol Plan

**Lead Author:** Experimental Design & Benchmark Architect  
**Date:** 2026-11-02  
**Authority:** Methodological Rigor and Stress-Test Specification  

---

## 1. Motivation: Beyond Idealized Step Perturbations

The initial synthetic benchmark established that when faults manifest as clean, isolated, single-step latency jumps, simple heuristics (earliest anomaly onset in `B1-LATENCY-CORR`) trivially identify the injected service.

However, real-world cloud-native microservice incidents exhibit complex dynamics where simple correlation heuristics fail:
1. **Asynchronous Queue Buffering:** Upstream queues hide root-cause degradation until buffers overflow, making downstream victim services spike *before* the upstream root cause.
2. **Cascading Retry Storms:** Service retries amplify downstream latency, causing downstream services to exhibit larger anomaly amplitudes than the failing service.
3. **Shared Infrastructure Confounding:** Co-located containers sharing physical CPU cores or network switches degrade simultaneously with identical onset timestamps.
4. **Non-Stationary Background Traffic:** Diurnal traffic variations and noisy neighbors create false anomaly triggers in non-faulty services.

---

## 2. Advanced Stress-Test Scenario Specifications

To evaluate RIFT and baselines under realistic conditions, we specify 5 complex failure archetypes:

```
┌─────────────────────────────────┬────────────────────────────────────────────┬──────────────────────────────────────┐
│ Scenario Archetype              │ Failure Mechanism                          │ Expected Heuristic Baseline Failure  │
├─────────────────────────────────┼────────────────────────────────────────────┼──────────────────────────────────────┤
│ Archetype 1: Inverted Onset     │ Asynchronous buffer masking root cause     │ B1 blames downstream victim (earliest│
│ Archetype 2: Confounded Cluster │ Shared hypervisor CPU throttle             │ Sieve blames upstream root caller    │
│ Archetype 3: Retry Amplification│ Upstream retry storm inflating child p99   │ B1 blames child (highest amplitude)  │
│ Archetype 4: Multi-Cause Chain  │ Intermittent DB lock + memory leak         │ One-shot misses secondary cause      │
│ Archetype 5: High Noise / Drops │ 15% random drop rate with noisy telemetry  │ Pure correlation yields false peaks  │
└─────────────────────────────────┴────────────────────────────────────────────┴──────────────────────────────────────┘
```

---

## 3. Protocol Freeze and Seed Isolation Rules

1. **Independent Evaluation Cohort:** Advanced stress scenarios must be registered as a distinct benchmark cohort (`stress_test_cohort.json`) and must *not* overwrite or contaminate the frozen `development.json`, `validation.json`, or `held_out_test.json` splits.
2. **Seed Determinism:** Each scenario uses isolated cryptographic PRNG seeds ($1000 + i$).
3. **Equivalence of Information:** All baselines (`B1-LATENCY-CORR`, `SIEVE-LIKE`, `RIFT-RANDOM`, `RIFT-ONE-SHOT`, `RIFT-FULL`) receive identical `IncidentContext` data structures.
4. **Primary Evaluation Endpoint:** Focus on **False Attribution Rate (FAR)** and **Identifiability-Conditioned Abstention Precision** under confounding and inverted onsets.
