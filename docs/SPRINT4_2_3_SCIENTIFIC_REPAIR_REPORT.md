# Sprint 4.2.3 — Scientific and Algorithmic Repair Report

**Scope:** statistical divergence detection, EBD validation, causal-attribution validation, and
analysis of the 50 ms vs ~230 ms observation from saved data only.
**Not in scope / untouched:** network intervention, rollback, safety, watchdog, orchestrator, saved
Stage 4 artifacts, held-out dataset files, historical sprint reports. No live experiment was run.
The historical 90 s baseline/recovery polling deviation is preserved.

All results are on **synthetic ground-truth scenarios** plus **one saved live trial (n = 1)**. Results are
*intervention-consistent* observations, not proof of causal accuracy.

---

## 1. Summary

| Question | Outcome |
|---|---|
| Is the existing Stage 4 rule (Z ≥ 3 ∧ Δμ ≥ 15 ms) defective? | No algorithmic bug. It has a **low FPR (0.9 %)** and a **higher FNR (22.5 %)** on the final evaluation set; its checkout miss is explained by the data (bimodal baseline), see §3.4. **It was not replaced.** |
| Does a variance-aware detector fix checkout? | Robust (median/MAD) detectors flag checkout in the active window, **but also flag it in the post-recovery window** with no intervention. This is not shown to be an intervention effect (§3.4). |
| Defects found in EBD / attribution | **5 demonstrated and fixed** (§4, §5), plus **2 documented-only** concerns (§5.3). |
| Historical evaluation artifacts | Re-running the dev and validation splits through the modified code reproduced `RIFT-FULL` and `RIFT-FULL-ORACLE` outputs **identically (timing fields excluded)**. Held-out was not re-run. |
| Tests | **700 passed** (655 baseline + 45 new). |
| 50 ms vs 230 ms | **Not resolvable from saved data** (§6). |

---

## 2. Actual defects discovered

D1, D2 and D6 were reproduced on the pre-sprint behaviour before being changed (probe script; D1 and D2 tests were
re-confirmed failing by temporarily restoring the R2 override: 3 tests fail, 32 pass). D3, D4, D5 and D7 were identified
by code inspection and are covered by regression tests, but their failure on the old code was not separately re-executed.
Tests tagged **DEFECT** in `tests/unit/test_sprint423_ebd_attribution.py` cover these.

| # | Defect | Evidence | Status |
|---|---|---|---|
| D1 | **R2 tie-resolution block overrode strict-earlier divergence.** In `compute_ebd`, when `_check_r2` returned `False`, `earlier_or_tied` held *strictly earlier* services. If the current service was a graph ancestor of all of them, R2 was set True. A service that diverged **after** its descendant was still promoted to CANDIDATE. | Probe: A→B, B diverges at t=10, A at t=60. Before: A = CANDIDATE (`r2_pass=True`). After: A = NONE (`r2_pass=False`). | **Fixed** (block removed) |
| D2 | **Semi-directed reachability was indistinguishable from directed ancestry.** An `o-o` edge made both endpoints R3-pass; nothing in the result marked the path as non-oriented. | Probe: A `o-o` B, A at 30, B at 50 → both CANDIDATE. After: B fails R2; A carries `causal_path_kind="SEMI_DIRECTED"` + warning. | **Fixed** (labelled, not silently equated) |
| D3 | **R4 ignored CID quality.** Only `w1 > theta_cid` was checked. `INSUFFICIENT` grade, a non-significant permutation test, or `exceeds_threshold=False` could still yield DEFINITIVE. | New tests with mock CIDs. | **Fixed** (`_cid_supports_r4`; duck-typed so old mocks keep behaviour) |
| D4 | **R1 anomaly score taken over the whole window**, not the run that triggered detection (an earlier isolated spike inflated it; used as a sort tiebreaker). | Test with spike at t=10, run at t=30: reported score 20 → now 5. | **Fixed** |
| D5 | **e2e abstention ignored `identifiability_state`.** A confounder-adjacent (`NOT_IDENTIFIABLE`) top candidate without R4 was reported as a PASS attribution. | Source inspection of Stage 16 + `TestConfidenceAndAbstention`. | **Fixed** in `e2e_runner.py` (abstain when NOT_IDENTIFIABLE and not R4) |
| D6 | **Label leakage in the learned-PAG RIFT-FULL path.** `run_rift_full_scenario` chose the identifiability outcome node from the ground-truth `affected_services` field for *both* learned and oracle variants. | Code inspection + `TestNoGroundTruthLeakage`. | **Fixed** for the learned variant (`select_outcome_node`). The ORACLE variant intentionally still uses ground truth. |
| D7 | **Missing telemetry broke R1 persistence runs** (a single dropped window reset the run and shifted `t*` later). | `test_default_strict_gap...` / `test_max_gap_bridges...` | **Mitigated, default unchanged**: new opt-in `max_gap_windows` (default 0 = historical). |

### 2.1 Impact of D1–D2 on existing evaluation (measured, not assumed)

Legacy vs patched EBD, oracle-PAG graphs, same metrics:

* Development + validation: 68 scenarios → 12 differ in per-service confidence labels, **top-1 candidate changed in 0**; 3 multi-cause scenarios changed secondary ranking order (MC_01, MC_02, MC_04: `…checkout, shipping` ↔ `…shipping, checkout`).
* Adversarial cohort (30): 6 differ. Family A (inverted onset, 5/5): the late-diverging upstream root `cart` is now NONE instead of CANDIDATE; ADV_B_03: `payment` NONE instead of CANDIDATE.
* Re-running `evaluate_dataset_split` on development and validation: `RIFT-FULL` and `RIFT-FULL-ORACLE` JSON are identical to the saved artifacts after excluding timing fields.

**Implication for Family A (inverted onset):** the legacy code ranked the true root `cart` as a CANDIDATE only *because* of the D1 override. After the fix, the pipeline reports the early downstream victim (`frontend`) as the sole CANDIDATE. That is the algorithm's specified behaviour (earliest supported divergence); it means the fix **removes a lucky correct answer** in an adversarial case rather than adding one. It was not hidden.

### 2.2 Concerns documented, not changed

* **C1 — Bidirectional R1 (default).** `|z| > θ` accepts negative deviations. Kept as default to preserve historical behaviour; a directional `direction="increase"` option was added and tested. (On the stress negatives, bidirectional R1 gives FPR 22 % vs 0.9 % for the directional Stage 4 rule — see §3.)
* **C2 — R4 key mismatch in `e2e_runner`.** Stage 13/14 key CID results as `"{svc}→{svc}.downstream"`, whereas `compute_ebd` looks up `"{src}→{tgt}"` from the causal path. Through that pipeline R4 can therefore not match, so DEFINITIVE is unreachable there. The mapping depends on how downstream targets are chosen at the live stage and I did not change it without a live test; flagged as a limitation.
* **C3 — Stage 4 attribution is not a pipeline output.** `scripts/stage4_intervention_analysis.py` hard-codes `attributed = "cartservice"` and `attribution_accuracy_top1 = 1.0`. The reported 1/1 attribution was **not computed by EBD**. The script and artifact are historical and were not modified. The only claim the saved data supports is: cartservice's p99 rose after a 50 ms delay was applied to its egress, and frontend's rose with it (single trial).

---

## 3. Statistical divergence detection

### 3.1 Detectors compared (`src/rift/statistics/divergence_detectors.py`)

| Detector | Rule |
|---|---|
| `existing_stage4_rule` | aggregate: (mean(test) − mean(base)) / std(base) ≥ 3 **and** Δ ≥ 15 ms |
| `ebd_r1` | shipped EBD R1: \|z\| > 3 for ≥ 2 consecutive windows (two-sided) |
| `absolute_threshold` | test − median(base) ≥ δ for ≥ 2 consecutive windows |
| `relative_increase` | (test − median)/median ≥ p for ≥ 2 consecutive windows |
| `robust_z` | (test − median)/max(1.4826·MAD, 5 % of median) ≥ z for ≥ 2 windows |
| `persistence_z` | classical z ≥ 3 ∧ Δ ≥ 15 ms for ≥ k consecutive windows |
| `combined` | robust-z ∧ absolute ∧ relative, ≥ 2 consecutive windows |

All except `ebd_r1` are directional (increase). None reads labels.

### 3.2 Protocol (no held-out leakage)

* **Selection (development only):** `development.json`, `validation.json`, adversarial scenarios #1–3 per family, and "stress" series seeds 0–299.
  Rule fixed beforehand: lowest DEV FNR subject to DEV FPR ≤ 5 %, ties → lower FPR → larger (more conservative) threshold. `existing_stage4_rule` and `ebd_r1` are *not* tuned.
* **Freeze:** `artifacts/sprint4_2_3/thresholds_frozen.json` with SHA-256 pin in `thresholds_frozen.sha256`; the final stage refuses to run if the hash differs.
* **Final evaluation (once):** held-out split (read through `HeldOutGuard`), adversarial #4–5 per family, stress seeds 1000–1299.
* **Saved Stage 4 telemetry** was applied *after* freezing and **never used for selection**.
* Unit = one (scenario, service) series; baseline = pre-injection samples, test = samples from injection onward. Existing-dataset series carry a documented constant +100 ms offset because the generators emit zero-mean values and relative detectors need a positive level.
* `verify_heldout_sealed.py`: my new script uses no quoted held-out filename. The gate still reports **1 FAIL**, caused by `scripts/run_reproducible_evaluation.py:505` (`evaluate_dataset_split("held_out_test.json", …)`), which existed before this sprint and was not introduced here.

### 3.3 Results (final set: 597 series — 169 positive, 428 negative)

| Detector | Frozen params | DEV FPR | DEV FNR | FINAL FP/neg | FINAL FPR [95 % CI] | FINAL FN/pos | FINAL FNR [95 % CI] |
|---|---|---|---|---|---|---|---|
| existing_stage4_rule | – | 0.003 | 0.164 | 4/428 | 0.009 [0.004, 0.024] | 38/169 | 0.225 [0.168, 0.294] |
| ebd_r1 (two-sided) | – | 0.120 | 0.096 | 96/428 | 0.224 [0.187, 0.266] | 19/169 | 0.112 [0.073, 0.169] |
| absolute_threshold | δ = 40 ms | 0.047 | 0.139 | 28/428 | 0.065 [0.046, 0.093] | 42/169 | 0.248 [0.189, 0.319] |
| relative_increase | p = 0.5 | 0.035 | 0.475 | 41/428 | 0.096 [0.071, 0.127] | 63/169 | 0.373 [0.304, 0.448] |
| robust_z | z = 3 | 0.044 | 0.082 | 35/428 | 0.082 [0.059, 0.112] | 21/169 | 0.124 [0.083, 0.183] |
| persistence_z | k = 2 | 0.015 | 0.096 | 13/428 | 0.030 [0.018, 0.051] | 20/169 | 0.118 [0.078, 0.176] |
| combined | z=3, δ=15 ms, p=0.1 | 0.032 | 0.082 | 20/428 | 0.047 [0.031, 0.071] | 21/169 | 0.124 [0.083, 0.183] |

Full per-group breakdown (held-out, each adversarial family, each stress regime): `artifacts/sprint4_2_3/detector_comparison.json`.

**Held-out scenarios only** (165 series, 32 pos / 133 neg; small n — read as indicative):

| Detector | FP | FN |
|---|---|---|
| existing_stage4_rule | 0 | 4 |
| ebd_r1 | 4 | 3 |
| absolute_threshold | 0 | 6 |
| relative_increase | 0 | 18 |
| robust_z | 5 | 1 |
| persistence_z | 1 | 3 |
| combined | 5 | 1 |

### 3.4 Interpretation

1. **No detector dominates.** Persistence (`persistence_z`, k = 2) has the lowest FNR at 3.0 % FPR — i.e. FN 22.5 % → 11.8 %, FP 0.9 % → 3.0 % versus the existing rule. The two FNR intervals overlap only barely ([16.8, 29.4] vs [7.8, 17.6]) and the FPR rises 3×; this is a trade-off, **not a free improvement**.
2. **Relative-% is the worst detector** here (FNR 37 %); absolute-only is weaker than the existing rule on FNR.
3. **Robust-z/combined** reduce FNR to 12 % but raise FPR to 5–8 % and fail specifically on spontaneous-mode-switch and null-noise series (see per-group counts).
4. **Positives are dominated by the stress generator (105 of 169).** That generator was written for this sprint around the checkout failure mode (bimodal/block-constant baselines, large shifts). Part of the FNR gap is therefore a property of *my* regime design, not of independent data. On the clean pre-existing synthetic datasets the detectors are nearly indistinguishable (held-out table above).
5. **Checkoutservice (saved live data), after thresholds were frozen:**

| Detector | active window flagged | post-recovery flagged |
|---|---|---|
| existing_stage4_rule | no | no |
| persistence_z | no | no |
| robust_z / absolute / relative / combined | **yes** | **yes** |

   The ~241–246 ms level is also present in the pre-baseline (first 3 samples) and in the post-recovery window, where no intervention was active. Detectors that "fix" checkout therefore flag **the same level in the post window**. The saved data cannot show that checkout's rise was caused by the cart delay, so this is not evidence of a missed detection; it is evidence that the baseline for checkout was contaminated and bimodal. The same detectors also flag `adservice`, which the existing rule does not.
6. `ebd_r1` (two-sided) flags `shippingservice` (a metric-artifact *decrease* 4.1–4.5 → 2.0 ms) and `adservice` as diverged in both active and post windows. Directional semantics matter for latency.

### 3.5 Decision

* **Production rule unchanged** (existing directional Stage 4 rule; EBD R1 default unchanged).
* The detectors module is a **comparison harness**; no threshold was moved on the basis of the single checkout result or the held-out set.
* If a future sprint adopts persistence, `persistence_z(k=2)` has the best measured FNR/FPR trade-off on this protocol, but that needs data that is not generated by the same authors' stress regime.

---

## 4. EBD validation

All in `tests/unit/test_sprint423_ebd_attribution.py` (35 tests).

| Requirement | Result |
|---|---|
| Earliest vs largest | Earlier small divergence (amp 35) ranks above later huge one (amp 500). **Pass** |
| Multiple affected services / different onsets | Chain A(20) → B(40) → C(60) ordered A, B, C; B and C NONE (R2). **Pass** |
| Same-window tie | Both CANDIDATE: ancestor by the primary rule and leaf by the deliberate P1-11 R3-leaf rule. **Documented tie**, timing alone cannot separate them. |
| High-variance service | A noisy service whose "shift" is 1σ is not flagged. **Pass** |
| Missing telemetry | A missing service is not fabricated; default strict gap handling delays `t*` (D7); opt-in `max_gap_windows` recovers true onset; an *observed* non-exceeding window always breaks a run. **Pass / limitation** |
| Downstream propagation | Larger downstream symptoms never outrank the earlier upstream cause; late upstream with early downstream fails R2 (D1). **Pass after fix** |
| Positive vs negative deviations | Default bidirectional (historical); `direction` = `increase`/`decrease` verified. **Pass** |
| Abstention | Single-window spike → `[]`; zero baseline std → no R1. **Pass** |

---

## 5. Attribution validation

### 5.1 FCI/PAG and root-cause scoring (inspected)

* `fci_runner` wraps causal-learn FCI (Fisher-z); `PAGEdge.confidence` is a fixed 0.5 placeholder and **carries no information**. Nothing downstream should interpret it as a probability.
* `_pag_to_digraph` treats `o->` as `→` and `o-o` as bidirectional reachability, `BIDIRECTED` as no edge. This is *semi-directed reachability*; after D2 every result now records whether its R3 path is `DIRECTED` or `SEMI_DIRECTED` and adds a warning in the latter case.
* `identify_query` defaults to "no confounding" when no bidirected edge touches the source, so identifiability is optimistic by construction.
* The held-out harness assigns confidence 0.95/0.80 by tier — a **label, not a calibrated probability**.

### 5.2 Requirements

| Requirement | Result |
|---|---|
| Downstream symptoms not auto-root | Leaf/mid symptoms are NONE once an earlier ancestor exists. **Pass** |
| Semi-directed ≠ ancestry | Labelled `SEMI_DIRECTED` with warning; later endpoint fails R2. **Pass after fix** |
| Intervention vs observational | New `evidence_type` field; DEFINITIVE requires valid CID (grade, permutation, IQR threshold). **Pass after fix** |
| Confidence / abstention | e2e abstains on NOT_IDENTIFIABLE without R4 (D5). Confidence is still a categorical tier, not a calibrated probability. **Partial** |
| No label leakage | `compute_ebd` has no label arguments (tested); D6 fixed for learned variant; Stage 4 hard-coded attribution documented (C3). **Pass with caveats** |

### 5.3 Not addressed

C2 (R4 key mismatch in e2e) and the placeholder PAG edge confidence.

---

## 6. 50 ms injected vs ~230 ms observed

Source: `scripts/sprint423_stage4_gap_analysis.py` → `artifacts/sprint4_2_3/stage4_50_vs_230_analysis.json` (saved data only).

Established:

1. **Update granularity.** Every Prometheus series is piecewise-constant in plateaus of 3–6 samples (median 6 = 60 s) at a 10 s query step. Effective independent observations are roughly 3 (pre), 2 (active), 4 (post) per service, so the Z-scores in the Stage 4 table overstate the evidence. A 60 s flush interval is consistent with this but was not verified on the stack.
2. **cartservice values are bucket-interpolated p99s.** Active values 227.5 and 244.8 ms lie inside the (100, 250] ms bucket; the specific number reflects bucket mass and linear interpolation, not a measured latency. Mean latency was not recorded.
3. **A single 50 ms egress delay would not by itself explain p99 > 100 ms** for a service whose baseline p99 is 5–8 ms. Two hops (~100 ms) reach the bucket edge but do not explain 227–245 ms. The "compounded delay" hypothesis is *consistent* but **insufficient on its own**.
4. **Measurement definition** (from query/config, not traces): the regex `span_name=~"(?i).*cartservice.*"` has no `span_kind` filter, and `sum by (le)` mixes callers' client spans with cartservice server spans across operations. The `u32 match ip protocol 6` filter delays *all* TCP egress (replies, Redis requests, telemetry export). The `[2m]` rate window and the 110 s analysis window extend well past the 30 s intervention.
5. **checkoutservice:** the 241–246 ms level appears pre-intervention and post-recovery (§3.4).

Not available: traces, per-hop spans, Redis span boundaries, retry counts, queue depths, per-request latency.

**Conclusion:** the gap is **not resolvable from saved data**. Compounded delay, queueing/retries, mixed client/server span aggregation, all-TCP egress shaping and histogram interpolation are all unexcluded contributors; no single mechanism is claimed.

---

## 7. Files

**Modified**

* `src/rift/ebd/ebd.py` — removed R2 override (D1); `causal_path_kind` / `evidence_type` fields and semi-directed warning (D2); `_cid_supports_r4` (D3); run-scoped anomaly score + `direction` / `max_gap_windows` options (D4, D7); rewrote `_check_r1` (defaults reproduce prior behaviour).
* `src/rift/pipeline/e2e_runner.py` — abstain on NOT_IDENTIFIABLE without R4; extra fields in EBD stage output (D5).
* `scripts/run_reproducible_evaluation.py` — `select_outcome_node`, no ground-truth read in the learned variant (D6).
* `docs/SPRINT_WORK_LEDGER.md` — one row added.

(`ebd.py`, `e2e_runner.py` and `fci_runner.py` also contain uncommitted edits from earlier sprints; only the changes listed above are Sprint 4.2.3.)

**Created**

* `src/rift/statistics/divergence_detectors.py`
* `scripts/sprint423_detector_comparison.py`, `scripts/sprint423_stage4_gap_analysis.py`
* `tests/unit/test_sprint423_ebd_attribution.py` (35), `tests/unit/test_sprint423_detectors.py` (10)
* `artifacts/sprint4_2_3/{thresholds_frozen.json, thresholds_frozen.sha256, detector_comparison.json, stage4_50_vs_230_analysis.json}`
* this report

**Not modified:** `src/rift/intervention/**`, `src/rift/safety/**`, `scripts/stage4_intervention_*.py`, `artifacts/stage4_intervention_results.json`, all `datasets/`, historical reports.

---

## 8. Remaining limitations

1. Stage 4 is a single trial with ~2–4 effectively independent blocks per phase; no inferential claim is supported.
2. All detector results are on synthetic data; 105 of 169 final positives come from a generator written in this sprint. The existing-dataset generators emit clean step changes, so they cannot discriminate between detectors.
3. Held-out has only 15 scenarios (12 confounded); series within a scenario are correlated, so the Wilson intervals are optimistic.
4. `datasets/rift_faults/manifest.json` says 69 scenarios / 36-18-15 but `development.json` holds 50; not edited.
5. `verify_heldout_sealed.py` still fails on a pre-existing literal path in `run_reproducible_evaluation.py`; held-out artifacts were generated in an earlier sprint, so the held-out set is no longer pristine. This sprint evaluates it only through frozen thresholds.
6. R4 cannot be reached through the e2e CID key mapping (C2); `PAGEdge.confidence` is a placeholder; confidence tiers are not calibrated.
7. Family A (inverted onset) shows that EBD correctly follows "earliest" but can then name a downstream victim; this is a modelling limit, not a fix.
8. Historical held-out comparative JSON predates D1–D6 and was not regenerated.

---

## 9. Reproducibility

```bash
python3 -m pytest -q -p no:cacheprovider                         # 700 passed
python3 -m pytest -q -p no:cacheprovider tests/unit/test_sprint423_*.py   # 45 passed
python3 scripts/sprint423_detector_comparison.py select          # dev-only; writes frozen thresholds + sha256
python3 scripts/sprint423_detector_comparison.py final           # evaluates held-out once, refuses if hash changed
python3 scripts/sprint423_stage4_gap_analysis.py                 # saved-data §6 analysis
python3 scripts/verify_heldout_sealed.py                         # 3/4 pass (pre-existing literal, see §3.2)
```

Environment: Python 3.9.6, numpy, pandas, scipy, networkx, causal-learn, pytest. Seeds: stress series use `90000 + seed`; adversarial cohort seeds are those stored in the dataset.
