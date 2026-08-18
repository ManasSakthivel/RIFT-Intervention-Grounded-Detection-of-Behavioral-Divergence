# RIFT Ablation Plan

**File:** `docs/experiments/ABLATION_PLAN.md`  
**Status:** AUTHORITATIVE  
**Phase:** 4.5 (Mac pre-Linux readiness sprint)  
**Authority:** `docs/hypotheses.md`, `experiments/ablations/ABLATION_REGISTRY.yaml`

---

## Purpose

This plan specifies all ablation conditions for RIFT, their implementation status,
and the component each tests. Every ablation is defined in
`experiments/ablations/ABLATION_REGISTRY.yaml`.

---

## Ablation Conditions

| ID | Description | Disabled Component | Tests Novelty | Hypothesis | Status |
|---|---|---|---|---|---|
| RIFT-FULL | Full pipeline (reference) | None | — | — | IMPLEMENTED |
| RIFT-OBS | No intervention | Network intervention + CID + closed-loop | N2 | H2 | IMPLEMENTED |
| RIFT-RANDOM | Random intervention selection | MSIS cost optimization | N3 | H4 | IMPLEMENTED |
| RIFT-ONE-SHOT | No closed-loop update | Closed-loop posterior update | N5 | H3 | **NOT_IMPLEMENTED** |
| RIFT-NO-CID | No CID scoring | Wasserstein divergence | N4 | — | NOT_IMPLEMENTED |
| RIFT-NO-EBD | No EBD | Behavioral divergence detection | N4 | — | NOT_IMPLEMENTED |
| RIFT-NO-MSIS | No MSIS | Cost optimization (same as RIFT-RANDOM) | N3 | H4 | IMPLEMENTED |
| RIFT-ALT-GRAPH | Correlation-based DAG | FCI-PAG graph learning | N1 | — | NOT_IMPLEMENTED |

---

## Critical Ablations for Paper Claims

### H2 Critical Ablation: RIFT-OBS
**Experiment:** EXP-005 (dev split), EXP-002 (confounded subset)  
**Question:** Does removing the intervention layer degrade attribution on confounded incidents?  
**Status:** RIFT-OBS is IMPLEMENTED. Requires Linux execution.

If RIFT-OBS achieves the same Conditional P@1 as RIFT-FULL:
- H2 is not confirmed
- Novelty claim N2 (intervention layer provides identifiable causal information) is invalidated
- The paper's core contribution collapses

### H3 Critical Ablation: RIFT-ONE-SHOT
**Experiment:** EXP-013 (multi-cause scenarios)  
**Question:** Does iterative Bayesian update improve over one-shot selection?  
**Status:** RIFT-ONE-SHOT is **NOT IMPLEMENTED**. Must be created before Linux execution.

**Required implementation:**
```
src/rift/baselines/rift_one_shot.py
```
The baseline runs the full intervention engine but uses the initial posterior for all
selections — no update after each observation.

### H4 Critical Ablation: RIFT-RANDOM
**Experiment:** EXP-006, EXP-014  
**Question:** Does MSIS cost optimization reduce total_ed_s vs random selection?  
**Status:** IMPLEMENTED

---

## Input Standardization

All ablation conditions receive the **identical** `IncidentContext`:
- Same metric DataFrames (same service, same window)
- Same `baseline_stats`
- Same `call_graph` topology
- Same scenario `seed`
- Ground truth withheld (scoring harness only)

**No ablation may receive extra information not in `IncidentContext`.**
The automated fairness checks in `tests/unit/baselines/test_baseline_fairness.py`
enforce this at the interface level.

---

## Execution Order

```
Phase 5 (after Linux T1+T2+T3 fixes deployed):
  1. Run RIFT-FULL, RIFT-OBS, RIFT-RANDOM, SIEVE-LIKE, ORACLE on EXP-001 dev split
  2. Run RIFT-FULL, RIFT-OBS on EXP-002 confounded subset (H2)
  3. Implement RIFT-ONE-SHOT → run EXP-013 (H3)
  4. Run RIFT-FULL, RIFT-RANDOM on EXP-014 (H4)

Phase 9 (deferred):
  5. Implement RIFT-NO-CID, RIFT-NO-EBD, RIFT-ALT-GRAPH
  6. Run component-level ablations
```

---

## Implementation Checklist

| Component | Status | Action Required |
|---|---|---|
| RIFT-FULL | ✅ IMPLEMENTED | Deploy T1+T2+T3 fixes on Linux |
| RIFT-OBS | ✅ IMPLEMENTED | Deploy on Linux |
| RIFT-RANDOM | ✅ IMPLEMENTED | Deploy on Linux |
| RIFT-ONE-SHOT | ❌ NOT_IMPLEMENTED | Create `src/rift/baselines/rift_one_shot.py` before EXP-013 |
| RIFT-NO-CID | ❌ NOT_IMPLEMENTED | Deferred to Phase 9 |
| RIFT-NO-EBD | ❌ NOT_IMPLEMENTED | Deferred to Phase 9 |
| RIFT-ALT-GRAPH | ❌ NOT_IMPLEMENTED | Deferred to Phase 9 |

---

## Sage+Chaos

**Status: DEFERRED_TO_PHASE_8**

Sage+Chaos requires pre-labeled fault trace data not yet available.
The `SageChaosStub` always abstains and must not appear in any comparison table.
Do not fabricate Sage+Chaos results.
