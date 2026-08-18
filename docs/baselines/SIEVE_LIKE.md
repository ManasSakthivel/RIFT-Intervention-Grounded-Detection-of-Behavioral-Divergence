# Sieve-Like Baseline Documentation
# Phase 3.6 §10
# Status: IMPLEMENTED
# IMPORTANT: Labeled SIEVE-LIKE — not SIEVE

## Naming Clarification

This baseline is labeled **SIEVE-LIKE**, not **SIEVE**.

The exact published Sieve implementation (Huang et al.) is not reproduced here.
If the exact published code is used in future evaluation, it must be re-labeled
as **SIEVE** with the original authors' attribution.

This implementation reproduces the **methodological approach** documented in the
published literature: anomaly-score propagation through a service dependency graph
with causal graph ranking.

## Definition

SIEVE-LIKE implements observational root-cause localization via:
1. Anomaly detection (z-score based, consistent with RIFT's θ_detect)
2. Service dependency graph traversal
3. Propagation-weighted ranking of candidate root causes
4. No interventions (pure observation)
5. No explicit causal identifiability check

## Key Differences from RIFT-FULL

| Dimension | SIEVE-LIKE | RIFT-FULL |
|---|---|---|
| Causal graph | Dependency graph (structural, not learned) | Learned PAG from FCI |
| Identifiability | Not checked | Explicitly checked (ABSTAIN if not identifiable) |
| Intervention | None | Active do(X) intervention |
| Attribution evidence | Observational propagation score | CID + EBD (R1-R4) |
| Confounding | Not distinguished | Explicitly detected and handled |
| Multi-cause | Not distinguished | Explicitly handled |

## Information Received

| Information | SIEVE-LIKE | RIFT-FULL |
|---|---|---|
| Anomaly scores | ✓ | ✓ |
| Call graph topology | ✓ | ✓ |
| Baseline statistics | ✓ | ✓ |
| Learned PAG | **✗** | ✓ |
| Intervention outcome | **✗** | ✓ |
| CID score | **✗** | ✓ |

This is not a disadvantage of the comparison — it reflects the methodological
difference between RIFT (interventional) and Sieve-like (observational).

## Pipeline

```
OBSERVE metrics
  ↓
ANOMALY DETECTION (z-score, θ_detect=3.0)
  ↓
SERVICE DEPENDENCY GRAPH (call graph)
  ↓
ANOMALY PROPAGATION SCORING
  (propagate anomaly backwards through call graph;
   upstream services with high propagation score ranked higher)
  ↓
RANK by propagation score
  ↓
RETURN top-k candidates
```

## Implementation

`src/rift/baselines/sieve_like.py` — `SieveLikeBaseline`

## Status

- Code: IMPLEMENTED (Phase 3.6)
- Documentation: COMPLETE (Phase 3.6)
- Tests: tests/unit/baselines/
- Live validation: PENDING_LINUX

## Citation Obligation

If this baseline is used in a publication, the paper must cite the original
Sieve work and clearly state that this is a METHODOLOGICAL REIMPLEMENTATION,
not the original code. The label SIEVE-LIKE must appear in all tables and figures.
