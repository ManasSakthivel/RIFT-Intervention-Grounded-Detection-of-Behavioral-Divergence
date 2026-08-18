# RIFT — Related Work Matrix
**Phase 1 | Version 2.0 — Updated after full literature survey**

---

## Confidence Legend
- **HIGH** — foundational/well-known; verifiable
- **MEDIUM** — likely exists; details may need independent verification
- **LOW** — uncertain; do not cite without verification

## Causal Depth Legend
- **INFORMAL** — "causal" used loosely; correlation or graph traversal only
- **GRAPHICAL** — directed DAGs, Bayesian nets, PC algorithm; conditional independence but no interventional distribution
- **FORMAL-SIM** — SCM/do-calculus used, but intervention is *simulated* on historical data, not executed at runtime
- **FORMAL-LIVE** — SCM + do-operator executed against a *live* running system ← **this is RIFT's claimed position**

---

## Master Novelty Matrix

| Work | Venue/Yr | Distributed | Causal Model | Causal Depth | Uses do(·) | Runtime Intervention (Live) | Counterfactual | RCA Output | RIFT Threat | RIFT Difference |
|---|---|---|---|---|---|---|---|---|---|---|
| **MicroRCA** (Li et al.) | NOMS 2020 | ✓ | Graph (call graph + PageRank) | INFORMAL | ✗ | ✗ | ✗ | ✓ | MEDIUM | RIFT: interventional; MicroRCA: correlational random walk |
| **Sage** (Gan et al.) | ASPLOS 2021 | ✓ | Bayesian Net (SCM-like) | GRAPHICAL | ✗ | ✗ | ✗ | ✓ | **HIGH** | Sage: offline static BN, observational; RIFT: live graph + do(·) |
| **CloudRanger** (Wang et al.) | CCGrid 2018 | ✓ | PC algorithm DAG | GRAPHICAL | ✗ | ✗ | ✗ | ✓ | MEDIUM | CloudRanger: PC discovery, observational; RIFT: adds live intervention |
| **CausalRCA / CIRCA** | Various 2022-23 | ✓ | PC/NOTEARS DAG | GRAPHICAL | ✗ | ✗ | ✗ | ✓ | **HIGH** | Both purely observational; RIFT closes the do(·) loop |
| **RCD** (Ikram et al.) | ICSE 2022 | ✓ | PC algo, repeated windows | GRAPHICAL | ✗ | ✗ | ✗ | ✓ | MEDIUM | RCD: sliding-window observational DAG; RIFT: live intervention |
| **Microscope** (Liu et al.) | ICSOC 2019 | ✓ | Granger causality graph | GRAPHICAL | ✗ | ✗ | ✗ | ✓ | **HIGH** | Granger ≠ Pearl; RIFT: structural do(·) vs. temporal prediction |
| **CauseInfer** | INFOCOM 2014 | ✓ | PC algorithm DAG | GRAPHICAL | ✗ | ✗ | ✗ | ✓ | MEDIUM | Same gap: observational only |
| **AutoMAP** (Du et al.) | WWW 2020 | ✓ | Correlation graph | INFORMAL | ✗ | ✗ | ✗ | ✓ | LOW | Purely correlational |
| **BARO** (Nguyen et al.) | FSE 2023 | ✓ | BOCPD + static DAG | GRAPHICAL | ✗ | ✗ | ✗ | ✓ | LOW | Change-point detection, not causal attribution |
| **KDD 2022 Causal RCA** (Li et al.) | KDD 2022 | ✓ | SCM (observed interventions) | FORMAL-SIM | PARTIAL | ✗ | ✗ | ✓ | **HIGH** | Uses do-notation but interventions are *logged events*, not executed |
| **Microsoft SCM Workshop** | SREcon 2021-22 | ✓ | SCM hand-specified | FORMAL-SIM | YES | ✗ | YES (limited) | ✓ | **HIGH** | Do-calculus on pre-specified static SCMs; RIFT: online, dynamic |
| **Sieve (ICSE 2023)** | ICSE 2023 | ✓ | Dependency graph | INFORMAL | ✗ | YES | ✗ | ✓ | **HIGH** | Runtime injection + adaptive — but no SCM, no do(·) formalism |
| **Pivot Tracing** | SOSP 2015 | ✓ | Happens-before causality | GRAPHICAL | ✗ | ✗ | ✗ | PARTIAL | MEDIUM | Observational causal chain tracing; RIFT: interventional |
| **NetMedic** | SIGCOMM 2008 | ✓ | Probabilistic dependency graph | GRAPHICAL | ✗ | ✗ | ✗ | ✓ | MEDIUM | Pre-specified graph, observational inference |
| **Shrink** | CoNEXT 2008 | ✓ | Hypothesis space | INFORMAL | YES (probes) | YES | ✗ | ✓ | MEDIUM | Active probing without formal SCM |
| **Gremlin/Chaos Engineering** | IEEE SW 2016 | ✓ | None | N/A | ✗ | YES | ✗ | ✗ | LOW | Resilience, not attribution |
| **LitmusChaos / Chaos Mesh** | CNCF OSS | ✓ | None | N/A | ✗ | YES | ✗ | ✗ | LOW | Infrastructure only |
| **Filibuster** (Meiklejohn et al.) | SoCC 2021 | ✓ | None | N/A | ✗ | YES (RPC) | ✗ | ✗ | LOW | Test-time minimization, not runtime RCA |
| **Active Fault Diagnosis (DES)** | IEEE TAC 2003-2015 | ✗ (CPS/control) | Automata model | FORMAL-LIVE | ✗ (do-analogue) | YES | ✗ | ✓ | **HIGH** | Conceptually closest; domain=control, not distributed SW |
| **Pearl do-calculus** | Book 2000/2009 | N/A | SCM (foundational) | FORMAL-LIVE | YES | N/A | YES | N/A | FOUNDATIONAL | RIFT's theoretical basis |
| **DoWhy** (Sharma & Kiciman) | arXiv/ICML 2020 | ✗ | SCM | FORMAL-SIM | YES | ✗ | YES | ✗ | MEDIUM | Offline library; RIFT applies to live systems |
| **Adaptive Submodularity** (Golovin & Krause) | JAIR 2011 | ✗ | None | N/A | N/A | YES (tests) | ✗ | ✓ | **HIGH** | Covers min-intervention-set theory; RIFT must show systems constraints require new algo |
| **Eberhardt & Scheines** | Phil Sci 2007 | ✗ | SCM | FORMAL | YES | ✗ | ✗ | N/A | MEDIUM | Theoretical min-intervention bounds; RIFT applies to live systems |
| **Dapper** (Sigelman et al.) | Google TR 2010 | ✓ | None | N/A | ✗ | ✗ | ✗ | ✗ | LOW | Trace infrastructure RIFT builds on |
| **CRISP** (critical path, ATC 2022) | ATC 2022 | ✓ | Critical path DAG | GRAPHICAL | ✗ | ✗ | ✗ | ✓ | LOW-MED | Critical-path attribution; no intervention; no SCM |
| **Gray Failure** (Huang et al.) | HotOS 2017 | ✓ | Conceptual | INFORMAL | ✗ | ✗ | ✗ | PARTIAL | MEDIUM | Defines the problem class RIFT targets; no mechanism |
| **LDFI** (Alvaro et al.) | SIGMOD 2015 | ✓ | Lineage graph | GRAPHICAL | ✗ | YES (backward) | YES (lineage) | PARTIAL | **HIGH** | Backward causal reasoning + injection; test-time only; no do(·) |

---

## Causal Depth Landscape (as of Phase 1)

```
INFORMAL (correlation/graph traversal)
  MicroRCA, AutoMAP, Microscope*, CloudRanger*,
  Gremlin, LitmusChaos, CRISP, Gray Failure, Filibuster

  * also uses causal discovery vocabulary informally

GRAPHICAL (PC algorithm, BN, Granger — observational only)
  CloudRanger, RCD, CausalRCA, CIRCA, Sage, CauseInfer,
  NetMedic, Pivot Tracing

FORMAL-SIMULATED (SCM + do(·) but offline/static)
  KDD 2022 Causal RCA (Li et al.)
  Microsoft SCM Workshop (Sericola group)
  DoWhy (library)

FORMAL-LIVE (SCM + do(·) executed on running system)
  Active DES Diagnosis (control systems domain only)
  *** GAP — no distributed systems paper occupies this tier ***
  *** RIFT's claimed position ***
```

---

## MANDATORY BASELINES FOR RIFT EVALUATION

Based on this matrix, RIFT must compare against (in priority order):

1. **Sage** (ASPLOS 2021) — strongest causal model in microservices; must be beaten
2. **MicroRCA** (NOMS 2020) — most-cited; mandatory named comparison
3. **RIFT-no-intervention** (ablation) — proves the live do(·) layer adds value
4. **CausalRCA / CIRCA** — covers the causal discovery tier
5. **Sieve** (ICSE 2023) — runtime injection without causal model; covers that axis

---

## PAPERS REQUIRING INDEPENDENT VERIFICATION BEFORE CITATION

The following entries have MEDIUM confidence and must be verified against ACM DL / IEEE Xplore before appearing in the paper:

- [ ] KDD 2022 Causal RCA — Li et al. — verify exact title and author list
- [ ] Microsoft SCM Workshop paper — verify publication venue and year
- [ ] Sieve (ICSE 2023) — verify exact authors and technical details
- [ ] RCD (Ikram et al., ICSE 2022) — verify details
- [ ] BARO (Nguyen et al., FSE 2023) — verify details
- [ ] Filibuster (Meiklejohn et al., SoCC 2021) — verify details

*All HIGH-confidence entries (MicroRCA, Sage, CloudRanger, Dapper, Pearl, DoWhy, Golovin & Krause, Eberhardt & Scheines, LDFI) are well-established and can be cited with verification of exact venue/year details.*
