# RIFT — Sprint 1: Scientific Claim-to-Evidence Matrix

**Audit Date:** 2026-11-02  
**Authority:** Empirical Grounding and Claim Traceability Matrix  

---

## 1. Claim-to-Evidence Mapping

```
┌─────────────────────────────────┬──────────────────────────┬─────────────────────────┬──────────────────────────┬──────────────────────────────┐
│ Scientific Claim / Hypothesis   │ Implementation Module    │ Test / Validation File  │ Experimental Output      │ Status & Evidential Verdict  │
├─────────────────────────────────┼──────────────────────────┼─────────────────────────┼──────────────────────────┼──────────────────────────────┤
│ H1: Interventional > Obs P@1    │ src/rift/fci/            │ test_fci.py             │ stat_test_results.json   │ UNSUPPORTED (p=0.5000, δ=0.0)│
│                                 │ src/rift/ebd/            │                         │ (Both abstain on N=18)   │ Needs N≥50 or graph prior.   │
├─────────────────────────────────┼──────────────────────────┼─────────────────────────┼──────────────────────────┼──────────────────────────────┤
│ H2: Confounder Abstention       │ src/rift/identifiability/│ test_identifiability.py │ stat_test_results.json   │ CONFIRMED (p<0.0001, δ=1.0)  │
│     (FAR = 0% vs Sieve 28%)     │                          │                         │ (100% correct abstention)│ Eliminates false attribution.│
├─────────────────────────────────┼──────────────────────────┼─────────────────────────┼──────────────────────────┼──────────────────────────────┤
│ H3: Closed-Loop > One-Shot      │ src/rift/loop/           │ test_closed_loop.py     │ stat_test_results.json   │ UNSUPPORTED (p=1.0000)       │
│     on Multi-Cause Scenarios    │                          │                         │ (Step data signal bounds)│ Needs dynamic cascades.      │
├─────────────────────────────────┼──────────────────────────┼─────────────────────────┼──────────────────────────┼──────────────────────────────┤
│ H4: MSIS Disruption Minimization│ src/rift/optimizer/      │ test_cost_model.py      │ comparative_results_*.json│ CONFIRMED (p<0.0001, δ=1.0)  │
│     (50% perturbation reduction)│                          │                         │ (30s MSIS vs 60s Random) │ Minimizes operational cost.  │
├─────────────────────────────────┼──────────────────────────┼─────────────────────────┼──────────────────────────┼──────────────────────────────┤
│ Oracle PAG Conditional Accuracy │ src/rift/baselines/oracle│ test_baselines_parity.py│ comparative_results_*.json│ CONFIRMED (100% Cond. P@1)   │
│     (Upper-Bound Diagnostic)    │                          │                         │ (100% precision on id-ed)│ Diagnostic upper bound only. │
└─────────────────────────────────┴──────────────────────────┴─────────────────────────┴──────────────────────────┴──────────────────────────────┘
```

---

## 2. In-Depth Evidential Analysis

1. **H2 (Identifiability-Conditioned Abstention):**  
   - *Claim:* Microservice RCA tools without formal identifiability checks produce catastrophic false root-cause attributions on confounded systems.
   - *Evidence:* Sieve-like heuristic propagation suffers 28.00% False Attribution Rate on Dev split ($n=50$) and 20.00% FAR on Held-Out split ($n=15$). RIFT's identifiability engine evaluates non-parametric backdoor/frontdoor criteria and achieves **0.00% FAR** ($p < 0.0001, \text{Cliff's } \delta = +1.000$).
2. **H4 (Cost-Budgeted Intervention Selection):**  
   - *Claim:* Multi-Stage Intervention Selection (MSIS) reduces runtime disruption compared to unguided exploration.
   - *Evidence:* MSIS reaches entropy convergence in 30.0s mean perturbation time vs. 60.0s for uniform random selection (**50.0% reduction**, $p < 0.0001, \text{Cliff's } \delta = +1.000$).
3. **H1 & H3 (Scientific Boundaries):**  
   - Unconstrained FCI requires $N \ge 50$ samples or topological priors to orient edges; contemporaneous step perturbations do not trigger unshielded colliders in tree topologies.
   - Step perturbations provide an overwhelming initial anomaly signal, masking the benefits of closed-loop Bayesian updating in single-point failures.
