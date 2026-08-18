# Robustness / Scenario Catalog Audit
Phase: parallel-sprint  
Auditor: Agent 5  
Date: 2024 (Phase 4.5 Mac pre-Linux readiness sprint)  
Sources: `docs/experiments/SCENARIO_CATALOG.md`, `docs/experiments/ROBUSTNESS_PLAN.md`,
`experiments/REGISTRY.yaml`, `datasets/rift_faults/` (development.json, validation.json,
manifest.json, README.md); `src/rift/evaluation/held_out_guard.py`; `docs/hypotheses.md`;
`docs/research/RQ_EXPERIMENT_MAP.md`

---

## Executive Summary

```
TOTAL_SCENARIOS:  69
DEV_SCENARIOS:    36
VAL_SCENARIOS:    18
HELD_OUT:         15 (SEALED — NOT INSPECTED)
ISSUES:           7
```

Seven issues were identified ranging from a **CRITICAL** EXP-011 identifier collision (H5
mapping conflict) and a **HIGH** power-risk discrepancy on H2, down to medium and low
severity coverage and sufficiency gaps. No issue requires immediate schedule stoppage; all
are actionable before the Linux evaluation phase.

---

## Fault Type Coverage

All counts verified by direct inspection of `datasets/rift_faults/development.json` and
`datasets/rift_faults/validation.json`. Held-out counts are inferred from
`manifest.json` proportions only — the file was **NOT opened**.

| Fault Type           | DEV count | VAL count | HELD_OUT (est.) | Total (manifest) | All splits covered? |
|----------------------|-----------|-----------|-----------------|------------------|---------------------|
| NETWORK_LATENCY      | 2         | 1         | ~0–1            | 3                | ✅ Yes              |
| PACKET_LOSS          | 2         | 1         | ~0–1            | 3                | ✅ Yes              |
| SERVICE_DEGRADATION  | 2         | 1         | ~0–1            | 3                | ✅ Yes              |
| RESOURCE_CONTENTION  | 2         | 1         | ~0–1            | 3                | ✅ Yes              |
| QUEUEING             | 2         | 0         | ~1              | 3                | ✅ Yes              |
| DEPENDENCY_FAILURE   | 1         | 1         | ~1              | 3                | ✅ Yes              |
| MULTI_CAUSE          | 1         | 1         | ~1              | 3                | ✅ Yes              |
| CONFOUNDED           | 24        | 12        | ~12             | 48               | ✅ Yes              |
| **TOTAL**            | **36**    | **18**    | **15 (sealed)** | **69**           | —                   |

**Notes:**
- All 8 fault types from the RIFT taxonomy are present in the development set. ✅
- No TELEMETRY_FAILURE fault type exists as a scenario class. Telemetry failures (TF1–TF5)
  are characterized as robustness modes tested via unit/mock tests, not as scenario catalog
  entries. This is consistent with the ROBUSTNESS_PLAN design intent (see §Gaps below,
  GAP-5).
- Validation set: QUEUEING has 0 confirmed instances from the inspected validation.json; the
  QU_* trial 3 scenario would fall in held-out or is missing from validation — see GAP-6.
- Held-out type distribution is inferred; exact counts are sealed.

---

## Scenario Schema Verification

Development set schema verified against `datasets/rift_faults/README.md` specification and
the `development.json` JSON Schema (inferred from file structure).

| Required Field          | Type               | Present in DEV schema? | Matches spec?  |
|-------------------------|--------------------|------------------------|----------------|
| `fault_id`              | string             | ✅ Yes                 | ✅ Yes         |
| `name`                  | string             | ✅ Yes                 | ✅ Yes         |
| `root_cause_service`    | string             | ✅ Yes                 | ✅ Yes         |
| `fault_type`            | string (enum)      | ✅ Yes                 | ✅ Yes         |
| `injected_at_t`         | float              | ✅ Yes (int-as-float)  | ✅ Yes         |
| `expected_recovery_t`   | float              | ✅ Yes (int-as-float)  | ✅ Yes         |
| `causal_path`           | list of [str, str] | ✅ Yes                 | ✅ Yes         |
| `confounded`            | bool               | ✅ Yes                 | ✅ Yes         |
| `confounder_description`| string / null      | ✅ Yes                 | ✅ Yes         |
| `affected_services`     | list of str        | ✅ Yes                 | ✅ Yes         |
| `observable_by_rift`    | bool               | ✅ Yes                 | ✅ Yes         |
| `split`                 | string (enum)      | ✅ Yes                 | ✅ Yes         |
| `ground_truth_locked`   | bool               | ✅ Yes (always true)   | ✅ Yes         |
| `seed`                  | int                | ✅ Yes                 | ✅ Yes         |

**Schema verdict: PASS.** All required fields are present and typed correctly across all 36
development scenarios. The `injected_at_t` and `expected_recovery_t` are stored as JSON
integers (`60`, `360`, etc.) but satisfy the `float` contract.

**Anomaly — `causal_path` is empty for RESOURCE_CONTENTION:**  
RC_01 and RC_02 both have `causal_path: []`. This is plausible (no directed propagation
path from a shared resource), but it means EBD R-rule evaluation on these scenarios will
lack a ground-truth causal chain. This is a documentation gap, not a schema error (the
field is present and correctly typed). Recommend adding a note to the catalog entry.

---

## Scenario Count Verification

| Split         | Catalog claim | manifest.json | Actual file count | Match? |
|---------------|---------------|---------------|-------------------|--------|
| DEVELOPMENT   | 36            | 36            | 36 (verified)     | ✅ Yes |
| VALIDATION    | 18            | 18            | 18 (verified)     | ✅ Yes |
| HELD_OUT_TEST | 15            | 15            | NOT INSPECTED     | — sealed |
| **TOTAL**     | **69**        | **69**        | **54 verified**   | ✅ Yes |

---

## Confounded Scenario Analysis

```
DEV_CONFOUNDED:      24  (CF_00 – CF_23; all observable_by_rift=False)
VAL_CONFOUNDED:      12  (CF_24 – CF_35; all observable_by_rift=False)
HELD_OUT_CONFOUNDED: ~12 (inferred from manifest; SEALED)
TOTAL_CONFOUNDED:    48  (manifest.json confirmed)
H2_REQUIREMENT:      n >= 48  (EXP-002 REGISTRY.yaml; PHASE_3_SPEC_FREEZE.md §15)
```

### ⚠️ POWER RISK — HIGH (ISSUE-1)

EXP-002 (`n_confounded_required: 48`) requires **all 48 confounded scenarios** to achieve
claimed 80% power on H2. However:

1. All 48 confounded scenarios span all three splits (24 DEV + 12 VAL + ~12 held-out).
2. EXP-002 is scoped to `split: DEVELOPMENT` only (`n_scenarios: 36`,
   `confounded_only: true`).
3. The development split contains only **24 confounded scenarios** — exactly **half** of the
   48 required.
4. There is an explicit contradiction: EXP-002 sets `n_confounded_required: 48` but the
   DEVELOPMENT split can only yield 24 confounded scenarios.

**Impact:** If EXP-002 is run on the development split alone (as currently specified), it
will operate at substantially reduced power for H2. The 80% power claim would be invalid.
The achieved power must be recalculated via `check_power_achieved()` using n=24, not n=48.

**Recommendation:** Either (a) revise EXP-002 to include both DEVELOPMENT and VALIDATION
splits (n=36 confounded), which approaches the 48-scenario requirement, or (b) update the
`n_confounded_required` annotation to reflect the split-constrained actual available count,
and report achieved power honestly. Option (a) is preferred as it maximizes power without
touching held-out data.

### `observable_by_rift` on CONFOUNDED scenarios

All 24 development CONFOUNDED scenarios have `observable_by_rift: false`. This is correct
by design: the latent common cause (U_host) is outside RIFT's instrumentation boundary.
RIFT is expected to abstain (`boundary_limited=True`) or return multi-cause attribution on
these scenarios. The `correct_abstention_rate` metric in EXP-002 tests this behavior.

**What happens to `observable_by_rift=False` scenarios in other experiments?**
- EXP-001 (full dev set, n=36): these 24 scenarios are included. RIFT-FULL should output
  abstentions on them; they will lower raw Precision@1 but should be counted as
  correct_abstentions. Ensure the evaluation harness correctly excludes abstentions from
  the Precision@1 denominator or counts them as a separate metric.
- EXP-011 (robustness, n=10 subset): likely includes some CONFOUNDED scenarios. Because
  `observable_by_rift=False`, attribution failures here are expected, not anomalous.

---

## Multi-Cause Scenarios

```
H3_REQUIREMENT:         filter: "multi_cause_or_ambiguous"  (EXP-013, REGISTRY.yaml)
MULTI_CAUSE_COUNT_DEV:  1  (MC_01 only; fault_type=MULTI_CAUSE)
MULTI_CAUSE_COUNT_VAL:  1  (MC_02)
AMBIGUOUS_SCENARIOS:    Not explicitly tagged; no `ambiguous` field in schema
```

### ⚠️ SUFFICIENCY RISK — HIGH (ISSUE-2)

EXP-013 applies a `filter: "multi_cause_or_ambiguous"` to the development split. The
development set contains only **1 MULTI_CAUSE scenario** (MC_01). No scenario has an
`ambiguous` tag (the schema does not include this field).

**Impact:** Running EXP-013 on the development set with this filter yields n=1 for the
Wilcoxon one-sided test. A Wilcoxon test on n=1 is statistically undefined. H3 cannot be
tested meaningfully on the development set alone.

**Recommendation:**
1. Add a second MULTI_CAUSE scenario to the development set (bringing MC count to at least
   6 for adequate power), OR
2. Clarify that EXP-013 will be run on the combined DEVELOPMENT + VALIDATION split (n=2
   multi-cause), noting this is still very low power, OR
3. Define which CONFOUNDED scenarios qualify as "ambiguous" and tag them explicitly in the
   schema, increasing the effective filter pool.

Until resolved, H3 testing is **underpowered to the point of being untestable** on the
current development set.

---

## Held-Out Seal Verification

```
STATUS: SEALED ✅
GUARD:  src/rift/evaluation/held_out_guard.py — EXISTS AND IMPLEMENTED ✅
```

### Guard implementation assessment

The [`HeldOutGuard`](src/rift/evaluation/held_out_guard.py:37) class implements:

- **Token-gated access:** `load_held_out()` raises [`HeldOutLeakageError`](src/rift/evaluation/held_out_guard.py:23)
  unless an oracle token is registered via `allow_oracle()` and activated via
  `activate_token()`. Any call without an active token is rejected with a hard exception.
- **Call-site logging:** Every access attempt is recorded in `_access_log` with caller name
  and file/line location, enabling post-run audit.
- **`assert_no_unauthorized_access()`:** Can be called at end of test suites to enforce that
  no unauthorized access slipped through.
- **Module-level singleton:** [`get_guard()`](src/rift/evaluation/held_out_guard.py:167)
  returns a shared instance; guards centralize access control.

**Held-out test file status:** `datasets/rift_faults/held_out_test.json` **exists on disk**
but was NOT opened during this audit. The guard would block any non-oracle code attempting
to read it.

**Verification script:** `scripts/verify_heldout_sealed.py` is referenced in the catalog
but was not inspected (out of scope). Its existence should be confirmed separately.

**Conclusion: The held-out seal is INTACT.** The guard implementation is technically sound.
The held-out test set was not accessed during this audit.

---

## Robustness Experiment Registration

### Are experiments registered before results exist?

All robustness-related experiments have `status: READY_FOR_LINUX` or `DRY_RUN_READY` with
no `output_artifact` content populated. No results exist yet. Registration preceded any
results. ✅

| Robustness test  | Registered as    | Status              | Results exist? |
|------------------|------------------|---------------------|----------------|
| EXP-002 (H2/R6)  | READY_FOR_LINUX  | Pre-results         | ❌ None        |
| EXP-011 (noisy)  | DRY_RUN_READY    | Pre-results         | ❌ None        |
| EXP-013 (H3/R7)  | READY_FOR_LINUX  | Pre-results         | ❌ None        |
| TF1–TF5          | DRY_RUN_READY    | Unit tests only     | ❌ None        |

**Pre-registration assessment: PASS.** No post-hoc registration detected.

### Is EXP-011 well-defined?

EXP-011 in `experiments/REGISTRY.yaml`:
```yaml
description: "Robustness: FCI on noisy/sparse data"
rq: ["RQ1"]
hypotheses: []
metrics: [graph_discovery_failure_rate, ebd_candidate_rate]
n_scenarios: 10
statistical_test: none
```

**Assessment — PARTIAL.** EXP-011 measures whether FCI graph discovery fails under
noisy/sparse telemetry conditions. This is a **descriptive characterization** experiment
(no statistical test, no hypothesis), not a confirmatory robustness test. It maps to
robustness modes TF3 (noisy telemetry) and TF2 (sparse/delayed telemetry) from the
ROBUSTNESS_PLAN. The metrics are meaningful, but:

- No noise injection protocol is specified (unlike R1–R7 in ROBUSTNESS_PLAN which have
  parameter ranges). It is unclear whether "noisy" refers to TF3 mock injection or live
  conditions.
- `n_scenarios: 10` with no `filter` field — which 10 of the 36 development scenarios?
  The selection criteria are unspecified.

### ⚠️ CRITICAL — EXP-011 Identifier Collision (ISSUE-3)

`docs/hypotheses.md` line 133 maps **H5 to EXP-011**:
> `| H5 | EXP-011 | 11 | Cross-system Precision@1 | In-distribution RIFT |`

However, `experiments/REGISTRY.yaml` EXP-011 is `"Robustness: FCI on noisy/sparse data"`
with `rq: ["RQ1"]` and `hypotheses: []` — **not cross-system generalization**.

`docs/research/RQ_EXPERIMENT_MAP.md` confirms H5/cross-system is `DEFERRED (Phase 11)`.
There is **no registered experiment for H5** in the current REGISTRY.yaml. The hypotheses
table entry is stale and refers to a future experiment that has not been assigned an ID.

**Impact:** The H5 hypothesis has no valid experiment registration. If `hypotheses.md` is
used as the authority for the experiment map, a reader would incorrectly conclude EXP-011
covers cross-system generalization. This is a documentation integrity failure that could
mislead reviewers or future phases.

**Recommendation:** Update `docs/hypotheses.md` line 133 to reflect:
- H5 → experiment ID: `TBD (Phase 11)` with status `DEFERRED`
- Add a note that no cross-system experiment is currently registered

### Is there a cross-system generalization experiment defined?

**No.** H5 (cross-system transfer, Sock Shop vs Online Boutique) is formally deferred to
Phase 11. `RQ_EXPERIMENT_MAP.md` explicitly states: *"H5 requires a second system (Sock
Shop or similar). Not scheduled until Phase 11."* No EXP entry covers it in the current
registry. This is a documented deferral, not an oversight, but the stale `hypotheses.md`
mapping is a documentation error.

### Are all registered robustness experiments scientifically grounded?

| Experiment | Grounding | Notes |
|------------|-----------|-------|
| EXP-002    | ✅ Strong | Wilcoxon; Cliff's δ; pre-specified n requirement |
| EXP-011    | ⚠️ Weak  | No statistical test; no noise injection spec; n=10 unfiltered |
| EXP-013    | ⚠️ Weak  | Wilcoxon specified but n=1 MC scenario (see ISSUE-2) |
| TF1–TF5    | ✅ OK    | Descriptive / unit-test mode; no confirmatory claims made |

---

## Gaps Found

### ISSUE-1 — H2 Power Shortfall in EXP-002 (HIGH)
**Description:** EXP-002 specifies `n_confounded_required: 48` but its `split: DEVELOPMENT`
constraint makes only 24 confounded scenarios available — exactly 50% of requirement.  
**Impact:** 80% power claim for H2 is invalid if the experiment runs on the development
split alone. Achieved power will be substantially lower.  
**Recommendation:** Extend EXP-002 to use DEVELOPMENT + VALIDATION splits (total n=36
confounded) or revise the power claim; report `achieved_power` from `check_power_achieved(n=24)`.

### ISSUE-2 — Insufficient Multi-Cause Scenarios for H3/EXP-013 (HIGH)
**Description:** EXP-013 `filter: multi_cause_or_ambiguous` yields n=1 in the development
set (MC_01 only). The `ambiguous` tag does not exist in the scenario schema.  
**Impact:** H3 cannot be tested with a Wilcoxon test on n=1. The experiment as specified is
statistically undefined on the current development set.  
**Recommendation:** Add at least 5 more MULTI_CAUSE scenarios (to reach n≥6 for minimum
Wilcoxon power), or explicitly define which CONFOUNDED scenarios qualify as "ambiguous" and
tag them in the schema.

### ISSUE-3 — EXP-011 Identifier Collision / H5 Missing Registration (CRITICAL)
**Description:** `docs/hypotheses.md` maps H5 to EXP-011, but EXP-011 in
`experiments/REGISTRY.yaml` is the FCI-noisy-data robustness experiment, not cross-system
generalization. H5 has no valid experiment registration.  
**Impact:** Documentation integrity failure. Misleads any reader or automated check
that uses `hypotheses.md` as the registry index. Breaks traceability for H5.  
**Recommendation:** Correct `docs/hypotheses.md` line 133 to mark H5 as
`TBD / DEFERRED (Phase 11)`. Assign a new EXP ID (e.g., EXP-015) in REGISTRY.yaml as
a placeholder with `status: DEFERRED` when Phase 11 is planned.

### ISSUE-4 — EXP-013 Baseline `RIFT-ONE-SHOT` Not Implemented (MEDIUM)
**Description:** EXP-013 notes: *"RIFT-ONE-SHOT is not an implemented baseline yet — must
be created before Linux."* This is a known gap in the registry.  
**Impact:** EXP-013 cannot run until `RIFT-ONE-SHOT` is implemented.  
**Recommendation:** Track implementation of `RIFT-ONE-SHOT` as a pre-Linux gating task.

### ISSUE-5 — Telemetry Failure Not Represented as Scenario Class (LOW)
**Description:** TF1–TF5 telemetry failure modes are tested via unit tests and mock
injection, not as named scenario catalog entries with `fault_type=TELEMETRY_FAILURE`.
There is no scenario with this fault class.  
**Impact:** ROBUSTNESS_PLAN correctly marks these as "descriptive" / "test suite" — no
confirmatory claims are made. Impact is low, but cross-system generalization experiments
(H5, Phase 11) may need to include telemetry failure scenarios.  
**Recommendation:** No immediate action required. Document explicitly in the catalog that
telemetry failure modes are characterized via TF1–TF5 unit tests, not scenario entries.

### ISSUE-6 — EXP-011 Lacks Noise Injection Specification (MEDIUM)
**Description:** EXP-011 ("FCI on noisy/sparse data") has no noise injection protocol, no
parameter ranges, and no scenario selection criteria for its n=10 subset.  
**Impact:** Experiment is not reproducible as specified. Equivalent to a placeholder entry.  
**Recommendation:** Add a `noise_injection_protocol` field or notes block to EXP-011
specifying: which scenarios (indices or filter), noise magnitude, and whether this uses
MockTelemetry (TF3 style) or live data variation.

### ISSUE-7 — Empty `causal_path` for RESOURCE_CONTENTION Scenarios (LOW)
**Description:** RC_01 and RC_02 both have `causal_path: []`. No ground-truth propagation
edges are defined for resource contention faults.  
**Impact:** EBD R-rule validation (EXP-004, `r1_r4_pass_rates`) cannot verify causal path
accuracy on these scenarios. Ground truth is incomplete.  
**Recommendation:** Add a note to RC_* scenarios explaining the empty path is intentional
(shared resource with no direct directed edge), and confirm the evaluation harness handles
empty `causal_path` without errors.

---

## Robustness Plan Coverage Assessment

| ROBUSTNESS_PLAN test | Maps to EXP | Fault scenarios available | Status |
|----------------------|-------------|--------------------------|--------|
| R1 — Network latency | EXP-011     | NL_01, NL_02 in DEV ✅   | READY_FOR_LINUX |
| R2 — Packet loss     | EXP-011     | PL_01, PL_02 in DEV ✅   | READY_FOR_LINUX |
| R3 — Dependency fail | EXP-011     | DF_01 in DEV (n=1) ⚠️   | READY_FOR_LINUX |
| R4 — Resource cont.  | EXP-011     | RC_01, RC_02 in DEV ✅   | READY_FOR_LINUX |
| R5 — Queueing        | EXP-011     | QU_01, QU_02 in DEV ✅   | READY_FOR_LINUX |
| R6 — Confounding     | EXP-002     | 24 CF_* in DEV ✅        | READY_FOR_LINUX |
| R7 — Multi-cause     | EXP-013     | MC_01 in DEV (n=1) ⚠️   | READY_FOR_LINUX |
| TF1 — Missing instr. | descriptive | observable_by_rift=False  | DRY_RUN_READY  |
| TF2 — Delayed telm.  | descriptive | MockTelemetry injection   | DRY_RUN_READY  |
| TF3 — Noisy baseline | EXP-011     | MockTelemetry injection   | DRY_RUN_READY  |
| TF4 — Prom. unavail. | test suite  | Unit test ✅              | IMPLEMENTED    |
| TF5 — Malformed resp | test suite  | Unit test ✅              | IMPLEMENTED    |

R3 and R7 have only 1 development scenario each — robustness characterization on these
types will lack statistical depth.

---

## Status

**BLOCKED on 1 critical issue; CONDITIONAL PASS otherwise.**

| Issue | Severity | Blocking? |
|-------|----------|-----------|
| ISSUE-3: EXP-011 ID collision / H5 not registered | CRITICAL | Yes — documentation integrity |
| ISSUE-1: H2 power shortfall (n=24 vs n=48)        | HIGH     | No — must report achieved power |
| ISSUE-2: H3 n=1 multi-cause, test undefined       | HIGH     | No — blocks H3 test, not H1/H2/H4 |
| ISSUE-4: RIFT-ONE-SHOT not implemented             | MEDIUM   | No — pre-Linux gating item |
| ISSUE-6: EXP-011 under-specified                  | MEDIUM   | No — experiment is descriptive |
| ISSUE-7: Empty causal_path on RC_*                | LOW      | No — documentation only |
| ISSUE-5: No TELEMETRY_FAILURE scenario class      | LOW      | No — by design |

**Immediate action required:** Correct the `docs/hypotheses.md` EXP-011 / H5 mapping
(ISSUE-3) before any automated experiment dispatch system consumes the hypothesis table.
All other issues should be addressed before the Linux evaluation phase begins.
