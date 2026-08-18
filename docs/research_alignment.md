# RIFT — Research Alignment Map
**Phase 0 | Version 1.0**

---

## Purpose

This document is the **single source of truth** that connects every research question to its implementation, experiment, metric, artifact, and paper section. It is updated at every phase gate. Any claim that cannot be traced through this map must not appear in the paper.

---

## How to Read This Document

Each row follows this chain:

```
Research Question → Implementation → Experiment → Metric → Artifact → Paper Section
```

A `MISSING` in any cell means the chain is broken and the claim cannot yet be made.

---

## Alignment Table

### RQ1 — Core Detection Question

> **Can do-calculus-grounded interventions detect behavioral divergence more precisely than observational methods alone?**

| Dimension | Detail | Status |
|---|---|---|
| **Research Question** | Does `P(Y \| do(X := x))` diverge from `P(Y \| X = x_obs)` in a detectable, attributable way? | DEFINED |
| **Formal Definition Required** | Structural Causal Model for service interactions; divergence = TV distance > τ | MISSING (Phase 2) |
| **Implementation** | RIFT/EBD algorithm: causal graph learning + do-query evaluator + divergence scorer | MISSING (Phase 6) |
| **Experiment** | EXP-001: Detection accuracy on frozen benchmark (Online Boutique + Sock Shop) | MISSING (Phase 10) |
| **Metric** | Precision, Recall, F1, AUROC; compared against Isolation Forest + MicroRCA baseline | MISSING (Phase 10) |
| **Statistical Test** | Mann-Whitney U; 95% bootstrap CI; p < 0.05; effect size (Cliff's delta) | MISSING (Phase 12) |
| **Artifact** | `experiments/exp_001_detection_accuracy.sh` → `results/tables/exp_001.csv` | MISSING (Phase 10) |
| **Paper Section** | §4 Evaluation — RQ1 | MISSING (Phase 14) |
| **Reviewer Risk** | R1 (causal cosmetic), R5 (missing baselines) | See `reviewer_risks.md` |

---

### RQ2 — Necessity Question

> **Is intervention necessary? Does removing the causal inference layer measurably degrade performance?**

| Dimension | Detail | Status |
|---|---|---|
| **Research Question** | Is `RIFT_full > RIFT_no_intervention` on root cause precision? | DEFINED |
| **Formal Definition Required** | RIFT_no_intervention = chaos injection + anomaly detection, no do-calculus | MISSING (Phase 9) |
| **Implementation** | Ablation variant: intervention engine disabled; direct anomaly scoring on traces | MISSING (Phase 9) |
| **Experiment** | EXP-009: Ablation — RIFT full vs. RIFT without intervention layer | MISSING (Phase 9) |
| **Metric** | Root cause precision (did the top-1 attributed component match ground truth?) | MISSING (Phase 9) |
| **Statistical Test** | Paired Wilcoxon signed-rank test (same faults, different methods) | MISSING (Phase 12) |
| **Artifact** | `experiments/exp_009_ablation_intervention.sh` → `results/tables/exp_009.csv` | MISSING (Phase 9) |
| **Paper Section** | §4 Evaluation — RQ2 (Ablation) | MISSING (Phase 14) |
| **Reviewer Risk** | R1 (this is the FATAL risk — this experiment is the answer to it) | See `reviewer_risks.md` |

---

### RQ3 — Causal Assumptions Question

> **Do the causal assumptions (acyclicity, faithfulness, causal sufficiency) approximately hold in the experimental setting, and are the results robust to violations?**

| Dimension | Detail | Status |
|---|---|---|
| **Research Question** | Are the conditions for do-calculus validity satisfied in the benchmark systems? | DEFINED |
| **Formal Definition Required** | Explicit statement of: DAG assumption, causal Markov condition, faithfulness, no unmeasured confounders | MISSING (Phase 2) |
| **Implementation** | Identifiability checker; cycle detector in learned graph; sensitivity analysis module | MISSING (Phase 6) |
| **Experiment** | EXP-010: Test acyclicity of learned graphs; sensitivity analysis with synthetic unmeasured confounder | MISSING (Phase 11) |
| **Metric** | % of learned graphs that are DAGs; sensitivity bound (Rosenbaum Γ) | MISSING (Phase 11) |
| **Statistical Test** | Not a hypothesis test; descriptive analysis + sensitivity bounds | MISSING (Phase 12) |
| **Artifact** | `experiments/exp_010_assumption_validation.sh` → `results/tables/exp_010.csv` | MISSING (Phase 11) |
| **Paper Section** | §3 Methodology — Assumptions; §5 Threats to Validity | MISSING (Phase 14) |
| **Reviewer Risk** | R4 (causal assumptions not stated) | See `reviewer_risks.md` |

---

### RQ4 — Ground Truth Question

> **Is the benchmark ground truth credible? Can the oracle be independently validated?**

| Dimension | Detail | Status |
|---|---|---|
| **Research Question** | Is the ground truth (fault injection log + multi-channel consensus) reliable enough to support precision/recall claims? | DEFINED |
| **Formal Definition Required** | Ground truth = multi-channel consensus: metrics deviation + fault log + trace divergence + system events | MISSING (Phase 7) |
| **Implementation** | Multi-channel oracle: `ground_truth/oracle.py` | MISSING (Phase 7) |
| **Experiment** | EXP-007: Inter-trial agreement across 3+ runs of same fault; oracle consistency rate | MISSING (Phase 7) |
| **Metric** | Inter-trial agreement ≥ 95%; labeling confidence distribution | MISSING (Phase 7) |
| **Statistical Test** | Cohen's kappa for inter-rater agreement (channels as raters) | MISSING (Phase 7) |
| **Artifact** | `datasets/ground_truth_manifest.json` + `experiments/exp_007_oracle_validation.sh` | MISSING (Phase 7) |
| **Paper Section** | §3 Methodology — Benchmark Design; §5 Threats to Validity | MISSING (Phase 14) |
| **Reviewer Risk** | R3 (toy benchmark) | See `reviewer_risks.md` |

---

### RQ5 — Generalization Question

> **Does RIFT generalize across systems and fault types not seen during development?**

| Dimension | Detail | Status |
|---|---|---|
| **Research Question** | Is RIFT's performance on system B (unseen) within Y% of its performance on system A (training)? | DEFINED |
| **Formal Definition Required** | Cross-system protocol: train on {A}, test on {B}; fault-type hold-out: train on {crash, network}, test on {logic, timing} | MISSING (Phase 11) |
| **Implementation** | System-stratified evaluation split; fault-type stratified split | MISSING (Phase 11) |
| **Experiment** | EXP-011: Cross-system transfer; EXP-012: Fault-type hold-out | MISSING (Phase 11) |
| **Metric** | OOD F1 ≥ 70% of in-distribution F1; degradation curve | MISSING (Phase 11) |
| **Statistical Test** | Bootstrap CI on OOD metrics; report degradation with bounds | MISSING (Phase 12) |
| **Artifact** | `experiments/exp_011_generalization.sh` + `results/tables/exp_011.csv` | MISSING (Phase 11) |
| **Paper Section** | §4 Evaluation — RQ3 (Generalization) | MISSING (Phase 14) |
| **Reviewer Risk** | R3 (toy benchmark), R7 (graph assumed) | See `reviewer_risks.md` |

---

### RQ6 — Efficiency Question

> **What is the overhead of RIFT on the monitored system, and how quickly does it detect divergence?**

| Dimension | Detail | Status |
|---|---|---|
| **Research Question** | Does RIFT add < X% CPU/memory overhead and detect divergence within Y seconds? | DEFINED |
| **Formal Definition Required** | Overhead = (resource usage with RIFT) − (resource usage without RIFT) / baseline; detection latency = time from fault injection to alert | MISSING (Phase 4/5) |
| **Implementation** | Overhead profiler; detection latency timer from injection log to alert | MISSING (Phase 6) |
| **Experiment** | EXP-004: CPU/memory/network overhead; EXP-005: Detection latency distribution | MISSING (Phase 10) |
| **Metric** | CPU overhead < 5%; memory < 10%; detection p50 < 30s, p99 < 120s | MISSING (Phase 10) |
| **Statistical Test** | Descriptive statistics; percentile distribution; confidence intervals | MISSING (Phase 12) |
| **Artifact** | `experiments/exp_004_overhead.sh` + `experiments/exp_005_latency.sh` | MISSING (Phase 10) |
| **Paper Section** | §4 Evaluation — RQ4 (Efficiency) | MISSING (Phase 14) |
| **Reviewer Risk** | R8 (detection latency not measured) | See `reviewer_risks.md` |

---

## Experiment Registry

| Experiment ID | Research Question | Phase | Status |
|---|---|---|---|
| EXP-001 | RQ1 — Detection accuracy vs. baselines | 10 | MISSING |
| EXP-002 | RQ1 — Precision/recall breakdown by fault type | 10 | MISSING |
| EXP-003 | RQ1 — False positive rate in production-like setting | 10 | MISSING |
| EXP-004 | RQ6 — Monitoring overhead | 10 | MISSING |
| EXP-005 | RQ6 — Detection latency distribution | 10 | MISSING |
| EXP-006 | RQ5 — Scalability (services 5 → 50) | 10 | MISSING |
| EXP-007 | RQ4 — Oracle consistency / ground truth validation | 7 | MISSING |
| EXP-008 | RQ6 — Hyperparameter sensitivity | 9 | MISSING |
| EXP-009 | RQ2 — **Ablation: causal layer necessity** | 9 | MISSING |
| EXP-010 | RQ3 — Causal assumption validation | 11 | MISSING |
| EXP-011 | RQ5 — Cross-system generalization | 11 | MISSING |
| EXP-012 | RQ5 — Fault-type hold-out | 11 | MISSING |

---

## Traceability Checklist (Pre-Submission Gate)

Before any paper claim is written, verify:

- [ ] The claim traces to a Research Question in this document
- [ ] The RQ traces to an Experiment (EXP-XXX)
- [ ] The Experiment has a result file in `results/`
- [ ] The result file has a 95% CI
- [ ] The claim is supported by p < 0.05 significance where applicable
- [ ] The claim does not appear in the paper if any cell in its row is MISSING

*This document is updated at every phase gate.*
