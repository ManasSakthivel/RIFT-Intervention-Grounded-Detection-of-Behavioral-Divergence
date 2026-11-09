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

| Method | P1 (den. N_attr) | P1 Wilson95 | P2 (den. N) | P2 Wilson95 | P3 unsafe (den. N) | unsafe on ABSTAIN_REQUIRED (den. N_abs) | wrong root on ATTRIBUTE (den. N_attr) | coverage overall (den. N) | coverage on ATTRIBUTE | conditional acc. (den. answered ATTRIBUTE) | selective risk (den. answered) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B0-EARLIEST | 17/45 = 0.378 | [0.25, 0.52] | 18/108 = 0.167 | [0.11, 0.25] | 90/108 = 0.833 | 62/63 = 0.984 | 28/45 = 0.622 | 107/108 = 0.991 | 45/45 = 1.000 | 17/45 = 0.378 | 90/107 = 0.841 |
| B0-HIGHEST | 18/45 = 0.400 | [0.27, 0.55] | 18/108 = 0.167 | [0.11, 0.25] | 90/108 = 0.833 | 63/63 = 1.000 | 27/45 = 0.600 | 108/108 = 1.000 | 45/45 = 1.000 | 18/45 = 0.400 | 90/108 = 0.833 |
| B1-LATENCY-CORR | 17/45 = 0.378 | [0.25, 0.52] | 18/108 = 0.167 | [0.11, 0.25] | 90/108 = 0.833 | 62/63 = 0.984 | 28/45 = 0.622 | 107/108 = 0.991 | 45/45 = 1.000 | 17/45 = 0.378 | 90/107 = 0.841 |
| B3-SIEVE-LIKE | 18/45 = 0.400 | [0.27, 0.55] | 19/108 = 0.176 | [0.12, 0.26] | 89/108 = 0.824 | 62/63 = 0.984 | 27/45 = 0.600 | 107/108 = 0.991 | 45/45 = 1.000 | 18/45 = 0.400 | 89/107 = 0.832 |
| B5-RIFT-OBS | 17/45 = 0.378 | [0.25, 0.52] | 42/108 = 0.389 | [0.30, 0.48] | 53/108 = 0.491 | 38/63 = 0.603 | 15/45 = 0.333 | 70/108 = 0.648 | 32/45 = 0.711 | 17/32 = 0.531 | 53/70 = 0.757 |
| B6-RIFT-RANDOM | 27/45 = 0.600 | [0.45, 0.73] | 33/108 = 0.306 | [0.23, 0.40] | 75/108 = 0.694 | 57/63 = 0.905 | 18/45 = 0.400 | 102/108 = 0.944 | 45/45 = 1.000 | 27/45 = 0.600 | 75/102 = 0.735 |
| B7-RIFT-ONE-SHOT | 27/45 = 0.600 | [0.45, 0.73] | 33/108 = 0.306 | [0.23, 0.40] | 75/108 = 0.694 | 57/63 = 0.905 | 18/45 = 0.400 | 102/108 = 0.944 | 45/45 = 1.000 | 27/45 = 0.600 | 75/102 = 0.735 |
| RIFT-FULL-LEGACY | 21/45 = 0.467 | [0.33, 0.61] | 52/108 = 0.481 | [0.39, 0.57] | 49/108 = 0.454 | 32/63 = 0.508 | 17/45 = 0.378 | 70/108 = 0.648 | 38/45 = 0.844 | 21/38 = 0.553 | 49/70 = 0.700 |
| RIFT-FULL-V2 | 20/45 = 0.444 | [0.31, 0.59] | 60/108 = 0.556 | [0.46, 0.65] | 37/108 = 0.343 | 23/63 = 0.365 | 14/45 = 0.311 | 57/108 = 0.528 | 34/45 = 0.756 | 20/34 = 0.588 | 37/57 = 0.649 |
| ORACLE:RIFT-FULL-LEGACY-ORACLE-PAG | 35/45 = 0.778 | [0.64, 0.87] | 55/108 = 0.509 | [0.42, 0.60] | 53/108 = 0.491 | 43/63 = 0.683 | 10/45 = 0.222 | 88/108 = 0.815 | 45/45 = 1.000 | 35/45 = 0.778 | 53/88 = 0.602 |
| ORACLE:RIFT-FULL-V2-ORACLE-GRAPH | 32/45 = 0.711 | [0.57, 0.82] | 60/108 = 0.556 | [0.46, 0.65] | 41/108 = 0.380 | 35/63 = 0.556 | 6/45 = 0.133 | 73/108 = 0.676 | 38/45 = 0.844 | 32/38 = 0.842 | 41/73 = 0.562 |
| ORACLE:UPPER-BOUND | 45/45 = 1.000 | [0.92, 1.00] | 108/108 = 1.000 | [0.97, 1.00] | 0/108 = 0.000 | 0/63 = 0.000 | 0/45 = 0.000 | 45/108 = 0.417 | 45/45 = 1.000 | 45/45 = 1.000 | 0/45 = 0.000 |
| RIFT-FULL-V2G (EXPLORATORY, post-hoc) | 14/45 = 0.311 | [0.20, 0.46] | 63/108 = 0.583 | [0.49, 0.67] | 18/108 = 0.167 | 14/63 = 0.222 | 4/45 = 0.089 | 32/108 = 0.296 | 18/45 = 0.400 | 14/18 = 0.778 | 18/32 = 0.562 |

Reading notes: B0/B1/B3 never abstain (coverage ~ 100 %), so P2 is low by construction. The oracle rows are an upper-reference only.
V2G is exploratory. V2's coverage is 57/108 = 52.8 % and its conditional accuracy is 20/34; **coverage and conditional accuracy
must always be read together with P2**.

### 2.2 Held-out secondary metrics

| Method | top-3 on ATTRIBUTE (den. N_attr with >=3 candidates) | correct abstention (den. N_abs) | lost coverage on ATTRIBUTE (den. N_attr) | mean intervention s | mean #perturbations | mean runtime ms | interventional / answered | DIRECTED / SEMI_DIRECTED (answered) | method errors |
|---|---|---|---|---|---|---|---|---|---|
| B0-EARLIEST | 41/45 = 0.911 | 1/63 = 0.016 | 0/45 = 0.000 | 0.0 | 0.00 | 1.4 | 0/107 | 0/0 | 0 |
| B0-HIGHEST | 39/45 = 0.867 | 0/63 = 0.000 | 0/45 = 0.000 | 0.0 | 0.00 | 0.9 | 0/108 | 0/0 | 0 |
| B1-LATENCY-CORR | 37/45 = 0.822 | 1/63 = 0.016 | 0/45 = 0.000 | 0.0 | 0.00 | 1.6 | 0/107 | 0/0 | 0 |
| B3-SIEVE-LIKE | 34/45 = 0.756 | 1/63 = 0.016 | 0/45 = 0.000 | 0.0 | 0.00 | 1.3 | 0/107 | 0/0 | 0 |
| B5-RIFT-OBS | 31/45 = 0.689 | 25/63 = 0.397 | 13/45 = 0.289 | 0.0 | 0.00 | 10.6 | 0/70 | 0/0 | 0 |
| B6-RIFT-RANDOM | 38/45 = 0.844 | 6/63 = 0.095 | 0/45 = 0.000 | 47.8 | 1.59 | 12.1 | 0/102 | 0/0 | 0 |
| B7-RIFT-ONE-SHOT | 38/45 = 0.844 | 6/63 = 0.095 | 0/45 = 0.000 | 47.8 | 1.59 | 12.0 | 0/102 | 0/0 | 0 |
| RIFT-FULL-LEGACY | 27/45 = 0.600 | 31/63 = 0.492 | 7/45 = 0.156 | 19.4 | 0.65 | 12.1 | 0/70 | 0/0 | 0 |
| RIFT-FULL-V2 | 28/45 = 0.622 | 40/63 = 0.635 | 11/45 = 0.244 | 56.4 | 1.88 | 41.0 | 57/57 | 1/56 | 0 |
| ORACLE:RIFT-FULL-LEGACY-ORACLE-PAG | 43/45 = 0.956 | 20/63 = 0.317 | 0/45 = 0.000 | 24.4 | 0.81 | 7.8 | 0/88 | 0/0 | 0 |
| ORACLE:RIFT-FULL-V2-ORACLE-GRAPH | 36/45 = 0.800 | 28/63 = 0.444 | 7/45 = 0.156 | 56.7 | 1.89 | 40.9 | 73/73 | 73/0 | 0 |
| ORACLE:UPPER-BOUND | 45/45 = 1.000 | 63/63 = 1.000 | 0/45 = 0.000 | 0.0 | 0.00 | 0.0 | 0/45 | 0/0 | 0 |
| RIFT-FULL-V2G | 16/45 = 0.356 | 49/63 = 0.778 | 27/45 = 0.600 | 56.4 | 1.88 | 6.7 | 32/32 | 1/31 | 0 |

### 2.3 Development split (n = 180; used for implementation / defect finding; **not** confirmatory)

| Method | P1 (den. N_attr) | P1 Wilson95 | P2 (den. N) | P2 Wilson95 | P3 unsafe (den. N) | unsafe on ABSTAIN_REQUIRED (den. N_abs) | wrong root on ATTRIBUTE (den. N_attr) | coverage overall (den. N) | coverage on ATTRIBUTE | conditional acc. (den. answered ATTRIBUTE) | selective risk (den. answered) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B0-EARLIEST | 38/68 = 0.559 | [0.44, 0.67] | 50/180 = 0.278 | [0.22, 0.35] | 130/180 = 0.722 | 100/112 = 0.893 | 30/68 = 0.441 | 168/180 = 0.933 | 68/68 = 1.000 | 38/68 = 0.559 | 130/168 = 0.774 |
| B0-HIGHEST | 27/68 = 0.397 | [0.29, 0.52] | 27/180 = 0.150 | [0.11, 0.21] | 153/180 = 0.850 | 112/112 = 1.000 | 41/68 = 0.603 | 180/180 = 1.000 | 68/68 = 1.000 | 27/68 = 0.397 | 153/180 = 0.850 |
| B1-LATENCY-CORR | 29/68 = 0.426 | [0.32, 0.54] | 42/180 = 0.233 | [0.18, 0.30] | 138/180 = 0.767 | 99/112 = 0.884 | 39/68 = 0.574 | 167/180 = 0.928 | 68/68 = 1.000 | 29/68 = 0.426 | 138/167 = 0.826 |
| B3-SIEVE-LIKE | 35/68 = 0.515 | [0.40, 0.63] | 48/180 = 0.267 | [0.21, 0.34] | 132/180 = 0.733 | 99/112 = 0.884 | 33/68 = 0.485 | 167/180 = 0.928 | 68/68 = 1.000 | 35/68 = 0.515 | 132/167 = 0.790 |
| B5-RIFT-OBS | 24/68 = 0.353 | [0.25, 0.47] | 70/180 = 0.389 | [0.32, 0.46] | 97/180 = 0.539 | 66/112 = 0.589 | 31/68 = 0.456 | 121/180 = 0.672 | 55/68 = 0.809 | 24/55 = 0.436 | 97/121 = 0.802 |
| B6-RIFT-RANDOM | 35/68 = 0.515 | [0.40, 0.63] | 58/180 = 0.322 | [0.26, 0.39] | 122/180 = 0.678 | 89/112 = 0.795 | 33/68 = 0.485 | 157/180 = 0.872 | 68/68 = 1.000 | 35/68 = 0.515 | 122/157 = 0.777 |
| B7-RIFT-ONE-SHOT | 35/68 = 0.515 | [0.40, 0.63] | 58/180 = 0.322 | [0.26, 0.39] | 122/180 = 0.678 | 89/112 = 0.795 | 33/68 = 0.485 | 157/180 = 0.872 | 68/68 = 1.000 | 35/68 = 0.515 | 122/157 = 0.777 |
| RIFT-FULL-LEGACY | 25/68 = 0.368 | [0.26, 0.49] | 81/180 = 0.450 | [0.38, 0.52] | 86/180 = 0.478 | 56/112 = 0.500 | 30/68 = 0.441 | 111/180 = 0.617 | 55/68 = 0.809 | 25/55 = 0.455 | 86/111 = 0.775 |
| RIFT-FULL-V2 | 28/68 = 0.412 | [0.30, 0.53] | 102/180 = 0.567 | [0.49, 0.64] | 52/180 = 0.289 | 38/112 = 0.339 | 14/68 = 0.206 | 80/180 = 0.444 | 42/68 = 0.618 | 28/42 = 0.667 | 52/80 = 0.650 |
| ORACLE:RIFT-FULL-LEGACY-ORACLE-PAG | 40/68 = 0.588 | [0.47, 0.70] | 99/180 = 0.550 | [0.48, 0.62] | 73/180 = 0.406 | 53/112 = 0.473 | 20/68 = 0.294 | 113/180 = 0.628 | 60/68 = 0.882 | 40/60 = 0.667 | 73/113 = 0.646 |
| ORACLE:RIFT-FULL-V2-ORACLE-GRAPH | 39/68 = 0.574 | [0.46, 0.68] | 104/180 = 0.578 | [0.50, 0.65] | 51/180 = 0.283 | 47/112 = 0.420 | 4/68 = 0.059 | 90/180 = 0.500 | 43/68 = 0.632 | 39/43 = 0.907 | 51/90 = 0.567 |
| ORACLE:UPPER-BOUND | 68/68 = 1.000 | [0.95, 1.00] | 180/180 = 1.000 | [0.98, 1.00] | 0/180 = 0.000 | 0/112 = 0.000 | 0/68 = 0.000 | 68/180 = 0.378 | 68/68 = 1.000 | 68/68 = 1.000 | 0/68 = 0.000 |
| RIFT-FULL-V2G (EXPLORATORY, post-hoc) | 24/68 = 0.353 | [0.25, 0.47] | 117/180 = 0.650 | [0.58, 0.72] | 26/180 = 0.144 | 19/112 = 0.170 | 7/68 = 0.103 | 50/180 = 0.278 | 31/68 = 0.456 | 24/31 = 0.774 | 26/50 = 0.520 |

### 2.4 Validation split (n = 72; used for protocol refinement; **not** confirmatory)

| Method | P1 (den. N_attr) | P1 Wilson95 | P2 (den. N) | P2 Wilson95 | P3 unsafe (den. N) | unsafe on ABSTAIN_REQUIRED (den. N_abs) | wrong root on ATTRIBUTE (den. N_attr) | coverage overall (den. N) | coverage on ATTRIBUTE | conditional acc. (den. answered ATTRIBUTE) | selective risk (den. answered) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B0-EARLIEST | 11/31 = 0.355 | [0.21, 0.53] | 14/72 = 0.194 | [0.12, 0.30] | 58/72 = 0.806 | 38/41 = 0.927 | 20/31 = 0.645 | 69/72 = 0.958 | 31/31 = 1.000 | 11/31 = 0.355 | 58/69 = 0.841 |
| B0-HIGHEST | 5/31 = 0.161 | [0.07, 0.33] | 5/72 = 0.069 | [0.03, 0.15] | 67/72 = 0.931 | 41/41 = 1.000 | 26/31 = 0.839 | 72/72 = 1.000 | 31/31 = 1.000 | 5/31 = 0.161 | 67/72 = 0.931 |
| B1-LATENCY-CORR | 8/31 = 0.258 | [0.14, 0.43] | 11/72 = 0.153 | [0.09, 0.25] | 61/72 = 0.847 | 38/41 = 0.927 | 23/31 = 0.742 | 69/72 = 0.958 | 31/31 = 1.000 | 8/31 = 0.258 | 61/69 = 0.884 |
| B3-SIEVE-LIKE | 11/31 = 0.355 | [0.21, 0.53] | 14/72 = 0.194 | [0.12, 0.30] | 58/72 = 0.806 | 38/41 = 0.927 | 20/31 = 0.645 | 69/72 = 0.958 | 31/31 = 1.000 | 11/31 = 0.355 | 58/69 = 0.841 |
| B5-RIFT-OBS | 6/31 = 0.194 | [0.09, 0.36] | 21/72 = 0.292 | [0.20, 0.41] | 44/72 = 0.611 | 26/41 = 0.634 | 18/31 = 0.581 | 50/72 = 0.694 | 24/31 = 0.774 | 6/24 = 0.250 | 44/50 = 0.880 |
| B6-RIFT-RANDOM | 16/31 = 0.516 | [0.35, 0.68] | 24/72 = 0.333 | [0.24, 0.45] | 48/72 = 0.667 | 33/41 = 0.805 | 15/31 = 0.484 | 64/72 = 0.889 | 31/31 = 1.000 | 16/31 = 0.516 | 48/64 = 0.750 |
| B7-RIFT-ONE-SHOT | 16/31 = 0.516 | [0.35, 0.68] | 24/72 = 0.333 | [0.24, 0.45] | 48/72 = 0.667 | 33/41 = 0.805 | 15/31 = 0.484 | 64/72 = 0.889 | 31/31 = 1.000 | 16/31 = 0.516 | 48/64 = 0.750 |
| RIFT-FULL-LEGACY | 15/31 = 0.484 | [0.32, 0.65] | 36/72 = 0.500 | [0.39, 0.61] | 28/72 = 0.389 | 20/41 = 0.488 | 8/31 = 0.258 | 43/72 = 0.597 | 23/31 = 0.742 | 15/23 = 0.652 | 28/43 = 0.651 |
| RIFT-FULL-V2 | 8/31 = 0.258 | [0.14, 0.43] | 35/72 = 0.486 | [0.37, 0.60] | 27/72 = 0.375 | 14/41 = 0.341 | 13/31 = 0.419 | 35/72 = 0.486 | 21/31 = 0.677 | 8/21 = 0.381 | 27/35 = 0.771 |
| ORACLE:RIFT-FULL-LEGACY-ORACLE-PAG | 23/31 = 0.742 | [0.57, 0.86] | 37/72 = 0.514 | [0.40, 0.63] | 34/72 = 0.472 | 27/41 = 0.659 | 7/31 = 0.226 | 57/72 = 0.792 | 30/31 = 0.968 | 23/30 = 0.767 | 34/57 = 0.596 |
| ORACLE:RIFT-FULL-V2-ORACLE-GRAPH | 19/31 = 0.613 | [0.44, 0.76] | 41/72 = 0.569 | [0.45, 0.68] | 22/72 = 0.306 | 19/41 = 0.463 | 3/31 = 0.097 | 41/72 = 0.569 | 22/31 = 0.710 | 19/22 = 0.864 | 22/41 = 0.537 |
| ORACLE:UPPER-BOUND | 31/31 = 1.000 | [0.89, 1.00] | 72/72 = 1.000 | [0.95, 1.00] | 0/72 = 0.000 | 0/41 = 0.000 | 0/31 = 0.000 | 31/72 = 0.431 | 31/31 = 1.000 | 31/31 = 1.000 | 0/31 = 0.000 |
| RIFT-FULL-V2G (EXPLORATORY, post-hoc) | 5/31 = 0.161 | [0.07, 0.33] | 41/72 = 0.569 | [0.45, 0.68] | 12/72 = 0.167 | 5/41 = 0.122 | 7/31 = 0.226 | 17/72 = 0.236 | 12/31 = 0.387 | 5/12 = 0.417 | 12/17 = 0.706 |

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

12 of 24 confirmatory tests are significant after Holm correction (family = 8 non-oracle comparators x 3 metrics = 24 tests).

| Comparator (vs RIFT-FULL-V2) | Metric | n | p(V2) | p(comp.) | diff (V2 - comp.) | scenario-boot 95% CI | template-boot 95% CI | Cohen h | V2-only / comp.-only correct | McNemar exact p | permutation p | Holm-adj. p (McNemar) | significant (Holm<0.05 & CI excl. 0) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0-EARLIEST | P1 | 45 | 0.444 | 0.378 | +0.067 | [-0.133, +0.267] | [-0.143, +0.267] | +0.14 | 12/9 | 0.6636 | 0.6620 | 1.0000 | no |
| B0-EARLIEST | P2 | 108 | 0.556 | 0.167 | +0.389 | [+0.269, +0.500] | [+0.269, +0.500] | +0.84 | 51/9 | 0.0000 | 0.0001 | 0.0000 | YES |
| B0-EARLIEST | P3_safe | 108 | 0.657 | 0.167 | +0.491 | [+0.370, +0.602] | [+0.376, +0.595] | +1.05 | 59/6 | 0.0000 | 0.0001 | 0.0000 | YES |
| B0-HIGHEST | P1 | 45 | 0.444 | 0.400 | +0.044 | [-0.178, +0.267] | [-0.149, +0.245] | +0.09 | 13/11 | 0.8388 | 0.8435 | 1.0000 | no |
| B0-HIGHEST | P2 | 108 | 0.556 | 0.167 | +0.389 | [+0.269, +0.509] | [+0.270, +0.505] | +0.84 | 53/11 | 0.0000 | 0.0001 | 0.0000 | YES |
| B0-HIGHEST | P3_safe | 108 | 0.657 | 0.167 | +0.491 | [+0.380, +0.602] | [+0.381, +0.593] | +1.05 | 59/6 | 0.0000 | 0.0001 | 0.0000 | YES |
| B1-LATENCY-CORR | P1 | 45 | 0.444 | 0.378 | +0.067 | [-0.133, +0.289] | [-0.130, +0.261] | +0.14 | 13/10 | 0.6776 | 0.6754 | 1.0000 | no |
| B1-LATENCY-CORR | P2 | 108 | 0.556 | 0.167 | +0.389 | [+0.269, +0.509] | [+0.274, +0.505] | +0.84 | 52/10 | 0.0000 | 0.0001 | 0.0000 | YES |
| B1-LATENCY-CORR | P3_safe | 108 | 0.657 | 0.167 | +0.491 | [+0.380, +0.602] | [+0.385, +0.595] | +1.05 | 59/6 | 0.0000 | 0.0001 | 0.0000 | YES |
| B3-SIEVE-LIKE | P1 | 45 | 0.444 | 0.400 | +0.044 | [-0.133, +0.244] | [-0.156, +0.229] | +0.09 | 11/9 | 0.8238 | 0.8205 | 1.0000 | no |
| B3-SIEVE-LIKE | P2 | 108 | 0.556 | 0.176 | +0.380 | [+0.269, +0.491] | [+0.264, +0.491] | +0.82 | 50/9 | 0.0000 | 0.0001 | 0.0000 | YES |
| B3-SIEVE-LIKE | P3_safe | 108 | 0.657 | 0.176 | +0.481 | [+0.370, +0.593] | [+0.370, +0.588] | +1.03 | 58/6 | 0.0000 | 0.0001 | 0.0000 | YES |
| B5-RIFT-OBS | P1 | 45 | 0.444 | 0.378 | +0.067 | [-0.133, +0.267] | [-0.143, +0.250] | +0.14 | 12/9 | 0.6636 | 0.6612 | 1.0000 | no |
| B5-RIFT-OBS | P2 | 108 | 0.556 | 0.389 | +0.167 | [+0.055, +0.278] | [+0.049, +0.283] | +0.34 | 31/13 | 0.0096 | 0.0110 | 0.1147 | no |
| B5-RIFT-OBS | P3_safe | 108 | 0.657 | 0.509 | +0.148 | [+0.037, +0.259] | [+0.033, +0.262] | +0.30 | 29/13 | 0.0195 | 0.0206 | 0.1952 | no |
| B6-RIFT-RANDOM | P1 | 45 | 0.444 | 0.600 | -0.156 | [-0.311, +0.022] | [-0.333, +0.022] | -0.31 | 5/12 | 0.1435 | 0.1482 | 1.0000 | no |
| B6-RIFT-RANDOM | P2 | 108 | 0.556 | 0.306 | +0.250 | [+0.130, +0.370] | [+0.121, +0.374] | +0.51 | 39/12 | 0.0002 | 0.0002 | 0.0028 | YES |
| B6-RIFT-RANDOM | P3_safe | 108 | 0.657 | 0.306 | +0.352 | [+0.241, +0.463] | [+0.236, +0.467] | +0.72 | 44/6 | 0.0000 | 0.0001 | 0.0000 | YES |
| B7-RIFT-ONE-SHOT | P1 | 45 | 0.444 | 0.600 | -0.156 | [-0.311, +0.022] | [-0.333, +0.022] | -0.31 | 5/12 | 0.1435 | 0.1482 | 1.0000 | no |
| B7-RIFT-ONE-SHOT | P2 | 108 | 0.556 | 0.306 | +0.250 | [+0.130, +0.370] | [+0.121, +0.374] | +0.51 | 39/12 | 0.0002 | 0.0002 | 0.0028 | YES |
| B7-RIFT-ONE-SHOT | P3_safe | 108 | 0.657 | 0.306 | +0.352 | [+0.241, +0.463] | [+0.236, +0.467] | +0.72 | 44/6 | 0.0000 | 0.0001 | 0.0000 | YES |
| RIFT-FULL-LEGACY | P1 | 45 | 0.444 | 0.467 | -0.022 | [-0.156, +0.111] | [-0.167, +0.128] | -0.04 | 5/6 | 1.0000 | 1.0000 | 1.0000 | no |
| RIFT-FULL-LEGACY | P2 | 108 | 0.556 | 0.481 | +0.074 | [-0.009, +0.157] | [-0.009, +0.159] | +0.15 | 15/7 | 0.1338 | 0.1309 | 1.0000 | no |
| RIFT-FULL-LEGACY | P3_safe | 108 | 0.657 | 0.546 | +0.111 | [+0.028, +0.194] | [+0.028, +0.189] | +0.23 | 17/5 | 0.0169 | 0.0170 | 0.1859 | no |

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

| Split | Method | P2 method | P2 always-abstain | diff | 95% CI (widest) | method-only / always-abstain-only correct | McNemar exact p (UNCORRECTED, post-hoc) |
|---|---|---|---|---|---|---|---|
| dev | RIFT-FULL-V2 | 102/180 = 0.567 | 112/180 = 0.622 | -0.056 | [-0.150, +0.039] | 28/38 | 0.2678 |
| dev | RIFT-FULL-V2G (exploratory) | 117/180 = 0.650 | 112/180 = 0.622 | +0.028 | [-0.048, +0.105] | 24/19 | 0.5424 |
| dev | RIFT-FULL-LEGACY | 81/180 = 0.450 | 112/180 = 0.622 | -0.172 | [-0.270, -0.075] | 25/56 | 0.0008 |
| dev | B5-RIFT-OBS | 70/180 = 0.389 | 112/180 = 0.622 | -0.233 | [-0.344, -0.119] | 24/66 | 0.0000 |
| val | RIFT-FULL-V2 | 35/72 = 0.486 | 41/72 = 0.569 | -0.083 | [-0.222, +0.058] | 8/14 | 0.2863 |
| val | RIFT-FULL-V2G (exploratory) | 41/72 = 0.569 | 41/72 = 0.569 | +0.000 | [-0.095, +0.091] | 5/5 | 1.0000 |
| val | RIFT-FULL-LEGACY | 36/72 = 0.500 | 41/72 = 0.569 | -0.069 | [-0.261, +0.128] | 15/20 | 0.4996 |
| val | B5-RIFT-OBS | 21/72 = 0.292 | 41/72 = 0.569 | -0.278 | [-0.459, -0.099] | 6/26 | 0.0005 |
| held-out | RIFT-FULL-V2 | 60/108 = 0.556 | 63/108 = 0.583 | -0.028 | [-0.145, +0.102] | 20/23 | 0.7608 |
| held-out | RIFT-FULL-V2G (exploratory) | 63/108 = 0.583 | 63/108 = 0.583 | +0.000 | [-0.099, +0.109] | 14/14 | 1.0000 |
| held-out | RIFT-FULL-LEGACY | 52/108 = 0.481 | 63/108 = 0.583 | -0.102 | [-0.231, +0.036] | 21/32 | 0.1690 |
| held-out | B5-RIFT-OBS | 42/108 = 0.389 | 63/108 = 0.583 | -0.194 | [-0.333, -0.046] | 17/38 | 0.0065 |

* On held-out, V2 is **-0.028** relative to always-abstain on P2 (McNemar p = 0.76). The honest reading: on this benchmark,
  where 58 % of scenarios require abstention, V2's P2 cannot be distinguished from the policy that never answers; its gains over
  the never-abstaining baselines mostly reflect abstention.
* B5-RIFT-OBS is significantly *below* always-abstain (p = 0.0065); legacy RIFT-FULL is below it (not significant).
* V2G (exploratory) ties always-abstain exactly on held-out (63/108 vs 63/108) and val (41/72), and is +0.028 on dev.
* This analysis exists because the always-abstain reference makes P2 interpretable. It should have been in the protocol; it
  was not. It is reported as post-hoc and not used to change any hypothesis verdict or threshold.

## 6. Detection (stage 1: EBD R1 persistence detector, method-independent)

| Split | fault scenarios | no-fault scenarios | TP | FN | FP | TN | precision | recall | F1 | FPR | FNR | delay s, median |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | 171 | 9 | 154 | 17 | 3 | 6 | 0.981 | 0.901 | 0.939 | 0.33 (3/9) | 0.099 (17/171) | 0 (IQR 0-30, n=154) |
| val | 68 | 4 | 63 | 5 | 1 | 3 | 0.984 | 0.926 | 0.955 | 0.25 (1/4) | 0.074 (5/68) | 0 (IQR 0-20, n=63) |
| held-out | 104 | 4 | 100 | 4 | 2 | 2 | 0.980 | 0.962 | 0.971 | 0.50 (2/4) | 0.038 (4/104) | 0 (IQR 0-20, n=100) |

Held-out FPR = 2/4 = 0.50 on **four** no-fault scenarios (dev 3/9, val 1/4). With so few no-fault scenarios the FPR estimate is
extremely imprecise (the exact 95 % CI for 2/4 spans roughly 0.07-0.93) and should not be used to claim a specific false-alarm rate.
Recall 100/104 on held-out fault scenarios; median detection delay 0 s (IQR 0-20 s; the simulation's window is 10 s).

## 7. Exploratory V2G (Amendment 3: designed after dev/val failures, before freeze; held-out never read for design)

Rule: abstain `UNRESOLVED_EARLIER_DIVERGENCE` when a service with an earlier R1 divergence than the attributed one is neither
attributed nor explained by a confirmed intervention. No free parameter.

| Metric | p(V2G) | p(V2) | diff (V2G - V2) | 95% CI | V2G-only / V2-only | McNemar p (exploratory, uncorrected) |
|---|---|---|---|---|---|---|
| P1 | 0.311 | 0.444 | -0.133 | [-0.244, -0.044] | 0/6 | 0.0312 |
| P2 | 0.583 | 0.556 | +0.028 | [-0.046, +0.093] | 9/6 | 0.6072 |
| P3_safe | 0.833 | 0.657 | +0.176 | [+0.107, +0.250] | 19/0 | 0.0000 |

V2G trades coverage and P1 for safety: P1 falls 0.444 -> 0.311 (V2G worse, McNemar p = 0.031, uncorrected), P2 rises 0.556 -> 0.583
(p = 0.61, not significant), unsafe falls 37/108 -> 18/108. It ties always-abstain on P2. It does **not** improve attribution
accuracy, and the amendment is **exploratory**: it was written after looking at dev/val failures. It is not part of the Holm family
and no claim in this sprint depends on it.

## 8. Ablations A1-A10 (held-out; exploratory; McNemar p uncorrected)

A1 = RIFT-FULL-V2. Column "dP1 vs V2" is *ablation minus V2* (positive = the ablation did better).

| Config | P1 | P2 | unsafe rate | coverage | mean intervention s | mean ms | dP1 vs V2 (ablation - V2; McNemar p) | dP2 vs V2 | d(not-unsafe) vs V2 |
|---|---|---|---|---|---|---|---|---|---|
| A1-FULL (= RIFT-FULL-V2) | 0.444 | 0.556 | 0.343 | 0.528 | 56.4 | 41 | - | - | - |
| A2-NO-FCI | 0.578 | 0.500 | 0.435 | 0.676 | 59.4 | 31 | +0.133 (p=0.109) | -0.056 (p=0.286) | -0.093 (p=0.041) |
| A3-NO-EBD | 0.378 | 0.417 | 0.500 | 0.657 | 70.8 | 10 | -0.067 (p=0.250) | -0.139 (p=0.000) | -0.157 (p=0.000) |
| A4-NO-CID | 0.511 | 0.546 | 0.361 | 0.574 | 52.5 | 7 | +0.067 (p=0.250) | -0.009 (p=1.000) | -0.019 (p=0.727) |
| A5-NO-IDENT | 0.444 | 0.556 | 0.352 | 0.537 | 56.9 | 7 | -0.000 (p=1.000) | -0.000 (p=1.000) | -0.009 (p=1.000) |
| A6-NO-INTERVENTION | 0.444 | 0.537 | 0.296 | 0.481 | 0.0 | 6 | -0.000 (p=1.000) | -0.019 (p=0.845) | +0.046 (p=0.424) |
| A7-NO-MSIS | 0.444 | 0.556 | 0.343 | 0.528 | 60.3 | 11 | -0.000 (p=1.000) | -0.000 (p=1.000) | -0.000 (p=1.000) |
| A8-OBSERVATIONAL-ONLY | 0.444 | 0.537 | 0.306 | 0.491 | 0.0 | 6 | -0.000 (p=1.000) | -0.019 (p=0.845) | +0.037 (p=0.557) |
| A9-ORACLE-GRAPH (ORACLE graph) | 0.711 | 0.556 | 0.380 | 0.676 | 56.7 | 41 | +0.267 (p=0.000) | -0.000 (p=1.000) | -0.037 (p=0.503) |
| A10-RANDOM-INTERVENTION | 0.378 | 0.528 | 0.370 | 0.528 | 61.1 | 10 | -0.067 (p=0.375) | -0.028 (p=0.375) | -0.028 (p=0.375) |

Across splits (P1 / P2 / unsafe / coverage):

| Config | dev  P1 / P2 / unsafe / coverage | val  P1 / P2 / unsafe / coverage | held-out  P1 / P2 / unsafe / coverage |
|---|---|---|---|
| A1-FULL | 0.41 / 0.57 / 0.29 / 0.44 | 0.26 / 0.49 / 0.38 / 0.49 | 0.44 / 0.56 / 0.34 / 0.53 |
| A2-NO-FCI | 0.56 / 0.57 / 0.30 / 0.51 | 0.52 / 0.51 / 0.36 / 0.58 | 0.58 / 0.50 / 0.44 / 0.68 |
| A3-NO-EBD | 0.40 / 0.53 / 0.33 / 0.48 | 0.29 / 0.44 / 0.43 / 0.56 | 0.38 / 0.42 / 0.50 / 0.66 |
| A4-NO-CID | 0.41 / 0.56 / 0.32 / 0.47 | 0.29 / 0.47 / 0.39 / 0.51 | 0.51 / 0.55 / 0.36 / 0.57 |
| A5-NO-IDENT | 0.41 / 0.57 / 0.29 / 0.44 | 0.29 / 0.49 / 0.40 / 0.53 | 0.44 / 0.56 / 0.35 / 0.54 |
| A6-NO-INTERVENTION | 0.41 / 0.52 / 0.38 / 0.53 | 0.42 / 0.58 / 0.24 / 0.42 | 0.44 / 0.54 / 0.30 / 0.48 |
| A7-NO-MSIS | 0.40 / 0.56 / 0.29 / 0.44 | 0.23 / 0.47 / 0.39 / 0.49 | 0.44 / 0.56 / 0.34 / 0.53 |
| A8-OBSERVATIONAL-ONLY | 0.41 / 0.52 / 0.38 / 0.53 | 0.48 / 0.60 / 0.25 / 0.46 | 0.44 / 0.54 / 0.31 / 0.49 |
| A9-ORACLE-GRAPH | 0.57 / 0.58 / 0.28 / 0.50 | 0.61 / 0.57 / 0.31 / 0.57 | 0.71 / 0.56 / 0.38 / 0.68 |
| A10-RANDOM-INTERVENTION | 0.38 / 0.56 / 0.30 / 0.44 | 0.29 / 0.50 / 0.36 / 0.49 | 0.38 / 0.53 / 0.37 / 0.53 |

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

| Split | n (earliest_not_root + coincidental_anomaly + indistinguishable_onsets) | V2 unsafe | A6 unsafe | A8 unsafe | V2 coverage | A6 coverage | verdict |
|---|---|---|---|---|---|---|---|
| dev | 12 | 6/12 = 0.500 | 5/12 = 0.417 | 5/12 = 0.417 | 7/12 = 0.583 | 6/12 = 0.500 | NOT SUPPORTED (no higher unsafe count without interventions) |
| val | 6 | 4/6 = 0.667 | 3/6 = 0.500 | 3/6 = 0.500 | 5/6 = 0.833 | 4/6 = 0.667 | NOT SUPPORTED (no higher unsafe count without interventions) |
| held-out | 7 | 4/7 = 0.571 | 3/7 = 0.429 | 3/7 = 0.429 | 5/7 = 0.714 | 3/7 = 0.429 | NOT SUPPORTED (no higher unsafe count without interventions) |

Without interventions (A6, A8) the unsafe count is **lower or equal** to V2's in every split (held-out 3 vs 4 of 7; dev 5 vs 6 of 12;
val 3 vs 4 of 6). The predicted direction (A6/A8 worse) was not observed. n = 7 / 12 / 6 is too small for inference; the result is
"not supported", not "refuted".

### 9.2 H5 — mixed

| Split | Alternative order | mean ED V2 (s) | mean ED alt. (s) | alt. - V2 (s) | template-boot 95% CI of diff | #scenarios differing | sign-flip permutation p (uncorrected) | P1 V2 vs alt. |
|---|---|---|---|---|---|---|---|---|
| dev | A10-RANDOM-INTERVENTION | 44.8 | 46.5 | +1.7 | [-0.5, +4.1] | 39 | 0.2409 | 0.412 vs 0.382 |
| dev | A7-NO-MSIS | 44.8 | 43.8 | -1.0 | [-2.9, +0.8] | 33 | 0.4532 | 0.412 vs 0.397 |
| val | A10-RANDOM-INTERVENTION | 51.2 | 50.8 | -0.4 | [-5.3, +4.2] | 22 | 1.0000 | 0.258 vs 0.290 |
| val | A7-NO-MSIS | 51.2 | 52.9 | +1.7 | [-3.0, +6.8] | 18 | 0.6101 | 0.258 vs 0.226 |
| held-out | A10-RANDOM-INTERVENTION | 56.4 | 61.1 | +4.7 | [+2.2, +7.4] | 24 | 0.0014 | 0.444 vs 0.378 |
| held-out | A7-NO-MSIS | 56.4 | 60.3 | +3.9 | [+0.8, +7.2] | 22 | 0.0246 | 0.444 vs 0.444 |

MSIS ordering reduces mean intervention seconds on held-out (V2 56.4 s vs random order 61.1 s, permutation p = 0.0014; vs alphabetical
60.3 s, p = 0.0246) but **not** on dev (p = 0.24 / 0.45) or val (p = 1.0 / 0.61). Accuracy differences are not significant (held-out
P1 0.444 vs 0.378 vs 0.444). The cost advantage is therefore split-dependent, small in absolute terms (4-5 s of ~60 s), uncorrected for
multiplicity, and based on simulated intervention durations.

## 10. Distribution shift (held-out only; descriptive)

| Stratum | Method | n | n ATTRIBUTE | P1 | P2 | unsafe | coverage |
|---|---|---|---|---|---|---|---|
| structure=feedback_like | RIFT-FULL-V2 | 24 | 13 | 4/13 = 0.31 | 11/24 = 0.46 | 8/24 = 0.33 | 12/24 = 0.50 |
| structure=feedback_like | RIFT-FULL-V2G | 24 | 13 | 3/13 = 0.23 | 12/24 = 0.50 | 5/24 = 0.21 | 8/24 = 0.33 |
| structure=feedback_like | RIFT-FULL-LEGACY | 24 | 13 | 4/13 = 0.31 | 9/24 = 0.38 | 11/24 = 0.46 | 15/24 = 0.62 |
| structure=feedback_like | B6-RIFT-RANDOM | 24 | 13 | 6/13 = 0.46 | 6/24 = 0.25 | 18/24 = 0.75 | 24/24 = 1.00 |
| family=recovery_instability | RIFT-FULL-V2 | 18 | 8 | 5/8 = 0.62 | 11/18 = 0.61 | 6/18 = 0.33 | 11/18 = 0.61 |
| family=recovery_instability | RIFT-FULL-V2G | 18 | 8 | 4/8 = 0.50 | 10/18 = 0.56 | 4/18 = 0.22 | 8/18 = 0.44 |
| family=recovery_instability | RIFT-FULL-LEGACY | 18 | 8 | 6/8 = 0.75 | 10/18 = 0.56 | 8/18 = 0.44 | 14/18 = 0.78 |
| family=recovery_instability | B6-RIFT-RANDOM | 18 | 8 | 7/8 = 0.88 | 7/18 = 0.39 | 11/18 = 0.61 | 18/18 = 1.00 |
| seen_structure_and_family | RIFT-FULL-V2 | 68 | 25 | 12/25 = 0.48 | 40/68 = 0.59 | 23/68 = 0.34 | 35/68 = 0.51 |
| seen_structure_and_family | RIFT-FULL-V2G | 68 | 25 | 8/25 = 0.32 | 43/68 = 0.63 | 9/68 = 0.13 | 17/68 = 0.25 |
| seen_structure_and_family | RIFT-FULL-LEGACY | 68 | 25 | 12/25 = 0.48 | 35/68 = 0.51 | 30/68 = 0.44 | 42/68 = 0.62 |
| seen_structure_and_family | B6-RIFT-RANDOM | 68 | 25 | 15/25 = 0.60 | 21/68 = 0.31 | 47/68 = 0.69 | 62/68 = 0.91 |

`feedback_like` (n = 24) and `recovery_instability` (n = 18) overlap, and per-cell n is small; V2's behaviour on unseen strata is
noisy and descriptive only.

## 11. Observability strata (held-out; descriptive)

| Observability stratum | Method | n | n ATTRIBUTE | P1 | P2 | unsafe | coverage |
|---|---|---|---|---|---|---|---|
| complete_or_ambiguous_pag | RIFT-FULL-V2 | 24 | 9 | 2/9 = 0.22 | 8/24 = 0.33 | 14/24 = 0.58 | 16/24 = 0.67 |
| complete_or_ambiguous_pag | RIFT-FULL-LEGACY | 24 | 9 | 4/9 = 0.44 | 10/24 = 0.42 | 12/24 = 0.50 | 16/24 = 0.67 |
| complete_or_ambiguous_pag | B6-RIFT-RANDOM | 24 | 9 | 5/9 = 0.56 | 6/24 = 0.25 | 18/24 = 0.75 | 23/24 = 0.96 |
| degraded:conflicting_observational_evidence | RIFT-FULL-V2 | 12 | 5 | 4/5 = 0.80 | 10/12 = 0.83 | 2/12 = 0.17 | 6/12 = 0.50 |
| degraded:conflicting_observational_evidence | RIFT-FULL-LEGACY | 12 | 5 | 4/5 = 0.80 | 6/12 = 0.50 | 6/12 = 0.50 | 10/12 = 0.83 |
| degraded:conflicting_observational_evidence | B6-RIFT-RANDOM | 12 | 5 | 2/5 = 0.40 | 2/12 = 0.17 | 10/12 = 0.83 | 12/12 = 1.00 |
| degraded:delayed_telemetry | RIFT-FULL-V2 | 12 | 6 | 3/6 = 0.50 | 6/12 = 0.50 | 6/12 = 0.50 | 9/12 = 0.75 |
| degraded:delayed_telemetry | RIFT-FULL-LEGACY | 12 | 6 | 3/6 = 0.50 | 6/12 = 0.50 | 6/12 = 0.50 | 9/12 = 0.75 |
| degraded:delayed_telemetry | B6-RIFT-RANDOM | 12 | 6 | 3/6 = 0.50 | 3/12 = 0.25 | 9/12 = 0.75 | 12/12 = 1.00 |
| degraded:insufficient_samples | RIFT-FULL-V2 | 12 | 0 | n/a | 12/12 = 1.00 | 0/12 = 0.00 | 0/12 = 0.00 |
| degraded:insufficient_samples | RIFT-FULL-LEGACY | 12 | 0 | n/a | 11/12 = 0.92 | 1/12 = 0.08 | 1/12 = 0.08 |
| degraded:insufficient_samples | B6-RIFT-RANDOM | 12 | 0 | n/a | 3/12 = 0.25 | 9/12 = 0.75 | 9/12 = 0.75 |
| degraded:missing_windows | RIFT-FULL-V2 | 12 | 7 | 3/7 = 0.43 | 5/12 = 0.42 | 5/12 = 0.42 | 8/12 = 0.67 |
| degraded:missing_windows | RIFT-FULL-LEGACY | 12 | 7 | 0/7 = 0.00 | 1/12 = 0.08 | 9/12 = 0.75 | 9/12 = 0.75 |
| degraded:missing_windows | B6-RIFT-RANDOM | 12 | 7 | 3/7 = 0.43 | 3/12 = 0.25 | 9/12 = 0.75 | 12/12 = 1.00 |
| degraded:noisy_telemetry | RIFT-FULL-V2 | 12 | 3 | 2/3 = 0.67 | 8/12 = 0.67 | 4/12 = 0.33 | 6/12 = 0.50 |
| degraded:noisy_telemetry | RIFT-FULL-LEGACY | 12 | 3 | 3/3 = 1.00 | 9/12 = 0.75 | 3/12 = 0.25 | 6/12 = 0.50 |
| degraded:noisy_telemetry | B6-RIFT-RANDOM | 12 | 3 | 3/3 = 1.00 | 5/12 = 0.42 | 7/12 = 0.58 | 10/12 = 0.83 |
| degraded:partial_service_observability | RIFT-FULL-V2 | 12 | 8 | 4/8 = 0.50 | 5/12 = 0.42 | 4/12 = 0.33 | 8/12 = 0.67 |
| degraded:partial_service_observability | RIFT-FULL-LEGACY | 12 | 8 | 3/8 = 0.38 | 3/12 = 0.25 | 8/12 = 0.67 | 11/12 = 0.92 |
| degraded:partial_service_observability | B6-RIFT-RANDOM | 12 | 8 | 4/8 = 0.50 | 4/12 = 0.33 | 8/12 = 0.67 | 12/12 = 1.00 |
| degraded:weak_interventional_evidence | RIFT-FULL-V2 | 12 | 7 | 2/7 = 0.29 | 6/12 = 0.50 | 2/12 = 0.17 | 4/12 = 0.33 |
| degraded:weak_interventional_evidence | RIFT-FULL-LEGACY | 12 | 7 | 4/7 = 0.57 | 6/12 = 0.50 | 4/12 = 0.33 | 8/12 = 0.67 |
| degraded:weak_interventional_evidence | B6-RIFT-RANDOM | 12 | 7 | 7/7 = 1.00 | 7/12 = 0.58 | 5/12 = 0.42 | 12/12 = 1.00 |
| **all degraded pooled** | RIFT-FULL-V2 | 84 | 36 | 18/36 = 0.50 | 52/84 = 0.62 | 23/84 = 0.27 | 41/84 = 0.49 |
| **all degraded pooled** | RIFT-FULL-V2G | 84 | 36 | 12/36 = 0.33 | 53/84 = 0.63 | 10/84 = 0.12 | 22/84 = 0.26 |
| **all degraded pooled** | RIFT-FULL-LEGACY | 84 | 36 | 17/36 = 0.47 | 42/84 = 0.50 | 37/84 = 0.44 | 54/84 = 0.64 |
| **all degraded pooled** | B6-RIFT-RANDOM | 84 | 36 | 22/36 = 0.61 | 27/84 = 0.32 | 57/84 = 0.68 | 79/84 = 0.94 |
| **all degraded pooled** | B3-SIEVE-LIKE | 84 | 36 | 15/36 = 0.42 | 16/84 = 0.19 | 68/84 = 0.81 | 83/84 = 0.99 |
| **all degraded pooled** | B1-LATENCY-CORR | 84 | 36 | 14/36 = 0.39 | 15/84 = 0.18 | 69/84 = 0.82 | 83/84 = 0.99 |

**Caveat on degraded observability.** V2 beats legacy and B6 on P2 in the pooled degraded stratum (52/84 vs 42/84 and 27/84), but much of
that comes from abstaining. For example, `insufficient_samples` shows V2 P2 = 12/12 with **coverage 0/12**: that is a zero-coverage
"perfect" score, not an advantage in attribution. V2's pooled degraded P1 is 18/36 against B6's 22/36.

## 12. Per-family and per-structure breakdowns (held-out, RIFT-FULL-V2; n per cell is small)

### 12.1 By fault family
| family | n | n ATTRIBUTE | P1 (den. n ATTRIBUTE) | P2 (den. n) | unsafe (den. n) | coverage (den. n) |
|---|---|---|---|---|---|---|
| cascading_failure | 9 | 0 | n/a | 6/9 = 0.67 | 3/9 = 0.33 | 3/9 = 0.33 |
| compound | 6 | 3 | 2/3 = 0.67 | 4/6 = 0.67 | 1/6 = 0.17 | 3/6 = 0.50 |
| cpu_contention | 6 | 3 | 1/3 = 0.33 | 2/6 = 0.33 | 3/6 = 0.50 | 4/6 = 0.67 |
| dependency_failure | 6 | 5 | 4/5 = 0.80 | 4/6 = 0.67 | 2/6 = 0.33 | 6/6 = 1.00 |
| intermittent | 5 | 4 | 3/4 = 0.75 | 4/5 = 0.80 | 1/5 = 0.20 | 4/5 = 0.80 |
| latency_degradation | 7 | 4 | 3/4 = 0.75 | 6/7 = 0.86 | 0/7 = 0.00 | 3/7 = 0.43 |
| memory_pressure | 6 | 4 | 1/4 = 0.25 | 2/6 = 0.33 | 2/6 = 0.33 | 3/6 = 0.50 |
| network_degradation | 8 | 2 | 0/2 = 0.00 | 4/8 = 0.50 | 3/8 = 0.38 | 3/8 = 0.38 |
| packet_loss | 8 | 1 | 0/1 = 0.00 | 4/8 = 0.50 | 4/8 = 0.50 | 4/8 = 0.50 |
| partial_degradation | 4 | 0 | n/a | 3/4 = 0.75 | 1/4 = 0.25 | 1/4 = 0.25 |
| queue_buildup | 5 | 2 | 0/2 = 0.00 | 2/5 = 0.40 | 2/5 = 0.40 | 2/5 = 0.40 |
| recovery_instability | 18 | 8 | 5/8 = 0.62 | 11/18 = 0.61 | 6/18 = 0.33 | 11/18 = 0.61 |
| resource_saturation | 4 | 0 | n/a | 3/4 = 0.75 | 1/4 = 0.25 | 1/4 = 0.25 |
| retry_amplification | 5 | 2 | 1/2 = 0.50 | 2/5 = 0.40 | 3/5 = 0.60 | 4/5 = 0.80 |
| service_unavailability | 6 | 4 | 0/4 = 0.00 | 1/6 = 0.17 | 4/6 = 0.67 | 4/6 = 0.67 |
| transient | 5 | 3 | 0/3 = 0.00 | 2/5 = 0.40 | 1/5 = 0.20 | 1/5 = 0.20 |

### 12.2 By causal structure
| structure | n | n ATTRIBUTE | P1 (den. n ATTRIBUTE) | P2 (den. n) | unsafe (den. n) | coverage (den. n) |
|---|---|---|---|---|---|---|
| ambiguous | 15 | 0 | n/a | 9/15 = 0.60 | 6/15 = 0.40 | 6/15 = 0.40 |
| branching | 9 | 5 | 2/5 = 0.40 | 6/9 = 0.67 | 3/9 = 0.33 | 5/9 = 0.56 |
| confounding | 11 | 6 | 2/6 = 0.33 | 5/11 = 0.45 | 3/11 = 0.27 | 5/11 = 0.45 |
| converging | 5 | 3 | 0/3 = 0.00 | 1/5 = 0.20 | 1/5 = 0.20 | 1/5 = 0.20 |
| diamond | 6 | 4 | 3/4 = 0.75 | 4/6 = 0.67 | 2/6 = 0.33 | 5/6 = 0.83 |
| feedback_like | 24 | 13 | 4/13 = 0.31 | 11/24 = 0.46 | 8/24 = 0.33 | 12/24 = 0.50 |
| hidden_common_cause | 9 | 0 | n/a | 6/9 = 0.67 | 3/9 = 0.33 | 3/9 = 0.33 |
| linear_chain | 6 | 2 | 1/2 = 0.50 | 4/6 = 0.67 | 2/6 = 0.33 | 3/6 = 0.50 |
| multiple_upstream | 9 | 5 | 4/5 = 0.80 | 6/9 = 0.67 | 3/9 = 0.33 | 7/9 = 0.78 |
| parallel_independent | 9 | 5 | 3/5 = 0.60 | 4/9 = 0.44 | 5/9 = 0.56 | 8/9 = 0.89 |
| shared_dependency | 5 | 2 | 1/2 = 0.50 | 4/5 = 0.80 | 1/5 = 0.20 | 2/5 = 0.40 |

### 12.3 By workload
| workload | n | n ATTRIBUTE | P1 (den. n ATTRIBUTE) | P2 (den. n) | unsafe (den. n) | coverage (den. n) |
|---|---|---|---|---|---|---|
| bursty_traffic | 11 | 4 | 4/4 = 1.00 | 8/11 = 0.73 | 3/11 = 0.27 | 7/11 = 0.64 |
| changing_workload | 10 | 3 | 2/3 = 0.67 | 6/10 = 0.60 | 3/10 = 0.30 | 5/10 = 0.50 |
| high_baseline_variance | 13 | 0 | n/a | 10/13 = 0.77 | 3/13 = 0.23 | 3/13 = 0.23 |
| high_load | 10 | 5 | 2/5 = 0.40 | 4/10 = 0.40 | 6/10 = 0.60 | 8/10 = 0.80 |
| low_baseline_variance | 11 | 9 | 3/9 = 0.33 | 5/11 = 0.45 | 4/11 = 0.36 | 7/11 = 0.64 |
| low_load | 10 | 2 | 1/2 = 0.50 | 6/10 = 0.60 | 4/10 = 0.40 | 5/10 = 0.50 |
| moderate_load | 10 | 3 | 1/3 = 0.33 | 4/10 = 0.40 | 6/10 = 0.60 | 7/10 = 0.70 |
| skewed_requests | 11 | 10 | 5/10 = 0.50 | 6/11 = 0.55 | 4/11 = 0.36 | 9/11 = 0.82 |
| sparse_telemetry | 11 | 6 | 0/6 = 0.00 | 4/11 = 0.36 | 1/11 = 0.09 | 1/11 = 0.09 |
| unequal_service_rates | 11 | 3 | 2/3 = 0.67 | 7/11 = 0.64 | 3/11 = 0.27 | 5/11 = 0.45 |

### 12.4 By observability
| observability | n | n ATTRIBUTE | P1 (den. n ATTRIBUTE) | P2 (den. n) | unsafe (den. n) | coverage (den. n) |
|---|---|---|---|---|---|---|
| ambiguous_pag | 12 | 8 | 2/8 = 0.25 | 4/12 = 0.33 | 6/12 = 0.50 | 8/12 = 0.67 |
| complete_telemetry | 12 | 1 | 0/1 = 0.00 | 4/12 = 0.33 | 8/12 = 0.67 | 8/12 = 0.67 |
| conflicting_observational_evidence | 12 | 5 | 4/5 = 0.80 | 10/12 = 0.83 | 2/12 = 0.17 | 6/12 = 0.50 |
| delayed_telemetry | 12 | 6 | 3/6 = 0.50 | 6/12 = 0.50 | 6/12 = 0.50 | 9/12 = 0.75 |
| insufficient_samples | 12 | 0 | n/a | 12/12 = 1.00 | 0/12 = 0.00 | 0/12 = 0.00 |
| missing_windows | 12 | 7 | 3/7 = 0.43 | 5/12 = 0.42 | 5/12 = 0.42 | 8/12 = 0.67 |
| noisy_telemetry | 12 | 3 | 2/3 = 0.67 | 8/12 = 0.67 | 4/12 = 0.33 | 6/12 = 0.50 |
| partial_service_observability | 12 | 8 | 4/8 = 0.50 | 5/12 = 0.42 | 4/12 = 0.33 | 8/12 = 0.67 |
| weak_interventional_evidence | 12 | 7 | 2/7 = 0.29 | 6/12 = 0.50 | 2/12 = 0.17 | 4/12 = 0.33 |

### 12.5 By intervention mode
| intervention | n | n ATTRIBUTE | P1 (den. n ATTRIBUTE) | P2 (den. n) | unsafe (den. n) | coverage (den. n) |
|---|---|---|---|---|---|---|
| collateral_effects | 12 | 5 | 3/5 = 0.60 | 6/12 = 0.50 | 4/12 = 0.33 | 7/12 = 0.58 |
| delayed | 12 | 3 | 2/3 = 0.67 | 6/12 = 0.50 | 6/12 = 0.50 | 8/12 = 0.67 |
| high_magnitude | 12 | 8 | 2/8 = 0.25 | 5/12 = 0.42 | 6/12 = 0.50 | 8/12 = 0.67 |
| imperfect | 12 | 4 | 0/4 = 0.00 | 6/12 = 0.50 | 3/12 = 0.25 | 3/12 = 0.25 |
| low_magnitude | 12 | 3 | 0/3 = 0.00 | 6/12 = 0.50 | 5/12 = 0.42 | 5/12 = 0.42 |
| multi_service | 12 | 6 | 4/6 = 0.67 | 9/12 = 0.75 | 1/12 = 0.08 | 5/12 = 0.42 |
| no_meaningful_effect | 12 | 5 | 1/5 = 0.20 | 8/12 = 0.67 | 2/12 = 0.17 | 3/12 = 0.25 |
| reversible | 12 | 4 | 3/4 = 0.75 | 8/12 = 0.67 | 4/12 = 0.33 | 7/12 = 0.58 |
| single_service | 12 | 7 | 5/7 = 0.71 | 6/12 = 0.50 | 6/12 = 0.50 | 11/12 = 0.92 |

### 12.6 By negative kind
| negative | n | n ATTRIBUTE | P1 (den. n ATTRIBUTE) | P2 (den. n) | unsafe (den. n) | coverage (den. n) |
|---|---|---|---|---|---|---|
| coincidental_anomaly | 2 | 0 | n/a | 1/2 = 0.50 | 1/2 = 0.50 | 1/2 = 0.50 |
| common_cause_several_services | 3 | 0 | n/a | 1/3 = 0.33 | 2/3 = 0.67 | 2/3 = 0.67 |
| downstream_largest_increase | 3 | 2 | 2/2 = 1.00 | 2/3 = 0.67 | 1/3 = 0.33 | 3/3 = 1.00 |
| earliest_not_root | 3 | 2 | 1/2 = 0.50 | 1/3 = 0.33 | 2/3 = 0.67 | 3/3 = 1.00 |
| high_variance_no_fault | 2 | 0 | n/a | 2/2 = 1.00 | 0/2 = 0.00 | 0/2 = 0.00 |
| incomplete_recovery_after_normalisation | 2 | 2 | 0/2 = 0.00 | 0/2 = 0.00 | 0/2 = 0.00 | 0/2 = 0.00 |
| indistinguishable_onsets | 2 | 1 | 0/1 = 0.00 | 1/2 = 0.50 | 1/2 = 0.50 | 1/2 = 0.50 |
| insufficient_telemetry | 2 | 0 | n/a | 2/2 = 1.00 | 0/2 = 0.00 | 0/2 = 0.00 |
| no_fault_plain | 2 | 0 | n/a | 2/2 = 1.00 | 0/2 = 0.00 | 0/2 = 0.00 |
| none | 81 | 37 | 17/37 = 0.46 | 44/81 = 0.54 | 28/81 = 0.35 | 45/81 = 0.56 |
| root_not_identifiable | 3 | 0 | n/a | 2/3 = 0.67 | 1/3 = 0.33 | 1/3 = 0.33 |
| weak_intervention_effects | 3 | 1 | 0/1 = 0.00 | 2/3 = 0.67 | 1/3 = 0.33 | 1/3 = 0.33 |

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

| Split | status | scenarios | dataset sha256 | config hash | wall-clock s | git commit | started (UTC) |
|---|---|---|---|---|---|---|---|
| dev | VALID | 180 | a833ad0ca1db0583... | 5eef12cd4f39a292... | 26.76 | cbc5ae5e78 | 2026-11-03T04:07:57 |
| val | VALID | 72 | e82252b47f29dc13... | 5eef12cd4f39a292... | 17.2 | cbc5ae5e78 | 2026-11-03T04:08:25 |
| held-out | VALID | 108 | 97b90fa424c3a7c0... | 5eef12cd4f39a292... | 30.97 | cbc5ae5e78 | 2026-11-03T04:06:00 |

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
