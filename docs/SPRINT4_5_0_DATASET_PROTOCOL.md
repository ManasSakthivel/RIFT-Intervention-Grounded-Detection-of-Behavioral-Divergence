# Sprint 4.5.0 — Confirmatory Dataset Protocol

**Status: PROPOSED (revised in Sprint 4.5.1, fixed-strata design). No confirmatory data exist, no generator code has been written, and no confirmatory seed has been drawn.** Binding only when recorded under [`SPRINT4_5_0_PREREGISTRATION.md`](SPRINT4_5_0_PREREGISTRATION.md) (PRE) §13.
All figures from existing data are dev/val (N = 252) and **non-confirmatory**. Figures labelled "prototype" come from `scripts/sprint451_dataset_protocol_checks.py` run on **pilot-range indices** (never confirmatory indices, never any RIFT method); artefacts are in `artifacts/sprint4_5_1/dataset/`.

**Hard rules for this protocol**
1. `datasets/rift_v2/heldout_candidate.json`, `heldout_status.json` and `artifacts/sprint4_3_0/results/held_out/` are never opened, read, loaded through `HeldOutGuard`/`load_v2`, or regenerated, and no quantity derived from their *content* (seeds, hashes, dynamics, labels, per-scenario topology) is computed or compared at any stage by anyone running Phase B. (An optional owner-only custodian check is described in §8.4 and is not part of the default procedure. The approved Sprint 4.4.2 `verify_freeze()` hashes the file inside a registered protected test; that is a different, owner-run procedure.)
2. No frozen file is edited, including `generator_v2.py` and `simulator.py`.
3. Ground-truth labels are computed from simulator state only, never from a method output.
4. No method (V3, V2 or baseline) is run on any scenario produced by the new generator before the dataset is hashed and recorded (§9). Pilot-tag scenarios are never scored by any RIFT method.

---

## 1. Independence requirements and the three-level hierarchy

### 1.1 Hierarchy (Sprint 4.5.1 decision 1)
| level | name | definition | count (target) |
|---|---|---|---|
| 1 | **Structure** | one of 16 **fixed** causal-graph motifs S01–S16 (§3). A fixed experimental stratum, not a random draw from a population of structures. | 16 |
| 2 | **Scenario group** | a **generator-assigned template**: `template_id` = structure \| fault family. A within-structure cluster. | 256 (16 per structure), 5–9 scenarios each |
| 3 | **Scenario** | one simulated incident (the unit of scoring; one row per method) | 2000 |

The claim is restricted to the 16 motifs crossed with the 16 fixed fault families. **256 groups are not 256 independent structural clusters**: groups are nested in 16 structures and crossed with 16 fault families, and no effective sample size is claimed (SAP §6). The estimand and the stratified estimator are in SAP §1 and §3.

### 1.2 Independence from protected sets
The confirmatory dataset ("CONFIRM") must be independent of every dataset that informed V3 or its evaluation:

| protected set | status | how independence is established |
|---|---|---|
| Sprint 4.3.0 dev (180) | readable | full `verify_independence` (§8.1) |
| Sprint 4.3.0 val (72) | readable | full `verify_independence` (§8.1) |
| Sprint 4.4.0 adversarial dev (`datasets/rift_v3_dev/adversarial_dev.json`) | readable | full `verify_independence` (§8.1) |
| Sprint 4.3.0 **held-out** (108) | sealed, already opened once for Sprint 4.3.0 (`heldout_opened.json`, 2026-11-03T04:06:00Z) | **exclusion by construction** (§8.2); never read |
| Phase A data (CID reliability) | separate namespace | disjoint seed tag, disjoint generator, no shared files |

"Independent" means: no shared scenario id, seed, content hash, dynamics hash, topology hash, template id, joint design cell, no union-find group (template-or-topology component) spanning CONFIRM and any protected set, and no cross-set near-duplicate (spec similarity ≥ 0.90). It does not mean merely a different random seed.

---

## 2. Why the frozen generator cannot be reused (verified)

Running the frozen code shows (no data were read):

* `generator_v2.py`: 11 structures × 16 families = **176 templates** (`template_id = structure|family`). `cell_split` assigns all 176: **dev 75, val 30, held-out 71, unassigned 0.**
* `build_scenario("confirm", …)` raises `KeyError: 'confirm'` because `_SIZE_BAND`, `SPLIT_PREFIX` and `_derive_seed`'s lookups only know `dev`, `val`, `held_out`.
* Using an existing split label would reproduce an existing seed namespace (seed = `sha256("rift-scenario-gen/2.0.0|<split>|<idx>")`); using any of the 176 templates would break template-disjointness with at least one of the protected sets, including the sealed one.

So the prior plan ("reuse the frozen generator with a new split label") is infeasible without editing a frozen file. Two routes remain:

| route | description | verdict |
|---|---|---|
| **A (recommended)** | a **new** module `src/rift/scenarios/generator_confirm.py` that imports the frozen `simulator.py` and the frozen `compute_ground_truth` unchanged, and defines **new structures** (§3), a new seed tag, a new size/periphery scheme and a node-order randomisation (§3.5) | satisfies every criterion in §1.2 by construction; costs new code, which must be validated (§7) |
| B | reuse existing templates with new topology sizes/parameters | fails template-disjointness against dev, val and the sealed set; rejected |

Decision D6 (PRE §14).

---

## 3. New scenario structures (Route A)

### 3.1 Structure set
16 **new structure kinds**, none of which is among the frozen 11 (`linear_chain, branching, converging, multiple_upstream, diamond, parallel_independent, shared_dependency, confounding, hidden_common_cause, ambiguous, feedback_like`). Each is a *motif* plus a random periphery (§3.2). Families are the frozen 16 (labels `latency_degradation` … `recovery_instability`), crossed with the new structures to give **16 × 16 = 256 new templates**. The motif definitions below are the ones implemented in the prototype (`MOTIFS` in `scripts/sprint451_dataset_protocol_checks.py`); the names S07 and S13 differ from the Sprint 4.5.0 draft (`hub_with_feeders`, `mutual_pair_chain`) because the Sprint 4.5.1 adversarial review showed those two draft motifs were isomorphic to frozen design-space skeletons (`converging`/extra 1 and `ambiguous`/extra 1–4).

| id | structure | motif (observed nodes unless marked [H] hidden) | roots | label route |
|---|---|---|---|---|
| S01 | `spine_with_leaves` | r→a→b→c, leaves off a and b | r | by state |
| S02 | `two_level_fanout` | r→{a,b,c}, each →one grandchild | r | by state |
| S03 | `ladder` | two parallel chains r→a→b and p→c→d with rungs a→c, b→d | r | by state |
| S04 | `double_diamond` | r→{a,b}→d→{e,f}→g | r | by state |
| S05 | `late_merge` | r→a→m, p→q→m, m→d (merge after two hops) | r | by state |
| S06 | `bypass_chain` | r→a→b→c plus shortcut r→c | r | by state |
| S07 | `two_stage_hub` | f1,f2→h1→h2, f3→h2, h2→d; root f1 | f1 | by state |
| S08 | `triangle_with_tail` | r→a, r→b, a→b, b→c | r | by state |
| S09 | `staggered_roots` | r1→a→b, r2→b→c, both faulted at different onsets | r1,r2 | by state |
| S10 | `latent_confounded_diamond` | [H]h→{r,c}, r→a→c, r→b→c | r | by state |
| S11 | `hidden_driver_chain` | [H]h→x→y, h→z | h (unobserved) | ROOT_UNOBSERVED |
| S12 | `hidden_driver_diamond` | [H]h→{a,b}, a→c, b→c | h (unobserved) | ROOT_UNOBSERVED |
| S13 | `mutual_pair_merge` | a⇄b→c, p→c, c→d | a | SYMMETRIC_MUTUAL_DEPENDENCY |
| S14 | `mutual_pair_fanout` | a⇄b, b→{c,d} | a | SYMMETRIC_MUTUAL_DEPENDENCY |
| S15 | `sink_with_two_chains` | r→a→s, p→q→s | r | by state |
| S16 | `pendant_cluster` | r→a→b, a→c, b→c, c→d | r | by state |

**Novel versus variant (preregistered table, requirement for the report).** "Structures V3 was not tuned on" is *not* claimed: S10–S14 are variants of categories (confounding, hidden cause, mutual dependency) that V3 has components for. The accurate statement is "motifs not present in the dev/val/held-out generators". The report must include a table classifying each motif as **novel topology** (no frozen skeleton is isomorphic, T5) or **variant of a frozen category** with the frozen category named. The study is a **designed stress set**, not a deployment estimate.

### 3.2 Per-scenario randomisation (so topologies are not shared)
Each scenario draws, from its own seed, a periphery of 0–3 extra observed nodes attached by an edge from a random non-root node and optionally a second edge to a random later node (acyclic), then the same edge-gain/lag/sigma/fault/telemetry/intervention draws as `build_scenario` with the same distributions. Total nodes (hidden included) ≤ 12 (FCI cap is 15). The purpose is topological diversity, but the design space is finite: the prototype's natural geometry over 6000 candidates has only **2,344 distinct topology hashes**, so topology uniqueness cannot come from the periphery alone and is enforced by acceptance rules (§6.2).

### 3.3 Label route (no frozen code edited)
Ground truth is computed by calling the frozen `generator_v2.compute_ground_truth` on the new scenario. That function reads only `sc["design"]`, the graph/telemetry/intervention state, and one structure name: `dims["structure"] == "ambiguous"` triggers SYMMETRIC_MUTUAL_DEPENDENCY. The new module therefore passes a **shallow copy** whose `dimensions.structure` is replaced by `"ambiguous"` **only** for S13 and S14, and by its own name otherwise. The stored scenario keeps its true structure name. This is a thin wrapper, declared and unit-tested (§7), not a modification. It requires independent review (D7). The frozen validators reject new structure names as "outside domain" on raw scenarios; validation therefore runs on a *validation view* (structure name mapped to a frozen name) and the mapping is part of the reviewed code.

### 3.4 What is "new" and what is not (stated honestly)
New: structure motifs, periphery, seed tag, template ids, topology hashes, per-scenario instance parameters, node order. **Not new:** the simulator physics, the family amplitude table, the temporal/workload/observability/intervention/negative level sets, the label function. CONFIRM therefore measures behaviour on new causal graphs under the same simulated physics and the same labelling rule. It does not test a different generative mechanism. This is limitation L3 in PRE §12; the circularity of the label function with V3's own thresholds is L2.

### 3.5 Node-order randomisation (Sprint 4.5.1 finding G)
The frozen generator appends root(s) first (`generator_v2._build_topology`) and only the *name pool* is shuffled. On dev+val the first true root is the first element of `graph.nodes` and of `observe()["metrics"]` in 99/99 attributable scenarios with an observed root (chance ≈ 0.16). This is a **generation artefact: an accidental label proxy available to any order-dependent method**. Frozen V3 is empirically order-invariant (0/252 outputs changed under 3 random permutations each); the order-dependent baseline B0-EARLIEST changed in 35/252; V2 was **not tested**. The prototype motif builder reproduces the pattern (root first in 489/489). Requirement: the new generator must apply a node-order permutation, drawn from the scenario seed independently of node role, to `graph.nodes`, to the telemetry/metrics dictionary order and to `edges`; test T10 (§7) verifies it. This is a property of the *new* generator and touches no frozen code.

---

## 4. Seeds and provenance of randomness
* **Generator tag:** `rift-confirm-gen/1.0.0`. Scenario seed for index i ∈ {1…M}: `int(sha256(f"rift-confirm-gen/1.0.0|confirm|{i}").hexdigest()[:8], 16) & 0x7FFFFFFF`. The tag is different from every tag used so far (`rift-scenario-gen/2.0.0`, Phase A `rift-cid-reliability/1.0.0`, audit seeds 450/4502/4505). Pilot (QC-only) tag: `…|pilot|i`. Validation tag for the replication test (§7): the **frozen** tag with `dev`/`val`, which is the point of that test.
* **Scenario id:** prefix `V3C-` followed by an opaque running number. The id must **not contain the structure token or any label-bearing string** (a structure token in the id would leak the label route to a method that sees the id).
* **Candidate draw order:** candidates are produced in index order 1, 2, 3, …; the sequence is fixed and cannot be edited or skipped; the acceptance rules (§5.2, §6.2) accept or reject each candidate using only state-derived labels and design keys. The accepted set is the first accepted candidates that fill the quotas. The index of every rejected candidate and its rejection reason are logged. No candidate is chosen by looking at anything a method does.
* **Cross-tag collisions.** A 31-bit seed collision with any other set is possible in principle (about 2000 × 252 / 2³¹ ≈ 2 × 10⁻⁴ against dev/val/adversarial, and negligible against the 108 sealed seeds). No sealed seed value is computed; collision against readable sets is checked explicitly (§8.1), and a colliding candidate is skipped and logged.
* **Pre-commitment.** The tag, quota matrix (§5.2), design cell lists and acceptance rules are fixed in the preregistration hash (PRE §13) before the first candidate is drawn.

---

## 5. Design: size, balance and strata

### 5.1 Size and what it rests on
**N = 2000** scenarios (proposed; decision D4), **K = 256 groups** (16 structures × 16 templates; gate K ≥ 250), 5–9 scenarios per group, maximum group size 14 as a gate. Derivation and its limits: SAP §6 (power is adequate only if within-group and family-level dependence are moderate; it cannot be raised by increasing N beyond what 16 structures × 16 families allow). N = 800 gives 54% power at the planning design effect under the normal approximation and is not used. The binding constraint on N is generation quality control, not computation (V3-FULL averaged 0.067 s per scenario on dev and 0.105 s on val, per `artifacts/sprint4_4_0/analysis.json`).

### 5.2 Quota matrix (fixed; enforced by acceptance sampling on state-derived labels)
Labels are the expected outcome (ATTRIBUTE) or the abstain reason. Not every structure can supply every label: S11/S12 give only ROOT_UNOBSERVED (plus a small NO_FAULT share) and S13/S14 only SYMMETRIC_MUTUAL_DEPENDENCY (the label is a function of the wrapper, §3.3). The matrix below makes the structure totals, the label totals and N mutually consistent:

| structures | ATTRIBUTE | WEAK_SIGNAL | INSUFFICIENT_BASELINE | NO_DISCRIMINATING_EVIDENCE | NO_FAULT | ROOT_UNOBSERVED | SYMMETRIC | row total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S01–S08 (8 structures, each) | 67 | 30 | 15 | 12 | 8 or 7 | — | — | 132 or 131 |
| S09, S10, S15, S16 (4 structures, each) | 66 | 30 | 15 | 11 | 8 or 7 | — | — | 130 or 129 |
| S11, S12 (each) | — | — | — | — | 5 | 120 | — | 125 |
| S13, S14 (each) | — | — | — | — | — | — | 90 | 90 |
| **column total (all 16)** | **800** | **360** | **180** | **140** | **100** | **240** | **180** | **2000** |

The explicit per-structure integers are produced by `quota_matrix()` in the prototype script (ATTRIBUTE 67 for the first 8 attributable-capable structures and 66 for the remaining four; NO_DISCRIMINATING_EVIDENCE 12 or 11; NO_FAULT 8 or 7 alternating along the list S01–S08, S09, S10, S15, S16; row sums 129–132; recomputed and verified to sum to 2000 with the column totals above). **The per-structure target is therefore "≈ 125–132, except S13/S14 at 90 (declared exception)"; the earlier criterion "125 ± 15 for every structure" is withdrawn because it contradicted the 180 SYMMETRIC quota** (the 180 SYMMETRIC scenarios can only come from S13 + S14 = 2 × 90). Per fault family the target is ≈ 125 (each template receives floor or ceil of its structure's row total ÷ 16); it is reported, not gated.

| stratum (label totals) | quota | basis |
|---|---:|---|
| expected outcome ATTRIBUTE | 800 (40.0%) | dev/val π = 0.393 (dev 0.378, val 0.431); PRE §3.2 |
| ABSTAIN_REQUIRED, `WEAK_SIGNAL` | 360 | dev/val share 46/153 = 30% of abstentions |
| ABSTAIN_REQUIRED, `ROOT_UNOBSERVED` | 240 | 31/153 = 20% |
| ABSTAIN_REQUIRED, `SYMMETRIC_MUTUAL_DEPENDENCY` | 180 | 22/153 = 14% |
| ABSTAIN_REQUIRED, `INSUFFICIENT_BASELINE` | 180 | 23/153 = 15% |
| ABSTAIN_REQUIRED, `NO_DISCRIMINATING_EVIDENCE` | 140 | 18/153 = 12% |
| ABSTAIN_REQUIRED, `NO_FAULT` | 100 | 13/153 = 8.5% |
| **total** | **2000** | |

Quotas follow the dev/val mix so that results are comparable, but they are a design choice, not an estimate of any real prevalence (PRE §3.2). Reachability (prototype, 6000 natural candidates): natural label shares ATTRIBUTE 0.367, WEAK_SIGNAL 0.1635, ROOT_UNOBSERVED 0.138, SYMMETRIC 0.137, INSUFFICIENT_BASELINE 0.090, NO_DISCRIMINATING_EVIDENCE 0.059, NO_FAULT 0.045; every quota is reachable with a ratio ≥ 5× within 12,000 candidates. Caveat: `partial_degradation` has a natural ATTRIBUTE share of only 0.059, so ATTRIBUTE scenarios with that family are scarce (7–13 in the simulation) and the corresponding templates are mostly abstention scenarios; 69–72 of the 256 templates carry zero ATTRIBUTE scenarios (all of S11–S14 plus a few others).

**Shortfall rule.** If a cell cannot be filled within the per-structure budget (§6.2), the attempt fails design QC (§9.2) unless the total shortfall is ≤ 10 scenarios (N ≥ 1990), in which case it is recorded and the realised N, n_s and weights are used (SAP §1). The quota matrix itself is not changed to suit what the generator produces without an amendment recorded before any method run (D15). In the prototype's four simulated attempts the shortfall was 0–1 scenario.

### 5.3 Temporal-confound stratum (serves the second clause of the primary question)
For each scenario the generator stores `design.drift_stat` = max over observed services y that have at least one observed **non-ancestor** x ≠ y of |d(y)| / σ_y, where d(y) is the noise-free change in `fault_series` at y between the baseline (30 s) and post (30 s) windows of the do() procedure. **Ancestry is evaluated on the full true graph including hidden nodes**, as in `scripts/sprint440_cid_audit.py`; a service y with no observed non-ancestor x is skipped, and a scenario with no eligible y gets stratum "none" and a flag. Strata: **none** < 0.1σ, **mild** 0.1–0.3σ, **substantial** ≥ 0.3σ.
**Prevalence, stated correctly.** In dev/val, 52 of 252 scenarios (20.6%; 37/180 and 15/72) are in the substantial stratum. The drift statistic is a near-deterministic function of the fault shape (intermittent and oscillation shapes are substantial in about 99% of cases, multi-onset in about 11%), so a **drift sub-quota is infeasible** without distorting the family mix. The target is therefore the *natural* share of **≥ 25%** (the prototype gave 26–28%): a modest +4 percentage points over dev/val, not a major expansion, giving about 500 scenarios. The earlier remark that "only 17 non-ancestral pairs per split had |drift| > 0.3σ" refers to **pairs** of a different (pair-level) analysis, not to scenarios, and is retained only as context for D22. The stored statistic is a label field (inside `design`), stripped before methods run.
Stratum contrasts are descriptive (SAP §8.2): with n ≈ 500 and a design effect of 2 the power for a contrast is about 0.37.

### 5.4 Factor levels
The temporal (11), workload (10), observability (9), intervention (9) and negative (11) level sets and the cycling scheme (`_cyc`) of `generate_split` are reused so every level occurs in all strata; one in four scenarios carries a negative kind. Allocation of cells to scenario indices is a function of the pre-committed master order, not of any outcome.

### 5.5 SNR boundary band (decision D20)
The label rule requires SNR ≥ 4 for ATTRIBUTE, whereas V3 acts on a 3σ boundary. For SNR in [3, 4) (n_do = 30) 0% of scenarios are labelled ATTRIBUTE but V3 answers 37% of them, with mean U −0.87; WEAK_SIGNAL contributes −0.166 of V3's −0.338 on dev/val (49%). Whether to exclude the SNR [3, 5) band at generation is a researcher decision; the **default is to report it as a stratum and not exclude it** (excluding it would be a design choice favouring V3).

---

## 6. Clustering unit and group geometry

### 6.1 Unit
**Group = template** (`template_id` = structure | family), generator-assigned, nested in a structure. Under the acceptance rules in §6.2 the union-find component over (template, topology hash) equals the template, so the scenario-group unit and the union-find group coincide for CONFIRM (verified by the prototype: 256 templates = 256 union-find groups).

### 6.2 Natural geometry fails; acceptance rules fix it
Without any rule (prototype, 6000 candidates) the union-find groups collapse to **7 groups** (maximum size 2,505) because topology hashes are shared across templates; there are only 2,344 distinct topology hashes; topology-only groups reach 132 scenarios per hash; in the first 2000 candidates there are 11 groups, maximum 363, unique-topology share 0.396. The Sprint 4.5.0 gate ("K ≥ 250, max ≤ 25, ≥ 90% unique topologies, no topology shared by > 3") could not have been met and contradicted the finite design space. It is replaced by the following **acceptance rules**, applied in candidate order using design keys only:

| rule | statement |
|---|---|
| R-CAP1 | at most **one** accepted scenario per topology hash |
| R-OWN | a topology hash already owned by a different template is rejected (topologies are owned by their first template) |
| R-NOVEL | reject a candidate whose topology/content/dynamics hash equals a hash derivable from the frozen design space or any readable protected set |
| R-DUP | reject exact duplicates within CONFIRM (content or dynamics hash; readable-spec near duplicate above the proxy threshold) |
| template_full | each template accepts at most its share of the structure's row total |
| cell_full | each (structure, label) cell accepts at most its quota |

Budget: 10,000 candidates per structure. Prototype (4 simulated attempts, offsets 0–3): accepted 1999 / 1999 / 2000 / 2000; 256 templates = 256 groups; **group size 5–9 (maximum 9)**; unique-topology share **1.0**; maximum scenarios per topology 1; about 98 s per attempt. Rejections in attempt 0: cell_full or label-not-in-quota 145,659; template_full 8,762; R-OWN 3,267; R-CAP1 171; R-NOVEL 126; R-DUP-within-set 15; R-DUP-readable 1. The rejection volume is large because rare labels (NO_FAULT, NO_DISCRIMINATING_EVIDENCE, `partial_degradation` ATTRIBUTE) are scarce, not because the rules are strict. Without R-OWN the geometry collapses (cap 3, no ownership: 10 groups, max 908); cap 3 with ownership at a budget of 3000 gives 256 groups, maximum 9, unique share 0.887.

### 6.3 Geometry gates (QC §9.2)
K = 256 groups (K ≥ 250); **maximum group size ≤ 14** (prototype 9); unique-topology share ≥ 0.99; maximum scenarios per topology hash = 1; every structure has 16 groups; no union-find group spans CONFIRM and any protected set. The earlier gate values (maximum group 25, ≥ 90% unique, ≤ 3 per topology) are withdrawn. **Dependence is not removed by these gates:** template-level and fault-family-level dependence remain possible and are handled in SAP §3 and §3.1. The realised ICC and DEFF are reported (SAP §8.5).

---

## 7. Validation of the new generator (before any confirmatory draw)
All tests use the **pilot tag** or the **frozen dev/val data**, never held-out, and no RIFT method (T10 part 2 runs methods on dev/val only).

| id | test | pass criterion |
|---|---|---|
| T1 | **Replication.** Run the new builder in "legacy registry" mode (old 11 structures, old size bands, frozen tag) for ≥ 100 dev + 50 val specs from `datasets/rift_v2/{dev,val}.json`. | `content_hash` identical for every replicated scenario (and identical labels). The prototype's frozen builder reproduced the stored dev/val content hashes 90/90. |
| T2 | **Label wrapper.** Constructed S13/S14 and non-mutual cases | S13/S14 → SYMMETRIC; S11/S12 → ROOT_UNOBSERVED; others by state |
| T3 | **Schema.** Every key emitted by `build_scenario` is present with the same type | all 100% |
| T4 | **Determinism.** Generate 200 pilot scenarios twice | byte-identical |
| T5 | **Non-isomorphism library (design space).** For each of the 16 motifs **as defined in §3.1** and every possible periphery, skeleton graphs (hidden flag only) must not be isomorphic to any skeleton produced by the frozen `_build_topology` for each of the 11 old kinds with extra ∈ {0,…,4}, including the frozen decoy and ambiguous-PAG augmentations. The library is the *design space of the frozen generator*, not any held-out scenario. Peripheries that coincide with a frozen skeleton are rejected operationally by R-NOVEL (the prototype found 148 overlapping scenario hashes, 25 distinct, concentrated in S09, S13, S07, S05). | zero isomorphic **motif cores**; peripheries handled by R-NOVEL; **T5 must be re-run on the final definitions** because the Sprint 4.5.0 versions of S07/S13 failed |
| T6 | **Quota feasibility.** Pilot-tag run of 6,000 candidates under the acceptance rules | every cell of the §5.2 matrix reachable within the per-structure budget; geometry gates of §6.3 met |
| T7 | **Independence dry run.** Pilot set vs dev/val/adversarial through `verify_independence` on a validation view | zero shared content, dynamics, template or joint-cell keys; zero confirm-spanning groups; zero near-duplicates ≥ 0.90 (prototype: 1992 simulated scenarios, all zero) |
| T8 | **Leakage / interface test.** `strip_labels` removes only `ground_truth` and `design`; it leaves `faults`, `dimensions`, `graph` and `template_id`. T8 therefore tests the **method-facing interface**: the signature `run_v3(o, iv, fid, seed, …)`, the key set of `observe()` and the closure outputs, and that scenario ids start with `V3C-` and contain no structure token. Poisoning every label field leaves `observe()` outputs and method outputs byte-identical (prototype: 40/40 dev scenarios). | no label-bearing key or string reaches a method; a test that merely checks absence of `ground_truth`/`design` is **insufficient** |
| T9 | **Independent code review** of the generator, wrapper and acceptance sampler by a second person, with a written checklist | signed (D7; unresolved until a named reviewer exists) |
| T10 | **Node-order test (new).** Part 1: for all accepted pilot scenarios with an observed root, the position of the first true root in `graph.nodes` and in the observed metrics dict is uniform (chi-square test, α = 0.01, and a permutation test). Part 2: on dev/val (and the pilot tag, no confirmatory data) permute node order three times per scenario and compare method outputs; any change in V3-FULL, V2 or a baseline is reported (V2 was not tested in Sprint 4.5.1). | Part 1 passes; Part 2 report filed before generation (informational for baselines; a change in V3 would mean a frozen-code order dependence and is reported, not fixed) |

T1 is what makes the new module trustworthy: if it cannot reproduce the frozen scenarios exactly, the new generator is not accepted.

---

## 8. Verifying independence without exposing protected scenarios

### 8.1 Readable protected sets (dev, val, adversarial dev)
Run `independence.verify_independence({"dev": dev, "val": val, "adv": adv, "confirm": confirm_stripped}, protected="confirm")` on **label-stripped, validation-view** records. Required: for each of `content_hash`, `dynamics_hash`, `topology_hash`, `template_id`, `joint_cell` zero shared keys between CONFIRM and every other set; zero near-duplicate pairs ≥ 0.90; zero group-integrity violations (no union-find group spans CONFIRM and another set); zero shared scenario ids; zero shared seeds. Report the maximum cross-set `spec_similarity` and its distribution (informs §8.3). The global `verify_independence` returns not-OK on the existing baseline for reasons unrelated to CONFIRM (violations already present among dev/val/adversarial); the required condition is on CONFIRM's pairs only.

### 8.2 Sealed held-out: exclusion by construction (default)
The held-out file is not read. Independence is established by facts about the **construction**, each checked with code that touches no held-out content:

| criterion | argument and check |
|---|---|
| scenario id | prefix `V2H-` (held-out) vs CONFIRM prefix `V3C-`; prefix check |
| seed | different tag; collision probability ~10⁻⁴ (§4). No sealed seed is computed. |
| template id | CONFIRM structure names ∩ frozen `STRUCTURES` = ∅, hence template ids disjoint from all 176, including the 71 assigned to held-out by the **public** rule in `cell_split` |
| joint cell | contains `structure`; disjoint for the same reason |
| topology hash | T5 plus R-NOVEL: no CONFIRM skeleton equals any skeleton the frozen generator can produce; the library covers extra ∈ {0,…,4}, a superset of the sealed set's band (extra = 3). No per-scenario sealed information is computed. |
| dynamics hash | includes the workload graph hash, so differs when the graph differs; additionally checked against dev/val |
| content hash | includes structure name and graph; collision negligible |
| near duplicates | spec similarity has a categorical component (structure, family, …) and a numeric component. A different structure caps the categorical part at 6/7 · 0.6 = 0.514 and requires the numeric part ≥ 0.965 to reach 0.90. Not checkable directly; proxied by §8.1 (max similarity to dev/val, required ≤ 0.88). |

**Limitation.** Near-duplicate and dynamics-hash independence from the sealed set are argued and proxied, not measured. This is stated in the final report. The sealed set has already been opened once and is not part of any hypothesis test here.

### 8.3 Proxy threshold
If the maximum cross-set similarity of CONFIRM to the readable sets exceeds **0.88**, the dataset fails QC (attempt limit D15). **Caution from the prototype:** the maximum cross-set specification similarity among the first 2000 *candidates* was 0.8997 with 3 pairs ≥ 0.88, so the proxy can fail on raw candidates; the R-DUP-readable rule rejects such candidates before acceptance, and the threshold applies to the **accepted** set. The threshold (D18) is a heuristic proxy, not a measured quantity.

### 8.4 Optional custodian check (owner decision D8; not recommended as default)
The owner could, on their own machine, run a script that reads the sealed file and CONFIRM's key hashes and prints **integer counts only**. This reads sealed content, albeit locally and never displayed, and would be a second opening of a file whose seal is the project's central safeguard. It is not part of the default procedure. If the owner chooses it, the script and its output format (counts only) are hashed in advance and the researcher never receives anything except the counts.

### 8.5 Topology and group geometry gates
Computed on CONFIRM alone: the gates of §6.3. These need no protected data.

---

## 9. Generation and run sequence

### 9.1 Before generation
1. Researcher approvals (PRE §14).
2. Generator, wrapper, acceptance sampler, **confirmatory runner `scripts/sprint450_run_confirm.py`**, analysis script, quota matrix, report template and interpretation function are written, tested (§7; the runner only on dev/val and the pilot tag) and hashed. Tests T1–T10 pass.
3. PRE, SAP, this protocol, the CID design and the audit are hashed together with the freeze manifests and the generator/runner/analysis hashes; the timestamp is recorded (PRE §13).
4. Freeze verification run (SAP §12) and the seal check, owner-run, with output stored.
5. *Execution smoke test* (D17, **recommend dropping**): at most 20 pilot-tag scenarios through the V3 runner to confirm it executes; only exit status and output schema examined; output discarded. Because it runs a method on generator output and adds a forking path, the recommended default is to skip it and rely on the dev/val and pilot-tag tests of the runner (which examine no confirmatory-generator output).

### 9.2 Generation
1. Generate CONFIRM once with the committed tag and rules; write to a temporary file; **do not run any method**.
2. QC gates (all automatic, labels used only for quota/consistency): schema (T3), quota matrix (§5.2), drift-stratum natural share ≥ 25% (§5.3, reported against target, not a hard gate), group geometry (§6.3), independence (§8.1–8.3), node-order uniformity (T10), determinism (re-generate and compare byte-for-byte), validators on the validation view, node-count cap, finite values, unique ids/content hashes.
3. If QC fails: the attempt is logged with the reason, the **dataset hash, the code diff and a reviewer sign-off per attempt**; code may be corrected **only for defects unrelated to any method outcome** (none has been seen); **quotas, motifs and rules may not be changed between attempts**; re-generate. At most **3 attempts** (D15). If the third fails, the sprint stops and the failure is reported.
4. If QC passes: compute SHA-256 of the labelled file and of the label-stripped file; write `artifacts/sprint4_5_0/confirm/provenance.json`: generator, wrapper, simulator, labeler, runner and independence-code hashes; git commit; Python and package versions; tag; first and last accepted candidate indices; counts of rejected candidates by reason; quota fill table; drift-stratum counts; group-geometry statistics; independence report; QC results; timestamp; the operator.
5. Append-only ledger row. Only then may methods run.

### 9.3 Running
The preregistered, hashed runner receives `strip_labels(sc)` plus `observe`/`intervene`; all methods use identical observed windows and seeds (`do-seed` and CID seed rules in PRE §2.5). One run per method. Error semantics are those of SAP §7 (exception or timeout ⇒ abstention with `error_flag = 1`, n_do consumed counted). Seal verification repeats after the run.

### 9.4 After the run
Scoring uses the labelled file (hash must match the recorded one). Results are written once; the analysis script produces the report (SAP). Re-runs only for infrastructure failure, logged. "First complete run" means all methods × all scenarios have a record (error rows are records).

---

## 10. What the dataset cannot show
* Anything about real systems or real telemetry.
* Performance on structures outside the 16 motifs and their periphery, or fault families outside the frozen 16.
* A deployment estimate: the quota mix is a designed stress set.
* Performance under a different labelling rule or a different physics; the label function mirrors V3's own R1 rule and the CID power criterion (limitation L2).
* Independence from the sealed set beyond the construction-based argument in §8.2.

## 11. Decisions for the researcher (dataset)
| id | decision |
|---|---|
| D6 | Route A (new generator module) approved |
| D7 | Independent reviewer for generator/wrapper/acceptance sampler (T9) |
| D8 | Held-out independence by construction (default) vs optional custodian count check |
| D3 | Quota matrix in §5.2 (40% ATTRIBUTE; abstain-reason mix; S13/S14 at 90 as a declared exception; natural drift target ≥ 25%; shortfall ≤ 10) |
| D4 | N = 2000, K = 256 groups (gate K ≥ 250) |
| D15 | Up to 3 generation attempts, all logged with dataset hash, code diff and reviewer sign-off; quotas and motifs frozen across attempts |
| D17 | Execution smoke test on ≤ 20 pilot-tag scenarios — **recommended to drop** |
| D18 | Structure set S01–S16 (names and motifs as in §3.1) and the 0.88 similarity proxy threshold |
| D20 | SNR [3, 5) band: report as a stratum (default) vs exclude at generation |
