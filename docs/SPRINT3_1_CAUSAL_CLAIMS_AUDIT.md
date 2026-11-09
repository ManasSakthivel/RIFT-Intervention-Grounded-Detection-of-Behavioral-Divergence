# RIFT Sprint 3.1 — Causal Claims & Inference Boundary Audit

**Audit Date:** 2026-11-02  
**Lead Auditor:** Causal Inference & Theory Auditor  
**Authority:** Task 6 Causal Semantics and Invariant Verification  

---

## 1. Disentangling the Three Causal Stages in RIFT

```
┌─────────────────────────────────┬──────────────────────────────────┬────────────────────────────────────────────────────────┐
│ Causal Stage                    │ Mechanism                        │ Scientific Meaning & Invariant                         │
├─────────────────────────────────┼──────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Stage 1: Candidate Reachability │ Semi-Directed Paths in PAG / SCG │ Identifies plausible upstream ancestors (u rightsquigarrow v).   │
│                                 │ (Allows →, o→, o-o; forbids ↔)   │ Does NOT prove causal direction.                       │
├─────────────────────────────────┼──────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Stage 2: Causal Identification  │ Non-parametric Backdoor/Frontdoor│ Determines if P(Y | do(X)) is identifiable from data. │
│                                 │ Checks over Learned / Oracle PAG │ Abstains if unmeasured confounding blocks derivation.  │
├─────────────────────────────────┼──────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Stage 3: Active Interventional  │ Wasserstein-1 (W₁) Divergence    │ Experimentally confirms directional transmission:      │
│ Confirmation (CID)              │ Permutation Test (p < 0.01)      │ Perturbing X induces significant downstream effect Y. │
└─────────────────────────────────┴──────────────────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 2. Invariant Boundaries & Paper Claims

1. **Semi-directed reachability is NOT causal proof:** Semi-directed reachability is strictly an admissibility filter that defines candidate intervention targets.
2. **Active Intervention is the causal arbiter:** The actual confirmation of root cause occurs during Stage 3 (CID), where physical network perturbation resolves Markov equivalence ambiguity.
3. **Confounder Protection:** If Stage 2 identifies latent confounding that cannot be disambiguated, RIFT safely abstains (FAR = 0.00%).
