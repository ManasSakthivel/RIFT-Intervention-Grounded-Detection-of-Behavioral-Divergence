# Sprint 7 / Workstream 2 — Non-Oracle End-to-End Causal Evaluation

**Scope:** learned-PAG (FCI on observed telemetry) RIFT pipeline versus oracle-PAG variants. DEV and VAL splits only; the sealed held-out split was **never opened** by this workstream.
**Git commit:** `ebad911087942f257ba434f69816ed6d692be170` (working tree carries the earlier uncommitted recovery edits; this workstream modified **no file under `src/`**).
**Driver:** [`scripts/sprint7_non_oracle_eval.py`](../../scripts/sprint7_non_oracle_eval.py) (new, read-only with respect to every other file).
**Raw outputs:** `artifacts/sprint7/ws2_non_oracle/*.json` (suffix `_cl0138` / `_cl0148` = causal-learn version used).
**Environment:** Python 3.11, numpy 1.25.2, scipy 1.16.3, pandas 2.1.0, networkx 3.6.1, macOS arm64. Two causal-learn versions were run: the installed **0.1.3.8**, and **0.1.4.8** (the version `requirements.txt` pins; installed with `pip install --no-deps --target /tmp/cl048`).

---

## 0. Verdict

| # | Question | Answer (all numbers are synthetic benchmark results, not live-system results) |
|---|---|---|
| 1 | Is the "97 %+ of learned edges are circle-marked" figure real? | **Yes, and it is reproduced.** Sprint 4.4.0's 271/277 (97.8 %, dev) and 162/167 (97.0 %, val) re-run **exactly** under causal-learn 0.1.4.8, with 0 of 196 scenarios differing. On every FCI-able scenario the figure is **465/476 = 97.7 %** [95.9, 98.7] (0.1.3.8: 471/476 = 98.9 %). Only **3/476 = 0.6 %** of edges are fully directed. It is **not** a decoder artefact: it is computed from the raw mark matrix (§3.3). |
| 2 | Is the circle share a data-size problem or structural? | **Both.** With a *perfect* conditional-independence oracle on the true graphs, FCI still leaves **822/949 = 86.6 %** of edges circle-marked (0.1.4.8) and only 13.4 % fully directed. I attribute the remaining ≈ 11 points to finite-sample error (median n = 33 windows, median 4 variables) but did not isolate which factor drives it. Graphs without an unshielded collider are observationally unorientable (§2 toy table, §6.1); I did not tabulate how many of the benchmark's ten structure families are collider-free. |
| 3 | Learned vs oracle on the legacy "10/12, 24/24" harness | **10/12 → 9/12** on the harness's own metric (top-1 *name* is 12/12 for both). **"24/24 confounded abstention" → 0/24 actual abstentions for both oracle and learned.** The harness counts "abstain **or** any warning". Oracle warnings are 24/24 bidirected-edge warnings; learned warnings are 24/24 but only **3/24** mention a bidirected edge, and the same generic warning fires on 10/12 non-confounded scenarios (§4.1). |
| 4 | Learned vs oracle on the legacy reproducible-evaluation path | Confounded abstention **24/24 → 0/24** (dev) and **12/12 → 0/12** (val). The "oracle upper bound" on non-confounded P@1 is **not** an upper bound: oracle **13/26** (50.0 %) vs learned **20/26** (76.9 %) on dev. The oracle PAG is built from `causal_path`; of its 13 non-confounded abstentions on dev I traced 4 (the outcome node is absent from the oracle PAG) and 2 (empty `causal_path`); the other 7 were not traced (§4.2). |
| 5 | Learned vs oracle on the independent `rift_v2` benchmark (N = 252) | V2 P@1 **58/99 → 36/99** (oracle DAG → learned, paired 24 vs 2, p = 1×10⁻⁵). V3 P@1 **46/99 → 45/99** (no measurable gap). Abstention on ABSTAIN_REQUIRED cases is **higher** with the learned graph for V2 (101/153 vs 87/153, p = 0.0013). V3 learned abstains on 115/153 = 75.2 % and has FAR_unsafe 48/93 = 51.6 % (§4.3). |
| 6 | Do active interventions (tc netem / MSIS) disambiguate the equivalence class? | **Not in the pipeline as built, and only partially in the simulator.** (a) No code path turns a `do()` result into a changed PAG mark; `disambiguating_intervention` is produced by `identify_query` and consumed by nothing (0 references outside its definition). (b) The legacy `RIFT-FULL` path executes **no** intervention at all (§5.1). (c) In a stand-alone simulated test of pairwise `do(x)→y` on 465 circle-marked edges, 182/319 (57.1 %) edges with a true one-way ancestral direction were resolved correctly, 27.3 % gave no verdict, 12.9 % gave "both ways", 2.8 % were oriented wrongly. A **placebo** (perturbation zeroed) passes the same gate 13.1 % of the time. (d) `tc netem` could not be executed on this host (macOS, no `tc`); the only live evidence is N = 1 and ended in `ABSTAINED / NOT_IDENTIFIABLE`. |

**Bottom line.** Without the ground-truth PAG, RIFT's observational stage supplies almost no orientation. Whatever localization it achieves comes from temporal precedence (EBD) and, in V2/V3, from interventions that bypass the graph. Its identifiability gate abstains on a hidden confounder only when FCI happens to emit an adjacent `↔` (3 of 252 scenarios). The oracle-PAG figures 10/12 and 24/24 are therefore **harness-consistency checks** and must not be cited as capabilities of the learned pipeline.

---

## 1. What was executed and how

No ground truth reaches a method. Labels are read only by scorers and by explicitly labelled ORACLE constructors, the same discipline as `benchmark_v2.py`. Every part of the driver is deterministic.

| Part (`python scripts/sprint7_non_oracle_eval.py <part>`) | What it does | N |
|---|---|---|
| `legacy` | `validation/validation_harness.py` (36 dev) and `scripts/run_reproducible_evaluation.py::run_rift_full_scenario` (dev 50, val 18), each with the oracle PAG and with a learned FCI PAG, plus mark census | 36 / 50 / 18 |
| `legacywarn` | Which assumption-warning kinds the harness sees with a learned PAG; does the `confounded` flag change the generated data? | 36 |
| `v2graph` | Raw-matrix FCI mark census and graph quality on `rift_v2` dev + val | 252 |
| `v2attr` | `run_v2` (A1-FULL) and `run_v3` (V3-FULL) with **learned PAG** vs **oracle DAG** (the benchmark's `_true_pag` / `from_true_dag`) | 252 |
| `v2poppag` | Same, but the oracle is the **population PAG** (FCI + perfect d-separation oracle; keeps circles). Acyclic graphs only | 222 |
| `popceiling` | Mark census of those population PAGs: the best any sample size can do | 222 |
| `interv` / `placebo` | Pairwise `do(x)→y` test on every learned edge, and its null calibration | 476 edges / 930 tests |
| `toy` | Population PAGs of chain / fork / collider / hub / latent structures | 6 |

**Corroborating checks run:** `scripts/recovery_ledger_verify.py` → **34 PASS / 0 FAIL / 0 SKIP**; `tests/unit/test_sprint440_attribution_v3.py` → **34 passed**.

**Deviations and limits (read before citing any number):**

1. **Everything is synthetic.** `rift_v2` is a linear-Gaussian simulator with injected faults; the legacy harness uses a toy step-function generator. No live Prometheus telemetry was analysed.
2. **`tc netem` was not executed.** The host is Darwin and `tc` is absent. "Intervention" below means the simulator's `do()` (`rift/scenarios/simulator.py::intervene`: 30 s baseline + 30 s perturbed window at 1 Hz, perfect delivery unless the scenario says otherwise).
3. **causal-learn version matters slightly.** Counts differ on the circle share (97.7 % vs 98.9 %) and on a handful of marks, but **every attribution result in §4.3 is byte-identical across both versions** (`v2attr_cl0138.json` ≡ `v2attr_cl0148.json`, `v2poppag` likewise). Primary numbers use 0.1.4.8 because it reproduces Sprint 4.4.0 exactly and is the version in `requirements.txt`.
4. **The `rift_v2` "oracle" is an oracle DAG, not an oracle PAG.** It has no circles and no `↔` edges and hides latent variables. §4.3 therefore also reports the population PAG.
5. **Cyclic scenarios** (30 of 252, `SYMMETRIC_MUTUAL_DEPENDENCY`) have no defined d-separation and are excluded from the population-PAG runs only.
6. **Statistics are exploratory.** Wilson 95 % intervals and exact McNemar tests are shown; no multiplicity correction. The 24 legacy confounded scenarios are 4 distinct contents (`DATASET_AUDIT.md` §4.1), so they are not 24 independent observations.

---

## 2. How the learned FCI pipeline handles circle marks (code trace)

```
telemetry ─► run_fci (fisherz, α=0.05)             src/rift/fci/fci_runner.py:179
          ─► _decode_pag_edges  (frozen, defect D1) fci_runner.py:105   PAGEdge types: DIRECTED / BIDIRECTED / PARTIALLY_DIRECTED / UNDIRECTED / TAIL_TAIL
          ─► compute_ebd  R1 deviation, R2 precedence, R3 reachability   ebd.py:60 _pag_to_digraph
          ─► identify_query  (backdoor / front-door / ↔ gate)            identifiability.py:227
          ─► [V2/V3] do() on candidates, CID gate, Holm                  rift_v2.py / rift_v3.py
```

| Stage | Behaviour on circle marks | Evidence |
|---|---|---|
| Decoding | causal-learn's `M[x][y]` is the mark **at x**. The frozen decoder reads the partially-directed pair as `(2,-1)` but real `o→` is `(2,1)`. Every `o→` therefore falls into `else: UNDIRECTED`, and the rare `o--` is invented as `PARTIALLY_DIRECTED`. | `fci_runner.py:151-166`; toy collider below |
| EBD R3 reachability | `UNDIRECTED` and `TAIL_TAIL` edges are added in **both** directions; `PARTIALLY_DIRECTED` one way. A path of `o-o` edges satisfies R3. Path kind is then `SEMI_DIRECTED` and only a warning is appended. | `ebd.py:60-77, 426-432` |
| Identifiability | An `o-o` or `o→` edge touching source or target yields `CONDITIONALLY_IDENTIFIABLE` (backdoor "in some MAGs"), **not** an abstention. `NOT_IDENTIFIABLE` is returned only for (i) a missing variable, (ii) `↔` adjacent to the source, or (iii) no backdoor/front-door set. | `identifiability.py:110-121, 267-285` |
| Gate probe | `o-o` chain → CONDITIONALLY_IDENTIFIABLE; `A o→ B` → CONDITIONALLY_IDENTIFIABLE; `A ↔ B` → NOT_IDENTIFIABLE; `A ↔ B` plus `A → B` → REQUIRES_INTERVENTION (method ABSTAIN). | executed directly in this workstream |
| Resulting status | V2 on dev: `CONDITIONALLY_IDENTIFIABLE` 114, `IDENTIFIABLE` 2, no status 64. Val: 47 / 0 / 22, plus `NOT_IDENTIFIABLE` 3. | `artifacts/sprint4_3_0/results/*/per_scenario.json` |
| V3 | Never selects or confirms a root from the PAG. It uses the corrected marks only as a *contradiction check* (`PAG_CONTRADICTS_INTERVENTION`). | `rift_v3.py:232-262` |

**Population-level behaviour of FCI itself (`toy.json`, perfect CI oracle, causal-learn 0.1.4.8):**

| True structure (H hidden) | Edge marks FCI can commit to |
|---|---|
| chain A→B→C | `A o-o B`, `B o-o C` |
| fork A←B→C | `A o-o B`, `B o-o C` |
| hub R→{X,Y,Z} | `R o-o X`, `R o-o Y`, `R o-o Z` |
| latent A←H→B | `A o-o B` |
| collider A→C←B | `A o→ C`, `B o→ C` |
| latent + collider A←H→B→C←D | `A o-o B`, `B o→ C`, `C ←o D` |

A root whose children have no other observed parent is a hub: **even with a perfect CI oracle FCI leaves its edges as `o-o`.** Only colliders, and the rules that propagate from them, orient. I did not tabulate which of the benchmark's ten structure families are collider-free; the measured outcome is the 86.6 % in §3.4.

---

## 3. The circle-mark share, verified

### 3.1 Reproduction of the reported 97 % figure

| Measurement | Edges | Circle-marked | Share | Wilson 95 % |
|---|---:|---:|---:|---|
| Sprint 4.4.0 report, dev (138 scenarios with a PAG) | 277 | 271 | 97.8 % | — |
| Sprint 4.4.0 report, val (58) | 167 | 162 | 97.0 % | — |
| **Re-run, same scenarios, cl 0.1.4.8** | 277 / 167 | 271 / 162 | **97.8 % / 97.0 %** | 0 of 196 scenarios differ from the saved trace |
| Re-run, same scenarios, cl 0.1.3.8 | 277 / 167 | 275 / 164 | 99.3 % / 98.2 % | 2 scenarios differ (V2D-0117, V2V-0022) |
| **All FCI-able scenarios, cl 0.1.4.8** (150 dev + 63 val) | 476 | **465** | **97.7 %** | [95.9, 98.7] |
| All FCI-able scenarios, cl 0.1.3.8 | 476 | 471 | 98.9 % | [97.6, 99.6] |
| Per scenario with ≥ 1 edge: every edge circle-marked | 204 scenarios | 197 | 96.6 % | [93.1, 98.3] |
| Legacy harness, learned PAG (36 dev, 11 variables, 18 samples) | 92 | 89 | 96.7 % | [90.8, 98.9] |
| Legacy reproducible path, dev 50 / val 18 | 139 / 46 | 139 / 46 | 100 % | [98.0, 100] pooled |

*Why 150/63 and not 138/58:* Sprint 4.4.0's saved traces mark 12 dev and 5 val scenarios as `pag_status = NONE` (FCI not run by V2; cause not recorded there). The driver runs FCI on every scenario with enough windows, so it also covers these 17. The 196 scenarios that did have a PAG in Sprint 4.4.0 are the ones compared one-for-one above.

### 3.2 Mark census (cl 0.1.4.8, 476 edges on 204 scenarios)

| Edge kind | Count | Share | Of which true-direct edges |
|---|---:|---:|---:|
| `o-o` | 417 | 87.6 % | 232 |
| `o→` / `←o` | 24 / 23 | 9.9 % | 14 / 17 |
| `→` / `←` (fully directed) | 3 | 0.6 % | 1 |
| `↔` | 4 | 0.8 % | 1 |
| `---` (tail–tail) | 4 | 0.8 % | 3 |
| `o--` | 1 | 0.2 % | 0 |

FCI on this corpus: 39/252 scenarios (15.5 %) yield **no PAG** (`INSUFFICIENT_SAMPLES`); 9 more yield an empty graph. The median FCI call has **n = 33 samples (range 17–37) and k = 4 variables (range 2–8)**.

### 3.3 Orientation quality of the learned PAG against the true DAG

Skeleton (409 scored adjacencies vs 687 true observed direct edges; the 67 learned adjacencies whose true relation is a hidden common cause are not counted as FP by `diagnostics.graph_quality`, as in Sprint 4.4.0): TP 268, FP 141, FN 419 → **precision 65.5 %** [60.8, 70.0], **recall 39.0 %** [35.4, 42.7].

Orientation of the 268 true-positive edges (confusion):

| FCI mark on a true edge | Count | Share |
|---|---:|---:|
| circle at either end, no arrowhead contradicting truth | 249 | 92.9 % |
| fully directed **correctly** | **1** | 0.4 % |
| arrowhead at the true source (**wrong**) | **14** | 5.2 % |
| tail–tail | 3 | 1.1 % |
| `↔` on a true direct edge | 1 | 0.4 % |

Only 1 of the 15 edges that FCI committed to was oriented correctly. With so few committed edges this supports "no evidence of reliable orientation", not an error-rate estimate.

**The 97 % figure is not a decoder artefact.** `SPRINT7_FINAL_CLAIMS_LEDGER.md` row S4 says part of the circle rate is an artefact of defect D1. The decoder does inflate the *UNDIRECTED* count (frozen decoder: 464 `UNDIRECTED` = 97.5 %, against 417 genuine `o-o` = 87.6 %, so 47 `o→` edges were collapsed). The *circle-marked* share is computed from the raw matrix and is unaffected. The ledger note should read "the frozen decoder over-reports `o-o` by 47 edges; the circle-marked share itself is correct".

### 3.4 Structural ceiling (perfect CI oracle)

222 acyclic scenarios, 949 edges, every true direct edge recovered (724/724):

| Mark class | cl 0.1.4.8 | cl 0.1.3.8 |
|---|---:|---:|
| circle-marked | 822 (**86.6 %**) | 870 (91.7 %) |
| `o-o` | 665 (70.1 %) | 665 (70.1 %) |
| fully directed | 127 (**13.4 %**) | 79 (8.3 %) |
| `↔` | **0** | **0** |

Two consequences. (i) Even unlimited data leaves ~87 % circle-marked on this corpus, so the learned 97.7 % is ≈ 11 points above the structural floor. I attribute that gap to finite-sample error but did not isolate which factor drives it. (ii) A perfect-CI PAG contains **no `↔` edge at all** in this corpus (hidden nodes feed several observed children, which FCI renders as `o-o`, not `↔`). The only `↔` that can appear in a learned PAG are finite-sample artefacts, which is exactly what §4.4 shows. (The two edge sets are different populations: 949 population edges vs 476 learned edges, so the comparison is indicative, not paired.)

---

## 4. Localization, abstention and false attribution: learned PAG vs oracle PAG

**Definitions.** `P@1` = correct top-1 root on ATTRIBUTE cases. `FAR_w` = wrong top-1 ÷ answered. `FAR_u` = unsafe ÷ answered, where unsafe = answered on an ABSTAIN_REQUIRED case **or** wrong root. "Abstained" means `BaselineOutput.abstained`, never "emitted a warning".

### 4.1 Legacy harness: the "10/12 and 24/24" numbers (36 dev scenarios)

Same data, same `compute_ebd`, only the PAG changes (`legacy_*.json`, `legacywarn_cl0148.json`).

| Metric | Oracle PAG | Learned PAG |
|---|---:|---:|
| Non-confounded (n = 12): root found, CANDIDATE/DEFINITIVE at any rank — the harness's "P@1" | **10/12** (83.3 %) [55.2, 95.3] | **9/12** (75.0 %) [46.8, 91.1] |
| Non-confounded: top-1 service equals the true root | 12/12 | 12/12 |
| Non-confounded misses | RC_01, RC_02 (`redis_cart`, confidence NONE) | RC_01, RC_02, MC_01 (confidence NONE) |
| Non-confounded wrong top-1 (FAR_w) | 0/12 | 0/12 |
| Confounded (n = 24): **actually abstained** | **0/24** | **0/24** |
| Confounded: "abstain **or** any warning" — the harness's V2 | **24/24** | **24/24** |
| Confounded: warning that names a bidirected edge | 24/24 | **3/24** (12.5 %) [4.3, 31.0] |
| Confounded: top candidate is the true root (i.e. it attributes) | 24/24 | 24/24 |
| Non-confounded scenarios that also receive a warning | 2/12 (`redis_cart` not in graph) | **10/12** (generic "non-oriented edges") |

Confusion matrix, learned PAG, confounded flag vs behaviour:

| | Abstained | Attributed with bidirected warning | Attributed with only "non-oriented edge" warning |
|---|---:|---:|---:|
| flagged confounded (24) | 0 | 3 | 21 |
| not confounded (12) | 0 | 0 | 10 (+2 no warning) |

The learned warning does not separate the classes: bidirected-warning Fisher p = 0.54, any-warning p = 0.10. **The `confounded` flag has no effect on the generated data**: flipping it changes the metrics of 0/24 scenarios. So no estimator could detect "confounding" from this telemetry; the oracle's 24/24 is the label being echoed through `build_oracle_pag` (ledger leak L1).

### 4.2 Legacy reproducible-evaluation path (`run_rift_full_scenario`; dev 50, val 18)

Source of the "oracle" here: `build_oracle_pag(scenario)` from `causal_path`, plus a bidirected edge from `affected_services` when `confounded` is true. The oracle's outcome node comes from ground-truth `affected_services` (`select_outcome_node`).

| Dev (50) | Oracle PAG | Learned PAG |
|---|---|---|
| Non-confounded (26): correct / wrong / abstained | **13** / 0 / 13 (4 `NOT_IDENTIFIABLE`, 9 `NO_CANDIDATES`) | **20** / 3 / 3 (`NO_CANDIDATES`) |
| Non-confounded P@1 | 13/26 = **50.0 %** [32.1, 67.9] | 20/26 = **76.9 %** [57.9, 89.0] |
| Confounded (24): abstained / attributed | **24** / 0 (all `NOT_IDENTIFIABLE`) | **0** / 24 |
| Wrong answers | 0 | 3 (QU_01, MC_04, MC_09) |
| FAR_w (wrong ÷ answered) | 0/13 | 3/47 = 6.4 % [2.2, 17.2] |
| Unsafe ÷ answered (confounded-as-ABSTAIN_REQUIRED) | 0/13 | 27/47 = 57.4 % [43.3, 70.5] |

| Val (18) | Oracle PAG | Learned PAG |
|---|---|---|
| Non-confounded (6): correct / wrong / abstained | 4 / 0 / 2 | 4 / 1 (MC_02) / 1 |
| Confounded (12): abstained | **12/12** | **0/12** |

Pooled dev + val, non-confounded P@1: oracle **17/32** (53.1 %) vs learned **24/32** (75.0 %); paired learned-only 10 vs oracle-only 3, exact McNemar p = 0.092. Pooled confounded abstention: **36/36 vs 0/36**. Pooled FAR_w: 0/17 vs 4/64 = 6.2 %.

*Why the "upper bound" is lower on P@1.* Traced cases: PL_01, PL_02, QU_01, QU_02 have an oracle PAG over 2–3 variables only, while `select_outcome_node` returns `frontend` (`affected_services[-1]`), which is not in that PAG, so `identify_query` abstains (`Target variable 'frontend' not in PAG variables`). RC_01 and RC_02 have an empty `causal_path`, so the root is absent from the graph and R3 fails. The MC and AA cases that return `NO_CANDIDATES` (MC_05/07/08/10/11, AA_01/02) were not traced further. The oracle path is an unfaithful ceiling, a defect of how the oracle is constructed.

### 4.3 Independent benchmark `rift_v2` (dev + val, N = 252: 99 ATTRIBUTE, 153 ABSTAIN_REQUIRED)

Methods differ only in the graph handed to the same code.

**Primary result (oracle = true observed DAG):**

| | V2 learned | V2 oracle DAG | V3 learned | V3 oracle DAG |
|---|---:|---:|---:|---:|
| **P@1** on 99 ATTRIBUTE | **36** (36.4 %) [27.6, 46.2] | **58** (58.6 %) [48.7, 67.8] | **45** (45.5 %) [36.0, 55.2] | **46** (46.5 %) [37.0, 56.2] |
| wrong root | 27 | 7 | 10 | 10 |
| ATTRIBUTE cases abstained | 36 | 34 | 44 | 43 |
| ABSTAIN_REQUIRED **correctly abstained** (of 153) | **101** (66.0 %) | 87 (56.9 %) | **115** (75.2 %) [67.8, 81.3] | 110 (71.9 %) |
| ABSTAIN_REQUIRED answered | 52 | 66 | 38 | 43 |
| Unsafe (of 252) | 79 (31.3 %) | 73 (29.0 %) | **48** (19.0 %) | 53 (21.0 %) |
| Answered | 115 | 131 | 93 | 99 |
| **FAR_u** (unsafe ÷ answered) | 68.7 % [59.7, 76.5] | 55.7 % [47.2, 63.9] | **51.6 %** [41.6, 61.5] | 53.5 % [43.8, 63.0] |
| FAR_w (wrong ÷ answered ATTRIBUTE) | 27/63 = 42.9 % | 7/65 = 10.8 % | 10/55 = 18.2 % | 10/56 = 17.9 % |

Paired tests (exact McNemar; first number = learned-only successes):

| Comparison | learned-only | oracle-only | p |
|---|---:|---:|---:|
| V2 P@1, learned vs oracle DAG | 2 | 24 | 1×10⁻⁵ |
| V3 P@1, learned vs oracle DAG | 0 | 1 | 1.00 |
| V2 abstention on ABSTAIN_REQUIRED | 16 | 2 | 0.0013 |
| V3 abstention on ABSTAIN_REQUIRED | 5 | 0 | 0.0625 |
| P@1 V3 learned vs V2 learned | 19 | 10 | 0.136 |

**Performance gap (oracle DAG − learned), `rift_v2`:**

| | V2 | V3 |
|---|---:|---:|
| P@1 | **+22** (+22.2 pts) | **+1** (+1.0 pt) |
| Wrong roots | −20 | 0 |
| Correct abstention | **−14** (the oracle graph makes V2 *over-answer*) | −5 |
| Unsafe | −6 | **+5** (learned V3 is *safer*) |

**Control: oracle = population PAG** (keeps circles; 222 acyclic scenarios, 95 ATTRIBUTE, 127 ABSTAIN_REQUIRED):

| | V2 learned | V2 population PAG | V3 learned | V3 population PAG |
|---|---:|---:|---:|---:|
| P@1 | 36/95 | **50/95** | 45/95 | 46/95 |
| wrong root | 27 | 18 | 10 | 10 |
| correct abstention (of 127) | 87 | 73 | 91 | 86 |
| unsafe (of 222) | 67 | 72 | 46 | 51 |

So the V2 gain from a better graph is real but about **a third smaller** (+14 vs +22) when the oracle is a faithful PAG rather than a fully oriented DAG. The Ns differ (95 vs 99 ATTRIBUTE cases, since cyclic scenarios are dropped), and V2-learned P@1 is 36 in both. V3 is nearly insensitive to the graph.

**Confusion matrices (N = 252).** Rows are the ground-truth expected outcome; columns are what the method did.

| Expected | Outcome | V2 learned | V2 oracle DAG | V3 learned | V3 oracle DAG |
|---|---|---:|---:|---:|---:|
| ATTRIBUTE (99) | correct root | 36 | 58 | 45 | 46 |
| | wrong root | 27 | 7 | 10 | 10 |
| | abstained | 36 | 34 | 44 | 43 |
| ABSTAIN_REQUIRED (153) | abstained | 101 | 87 | 115 | 110 |
| | answered | 52 | 66 | 38 | 43 |

**Confounded / hidden-cause subsets** (structure ∈ {`confounding`, `hidden_common_cause`}, 53 scenarios, 38 of them ABSTAIN_REQUIRED):

| | V2 learned | V2 oracle DAG | V3 learned | V3 oracle DAG |
|---|---:|---:|---:|---:|
| ABSTAIN_REQUIRED abstained (of 38) | 27 (71.1 %) [55.2, 83.0] | 26 (68.4 %) | 28 (73.7 %) [58.0, 85.0] | 28 (73.7 %) |
| `hidden_common_cause` only, abstained (of 31, root unobserved) | 22 (71.0 %) | 22 | 23 (74.2 %) | 23 |
| `hidden_common_cause` answered (unsafe) | 9 | 9 | 8 | 8 |
| ATTRIBUTE cases in `confounding`, P@1 (of 15) | 4 | 6 | 6 | 6 |

Abstention here comes from `INSUFFICIENT_BASELINE`, `INSUFFICIENT_SAMPLES`, `NO_CANDIDATES` and intervention-gate refusals, **not** from detecting confounding. The learned and oracle numbers are almost identical because the oracle DAG cannot represent the hidden cause. By ground-truth abstain reason, ROOT_UNOBSERVED is answered on 9/31 (V2) and 8/31 (V3) regardless of graph.

### 4.4 Does the abstention gate recognise confounding at all?

`NOT_IDENTIFIABLE` fired on **3/252** scenarios with the learned PAG (all in val): V2V-0051 (ATTRIBUTE), V2V-0062 (ABSTAIN_REQUIRED), V2V-0069 (ATTRIBUTE). One was a required abstention and two were spurious. In total the learned PAGs contain **4 `↔` edges in 476** (0.8 %; 0/67 on edges whose true relation is a hidden common cause). The gate's ability to detect latent confounding is therefore bounded by P(FCI emits an adjacent `↔`) ≈ 1 % here. The perfect-CI ceiling is 0 (§3.4).

---

## 5. Do active interventions (tc netem / MSIS) disambiguate the equivalence class?

### 5.1 What the code does (static trace)

| Claim | Finding | Evidence |
|---|---|---|
| "An intervention on the source can disambiguate the true MAG" | The field `IdentifiabilityResult.disambiguating_intervention` is set in 3 places and **read nowhere** (grep over `src/` and `scripts/`: 0 hits outside `identifiability.py`). | `identifiability.py:279, 348, 364` |
| Interventions update the graph | `ClosedLoop.update_graph_structure` edits a `networkx` graph of its own, never a PAG mark. It is reached only through `ClosedLoop.step` (tests and `run_to_completion`). The end-to-end runner calls only `update_edge_confidence` and `update_candidate_posterior`; `structure_changed` stays `False`. V2 and V3 never call it. | `closed_loop.py:220-266, 346`; `e2e_runner.py:1218-1221` |
| Legacy `RIFT-FULL` is "active" (SPRINT2_ABLATION_REPORT: "Active Intervention is the Engine of Disambiguation … 93.62 %") | `run_rift_full_scenario` performs **no** `do()` and no CID call. Step 4 ranks `passing_ebd` with a fixed 0.95/0.80 confidence and writes the constant `total_intervention_ed_s=30.0`. The 88 %/93.6 % legacy figures are observational EBD plus the semi-directed R3 relaxation, and that benchmark is non-discriminative (a trivial latency-correlation baseline scores 50/50; ledger check E). | `run_reproducible_evaluation.py:264-277` |
| MSIS selects the interventions that disambiguate | `greedy_msis` / `compute_intervention_costs` use an EIG proxy `h_before × posterior_mass`. The posterior comes from EBD timing (`exp(−Δt/20)`), with **no equivalence-class term**. V2 ablations (pooled, 99 ATTRIBUTE): NO-MSIS P@1 34 vs 36 (p = 0.63); RANDOM-INTERVENTION 35 vs 36 (p = 1.0). MSIS ordering has no detectable effect. | `cost_model.py:171-175, 250-340`; `rift_v2.py:226`; `artifacts/sprint4_3_0/results/*/aggregate.json` |
| Interventions help V2 at all | NO-INTERVENTION P@1 41 vs 36 (p = 0.50) and unsafe 85 vs 79. No significant gain from interventions on P@1 or unsafe in V2 (not powered to claim equivalence). | same |

### 5.2 Stand-alone test: can `do(x)→y` orient a circle-marked edge? (`interv`, `placebo`)

For every learned edge `{a,b}` the simulator's `intervene` was called twice (`do(a)→b` and `do(b)→a`) and the V2/V3 CID gate (`compute_cid` + `validate_cid_for_r4`) was applied. Verdict = which directions pass. Truth = **ancestry in the full DAG** (`true_structure["anc"]`), because a `do()` test sees descendants, not direct edges. cl 0.1.4.8; 476 edges, of which 465 carry a circle.

Confusion matrix on the **465 circle-marked edges**:

| Truth for the pair | Correct direction | Wrong direction | "Both ways" | No verdict | Total |
|---|---:|---:|---:|---:|---:|
| one-way ancestry (319) | **182** (57.1 %) [51.6, 62.4] | 9 (2.8 %) | 41 (12.9 %) | 87 (27.3 %) | 319 |
| mutual ancestry (15, symmetric mutual-dependency pairs) | — | 2 oriented | 12 | 1 | 15 |
| no ancestry (131) | — | **14** oriented spuriously (10.7 %) [6.5, 17.1] | 9 | 108 (82.4 %) | 131 |

Headline: when the gate commits to a direction on a circle-marked edge it is right **182/207 = 87.9 %** [82.8, 91.7] of the time, but it commits on only **207/465 = 44.5 %** of them. 100 of the 204 scenarios (49.0 %) have **all** their circle edges resolved to the truth.

By edge truth class (rows are FCI-reported edges; columns are the `do()` verdict):

| Truth class of edge | One-way | Both | None | n |
|---|---:|---:|---:|---:|
| DIRECT | 160 | 37 | 66 | 263 |
| INDIRECT_ANCESTRAL | 33 | 16 | 22 | 71 |
| HIDDEN_COMMON_CAUSE | 6 | 7 | 54 | 67 |
| UNRELATED | 8 | 2 | 54 | 64 |

(Circle-marked edges only; the 11 non-circle edges are excluded, so the rows sum to 465.)

Hidden-common-cause pairs are spuriously oriented or "both" in 13/67 = 19.4 % of cases (the `do()` gate sees the latent's downstream correlation as an effect in a minority of cases).

**Where it fails.** In scenarios labelled `weak_interventional_evidence` the correct-direction rate is 6/42 = **14.3 %** [6.7, 27.8], against 176/277 = 63.5 % [57.7, 69.0] elsewhere. `no_meaningful_effect`, `low_magnitude` and `imperfect` delivery modes are included in the aggregate above.

**Placebo (null calibration).** With the perturbation set to zero and collateral leakage removed, the same gate still passes **122/930 = 13.1 %** [11.1, 15.4] of directed tests on the same edges. The intervention cannot be the cause of these passes. I did not trace their source; the likely mechanism is that the simulator's fault signal continues across the baseline and perturbed windows. It is a plausible contributor to the "one-way" verdict being only 88 % precise and to the "both" verdict being common. The test used here is a single-pair test without Holm correction; V3's production gate also applies Holm and a manipulation check.

**Cost.** Covering all circle edges needs `do()` on a mean of **3.4 services per scenario** (max 7), well inside the 20-intervention / 600 s budget.

### 5.3 Live evidence (`tc netem`)

`tc` is not installed on this host, so no netem intervention was executed. The only live record is N = 1 (`artifacts/stage4_intervention_results.json`). The ledger verifier re-computed it this session: telemetry Z cartservice 143.06, rollback and netns isolation true, 15 pre / 12 active / 23 post samples. The offline pipeline on that same telemetry returns **ABSTAINED / NOT_IDENTIFIABLE**, `top1_correct = null`, CID grade **INSUFFICIENT** (15/12 samples < the 20-sample CID floor). The stored literal `attribution_accuracy_top1 = 1.0` is a historical orchestrator field, not an inference.

### 5.4 Verdict on the "interventions disambiguate equivalence classes" claim

* **Supported (simulation only):** a perfectly delivered `do(x)` provides *ancestral* information the PAG lacks. It resolves 57 % of true one-way circle edges at 88 % precision and 3.4 `do()`s per scenario.
* **Not supported:** (a) that this *updates the PAG* or *selects among MAGs in the equivalence class*: it does not, no code does; (b) that MSIS chooses the disambiguating interventions: MSIS ordering has no measurable effect; (c) that the legacy `RIFT-FULL` 88 % involves any intervention; (d) any live result: N = 1, below the CID floor, ended in abstention; (e) that it separates a latent confounder from a cause: 19 % of hidden-common-cause pairs are mis-resolved.
* A single-pair `do()` establishes an **ancestor relation**. An equivalence class is a statement about *edge marks*. Resolving `o-o` to `→` for an adjacent pair is necessary but not sufficient to select a MAG, and the pipeline never makes that step.

---

## 6. Formal analysis

**Notation.** `G` = true DAG over observed `O` and latent `L`. `P(G)` = the PAG FCI returns under a perfect CI oracle. `P̂` = the PAG learned from `n` samples.

### 6.1 Why `o-o` dominates (structural)

FCI orients an endpoint only via (i) unshielded colliders `a *→ c ←* b` with `c ∉ Sepset(a,b)`, and (ii) the propagation/discriminating-path rules that follow from (i). If `G[O]` has no unshielded collider in a connected component, `P(G)` on that component has every edge as `o-o`, whatever `n` is (§2 toy table). The measured **86.6 % circle-marked under a perfect CI oracle (§3.4)** is therefore a property of the benchmark's graph family, not of FCI's tuning. In a hub, the root (the object RIFT wants to attribute) cannot be distinguished from its children by observational data alone.

### 6.2 Sample-size loss (finite-sample)

With `n ≈ 33` and Fisher-z at `α = 0.05` on windows that are not shown to be i.i.d., the learned skeleton has recall 39.0 % and precision 65.5 % (§3.3). Missing and spurious edges can also remove or create colliders, so orientation can fail in two ways. Of the 268 true-positive edges, 249 (92.9 %) stay circle-marked, 3 are tail–tail, 1 is `↔`, 14 (5.2 %) are oriented against the truth, and only 1 (0.4 %) is oriented correctly. This is consistent with the 11-point gap between 86.6 % (ceiling) and 97.7 % (learned). *Which* finite-sample factor dominates (power, autocorrelation, non-Gaussian noise, hidden variables) was **not** isolated; it is an open hypothesis.

### 6.3 The identifiability gate (a decision-theoretic statement)

Let `A` = "RIFT abstains on identifiability" and `C` = "the incident has a latent confounder of the root". The code sets `A = 1[↔ adjacent to source ∧ no directed source→target path] ∨ 1[variable missing] ∨ 1[no backdoor/front-door set]`. Because backdoor returns `[]` by default (`identifiability.py:169`, "assume no confounding paths"), the third term almost never fires. Hence

`P(A | C) ≲ P(P̂ has ↔ adjacent to source | C)`.

Empirically that probability is ≈ 3/252 overall (§4.4) and 0/67 for hidden-common-cause edges, versus a perfect-CI value of 0. Oracle graphs achieve `P(A | C) = 1` only by construction (`build_oracle_pag` inserts `↔` when `confounded`), so "24/24" measures the code path `flag → edge → gate`, not detection.

### 6.4 Equivalence-class ambiguity does not trigger abstention

For a source adjacent to an `o-o` or `o→` edge, `identify_query` returns `CONDITIONALLY_IDENTIFIABLE` with `disambiguating_intervention = source`. V2/V3 treat that as answerable. The set of MAGs consistent with `P̂` is therefore large (any orientation of ~88 % of edges) but is never reported as a reason to abstain. The abstentions that do protect the user (`INTERVENTION_NOT_VERIFIED`, `AMBIGUOUS_ATTRIBUTION`, `UNRESOLVED_EARLIER_DIVERGENCE`) arise from the *interventional* evidence, which explains why V3, which ignores the PAG for selection, is safer than V2 with the same learned graph (unsafe 48 vs 79).

### 6.5 Why a better graph helps V2 but not V3

V2 uses the PAG to define candidate/outcome sets (`nx.has_path` on `_pag_to_digraph`), so graph errors translate directly into missed outcomes (36 → 58 correct roots with the oracle DAG). V3 uses graph-agnostic outcome sets (all other divergent services) plus Holm-corrected CID, so the learned graph affects only the *contradiction caveat*: 45 vs 46 correct.

---

## 7. Corrections to existing documents

| Document | Statement | Status after this workstream |
|---|---|---|
| `SPRINT7_FINAL_CLAIMS_LEDGER.md` S4 | "part of the 'circle' rate is a decoder artefact" | **Refine.** The decoder inflates the *UNDIRECTED* count by 47 edges (464 vs 417 genuine `o-o`). The circle-marked share is computed from raw marks and reproduces at 97.7 %. |
| `CLAIMS_EVIDENCE_LEDGER.md` C5 / `SPRINT7_FINAL_CLAIMS_LEDGER.md` H5 | "Learned FCI … achieves 0 % abstention on confounded faults due to orientation ambiguities" | **Confirmed numerically (0/24, 0/36 pooled)**, but the *cause* is not "orientation ambiguity": it is that the data contain no confounding signal (flag flip changes 0/24 datasets) and that a perfect-CI PAG has no `↔`. |
| `docs/phase3_5/oracle_vs_fci.md` | "FCI V1 ≤ Oracle V1" | **Wrong in the legacy path** (oracle 13/26 < learned 20/26 on dev non-confounded). Holds for V2 on `rift_v2` (36 vs 58 correct), not for V3 (45 vs 46). |
| `SPRINT2_ABLATION_REPORT.md` | "Active intervention is the engine of disambiguation … 93.62 %" | **Unsupported.** The `RIFT-FULL` path behind that figure executes no `do()`. |
| `REMEDIATION_STATUS.md:86` | "Active interventional disambiguation is most effective when combined with prior call graph topologies …" | **Unsupported as a general statement.** Ablation A2 (call-graph substitute for FCI) beats the learned graph (P@1 54 vs 36, paired 19 vs 1), but that is a result about FCI quality, not about interventions. |

---

## 8. Safe wording

> "On a synthetic corpus, FCI run on ≈ 33 observational windows per incident returns a PAG in which 97.7 % of edges (465/476) carry at least one circle mark and 0.6 % are fully directed. With a perfect conditional-independence oracle the same corpus still yields 86.6 % circle-marked edges, so most of the ambiguity is structural. With the learned graph, RIFT-V3 attributes the correct root in 45/99 attributable incidents and abstains on 115/153 incidents that require abstention; with the ground-truth DAG supplied it scores 46/99 and 110/153. RIFT does not detect hidden confounding from telemetry: its identifiability gate fired on 3 of 252 learned graphs, and the legacy 'confounded abstention 24/24' is a label echo. In simulation, a perfectly delivered `do()` resolves the direction of 57 % of ambiguous true-ancestor edges at 88 % precision; this update is not applied to the PAG by the pipeline, and it has not been demonstrated on a live system."

**Do not write:** "FCI + interventions recovers the causal graph", "RIFT abstains on confounded incidents", "learned-PAG RIFT approaches the oracle upper bound", "MSIS selects the disambiguating interventions", "netem interventions orient the PAG".

---

## 9. Reproduction

```bash
cd "RIFT FINAL"
# installed causal-learn (0.1.3.8)
PYTHONPATH=src:. python3.11 scripts/sprint7_non_oracle_eval.py legacy       # 1.5 s
PYTHONPATH=src:. python3.11 scripts/sprint7_non_oracle_eval.py v2graph      # ~15 s
PYTHONPATH=src:. python3.11 scripts/sprint7_non_oracle_eval.py v2attr       # ~60 s
# canonical pin (0.1.4.8) used for the primary numbers
python3.11 -m pip install --no-deps --target /tmp/cl048 causal-learn==0.1.4.8 momentchi2
for p in legacy legacywarn v2graph v2attr v2poppag popceiling interv placebo toy; do
  PYTHONPATH=/tmp/cl048:src:. python3.11 scripts/sprint7_non_oracle_eval.py $p
done        # each part writes artifacts/sprint7/ws2_non_oracle/<part>.json (rename with _cl0148 to keep both versions)
# corroboration
PYTHONPATH=src:. python3.11 scripts/recovery_ledger_verify.py                       # 34 PASS / 0 FAIL / 0 SKIP
python3.11 -m pytest tests/unit/test_sprint440_attribution_v3.py -q -p no:cacheprovider   # 34 passed
```

| Artifact | Contents |
|---|---|
| `legacy_cl01{38,48}.json` | §4.1 and §4.2: oracle vs learned counts, per-scenario outcomes, mark census |
| `legacywarn_cl0148.json` | §4.1 warning-type breakdown, flag-flip test, Fisher tests |
| `v2graph_cl01{38,48}.json`, `census_sprint440_subset_cl0148.json` | §3: census, graph quality, reproduction of Sprint 4.4.0 |
| `v2attr_cl01{38,48}.json` | §4.3: per-scenario V2/V3 × learned/oracle outcomes (identical across versions) |
| `v2poppag_cl01{38,48}.json`, `popceiling_cl01{38,48}.json`, `toy.json` | §3.4, §4.3 control, §2 |
| `interv_cl01{38,48}.json`, `interv_rows_cl01{38,48}.json`, `placebo_cl01{38,48}.json` | §5.2 |

## 10. What this workstream did **not** establish

* Live behaviour of any of the above (no `tc netem`, no Prometheus telemetry, no live FCI).
* Why finite-sample orientation fails (power vs autocorrelation vs non-Gaussianity). Untested.
* Whether a time-series-aware discovery algorithm (PCMCI, tsFCI, LPCMCI) or a larger window would change §3 or §4. Untested.
* Held-out behaviour of the learned-PAG pipeline: the sealed split was not opened here (the Sprint 7 / WS1 report covers V3 on it).
* Any inference about confounded *real* incidents: in the legacy harness the flag is inert in the data, and in `rift_v2` the confounding structures are simulated latent variables.
res are simulated latent variables.
