# Agent 2 (utility / decision theory): recommended document edits — Sprint 4.5.1

Evidence: `scripts/sprint451_utility_sensitivity.py` → `utility_verification.json`, `sensitivity_grid.json`, `sensitivity_grid.md`
(same directory). Development evidence only (dev+val, N = 252); **non-confirmatory**; seed 4510; B = 10 000 (primary), 4 000 (grid).
Nothing here selects a weight. The values λ = 2, γ = 1, δ = 0.10 are **kept unchanged**; the edits correct wording, add exact
bounds, and add immutability language. No doc file was edited by Agent 2 — the lead integrates.

Abbreviations: PRE = `SPRINT4_5_0_PREREGISTRATION.md`, SAP = `SPRINT4_5_0_STATISTICAL_ANALYSIS_PLAN.md`,
AUD = `SPRINT4_5_0_FINAL_PREREGISTRATION_AUDIT.md`, PLAN = `SPRINT4_5_0_EXECUTION_PLAN.md`.

---

## 0. Verdict

All numerical utility claims in PRE/SAP/AUD reproduce from scratch (56 of 58 checked claims inside tolerance; the other two are
rounding, see §1). The scorer re-implementation matches the saved `score` for **3 276 / 3 276** (scenario, method) pairs on
`answered`, `correct`, `unsafe`. Three **wording errors** (not numeric errors) were found (§2). The weights stay; the specification is sound
as a *normative* choice, with the bound and precision statements below corrected.

## 1. Verified-vs-claimed (selected; full 58-row table in `utility_verification.json → verified_vs_claimed`)

| claim (location) | claimed | recomputed | status |
|---|---|---|---|
| γ = 1 ⇔ κ = 0.05 per do() (PRE §3.1) | γ = 20κ | γ = 1.000; U identical on all 252 V3 scenarios | verified |
| V3 mean U at (λ = 2, γ = 1) (PRE §3.5, AUD §3.4, SAP §6) | −0.338 | −0.3377 | verified |
| V3 template-cluster 95% CI | [−0.465, −0.219] | [−0.461, −0.217] (seed 4510, B = 10 000) | verified within 0.01 (SAP §12 step 4 tolerance) |
| V3 union-find-group 95% CI (K = 21) | not stated | pct [−0.476, −0.202]; studentised [−0.514, −0.203] | new, add to AUD §3.4 |
| V3 template studentised CI | not stated | [−0.472, −0.222] | new |
| V2 mean U | −0.562 | −0.5619; CI [−0.712, −0.413] | verified |
| V3 − V2 | +0.224 [0.085, 0.365] | +0.2242 [0.086, 0.366]; groups [0.085, 0.401] | verified |
| SD / skewness of V3 U | 0.969 / −1.09 | 0.9692 / −1.092 | verified |
| P(bootstrap mean U > 0) | 0.000 | 0.0000 (10 000 draws), template and group | verified |
| Break-even λ* V3, κ = 0 | 0.938 [0.61, 1.42] | 0.9375 [0.614, 1.436]; groups [0.603, 1.489] | verified |
| λ* V3, κ = 0.025 / 0.05 / 0.10 | 0.582 [0.31, 0.97] / 0.227 [0.00, 0.54] / negative | 0.5823 [0.308, 0.985] / 0.2271 [−0.010, 0.550] / −0.483 [−0.715, −0.255] | verified |
| λ* V2 κ = 0 / 0.05; V3-DEF κ = 0; Legacy κ = 0; B0-EARLIEST κ = 0 | 0.456 / 0.208; 0.892; 0.351; 0.26 | 0.456 / 0.208; 0.892; 0.351; 0.2606 | verified (B0 rounds to 0.261, not 0.26) |
| Operational mean U, V3 λ = 1/2/4, κ = 0.05 | −0.076/−0.195/−0.433 | −0.0758/−0.1948/−0.4329 | verified |
| Operational mean U, V2 | −0.149/−0.363/−0.792 | −0.1492/−0.3635/−0.7921 | verified |
| Full strict V3−AA grid (AUD §3.4, 28 cells, mean and CI) | as tabulated | every cell within 0.0105 of recomputed (CI differences are bootstrap-seed noise) | verified |
| Break-even prevalence π* (λ,κ) = (2,.05)/(1,.05)/(2,0) (AUD §3.2.6) | 0.885 / 0.667 / 0.663 | 0.885 / 0.666 / 0.663 | verified |
| Post-stratified V3 U at π_ref .2/.4/.6/.8 (AUD §3.4) | −0.470/−0.333/−0.196/−0.058 | −0.470/−0.333/−0.196/−0.058 | verified |
| V3 precision among answered | 45/93 = 0.484 | 0.4839 | verified |
| "Lucky-correct": V3 18 of 38 answers on ABSTAIN_REQUIRED; V2 25 of 52 | 18/38, 25/52 | 18/38, 25/52 | verified |
| Lucky decomposition (new) | — | V3: WEAK_SIGNAL 14, NO_DISCRIMINATING_EVIDENCE 4. V2: WEAK_SIGNAL 12, NO_DISC 4, **SYMMETRIC_MUTUAL_DEPENDENCY 9** | new (see §4) |
| V3 38 answers on ABSTAIN_REQUIRED by reason | WEAK_SIGNAL 18, NO_DISC 9, ROOT_UNOBSERVED 8, SYMMETRIC 2, NO_FAULT 1 | identical | verified |
| ORACLE 99 correct / 0 unsafe; π = 99/252 = 0.393; δ/π = 25% | as stated | 99/0; 0.3929; 25.5% (25.0% at π = 0.40) | verified |
| Mean n_do V3 | 2.71 | 2.708 | verified |
| Mean cost term V3 at γ = 1 (PRE §3.3 "0.136") | 0.136 | 0.1353 | **rounding: write 0.135** |
| V3 significantly > AA only at λ = 0.25 (κ ≤ 0.025) and λ = 0.5 (κ = 0) (PRE §3.5) | as stated | identical cells (template and group CIs; strict and operational) | verified |
| V3 − V2 CI > 0 at every λ ≥ 1, κ ≤ 0.05 (AUD §3.4) | as stated | 25 of 32 strict template cells have CI > 0; all λ ≥ 1, κ ≤ 0.05 cells included; group CI at (2, .05) [0.085, 0.401] | verified |

## 2. Errors / imprecisions found in the existing documents (exact locations)

| # | location | problem | fix |
|---|---|---|---|
| E1 | **AUD §3.6 bullet 1** ("V3 would need precision ≥ 2/3 on the answers it gives at its dev/val coverage") | Understates the requirement. 2/3 is the zero-cost floor for U = 0 at λ = 2. At V3's dev/val answer rate (0.369) and mean cost term (0.135), U = 0 needs precision ≈ **0.79** and U = δ = 0.10 needs ≈ **0.88** (V2: 0.72 / 0.80). Observed V3 precision is 0.484. Assumes all non-correct answers are unsafe. | Replace with the text in §5-E1 below. |
| E2 | **PRE §3.5 bullet 2** ("V3 beats ALWAYS-ABSTAIN only when λ ≲ 0.9 and κ ≈ 0") | 0.9 is the *point-estimate* break-even at κ = 0 (0.938). A 95% cluster CI for V3 − AA is entirely above 0 only for λ ≤ **0.61** at κ = 0 (template; 0.60 by group) and λ ≤ **0.30** at κ = 0.025; at κ = 0.05 and 0.10 there is no λ ≥ 0 where it is significant. The same is true of AUD §3.5 "positive only for λ ≲ 0.5–0.9". | Replace with the text in §5-E2. |
| E3 | **PRE §3.3 bullet 2** "0.136" | Recomputed 0.1353. | "0.135". |
| E4 | **AUD §3.4 last bullet** (ordering V3 > V3-DEF > V2 > legacy > B0-EARLIEST) | Correct but explicitly κ = 0 only. Verified here that it is **not** stable across κ: at κ = 0.05 the break-evens are legacy 0.283 > B0-EARLIEST 0.261 > V3 0.227 > V2 0.208 > V3-DEF −0.03; at κ = 0.10 legacy 0.216 is the only one with a positive break-even among these. This is dev/val only and informative: the ordering is a function of κ. | Keep, and add "the ordering reverses with κ: at κ = 0.05 legacy and B0-EARLIEST have higher break-even λ than V3-FULL (0.283, 0.261 vs 0.227); at κ = 0.10 only legacy (0.216) and B0-EARLIEST (0.261) are positive". |
| E5 | **AUD §3.4 "V3 − V2 … at κ = 0.10, CI includes 0 for λ ≤ 1.5"** | At λ = 0.25 the CI is entirely *below* 0 (−0.049 [−0.095, −0.000]), so the statement should read "for 0.5 ≤ λ ≤ 1.5". | edit |
| E6 | **PRE §3.2 / AUD §3.2.3 "The scale is bounded by prevalence"** | Correct only as an *upper* bound on the mean. The scale is **not** within [0, 1] and the per-scenario floor is −(λ+γ). The ceiling π is attained only by an unattainable method (correct on all ATTRIBUTE scenarios with 0 do()); the ORACLE row has n_do = 0. For any method that needs ≥ 2 do() to be correct (V3's observed minimum is 2; V2's is 1) the per-scenario ceiling is 0.90 (V3) / 0.95 (V2). | Add the bounds paragraph §5-B below. |

No numerical error was found in the dev/val utility figures themselves.

## 3. Exact bounds (verified in code and data)

Per scenario, with C, S ∈ {0, 1}, **C·S = 0** (checked on all 3 276 pairs: 0 violations; `correct` requires `expected = ATTRIBUTE` and top1 ∈ roots, `unsafe` requires an answer that is on an ABSTAIN_REQUIRED scenario or names a non-root), c = n_do/20 ∈ {0, 0.05, …, 1} (code stops at `MAX_DO = 20`; 0 of 3 276 pairs exceed 20; maxima: V3 8, V2 6, legacy 1, B6/B7 4, oracle-graph 5):

| outcome | U range | at λ = 2, γ = 1 |
|---|---|---|
| correct answer | [1 − γ, 1] | [0, 1] |
| unsafe answer | [−λ − γ, −λ] | [−3, −2] |
| abstain (C = S = 0), after k do() | −γk/20 ∈ [−γ, 0] | [−1, 0] |
| **all outcomes** | **[−(λ+γ), 1]** | **[−3, 1]** |

* The three outcome classes partition the scenarios exactly (V3: 45 correct + 48 unsafe + 159 abstain = 252; V2: 36 + 79 + 137 = 252; 0 "answered but neither").
* The claim "U ∈ [0, 1]" (never made in the documents, but easy to read into "correct-attribution equivalents") is **false**. U ∈ [−(λ+γ), 1].
* **Mean-utility ceiling.** Sup over all methods of mean U is π (prevalence of ATTRIBUTE), attained only by perfect attribution at zero cost. In dev/val π = 0.3929 (99/252); in the confirmatory design π = 0.40 by quota. δ = 0.10 is 25.0% of that ceiling.
* **Floor of the mean:** −(λ + γ) = −3 (unsafe answer after 20 do() on every scenario). Not attained: observed per-scenario range at (2, 1) for V3 is [−2.40, +0.90]; for V2 [−2.25, +0.95]. The distribution at λ = 2, γ = 1 is on a 0.05 lattice, discrete and skewed (−1.09).
* **Cost on abstentions.** 41% of V3's total do() count (82 scenarios) is spent on scenarios where it then abstains; this is charged to V3 (an abstention after interventions has U < 0). Always-abstain does no interventions and is exactly 0, so it stays a meaningful (and strict) comparator.
* **Practical ceiling for V3** is below π: it never answered correctly with < 2 do() in dev/val (min n_do when correct = 2), so per-scenario U ≤ 0.90 for a correct answer.

## 4. Why λ, γ, δ are normative, not empirical constants

(Content for PRE §3.3 and AUD §3.5.)

* The utility is a **decision-theoretic loss specification**, not an estimand with a true value in nature. λ is the exchange rate between one unwarranted or wrong named service and one correct attribution; γ is the exchange rate between a fully consumed intervention budget and one correct attribution; δ is the smallest net gain worth acting on. None of the three is identifiable from RIFT's data: the simulator contains no operator, no incident cost, no blast radius and no SLA (limitation L4), so no experiment on synthetic scenarios can estimate "the" λ. They are set by the application's stakeholders and can differ by orders of magnitude across deployments.
* **Precision-floor reading.** At zero intervention cost, answering a scenario with probability p of being correct has expected utility p − λ(1 − p). It is non-negative iff **p ≥ λ/(1 + λ)**: λ = 1 → 0.50, **2 → 0.667**, 3 → 0.75, 5 → 0.833, 9 → 0.90. With cost it becomes p ≥ (λ + γ·c̄/a)/(1 + λ) where a is the answer rate. Choosing λ is therefore the same as choosing the minimum acceptable precision for an automated attribution; "two wrong or unwarranted answers cancel four correct ones' worth of benefit per three answers" is a statement about risk appetite, not a measured fact.
* **Why 2 and 1, and not the value that is best for V3.** Dev/val results say V3 wins only for λ below about 0.6–0.9 (point break-even 0.94, 95% significance limit 0.61 at κ = 0), i.e. a stakeholder who accepts ≈ 48–49% precision. The preregistration keeps λ = 2 because it was proposed before the sensitivity audit (the proposer had nevertheless seen dev/val; independence is not claimed) and because moving it toward V3's favour requires an application argument that is not available. This does **not** make λ = 2 "correct". It makes it declared in advance. Conversely, the audit does **not** claim that V3 is unsafe in general: it claims that, at the declared exchange rate, it does not clear the declared bar on development data.
* **Consequence for reporting.** Because the conclusion is a function of normative weights, the preregistration reports (i) the primary at one declared (λ, γ, δ), (ii) the full grid and break-even λ* as secondary, labelled "sensitivity, not confirmatory", and (iii) never states "V3 is useful" without the declared weights.

## 5. Recommended replacement text

### 5-A. Immutable definition (new PRE §3.6, referenced from SAP §1 and §11 and PLAN §2)

> **§3.6 Immutability of the primary utility definition.** The following are frozen by this preregistration and cannot be altered, supplemented or re-selected after any confirmatory outcome (V3, V2, baseline or always-abstain) has been computed on the confirmatory dataset:
> 1. the formula U_i = C_i − λ·S_i − γ·(n_do,i / 20);
> 2. λ = 2.0, γ = 1.0 (≡ κ = 0.05 per do()), δ = 0.10;
> 3. C_i and S_i exactly as returned by `benchmark_v2.score_one(...)["correct"]` and `["unsafe"]` (strict unsafe), computed from the file `src/rift/evaluation/benchmark_v2.py` with SHA-256 `efc5fcf4a947e12f608aa173f5f4f7d0d7b03f0a04120213c6f503e09eafce92`;
> 4. n_do,i as the integer `n_do` recorded by the method for scenario i; cost normalisation constant 20 = `MAX_DO`; U_AA ≡ 0;
> 5. the comparator set and the unit of analysis (scenario, clustered by union-find group).
>
> The operational-unsafe definition (S^op_i = 1 iff the method answers and the named service is not a ground-truth root), the (λ, κ) grid, break-even λ*, U/π, coverage, P1 and unsafe-rate are **secondary**: they are computed and reported whatever the primary result is, are labelled "sensitivity (not confirmatory)", and cannot change the primary label except where §10 explicitly makes the operational result a condition of the label POSITIVE-USEFUL. Any value of λ or γ other than 2 and 1 may appear only as a labelled secondary sensitivity. No weight, definition, comparator or endpoint may be added after unblinding of confirmatory outcomes; if a different utility is later considered, it requires a new preregistration, new data and is reported as a different study. The analysis script computing U is hashed and recorded before the confirmatory run; the dev/val reproduction test (SAP §12 step 4) must pass first. Before any confirmatory result is computed, the utility code is checked for U_AA ≡ 0, C·S = 0 and U ∈ [−(λ+γ), 1] on every scenario; a violation aborts the analysis (it indicates a recording or scoring defect, and the scenario is not dropped silently).

### 5-B. Bounds paragraph (new PRE §3.2 bullets, replacing "bounded by prevalence" wording in AUD §3.2.3)

> * **Bounds.** For every scenario U_i ∈ [−(λ+γ), 1] = [−3, 1] at the primary values: a correct answer gives U ∈ [1−γ, 1] = [0, 1]; an unsafe answer gives U ∈ [−λ−γ, −λ] = [−3, −2]; an abstention after k do() gives U = −γk/20 ∈ [−1, 0]. C_i·S_i = 0 always. The mean utility of any method is ≤ π (prevalence of ATTRIBUTE, 0.40 by quota), attained only by perfect attribution at zero cost, which no method that uses interventions can reach. U is not confined to [0, 1]; it is discrete (0.05 lattice at integer λ), bounded and negatively skewed (−1.09 on dev/val).

### 5-C. PRE §3.5 bullet 2 (error E2)

> * V3's mean U is below zero at the primary values. As a point estimate V3 beats ALWAYS-ABSTAIN only when λ < λ* = 0.94 at κ = 0 (0.58 at κ = 0.025; 0.23 at κ = 0.05; none at κ = 0.10). With a 95% cluster CI, V3 − AA is entirely above zero only for λ ≤ 0.61 at κ = 0 and λ ≤ 0.30 at κ = 0.025, and for no λ ≥ 0 at κ ≥ 0.05 (template and union-find clusters agree). Break-even λ by κ: κ = 0: 0.938 [0.61, 1.42]; κ = 0.025: 0.582 [0.31, 0.98]; κ = 0.05: 0.227 [−0.01, 0.55]; κ = 0.10: −0.48 [−0.72, −0.25] (never beats AA).

(AUD §3.5: replace "positive only for λ ≲ 0.5–0.9 with κ ≈ 0" by "significantly positive only for λ ≤ 0.61 with κ = 0 and λ ≤ 0.30 with κ = 0.025".)

### 5-D. PRE §3.3 bullet 2

"…the cost term averages **0.135** (V3 mean n_do 2.71 / 20), smaller than the unsafe term λ·48/252 = 0.381." (Recomputed three-term decomposition at (2, 1): correct 45/252 = 0.179; unsafe 2 × 48/252 = 0.381; cost 0.135; total 0.179 − 0.381 − 0.135 = −0.338.)

### 5-E1. AUD §3.6 bullet 1

> * As a fraction of the ceiling, 25%. In terms of precision: at zero cost and λ = 2 the break-even precision is 2/3, but at V3's dev/val answer rate (0.369) and mean cost term (0.135), U = 0 requires precision ≈ 0.79 and U = δ = 0.10 requires ≈ 0.88 (V2: 0.72 and 0.80), against an observed 0.484 for V3 (computed holding the answer rate and cost fixed, with every non-correct answer unsafe). δ = 0.10 is therefore a demanding but internally consistent bar; it is a judgement (D2).

### 5-F. Primary and secondary reporting rules (add to SAP §11 and PRE §10)

1. **One primary number:** mean paired difference θ = mean(U_V3 − U_AA) = mean(U_V3) at (λ = 2, γ = 1, strict unsafe), scenario unit, group-clustered studentised bootstrap, one-sided α = 0.025 (SAP §2). Nothing else is called "the result".
2. **Mandatory secondaries, every report, whatever the outcome:** (a) the λ × κ grid (λ ∈ {0.25, 0.5, 1, 1.5, 2, 3, 4, 5} × κ ∈ {0, 0.025, 0.05, 0.10}) for V3 − AA and V3 − V2, strict and operational, with group-cluster CIs, produced by the same code as `scripts/sprint451_utility_sensitivity.py` (grid layout in `sensitivity_grid.md`); (b) break-even λ* per κ with CI and the 95%-significance limit of λ; (c) U/π, coverage on ATTRIBUTE, P1, answer rate on ABSTAIN_REQUIRED, precision among answered, unsafe rate, mean n_do; (d) the three-term decomposition (correct, λ·unsafe, γ·cost) for each method; (e) the "lucky" count (right service on ABSTAIN_REQUIRED) by abstain reason.
3. **No selection among grid cells.** The report may not describe the grid by its most favourable cell. A statement of the form "V3 beats always-abstain at λ ≤ x" is only allowed together with the primary result and the range of λ over which the CI excludes 0 in each direction.
4. **Oracle rows** (ORACLE:UPPER-BOUND, ORACLE:RIFT-FULL-V2-ORACLE-GRAPH) are labelled "privileged upper bound (reads ground truth)" and never enter a comparison against the primary, a Holm family, or a ranking.
5. **Weights are reported with the claim.** Any sentence that says V3 is "useful", "safe" or "not useful" must be followed by "at the preregistered exchange rates λ = 2, γ = 1 (minimum precision 2/3 at zero cost), δ = 0.10".
6. **No post-hoc λ.** The break-even λ* is an outcome, not an alternative primary. Recommending a "better" λ after seeing results is excluded; a stakeholder may apply their own λ to the reported grid.

## 6. Deliberate non-changes

* Primary form and values unchanged. Alternatives (U/π, operational-primary, co-primary, cost-effectiveness ratio, missed-attribution penalty) stay secondary as in AUD §3.3. Reason: every alternative would be chosen after seeing that V3 fails at the declared values; the operational variant helps V3 (−0.195 instead of −0.338) and is therefore the alternative most open to the charge of being chosen for that reason. It stays a robustness condition.
* Strict unsafe remains primary even though 18/38 V3 answers on ABSTAIN_REQUIRED named a true root. Note for the researcher (D2): the 18 comprise 14 WEAK_SIGNAL and 4 NO_DISCRIMINATING_EVIDENCE; V2's 25 include 9 SYMMETRIC_MUTUAL_DEPENDENCY. Under SYMMETRIC_MUTUAL_DEPENDENCY the label says the true root is not identifiable from the data, and naming one of the pair is a coin flip; this is the clearest case for the strict definition and should be cited in PRE §3.4.

## 7. Unresolved issues (need researcher input or lead action)

1. **D2 stays open.** λ, γ, δ are normative judgements; the document can only declare them. Reviewer should see §4 above and confirm the exchange rates against a stated application.
2. **Group-clustered CIs on dev/val have K = 21** (group sizes 2–23), so the studentised bootstrap and the "group" CIs are rough (K small); the confirmatory design has ≥ 250 groups. Do not quote group CIs as precise.
3. **Operational unsafe treats a lucky root among SYMMETRIC cases as safe.** Whether that is operationally reasonable is a researcher decision; the conservative reading is the strict one.
4. **λ·S counts wrong-root and unwarranted answers equally.** A graded harm (wrong root > lucky root) would be a different utility; not adopted (would need a preregistered new weight).
5. The gap between "ceiling π" and what any interventional method can reach (≥ 1–2 do()) is small (0.90–0.95 per scenario) but real; PRE §3.2 should not describe δ as "25% of the attainable range" without the word "ceiling".
6. If the lead chooses to keep `κ` language anywhere (PLAN, SAP), use "κ = γ/20 per do()" consistently; `utility_verification.json` uses κ per do() and γ = 20κ.

## 8. Commands

```
cd "/Users/manassakthivel/Desktop/RIFT FINAL"
python3 scripts/sprint451_utility_sensitivity.py        # ~1 s; seed 4510; writes artifacts/sprint4_5_1/utility/*
shasum -a 256 scripts/sprint451_utility_sensitivity.py src/rift/evaluation/benchmark_v2.py
```
Reads only `datasets/rift_v2/{dev,val}.json` (sha256-pinned), `artifacts/sprint4_4_0/v3_{dev,val}.json`,
`artifacts/sprint4_3_0/results/{dev,val}/per_scenario.json`. Imports `src.rift.scenarios.independence.topology_hash` and
`splitter.build_groups` for union-find groups only; imports no method, no `score_one`, and does not touch held-out files.
