# RIFT: Independent Scientific Red-Team Review

**Lead Investigator:** Agent N (Independent Scientific Red-Team Reviewer)  
**Date:** 2026-11-02  
**Purpose:** Rigorous Falsification and Critical Review of RIFT Claims  

---

## 1. Executive Summary & Critical Probing

As an independent red-team reviewer, this audit challenges the core empirical claims of RIFT to ensure that no circular reasoning, misleading metrics, or overstated contributions survive peer review.

---

## 2. Targeted Falsification Inquiries

### Inquiry 1: *"Does RIFT's 0.00% False Attribution Rate (FAR) merely reflect a trivial system that abstains on everything?"*
- **Skeptical Challenge:** A diagnostic system that always abstains trivially achieves 0% FAR and 100% abstention precision on confounded cases, but provides 0% utility to an SRE.
- **Red-Team Finding & Evidence:**  
  1. On unconstrained learned FCI graphs with small sample sizes ($N=18$), RIFT does indeed abstain 100% of the time because it refuses to guess on ambiguous orientations.
  2. However, when causal orientations are identified (e.g., under Oracle PAG or when call graph priors orient edges), RIFT achieves **100.00% Conditional Precision@1** on all identifiable cases ($26\%$ coverage on Dev split), while continuing to abstain on the $74\%$ confounded or unidentifiable cases.
  3. **Paper Remediation:** The manuscript must report Coverage and Conditional Precision side-by-side with Raw Precision. It must explicitly state: *"RIFT trades off coverage for zero false attributions when causal directions cannot be verified."*

### Inquiry 2: *"Why does a trivial latency baseline (B1-LATENCY-CORR) achieve 100% accuracy?"*
- **Skeptical Challenge:** If a simple z-score + trigger time ranking achieves 100% accuracy on the benchmark, why is complex causal discovery and active network intervention needed?
- **Red-Team Finding & Evidence:**  
  1. Synthetic benchmark step functions inject an instantaneous shift ($+50\text{ms}$) into the root cause at $t_0$, and delayed shifts ($+40\text{ms}$) into downstream nodes.
  2. In this idealized setting, temporal onset perfectly tracks root causes.
  3. However, on confounded faults (where two services degrade at the exact same $t_0$ due to an unmeasured resource), correlation-based methods cannot determine which service is the root cause and which is a bystander, yielding up to 28% false attributions in Sieve-like propagation models.
  4. **Paper Remediation:** The manuscript must acknowledge this benchmark characteristic honestly and position RIFT's true value as resolving confounding ambiguities rather than simple single-step latency spikes.

### Inquiry 3: *"Does Oracle PAG overstate practical performance?"*
- **Skeptical Challenge:** Oracle PAG uses the ground-truth causal path, which an operator does not possess in advance.
- **Red-Team Finding & Evidence:**  
  1. Oracle PAG is strictly an **upper-bound diagnostic** demonstrating the efficacy of CID intervention divergence when topological orientation is known.
  2. In the paper, Learned FCI and Oracle PAG are presented in separate columns, preventing any misinterpretation of oracle results as deployable baseline performance.

---

## 3. Red-Team Recommendations for IEEE Manuscript

1. **Do not claim superior raw accuracy over heuristic baselines on synthetic step data.** Frame RIFT's contribution as **principled identifiability-conditioned abstention and cost-budgeted active divergence under unmeasured confounding**.
2. **Explicitly disclose sample density requirements for FCI ($N \ge 50$ samples or static tracing priors).**
3. **Report leaf-service boundaries as an inherent structural property of downstream divergence detection.**
