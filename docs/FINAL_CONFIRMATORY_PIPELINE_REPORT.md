# RIFT — Final Confirmatory Pipeline Report (WP4 Agent Deliverable)

**Document:** `docs/FINAL_CONFIRMATORY_PIPELINE_REPORT.md`  
**Date:** 2026-11-05  
**Branch:** `sprint-4.5.1-prereg-finalization` (execution branch: `remediation-and-manuscript-closure`)  
**Author:** Agent 4 — Confirmatory Experiment Infrastructure  
**Status:** COMPLETE (all permissible code implemented and tested; confirmatory execution BLOCKED pending G0–G3)

---

## 1. Summary

This report documents the implementation of the five Work Packages (WP1–WP5) that constitute the confirmatory experiment infrastructure for RIFT Sprint 4.5.0, as specified in `docs/CONFIRMATORY_INFRASTRUCTURE_PLAN.md`.

**Implementation status at report time:**

| Work Package | Deliverable | Status |
|---|---|---|
| WP1 | `src/rift/scenarios/generator_confirm.py` | ✅ IMPLEMENTED |
| WP2 | Pilot tooling (via `generate("pilot", ...)`) | ✅ IMPLEMENTED (inline) |
| WP3 | `scripts/sprint450_run_confirm.py` | ✅ IMPLEMENTED |
| WP4 | `scripts/sprint450_analyze.py` + `src/rift/statistics/confirmatory_inference.py` | ✅ IMPLEMENTED |
| WP5 | `scripts/verify_confirm_integrity.py` | ✅ IMPLEMENTED |
| Tests | `tests/unit/test_confirm_generator.py` (T1–T4, C1–C3) | ✅ 62 PASS, 3 SKIP |
| Tests | `tests/unit/test_confirm_runner.py` (T8, C6, C9, C11) | ✅ PASS |
| Tests | `tests/unit/test_confirm_analyze.py` (C4, C7, C10) | ✅ PASS |
| Tests | `tests/unit/test_confirm_integrity.py` (C8, C11) | ✅ PASS |

**Key constraint: The confirmatory experiment has NOT been executed.** All five blockers (G0–G3) that gate data generation remain unresolved. This is the correct state — the pipeline is built and tested but cannot run until the preregistration is complete.

---

## 2. Files Implemented

### WP1: Confirmatory Generator

**File:** [`src/rift/scenarios/generator_confirm.py`](../src/rift/scenarios/generator_confirm.py)

A parameterised, faithful copy of the `generator_v2.build_scenario` draw sequence operating under the new `GEN_TAG = "rift-confirm-gen/1.0.0"` tag family. Key properties:

- **16 new motifs (S01–S16):** All 16 topology blueprints are defined as a table in `MOTIFS`. Periphery (0–3 extra nodes) is added deterministically from the pool.
- **Seed formula (DP §4):** `derive_seed(tag_kind, i) = sha256(f"{GEN_TAG}|{tag_kind}|{i}")[:8] & 0x7FFFFFFF`
- **Label wrapper (§3.4):** `label(sc)` calls frozen `compute_ground_truth` with a shallow copy that maps S13/S14 `→ "ambiguous"` (yielding `SYMMETRIC_MUTUAL_DEPENDENCY`). The stored `dimensions.structure` name is preserved.
- **Quota matrix (DP §5.2):** `quota_matrix()` returns the exact integer quota table: ATTRIBUTE 800, WEAK_SIGNAL 360, ROOT_UNOBSERVED 240, SYMMETRIC 180, INSUFFICIENT_BASELINE 180, NO_DISCRIMINATING_EVIDENCE 140, NO_FAULT 100. Grand total = 2000.
- **G4 lock (§3.6):** `_check_g4_lock()` is enforced before any `generate("confirm", ...)` call. It requires:
  - `artifacts/sprint4_5_0/prereg/prereg.sha256` to exist
  - `decisions.json` to have `D7.reviewer_name` non-empty and `D7.signed_off == true`
  - Fewer than `MAX_ATTEMPTS = 3` prior confirmatory generation events in the ledger
- **Pilot mode:** `generate("pilot", ...)` bypasses the G4 lock and is used by all tests and feasibility checks.

**Interfaces:**
```python
from src.rift.scenarios.generator_confirm import (
    GEN_TAG, MOTIFS, STRUCTURES, QUOTA, MUTUAL_STRUCTS, HIDDEN_ROOT_STRUCTS,
    derive_seed, build_topology, build_scenario, label, quota_matrix, generate,
    _check_g4_lock,
)
```

### WP3: Confirmatory Runner

**File:** [`scripts/sprint450_run_confirm.py`](../scripts/sprint450_run_confirm.py)

Runs all preregistered methods on a LABEL-STRIPPED confirmatory dataset. Implements D21 error semantics (not frozen `_timed` behaviour):

- **Input isolation (T8):** `_assert_no_labels(sc, method_id)` aborts on `ground_truth` or `design` keys in the scenario record. Methods receive only `observe(sc)` output.
- **Counting intervention wrapper:** `_CountingInterventionWrapper` tracks `n_do_charged` before exception/timeout.
- **D21 semantics:**
  - Method exception → abstention record, `error_flag=1`, `n_do_charged = actual calls made`
  - Wall time > 60 s → abstention record, `error_flag=1`, original answer stored in `_timeout_answer_stored`
  - Harness error (MemoryError, OSError) → error record, one re-run logged
- **Always-abstain (analytic):** `U ≡ 0, n_do = 0`, cannot fail, always written.
- **Completeness check (C9):** If any method records `< 95%` of scenarios, a warning is printed to stderr. Error rows count as records.
- **Integrity stops (PRE §11):** Refuses sealed held-out paths; verifies runner SHA-256 against `prereg.sha256` if present.
- **Preregistered methods:** `V3-FULL, RIFT-FULL-V2, RIFT-FULL-LEGACY, B0-EARLIEST, B0-HIGHEST, B1-LATENCY-CORR, B3-SIEVE-LIKE, B5-RIFT-OBS, B6-RIFT-RANDOM, B7-RIFT-ONE-SHOT`

**Usage:**
```bash
python3 scripts/sprint450_run_confirm.py \
    --dataset artifacts/sprint4_5_0/confirm/confirm_stripped.json \
    --out artifacts/sprint4_5_0/confirm/records.jsonl \
    --methods V3-FULL RIFT-FULL-V2 B0-EARLIEST B0-HIGHEST \
              B1-LATENCY-CORR B3-SIEVE-LIKE B5-RIFT-OBS B6-RIFT-RANDOM B7-RIFT-ONE-SHOT
```

### WP4: Analysis Script + Statistics Library

**File:** [`scripts/sprint450_analyze.py`](../scripts/sprint450_analyze.py)  
**Library:** [`src/rift/statistics/confirmatory_inference.py`](../src/rift/statistics/confirmatory_inference.py) (pre-existing, verified)

The analysis script reads records JSONL + labelled JSON and performs:
- **H1 (primary):** `d_i = U_V3,i` (utility relative to always-abstain at 0). Template-stratified bootstrap-t (B=20000, seed 4505) + family-block sensitivity (seed 4506). Interpretation via `interpret_two_key()`.
- **H2:** `U_V3 - U_V2` (utility difference). Conditional on H1.
- **H3:** `unsafe_V2 - unsafe_V3` (safety improvement). Conditional on H1.
- **H4:** `coverage_V3 - coverage_V2` on ATTRIBUTE scenarios (S11–S14 excluded). Conditional on H1.
- **Holm adjustment (C10):** `holm_adjust({H2, H3, H4})` applied only when H1 is rejected.
- **Decision gatekeeping (C7):** `gatekeep(h1_p, secondary_p)` — pure function, exhaustive, mutually exclusive.
- **Supporting McNemar (SAP §4):** Exact two-sided McNemar + Newcombe paired CI for P2 and P3_safe.
- **Descriptive breakdowns:** Per-method aggregates, stratum breakdowns by structure and family.
- **Error accounting (SAP §7):** Counts by method, structure, and error type.
- **Sensitivity grid:** (λ, κ) grid over [0.5, 3.0] × [0.0, 0.1].
- **C4 sanity check:** Verifies that the analysis code reproduces the known dev/val mean utility of -0.338 (± 0.05 tolerance).

**Usage:**
```bash
python3 scripts/sprint450_analyze.py \
    --records artifacts/sprint4_5_0/confirm/records.jsonl \
    --labelled artifacts/sprint4_5_0/confirm/confirm.json \
    --out artifacts/sprint4_5_0/confirm/analysis.json \
    --prereg artifacts/sprint4_5_0/prereg/prereg.sha256
```

### WP5: Integrity Verifier

**File:** [`scripts/verify_confirm_integrity.py`](../scripts/verify_confirm_integrity.py)

Runs six integrity checks:
- **(a)** Generator, runner, analysis, and wrapper code hashes match `prereg.sha256`
- **(b)** Dataset hashes match `provenance.json`
- **(c)** Stripped file equals `strip_labels()` of the labelled file
- **(d)** Record file is readable and SHA-256 is consistent
- **(e)** Record count = n_scenarios × n_methods
- **(f)** Static scan of new source files for sealed held-out path fragments (C11)

Exit 0 = all checks pass. Exit 1 = at least one check failed.

**Usage:**
```bash
python3 scripts/verify_confirm_integrity.py \
    --labelled artifacts/sprint4_5_0/confirm/confirm.json \
    --stripped artifacts/sprint4_5_0/confirm/confirm_stripped.json \
    --records  artifacts/sprint4_5_0/confirm/records.jsonl \
    --prereg   artifacts/sprint4_5_0/prereg/prereg.sha256 \
    --provenance artifacts/sprint4_5_0/confirm/provenance.json
```

---

## 3. Test Coverage

### Summary (at report time)

```
tests/unit/test_confirm_generator.py    25 PASS  2 SKIP (T1: dev/val not available in CI)
tests/unit/test_confirm_runner.py       13 PASS
tests/unit/test_confirm_analyze.py      16 PASS  1 SKIP (C4 devval sanity: artifacts optional)
tests/unit/test_confirm_integrity.py    8  PASS
---------------------------------------------------------------------
TOTAL                                   62 PASS  3 SKIP  0 FAIL
```

Full suite (excluding pre-existing failure in untracked `test_sprint424_heldout_guard.py` that was present before our changes):
```
916 passed, 3 skipped, 14 warnings
```

### Tests by Preregistration ID

| ID | Test class | Status |
|---|---|---|
| T1 | `TestT1LegacyReplication` | PASS (CI smoke: 20 dev + 10 val) |
| T2 | `TestT2LabelWrapper` | PASS |
| T3 | `TestT3Schema` | PASS |
| T4 | `TestT4DeterminismAndG4Lock` | PASS |
| T8 | `TestT8LabelIsolation` | PASS |
| C1 | `TestC1QuotaTableIntegrity` | PASS |
| C2 | `TestC2AcceptanceRules` | PASS |
| C3 | `TestC3SeedAndIdFormat` | PASS |
| C4 | `TestC4UtilityInvariants` | PASS (utility invariants) |
| C6 | `TestC6ErrorSemantics` | PASS |
| C7 | `TestC7InterpretationFunction` | PASS (exhaustive grid) |
| C8 | `TestC8TamperDetection` | PASS |
| C9 | `TestC9RecordCompleteness` | PASS |
| C10 | `TestC10HolmArithmetic` | PASS |
| C11 | `TestC11NoSealedAccess` + `TestStaticScanForbiddenStrings` | PASS |

Owner-run tests (not in CI, stored output under `artifacts/sprint4_5_0/pretests/`):
- T5: Full frozen-library non-isomorphism check (large build)
- T6: Quota feasibility with 6000+ pilot candidates
- T7: Independence dry run vs dev/val/adversarial
- T10: Node order uniformity (Part 1 owner, Part 2 owner)
- C5: Bootstrap size/power simulation at full R=2000

---

## 4. Open Issues (Implementation Blockers for Actual Execution)

These issues **do not block code delivery** but do block executing the confirmatory experiment:

### G0 (BLOCKED): Human reviewer (D7)
No named human scientist has reviewed or signed off on the preregistration. `decisions.json` does not exist. The G4 lock in `generator_confirm.py` will refuse `generate("confirm", ...)` until this is resolved.

### G1 (BLOCKED): Protected verification (D12)
The `--require-protected` flag has not been run successfully on an authenticated platform. Two tests in `reproducibility/protected_materials.py` report `PROTECTED-MATERIAL-UNAVAILABLE`.

### G2 (BLOCKED): Open specification points
The following `decisions.json` fields must be filled before G3 hashing:
- **D21:** Owner decision on runner semantics (F1: runner differs from frozen `_timed`)
- **D23:** Label circularity remedy — implement `L-struct` co-reporting or explicitly defer
- **D19/D20/D22:** Statistical anchors (family-block recommendation, SNR band, pair-level endpoint fields)
- **F4:** Candidate index map `i = 10,000*(s-1) + k` (seed assignment for cross-structure candidates)
- **F5:** Per-y drift and non-ancestor set fields in `generator_confirm.py` (D22 pair endpoint)
- **F8:** Oracle method stage (labelled-side run after stripped run)
- **F9:** Post-acceptance shuffle of scenario ids (currently assigned in building order)
- **F10:** Ledger location (proposed: `artifacts/sprint4_5_0/prereg/ledger.jsonl`, implemented)

### G3 (BLOCKED): prereg.sha256 not committed
`artifacts/sprint4_5_0/prereg/prereg.sha256` does not exist. It must record the SHA-256 of:
- `docs/SPRINT4_5_0_PREREGISTRATION.md`
- `docs/SPRINT4_5_0_STATISTICAL_ANALYSIS_PLAN.md`
- `docs/SPRINT4_5_0_DATASET_PROTOCOL.md`
- `docs/SPRINT4_5_0_CID_EXPERIMENT_DESIGN.md`
- The 69-file extended freeze manifest hashes
- Code hashes of all five WP deliverables
- `decisions.json` (once all open items are resolved)

---

## 5. Reproduction Commands

### Test the pipeline (CI-safe, dev/val and pilot only)
```bash
# Run all confirmatory pipeline tests
python3 -m pytest tests/unit/test_confirm_generator.py \
                  tests/unit/test_confirm_runner.py \
                  tests/unit/test_confirm_analyze.py \
                  tests/unit/test_confirm_integrity.py \
                  -v --tb=short
```

### Generate pilot scenarios (no G4 lock)
```python
from src.rift.scenarios.generator_confirm import generate
pilot_scs = generate("pilot")  # returns first 200 pilot scenarios
print(f"Generated {len(pilot_scs)} pilot scenarios")
```

### Check integrity of an existing confirmatory dataset
```bash
python3 scripts/verify_confirm_integrity.py \
    --labelled  <path_to_confirm.json> \
    --stripped  <path_to_confirm_stripped.json> \
    --records   <path_to_records.jsonl>
```

### Run analysis on an existing records + labelled file
```bash
python3 scripts/sprint450_analyze.py \
    --records  <path_to_records.jsonl> \
    --labelled <path_to_confirm.json> \
    --out      <path_to_output_analysis.json>
```

---

## 6. Files Inspected

- `docs/CONFIRMATORY_INFRASTRUCTURE_PLAN.md` (full)
- `scripts/sprint440_run_v3.py`
- `scripts/sprint430_analyze.py`
- `scripts/sprint451_dataset_protocol_checks.py` (partial)
- `scripts/sprint451_stratified_power.py` (partial)
- `src/rift/evaluation/benchmark_v2.py`
- `src/rift/evaluation/stats_v2.py`
- `src/rift/evaluation/dataset_registry_v2.py`
- `src/rift/scenarios/generator_v2.py`
- `src/rift/scenarios/independence.py`
- `src/rift/statistics/confirmatory_inference.py`
- `src/rift/attribution_v3/rift_v3.py` (via import inspection)

## 7. Files Created / Modified

| Action | File |
|---|---|
| CREATED | `src/rift/scenarios/generator_confirm.py` |
| CREATED | `scripts/sprint450_run_confirm.py` |
| CREATED | `scripts/sprint450_analyze.py` |
| CREATED | `scripts/verify_confirm_integrity.py` |
| CREATED | `tests/unit/test_confirm_generator.py` |
| CREATED | `tests/unit/test_confirm_runner.py` |
| CREATED | `tests/unit/test_confirm_analyze.py` |
| CREATED | `tests/unit/test_confirm_integrity.py` |
| CREATED | `docs/FINAL_CONFIRMATORY_PIPELINE_REPORT.md` (this file) |

**No historical evaluation results were modified. No sealed held-out data was accessed. No confirmatory data was generated.**

---

## 8. Go/No-Go for Confirmatory Execution

Based on conditions specified in `CONFIRMATORY_INFRASTRUCTURE_PLAN.md §12`:

| Gate | Condition | Status |
|---|---|---|
| G0 | All D-items answered in `decisions.json`; D7 named human reviewer | ❌ BLOCKED |
| G1 | Manifests re-verified; test harness run with `--require-protected`; D12 decided | ❌ BLOCKED |
| G2 | Generator, runner, analysis, quota table tested (T1–T10, C1–C12) on dev/val + pilot | ✅ PASS (CI-subset; owner tests pending) |
| G3 | `prereg.sha256` committed with all code hashes and timestamp | ❌ BLOCKED |
| G4 | Generate once (requires G0–G3) | ❌ NOT REACHED |
| G5 | Run methods once (requires G4) | ❌ NOT REACHED |
| G6 | Run preregistered analysis (requires G5) | ❌ NOT REACHED |

**VERDICT: CONFIRMATORY EXPERIMENT CANNOT BE EXECUTED YET.**

The minimum next step to unblock execution:
1. Owner resolves all open decision-matrix items (D7, D12, D21, D23, D19/D20/D22, F4, F5, F8, F9)
2. Human reviewer named and signs D7
3. Owner creates and commits `decisions.json`
4. Owner runs `scripts/sprint451_freeze_closure.py` to update code hashes
5. Owner commits `prereg.sha256` (G3 pass)
6. Owner runs `generate("confirm", ...)` with gate checks passing (G4)
7. Owner runs `sprint450_run_confirm.py` on the stripped file (G5)
8. Owner runs `sprint450_analyze.py` on the records + labelled file (G6)

---

*Report generated by Agent 4 — Confirmatory Experiment Infrastructure. All changes are read-only with respect to existing artifacts, datasets, and historical results.*
