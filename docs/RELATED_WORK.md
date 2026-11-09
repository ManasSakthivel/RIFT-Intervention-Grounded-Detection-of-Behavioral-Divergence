# RIFT: Related Work and Research Positioning

**Authority:** IEEE Transactions on Software Engineering (TSE) / IEEE International Conference on Software Engineering (ICSE) Framing

---

## 1. Overview and Taxonomy

Root-Cause Analysis (RCA) in distributed microservices has progressed through three primary generations:

1. **Correlation & Topology-Based Ranking:** Systems that construct dependency graphs from distributed traces and rank anomalous services via metric thresholds or random-walk algorithms (e.g., MicroRCA, AutoMAP, NetMedic).
2. **Observational Causal Discovery:** Systems that infer Directed Acyclic Graphs (DAGs) using observational constraint-based or continuous optimization methods (e.g., PC algorithm, NOTEARS, Granger causality in RCD, CauseInfer, CIRCA, Sage, CloudRanger).
3. **Active/Interventional Fault Probing:** Systems that actively inject perturbations during testing or runtime to isolate anomalies (e.g., Sieve, LDFI, Chaos Engineering, Shrink).

**RIFT's Positioning:**  
RIFT operates at the intersection of causal discovery under unmeasured confounding (Pearl's do-calculus and Spirtes-Glymour-Scheines FCI algorithm producing Partial Ancestral Graphs) and controlled live network intervention (`tc netem`). RIFT is explicitly evaluated to determine whether **active intervention-grounded divergence (Wasserstein $W_1$)** and **identifiability-conditioned abstention** improve attribution accuracy and prevent false attributions compared to observational-only causal models.

```
                      Taxonomy of Microservice RCA
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│     Observational-Only RCA      │   │     Active / Interventional     │
├─────────────────────────────────┤   ├─────────────────────────────────┤
│ Correlational / Random Walk     │   │ Heuristic Chaos Probing         │
│  - MicroRCA (NOMS '20)          │   │  - Chaos Engineering (IEEE '16) │
│  - NetMedic (SIGCOMM '08)       │   │  - Sieve (ICSE '23)             │
│                                 │   │  - LDFI (SIGMOD '15 - test time)│
│ Observational Causal Discovery  │   │                                 │
│  - RCD (ICSE '22)               │   │ SCM + Interventional Discovery │
│  - Sage (ASPLOS '21)            │   │  - RIFT (This work)             │
│  - CauseInfer (INFOCOM '14)     │   │    - FCI/PAG Discovery          │
│  - CloudRanger (CCGrid '18)     │   │    - Identifiability Abstention │
│                                 │   │    - Earliest Behavioral Div.   │
│ SCM (Offline / Simulated do(·)) │   │    - Closed-Loop Bayesian Update│
│  - DoWhy (ICML '20)             │   │                                 │
└─────────────────────────────────┘   └─────────────────────────────────┘
```

---

## 2. In-Depth Comparative Analysis

### 2.1 MicroRCA (Wu / Li et al., NOMS 2020)
- **Method:** MicroRCA builds an attributed graph combining service call topology with resource metrics (CPU, memory). Edge weights are derived from Pearson correlation of latencies. RCA is performed via Personalized PageRank walking backward from anomalous entry points.
- **Methodological Difference:** MicroRCA is purely correlational and assumes anomalies always propagate along observed call-graph edges. It cannot distinguish true causal influence from common-cause confounding (e.g., a shared database or network switch degrading two independent services simultaneously).
- **RIFT Contrast:** RIFT estimates the Partial Ancestral Graph (PAG) to explicitly represent latent confounders ($X \leftrightarrow Y$) and uses active perturbation ($do(X)$) to test directional transmission ($W_1$ divergence).

### 2.2 Sieve (Zhang et al., ICSE 2023)
- **Method:** Sieve performs adaptive runtime fault injection to prune candidate root causes. It isolates failure hypotheses by reproducing symptoms under controlled perturbations.
- **Methodological Difference:** Sieve relies on heuristic candidate selection without a formal Structural Causal Model (SCM) or identifiability criterion. It does not formally evaluate whether a query is identifiable under confounding.
- **RIFT Contrast:** RIFT integrates formal constraint-based discovery (FCI), evaluates non-parametric identifiability (backdoor/frontdoor criteria), uses Wasserstein-1 distributional divergence with permutation tests, and executes cost-budgeted multi-stage intervention selection (MSIS).

### 2.3 RCD (Ikram et al., ICSE 2022) & CauseInfer (Chen et al., INFOCOM 2014)
- **Method:** RCD applies constraint-based causal discovery (PC algorithm) over sliding observational time windows to learn DAGs from microservice metrics, ranking upstream nodes in the learned DAG.
- **Methodological Difference:** PC assumes causal sufficiency (no unmeasured confounders). In microservices, unmeasured shared infrastructure (hypervisor CPU stealing, shared DB connection pools, physical link congestion) frequently violates causal sufficiency, causing PC to orient spurious directed edges.
- **RIFT Contrast:** RIFT uses FCI (which allows latent confounders and selection bias) and abstains when the PAG indicates that the causal query is confounded and non-identifiable.

### 2.4 Sage (Gan et al., ASPLOS 2021)
- **Method:** Sage constructs Bayesian Networks from microservice traces to attribute performance bugs and tail latency amplification.
- **Methodological Difference:** Sage relies on observational Bayesian networks trained offline, which cannot resolve Markov equivalence classes without active interventional data.
- **RIFT Contrast:** RIFT uses online runtime network intervention to break observational Markov equivalence and dynamically updates posterior edge confidences via closed-loop Bayesian inference.

---

## 3. Explicit Methodological Scope & Limitations

To ensure scientific honesty and prevent overclaiming in peer review:

1. **Leaf-Service Limitation:**  
   In call topologies where a service is a terminal sink (leaf node), perturbing the service produces no downstream telemetry variations. Consequently, Criterion R3 (Causal Relevance) fails for pure sink nodes. RIFT's causal divergence detection is fundamentally designed for intermediate and upstream services with observable downstream effects.
2. **Assumptions on FCI:**  
   FCI assumes the Causal Markov Condition and near-faithfulness. High-frequency non-linear queueing or feedback loops in microservices can cause local faithfulness violations, which RIFT handles by falling back to conservative abstention.
3. **Safety & Budget Constraints:**  
   Live intervention carries operational overhead. RIFT enforces 8 deterministic safety hard-stops and a disruption cost model ($\text{ED}(X) = \text{TTR}(X) \times \text{DegradationFactor}$) to constrain runtime risk.

---

## 4. Key Reviewer Risks & Mitigation Strategy

| Reviewer Objection | Reality & Evidence | RIFT Mitigation in Paper |
|---|---|---|
| *"Why intervene in production when observation is safe?"* | Observational RCA fails on confounded and Markov-equivalent structures (yielding spurious attributions). | Directly measure Precision@1 on confounded scenarios; show RIFT-OBS false attribution rate vs. RIFT-FULL abstention/precision. |
| *"Is Sieve already doing interventional RCA?"* | Sieve lacks formal SCM/do-calculus, confounder identification, and identifiability-conditioned abstention. | Include formal comparison and label reimplementation explicitly as `SIEVE-LIKE`. |
| *"Does RIFT require an oracle graph?"* | A practical system must learn graphs from observational data. | Present **Learned Graph (FCI)** results as primary; report **Oracle Graph** strictly as upper-bound diagnostic. |
| *"What happens on leaf services?"* | Leaf services have no downstream nodes in the call graph. | Report performance disaggregated by leaf vs. non-leaf faults and state limitation explicitly. |

---

## 5. Recommended IEEE Paper Positioning

- **Primary Research Question:**  
  *Does active network perturbation combined with identifiability analysis improve root-cause attribution accuracy and reduce false attributions over state-of-the-art observational causal models in microservice architectures?*
- **Target Venues:** IEEE Transactions on Software Engineering (TSE), IEEE International Conference on Software Engineering (ICSE), or IEEE Transactions on Dependable and Secure Computing (TDSC).
