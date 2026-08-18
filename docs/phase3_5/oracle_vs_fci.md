# Phase 3.5 — Oracle vs FCI PAG Analysis
**Gate 3.5H | Status: SPECIFICATION_COMPLETE — EXECUTION PENDING**

The oracle PAG validation (Phase 3) achieved V1=50% on the DEVELOPMENT split (n=12 non-confounded scenarios). This represents the **upper bound** on RIFT's P@1 — it bypasses FCI estimation error entirely.

The FCI-estimated PAG performance on live telemetry is **not yet measured**. This requires Online Boutique deployment on Linux with real Prometheus/Jaeger data.

## Key Distinction

| Mode | PAG Source | V1 P@1 | Status |
|---|---|---|---|
| Oracle | Ground-truth `causal_path` | 50% | Measured (Phase 3) |
| FCI-estimated | Live telemetry → FCI → PAG | Unknown | Pending live deployment |

## Expected Direction of Gap
FCI introduces finite-sample independence test errors, faithfulness violations, and ambiguous edge marks (o-o, o->). These expand the NOT_IDENTIFIABLE set and may produce false bidirected edges. Realistic estimate: FCI V1 ≤ Oracle V1.

## Path to Measurement
See [`artifacts/phase3_5/oracle_vs_fci.json`](../../artifacts/phase3_5/oracle_vs_fci.json) for the full comparison plan.
