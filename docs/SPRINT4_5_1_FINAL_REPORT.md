# Sprint 4.5.1 — Final Report: Finalisation and Verification of the Confirmatory Preregistration

Base commit `be5e0318fcd9cb17285ce6b8dff632cb68274b65` (branch `sprint-4.4.2-reproducibility-hardening`). Work branch `sprint-4.5.1-prereg-finalization`.
Commit SHA and push status: a commit cannot contain its own hash, so they are recorded in `git log -1 sprint-4.5.1-prereg-finalization` and in the closing message of the session that produced this report. **No SHA or push result is asserted inside this file.**

## 0. Status in one paragraph

The Sprint 4.5.0 preregistration is **corrected, internally consistent (machine-checked) and committed, but NOT fully approved.** Two BLOCKERs remain: **D7** (no named independent human reviewer; all review so far was internal, by AI agents) and **D12** (the owner-run protected full-tree test run was not done; 27 of 888 tests were deliberately not run and are not reported as passed). Decisions D1–D22 and A1–A9 and several X rows await the researcher. Nothing was implemented: no confirmatory data, no confirmatory runner, no generator, no confirmatory CID experiment, no confirmatory V3 run. Frozen V3 is unchanged. V3 is **expected to fail H1** (dev/val mean utility −0.338 at λ = 2, γ = 1), and the design reports that as a result.

## 1. Corrected estimand and group hierarchy (researcher decision 1)

* The 16 structures S01–S16 are **fixed experimental strata**. Conclusions are restricted to those 16 motifs as produced by the confirmatory generator, on the simulator. There is no generalisation to unseen structures or arbitrary production environments.
* Hierarchy: **structure** (16 fixed strata) → **scenario group** (generator-assigned, one group = one template; K = 256, 16 per structure, 5–9 scenarios, max 9; gate K ≥ 250) → **scenario** (the observation).
* Estimand θ = Σ_s W_s μ_s with preregistered quota weights; estimator: stratified ratio estimator; variance: stratified CR1; CI: stratified group bootstrap-t (seed 4505, B = 20,000); sensitivity: family-block bootstrap (seed 4506, D19). 256 groups are **not** claimed to be 256 independent structural clusters, and no effective sample size is claimed. A random-structures reading would have MDE ≈ 0.18–0.25 independent of N; it is not adopted.

## 2. Revised power analysis (all non-confirmatory; SAP §6)

* The closed-form normal approximation (N = 2000: 0.965 at DEFF 1.5, 0.90 at DEFF 2, 0.76 at DEFF 3; N = 800 at DEFF 2: 0.54, MDE80 0.135) is **optimistic** and is labelled so. N = 800 is insufficient.
* Bootstrap-t Monte-Carlo, pooled layout (250 groups, mean size 8): 0.917 / **0.831** / 0.653 / 0.367 at DEFF 1.5 / 2 / 3 / 6. The earlier DEFF-cap claim and the "90% at DEFF 2" claim are **retracted**.
* Adopted fixed-strata layout (16 × 16), μ = +0.10: 0.83–0.99 for template ICC ≤ 0.10 without a crossed family effect; 0.65–0.83 at ICC 0.2–0.3; **0.30–0.59 under the family-block rule if a real crossed family effect exists**; a template-level test that ignores a real family effect has size 0.05–0.20. SD ×1.25 stress: 0.943 / 0.878 / 0.763 / 0.608 at ICC 0 / 0.05 / 0.10 / 0.20. H4 at half effect: 0.23.
* **Power is inadequate at higher design effects.** The 16-structure/16-family limitation is a property of the design and cannot be repaired by raising N. Because the expected effect is negative, the likely outcome is a decisive negative result; the powers describe the unlikely positive case.

## 3. Utility specification

U_i = C_i − λ·S_i − γ·(n_do,i / 20); λ = 2.0, γ = 1.0 (≡ κ = 0.05 per do()), δ = 0.10; strict unsafe (`score_one`) primary, operational unsafe as sensitivity; U_AA ≡ 0. These are **researcher judgements, not empirical constants.** Per-scenario U ∈ [−3, 1]; the ceiling π = 0.40 bounds the *mean* only (E6). The six wording errors E1–E6 were corrected: precision needed for U = 0 / U = δ is ≈ 0.79 / ≈ 0.88 (V2: 0.72 / 0.80), not "≥ 2/3" (E1); CI above zero only for λ ≤ 0.61 at κ = 0 and λ ≤ 0.30 at κ = 0.025, and for no λ ≥ 0 at κ ≥ 0.05 (E2); 0.135 not 0.136 (E3); the break-even ordering holds at κ = 0 only (E4); at κ = 0.10 the V3 − V2 CI includes 0 for 0.5 ≤ λ ≤ 1.5 (E5). Sensitivity analyses are kept separate from the primary rule. Dev/val: V3 −0.338 [−0.465, −0.219], V3 − V2 +0.224, break-even λ 0.938 at κ = 0. Zero-unsafe V3 would reach only +0.043 < δ.

## 4. CID reconciliation (researcher item I)

218 design cells = 214 factorial + 4 mixture; 8 are degenerate (6 in B1 with d = 0 and delay > 0, 2 in B6 with ω = 0 at τ = 30), giving **210 distinct DGPs**; 468,000 replicates = 214 × 2000 + 4 × 10,000. Cells, estimators (seven core, E0–E6), replicates, scenarios and DGPs are distinguished in the CID design. An internal agent's "18 duplicates" came from a broader canonicalisation (it also collapsed B4 ρ = 0, B5 v = 1 and B7 into B1's null); the official count stays 8 and 210. Eligibility: k ≤ 138 of 2000 per null cell, k ≤ 557 of 10,000 per mixture cell (P(ineligible) at true size 0.05 is 0.008 / 0.009); "same replicate data" removed for E1, E2, E6.

## 5. Dataset geometry (researcher items B, C, D)

Natural geometry (6000 candidates): union-find collapses to 7 groups (max 2,505) with 2,344 distinct topology hashes; hence group = template. Acceptance simulation: 256 templates, group size 5–9, unique-topology share 1.0, four attempts accepted 1999/1999/2000/2000; about 98 s per attempt. Quota matrix verified to sum to 2000 (ATTRIBUTE 800, WEAK_SIGNAL 360, ROOT_UNOBSERVED 240, SYMMETRIC 180, INSUFFICIENT_BASELINE 180, NO_DISCRIMINATING_EVIDENCE 140, NO_FAULT 100) with the S13/S14 exception (90 each). Drift: dev/val already 52/252 = 20.6%; a ≥ 25% natural share is +4 pp; a drift sub-quota is infeasible. Independence dry run: zero shared keys; max cross-set similarity 0.8997 (3 pairs ≥ 0.88; the 0.88 threshold is a proxy). T1 replication 90/90. No confirmatory data exist.

## 6. Node-order investigation (item G)

The root is first in 489/489 prototype scenarios and 99/99 dev+val attributable scenarios with an observed root. Frozen V3 is order-invariant on dev/val (0/252 changed); B0-EARLIEST changed in 35/252; V2 not tested. Classification: a generator-side leak. The new generator must randomise node order; test T10 (permutation invariance) is preregistered.

## 7. Expanded freeze manifest (researcher decision 2)

69 files = 51 original + 18 added, with roles (see the Reproducibility Report §2). Extended-manifest SHA-256 `0e3a9262f4619d33ba55c4f76cb17a36aec02b987aac4befa35f4464f6eb25ec`; original manifest `609bcb9d8a9786492f045e4fe13e10e1d17518f3111814a91e5ca73b6902aeb6` unchanged. Final check of the 51 original hashes against `artifacts/sprint4_5_1/baseline_freeze_manifest_before.json`: **0 mismatches.** The freeze was not expanded indiscriminately.

## 8. Error handling (item F)

The "errors map to abstention" behaviour belongs to `benchmark_v2._timed` (`METHOD_ERROR`, `TIMEOUT_S = 60`), not to V3 or `sprint440_run_v3.py`. A confirmatory runner `scripts/sprint450_run_confirm.py` must be written, tested on dev/val and hashed at G2; it records exception/timeout as abstention with `error_flag = 1` and charges the n_do consumed (D21). It does not exist yet.

## 9. Python outcome and protected-data deviation

`requires-python` is now `>=3.9` (committed; one platform; invalid build-backend and non-PEP 440 version unchanged; CI targets 3.11). One agent ran an unapproved `shasum -a 256` on `datasets/rift_v2/heldout_candidate.json`; the digest was neither displayed nor recorded and no content was read. Hashing is distinct from content inspection; this does not claim that nothing was done to the file. `verify_freeze()` hashing inside the registered protected test is the approved 4.4.2 procedure. Details: `docs/SPRINT4_5_1_REPRODUCIBILITY_REPORT.md`.

## 10. Exact test and check results

| check | result |
|---|---|
| doc-consistency checker | FAIL 0, WARN 0; 58 numerical claims recomputed, 0 failed |
| 218 cells / 210 DGPs / 468,000 replicates | verified by `sprint451_cid_cell_reconciliation.py` |
| V3 tests | 34 / 34 passed |
| safe harness subset | 803 passed (801 reproducible + 2 protected), 0 failures; + 48 + 10 = **861 of 888 executed and passed** |
| **27 tests NOT RUN** (held-out parse risk) | 15 manifest, 9 guard, 2 independence, 1 metrics-access; **not reported as passed** (D12) |
| 51 original frozen hashes vs baseline | 0 mismatches |
| `artifacts/sprint4_5_0/confirm/` | does not exist |
| held-out content | not accessed (one unapproved byte-level hash, disclosed) |

## 11. Remaining researcher decisions

* **BLOCKERs:** D7 (name an independent reviewer), D12 (owner-run protected full-tree run).
* **MUST FIX:** X2 (write, test on dev/val and hash the generator, runner and analysis script).
* **Approval:** D1–D6, D8–D11, D13 (ratify the committed `>=3.9`), D14–D16, D18, **D19** (cluster unit / family-block rule), **D20** (SNR [3, 5) band), **D21** (runner and error semantics), **D22** (pair-level robustness endpoint), A1–A9, X5, X6, X11 (S13/S14 quota exception), X12 (eligibility cut-offs). D17 is recommended for removal.

## 12. Methodological risks

Label circularity (the label mirrors RIFT's own 3σ/persist-2 rule and CID power criterion; WEAK_SIGNAL gives −0.166 of V3's −0.338); fixed-strata claim only (16 motifs × 16 families); crossed family dependence (size inflation or low power); designed stress set, with S10–S14 variants of dev/val motifs; the 0.88 similarity proxy; normative λ, γ, δ; H1 a known negative at λ = 2; single-platform evidence; 14 transitive pin differences; 663 vs 664 unexplained; internal review only.

## 13. Git

Staged by explicit path only. Not staged: the 11 pre-existing modified files and the roughly 166 other untracked historical files. Branch `sprint-4.5.1-prereg-finalization`; commit message `Sprint 4.5.1: finalize and verify confirmatory preregistration`; remote `origin` = `https://github.com/ManasSakthivel/RIFT-Intervention-Grounded-Detection-of-Behavioral-Divergence`; no force, not to main. The six unpushed 4.4.x commits remain in the branch ancestry (no history rewrite). The push result is reported in the session's closing message.
