# RIFT Sprint 2 — Structural Prior Design & Comparison

**Lead Architect:** Principal Causal Discovery Scientist  
**Date:** 2026-11-02  
**Authority:** Methodological Prior Integration Specification  

---

## 1. Comparison of Structural Prior Approaches

```
┌─────────────────────────────────┬────────────────────────────────────────────┬──────────────────────────────────────┐
│ Approach                        │ Implementation Strategy                    │ Scientific Merits & Trade-offs       │
├─────────────────────────────────┼────────────────────────────────────────────┼──────────────────────────────────────┤
│ Approach A: Observational FCI   │ Control Condition: Pure constraint-based   │ Sound but uninformative on small N;  │
│ (Unconstrained Baseline)        │ FCI over observational metric time-series. │ produces unoriented circle marks.    │
├─────────────────────────────────┼────────────────────────────────────────────┼──────────────────────────────────────┤
│ Approach B: Call-Topology       │ BackgroundKnowledge forbidding direct edges│ Prunes spurious correlations between │
│ Adjacency Constraints           │ between non-communicating service pairs.   │ non-adjacent services; preserves     │
│                                 │                                            │ directional uncertainty.             │
├─────────────────────────────────┼────────────────────────────────────────────┼──────────────────────────────────────┤
│ Approach C: Uncertainty-        │ Adjacency constraints + Semi-directed path │ Combines sound topological pruning   │
│ Preserving Active Interventional│ exploration in EBD (R3) + Active CID       │ with active interventional do(X)     │
│ Divergence (Selected)           │ Wasserstein-1 disambiguation.              │ disambiguation of orientation ties.  │
└─────────────────────────────────┴────────────────────────────────────────────┴──────────────────────────────────────┘
```

---

## 2. In-Depth Analysis of Approach C (Selected Method)

### 2.1 Mathematical Formulation
1. **Adjacency Pruning via Call Topology $\mathcal{T}$:**  
   Let $\mathcal{T} = (V, E_{\text{call}})$ be the observed service call graph. If $(u, v) \notin E_{\text{call}}$ and $(v, u) \notin E_{\text{call}}$, we enforce the background constraint:
   $$\text{Forbidden}(u, v) = \text{True}$$
   This prevents FCI from evaluating or orienting direct unmediated edges between disjoint architectural domains.
2. **Semi-Directed Path Reachability ($\mathcal{P}_{\text{semi}}$):**  
   In the learned PAG $\mathcal{P}$, a candidate path $u \rightsquigarrow v$ is admissible if every edge along the path is a valid semi-directed step:
   $$\text{Step}(X, Y) \in \{\text{DIRECTED } (X \rightarrow Y), \text{PARTIALLY\_DIRECTED } (X \circ\!\!\rightarrow Y), \text{UNDIRECTED } (X \circ\!\!-\!\!\circ Y)\}$$
   Edges with $X \leftarrow Y$ or $X \leftrightarrow Y$ (bidirected confounders) are strictly excluded from downstream causal reachability.
3. **Active Interventional Disambiguation:**  
   When an edge $X \circ\!\!-\!\!\circ Y$ remains observationally unoriented, RIFT dispatches a controlled network intervention $do(X = \text{perturb})$:
   $$\text{CID}(Y | do(X)) = W_1\left( P(Y | do(X)), P(Y | \text{baseline}) \right)$$
   If $\text{CID}(Y | do(X)) > \theta_{\text{CID}}$ ($p < 0.01$), the causal direction $X \rightarrow Y$ is experimentally confirmed.

---

## 3. Assumptions and Failure Modes

- **Assumption A1 (Communication Completeness):** The distributed tracing sampler captures all active RPC communication edges during normal profiling.
- **Assumption A2 (Intervention Invariance):** Perturbing $X$ does not alter downstream structural equations $f_Y$.
- **Failure Mode (Leaf-Node Sinks):** If $X$ is a terminal leaf node (callee with out-degree 0), perturbing $X$ produces no downstream effects. Handled via Criterion R3-leaf upstream caller degradation checks.
