# RIFT — Baseline Information Matrix
**Phase 3 | Status: IMPLEMENTED**

This document specifies the exact information given to each baseline and ablation.
It is the authoritative record for fair-comparison audits during paper review.

Authority: `docs/baseline_specification.md`, `docs/PHASE_3_SPEC_FREEZE.md §16`

---

## Information Matrix

| Input Component | B1 Threshold | B2 IsoForest | B3 MicroRCA | B4 Sieve | B5 RIFT-OBS | B6 Spectrum | B7 Sage+Chaos | RIFT-FULL |
|---|---|---|---|---|---|---|---|---|
| Prometheus metrics (1s) | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| Distributed traces (100%) | — | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Call graph topology | — | — | ✅ | ✅ | ✅ | — | — | ✅ |
| FCI-learned causal graph G_T | — | — | — | — | ✅ | — | — | ✅ |
| RIFT SCM (M/M/1, queueing) | — | — | — | — | — | — | — | ✅ |
| Identifiability check output | — | — | — | — | ✅ (no interv) | — | — | ✅ |
| Fault injection capability | — | — | — | ✅ | — | — | ✅ | ✅ |
| Intervention outcomes (CID) | — | — | — | Binary only | — | — | — | ✅ |
| Closed-loop update (M.2) | — | — | — | — | — | — | — | ✅ |
| Fault injection budget T=600s | — | — | — | ✅ | — | — | ✅ | ✅ |
| Pre-trained Sage BN | — | — | — | — | — | — | ✅ | — |
| Baseline window (1hr pre) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ground truth (for scoring) | ✅ (held-out) | ✅ (held-out) | ✅ (held-out) | ✅ (held-out) | ✅ (held-out) | ✅ (held-out) | ✅ (held-out) | ✅ (held-out) |

**Note:** Ground truth is withheld during the inference phase and used only for evaluation scoring.

---

## Shared G_T Protocol (RIFT-OBS / B5)

To isolate the effect of intervention from graph-learning differences:

- **B5 (RIFT-OBS)** uses the **same serialized G_T** learned by RIFT-FULL from observational data
- Both use the same FCI run, same PAGResult, same identifiability check output
- The ONLY difference: B5 skips steps 3G–3M (intervention dispatch + CID scoring + closed-loop update)
- B5 uses backdoor adjustment on observational data for causal effect estimation

This ensures that any performance gap between RIFT-FULL and RIFT-OBS is attributable solely to
the interventional signal, not to different causal graph structure learning.

Implementation: `src/rift/baselines/rift_obs.py`

---

## Shared Input Serialization

All baselines consume inputs from a shared serialized format to prevent inadvertent data leakage:

```
datasets/rift_faults/{split}/scenario_{fault_id}/
  ├── metrics.parquet          # Prometheus metrics (all services, 1s resolution)
  ├── traces.jsonl             # OpenTelemetry spans (100% sampled)
  ├── call_graph.json          # Static call graph topology
  ├── baseline_stats.json      # Pre-incident baseline statistics (μ, σ per service/metric)
  ├── incident_window.json     # {t_start, t_end, fault_id}
  └── ground_truth.json        # SEALED — only opened by scoring harness
```

The `ground_truth.json` file is read-protected during baseline inference runs.
The evaluation harness opens it only after all baselines have produced their outputs.

---

## Authorization Scope per Baseline

| Baseline | Can Execute Interventions? | CAP_NET_ADMIN? | Namespace Required |
|---|---|---|---|
| B1–B3, B5, B6 | No | No | None |
| B4 Sieve | Yes (binary outcome only) | Yes | rift-eval-* only |
| B7 Sage+Chaos | Yes (top-3 candidates) | Yes | rift-eval-* only |
| RIFT-FULL | Yes (CID-guided) | Yes | rift-eval-* only |

All baselines that execute interventions are subject to the same 8 safety hard stops
as RIFT-FULL. See `src/rift/safety/safety.py`.

---

## Evaluation Metrics (All Baselines)

| Metric | Description | Primary for H- |
|---|---|---|
| Precision@1 | Root cause is correct top-1 candidate | H1, H3 |
| Precision@3 | Root cause is in top-3 candidates | H1 |
| Detection Latency (s) | Time from fault injection to first CANDIDATE EBD | H3 |
| False Positive Rate (%) | RIFT attributes fault where ground truth is no-fault | H1 |
| Confounded Precision@1 | P@1 on confounded scenarios only | H2 |
| Confounded Abstention Rate | Fraction of confounded scenarios RIFT correctly abstains on | H2 |
| ABSTAIN Rate | Fraction of scenarios where RIFT outputs ABSTAIN (not NONE) | H2 |
| Cost per correct diagnosis (total ED) | Total execution duration for correct diagnoses | H4 |

---

## Ablation Matrix

| Ablation | What is removed | Purpose |
|---|---|---|
| RIFT-FULL | Nothing | Baseline for all comparisons |
| RIFT-OBS (B5) | Intervention + CID + closed-loop | Tests N2: does intervention add info? |
| RIFT-RANDOM | Greedy MSIS replaced by random selection | Tests N3: does cost optimization matter? |
| RIFT-NO-FCI | G_T replaced by call graph | Tests N4: does learned causal graph matter? |
| RIFT-NO-STOP | Entropy stopping criterion disabled | Tests N5: does stopping criterion matter? |

All ablations run on the same DEVELOPMENT split. Final claims use HELD_OUT_TEST only.

---

## Status

| Component | Status |
|---|---|
| Baseline spec (`docs/baseline_specification.md`) | ✅ Complete (Phase 2) |
| Baseline information matrix (this document) | ✅ Complete |
| RIFT-OBS interface (`src/rift/baselines/rift_obs.py`) | ✅ Implemented |
| Sieve interface (`src/rift/baselines/sieve.py`) | ✅ Implemented |
| RIFT-RANDOM ablation (`src/rift/baselines/rift_random.py`) | ✅ Implemented |
| B1 Threshold (`src/rift/baselines/threshold.py`) | PARTIAL — interface only |
| B2 Isolation Forest (`src/rift/baselines/isolation_forest.py`) | PARTIAL — interface only |
| B3 MicroRCA (`src/rift/baselines/microrca.py`) | PARTIAL — interface only |
| B6 Spectrum (`src/rift/baselines/spectrum.py`) | PARTIAL — interface only |
| Full evaluation harness | Phase 10 |
