# RIFT — Novelty Claims
**Phase 1 | Version 1.0 — After Full Literature Survey**

---

## Verdict Summary

| Claim | Status | Confidence | Key Condition |
|---|---|---|---|
| N1: Runtime Pearl-style intervention for distributed RCA | **SUPPORTED** | MEDIUM-HIGH | Must distinguish from Sieve (ops) and Sage (formal); ablation required |
| N2: Intervention adds information beyond observation | **PARTIALLY SUPPORTED** | MEDIUM | Theoretically grounded; empirical demonstration required |
| N3: Minimum intervention set selection is novel | **PARTIALLY SUPPORTED** | LOW-MEDIUM | Golovin & Krause cover the theory; RIFT's contribution is systems cost model |
| N4: Formal behavioral divergence definition is novel | **PARTIALLY SUPPORTED** | LOW | Only novel if causally indexed; otherwise covered by RV literature |
| N5: Full combination novel as system | **SUPPORTED** | HIGH | Closed-loop architecture is the most defensible framing |

---

## N1 — Runtime Pearl-Style Intervention for Distributed RCA

**CLAIM:** RIFT is the first system to execute Pearl's do-operator as a live operational mechanism against a running distributed microservice system for root-cause attribution.

**STATUS: SUPPORTED** *(conditional)*

**Evidence supporting the claim:**
- Phase 1 surveyed 27+ papers. No paper occupies the FORMAL-LIVE tier of causal depth for distributed software systems.
- Sage (ASPLOS 2021) uses SCMs but offline and without live intervention.
- Sieve (ICSE 2023) uses runtime injection but without SCM or do-calculus.
- KDD 2022 and Microsoft SCM papers use do-calculus but with historical/static models.
- Active DES Diagnosis performs live active probing but in control systems with automata models, not distributed software with SCMs.

**The gap is real:** No single paper combines {SCM + do-operator + live distributed system + runtime execution + RCA output}.

**Conditions that must remain true for this claim to hold:**
1. Phase 1 literature review must not have missed a directly equivalent paper (verify via Semantic Scholar search with exact string matches before submission).
2. RIFT's implementation must actually execute `do(X := x)` against a live system — not simulate it on historical data.
3. RIFT must maintain and update an SCM online — not use a pre-specified static graph.

**Closest prior art threats:** Sieve (T3), Sage (T1), MSFT SCM (T6)

**Remaining differentiation:** The *closed-loop* between SCM maintenance, intervention execution, and online model update is RIFT's irreducible contribution. Each prior paper has one or two of the three components but not all three.

---

## N2 — Intervention Provides Information Beyond Observational RCA

**CLAIM:** Executing do(X := x) against a live system provides causal signal that cannot be obtained from passive observational data alone, and this advantage is demonstrable in the distributed systems RCA context.

**STATUS: PARTIALLY SUPPORTED**

**Evidence supporting the theoretical premise:**
- Pearl's framework establishes this definitionally: P(Y | do(X)) ≠ P(Y | X) in the presence of confounders. This is the foundational justification.
- Observational causal discovery (PC algorithm, NOTEARS) is known to fail under unmeasured confounders — a realistic condition in distributed systems (shared infrastructure, noisy neighbors).
- The KDD 2022 survey paper on causal inference for AIOps explicitly documents that the field is correlational and calls for interventional approaches.

**What is NOT yet supported:**
- **Empirical demonstration** in the distributed systems context is absent. The theoretical claim is standard causal inference; RIFT must provide the experimental evidence that shows Sage-style observational methods fail on the benchmark and RIFT's interventional method succeeds.
- The gap must be demonstrated specifically on at least one fault type where confounding is present (e.g., a shared database causing correlated anomalies across multiple services).

**Required for full support:** EXP-009 (ablation: RIFT without intervention layer) + at least one scenario constructed to contain a genuine confounder. Without this, N2 is theory without evidence.

---

## N3 — Minimum Intervention Set Selection

**CLAIM:** RIFT introduces a novel algorithm for selecting the minimal set of do-calculus interventions required to confirm root cause attribution in distributed systems.

**STATUS: PARTIALLY SUPPORTED — weakened after Phase 1**

**What Phase 1 revealed:**
- **Golovin & Krause (2011)** provide the theoretical foundation for adaptive sequential test minimization (adaptive submodularity). This is the theory RIFT's algorithm would instantiate.
- **Eberhardt & Scheines (2007)** establish bounds on minimum interventions needed for causal structure identification.
- The *algorithmic* novelty of minimizing interventions is not new.

**What remains novel:**
The **microservice-specific cost model** that RIFT must bring to this theory:
- Intervention blast radius (how much does injecting a fault in X affect other services?)
- SLA guard constraints (which interventions are safe during business hours?)
- Rollback requirements (can the intervention be cleanly reversed?)
- Partial observability (traces may be sampled; not all effects are observable)
- Non-stationarity (system behavior changes during intervention windows)

None of Golovin & Krause, Eberhardt & Scheines, or any active diagnosis paper addresses these constraints jointly.

**Required repositioning:** N3 must be stated as: "We extend the adaptive submodularity framework with a systems-aware cost model for live microservice intervention safety." Not: "We introduce minimum intervention set selection."

---

## N4 — Formal Definition of Behavioral Divergence

**CLAIM:** RIFT provides the first formal, operationalizable definition of behavioral divergence in distributed systems grounded in structural causal models.

**STATUS: PARTIALLY SUPPORTED — requires careful scoping**

**What Phase 1 revealed:**
- Runtime verification (MTL, STL, LTL monitor automata) extensively formalizes behavioral deviation. These are well-established.
- "Steady-state hypothesis" in chaos engineering operationalizes a divergence check informally.
- SLO violation is the de facto production definition of behavioral divergence.

**What remains novel:**
The *causal indexing* of the divergence definition. RIFT's definition is not "behavior changed" but "behavior changed *because* component X's causal contribution changed." Formally:

> *Behavioral divergence at node Y attributable to component X is:*
> `TV(P(Y | trace_baseline), P(Y | do(X := x_nominal))) > τ`

This couples divergence detection with causal attribution in a single formal object. No runtime verification paper, SLO paper, or anomaly detection paper defines divergence this way. The causal indexing is the novel element.

**Required repositioning:** N4 must not claim novelty for detecting divergence. It must claim novelty for the *causally-indexed* divergence metric — one that is only non-zero when component X is causally responsible, not merely when behavior changes.

---

## N5 — Combination Novelty (Full System)

**CLAIM:** The closed-loop architecture combining (1) online SCM induction from distributed traces, (2) adaptive do-operator intervention execution, (3) counterfactual outcome observation, and (4) causal root cause localization is novel as a unified system.

**STATUS: SUPPORTED** *(highest confidence)*

**Evidence:**
- No prior paper closes all four loops simultaneously.
- Sage has (1) and (4) but not (2) or (3) — live execution.
- Sieve has (2) and partial (4) but not (1) SCM formalism or (3) counterfactual.
- KDD 2022 has (1) and partial (4) but not live (2) or real (3).
- Active DES has (2) and (4) but not (1) for distributed software or Pearl (3).
- The combination is the irreducible contribution.

**Important caveat from Agent 9:**
The composition threat is real: a reviewer could argue "Sage + chaos engineering = RIFT." RIFT must demonstrate that the closed-loop is **not** reducible to running Sage first and then adding chaos engineering — specifically because the causal model must be updated by intervention outcomes, which requires architectural integration that a naive composition does not provide.

**Required evidence:** Show that Sage + LitmusChaos (naive composition) fails on at least one benchmark scenario that RIFT's integrated architecture handles correctly, due to the online model update from intervention feedback.

---

## THE SINGLE STRONGEST NOVELTY STATEMENT

Based on the Phase 1 analysis across all 10 agents, the most defensible novelty statement is:

> **RIFT is the first system to operationalize Pearl's do-calculus as a runtime closed-loop mechanism in live distributed microservice systems: it learns a structural causal model from traces, selects minimal safe interventions via an SCM-guided adaptive strategy, executes those interventions against the running system, and updates the causal model from the observed counterfactual outcomes to produce intervention-confirmed root cause attribution.**

This statement is:
- **Differentiable from Sage** (Sage is offline; RIFT is live; Sage does not execute interventions)
- **Differentiable from Sieve** (Sieve has no SCM and no do-calculus; RIFT has both)
- **Differentiable from chaos engineering** (Chaos tests resilience; RIFT confirms causation)
- **Differentiable from active DES diagnosis** (DES is for control systems with automata; RIFT is for distributed software with SCMs)
- **Grounded in theory** (Pearl, Golovin & Krause, Eberhardt & Scheines cited as foundations)
- **Falsifiable** (a reviewer must find a paper that does all components simultaneously, not just some)

---

## WHAT MUST BE EMPIRICALLY PROVEN TO DEFEND THESE CLAIMS

| Claim | Required Experiment | Current Status |
|---|---|---|
| N1 | Outperform Sage and Sieve on root cause precision on benchmark | MISSING |
| N2 | Show confounded scenario where observational-only RCA fails and RIFT succeeds | MISSING |
| N3 | Show RIFT's cost-constrained intervention selection uses fewer interventions than random/exhaustive | MISSING |
| N4 | Show causally-indexed divergence metric reduces false attributions vs. SLO-based metric | MISSING |
| N5 | Show integrated closed-loop outperforms Sage + chaos engineering naive composition | MISSING |

All experiments are planned for Phases 9–10. No experiments can be run until the benchmark is frozen (Phase 7).

---

## REQUIRED CHANGES TO RESEARCH DESIGN FROM PHASE 1

1. **Add Sieve (ICSE 2023) as a mandatory baseline.** It was not in Phase 0's baseline list. It must be added.
2. **Reframe N3.** Do not claim novelty for the minimization objective. Claim novelty for the systems cost model.
3. **Reframe N4.** Do not claim novelty for "formal divergence definition." Claim novelty for the *causally-indexed* divergence metric.
4. **Add a confounder scenario to the benchmark.** At least one fault scenario must involve an unmeasured confounder to demonstrate N2.
5. **Add a Sage + chaos naive composition experiment.** This directly defends N5 against the composition attack.
6. **Cite Golovin & Krause and Eberhardt & Scheines as theoretical foundations** for N3 — do not present the minimization theory as novel.
