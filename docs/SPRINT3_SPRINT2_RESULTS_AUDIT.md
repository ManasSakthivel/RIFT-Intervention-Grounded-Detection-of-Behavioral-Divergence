# RIFT Sprint 3 — Audit of Sprint 2 Results & Oracle Discrepancy

**Audit Date:** 2026-11-02  
**Lead Auditor:** Scientific Red-Team & Verification Lead  
**Authority:** Sprint 3 Phase 1 Forensic Audit  

---

## 1. Dissection of the Oracle-PAG vs. Learned RIFT Discrepancy

In Sprint 2, a critical apparent paradox was identified:
- **`RIFT-FULL` (Learned FCI):** Reported 88.00% Raw P@1 on Dev Split ($n=50$).
- **`RIFT-FULL-ORACLE` (Oracle PAG):** Reported 26.00% Raw P@1 on Dev Split ($n=50$).

### Root Cause Analysis:
1. **Ground Truth Confounder Representation:**  
   In `build_oracle_pag()`, ground-truth confounders are explicitly encoded as `BIDIRECTED` edges ($X \leftrightarrow Y$) between affected services.
2. **Identifiability Engine Trigger:**  
   In `identify_query()`, when a `BIDIRECTED` edge exists along a causal path, the causal effect $P(Y | do(X))$ is formally non-identifiable. Consequently, `RIFT-FULL-ORACLE` safely **abstained on all 24 confounded scenarios and 13 leaf scenarios** (74.00% abstention rate). On the 13 identifiable scenarios where it emitted a prediction, its **Conditional Precision@1 was 100.00% (13/13 correct, 0% FAR)**.
3. **Learned FCI Behavior on Short Windows:**  
   In contrast, constraint-based FCI on short windows ($N=18$) produced `UNDIRECTED` edges ($X \circ\!\!-\!\!\circ Y$) without detecting bidirected arcs. Under semi-directed reachability, RIFT attempted attribution on these unconfounded-appearing graphs, achieving 88.00% raw accuracy but incurring a 6.38% False Attribution Rate.
4. **Conclusion:**  
   `RIFT-FULL-ORACLE` is an upper bound on **safe conditional precision under true structural identifiability**, not an upper bound on unconstrained raw prediction volume.

---

## 2. Metric Definitions & Disambiguation

```
┌─────────────────────────────────┬────────────────────────────────────────────────────────────┐
│ Metric                          │ Exact Mathematical Definition                              │
├─────────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Raw Precision@1 (Raw Accuracy)  │ Correct Predictions / Total Scenarios                      │
│ Conditional Precision@1         │ Correct Predictions / (Total Scenarios - Abstentions)      │
│ Diagnostic Coverage             │ (Total Scenarios - Abstentions) / Total Scenarios          │
│ False Attribution Rate (FAR)    │ Incorrect Attributions / Total Scenarios                   │
│ Selective Risk                  │ Incorrect Attributions / Total Predictions Emitted         │
└─────────────────────────────────┴────────────────────────────────────────────────────────────┘
```
