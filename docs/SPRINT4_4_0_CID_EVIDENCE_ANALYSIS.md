# Sprint 4.4.0 — CID Evidence Analysis

Scope: offline, synthetic, **dev and val only** (180 + 72 scenarios). No held-out data, no live intervention. All statements are
*validated on synthetic ground-truth scenarios* and *intervention-consistent* only in the simulator's sense. Ground truth is used
**only for post-hoc labelling** of pairs; no method sees it.

Sources: `artifacts/sprint4_4_0/analysis.json` (sections `cid`, `cid_power_monte_carlo`), `artifacts/sprint4_4_0/cid_audit.json`
(written by `scripts/sprint440_cid_audit.py`), `v3_{dev,val}.json`.

## 1. Why every CID check stays CANDIDATE

* Every one of the 555 dev and 314 val CID rows is graded **CANDIDATE**, with `n_min = 30` (`analysis.json: cid.grades`, `cid.n_min`).
* The simulator's `intervene()` returns 30 baseline + 30 post samples at 1 Hz. The frozen CID grading requires n >= 50 for RELIABLE.
  With 30 samples per arm RELIABLE is **unreachable by construction**. This is a data-collection limit of the (frozen) simulated
  do() window, not a threshold that was tuned. We did not lower any threshold to manufacture a higher grade.
* The W1 gate never binds beyond significance: 0 of 181 significant dev rows and 0 of 113 significant val rows fail the W1 gate.
  Practically, "CID confirmed" = "uncorrected/corrected permutation test significant".
* Consequence: V3's `DEFINITIVE_ROOT` is a **status label for the decision rule's internal bookkeeping** (no caveats raised); its
  underlying CID grade is still CANDIDATE. It must not be read as definitive causal evidence. Empirically, V3's DEFINITIVE answers were
  wrong or unsafe about half the time (dev 25 of 48, val 12 of 22; see FINAL_REPORT).

## 2. Sensitivity across effect sizes

Sensitivity = share of **true-ancestor** pairs (x truly an ancestor of y in the full hidden-node-inclusive DAG) with uncorrected
permutation p < 0.05, binned by true noise-free effect of the do() on y in units of sigma_y (Wilson 95% CIs in `analysis.json`).

| effect (sigma_y) | dev k/n | dev | val k/n | val |
|---|---:|---:|---:|---:|
| < 0.25 | 5/51 | 9.8% | 1/28 | 3.6% |
| 0.25–0.5 | 3/14 | 21% | 4/6 | 67% |
| 0.5–1 | 17/35 | 49% | 23/34 | 68% |
| 1–2 | 76/87 | 87% | 46/52 | 88% |
| >= 2 | 45/45 | 100% | 11/12 | 92% |

Monte-Carlo power of the CID permutation test (`scripts/sprint440_analyze.py::power_curve`: i.i.d. Gaussian noise, shift d in sigma units, 150 draws
per cell, 400 permutations per test, rejection at p < 0.05/m i.e. a **Bonferroni** cut-off; i.i.d. noise is more favourable than autocorrelated
simulator series, so these are optimistic; Monte-Carlo error about +/- 4 points; `cid_power_monte_carlo`):

| d (sigma) | n=30, m=1 | n=30, m=3 | n=60, m=1 | n=60, m=3 |
|---|---:|---:|---:|---:|
| 0 (size) | 0.020 | 0.013 | 0.047 | 0.027 |
| 0.25 | 0.147 | 0.087 | 0.267 | 0.133 |
| 0.5 | 0.487 | 0.293 | 0.753 | 0.587 |
| 0.75 | 0.820 | 0.667 | 0.993 | 0.947 |
| 1.0 | 0.953 | 0.900 | 1.0 | 1.0 |

(`m` = number of outcomes in the multiplicity family; V3 itself uses Holm, which is slightly more powerful than the Bonferroni cut-off used here.) With 30 samples per arm the test has ~50% power at 0.5 sigma and roughly 30% with
three outcomes; below 0.5 sigma it is close to blind. Doubling to n = 60 would raise power at 0.5 sigma to 75% (m=1) — a candidate
design change for a future experiment, **not** something this sprint tested on the pipeline.

By intervention mode (dev; sensitivity of true-ancestor pairs): collateral 33/35 (94%), high-magnitude 16/18 (89%), reversible 20/20,
single-service 18/21 (86%), delayed 14/32 (44%), imperfect 13/28 (46%), low-magnitude 13/30 (43%), multi-service 17/30 (57%),
no-meaningful-effect 2/18 (11%). Val differs in places (e.g. high-magnitude 5/9, low-magnitude 10/12) — cells are small (n = 4–26) and
should not be compared across splits.

## 3. The "~94% spurious-effect" figure: critical investigation

### 3.1 What the figure actually is
It first appeared in `scripts/sprint440_analyze.py::cid_analysis` as `false_positive_rate_nonancestral.fault_drift_gt_0.3sigma`:

* **Numerator:** pairs (x, y) with CID permutation p < 0.05 (**uncorrected**).
* **Denominator:** pairs where x is **not** an ancestor of y *and* the noise-free fault contribution to y differs by more than 0.3 sigma_y
  between the 30 s baseline window and the 30 s post window ("window drift").
* **Dev: 16/17 = 94.1%. Val: 17/17 = 100%.** The denominators are **17 pairs per split** (from 10 dev and 6 val scenarios).
* It is **not** a general false-positive rate. It is a rate **conditional on a small, specific stratum**.

### 3.2 Does it reproduce?
`scripts/sprint440_cid_audit.py` re-derives it independently (does not import `analyze.py`; ancestry = `nx.has_path` on the full true
graph incl. hidden nodes; drift computed from the simulator's `fault_series` on the exact do() timestamps). Result
(`cid_audit.json: reproducibility`):

* dev: analyze.py 16/17, audit 16/17; val: analyze.py 17/17, audit 17/17. **Reproduces exactly**, and a second from-scratch run is identical.
* Stratum membership is unchanged after additionally excluding pairs reachable through the co-target/collateral channel (audit
  category C is separate: 2 dev pairs, 0 val).

### 3.3 Is it conditional or broad? (V2 trace pair set; V3 pair set is larger)

| Non-ancestral pairs | dev V2 set | dev V3 set | val V2 set | val V3 set |
|---|---|---|---|---|
| **A** clean (|drift| <= 0.3 sigma, no other channel) | 17/304 = 5.6% (Wilson 3.5–8.8) | 44/780 = 5.6% (4.2–7.5) | 11/165 = 6.7% (3.8–11.5) | 21/535 = 3.9% (2.6–5.9) |
| **B** |drift| > 0.3 sigma | 16/17 = 94% (73–99) | 103/110 = 94% (87–97) | 17/17 = 100% (82–100) | 64/69 = 93% (84–97) |
| **C** real co-target/collateral channel | 2/2 | 2/3 | 0/0 | 0/0 |
| all non-ancestral | 35/323 = 10.8% | 149/893 = 16.7% | 28/182 = 15.4% | 85/604 = 14.1% |
| scenarios contributing to B | 10 | 18 | 6 | 10 |

Scenario-clustered bootstrap 95% CIs (B): dev V2 [0.73, 1.0], dev V3 [0.87, 0.98], val V2 [1.0, 1.0], val V3 [0.88, 1.0] (pairs are nested
in scenarios; the bootstrap resamples scenarios). Clean-pair (A) rates are consistent with the nominal uncorrected 5% level (the
Wilson intervals all contain 0.05).

Conclusions:
1. **Not a general false-positive rate.** In the clean stratum the uncorrected rate is ~4–7%, i.e. close to the 5% the test promises.
2. The 94% applies only to pairs whose outcome y has its *own* time-varying fault contribution between the two windows. Those pairs are a
   minority of non-ancestral pairs (5% of V2-set pairs in dev, 9% in val; 12% / 11% in the V3 sets).
3. All B pairs come from scenarios whose faults have **oscillation or intermittent (and a few recovery_delay)** shapes
   (`B_pairs_by_upstream_fault_shapes`): dev V2 set oscillation 13/13 significant, intermittent 3/4; val intermittent 8/8, oscillation 9/9.
   So the stratum is entangled with scenario temporal family; we cannot separate "time-varying fault" from "that scenario type" with
   10–18 scenarios.

### 3.4 Real intervention effect vs. baseline drift vs. window selection
Dose-response of the non-ancestral uncorrected rate against |drift| (dev V3 set; clean pairs only, `nonancestral_by_abs_drift_sigma`):

| |drift| (sigma_y) | rate | n |
|---|---:|---:|
| 0–0.1 | 38/745 = 5.1% | 745 |
| 0.1–0.3 | 6/35 = 17% | 35 |
| 0.3–0.6 | 2/4 | 4 |
| 0.6–1.0 | 2/3 | 3 |
| >= 1.0 | 99/103 = 96% | 103 |

Val V3: 0–0.1: 4.1% (21/517); 0.1–0.3: 0/18; 0.3–0.6: 0/4; >= 1.0: 64/65 = 98%. The mid-range bins are far too small to describe a curve
(n = 3–35); the only well-populated contrasts are "essentially no drift" (~5%) versus "drift >= 1 sigma" (~96–98%).

What this supports and what it does not:
* The *x -> y* effects flagged in group B are, by the simulator's ground truth, **not interventional effects of x**: x is not an ancestor
  of y. The only thing that differs between the two windows is y's own noise-free fault contribution. The CID design compares y's post-do()
  samples against y's immediately preceding baseline samples with **no concurrent control arm**; any non-stationarity of y over those 60 s is
  therefore attributed to x. This is the mechanism the evidence supports (a **window-selection / missing-control-arm artifact**).
* The data do **not** show whether a real deployment would exhibit such drift (it depends on the simulator's fault shapes) or whether a
  control arm, detrending or randomised do() timing would remove it — we did not test that. It is a *hypothesis for the next experiment*.
* The same drift can also *inflate sensitivity* for genuinely ancestral pairs: 15/232 (dev V2 set) and 14/132 (val) ancestral pairs have
  |drift| > 0.3 sigma, so some "true positives" may be partly drift. The sensitivity table above is therefore an upper-leaning estimate for
  those bins.
* Signed drift among significant B pairs has both signs (dev V3 min -6.2, max +4.8 sigma), so the artifact is not a one-directional bias.

### 3.5 Decision-level implication (V2 vs V3, `cid_audit.json: decision_level`)
Number of *answered* scenarios in which the named service had at least one CID-confirmed effect on a non-ancestral outcome, and the cause
of those spurious confirmations (counted per pair):

| | answered | decisions with a spurious confirmation | of which unsafe | pair causes |
|---|---:|---:|---:|---|
| dev V2 | 80 | 18 | 17 | drift 14, clean FP 9, other channel 1 |
| dev V3 | 67 | 16 | 15 | drift 10, clean FP 11, other channel 1 |
| val V2 | 35 | 7 | 7 | drift 12, clean FP 1 |
| val V3 | 26 | 4 | 4 | drift 6, clean FP 2 |

So 17 of V2's 52 and 15 of V3's 35 dev unsafe answers, and 7 of 27 / 4 of 13 on val, contained at least one spurious confirmation from the
named service. About half of the pair-level causes are drift-affected and half are ordinary ~5% false positives. This is an association in
the decision logs, not a proven causal explanation of each failure; other mechanisms (symmetric dependence, weak signal, unobserved roots)
also produce unsafe answers.

## 4. Implications for attribution confidence

1. A CID "confirmation" in this pipeline is an **uncorrected-then-Holm/Bonferroni permutation test on 30 vs 30 samples without a control
   arm**. It is intervention-*consistent* evidence, not proof. It cannot distinguish the effect of x from concurrent non-stationarity in y.
2. Because spurious confirmations occur in ~5% of clean pairs and in ~94–100% of drift pairs, **a single confirmed edge is weak evidence**
   in scenarios with oscillating or intermittent faults. V3's source rule (require no confirmed effect *into* the source and treat mutual
   effects as non-identifiable) offsets some of this but, as the numbers above show, does not eliminate it.
3. V3 confidence values (1.0 / 0.5 / 0.25 / 0.1) are **ordinal and uncalibrated**. DEFINITIVE answers were ~50% unsafe; no probability or
   coverage guarantee should be read from them.
4. Low-effect true ancestors (< 0.5 sigma) are mostly missed (dev 8/65, val 5/34): the pipeline will abstain or mis-attribute when the
   intervention is weak. That is an abstention failure (LOST_ATTRIBUTE), not a false claim, but it caps achievable P1.

## 5. What this does not establish
* It does not show that CID is "wrong" in general: only that, on these simulator scenarios, its type-I error is nominal in the clean
  stratum and ~1 in the drift stratum, and its power is ~50% at 0.5 sigma with 30 samples.
* It does not show that a control-arm or detrended design would fix the drift problem (untested).
* It does not generalise beyond the 252 dev+val synthetic scenarios and their generator.

## 6. Reproduction
```
python3 scripts/sprint440_analyze.py        # writes analysis.json (cid, power) and graph_quality.csv
python3 scripts/sprint440_cid_audit.py      # writes cid_audit.json (independent re-derivation of the 94% figure)
```
Both scripts load only `load_v2("dev")` and `load_v2("val")`.
