# Sprint 4.3.0 — Dataset Provenance Audit (legacy `rift_faults`)

Scope: the 83 legacy scenario records in `datasets/rift_faults/` (development 50, validation 18, held-out v1 15) plus the 30-record adversarial cohort.
Everything below is *validated on synthetic ground-truth scenarios*; nothing concerns a live system.
Reproduce: `python3 scripts/sprint430_provenance_audit.py` → `artifacts/sprint4_3_0/provenance/{legacy_lineage.json,legacy_lineage.csv,legacy_provenance_summary.json}`.
Code: `src/rift/scenarios/fingerprint.py`, `duplicates.py`. Tests: `tests/unit/test_sprint430_independence.py`.

## 1. Verdict

**The legacy splits are access-separated, not content-independent.** Every one of the 15 held-out-v1 scenarios has a content-identical twin in development or validation, at all four fingerprint levels. The legacy "held-out" guard (`held_out_guard.py`, `verify_heldout_sealed.py`) prevents *reading* the file; it cannot make the file's content independent of what was used to build and tune methods. Results quoted from the legacy held-out set must not be treated as independent evidence.

## 2. Fingerprints used

| Level | Definition | Purpose |
|---|---|---|
| `raw_content` | SHA-256 of every field except id/name/seed/split/bookkeeping | exact duplicates regardless of id or seed |
| `effective_dynamics` | exactly the fields the legacy generator consumes: `root_cause_service`, ordered `causal_path`, `injected_at_t` | records that produce statistically identical observable series |
| `structure` | Weisfeiler-Lehman hash of the causal graph with root marked + confounded flag + sizes | same propagation structure under renaming |
| `template` | `structure` + `fault_type` + timing rounded to 30 s | parameter-only variants collapse |
| near-duplicate | weighted similarity (edges .40, affected .20, root .15, type .10, timing .10, confounded .05) | partial copies |

## 3. Counts

| Level | dev (50) | val (18) | held-out v1 (15) | adversarial (30) | pooled dev+val+held-out (83) | pooled incl. adversarial (113) |
|---|---|---|---|---|---|---|
| raw_content | 25 | 10 | 7 | 6 | **25** | 31 |
| effective_dynamics | 22 | 9 | 7 | 6 | **22** | 28 |
| structure | 13 | 6 | 4 | 5 | **13** | 18 |
| template | 17 | 7 | 4 | 5 | **17** | 22 |

83 records contain **25 distinct contents**, 22 distinct generator inputs, 13 distinct structures and 17 templates.

## 4. Leakage matrix (raw_content; cell = number of scenarios in the row split that have a content twin in the column split; denominator = row size)

| row \ col | dev | val | held-out v1 |
|---|---|---|---|
| dev (50) | 34 (within-split) | 34 | 28 |
| val (18) | 18 | 12 (within) | 14 |
| held-out v1 (15) | **15** | **14** | 12 (within) |

Held-out v1 scenarios with a twin in dev or val: **15 / 15** at raw_content, effective_dynamics, structure and template (ids: QU_03, DF_03, MC_03, CF_36 … CF_47). Full matrices for all four levels are in `legacy_provenance_summary.json`.

## 5. Seed-only variation

11 groups of records are identical in content and differ only in `seed` (e.g. {NL_01, NL_02, NL_03}, {PL_01..03}, {SD_01..03}, {RC_01..03}, {QU_01..03}, {DF_01..03}, {MC_01..03}, and four groups of twelve CF_* records each stepping by 4: CF_00/04/08/…/44, CF_01/05/…/45, CF_02/06/…/46, CF_03/07/…/47). Inside a single split the same CF series also repeats (dev: four CF groups of six; val: four of three; held-out v1: four of three), but the pooled groups span dev, val and held-out v1, which is the leakage that matters. A different seed changes only the noise realisation, not the scenario; counting them as separate scenarios inflates N and, across splits, leaks content.

Near-duplicates (excluding exact duplicates): 1 pair at similarity ≥ 0.85, 50 pairs at ≥ 0.70.

## 6. Why: the legacy generator ignores most fields

`scripts/run_reproducible_evaluation.py::generate_scenario_metrics` consumes only `injected_at_t`, `root_cause_service`, `causal_path` and `seed`. It ignores `fault_type`, `confounded`, `affected_services`, `expected_recovery_t`, workload and observability. Baseline statistics are fixed at `{mean 0, std 10}`, so a label such as `fault_type="PACKET_LOSS"` or `confounded=True` changes nothing observable. The incident window is `injected_at_t − 60`, which is derived from ground truth. Consequences:

* Scenario diversity visible in the JSON labels is not diversity in the data any method sees.
* Records may share dynamics while carrying different labels, so some method differences on "different" scenarios are differences on the same input.

Other findings: scenario-id collisions across splits (`MC_02`: dev and val; `MC_03`: dev and held-out v1); template-prefix concentration (dev: CF 24 of 50; held-out v1: CF 12 of 15).

## 7. Adversarial script label leak (documented, not fixed)

`scripts/run_adversarial_benchmark.py::run_rift_full_adversarial` (lines 164–165) chooses the identifiability outcome node as `scenario.affected_services[-1]`, i.e. from ground truth. The learned-PAG variant in `run_reproducible_evaluation.py` was fixed in Sprint 4.2.3; this adversarial copy was not. `benchmark_v2.py` does **not** call it (it imports only the inline baseline classes); RIFT-FULL-V2 selects the outcome node from observed EBD output only. The pinned adversarial cohort and its artifacts were not touched; do not run that script's `main()` (it overwrites pinned files).

ID inconsistency recorded, not renamed: RIFT-ONE-SHOT is class id `B7-RIFT-ONE-SHOT` but dict key `B4-RIFT-ONE-SHOT` in the adversarial script. `B4-SAGE-CHAOS` is an always-abstain stub and is excluded.

## 8. Consequences for earlier claims

Legacy numbers (e.g. Sprint 4.2.3 "held-out once", `artifacts/evaluation/comparative_results_held_out.json`) were obtained on a set whose content is fully present in dev/val. They remain reproducible but are **not independent**. They are left untouched (Sprint 4.2.3/4.2.4 records and hashes verified unchanged). The v2 corpus (see `SPRINT4_3_0_SCENARIO_DIVERSITY_REPORT.md`) replaces them for any new claim.

## 9. Limitations of this audit

Fingerprints detect identity and structural similarity; they cannot prove two *different* hashes are scientifically independent. The audit covers only the files in `datasets/rift_faults/`.
