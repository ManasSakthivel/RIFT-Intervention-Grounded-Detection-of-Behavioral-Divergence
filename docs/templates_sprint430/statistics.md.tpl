# Sprint 4.3.0 — Statistical Validation

> Every table is rendered by `python3 scripts/sprint430_build_docs.py` from
> `artifacts/sprint4_3_0/results/{dev,val,held_out}/{aggregate,statistics,analysis,detection,run_metadata}.json`.
> All results are **validated on synthetic ground-truth scenarios**. Nothing here establishes real-world causal attribution.
> The protocol is `docs/EVALUATION_PROTOCOL_V2.md` (SHA-256 of the registered text in `protocol_v2.sha256`; amendments 1-3 logged
> in §16 with their own hashes).

## 0. Headline statements (required, stated plainly)

1. **RIFT-FULL-V2 P1 = 20/45 = 0.444** (95 % Wilson CI [0.31, 0.59]); abstention on an ATTRIBUTE scenario counts as a miss.
2. **RIFT-FULL-V2 P2 = 60/108 = 0.556** (95 % Wilson CI [0.46, 0.65]).
3. **The trivial always-abstain policy scores P2 = 63/108 = 0.583** on the same held-out scenarios.
4. **RIFT-FULL-V2 does not outperform always-abstain on P2** (difference -0.028, 95 % CI [-0.145, +0.102], exact McNemar
   p = 0.76; 20 scenarios only V2 correct, 23 only always-abstain correct).
5. **RIFT-FULL-V2 is not significantly better than legacy RIFT-FULL on P2**: difference +0.074, 95 % CI [-0.009, +0.159],
   exact McNemar p = 0.13 (0.1338), Holm-adjusted p = 1.0.
6. **H4 is unsupported** (section 8).
7. **H5 is mixed** (section 9).
8. **Observational variants are competitive**: A6 (no interventions) and A8 (observational only) have the same held-out P1
   as V2 (0.444), P2 within 0.02, and lower unsafe rates (0.296 / 0.306 vs 0.343), at lower coverage (0.481 / 0.491 vs 0.528).
9. **P1 is not better than the baselines.** V2 P1 (20/45) is nominally *below* the never-abstaining B6/B7 (27/45) and
   below legacy RIFT-FULL (21/45); none of the P1 differences is significant.
10. The statistically supported advantage is on **P2 and P3_safe against baselines that never abstain** (B0-EARLIEST, B0-HIGHEST,
    B1, B3, B6, B7). That advantage is driven largely by abstention on a benchmark where 58 % of scenarios require abstention.

**The always-abstain comparison is POST-HOC.** It was not pre-registered, is not in the Holm family, and was added during analysis, not in the protocol,
because the large ABSTAIN_REQUIRED share makes P2 hard to interpret without it. All its p-values are
uncorrected and exploratory. Always-abstain is "trivial" in that it has coverage 0 and P1 = 0.

## 1. Design and denominators

* **Unit of analysis = scenario.** Held-out: n = 108 (45 ATTRIBUTE, 63 ABSTAIN_REQUIRED), 71 templates.
* **P1** attribution accuracy: den. N_attr = 45; success = answered and top-1 in true root set; abstention = miss.
* **P2** outcome-correct: den. N = 108; success = (ATTRIBUTE and P1 success) or (ABSTAIN_REQUIRED and abstained).
* **P3** unsafe attribution: den. N = 108 (also reported over N_abs = 63 and N_attr = 45); numerator = wrong answers on
  ATTRIBUTE or any answer on ABSTAIN_REQUIRED. P3 is lower-is-better; the paired test uses the indicator "not unsafe" (**P3_safe**).
* **Secondary**: coverage (den. N and per class), conditional accuracy (den. answered ATTRIBUTE), selective risk (den. answered),
  top-3 (den. ATTRIBUTE scenarios with >=3 candidates), correct-abstention rate (den. N_abs), detection precision/recall/F1/FPR/FNR
  with counts, runtime, #perturbations, intervention seconds.
* **Primary metrics were not redefined.** P1, P2, P3 are exactly the §3 definitions of the pre-registered protocol. Any other
  quantity (always-abstain P2, V2G, strata) is labelled exploratory/post-hoc.

## 2. The 12 pre-registered methods, plus one exploratory

| # | Registry id | Role | Uses ground truth? |
|---|---|---|---|
| 1 | B0-EARLIEST | confirmatory baseline | no |
| 2 | B0-HIGHEST | confirmatory baseline | no |
| 3 | B1-LATENCY-CORR | confirmatory baseline | no |
| 4 | B3-SIEVE-LIKE | confirmatory baseline | no |
| 5 | B5-RIFT-OBS | confirmatory baseline (observational RIFT) | no |
| 6 | B6-RIFT-RANDOM | confirmatory baseline (nominal interventions) | no |
| 7 | B7-RIFT-ONE-SHOT | confirmatory baseline (nominal interventions) | no |
| 8 | RIFT-FULL-LEGACY | confirmatory baseline (legacy harness, no CID) | no |
| 9 | **RIFT-FULL-V2** | focal method | no |
| 10 | ORACLE:RIFT-FULL-LEGACY-ORACLE-PAG | oracle (never counts) | yes (graph) |
| 11 | ORACLE:RIFT-FULL-V2-ORACLE-GRAPH | oracle (never counts) | yes (graph) |
| 12 | ORACLE:UPPER-BOUND | oracle (never counts) | yes (root) |
| — | RIFT-FULL-V2G | **exploratory, post-hoc (Amendment 3)** | no |

`B4-SAGE-CHAOS` is excluded (a deferred always-abstain stub, listed in `run_metadata.json`). B6 and B7 produce identical outputs on
this corpus (both use nominal interventions and the same candidate ordering); they are reported separately but are not independent
evidence. ORACLE:RIFT-FULL-V2-ORACLE-GRAPH and ablation A9 are the same configuration and give identical numbers.

### 2.1 Held-out primary metrics (n = 108; 45 ATTRIBUTE; 63 ABSTAIN_REQUIRED)

{{TABLE:methods_held_out}}

Reading notes: B0/B1/B3 never abstain (coverage ~ 100 %), so P2 is low by construction. The oracle rows are an upper-reference only.
V2G is exploratory. V2's coverage is 57/108 = 52.8 % and its conditional accuracy is 20/34; **coverage and conditional accuracy
must always be read together with P2**.

### 2.2 Held-out secondary metrics

{{TABLE:secondary_held_out}}

### 2.3 Development split (n = 180; used for implementation / defect finding; **not** confirmatory)

{{TABLE:methods_dev}}

### 2.4 Validation split (n = 72; used for protocol refinement; **not** confirmatory)

{{TABLE:methods_val}}

On dev and val V2 is also at or below the trivial always-abstain policy (dev 102/180 vs 112/180; val 35/72 vs 41/72), and its P1
is below several baselines (val 8/31 vs B6/B7 16/31). The held-out result is therefore consistent with, not different from,
what dev/val showed.

## 3. Statistical methodology

* **Paired exact McNemar** (two-sided binomial on discordant pairs) for P1, P2, P3_safe; **paired sign-flip permutation test**
  (10 000 resamples, seed 430) as a second opinion; paired risk difference and Cohen's *h* as effect sizes.
* **Confidence intervals.** Single proportions: Wilson 95 %. Differences: percentile bootstrap, B = 2000, seed 430, resampling
  **scenarios** (pairing preserved) *and* resampling **templates** (71 clusters, correlated scenarios within a template).
  The wider of the two is quoted where a single interval is given.
* **Multiple comparisons.** Holm step-down over the confirmatory family = 8 non-oracle comparators x 3 metrics (P1, P2, P3_safe)
  = 24 tests, alpha = 0.05. Everything else is exploratory and uncorrected.
* **Rule 15.1** (pre-committed): "RIFT beats baseline B" requires Holm-adjusted p < 0.05 *and* a scenario-clustered CI excluding 0.
  Oracle rows never count. No stratum with fewer than 10 scenarios is treated as inferential.
* Pipeline is deterministic; there are no repeated runs, so there is no run-to-run variance estimate.

## 4. Confirmatory family (held-out; V2 minus comparator; Holm over 24 tests)

{{TABLE:holm_summary}}

{{TABLE:conf_table}}

**What this shows.**

* P2 and P3_safe: significant after Holm against B0-EARLIEST, B0-HIGHEST, B1-LATENCY-CORR, B3-SIEVE-LIKE, B6-RIFT-RANDOM and
  B7-RIFT-ONE-SHOT (each Holm p <= 0.0028; e.g. P2 vs B6/B7: +0.250, template-bootstrap CI [+0.121, +0.374]).
  All of these comparators answer (almost) every scenario, so they are penalised for answering on ABSTAIN_REQUIRED.
* **P1: nothing is significant.** V2 vs B6/B7 P1 is **-0.156** (V2 lower; McNemar p = 0.14); V2 vs legacy RIFT-FULL is -0.022
  (p = 1.0); V2 vs B0/B1/B3/B5 is +0.04 to +0.07, p >= 0.66.
* **B5-RIFT-OBS** (observational RIFT): P2 +0.167, McNemar p = 0.0096 but Holm p = 0.115 -> not significant; P3_safe Holm p = 0.195.
* **RIFT-FULL-LEGACY**: P2 +0.074 (CI [-0.009, +0.159], McNemar p = 0.1338, Holm p = 1.0), P3_safe +0.111 (McNemar p = 0.0169, Holm
  p = 0.186). **V2 is not significantly better than legacy RIFT-FULL on any of the three primary metrics.**

## 5. Post-hoc: trivial always-abstain reference (NOT pre-registered; uncorrected)

{{TABLE:posthoc_table}}

* On held-out, V2 is **-0.028** relative to always-abstain on P2 (McNemar p = 0.76). The honest reading: on this benchmark,
  where 58 % of scenarios require abstention, V2's P2 cannot be distinguished from the policy that never answers; its gains over
  the never-abstaining baselines mostly reflect abstention.
* B5-RIFT-OBS is significantly *below* always-abstain (p = 0.0065); legacy RIFT-FULL is below it (not significant).
* V2G (exploratory) ties always-abstain exactly on held-out (63/108 vs 63/108) and val (41/72), and is +0.028 on dev.
* This analysis exists because the always-abstain reference makes P2 interpretable. It should have been in the protocol; it
  was not. It is reported as post-hoc and not used to change any hypothesis verdict or threshold.

## 6. Detection (stage 1: EBD R1 persistence detector, method-independent)

{{TABLE:detection_table}}

Held-out FPR = 2/4 = 0.50 on **four** no-fault scenarios (dev 3/9, val 1/4). With so few no-fault scenarios the FPR estimate is
extremely imprecise (the exact 95 % CI for 2/4 spans roughly 0.07-0.93) and should not be used to claim a specific false-alarm rate.
Recall 100/104 on held-out fault scenarios; median detection delay 0 s (IQR 0-20 s; the simulation's window is 10 s).

## 7. Exploratory V2G (Amendment 3: designed after dev/val failures, before freeze; held-out never read for design)

Rule: abstain `UNRESOLVED_EARLIER_DIVERGENCE` when a service with an earlier R1 divergence than the attributed one is neither
attributed nor explained by a confirmed intervention. No free parameter.

{{TABLE:v2g_table}}

V2G trades coverage and P1 for safety: P1 falls 0.444 -> 0.311 (V2G worse, McNemar p = 0.031, uncorrected), P2 rises 0.556 -> 0.583
(p = 0.61, not significant), unsafe falls 37/108 -> 18/108. It ties always-abstain on P2. It does **not** improve attribution
accuracy, and the amendment is **exploratory**: it was written after looking at dev/val failures. It is not part of the Holm family
and no claim in this sprint depends on it.

## 8. Ablations A1-A10 (held-out; exploratory; McNemar p uncorrected)

A1 = RIFT-FULL-V2. Column "dP1 vs V2" is *ablation minus V2* (positive = the ablation did better).

{{TABLE:ablation_held_out}}

Across splits (P1 / P2 / unsafe / coverage):

{{TABLE:ablation_splits}}

Interpretation (exploratory):

* **A3 (no EBD)** is clearly worse than V2 on P2 (-0.139, p ~ 0.0001) and on not-unsafe (-0.157, p < 0.0001): the EBD
  temporal/persistence logic contributes measurable safety.
* **A9 (oracle graph)** raises P1 from 0.444 to 0.711 (+0.267, p ~ 0.0005) with P2 unchanged. A graph-quality bottleneck (FCI)
  limits V2's attribution accuracy; this is an ORACLE configuration and is not a method result.
* **A2 (call graph instead of FCI)** reaches P1 0.578 (+0.133, p = 0.109) with a lower not-unsafe rate (-0.093, p = 0.041): FCI does not
  help accuracy on this corpus.
* **A6 and A8 (no interventions)** match V2's P1 (0.444), have P2 within 0.02, and lower unsafe rates (0.296, 0.306 vs 0.343) at lower
  coverage. **Interventional evidence adds no demonstrated benefit on this benchmark.**
* A4, A5, A7, A10: no significant difference from V2.

## 9. Pre-registered hypotheses and their verdicts

| Hypothesis | Verdict (held-out) | Evidence |
|---|---|---|
| H1: P2 above every non-oracle baseline | **Partly met.** Significant after Holm vs 6 of 8 (B0-E, B0-H, B1, B3, B6, B7); not vs B5-RIFT-OBS (Holm p = 0.115) or legacy RIFT-FULL (p = 0.13 / Holm 1.0) | section 4 |
| H2: P1 not lower than best observational baseline | **Not met nominally.** V2 20/45 vs B6/B7 27/45 (-0.156, p = 0.14, not significant) | section 4 |
| H3: lower unsafe rate on ABSTAIN_REQUIRED than baselines w/o abstention | **Met.** V2 23/63 vs 57-63/63 for B0/B1/B3/B6/B7 | section 2.1 |
| H4: removing interventions raises unsafe rate on counterexample strata | **UNSUPPORTED** | below |
| H5: MSIS lowers intervention duration vs random, no accuracy change | **MIXED** | below |

### 9.1 H4 — unsupported

Counterexample strata = `earliest_not_root` + `coincidental_anomaly` + `indistinguishable_onsets`.

{{TABLE:h4_table}}

Without interventions (A6, A8) the unsafe count is **lower or equal** to V2's in every split (held-out 3 vs 4 of 7; dev 5 vs 6 of 12;
val 3 vs 4 of 6). The predicted direction (A6/A8 worse) was not observed. n = 7 / 12 / 6 is too small for inference; the result is
"not supported", not "refuted".

### 9.2 H5 — mixed

{{TABLE:h5_table}}

MSIS ordering reduces mean intervention seconds on held-out (V2 56.4 s vs random order 61.1 s, permutation p = 0.0014; vs alphabetical
60.3 s, p = 0.0246) but **not** on dev (p = 0.24 / 0.45) or val (p = 1.0 / 0.61). Accuracy differences are not significant (held-out
P1 0.444 vs 0.378 vs 0.444). The cost advantage is therefore split-dependent, small in absolute terms (4-5 s of ~60 s), uncorrected for
multiplicity, and based on simulated intervention durations.

## 10. Distribution shift (held-out only; descriptive)

{{TABLE:shift_table}}

`feedback_like` (n = 24) and `recovery_instability` (n = 18) overlap, and per-cell n is small; V2's behaviour on unseen strata is
noisy and descriptive only.

## 11. Observability strata (held-out; descriptive)

{{TABLE:obs_table}}

**Caveat on degraded observability.** V2 beats legacy and B6 on P2 in the pooled degraded stratum (52/84 vs 42/84 and 27/84), but much of
that comes from abstaining. For example, `insufficient_samples` shows V2 P2 = 12/12 with **coverage 0/12**: that is a zero-coverage
"perfect" score, not an advantage in attribution. V2's pooled degraded P1 is 18/36 against B6's 22/36.

## 12. Per-family and per-structure breakdowns (held-out, RIFT-FULL-V2; n per cell is small)

### 12.1 By fault family
{{TABLE:bk_family}}

### 12.2 By causal structure
{{TABLE:bk_structure}}

### 12.3 By workload
{{TABLE:bk_workload}}

### 12.4 By observability
{{TABLE:bk_observability}}

### 12.5 By intervention mode
{{TABLE:bk_intervention}}

### 12.6 By negative kind
{{TABLE:bk_negative}}

Every cell has n <= 24 (most 2-15); none is large enough for a stand-alone inferential claim. Breakdowns for other methods are in
`artifacts/sprint4_3_0/results/held_out/breakdowns.json`.

## 13. Abstention and coverage

* V2 held-out coverage 57/108 = 52.8 %. Among 45 ATTRIBUTE scenarios V2 answered 34 (20 correct, 14 wrong) and abstained 11; among
  63 ABSTAIN_REQUIRED scenarios it abstained on 40 and answered 23 (unsafe).
* Selective risk = 37/57 = 0.649 (the answered set is wrong or should have abstained 65 % of the time). Conditional accuracy on
  answered ATTRIBUTE scenarios = 20/34 = 0.588.
* Abstention is informative only weakly: V2 abstains 40/63 = 63.5 % of the time when it should (always-abstain: 63/63 = 100 %) and 11/45 = 24.4 %
  of the time when it should answer (always-abstain: 45/45 = 100 %, i.e. all lost coverage).
* The reasons for the 11 abstentions on ATTRIBUTE scenarios are listed in the failure taxonomy.

## 14. Reproducibility metadata

{{TABLE:meta_table}}

Software: Python 3.9.6, numpy 2.0.2, scipy 1.13.1, pandas 2.3.3, networkx 3.2.1, causal-learn 0.1.4.8 (the run metadata records
`causallearn: unknown` because that package exposes no `__version__`; 0.1.4.8 is the installed version), pytest 8.4.2. Statistical seed 430;
bootstrap B = 2000; permutations 10 000.

```bash
python3 scripts/sprint430_run_pipeline.py            # dev + val only; refuses to touch the held-out result
python3 scripts/sprint430_analyze.py --split held_out   # post-hoc analyses over saved results (reads results only)
python3 scripts/sprint430_build_docs.py              # re-render every table in this document
python3 scripts/verify_heldout_sealed.py             # sealed-gate check
```

## 15. What this validation does and does not show

Shows (on synthetic ground-truth scenarios): V2 abstains much more appropriately than baselines that never abstain; the EBD component
contributes safety; FCI graph quality is a bottleneck for V2's accuracy.

Does **not** show: that V2 attributes root causes more accurately than the baselines (P1 is not better); that V2 outperforms
always-abstain; that V2 beats legacy RIFT-FULL; that interventional evidence helps; that MSIS reliably saves time; anything about
live systems or real-world causal attribution.
