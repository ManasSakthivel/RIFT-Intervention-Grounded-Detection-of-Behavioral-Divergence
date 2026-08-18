# RIFT-ONE-SHOT — Ablation Baseline for H3

**Baseline ID:** B7-RIFT-ONE-SHOT  
**Status:** IMPLEMENTED  
**Experiment:** EXP-013  
**Authority:** `docs/hypotheses.md` H3, `experiments/REGISTRY.yaml` EXP-013,  
`experiments/ablations/ABLATION_REGISTRY.yaml` RIFT-ONE-SHOT  

---

## 1. Purpose

RIFT-ONE-SHOT is the ablation baseline for **Hypothesis H3**:

> H3: Closed-Loop Model Update Improves Attribution Over One-Shot Intervention

It isolates the contribution of the iterative Bayesian posterior update (the
`closed_loop_update` component) by running the full RIFT pipeline with that
single component disabled. All other components are identical to RIFT-FULL.

---

## 2. Formal Definition (from `docs/hypotheses.md` H3)

```
H3: Precision@1(RIFT-FULL-CLOSED-LOOP) > Precision@1(RIFT-ONE-SHOT)
    on multi-cause or ambiguous fault scenarios

where RIFT-ONE-SHOT = RIFT-FULL with closed-loop update disabled
    (model is NOT updated between successive interventions)
```

**Operationalization:**
- RIFT-ONE-SHOT: runs interventions in sequence but uses the **initial candidate
  ranking** from the original G_T for all subsequent selections — no Bayesian
  update of posterior.
- RIFT-FULL-CLOSED-LOOP: updates candidate posterior and edge confidence after
  each intervention.
- Expected benefit of RIFT-FULL: converges to correct attribution in fewer
  interventions on multi-cause faults.

---

## 3. Component Configuration

| Component                | RIFT-FULL | RIFT-ONE-SHOT |
|--------------------------|-----------|---------------|
| `fci_graph_learning`     | ✅ true    | ✅ true        |
| `identifiability_check`  | ✅ true    | ✅ true        |
| `msis_cost_selection`    | ✅ true    | ✅ true        |
| `network_intervention`   | ✅ true    | ✅ true        |
| `cid_scoring`            | ✅ true    | ✅ true        |
| `ebd_scoring`            | ✅ true    | ✅ true        |
| `closed_loop_update`     | ✅ true    | ❌ **false**   |

The single disabled component is `closed_loop_update`. This means:

- `update_candidate_posterior()` is **never called** after any intervention
- `update_edge_confidence()` is **never called** after any intervention
- `update_graph_structure()` is **never called** after any intervention

---

## 4. Implementation

**File:** `src/rift/baselines/rift_one_shot.py`  
**Class:** `RIFTOneShotBaseline`

### Pipeline

1. **PAG construction:** Run FCI on metric data from `IncidentContext` (same as
   RIFT-FULL). Fall back to empty `PAGResult` if FCI cannot run.
2. **EBD detection:** Run `compute_ebd()` with `cid_results=None` to obtain
   CANDIDATE/DEFINITIVE services and anomaly scores.
3. **Initial posterior (FROZEN):** Normalize EBD anomaly scores into a
   probability distribution `P(C = service_i)`. Store this as
   `self._frozen_posterior`. **This is never mutated.**
4. **MSIS selection:** Run `greedy_msis()` using `self._frozen_posterior`. The
   FROZEN posterior is passed to every MSIS call — no update between selections.
5. **Candidate ranking:** Return `top_candidates` ordered by the FROZEN initial
   posterior scores.
6. **Output:** Return `BaselineOutput` with notes stating
   `"no closed-loop update"`.

### Key invariant

```python
# Set ONCE after EBD — never mutated thereafter
self._frozen_posterior: Dict[str, float] = dict(initial_posterior)

# Every MSIS call receives the frozen posterior
greedy_msis(costs=costs, candidate_posterior=self._frozen_posterior, ...)
```

---

## 5. Fairness Guarantee (Critical for H3)

RIFT-ONE-SHOT is **exactly identical** to RIFT-FULL except for the posterior
update. The following properties are guaranteed:

| Property                          | Guarantee |
|-----------------------------------|-----------|
| Same seed/budget/alpha/theta      | ✅         |
| Same `IncidentContext` input       | ✅         |
| Same FCI graph learning           | ✅         |
| Same EBD detection                | ✅         |
| Same MSIS cost selection logic    | ✅ (but using frozen posterior) |
| Same stopping conditions          | ✅ ENTROPY_CONVERGED / BUDGET_EXHAUSTED / SAFETY_ABORT / ALL_NON_IDENTIFIABLE |
| Posterior NOT updated after any intervention | ✅ enforced by design |
| No access to ground truth         | ✅         |
| No extra information beyond `IncidentContext` | ✅         |

---

## 6. Experiment: EXP-013

From `experiments/REGISTRY.yaml`:

```yaml
EXP-013:
  description: "Ablation: closed-loop update vs one-shot intervention (H3)"
  rq: ["RQ2"]
  hypotheses: ["H3"]
  method: "RIFT-FULL"
  baselines: ["RIFT-ONE-SHOT"]
  filter: "multi_cause_or_ambiguous"
  metrics:
    - precision_at_1
    - n_interventions_to_attribution
    - detection_latency_s
  statistical_test: "wilcoxon_one_sided"
  seed: 42
  status: "READY_FOR_LINUX"
```

H3 is tested on the `multi_cause_or_ambiguous` scenario filter. If
`Precision@1(RIFT-FULL) ≤ Precision@1(RIFT-ONE-SHOT)`, the closed-loop
update provides no measurable benefit and the N5 contribution claim must be
weakened.

---

## 7. Distinction from RIFT-FULL

| Dimension                     | RIFT-FULL                          | RIFT-ONE-SHOT                      |
|-------------------------------|------------------------------------|------------------------------------|
| Posterior after intervention  | Updated via Bayesian likelihood    | **Frozen** — never updated         |
| Graph structure update        | Yes (`update_graph_structure`)     | **No**                             |
| Edge confidence update        | Yes (`update_edge_confidence`)     | **No**                             |
| Intervention selection basis  | Latest posterior (iterative)       | Initial EBD-derived posterior      |
| Expected performance          | Higher P@1 on multi-cause faults   | Lower P@1 (ablation hypothesis)    |

---

## 8. Tests

**File:** `tests/unit/baselines/test_rift_one_shot.py`

14 tests covering:
- Interface compliance (BaselineInterface, baseline_id)
- Output schema (BaselineOutput fields, tuple types, float scores)
- Fairness (no extra run() params, no ground truth field or `_gt` attribute)
- Determinism (same seed → same result)
- **Post-intervention leakage** (frozen posterior integrity, test 13)
- Notes field audit (must mention `"no closed-loop"`)

---

*Last updated: Phase 4.5 — RIFT-ONE-SHOT implementation complete.*
