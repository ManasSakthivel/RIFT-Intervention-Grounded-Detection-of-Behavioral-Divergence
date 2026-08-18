# RIFT — Prior Art Threat Analysis
**Phase 1 | Version 1.0**

---

## Preface

This document catalogues every prior work identified in Phase 1 that poses a credible threat to RIFT's novelty claims. Threats are classified by severity and resolution strategy.

---

## Threat Classification

- **FATAL** — prior work already does what RIFT claims; claim must be abandoned or completely reframed
- **HIGH** — prior work substantially overlaps; RIFT must precisely differentiate or narrow the claim
- **MEDIUM** — prior work partially overlaps; clear differentiation exists but must be explicitly argued
- **LOW** — prior work is related but clearly different; mention and dismiss in related work

---

## THREAT T1 — Sage (Gan et al., ASPLOS 2021)

**Threat Level: HIGH**

**What Sage does:**
Sage builds a Bayesian Network (SCM-like) over distributed microservice traces. It uses probabilistic inference to attribute latency anomalies to a root-cause service. It performs graph surgery (removing incoming edges) to simulate interventional reasoning.

**Why it threatens RIFT:**
- Uses structural causal models in microservices — this is the closest existing system to RIFT's formal layer
- Performs graph surgery (which is what do-calculus does algebraically to a DAG)
- A reviewer could argue: "Sage already does do-calculus; RIFT adds nothing"

**Why the threat does NOT succeed (RIFT's defense):**
1. **Offline vs. live:** Sage builds its Bayesian network from historical labeled fault-injection training data. It cannot adapt its causal model during a live incident. RIFT constructs and updates its SCM online from live traces.
2. **Simulation vs. execution:** Sage's "graph surgery" is a mathematical operation on the model — it does not actually execute `do(X := x)` in the running system. RIFT physically executes the intervention and observes the counterfactual.
3. **Supervised vs. unsupervised:** Sage requires labeled fault data to train its BN. RIFT does not require pre-labeling of fault types.
4. **Static graph vs. adaptive graph:** Sage's causal graph is static. RIFT's is updated by intervention outcomes (closed-loop).

**Required evidence in paper:** Experimental comparison against Sage on same benchmark. Show at least one scenario where Sage fails (confounded by unknown fault topology) and RIFT succeeds (live intervention breaks the confound).

---

## THREAT T2 — KDD 2022 Causal RCA (Li et al.)

**Threat Level: HIGH**

**What it does:**
Constructs an SCM from metric time-series using PC-algorithm. Models historical deployment/restart events as do-like exogenous interventions within the SCM. Uses the adjustment formula to estimate causal effects.

**Why it threatens RIFT:**
- Explicitly uses SCM formalism and do-notation
- Explicitly models "interventions" (though logged, not executed)
- Applied to online service systems (similar operational context)

**Why the threat does NOT succeed:**
1. **Observed vs. executed:** Interventions in this paper are observed from historical deployment logs — they are things that happened and were recorded. RIFT executes new interventions against the live system to test specific causal hypotheses.
2. **Historical graph:** The SCM is built from historical data. It cannot reason about novel fault topologies.
3. **No counterfactual outcome measurement:** The paper estimates causal effects via adjustment formula, not by observing a real counterfactual.

**Required evidence:** Note this paper explicitly in related work. Show that RIFT's intervention execution provides ground-truth counterfactuals that the adjustment formula cannot produce when causal assumptions are violated.

---

## THREAT T3 — Sieve (ICSE 2023)

**Threat Level: HIGH**

**What it does:**
Builds a causal dependency graph from distributed traces. Selects targeted fault injections at runtime to discriminate between candidate root causes. Uses injection outcomes to prune the hypothesis space. Adaptive — next injection is chosen based on prior outcomes.

**Why it threatens RIFT:**
- Runtime injection in microservices ✓
- Adaptive intervention selection based on prior outcomes ✓
- Graph-guided injection selection ✓
- Applied to root cause analysis ✓

This is **operationally the most similar paper to RIFT** in the systems/SE literature.

**Why the threat does NOT succeed (critical differences):**
1. **No SCM formalism:** Sieve's "causal graph" is a structural dependency graph — a call graph + correlation edges. It does not define structural equations, noise terms, or identifiability conditions.
2. **No do-calculus:** Sieve does not evaluate `P(Y | do(X := x))`. Its hypothesis pruning is based on outcome matching, not interventional distribution estimation.
3. **No confounder handling:** Because Sieve has no formal SCM, it cannot detect or handle unmeasured confounders. RIFT's identifiability check explicitly flags cases where confounders would invalidate attribution.
4. **No counterfactual:** Sieve observes "did the injection cause an anomaly?" — not "what would Y have been if X had been nominal?"

**Required evidence:** Must compare directly against Sieve. Must show on benchmark that in the presence of confounders, Sieve misattributes and RIFT correctly attributes due to the causal formalism.

**NOTE:** This is the most important comparison in the paper. If RIFT cannot outperform Sieve, the formal causal layer claim (N1) loses its empirical support.

---

## THREAT T4 — Active Fault Diagnosis / DES (Lafortune group, IEEE TAC 2003–2015)

**Threat Level: HIGH (conceptual)**

**What it does:**
Computes sequences of input stimuli (probes) to inject into a live system, selected to maximally disambiguate between fault hypotheses. Formally optimal under observability constraints. Domain: discrete-event systems and cyber-physical systems.

**Why it threatens RIFT:**
- Formal active probing = intervention ✓
- Adaptive selection of probes (minimizes expected probes to diagnosis) ✓
- Live system ✓
- Optimal information gain ✓
- The conceptual model is isomorphic to RIFT's intervention design problem

**Why the threat does NOT succeed:**
1. **Domain:** CPS/control systems, not distributed software systems. The system model is a finite-state automaton, not a microservice topology.
2. **No Pearl SCM:** The model is automata-theoretic (DES), not structural causal. No noise terms, no confounders, no identifiability.
3. **No counterfactual:** DES active diagnosis identifies the current fault mode — it does not reason about what *would have* happened under different conditions.
4. **Closed fault space:** Classic DES diagnosis assumes a finite, enumerable fault set known in advance. RIFT handles open-world, emergent fault topologies.

**Required action:** Acknowledge the conceptual similarity explicitly in the paper. Frame RIFT as extending active fault diagnosis to the distributed software domain with Pearl causal semantics.

---

## THREAT T5 — Adaptive Submodularity (Golovin & Krause, JAIR 2011)

**Threat Level: HIGH (for N3 specifically)**

**What it does:**
Provides the theoretical framework for adaptive sequential decision-making under uncertainty, formally proving that greedy adaptive policies achieve near-optimal expected cost for submodular objective functions. Directly covers the minimum-test-set problem.

**Why it threatens RIFT:**
- RIFT's minimum intervention set selection is formally an instance of adaptive sequential testing
- The optimality guarantees RIFT needs for this component already exist in this paper
- A reviewer could say: "RIFT's intervention selection is just Golovin & Krause instantiated on a causal graph"

**Why the threat does NOT succeed for N3:**
1. **Golovin & Krause is a theoretical framework**, not a systems algorithm. It does not account for: intervention blast radius, rollback requirements, SLA constraints, partial observability during live execution, or the coupling between intervention cost and causal graph uncertainty.
2. **The systems constraints are the contribution.** RIFT's novelty for N3 is the *microservice-specific cost model* that G&K does not provide.

**Required action:** Cite Golovin & Krause as the theoretical foundation for RIFT's intervention selection algorithm. Show that RIFT's cost model extends G&K with systems-specific constraints. Do not claim G&K's result is novel — claim the *instantiation and extension* is novel.

---

## THREAT T6 — Microsoft SCM Workshop Paper (SREcon 2021–22)

**Threat Level: HIGH**

**What it does:**
Uses hand-specified SCMs for a finite catalog of known fault types. Applies do-calculus and counterfactual queries to answer "would the SLO have been violated if X were normal?" Applied to real production cloud infrastructure incidents.

**Why it threatens RIFT:**
- Uses do-calculus and counterfactual queries ✓
- Applied to real production systems ✓
- Formal SCM ✓

**Why the threat does NOT succeed:**
1. **Hand-specified SCMs:** Every structural equation is manually written by SREs for each known fault type. No learning. Cannot generalize to novel faults.
2. **Infrastructure layer:** VM/host-level, not microservice-level. Static topology.
3. **No runtime intervention:** The do-queries are answered by evaluating the pre-specified SCM — no intervention is executed against the live system.
4. **Closed fault catalog:** Cannot diagnose faults outside the pre-enumerated set.

**Required action:** Verify publication details. If confirmed, cite as the closest related work using do-calculus in production systems, and position RIFT's generality (learned, adaptive SCM, open-world faults) as the advancement.

---

## THREAT T7 — LDFI (Lineage-Driven Fault Injection, Alvaro et al., SIGMOD 2015)

**Threat Level: HIGH (structural reasoning)**

**What it does:**
Works backward from a correctness proof (provenance/lineage of a correct execution) to identify the specific combinations of faults that would cause incorrect behavior. Injects those faults to test resilience.

**Why it threatens RIFT:**
- Backward causal reasoning from observed outcome to fault hypothesis ✓
- Fault injection driven by causal reasoning ✓
- Distributed systems ✓

**Why the threat does NOT succeed:**
1. **Goal is pre-deployment testing, not runtime RCA.** LDFI asks "what faults would break this program?" before deployment. RIFT asks "what caused this failure?" during or after an incident.
2. **No SCM / Pearl semantics.** Lineage is data provenance — a different causal model.
3. **No online operation.** LDFI is a static analysis / testing tool.

**Required action:** Distinguish clearly in related work: LDFI is fault *injection for testing*; RIFT is fault *attribution for diagnosis*. These are opposite directions.

---

## THREAT T8 — RCD (Ikram et al., ICSE 2022)

**Threat Level: MEDIUM**

**What it does:**
Uses the PC algorithm with structural constraints from call graph topology. Runs repeatedly over sliding time windows to capture temporal causal evolution. Root cause ranking via graph centrality.

**Why it threatens RIFT:**
- Published in ICSE (same target venue) ✓
- Uses causal discovery (PC) ✓
- Handles temporal evolution ✓

**Why the threat does NOT succeed:**
- Purely observational — no intervention
- Cannot compute interventional distributions
- Relies on faithfulness and causal sufficiency assumptions RIFT explicitly tests

**Required action:** Standard related work comparison. This is a medium-difficulty baseline.

---

## CONSOLIDATED THREAT TABLE

| Threat | Paper | Level | N1 | N2 | N3 | N4 | N5 | Resolution |
|---|---|---|---|---|---|---|---|---|
| T1 | Sage | HIGH | ✓ partial | ✓ partial | ✗ | ✗ | ✓ partial | Live vs. offline; experimental comparison required |
| T2 | KDD 2022 Causal RCA | HIGH | ✓ partial | ✓ partial | ✗ | ✗ | ✓ partial | Observed vs. executed interventions |
| T3 | Sieve ICSE 2023 | HIGH | ✓ strong | ✗ | ✓ partial | ✗ | ✓ strong | SCM formalism gap; confounder handling; ablation required |
| T4 | Active DES Diagnosis | HIGH | ✓ conceptual | ✗ | ✓ partial | ✗ | ✗ | Domain gap; SCM vs. automata |
| T5 | Adaptive Submodularity | HIGH | ✗ | ✗ | ✓ **strong** | ✗ | ✗ | Theory vs. systems; extend with cost model |
| T6 | MSFT SCM Workshop | HIGH | ✓ partial | ✓ partial | ✗ | ✗ | ✓ partial | Static/hand-specified vs. learned/dynamic |
| T7 | LDFI | HIGH | ✓ partial | ✗ | ✗ | ✗ | ✓ partial | Testing vs. diagnosis direction |
| T8 | RCD ICSE 2022 | MEDIUM | ✗ | ✗ | ✗ | ✗ | ✗ | Observational only; easy differentiation |

---

## CRITICAL FINDING

**The N3 threat (Golovin & Krause) is the most dangerous individual threat.** RIFT cannot claim its intervention selection algorithm is novel without acknowledging this foundational work and demonstrating what RIFT adds beyond it. This must be addressed in the algorithm design phase (Phase 6).

**The Sieve threat is the most dangerous operational threat.** If RIFT cannot outperform Sieve on the benchmark, the case for adding Pearl SCM formalism is empirically undefended. The Sieve comparison is mandatory and must be won on the confounder-handling axis specifically.
