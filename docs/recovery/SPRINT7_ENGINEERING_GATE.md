# RIFT Sprint 7 — Workstream 5: Engineering & Reproducibility Gate

**Document ID:** `RIFT-DOC-S7-WS5-ENG-GATE-001`
**Execution date:** 2026-11-09 (system clock)
**Platform:** macOS arm64 (Darwin), Python 3.11.15 (`/opt/homebrew/bin/python3.11`), pytest 9.1.1
**Git:** HEAD `ebad911` (working tree dirty; see §7)
**Scope:** Execute the five mandated commands, audit Makefile targets, directory creation, seed propagation and CLI arguments. All numbers below were measured in this session; no figure is carried over from earlier reports.

---

## 1. Verdict

| Gate | Result |
|---|---|
| Functional tests (1,017 of 1,025 collected) | PASS |
| Environment-lock tests (8 of 1,025) | **FAIL** — installed packages differ from the canonical lock |
| `make test-gate3a` | PASS (119/119) |
| `validation_harness.py` | PASS (exit 0, V1–V5 PASS) |
| `sprint451_utility_sensitivity.py` | PASS with 2 unverified claims (56/58) |
| `rift.experiments.run EXP-001 --dry-run` | PASS only with `PYTHONPATH=src`; **FAILS as written** |
| **Overall engineering gate** | **NOT CLEAN — PASS WITH DEFECTS (see §6)** |

The repository does not meet the "all green on the stock interpreter" bar. Two root causes: (a) the local Python 3.11 environment does not match the canonical lock, and (b) `rift` is not importable without `PYTHONPATH=src`.

---

## 2. Mandated command results

| # | Command | Exit | Wall time | Result |
|---|---|---|---|---|
| 1 | `make test-gate3a` | 0 | 0.42 s (pytest 0.09 s) | 119 passed, `GATE 3A: PASS` |
| 2 | `python3.11 -m pytest tests/ -v -k "not linux_only"` | 1 | 52.35 s (pytest 52.06 s) | **1017 passed, 8 failed**, 0 skipped, 33 warnings |
| 3 | `python3.11 validation/validation_harness.py` | 0 | 1.67 s | V1–V4 PASS, V5 FAR = 0.00 % |
| 4 | `python3.11 scripts/sprint451_utility_sensitivity.py` | 0 | 1.28 s | "claims verified: 56/58"; 0 of 3276 score mismatches |
| 5 | `python3.11 -m rift.experiments.run --experiment EXP-001 --dry-run` | **1** | 0.03 s | `ModuleNotFoundError: No module named 'rift'` |
| 5b | same, with `PYTHONPATH=src` | 0 | 0.54 s | `Status: COMPLETE`, artifacts in `results/EXP-001/` |

### 2.1 Full pytest suite (command 2)
- Collected: 1,025 with and without `-k "not linux_only"`. The filter deselects nothing in this checkout (`grep linux_only` in `tests/`, `conftest.py`, `pyproject.toml` returns no match). `docs/recovery/TESTING_REPORT.md` states "12 deselected"; that is **not reproduced** here.
- 1017 passed + 8 failed = 1025.
- All 8 failures are in `tests/unit/test_final_reproducibility.py`:

| Test | Installed | Canonical lock expects |
|---|---|---|
| `test_installed_causal_learn_is_canonical` | causal-learn 0.1.3.8 | 0.1.4.8 |
| `test_numeric_stack_matches_canonical_lock[numpy]` | 1.25.2 | 2.0.2 |
| `…[scipy]` | 1.16.3 | 1.13.1 |
| `…[scikit-learn]` | 1.5.2 | 1.6.1 |
| `…[networkx]` | 3.6.1 | 3.2.1 |
| `…[pandas]` | 2.1.0 | 2.3.3 |
| `…[causal-learn]` | 0.1.3.8 | 0.1.4.8 |
| `test_v2d0117_ident_status_matches_committed_v3_record` | `CONDITIONALLY_IDENTIFIABLE` | `IDENTIFIABLE` (V3-FULL) |

The last failure is a **scientific-output** difference, not just a version string: with causal-learn 0.1.3.8 the V2D-0117 ident-status label changes. This matches the documented hazard in the header of `requirements.txt` (Sprint 4.4.2). It is a consequence of the unsynchronised local environment (`pip install -r requirements.txt` was not run), not of a code defect. Not verified in this session: that a fresh venv built from `requirements.txt` clears all 8 (not attempted; no environment changes were made).
- `docs/recovery/TESTING_REPORT.md` reports "1,013 passed, 0 failed" and attributes the 8 pin failures to a lockfile requirement; the actual current count is **1017 passed / 8 failed**, so that report is stale on counts and its "0 failed" headline is inaccurate.

### 2.2 Validation harness (command 3)
Output: V1 P@1 = 83.33 % (≥ 70 %), V2 confounded-correct = 100 %, V3 R2 invariant holds, V4 R4 invariant holds, V5 FAR = 0.00 %; n = 36 (12 non-confounded, 24 confounded). Report written to `artifacts/phase3/independent_validation_report.json`.
- Determinism: two further runs produced an identical MD5 (`fd8d2090d0813a02f8223669b1cd2ff3`).
- Side effect: the script **overwrites a git-tracked file**. Versus HEAD the committed values were V1 = 0.50 (PARTIAL) and FAR = 0.3333; they now read V1 = 0.8333 (PASS) and FAR = 0.0. The working tree already carried this modification (alongside a modified `validation/run_cid_validation.py`) before this session, so the change reflects uncommitted code changes rather than nondeterminism. The harness's own caveat stands: oracle PAG, upper-bound estimate only.

### 2.3 Utility sensitivity (command 4)
- 56/58 claims verified; 0 mismatches vs saved scores across 3276 comparisons.
- Not verified (both are rounding-tolerance failures, tolerance 0.0006):
  1. "V3 mean cost term gamma=1 (PRE 3.3: 0.136)" — recomputed 0.135317 (diff 0.000683).
  2. "B0-EARLIEST BE kappa=0" — claimed 0.26, recomputed 0.260638 (diff 0.000638).
- The script exits 0 even though claims are unverified, so a CI exit-code check would not catch this. Also emits a networkx ≥3.5 hash-change UserWarning.

### 2.4 Experiment dry-run (command 5)
- As specified, fails: `rift` lives under `src/` and is not installed (`pip list` has no rift; `pyproject.toml` has `[tool.setuptools.packages.find] where=["src"]` but the package is not installed, and root `conftest.py` only patches `sys.path` for pytest).
- `make experiment EXP=EXP-001` and `make experiment-list` both inherit this failure (`make experiment-list` exit 2).
- With `PYTHONPATH=src` it succeeds. Output: Status COMPLETE, 6 files per manifest (`config, environment, inputs, raw_results, metrics, statistics`), SHA-256 checksums recorded; 36 development scenarios exist, `n_scenarios` from the registry limits to the first N (raw_results begins NL_01, PL_01, SD_01…).
- The run code imports `src.rift.…` internally (works from repo root with the CWD on `sys.path`) while the entrypoint is `rift.experiments.run`; both import roots coexist, meaning the same modules are loaded under two names when both are used.

---

## 3. Makefile audit

Every target was exercised (or parsed with `make -n`). Per-target results, all run via `make`:

| Target | Exit | Tests | Time |
|---|---|---|---|
| `test-gate3a` | 0 | 119 passed | 0.42 s |
| `test-unit` | 0* | 846 passed, **8 failed** | 50.17 s |
| `test-causal` | 0 | 105 passed | 3.32 s |
| `test-integration` | 0 | 66 passed | 1.52 s |
| `test-intervention` | 0 | **no tests ran** | 0.20 s |
| `test-safety` | 0 | 10 passed | 0.20 s |
| `test-baselines` | 0 | 60 passed | 1.45 s |
| `test-evaluation` | 0 | 39 passed | 0.97 s |
| `test-leakage` | 0 | 5 passed | 0.21 s |
| `setup`, `reproduce-all`, `pre-linux-check` | parse OK (`make -n`) | not executed (setup runs pip install; reproduce-* run `clean`) | — |
| `experiment EXP=EXP-001` / `experiment-list` | 1 / 2 | module not found (see §2.4) | — |

\* `test-unit` exits 0 although 8 tests fail: the recipe pipes pytest through `tee`, so the pipeline status is `tee`'s. **The same masking applies to every `make test-*` target and to `make test`.** Only `test-gate3a` has an explicit grep for `passed`, and that grep matches any log containing the word "passed" (a run with failures and some passes would still print `GATE 3A: PASS`). Fix: add `SHELL := /bin/bash` with `.SHELLFLAGS := -o pipefail -c`, and grep for `failed`/exit status.

Other findings:
- `test-intervention` points at `tests/integration/intervention/`, which does **not exist** in this checkout; pytest reports "no tests ran" and make still exits 0 (pytest exit 5 is masked by `tee`). It is a vacuous pass. The directory is only created by `make setup`.
- Directory creation: `make setup` creates `artifacts/{phase3,phase3_5,coverage,logs,pre_linux}`, many `tests/**` dirs, `results experiments configs`. Of those paths, the only one missing in the checkout is `tests/integration/intervention`. Not run: `make setup` itself (would pip-install over the environment). Verified via `make -n setup`.
- `test-gate3a` and every other `tee artifacts/logs/*.log` target **fail if `artifacts/logs/` does not exist** (it is git-ignored and removed by `make clean`). I confirmed this: with the directory absent, `make test-gate3a` runs 119 tests then dies with `Error 1`. Callers must run `make setup` first (reproduce-phase3 does so; the standalone targets do not). Directory restored afterwards.
- `make experiment` without `EXP` prints usage and exits 1 (as designed).
- `.github/workflows/test.yml` uses Python 3.11, `pip install -r requirements.txt` (which would install the canonical pins and avoid the 8 failures) and runs `make lint`. CI has no `PYTHONPATH` handling shown in the grepped lines; not verified whether the experiment step is covered.

---

## 4. Deterministic seed propagation audit

| Check | Evidence | Result |
|---|---|---|
| Default seed | All 14 registry entries have `seed: 42`; manifest of default run has `"seed": 42` | OK |
| `SyntheticBenchmark.generate_all_faults(seed)` | uses `random.Random(seed)`; per-trial seeds are `seed + trial`/`seed + idx` (e.g. first scenario seed 43 for 42, 8 for 7) | OK, deterministic |
| Repeated default runs | `raw_results.json` SHA-256 prefix `daa4397893…`, `inputs.json` `44b3ca2f…` identical across runs | OK |
| Repeated `--seed=7` runs | identical `raw_results`, `inputs`, `config` hashes across two runs | OK |
| Scenario IDs vs seed | development-split scenario IDs/count (36) are identical for seeds 42 and 7; only per-scenario seeds change | Observation: the seed does not change which scenarios are chosen |
| `--seed` plumbing | manifest `seed` = 7 after `--seed=7`, config hash differs (`3fb4…`/`f35d…` vs `53dd…`) | OK |
| `--seed 0` | manifest records **42**, not 0 | **Defect**: `self.seed_override or spec.get("seed", 42)` treats 0 as unset |
| Reproducibility of `config.json` / `manifest.json` / `environment.json` across runs | `environment.json` embeds `timestamp_utc`; manifest checksum of it differs run to run; `provenance_<uuid>.json` plus a fresh `run_id` per run accumulate in `results/EXP-001/` (6 → 26 files after my runs) | Expected, but the artifact directory is not idempotent |
| `numpy`/global RNG seeding in `run.py` | `run.py` imports numpy but only uses `random.Random(seed)` inside the benchmark; no global `np.random.seed` / `PYTHONHASHSEED` handling | Not an issue for the current dry-run, which executes no stochastic analysis |
| `git_commit` / `config_hash` | manifest: `config_hash: "unknown"` | Provenance gap |

The dry-run only enumerates scenarios (`status: DRY_RUN_COMPLETE`); it executes no estimator, so seed propagation into FCI/CID/attribution is **not exercised** by command 5. Seed determinism for those paths is covered only by unit tests (all passing apart from the 8 environment ones).

---

## 5. CLI argument audit (`rift.experiments.run`)

| Invocation | Observed |
|---|---|
| `--list` | prints "14 experiments" (EXP-001 … EXP-014), exit 0 |
| `-e EXP-001 --dry-run` | OK |
| `-e EXP-001` | OK (dry-run is the default) |
| `-e EXP-001 --live` | **exit 0** with `Status: COMPLETE`, writing artifacts to `results/EXP-001/` while `dry_run=False`; the PENDING_LINUX guard only fires for experiments whose registry status is `PENDING_LINUX`, and EXP-001 is `READY_FOR_LINUX`. A "live" flag therefore runs the synthetic path, silently. |
| `--seed=7` / `--seed=0` | accepted; `--seed 0` ignored (see §4) |
| `--seed 7` (space form) | accepted, exit 0, manifest seed = 7 (verified directly) |
| No arguments | prints help, exit 1 |
| `-e EXP-999` | **uncaught `KeyError` traceback** (only `RuntimeError` is caught), exit 1 |
| `--dry-run` | `store_true` with `default=True`: the flag is a no-op; `--dry-run --live` resolves to live |

---

## 6. Defect register

| ID | Severity | Defect | Suggested fix (not applied; scope was audit) |
|---|---|---|---|
| D1 | High | Local env ≠ canonical lock: 8 failing tests incl. one changing V2D-0117 ident status | Rebuild venv from `requirements.txt` (causal-learn 0.1.4.8 etc.), rerun suite |
| D2 | High | `python3.11 -m rift.experiments.run` and `make experiment[-list]` fail without `PYTHONPATH=src` | `pip install -e .`, or set `PYTHONPATH := src` in Makefile |
| D3 | High | `make test-*` targets mask pytest failures (`| tee`) | `.SHELLFLAGS := -eu -o pipefail -c` |
| D4 | Medium | `test-intervention` points to non-existent dir; passes vacuously | Create tests or retarget; fail on exit code 5 |
| D5 | Medium | `tee artifacts/logs/…` targets fail when the dir is missing | `mkdir -p artifacts/logs` in `_check-python` or per target |
| D6 | Medium | `--seed 0` silently ignored | `seed = spec_seed if self.seed_override is None else self.seed_override` |
| D7 | Medium | `--live` on a non-PENDING_LINUX experiment runs the synthetic path as "live" | Reject `--live` unless live path implemented |
| D8 | Low | Unknown experiment ID gives raw traceback | Catch `KeyError` |
| D9 | Low | `sprint451_utility_sensitivity.py` exit code 0 with 2/58 claims unverified (rounding, diff ≈ 6.4–6.8e‑4 vs tolerance 6e‑4) | Non-zero exit, or widen tolerance with justification |
| D10 | Low | `docs/recovery/TESTING_REPORT.md` counts (1013 passed / 0 failed / 12 deselected) differ from measured (1017 / 8 / 0 deselected) | Update report |
| D11 | Low | `validation_harness.py` mutates tracked artifact; `results/EXP-001` accumulates provenance files | Write to a scratch/output dir |
| D12 | Low | `config_hash` recorded as `"unknown"` in manifest | Compute hash of config |

---

## 7. State of the workspace after this run
- Files created by this gate: this document; `results/EXP-001/` (untracked, regenerated by dry-runs; now holds 26 files because provenance files accumulate), plus per-target logs in `artifacts/logs/` (git-ignored) — a stray `results/EXP-004/` I generated while testing was deleted.
- `artifacts/phase3/independent_validation_report.json` was rewritten by the harness (content identical to the pre-existing working-tree modification; MD5 `fd8d2090…`).
- No source, Makefile, or test files were modified. The working tree already contained uncommitted changes to `Makefile`, `requirements.txt`, `.github/workflows/test.yml`, `validation/run_cid_validation.py`, and others before this session, so results describe the working tree, not the `ebad911` commit.

## 8. Reproduce this gate
```bash
cd "RIFT FINAL"
make test-gate3a
python3.11 -m pytest tests/ -v -k "not linux_only"
python3.11 validation/validation_harness.py
python3.11 scripts/sprint451_utility_sensitivity.py
PYTHONPATH=src python3.11 -m rift.experiments.run --experiment EXP-001 --dry-run
```
