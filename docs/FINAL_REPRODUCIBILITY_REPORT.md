# FINAL REPRODUCIBILITY REPORT (Agent 5 — Reproducibility & Environment)

Branch: `remediation-and-manuscript-closure`. Nothing was committed or pushed. No historical artifact was modified
(`git status` is clean for `artifacts/sprint4_4_0/`, `artifacts/sprint4_4_2/`, `reproducibility/`, `datasets/rift_v2/{dev,val}.json`).
No sealed material was opened. Only `dev` / `val` were loaded.

## 1. Findings

| # | Finding | Evidence |
|---|---|---|
| F1 | Canonical results (Sprint 4.3.0 / 4.4.0) were produced on **Python 3.9.6**, numpy 2.0.2, scipy 1.13.1, scikit-learn 1.6.1, networkx 3.2.1, pandas 2.3.3, **causal-learn 0.1.4.8**. | `reproducibility/requirements-canonical-py39.lock.txt`; `artifacts/sprint4_3_0/run_metadata.json` (`python: 3.9.6`) |
| F2 | The `HEAD` `requirements.txt` (and therefore CI on Python 3.11) pinned a **different stack** (numpy 1.26.4, sklearn 1.5.0, networkx 3.3, pandas 2.2.2, **causal-learn 0.1.3.8**). Origin: Phase 3.6 pins written before the canonical lock existed; Sprint 4.4.2 documented but never reconciled them (the lock file header says "do NOT use with requirements.txt"). | `git show HEAD:requirements.txt`; `artifacts/sprint4_4_2/cross_environment_comparison.json` |
| F3 | The old stack changes the FCI PAG on 2 of 252 dev/val scenarios and flips `ident_status` of **V2D-0117** (`IDENTIFIABLE` -> `CONDITIONALLY_IDENTIFIABLE`), affecting 6 V3 records. | `artifacts/sprint4_4_2/cross_environment_comparison.json`; re-observed here (§3, negative control) |
| F4 | **The Python version (3.9 vs 3.11) is not the cause.** With identical package pins, 3.9.6 and 3.11.15 both reproduce the committed V3 records byte-for-byte (structural compare; only `runtime_s`/`mem_kb` ignored). The cause is the dependency stack, specifically causal-learn 0.1.3.8 vs 0.1.4.8. | §3 |
| F5 | The existing CI "test suite" step ran the committed tests but no step regenerated V3 outputs, so a label drift could pass CI unnoticed. | `.github/workflows/test.yml` (HEAD) |
| F6 | Latent defect found: `tests/unit/test_confirm_generator.py` and `tests/unit/test_confirm_analyze.py` computed `REPO = Path(__file__).resolve().parents[3]`. From `tests/unit/` that is the **parent of the repo**, so `dev.json`/`val.json` were "not present" and 3 tests were **silently skipped** (T1 content-hash replication x2, C4 utility sanity). | skip reasons in `pytest -rs` |
| F7 | Once un-skipped, `test_devval_utility_sanity` failed (0.119 vs -0.338). Root cause: the test used `score_one()["p2"]` (outcome accuracy, credits correct abstentions) as C_i, but the preregistered C_i is `score_one()["correct"]` (SAP §utility, `docs/SPRINT4_5_0_PREREGISTRATION.md:134`). With `correct` the value is **-0.33770 (= -0.338)**, matching the verified utility in `artifacts/sprint4_5_1/utility/utility_verification.json`. The defect was in the test only, not in `sprint450_analyze.utility`. | recomputation in §4 |

## 2. Changes made

| File | Status | Change |
|---|---|---|
| `requirements.txt` | modified (was already edited by the earlier pass; verified here) | Pins are **identical** to `reproducibility/requirements-canonical-py39.lock.txt`, plus PEP 508 markers on four backport-only packages (`backports.asyncio.runner`, `exceptiongroup`, `tomli` `<3.11`; `importlib_resources` `<3.10`) so one file installs on 3.9 and 3.11. Verified: `pip install -r requirements.txt` succeeds on 3.9.6 and 3.11.15. |
| `reproducibility/requirements-canonical-py39.lock.txt` | **unchanged** | Part of the frozen Sprint 4.5.0 manifest (sha256 `121304ed...3fae`). |
| `.github/workflows/test.yml` | modified (earlier pass; verified) | Adds step `Reproduce committed V3 dev/val records` running `scripts/final_repro_check.py`, which **executes the pipeline** and fails on any difference. CI keeps Python 3.11 and installs `requirements.txt` only (no `causal-learn` override). |
| `scripts/final_repro_check.py` | new (earlier pass; executed here) | Regenerates V3 dev/val in the current interpreter into a scratch dir; refuses to write under `artifacts/`; reports `ident_status`/`abstained`/`top`/`score` drift by name. |
| `tests/unit/test_final_reproducibility.py` | new (earlier pass; executed here) | 12 tests: requirements == lock (modulo markers), markers restricted to backports, installed causal-learn == 0.1.4.8, numeric stack == lock, CI has no causal-learn override, V2D-0117 functional regression, script refuses to write in `artifacts/`. |
| `tests/unit/test_confirm_generator.py` | edited (1 line) | `parents[3]` -> `parents[2]` (F6). |
| `tests/unit/test_confirm_analyze.py` | edited (2 lines) | `parents[3]` -> `parents[2]` (F6); C_i uses `["correct"]` instead of `["p2"]` (F7). The asserted value (-0.338, tolerance 0.05) is unchanged; no assertion was weakened. |
| `artifacts/final_closure/repro/*` | new | Evidence files listed in §5. |

## 3. Reproduction evidence (dev + val, all V3 configurations, 252 scenarios)

All runs were done in fresh venvs under `/tmp` from the repository's own `requirements.txt`.

| Environment | Python | causal-learn | numpy | `scripts/final_repro_check.py` verdict | `v3_dev.json` | `v3_val.json` | ident_status / abstained / top / score drift |
|---|---|---|---|---|---|---|---|
| A. canonical pins | 3.9.6 | 0.1.4.8 | 2.0.2 | **REPRODUCES_COMMITTED_RECORDS** | IDENTICAL | IDENTICAL | 0 / 0 / 0 / 0 |
| B. canonical pins | 3.11.15 | 0.1.4.8 | 2.0.2 | **REPRODUCES_COMMITTED_RECORDS** | IDENTICAL | IDENTICAL | 0 / 0 / 0 / 0 |
| C. **negative control**: old `HEAD` pins | 3.11.15 | 0.1.3.8 | 1.26.4 | **DIFFERS_FROM_COMMITTED_RECORDS** | 6 differences | IDENTICAL | dev ident_status **6**, others 0 |

C confirms that the check can detect the failure mode (all 6 differences are `ident_status` of V2D-0117 across the V3 variants, matching Sprint 4.4.2) and that the fix is the dependency pins, not the interpreter.
Reports: `artifacts/final_closure/repro/repro_py3.9.6_canonical_pins.json`, `repro_py3.11.15_canonical_pins.json`, `negative_control_py3.11.15_old_HEAD_pins.json`.

Scope limit: this verifies the **V3 dev/val records** (the data behind the V3 headline numbers). It does not re-run the Sprint 4.3.0 V2 evaluation or the 112-scenario adversarial cohort; V2 results were not re-verified in Agent 5's run. Platform tested: macOS arm64 only; the Linux x86-64 GitHub runner has not been observed (see blockers).

## 4. Test results (CI-equivalent harness `scripts/sprint442_run_tests.py tests`)

Run on the working tree (includes other agents' new tests), once per interpreter, with canonical pins:

| Interpreter | Passed | Failed | Skipped | Classification |
|---|---|---|---|---|
| 3.9.6 | 1012 | **1** | 3 (before fix F6/F7) | REPRODUCIBLE 1010, PROTECTED 2 (materials present locally), UNAVAILABLE 0 |
| 3.11.15 | 1012 | **1** | 3 (before fix F6/F7) | same |

After F6/F7: `tests/unit/test_confirm_generator.py` + `tests/unit/test_confirm_analyze.py` = **45 passed, 0 skipped** on both 3.9.6 and 3.11.15. `tests/unit/test_final_reproducibility.py` = **12 passed** on both. Full harness re-run on 3.11.15 after F6/F7 (`artifacts/final_closure/repro/test_classification_py3.11.15_after_fix.json`): **1015 passed (1013 reproducible + 2 protected), 1 failed, 0 skipped**. The 3.9.6 full harness was not re-run after F6/F7.

**The one remaining failure is not an environment problem:**
`tests/unit/test_sprint424_heldout_guard.py::test_sealed_script_passes_from_other_cwd` fails identically on 3.9 and 3.11 because `scripts/verify_heldout_sealed.py` (check 1/4) flags two **newly added, untracked** files that merely contain the string `held_out_test.json`:
- `tests/unit/test_dataset_leakage_checks.py` (Agent 2; asserts the loader *refuses* that path, and reads the manifest's `sealed` flag)
- `scripts/final_dataset_independence_report.py` (Agent 2; copies the manifest's sha256, never opens the file — verified: its only `read_bytes` is on `READABLE` files)

Neither opens the sealed file, so this is a false positive of a string scanner, but the gate is a safety control and **must not be weakened or skipped by Agent 5**. It is owned by Agent 2 (new files) / Agent 4-6 (the modified `verify_heldout_sealed.py`). Resolution options, owner to choose: (a) add the two paths to `ALLOWED_PATHS` in `scripts/verify_heldout_sealed.py` with a justification, or (b) rewrite those references to avoid the literal filename. Until then the CI-equivalent suite is red.

## 5. Evidence files (new, `artifacts/final_closure/repro/`)
`repro_py3.9.6_canonical_pins.json`, `repro_py3.11.15_canonical_pins.json`, `negative_control_py3.11.15_old_HEAD_pins.json`, `test_classification_py3.9.6.json`, `test_classification_py3.11.15.json`, `pip_freeze_py39.txt`, `pip_freeze_py311.txt`, `requirements_old_HEAD.txt`.
`test_classification_py3.9.6.json` and `test_classification_py3.11.15.json` were captured **before** F6/F7 and still list the 3 skips; `..._after_fix.json` is the post-fix 3.11 run.

## 6. Reproduction commands
```bash
python3.9  -m venv /tmp/e39  && /tmp/e39/bin/pip  install -r requirements.txt
python3.11 -m venv /tmp/e311 && /tmp/e311/bin/pip install -r requirements.txt
/tmp/e311/bin/python scripts/final_repro_check.py /tmp/repro --report /tmp/repro_report.json   # exit 0 iff identical
/tmp/e311/bin/python -m pytest tests/unit/test_final_reproducibility.py -q
/tmp/e311/bin/python scripts/sprint442_run_tests.py tests --tb=short --json /tmp/tc.json
```

## 7. Remaining blockers / caveats
1. **CI red until the sealed-gate false positive (§4) is resolved** by its owner. Not suppressed here.
2. CI on the real Ubuntu runner is unobserved. Resolver/BLAS differences across OS are possible; the first CI run after push will execute `final_repro_check.py` and report. Nothing was pushed.
3. `docs/ENVIRONMENT.md` still states "Python 3.9 and 3.10 are not supported" and 3.11 only; this contradicts the 3.9.6 canonical environment (empirically 3.9.6 and 3.11.15 give identical results). Not edited (documentation owned elsewhere); should be reconciled.
4. Only V3 dev/val were re-executed; V2 dev/val/held-out and the adversarial cohort were not (held-out must not be re-run).
5. `requirements.txt` changed from the committed version: any claim that "CI == canonical" is valid only once this file is committed; the lock file stays the frozen reference.
6. Historical results are unchanged and remain valid: the committed artifacts were produced on the canonical stack, which is now also what `requirements.txt` installs.
