# RIFT — Research Charter
**Intervention-Grounded Detection of Behavioral Divergence**
**Phase 0 | Version 1.0**

---

## 1. Project Identity

| Field | Value |
|---|---|
| **Project Name** | RIFT |
| **Full Title** | Intervention-Grounded Detection of Behavioral Divergence in Distributed Systems |
| **Target Venue** | ICSE (ACM/IEEE International Conference on Software Engineering) |
| **Track** | Technical Research (primary); Artifact Evaluation (secondary) |
| **Research Phase** | Phase 0 — Charter |
| **Repository Status** | GREENFIELD — no implementation exists |

---

## 2. Mission Statement

RIFT is a research project that investigates whether **causal intervention**, formalized via Pearl's do-calculus, provides a strictly stronger foundation for detecting and localizing behavioral divergence in distributed systems than existing correlational, anomaly-detection, or chaos-engineering approaches.

The project is built through **research gates**, not implementation milestones. No phase begins until the prior phase's research questions are answered with evidence.

---

## 3. Core Research Question

> **When a distributed system exhibits behavioral divergence, can systematic causal interventions — modeled as do-operators — identify the causally responsible component more precisely, more quickly, and with fewer false attributions than methods that rely on observational data alone?**

---

## 4. Definitions (Provisional — to be formalized in Phase 2)

| Term | Provisional Definition | Status |
|---|---|---|
| **Behavioral Divergence** | A measurable deviation in a system component's observable outputs relative to a counterfactual baseline established under identical inputs | PLANNED — requires formal definition |
| **Intervention** | A controlled perturbation modeled as a do-operator: `do(X := x)` overrides the structural equation for variable X | PLANNED — requires operational mapping |
| **Causal Attribution** | The identification of a component C such that `P(divergence | do(C := nominal)) < threshold` | PLANNED — requires formal specification |
| **Counterfactual Baseline** | The predicted system behavior under the intervened causal graph | PLANNED |

---

## 5. Research Objectives

### Primary Objective
Develop and validate an algorithm (RIFT/EBD) that uses intervention-driven causal inference to detect and localize behavioral divergence in distributed systems.

### Secondary Objectives
1. Construct a reproducible benchmark suite covering ≥4 fault types across ≥2 real microservice systems.
2. Demonstrate that causal attribution outperforms correlational baselines on precision of root-cause identification.
3. Establish that the do-calculus framing is not merely cosmetic — interventions must be shown to be **necessary** for the claimed performance.
4. Produce an open-source artifact meeting ICSE Artifact Evaluation standards (Functional + Reusable badges).

---

## 6. Research Constraints

| Constraint | Description |
|---|---|
| **No invented citations** | All related work must be verified before inclusion |
| **No invented results** | No numbers reported until experiments are run |
| **No unsupported novelty claims** | Every novelty claim requires a literature gap proof |
| **No cherry-picked benchmarks** | Benchmark must be designed before results are known |
| **Causal claims require causal evidence** | do-calculus must be operationally justified, not decorative |
| **IMPLEMENTED / PLANNED / MISSING labels** | Every capability carries one of these three labels at all times |

---

## 7. Phases and Gates

| Phase | Name | Gate Condition |
|---|---|---|
| 0 | Research and Repository Audit | Charter + gap analysis complete |
| 1 | Literature + Novelty Positioning | Related work matrix complete; novelty gap confirmed |
| 2 | Formal Problem + Causal Model | Formal definitions accepted; causal assumptions stated |
| 3 | Behavioral State Graph | State graph specification complete |
| 4 | Execution Instrumentation | Trace collection pipeline running end-to-end |
| 5 | Intervention Engine | Intervention injection + safety wrapper implemented |
| 6 | RIFT / EBD Algorithm | Core algorithm implemented and unit-tested |
| 7 | Independent Fault Benchmark | Benchmark designed, populated, and frozen before evaluation |
| 8 | Baselines | All baselines implemented and validated |
| 9 | Ablations | Ablation study designed and executed |
| 10 | Full Evaluation | All experiments complete with statistical tests |
| 11 | Generalization + Robustness | Cross-system and cross-fault-type results available |
| 12 | Statistical + Claim Audit | All claims backed by evidence; significance confirmed |
| 13 | Reproducibility / Artifact | Artifact package complete; Docker + REPRODUCE.md |
| 14 | ICSE Paper | Full paper draft complete |
| 15 | Hostile Review + Final Submission | Internal review passed; submission package ready |

---

## 8. Roles and Responsibilities

| Role | Responsibility |
|---|---|
| **Research Lead** | Research question ownership; phase gate decisions |
| **Implementation Lead** | Algorithm, instrumentation, intervention engine |
| **Evaluation Lead** | Benchmark design, baselines, statistical analysis |
| **Writing Lead** | Paper drafting, related work, claims audit |

---

## 9. Document Index

| Document | Purpose | Status |
|---|---|---|
| `research_charter.md` | This document | COMPLETE |
| `research_gap.md` | What is missing from prior work | COMPLETE |
| `novelty_positioning.md` | How RIFT differentiates | COMPLETE |
| `related_work_matrix.md` | Prior work comparison table | COMPLETE |
| `current_capabilities.md` | What is implemented | COMPLETE |
| `missing_capabilities.md` | What must be built | COMPLETE |
| `reviewer_risks.md` | Hostile reviewer analysis | COMPLETE |
| `research_alignment.md` | RQ → impl → experiment → metric → artifact → paper | COMPLETE |

---

## 10. Success Criteria for Publication

- [ ] Core algorithm implemented, tested, and reproducible
- [ ] Benchmark: ≥2 systems, ≥4 fault types, ≥100 labeled traces
- [ ] Baselines: ≥3 competing methods evaluated on same benchmark
- [ ] Ablation: Each major component validated as necessary
- [ ] Statistics: All claims carry 95% CI and p < 0.05 significance
- [ ] Causal validity: Interventions shown to be necessary (not just helpful)
- [ ] Artifact: Passes ICSE AE Functional + Reusable criteria
- [ ] Paper: ≤10 pages, all claims traceable to experiments

---

*Document status: AUTHORITATIVE. Updates require phase gate review.*
