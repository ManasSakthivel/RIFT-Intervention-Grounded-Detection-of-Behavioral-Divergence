# Stage 4 Attribution Analysis — Predictions Separated from Ground Truth (Sprint 4.2.4)

**Status:** supersedes the *attribution* statements of `docs/SPRINT4_2_1_STAGE4_INTERVENTION_EXECUTION_REPORT.md` (§1 item 5, §5, §7 gate 5). That report is a historical record and is left unchanged. Its network-intervention, rollback and coexistence findings are not affected by this document.

**Scope.** Offline re-analysis of the saved telemetry in `artifacts/stage4_intervention_results.json` (SHA-256 `e4cf1391c83bcb33070e8bc4ae3f8b792df2e0d1970df14524fc6c8d5d1dcffe`, verified unchanged before and after). No live experiment was run.

---

## 1. What was wrong with the historical attribution

`scripts/stage4_intervention_analysis.py` assigned `attributed = "cartservice"`, `ground_truth = "cartservice"` and `attribution_accuracy_top1 = 1.0` as literals. The reported "100 % Top-1 attribution" was therefore not an output of EBD or any other inference. The telemetry-derived parts of that report (Z-scores, shifts, rollback evidence) are unaffected.

## 2. Method

| Step | Component | Inputs it may read |
|---|---|---|
| Evidence adapter | `src/rift/pipeline/stage4_attribution.py::build_evidence` | `pre_baseline`, `intervention`, `target_service` only |
| Interventional evidence | `build_cid_store` → real `compute_cid(X→Y)` for the applied intervention X over every other service Y (baseline = Y's pre phase, post = Y's active phase) | adapter output |
| Learned graph | `run_fci` (α = 0.05, seed 42) on the pre + active data, no oracle fallback | adapter output |
| EBD | `compute_ebd` (θ_detect 3.0, persistence 2 windows, Δt 10 s, `direction="both"`, CID store supplied) | adapter output |
| Identifiability | `identify_query(cartservice → latest-diverging other service)`, plus all other diverging services as diagnostics | PAG |
| Evaluation | `evaluate_prediction(prediction, ground_truth_root)` | an already-built prediction and a label |

Labels in the saved record (`ground_truth`, `attributed_root_cause`, `attribution_accuracy_top1`, `verdict`, `summary_table`) are never read by the adapter or by inference. A test replaces the record with an object that raises on access to those keys.

The `post_recovery` phase is not used for inference.

## 3. Result (predictions)

Produced by `python3 scripts/sprint424_stage4_offline_attribution.py` → `artifacts/sprint4_2_4/stage4_attribution_result.json`.

| Field | Value |
|---|---|
| `predicted_root` | **none** |
| `abstained` | **true** — `NOT_IDENTIFIABLE` |
| `confidence` | 0.0 |
| `ebd_candidate` | `cartservice` (earliest divergence; tied at the first active window with `frontend`, `shippingservice`, `adservice`) |
| `diverging_services` (R1) | `cartservice`, `frontend`, `shippingservice`, `adservice` |
| `causal_path_kind` | `SEMI_DIRECTED` |
| `evidence_type` | `OBSERVATIONAL` |
| `cid_grade` | `INSUFFICIENT` (n_baseline = 15, n_post = 12; the hard floor is 20 per side) |
| `detection_timestamp` | 1793642335.0 (first active-phase sample) |
| `prediction_timestamp` | 1793642445.0 (last active-phase sample) |

## 4. Result (evaluation against the injected label, computed after inference)

| Field | Value |
|---|---|
| `ground_truth_root` | `cartservice` (the service the experimenter injected) |
| outcome | **ABSTAINED** — neither correct nor incorrect |
| `ebd_candidate` equals ground truth | yes |
| `top1_correct` | `null` (no prediction was made) |
| `coverage` | 0.0 |
| trials | 1 |

The historical "1/1 = 100 %" is replaced by: *EBD ranked the injected service as its earliest candidate (tied with three others in the first window); the full pipeline abstained; no top-1 accuracy is defined for a single abstained trial.*

## 5. Why the pipeline abstains

1. **No R4 / interventional support is possible from this data.** CID needs ≥ 20 samples on each side; Stage 4 has 15 baseline and 12 active samples per service. Every CID result is `INSUFFICIENT`, so R4 cannot pass and the evidence is observational, not interventional.
2. **The learned PAG is weak.** The series are plateau-constant (about 60 s blocks), so there are only about two independent blocks in the active phase and 27 usable rows for 10 variables. FCI returns 12 edges, mostly undirected, with `cartservice ↔ emailservice` and `emailservice ↔ shippingservice` bidirected. A bidirected edge adjacent to the candidate and no oriented path to the outcome make the identifiability check return `NOT_IDENTIFIABLE`.
3. This abstention is the pipeline's rule applied to weak structure evidence. It is **not** evidence that cartservice is not the cause, and it is not evidence of a confounder on `emailservice`. The `cartservice ↔ emailservice` edge may be a small-sample artefact of FCI, but that is an interpretation, not a tested result (see item 4: it disappears at some α).
4. **The abstention is fragile with respect to the FCI significance level.** A sensitivity probe over α (seed 42; run after the default α = 0.05 had been fixed, and not used to choose it):

   | FCI α | Outcome | Learned-PAG bidirected edges | Identifiability of the query |
   |---|---|---|---|
   | 0.01 | **predicts `cartservice`** (CANDIDATE, SEMI_DIRECTED, OBSERVATIONAL) | `email↔productcatalog`, `email↔shipping` | CONDITIONALLY_IDENTIFIABLE |
   | 0.02 – 0.07 (includes the default 0.05) | **abstains** (`NOT_IDENTIFIABLE`) | `cart↔email`, `email↔shipping` | NOT_IDENTIFIABLE |
   | 0.10 | **predicts `cartservice`** (CANDIDATE, SEMI_DIRECTED, OBSERVATIONAL) | `currency↔payment`, `currency↔productcatalog` | CONDITIONALLY_IDENTIFIABLE |
   | 0.20 | **predicts `cartservice`** (CANDIDATE, DIRECTED, OBSERVATIONAL) | six bidirected edges | REQUIRES_INTERVENTION |

   `cartservice` is the EBD candidate in every setting. Whether the pipeline *commits* to it depends on which spurious bidirected edges the weakly powered FCI run happens to produce. In no setting is the evidence interventional (CID is `INSUFFICIENT` throughout), and no setting yields DEFINITIVE. Reporting a "predicted cartservice" at a hand-picked α would be selecting the answer; the reported result is the pre-fixed default.

## 6. What can and cannot be claimed

Supported by the saved data:
- A 50 ms ± 5 ms netem delay on cartservice's egress was followed by a large rise in cartservice's p99 and in `frontend`'s p99 (single trial).
- The EBD detector flags cartservice at the first active window.
- The experiment's interventional design (known applied intervention) is intervention-consistent with cartservice being the origin of the divergence. This is true by construction of the experiment and is not a result of the algorithm.

Not supported:
- "100 % Top-1 attribution accuracy", or any accuracy estimate (n = 1, abstained).
- Any statement that the pipeline identified the root cause from data without being told the intervention target.
- DEFINITIVE / interventional attribution (CID evidence is insufficient).
- Causal ancestry (the path is semi-directed reachability).

## 7. Reproduction

```bash
python3 scripts/sprint424_stage4_offline_attribution.py
python3 -m pytest -q -p no:cacheprovider tests/unit/test_sprint424_stage4_attribution.py
shasum -a 256 artifacts/stage4_intervention_results.json    # e4cf1391...dcffe, unchanged
```
