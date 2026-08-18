# Phase 3.5 — Supplementary Gates Status
**Gates 3.5H / 3.5J / 3.5K / 3.5L / 3.5M**

| Gate | Title | Status |
|---|---|---|
| 3.5H | Oracle vs FCI PAG Comparison | SPECIFICATION_COMPLETE — EXECUTION PENDING |
| 3.5J | Live Fault Classes Evaluation | EVALUATION_PLAN_COMPLETE — EXECUTION PENDING |
| 3.5K | Confounded Scenario Evaluation | SCENARIOS_SPECIFIED — EXECUTION PENDING |
| 3.5L | Closed-Loop Repeatability | PLAN_COMPLETE — EXECUTION PENDING |
| 3.5M | Performance Latency Measurement | SPECIFICATION_COMPLETE — MEASUREMENT PENDING |

All five gates are blocked by the same prerequisite: **Online Boutique deployment on Linux with resolved Prometheus/gRPC telemetry**.

## Gate 3.5H — Oracle vs FCI
Oracle V1=50% (Phase 3). FCI-estimated V1 unknown. Full plan in [`artifacts/phase3_5/oracle_vs_fci.json`](../../artifacts/phase3_5/oracle_vs_fci.json).

## Gate 3.5J — Fault Classes
Oracle results show: IDENTIFIED (NL, PL, QU, confounded), PARTIALLY_SUPPORTED with R3 limitation (SD, DF, MC), ABSTAINED (confounded). See [`artifacts/phase3_5/fault_class_results.json`](../../artifacts/phase3_5/fault_class_results.json).

## Gate 3.5K — Confounded Scenarios
Four live Online Boutique confounded scenarios specified: shared_redis, shared_product_catalog, network_congestion, common_currency. See [`artifacts/phase3_5/confounded_results.json`](../../artifacts/phase3_5/confounded_results.json).

## Gate 3.5L — Repeatability
5-run plan for NL_01 scenario with pre-seeded runs [1001-1005]. HIGH_VARIANCE threshold: IQR > 0.3 × median. Cherry-picking prevention: all 5 runs reported. See [`artifacts/phase3_5/repeatability_plan.json`](../../artifacts/phase3_5/repeatability_plan.json).

## Gate 3.5M — Latency
Latency targets: CANDIDATE ~30s, DEFINITIVE 120-300s. All stages pending live measurement. See [`artifacts/phase3_5/performance_latency.json`](../../artifacts/phase3_5/performance_latency.json).
