# Sprint 4.5.1 — Reproducibility and Protected-Verification Report

Machine: macOS arm64, CPython 3.9.6. **Only this platform was exercised. No cross-platform or other-Python claim is made.** Base commit `be5e0318fcd9cb17285ce6b8dff632cb68274b65`. Source: `artifacts/sprint4_5_1/repro/REPRO_FINDINGS.md` and the final re-runs recorded below.

## 1. Protected-data deviation (disclosure)

* **Procedural deviation.** One agent ran `shasum -a 256 datasets/rift_v2/heldout_candidate.json | wc -l` once, outside the approved procedure. That computed a SHA-256 over the sealed Sprint 4.3.0 held-out file's bytes. The digest was **neither displayed nor recorded** (only the line count "1" appeared) and **no content was read, parsed or printed**.
* **Hashing is not content inspection.** This report does not claim that no operation of any kind was performed on the file; it claims that no content was read.
* **Approved hash access.** `verify_freeze()` reads the file's bytes and compares the SHA-256 with `artifacts/sprint4_3_0/freeze.json`. It runs inside the registered protected test `test_dev_val_pins_and_freeze_intact` and is the approved Sprint 4.4.2 procedure. It ran and passed.
* The file was not modified. No result depends on the deviation. Whether to accept it is decision X5 (researcher).
* The SHA-256 string quoted in the preregistration was copied from `datasets/rift_v2/independence_report.json`, not computed here. No hashing of the sealed files was repeated during final validation.

## 2. Freeze manifests

| manifest | files | SHA-256 | result |
|---|---|---|---|
| original `artifacts/sprint4_5_0/prereg/freeze_manifest.json` | 51 | `609bcb9d8a9786492f045e4fe13e10e1d17518f3111814a91e5ca73b6902aeb6` | final re-check against `artifacts/sprint4_5_1/baseline_freeze_manifest_before.json`: **51 files, 0 mismatches** (working tree = baseline). The baseline was not overwritten. |
| extended `artifacts/sprint4_5_1/freeze/extended_manifest.json` | 69 = 51 + 18 | `0e3a9262f4619d33ba55c4f76cb17a36aec02b987aac4befa35f4464f6eb25ec` | regenerated last; `problems []` |

Roles in the extended manifest: comparator_implementation_dependencies 14, dataset_generation_dependencies 8, development_data 7, environment_and_lock 1, evaluation_framework 7, evaluation_scripts 6, protocol 1, shared_method_dependencies 14, test_suite 5, v2_frozen_implementation 1, v3_frozen_implementation 5. The 18 added files include `src/rift/evaluation/dataset_registry.py` and `src/rift/benchmark/adversarial_generator.py`, which were untracked before this sprint and are committed with it. The extended-manifest hash appears only in the Sprint 4.5.1 reports, by design (the consistency checker forbids it in the five preregistration documents).

## 3. Test results (exact)

| check | result |
|---|---|
| V3 tests, `python3 -m pytest -q -p no:cacheprovider -W ignore tests/unit/test_sprint440_attribution_v3.py` | **34 passed** |
| safe harness subset: `scripts/sprint442_run_tests.py --require-protected tests --ignore=<4 held-out-parsing modules>` | **803 passed** (801 reproducible + 2 protected passes), 0 unavailable, 0 failures; exit code 0. Re-run at final validation (`harness_safe_subset_final_rerun.txt`). |
| sprint-430 subset (3 tests deselected) | 48 passed, 0 failures |
| sprint-424 guard subset (10 individually named tests that never reach the data) | 10 passed, 0 failures |
| **Total executed and passed** | **861 of 888**, 0 failures |
| doc-consistency checker | FAIL 0, WARN 0; 58 numerical claims recomputed, 0 failed; 42 power-table cells compared |
| CID cell reconciliation | 218 cells (214 factorial + 4 mixture), 8 degenerate, **210 distinct DGPs**, 468,000 replicates |

## 4. The 27 tests that were NOT run

They would `json.loads` (or otherwise parse) sealed held-out content, so they were deliberately not executed. **They are NOT reported as passed; their status this sprint is NOT RUN.** List: `artifacts/sprint4_5_1/repro/tests_not_run_held_out_content_risk.txt`.

* 15 in `tests/unit/test_sprint424_dataset_manifest.py`
* 9 in `tests/unit/test_sprint424_heldout_guard.py`
* 2 in `tests/unit/test_sprint430_independence.py`
* 1 in `tests/unit/test_sprint430_metrics_access_stats.py`

Sprint 4.4.2 reported 886 + 2 = 888 on the owner's tree; this sprint cannot confirm those 27. Running the full tree with `--require-protected` is decision **D12 (BLOCKER)** and is left to the owner. `scripts/verify_heldout_sealed.py` ran (4/4 PASS) but concerns the legacy Sprint 4.2.4 set, not the Sprint 4.3.0 `rift_v2` file.

## 5. Environment

* The lock `reproducibility/requirements-canonical-py39.lock.txt` (65 lines) has SHA-256 `121304edcc036611eca354c23c6910882965bfa835822c78354c3f19a32e3fae` (matches).
* **Direct scientific pins match; 14 transitive pins differ** (attrs, backports.asyncio.runner, packaging, patsy, Pygments, pyparsing, python-dateutil, pytz, six, threadpoolctl, tomli, typing_extensions, tzdata, zipp). Results are not claimed to be independent of them (not tested).
* CI (Ubuntu, Python 3.11, `requirements.txt`) and the Makefile do not use the canonical lock.
* Clean-export reproducible passes were 663 here against 664 in the 4.4.2 report; the difference is unexplained and not a failure.

## 6. Python outcome (researcher decision 3)

`pyproject.toml` `requires-python` changed from `>=3.10` to `>=3.9` and committed. Evidence: all 185 `.py` files parse under 3.9 (`ast.parse(feature_version=(3,9))`); no 3.10+ constructs found; the suite runs on 3.9.6; the 4.4.2 report also shows 3.11.15 passing. **Caveats:** one platform; the invalid `build-backend = "setuptools.backends.legacy:build"` and the non-PEP 440 `version = "0.1.0-phase3"` are unchanged, so `pip install -e .` still fails regardless of Python version (X6); CI targets 3.11. An addendum was added to `docs/SPRINT4_4_2_REPRODUCIBILITY_REPORT.md`.

## 7. What was not done

No confirmatory data were generated (`artifacts/sprint4_5_0/confirm/` does not exist); no method was run on new data; no frozen file changed; the 11 pre-existing modified files and the other untracked historical files were not staged.
