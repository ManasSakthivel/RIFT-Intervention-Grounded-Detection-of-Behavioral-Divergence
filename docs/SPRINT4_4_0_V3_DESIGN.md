# Sprint 4.4.0 — RIFT-FULL-V3 Design

V3 is a **new, separate** method (`src/rift/attribution_v3/rift_v3.py::run_v3`). RIFT-FULL-V2 and every Sprint 4.3.0 frozen file are
unchanged (`verify_freeze()` = `(True, 'ok')`). V3 runs on **synthetic scenarios only**, with simulated interventions; it was developed on
dev, confirmed on val, and was **never run on held-out data**. All results are "validated on synthetic ground-truth scenarios" and
"intervention-consistent", nothing more.

## 1. Interface and isolation
* Signature: `run_v3(observed, intervene, scenario_id, seed, config, cache=None)`. It receives only `observe(sc)` output and an
  `intervene(x, outcomes, seed)` callable. It has no scenario / label argument (`test_run_v3_signature_has_no_scenario_argument`);
  its source is grep-tested for ground-truth identifiers (`test_v3_source_does_not_reference_ground_truth`); output is shown independent of
  labels by `test_v3_output_independent_of_ground_truth_and_labels`.
* The runner `scripts/sprint440_run_v3.py` refuses any split other than dev/val; no Sprint 4.4.0 file references `heldout_candidate`
  (`test_new_sprint440_code_never_references_heldout_data`).
* Inherited parameters (no new thresholds): `theta_detect = 3.0`, `persist = 2`, `alpha = 0.05`, CID gate (`validate_cid_for_r4`),
  30 s do() window, `MAX_DO`, 1000 permutations. **No hyper-parameter was tuned to improve a metric.**

## 2. Design choices, each tied to a measured failure

| # | V3 choice | Failure it responds to (evidence) | Empirical effect (dev / val, V3 variant vs V3-FULL) |
|---|---|---|---|
| 1 | Candidates = every EBD-R1 divergent service (no R3 filter) | Root isolated in the PAG in 8/14 dev, 5/13 val wrong-root chains; R3 treats skeleton connectivity as ancestry | `V3-R3-CANDIDATES`: P1 24/68 vs 32/68 (dev), 8/31 vs 13/31 (val); wrong roots 12 vs 7 and 9 vs 3. **Largest single contributor to P1.** |
| 2 | Outcomes of each do() = all other divergent services (graph-agnostic) | V2 outcomes limited to PAG-reachable services; reachability was symmetric and D1-affected | not ablated separately |
| 3 | PAG decoded with the corrected mark convention; used only for diagnostics and a *contradiction caveat* | D1 (collider `X o-> Z` reported UNDIRECTED); semi-directed reachability is not ancestry | re-decoding alone ≈ no change in V2; graph never selects a root |
| 4 | Positive control: do(x) also observed on x | An intervention with no detectable effect on x makes "no effect on y" uninformative | `V3-NO-MANIPULATION-CHECK`: unsafe 36 vs 35 (dev), 16 vs 13 (val); coverage 68 vs 67, 29 vs 26 |
| 5 | Holm correction over outcomes (`holm_reject`) + `validate_cid_for_r4` | Bonferroni is conservative; Holm is uniformly more powerful at the same FWER | not ablated separately |
| 6 | **Symmetry check:** services already "explained" by an earlier do() are still intervened on | V2 skipped them, hiding *mutual* effects (A13 adversarial; V2 symmetric/mutual-dependence unsafe answers: dev 9) | `V3-NO-SYMMETRY-CHECK`: unsafe 54 vs 35 and P2 104 vs 116 (dev); unsafe 23 vs 13, P2 38 vs 44 (val). **Chosen on dev, confirmed on val.** It also lowers P1: 35/68 vs 32/68 (dev), 14/31 vs 13/31 (val) — the check trades accuracy for safety. |
| 7 | **Source rule:** a source has ≥ 1 confirmed outgoing effect and none *from* another intervened service; mutual effects leave no source ⇒ abstain | V2 named mediators whose own upstream cause was never tested | part of V3-FULL |
| 8 | **Earlier-divergence guard:** an unresolved earlier divergence blocks attribution | The true root diverged earlier than the named service in 9/14 dev, 7/13 val wrong roots | `V3-NO-EARLIER-GUARD`: same as no-manipulation-check (36/16 unsafe) in this corpus |
| 9 | Decision statuses and ordinal confidence | V2's constant confidence (0.95/0.80) carried no information | see below |

## 3. Decision statuses (what V3 returns)

| status | meaning | returned as an attribution? |
|---|---|---|
| `DEFINITIVE_ROOT` | a unique interventional source, no caveats | yes |
| `QUALIFIED_ROOT` | a source, with ≥ 1 caveat: `MULTIPLE_INTERVENTIONAL_SOURCES`, `UNRESOLVED_DIVERGENCE`, `PAG_CONTRADICTS_INTERVENTION` | yes |
| `POSSIBLE_ROOT` | candidates remain but no confirmed effect (`INTERVENTION_NOT_VERIFIED`, `INTERVENTION_UNINFORMATIVE`, `SOLE_DIVERGENCE_NO_CORROBORATION`) | **never** (reported as possible roots) |
| `INSUFFICIENT_EVIDENCE` | `AMBIGUOUS_ATTRIBUTION` (confirmed effects exist but every service has a confirmed effect *from* another: mutual effects, no source), `UNRESOLVED_EARLIER_DIVERGENCE`, `INSUFFICIENT_BASELINE`, `INSUFFICIENT_SAMPLES`, `NO_CANDIDATES` | no |
| `NON_IDENTIFIABLE` | the frozen identifiability step reported non-identifiability (3 val scenarios, 0 dev) | no |

Reasons observed for V3-FULL non-answers (dev / val): POSSIBLE/INTERVENTION_NOT_VERIFIED 24 / 7; INSUFFICIENT/AMBIGUOUS_ATTRIBUTION 22 / 11;
INSUFFICIENT_BASELINE 21 / 5; INSUFFICIENT_SAMPLES 21 / 9; POSSIBLE/INTERVENTION_UNINFORMATIVE 9 / 5; POSSIBLE/SOLE_DIVERGENCE 9 / 1; NO_CANDIDATES 6 / 2;
UNRESOLVED_EARLIER_DIVERGENCE 1 / 3; NON_IDENTIFIABLE 0 / 3. About 42 of the 113 dev and 14 of the 46 val non-answers stem from telemetry that is too short to
run anything (`INSUFFICIENT_BASELINE`, `INSUFFICIENT_SAMPLES`), a limit independent of the decision rule.

**Caution on naming.** `DEFINITIVE_ROOT` means "the decision rule raised no caveat". Every underlying CID check is graded CANDIDATE (30 samples per arm;
see CID doc). Measured: 25/48 (dev) and 12/22 (val) DEFINITIVE answers were unsafe. The label is not a calibrated confidence and must not be read as
definitive causal evidence. (A rename such as `UNCAVEATED_ROOT` would be more honest; it was not done in this sprint to keep the outputs consistent with the saved artifacts and tests.)

Confidence is ordinal only: top source scores 1.0 (DEFINITIVE) or 0.5 (QUALIFIED); other interventional sources 0.25; remaining divergent candidates 0.1. It is not a probability.

## 4. Configurations (`V3_CONFIGS`)
V3-FULL (headline), V3-DEFINITIVE-ONLY (answers only DEFINITIVE), V3-NO-MANIPULATION-CHECK, V3-NO-EARLIER-GUARD, V3-R3-CANDIDATES,
V3-NO-SYMMETRY-CHECK. Ablation outcomes (dev / val): see table in §2 and FINAL_REPORT. V3-DEFINITIVE-ONLY gives the lowest unsafe counts
(dev 25, val 12) but at coverage 48/180 and 22/72 and lower P1 (23/68, 10/31).

## 5. Cost
Mean interventions per scenario: V3 2.51 (dev) / 3.19 (val) vs V2 1.49 / 1.71. Mean simulated experiment duration: 75.3 s / 95.8 s vs 44.8 s / 51.3 s.
Runtime per scenario ≈ 0.07–0.11 s vs 0.03–0.04 s. In a real system every extra do() is an intervention against a service, with a modelled 30 s
recovery per rollback (a model constant, not a measurement). Whether the gains justify this is discussed candidly in FINAL_REPORT §7.

## 6. Known limits of the design
1. CID evidence has no concurrent control arm; drift in an outcome service's own fault contribution produces spurious confirmations (CID doc §3).
2. An unobserved root cannot be distinguished from its observed descendants (adversarial A12, 7/7 unsafe for V3). This is an identifiability
   boundary: no change to the decision rule can fix it with the telemetry available.
3. `A07` (weak intervention): V3 answers 0/8 — correct behaviour for ABSTAIN but a lost attribution if an answer was possible.
4. V3's contradiction check needs a PAG relation to be present; with recall 0.35–0.42 a missing edge is not evidence either way.
5. The dev set informed choices 1, 6, and the adversarial generator; val was used to confirm, not as an independent test. No held-out
   confirmation of V3 exists, and none was permitted in this sprint.
6. DEFINITIVE naming (above).
