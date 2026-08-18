# RIFT — Reviewer Risks
**Phase 0 | Version 1.0 | Hostile Review Simulation**

---

## Preface

This document simulates the most aggressive, expert ICSE reviewer possible. Every item here represents a real rejection risk. Each risk must be addressed before submission — either by design, by experiment, or by explicit, honest acknowledgment in the paper.

If a risk cannot be addressed, the paper should not be submitted until it can.

---

## TOP 5 MOST LIKELY REJECTION REASONS (Ranked)

### R1 — "The causal framing is cosmetic. This is anomaly detection with a do-calculus label."

**Probability:** HIGH  
**Severity:** FATAL (rejection without revision)

**Reviewer argument:**
> "The authors claim to use Pearl's do-calculus, but what they actually do is inject faults (standard chaos engineering), observe metric changes (standard anomaly detection), and call the injection a 'do-operator.' The do-calculus framework adds no technical content beyond what Chaos Monkey already does. The identifiability conditions are not checked. The causal graph is not validated. The backdoor criterion is never verified to hold. This is rebranding, not contribution."

**Required defense:**
- Prove identifiability: show that for each query `P(Y | do(X := x))`, the do-expression is non-trivially identifiable in the causal graph (i.e., the back-door or front-door criterion applies, and this is checked, not assumed).
- Show a scenario where correlational RCA gives wrong attribution and do-calculus gives correct attribution. This is the core "necessity proof."
- Ablation: disable the causal inference layer (reduce to chaos + anomaly detection). Show measurable precision degradation. Without this ablation, R1 is unanswerable.

**Status:** UNADDRESSED — requires Phase 6 + 9 to resolve.

---

### R2 — "Behavioral divergence is not formally defined."

**Probability:** HIGH  
**Severity:** MAJOR (likely rejection or major revision)

**Reviewer argument:**
> "The paper uses 'behavioral divergence' throughout but never formally defines it. What exactly diverges? State? Output? Timing? With respect to what baseline? The phrase 'deviation from expected behavior' is not a definition — it is a circular placeholder. Without a precise definition, the detection algorithm's correctness cannot be stated, let alone proven."

**Required defense:**
- Provide a formal definition in the paper: e.g., "Behavioral divergence at component C under intervention I is defined as: `TV(P(Y_C | trace_baseline), P(Y_C | do(X := x_I))) > τ`" where `TV` is Total Variation distance and `τ` is a threshold established from baseline variance.
- Show the definition is computable from observable traces.
- Show it is falsifiable: provide a concrete example where it holds and one where it does not.

**Status:** UNADDRESSED — requires Phase 2 to resolve.

---

### R3 — "The evaluation is on a synthetic/toy benchmark with cherry-picked faults."

**Probability:** HIGH  
**Severity:** MAJOR (likely rejection)

**Reviewer argument:**
> "The evaluation uses a single microservice demo application (Online Boutique) with 11 services and 24 injected faults. Online Boutique is not a production system. The fault types were designed by the authors, creating a risk of benchmark overfitting. There is no evaluation on real production traces, no comparison on an independently established benchmark, and no evidence that the approach generalizes beyond the authors' own testbed."

**Required defense:**
- Use ≥2 independent systems (not designed by RIFT team).
- Benchmark must be designed and frozen before the algorithm is evaluated. Document this in the paper.
- Include at least one fault type discovered from real incident post-mortems (not invented by the research team).
- Include cross-system evaluation: train on system A, test on system B.
- Acknowledge limitations honestly and scope the claims accordingly.

**Status:** UNADDRESSED — requires Phase 7 to resolve.

---

### R4 — "The causal assumptions are never stated or validated."

**Probability:** HIGH  
**Severity:** MAJOR

**Reviewer argument:**
> "The do-calculus is valid only under specific assumptions: causal Markov condition, causal faithfulness, causal sufficiency (no unmeasured confounders), and acyclicity of the causal graph. Real distributed systems violate all of these: feedback loops create cycles, shared infrastructure creates unmeasured confounders, and non-stationarity violates faithfulness. The paper never states which assumptions are made, never checks whether they hold, and never tests sensitivity to assumption violations."

**Required defense:**
- State all assumptions explicitly in the paper (not in an appendix only).
- For each assumption, either: (a) argue it holds in the experimental setup, or (b) show empirical evidence it approximately holds, or (c) provide sensitivity analysis showing results are robust to violations.
- Handle cycles: use time-sliced DAG formulation (`G_t` with edges only backward in time).
- Handle unmeasured confounders: state they exist, show results are robust via sensitivity analysis (e.g., Rosenbaum bounds).

**Status:** UNADDRESSED — requires Phase 2 to resolve.

---

### R5 — "No comparison to the most relevant baselines."

**Probability:** MEDIUM-HIGH  
**Severity:** MAJOR

**Reviewer argument:**
> "The paper compares RIFT against anomaly detection baselines (Isolation Forest, Prometheus rules) but does not compare against the most relevant prior work in RCA for microservices. Systems like MicroRCA, CloudRanger, and related work are directly solving the same problem. Without these comparisons, the claimed advantages are unsubstantiated."

**Required defense:**
- Implement and evaluate against ≥1 microservice-specific RCA baseline (MicroRCA-style or equivalent).
- If the exact system is unavailable, re-implement based on the paper's description and state this clearly.
- If no comparable open-source system exists, document the search and explain why none was used.

**Status:** UNADDRESSED — requires Phase 8 to resolve.

---

## Secondary Reviewer Risks (Would Cause Major Revision)

### R6 — "Intervention safety is not addressed."

**Reviewer argument:** "RIFT injects faults into a running system. What prevents these interventions from causing production outages? What is the blast radius? What is the rollback mechanism? A system deployed in production that can cause arbitrary service degradation has unacceptable risk."

**Required defense:** Explicit SLA guard rails, blast radius bounds, rollback mechanism, and a section on operational safety. Must show interventions add ≤X% latency to production traffic.

---

### R7 — "The causal graph is assumed, not learned."

**Reviewer argument:** "If the causal graph is hand-specified by the operator, the approach is not general. In a real 50-service system, no operator can specify a correct causal graph. If the graph is learned, what is the learning algorithm, what are its convergence guarantees, and how does it handle non-stationarity?"

**Required defense:** Either provide a validated graph learning algorithm, or scope the paper to systems where the graph can be derived from deployment manifests (K8s service mesh). State the limitation explicitly.

---

### R8 — "Detection latency is never measured."

**Reviewer argument:** "The paper claims to detect divergence, but never reports how quickly. An RCA system that takes 30 minutes to identify a root cause is useless in production. Detection latency must be a primary metric, not an afterthought."

**Required defense:** Report detection latency (p50, p95, p99) as a first-class metric. Target: p50 < 30 seconds.

---

### R9 — "Statistical significance is not established."

**Reviewer argument:** "Results are reported as point estimates without confidence intervals or significance tests. With a benchmark of 24 fault instances, the statistical power is insufficient to support strong claims."

**Required defense:** Run ≥3 trials per fault. Report 95% CI via bootstrap. Mann-Whitney U test for all comparisons. Effect sizes (Cohen's d or Cliff's delta).

---

### R10 — "The artifact is not reproducible."

**Reviewer argument:** "The code depends on cloud infrastructure not available to reviewers. The dataset is not included. The Docker image does not build cleanly. The REPRODUCE.md skips steps. Artifact evaluation: Functional badge denied."

**Required defense:** Test on a clean VM before submission. No cloud dependencies. Dockerfile must build from scratch. All datasets included or reproducible from scripts. REPRODUCE.md tested by a team member not involved in initial setup.

---

### R11 — "ICSE scope mismatch."

**Reviewer argument:** "This is a systems paper (distributed systems monitoring) submitted to a software engineering venue. ICSE values software engineering concerns: correctness, testing, specifications, tooling for developers. This paper is closer to OSDI, EuroSys, or ATC. The SE angle is thin."

**Required defense:** Emphasize the SE contributions: (1) formal behavioral specification as ground for divergence, (2) automated test generation via interventions, (3) developer tooling for root cause attribution. Position RIFT as a contribution to automated software debugging, not just systems monitoring.

---

## What Would Make a Hostile Reviewer Accept the Paper

1. A formal, precise definition of behavioral divergence grounded in SCMs.
2. A proof or strong empirical evidence that intervention is *necessary* — the ablation without the causal layer must show measurable degradation.
3. Evaluation on ≥2 independent systems with ≥4 fault types, benchmarked before the algorithm was developed.
4. Comparison against ≥1 microservice-specific RCA baseline.
5. All assumptions stated explicitly, with sensitivity analysis.
6. Detection latency < 30s (p50) reported as a primary metric.
7. 95% CI on all reported metrics, p < 0.05 significance.
8. Fully reproducible artifact with Dockerfile and no cloud dependencies.
9. Honest, precise acknowledgment of limitations (single testbed, known assumptions).
10. A clear SE contribution angle beyond "systems monitoring."

---

## Risk Summary Table

| Risk | Probability | Severity | Phase That Resolves It |
|---|---|---|---|
| R1: Causal framing is cosmetic | HIGH | FATAL | Phase 9 (ablation) |
| R2: Divergence not formally defined | HIGH | MAJOR | Phase 2 |
| R3: Toy benchmark | HIGH | MAJOR | Phase 7 |
| R4: Causal assumptions not stated | HIGH | MAJOR | Phase 2 |
| R5: Missing baselines | MEDIUM-HIGH | MAJOR | Phase 8 |
| R6: Intervention safety | MEDIUM | MODERATE | Phase 5 |
| R7: Graph assumed not learned | MEDIUM | MODERATE | Phase 2/6 |
| R8: Detection latency not measured | MEDIUM | MODERATE | Phase 10 |
| R9: No statistical significance | MEDIUM | MODERATE | Phase 12 |
| R10: Not reproducible | LOW-MEDIUM | MODERATE | Phase 13 |
| R11: ICSE scope mismatch | LOW | MODERATE | Phase 14 |
