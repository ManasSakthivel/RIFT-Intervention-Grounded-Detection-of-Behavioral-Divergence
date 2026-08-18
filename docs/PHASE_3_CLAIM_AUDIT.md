# RIFT Phase 3 — Scientific Claim Audit
**Date:** Phase 3 completion
**Status:** PASS — no forbidden claims found

---

## Scan Summary

| Forbidden Phrase | Files Scanned | Violations | Status |
|---|---|---|---|
| "causally accurate" | All .py, .md | 0 (appears only in forbidden-phrase list) | ✅ CLEAN |
| "proves causality" | All .py, .md | 0 | ✅ CLEAN |
| "demonstrates causality" | All .py, .md | 0 | ✅ CLEAN |
| "establishes causality" | All .py, .md | 0 | ✅ CLEAN |
| "causal proof" | All .py, .md | 0 | ✅ CLEAN |
| "true causal graph" | All .py, .md | 3 (all in "NOT the true causal graph" context) | ✅ CLEAN |
| "confirms causality" | All .py, .md | 0 | ✅ CLEAN |
| "causally correct" | All .py, .md | 0 | ✅ CLEAN |

---

## Mandatory Disclaimers Present

All files that describe causal inference include at least one of:

| Required Disclaimer | Present In | ✓ |
|---|---|---|
| "PAG is intervention-consistent; not the true causal graph" | `src/rift/fci/fci_runner.py` | ✅ |
| "Validated on synthetic ground-truth scenarios only" | `src/rift/ebd/ebd.py`, `src/rift/fci/fci_runner.py` | ✅ |
| "RIFT does not claim this bound" (submodularity) | `src/rift/optimizer/cost_model.py` | ✅ |
| "MSIS approximation via greedy utility maximization. Does not claim (1-1/e) guarantee" | `src/rift/optimizer/cost_model.py` | ✅ |
| "EIG is proportional to posterior mass on this service" + conservative placeholder note | `src/rift/optimizer/cost_model.py` | ✅ |
| ABSTAIN invariant enforced | `src/rift/identifiability/identifiability.py` | ✅ |
| "This is NOT Bayesian but a conservative placeholder" | `src/rift/optimizer/cost_model.py` | ✅ |
| "Bidirected edges signal potential hidden confounders" | `src/rift/fci/fci_runner.py` | ✅ |
| "boundary_limited=TRUE" on subgraph overflow | `src/rift/fci/fci_runner.py` | ✅ |

---

## Claim Status by Novelty Claim

| Claim | Code Location | Status | Limitation Documented |
|---|---|---|---|
| N1: Live do-calculus closed-loop | `src/rift/loop/closed_loop.py` | IMPLEMENTED (synthetic) | L1: confounders limit DEFINITIVE; L2: observational proxy in RIFT-OBS |
| N2: Intervention adds signal beyond observation | `src/rift/baselines/rift_obs.py` | INTERFACE READY | Not yet evaluated (Phase 10) |
| N3: Cost-optimal intervention via MSIS | `src/rift/optimizer/cost_model.py` | IMPLEMENTED | No (1-1/e) claim unless submodularity verified |
| N4: FCI-learned PAG propagation | `src/rift/fci/fci_runner.py` | IMPLEMENTED | k≤15 constraint; PAG not "causally accurate" |
| N5: Closed-loop entropy stopping | `src/rift/loop/closed_loop.py` | IMPLEMENTED | θ_stop=0.5 nats is empirically motivated |

---

## Forbidden Phrase Prevention Rules

All future code/documentation MUST NOT use:
- "causally accurate" — use "intervention-consistent" instead
- "proves causality" — use "consistent with causal hypothesis" or "supports"  
- "true causal graph" in positive claims — allowed only in "NOT the true causal graph" disclaimers
- "confirms causality" — use "intervention outcome consistent with causal hypothesis"
- Any claim that the (1-1/e) greedy bound holds unless submodularity is verified

---

## Audit Result

**PASS** — All checked. No forbidden positive claims found.
All implemented components include appropriate disclaimers.
Statistical bounds are labeled with their assumptions.
