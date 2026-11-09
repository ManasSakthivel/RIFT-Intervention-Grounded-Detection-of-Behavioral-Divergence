# RIFT Sprint 3.1 — Baseline Independence & Mechanism Audit

**Audit Date:** 2026-11-02  
**Lead Auditor:** Baseline Evaluation & Independence Auditor  
**Authority:** Task 4 Baseline Mechanism Verification  

---

## 1. Dissection of Identical Aggregate Baseline Scores (22/30 = 73.3%)

`B0-HIGHEST`, `B1-LATENCY-CORR`, `B6-RIFT-RANDOM`, and `B4-RIFT-ONE-SHOT` produced identical family-level and aggregate scores across the adversarial cohort:

```
┌──────────────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬───────────┐
│ Method           │ A:Invert │ B:Retry  │ C:Conf   │ D:Multi  │ E:Noise  │ F:Deep   │ Total     │
├──────────────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼───────────┤
│ B0-HIGHEST       │ 5 / 5    │ 0 / 5    │ 3 / 5    │ 5 / 5    │ 4 / 5    │ 5 / 5    │ 22 / 30   │
│ B1-LATENCY-CORR  │ 5 / 5    │ 0 / 5    │ 3 / 5    │ 5 / 5    │ 4 / 5    │ 5 / 5    │ 22 / 30   │
│ B6-RIFT-RANDOM   │ 5 / 5    │ 0 / 5    │ 3 / 5    │ 5 / 5    │ 4 / 5    │ 5 / 5    │ 22 / 30   │
│ B4-RIFT-ONE-SHOT │ 5 / 5    │ 0 / 5    │ 3 / 5    │ 5 / 5    │ 4 / 5    │ 5 / 5    │ 22 / 30   │
└──────────────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴───────────┘
```

### Mechanism Explanation:
1. **Decision Rule Convergence:**  
   - `B0-HIGHEST` ranks by $\max_t |z_t|$.
   - `B1-LATENCY-CORR` ranks by $z / (1 + \text{delay})$. In steady-state synthetic windows (180s), delay penalty is small relative to $z$-score amplitude differences.
   - `B6-RIFT-RANDOM` and `B4-RIFT-ONE-SHOT` construct their initial prior over candidate services using EBD $z$-scores ($\max_t |z_t|$).
2. **Behavior on Each Family:**
   - **Family A (Inverted):** Steady-state root amplitude ($z=5.5$) exceeds victim amplitude ($z=4.5$) $\implies$ all 4 pick root (5/5).
   - **Family B (Retry Storm):** Client retry storm inflates child amplitude ($z=8.0$) above root amplitude ($z=3.5$) $\implies$ all 4 falsely pick child (0/5).
   - **Family C (Confounding):** Both services have $z=5.0$; tie-breaking ordering selects root in 3/5 cases across all 4.
   - **Family D (Multi-Cause):** Root has $z=5.0 \implies$ all 4 pick root (5/5).
   - **Family E (Noisy Telemetry):** Noise variance causes 1 false peak in scenario 3 $\implies$ all 4 score 4/5.
   - **Family F (Deep Cascades):** Root has $z=5.0 \implies$ all 4 pick root (5/5).

---

## 2. Unit Testing Baseline Independence

Added verification tests in `tests/unit/baselines/test_baseline_independence.py` to confirm that each baseline executes distinct decision logic and that RandomMSIS implements genuine uniform pseudo-random selection under distinct seeds.
