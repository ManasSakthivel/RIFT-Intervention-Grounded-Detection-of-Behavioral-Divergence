# RIFT Paper Evidence Matrix
# Phase 3.6 §23
# Authority: Phase 3.6 specification §23
#
# This document maps each research question and hypothesis to its
# experimental evidence, metric, and current status.
#
# Do NOT write the paper. Build the evidence infrastructure.

## Research Questions

| RQ | Question | Status |
|---|---|---|
| RQ1 | Can RIFT perform accurate causal attribution on live distributed systems? | PLANNED |
| RQ2 | Does RIFT correctly handle confounded incidents and non-identifiable queries? | PLANNED |
| RQ3 | Does RIFT's cost-optimized intervention selection improve efficiency? | PLANNED |
| RQ4 | Is RIFT's causal evidence (CID+EBD) reproducible and statistically valid? | PARTIALLY_SUPPORTED |
| RQ5 | Does RIFT generalize across system deployments? | PLANNED |

---

## Evidence Matrix

| RQ | Claim | Experiment | Metric | Baseline | Artifact | Current Status | Required Evidence |
|---|---|---|---|---|---|---|---|
| RQ1 | RIFT > baselines on P@1 | EXP-001 | precision_at_1 | RIFT-OBS, RIFT-RANDOM, SIEVE-LIKE | results/EXP-001/ | PLANNED | Live Linux E2E + H1 Wilcoxon |
| RQ1 | RIFT attribution > RIFT-OBS | EXP-005 | Δ P@1 (RIFT vs OBS) | RIFT-OBS | results/EXP-005/ | PLANNED | Live Linux E2E |
| RQ1 | FCI-PAG approximates true graph | EXP-004 | oracle_vs_fci | ORACLE | artifacts/phase3/oracle_vs_fci.json | PARTIALLY_SUPPORTED | Live FCI validation |
| RQ2 | RIFT abstains on confounded | EXP-002 | correct_abstention_rate | — | artifacts/phase3_5/v1_decomposition.json | PARTIALLY_SUPPORTED | Live H2 test (n≥48) |
| RQ2 | RIFT > baselines on confounded P@1 | EXP-002 | conditional_precision_at_1 | RIFT-OBS, SIEVE-LIKE | results/EXP-002/ | PLANNED | Live Linux + n≥48 confounded |
| RQ2 | NOT_IDENTIFIABLE abstention correct | EXP-002 | not_identifiable_rate | — | artifacts/phase3_5/v1_decomposition.json | PARTIALLY_SUPPORTED | Live identifiability validation |
| RQ3 | MSIS < RANDOM on total_ed_s | EXP-003 | total_ed_s | RIFT-RANDOM | results/EXP-003/ | PLANNED | Live H4 Wilcoxon |
| RQ3 | MSIS lower cost, same P@1 (TOST) | EXP-006 | Δ P@1, total_ed_s | RIFT-RANDOM | results/EXP-006/ | PLANNED | Live H4 TOST |
| RQ4 | CID > θ_CID iff truly causal | EXP-004 | cid_grade, w1_estimate | ORACLE | artifacts/phase3/cid_validation.json | PARTIALLY_SUPPORTED | Live CID on real data |
| RQ4 | EBD t* precedes downstream anomaly | EXP-004 | r2_pass_rate | — | artifacts/phase3/ebd_validation.json | PARTIALLY_SUPPORTED | Live EBD on real data |
| RQ4 | Same seed → same result | EXP-010 | result_hash_consistency | — | artifacts/phase3_5/reproducibility_checklist.json | PARTIALLY_SUPPORTED | Live repeatability run |
| RQ5 | RIFT ≥ 70% transfer success | EXP-001 | H5 binomial test | — | results/EXP-001/ | PLANNED | Cross-system deployment |

---

## Hypothesis → Evidence Mapping

| Hypothesis | Test | Experiment | Required n | Current Status |
|---|---|---|---|---|
| H1: RIFT > baselines on P@1 | Wilcoxon one-sided | EXP-001 | 36 | PLANNED |
| H2: RIFT > baselines on confounded P@1 | Wilcoxon one-sided | EXP-002 | 48 (80% power) | PLANNED |
| H3: RIFT < baselines on detection latency | Wilcoxon one-sided | EXP-001 | 36 | PLANNED |
| H4a: RIFT ≈ RIFT-RANDOM on P@1 (TOST) | TOST equivalence | EXP-003 | 36 | PLANNED |
| H4b: RIFT < RIFT-RANDOM on total_ed_s | Wilcoxon one-sided | EXP-003 | 36 | PLANNED |
| H5: Cross-system ≥ 70% transfer | Binomial one-sided | Cross-system | ≥15 | PLANNED |

---

## Frozen Historical Evidence

| Evidence | Value | Source | Notes |
|---|---|---|---|
| Raw Precision@1 | 50% | artifacts/phase3_5/v1_decomposition.json | Synthetic, development set |
| Conditional Precision@1 | 60% | artifacts/phase3_5/v1_decomposition.json | Synthetic, non-abstained only |
| Safety validation | 6/8 hard stops (dry-run) | artifacts/phase3_5/safety_validation.json | 2/8 PENDING_LINUX |
| FCI vs Oracle | See oracle_vs_fci.json | artifacts/phase3_5/oracle_vs_fci.json | Synthetic |

These values MUST NOT be modified.
They represent the pre-Linux state and will be superseded by live evidence.

---

## Status Summary

| Status | Count |
|---|---|
| SUPPORTED | 0 |
| PARTIALLY_SUPPORTED | 6 |
| PLANNED | 6 |
| UNSUPPORTED | 0 |

**LINUX EXECUTION REQUIRED** to upgrade PLANNED → SUPPORTED.
