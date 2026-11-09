# Where Intervention-Grounded Root-Cause Attribution Fails: A Synthetic Study with a Conservative Abstaining Framework

**Manas Sakthivel**  
*Department of Computer Science / Engineering*  
*Contact: GitHub `@ManasSakthivel`*

---

## Abstract

Root-Cause Analysis (RCA) in distributed microservice architectures is fundamentally hindered by unmeasured shared-infrastructure confounding, cyclic dependencies, and observational Markov equivalence. While active interventional probing has been proposed to overcome observational ambiguity, the empirical boundaries of causal discovery and runtime fault isolation under unobserved confounding remain poorly characterized. In this paper, we present **RIFT (Root Isolation via Fault-guided Telemetry)**, a causal microservice attribution framework that combines constraint-based causal discovery (Fast Causal Inference, producing Partial Ancestral Graphs) with targeted network interventions and identifiability-conditioned abstention. We evaluate RIFT across 360 synthetic microservice benchmark scenarios, an adversarial stress cohort of 112 scenarios, and 252 pooled development/validation evaluations. On a spent, one-shot held-out split of 108 scenarios evaluated under RIFT V2, the method achieved a correct-root accuracy of $44.4\%$ (20/45 attributable cases) and an overall outcome accuracy of $55.6\%$ (60/108), failing to statistically outperform a trivial **always-abstain baseline** ($58.3\%$, 63/108; McNemar $p=0.76$). Detailed failure analysis reveals that constraint-based discovery severely bottlenecks attribution (97.0%–97.8% of learned edges remain circle-marked) and that 100% of wrong-root attributions misidentify downstream descendants along semi-directed paths. In response, RIFT V3 incorporates conservative abstention guards, positive controls, and multiple-testing corrections, significantly reducing unsafe attributions across 252 pooled scenarios from $31.3\%$ (79/252) to $19.0\%$ (48/252) without significantly improving correct-root accuracy (36/252 to 45/252 of all scenarios, i.e. $36.4\%$ to $45.5\%$ of the 99 attributable cases). Under a linear utility model with normative weights (specified in a drafted but not yet recorded or approved preregistration) penalizing unsafe interventions, RIFT V3 yields a negative expected utility ($U = -0.338$, 95% bootstrap CI $[-0.472, -0.222]$), remaining inferior to always-abstain ($U \equiv 0$). We document why active intervention fails to rescue passive attribution when underlying graphs are unresolved, formalize the necessity of trivial-abstain baselines in AIOps benchmarking, and release a drafted experimental protocol (not yet recorded or approved; no confirmatory data exist) for future microservice causal inference.

**Index Terms**—Root Cause Analysis, Microservices, Causal Discovery, Fast Causal Inference, Interventional Probing, Selective Prediction, Abstention, Negative Empirical Results.

---

## 1. Introduction

Modern cloud-native applications rely on complex microservice topologies executing over dynamic, multi-tenant container platforms. When performance anomalies, latency spikes, or cascading HTTP error storms occur, site reliability engineers (SREs) must rapidly identify the root-cause service to execute mitigation (e.g., container restarts, circuit breaking, traffic draining). However, observational telemetry in microservices—such as distributed OpenTelemetry spans, Prometheus request rates, and CPU utilization—presents severe identifiability challenges:

1. **Unmeasured Confounding:** Co-located services frequently share uninstrumented physical resources (e.g., CPU cache contention, hypervisor scheduling, physical top-of-rack switch queueing). These latent confounders induce spurious statistical dependencies that observational Directed Acyclic Graph (DAG) estimators (e.g., PC algorithm, NOTEARS, VAR-Granger) misinterpret as direct causal links.
2. **Observational Equivalence and Descendant Diffusion:** Upstream service failures propagate downstream through synchronous RPC chains. Consequently, downstream services often express higher anomaly amplitudes and earlier detector triggerings than the true root, causing correlation-based rankers to misidentify descendants as culprits.
3. **Severe Cost of False Attribution:** In automated remediation pipelines, triggering an intervention (such as a container restart or traffic drop) on an incorrectly attributed service degrades healthy services and exacerbates outages.

To overcome the fundamental limitations of observational inference, recent research has explored active interventional testing (e.g., *Sieve* [Zhang et al., ICSE 2023], Chaos Engineering [Basiri et al., IEEE 2016]). By perturbing suspected microservices via network emulation (`tc netem`) or thread injection and measuring downstream response divergence (Pearl's $do$-calculus), active systems attempt to break Markov equivalence.

In this work, we present an empirical investigation into whether active network perturbation, paired with formal constraint-based causal discovery under latent confounding (the Fast Causal Inference algorithm, FCI), can achieve reliable root-cause attribution. We design **RIFT (Root Isolation via Fault-guided Telemetry)**, a staged pipeline combining:
- **Earliest Behavioral Divergence (EBD):** Non-parametric change-point detection across multi-metric telemetry streams.
- **PAG Causal Discovery:** Learning Partial Ancestral Graphs via FCI to explicitly represent latent common causes ($X \leftrightarrow Y$) and unoriented adjacencies ($X \circ-\circ Y$).
- **Causal Identifiability and Divergence (CID):** Evaluating graphical identifiability and validating causal transmission via 2-sample Wasserstein-1 ($W_1$) permutation tests during controlled perturbations.
- **Identifiability-Conditioned Abstention:** A disciplined decision engine that abstains (`ABSTAIN_REQUIRED`) whenever the causal graph is non-identifiable, the signal is weak, or candidate services exhibit mutual symmetry.

### Central Contributions and Findings

Rather than presenting RIFT as a solved commercial diagnosis tool, this paper reports an **honest empirical characterization of the fundamental limits of interventional microservice attribution** on rigorous synthetic benchmarks:

1. **Failure to Outperform Trivial Always-Abstain:** On a spent, one-shot held-out test split of 108 synthetic scenarios evaluated under RIFT V2, the method achieved $44.4\%$ correct-root accuracy (20/45 attributable cases) and $55.6\%$ overall outcome accuracy (60/108). A trivial baseline that unconditionally abstains on every incident achieves $58.3\%$ outcome accuracy (63/108; McNemar $p=0.76$). Under a normative utility model ($U = \text{Correct} - 2.0 \cdot \text{Unsafe} - \text{Cost}$), RIFT V3 achieves a mean utility of $-0.338$ ($95\%$ CI $[-0.472, -0.222]$), remaining significantly inferior to always-abstain ($U \equiv 0$).
2. **Empirical Taxonomy of Attribution Bottlenecks:** We identify four core structural barriers in causal microservice RCA:
   - *FCI Graph Undecidability:* In finite-sample microservice time series, FCI leaves $97.0\%–97.8\%$ of learned edges circle-marked ($\circ$), failing to orient causal ancestry.
   - *Downstream Descendant Trap:* In $100\%$ of RIFT V2 false attributions, the system selected a downstream descendant of the true root along a semi-directed path.
   - *Interventional Drift Confounding:* Consecutive-window active perturbation designs without concurrent control arms are confounded by background temporal load drift.
   - *Unobserved Root Failure:* When root causes reside in uninstrumented infrastructure, active testing yields $100\%$ false-positive attributions ($7/7$ unsafe in adversarial stress testing).
3. **Safety Gains via Disciplined Abstention:** We show that RIFT V3 successfully reduces unsafe interventions from $31.3\%$ (79/252) in V2 to $19.0\%$ (48/252) on pooled development and validation scenarios (a $39\%$ relative reduction, template-cluster 95% CI $23\%$ to $54\%$; the quoted $p = 0.0026$ is the validation split alone, Holm-adjusted $0.0155$). V3 was designed on these scenarios, so this is adaptive development evidence, not a confirmatory result. However, this gain is entirely a *selective prediction (abstention) effect*: correct-root accuracy does not significantly improve ($41.2\% \rightarrow 47.1\%$ on dev, $p=0.50$; $25.8\% \rightarrow 41.9\%$ on val, $p=0.18$).
4. **Methodological Recommendations for AIOps:** We provide actionable guidelines for microservice RCA research, emphasizing the mandatory inclusion of always-abstain baselines, cluster-aware family-block statistical inference, and disclosure of definitional label circularity.

---

## 2. Related Work

Root-Cause Analysis in distributed systems spans three distinct generations, summarized below:

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

### 2.1 Correlational and Topology-Based Methods
First-generation systems construct dependency graphs from static architecture models or distributed tracing spans and rank anomalous services using metric correlations or random-walk algorithms. **MicroRCA** [Wu et al., NOMS 2020] builds an attributed graph combining service topologies with host metrics and executes Personalized PageRank backward from anomalous endpoints. **NetMedic** [Kandula et al., SIGCOMM 2008] computes correlation profiles across components. These methods assume anomalies strictly propagate along observed RPC call edges and cannot differentiate direct causal dependencies from common-cause confounding (e.g., two independent microservices degrading simultaneously due to a noisy neighbor on a shared Kubernetes node).

### 2.2 Observational Causal Discovery
Second-generation systems attempt to learn Directed Acyclic Graphs (DAGs) directly from runtime metrics. **RCD** [Ikram et al., ICSE 2022] applies the PC algorithm over localized time windows. **CauseInfer** [Chen et al., INFOCOM 2014] and **CloudRanger** [Wang et al., CCGrid 2018] use Granger causality and PC-derived structures. **Sage** [Gan et al., ASPLOS 2021] constructs offline Bayesian networks from distributed traces. 

A critical vulnerability of PC and standard causal Bayesian networks is the assumption of *causal sufficiency* (the assumption that all common causes are measured). In production microservices, unmeasured shared infrastructure (e.g., kernel socket locks, hypervisor stealing, shared database connection pools) routinely violates causal sufficiency, causing PC-based approaches to orient false directed edges.

### 2.3 Active and Interventional Fault Isolation
Third-generation systems actively inject perturbations at runtime to isolate faults. **Sieve** [Zhang et al., ICSE 2023] performs adaptive runtime fault injection to prune candidate root causes by reproducing symptoms. **LDFI** [Alvaro et al., SIGMOD 2015] uses lineage-driven fault injection during test-time chaos verification. 

While Sieve demonstrated the utility of runtime probing, it relies on heuristic candidate ranking without a formal Structural Causal Model (SCM), does not assess graphical identifiability under latent confounding, and lacks formal criteria for when a system must abstain. RIFT was designed to bridge this gap by combining Spirtes-Glymour-Scheines Fast Causal Inference (FCI) with Pearl's $do$-calculus, explicit Partial Ancestral Graphs (PAGs), and identifiability-conditioned abstention.

---

## 3. Problem Formulation

We consider a microservice system comprising $N$ observed services $\mathcal{V} = \{V_1, V_2, \dots, V_N\}$ and an unobserved set of latent infrastructure variables $\mathcal{L} = \{L_1, \dots, L_K\}$. Each service $V_i$ emits a continuous multi-variate telemetry stream $\mathbf{X}_i(t) = [x_{i,\text{latency}}(t), x_{i,\text{error}}(t), x_{i,\text{cpu}}(t)]^T$ sampled at uniform discrete intervals $\Delta t = 5.0\,\text{s}$.

An incident occurs at an unknown onset time $t^*$, triggered by an exogenous fault injected into a root service $V^* \in \mathcal{V}$ (or an unobserved latent entity $L^* \in \mathcal{L}$). The diagnosis system receives an observation window $\mathcal{W}_{\text{obs}} = [t^* - T_{\text{ref}}, t^* + T_{\text{post}}]$ consisting of a reference baseline period ($T_{\text{ref}} = 100\,\text{s}$, 20 windows) and an incident period ($T_{\text{post}} = 100\,\text{s}$, 20 windows).

### 3.1 Ground-Truth Labels and Identifiability
A diagnostic scenario $s$ is assigned a ground-truth label $y(s) \in \{\text{ATTRIBUTE}(V^*), \text{ABSTAIN\_REQUIRED}\}$ derived from noise-free simulator physics:
1. **ATTRIBUTE($V^*$):** The fault originates at an observed root $V^* \in \mathcal{V}$, exhibits an apparent signal-to-noise ratio $\text{SNR} \ge 4.0\sigma$ above reference baseline, generates a detectable interventional effect ($\Delta \ge 1.0\sigma$), and possesses asymmetric temporal or graphical structure that distinguishes $V^*$ from its peers.
2. **ABSTAIN\_REQUIRED:** The scenario cannot be reliably attributed due to one of five fundamental identifiability barriers:
   - `NO_FAULT`: No anomalous behavior injected.
   - `ROOT_UNOBSERVED`: The fault originated in an uninstrumented service or latent infrastructure node ($L^* \in \mathcal{L}$).
   - `SYMMETRIC_MUTUAL_DEPENDENCY`: Mutual cyclic RPC dependencies prevent causal ordering.
   - `WEAK_SIGNAL`: The fault amplitude is buried in baseline noise ($\text{SNR} < 4.0\sigma$).
   - `NO_DISCRIMINATING_EVIDENCE`: Telemetry divergence is observationally indistinguishable across multiple candidates.

### 3.2 Evaluation Metrics and Outcome Partition
Given system prediction $\hat{y}(s) \in \mathcal{V} \cup \{\text{ABSTAIN}\}$, each scenario outcome is partitioned into mutually exclusive categories:
- **Correct Attribution ($C$):** $y(s) = \text{ATTRIBUTE}(V^*)$ and $\hat{y}(s) = V^*$.
- **Correct Abstention ($A$):** $y(s) = \text{ABSTAIN\_REQUIRED}$ and $\hat{y}(s) = \text{ABSTAIN}$.
- **Unsafe False Attribution ($S$):** The system outputs $\hat{y}(s) = V'$ where either $y(s) = \text{ABSTAIN\_REQUIRED}$ (attributing an unidentifiable scenario) or $y(s) = \text{ATTRIBUTE}(V^*)$ with $V' \ne V^*$ (attributing the wrong root).
- **Benign Miss ($M$):** $y(s) = \text{ATTRIBUTE}(V^*)$ and $\hat{y}(s) = \text{ABSTAIN}$.

We report:
1. **Correct-Root Accuracy ($P_1$):** Fraction of correct attributions among ATTRIBUTE scenarios ($C / N_{\text{ATTR}}$).
2. **Outcome Accuracy ($P_2$):** Fraction of overall correct decisions ($(C + A) / N_{\text{total}}$).
3. **Unsafe Rate ($P_3$):** Fraction of unsafe false attributions ($S / N_{\text{total}}$).
4. **Coverage:** Fraction of scenarios where the system attempts an attribution ($(\text{Total Answered}) / N_{\text{total}}$).

### 3.3 Linear Expected Utility Model
To balance attribution benefits against the severe operational risks and overhead of active network probing, we define a normative linear utility function:
$$U(s) = \mathbb{I}[\text{Correct}] - \lambda \cdot \mathbb{I}[\text{Unsafe}] - \gamma \cdot \left(\frac{n_{do}(s)}{n_{do,\text{max}}}\right)$$
where $\lambda = 2.0$ represents the penalty for an unsafe attribution, $\gamma = 1.0$ scales intervention cost, $n_{do}(s)$ is the number of active interventions executed, and $n_{do,\text{max}} = 20$ normalizes interventional budget. The always-abstain baseline ($n_{do} = 0, \text{Unsafe} = 0, \text{Correct} = 0$) achieves $U \equiv 0.000$ by definition.

---

## 4. RIFT Architecture

RIFT executes across five sequential pipeline stages:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RIFT V3 PIPELINE                               │
│                                                                             │
│  ┌───────────────────────┐         ┌──────────────────────────────────────┐ │
│  │ Stage 1: EBD Detector │         │ Stage 2: FCI / PAG Causal Discovery  │ │
│  │ Multi-metric CUSUM    │ ──────► │ Learns Partial Ancestral Graph (PAG) │ │
│  │ θ = 3.0σ, persist = 2 │         │ Identifies Latent Confounders (↔)    │ │
│  └───────────────────────┘         └──────────────────┬───────────────────┘ │
│                                                       │                     │
│  ┌────────────────────────────────────────────────────┘                     │
│  ▼                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Stage 3: MSIS Budgeted Intervention Selection                          │ │
│  │ Prioritizes upstream candidates; enforces safety hard-stops            │ │
│  └────────────────────────────────────┬───────────────────────────────────┘ │
│                                       │                                     │
│  ┌────────────────────────────────────┘                                     │
│  ▼                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Stage 4: CID Interventional Divergence Engine                          │ │
│  │ Injects NetNS tc netem latency; computes 2-sample W₁ Permutation Test  │ │
│  └────────────────────────────────────┬───────────────────────────────────┘ │
│                                       │                                     │
│  ┌────────────────────────────────────┘                                     │
│  ▼                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Stage 5: Decision & Abstention Controller                              │ │
│  │ Abstains if unidentifiable, symmetric, weak-signal, or unoriented      │ │
│  │ Outputs: ATTRIBUTE(V*) or ABSTAIN_REQUIRED                             │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Stage 1: Earliest Behavioral Divergence (EBD)
EBD computes standardized score deviations $z_i(t) = (x_i(t) - \mu_{i,\text{ref}}) / \sigma_{i,\text{ref}}$ across telemetry streams. A divergence candidate is flagged when $z_i(t) \ge \theta_{\text{detect}} = 3.0$ for at least $k_{\text{persist}} = 2$ consecutive windows. EBD outputs an initial candidate set $\mathcal{C}_{\text{EBD}}$ ranked by earliest onset timestamp.

### 4.2 Stage 2: Fast Causal Inference (FCI)
RIFT constructs a Partial Ancestral Graph (PAG) $\mathcal{P} = (\mathcal{V}, \mathcal{E})$ from observation-window telemetry using the constraint-based FCI algorithm (`causal-learn` implementation with Fisher-$Z$ conditional independence testing at $\alpha = 0.05$). The PAG explicitly models latent confounders:
- **Directed Edge ($X \rightarrow Y$):** $X$ is an ancestor of $Y$; no latent confounder.
- **Bi-directed Edge ($X \leftrightarrow Y$):** Latent common cause $L \rightarrow X, L \rightarrow Y$; neither is an ancestor of the other.
- **Partially Oriented Edge ($X \circ\rightarrow Y, X \circ-\circ Y$):** Tail marks ($\circ$) indicate uncertainty regarding ancestry due to equivalence classes.

### 4.3 Stage 3: Multi-Stage Intervention Selection (MSIS)
To minimize runtime operational risk, MSIS selects intervention candidates using a greedy cost-benefit heuristic. It computes an expected disruption cost:
$$\text{Cost}(V_i) = \text{DegradationFactor}(V_i) \times \text{EstimatedTTR}(V_i)$$
MSIS prunes downstream services whose anomaly can be accounted for by upstream ancestral paths in $\mathcal{P}$.

### 4.4 Stage 4: Causal Identifiability and Divergence (CID)
For each selected candidate $V_c$, RIFT injects a synthetic network perturbation (e.g., adding $100\,\text{ms}$ delay with $10\,\text{ms}$ jitter via container network namespace `tc netem`). Downstream metric distributions during the baseline window $\mathcal{W}_{\text{pre}}$ and intervention window $\mathcal{W}_{\text{do}}$ are compared using the 1-Wasserstein metric:
$$\mathcal{W}_1(P, Q) = \int_{-\infty}^{\infty} |F_P(u) - F_Q(u)| \, du$$
Statistical significance is established via a two-sample permutation test ($B = 1000$ resamples) with false-discovery rate control.

### 4.5 Stage 5: Decision Engine (V2 vs. V3 Architectural Differences)
- **RIFT V2 (Baseline Architecture):** Attributes $V^*$ if $V^*$ is the earliest divergent node exhibiting significant interventional divergence ($p < 0.05$) on a semi-directed path in $\mathcal{P}$.
- **RIFT V3 (Conservative Hardened Architecture):** Introduces four safety guards:
  1. *Graph-Agnostic Candidate Injection:* Prevents graph-miss dropouts when FCI erroneously isolates the true root.
  2. *Positive Control & Symmetry Check:* Enforces bidirectional intervention testing across mutual dependencies; abstains if both directions diverge symmetrically.
  3. *Earlier-Divergence Guard:* Forbids attributing node $V_i$ if an upstream or peer node $V_j$ exhibited earlier divergence with comparable SNR.
  4. *Holm-Bonferroni Correction:* Controls family-wise error across multiple interventional candidate tests.

---

## 5. Ground-Truth and Evaluation Framework

### 5.1 Definitional Label Cascade and Circularity
Ground-truth scenario labels are computed via a 6-step cascade over noise-free simulator physics:
1. `NO_FAULT`: If fault amplitude $= 0 \implies \text{ABSTAIN\_REQUIRED}$.
2. `ROOT_UNOBSERVED`: If $V^* \notin \mathcal{V} \implies \text{ABSTAIN\_REQUIRED}$.
3. `INSUFFICIENT_BASELINE`: If baseline duration $< 100\,\text{s} \implies \text{ABSTAIN\_REQUIRED}$.
4. `SYMMETRIC_MUTUAL_DEPENDENCY`: If cyclic structure prevents causal ordering $\implies \text{ABSTAIN\_REQUIRED}$.
5. `WEAK_SIGNAL`: If apparent fault $\text{SNR} < 4.0\sigma \implies \text{ABSTAIN\_REQUIRED}$.
6. `ATTRIBUTE(V*)`: If the root produces an interventional effect $\ge 1.0\sigma$ within $45\,\text{s}$.

**Methodological Disclosure on Definitional Circularity:**  
While ground-truth generation contains **no method-output leakage** (labels are generated strictly before inference without reading RIFT predictions), the criteria for `ATTRIBUTE` vs `ABSTAIN_REQUIRED` share structural constants with RIFT's detection engine (e.g., $\text{SNR} \ge 4.0\sigma$ mirrors the $\theta = 3.0\sigma$ detector; $1.0\sigma$ mirrors CID effect thresholds). In the pooled development and validation set ($N=252$), $49$ of $99$ ATTRIBUTE labels rely solely on the earliest-divergence rule. Consequently, measured performance represents agreement with the simulator's formal identifiability specifications rather than unconstrained causal discovery.

### 5.2 Threshold-Free Structural Sensitivity (L-struct)
To evaluate the impact of threshold circularity, we implemented **L-struct**, a structural sensitivity label that evaluates steps 1–4 of the cascade (pure topology, observability, and baseline duration) without applying signal, SNR, or persistence thresholds, co-reporting four continuous detectability covariates:
- `root_snr_noisefree`: True noise-free fault magnitude in standard deviations.
- `expected_do_effect_sigma`: Theoretical perturbation effect delivered to downstream sinks.
- `effect_arrival_latency_s`: Expected transit lag along causal paths.
- `temporal_separation_s`: Difference in onset arrival between root and nearest peer.

---

## 6. Experimental Design

Our evaluation is structured across four distinct evidence tiers:

```mermaid
graph TD
    subgraph Historical Evidence
        E1[Spent Held-Out Split<br>N=108, V2 Only<br>One-Shot Frozen]
        E2[Development Split<br>N=180, V2 & V3]
        E3[Validation Split<br>N=72, V2 & V3]
        E4[Adversarial Stress Cohort<br>N=112, 14 Fault Types]
    end
    subgraph Confirmatory Protocol
        C1[Drafted Confirmatory Plan (not yet recorded/approved)<br>N=2000, 256 Template Cells<br>Gates G0-G6: PENDING CONFIRMATORY RUN]
    end
```

1. **Spent Held-Out Split ($N=108$, Sprint 4.3):** A sealed, one-shot test partition ($45$ ATTRIBUTE, $63$ ABSTAIN\_REQUIRED) executed once on RIFT V2 at timestamp `2026-11-03T04:06:00Z` following a 37-file hash freeze. RIFT V3 was not evaluated on this split during Sprint 4.4 (to prevent adaptive overfitting). In Sprint 7 the frozen V3 was run once on it as a re-opening (`allow_reopen=True`, registry flag `valid_for_final_claims=False`; `docs/recovery/SPRINT7_HELDOUT_EVALUATION.md`): V3 mean utility was $-0.664$ at $\lambda=2$ (below always-abstain, CI entirely below 0) and not distinguishable from V2 ($-0.594$; V3$-$V2 $-0.070$, CI $[-0.336, +0.194]$), so V3's development/validation safety gain did not reappear (P3\_safe $+0.037$, $p=0.585$). This is not a confirmatory result; V3's design had seen the published V2 held-out failure analysis.
2. **Development Split ($N=180$, Sprint 4.4):** Used for iterative failure taxonomy analysis and V3 architectural design ($68$ ATTRIBUTE, $112$ ABSTAIN\_REQUIRED).
3. **Validation Split ($N=72$, Sprint 4.4):** Used for frozen intermediate verification ($31$ ATTRIBUTE, $41$ ABSTAIN\_REQUIRED).
4. **Adversarial Stress Cohort ($N=112$, Sprint 4.4):** 14 targeted structural failure archetypes (8 variants each, $80$ ATTRIBUTE, $32$ ABSTAIN\_REQUIRED), including unobserved roots, cyclic feedback, multi-hop latency cascades, and confounding noise.
5. **Confirmatory Experiment ($N=2000$, Sprint 4.5.1 Plan):** A drafted (not yet recorded or approved) $16 \times 16$ crossed motif design. **Status: PENDING CONFIRMATORY RUN (Not Yet Executed).**

---

## 7. Empirical Results

All reported results are derived strictly from recomputed, verified repository ledgers (`artifacts/sprint4_5_1/utility/utility_verification.json`, `docs/SPRINT4_3_0_FINAL_REPORT.md`, `docs/SPRINT4_4_0_FINAL_REPORT.md`).

### 7.1 Spent Held-Out Split Results (RIFT V2, $N=108$)

| Method / Comparator | $N$ | Correct Root ($P_1$) | Outcome Acc ($P_2$) | Unsafe Rate ($P_3$) | Coverage |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **RIFT-FULL-V2** | 108 | 20 / 45 (44.4%) | 60 / 108 (55.6%) | 37 / 108 (34.3%) | 57 / 108 (52.8%) |
| **Always-Abstain (AA)** | 108 | 0 / 45 (0.0%) | **63 / 108 (58.3%)** | **0 / 108 (0.0%)** | 0 / 108 (0.0%) |
| RIFT-LEGACY | 108 | 21 / 45 (46.7%) | 52 / 108 (48.1%) | 49 / 108 (45.4%) | 70 / 108 (64.8%) |
| B5-RIFT-OBS (Observational) | 108 | 17 / 45 (37.8%) | 42 / 108 (38.9%) | 53 / 108 (49.1%) | 70 / 108 (64.8%) |
| B6/B7 (One-Shot / Random Probing) | 108 | 27 / 45 (60.0%) | 33 / 108 (30.6%) | 75 / 108 (69.4%) | 102 / 108 (94.4%) |
| Oracle Graph Upper Bound | 108 | 32 / 45 (71.1%) | 60 / 108 (55.6%) | 41 / 108 (38.0%) | 73 / 108 (67.6%) |
| Theoretical Oracle Ceiling | 108 | 45 / 45 (100.0%) | 108 / 108 (100.0%) | 0 / 108 (0.0%) | 45 / 108 (41.7%) |

*Key Findings on Held-Out Split:*
- **Failure to Beat Always-Abstain:** RIFT V2 outcome accuracy ($55.6\%$) is statistically indistinguishable from, and numerically lower than, the always-abstain baseline ($58.3\%$; $\Delta = -0.028$, $95\%$ CI $[-0.145, +0.102]$, exact McNemar $p = 0.76$).
- **Dominance over Unconstrained Baselines:** RIFT V2 significantly outperforms never-abstaining baselines (B0–B3, B6–B7; Holm-adjusted $p \le 0.0028$), but this advantage is driven entirely by abstaining on unidentifiable scenarios ($58.3\%$ of the benchmark).

### 7.2 Development and Validation Split Performance (V2 vs. V3)

| Partition / Split | Method | Correct Root ($P_1$) | Outcome Acc ($P_2$) | Unsafe Rate ($P_3$) | Coverage | Mean Interventions ($n_{do}$) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Development**<br>($N=180; 68\,\text{ATTR}$)| RIFT V2<br>RIFT V3<br>**Always-Abstain** | 28 / 68 (41.2%)<br>32 / 68 (47.1%)<br>0 / 68 (0.0%) | 102 / 180 (56.7%)<br>116 / 180 (64.4%)<br>**112 / 180 (62.2%)** | 52 / 180 (28.9%)<br>35 / 180 (19.4%)<br>**0 / 180 (0.0%)** | 80 / 180 (44.4%)<br>67 / 180 (37.2%)<br>0 / 180 (0.0%) | 1.49 (max 6)<br>2.51 (max 8)<br>0.0 |
| **Validation**<br>($N=72; 31\,\text{ATTR}$) | RIFT V2<br>RIFT V3<br>**Always-Abstain** | 8 / 31 (25.8%)<br>13 / 31 (41.9%)<br>0 / 31 (0.0%) | 35 / 72 (48.6%)<br>44 / 72 (61.1%)<br>**41 / 72 (56.9%)** | 27 / 72 (37.5%)<br>13 / 72 (18.1%)<br>**0 / 72 (0.0%)** | 35 / 72 (48.6%)<br>26 / 72 (36.1%)<br>0 / 72 (0.0%) | 1.71 (max 6)<br>3.19 (max 8)<br>0.0 |
| **Pooled [DEV+VAL]**<br>($N=252; 99\,\text{ATTR}$) | RIFT V2<br>RIFT V3<br>**Always-Abstain** | 36 / 99 (36.4%)<br>45 / 99 (45.5%)<br>0 / 99 (0.0%) | 137 / 252 (54.4%)<br>160 / 252 (63.5%)<br>**153 / 252 (60.7%)** | 79 / 252 (31.3%)<br>48 / 252 (19.0%)<br>**0 / 252 (0.0%)** | 115 / 252 (45.6%)<br>93 / 252 (36.9%)<br>0 / 252 (0.0%) | 1.556 (max 6)<br>2.706 (max 8)<br>0.0 |

*Statistical Comparisons (McNemar Tests):*
- **Correct-Root Accuracy ($P_1$):** Dev $\Delta = +5.9\%$ ($p=0.503$); Val $\Delta = +16.1\%$ ($p=0.180$). **No statistically significant improvement.**
- **Outcome Accuracy ($P_2$):** Dev $\Delta = +7.8\%$ (uncorrected $p=0.0488$, Holm-adjusted $p=0.195$); Val $\Delta = +12.5\%$ (uncorrected $p=0.0490$, Holm-adjusted $p=0.195$). **Does not survive multi-test correction.**
- **Unsafe Rate Reduction ($P_3$):** Dev $-9.5\%$ ($p=0.0115$, Holm $p=0.0575$); Val $-19.4\%$ ($p=0.0026$, Holm $p=0.0155$). **Statistically significant on validation split.**

### 7.3 Linear Utility Analysis (Pooled $N=252$)
At normative weights ($\lambda = 2.0, \gamma = 1.0, \kappa = 0.05$):
- **RIFT V3-FULL:** Mean $U = \mathbf{-0.3377}$ ($95\%$ studentized template bootstrap CI $[-0.472, -0.222]$; group-clustered CI $[-0.514, -0.203]$).
- **RIFT V2-FULL:** Mean $U = \mathbf{-0.5619}$ ($95\%$ CI $[-0.712, -0.413]$).
- **Always-Abstain (AA):** Mean $U \equiv \mathbf{0.0000}$.
- **Contrast ($V_3 - V_2$):** $\Delta U = \mathbf{+0.2242}$ ($95\%$ CI $[+0.086, +0.366]$, $p < 0.001$).
- **Contrast ($V_3 - \text{AA}$):** $\Delta U = \mathbf{-0.3377}$ (Bootstrap $P(U > 0) = 0.0000$).
- **Break-Even Analysis:** RIFT V3's point-estimate break-even against always-abstain is $\lambda^* = 0.9375$ (95% CI $[0.614, 1.436]$) at zero intervention cost ($\kappa = 0$); the paired difference is significantly positive only for $\lambda \le 0.61$ at $\kappa = 0$ and $\lambda \le 0.30$ at $\kappa = 0.025$, and at no $\lambda \ge 0$ for $\kappa \ge 0.05$. These weights are normative, not calibrated to real costs. For any realistic operational penalty ($\lambda \ge 2.0$), always-abstain strictly dominates.

---

## 8. Failure Analysis

Through systematic auditing of all 252 development/validation scenarios and 112 adversarial runs, we isolate the fundamental failure modes of interventional causal RCA:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DISTRIBUTION OF ATTRIBUTION FAILURES                  │
│                                                                             │
│  Downstream Descendant Selected (100% of V2 Wrong Roots)                    │
│  ████████████████████████████████████████████████████████████ 14/14 cases   │
│                                                                             │
│  FCI Skeleton Undecidability (Circle Marks on Learned Edges)                │
│  ███████████████████████████████████████████████████████████░ 97.8% of edges│
│                                                                             │
│  Unobserved Root Identifiability Boundary (A12 Adversarial)                 │
│  ████████████████████████████████████████████████████████████ 7/7 unsafe    │
│                                                                             │
│  Lucky Attributions on Unidentifiable Scenarios (V3 Pooled)                 │
│  ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 18/153 cases  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.1 The Downstream Descendant Trap
In $100\%$ of RIFT V2 wrong-root attributions on the held-out split (14/14 cases), the algorithm selected a downstream descendant of the true root along a semi-directed path ($\circ\rightarrow$ or $\rightarrow$). Because downstream services accumulate latency cascades from upstream dependencies, their telemetry variance often exceeds that of the root. When constraint-based discovery fails to direct the edge, EBD heuristics fall back to downstream nodes.

### 8.2 FCI Graph Undecidability
Across all evaluated scenarios, FCI graph reconstruction suffered severe undecidability:
- **Skeleton Quality:** Precision $= 0.675$ (dev) / $0.622$ (val); Recall $= 0.424$ (dev) / $0.355$ (val); $F_1 = 0.52$ / $0.45$.
- **Edge Orientation:** $97.8\%$ (dev) and $97.0\%$ (val) of learned edges contained circle marks ($\circ-\circ$ or $\circ\rightarrow$). Only 1 edge on dev and 2 edges on val were fully directed ($X \rightarrow Y$).
- **Graph Bottleneck:** Replacing learned graphs with an Oracle Graph (Table 1, R10) increased correct-root accuracy from $44.4\%$ to $71.1\%$, proving that causal discovery quality is the primary limiting bottleneck.

### 8.3 Interventional Temporal Drift Confounding
CID evaluates $do(X)$ by comparing pre-intervention baseline $\mathcal{W}_{\text{pre}}$ with intervention window $\mathcal{W}_{\text{do}}$. Because both windows execute sequentially in the same service instance without a concurrent untreated twin, background non-stationary load drift is confounded with intervention effect. In exploratory audits, uncompensated drift triggered false interventional divergences in $94\%$ (dev) and $100\%$ (val) of non-ancestral candidate pairs whose outcome experienced drift $\ge 0.3\sigma$.

### 8.4 Unobserved Root Identifiability Boundary
When a fault originates in unobserved infrastructure (Adversarial Type A12), RIFT V3 triggered an unsafe attribution in $100\%$ of cases ($7/7$ unsafe; V2 $8/8$ unsafe). Because the true root $L^*$ is unmeasured, the earliest observed descendant $V_{\text{first}}$ behaves statistically as an exogenous source node, completely evading abstention guards.

---

## 9. Threats to Validity

1. **Definitional Circularity:** Ground-truth identifiability labels share detection thresholds ($\text{SNR} \ge 4.0\sigma$, $\theta = 3.0\sigma$) with RIFT. Shifting the SNR gate to $3.0\sigma$ on dev/val reclassifies 29 scenarios from ABSTAIN to ATTRIBUTE, demonstrating that measured accuracy is coupled to simulator design choices.
2. **Crossed Statistical Dependence:** Scenarios are constructed by crossing 16 structural motifs with 16 fault families. Observations within the same family exhibit intra-class correlation ($\text{ICC} = +0.016$), inflating standard bootstrap Type I error ($0.05 \rightarrow 0.20$).
3. **Synthetic Testbed Scope:** All telemetry is generated from a synthetic queuing simulator. Real-world microservices feature non-linear queue saturation, thread pool exhaustion, and asynchronous event loops not fully captured by linear Gaussian models.
4. **Environment Discrepancies:** Historical results were generated under Python 3.9.6 with `causal-learn 0.1.4.8`, whereas CI platforms utilizing Python 3.11 with `causal-learn 0.1.3.8` exhibit minor edge-orientation variations on isolated scenarios.
5. **Confirmatory Experiment Status:** Gates G0–G6 of the 2,000-scenario confirmatory trial remain unexecuted pending independent human sign-off (D7) and full protected test authorization (D12).

---

## 10. Discussion

### 10.1 Why Does Always-Abstain Dominate?
In operational environments where the majority of incidents ($\approx 58\%–60\%$) represent unidentifiable scenarios (weak signals, unobserved infrastructure, symmetric dependencies), the expected utility of attempting an attribution is sharply constrained. If an algorithm achieves $45\%$ accuracy on the $40\%$ attributable partition but incurs a $20\%$ unsafe rate across the entire corpus, the penalty $\lambda \cdot P(\text{Unsafe}) = 2.0 \times 0.20 = 0.40$ completely cancels out the correct attribution reward $1.0 \times (0.45 \times 0.40) = 0.18$. Under realistic operational costs, conservative abstention is the mathematically optimal policy.

### 10.2 What Do Interventions Actually Provide?
Our empirical ablations demonstrate that runtime network interventions provided **no statistically significant improvement in attribution accuracy** over purely observational ranking (A6/A8 ablations achieved $P_1 = 44.4\%$, identical to full RIFT V2). Interventions served primarily as a secondary filtering gate for abstention, which RIFT V3 achieved more safely through algorithmic guards and multiple-testing corrections without requiring live perturbations.

---

## 11. Conclusion

This paper presented an empirical investigation into the limits of passive and interventional causal root-cause analysis in microservices. Evaluating RIFT across 360 benchmark scenarios and 112 adversarial tests demonstrates that constraint-based discovery cannot reliably orient causal ancestry in finite telemetry samples, leading to persistent downstream descendant misattributions. While RIFT V3 establishes a disciplined framework for identifiability-conditioned abstention—reducing unsafe decisions by $39\%$ relative to RIFT V2 on development/validation scenarios (partly by answering less often)—it does not outperform a trivial always-abstain baseline on outcome accuracy or linear expected utility. We conclude that future microservice diagnosis research must abandon unconstrained accuracy claims, mandate always-abstain baselines, and account for cluster-level statistical dependencies in benchmark evaluation.

---

## References

1. **[Alvaro et al., SIGMOD 2015]** P. Alvaro, J. Rosen, and J. M. Hellerstein, "Lineage-driven fault injection," in *Proc. 2015 ACM SIGMOD Int. Conf. Management of Data*, 2015, pp. 515–526.
2. **[Basiri et al., IEEE Software 2016]** A. Basiri, N. Sengupta, J. Trichter, M. Ruehle, et al., "Chaos Engineering," *IEEE Software*, vol. 33, no. 3, pp. 35–41, 2016.
3. **[Chen et al., INFOCOM 2014]** P. Chen, Y. Qi, P. Zheng, and D. Hou, "CauseInfer: Automated end-to-end performance anomaly diagnosis for multi-tier distributed systems," in *Proc. IEEE INFOCOM*, 2014, pp. 1337–1345.
4. **[Gan et al., ASPLOS 2021]** Y. Gan, M. Liang, et al., "Sage: Practical and consistent anomaly detection and root cause analysis in microservices," in *Proc. ASPLOS*, 2021, pp. 878–893.
5. **[Ikram et al., ICSE 2022]** A. Ikram, S. Chakrabarti, et al., "Root cause analysis of anomalies in microservices using causal inference," in *Proc. 44th Int. Conf. Software Engineering (ICSE)*, 2022, pp. 1–12.
6. **[Kandula et al., SIGCOMM 2008]** S. Kandula, R. Mahajan, et al., "Detailed diagnosis in enterprise networks," in *Proc. ACM SIGCOMM*, 2008, pp. 243–254.
7. **[Pearl, 2009]** J. Pearl, *Causality: Models, Reasoning, and Inference*, 2nd ed. Cambridge University Press, 2009.
8. **[Spirtes et al., 2000]** P. Spirtes, C. N. Glymour, and R. Scheines, *Causation, Prediction, and Search*, 2nd ed. MIT Press, 2000.
9. **[Wang et al., CCGrid 2018]** P. Wang, J. Xu, M. Ma, et al., "CloudRanger: Root cause analysis on large-scale distributed systems via causal reasoning," in *Proc. 18th IEEE/ACM CCGrid*, 2018, pp. 112–121.
10. **[Wu et al., NOMS 2020]** L. Wu, J. Tordsson, E. Elmroth, and O. Kao, "MicroRCA: Root cause analysis of performance anomalies in microservices," in *Proc. IEEE/IFIP NOMS*, 2020, pp. 1–9.
11. **[Zhang et al., ICSE 2023]** Y. Zhang, Z. Hua, et al., "Sieve: Actionable root cause analysis for microservices via adaptive fault injection," in *Proc. 45th Int. Conf. Software Engineering (ICSE)*, 2023, pp. 1–13.
