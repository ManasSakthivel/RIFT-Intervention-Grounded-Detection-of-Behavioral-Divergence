# RIFT Evaluation Protocol v2 (Sprint 4.3.0) — pre-registration

Status: **PRE-REGISTERED before the v2 held-out candidate set was generated.**
The SHA-256 of this file is recorded in `artifacts/sprint4_3_0/protocol_v2.sha256` *before* the generator is allowed to
emit the held-out candidate file (the generator refuses to write it otherwise; see §14). Later amendments are appended
to §16 (Amendment log) with a timestamp and a new hash; text above §16 is never edited after registration.

Scope statement. Everything in this protocol concerns **synthetic ground-truth scenarios**. Results are
*validated on synthetic ground-truth scenarios* and are *intervention-consistent*; they are not evidence about live
systems, and they say nothing new about the Stage 4 live run.

## 1. Research questions

* **RQ1 (attribution).** On scenarios whose structure, family, workload and observability are unseen at development time,
  does RIFT-FULL-V2 identify the true root cause more often than meaningful non-oracle baselines, *counting abstentions as
  misses*?
* **RQ2 (safety).** Does RIFT-FULL-V2 make fewer *unsafe attributions* (naming a service when the correct behaviour is to
  abstain, or naming a wrong service) than baselines that lack an abstention mechanism?
* **RQ3 (usefulness under poor observability).** Do RQ1/RQ2 hold in the degraded-observability strata (missing, noisy,
  delayed, partial, insufficient telemetry), or does RIFT merely abstain?
* **RQ4 (abstention quality).** Is abstention informative — is the selective risk of the non-abstained set lower than the
  risk of a method that always answers, and does the accuracy-vs-coverage curve behave sensibly?
* **RQ5 (components).** Which pipeline components (FCI, EBD, CID, identifiability, interventional evidence, MSIS)
  contribute measurable accuracy, coverage, safety or cost?
* **RQ6 (failure structure).** Which fault families, causal structures, workloads and observability conditions fail?

## 2. Hypotheses (directional; each can be refuted)

* **H1** RIFT-FULL-V2 outcome-correct rate (§3, P2) exceeds that of each non-oracle baseline.
* **H2** RIFT-FULL-V2 top-1 accuracy on ATTRIBUTE scenarios (P1; abstention = miss) is **not lower** than the best
  observational baseline. (A weaker claim than superiority on purpose: the baselines never abstain, so on easy
  ATTRIBUTE scenarios they are expected to be competitive.)
* **H3** RIFT-FULL-V2 has a lower unsafe-attribution rate on ABSTAIN_REQUIRED scenarios than every baseline without
  abstention logic.
* **H4** Removing interventional evidence (ablation A6/A8) raises the unsafe-attribution rate on the *counterexample*
  strata (earliest-not-root, coincidental anomaly, indistinguishable onsets).
* **H5** Greedy MSIS ordering lowers cumulative intervention duration vs random ordering with no change in accuracy.
* **Null/negative outcomes are reported with the same prominence as positive ones.** No hypothesis is dropped after
  seeing held-out data.

## 3. Primary metrics (all denominators explicit)

Each scenario carries `ground_truth.expected_outcome ∈ {ATTRIBUTE, ABSTAIN_REQUIRED}` and a root set `R`
(`R=∅` for NO_FAULT and for hidden/unobserved roots).

* **P1 — attribution accuracy.** Denominator `N_attr` = #ATTRIBUTE scenarios. Success: not abstained and top-1 ∈ `R`.
  Abstention on an ATTRIBUTE scenario counts as a **miss** (reported separately as *lost coverage*).
* **P2 — outcome-correct rate.** Denominator `N` = all scenarios. Success: (ATTRIBUTE and success as in P1) or
  (ABSTAIN_REQUIRED and abstained).
* **P3 — unsafe-attribution rate.** Denominator `N` (and separately `N_abs` = #ABSTAIN_REQUIRED, `N_attr`):
  numerator = non-abstained answers that are wrong (top-1 ∉ `R` on ATTRIBUTE) **or** any answer on ABSTAIN_REQUIRED.

Baselines without abstention are *not* penalised on P1; they are on P2/P3 because ignoring non-identifiability is
precisely what these metrics test. Both views are always shown together. **A zero unsafe-attribution rate is never
presented as an advantage without the accompanying coverage (§4).**

## 4. Secondary metrics

* **Coverage** = #non-abstained / `N` (and per class). **Conditional accuracy** = correct / #non-abstained
  ATTRIBUTE answers (always printed next to coverage). **Overall accuracy** = P2.
* **Selective risk** = error rate among non-abstained answers; **accuracy-vs-coverage curve** by thresholding the
  method's own confidence score (only for methods with graded confidence; otherwise a single point).
* **Detection** (stage-1 persistence detector, method-independent; §5.1) — fault present vs no-fault, scenario unit:
  precision, recall, F1, FPR, FNR with explicit counts; *detection delay* = `t*(first diverging service) − true onset`
  on detected fault scenarios (median, IQR, n). Per-method detection flag (non-abstained, or abstained with
  `NOT_IDENTIFIABLE`) is reported too and labelled as such.
* **Top-3** on ATTRIBUTE scenarios for methods that return ≥3 candidates (denominator = those scenarios).
* **Causal evidence**: CID grade distribution; fraction with interventional evidence (R4 pass); identifiability rate
  (#identify_query != NOT_IDENTIFIABLE / #queries); definitive-attribution rate (= attributions backed by R4 / #attributions);
  path-kind split DIRECTED vs SEMI_DIRECTED among attributions.
* **Operational**: wall-clock per scenario, peak traced memory (tracemalloc), #perturbations, cumulative intervention
  duration (s), recovery time (fixed 30 s per rollback in the simulator — *not measured*, stated as a model constant).
* **Breakdowns** by fault family, causal structure, workload, observability, intervention mode, negative type, with `n`.

## 5. Methods (authoritative registry; nothing silently omitted or redefined)

Legacy classes/functions are used **unmodified** under their legacy behaviour. Id inconsistencies are documented, not
renamed: RIFT-ONE-SHOT is class id `B7-RIFT-ONE-SHOT` but dict key `B4-RIFT-ONE-SHOT` in the adversarial script;
`B4-SAGE-CHAOS` is a deferred always-abstain stub and is **excluded** (listed as excluded in every table).

| Registry id | Source | Class | Uses ground truth? |
|---|---|---|---|
| B0-EARLIEST | `scripts/run_adversarial_benchmark.py` (inline class, imported not rewritten) | baseline | no |
| B0-HIGHEST | same | baseline | no |
| B1-LATENCY-CORR | `src/rift/baselines/latency_correlation.py` | baseline | no |
| B3-SIEVE-LIKE | `src/rift/baselines/sieve_like.py` | baseline | no |
| B5-RIFT-OBS | `src/rift/baselines/rift_obs.py` | observational RIFT | no |
| B6-RIFT-RANDOM | `src/rift/baselines/rift_random.py` | RIFT variant (nominal interventions) | no |
| B7-RIFT-ONE-SHOT | `src/rift/baselines/rift_one_shot.py` | RIFT variant (nominal interventions) | no |
| RIFT-FULL (legacy harness) | `scripts/run_reproducible_evaluation.py::run_rift_full_scenario(use_oracle_pag=False)` | learned FCI+EBD(R1–R3)+identifiability; **no CID is executed** | no |
| RIFT-FULL-V2 | `src/rift/evaluation/rift_v2.py` (new) | learned FCI+EBD+identifiability+MSIS+simulated interventions+CID+R4 | no |
| *ORACLE* RIFT-FULL-ORACLE | legacy harness, oracle PAG | **oracle** | yes (graph, affected set) |
| *ORACLE* RIFT-FULL-V2-ORACLE-GRAPH | V2 with oracle PAG | **oracle** | yes (graph) |
| *ORACLE* ORACLE-UPPER-BOUND | `src/rift/baselines/oracle.py` | **oracle** | yes (root) |
| EXCLUDED B4-SAGE-CHAOS | stub | — | — |

Oracle rows are labelled "ORACLE" in every table and never enter a "RIFT beats baselines" statement.

Finding recorded up front (from code inspection): the legacy `RIFT-FULL`, `RIFT-RANDOM`, `RIFT-ONE-SHOT` paths call
`compute_ebd(cid_results=None)`; their "interventions" are nominal constants (30 s) and **no interventional evidence is
consumed**. They are therefore *observational-evidence methods with intervention cost accounting*. RIFT-FULL-V2 exists
to test the intervention claim honestly; it is a **new** method, introduced under that name, not a redefinition of
RIFT-FULL.

### 5.1 RIFT-FULL-V2 (specification, frozen before any scenario is run)
1. PAG by FCI (fisher-z, α=0.05) on the incident-window rows, seed = scenario seed (as legacy).
2. EBD (θ_detect=3.0, persistence 2 windows, Δt=10 s) with baseline stats **estimated from the pre-incident period**
   (mean, sample std; services with <8 baseline samples get no stats entry).
3. Candidate set `C` = services with R1∧R3 (ordered by t*). Empty → abstain `NO_CANDIDATES`.
4. Identifiability on (earliest candidate → latest-diverging other service); `NOT_IDENTIFIABLE` → abstain.
   Outcome node chosen only from observed EBD output (no ground truth).
5. Intervention plan = `greedy_msis` order over `C` (existing module, existing θ_entropy=0.5, budget 600 s, 30 s each).
   Each do(X) is executed by the **scenario simulator** (a synthetic environment, never a live system); CID is computed
   by `compute_cid` (n_bootstrap=200, n_permutations=1000, seed derived from scenario seed) on baseline vs post samples of
   each outcome node on X's PAG path.
6. R4 via the existing strict `validate_cid_for_r4`. Stop early when a confirmed candidate exists and every
   un-intervened candidate has t* ≥ t*(confirmed).
7. Attribute the confirmed candidate with minimum t* (ties → larger W1). **No confirmed candidate → abstain
   `INTERVENTION_NOT_VERIFIED`.** Confidence = 0.95 if SEMI path absent, 0.80 for semi-directed path (reported, not tuned).

Hyper-parameters are the *pre-existing* repository defaults. They are not tuned in this sprint (§13). If a genuine
defect is found on dev/val (e.g. uncorrected multiple comparison across outcome nodes in the R4 gate), the fix and its
justification are logged in §16 and the freeze is re-hashed; held-out is never consulted.

## 6. Statistical tests

* Unit of analysis = **scenario**. Overlapping windows within a scenario are never samples.
* Paired comparison of two methods on identical scenarios: **exact McNemar** (two-sided binomial on discordant pairs)
  for P1, P2 and (1 − P3) indicators; **paired sign-flip permutation test** (10 000 resamples, fixed seed) on the mean
  per-scenario difference as a second opinion; effect size = paired risk difference and Cohen's *h* on the two
  proportions.
* **Multiple comparisons:** Holm step-down over the confirmatory family {V2 vs each non-oracle baseline} × {P1, P2, P3}
  at α=0.05. Everything else (ablations, strata) is exploratory and labelled so.
* No significance is claimed for strata with `n < 10` discordant+concordant scenarios; they are descriptive.

## 7. Confidence intervals

* Single proportions: Wilson 95 %.
* Differences and all derived metrics: **scenario-clustered percentile bootstrap** (B=2000, seed fixed, resampling
  scenarios with all method outputs together to keep pairing).
* Sensitivity: **template-clustered bootstrap** (resampling templates, since scenarios inside a template are correlated);
  the wider interval is the one quoted when they disagree.
* Repeated runs: none (deterministic pipeline); if added, hierarchical (run within scenario within template).

## 8. Ablations (same scenarios, same rules, no per-ablation tuning)

Base = RIFT-FULL-V2 (learned graph). For each ablation we report Δ accuracy (P1, P2), Δ coverage, Δ unsafe attribution
(P3), Δ runtime, Δ intervention cost.

| Id | Ablation | Removed component | Definition |
|---|---|---|---|
| A1 | Full | — | RIFT-FULL-V2 |
| A2 | w/o FCI | graph discovery | PAG replaced by the *call graph* (directed), no CI testing |
| A3 | w/o EBD | temporal-precedence/persistence logic | candidates ranked by max |z| (no R1 persistence, R2 precedence); interventions still run |
| A4 | w/o CID | effect-size/permutation gate | R4 replaced by raw mean-shift sign (no permutation test, no W1 threshold) |
| A5 | w/o identifiability | identify_query | step 4 skipped |
| A6 | w/o intervention evidence | step 5–7 | attribute earliest R1∧R2∧R3 candidate (observational) |
| A7 | w/o MSIS | utility ordering | intervene in alphabetical order |
| A8 | observational-only | steps 5–7 + identifiability | same as A6 with identifiability retained (A6 minus A5 interplay is reported) |
| A9 | oracle-graph | FCI learned graph | ORACLE label; PAG from ground truth |
| A10 | random intervention | MSIS | `RandomMSIS` ordering, seeded |

A6 vs A8 differ only in identifiability (A6 keeps it; A8 is the registry's `RIFT-OBS`-style pure observational variant
with *no* abstention on non-identifiability). Their difference is reported, not hidden.

## 9. Exclusion criteria

None based on difficulty or outcome. A scenario is removed only by **label-independent generator QC** (schema, graph
validity, temporal consistency, intervention consistency, duplicate/near-duplicate), *before* any method runs; every
removal is listed with its reason in the diversity report. Method crashes are **not** exclusions (§11).

## 10. Abstention handling

Abstentions are never dropped. Every table prints `n`, `coverage`, `abstention reasons`. Conditional accuracy is never
shown without coverage. Methods with no abstention logic have coverage 100 % by construction and this is shown.

## 11. Failure handling

A method exception is recorded as abstention with reason `METHOD_ERROR:<type>`, counted in all denominators and listed
in a failure table. A runtime above 60 s per scenario is a failure (`TIMEOUT`) recorded the same way.

## 12. Split methodology

* Roles: **dev** = implementation and defect finding; **val** = model/protocol refinement and threshold sanity checks;
  **held-out** = one-time, post-freeze.
* **Group-aware**: scenarios are grouped by `template_id` (= causal structure × fault family) and by topology hash;
  union-find over both; a group lives in exactly one split. Additional strata (workload, propagation mechanism,
  intervention mechanism) are balanced, and the *joint 6-tuple* is disjoint across splits.
* Held-out additionally holds out **whole structure kinds** (`feedback_like`, `ambiguous`) and **a whole fault family**
  (`recovery_instability`) never present in dev/val (distribution shift), plus unseen (structure × family) cells.
* Independence is *verified*, not asserted: `scripts/sprint430_verify_independence.py` must report zero shared
  raw-content, effective-dynamics, template, topology and group keys across splits, and ≤ the declared near-duplicate
  allowance. Seeds are never accepted as evidence of independence.
* Targets (reported as actuals if missed, never padded): ≥300 distinct scenarios, dev ≥150, val ≥60, held-out ≥90.

## 13. Threshold-freeze policy

* All method parameters are existing repository defaults (θ_detect 3.0, persistence 2, FCI α 0.05, θ_cid 0.1·IQR,
  CID α 0.05, MSIS θ_entropy 0.5, budget 600 s, 30 s per intervention).
* Any change made after inspecting dev/val results is a **logged amendment** (§16) justified by a demonstrated defect,
  verified on dev+val only, and followed by a new freeze.
* `scripts/sprint430_freeze.py` writes `artifacts/sprint4_3_0/freeze.json` = SHA-256 of {protocol, all method source
  files, dataset hashes (dev, val, held-out candidate), configuration}. The held-out run requires the freeze file to
  verify against the working tree (any edit after freezing → refuse).

## 14. Held-out access policy

* The v2 held-out candidate is generated **after** the protocol hash is recorded, and is labelled `CANDIDATE` in
  `datasets/rift_v2/heldout_status.json` until (a) the independence verifier passes and (b) the freeze exists, at which
  point it becomes `FINAL_FROZEN`. It is never called "final" before that.
* Loading requires: registry pin match + `FINAL_FROZEN` status + valid freeze + independence report + an active
  `HeldOutGuard` token + purpose `final`. Everything fails closed.
* **One-time**: opening writes `artifacts/sprint4_3_0/heldout_opened.json`. A second opening is refused unless
  `--allow-reopen` is given; a reopened run is stamped `NOT_VALID_FOR_FINAL_CLAIMS`.
* The v1 held-out (`held_out_test`) is **legacy and contaminated** (earlier sprints inspected it; all 15 scenarios have
  content twins in dev/val — see the provenance audit). It is not used for any v2 claim.
* Verification of the sealed gate (`scripts/verify_heldout_sealed.py`) must keep passing; v2 held-out file names are
  derived from the registry, never hard-coded literals elsewhere.

## 15. Interpretation rules (pre-committed)

1. "RIFT beats baseline B" requires Holm-adjusted p < 0.05 **and** a scenario-clustered CI for the paired difference that
   excludes 0, on the held-out set.
2. Oracle rows never count.
3. Results are described as *validated on synthetic ground-truth scenarios* / *intervention-consistent*; synthetic ≠ real.
4. If simulated interventions are the only source of V2's advantage over the legacy RIFT-FULL, the report says so: the
   advantage is conditional on the simulator's intervention-fidelity assumption (a limitation, not a finding about live
   systems).
5. PASS requires independence verified, all methods on identical scenarios/rules, denominators explicit, and statistics
   defensible; scenario or test counts alone never justify PASS.

## 16. Amendment log

### Amendment 1 — design clarifications (logged BEFORE any scenario was generated and BEFORE any method was run)

Reason: while writing the simulator I found the registered text under-specified or self-contradictory in five places.
No data and no method output existed at the time; nothing below was chosen by looking at results.

1. **A6 / A8 contradiction resolved.** A6 = RIFT-FULL-V2 minus steps 5–7 (no interventions), identifiability (step 4) *kept*;
   A8 (observational-only) = A6 minus step 4 as well (pure EBD earliest-candidate attribution).
2. **MSIS ordering.** `greedy_msis` stops immediately when the candidate posterior entropy is already below θ_entropy
   (a single candidate has entropy 0), which would mean "no intervention at all". V2 therefore uses the existing
   `compute_intervention_costs` **utility** as the intervention *ordering* and its own stop rule: stop when (a) every
   candidate has been intervened, (b) the 600 s budget (20 × 30 s) is spent, or (c) every not-yet-intervened candidate has
   already been *explained* (a confirmed CID(X→Z) from an intervened X). Initial posterior ∝ exp(−(t*−t*_min)/20 s).
3. **Explained-candidate exclusion.** A confirmed outcome only shows that X *influences* Y. A symptom with its own downstream
   service also "confirms". V2 therefore attributes only intervened candidates with ≥1 confirmed outcome that are **not
   themselves** a confirmed outcome of another intervened candidate. This is the interventional analogue of "downstream
   symptoms are not automatically root causes".
4. **Multiplicity.** CID is evaluated for every R1-diverging, PAG-reachable outcome Y of an intervened X; the per-candidate
   significance level is α/m (Bonferroni, m = #tested outcomes). Resamples: `n_permutations=1000`, `n_bootstrap=100`
   (the CI is not part of the gate). CID is computed once per (scenario, X, Y) and shared across V2 and its ablations.
5. **Observable windows and baselines (all methods, identical).** Incident window = (end of the pre-incident period, end of
   series) — *not* derived from the true injection time (the legacy harness used `injected_at_t − 60`, a ground-truth
   dependence). `baseline_stats` = mean / sample-std of the pre-incident samples of each service (provided whenever ≥3 samples
   exist). RIFT-FULL-V2 itself abstains (`INSUFFICIENT_BASELINE`) when fewer than 2 services have ≥8 pre-incident samples,
   and (`INSUFFICIENT_SAMPLES`) when fewer than 12 complete rows remain for FCI.
6. **Ground-truth label rule (generator, label-only).** `expected_outcome = ATTRIBUTE` iff a root service is *observed*, its
   noise-free signal reaches SNR ≥ 4, the series has ≥ 8 baseline windows, and the root is identifiable by **temporal** evidence
   (its analytic detectable onset strictly precedes that of every other diverging observed service) **or** by
   **interventional** evidence (analytic expected CID effect on an observed descendant ≥ 1.0 σ). Otherwise
   `ABSTAIN_REQUIRED` with a stated reason. Labels are computed from the noise-free simulator state, never from any method.
7. **Call graph given to methods** = true propagation edges among observed services ∪ 2–3 decoy non-propagating dependency
   edges (a static dependency map, as traces would give); hidden variables never appear. Edge direction = propagation direction.

*Only text above this amendment is the originally registered protocol (its hash is in `protocol_v2.sha256`); the amended
hash is recorded in `protocol_v2_amendments.sha256`.*

### Amendment 2 — simulator and runner conventions (logged BEFORE any scenario was generated and BEFORE any method was run)

1. **Reference period.** Every method receives the same `baseline_stats` computed from the **first 10 windows (100 s)** of each
   service's series (mean, sample std; entry omitted when < 5 samples remain). The *incident window* handed to every method is
   `[100 s, end of series]`. This is a fixed monitoring convention, not derived from the true onset. Normal scenarios have
   onset ≥ window 14; `insufficient_samples` scenarios deliberately violate this (series of 16 windows, onset at window 6) so that
   the reference period is contaminated.
2. **Telemetry gaps.** Missing windows are *absent rows*. RIFT-FULL-V2 runs EBD with `max_gap_windows=1` (the existing, documented
   gap-tolerance parameter); every other method keeps its legacy behaviour. For FCI only, V2 linearly interpolates gaps of ≤ 3
   windows and drops remaining incomplete rows (< 12 rows → abstain `INSUFFICIENT_SAMPLES`). Legacy methods keep their legacy
   `dropna` handling, which is a property of those methods.
3. **A4 (w/o CID) clarified:** R4 is replaced by a naive two-sample z-test on the intervention windows (|Δmean| > 2·SE; no
   permutation test, no IQR threshold, no multiplicity correction). The earlier "raw sign" wording would be a straw man.
4. **Ambiguity label.** The `ambiguous` structure kind (symmetric mutual dependency between two candidate roots) is labelled
   `ABSTAIN_REQUIRED / NOT_IDENTIFIABLE` by construction: neither temporal order nor a do() on either service can separate
   the two. This overrides the generic label rule of Amendment 1 §6 for that structure kind only.
5. **Intervention simulator.** A do(X) is a 30 s baseline window followed by a 30 s perturbation window sampled at 1 Hz, run on the
   incident-state system (the fault keeps evolving; there is no control arm — non-stationary faults can therefore produce
   spurious CID, which is a known limitation and is measured, not corrected). Perturbation amplitude is
   `magnitude_σ · σ_X · delivered_fraction`; its effect on a descendant Y is `path_gain · amplitude`, arriving after `2 s ×` the
   path's window lag (accumulation delays of the observational series are not applied to a direct perturbation). All simulated
   rollbacks are complete (the "reversible" profile is therefore the default). Recovery time is the fixed constant 30 s per
   rollback and is reported as a **model constant, not a measurement**.
6. **Topology size bands (for the unseen-topology requirement).** For structure kinds shared across splits, topology instances are
   drawn from disjoint size bands (dev: base+{0,1} extra nodes; val: +2; held-out: +3), and the held-out additionally contains two
   structure kinds (`feedback_like`, `ambiguous`) and one fault family (`recovery_instability`) that exist in no other split.
   Independence of template, topology hash and content is **verified empirically** by `scripts/sprint430_verify_independence.py`;
   the size bands are a generation mechanism, not evidence.
7. **Stage-1 detector for the detection metrics** is the EBD R1 persistence test (θ=3.0, 2 windows) with the shared baseline
   stats. Positive = a fault exists anywhere in the (possibly partly hidden) system.

*Amendment 2 hash is recorded in `artifacts/sprint4_3_0/protocol_v2_amendments.sha256`.*

### Amendment 3 — post-hoc exploratory variant RIFT-FULL-V2G (logged 2026-11-03T04:00:04Z, AFTER dev/val method runs, BEFORE freeze, held-out never read)

**Observation (dev + val only).** Running the pre-registered RIFT-FULL-V2 (config A1) on dev (N=180) and val (N=72) shows that
many of its attributions name a service whose R1 divergence is *later* than another service's R1 divergence that no confirmed
intervention explains (dev: 10 of 14 wrong ATTRIBUTE answers and 21 of 38 unsafe ABSTAIN_REQUIRED answers; val: 9 of 13 and 10 of 14).
Cause: the "explained" set only records outcomes confirmed by R4 from an intervened candidate, so an earlier divergence on a node
that failed R3 (e.g. a leaf / PAG-isolated root) is silently ignored when ranking.

**Decision.** The pre-registered method is **unchanged and remains the confirmatory method** (A1 / "RIFT-FULL-V2"; all
Holm-family tests, all ablations A1-A10 and the H1-H5 hypotheses refer to it). A *separate, exploratory, post-hoc* variant
**RIFT-FULL-V2G** adds one rule: after choosing the attributed service `x*`, abstain with `UNRESOLVED_EARLIER_DIVERGENCE` if any
service with R1 divergence earlier than `t*(x*)` is neither `x*` nor explained by a confirmed intervention. No threshold is tuned;
the rule has no free parameter. V2G is reported in a separate table labelled **EXPLORATORY / POST-HOC**; it is excluded from
the confirmatory family and from Rule 15.1 statements. Because it was designed after seeing dev/val failures, any improvement it
shows on held-out is a *hypothesis-confirming replication test* of one pre-declared rule, not a new tuned result.

**Dev/val effect (recorded for transparency, trade-off not a free gain).** dev: unsafe 52/180 -> 26/180, coverage 80/180 -> 50/180,
P1 28/68 -> 24/68, P2 102/180 -> 117/180. val: unsafe 27/72 -> 12/72, coverage 35/72 -> 17/72, P1 8/31 -> 5/31, P2 35/72 -> 41/72.
The guard buys safety with attribution coverage; it does not improve attribution accuracy.

*Amendment 3 hash is recorded in `artifacts/sprint4_3_0/protocol_v2_amendments.sha256` (previous amendment hash retained in `protocol_v2_amendments_history.txt`).*
