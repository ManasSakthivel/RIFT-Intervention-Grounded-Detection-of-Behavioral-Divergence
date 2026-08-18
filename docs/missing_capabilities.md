# RIFT — Missing Capabilities
**Phase 0 | Version 1.0**

---

## Overview

Everything is missing. This document prioritizes what must be built, in what order, and what the blocker dependencies are.

All items are labeled **MISSING** unless otherwise noted.

---

## Critical Path (Cannot Skip or Reorder)

```
[Phase 1]  Literature confirmed → novelty claim verified
     ↓
[Phase 2]  Formal problem definition → causal assumptions stated
     ↓
[Phase 3]  Behavioral state graph → state representation specified
     ↓
[Phase 4]  Trace collection pipeline → observable data exists
     ↓
[Phase 5]  Intervention engine → causal experiments possible
     ↓
[Phase 6]  RIFT/EBD algorithm → core contribution implemented
     ↓
[Phase 7]  Benchmark (frozen before eval) → ground truth exists
     ↓
[Phase 8]  Baselines implemented → comparison possible
     ↓
[Phase 9]  Ablations → component necessity proven
     ↓
[Phase 10] Full evaluation → results exist
```

---

## Missing Capabilities by Category

### 1. Formal Foundations (Phase 2)

| Capability | Why Needed | Blocker For | Status |
|---|---|---|---|
| Formal definition of "behavioral divergence" | All claims rest on this; reviewer will attack informality | Everything | MISSING |
| Structural Causal Model (SCM) for distributed services | Required to apply do-calculus | Intervention engine, algorithm | MISSING |
| Causal graph specification language | How to express service dependencies as a DAG | Graph learning, intervention selection | MISSING |
| Identifiability checker | Determines if a causal query is answerable from data | Causal queries | MISSING |
| Formal statement of assumptions (causal sufficiency, etc.) | Must state what is assumed; reviewers will check | Paper credibility | MISSING |

---

### 2. Execution Instrumentation (Phase 4)

| Capability | Why Needed | Blocker For | Status |
|---|---|---|---|
| OpenTelemetry trace collection pipeline | Source of behavioral observations | All experiments | MISSING |
| Prometheus metrics collection | Baseline state + deviation detection | Divergence scoring | MISSING |
| State vector extraction from traces | Convert raw spans to structured state | Algorithm input | MISSING |
| Vector clock reconstruction | Establish happened-before ordering | Causal graph learning | MISSING |
| Trace-to-DAG alignment | Map trace structure to causal graph nodes | Graph learning | MISSING |
| Baseline (fault-free) trace archive | Counterfactual baseline comparison | Divergence metric | MISSING |

---

### 3. Intervention Engine (Phase 5)

| Capability | Why Needed | Blocker For | Status |
|---|---|---|---|
| Fault injection framework (LitmusChaos or equivalent) | Execute do(X := x) in the real system | All causal experiments | MISSING |
| Intervention atomicity wrapper | Ensure do-operator is applied cleanly | Causal validity | MISSING |
| Intervention reversibility guarantee | Must be able to undo do(X := x) | Production safety | MISSING |
| SLA guard rails | Prevent runaway interventions from cascading | Production safety | MISSING |
| Intervention scheduler | Sequence interventions without interference | Experimental validity | MISSING |
| Blast radius limiter | Contain intervention to target service | Production safety | MISSING |
| Intervention log | Record what was done, when, to what | Ground truth | MISSING |

---

### 4. Core Algorithm — RIFT/EBD (Phase 6)

| Capability | Why Needed | Blocker For | Status |
|---|---|---|---|
| Causal graph learning (PC algorithm or equivalent) | Discover service dependencies from traces | All causal queries | MISSING |
| Online causal graph update | Handle concept drift in service behavior | Temporal validity | MISSING |
| do-calculus query evaluator | Compute P(Y \| do(X := x)) | Attribution | MISSING |
| Backdoor adjustment computation | Remove confounders from causal estimate | Valid causal estimates | MISSING |
| Counterfactual outcome sampler | Generate predicted outcome under intervention | Comparison | MISSING |
| Divergence metric (Total Variation Distance) | Quantify how much behavior changed | Detection threshold | MISSING |
| Root cause ranker | Rank candidate components by causal responsibility | Final output | MISSING |
| Minimum intervention set selector | Choose smallest set of interventions for confirmation | Efficiency | MISSING |
| SPRT online detector | Real-time detection with false positive control | Online operation | MISSING |

---

### 5. Benchmark (Phase 7)

| Capability | Why Needed | Blocker For | Status |
|---|---|---|---|
| Benchmark application deployment (Online Boutique or equivalent) | Target system for experiments | All experiments | MISSING |
| Fault injection scripts (≥4 fault types) | Ground truth generation | Evaluation | MISSING |
| Multi-channel ground truth oracle | Credible labels for detection accuracy | All metrics | MISSING |
| Workload generator | Realistic request patterns | Representative experiments | MISSING |
| Trace archival pipeline | Preserve raw data for reproducibility | Reproducibility | MISSING |
| Benchmark metadata manifest | Document what is in the dataset | Artifact evaluation | MISSING |

---

### 6. Baselines (Phase 8)

| Capability | Why Needed | Blocker For | Status |
|---|---|---|---|
| Isolation Forest baseline | Classic unsupervised anomaly detection | Comparison | MISSING |
| Prometheus rule-based baseline | Simple production heuristic | Comparison | MISSING |
| Correlational RCA baseline (e.g., MicroRCA-style) | Direct competitor in the same problem space | Comparison | MISSING |
| Chaos-only baseline (injection without causal inference) | Ablation of the causal layer | Necessity proof | MISSING |
| Statistical debugging baseline | Prior FL method adapted to runtime | Comparison | MISSING |

---

### 7. Evaluation Infrastructure (Phase 10)

| Capability | Why Needed | Blocker For | Status |
|---|---|---|---|
| Experiment runner (reproducible, seeded) | Reproducibility | Artifact evaluation | MISSING |
| Statistical test suite (Mann-Whitney, bootstrap CI) | Significance claims | All metric reports | MISSING |
| Figure generation pipeline | Paper figures | Submission | MISSING |
| Result archival (DVC or equivalent) | Reproducible results | Artifact | MISSING |
| CLAIMS.md (claim → experiment → result mapping) | Artifact evaluation | AE badge | MISSING |

---

### 8. Artifact Package (Phase 13)

| Capability | Why Needed | Blocker For | Status |
|---|---|---|---|
| Dockerfile (single-command setup) | AE functional badge | Artifact submission | MISSING |
| REPRODUCE.md (step-by-step replication) | AE functional badge | Artifact submission | MISSING |
| Persistent archive (Zenodo DOI) | AE available badge | Artifact submission | MISSING |
| requirements.txt (exact versions) | Reproducibility | Artifact submission | MISSING |
| CI/CD pipeline (.github/workflows) | Ongoing reproducibility | Credibility | MISSING |

---

## Priority Order for Implementation

1. Formal definitions (Phase 2) — nothing else is valid without these
2. Trace pipeline (Phase 4) — generates the data everything depends on
3. Intervention engine (Phase 5) — required for causal claims
4. Benchmark (Phase 7) — must be frozen BEFORE algorithm is evaluated
5. Algorithm (Phase 6) — evaluated against frozen benchmark only
6. Baselines (Phase 8) — evaluated on same frozen benchmark
7. Ablations (Phase 9) — evaluated on same frozen benchmark
8. Statistics + paper (Phases 12–14)
