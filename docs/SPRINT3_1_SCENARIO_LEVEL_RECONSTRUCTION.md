# RIFT Sprint 3.1 — Scenario-Level Reconstruction & Traceability

**Audit Date:** 2026-11-02  
**Dataset:** `datasets/rift_faults/adversarial_stress_cohort.json` ($n=30$)  
**Dataset SHA-256:** `46e769c6e75895fa25bfc22616aabb38757a2dac3c3c190025a4e57eb1215577`  
**Machine-Readable Predictions:** `artifacts/evaluation/adversarial_scenario_predictions.json`  

---

## 1. Summary of Reconstructed Scenario Outcomes

```
┌──────────────────┬──────────┬───────────┬───────────────┬────────────────────┬──────────────┐
│ Method           │ Total    │ Correct   │ Abstained     │ False Attribution  │ Raw P@1      │
├──────────────────┼──────────┼───────────┼───────────────┼────────────────────┼──────────────┤
│ B0-EARLIEST      │ 30       │ 11        │ 0             │ 19                 │ 36.7%        │
│ B0-HIGHEST       │ 30       │ 22        │ 0             │ 8                  │ 73.3%        │
│ B1-LATENCY-CORR  │ 30       │ 22        │ 0             │ 8                  │ 73.3%        │
│ B3-SIEVE-LIKE    │ 30       │ 5         │ 0             │ 25                 │ 16.7%        │
│ B6-RIFT-RANDOM   │ 30       │ 22        │ 0             │ 8                  │ 73.3%        │
│ B4-RIFT-ONE-SHOT │ 30       │ 22        │ 0             │ 8                  │ 73.3%        │
│ RIFT-OBS         │ 30       │ 0         │ 30            │ 0                  │ 0.0%         │
│ RIFT-FULL        │ 30       │ 14        │ 5             │ 11                 │ 46.7%        │
│ RIFT-FULL-ORACLE │ 30       │ 14        │ 5             │ 11                 │ 46.7%        │
└──────────────────┴──────────┴───────────┴───────────────┴────────────────────┴──────────────┘
```

---

## 2. Breakdown Across the 6 Adversarial Families ($n=5$ per family)

- **Family A (Inverted Onset):**  
  - Ground truth: `cart`. Upstream victim: `frontend`.
  - `B0-EARLIEST`: 0/5 correct (blames `frontend`).
  - `B0-HIGHEST`, `B1`, `B6`, `B4`: 5/5 correct (steady-state root amplitude $z=5.5 > 4.5$).
  - `RIFT-FULL`: 0/5 correct (FCI unoriented on inverted onset without background temporal order).
- **Family B (Client Retry Amplification):**  
  - Ground truth: `payment` ($z=3.5$). Child victim: `checkout` ($z=8.0$).
  - `B0-HIGHEST`, `B1`, `B6`, `B4`: 0/5 correct (all falsely blame `checkout` due to inflated amplitude).
  - `RIFT-FULL-ORACLE`: 2/5 correct (40%), using true directed path `payment -> checkout`.
- **Family C (Shared Infrastructure Confounding):**  
  - Ground truth: `recommendation`. Confounded peer: `product_catalog`.
  - `B3-SIEVE-LIKE`: 0/5 correct (100% false attribution to common caller).
  - `RIFT-FULL-ORACLE`: 0/5 attributed, 5/5 abstained (100% correct abstention on non-identifiable confounding).
- **Family D (Multiple Simultaneous Faults):**  
  - Concurrent roots: `shipping` & `email`.
  - `RIFT-FULL` & `RIFT-FULL-ORACLE`: 5/5 correct (100%).
- **Family E (Noisy Telemetry & Dropouts):**  
  - Ground truth: `product_catalog` with 15% missing telemetry.
  - `RIFT-FULL`: 1/5 correct (20%), `B1`: 4/5 correct (80%).
- **Family F (Deep Cascades):**  
  - 4-tier chain: `redis_cart -> cart -> checkout -> frontend`.
  - `RIFT-FULL` & `RIFT-FULL-ORACLE`: 5/5 correct (100%).
