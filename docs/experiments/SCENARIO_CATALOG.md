# RIFT Scenario Catalog

**File:** `docs/experiments/SCENARIO_CATALOG.md`  
**Status:** AUTHORITATIVE  
**Phase:** 4.5 (Mac pre-Linux readiness sprint)  
**Authority:** `datasets/rift_faults/`, `datasets/rift_faults/manifest.json`

---

## Overview

All scenarios are in `datasets/rift_faults/`. The manifest is at
`datasets/rift_faults/manifest.json`.

| Split | File | n_scenarios | Purpose |
|---|---|---|---|
| DEVELOPMENT | `development.json` | 50 | Method development, tuning |
| VALIDATION | `validation.json` | 18 | Hyperparameter validation |
| HELD_OUT_TEST | `held_out_test.json` | 15 | **Final evaluation only** |

**Total: 83 scenarios** (35 non-confounded + 48 confounded)

**P0-02 fix:** Development set expanded from 36 to 50 scenarios by adding:
- 11 new MULTI_CAUSE scenarios (MC_02–MC_12, seeds 100–110)
- 3 new AMBIGUOUS_ATTRIBUTION scenarios (AA_01–AA_03, seeds 111–113)
- Total multi_cause_or_ambiguous = 15 (EXP-013 filter); Wilcoxon achievable at n=15.
- Confounded count unchanged = 24 in development (48 total across all splits — H2 power met).

---

## Held-Out Test Set Policy

The held-out test set (`datasets/rift_faults/held_out_test.json`) is **SEALED**.

- It MUST NOT be used during method development, threshold tuning, or ablation analysis
- Access is controlled by `src/rift/evaluation/held_out_guard.py`
- Verification script: `scripts/verify_heldout_sealed.py`
- Only authorized oracle token can open it (Phase 5 final evaluation)

**Any use of held-out labels before Phase 5 authorization invalidates the evaluation.**

---

## Fault Type Distribution

### Development Set (50 scenarios)

| Fault Type | Count | Confounded | Observable |
|---|---|---|---|
| NETWORK_LATENCY | 2 | No | Yes |
| PACKET_LOSS | 2 | No | Yes |
| SERVICE_DEGRADATION | 2 | No | Yes |
| RESOURCE_CONTENTION | 2 | No | Yes |
| QUEUEING | 2 | No | Yes |
| DEPENDENCY_FAILURE | 1 | No | Yes |
| MULTI_CAUSE | 12 | No | Yes |
| AMBIGUOUS_ATTRIBUTION | 3 | No | Yes |
| CONFOUNDED | 24 | Yes | Partial |
| **Total** | **50** | **24** | — |

**MULTI_CAUSE scenarios (12):** MC_01–MC_12
Each has a distinct combination of two simultaneously injected faults, different service
pairs, and different causal path structures. Seeds 43, 100–110 (all different).

**AMBIGUOUS_ATTRIBUTION scenarios (3):** AA_01–AA_03
Scenarios where ≥2 services are plausible root causes under observational analysis alone.
Require closed-loop CID intervention to resolve. Test H3 (closed-loop vs one-shot).

### Validation Set (18 scenarios)

Subset of all fault types for threshold validation. Ground truth locked.

### Held-Out Test Set (15 scenarios)

**SEALED.** Contents unknown until Phase 5 authorization.

---

## Scenario Schema

Each scenario in the JSON files has the following fields:

| Field | Type | Description |
|---|---|---|
| `fault_id` | string | Unique identifier (e.g., "NL_01") |
| `name` | string | Human-readable description |
| `root_cause_service` | string | Ground truth: the service causing the fault |
| `fault_type` | string | One of the fault classes above |
| `injected_at_t` | float | Unix offset (seconds) when fault was injected |
| `expected_recovery_t` | float | Expected recovery time |
| `causal_path` | list of edges | Ground truth causal propagation path |
| `confounded` | bool | True if shared infrastructure confounder present |
| `confounder_description` | string/null | Description of confounding mechanism |
| `affected_services` | list | All services impacted |
| `observable_by_rift` | bool | True if root cause is within RIFT's instrumentation boundary |
| `split` | string | DEVELOPMENT / VALIDATION / HELD_OUT_TEST |
| `ground_truth_locked` | bool | True = locked, do not modify |
| `seed` | int | RNG seed for scenario generation |

---

## Fault Class Descriptions

### Non-Confounded Faults (21 scenarios)

| Class | Description | Expected RIFT Behavior |
|---|---|---|
| NETWORK_LATENCY | tc netem adds latency to target service | Attribution DEFINITIVE at root-cause service |
| PACKET_LOSS | tc netem drops packets on link | Attribution CANDIDATE; R3 confirmed by CID |
| SERVICE_DEGRADATION | Service becomes slow (CPU stress) | Attribution via EBD R1+R2; CID confirms |
| RESOURCE_CONTENTION | Shared DB/resource bottleneck | Attribution at upstream resource holder |
| QUEUEING | High request rate saturates service | Attribution to bottleneck service |
| DEPENDENCY_FAILURE | Downstream returns errors | Attribution at failure point; boundary_limited possible |
| MULTI_CAUSE | Two faults in same window | Multi-cause attribution; closed-loop required |

### Multi-Cause and Ambiguous Faults (15 scenarios in development, for H3)

The `multi_cause_or_ambiguous` filter (EXP-013) selects:
- `fault_type = MULTI_CAUSE`: 12 scenarios (MC_01–MC_12)
- `fault_type = AMBIGUOUS_ATTRIBUTION`: 3 scenarios (AA_01–AA_03)

Total for H3 Wilcoxon test: n=15. Achieved power ≈ 64% (δ=0.30, α=0.05, one-sided).

These scenarios are scientifically distinct: different service pairs, different causal
structures, different seeds, different fault type combinations.

### Confounded Faults (48 scenarios, all splits combined)

| Description | FCI Outcome | RIFT Behavior |
|---|---|---|
| Shared physical host causes correlated anomalies in 2 services | Bidirected edge in PAG | Abstain or MULTI_CAUSE; correct_abstention_rate measured |
| External CDN failure affects all frontend services | Boundary limited | boundary_limited=True; attribution to first affected internal service |
| Noisy neighbor on same VM | PAG uncertain | Low-confidence attribution; RIFT-OBS vs RIFT-FULL gap tested (H2) |

---

## Coverage Analysis

The 69 scenarios cover:
- All fault types from the RIFT fault taxonomy (8 classes)
- All services in the Online Boutique call graph (10 services)
- Confounded subset: 48 scenarios (meets H2 power requirement of n≥48)
- Non-identifiable subset: embedded in confounded scenarios

**Power note from `manifest.json`:**
> "48 confounded scenarios generated; 80% power claimed for H2"

This claim is valid only when all 48 confounded scenarios are collected in the live run.
If fewer are collected (e.g., some scenarios fail to trigger), see
`src/rift/statistics/stats.py::check_power_achieved()` for achieved power calculation.

---

## Scenario Access Rules

| Code Path | Can Access Development | Can Access Validation | Can Access Held-Out |
|---|---|---|---|
| Method development | ✅ Yes | ✅ Yes | ❌ No |
| Threshold tuning | ✅ Yes | ✅ Yes | ❌ No |
| Ablation experiments | ✅ Yes | ✅ Yes | ❌ No |
| Confirmatory H1–H5 tests | ✅ Yes (for development estimates) | ✅ Yes | ❌ No |
| Final held-out evaluation | — | — | ✅ Phase 5 only |
| Oracle baseline | ✅ Yes (oracle token) | ✅ Yes | ✅ Phase 5 only |
