# Sprint 4.4.2 — Reproducibility Hardening Report

**Branch:** `sprint-4.4.2-reproducibility-hardening` (based on the Sprint 4.4.1 checkpoint `db77446`; parent chain `b33ad64` → `db77446`)
**Scope:** close reproducibility gaps for the Sprint 4.4.0 V3 results. No V3 algorithm, frozen verification code, dataset, historical report or historical artifact was modified. Sprint 4.5.0 was not started. Nothing was pushed.
**Wording:** all results below are *validated on synthetic ground-truth scenarios* (development and validation splits only). Nothing here opens or evaluates the sealed held-out split, and nothing here is a claim about real systems.

---

## 1. Summary

| Question | Answer (evidence-backed) |
|---|---|
| Does a genuinely fresh clone reproduce the committed V3 dev/val results? | **Yes**, in the canonical environment built only from the committed lock file. All six variants, all 252 scenarios, scores identical; 9 of 10 `artifacts/sprint4_4_0` files reproduce (timing fields excluded, see §6). |
| Is the canonical environment documented and pinned? | **Yes** — `reproducibility/requirements-canonical-py39.lock.txt` (65 packages, exact versions). A venv built from it matches the lock file exactly (`pip freeze` diff is empty). |
| Is Python 3.9.6 a hard requirement? | **No** — it is the interpreter that produced the results. Python 3.11.15 reproduces all scores (§4). Untested: other interpreters/platforms. |
| Does `requirements.txt` (Python 3.11, causal-learn 0.1.3.8) reproduce V3? | **Scores: yes (252/252 scenarios, 6/6 variants, 0 score differences). Records: not byte-for-byte** — 6 records for one dev scenario differ in the `ident_status` label (§4.3). |
| What causes the difference? | **causal-learn 0.1.3.8 vs 0.1.4.8 FCI output** (isolated, §4.2). Not NumPy/scikit-learn/NetworkX/pandas/Python. |
| Protected-material checks on a fresh clone | Reported as **PROTECTED-MATERIAL-UNAVAILABLE** (2 tests), not as passed, not silently skipped. |
| Genuine failures | **0** in the canonical environment. |

---

## 2. Which versions produced the committed results?

Recorded evidence (not inferred from the present machine alone):

* `artifacts/sprint4_3_0/results/{dev,val}/run_metadata.json` → `python 3.9.6`, `macOS-26.6.2-arm64`, `numpy 2.0.2`, `scipy 1.13.1`, `pandas 2.3.3`, `networkx 3.2.1`, and **`causallearn: "unknown"`** (the Sprint 4.3.0 recorder used `__version__`, which causal-learn does not expose).
* `artifacts/sprint4_3_0/run_metadata.json` → `python 3.9.6`.
* The Sprint 4.4.0 artifacts carry no environment metadata.
* scikit-learn 1.6.1 and causal-learn 0.1.4.8 are **not recorded by any committed artifact**. They are the versions installed in the interpreter that ran the work (`pip` metadata), and they are the *only* versions for which an end-to-end regeneration was found to equal the committed records exactly (§4).

**Honest conclusion:** Python 3.9.6, NumPy 2.0.2, SciPy 1.13.1, pandas 2.3.3, NetworkX 3.2.1 are recorded. scikit-learn 1.6.1 and causal-learn 0.1.4.8 are *inferred* from the installed environment plus the exact-match result; they are not independently recorded. Sprint 4.4.2 now records full versions at run time (`scripts/sprint442_capture_environment.py`).

Cross-check with the saved Sprint 4.3.0 V2 records (`RIFT-FULL-V2`, scenarios V2D-0001, V2D-0015, V2D-0117, V2V-0022): canonical env reproduces all four; `requirements.txt` env reproduces three and differs on the `ident_status` of V2D-0117. This is further (indirect) evidence that causal-learn 0.1.4.8 behaviour produced the saved records, since V2D-0117's saved label matches 0.1.4.8, not 0.1.3.8.

## 3. Canonical environment

* **File:** `reproducibility/requirements-canonical-py39.lock.txt` (fully pinned, direct and transitive).
* **Direct pins:** Python 3.9.6, numpy 2.0.2, scipy 1.13.1, scikit-learn 1.6.1, networkx 3.2.1, pandas 2.3.3, causal-learn 0.1.4.8 (+ momentchi2 0.1.8, joblib 1.5.3, statsmodels 0.14.6), pytest 8.4.2, requests 2.32.5.
* **`requirements.txt` was deliberately not changed.** It pins a different, historically-unrun stack. It also omits `requests`, which `tests/unit/test_prometheus_client.py` needs (found when the lock-file venv failed 3 tests; fixed by adding `requests`/`urllib3`/`certifi`/`charset-normalizer`/`idna` to the lock — a real gap in the old requirements file, left unmodified and documented here).
* **Platform:** macOS 26.6.2, arm64 (Apple Silicon), Apple CommandLineTools Python 3.9.6. Recorded in `artifacts/sprint4_4_2/env_freshclone_lockfile_py39.json`.
* **Seeds (all fixed in code; none drawn at run time):** FCI `np.random.seed(scenario.seed)`; simulator `default_rng(scenario.seed)`; intervention `default_rng((seed·7919+crc32(node)) & 0x7FFFFFFF)`; CID bootstrap/permutation `(seed·1000003+crc32("x->y")) & 0x7FFFFFFF`; adversarial generator `sha256("rift-v3-adversarial|tag|k")[:8]`; Sprint 4.4.0 Monte-Carlo analysis 440; Sprint 4.3.0 statistics seed 430 (B=2000, 10000 permutations).
* **Create the environment:**
  ```bash
  /usr/bin/python3 -m venv .venv && .venv/bin/python -m pip install -r reproducibility/requirements-canonical-py39.lock.txt
  ```
  (any CPython 3.9.6 works; the Apple build was used here.)

## 4. Dependency compatibility (dev + val; 252 scenarios × 6 V3 variants)

Three environments were actually executed. No other environment was tested.

| | Python | numpy | scikit-learn | networkx | pandas | causal-learn |
|---|---|---|---|---|---|---|
| **A** canonical (lock file) | 3.9.6 | 2.0.2 | 1.6.1 | 3.2.1 | 2.3.3 | **0.1.4.8** |
| **B** `requirements.txt` | 3.11.15 | 1.26.4 | 1.5.0 | 3.3 | 2.2.2 | **0.1.3.8** |
| **C** B with only causal-learn upgraded | 3.11.15 | 1.26.4 | 1.5.0 | 3.3 | 2.2.2 | **0.1.4.8** |

(`artifacts/sprint4_4_2/environments_tested.json`, `cross_environment_comparison.json`.)

### 4.1 V3 metrics (V3-FULL, identical in A, B and C)
| | P1 | P2 | Unsafe | Coverage | Wrong root |
|---|---|---|---|---|---|
| Dev | 32/68 | 116 | 35 | 67 | 7 |
| Val | 13/31 | 44 | 13 | 26 | 3 |

All six variants (V3-FULL, DEFINITIVE-ONLY, NO-MANIPULATION-CHECK, NO-EARLIER-GUARD, R3-CANDIDATES, NO-SYMMETRY-CHECK) produce the identical summary lines in all three environments.

### 4.2 FCI output across environments (213 of 252 scenarios have a learned PAG)
* **A vs C: 0 differing PAGs.** (same causal-learn, different Python/NumPy/scikit-learn/NetworkX/pandas)
* **A vs B: 2 differing PAGs** (V2D-0117, V2V-0022). **C vs B: the same 2.** ⇒ the difference is attributable to **causal-learn 0.1.3.8 → 0.1.4.8**, not to the numeric stack or Python.
  * V2D-0117: `o→` and `—` marks in 0.1.4.8 appear as `o-o` in 0.1.3.8 (5 edges re-labelled).
  * V2V-0022: two oriented edges `olive→dill`, `pine→dill` in 0.1.4.8 appear as `o-o` in 0.1.3.8.

### 4.3 Effect on V3 records
* **Env C: 0 records differ from the committed artifacts** (dev 180 and val 72 scenarios × 6 variants).
* **Env B: 6 records differ, all in the single field `ident_status`** of scenario V2D-0117 (`IDENTIFIABLE` committed → `CONDITIONALLY_IDENTIFIABLE`). **0 records differ in `abstained`, `top` candidates, or any score.** V2V-0022 has a different PAG in env B, but its saved V2 record (checked against Sprint 4.3.0) and all of its V3 records are identical in all three environments; the PAG-mark difference did not change any recorded output for that scenario.
* So: **metrics are cross-environment stable on this data; one diagnostic label is not.** This is evidence about these 252 synthetic scenarios, not a general guarantee: a different scenario set could expose causal-learn-version-dependent attributions.

### 4.4 Is Python 3.9.6 a hard requirement?
* Code runs and passes the suite on 3.9.6 and 3.11.15. `pyproject.toml` says `>=3.10` and `Makefile`/CI say 3.11, yet the results were produced on 3.9.6 — the repository's declared requirement and its execution history were inconsistent before this sprint. Python version is **not** the cause of any difference seen (A vs C). Python 3.9.6 is the **canonical historical** interpreter; 3.11.15 is **tested-compatible for scores**.

### 4.5 Nondeterminism sources
* `PYTHONHASHSEED=1`/`OMP_NUM_THREADS=1` and `PYTHONHASHSEED=12345`/`OMP_NUM_THREADS=4` (180 runs each, every 6th dev scenario × 6 variants, canonical venv): **0 score mismatches** (`determinism_check.json`). The sampled check is not exhaustive.
* Regenerated `runtime_s`/`mem_kb` differ between runs: these are wall-clock and memory measurements, not results.

## 5. Test classification

Two committed tests inspect **protected materials that are deliberately not in git**:

| Test | Protected material it needs | Why protected |
|---|---|---|
| `test_dev_val_pins_and_freeze_intact` | `datasets/rift_v2/heldout_candidate.json` (`verify_freeze()` hashes all 37 frozen files, including the sealed held-out file) | sealed held-out data |
| `test_historical_stage4_artifact_untouched` | `artifacts/stage4_intervention_results.json` | contains an internal IBM host name; pinned by SHA-256 `e4cf1391…` |

Implementation (no frozen code or existing test edited):
* `reproducibility/protected_materials.py` — pytest plugin with an explicit registry of the two tests. If a required file is absent the test is marked skipped with the prefix `PROTECTED-MATERIAL-UNAVAILABLE`, and the plugin counts it separately; if present it runs unmodified and is counted as `PROTECTED_PASS`.
* `scripts/sprint442_run_tests.py` — runs pytest with the plugin. Output classes: `REPRODUCIBLE_PASS`, `PROTECTED_PASS`, `PROTECTED_UNAVAILABLE`, `SKIPPED_OTHER`, `FAILED`. `--require-protected` exits 3 if any protected check was unavailable; `--json` records the classification.
* `tests/unit/test_sprint442_reproducibility.py` (8 tests) — from committed files only: dev/val pins and counts; every freeze entry *except* the sealed held-out file matches; manifest/freeze consistency (held-out hash compared as a string, never opened); held-out/Stage 4 files are not tracked in git; the classifier never counts an unavailable check as passed; environment capture reads no protected contents.
* Plain `pytest` is unchanged and still reports the 2 protected checks as failures on a fresh clone (verified: `2 failed, 664 passed`). That is intentional: only the transparent runner reclassifies them, with the reason printed.

Results:

| Location | Reproducible passed | Protected passed | Protected UNAVAILABLE | Genuine failures |
|---|---|---|---|---|
| Fresh clone, env A (lock file) | **664** | 0 | **2** (not verified) | **0** |
| Original tree (materials present), env A-equivalent | 886 | **2** | 0 | 0 (888 total) |
| Fresh clone, env B / env C | 661 | 0 | 2 | 3 (see below) |

The 3 failures in env B/C are `test_prometheus_client.py` (needs `requests`, which `requirements.txt` omits and which is not in B/C) — an environment-completeness gap, unrelated to V3.

## 6. Fresh-clone verification (env A, venv built only from the committed lock file)

Procedure (see §8). Everything below was regenerated in the clone and compared with the committed `artifacts/sprint4_4_0/*` by `scripts/sprint442_compare_artifacts.py`:

| Artifact | Result |
|---|---|
| `v3_dev.json`, `v3_val.json` (all 6 variants, per-scenario records & scores) | identical (only `runtime_s`/`mem_kb` ignored: 2,160+2,160 and 864+864 values) |
| `analysis.json` (incl. `graph_quality`, Monte-Carlo CID power) | identical (only 56 `runtime_s` timing subtrees ignored) |
| `adversarial_results.json` (14 families) | identical (only timing keys ignored; otherwise byte-identical) |
| `adversarial_summary.json`, `cid_audit.json`, `failure_traces_{dev,val}.json`, `graph_quality.csv` | **byte-identical** |
| `trace_meta.json` | **PROTECTED_UNAVAILABLE** — its recorded `verify_freeze = [true,"ok"]` was produced with the sealed held-out file present; a fresh clone correctly records `[false, "…heldout_candidate.json missing"]`. Not counted as reproduced. |

Dataset hashes (dev `a833ad0c…`, val `e82252b4…`) verified from committed files. Imports of `rift_v3`, `benchmark_v2` and the scenario simulator succeed.

**What the comparison ignores, and why:** only `runtime_s` and `mem_kb` (wall-clock/memory measurements; different on every run). The comparator counts what it ignored and prints it, so an over-broad filter would be visible. `NaN == NaN` is treated as equal (Wilson intervals with undefined values). Anything else is a failure.

## 7. Protected-material requirements

To run the two protected-integrity checks (and `verify_freeze()`), a local checkout needs, **outside git**:
`datasets/rift_v2/heldout_candidate.json` (+ `heldout_status.json`), `artifacts/sprint4_3_0/heldout_opened.json`, `artifacts/sprint4_3_0/results/held_out/`, `artifacts/stage4_intervention_results.json`. None was committed, opened, or modified. Without them a fresh clone *cannot* prove the held-out seal or the Stage 4 artifact's integrity — it can only prove everything else.

Unchanged and re-verified at the end of this sprint (original tree): freeze file `f2b0997c…`; Stage 4 artifact `e4cf1391…`; held-out candidate `97b90fa4…`; dev/val pins; `verify_freeze() == (True,'ok')`; `scripts/verify_heldout_sealed.py` 4/4; `sprint-4.4.0-v3-attribution` still at `b33ad64`.

## 8. Reproduction procedure (fresh clone)

```bash
git clone <repo> rift && cd rift && git checkout sprint-4.4.2-reproducibility-hardening
/usr/bin/python3 -m venv .venv                      # CPython 3.9.6
.venv/bin/python -m pip install -r reproducibility/requirements-canonical-py39.lock.txt
.venv/bin/python scripts/sprint442_capture_environment.py artifacts/sprint4_4_2/env.json
cp -r artifacts/sprint4_4_0 /tmp/committed_440      # reference copy
.venv/bin/python scripts/sprint440_trace_failures.py
.venv/bin/python scripts/sprint440_run_v3.py dev
.venv/bin/python scripts/sprint440_run_v3.py val
.venv/bin/python scripts/sprint440_analyze.py
.venv/bin/python scripts/sprint440_adversarial.py
.venv/bin/python scripts/sprint440_cid_audit.py
.venv/bin/python scripts/sprint442_compare_artifacts.py /tmp/committed_440 artifacts/sprint4_4_0
.venv/bin/python scripts/sprint442_run_tests.py                  # add --require-protected on the owner's machine
```
Total: roughly 5 minutes of compute on Apple Silicon. Regeneration overwrites tracked `artifacts/sprint4_4_0/*` in the clone; do it in a throwaway clone (or restore from git) to keep the committed copies.

## 9. Files

Added (this sprint, all new): `reproducibility/__init__.py`, `reproducibility/protected_materials.py`, `reproducibility/requirements-canonical-py39.lock.txt`, `scripts/sprint442_capture_environment.py`, `scripts/sprint442_run_tests.py`, `scripts/sprint442_compare_artifacts.py`, `tests/unit/test_sprint442_reproducibility.py`, `artifacts/sprint4_4_2/*.json` (evidence), this report. **Modified: none.** `requirements.txt`, the V3 code, frozen verification code, datasets and historical artifacts are untouched.

## 10. Known limitations and remaining risks

1. **Two integrity checks cannot be verified on a fresh clone** (held-out seal via `verify_freeze`, Stage 4 hash). They are reported honestly as unavailable; they pass in the owner's tree. A third party cannot independently confirm the seal from git alone.
2. **`trace_meta.json` cannot be reproduced without the sealed file.** Same cause.
3. **The exact scikit-learn and causal-learn versions of the original run are inferred, not recorded** (§2).
4. **Cross-environment claim is limited to three tested environments, to dev/val data, to one platform (macOS arm64).** Linux/x86_64, other BLAS builds, Python 3.10/3.12, and NumPy 2 on 3.11 were *not* tested. Scores matching on 252 synthetic scenarios does not imply every scenario would match.
5. **causal-learn is version-sensitive:** 0.1.3.8 and 0.1.4.8 give different PAG marks for 2 of 213 scenarios, which changes one diagnostic label. Anyone using `requirements.txt` will see this.
6. **`requirements.txt` is inconsistent with history and incomplete** (Python 3.11 / older stack, no `requests`; CI uses it, so CI would exercise a stack different from the one that produced the results). Not changed here; a decision for the owner.
7. **`pyproject.toml` declares `requires-python >=3.10`, but results were produced on 3.9.6.**
8. **Wall-clock and memory fields are non-reproducible by nature** and are excluded from comparison.
9. **Lock file is OS/arch specific** (pinned wheels such as `numpy`/`scipy` are platform builds); it documents what was run, not a universal environment.
10. **Determinism sampling** (180 runs per hash-seed/thread setting) is a sample, not exhaustive.
11. **Eleven unrelated tracked modifications and many untracked historical files remain uncommitted** in the working tree by design (not part of V3's dependency closure).
12. `docs/SPRINT_WORK_LEDGER.md` and `docs/SPRINT4_5_0_EXECUTION_PLAN.md` remain untracked; the Stage 4 artifact remains uncommitted pending owner approval to redact or accept the internal host name.
