# Sprint 4.5.1 — Internal Scientific Review of the Sprint 4.5.0 Preregistration

> **This is an INTERNAL adversarial review performed by an AI agent.** It is not external independent validation, not peer review, and it does not satisfy decision **D7** (a named independent human reviewer of the generator and analysis script). No document in this repository claims otherwise.

Source: `artifacts/sprint4_5_1/review/adversarial_review.md` (234 lines, evidence scripts and JSON beside it, seeds 4510–4513). The reviewer was read-only with respect to existing files, did not touch any held-out file, and did not run V3, V2 or RIFT on any data (only the cheap B0-EARLIEST baseline on dev/val, and `compute_cid` on synthetic arrays). All empirical numbers are dev/val (N = 252) and therefore non-confirmatory.

## 1. Verdict of the review

The preregistration must not be described as "fully approved" and, in the form reviewed, should not have been recorded. H1 is testable and the power arithmetic was re-derived correctly, but H1 is expected to fail, so the study is mostly a pre-registered confirmation of a known negative unless the changes below are adopted.

## 2. Findings and how each was resolved

| # | priority | finding | resolution in Sprint 4.5.1 | status |
|---|---|---|---|---|
| 1 | P0 | Dataset-geometry gates are unattainable. Union-find groups collapse to about 9–11 (max size 384–512); the design space has only 2,354 distinct topology hashes; T5 non-isomorphism fails for the original S07 and S13. | Cluster unit changed to a generator-assigned group = template (256 groups, 16 per structure, 5–9 scenarios, max 9). Acceptance rules R-CAP1, R-OWN, R-NOVEL, R-DUP, template_full, cell_full simulated four times (accepted 1999/1999/2000/2000 within a 10,000-candidate budget per structure). S07 and S13 renamed and redefined (`two_stage_hub`, `mutual_pair_merge`). Dataset Protocol §2, §3, §6. | resolved in design; generator not yet written or reviewed (X2, D7) |
| 2 | P0 | Freeze manifest omitted runtime-imported files; two were untracked; B0 baselines, LEGACY and ORACLE could not be produced from the committed tree. | 69-file extended manifest with roles; the two untracked files are tracked in this commit; original 51-file manifest and hash unchanged. | resolved (X10) |
| 3 | P1 | Estimand and DEFF mis-specified. Structure-level ICC 0.042 at m = 125 per structure gives DEFF ≈ 6.2 and power ≈ 0.46; the random-structures reading gives MDE ≈ 0.197 independent of N. | Researcher decision 1: the 16 structures are fixed strata; claim restricted to those 16 motifs; fixed-weight stratified estimator; three-level hierarchy; power recomputed by Monte-Carlo; no effective sample size claimed. | resolved by decision; residual limitation stated (R20) |
| 4 | P1 | No confirmatory runner; error→abstention was attributed to V3 but lives in `benchmark_v2._timed`; T8 too weak; node order leaks the root. | Runner `scripts/sprint450_run_confirm.py` preregistered and hashed at G2 with the `_timed` semantics (error ⇒ abstention, `error_flag`, n_do consumed charged, 60 s). T8 tests the method-facing signature and key set; id prefix `V3C-` carries no structure token; T10 node-order permutation test; the generator randomises node order. | resolved in design (D21); runner not written |
| 5 | P1 | Label function mirrors RIFT's own R1 (3σ, persist 2) and the CID power criterion; label SNR ≥ 4 vs method 3σ boundary; WEAK_SIGNAL gives −0.166 of V3's −0.338; with zero unsafe answers V3 would reach only +0.043 < δ. | Circularity added to L2; SNR [3, 5) band reported as a stratum (D20, default: report, do not exclude); zero-unsafe decomposition preregistered (SAP §8.6). Labels unchanged. | stated; D20 open |
| 6 | P1 | The drift-stratum contrast measures answer suppression, not robustness; the premise "17 pairs" was a pair count — at scenario level dev/val is already 52/252 = 20.6%. | Wording rule forbids inferring "robust" from scenario-level unsafe rates; pair-level false-confirmation endpoint (D22); target restated as ≥ 25% natural share (+4 pp); stratum power stated (0.37, MDE 0.17). | resolved in design; D22 open |
| 7 | P1 | SYMMETRIC quota 180 conflicts with S13+S14 needing 220+; "structures V3 was not tuned on" overstated (S10–S14 are variants). | Quota matrix rebuilt (S13/S14 = 90 each, sums to 2000; X11); novel-versus-variant table preregistered; "designed stress set" wording. | resolved; X11 open |
| 8 | P1 | CID "borderline ⇒ ineligible" rejects a correct size-0.05 estimator with probability 0.978; "same replicate data" false for E1, E2, E6; V0 target noisy; simulator has iid noise. | Exact-count rule k ≤ 138 of 2000 / k ≤ 557 of 10,000; E2 and E6 declared different designs; V0 uses a high-R E0 reference; simulator mismatch noted. | resolved; X12 open |
| 9 | P2 | POSITIVE-USEFUL uses a point estimate; `DEFINITIVE_ROOT` sits on CANDIDATE-grade CID; forking paths (3 attempts, D17, "first complete run", `drift_stat` ancestry, bootstrap rerun). | Wording clarified ("point estimate"); `DEFINITIVE_ROOT` rule; "safe" defined by the indicator; "complete run" defined; ancestry on the full true graph; D17 recommended for removal. | resolved in text |
| 10 | P2 | Reproducibility evidence is one macOS arm64 machine; CI uses Ubuntu, Python 3.11, `requirements.txt`; 663 vs 664 unexplained. | Stated as a limitation (L9, X4, X8); no cross-platform claim. | accepted limitation |

## 3. Review items that remain true after this sprint

* **No external reviewer exists** (D7, BLOCKER). The generator, runner and analysis script do not exist yet and cannot have been reviewed.
* **The protected full-tree run (D12, BLOCKER)** has not been done. 27 of 888 tests were deliberately not run.
* **Label circularity** is documented, not removed. Any conclusion is relative to the simulator's labelling.
* **16 fixed motifs and 16 families.** Crossed family dependence cannot be removed by increasing N. A template-level test that ignores a real family effect has size 0.05–0.20; the family-block rule has power 0.30–0.59 under such an effect.
* **H1 is a known negative at the preregistered exchange rates.** The most likely outcome is NEGATIVE-WORSE.
* The reviewer could not verify whether node insertion order changes V2/V3 outputs; the lead's separate check found frozen V3 order-invariant on dev/val (0/252 changed), V2 untested.

## 4. Limits of this review

It shares the blind spots of the authoring team's tooling, saw only dev/val, and was not a substitute for a human review. The preregistration is **not** approved by it.
