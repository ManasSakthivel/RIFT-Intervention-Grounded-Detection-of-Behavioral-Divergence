# Phase 3.5 — Safety Validation
**Gate 3.5I | Status: PASS**

---

## 1. All 8 Hard Stops Verified

| Hard Stop | Phase | Test Status | Notes |
|---|---|---|---|
| KILL_SWITCH | 3 + 3.5 | ✅ PASS | `activate_kill_switch()` + subsequent block |
| PRODUCTION_NAMESPACE | 3 | ✅ PASS | Non-`rift-eval-*` namespace → SAFE_ABORT |
| UNAUTHORIZED_TARGET | 3 | ✅ PASS | Service not in `approved_targets` → SAFE_ABORT |
| BUDGET_EXCEEDED | 3 | ✅ PASS | `cumulative_ed + proposed_ed > T_budget` |
| CASCADE_FAILURE | 3 | ✅ PASS | `error_rate > 0.5` for > 30s |
| UNEXPECTED_BLAST_RADIUS | 3 | ✅ PASS | Non-target service anomaly > 2σ |
| **DATA_MUTATION_ATTEMPT** | **3.5 — NEW** | ✅ **PASS** | `candidate.mutates_data=True` OR `intervention_type='DATA_WRITE'` |
| **ROLLBACK_FAILURE** | **3.5 — NEW** | ✅ **PASS** | `rollback_succeeded=False` → SAFE_ABORT + kill-switch |

**Test run: `python3 -m pytest tests/integration/safety/test_safety_35.py -v` → 10/10 PASS**

---

## 2. DATA_MUTATION_ATTEMPT Implementation

Added to `assess_pre_intervention()` in [`src/rift/safety/safety.py`](../../src/rift/safety/safety.py):

```python
# Hard stop 4: Data mutation attempt
if (
    getattr(candidate, "mutates_data", False)
    or getattr(candidate, "intervention_type", "") == "DATA_WRITE"
):
    return SafetyAssessment(
        decision=SafetyDecision.SAFE_ABORT,
        hard_stop_reason=HardStopReason.DATA_MUTATION_ATTEMPT, ...
    )
```

**RIFT never mutates application data.** This hard stop fires before blast-radius checks and cannot be bypassed by `human_override=True`.

---

## 3. ROLLBACK_FAILURE Implementation

New method `assess_post_rollback()` in [`src/rift/safety/safety.py`](../../src/rift/safety/safety.py).

Called **after every rollback attempt**.

Triggers SAFE_ABORT if:
- `rollback_succeeded=False` (tc command failed or returned non-zero)
- `rollback_record.rollback_attempts > 3` (excessive retry detected)

**Also activates the kill-switch** — preventing any further intervention attempts until the environment is reset.

This is a safety-critical state: a failed rollback means an active tc rule may still be affecting traffic. Operator action is required before RIFT can resume.

---

## 4. Invariants Verified

| Invariant | Test | Result |
|---|---|---|
| `human_override` cannot bypass DATA_MUTATION | `test_human_override_cannot_bypass_data_mutation` | ✅ PASS |
| `human_override` cannot bypass subsequent blocked interventions after rollback failure | `test_human_override_cannot_bypass_rollback_failure` | ✅ PASS |
| Rollback failure activates kill-switch atomically | `test_rollback_failure_activates_kill_switch` | ✅ PASS |
| Kill-switch blocks all subsequent interventions | `test_rollback_failure_blocks_subsequent_interventions` | ✅ PASS |
| Clean rollback does not activate kill-switch | `test_successful_rollback_returns_approved` | ✅ PASS |
| > 3 rollback attempts triggers abort | `test_excessive_rollback_attempts_triggers_abort` | ✅ PASS |

---

## 5. Remaining Concerns (from hostile review)

1. **Rollback partial state**: If `tc filter del` succeeds but `tc qdisc del` fails, the qdisc remains. The implementation logs `all_ok=False` but marks `status=ROLLED_BACK` regardless. This should be tightened — `assess_post_rollback(rollback_succeeded=False)` should be called if any rollback command fails. **(P1)**

2. **DATA_MUTATION detection depends on caller setting the flag**: The `mutates_data` check relies on the `InterventionCandidate` having the field set. This is a soft check — there is no way to prevent a caller from constructing a candidate without the field. Document this as a design limitation. **(P2)**

3. **SAFE_ABORT during INTERVENE**: If SAFE_ABORT is reached while tc is mid-execution, the rollback has not yet been called. The closed-loop state machine must call `rollback_all()` when transitioning to SAFE_ABORT from INTERVENE. This integration point must be verified during live E2E testing. **(P1)**

---

Artifact: [`artifacts/phase3_5/safety_validation.json`](../../artifacts/phase3_5/safety_validation.json)
Test file: [`tests/integration/safety/test_safety_35.py`](../../tests/integration/safety/test_safety_35.py)
