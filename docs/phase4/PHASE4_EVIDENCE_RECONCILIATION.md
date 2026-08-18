# Phase 4 Evidence Reconciliation

**File:** `docs/phase4/PHASE4_EVIDENCE_RECONCILIATION.md`  
**Status:** AUTHORITATIVE — do not modify without updating all downstream claim statuses  
**Phase:** 4.5 (Mac pre-Linux readiness sprint)  
**Authority:** `artifacts/phase4/PHASE_4_MANIFEST.json`

---

## Purpose

This document draws strict boundaries between three categories of evidence
produced during RIFT development. These boundaries MUST be maintained in all
paper drafts, reviewer responses, and claims registries.

Mixing evidence categories constitutes scope inflation and invalidates claims.

---

## Evidence Categories

### Category A: Linux Infrastructure Evidence (Frozen, Real)

Evidence collected on `manas1.fyre.ibm.com` (Red Hat Enterprise Linux 9.6,
kernel 5.14.0-570.62.1.el9_6.x86_64) during Phase 4 execution.

**This evidence is real, frozen, and cannot be regenerated on Mac.**

| Item | Artifact | Status | Notes |
|---|---|---|---|
| 513/513 unit tests passing | `artifacts/phase4/PHASE_4_MANIFEST.json` gate 4B | PASS | All test classes pass on Linux Python 3.11.13 |
| Online Boutique 14 containers healthy | `artifacts/phase4/testbed/health.json` | PASS | All services up, frontend HTTP 200 |
| tc/netem 200ms verified | `artifacts/phase4/intervention/net1_latency.json` | PASS | Kernel `tc` executed; 200ms confirmed |
| Packet loss injection | `artifacts/phase4/intervention/net2_packet_loss.json` | PASS | 5% loss verified |
| Rollback complete | `artifacts/phase4/intervention/net3_rollback.json` | PASS | tc rules removed cleanly |
| Wrong-target rejection | `artifacts/phase4/intervention/net4_wrong_target.json` | PASS | Safety rejection confirmed |
| Destination isolation | `artifacts/phase4/intervention/net5_destination_isolation.json` | PASS | Per-destination confirmed |
| Repeated intervention | `artifacts/phase4/intervention/net6_repeated.json` | PASS | Idempotent apply/rollback |
| Intervention failure handling | `artifacts/phase4/intervention/net7_failure.json` | PASS | FAILED status set correctly |
| Safety 8/8 hard stops | `artifacts/phase4/safety/live_safety_results.json` | PASS | All 8 safety guards validated |
| Linux environment verified | `artifacts/phase4/environment/linux_environment.json` | PASS | Docker 29.7.2, Python 3.11.13 |
| Prometheus operational (self-monitoring) | `artifacts/phase4/telemetry/live_validation.json` | PASS | 10 time-series, 104 HTTP requests |
| Jaeger operational | `artifacts/phase4/telemetry/live_validation.json` | PASS | Traces collected |
| Boutique traffic active | `artifacts/phase4/telemetry/live_validation.json` | PASS | Orders/cart/checkout confirmed via docker logs |

**What Category A does NOT include:**
- Live RIFT-to-Prometheus telemetry ingestion (blocked: T1 stub)
- Live causal attribution results on real traffic (blocked: T1 + T2 + T3)
- Final held-out evaluation results

---

### Category B: Synthetic / Mock Pipeline Evidence

Evidence produced on Mac (or Linux) using `MockTelemetry` instead of
`PrometheusClient`. All runs with `synthetic_substitution=True` are in this
category regardless of which machine they ran on.

**This evidence validates pipeline correctness, not live system behavior.**

| Item | Artifact | What It Shows | What It Does NOT Show |
|---|---|---|---|
| Raw P@1 = 0.50 | `artifacts/phase3_5/v1_decomposition.json` | Pipeline logic on synthetic faults | Live system attribution accuracy |
| Conditional P@1 = 0.60 | same | Pipeline logic on synthetic faults | Live system accuracy under confounding |
| FCI vs Oracle comparison | `artifacts/phase4/oracle_vs_fci/comparison.json` | FCI correct on synthetic G_T | FCI correctness on live traffic |
| Baseline results | `artifacts/phase4/baselines/*/result.json` | Baseline code runs | Live baseline performance |
| Safety validation (6/8) | `artifacts/phase3_5/safety_validation.json` | 6 hard stops in dry-run | 2 hard stops requiring live tc |
| Repeatability | `artifacts/phase4/repeatability/repeatability_NL01.json` | Same seed → same result (mock) | Reproducibility with live telemetry |
| Performance latency | `artifacts/phase4/performance/performance.json` | Stage timing on mock run | Runtime on live system |
| E2E pipeline spec | `artifacts/phase3_5/e2e/e2e_pipeline_spec.json` | 17 stages specified | Live E2E validated |

**These values are FROZEN HISTORICAL EVIDENCE.** Do not update them.
They represent the pre-live-validation state and will be superseded by
Category C evidence after Linux E2E with `live_telemetry_used=True`.

**CRITICAL:** The P@1 = 0.50 / 0.60 values MUST NOT appear in the paper as
evidence of live system performance. They may only be cited as:
> "Synthetic validation baseline: raw P@1=50%, conditional P@1=60% on
> development set (36 scenarios, MockTelemetry). See artifacts/phase3_5/
> v1_decomposition.json."

---

### Category C: Future Live RIFT Evidence (Not Yet Collected)

Evidence that requires a live Online Boutique deployment with
`PrometheusClient.collect()` returning real data.

**This evidence does not yet exist. It will be collected in Phase 5.**

| Item | Required Gate | Prerequisite |
|---|---|---|
| `live_telemetry_used=True` RIFTRunRecord | Gate 4G full pass | T1 + T2 + T3 fixes deployed on Linux |
| Live P@1 on development set | EXP-001 | Full E2E with real telemetry |
| Live P@1 on held-out test set | Phase 5 final evaluation | Phase 5 authorization |
| H1–H5 hypothesis test results | Phase 5 | Held-out evaluation + statistical pipeline |
| C001–C006 claim SUPPORTED | Phase 5 | Live E2E results |

**ABSOLUTE RULE:** No result from Category C may be fabricated, estimated,
or derived from Category B data and presented as Category C.

---

## Three-Blocker Summary

The three blockers identified in Phase 4 map exactly to Category A → Category C gaps:

| Blocker | Root Cause | Fix (Phase 4.5 Mac) | Status After Fix |
|---|---|---|---|
| B1: `PrometheusClient.collect()` stub | Category B only: mock data | Implemented in `src/rift/pipeline/e2e_runner.py` (T1) | IMPLEMENTED/MAC_TESTED/NOT_LIVE_VALIDATED |
| B2: Boutique telemetry not wired through OTEL→Prometheus | docker-compose missing OTel Collector service + env vars | Added OTel Collector to docker-compose, updated prometheus.yml (T2) | IMPLEMENTED/MAC_TESTABLE/READY_FOR_LINUX |
| B3: tc band `1:10` invalid on prio qdisc | NetworkInterventionEngine used `tc_handle="10:"` | Fixed to `prio_band=1,2,3` scheme; `NetworkInterventionRecord.__post_init__` validates (T3) | IMPLEMENTED/MAC_TESTED/READY_FOR_LINUX |

After these fixes are deployed on Linux and a single E2E run with
`live_telemetry_used=True` completes, Phase 5 is authorized.

---

## Scope Boundary Enforcement Rules

1. **Paper claims**: Every claim must cite the evidence category explicitly.
   Claims citing Category B as Category A are scientific errors.

2. **Claims registry** (`docs/CLAIMS_REGISTRY.yaml`): Status `SUPPORTED` is only
   valid after Category C evidence is collected. Category B evidence supports
   `PARTIALLY_SUPPORTED` status at most.

3. **Figures and tables**: Must include a footer: "Source: [Category A / B / C]".
   No hardcoded numeric results from Category B may appear in primary comparison
   tables without the Category B label.

4. **Hypothesis testing**: H1–H5 tests MUST NOT be run until Category C evidence
   exists. Running them on Category B data and reporting as hypothesis test results
   is a Type I validity error.

5. **Frozen values**: P@1=0.50, Conditional P@1=0.60 from `v1_decomposition.json`
   must never be modified. They are the pre-validation baseline reference.

---

## Phase 4 Conditional Pass Interpretation

The Phase 4 result of `CONDITIONAL_PASS` means:
- **Infrastructure (Category A)**: All gates pass — Linux, tc, Boutique, safety
- **Pipeline (Category B)**: All synthetic pipeline tests pass
- **Live E2E (Category C)**: BLOCKED by 3 fixable implementation gaps

The conditional pass does NOT represent a full live RIFT attribution result.
It represents confirmation that the testbed is operational and the pipeline is
structurally sound, pending the three implementation fixes above.

---

## Summary Table

| Category | Evidence Type | Frozen? | Use in Paper | Current Status |
|---|---|---|---|---|
| A | Linux infrastructure | ✅ Yes | SUPPORTED for infrastructure claims | Complete |
| B | Synthetic/mock pipeline | ✅ Yes (frozen P@1 values) | PARTIALLY_SUPPORTED for pipeline claims | Complete |
| C | Live RIFT E2E | ❌ Not yet | Required for SUPPORTED on H1–H5 claims | PENDING_LINUX (after T1+T2+T3 fixes) |
