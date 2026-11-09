# RIFT Sprint 2 — Formal Identifiability & Decision Theory

**Lead Author:** Causal Decision Theorist & Formal Methods Lead  
**Date:** 2026-11-02  
**Authority:** Formal Identifiability & Selective Classification Foundations  

---

## 1. Formal Decision Problem Formulation

Let $\mathcal{S} = \{s_1, \dots, s_n\}$ be the set of microservices in a cloud architecture.
- **Observed Evidence:** Incident metric telemetry time-series $\mathbf{X}_t \in \mathbb{R}^{n \times T}$ and invocation call graph $\mathcal{T} = (\mathcal{S}, E_{\text{call}})$.
- **Admissible Causal Model Set:** The learned Partial Ancestral Graph $\mathcal{P}$ represents the equivalence class of admissible Directed Acyclic Graphs $\mathcal{G}(\mathcal{P})$ compatible with conditional independencies and topological constraints.
- **Attribution Decision Space:** An action $\alpha \in \mathcal{S} \cup \{\bot\}$, where $\alpha = s_i$ attributes service $s_i$ as the root cause, and $\alpha = \bot$ represents safe abstention.

### Loss Function:
$$L(\alpha, s^*) = \begin{cases}
0 & \text{if } \alpha = s^* \text{ (Correct Attribution)} \\
C_{\text{FAR}} & \text{if } \alpha \neq s^* \text{ and } \alpha \neq \bot \text{ (False Attribution)} \\
C_{\text{abstain}} & \text{if } \alpha = \bot \text{ (Safe Abstention)}
\end{cases}$$
In production SRE operations, false remediation on an innocent service causes compounding outage duration ($C_{\text{FAR}} \gg C_{\text{abstain}}$).

---

## 2. Theoretical Theorems & Proofs

### Theorem 1 (Sound Identifiability Abstention)
*Let $\mathcal{P}$ be the learned PAG. If for a candidate service $s_i$, the causal effect on downstream anomalous symptoms $P(\mathbf{Y} | do(s_i))$ is non-identifiable under unmeasured confounding (violating both generalized backdoor and frontdoor criteria), and no distinguishing interventional evidence exists, then the Bayes-optimal decision is $\alpha^* = \bot$ whenever $\text{Pr}(s_i = s^* | \mathcal{P}) < 1 - \frac{C_{\text{abstain}}}{C_{\text{FAR}}}$.*

**Proof Sketch:**  
The expected loss of attributing $s_i$ is $R(s_i) = (1 - p_i) C_{\text{FAR}}$, where $p_i = \text{Pr}(s_i = s^* | \mathcal{P})$. The expected loss of abstaining is $R(\bot) = C_{\text{abstain}}$. Setting $R(s_i) > R(\bot)$ yields $(1 - p_i) C_{\text{FAR}} > C_{\text{abstain}} \implies p_i < 1 - \frac{C_{\text{abstain}}}{C_{\text{FAR}}}$. When confounding induces Markov equivalence among candidate nodes with uniform posterior entropy, $p_i \le 0.5$. Since $C_{\text{FAR}} \ge 5 C_{\text{abstain}}$, $1 - \frac{C_{\text{abstain}}}{C_{\text{FAR}}} \ge 0.8 > 0.5$. Hence, $R(s_i) > R(\bot)$ and $\alpha^* = \bot$. $\blacksquare$

### Theorem 2 (Conditional Attribution Validity under Active CID)
*Under Assumption A2 (Intervention Invariance) and an $\alpha$-level permutation test with $B \ge 1,000$ resamples for Wasserstein-1 distance $W_1(\hat{P}_{\text{pre}}, \hat{P}_{\text{post}})$, the probability of a false causal confirmation on an independent bystander node is bounded by $\alpha$.*

**Proof Sketch:**  
Under the null hypothesis $H_0: P(Y | do(X)) = P(Y | \text{baseline})$, the permutation distribution of the Wasserstein-1 test statistic $T = W_1$ is asymptotically exact. Selecting candidates that satisfy $p_{\text{perm}} < \alpha$ limits Type I error rate to $\le \alpha$, guaranteeing bounded false positive rates. $\blacksquare$
