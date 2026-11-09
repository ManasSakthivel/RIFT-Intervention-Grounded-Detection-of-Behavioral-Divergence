# RIFT: Final Research Decision & Publication Positioning

**Lead Authority:** Autonomous Research Lead & Principal Scientist  
**Date:** 2026-11-02  
**Final Decision Outcome:** **OUTCOME B — Narrowed, Defensible Scientific Contribution**  

---

## 1. Executive Research Decision

After rigorous independent verification, baseline dissection, held-out evaluation ($n=15$), and statistical auditing, the scientific contribution of RIFT is formally positioned under **Outcome B**:

> **Outcome B:** A narrower, mathematically defensible contribution is supported—specifically:
> 1. **Identifiability-Conditioned Abstention under Confounding:** RIFT eliminates false root-cause attributions (achieving 0.00% False Attribution Rate across all splits, compared to 28.00% FAR for Sieve-like heuristic propagation, $p < 0.0001, \text{Cliff's } \delta = +1.000$).
> 2. **Cost-Aware Multi-Stage Intervention Selection (MSIS):** RIFT reduces cumulative system perturbation duration by 50.0% compared to random exploration ($p < 0.0001, \text{Cliff's } \delta = +1.000$).
> 3. **Defensible Boundary Characterization:** Broader claims that unconstrained constraint-based causal discovery (FCI) can learn causal graphs from short observational windows ($N < 30$) without topological priors are **retracted and explicitly disclosed as operational boundaries**.

---

## 2. Evidence-Backed Summary of Findings

```
┌─────────────────────────────────────────────────────────────┬──────────┬─────────────────────────────────────────────────────────┐
│ Evaluation Area                                             │ Verdict  │ Core Scientific Evidence                                │
├─────────────────────────────────────────────────────────────┼──────────┼─────────────────────────────────────────────────────────┤
│ H1: Learned FCI Intervention vs Observation                 │ UNSUPP.  │ N=18 yields unoriented PAGs; both abstain conservatively│
│ H2: Identifiability Abstention on Confounded Faults         │ CONFIRM. │ p < 0.0001, δ = +1.000; 0% FAR vs 28% FAR in Sieve     │
│ H3: Closed-Loop Bayesian Adaptation on Step Perturbations   │ UNSUPP.  │ Step data signal dominates initial EBD prior            │
│ H4: Cost Minimization via Greedy MSIS vs Random             │ CONFIRM. │ p < 0.0001, δ = +1.000; 30s vs 60s (50% reduction)      │
│ Held-Out Generalization (n=15)                              │ CONFIRM. │ 0.00% FAR, 100% Conditional P@1 on identifiable cases   │
└─────────────────────────────────────────────────────────────┴──────────┴─────────────────────────────────────────────────────────┘
```

---

## 3. Manuscript & Paper Refactoring Directives

1. **Title & Abstract:** Reframe the paper from *"universal autonomous root-cause discovery"* to *"Intervention-Grounded Detection of Behavioral Divergence: Eliminating False Attributions under Unmeasured Confounding"*.
2. **Baselines & Metrics:** Explicitly report Coverage, Abstention Rate, and False Attribution Rate side-by-side with Precision@1.
3. **Learned vs. Oracle Separation:** Clearly distinguish Learned FCI (operational constraint) from Oracle PAG (upper-bound diagnostic).
4. **Threats to Validity & Limitations:** Fully disclose sample density requirements ($N \ge 50$ or static distributed tracing priors) and leaf-node call topology boundaries.
