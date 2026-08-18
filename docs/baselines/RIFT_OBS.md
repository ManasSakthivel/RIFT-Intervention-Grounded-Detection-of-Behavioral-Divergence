# RIFT-OBS Baseline Documentation
# Phase 3.6 §8
# Status: IMPLEMENTED

## Definition

**RIFT-OBS** is the "RIFT without intervention" ablation baseline.

It receives the **same serialized G_T** as RIFT-FULL and uses the same
causal model (FCI → PAG → identifiability). The only intended difference
is the absence of the intervention layer and its downstream evidence.

## Purpose

Tests **N2**: *Does the intervention layer add measurable information
beyond the observational causal model alone?*

If RIFT-OBS achieves the same Precision@1 as RIFT-FULL, the intervention
layer provides no measurable benefit and N1/N2 claims collapse.
This is an explicit adversarial test of the core RIFT claim.

## Information Received

| Information | RIFT-FULL | RIFT-OBS |
|---|---|---|
| Anomaly scores (z-scores) | ✓ | ✓ |
| Serialized G_T (same object) | ✓ | ✓ |
| PAG from FCI | ✓ | ✓ |
| Identifiability status | ✓ | ✓ |
| Call graph topology | ✓ | ✓ |
| Baseline metric statistics | ✓ | ✓ |
| do(X) intervention outcome | ✓ | **✗ NOT RECEIVED** |
| CID(X→Y, t) score | ✓ | **✗ NOT RECEIVED** |
| Closed-loop posterior update | ✓ | **✗ NOT RECEIVED** |

The information parity constraint is enforced by the test suite.
See `tests/unit/baselines/test_rift_obs_parity.py`.

## Pipeline

```
OBSERVE
  ↓
ANOMALY DETECTION
  ↓
G_T (same serialized graph as RIFT-FULL)
  ↓
ANOMALY SUBGRAPH (Strategy D)
  ↓
FCI → PAG
  ↓
IDENTIFIABILITY CHECK
  ↓
OBSERVATIONAL EFFECT ESTIMATE (correlation proxy, NOT do-calculus)
  ↓
EBD (R1-R3 only; R4 skipped — no intervention evidence)
  ↓
ATTRIBUTION / ABSTENTION
```

## Known Limitations

**L1**: The observational effect estimate uses Pearson correlation as a
proxy for P(Y | do(X)). This is NOT the true do-calculus causal effect.
Full backdoor adjustment is deferred to Phase 8 baseline evaluation.

**L2**: RIFT-OBS cannot achieve DEFINITIVE EBD confidence (requires R4).
Maximum confidence is CANDIDATE (R1-R3 satisfied).

**L3**: On NOT_IDENTIFIABLE scenarios, RIFT-OBS must also abstain
(identifiability is a property of the causal graph, not of interventions).

## Implementation

`src/rift/baselines/rift_obs.py` — `RIFTObsBaseline`

## Status

- Code: IMPLEMENTED (Phase 3.5)
- Documentation: COMPLETE (Phase 3.6)
- Tests: tests/unit/baselines/
- Live validation: PENDING_LINUX
