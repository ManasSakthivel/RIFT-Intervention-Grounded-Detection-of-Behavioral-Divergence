# RIFT — Novelty Positioning
**Phase 1 | Version 2.0 — Updated after full literature survey**

---

## Status Change from Phase 0

Phase 0 marked all novelty claims `[UNVERIFIED]`.

Phase 1 has now surveyed 27+ relevant papers across 10 independent research angles.

**Status update:** The core novelty claim (N1/N5) is now **SUPPORTED** at MEDIUM-HIGH confidence. Several sub-claims have been narrowed or repositioned. The research direction is confirmed viable.

---

## 1. The Causal Depth Landscape (Empirically Established)

Phase 1 has confirmed that the distributed systems RCA field stratifies into four tiers, with the top tier unoccupied:

```
TIER 4 — FORMAL-LIVE (SCM + do(·) against live system)
         ┌─────────────────────────────────────────┐
         │         *** VACANT ***                  │
         │    RIFT's claimed position              │
         └─────────────────────────────────────────┘

TIER 3 — FORMAL-SIMULATED (SCM + do(·) on historical data)
         KDD 2022 Causal RCA (Li et al.)
         Microsoft SCM Workshop paper
         DoWhy (library, offline)

TIER 2 — GRAPHICAL (PC algorithm / BN / Granger — observational)
         CloudRanger, RCD (ICSE 2022), Sage (ASPLOS 2021),
         CIRCA, CausalRCA, CauseInfer, Microscope

TIER 1 — INFORMAL (correlation / graph traversal)
         MicroRCA, AutoMAP, BARO, Sieve*, Gremlin
         (* Sieve injects at runtime but has no causal model)
```

**The gap RIFT fills is real and empirically confirmed.** No paper in the surveyed corpus occupies Tier 4 for distributed software systems.

---

## 2. The Three-Axis Differentiation

RIFT's position can be described precisely on three axes where it differs from every existing system:

| Axis | Existing Best | RIFT |
|---|---|---|
| **Causal Formalism** | Graphical/observational (Sage, CIRCA) | Structural Causal Model + Pearl do-calculus + identifiability checking |
| **Intervention Mode** | Either simulated (KDD 2022) or without causal model (Sieve) | Live `do(X:=x)` executed against running system, guided by SCM |
| **Feedback Loop** | One-shot: graph learned once, used for attribution | Closed-loop: intervention outcomes update the SCM online |

No prior system scores at RIFT's position on all three axes simultaneously.

---

## 3. Positioning Against Closest Competitors

### vs. Sage (ASPLOS 2021) — "Closest in formalism"

> Sage builds a Bayesian network SCM offline from labeled historical data and uses it for observational attribution. Sage does not execute interventions. Sage's model is static.

**RIFT advances beyond Sage by:** (1) online SCM induction from live traces without pre-labeled fault data, (2) execution of `do(X := x)` against the live system — not simulation on historical data, (3) closed-loop update of the SCM from intervention outcomes.

### vs. Sieve (ICSE 2023) — "Closest in operation"

> Sieve performs adaptive runtime fault injection in microservices and uses injection outcomes to prune root cause hypotheses. Sieve uses a structural dependency graph.

**RIFT advances beyond Sieve by:** (1) grounding the causal graph in Pearl SCM with structural equations and identifiability conditions, (2) evaluating interventional distributions `P(Y | do(X))` rather than binary outcome matching, (3) handling unmeasured confounders — which Sieve cannot do because it has no formal causal model.

### vs. KDD 2022 Causal RCA — "Closest in causal depth"

> Uses SCM and do-notation to model historical deployment events as interventions. Applies adjustment formula to estimate causal effects.

**RIFT advances beyond KDD 2022 by:** (1) executing real interventions against the live system rather than estimating effects from logged historical events, (2) adapting the SCM dynamically rather than using a static historically-learned graph, (3) handling novel fault topologies not present in historical data.

### vs. Active DES Diagnosis — "Closest in mechanism"

> Performs optimal adaptive active probing on live systems, selecting probes to maximally disambiguate fault hypotheses. Formally optimal. Domain: CPS/control systems.

**RIFT advances beyond Active DES by:** (1) operating on distributed microservice software (not CPS), (2) using Pearl SCM rather than automata-theoretic models, (3) handling open-world fault topologies rather than finite pre-enumerated fault modes.

---

## 4. The Definitive Novelty Statement

*(Updated from Phase 0 draft — this is the working abstract framing)*

> RIFT is the first system to operationalize Pearl's structural causal model framework as a runtime closed-loop mechanism in live distributed microservice systems. RIFT learns a causal graph from distributed traces, selects minimal safe interventions using an SCM-guided adaptive cost model, executes `do(X := x)` against the running system, observes the counterfactual outcome, and uses Pearl's adjustment formula to produce intervention-confirmed root cause attribution with formal causal guarantees. Unlike observational causal RCA systems (Sage, CIRCA, CloudRanger), RIFT does not require the causal graph to be pre-specified or confound-free. Unlike runtime intervention systems (Sieve, chaos engineering), RIFT's interventions are formally modeled as do-operators on an SCM, enabling identifiability checking, confounder detection, and counterfactual verification.

**Note:** All bracketed values and performance claims are still MISSING. This framing is ready for Phase 14 paper writing once experiments are complete.

---

## 5. What Is NOT Novel (Honest Accounting)

| Component | What Exists | Status |
|---|---|---|
| Distributed trace collection | Dapper, OpenTelemetry, Jaeger | Reuse existing infrastructure |
| Causal graph learning (PC algo) | Spirtes et al. (2000), DoWhy | Reuse existing algorithm |
| do-calculus theory | Pearl (2000) | Apply foundational theory |
| Fault injection infrastructure | LitmusChaos, Chaos Mesh | Reuse existing tools |
| Behavioral anomaly detection | Prometheus, Isolation Forest | Use as baseline/detection trigger |
| Intervention set theory (minimization) | Golovin & Krause (2011) | Cite as theoretical foundation; extend |

RIFT does not claim any of these components as novel. RIFT claims novelty in their *integration into a closed-loop runtime causal RCA system* and in the *systems-specific contributions* (online SCM update, blast-radius cost model, identifiability-gated intervention selection).

---

## 6. Risk Profile (Updated from Phase 0)

| Risk | Phase 0 Assessment | Phase 1 Update |
|---|---|---|
| R1: Causal framing is cosmetic | HIGH | **MEDIUM** — Phase 1 confirms genuine gap; but Sieve comparison is now critical |
| R2: Divergence not formally defined | HIGH | **MEDIUM** — causally-indexed definition is novel; standard deviation detection is not |
| R3: Toy benchmark | HIGH | **UNCHANGED** — benchmark design still required |
| R4: Causal assumptions not stated | HIGH | **UNCHANGED** — must be addressed in Phase 2 |
| R5: Missing baselines | MEDIUM-HIGH | **NOW ELEVATED** — Sieve must be added as mandatory baseline |
| R_NEW: Golovin & Krause kills N3 | Not identified | **HIGH** — N3 repositioned to systems cost model, not algorithm theory |
| R_NEW: Sage+Chaos composition | Not identified | **HIGH** — ablation experiment required |
