# RIFT — Confirmatory Infrastructure: Implementation Plan and Test Plan

**This is a plan. Nothing in it has been built, run on confirmatory data, or approved.** No confirmatory scenario was generated and no sealed held-out file was opened, read, listed or hashed to write it. It is written by an AI agent and is not an independent review (D7 still needs a named human; see `docs/FINAL_APPROVAL_MATRIX.md`).

Date: 2026-11-04. Branch `sprint-4.5.1-prereg-finalization`, HEAD `1efc229783a4adece3c4041efb6ae8a9aa29b326`.

Governing documents (read directly for this plan): `docs/SPRINT4_5_0_PREREGISTRATION.md` (PRE) §7, §9, §11, §13, §14; `docs/SPRINT4_5_0_STATISTICAL_ANALYSIS_PLAN.md` (SAP) §1–§3, §5, §7–§9, §12; `docs/SPRINT4_5_0_DATASET_PROTOCOL.md` (DP) §2–§9; `docs/SPRINT4_5_0_CID_EXPERIMENT_DESIGN.md` (CID) §3, §4, §6, §7, §9. Where this plan disagrees with one of them, the disagreement is listed in §10 and the preregistered text is not changed by this plan.

A parallel AI-written draft was moved, unedited, to `artifacts/final_closure/FINAL_CONFIRMATORY_INFRASTRUCTURE_PLAN.parallel_draft.md` so that this closure has a single canonical plan. Where this plan differs from it, the difference is deliberate and noted in §11.

## 0. Hard rules this plan keeps

1. No confirmatory data are generated until G4 (PRE §7). A code-level lock enforces this (§3.6).
2. No file in the 69-file extended freeze manifest is edited. New code imports frozen modules and never patches them at runtime in the confirmatory path.
3. The sealed files (`datasets/rift_v2/heldout_candidate.json`, `heldout_status.json`, `artifacts/sprint4_3_0/results/held_out/`) are never opened by any new code, test or script. A test enforces this (C11).
4. Labels, thresholds, λ, γ, δ, N, α, the quota matrix and the interpretation table are not changed. Fixes to the plan's own ambiguities (§10) are amendments that must be recorded before hashing (PRE §13).
5. Tests run on dev/val (committed, readable), `datasets/rift_v3_dev/adversarial_dev.json` (committed), or pilot-tag scenarios generated in memory. No RIFT method is scored on pilot-tag output (DP hard rule 4).

## 1. What exists and what is missing (checked on disk this step)

| # | Component | Status | What exists | What is missing |
|---|---|---|---|---|
| 1 | Independent generator | **MISSING** (prototype only) | `scripts/sprint451_dataset_protocol_checks.py` (tracked): motif table `MOTIFS`, `_proto_topology`, `label_with_wrapper`, `drift_stat`, `quota_matrix`, `accept_once`, `build_library`. It swaps `gv2._build_topology` in process memory (line 117), so it is analysis tooling, not a module | `src/rift/scenarios/generator_confirm.py`; it does not exist |
| 2 | Hashed confirmatory runner | **MISSING** | `scripts/sprint440_run_v3.py` runs V3 configs but refuses anything but dev/val (line 53) and has no error handling; `benchmark_v2.run_methods` runs the baselines and V2 | `scripts/sprint450_run_confirm.py` |
| 3 | Preregistered analysis script | **MISSING** | `src/rift/evaluation/stats_v2.py` (frozen, in the manifest): percentile cluster bootstrap, exact McNemar, sign-flip, Holm adjusted p. Prototype of the stratified bootstrap-t in `scripts/sprint451_stratified_power.py` (`strat_boot_reject`); prototype of the family-block rule in `sprint451_family_block_power.py` | `scripts/sprint450_analyze.py`; interpretation function; report template. `error_flag` appears in no `*.py` file |
| 4 | Dataset manifest and integrity checks | **PARTIAL** | `scripts/sprint451_extended_manifest.py` (69-file freeze manifest, never opens sealed paths; it only lists them as FORBIDDEN names), `scripts/sprint451_freeze_closure.py`, `artifacts/sprint4_5_1/freeze/extended_manifest.json`, `src/rift/scenarios/independence.py` (`verify_independence`, `strip_labels`) | Confirmatory provenance writer, dataset hash check, post-run record check, `scripts/verify_confirm_integrity.py`; `prereg.sha256`, `decisions.json`, `freeze_verification.json` |
| 5 | Result records (scenario and group level) | **MISSING** | Frozen record shape from `benchmark_v2._out_to_rec` (fields: `abstained, reason, top, ed_s, n_do, evidence_type, path_kind, cid_grades, ident_status, detect_latency_s, runtime_s, mem_kb, error`) | `error_flag`, charged n_do, V3 `status`/`confirmed`/`intervened`/`diverging`, group id, seeds, code hashes |
| 6 | Statistics and CIs | **MISSING** as the SAP estimator | see #3 | stratified ratio estimator, CR1 variance, B = 20,000 bootstrap-t (seed 4505), family-block bootstrap (seed 4506), Holm over {H2,H3,H4}, Newcombe/McNemar, sensitivities |
| 7 | Baseline comparison | **EXISTS, needs a label-free entry** | `benchmark_v2.REGISTRY`: 13 entries (10 non-oracle, 3 oracle); 8 flagged `confirmatory=True`; `run_methods` | V3 and always-abstain are not in `REGISTRY` (V3 is run via `run_v3` + `V3_CONFIGS["V3-FULL"]`, always-abstain via `sprint440_analyze.always_abstain`). `run_methods` reads `sc["ground_truth"]` at line 198 even for non-oracle methods: on a label-stripped scenario it raises `KeyError: 'ground_truth'` (executed on dev this step); with an inert placeholder it runs |
| 8 | CID estimator comparison (Phase A) | **MISSING** | Design only (CID §3–§7); `artifacts/sprint4_5_1/cid/cell_list.csv` (218 rows: 96 null, 122 alternative, 8 degenerate, 210 distinct DGPs; R = 2000 for 214 rows and 10,000 for 4); frozen `src/rift/cid/cid.py::compute_cid` | `src/rift/cid_reliability/` (dgp, estimators E0–E7, run, analyse) |
| 9 | Error and abstention accounting | **PARTIAL** | `benchmark_v2._timed`, `_error_out`, `TIMEOUT_S = 60.0` | A runner implementing the preregistered rule (D21). Measured this step: the frozen harness does **not** do what PRE §9 says (see §5.3) |
| 10 | Reproducibility metadata | **PARTIAL** | `scripts/sprint442_capture_environment.py` records Python, platform, versions of numerically relevant packages including `causal-learn` through `importlib.metadata`, thread env vars, seed table, git commit and branch, protected-file existence | git dirty state (not recorded; the working tree currently has 13 modified tracked files), file hashes of the new code, dataset hashes, run-time arguments (§8) |

Other items that exist: `scripts/sprint442_run_tests.py` and `reproducibility/protected_materials.py` (reproducibility-aware harness; `.github/workflows/test.yml` calls it in the uncommitted working tree), `reproducibility/requirements-canonical-py39.lock.txt`.

## 2. Order of work and dependencies

```
Researcher / reviewer decisions (blocking)      Engineering (after the decisions they depend on)
-----------------------------------------      -------------------------------------------------
D7  name reviewer + checklist  ────────────────►  WP6 reviewer sign-off (needs WP1–WP5 done)
D23/LC decide label co-reporting  ─────────────►  WP1 generator label-side fields
D21 runner semantics + §10 F8/F9  ─────────────►  WP3 runner
D19, D22 field specs, F4 index map ────────────►  WP1 generator, WP4 analysis
D20 SNR band                       ────────────►  WP1 (stored covariates), WP4 (stratum)
```

| WP | Deliverable | Depends on | Notes |
|---|---|---|---|
| WP0 | Settle §10 ambiguities as pre-hash amendments | researcher | cheap; do first |
| WP1 | `src/rift/scenarios/generator_confirm.py` + tests T1–T8, T10, C1–C3 | D6, D18, D23, D20, F4 | largest piece |
| WP2 | Pilot tooling: acceptance sampler run in memory (T6, T7) | WP1 | pilot tag only |
| WP3 | `scripts/sprint450_run_confirm.py` + C6, C9 | D21, WP1 schema | tested on dev/val only |
| WP4 | `scripts/sprint450_analyze.py` + `src/rift/evaluation/confirm_stats.py` (new) + C4, C5, C7, C10, C12 | D19, D22 | tested on dev/val and simulated tables |
| WP5 | `scripts/verify_confirm_integrity.py`, provenance writer, G4 lock, C8, C11 | WP1, WP3, WP4 | |
| WP6 | T9 independent human review, per attempt | D7 | cannot be done by an AI |
| WP7 | Phase A `src/rift/cid_reliability/` | A1–A9, X12 | does not gate V3 generation (PRE §8) |

I give no effort estimates. The earlier plan's day counts were not measured and are not repeated here.

## 3. WP1 — Independent confirmatory generator

### 3.1 Why a module and not the frozen builder

`generator_v2.build_scenario` looks up `_SIZE_BAND[split]` and `SPLIT_PREFIX[split]` (lines 65–68, 197–198) that only know dev, val and held_out, and `_build_topology` knows only the 11 old structure kinds. DP §2 verified the template inventory is exhausted (11 × 16 = 176 templates, all assigned to dev, val or held-out). Route A (D6) is therefore a new module.

### 3.2 Implementation choice for the reviewer (D7) to confirm

* **Option A (recommended): a parameterised copy of the `build_scenario` draw sequence** inside `generator_confirm.py`, importing the frozen `simulator.py`, `compute_ground_truth`, `content_hash` and the level lists unchanged. The copy accepts a registry (structure builders, size band, prefix, seed tag). T1 proves it is faithful: in "legacy registry" mode it must reproduce the stored dev/val `content_hash` for ≥ 100 dev and ≥ 50 val specs.
* **Option B: run the frozen `build_scenario` with module globals swapped at runtime**, as the prototype does. This mutates process-global state of a frozen module, is not thread-safe, and any difference is invisible. Acceptable for pilot tooling, not recommended for the confirmatory path.

The prototype shows B works on pilot indices; it does not show the copy in A is faithful. T1 is the control that must pass before A is trusted.

### 3.3 Module interface

```
generator_confirm.py
  GEN_TAG = "rift-confirm-gen/1.0.0"                       # DP §4
  MOTIFS (S01..S16), MUTUAL = {S13,S14}, HIDDEN_ROOT = {S11,S12}
  derive_seed(tag_kind, i)   -> sha256(f"{GEN_TAG}|{tag_kind}|{i}")[:8] & 0x7FFFFFFF
  build_topology(kind, rng)  -> nodes, edges, hidden, latent, roots, mutual     # motif + periphery 0..3
  build_scenario(tag_kind, i, structure, family, temporal, workload, observability, intervention, negative)
  label(sc)                  -> frozen compute_ground_truth on a shallow copy (S13/S14 -> "ambiguous")
  validation_view(sc)        -> copy mapped to frozen names for frozen validators (§3.5)
  QUOTA, quota_matrix()      -> DP §5.2
  accept(candidate, state)   -> R-CAP1, R-OWN, R-NOVEL, R-DUP, template_full, cell_full
  generate(tag_kind, ...)    -> only tag_kind == "pilot" is allowed unless the G4 lock passes (§3.6)
```

* `tag_kind` is `"pilot"` for all tests and `"confirm"` only at G4. The seed formula in DP §4 uses the literal strings `confirm` and `pilot`.
* Scenario ids are `V3C-<number>`; no structure token and no label-bearing string.

### 3.4 Quotas, S13/S14 exception, acceptance rules

Quota matrix (DP §5.2, X11). I re-added it this step: ATTRIBUTE 8×67 + 4×66 = 800; WEAK_SIGNAL 12×30 = 360; INSUFFICIENT_BASELINE 12×15 = 180; NO_DISCRIMINATING_EVIDENCE 8×12 + 4×11 = 140; NO_FAULT (6×8 + 6×7) + 2×5 = 100; ROOT_UNOBSERVED 2×120 = 240; SYMMETRIC 2×90 = 180; total 2000.

| structures | row total | templates | per-template scenarios |
|---|---:|---:|---|
| S01–S08 | 132 or 131 | 16 | 8 or 9 (132 = 16·8 + 4) |
| S09, S10, S15, S16 | 130 or 129 | 16 | 8 or 9 |
| S11, S12 | 125 | 16 | 7 or 8 (125 = 16·7 + 13) |
| **S13, S14** | **90 each** | 16 | **5 or 6 (90 = 16·5 + 10); the declared exception** |

* The S13/S14 exception is implemented as data (two rows of the quota table with a single SYMMETRIC cell), not as a special case in code, and test C1 asserts it: `QUOTA[S13] == QUOTA[S14] == {"SYMMETRIC_MUTUAL_DEPENDENCY": 90}`, column total 180, grand total 2000, row totals within 129–132 except S11/S12 (125) and S13/S14 (90). The earlier criterion "125 ± 15 per structure" stays withdrawn (DP §5.2).
* The wrapper (DP §3.3): `compute_ground_truth` is called on a shallow copy with `dimensions.structure = "ambiguous"` only for S13/S14. The stored scenario keeps its true structure name. Test T2 covers S13/S14 → SYMMETRIC, S11/S12 → ROOT_UNOBSERVED, others by state.
* Acceptance rules (DP §6.2): R-CAP1 (≤ 1 accepted scenario per topology hash), R-OWN (a topology hash owned by another template is rejected), R-NOVEL (reject hashes derivable from the frozen design space or any readable protected set), R-DUP (content/dynamics duplicates; spec similarity ≥ 0.88 against readable sets), `template_full`, `cell_full`. Budget 10,000 candidates per structure. Shortfall ≤ 10 scenarios (N ≥ 1990) is recorded; larger fails QC. At most 3 attempts (D15); quotas, motifs and rules are not changed between attempts.
* Geometry gates (DP §6.3): K = 256, K ≥ 250, maximum group size ≤ 14, unique-topology share ≥ 0.99, ≤ 1 scenario per topology hash, 16 groups per structure, no union-find group spanning CONFIRM and a protected set.

### 3.5 Validation view (needed to run the frozen validators)

The frozen validators reject new structure names and compare against frozen strings. Reading `validators.py` this step, the view must map all of: `dimensions.structure` (→ a frozen name; S13/S14 → `ambiguous`, which `check_graph` requires to contain a cycle), `template_id` (so `template_id == f"{structure}|{family}"` still holds in `check_ground_truth`, line ≈ 139), `generator_version` (`check_schema`, line ≈ 38), and it must skip `check_reproducible` (it rebuilds with the frozen builder and cannot reproduce a new-tag scenario; determinism is tested by T4 instead). The mapping is part of the reviewed code.

### 3.6 G4 lock (prevents premature generation)

`generate("confirm", …)` refuses unless all hold: `artifacts/sprint4_5_0/prereg/prereg.sha256` exists; the generator's own SHA-256 equals the value recorded in it; `decisions.json` records D7 sign-off with a named reviewer; and the attempt counter in the provenance ledger is below D15's limit. Tests C11 and T4 assert the refusal path with the files absent (today they are all absent). This does not replace human control, but it makes an accidental early run fail closed.

### 3.7 Node-order randomisation (finding G; T10)

Dev/val facts quoted from DP §3.5 and `artifacts/sprint4_5_1/nodeorder/node_order_investigation.json` (not re-run this step): the true root is first in `graph.nodes` in 99/99 attributable scenarios with an observed root; frozen V3 changed output in 0/252 scenarios under three observation-order permutations while B0-EARLIEST changed in 35/252; V2 was not tested (the JSON's method list is V3-FULL, B0-EARLIEST, B0-HIGHEST, B1, B3, B5, B7).

Two facts established this step change how T10 must be built:

* **Permuting `graph.nodes` or `edges` inside a stored scenario changes the simulated data**, because `simulate_full` draws noise from one RNG stream in node order. On the 252 dev/val scenarios, 243 had different simulated series after a node and edge permutation; only 9 were unchanged. The ground-truth label fields were unchanged in 252/252, because `compute_ground_truth` uses the noise-free `apparent_signal`.
* So the generator applies its permutation **once, before simulation**, as part of the scenario definition (drawn from the scenario seed independently of node role), and labels are computed on the stored order. This is safe because labels are order-invariant (252/252).

Consequence for T10 part 2 (method invariance): it must permute the **method-facing `observe()` output** (metrics dict order, call-graph insertion order, baseline stats), as `scripts/sprint451_node_order_investigation.py::permuted_obs` does. It must not permute the scenario graph, which would regenerate different data and confound the comparison.

T10 part 1 statistic: position of the first true root among the observed nodes is not on a common scale (observed node counts differ), so the expected count per position is computed as Σ over scenarios of 1/n_i, and the chi-square uses those expectations; a permutation test is run alongside. α = 0.01 for both. The position of the root inside `faults[]` and in `observed_services` order should be reported as well, as a hygiene check (`strip_labels` leaves `faults`).

## 4. WP2 — Pilot tooling (no methods run)

* `scripts/sprint450_pilot_qc.py` (new, optional): runs the acceptance sampler on the pilot tag in memory, prints aggregate counts only, and writes nothing under `artifacts/sprint4_5_0/confirm/`.
* It covers T5, T6, T7 and the quota-feasibility check (every cell reachable; prototype: ≥ 5× within 12,000 candidates). The prototype took about 98 s per attempt, so T6 and T7 are owner-run scripts with stored output, with only small seeded smoke versions in `tests/`.
* Note from DP §5.2: `partial_degradation` has a natural ATTRIBUTE share of about 0.059, and 69–72 of 256 templates carry no ATTRIBUTE scenario. T6 must report this and not treat it as a failure.

## 5. WP3 — Hashed confirmatory runner `scripts/sprint450_run_confirm.py`

### 5.1 Interface

```
python3 scripts/sprint450_run_confirm.py --dataset <stripped.json> --out <records.jsonl>
        --methods <list> [--resume-check]
```

* Input is the **label-stripped** file only. Every method receives `observe(sc)` output and an `intervene` callable, never the scenario record (DP §9.3, T8).
* Methods and entry points: V3-FULL via `run_v3(o, iv, fid, seed, V3_CONFIGS["V3-FULL"], cache=SharedCache())`; V2 and the others via `benchmark_v2.run_methods(...)` with `methods=[…]`; always-abstain computed analytically (U ≡ 0, n_do = 0, cannot fail, SAP §7). Comparators from PRE §6: RIFT-FULL-V2, RIFT-FULL-LEGACY, B0-EARLIEST, B0-HIGHEST, B1-LATENCY-CORR, B3-SIEVE-LIKE, B5-RIFT-OBS, B6-RIFT-RANDOM, B7-RIFT-ONE-SHOT. `RIFT-FULL-V2G` is exploratory and post hoc (registry comment) and is not in the preregistered list.
* **Placeholder issue:** `run_methods` reads `sc["ground_truth"]` unconditionally (line 198). The runner passes an **inert placeholder** `{"expected_outcome": None, "roots": []}` (verified to run for a non-oracle method). Test T8 poisons every label field with that placeholder replaced by garbage and requires byte-identical method outputs. ORACLE rows need real labels and are computed in a **separate, clearly labelled labelled-side stage** (§10 F8).
* Identical observed windows and seeds for all methods: `observe(sc)` is called once per scenario and shared; `do()` seeds follow the existing rule `seed_do = (scenario_seed·7919 + crc32(node|v3)) & 0x7FFFFFFF` inside V3.

### 5.2 Records

One JSON line per scenario × method. Fields: the frozen `_out_to_rec` fields; plus `error_flag` (0/1), `error_type`, `n_do_charged`, `status`, `caveats`, `possible_roots` (V3), and for D22 the V3 raw fields `intervened`, `diverging`, `confirmed` and `cid_grades` (the frozen `_out_to_rec` keeps only `cid_grades`; the others are in `raw_output`); `scenario_id`, `method_id`, `seed`, `runner_sha256`, `wall_s`. Group-level rows (template id, structure, family, sums S_g) are built by the analysis script from these records and the labelled file, never by the runner.

### 5.3 Error semantics (D21): what the frozen harness actually does

Executed this step against `benchmark_v2`:

| case | frozen behaviour | PRE §9 / SAP §7 text |
|---|---|---|
| method raises | `_timed` returns `out=None`, `err="METHOD_ERROR:<Type>"`; `run_methods` builds an abstention via `_error_out`; record has `n_do = 0`, `ed_s = 0.0`, `error` set | "abstention with `error_flag = 1`, and the n_do consumed up to the failure counted" — the frozen harness charges **0** |
| method returns after > 60 s | `_timed` keeps the output and sets `err="TIMEOUT"` (with `TIMEOUT_S` patched to 0, the output "ANSWER" was kept); the record is **not** an abstention (`abstained=False`, `n_do` kept, `error="TIMEOUT"`) | "a call over 60 s is recorded as an abstention with `error_flag = 1`" |
| preemption | none: `_timed` measures elapsed time after the call returns | — |

So the preregistered rule is not a reproduction of the frozen behaviour; it is a stricter, different rule. The runner must implement the preregistered rule explicitly:

* wrap `intervene` in a counter so the number of `do()` calls consumed survives an exception or a late return, and charge it as `n_do_charged`;
* classify a call whose wall time exceeds 60 s as an abstention with `error_flag = 1`, even if it returned an answer (the answer is stored in a separate field and not scored);
* separate **method failure** from **harness failure** by a stated rule (suggestion for the researcher: an exception raised inside the method callable is a method failure; `MemoryError`, `OSError`, `KeyboardInterrupt`, a worker crash or disk error is a harness failure that is re-run once with the same seeds and logged);
* optional hard wall-clock limit (e.g. a subprocess kill at a preregistered multiple of 60 s) is a harness safeguard against hangs and is logged as a harness failure. The value is a researcher decision.

V3 averaged 0.067 s per scenario on dev and 0.105 s on val (PRE/DP), so timeouts should be rare for V3. They may not be for the learned-FCI comparators; this is why the count of error rows per method and structure must be reported (SAP §7).

### 5.4 Integrity stops (PRE §11) implemented in the runner

Any frozen-hash mismatch (checked at start against `prereg.sha256`), any independence-check failure recorded in `provenance.json`, any label-bearing key reaching a method (T8 interface assertion at start), held-out seal check failure, and < 95% completion for a method (completion = a record exists, error rows included). H1 depends on V3 completeness only; always-abstain cannot fail. The runner writes the completion fraction per method.

### 5.5 Testing the runner

Only on dev/val and pilot-tag scenarios in memory (and, per hard rule 4, no method on pilot-tag output: for pilot-tag input the runner is tested with **stub methods**). Tests C6 and C9 (§9).

## 6. WP4 — Analysis `scripts/sprint450_analyze.py`

New library module `src/rift/evaluation/confirm_stats.py` (does not touch the frozen `stats_v2.py`) plus the script. Inputs: records (§5.2), the labelled file (hash must equal the recorded one, DP §9.4), `prereg.sha256`.

* **Estimand and estimator (SAP §1, §3):** θ̂ = Σ_s W_s θ̂_s with W_s = n_s/N (realised design weights, fixed), θ̂_s = Σ_{g∈s} S_g / n_s. S13/S14 carry 90 each, so the realised weights are not equal; the equal-weight macro-average is reported as a sensitivity (SAP §1, §9.6).
* **Variance:** stratified CR1 as in SAP §3 (the K_s/(K_s−1) factor, requires K_s ≥ 2).
* **Primary:** stratified group bootstrap-t, B = 20,000, `numpy.random.default_rng(4505)`, single generator used in the order H1, H2, H3, H4, H5…; groups resampled within structure; weights fixed; one-sided p = (1 + #{t*_b ≥ θ̂/ŝe})/(B + 1); studentised 95% CI per SAP §3. The one permitted rerun is B = 100,000 with the same seed rule when the p rule and the CI rule disagree (SAP §3.1, last bullet).
* **Family-block sensitivity (D19):** resampling unit = fault-family column (16), seed 4506, structure weights fixed; the report states in its first paragraph "not robust to family-level dependence" if the family-block lower bound ≤ 0 while the primary is > 0. This plan recommends stating **both** intervals and the 16 × 16 scope in the first paragraph always (a proposal from the validity closure; it needs researcher approval).
* **Decision rules (SAP §5, PRE §10):** H1 alone at one-sided 0.025; then Holm over {H2, H3, H4} at total 0.025; otherwise those rows are labelled "descriptive, not confirmatory". The interpretation label is a **pure function** of (lo, hi, θ̂, operational lo), tested for exhaustiveness and mutual exclusivity (C7). Note the existing `stats_v2.holm` adjusts all p-values with factor m−i over the given set; the new code applies it only to the three secondary hypotheses.
* **Endpoints:** H1: d_i = U_V3,i; H2: U_V3 − U_V2; H3: S_V2 − S_V3 (unsafe indicator); H4: C_V3 − C_V2 on ATTRIBUTE scenarios only (S11–S14 drop out); H5 exploratory with no multiplicity correction; ORACLE rows labelled "ORACLE (privileged upper bound)" with no p-value. Utility is U = C − 2.0·S − 1.0·(n_do/20), with `MAX_DO = 20` (confirmed in `rift_v2`). C and S follow `benchmark_v2.score_one` for the strict definition; the operational unsafe definition is `answered ∧ top1 ∉ roots` (SAP §9.3).
* **Binary outcomes:** exact McNemar (mid-p included) and a Newcombe/Wilson paired interval; these ignore clustering and are supporting only (SAP §4).
* **Descriptive and sensitivity outputs (SAP §8–§9):** strata tables (expected outcome, abstain reason, temporal-confound stratum, structure, family, SNR band [3,5) per D20, novel-vs-variant structure), (λ, κ) grid, break-even λ* and prevalence, post-stratification, coverage-risk from `V3-DEFINITIVE-ONLY`, CR1 and percentile alternatives, leave-one-group-out and leave-structure-out, mixed-model ICC (statsmodels `MixedLM`, in `requirements.txt`), missing-data variants (SAP §7), multiplicity-free variant of H2–H4.
* **Pair-level endpoint (D22):** false-confirmation rate of non-ancestral pairs by drift stratum. Pairs are (x, y) with x ∈ `intervened` and y ∈ `diverging`, taken from the runner records; non-ancestry and drift come from the labelled file. It is conditional on V3's own choice of which pairs to test (stated in the report). The generator must store, per scenario, per observed y: |d(y)|/σ_y and the set of observed non-ancestors of y on the full graph including hidden nodes (open item F5).
* **Error accounting tables:** counts of `error_flag` rows per method and structure, completion fraction, and the three missing-data sensitivities.

## 7. WP5 — Manifest, integrity, G4 lock

* **Pre-run (G1):** re-hash the 51-file and 69-file manifests (existing scripts; neither lists a sealed file), write `freeze_verification.json`, run `scripts/sprint442_run_tests.py` (owner-run `--require-protected` for D12), and the owner-run seal check. No new code hashes a sealed file. `verify_heldout_sealed.py` covers the legacy set only (audit D12).
* **Provenance (G4):** `artifacts/sprint4_5_0/confirm/provenance.json` with the fields in DP §9.2 item 4 plus the additions in §8; `confirm.json` and `confirm_stripped.json` with SHA-256 each; append-only ledger row.
* **`scripts/verify_confirm_integrity.py`:** (a) generator, runner, analysis and wrapper hashes equal those in `prereg.sha256`; (b) dataset hashes equal `provenance.json`; (c) the stripped file equals `strip_labels` of the labelled one; (d) record file hash recorded after the run; (e) record counts equal scenarios × methods; (f) refuses to read any path matching the sealed names (C11).
* The ledger location is not defined anywhere in the preregistration documents (they only say "a ledger row"). Proposed: `artifacts/sprint4_5_0/prereg/ledger.jsonl`, append-only, one JSON object per event. This is a proposal (F10).

## 8. Reproducibility metadata

Record, at generation and at run time: everything `sprint442_capture_environment.capture()` already records, plus: `git status --porcelain` hash and the list of modified files (the tree must be clean at G4 and G5; today it is not); SHA-256 of each new code file and of the frozen 69 files; dataset SHA-256 (labelled, stripped); command line and arguments; `PYTHONHASHSEED`, thread variables (already captured) set to fixed recorded values; wall time per scenario and per method; counts of rejected candidates by reason; first and last accepted candidate indices; operator; RFC 3339 UTC timestamps.

Environment rule: generate and run in the canonical environment (CPython 3.9.6, `reproducibility/requirements-canonical-py39.lock.txt`). CI runs the unit tests on Python 3.11 with `requirements.txt`, a different stack (e.g. numpy 1.26.4 versus 2.0.2, causal-learn 0.1.3.8 versus 0.1.4.8). Sprint 4.4.2 found identical scores and one record differing in `ident_status`. So CI shows that tests pass in that stack; it does not show that confirmatory numbers would reproduce there. Run T1 in both environments; a mismatch in the CI stack is reported, not hidden.

## 9. Test plan

### 9.1 Preregistered tests T1–T10 (DP §7)

All use dev/val, adversarial_dev, or in-memory pilot-tag objects. "CI" = suitable for the Python 3.11 GitHub Actions checkout using only committed files; "owner" = long-running, run by the owner with stored output.

| ID | Test | Pass criterion | Where | Sealed access? |
|---|---|---|---|---|
| T1 | Replication in legacy-registry mode: rebuild ≥ 100 dev + ≥ 50 val specs from `datasets/rift_v2/{dev,val}.json` | identical `content_hash` and identical labels for every one (prototype reproduced 90/90) | CI + env comparison | No |
| T2 | Label wrapper | S13/S14 → SYMMETRIC_MUTUAL_DEPENDENCY; S11/S12 → ROOT_UNOBSERVED; others by state; stored structure name unchanged | CI | No |
| T3 | Schema | every key emitted by `build_scenario` present with same type | CI | No |
| T4 | Determinism | 200 pilot scenarios generated twice are byte-identical; `generate("confirm")` refuses (§3.6) | CI | No |
| T5 | Non-isomorphism of the 16 motif cores against the frozen design space (11 kinds × extra 0–4, with decoy / hidden-confounder / secondary-fault augmentations) | zero isomorphic cores; peripheries handled by R-NOVEL; rerun on final motif definitions | owner (library build is large) + CI smoke | No |
| T6 | Quota feasibility, 6000 pilot candidates under the acceptance rules | every §5.2 cell reachable within budget; geometry gates met | owner | No |
| T7 | Independence dry run: pilot set versus dev, val, adversarial_dev via `verify_independence` on the validation view | zero shared content/dynamics/topology/template/joint-cell keys; zero confirm-spanning groups; zero near-duplicates ≥ 0.90; max similarity ≤ 0.88 on the accepted set | owner | No |
| T8 | Leakage / interface: signature `run_v3(o, iv, fid, seed, …)`, key set of `observe()`, ids start with `V3C-` and carry no structure token; poison every label field and require byte-identical `observe()` and method outputs | no label-bearing key or string reaches a method; a mere check that `ground_truth`/`design` are absent is not enough | CI | No |
| T9 | Independent human review with a written checklist | signed by a named human | manual | — |
| T10 | Node order. Part 1: root-position uniformity on accepted pilot scenarios (χ² with expectations Σ 1/n_i and a permutation test, α = 0.01). Part 2: permute **`observe()` output** three times per scenario on dev/val (not pilot, not the scenario graph, §3.7) and compare V3-FULL, V2 and baselines | Part 1 passes; Part 2 report filed before generation. V3 change would be reported, not fixed | Part 1 owner; Part 2 owner (heavy) + CI smoke | No |

### 9.2 Additional tests proposed by this plan (C-series)

| ID | Test | Pass criterion |
|---|---|---|
| C1 | Quota table integrity (X11) | S13 = S14 = {SYMMETRIC: 90}; SYMMETRIC column 180; all columns as §3.4; grand total 2000; per-template counts 5–9 |
| C2 | Acceptance rules on synthetic candidates | R-CAP1, R-OWN, R-DUP, template_full, cell_full each reject exactly the constructed violations; accepted set order-reproducible |
| C3 | Seed and id format | seed formula equals DP §4; no collision with dev/val/adversarial seeds in a sample; ids match `^V3C-\d+$`; ids are not monotone in structure (F9) |
| C4 | Analysis reproduces dev/val numbers (SAP §12.4) | V3 mean U = −0.338 and V3 − V2 = +0.224 to three decimals; template-cluster percentile CI within 0.01 of [−0.465, −0.219]. Source numbers: `artifacts/sprint4_5_1/utility/utility_verification.json` (pct95 template −0.4613, −0.2172) |
| C5 | Bootstrap behaviour on simulated tables (SAP §12.5): template ICC ∈ {0, 0.05, 0.1}, effect {0, 0.1}, R = 2000 each, plus the family-block rule | size and power consistent with SAP §6.7(b),(c). **See the criterion problem below** |
| C6 | Runner error semantics (D21) | injected exception ⇒ abstention, `error_flag = 1`, `n_do_charged` = number of `intervene` calls made; late return ⇒ abstention with the answer set aside; harness-class error ⇒ one re-run, logged; no crash; record count preserved |
| C7 | Interpretation function exhaustive and exclusive | enumeration over a grid of (lo, hi, θ̂, operational lo) gives exactly one label for each point, including boundaries lo = 0, hi = 0, hi = δ, θ̂ = δ |
| C8 | Tamper detection | a single-byte change in any hashed file, dataset or record file makes `verify_confirm_integrity.py` fail |
| C9 | Record completeness and integrity stop | < 95% records for a method stops that method and reports the fraction; error rows count as records |
| C10 | Holm arithmetic | step-down thresholds 0.00833, 0.0125, 0.025 and adjusted p-values match a hand-checked table |
| C11 | No sealed access | static scan of all new source and test files finds no open/read/hash call on a path containing `heldout_candidate`, `heldout_status` or `results/held_out`; the integrity script rejects such a path; the G4 lock refuses |
| C12 | Pair table (D22) | on dev/val the pair table is built from V3 records; non-ancestry uses the full graph including hidden nodes; counts reproduce the audit's pair counts where stated (V3 pair set 103/110 dev, 64/69 val) within the same definitions |

**Criterion problem in C5 / SAP §12.5 (found by computation this step).** SAP §12.5 requires "size ≤ 0.03 at α = 0.025" from R = 2000 repetitions. For a correct procedure whose true size is exactly 0.025, P(observed rate > 0.030) at R = 2000 is about 7%, so a correct script fails this check about one run in fourteen. The SAP's own table shows a true bootstrap-t size of 0.034 at rg = 0.03 (R = 1000, one cell). Proposed fix, to be recorded as a pre-hash amendment: use an exact binomial cut-off fixed in advance (for example k ≤ 67 of 2000 corresponds to P(Bin(2000, 0.025) > 67) ≤ 0.01) and fixed seeds so the test is deterministic. This is a test-design clarification, not a change to α.

### 9.3 CI plan

* New tests live in `tests/unit/test_confirm_generator.py`, `test_confirm_analyze.py`, `test_confirm_runner.py`, `test_confirm_integrity.py` (none exist today). The workflow already runs `scripts/sprint442_run_tests.py tests`, so they are collected without a workflow change.
* Only the CI-suitable parts (small seeded variants) go in `tests/`. The long jobs (T5 library, T6, T7, T10, C5 at full R) are owner scripts with stored output under `artifacts/sprint4_5_0/pretests/`, hashed at G3.
* No new test touches protected material, so none needs entries in `reproducibility/protected_materials.py::PROTECTED_TESTS`. If any test were to depend on a protected file it must be added there so it reports PROTECTED-MATERIAL-UNAVAILABLE and never a silent skip or a pass.
* New files must not contain the six forbidden phrases in the Makefile list (`FORBIDDEN_PHRASES`, Makefile lines 22–28), including inside negations, because the lint step greps them; but see the next point.
* **CI lint gives no signal today.** `make lint` stops at `Makefile:188: *** missing separator` (reproduced this step; `make -n clean` fails identically) and the workflow marks the lint step `continue-on-error: true` (line 70 of the working tree, line 37 at HEAD). CI must not be described as clean on the basis of lint. This is matrix rows N2 and N3.
* A green CI run would run in the Python 3.11 / `requirements.txt` stack (matrix N4).

## 10. Open specification points to fix before hashing

These are amendments to a preregistration that is not yet recorded. They are listed so the reviewer and researcher see them; none is decided here.

| ID | Point | Why it matters |
|---|---|---|
| F1 | D21: the runner rule differs from the frozen harness (§5.3) | text says "reproduces `_timed`"; it cannot |
| F2 | G0 scope: "all D-items" (PRE §7) versus "approves §14" (PRE §13) | which rows need a recorded answer |
| F4 | Candidate index map: DP §4 defines one global order 1, 2, 3, … feeding the seed, while DP §6.2 applies a budget of 10,000 candidates per structure and the prototype loops structure by structure | the seed for (structure s, k-th candidate) is undefined. Suggested map `i = 10,000·(s−1) + k`, so M = 160,000; needs a decision |
| F5 | D22 pair fields (per-y drift, non-ancestor set) are not in the protocol | the generator must store them |
| F8 | ORACLE rows need labels but the runner is label-free | decide whether ORACLE runs in a labelled-side stage after the stripped run, and hash that stage too |
| F9 | Scenario ids are "opaque running numbers", but assigning them in the accepted order, which proceeds structure by structure, would make the id monotone in structure | assign ids after a seed-derived shuffle of the accepted set; run in that order |
| F10 | The "ledger" has no defined location or format | see §7 |
| F11 | SAP §12.5 size criterion (§9.2) | a correct script can fail by chance |
| F7 | T10 part 2 is "dev/val only" in the DP §7 header and "dev/val (and the pilot tag)" in the T10 row; hard rule 4 forbids scoring pilot output with a RIFT method | this plan follows the stricter reading: dev/val only for method comparison, pilot only for root-position statistics |
| F12 | `faults[]` and `observed_services` order may also carry the root-first pattern, and `strip_labels` leaves `faults` | report it in T10 part 1; confirm methods never read the scenario record (T8) |

## 11. Differences from the parallel draft (`artifacts/final_closure/FINAL_CONFIRMATORY_INFRASTRUCTURE_PLAN.parallel_draft.md`)

* That plan says the runner will execute "all 12 comparators". The registry has 13 entries (10 non-oracle, 3 oracle), V3 and always-abstain are not in it, and the preregistered comparator list has 9 non-AA comparators plus ORACLE rows. This plan uses the preregistered list.
* That plan says it must add `causal-learn` version capture; `sprint442_capture_environment.py` already records it.
* That plan describes T10 part 2 as "V3 invariant under 3 node permutations on dev/val" without saying what is permuted. This plan specifies the observation-level permutation, because a graph-level permutation changes the data (243/252 scenarios in a check run this step).
* That plan does not mention the D21 mismatch, the `run_methods` label read, F4, F8, F9 or the size-criterion problem.
* That plan assigns effort estimates in engineer-days. This plan gives none.

## 12. Gates and exit conditions

| gate | what must hold (PRE §7) | plan items |
|---|---|---|
| G0 | all D-items answered in `decisions.json`; D7 reviewer named | WP0 |
| G1 | 51- and 69-file manifests re-verified; test harness run; owner-run seal check; D12 decided | §7 |
| G2 | generator, runner, analysis script, interpretation function, quota table written, tested (T1–T10, C1–C12) on dev/val and pilot only, hashed | WP1–WP5 |
| G3 | PRE, SAP, DP, CID design, audit, manifests, code hashes, commit and RFC 3339 timestamp in `prereg.sha256`; signed tag if D14 | §7 |
| G4 | generate once; QC (T3, T6, T7, T10, C1); ≤ 3 attempts with per-attempt reviewer sign-off | §3.6 |
| G5 | run each method once; completion ≥ 95%; seal verification repeated (owner) | §5 |
| G6 | run the preregistered analysis; report only the interpretation table wording | §6 |

The plan is complete when every row above has an owner and every §10 point has a recorded answer. It does not authorise any step. No gate has passed.
