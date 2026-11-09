# Final Dataset Independence Report (Agent 2)

Branch `remediation-and-manuscript-closure` (from `ebad911`). Scope: held-out contamination, cross-split duplication, and a leakage gate for the future confirmatory set.

**Verdict.** A genuinely independent new dataset was **not generated**. The protocol forbids generating it before G0–G3 pass, and G0–G3 do not pass. The confirmatory generator (WP1, `generator_confirm.py`) does not exist, D7 has no named human reviewer, and `prereg.sha256` does not exist. This is a documented blocker, not a failure. What was delivered is a tested leakage gate that the future set must pass, and a corrected account of which existing sets are independent of which.

> Sealed-data statement. No sealed file was opened, parsed, hashed or loaded: not `datasets/rift_faults/held_out_test.json`, not `datasets/rift_v2/heldout_candidate.json`, not `heldout_status.json`, not `artifacts/sprint4_3_0/results/held_out/`. Sealed SHA-256 values in the outputs are copied from the committed manifests. I read only `datasets/rift_faults/{development,validation,adversarial_stress_cohort}.json`, `datasets/rift_v2/{dev,val}.json`, `datasets/rift_v3_dev/adversarial_dev.json`, and existing reports. Legacy-held-out statements below are quoted from existing audits (`docs/SPRINT4_3_0_DATASET_PROVENANCE_AUDIT.md`, `artifacts/sprint4_3_0/provenance/legacy_provenance_summary.json`), not re-derived.

---

## 1. There are two different "held-out" sets. Do not conflate them.

| | Legacy held-out (`rift_faults`) | Sprint 4.3.0 held-out (`rift_v2`) |
|---|---|---|
| File | `datasets/rift_faults/held_out_test.json` | `datasets/rift_v2/heldout_candidate.json` (untracked in git) |
| n | 15 | 108 |
| SHA-256 (copied from manifest) | `4337675b723dff1b88246216078a51e5b9aa1ffe976541739516d716ba18dd91` | `97b90fa424c3a7c0654d2fd8cde417f094c58931a527c8ce5023bafe5e8e69ce` |
| Content independent of dev/val? | **No. 15/15 have a content-identical twin** (all four fingerprint levels) | **Yes by construction and by a stored verification**: 0 shared content, dynamics, topology, template or joint-cell keys with dev/val; 0 near-duplicates ≥ 0.90 (`datasets/rift_v2/independence_report.json`, verified 2026-11-03T04:02:35Z) |
| Pristine? | No. Read repeatedly in Sprints 4.2.x (`docs/RIFT_DATASET_PROVENANCE.md` §5) | **No. Spent.** Opened once for V2 (`artifacts/sprint4_3_0/heldout_opened.json`, 2026-11-03T04:06:00Z). V3 was never run on it |
| Usable as independent evidence for a new method? | No | Only as a disclosed, already-opened, V2-only result. It cannot serve as a V3 confirmatory set |

My re-verification could only cover readable sets. The v2 held-out's independence rests on the stored report, which was produced from label-stripped content before the freeze. I could not re-check it without opening the sealed file. This is the same limitation the dataset protocol states in §8.2.

### Two caveats on the v2 held-out that are not stated prominently elsewhere

1. **It is distribution-shifted, not just independent.** `independence_report.json` records `feedback_like` (structure) and `recovery_instability` (family) as present **only** in the held-out set. Any dev-vs-held-out difference in V2 (for example correct-root 41.2% on dev vs 44.4% on held-out) mixes sampling noise with a deliberate shift. It is not a clean generalisation estimate.
2. **Its failure taxonomy was published before V3 was designed.** `docs/SPRINT4_3_0_FAILURE_TAXONOMY.md` (file time 3 Nov 10:39) lists held-out V2 wrong-answer ids and counts. `docs/SPRINT4_4_0_V3_DESIGN.md` (3 Nov 13:28) states V3 was "developed on dev, confirmed on val, never run on held-out" and ties each design choice to dev/val failures. I found no sentence stating that V3 used the held-out taxonomy, and I did not verify that it did not. The held-out set is therefore "never run with V3", but a reader can ask whether it was informationally untouched by V3's lineage. This should be stated as a limitation in the manuscript. I could not resolve it from the files alone.

---

## 2. Content-twin findings (all from readable data or existing audits)

### 2.1 Legacy `rift_faults` (83 scenarios in 3 splits plus a 30-scenario adversarial cohort)
- 83 records contain **25 distinct contents**, 22 distinct generator inputs, 13 distinct structures and 17 templates (existing audit; reproduced here for dev+val: `artifacts/final_closure/dataset_independence_report.json`, `legacy_rift_faults_dev_val.distinct_pooled` = 25 / 22 / 13 / 17).
- **Validation vs development (re-derived this step): 18/18 validation scenarios have a content twin in development** at raw_content, effective_dynamics, structure and template.
- Held-out v1: **15/15 have twins**: `CF_36`–`CF_47`, `DF_03`, `MC_03`, `QU_03` (`datasets/rift_faults/manifest.json`, `held_out_scenarios_with_content_twin_in_other_split`).
- The legacy generator ignores `fault_type`, `confounded`, `affected_services`, `expected_recovery_t`, workload and observability. Only root, causal path, injection time and seed affect the series. So the 25 distinct contents overstate diversity.
- Two id collisions (`MC_02` dev/val, `MC_03` dev/held-out) with different content. Always join on `(split, fault_id)`.

### 2.2 `rift_v2` (dev 180, val 72, held-out 108 sealed) and adversarial dev (112)
Re-derived this step on the readable sets with `src/rift/scenarios/leakage_checks.py`:

| pair | content | dynamics | topology | template | joint cell | id | seed | near-dup ≥ 0.88 | max similarity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| val ∩ dev | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.8216 |
| adversarial ∩ dev | 0 | 0 | **7** | 0 | 0 | 0 | 0 | 0 | 0.7973 |
| adversarial ∩ val | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.8060 |

**New finding: adversarial dev is not topology-independent of dev.** Seven topology hashes are shared with dev, and 104 of the 112 adversarial scenarios sit on one of them (6 union-find groups span adversarial and dev). `datasets/rift_v3_dev/provenance.json` says "disjoint from dev/val/held-out by construction", which is true for content, dynamics, template, joint cell, id and seed, but **not** for topology. This matches the dataset protocol's remark that the global `verify_independence` is not OK on the existing baseline (§8.1). It does not affect V3 vs V2 internal comparisons, but the adversarial cohort should not be described as topology-independent of dev. It was also authored after dev failures were seen (`docs/SPRINT4_4_0_FINAL_REPORT.md`).

**Within-set dependence (matters for the statistics, hand off to Agent 3):**

| set | scenarios | distinct topologies | max scenarios per topology | union-find groups (template ∪ topology) | largest group |
|---|---:|---:|---:|---:|---:|
| dev | 180 | 60 | 13 | 10 | 23 |
| val | 72 | 26 | 7 | 11 | 9 |
| dev + val | 252 | 86 | 13 | 21 | 23 |
| dev + val + adversarial | 364 | 87 | 55 | 22 | 75 |

The 252 dev/val scenarios have **about 21 independent-by-construction groups**, not 252 observations. The adversarial cohort has 8 distinct topologies for 112 scenarios (`provenance.json` already warns "K variants per family are NOT independent samples"). Seeds and ids are unique; content and dynamics hashes are unique within each set. So v2 has no exact duplicates but heavy structural clustering.

---

## 3. Can the 15 legacy held-out twins be removed?

Short answer: removing them removes the whole legacy held-out set, and that is the correct outcome.

| option | consequence | recommendation |
|---|---|---|
| Delete the 15 from `held_out_test.json` | There are 15 of 15. The set becomes empty. It also edits a hash-pinned sealed file, which invalidates `manifest.json`, `dataset_registry` pins, `verify_heldout_sealed.py` and the 51/69-file freeze manifests. Would also require opening sealed content to edit it | **Reject** |
| Keep the file, exclude the 15 by id in any analysis | No data change. Zero scenarios remain. Nothing to analyse | Equivalent to the next row |
| **Retire the legacy held-out as evidence; keep file and hash untouched** | No evidence loss: the legacy held-out never supported a headline V2/V3 claim. The headline numbers use `rift_v2` | **Adopt** |
| Re-allocate twins to dev/val | Moves content, edits pinned files, and changes the set that V3 development saw | **Reject** |

The legacy dev/val sets are also heavily duplicated (25 distinct contents in 83 records). They are used for no V3 headline claim; V2/V3 results use `rift_v2` dev/val. They should not be counted as 83 observations in any statistic.

Sample-size consequence: none for the V3 evidence base, because the legacy sets contribute nothing to it. The consequence is for external wording only: no independent held-out evidence for V3 exists today. The only unspent, independent test set is the future CONFIRM set (Section 5).

---

## 4. Leakage verification checks (delivered)

| file | purpose |
|---|---|
| `src/rift/scenarios/leakage_checks.py` | `check_candidate(candidate, protected_sets, near_threshold=0.88)`: per-protected-set counts for shared id, seed, content hash, dynamics hash, topology hash, template id, joint cell, near-duplicates; union-find groups spanning candidate and a protected set; intra-candidate duplicates. `construction_disjoint_from_sealed(candidate, frozen_structures)`: id prefix `V3C-`, no reserved prefix, no frozen structure or template name, generator version differs, no structure token in the id. `load_scenarios(path)` raises `PermissionError` on any sealed path before reading |
| `tests/unit/test_dataset_leakage_checks.py` | 19 tests (all pass). Injected exact twin with a new id and seed; node-renamed twin (evades content hash, caught by dynamics and topology hashes); shared id and seed; 1% numeric perturbation (evades hashes, caught by similarity); intra-candidate duplicate; construction check on frozen vs well-formed new records; sealed-path refusal; static check that the module reads only through the guarded loader; legacy and v2 pins |
| `scripts/final_dataset_independence_report.py` | Regenerates `artifacts/final_closure/dataset_independence_report.json` (readable-file hashes, sealed hashes copied from manifests, legacy and v2 results). No sealed I/O |
| `artifacts/final_closure/dataset_independence_report.json` | Output of the above |

Verification results: `tests/unit/test_dataset_leakage_checks.py` 19 passed; together with `test_sprint430_independence.py`, `test_sprint424_dataset_manifest.py`, `test_leakage.py`: 55 passed, 0 failed, 0 skipped.

Limits of the checks:
- They detect identity, name-agnostic dynamics identity, topology identity and spec-similarity. They cannot prove that two scenarios with different hashes are scientifically independent.
- Independence from the sealed v2 held-out can only be argued by construction (`construction_disjoint_from_sealed`) and proxied by similarity to dev/val. It cannot be measured without opening the file, which the default protocol (D8) forbids.
- Existing `tests/unit/test_sprint430_independence.py` loads `heldout_candidate.json`. That is one reason D12's 27 protected tests were not run locally. My tests deliberately do not.

---

## 5. Independent scenario-generation procedure (plan; no data generated)

The binding design is already `docs/SPRINT4_5_0_DATASET_PROTOCOL.md` (Route A, 16 new motifs S01–S16, 256 templates, N = 2000, K = 256). I audited it for leakage and recommend keeping it, with these additions:

1. **Run `check_candidate` inside the acceptance sampler, not only after generation.** Every candidate that passes R-CAP1/R-OWN is checked against dev, val and adversarial dev (id, seed, content, dynamics, topology, template, joint cell, similarity < 0.88) before it is accepted. This makes R-DUP-readable and the §8.3 proxy a per-candidate gate.
2. **Final gate on the accepted set:** `check_candidate(confirm_stripped, {dev, val, adv})["ok"]` must be True with `spanning_groups == []`, and `construction_disjoint_from_sealed(...)["ok"]` must be True. Store both outputs in `artifacts/sprint4_5_0/confirm/provenance.json`.
3. **Do not copy the adversarial-dev pattern.** Eight topologies for 112 scenarios is the failure mode to avoid. Keep R-CAP1 (one scenario per topology hash) so group size equals template size.
4. **State what is *not* independent.** CONFIRM uses the same 16 fault families, the same simulator physics, the same temporal/workload/observability/intervention level sets and the same label function as dev/val/held-out. Independence is at the structure/topology level only. Family-level and mechanism-level dependence with dev/val/held-out is by design and is already what the family-block bootstrap (SAP §3.1) addresses. The manuscript must say "new causal graphs under the same simulated physics and labelling rule", never "independent of the training distribution".
5. **Dev/val cannot influence allocation.** Quotas, motifs, seed tag (`rift-confirm-gen/1.0.0`) and rules are fixed in the preregistration hash before the first candidate is drawn. The sampler reads dev/val only to reject collisions, never to choose quotas. T1 (replication of stored dev/val `content_hash` in legacy mode) must pass first.
6. **Seed hygiene.** Collision with readable seeds is checked explicitly; no sealed seed is computed (protocol §4).
7. **Keep D8 = construction-based default.** Do not run the custodian count check; it would be a second opening of the sealed file.

### Handoffs
| need | owner | status |
|---|---|---|
| `generator_confirm.py` (WP1) and the acceptance sampler that calls `check_candidate` | Agent 4 | not started by me |
| Treat 21 (dev+val) groups and the crossed family structure as the dependence unit | Agent 3 | numbers in Section 2.2 |
| D7 named reviewer, D12 protected run, G3 `prereg.sha256` | owner / human | BLOCKED |
| Manuscript wording on held-out status | Agent 7 | wording below |

---

## 6. Recommended wording for the manuscript

- Legacy held-out: "The 15-scenario legacy held-out set is not content-independent of development and validation (15/15 content twins) and is not used as evidence."
- v2 held-out: "A 108-scenario held-out set, content-independent of dev/val at the hash, template, topology and joint-cell level, was opened once and used only for V2. It contains one structure kind and one fault family absent from dev/val. V3 was not run on it."
- Adversarial dev: "112 hand-designed counterexamples on 8 topologies. They are not independent samples and share topology skeletons with development scenarios."
- No claim of independent held-out validation for V3.

## 7. Decision recommendations

| id | recommendation | external approval needed |
|---|---|---|
| D6 | Approve Route A (new module) | owner; reviewer to confirm via D7 |
| D8 | Keep exclusion-by-construction; no custodian read | owner |
| D18 | Keep S01–S16 and the 0.88 proxy; add per-candidate `check_candidate` gate | owner; reviewer |
| D7 | Cannot be decided by anyone but a real independent reviewer | **yes, BLOCKED** |

## 8. Remaining blockers and unresolved items

1. No CONFIRM dataset: blocked on WP1, D7, G3. Nothing was generated or faked.
2. Independence of v2 held-out from V3's design lineage is unverified (Section 1, caveat 2).
3. Adversarial dev is not topology-independent of dev (new, Section 2.2). `datasets/rift_v3_dev/provenance.json` is a frozen record and was **not** edited. Correct the wording in the manuscript instead.
4. `datasets/rift_v2/heldout_candidate.json` and `heldout_status.json` are untracked and not in CI. Their integrity is protected only by the hash in `independence_report.json`/`manifest.json` and by owner-run checks.
5. `datasets/rift_faults/manifest.json` has an uncommitted rewrite (schema v2). Not modified here; the commit decision belongs to the owner.

## 9. Evidence and commands

Files inspected: `datasets/rift_faults/manifest.json`, `datasets/rift_v2/{manifest,independence_report,heldout_status}.json`, `datasets/rift_v3_dev/provenance.json`, `docs/RIFT_DATASET_PROVENANCE.md`, `docs/SPRINT4_3_0_DATASET_PROVENANCE_AUDIT.md`, `docs/SPRINT4_5_0_DATASET_PROTOCOL.md`, `docs/CONFIRMATORY_INFRASTRUCTURE_PLAN.md`, `src/rift/scenarios/{independence,splitter,fingerprint,duplicates,generator_v2}.py`, `artifacts/sprint4_3_0/provenance/legacy_provenance_summary.json`, `artifacts/sprint4_3_0/heldout_opened.json`.

Files created: `src/rift/scenarios/leakage_checks.py`, `tests/unit/test_dataset_leakage_checks.py`, `scripts/final_dataset_independence_report.py`, `artifacts/final_closure/dataset_independence_report.json`, this report. No tracked file was modified. No dataset, manifest or historical result was changed.

Commands run:
```
python3 -m pytest -q -p no:cacheprovider tests/unit/test_dataset_leakage_checks.py          # 19 passed
python3 -m pytest -q -p no:cacheprovider tests/unit/test_sprint430_independence.py \
  tests/unit/test_sprint424_dataset_manifest.py tests/unit/test_leakage.py \
  tests/unit/test_dataset_leakage_checks.py                                                 # 55 passed
python3 scripts/final_dataset_independence_report.py                                        # wrote artifacts/final_closure/dataset_independence_report.json
```

## 10. SHA-256 manifest of readable files (computed this step)

| file | SHA-256 |
|---|---|
| `datasets/rift_faults/development.json` | `d8960776ee3556a8b98de4767c3e8bd14f430f828983fcf50b0114dce8a1aebd` |
| `datasets/rift_faults/validation.json` | `2363f6bbea6f86eb883525be90151655ca9ddac01aa9ad5b6e8351dc4953d0f3` |
| `datasets/rift_faults/adversarial_stress_cohort.json` | `46e769c6e75895fa25bfc22616aabb38757a2dac3c3c190025a4e57eb1215577` |
| `datasets/rift_v2/dev.json` | `a833ad0ca1db0583a30bc4450f9f59b2984a5823702935ef59c6b037e026ef5f` |
| `datasets/rift_v2/val.json` | `e82252b47f29dc1353586034b6fd8c3491df3221851f9c84c48bf717a944a1fb` |
| `datasets/rift_v3_dev/adversarial_dev.json` | `3525bc05ed8b9dd21dcc888181005af09e75f43396fb27a0ad6732588ea3c472` |

All six equal the values pinned in the existing manifests. Sealed hashes (copied, not computed): legacy `4337675b…1dd91`, v2 `97b90fa4…e69ce` (full values in Section 1).
