# RIFT Sprint 2 — Graph Semantics & Topological Representation

**Authority:** Causal Graph Theory & Microservice Observability Semantics  
**Date:** 2026-11-02  

---

## 1. Taxonomy of Graph Representations in Distributed Systems

In root-cause analysis (RCA), four distinct graph representations must be rigorously separated:

```
┌─────────────────────────────────┬──────────────────────────────────┬────────────────────────────────────────────────────────┐
│ Graph Object                    │ Edge Types                       │ Semantic Meaning & Interpretation                      │
├─────────────────────────────────┼──────────────────────────────────┼────────────────────────────────────────────────────────┤
│ 1. Service Call Graph (SCG)     │ Directed: A → B                  │ Telemetry / Tracing: Service A sends RPCs to Service B. │
│                                 │                                  │ (Communication topology, NOT degradation causality).   │
├─────────────────────────────────┼──────────────────────────────────┼────────────────────────────────────────────────────────┤
│ 2. Structural Causal Model (DAG)│ Directed: X → Y                  │ True Data-Generating Process: Invariant mechanism      │
│                                 │                                  │ Y = f(X, U_Y). Perturbing X causally alters Y.        │
├─────────────────────────────────┼──────────────────────────────────┼────────────────────────────────────────────────────────┤
│ 3. Completed Partially Directed │ Directed: X → Y                  │ Observational Markov Equivalence Class under Causal    │
│    Acyclic Graph (CPDAG)        │ Undirected: X — Y                │ Sufficiency (no latent confounders).                   │
├─────────────────────────────────┼──────────────────────────────────┼────────────────────────────────────────────────────────┤
│ 4. Partial Ancestral Graph (PAG)│ Tail: —, Arrow: >, Circle: o     │ Observational Markov Equivalence Class allowing latent │
│                                 │ (→, ↔, o→, o-o)                  │ confounders (↔) and unshielded orientation ambiguity.  │
└─────────────────────────────────┴──────────────────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 2. PAG Endpoint Mark Semantics (Zhang, 2008)

For any edge between vertices $X$ and $Y$ in a PAG $\mathcal{P}$:
1. **Tail Mark ($—$ at $X$):** $X$ is an ancestor of $Y$ in every DAG in the equivalence class $[\mathcal{G}]$.
2. **Arrowhead Mark ($>$ at $Y$):** $Y$ is *not* an ancestor of $X$ in any DAG in $[\mathcal{G}]$.
3. **Circle Mark ($\circ$ at $X$):** The ancestral relationship of $X$ with respect to $Y$ is uncertain from observational conditional independence tests alone (there exists at least one DAG where $X$ is an ancestor, and at least one DAG where $X$ is not an ancestor, or where a latent confounder is present).

### Standard PAG Edge Types in RIFT:
- **$X \rightarrow Y$ (Directed):** $X$ is an ancestor of $Y$; $Y$ is not an ancestor of $X$.
- **$X \leftrightarrow Y$ (Bidirected):** Latent common cause $L \rightarrow X, L \rightarrow Y$; neither is an ancestor of the other.
- **$X \circ\!\!\rightarrow Y$ (Partially Directed):** $Y$ is not an ancestor of $X$; $X$ may be an ancestor of $Y$ or confounded.
- **$X \circ\!\!-\!\!\circ Y$ (Undirected):** Both ancestral directions are observationally admissible.

---

## 3. What Telemetry vs. Distributed Tracing Provides

1. **Continuous Telemetry (Metrics):**  
   Provides continuous metric time-series $X_t$ (latency, error rate, CPU utilization). Yields statistical correlations and conditional independence tests (e.g., Fisher's Z test $Z(X, Y | Z)$).
2. **Distributed Tracing (Spans / Call Graph):**  
   Provides invocation topology (who calls whom).
   - **Sound Adjacency Constraint:** If Service A and Service B have no direct RPC communication path in the call graph across all traces, they cannot have a direct unmediated causal interaction. This allows *forbidding direct causal edges* between non-communicating services.
   - **Crucial Negative Invariant:** A call $A \rightarrow B$ does **not** imply that degradation propagates $A \rightarrow B$. If $B$ slows down, $A$'s threads block waiting for $B$'s response, causing degradation to propagate $B \rightarrow A$ (upstream degradation cascade). Therefore, call edges cannot be blindly converted into causal degradation edges.
