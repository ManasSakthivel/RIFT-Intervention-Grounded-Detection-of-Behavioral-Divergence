# RIFT Sprint 3 — Statistical Analysis & Robustness Report

**Lead Statistician:** Principal Statistician  
**Date:** 2026-11-02  
**Authority:** Statistical Rigor and Multi-Family Hypothesis Testing  

---

## 1. Statistical Hypothesis Tests Across Adversarial Families

```
┌─────────────────────────────────┬────────────┬─────────────┬──────────────┬───────────────────┐
│ Hypothesis                      │ Raw p      │ α_corr      │ Cliff's δ    │ Conclusion        │
├─────────────────────────────────┼────────────┼─────────────┼──────────────┼───────────────────┤
│ H1: RIFT-FULL > RIFT-OBS P@1    │ < 0.0001   │ 0.0167      │ +0.880       │ CONFIRMED (p < α) │
│ H4: MSIS Cost < Random Cost     │ < 0.0001   │ 0.0125      │ +1.000       │ CONFIRMED (p < α) │
│ Adv-1: Earliest Anomaly Fails   │ < 0.0001   │ 0.0250      │ +1.000       │ CONFIRMED (0% P@1)│
│        on Inverted Onset        │            │             │              │                   │
│ Adv-2: Highest Anomaly Fails    │ < 0.0001   │ 0.0250      │ +1.000       │ CONFIRMED (0% P@1)│
│        on Retry Amplification   │            │             │              │                   │
└─────────────────────────────────┴────────────┴─────────────┴──────────────┴───────────────────┘
```

---

## 2. Statistical Interpretation

1. **Failure of Heuristic Onset:** Inverted onset significantly defeats earliest-anomaly heuristics ($p < 0.0001$), proving that temporal precedence in telemetry is not invariant under asynchronous buffering.
2. **Failure of Amplitude Heuristics:** Retry storms significantly defeat highest-anomaly heuristics ($p < 0.0001$), confirming that downstream retry amplification obscures root-cause signal magnitude.
3. **RIFT Resilience:** RIFT's active intervention and causal reachability isolate multi-hop and multi-cause faults where static single-step heuristics fail.
