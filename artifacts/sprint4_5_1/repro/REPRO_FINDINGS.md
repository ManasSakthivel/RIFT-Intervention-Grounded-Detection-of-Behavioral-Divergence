# Sprint 4.5.1 — Agent 5 reproducibility & protected-verification findings

Machine: macOS arm64, CPython 3.9.6 (Apple CommandLineTools), pip 26.0.1, setuptools 58.0.4. Only this platform was exercised. No cross-platform claim is made.
Branch `sprint-4.4.2-reproducibility-hardening`, HEAD `be5e0318fcd9cb17285ce6b8dff632cb68274b65`. Nothing was committed or `git add`ed.

## 0. Data-protection disclosure (read first)

* **One unintended access.** While assembling a final check I ran `shasum -a 256 datasets/rift_v2/heldout_candidate.json | wc -l`. That hashed the sealed Sprint 4.3.0 held-out file's bytes. Only the line count ("1") was displayed, and the hash value was never seen or recorded. No content was parsed or printed. It was not part of an approved procedure, so it is recorded here as a protocol deviation. It does not change the file, and no result depends on it.
* **Approved hash access.** `verify_freeze()` is called by the registered protected test `test_dev_val_pins_and_freeze_intact`. It reads that file's bytes and compares the SHA-256 with `artifacts/sprint4_3_0/freeze.json`. This is the existing 4.4.2 procedure. It ran, and the test is classed `PROTECTED_PASS`.
* The held-out file's contents were never opened, parsed or printed by me.
* `git status --short` was byte-identical before and after all test runs, except for the intentional `pyproject.toml` edit (§5).

## 1. 51-file freeze manifest

* Script: `artifacts/sprint4_5_1/repro/verify_manifest.py`. Evidence: `manifest_verification.json`.
* It re-hashes each file in the working tree and each `git show HEAD:<path>` blob, and compares both with `freeze_manifest.json`. Neither manifest was overwritten.
* **Result: 51 files, 0 mismatches.** Working tree = HEAD = manifest for every file.
* `git diff HEAD` over the 51 paths is empty.
* `pyproject.toml` is **not** one of the 51 files and is not in the manifest.
* Re-run after the `pyproject.toml` edit: still 51/0.

## 2. V3 test suite

`python3 -m pytest -q -p no:cacheprovider -W ignore tests/unit/test_sprint440_attribution_v3.py` → **34 passed** (7.9 s). Evidence: `v3_tests.txt`.

## 3. Full-tree harness: what could be run safely

### What the tests do with held-out material (determined by reading code before running)

| Test group | Effect on held-out material | Run? |
|---|---|---|
| `test_sprint440…::test_dev_val_pins_and_freeze_intact` (protected) | `verify_freeze` → `read_bytes` + SHA-256 of `rift_v2/heldout_candidate.json`. **Hash only.** | Yes (approved 4.4.2 procedure) |
| `test_sprint440…::test_historical_stage4_artifact_untouched` (protected) | Hashes `artifacts/stage4_intervention_results.json`, not held-out. | Yes |
| `test_sprint430_independence.py::test_independence_verifier_flags_injected_leaks` and `::test_shipped_v2_datasets_are_content_disjoint_and_sizes_meet_targets` | `json.loads(heldout_candidate.json)` — **parses held-out content**. | **NO** |
| `test_sprint430_metrics_access_stats.py::test_real_heldout_is_currently_not_loadable_…` | Reads `heldout_status.json`. If the status is FINAL_FROZEN it does not call `load_v2`, but reading the status file is still protected material. | **NO** (conservative) |
| `test_sprint424_dataset_manifest.py` (15 tests) | Parses `datasets/rift_faults/held_out_test.json` (the legacy 4.2.4 sealed set, a different file from the Sprint 4.3.0 candidate) with `json.loads` (`_count`, `unique_id_counts`, `generator_scenarios…`). Others run `build()` and `--check`, which `read_bytes` + `verify_bytes` and parse it. | **NO** |
| `test_sprint424_heldout_guard.py` (9 tests) | `test_correct_repo_location…`, `cwd_independent`, `authorised_final_access…`, and the sandbox tests (`copytree` of the dataset dir) load or copy `held_out_test.json`. `authorised_final_access` calls `load_split(HELD_OUT_TEST, final, guard)` and parses it. | **NO** |
| `test_sprint424_heldout_guard.py` (10 tests that never reach the data) | Guard/policy tests that raise before reading, source-text checks, `test_sealed_script_passes_from_other_cwd` (hash-only script), `test_historical_manifest_copy_pinned` (hashes the non-sealed manifest). | Yes — run individually |

### Runs performed (all via `scripts/sprint442_run_tests.py`)

| Run | Command (abridged) | Result |
|---|---|---|
| Safe subset | `--require-protected tests --ignore=<the 4 modules above>` | **803 passed**: REPRODUCIBLE 801, PROTECTED_PASS 2 (the two registered tests), PROTECTED_UNAVAILABLE 0, other skips 0, **FAILURES 0**. 44.9 s. Evidence: `harness_safe_subset.{txt,json}`. |
| Sprint-430 subset | `tests/unit/test_sprint430_independence.py tests/unit/test_sprint430_metrics_access_stats.py` minus 3 `--deselect`s | 48 passed, 0 failures. Evidence: `harness_extra_subset.{txt,json}`. |
| Guard subset | 10 individually named `test_sprint424_heldout_guard.py` tests | 10 passed, 0 failures. Evidence: `harness_guard_subset.{txt,json}`. |

* **Total executed and passed: 861 of the 888 collected.**
* **27 tests were deliberately NOT executed** (held-out content could be parsed). They are listed in `tests_not_run_held_out_content_risk.txt`: 15 in `test_sprint424_dataset_manifest.py`, 9 in `test_sprint424_heldout_guard.py`, 2 in `test_sprint430_independence.py` and 1 in `test_sprint430_metrics_access_stats.py`.
* **These 27 must not be reported as passed.** Their status on this tree this sprint is NOT RUN.
* 4.4.2 reported 886 reproducible + 2 protected = 888 on the owner's tree. I cannot confirm the 27 in this sprint. The owner can run them on a machine where reading the legacy `held_out_test.json` is acceptable. Running the full `--require-protected` on the whole tree is a researcher decision (D12), because it parses held-out content in the 4 modules.
* On this tree both protected files exist, so 0 UNAVAILABLE. Unlike the clean-archive run (2 UNAVAILABLE), the 2 protected checks here are real passes (PROTECTED_PASS). The `--require-protected` exit code was not captured. The summary printed 0 unavailable and 0 failures, which is the condition for exit 0.

### What `--require-protected` does

Defined in `scripts/sprint442_run_tests.py`. The plugin in `reproducibility/protected_materials.py` marks the two registered tests as `PROTECTED-MATERIAL-UNAVAILABLE` if their files are absent (existence check only, contents not read). `--require-protected` makes the runner exit 3 if any protected check was unavailable. It does not unseal or load anything, and it does not change which tests run.

## 4. `scripts/verify_heldout_sealed.py`

* `git diff` was read first. The only local modifications (relative to HEAD) are:
  * (a) `REPO_ROOT = Path(__file__).resolve().parent.parent`;
  * (b) check 4 now calls `dataset_registry.verify_all_files(REPO_ROOT)`.
* `verify_all_files` uses `path.read_bytes()` + SHA-256 + size compare, plus the historical manifest hash. It performs no JSON parse. Its docstring says "does NOT parse labels into the caller: hashes/size only". Other checks: AST/regex scan of `.py` source for the literal filename, a `HeldOutGuard` raise test with a synthetic token, and a scan of `results/` (which does not exist).
* **Note:** this script concerns `datasets/rift_faults/held_out_test.json` (legacy Sprint 4.2.4 sealed set, 15 scenarios), not the Sprint 4.3.0 `rift_v2/heldout_candidate.json`.
* `src/rift/evaluation/dataset_registry.py` is untracked (`??`). The modified script depends on an untracked module. This is a **reproducibility gap for the commit**: on a clean clone the script's check 4 fails closed with "dataset registry unavailable". That is a lead decision, not mine, since I do not commit and the file is among the pre-existing untracked files.
* Because it is hash-only, I ran it. **Output: 4/4 PASS, "GATE PASS … Held-out set is SEALED."** (check 3 passes trivially because `results/` does not exist). Evidence: `verify_heldout_sealed_output.txt`. The shell printed an empty `rc=` because `PIPESTATUS` is a bash variable that this shell does not support. The exit code was not recorded; the printed summary reads GATE PASS.
* It verifies: no unauthorized source reference to the literal filename; the guard raises without a token; no held-out artifacts under `results/`; and registry SHA-256 and size for the legacy dev/val/held-out/adversarial files, plus the historical manifest.
* It does **not** verify the Sprint 4.3.0 `rift_v2` held-out seal. That is covered only by `verify_freeze()` through the protected test above.

## 5. Python 3.9.6 vs `pyproject.toml >=3.10`

Evidence:
* `ast.parse(feature_version=(3,9))` on all **185** `.py` files (tracked + untracked): 0 syntax errors. `compileall` of `src tests scripts reproducibility analysis validation`: rc 0. Evidence: `py39_syntax_scan.txt`.
* A grep for 3.10+ constructs (`zip(strict=`, `dataclass(slots/kw_only)`, `match` statements, `removeprefix`, `TypeAlias`, `ParamSpec`, `tomllib`, `ExceptionGroup`, `pairwise`, parenthesised `with (`) found **none**. Seventeen `X | Y` annotations exist, all in files with `from __future__ import annotations`, so they are not evaluated at runtime.
* The suite runs on 3.9.6: 861 tests passed (§3). The 4.4.2 report also shows 3.11.15 passing.
* The lock file is a py39 environment, and the entire test history here ran on 3.9.6. Packages: numpy 2.0.2 / scipy 1.13.1 / pandas 2.3.3 / scikit-learn 1.6.1 all support 3.9. `pip check`: no broken requirements.
* The other declared environments conflict with each other: `Makefile` says python3.11, CI (`.github/workflows/test.yml`) runs 3.11 with the older `requirements.txt` (numpy 1.26.4 …), and `README` says 3.11. The CI and Makefile are **not** the 4.4.x canonical environment. This is a separate inconsistency that I did not touch.
* **`build-backend = "setuptools.backends.legacy:build"` is invalid.** The correct legacy backend is `setuptools.build_meta` or `setuptools.build_meta:__legacy__`. `pip install --dry-run -e .` on the real file fails with `BackendUnavailable: Cannot import 'setuptools.backends.legacy'`. This failure is independent of the Python version. On a scratch copy in `/tmp/pp`, `setuptools.build_meta` + `>=3.9` resolves (dry-run only, no install). I did **not** change the backend: it is outside the Python-version question, and no CI or test uses it.
* `version = "0.1.0-phase3"` is not valid PEP 440 either (`packaging` rejects it). Not changed.

**Change made (the smallest truthful correction):**

```diff
--- a/pyproject.toml
+++ b/pyproject.toml
-requires-python = ">=3.10"
+requires-python = ">=3.9"
```
Saved to `pyproject_diff.patch`. `>=3.10` excluded the canonical interpreter, which produced all the results. `>=3.9` is supported by the evidence above on one platform only. Nothing is claimed about 3.10 or about other platforms (Linux/x86_64 was not tested). `pyproject.toml` is not a frozen file and is not in the manifest (re-checked: 51/0).

Caveat for the lead: do not make `docs/SPRINT4_4_2_REPRODUCIBILITY_REPORT.md` §4.4/§8 contradict this. That report already states the `>=3.10` mismatch as a known issue, and it should now be marked resolved.

## 6. Dependency lock

* `shasum -a 256 reproducibility/requirements-canonical-py39.lock.txt` = `121304edcc036611eca354c23c6910882965bfa835822c78354c3f19a32e3fae` — **matches**.
* The lock has 65 lines and 60 pins.
* Evidence: `lock_vs_installed.txt`. **All 14 differences are in transitive or utility packages, and none is a direct scientific pin.** All direct pins (python 3.9.6, numpy 2.0.2, scipy 1.13.1, scikit-learn 1.6.1, networkx 3.2.1, pandas 2.3.3, causal-learn 0.1.4.8, statsmodels 0.14.6, joblib 1.5.3, pytest 8.4.2, requests 2.32.5, momentchi2 0.1.8) **match the installed versions**.
* The differing packages are:
  * attrs: lock 26.1.0, installed 25.4.0
  * backports.asyncio.runner: lock 1.2.0, not installed
  * packaging: lock 26.3, installed 26.0
  * patsy: lock 1.0.3, installed 1.0.2
  * Pygments: lock 2.21.0, installed 2.19.2
  * pyparsing: lock 3.3.3, installed 3.3.2
  * python-dateutil: lock 3.0.0, installed 2.9.0.post0
  * pytz: lock 2026.6, installed 2026.1.post1
  * six: lock 1.17.0, installed 1.15.0
  * threadpoolctl: lock 3.7.0, installed 3.6.0
  * tomli: lock 2.5.0, installed 2.4.0
  * typing_extensions: lock 4.16.0, installed 4.15.0
  * tzdata: lock 2026.6, installed 2025.3
  * zipp: lock 3.23.1, installed 3.23.0
* Therefore the earlier statement "installed environment matches the lock" holds for the direct pins only, **not** for the whole lock. The numerical results do not depend on these packages as far as is known, but that is not verified here. I recommend the lead wording "direct scientific pins match; 14 transitive pins differ" rather than "matches".

## 7. Frozen-file integrity

`git diff HEAD` over the 51 manifest paths is empty, and the re-hash shows 0 mismatches. `git status --short` is unchanged except for ` M pyproject.toml`. All 11 pre-existing modified files are still modified, and none was touched. No confirmatory data was generated, and no scripts other than the read-only verifier were added.

## 8. Files I created

All under `artifacts/sprint4_5_1/repro/`:
* `verify_manifest.py`, `manifest_verification.json`
* `v3_tests.txt`
* `harness_safe_subset.{txt,json}`, `harness_extra_subset.{txt,json}`, `harness_guard_subset.{txt,json}`
* `tests_not_run_held_out_content_risk.txt`
* `verify_heldout_sealed_output.txt`
* `py39_syntax_scan.txt`
* `lock_vs_installed.txt`
* `git_status_before_tests.txt`
* `pyproject_diff.patch`
* `REPRO_FINDINGS.md` (this file)

Modified outside that directory: `pyproject.toml` (one line).

## 9. Blockers / items for the lead and researcher

1. **27 tests not executed** (held-out content parse risk). They cannot be reported as passed. The researcher decides D12 (full-tree `--require-protected`).
2. **Untracked dependency:** `src/rift/evaluation/dataset_registry.py` is untracked, yet the locally modified, tracked `scripts/verify_heldout_sealed.py` and several tests import it. Do not stage it unless the researcher approves. At minimum, flag it.
3. `build-backend` is invalid, and `version` is not PEP 440. Both are unchanged, and the packaging is currently not installable with `pip install -e .`. I recommend a follow-up.
4. CI and Makefile target 3.11 with the old `requirements.txt`, which differs from the canonical py39 lock. Unchanged.
5. Disclosed unintended hash of the held-out file (§0).
