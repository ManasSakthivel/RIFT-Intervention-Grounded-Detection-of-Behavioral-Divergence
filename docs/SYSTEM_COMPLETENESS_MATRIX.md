# RIFT System Completeness Matrix
# Phase 3.6 — Pre-Linux Readiness Audit
# Generated: Phase 3.6
# Authority: PHASE_3_6_PRE_LINUX_READINESS_REPORT.md

## Legend

| Status | Meaning |
|---|---|
| IMPLEMENTED | Code exists and is complete |
| TESTED | Has unit/integration tests |
| VALIDATED | Passed synthetic ground-truth validation |
| READY_FOR_LINUX | Fully implemented; awaits Linux execution |
| PENDING_LINUX | Cannot be tested without Linux+CAP_NET_ADMIN |
| MISSING | Not yet implemented |
| UNSUPPORTED | Intentionally excluded from scope |
| DEFERRED | Deferred to future phase (documented reason) |

---

## Core SCM / Formal Model

| Component | Specification | Implementation | Unit Tests | Integration Tests | Synthetic Validation | Live Validation | Experiment | Artifact | Status | Remaining Dependency |
|---|---|---|---|---|---|---|---|---|---|---|
| SCM `<U,V,F,P(U)>` | docs/formal_model.md §B | src/rift/scm/scm.py | tests/causal/test_scm.py | — | artifacts/phase3/scm_validation.json | PENDING_LINUX | EXP-001 | phase3/scm_validation.json | VALIDATED | None |
| Time-sliced G_T | docs/formal_model.md §C | src/rift/graph/time_slice.py | tests/causal/ | — | artifacts/phase3/time_slice_validation.json | PENDING_LINUX | EXP-001 | phase3/time_slice_validation.json | VALIDATED | None |
| CausalVariable / Metric / TimeWindow | docs/formal_model.md | src/rift/models/data_models.py | tests/unit/test_data_models.py | — | — | — | — | — | TESTED | None |

---

## Causal Discovery (FCI / PAG)

| Component | Specification | Implementation | Unit Tests | Integration Tests | Synthetic Validation | Live Validation | Experiment | Artifact | Status | Remaining Dependency |
|---|---|---|---|---|---|---|---|---|---|---|
| FCI → PAG | SPEC_FREEZE §3 | src/rift/fci/fci_runner.py | tests/causal/test_fci.py | — | artifacts/phase3/fci_validation.json | PENDING_LINUX | EXP-001 | phase3/fci_validation.json | VALIDATED | None |
| Anomaly subgraph (Strategy D, k≤15) | SPEC_FREEZE §4 | src/rift/graph/anomaly_subgraph.py | — | — | artifacts/phase3/anomaly_subgraph_validation.json | PENDING_LINUX | EXP-001 | phase3/anomaly_subgraph_validation.json | VALIDATED | None |
| Identifiability (backdoor/front-door/ABSTAIN) | SPEC_FREEZE §5 | src/rift/identifiability/identifiability.py | tests/causal/test_identifiability.py | — | artifacts/phase3/identifiability_validation.json | PENDING_LINUX | EXP-002 | phase3/identifiability_validation.json | VALIDATED | None |

---

## Telemetry

| Component | Specification | Implementation | Unit Tests | Integration Tests | Synthetic Validation | Live Validation | Experiment | Artifact | Status | Remaining Dependency |
|---|---|---|---|---|---|---|---|---|---|---|
| OTEL Collector config | docs/telemetry/ARCHITECTURE.md | docker/otel-collector-config.yaml | — | tests/integration/telemetry/ | — | PENDING_LINUX | — | — | READY_FOR_LINUX | Linux+Docker |
| Prometheus scrape config | docs/telemetry/ARCHITECTURE.md | docker/prometheus.yml | — | — | — | PENDING_LINUX | — | — | READY_FOR_LINUX | Linux+Docker |
| PrometheusClient (live) | SPEC_FREEZE §1 | src/rift/pipeline/e2e_runner.py:PrometheusClient | — | tests/integration/telemetry/ | — | PENDING_LINUX | — | — | READY_FOR_LINUX | Linux+Prometheus |
| MockTelemetry (synthetic) | SPEC_FREEZE §1 | src/rift/pipeline/e2e_runner.py:MockTelemetry | tests/unit/ | — | — | N/A | — | — | IMPLEMENTED | None |
| Time alignment / normalization | docs/telemetry/ARCHITECTURE.md | src/rift/telemetry/normalizer.py | tests/unit/telemetry/ | — | — | PENDING_LINUX | — | — | IMPLEMENTED | None |
| Metric time-slicing into G_T | SPEC_FREEZE §2 | src/rift/graph/time_slice.py | tests/causal/ | — | artifacts/phase3/time_slice_validation.json | PENDING_LINUX | — | — | VALIDATED | None |

---

## Intervention Engine

| Component | Specification | Implementation | Unit Tests | Integration Tests | Synthetic Validation | Live Validation | Experiment | Artifact | Status | Remaining Dependency |
|---|---|---|---|---|---|---|---|---|---|---|
| NetworkInterventionEngine (tc u32+netem) | SPEC_FREEZE §11 | src/rift/intervention/network_intervention.py | tests/unit/ | tests/integration/ | artifacts/phase3/network_intervention_validation.json | PENDING_LINUX | EXP-003 | phase3/network_intervention_validation.json | READY_FOR_LINUX | Linux+CAP_NET_ADMIN |
| DryRunBackend | SPEC_FREEZE §11 | src/rift/intervention/backends/dry_run.py | tests/unit/intervention/ | — | — | N/A | — | — | IMPLEMENTED | None |
| LinuxTcNetemBackend | SPEC_FREEZE §11 | src/rift/intervention/backends/linux_tc_netem.py | — | tests/integration/intervention/ | — | PENDING_LINUX | EXP-003 | — | READY_FOR_LINUX | Linux+CAP_NET_ADMIN |
| Intervention lifecycle (prepare/authorize/apply/verify/observe/rollback/finalize) | SPEC_FREEZE §11 | src/rift/intervention/intervention_lifecycle.py | tests/unit/intervention/ | — | — | PENDING_LINUX | — | — | IMPLEMENTED | None |
| Safety Controller (8 hard stops) | SPEC_FREEZE §14 | src/rift/safety/safety.py | tests/integration/safety/ | tests/integration/safety/test_safety_35.py | artifacts/phase3_5/safety_validation.json | PENDING_LINUX | EXP-008 | phase3_5/safety_validation.json | VALIDATED | None |

---

## Fault Injection

| Component | Specification | Implementation | Unit Tests | Integration Tests | Synthetic Validation | Live Validation | Experiment | Artifact | Status | Remaining Dependency |
|---|---|---|---|---|---|---|---|---|---|---|
| FaultInjector (8 fault types) | SPEC_FREEZE §11 | src/rift/fault_injection/fault_injector.py | tests/unit/fault_injection/ | tests/integration/fault_injection/ | artifacts/phase3_5/fault_injection_validation.json | PENDING_LINUX | EXP-001 | phase3_5/fault_injection_validation.json | READY_FOR_LINUX | Linux+kubectl |
| Manifest (69 scenarios, 3-way split) | datasets/rift_faults/README.md | datasets/rift_faults/{dev,val,held_out}.json | — | — | artifacts/phase3_5/benchmark_integrity.json | N/A | — | phase3_5/benchmark_integrity.json | VALIDATED | None |
| Held-out leakage guard | SPEC_FREEZE §16 | src/rift/fault_injection/fault_injector.py | tests/unit/test_leakage.py | — | — | N/A | — | — | IMPLEMENTED | None |
| MULTI_CAUSE composition | SPEC_FREEZE §11 | src/rift/fault_injection/fault_injector.py | — | — | — | PENDING_LINUX | — | — | READY_FOR_LINUX | Linux |
| CONFOUNDED (latent U_host) | SPEC_FREEZE §11 | src/rift/fault_injection/fault_injector.py | — | — | — | PENDING_LINUX | — | — | READY_FOR_LINUX | Linux |

---

## RIFT-FULL Pipeline

| Component | Specification | Implementation | Unit Tests | Integration Tests | Synthetic Validation | Live Validation | Experiment | Artifact | Status | Remaining Dependency |
|---|---|---|---|---|---|---|---|---|---|---|
| 17-stage pipeline | SPEC_FREEZE all | src/rift/pipeline/e2e_runner.py | tests/unit/test_e2e_runner.py | tests/integration/pipeline/ | — | PENDING_LINUX | EXP-001 | phase3_5/e2e/ | READY_FOR_LINUX | Linux+Prometheus |
| RIFTRunRecord | SPEC_FREEZE | src/rift/pipeline/e2e_runner.py:RIFTRunRecord | tests/unit/test_e2e_runner.py | — | — | PENDING_LINUX | — | phase3_5/e2e/rift_run_record_schema.json | IMPLEMENTED | None |
| CID (Wasserstein+permutation) | SPEC_FREEZE §6-8 | src/rift/cid/cid.py | tests/unit/test_cid.py | — | artifacts/phase3/cid_validation.json | PENDING_LINUX | EXP-001 | phase3/cid_validation.json | VALIDATED | None |
| EBD (R1-R4, t*) | SPEC_FREEZE §9 | src/rift/ebd/ebd.py | tests/unit/test_ebd.py | — | artifacts/phase3/ebd_validation.json | PENDING_LINUX | EXP-001 | phase3/ebd_validation.json | VALIDATED | None |
| Closed-loop state machine | SPEC_FREEZE §13 | src/rift/loop/closed_loop.py | tests/unit/test_closed_loop.py | — | artifacts/phase3/closed_loop_validation.json | PENDING_LINUX | EXP-001 | phase3/closed_loop_validation.json | VALIDATED | None |
| Cost model / greedy MSIS | SPEC_FREEZE §12 | src/rift/optimizer/cost_model.py | tests/unit/test_cost_model.py | — | artifacts/phase3/intervention_selection_validation.json | PENDING_LINUX | EXP-004 | phase3/intervention_selection_validation.json | VALIDATED | None |
| Attribution / abstention | SPEC_FREEZE §9 | src/rift/pipeline/e2e_runner.py | tests/unit/ | — | artifacts/phase3_5/v1_decomposition.json | PENDING_LINUX | EXP-001 | phase3_5/v1_decomposition.json | VALIDATED | None |

---

## Baselines

| Component | Specification | Implementation | Unit Tests | Integration Tests | Synthetic Validation | Live Validation | Experiment | Artifact | Status | Remaining Dependency |
|---|---|---|---|---|---|---|---|---|---|---|
| RIFT-OBS (ablation, no intervention) | docs/baselines/RIFT_OBS.md | src/rift/baselines/rift_obs.py | tests/unit/baselines/ | — | — | PENDING_LINUX | EXP-005 | — | IMPLEMENTED | None |
| RIFT-RANDOM (ablation, random selection) | docs/baselines/RIFT_RANDOM.md | src/rift/baselines/rift_random.py | tests/unit/baselines/ | — | — | PENDING_LINUX | EXP-006 | — | IMPLEMENTED | None |
| Sieve-like (methodological baseline) | docs/baselines/SIEVE_LIKE.md | src/rift/baselines/sieve_like.py | tests/unit/baselines/ | — | — | PENDING_LINUX | EXP-007 | — | IMPLEMENTED | None |
| Sage+Chaos (external baseline) | docs/baselines/SAGE_CHAOS.md | interface stub only | — | — | — | — | — | — | DEFERRED | Phase 8 (pre-labeled data) |
| Oracle Upper Bound | docs/baselines/ORACLE.md | src/rift/baselines/oracle.py | tests/unit/baselines/ | — | — | — | EXP-012 | — | IMPLEMENTED | None |

---

## Evaluation Framework

| Component | Specification | Implementation | Unit Tests | Integration Tests | Synthetic Validation | Live Validation | Experiment | Artifact | Status | Remaining Dependency |
|---|---|---|---|---|---|---|---|---|---|---|
| Attribution metrics (P@1, coverage, abstention, etc.) | SPEC_FREEZE §15 | src/rift/evaluation/attribution_metrics.py | tests/unit/evaluation/ | — | artifacts/phase3_5/v1_decomposition.json | PENDING_LINUX | EXP-001 | — | IMPLEMENTED | None |
| Divergence metrics (W1, permutation, CID) | SPEC_FREEZE §6-8 | src/rift/evaluation/divergence_metrics.py | tests/unit/evaluation/ | — | — | PENDING_LINUX | EXP-001 | — | IMPLEMENTED | None |
| EBD metrics evaluator | SPEC_FREEZE §9 | src/rift/evaluation/ebd_metrics.py | tests/unit/evaluation/ | — | — | PENDING_LINUX | EXP-001 | — | IMPLEMENTED | None |
| Statistical tests (H1-H5, Wilcoxon/TOST/binomial) | docs/risk_closure/statistical_plan.md | src/rift/statistics/stats.py + src/rift/evaluation/statistics/ | tests/unit/test_stats.py | — | — | PENDING_LINUX | Final eval only | — | IMPLEMENTED | Final benchmark data |
| Holm-Bonferroni + BH FDR | SPEC_FREEZE §15 | src/rift/statistics/stats.py | tests/unit/test_stats.py | — | — | — | — | — | IMPLEMENTED | None |
| Power analysis (n≥48, 80% power) | docs/risk_closure/sample_requirements.md | src/rift/evaluation/power.py | tests/unit/evaluation/ | — | — | — | — | — | IMPLEMENTED | None |
| Held-out leakage detection | SPEC_FREEZE §16 | src/rift/evaluation/held_out_guard.py | tests/unit/test_leakage.py | — | — | — | — | — | IMPLEMENTED | None |

---

## Experiment Infrastructure

| Component | Specification | Implementation | Unit Tests | Integration Tests | Synthetic Validation | Live Validation | Experiment | Artifact | Status | Remaining Dependency |
|---|---|---|---|---|---|---|---|---|---|---|
| Experiment runner | Phase 3.6 §17 | src/rift/experiments/run.py | — | — | — | PENDING_LINUX | all | — | IMPLEMENTED | None |
| Experiment registry | Phase 3.6 §18 | experiments/REGISTRY.yaml | — | — | — | — | — | — | IMPLEMENTED | None |
| Artifact writer (checksums+provenance) | Phase 3.6 §21 | src/rift/artifacts/writer.py | tests/unit/artifacts/ | — | — | — | — | — | IMPLEMENTED | None |
| Claims registry | Phase 3.6 §22 | docs/CLAIMS_REGISTRY.yaml | — | — | — | — | — | — | IMPLEMENTED | None |
| Paper evidence matrix | Phase 3.6 §23 | docs/PAPER_EVIDENCE_MATRIX.md | — | — | — | — | — | — | IMPLEMENTED | None |
| Provenance / logging | Phase 3.6 §24 | src/rift/provenance/logger.py | tests/unit/provenance/ | — | — | — | — | — | IMPLEMENTED | None |
| Configuration system | Phase 3.6 §25 | configs/{dev,val,held_out,live,dry_run}.yaml | — | — | — | — | — | — | IMPLEMENTED | None |

---

## Performance Instrumentation

| Component | Specification | Implementation | Unit Tests | Integration Tests | Synthetic Validation | Live Validation | Experiment | Artifact | Status | Remaining Dependency |
|---|---|---|---|---|---|---|---|---|---|---|
| Stage timing (wall+CPU) | Phase 3.6 §28 | src/rift/telemetry/instrumentation.py | tests/unit/telemetry/ | — | — | PENDING_LINUX | EXP-009 | — | IMPLEMENTED | None |

---

## Failure Taxonomy

| Component | Specification | Implementation | Unit Tests | Integration Tests | Synthetic Validation | Live Validation | Experiment | Artifact | Status | Remaining Dependency |
|---|---|---|---|---|---|---|---|---|---|---|
| Failure codes enum | Phase 3.6 §29 | src/rift/models/failure_codes.py | — | — | — | — | — | — | IMPLEMENTED | None |

---

## Security

| Component | Specification | Implementation | Unit Tests | Integration Tests | Synthetic Validation | Live Validation | Experiment | Artifact | Status | Remaining Dependency |
|---|---|---|---|---|---|---|---|---|---|---|
| .gitignore | Phase 3.6 §31 | .gitignore | — | — | — | — | — | — | IMPLEMENTED | None |
| Security audit | Phase 3.6 §31 | docs/SECURITY_AUDIT.md | — | — | — | — | — | — | IMPLEMENTED | None |

---

## Pre-Linux Gate

| Checklist Item | Status |
|---|---|
| Complete RIFT pipeline implemented | IMPLEMENTED |
| Telemetry software/configuration complete | READY_FOR_LINUX |
| Online Boutique deployment complete | READY_FOR_LINUX |
| Fault injection complete | READY_FOR_LINUX |
| RIFT-FULL complete | READY_FOR_LINUX |
| RIFT-OBS complete | IMPLEMENTED |
| RIFT-RANDOM complete | IMPLEMENTED |
| Sieve-like baseline complete | IMPLEMENTED |
| Sage+Chaos interface prepared/deferred | DEFERRED_TO_PHASE_8 |
| Oracle upper bound complete | IMPLEMENTED |
| Attribution metrics complete | IMPLEMENTED |
| CID/EBD evaluation complete | IMPLEMENTED |
| Statistical infrastructure complete | IMPLEMENTED |
| Power analysis complete | IMPLEMENTED |
| Experiment registry complete | IMPLEMENTED |
| Held-out leakage protection complete | IMPLEMENTED |
| Reproduction commands complete | IMPLEMENTED |
| Artifact system complete | IMPLEMENTED |
| Claims registry complete | IMPLEMENTED |
| Evidence matrix complete | IMPLEMENTED |
| Provenance complete | IMPLEMENTED |
| Failure taxonomy complete | IMPLEMENTED |
| Security audit complete | IMPLEMENTED |
| Repository structure clean | IMPLEMENTED |
| All macOS-possible tests pass | PENDING (final run) |
| Linux tests explicitly marked READY_FOR_LINUX | IMPLEMENTED |
