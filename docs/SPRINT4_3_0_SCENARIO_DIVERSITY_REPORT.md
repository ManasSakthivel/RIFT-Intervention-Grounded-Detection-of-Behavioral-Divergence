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

| Split | File | scenarios | bytes | SHA-256 (prefix) | distinct content | distinct dynamics | distinct topology | distinct template | distinct joint cell | QC failures |
|---|---|---|---|---|---|---|---|---|---|---|
| dev | dev.json | 180 | 447520 | a833ad0ca1db0583... | 180 | 180 | 60 | 75 | 180 | 0 |
| val | val.json | 72 | 198802 | e82252b47f29dc13... | 72 | 72 | 26 | 30 | 72 | 0 |
| held-out | heldout_candidate.json | 108 | 314885 | 97b90fa424c3a7c0... | 108 | 108 | 27 | 71 | 108 | 0 |
| **total** |  | 360 |  |  |  |  |  |  |  |  |

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

| Split | n | ATTRIBUTE | ABSTAIN_REQUIRED | WEAK_SIGNAL | ROOT_UNOBSERVED | SYMMETRIC_MUTUAL_DEPENDENCY | INSUFFICIENT_BASELINE | NO_DISCRIMINATING_EVIDENCE | NO_FAULT | #faults 0/1/2/3 |
|---|---|---|---|---|---|---|---|---|---|---|
| dev | 180 | 68 | 112 | 34 | 23 | 15 | 16 | 15 | 9 | 9/123/43/5 |
| val | 72 | 31 | 41 | 12 | 8 | 7 | 7 | 3 | 4 | 4/48/19/1 |
| held-out | 108 | 45 | 63 | 22 | 8 | 13 | 9 | 7 | 4 | 4/76/27/1 |

The ABSTAIN_REQUIRED share is **dominant** (62 % dev, 57 % val, 58 % held-out). That is a deliberate property of a benchmark
built to test abstention, but it has a consequence repeated in the statistical report: a method that never answers scores 63/108
= 0.583 on the held-out P2 metric. WEAK_SIGNAL abstentions are concentrated in the `high_baseline_variance`, `low_load` and
`partial_degradation` cells *by design* (fault amplitudes are absolute, `AMP_K * 8 ms`, so a larger baseline sigma lowers SNR).

## 4. Coverage of each dimension

"Distinct levels" is the number of levels that occur in that split / in the union. Counts are scenarios.

### 4.1 Fault families (16 levels)
| family | dev | val | held-out | total |
|---|---|---|---|---|
| cascading_failure | 12 | 4 | 9 | 25 |
| compound | 13 | 6 | 6 | 25 |
| cpu_contention | 13 | 4 | 6 | 23 |
| dependency_failure | 13 | 5 | 6 | 24 |
| intermittent | 12 | 5 | 5 | 22 |
| latency_degradation | 14 | 4 | 7 | 25 |
| memory_pressure | 12 | 5 | 6 | 23 |
| network_degradation | 10 | 4 | 8 | 22 |
| packet_loss | 11 | 6 | 8 | 25 |
| partial_degradation | 12 | 5 | 4 | 21 |
| queue_buildup | 13 | 4 | 5 | 22 |
| recovery_instability | 0 | 0 | 18 | 18 |
| resource_saturation | 11 | 5 | 4 | 20 |
| retry_amplification | 11 | 5 | 5 | 21 |
| service_unavailability | 11 | 5 | 6 | 22 |
| transient | 12 | 5 | 5 | 22 |
| **distinct levels** | 15 | 15 | 16 | 16 |

Held-out contains 16 families, dev and val 15; `recovery_instability` (18 held-out scenarios) exists **only** in held-out.

### 4.2 Causal structures (11 levels)
| structure | dev | val | held-out | total |
|---|---|---|---|---|
| ambiguous | 16 | 7 | 15 | 38 |
| branching | 15 | 6 | 9 | 30 |
| confounding | 15 | 7 | 11 | 33 |
| converging | 21 | 8 | 5 | 34 |
| diamond | 22 | 9 | 6 | 37 |
| feedback_like | 0 | 0 | 24 | 24 |
| hidden_common_cause | 23 | 8 | 9 | 40 |
| linear_chain | 19 | 7 | 6 | 32 |
| multiple_upstream | 14 | 6 | 9 | 29 |
| parallel_independent | 13 | 7 | 9 | 29 |
| shared_dependency | 22 | 7 | 5 | 34 |
| **distinct levels** | 10 | 10 | 11 | 11 |

`feedback_like` (24 held-out scenarios, a three-node feedback loop) exists **only** in held-out. `ambiguous` is present in all
splits. `confounding` and `hidden_common_cause` contain latent/hidden
nodes that never appear in a method's observations.

### 4.3 Temporal patterns (11 levels)
| temporal | dev | val | held-out | total |
|---|---|---|---|---|
| abrupt_degradation | 22 | 9 | 15 | 46 |
| delayed_downstream_effects | 22 | 8 | 15 | 45 |
| delayed_propagation | 22 | 6 | 12 | 40 |
| gradual_degradation | 14 | 6 | 7 | 27 |
| immediate_propagation | 16 | 7 | 11 | 34 |
| intermittent_degradation | 10 | 6 | 7 | 23 |
| multiple_onsets | 16 | 4 | 7 | 27 |
| oscillation | 13 | 6 | 8 | 27 |
| overlapping_faults | 20 | 9 | 12 | 41 |
| partial_recovery | 10 | 6 | 6 | 22 |
| recovery_delay | 15 | 5 | 8 | 28 |
| **distinct levels** | 11 | 11 | 11 | 11 |

### 4.4 Workloads (10 levels)
| workload | dev | val | held-out | total |
|---|---|---|---|---|
| bursty_traffic | 18 | 7 | 11 | 36 |
| changing_workload | 17 | 7 | 10 | 34 |
| high_baseline_variance | 23 | 8 | 13 | 44 |
| high_load | 15 | 7 | 10 | 32 |
| low_baseline_variance | 18 | 8 | 11 | 37 |
| low_load | 18 | 6 | 10 | 34 |
| moderate_load | 18 | 8 | 10 | 36 |
| skewed_requests | 18 | 7 | 11 | 36 |
| sparse_telemetry | 17 | 7 | 11 | 35 |
| unequal_service_rates | 18 | 7 | 11 | 36 |
| **distinct levels** | 10 | 10 | 10 | 10 |

### 4.5 Observability conditions (9 levels)
| observability | dev | val | held-out | total |
|---|---|---|---|---|
| ambiguous_pag | 20 | 8 | 12 | 40 |
| complete_telemetry | 20 | 8 | 12 | 40 |
| conflicting_observational_evidence | 20 | 8 | 12 | 40 |
| delayed_telemetry | 20 | 8 | 12 | 40 |
| insufficient_samples | 20 | 8 | 12 | 40 |
| missing_windows | 20 | 8 | 12 | 40 |
| noisy_telemetry | 20 | 8 | 12 | 40 |
| partial_service_observability | 20 | 8 | 12 | 40 |
| weak_interventional_evidence | 20 | 8 | 12 | 40 |
| **distinct levels** | 9 | 9 | 9 | 9 |

### 4.6 Intervention modes (9 levels)
| intervention | dev | val | held-out | total |
|---|---|---|---|---|
| collateral_effects | 20 | 8 | 12 | 40 |
| delayed | 20 | 8 | 12 | 40 |
| high_magnitude | 20 | 8 | 12 | 40 |
| imperfect | 20 | 8 | 12 | 40 |
| low_magnitude | 20 | 8 | 12 | 40 |
| multi_service | 20 | 8 | 12 | 40 |
| no_meaningful_effect | 20 | 8 | 12 | 40 |
| reversible | 20 | 8 | 12 | 40 |
| single_service | 20 | 8 | 12 | 40 |
| **distinct levels** | 9 | 9 | 9 | 9 |

### 4.7 Negative / adversarial kinds (11 named kinds + none = 12 levels)
| negative | dev | val | held-out | total |
|---|---|---|---|---|
| None | 135 | 54 | 81 | 270 |
| coincidental_anomaly | 6 | 2 | 2 | 10 |
| common_cause_several_services | 4 | 1 | 3 | 8 |
| downstream_largest_increase | 4 | 1 | 3 | 8 |
| earliest_not_root | 3 | 2 | 3 | 8 |
| high_variance_no_fault | 5 | 2 | 2 | 9 |
| incomplete_recovery_after_normalisation | 4 | 2 | 2 | 8 |
| indistinguishable_onsets | 3 | 2 | 2 | 7 |
| insufficient_telemetry | 4 | 1 | 2 | 7 |
| no_fault_plain | 4 | 2 | 2 | 8 |
| root_not_identifiable | 4 | 1 | 3 | 8 |
| weak_intervention_effects | 4 | 2 | 3 | 9 |
| **distinct levels** | 12 | 12 | 12 | 12 |

**90 of 360 scenarios (25 %)** carry a named negative kind; 270 carry none. Per-split named-negative counts are in the table
above. `no_fault_plain` and `high_variance_no_fault` are the no-fault negatives (4+5, 2+2, 2+2): NO_FAULT-labelled scenarios number only **9 / 4 / 4** in dev / val / held-out.
False-positive-rate estimates are therefore very imprecise (held-out FPR = 2/4).

## 5. What is and is not independent across splits

Independence is **verified on content**, not asserted from seeds (`scripts/sprint430_verify_independence.py`,
`datasets/rift_v2/independence_report.json`, verified 2026-11-03T04:02:35Z, before the freeze).

| Key | shared dev&val | shared dev&held-out | shared val&held-out |
|---|---|---|---|
| content_hash | 0 | 0 | 0 |
| dynamics_hash | 0 | 0 | 0 |
| joint_cell | 0 | 0 | 0 |
| template_id | 0 | 0 | 0 |
| topology_hash | 0 | 0 | 0 |

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

| Dimension (marginals are shared BY DESIGN) | distinct levels per split |
|---|---|
| intervention | dev:9, held_out:9, val:9 |
| observability | dev:9, held_out:9, val:9 |
| temporal | dev:11, held_out:11, val:11 |
| workload | dev:10, held_out:10, val:10 |

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
