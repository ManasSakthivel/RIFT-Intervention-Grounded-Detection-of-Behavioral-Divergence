# Oracle Upper Bound Documentation
# Phase 3.6 §12
# Status: IMPLEMENTED

## Definition

The **Oracle Upper Bound** is a reference method that uses known ground-truth
causal structure to perform attribution.

It represents the theoretical maximum performance achievable by any method
that uses the same observational data. It is NOT a deployable RCA method —
no real system has access to the ground-truth causal structure at runtime.

## Purpose

The Oracle establishes an upper bound on Precision@1:
- If RIFT approaches Oracle performance, the causal model (FCI → PAG) is
  nearly as good as knowing the true graph
- If RIFT is far below Oracle, the bottleneck may be graph quality or sample size

## Critical Labeling Requirement

The Oracle MUST be labeled **"ORACLE UPPER BOUND"** in all tables, figures, and
paper text. It MUST NEVER appear in the primary comparison column as if it were
a real baseline.

## Information Received

| Information | Oracle | RIFT-FULL | RIFT-OBS |
|---|---|---|---|
| Ground-truth causal graph | **✓ YES** | ✗ | ✗ |
| Ground-truth root cause | **✓ YES** | ✗ | ✗ |
| Anomaly scores | ✓ | ✓ | ✓ |
| Metrics | ✓ | ✓ | ✓ |

## Pipeline

```
OBSERVE
  ↓
GROUND TRUTH CAUSAL GRAPH (injected from scenario)
  ↓
GROUND TRUTH ROOT CAUSE (known service + fault type)
  ↓
RANK: true root cause gets score=1.0, others get 0.0
  ↓
RETURN attribution with DEFINITIVE confidence
```

## Implementation

`src/rift/baselines/oracle.py` — `OracleUpperBound`

The Oracle receives ground-truth labels via a privileged interface not
available to any real baseline. The scoring harness passes ground-truth
only to Oracle evaluations and must log a WARNING if any other baseline
attempts to access ground-truth labels during run().

## Status

- Code: IMPLEMENTED (Phase 3.6)
- Documentation: COMPLETE (Phase 3.6)
- Tests: tests/unit/baselines/
- Live validation: Not applicable (uses injected ground truth)
