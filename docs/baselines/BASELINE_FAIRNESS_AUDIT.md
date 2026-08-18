# Baseline Fairness Audit
Phase: parallel-sprint
Auditor: Agent 3
Audit Date: 2025-07-14
Authority: docs/baseline_specification.md, docs/baseline_information_matrix.md

---

## Executive Summary

```
BASELINES_AUDITED: 6
FAIRNESS_PASS:     4
FAIRNESS_FAIL:     1
PENDING:           1
DEFECTS_FOUND:     2
OVERALL_STATUS:    PASS_WITH_DEFECTS
```

Four baselines (RIFT-OBS, SIEVE-LIKE, ORACLE, SAGE-CHAOS) pass all applicable
fairness criteria. RIFT-RANDOM has one structural defect (D1) that must be
resolved before claims about N3 (cost-optimization benefit) can be made.
RIFT-ONE-SHOT is pending Agent 1 implementation.

RIFT-FULL is audited only for the shared-input and safety dimensions (it has no
`run(context: IncidentContext)` adapter in `src/rift/baselines/`; it is the
reference pipeline in `src/rift/pipeline/e2e_runner.py`).

---

## Fairness Criteria Legend

| Code | Criterion |
|------|-----------|
| SAME_SCENARIO | Receives identical IncidentContext (same fault_id, window, metrics) |
| SAME_GROUND_TRUTH | Ground truth withheld during inference; not present in IncidentContext |
| SAME_INITIAL_OBS | All baselines see the same initial metric observations |
| SAME_CANDIDATE_INFO | All baselines have access to the same call_graph topology |
| SAME_BUDGET | All intervention baselines use t_budget = 600 s |
| SAME_SAFETY | All baselines subject to same safety constraints |
| NO_FUTURE_INFO | No post-intervention CID data leaks to non-intervening baselines |

---

## Per-Baseline Fairness Matrix

### RIFT-FULL
> Reference pipeline: `src/rift/pipeline/e2e_runner.py — RIFTEndToEndRunner`

| Criterion | Result | Evidence |
|-----------|--------|----------|
| SAME_SCENARIO | PASS | `RIFTEndToEndRunner` consumes the same telemetry window as all baselines (1 hr pre + 1 hr incident). `incident_window` parameter mirrors `IncidentContext.incident_window`. |
| SAME_GROUND_TRUTH | PASS | `ground_truth.json` is never opened by the pipeline runner. Scoring harness opens it post-hoc only. No `ground_truth`, `true_root_cause`, or `label` parameter in `run()`. |
| SAME_INITIAL_OBS | PASS | Consumes identical `metrics` dict from the shared serialized input path. |
| SAME_CANDIDATE_INFO | PASS | `call_graph` (`nx.DiGraph`) passed at construction; same topology source as all baselines. |
| SAME_BUDGET | PASS | `t_budget_s=600.0` (default) enforced via `SafetyController.t_budget` and `greedy_msis(t_budget=600.0)`. |
| SAME_SAFETY | PASS | `SafetyController` wired directly in `__init__`. All 8 hard stops active. Namespace restricted to `rift-eval-*`. |
| NO_FUTURE_INFO | N/A | RIFT-FULL is the source of post-intervention CID data; it does not receive it from an external source. |

**Verdict: PASS**

---

### RIFT-OBS
> `src/rift/baselines/rift_obs.py — RIFTObsBaseline`

| Criterion | Result | Evidence |
|-----------|--------|----------|
| SAME_SCENARIO | PASS | `run(self, context: IncidentContext)` — signature verified. No extra required parameters. `context.fault_id` and `context.incident_window` used directly. |
| SAME_GROUND_TRUTH | PASS | `IncidentContext` has no `ground_truth_service`, `root_cause_service`, `true_root_cause`, or `label` field (confirmed in `__init__.py`). `run()` signature contains none of these. No import of `OracleGroundTruth`. |
| SAME_INITIAL_OBS | PASS | Reads `context.metrics` and `context.baseline_stats` — same objects as all baselines. |
| SAME_CANDIDATE_INFO | PASS | Reads `context.call_graph`. Receives the same serialized G_T as RIFT-FULL per `docs/baseline_information_matrix.md §Shared G_T Protocol`. |
| SAME_BUDGET | N/A | RIFT-OBS is non-intervening. No budget consumed. `total_intervention_ed_s=0.0` confirmed at line 214. |
| SAME_SAFETY | N/A | Non-intervening baseline; no `SafetyController` needed. Correctly omitted. |
| NO_FUTURE_INFO | PASS | `cid_results=None` passed to `compute_ebd()` at line 169 — explicitly no post-intervention CID data. No CID import. Comment reads `# ← key: NO intervention data`. |

**Verdict: PASS**

---

### RIFT-RANDOM
> `src/rift/baselines/rift_random.py — RIFTRandomBaseline`

| Criterion | Result | Evidence |
|-----------|--------|----------|
| SAME_SCENARIO | PASS | `run(self, context: IncidentContext)` — signature verified. No extra required parameters. |
| SAME_GROUND_TRUTH | PASS | No `ground_truth`, `true_root_cause`, or `label` parameter in `run()` or `RandomMSIS.select()`. No import of `OracleGroundTruth`. |
| SAME_INITIAL_OBS | PASS | Reads `context.metrics` and `context.baseline_stats` — same objects as all baselines. |
| SAME_CANDIDATE_INFO | PASS | `context.call_graph` available in context; FCI run on same metric data. |
| SAME_BUDGET | **FAIL** | **See Defect D1.** `RIFTRandomBaseline.run()` never calls `self._random_msis.select()`. It runs FCI+EBD only and sets `total_intervention_ed_s=0.0`. The `RandomMSIS` class is fully implemented but is dead code in `run()`. As implemented, RIFT-RANDOM is indistinguishable from RIFT-OBS — it does not perform any interventions at all, let alone random ones. The `t_budget=600.0` field exists on the instance but is never passed to any active code path. |
| SAME_SAFETY | **FAIL** | Consequence of D1. Because no interventions are dispatched, `SafetyController` is never invoked. If/when the `run()` method is fixed to dispatch random interventions, safety constraints must be wired identically to RIFT-FULL. |
| NO_FUTURE_INFO | PASS | `cid_results=None` at line 177. No CID data used. |

**Verdict: FAIL — Defect D1 (see §Defects Found)**

---

### RIFT-ONE-SHOT
> `src/rift/baselines/rift_one_shot.py` — **file does not exist**

| Criterion | Result | Evidence |
|-----------|--------|----------|
| SAME_SCENARIO | PENDING_AGENT_1 | File not yet created. |
| SAME_GROUND_TRUTH | PENDING_AGENT_1 | — |
| SAME_INITIAL_OBS | PENDING_AGENT_1 | — |
| SAME_CANDIDATE_INFO | PENDING_AGENT_1 | — |
| SAME_BUDGET | PENDING_AGENT_1 | — |
| SAME_SAFETY | PENDING_AGENT_1 | — |
| NO_FUTURE_INFO | PENDING_AGENT_1 | **Key requirement when implemented:** RIFT-ONE-SHOT must NOT receive post-intervention posterior updates. It must use `cid_results=None` (or a single-shot CID result with no closed-loop update). The absence of closed-loop graph update must be enforced. |

**Verdict: PENDING_AGENT_1 — not blocking this sprint**

Pre-conditions for future audit:
1. `run(self, context: IncidentContext)` signature, no extra required params.
2. No import of `OracleGroundTruth`.
3. `total_intervention_ed_s` either `0.0` (if non-intervening) or accurately records actual ED.
4. If it dispatches one intervention: `SafetyController` must be wired.
5. No closed-loop posterior update after the single intervention.

---

### SIEVE-LIKE
> `src/rift/baselines/sieve_like.py — SieveLikeBaseline`

| Criterion | Result | Evidence |
|-----------|--------|----------|
| SAME_SCENARIO | PASS | `run(self, context: IncidentContext)` — signature verified. `baseline_id = "B3-SIEVE-LIKE"` (not "SIEVE") — naming obligation satisfied. |
| SAME_GROUND_TRUTH | PASS | No `ground_truth`, `true_root_cause`, or `label` parameter anywhere. No import of `OracleGroundTruth`. `IncidentContext` contains no ground-truth field. |
| SAME_INITIAL_OBS | PASS | Reads `context.metrics` and `context.baseline_stats`. Same anomaly threshold `theta_detect=3.0` as RIFT-FULL. |
| SAME_CANDIDATE_INFO | PASS | Reads `context.call_graph` for upstream propagation traversal. Same topology object. |
| SAME_BUDGET | N/A | Non-intervening (pure observational). `total_intervention_ed_s=0.0` confirmed at line 164. |
| SAME_SAFETY | N/A | Non-intervening. No `SafetyController` needed. Correctly omitted. |
| NO_FUTURE_INFO | PASS | No CID, no intervention, no PAG. Pipeline is fully observational. No post-intervention data could reach this baseline. |

**Additional fairness note:** `docs/baselines/SIEVE_LIKE.md` correctly acknowledges that SIEVE-LIKE not receiving a learned PAG or CID score is a *methodological difference*, not a fairness disadvantage. The audit agrees: this is by design.

**Verdict: PASS**

---

### ORACLE
> `src/rift/baselines/oracle.py — OracleUpperBound`

| Criterion | Result | Evidence |
|-----------|--------|----------|
| SAME_SCENARIO | PASS | `run(self, context: IncidentContext)` — signature verified. `OracleUpperBound` still reads `context.metrics` to enumerate all services for the output ranking. |
| SAME_GROUND_TRUTH | PASS (by design) | Oracle is the **sole** intentional exception to the ground-truth withholding rule. It receives `OracleGroundTruth` via a **separate privileged struct** (not via `IncidentContext`). `OracleGroundTruth` is defined in `oracle.py` and is not exported from `src/rift/baselines/__init__.py`. No other baseline imports it (confirmed by grep — only `oracle.py` defines and uses it; only `test_baseline_fairness.py` imports it for testing). |
| SAME_INITIAL_OBS | PASS | `context.metrics` is read to build the full candidate list. Same metric object as all baselines. |
| SAME_CANDIDATE_INFO | PASS | `context.metrics.keys()` used for the non-root-cause candidate list. Same topology available via context. |
| SAME_BUDGET | N/A | Non-intervening. `total_intervention_ed_s=0.0` confirmed at line 73. |
| SAME_SAFETY | N/A | Non-intervening. Correctly omitted. |
| NO_FUTURE_INFO | N/A | Oracle uses only ground-truth graph structure, not runtime post-intervention CID data. |

**Labeling check:** `baseline_id = "ORACLE-UPPER-BOUND"` (line 54). Output `notes` contains `"ORACLE UPPER BOUND"` and `"NOT a deployable RCA method"` and `"Must NOT appear in primary comparison"`. Passes the ORACLE.md critical labeling requirement.

**Verdict: PASS**

---

### SAGE-CHAOS
> `src/rift/baselines/sage_chaos.py — SageChaosStub`

| Criterion | Result | Evidence |
|-----------|--------|----------|
| SAME_SCENARIO | PASS | `run(self, context: IncidentContext)` — signature verified. |
| SAME_GROUND_TRUTH | PASS | No `ground_truth`, `true_root_cause`, or `label` in `run()` signature. No `OracleGroundTruth` import. |
| SAME_INITIAL_OBS | N/A (DEFERRED) | Stub ignores `context` and immediately returns `abstained=True`. When real implementation arrives (Phase 8), this criterion must be re-audited. |
| SAME_CANDIDATE_INFO | N/A (DEFERRED) | Same as above. |
| SAME_BUDGET | N/A (DEFERRED) | Stub never dispatches interventions. `total_intervention_ed_s` is `0.0` (default). When Phase 8 implementation arrives and interventions are dispatched, `t_budget=600.0` must be enforced. |
| SAME_SAFETY | N/A (DEFERRED) | Stub dispatches no interventions. Re-audit required at Phase 8. |
| NO_FUTURE_INFO | PASS | Stub produces no attribution and uses no data. |

**SAGE_CHAOS abstention check:** All four test seeds (42, 99, 0, 1234) verified via `TestSageChaosDeferred`. `top_candidates == []`. `notes` contains `"DEFERRED"`. **SAGE_CHAOS always ABSTAINs as required.**

**Note on `total_intervention_ed_s`:** The `SageChaosStub.run()` returns a `BaselineOutput` that inherits the dataclass default `total_intervention_ed_s=0.0`. This is correct for the stub.

**Verdict: PASS (stub phase)**

---

## Automated Parity Checks

### Present

The following fairness checks are covered by `tests/unit/baselines/test_baseline_fairness.py`:

| Test Class | Checks Covered | Baselines Covered |
|---|---|---|
| `TestSharedInputInterface` | F1: All baselines implement `BaselineInterface`; `run()` accepts only `(self, context: IncidentContext)` — no extra required params | RIFT-OBS, RIFT-RANDOM, SIEVE-LIKE, SAGE-CHAOS, ORACLE |
| `TestOutputSchema` | F2: All baselines return `BaselineOutput` with correct types; `top_candidates` are `(str, float)` tuples; scores are numeric; `baseline_id` contains expected identifier | RIFT-OBS, RIFT-RANDOM, SIEVE-LIKE, SAGE-CHAOS, ORACLE |
| `TestNoInformationLeakage` | F3: `IncidentContext` has no `ground_truth_service` or `root_cause_service`; `run()` has no `ground_truth`, `true_root_cause`, or `label` parameter; `OracleGroundTruth` is a separate struct; non-oracle baselines have no `_gt` attribute | RIFT-OBS, RIFT-RANDOM, SIEVE-LIKE, SAGE-CHAOS |
| `TestSageChaosDeferred` | F4: `SageChaosStub` always `abstained=True`; `top_candidates == []`; `notes` contains `"DEFERRED"` | SAGE-CHAOS |
| `TestOracleLabeling` | F5: `baseline_id` contains `"ORACLE"`; output notes contain `"UPPER BOUND"`; oracle attributes the correct ground-truth service | ORACLE |
| `TestSameEvaluationMetrics` | F6: `top_candidates` and `abstained` present (P@1 support); `detection_latency_s` present; `total_intervention_ed_s == 0.0` for non-intervening baselines | RIFT-OBS, RIFT-RANDOM, SIEVE-LIKE, SAGE-CHAOS |

### Missing / Recommended

The following fairness dimensions are **not covered** by existing automated tests.
These are gaps, not existing defects — Agent 1 or the integration agent should
add them in a follow-up.

| Gap ID | Missing Check | Why It Matters | Recommended Test Location |
|--------|--------------|----------------|--------------------------|
| G1 | **RIFT-RANDOM actually dispatches interventions** — no test verifies that `RIFTRandomBaseline.run()` calls `self._random_msis.select()` and incurs non-zero `total_intervention_ed_s`. | Without this, Defect D1 would not be caught automatically. The current test only checks that the output schema is valid, not that the intervention path was exercised. | `test_baseline_fairness.py::TestOutputSchema::test_rift_random_intervention_dispatched` |
| G2 | **No future info leakage (code-level)** — no test verifies that `cid_results=None` is passed to `compute_ebd()` in RIFT-OBS and RIFT-RANDOM. A regression could silently feed CID data to an observational baseline. | This is the most safety-critical fairness property for the N2 claim. | `test_baseline_fairness.py::TestNoInformationLeakage::test_rift_obs_cid_is_none` |
| G3 | **SAME_BUDGET parity** — no test verifies that RIFT-RANDOM uses `t_budget=600.0` in its MSIS call and not a different value. | Silently changing `t_budget` in one baseline would invalidate the N3 comparison. | `test_baseline_fairness.py::TestBudgetParity` |
| G4 | **RIFT-ONE-SHOT no posterior update** — once implemented, a test should assert that RIFT-ONE-SHOT does not perform a closed-loop graph update after its single intervention. | This distinguishes it from RIFT-FULL and is the defining property of the one-shot ablation. | `tests/unit/baselines/test_rift_one_shot_fairness.py` |
| G5 | **Oracle ground truth isolation** — test verifies `_gt` attribute absence on non-oracle baselines, but no test verifies that `OracleGroundTruth` is not importable from `rift.baselines` (the top-level package). It is currently only in `rift.baselines.oracle`. The import boundary should be asserted. | If `OracleGroundTruth` were accidentally re-exported from `__init__.py`, a careless developer could pass it to a real baseline. | `test_baseline_fairness.py::TestNoInformationLeakage::test_oracle_ground_truth_not_in_public_api` |
| G6 | **Shared `fault_id` echo** — no test verifies that `output.fault_id == context.fault_id` for all baselines. A mismatch would silently corrupt evaluation scoring. | The scoring harness keys results by `fault_id`. | `test_baseline_fairness.py::TestOutputSchema::test_fault_id_propagated` |
| G7 | **Same `scenario_seed` usage** — no test verifies that `context.scenario_seed` is honoured by RIFT-RANDOM for reproducibility. RIFT-RANDOM uses `self.seed` (constructor argument), not `context.scenario_seed`. These may diverge. | Reproducibility of random-selection results requires the seed to come from the scenario, not a fixed constructor default. | `test_baseline_fairness.py::TestReproducibility::test_rift_random_seed_from_context` |
| G8 | **SAGE-CHAOS Phase 8 stub gate** — no test verifies that `SageChaosStub` will fail loudly if it is given pre-labeled trace data and still returns `abstained=True` (i.e., a guard that forces re-implementation before results can be published). | Without this, a developer could forget to replace the stub and silently publish ABSTAIN results as valid Sage+Chaos comparisons. | `test_baseline_fairness.py::TestSageChaosDeferred::test_sage_chaos_stub_rejects_labeled_data` |

---

## Defects Found

### D1 — RIFT-RANDOM: `run()` never dispatches interventions (CRITICAL)

**File:** `src/rift/baselines/rift_random.py — RIFTRandomBaseline.run()` (lines 143–201)

**Description:**
`RIFTRandomBaseline.run()` builds a PAG via FCI and runs EBD — exactly as
RIFT-OBS does — and then returns `total_intervention_ed_s=0.0`. The
`RandomMSIS` class is fully implemented with `select()`, and the instance
`self._random_msis` is created in `__init__`, but `run()` never calls
`self._random_msis.select()`. No interventions are dispatched.

**Why It Matters:**
The RIFT-RANDOM baseline exists to test **N3**: *does the cost-optimized
greedy MSIS selection improve over uniform-random selection?* If RIFT-RANDOM
never dispatches any interventions, it is functionally identical to RIFT-OBS
(pure observational). Any experimental result comparing RIFT-FULL vs.
RIFT-RANDOM currently measures RIFT-FULL (interventional + greedy) vs.
RIFT-OBS (purely observational) — a different claim entirely. The N3 ablation
is currently unimplementable in this state.

Additionally, `SAME_SAFETY` is also unverifiable: when real random interventions
are dispatched, `SafetyController` must be wired to apply the same 8 hard stops
as RIFT-FULL.

**Required Fix:**
`RIFTRandomBaseline.run()` must be revised to:
1. Build the intervention candidate list from `context` (same as stage 8 of RIFT-FULL).
2. Call `self._random_msis.select(costs, candidate_posterior, theta_entropy, t_budget=self.t_budget)`.
3. Dispatch selected interventions via `NetworkInterventionEngine` with a `SafetyController` wired with `t_budget=600.0`.
4. Collect post-intervention metrics and compute CID results.
5. Propagate CID results to `compute_ebd()`.
6. Set `total_intervention_ed_s` to the actual execution duration consumed.

This fix is **Agent 1's responsibility** (owns the RIFT-RANDOM baseline source file).

**Severity:** CRITICAL for N3 claim validity.

---

### D2 — RIFT-RANDOM: `baseline_id` uses non-canonical label "B6-RIFT-RANDOM"

**File:** `src/rift/baselines/rift_random.py — RIFTRandomBaseline.baseline_id` (line 141)

**Description:**
`baseline_id` returns `"B6-RIFT-RANDOM"`. However, `docs/baseline_information_matrix.md
§Ablation Matrix` and `docs/baselines/RIFT_RANDOM.md` consistently refer to this
baseline as **RIFT-RANDOM** with no `B6` prefix. The `B6` designation belongs to
**Baseline 6 — Spectrum-Based Debugging** in `docs/baseline_specification.md §Baseline 6`.

The existing fairness test `test_rift_random_output_schema` accepts both
`"RIFT-RANDOM"` and `"B6"` (line 141: `assert "RIFT-RANDOM" in out.baseline_id or "B6" in out.baseline_id`),
which masks the collision rather than detecting it.

**Why It Matters:**
The `baseline_id` field is the primary key used by the scoring harness to aggregate
results. If the spectrum baseline (`src/rift/baselines/spectrum.py`) is ever
implemented with `baseline_id = "B6-SPECTRUM"`, there is no collision at that level,
but paper tables will show "B6-RIFT-RANDOM" in a row that documentation calls "RIFT-RANDOM",
creating a labeling inconsistency in the published comparison.

**Required Fix:**
Change `baseline_id` in `RIFTRandomBaseline` from `"B6-RIFT-RANDOM"` to
`"RIFT-RANDOM"`. Update the corresponding fairness test assertion to require an
exact match: `assert out.baseline_id == "RIFT-RANDOM"`.

**Severity:** LOW (labeling / documentation consistency). Does not affect current
experimental results but must be resolved before paper submission.

---

## Status

```
OVERALL: PASS_WITH_DEFECTS
```

The comparison framework is structurally sound. The `IncidentContext` / `BaselineOutput` /
`BaselineInterface` contract is correctly implemented by all existing baselines.
Ground-truth isolation is enforced. Oracle is correctly separated via `OracleGroundTruth`.
SAGE-CHAOS correctly abstains.

**Blocking issues before N3 claim can be made:**
- D1 must be resolved: RIFT-RANDOM must actually dispatch random interventions.

**Non-blocking before paper submission:**
- D2: label cleanup.
- G1–G8: recommended test additions for the automated test suite.

**Pending (not blocking this sprint):**
- RIFT-ONE-SHOT: awaiting Agent 1 implementation.
