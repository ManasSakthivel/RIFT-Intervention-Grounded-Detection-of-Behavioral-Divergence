# Sprint 4.5.0 — Final Preregistration Audit

**Status: audit of the proposed preregistration (revision 3, Sprint 4.5.1). Not a result. Not fully approved (see §10: 2 BLOCKERs, 1 MUST FIX open). Sprint 4.5.1 review was internal only (seven internal agents plus a lead); it is not external independent validation.** Date 2026-11-03. Base commit `be5e0318fcd9cb17285ce6b8dff632cb68274b65`; finalised on branch `sprint-4.5.1-prereg-finalization`.
Documents audited and produced: [`PREREGISTRATION`](SPRINT4_5_0_PREREGISTRATION.md) (PRE), [`STATISTICAL_ANALYSIS_PLAN`](SPRINT4_5_0_STATISTICAL_ANALYSIS_PLAN.md) (SAP), [`CID_EXPERIMENT_DESIGN`](SPRINT4_5_0_CID_EXPERIMENT_DESIGN.md), [`DATASET_PROTOCOL`](SPRINT4_5_0_DATASET_PROTOCOL.md), and the revised [`EXECUTION_PLAN`](SPRINT4_5_0_EXECUTION_PLAN.md).

**What this work did not do.** It did not implement the experiment, generate confirmatory data, run any method on new data, change V3 or any frozen file, or open, read or parse the Sprint 4.3.0 held-out data. Its SHA-256 *string*, already stored in `datasets/rift_v2/independence_report.json`, is quoted. Two byte-level hash computations over the file did occur in Sprint 4.5.1 and are disclosed in §2 and register item X5.

**Evidence base.** All empirical numbers are from Sprint 4.3.0/4.4.0 dev and val (N = 252), which informed V3's design. They are used for calibration and for stating expectations. They are **non-confirmatory**. Scripts: `scripts/sprint450_prereg_audit.py`, `scripts/sprint450_prereg_audit_part2.py`, `scripts/sprint450_freeze_manifest.py`; outputs in `artifacts/sprint4_5_0/`.

---

## 1. Audit summary

| area | finding | action in this sprint |
|---|---|---|
| Freeze | 51 listed files are tracked and have identical SHA-256 in the working tree and at HEAD; all match the hashes in the earlier plan | manifest written; PRE §2 |
| Earlier plan §1.5 (untracked V3 dependencies) | **stale**: commit `db77446` (Sprint 4.4.1) tracked them | corrected in execution plan |
| Utility parameters | λ = 2, κ = 0.05, δ = 0.10 are **not justified by data or by an application analysis**; κ is un-normalised; δ is 25% of the attainable range | normalised cost, justification stated honestly, grid and break-even preregistered (§3) |
| N = 800 | **insufficient**: 54% power at the planning design effect | N = 2000 from ≥ 250 groups (§4) |
| Multiplicity | earlier plan inconsistent (α = 0.025 vs 0.05; m = 3 vs 4; H1′ in family) | gatekeeping, Holm over {H2, H3, H4}, V3-CIDx removed from family (§5) |
| Test | earlier plan used sign-flip and percentile bootstrap; the utility is skewed and clustered | studentised group bootstrap (§4.3, SAP §3) |
| Estimand | the 16 structures are fixed experimental strata; 250 groups are not 250 independent structural clusters; the random-structures reading would have MDE ≈ 0.18–0.25 independent of N | fixed-strata stratified estimator; claim restricted to the 16 motifs (PRE §1.1, SAP §1, §6) |
| Power | the closed-form figures (0.90 at DEFF 2) are optimistic; bootstrap-t Monte-Carlo gives 0.83 at DEFF 2 and 0.30–0.59 under a crossed family effect with the family-block rule | corrected in SAP §6.7; "inadequate at higher DEFF" stated; the earlier DEFF-cap claim retracted |
| Freeze closure | 18 import-closure files missing from the 51-file manifest | 69-file extended manifest with roles (X10) |
| Dataset generator | **frozen generator has no capacity left** (176 of 176 templates consumed; `KeyError: 'confirm'`) | new generator module, new structures (§6) |
| Held-out independence | no membership-only mechanism exists; every access path exposes content or is one-shot | exclusion by construction (§6) |
| Dose of temporal-confound scenarios | dev/val has 17 pairs per split in the drift stratum, entangled with oscillation scenarios | a designed stratum of ≥ 500 scenarios (§6, SAP §8) |
| "Robustness" clause of the research question | cannot be answered by end-to-end utility; V3 uses E0 CID unchanged | separate Phase A plus a pre-specified stratum (§7) |
| Test harness | 663 reproducible passes on a clean export (4.4.2 report: 664); 2 protected checks unavailable without the sealed materials | recorded; owner-run verification required (§9) |
| `pyproject.toml` | `requires-python >=3.10` while the canonical environment is Python 3.9.6 | changed to `>=3.9` and committed in Sprint 4.5.1 (D13; one platform, caveats in PRE §2.5) |

---

## 2. Verification of the freeze

* `scripts/sprint450_freeze_manifest.py` hashes 51 files (V3 source, evaluation scripts, evaluation/EBD/FCI/CID dependencies, baselines, scenario generator and simulator and independence code, the V3 test file and reproducibility harness, dev/val/adversarial datasets and their manifests, the lock file, the evaluation protocol). Result: 51 hashed, 51 tracked, **0 mismatches** between working tree and `HEAD`. Manifest SHA-256 at the time of writing: `609bcb9d8a9786492f045e4fe13e10e1d17518f3111814a91e5ca73b6902aeb6`.
* The dependency lock (65 lines) has SHA-256 `121304edcc036611eca354c23c6910882965bfa835822c78354c3f19a32e3fae`. The active interpreter (Python 3.9.6, numpy 2.0.2, scipy 1.13.1, scikit-learn 1.6.1, networkx 3.2.1, pandas 2.3.3, causal-learn 0.1.4.8, statsmodels 0.14.6, joblib 1.5.3, pytest 8.4.2, requests 2.32.5, momentchi2 0.1.8) matches the lock.
* Test suite on a clean `git archive HEAD` export (no held-out file present): **663 reproducible passes, 2 protected-material checks UNAVAILABLE, 0 failures** via `scripts/sprint442_run_tests.py`. Plain pytest on the same export: 663 passed, 1 skipped, 2 failed (the two protected tests, as expected without the sealed material). The 4.4.2 report quotes 664 reproducible passes in the same configuration; the difference of one is recorded and not a failure. The full tree reported 886 + 2 = 888 in 4.4.2.
* Sprint 4.5.0 did not run the sealed-material checks. **Sprint 4.5.1 ran them partially** (`artifacts/sprint4_5_1/repro/REPRO_FINDINGS.md`): `verify_freeze()` ran inside the registered protected test and passed (it hashes the sealed `rift_v2` held-out file and compares with `freeze.json`; no parse); `scripts/verify_heldout_sealed.py` ran, 4/4 PASS, but concerns the legacy `datasets/rift_faults/held_out_test.json`; harness on the owner's tree: V3 tests 34/34 and 861 of 888 harness tests executed and passed (0 failures). **27 tests were deliberately not run** because they `json.loads` sealed held-out files, and are not reported as passed (D12, BLOCKER). One **unintended** `shasum` of the Sprint 4.3.0 held-out file also occurred (value not displayed or recorded; X5).
* Eleven tracked files are modified in the working tree and many untracked historical files exist (listed by `git status`). None is in the manifest or is a V3 dependency; they were left alone and are not committed.
* **Extended manifest (X10).** A closure analysis found 18 further imported files; the 69-file extended manifest (51 + 18, with roles) is `artifacts/sprint4_5_1/freeze/extended_manifest.json`. The original 51-file manifest is unchanged. Two of the 18 (`dataset_registry.py`, `adversarial_generator.py`) were untracked and are committed in Sprint 4.5.1.

---

## 3. Utility function assessment

### 3.1 Starting point
U = correct − λ · unsafe − κ · (number of do() interventions), λ = 2, κ = 0.05, δ = 0.10, with always-abstain U ≡ 0.

### 3.2 Problems found
1. **Unsafe is defined by the label function, not by harm.** `score_one` counts an answer as unsafe if the scenario is ABSTAIN_REQUIRED (even if the named service is a true root) or the named service is wrong. Of V3's 38 answers on ABSTAIN_REQUIRED scenarios in dev/val, **18 named a true observed root** ("right service, evidence insufficient"); for V2, 25 of 52. Whether those are "unsafe" is a value judgement. The strict definition is kept as primary (reasoning: a method that cannot tell when evidence is insufficient cannot be trusted to be right next time), and the operational definition (unsafe = a wrong service) is a preregistered robustness condition. Results under both are reported. Under the operational definition V3's dev/val utility at κ = 0.05 is still negative: −0.076 (λ = 1), −0.195 (λ = 2), −0.433 (λ = 4); V2 −0.149, −0.363, −0.792.
2. **Cost is un-normalised and has no stated anchor.** "Number of do()" ranges 0–8 for V3 (mean 2.71). κ = 0.05 means 20 interventions equal one correct root, a number that is not tied to any cost. The existing cost model (`docs/intervention_cost_model.md` §K) has blast radius, SLA impact, duration, rollback and safety cost, of which only duration is simulated. Normalising by the code's own budget (MAX_DO × 30 s = 600 s, the default T_budget of the cost model) gives c = n_do/20 ∈ [0, 1], and the proposed κ = 0.05 maps to γ = 1.0 with no change to any number. Normalisation changes interpretation, not values.
3. **The scale is bounded by prevalence.** Perfect attribution at zero cost yields mean U = π = 0.393 (99/252). The ORACLE row scores 99/252 correct with 0 unsafe. **δ = 0.10 is therefore 25% of the ceiling** (the ceiling is attained only by an unattainable method: correct on every ATTRIBUTE scenario at zero cost; V3's observed minimum n_do when correct is 2, so its per-scenario ceiling is 0.90). It requires V3 to answer correctly about a quarter of all attributable incidents net of penalties. That is a large effect, and what it means must be stated, not assumed. U is **not** confined to [0, 1]: per scenario U ∈ [−(λ+γ), 1] = [−3, 1] (verified over 3276 scenario-method pairs, `artifacts/sprint4_5_1/utility/utility_verification.json`).
4. **Missed attributions score 0, so always-abstain is never charged for them.** This is conservative for the claim; it also means U cannot reward coverage. Coverage, P1 and U/π are reported so the foregone value stays visible.
5. **λ and κ are not derivable from the data or from the application as specified.** The proposal was written beside the dev/val break-even analysis, and the researcher has seen the dev/val results. The independence of the choice cannot be demonstrated.
6. **U depends on prevalence.** Break-even prevalence for V3 at λ = 2, κ = 0.05 is 0.885; at λ = 1, κ = 0.05 it is 0.667; at λ = 2, κ = 0 it is 0.663. So V3 beats always-abstain only if the mix of incidents is dominated by attributable ones.

### 3.3 Decision
Keep the form **U = C − λ·S − γ·c**, with c = n_do/20 normalised, **λ = 2, γ = 1 (= κ 0.05), δ = 0.10**, strict-unsafe primary, operational-unsafe as a robustness condition for the "useful" label, the full (λ, κ) grid and break-even values as secondary results. Reason for not replacing the proposal with a "better" alternative: any alternative chosen now would be selected with knowledge of the dev/val outcomes, and the alternatives that were examined (below) either collapse into the same quantity or add parameters that cannot be justified independently.

| alternative examined | assessment |
|---|---|
| U/π (normalised utility) | same test, ceiling 1.0 rather than 0.39; reported alongside, not a different primary |
| Operational unsafe | defensible, but would change what counts as a failure after seeing that V3 gives many right-service-wrong-evidence answers; kept as a pre-specified robustness condition |
| Coverage–risk with a precision floor λ/(1+λ) | equivalent to U at zero cost; kept as the interpretation (λ = 2 → precision ≥ 2/3) |
| Co-primary (U and unsafe rate) | doubles the family and adds no information |
| Cost-effectiveness ratio | undefined when numerator ≤ 0; unstable |
| a penalty on missed attributions | would rank always-abstain below zero and make it a different baseline; rejected because "always-abstain must remain a meaningful baseline" with U ≡ 0 |

### 3.4 Sensitivity analysis on development evidence only
Mean V3 − ALWAYS-ABSTAIN utility (dev+val, N = 252) with 95% template-cluster percentile bootstrap CI (from `audit.json` and `audit_part2.json`, B = 2000–4000; an independent recomputation, seed 4510, B = 4000, agrees in every cell to within 0.011, and the union-find-group CIs (K = 21) have the same sign pattern, `artifacts/sprint4_5_1/utility/sensitivity_grid.md`):

| λ \ κ per do() | 0 | 0.025 | 0.05 | 0.10 |
|---|---|---|---|---|
| 0.25 | +0.131 [0.08, 0.19] | +0.063 [0.01, 0.12] | −0.004 [−0.05, 0.05] | −0.140 [−0.19, −0.09] |
| 0.5 | +0.083 [0.03, 0.14] | +0.016 [−0.04, 0.07] | −0.052 [−0.11, 0.01] | −0.187 [−0.25, −0.13] |
| 1 | −0.012 [−0.08, 0.06] | −0.080 [−0.15, −0.00] | −0.147 [−0.22, −0.07] | −0.283 [−0.36, −0.20] |
| 1.5 | −0.107 [−0.20, −0.01] | −0.175 [−0.27, −0.08] | −0.242 [−0.34, −0.15] | −0.378 [−0.48, −0.28] |
| **2** | −0.202 [−0.32, −0.09] | −0.270 [−0.39, −0.15] | **−0.338 [−0.46, −0.22]** | −0.473 [−0.60, −0.35] |
| 3 | −0.393 [−0.56, −0.23] | −0.461 [−0.63, −0.29] | −0.528 [−0.70, −0.36] | −0.663 [−0.84, −0.49] |
| 4 | −0.583 [−0.80, −0.37] | −0.651 [−0.87, −0.44] | −0.719 [−0.94, −0.50] | −0.854 [−1.08, −0.63] |

Mean V3 − V2: at (λ = 2, κ = 0.05) **+0.224 [0.08, 0.37]**; CI above 0 at every cell with λ ≥ 1 and κ ≤ 0.05; at κ = 0.10 the CI includes 0 for 0.5 ≤ λ ≤ 1.5 (at λ = 0.25 it is entirely below 0, −0.049 [−0.095, −0.000]). At the primary values the union-find-group CI for V3 − AA is [−0.476, −0.202] (percentile) and [−0.514, −0.203] (studentised), K = 21 groups, rough because K is small.

* **Break-even λ\*** for V3-FULL (template-cluster 95% CI): 0.938 [0.61, 1.42] at κ = 0; 0.582 [0.31, 0.97] at κ = 0.025; 0.227 [0.00, 0.54] at κ = 0.05; negative (never beats AA) at κ = 0.10. V2: 0.456 at κ = 0; 0.208 at κ = 0.05. V3-DEFINITIVE-ONLY: 0.892 at κ = 0.
* Required answering precision for U ≥ 0 at zero cost: λ = 1 → 0.50; 2 → 0.667; 3 → 0.75; 5 → 0.833; 9 → 0.90. V3's precision among answered scenarios is 45/93 = **0.484**.
* Post-stratified by prevalence (λ = 2, κ = 0.05): π_ref = 0.2 → −0.470; 0.4 → −0.333; 0.6 → −0.196; 0.8 → −0.058 [−0.20, +0.07]. Only at the extreme 0.8 does the CI include zero.
* Prior-predictive check (4000 resamples of dev/val template clusters, seed 4502): P(mean U > 0) = 0.043 at λ = 0.5; 0.002 at λ = 0.75; 0.0003 at λ = 1; 0.000 at λ = 2 (all κ = 0.05). P(mean U ≥ 0.10) = 0 in every case. (`P = 0.000` means no draw in 4000 exceeded 0, not an exact zero.)
* Break-even λ at κ = 0 orders the tabulated methods V3-FULL (0.94) > V3-DEFINITIVE-ONLY (0.89) > V2 (0.46) > legacy (0.35) > B0-EARLIEST (0.26). **That ordering depends on κ.** Recomputed in Sprint 4.5.1: at κ = 0.05 the break-even values are legacy 0.283 > B0-EARLIEST 0.261 > V3-FULL 0.227 > V2 0.208 > V3-DEFINITIVE-ONLY −0.03; at κ = 0.10 only legacy (0.216) and B0-EARLIEST (0.261) are positive. V3 − AA changes sign near λ ≈ 1 at κ = 0 (point estimate).
* **Significance limit.** With a 95% cluster CI, V3 − AA is entirely above zero only for λ ≤ 0.61 at κ = 0 and λ ≤ 0.30 at κ = 0.025, and for no λ ≥ 0 at κ ≥ 0.05 (grid cells: λ = 0.25 with κ ≤ 0.025, and λ = 0.5 with κ = 0).

### 3.5 What the sensitivity analysis says about the choice
The conclusion about V3 vs always-abstain **depends on λ**: as a point estimate it is positive only for λ below the break-even (0.94 at κ = 0) and significantly positive only for λ ≤ 0.61 at κ = 0 and λ ≤ 0.30 at κ = 0.025, and it is negative for the proposed λ = 2. Taking the least penalising λ would be the analysis most favourable to V3 and is therefore not a justification. The proposed value is retained for the stated reasons in PRE §3.3, because it was proposed before this audit, and the break-even λ\* is a primary reported quantity, so a reader can see the answer for any other λ.

### 3.6 Is δ = 0.10 meaningful?
* As a fraction of the ceiling, 25%. In terms of precision: at zero cost and λ = 2 the break-even precision is 2/3, but at V3's dev/val answer rate (0.369) and mean cost term (0.135), U = 0 requires precision ≈ 0.79 and U = δ = 0.10 requires ≈ 0.88 (V2: 0.72 and 0.80), against an observed 0.484 for V3 (holding the answer rate and cost fixed, every non-correct answer unsafe). δ is demanding but internally consistent; it remains a judgement.
* It is an effect size chosen so that "useful" means a quarter of the attainable value. A smaller δ (0.05) is 12.7% of the ceiling and would need N ≈ 5,900 at DEFF 2 (80% power). It is not used for powering, but the interpretation table (PRE §10) separates "superior" (lo > 0) from "useful" (θ̂ ≥ δ), so a significant but small improvement is reported as such.
* δ remains a **judgement** requiring approval (D2).

---

## 4. Sample size and power audit

### 4.1 Results (details SAP §6)
**Closed-form normal approximation (optimistic; see 4.1a for the Monte-Carlo correction).** H1: one-sided α = 0.025, SD 0.969 (dev/val), δ = 0.10:

| N | DEFF 1.5 | DEFF 2.0 | DEFF 3.0 |
|---|---|---|---|
| 800 | 0.66 | 0.54 | 0.39 |
| 1200 | 0.83 | 0.71 | 0.54 |
| 1600 | 0.92 | 0.83 | 0.66 |
| **2000** | 0.96 | **0.90** | 0.76 |
| 2400 | 0.985 | 0.947 | 0.83 |
| 3000 | 0.996 | 0.979 | 0.90 |

N for 80% power: 738 (DEFF 1), 1,106 (1.5), 1,475 (2), 2,212 (3) (±1 across implementations). For 90%: 987, 1,481, 1,974 (DEFF 1, 1.5, 2). With a 20% larger SD (1.17), power at N = 2000 and DEFF 2 falls to 0.77. A single Holm over {H1…H4} (H1 at 0.00625) would give 0.78 at N = 2000 and DEFF 2, which is the reason for gatekeeping.

### 4.1a Monte-Carlo correction and the fixed-strata design (Sprint 4.5.1; SAP §6.7)
* The 0.90 at DEFF 2 above is a closed-form figure. With the studentised bootstrap-t of SAP §3, pooled layouts of 250 groups of mean size 8 give power 0.917 (DEFF 1.5), **0.831 (DEFF 2.0)**, 0.653 (DEFF 3.0) and 0.367 (DEFF 6.0). The earlier statements that realised DEFF is capped near 1.6–2.6 and that power is 90% at DEFF 2 were unsupported and are retracted.
* Researcher decision 1: the 16 structures are **fixed strata**. The estimand is the fixed-weight stratified mean; the design has three levels (structure / generator-assigned group = template / scenario), K = 256 groups with 16 per structure, group size 5–9. Under this layout power at μ = +0.10 is 0.83–0.99 for template-level ICC ≤ 0.10 with no crossed family effect, 0.65–0.83 at ICC 0.2–0.3, and **0.30–0.59 if the family-block bootstrap governs under a real crossed family effect**; a template-level bootstrap that ignores a real family effect has size 0.05–0.20. The random-structures reading (MDE 0.18–0.25, not shrinking with N) is not adopted. 256 groups are not 256 independent structural clusters, and no effective sample size is claimed.
* Power is **inadequate at higher design effects** and cannot be repaired by a larger N when the dependence is at family or structure level.

### 4.2 Assumptions and their weaknesses
* **SD** comes from dev/val, on 21 groups, with strongly heterogeneous structure means (−0.73 to +0.14). SD on new structures may be larger. Sensitivity is shown.
* **DEFF** is not known for the new design. Observed values on dev/val: 1.37 (21 union-find groups), 1.06 (105 templates), 1.07 (86 topology hashes), 2.21 (10 structures). The planning value 2.0 is deliberately between the group-level estimate and the structure-level estimate; 3.0 is the stress value. The ICC template CI [−0.14, 0.19] is wide.
* **Effect** δ = 0.10 is a *planning alternative*, not an expected value: the dev/val estimate is −0.338. The power calculation is for the case that matters for the question being answered (does a useful improvement exist?), and a decisive negative requires only about 130 scenarios (hi < 0 at 80% power, DEFF 2), so N = 2000 is not undersized for the negative outcome.
* **Normal approximation.** Verified by Monte-Carlo from the empirical dev/val utility distribution (skewness −1.09) at N = 1200 (scenario-level, unclustered, R = 2000, one-sided α = 0.025): size under the null t 0.029, sign-flip 0.0315, bootstrap-t 0.0255; power at +0.10: 0.942, 0.938, 0.930. Clustered behaviour is checked by the pre-run simulation in SAP §12.
* **Abstention rate.** V3 abstains on 63% of scenarios overall (coverage 55.6% on ATTRIBUTE; answers on 24.8% of ABSTAIN_REQUIRED). The variance of D depends on this rate. The quotas keep the abstain-required mix at dev/val proportions; a different mix changes SD.
* **Cost of heterogeneity.** If the confirmatory structures produce mean utilities that vary more than dev/val, the realised DEFF can exceed 3. That reduces power but cannot cause a false positive (the group bootstrap-t accounts for it).

### 4.3 Secondary hypotheses (under the H1 gate, Holm m = 3, N = 2000, DEFF 2)
H2 (SD 1.111): power ≈ 1.00 at +0.224, 0.79 at +0.112, 0.67 at +0.10, 0.17 at +0.05. H3: ≈ 1.00 at dev/val discordance, 0.95 at half. H4 (800 ATTRIBUTE; discordant 19:10): 0.85 at the dev/val effect, **0.23 at half**. H4 is **likely underpowered if the effect shrinks**, and a non-significant H4 is inconclusive.

### 4.4 The independent unit
The scenario (clustered into union-find groups). Telemetry windows, do() windows and service pairs are never counted. All CIs and tests resample groups.

---

## 5. Internal consistency fixes to the earlier plan

| earlier plan | issue | fix |
|---|---|---|
| §2.5: "α = 0.025 (H1 alone)" and "Holm worst case 3 tests" | family inconsistent with H1–H4 | gatekeeping: H1 alone at 0.025, then Holm over 3 |
| §6: "Holm-adjusted one-sided p < 0.05 and lower CI bound > 0" | two different α | single rule: one-sided p < 0.025 ⇔ lower bound of the 95% two-sided CI > 0 |
| §5.1: V3-CIDx added to the same family as H1′ | a system chosen with knowledge of Phase A inside the same confirmatory family; enlarges Holm | V3-CIDx moved to a future preregistration (D9) |
| §2.6: sign-flip test | symmetry assumption wrong for a skewed distribution; ignores clusters | studentised group bootstrap |
| §2.6: percentile bootstrap "at group level (template/group IDs)" | acceptable, but the percentile CI undercovers for skewed means | studentised CI as primary, percentile as sensitivity |
| §2.5: N = 800 | insufficient | N = 2000 |
| §2.3: κ unnormalised | uninterpretable | γ with c = n_do/20 |
| §4.2: reuse frozen generator | impossible | Route A |
| §4.3: "membership-only check through HeldOutGuard" | no such mode exists (`held_out_guard.py` has none; `load_v2` exposes content and is one-shot) | exclusion by construction |
| §1.5: dependency commit needed | already done in Sprint 4.4.1 | removed |
| §3.3: 9 simulated factors in a "factorial" | not enumerated | 218 cells specified |
| §3.7: type-I ≤ 0.07 in "every" cell including out-of-domain | unattainable for E3/E4/E2 outside their domains by design | declared domains plus gated false-confirmation with NOT_ASSESSABLE |

---

## 6. Dataset and independence audit
* Capacity (verified by running the frozen code, no data read): 11 × 16 = 176 templates; `cell_split` assigns dev 75, val 30, held-out 71, unassigned 0; `build_scenario` accepts only `dev`, `val`, `held_out`.
* Consequence: independence requires a **new generator** with new structures (Route A). CONFIRM then shares no template with any of the three sets by construction; it shares the simulator, the label function and the factor level sets, which is declared as a limitation (PRE L3).
* Independence from the readable sets is **measured** by `verify_independence` on label-stripped records. Independence from the sealed set is **argued** from the construction (disjoint template ids by public rule, disjoint seed tag, topology-library non-isomorphism, a similarity proxy against the readable sets with a 0.88 cap). Near-duplicate and dynamics independence from the sealed set is therefore **not directly measured**. The optional custodian count check reads the sealed file and is not recommended.
* **Group geometry (corrected).** Union-find grouping under the protocol's own periphery rule collapses to 7–11 giant groups (max 363–2,505) with only about 2,350 distinct topology hashes in the design space, so union-find components cannot be the cluster unit. The cluster unit is now the **generator-assigned group = template**: 256 templates (16 per structure), 5–9 scenarios each (max 9), each topology used once, gate K ≥ 250. Four simulated acceptance attempts accepted 1999/1999/2000/2000 of the requested 2000 within a 10,000-candidate budget per structure; the shortfall rule is in the Dataset Protocol. The earlier criteria "≥ 250 groups, max 25, ≥ 90% unique topologies" are superseded; topology uniqueness and ownership rules are in Dataset Protocol §6.
* A temporal-confound stratum is designed in by raising the natural share from the dev/val 20.6% (52/252) to ≥ 25% (about 500 scenarios): a modest +4 percentage-point increase, not a major expansion. Dev/val had 17 drift-stratum pairs per split in the V2 trace pair set (10 dev and 6 val scenarios), and 110 pairs (18 scenarios, dev) and 69 pairs (10 scenarios, val) in V3's pair set. A drift sub-quota is infeasible (drift is determined by fault shape).
* **Quotas.** The 180 SYMMETRIC_MUTUAL_DEPENDENCY quota conflicted with the 220+ scenarios the S13 and S14 mutual-pair structures need; S13/S14 now carry 90 each (X11), and the matrix sums to 2000 with column totals ATTRIBUTE 800, WEAK_SIGNAL 360, ROOT_UNOBSERVED 240, SYMMETRIC 180, INSUFFICIENT_BASELINE 180, NO_DISCRIMINATING_EVIDENCE 140, NO_FAULT 100.
* **Node-order leakage.** The root is first in the node list in 489/489 prototype scenarios and 99/99 dev+val attributable scenarios with an observed root. Frozen V3 is order-invariant on dev/val (0/252 changed); B0-EARLIEST changed in 35/252; V2 was not tested. The new generator must randomise node order, and test T10 (permutation invariance) is mandatory.
* The new generator must pass a **replication test** (identical `content_hash` for ≥ 100 dev and ≥ 50 val scenarios in legacy mode), a label-wrapper test, a determinism test and a topology non-isomorphism test, plus independent review, before the first confirmatory draw.

---

## 7. CID reliability audit

* Statement of what the data show: the CID check is a detector of between-window change. In dev/val, pairs whose outcome service has its own drift > 0.3σ were flagged "significant" in 94% (dev) and 100% (val) of non-ancestral cases against 5.6% and 6.7% for clean pairs; the drift stratum has 17 pairs per split and is confounded with oscillation/intermittent scenarios, so the mechanism is plausible but not isolated.
* Identification: with consecutive windows the treatment is deterministically in the later window, so time and treatment are perfectly confounded. By the triangle inequality, ψ₀ = W₁(A, B) satisfies Δ − κ ≤ ψ₀ ≤ Δ + κ. No statistic computed from that design can separate the effect from the natural change; more samples or a better null only sharpen the estimate of ψ₀.
* Of the compared approaches, only a concurrent control with exchangeable arms (E2), a parallel-trends control (E4), and randomised timing (E6, switchback) address identification, each under a stated assumption; detrending (E3) addresses it only inside its model class; longer windows (E1) and AR-aware nulls (E5) address detection and calibration. The design specifies, for each, the target, assumption, diagnostic and the cells where it should fail.
* **Seven core estimators E0–E6** (existing CID, longer windows, concurrent control, detrended, difference-in-differences, AR-aware, randomised switchback), plus a placebo-timing diagnostic layer E7 and a negative-control layer. 218 cells = 214 factorial + 4 mixture (reconciled in `artifacts/sprint4_5_1/cid/cell_reconciliation.md`: 210 distinct data-generating processes after 8 structurally degenerate factorial cells; 468,000 replicates = 214 × 2000 + 4 × 10,000), R = 2000 per factorial cell (10,000 per mixture cell), with negative controls (sham, placebo outcome, placebo exposure, placebo timing), and acceptance criteria declared before running. Eligibility of an estimator **never changes V3**; it leads to a separate future preregistration.
* Compute: one E0 evaluation took 6.2 ms in a timing check (n = 30, 1000 permutations, 100 bootstraps). The CID design's benchmarked estimate for all 468,000 replicates is about 14.95 CPU-hours, capped at 20 (CID design §7.1, A8); to be re-measured on a pilot.
* The module `src/rift/cid_reliability/` must first reproduce the E0 size/power and the dev/val drift-stratum false-positive counts (gate V0), because the frozen simulator cannot supply the control arm, longer windows or controlled drift.

---

## 8. Methodological risks (with severity and mitigation)

| id | risk | severity | mitigation / residual |
|---|---|---|---|
| R1 | V3 is expected to **fail** the primary endpoint at λ = 2, κ = 0.05 (dev/val mean −0.338, bootstrap P(U > 0) = 0) | n/a (not a defect) | pre-stated; negative result reported with equal prominence |
| R2 | λ, γ, δ are judgements, and the result flips with λ | high | grid, break-even λ\* and operational variant reported; primary fixed before data |
| R3 | dev/val-informed values for SD, DEFF, π | medium | stated as non-confirmatory; DEFF stress value; no re-estimation of N |
| R4 | new generator bug (manufacturing or hiding difficulty) | high | T1 replication, T2–T9, independent review, three-attempt limit |
| R5 | new structures change V3's behaviour for reasons unrelated to the claim | medium | structure-level descriptive results; limitation L3 |
| R6 | sealed-set independence argued, not measured | medium | stated; proxy threshold; optional custodian check |
| R7 | DEFF higher than 3 (a few structures dominate) | medium | lower power only; group-bootstrap validity unaffected |
| R8 | analysis script bug discovered after data | medium | script tested on dev/val reproduction and simulated tables; deviations reported; cannot change labels |
| R9 | lock/`pyproject` mismatch and protected tests unavailable outside the owner's tree | low–medium | owner-run verification (D12); D13 |
| R10 | gatekeeping makes H2–H4 "descriptive" when H1 fails; a reader may over-read H2 | medium | wording rule in PRE §5 and §10 |
| R11 | label function is the simulator's own; "ABSTAIN_REQUIRED" reflects its rules | medium | limitation L2 |
| R12 | multiple hypotheses over the sensitivity grid used to "find" a favourable cell | medium | grid is labelled secondary; the label function takes the primary only |
| R13 | Phase A artefact: new DGP may differ from the simulator | medium | gate V0 |
| R14 | post-hoc discovery of an error in the preregistration | medium | append-only amendments after a hash line; cannot alter primary rules after data |
| R15 | researcher degrees of freedom in dataset QC (rejecting candidates) | medium | quota acceptance uses state-derived labels only; every rejection logged; attempts limited |
| R16 | the simulator-based result is mistaken for real-world performance | high | language rules; PRE §10, §12 |
| R17 | all review so far is internal (agents plus lead); no external reviewer | high | not described as independent validation anywhere; D7 is a BLOCKER |
| R18 | 27 of 888 harness tests not executed (would parse sealed held-out content) | medium | not reported as passed; D12 is a BLOCKER |
| R19 | one unintended byte-level hash of the sealed file (value not seen); installed environment differs from the lock in 14 transitive pins; one platform only | low–medium | disclosed (X4, X5); no result depends on them |
| R20 | only 16 fixed structures and 16 families: crossed family dependence cannot be removed by N; the template-level test may be anti-conservative or the family-block test under-powered | high | fixed-strata claim restriction; both rules reported (D19); no effective-N claim |
| R21 | label circularity: the label function mirrors RIFT's 3σ rule and the CID power criterion; SNR [3, 4) boundary artefact | medium | SNR band reported as a stratum (D20); labels never changed |
| R22 | "designed stress set"; S10–S14 are variants of dev/val motifs | medium | novel-versus-variant table; wording rules |
| R23 | no confirmatory runner exists; error semantics were attributed to V3 in error | medium | runner hashed at G2; semantics from `benchmark_v2._timed` (D21) |

---

## 9. Items that cannot be completed without the researcher
1. Decide on, and if approved run, the full-tree test harness with `--require-protected` and store the output (D12). `verify_heldout_sealed.py` has been run (4/4) but covers the legacy set only.
2. Approve the decision register (§10).
3. Provide an independent reviewer for the generator and analysis script (D7).
4. Commit or tag the preregistration base (D1, D14).

---

## 10. Decision register (single register; all open decisions and issues)

Classification vocabulary: **BLOCKER** (the preregistration cannot be recorded or data generated until resolved), **MUST FIX** (a defect the lead or owner must correct before recording; it needs no scientific judgement), **REQUIRES RESEARCHER APPROVAL** (a judgement or authority that only the researcher can supply; the recommended value is not approved until the researcher says so), **ACCEPTED LIMITATION** (cannot be removed; stated openly), **INFORMATIONAL** (no action). This register is the only place where classifications are held. The counts quoted in PRE (status block) are verified against it by `scripts/sprint451_doc_consistency_check.py`.

| id | classification | decision or issue | recommended | where |
|---|---|---|---|---|
| D1 | REQUIRES RESEARCHER APPROVAL | freeze commit `be5e031…` plus a commit of these documents/scripts as the preregistration base; git tag | yes | PRE §14 |
| D2 | REQUIRES RESEARCHER APPROVAL | λ = 2.0, γ = 1.0 (κ = 0.05), δ = 0.10; strict unsafe primary; operational unsafe as robustness. These are normative judgements, not empirical constants | as stated | PRE §3 |
| D3 | REQUIRES RESEARCHER APPROVAL | quotas: 40% ATTRIBUTE (an experimental mix, not an operational prevalence); abstain-reason mix; drift-stratum targets | as stated | Dataset §5 |
| D4 | REQUIRES RESEARCHER APPROVAL | N = 2000 in K = 256 generator-assigned groups (16 per structure; gate K ≥ 250), fixed-strata estimand; power per SAP §6.7 (inadequate at higher DEFF) | 2000 | SAP §6 |
| D5 | REQUIRES RESEARCHER APPROVAL | gatekeeping + Holm over {H2, H3, H4} at one-sided 0.025 | as stated | SAP §5 |
| D6 | REQUIRES RESEARCHER APPROVAL | Route A (new generator module) | yes | Dataset §2 |
| D7 | BLOCKER | independent review of generator, wrapper, acceptance sampler and analysis script: no external reviewer is named, and all review so far is internal | name a reviewer | Dataset §7 T9 |
| D8 | REQUIRES RESEARCHER APPROVAL | held-out independence by construction; no custodian count | default | Dataset §8 |
| D9 | REQUIRES RESEARCHER APPROVAL | V3-CIDx outside this confirmatory family; own preregistration | yes | PRE §8 |
| D10 | REQUIRES RESEARCHER APPROVAL | approve `src/rift/cid_reliability/` and E6 | yes | CID §9 |
| D11 | REQUIRES RESEARCHER APPROVAL | missing-data handling | yes | PRE §9, SAP §7 |
| D12 | BLOCKER | protected full-tree verification is incomplete: 27 of 888 tests would parse sealed held-out content and were not run (not reported as passed); the owner decides whether to run `--require-protected` on the whole tree and stores the output. `verify_heldout_sealed.py` ran 4/4 but covers the legacy set only | decide and run | PRE §2.5 |
| D13 | REQUIRES RESEARCHER APPROVAL | `requires-python`: base commit said `>=3.10`; Sprint 4.5.1 committed `>=3.9` (one platform; build-backend and version string unchanged; CI targets 3.11) | ratify or revert | PRE §14 |
| D14 | REQUIRES RESEARCHER APPROVAL | external anchoring of the hash | signed tag | PRE §13 |
| D15 | REQUIRES RESEARCHER APPROVAL | at most 3 generation attempts, logged | 3 | Dataset §9.2 |
| D16 | REQUIRES RESEARCHER APPROVAL | binding language rules | yes | PRE §10 |
| D17 | REQUIRES RESEARCHER APPROVAL | execution smoke test ≤ 20 pilot scenarios (forking-path risk) | recommend drop | Dataset §9.1 |
| D19 | REQUIRES RESEARCHER APPROVAL | cluster unit and dependence rule: stratified template-level group bootstrap primary, family-block bootstrap as preregistered sensitivity; power 0.30–0.59 under the family-block rule with a real crossed family effect | as stated | SAP §3.1 |
| D20 | REQUIRES RESEARCHER APPROVAL | SNR [3, 5) band: report as a stratum, do not exclude | report | SAP §8.3, Dataset §5.5 |
| D21 | REQUIRES RESEARCHER APPROVAL | confirmatory runner and error semantics (exception or timeout ⇒ abstention with `error_flag`, n_do charged, 60 s), runner hashed at G2 | as stated | SAP §7 |
| D22 | REQUIRES RESEARCHER APPROVAL | pair-level robustness endpoint (false confirmation of non-ancestral pairs by drift stratum), secondary and descriptive | as stated | SAP §8.2 |
| D18 | REQUIRES RESEARCHER APPROVAL | structure set S01–S16; 0.88 proxy threshold | as stated | Dataset §3, §8.3 |
| A1–A9 | REQUIRES RESEARCHER APPROVAL | Phase A decisions (module, E6, E2 replica assumption, grids, thresholds, R, order, compute, mixtures) | as stated | CID §9 |
| X1 | INFORMATIONAL | cross-document corrections to the SAP, CID design and Dataset Protocol were integrated by the lead in Sprint 4.5.1 and the consistency checker was re-run (resolved) | none | consistency report |
| X2 | MUST FIX | the analysis script, the generator module, the replication tests and the interpretation function do not exist yet (G2); they must be written, tested on dev/val only, reviewed (D7) and hashed before G3 | write and hash | PRE §7 |
| X3 | INFORMATIONAL | `src/rift/evaluation/dataset_registry.py` (and `src/rift/benchmark/adversarial_generator.py`) were untracked; both are now tracked and committed in Sprint 4.5.1 (resolved; part of the extended manifest, X10) | none | `REPRO_FINDINGS.md` §4, §9 |
| X4 | ACCEPTED LIMITATION | the installed environment matches the lock on all direct pins but differs in 14 transitive or utility pins; only one platform (macOS arm64, CPython 3.9.6) was exercised; no cross-platform or other-Python claim is made | state it | PRE §2.5 |
| X5 | REQUIRES RESEARCHER APPROVAL | one unintended `shasum` of the sealed Sprint 4.3.0 held-out file by an agent (digest not displayed or recorded; no content read). The researcher acknowledges or rejects the deviation | acknowledge | `REPRO_FINDINGS.md` §0 |
| X6 | REQUIRES RESEARCHER APPROVAL | packaging follow-up outside this work: `pyproject.toml` has an invalid `build-backend` and a non-PEP 440 version; CI and Makefile target Python 3.11 with the older `requirements.txt`, which is not the canonical py39 lock | separate follow-up | `REPRO_FINDINGS.md` §5 |
| X7 | ACCEPTED LIMITATION | SD, DEFF and prevalence in the power analysis come from dev/val (21 union-find groups, informed V3); DEFF for the new structures is unknown; H4 is likely underpowered if its effect halves | state it | SAP §6, PRE §4 |
| X8 | INFORMATIONAL | clean-export reproducible passes are 663 here and 664 in the 4.4.2 report for the same configuration | none | PRE §2.5 |
| X9 | INFORMATIONAL | the operational-unsafe clause of POSITIVE-USEFUL cannot bind in practice (S^op ≤ S, so the operational utility is never below the strict one); it is kept as a guard | none | PRE §10 |
| X10 | INFORMATIONAL | extended freeze manifest: 69 files = 51 original + 18 closure files, with roles; the original 51-file manifest and its hash are unchanged; the extended manifest hash is held in the Sprint 4.5.1 reports | none | PRE §2 |
| X11 | REQUIRES RESEARCHER APPROVAL | quota exception: S13 and S14 carry 90 SYMMETRIC_MUTUAL_DEPENDENCY scenarios each, because the earlier 180 total could not host the 220+ those structures need | approve | Dataset §5.2 |
| X12 | REQUIRES RESEARCHER APPROVAL | CID eligibility cut-offs replace the borderline rule: k ≤ 138 of 2000 per null cell and k ≤ 557 of 10,000 per mixture cell | approve | CID §6 |

---

## 11. Language compliance
The documents use "validated on synthetic ground-truth scenarios" and "intervention-consistent". They do not use "causally accurate", "production-ready" or "guarantees" other than inside the rule that forbids them, and never call a CANDIDATE-grade CID check definitive. The consistency checker searches for this (Sprint 4.5.1 result in §13).

## 12. Validation performed
* Sprint 4.5.0 (this document's original scope): frozen-file re-hash 51/51, `git status` limited to new files plus the 11 pre-existing modified files, language search, cross-check of document numbers against `audit.json`, `audit_part2.json` and `freeze_manifest.json`.
* Sprint 4.5.1: independent re-verification by seven internal workstreams (power, utility, dataset, CID, reproducibility, documents, adversarial review). The reproducibility and protected-verification outcome is in §2; the machine-checkable consistency results are in §13. Everything is internal review. There is no external validation.

## 13. Sprint 4.5.1 consistency checklist
Produced by `python3 scripts/sprint451_doc_consistency_check.py` (read-only, re-runnable; outputs in `artifacts/sprint4_5_1/consistency/`). It checks: (A) backticked paths exist or are on a planned-path allow-list; (B) every 64-hex hash and every truncated hash is known to `freeze_manifest.json`; the document-line path-to-hash pairing; (C) 16 key numeric claims and their stale variants outside SUPERSEDED text; (D) forbidden phrases outside rule statements; (E) the manifest does not contain its own hash, contains 51 files, lists no sprint document, and no document embeds its own hash or a sibling's; all 51 frozen files match the working tree and HEAD; (F) 58 numbers recomputed from `audit.json`, `audit_part2.json` and closed-form power formulas, plus every cell of the SAP and audit power tables; (G) register ids, one classification per register row, count agreement with PRE, label set, identical research-question wording, and H5 never presented as confirmatory. The final result of the last run is recorded in `artifacts/sprint4_5_1/consistency/consistency_report.md`.
bling's; all 51 frozen files match the working tree and HEAD; (F) 58 numbers recomputed from `audit.json`, `audit_part2.json` and closed-form power formulas, plus every cell of the SAP and audit power tables; (G) register ids, one classification per register row, count agreement with PRE, label set, identical research-question wording, and H5 never presented as confirmatory. The final result of the last run is recorded in `artifacts/sprint4_5_1/consistency/consistency_report.md`.
