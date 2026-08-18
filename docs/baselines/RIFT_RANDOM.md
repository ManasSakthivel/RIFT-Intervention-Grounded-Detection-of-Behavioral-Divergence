# RIFT-RANDOM Baseline Documentation
# Phase 3.6 §9
# Status: IMPLEMENTED

## Definition

**RIFT-RANDOM** is the "RIFT with random intervention selection" ablation baseline.

It is identical to RIFT-FULL **except** the greedy MSIS cost optimizer is replaced
by uniform-random intervention selection from the eligible set.

## Purpose

Tests **N3**: *Does the cost optimization / EIG-guided intervention selection
matter for attribution quality?*

If RIFT-RANDOM achieves similar Precision@1 and detection latency as RIFT-FULL,
the greedy MSIS optimization layer provides no measurable benefit.

Expected result: RIFT-FULL should outperform RIFT-RANDOM on:
- Detection latency (fewer, more targeted interventions)
- Total execution duration cost (less wasted ED budget)
- Attribution accuracy on confounded scenarios (better EIG targeting)

## Information Received

| Information | RIFT-FULL | RIFT-RANDOM |
|---|---|---|
| Candidate intervention set | ✓ | ✓ (same) |
| Causal graph G_T | ✓ | ✓ (same) |
| Observations / metrics | ✓ | ✓ (same) |
| Intervention budget T | ✓ | ✓ (same) |
| Safety constraints | ✓ | ✓ (same) |
| Authorization levels | ✓ | ✓ (same) |
| Greedy EIG-maximizing selection | ✓ | **✗ REPLACED BY RANDOM** |

The information parity constraint is verified by the test suite.
See `tests/unit/baselines/test_rift_random_fairness.py`.

## Fairness Requirements

The comparison is fair only if:
1. The candidate set is identical
2. The stopping conditions are identical (entropy threshold, budget)
3. The posterior update rule is identical (same Bayesian update)
4. The only difference is greedy → uniform-random selection
5. The same random seed is used for each scenario in repeated runs

## Implementation

`src/rift/baselines/rift_random.py` — `RandomMSIS`, `RIFTRandomBaseline`

## Status

- Code: IMPLEMENTED (Phase 3.5 / 3.6)
- Documentation: COMPLETE (Phase 3.6)
- Tests: tests/unit/baselines/
- Live validation: PENDING_LINUX
