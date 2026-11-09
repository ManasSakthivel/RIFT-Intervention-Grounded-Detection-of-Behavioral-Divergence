# RIFT Sprint 3.1 — Oracle Graph Validity & Upper-Bound Audit

**Audit Date:** 2026-11-02  
**Lead Auditor:** Causal Graph & Oracle Validity Auditor  
**Authority:** Task 3 Oracle Discrepancy Dissection  

---

## 1. Oracle Graph Information & Architecture

1. **Ground-Truth Input:** `RIFT-FULL-ORACLE` constructs its Partial Ancestral Graph directly from the scenario's ground-truth causal path and ground-truth confounder definitions:
   - Directed edges: $u \rightarrow v \quad \forall (u, v) \in \text{causal\_path}$.
   - Bidirected edges: $u \leftrightarrow v \quad \forall (u, v) \text{ sharing latent confounder}$.
2. **Execution Equality:** Operates over identical metric time-series, incident windows, intervention budgets ($T_{\text{budget}} \le 600\text{s}$), and identifiability rules (`identify_query()`).
3. **Abstention Semantics:** When `identify_query()` detects a bidirected edge along the path to the observed symptom, it formally returns `IdentifiabilityStatus.NOT_IDENTIFIABLE`.

---

## 2. Why Aggregate Raw Accuracy Matched (14/30 = 46.7%)

The identical aggregate score (14/30) between `RIFT-FULL-ORACLE` and `RIFT-FULL` on the adversarial cohort is a mathematical coincidence of compensating failure family behaviors:

```
┌─────────────────────────────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬───────────┐
│ Method                          │ A:Invert │ B:Retry  │ C:Conf   │ D:Multi  │ E:Noise  │ F:Deep   │ Total     │
├─────────────────────────────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼───────────┤
│ RIFT-FULL (Learned FCI)         │ 0 / 5    │ 0 / 5    │ 3 / 5    │ 5 / 5    │ 1 / 5    │ 5 / 5    │ 14 / 30   │
│ RIFT-FULL-ORACLE (Oracle PAG)   │ 0 / 5    │ 2 / 5    │ 0 / 5    │ 5 / 5    │ 2 / 5    │ 5 / 5    │ 14 / 30   │
└─────────────────────────────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴───────────┘
```

### Compensating Explanations:
- **Family B (Client Retry Storm):** `RIFT-FULL-ORACLE` achieves **2/5 (40%)** vs. **0/5 (0%)** for Learned FCI because its true directed edge `payment -> checkout` allows it to recognize `payment` as the upstream ancestor despite `checkout`'s larger retry amplitude.
- **Family C (Shared Confounding):** `RIFT-FULL-ORACLE` achieves **0/5 raw attribution** because it possesses the ground-truth bidirected arc `recommendation <-> product_catalog`, correctly triggering **100% sound abstention (5/5 abstained)**. Learned FCI missed the latent confounder arc and emitted 3 false attributions.
- **Family E (Noisy Telemetry):** `RIFT-FULL-ORACLE` achieves **2/5** vs. **1/5** for Learned FCI.

---

## 3. Formal Scientific Interpretation

`RIFT-FULL-ORACLE` is **strictly an upper bound on safe identifiability-conditioned precision** under perfect structural knowledge. It proves that when confounding is known, RIFT safely refuses to emit false attributions.
