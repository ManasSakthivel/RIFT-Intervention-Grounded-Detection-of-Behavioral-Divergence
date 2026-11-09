# Sprint 4.3.0 — Scenario Diversity Report

> Machine-rendered tables: every table below is produced by `python3 scripts/sprint430_build_docs.py` from
> `datasets/rift_v2/{dev,val,heldout_candidate}.json`, `datasets/rift_v2/manifest.json` and
> `datasets/rift_v2/independence_report.json`. Prose numbers are copied from the same artifacts.
> All scenarios are **synthetic ground-truth scenarios**; nothing here is evidence about live systems.

## 1. What was built

A new factorial scenario corpus (`rift-scenario-gen/2.0.0`, `src/rift/scenarios/generator_v2.py`) of **360 scenarios**
in three splits:

| Split | Role | Scenarios | Protocol target | Target met |
|---|---|---|---|---|
| dev | implementation and defect finding | 180 | >= 150 | yes |
| val | protocol refinement / sanity checks | 72 | >= 60 | yes |
| held-out | one-time post-freeze evaluation | 108 | >= 90 | yes |
| **total** | | **360** | >= 300 | yes |

{{TABLE:corpus_table}}

The legacy corpus (`datasets/rift_faults/*`, 83 records) is **not** used for any v2 claim. The provenance audit
(`docs/SPRINT4_3_0_DATASET_PROVENANCE_AUDIT.md`) found that the 83 legacy records contain only 25 distinct contents, 22 distinct
dynamics, 13 distinct structures and 17 templates, that all 15 legacy held-out scenarios have a twin in dev or val, and that
11 groups are seed-only variants. That is why a new corpus was generated rather than re-splitting the old one.

## 2. Generation methodology

1. **Factorial design.** 16 fault families x 11 causal structures x 11 temporal patterns x 10 workloads x 9 observability
   conditions x 9 intervention modes x 11 negative kinds (plus "no negative"). Each scenario fixes one level per dimension; the
   full cross-product is not enumerated (that would be far more than 360). Levels within a split are assigned by cycling through
   seeded random permutations of each dimension's levels (`_cyc`), so marginals inside a split are near-balanced by construction.
2. **Split by design cell.** The unit that may not straddle splits is the *template* = (causal structure, fault family):
   `cell_split(structure, family) = dev if (si + 2*fi) mod 10 < 5, val if < 7, else held-out`. `feedback_like` structures and
   the `recovery_instability` family are forced to held-out (distribution shift).
3. **Topology.** Topologies are built per structure kind with disjoint size bands per split (dev: +0/1 extra nodes, val: +2,
   held-out: +3). The size band is a generation mechanism, **not** accepted as evidence of independence.
4. **Seeds.** `seed = sha256(generator_version | split | index)`; seeds are never treated as evidence of independence.
5. **Labels by construction, not by any method.** `expected_outcome` and `abstain_reason` are computed from the noise-free
   simulator state (`compute_ground_truth`), using SNR >= 4, >= 8 baseline windows, strict temporal precedence or an analytic
   interventional effect (>= 1.0 sigma) — see `docs/EVALUATION_PROTOCOL_V2.md` Amendment 1 §6 and Amendment 2 §4. The generator
   never looks at any method output; no method was run before the datasets were frozen.
6. **QC (label-independent).** Schema, graph validity, temporal consistency, intervention consistency, ground-truth consistency
   and reproducibility checks (`src/rift/scenarios/validators.py`). **QC failures: 0 in dev, 0 in val, 0 in held-out.** No
   scenario was removed.
7. **Deterministic regeneration.** `python3 scripts/sprint430_generate_datasets.py --check` regenerates all three splits in
   memory and compares them with the stored files (read-only). At finalization all three reported IDENTICAL.

## 3. Outcome mix and fault counts

{{TABLE:outcome_table}}

The ABSTAIN_REQUIRED share is **dominant** (62 % dev, 57 % val, 58 % held-out). That is a deliberate property of a benchmark
built to test abstention, but it has a consequence repeated in the statistical report: a method that never answers scores 63/108
= 0.583 on the held-out P2 metric. WEAK_SIGNAL abstentions are concentrated in the `high_baseline_variance`, `low_load` and
`partial_degradation` cells *by design* (fault amplitudes are absolute, `AMP_K * 8 ms`, so a larger baseline sigma lowers SNR).

## 4. Coverage of each dimension

"Distinct levels" is the number of levels that occur in that split / in the union. Counts are scenarios.

### 4.1 Fault families (16 levels)
{{TABLE:dist_family}}

Held-out contains 16 families, dev and val 15; `recovery_instability` (18 held-out scenarios) exists **only** in held-out.

### 4.2 Causal structures (11 levels)
{{TABLE:dist_structure}}

`feedback_like` (24 held-out scenarios, a three-node feedback loop) exists **only** in held-out. `ambiguous` is present in all
splits. `confounding` and `hidden_common_cause` contain latent/hidden
nodes that never appear in a method's observations.

### 4.3 Temporal patterns (11 levels)
{{TABLE:dist_temporal}}

### 4.4 Workloads (10 levels)
{{TABLE:dist_workload}}

### 4.5 Observability conditions (9 levels)
{{TABLE:dist_observability}}

### 4.6 Intervention modes (9 levels)
{{TABLE:dist_intervention}}

### 4.7 Negative / adversarial kinds (11 named kinds + none = 12 levels)
{{TABLE:dist_negative}}

**90 of 360 scenarios (25 %)** carry a named negative kind; 270 carry none. Per-split named-negative counts are in the table
above. `no_fault_plain` and `high_variance_no_fault` are the no-fault negatives (4+5, 2+2, 2+2): NO_FAULT-labelled scenarios number only **9 / 4 / 4** in dev / val / held-out.
False-positive-rate estimates are therefore very imprecise (held-out FPR = 2/4).

## 5. What is and is not independent across splits

Independence is **verified on content**, not asserted from seeds (`scripts/sprint430_verify_independence.py`,
`datasets/rift_v2/independence_report.json`, verified 2026-11-03T04:02:35Z, before the freeze).

{{TABLE:shared_keys}}

* Cross-split leakage of content hash, effective-dynamics hash, topology hash, template id and joint design cell: **0** for
  every pair.
* Group integrity violations (a union-find group spanning two splits): **0** across **35** groups.
* Cross-split near-duplicate pairs at similarity >= 0.90: **0**.
* Unseen in held-out relative to dev+val: structure `feedback_like`, family `recovery_instability`.
* Within each split every scenario has distinct content and distinct dynamics (180 / 72 / 108). Distinct topology hashes are
  far fewer than scenarios (60 / 26 / 27) and distinct templates are 75 / 30 / 71: **many scenarios share a topology or template
  inside a split**, which is why the statistics use template-clustered bootstrap intervals (71 held-out templates).

### Marginals shared by design

The following dimensions are **not** held out; their levels appear in all three splits:

{{TABLE:marginals}}

So the held-out set tests unseen *structure x family cells*, unseen topologies, an unseen structure kind and an unseen family,
**but not** unseen workloads, observability conditions, temporal patterns or intervention modes. Claims of
"unseen workload/observability/intervention" would be wrong and are not made.

## 6. Simulator assumptions (what the diversity is diversity *of*)

* Linear additive Gaussian-noise model sampled once per window of Delta_t = 10 s with mean 100 ms; faults propagate along simple
  paths with a path gain and window lag. This is a model, not a trace replay.
* The reference period is the first 10 windows (100 s); incident window = [100 s, end]. Normal scenarios have onset >= window 14;
  `insufficient_samples` scenarios deliberately violate this.
* Interventions are **simulated** by the scenario simulator (30 s baseline + 30 s perturbation at 1 Hz). There is no control arm;
  non-stationary faults can create spurious CID. Intervention fidelity is a simulator assumption.
* Recovery time is a fixed **model constant** of 30 s per rollback, not a measurement.
* The call graph given to methods is the true propagation edge set among observed services plus 2-3 decoy dependency edges;
  hidden variables never appear.
* Absolute fault amplitudes (`AMP_K * 8 ms`) with workload-dependent sigma mean that "weak signal" is partly a consequence of the
  workload choice. This is a design coupling, not an independent source of diversity.
* The generator was not tuned after seeing method results (generator and datasets were frozen before the held-out run; see
  the final report).

## 7. Limitations of the diversity claim

* 360 scenarios is a modest corpus; 71 held-out templates is the effective sample size for template-level inference.
* Shared marginals (workload, observability, temporal, intervention) mean no distribution shift on those axes.
* Only 4 NO_FAULT scenarios in held-out and val.
* All graphs are small synthetic graphs (observed nodes per scenario: dev 3-7, val 5-8, held-out 6-11); there is no evidence about large service meshes.
* Diversity is counted in design levels. Level counts are not a measure of realism and do not show that the simulator resembles
  production telemetry.

## 8. Reproducibility

```bash
python3 scripts/sprint430_generate_datasets.py --check     # read-only: regenerate in memory, compare to stored files
python3 scripts/sprint430_verify_independence.py --check   # read-only: recompute independence report, compare to stored
python3 scripts/sprint430_build_docs.py                    # re-render this document's tables
```
