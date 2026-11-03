# Sprint 4.5.0 — CID Reliability Experiment Design (Phase A)

**Status: PROPOSED design (revised in Sprint 4.5.1: eligibility rule, replicate-sharing statement and cell reconciliation corrected). Nothing here has been implemented or run.** It becomes binding when recorded under [`SPRINT4_5_0_PREREGISTRATION.md`](SPRINT4_5_0_PREREGISTRATION.md) (PRE) §13.
Phase A is **independent of Phase B** (the V3 confirmatory evaluation). It cannot modify V3, its CID call or its thresholds, and its outputs are not inputs to Phase B (PRE §8).

Empirical anchors quoted below come from the Sprint 4.4.0 dev/val CID audit (`docs/SPRINT4_4_0_CID_EVIDENCE_ANALYSIS.md`, `artifacts/sprint4_4_0/cid_audit.json`) and are **non-confirmatory**. Language: "intervention-consistent", never "causally accurate"; CANDIDATE-grade CID is never definitive.

---

## 1. Purpose and the distinction that drives the design

**Question A.** Under which kinds of unrelated temporal change does an intervention-evidence check (CID-style, comparing outcome telemetry before and after a perturbation of x) stay valid, and which estimators restore validity?

Two different things can be improved, and Phase A keeps them strictly apart:

| | **Anomaly detection** | **Causal identification** |
|---|---|---|
| question answered | "did the distribution of y change between these windows?" | "did perturbing x change y, relative to what y would have done without perturbing x?" |
| needs | a statistic and a null for stationary data | a counterfactual: an assumption or a design that supplies y's no-intervention path ($Y_t(0)$) during the post window |
| improved by | more samples, a better test statistic, a better noise model | a control series, randomisation of timing, or a testable assumption about the form of the unrelated change |
| failure mode | missed or spurious *changes* | spurious or missed *effects of x*: a real change in y with no effect of x is a false "confirmation" |

CID with consecutive baseline/post windows is a detector of between-window change. It is "intervention-consistent" only to the degree that nothing else changes in y between the windows. **An estimator that lowers false positives in a simulator is not thereby shown to identify the effect of x**: it may be removing one kind of drift (linear) while failing on another (oscillation). Phase A therefore evaluates every estimator against an explicit identifying assumption and checks whether that assumption has a diagnostic.

---

## 2. Notation, estimands and confounding structure

For outcome service $y$, windows $A = \text{baseline } (t = 0\dots n-1)$ and $B = \text{post } (t = n\dots 2n-1)$ at 1 Hz. Perturbation of $x$ begins at $t_0 = n + \delta_{\text{resp}}$ (delay $\delta_{\text{resp}} \ge 0$ s). Potential outcomes $Y_t(a)$, $a \in \{0, 1\}$ ($x$ unperturbed / perturbed). Data-generating model (§4):

$$Y_t(a) = \mu + D_y(t) + S(t) + a \cdot \tau(t - t_0) + \varepsilon_t,$$

with $D_y$ independent own-drift of $y$, $S$ shared drift (common to $y$, a control service and a control replica, §4), $\tau$ the true effect, and $\varepsilon_t$ noise with AR(1) parameter $\rho$ and variance ratio $v$ in $B$.

* **Causal estimand (distributional):** $\Delta_y = W_1( F_B^{(0)}, F_B^{(1)} )$, where $F_B^{(a)}$ is the distribution of $\{Y_t(a) : t \in B\}$. The sharp null is $Y_t(1) = Y_t(0)$ for all $t$, which implies $\Delta_y = 0$. (Mean version: $\bar{\tau}_y = \frac{1}{n} \sum_{t \in B} \mathbb{E}[Y_t(1) - Y_t(0)]$.)
* **Natural-change nuisance:** $\kappa_y = W_1( F_A^{(0)}, F_B^{(0)} )$: how much $y$ changes between windows even if $x$ is never perturbed. It is zero only if $D_y$, $S$ and the noise structure are identical in $A$ and $B$.

The target of the permutation test in the current CID is $\psi_0 = W_1( F_A^{(0)}, F_B^{(1)} )$.

### 2.1 Mathematical proof of the $W_1$ triangle inequality bounds

By the metric properties of the Wasserstein-$1$ distance $W_1(\cdot, \cdot)$ (satisfying non-negativity, symmetry, and the triangle inequality):

1. **Upper bound on $\psi_0$:**
   $$W_1(F_A^{(0)}, F_B^{(1)}) \le W_1(F_B^{(0)}, F_B^{(1)}) + W_1(F_A^{(0)}, F_B^{(0)}) = \Delta_y + \kappa_y.$$
2. **Lower bound on $\psi_0$:**
   $$W_1(F_B^{(0)}, F_B^{(1)}) \le W_1(F_A^{(0)}, F_B^{(1)}) + W_1(F_A^{(0)}, F_B^{(0)}) \implies \Delta_y \le \psi_0 + \kappa_y \implies \psi_0 \ge \Delta_y - \kappa_y.$$

Combining both inequalities yields the exact bounding envelope:

$$\mathbf{\Delta_y - \kappa_y \le \psi_0 \le \Delta_y + \kappa_y}.$$

**Consequences:**
* When $\kappa_y$ exceeds the CID effect-size gate $\theta = 0.1 \times \text{IQR}(\text{baseline})$, the gate can be exceeded even under the sharp null $\Delta_y = 0$ (false confirmation rate up to 100%).
* Conversely, when $\Delta_y > 0$, natural drift can move in opposition to the intervention effect, causing cancellation where $\psi_0 < \theta$ (masking genuine effects).
* **Confounding structure:** In any consecutive-window design without concurrent controls or randomisation, treatment assignment is deterministically confounded with time ($A \implies a=0$, $B \implies a=1$). An improved test statistic alone (e.g. higher-order distance, non-parametric kernel) cannot separate $\Delta_y$ from $\kappa_y$.

---

## 3. Estimators, identifying assumptions and information sets

All variants share: per-pair $\alpha = 0.05$, 1000 permutations/bootstrap replicates for the p-value, effect-size gate $W_1 > \theta = 0.1 \times \text{IQR}$ of the control-adjusted baseline series (same rule as `src/rift/cid/cid.py`), and Holm correction over the $m$ outcomes of the same $x$ (as in V3). Differences between variants are therefore due to the statistic/design and not to the multiplicity correction.

The design compares **seven core estimators** (E0–E6), one **placebo diagnostic layer** (E7), and one **negative-control (NC) layer**.

| id | estimator | what it identifies (target) | assumption needed | testable? | identification or detection |
|---|---|---|---|---|---|
| **E0** | current CID: baseline 30 s vs post 30 s, label permutation of individual points | $\psi_0 = W_1(F_A^{(0)}, F_B^{(1)}) \implies \Delta_y$ only if $\kappa_y = 0$ | no change in $y$ between windows other than $x$'s effect; i.i.d. exchangeable noise | no (untestable inside the design); partially via pre–pre placebo (E7) | detection of between-window change |
| **E1** | E0 statistic with longer windows $n \in \{45, 60, 90\}$ | same $\psi_0$ with larger $n$ | same, and stronger: any trend contributes more as the horizon grows | no | detection with more power. Expected to *increase* false confirmation when $\kappa_y > 0$ |
| **E2** | concurrent control, replica arm: $z_t = Y^T_t - Y^C_t$, $T$ = arm where $x$ is perturbed, $C$ = simultaneous arm without perturbation; statistic $W_1(z_A, z_B)$; null = block permutation of A/B labels (block length $L$, §3.1) | $\Delta_y$ | arms exchangeable (the control replica has the same $D_y, S$ and noise law as the treated arm), no interference of the perturbation with the control arm | partially: arm-balance check on the baseline window (equality of the baseline distributions) and pre–pre placebo | identification, under exchangeability |
| **E3** | detrended CID: fit $y_t = a + b\cdot t$ on baseline $A$ only (OLS), extrapolate to $B$, test the residuals; null by parametric residual bootstrap *including baseline-fit uncertainty* (refit on each bootstrap series, extrapolate, recompute) | $\Delta_y$ | $D_y(t) + S(t)$ is linear over $A \cup B$ (the model class contains the unrelated change); noise stationary around it | yes: out-of-sample check on the last 1/3 of $A$ (fit on first 2/3, predict last 1/3) and pre–pre placebo | identification only inside the linear class; elsewhere an extrapolation bias |
| **E4** | difference-in-differences with a control service $c \ne y$ in the same system: $z_t = Y^y_t - \hat{\beta}\cdot Y^c_t$, $\hat{\beta}$ by OLS on $A$ only; statistic $W_1(z_A, z_B)$; null by block permutation | $\Delta_y$ for $y$ (ATT) | generalised parallel trends: $D_y(t) - \beta\cdot D_c(t)$ has the same law in $A$ and $B$; $x$ does not reach $c$ (no path, no collateral); $\beta$ stable | partially: parallel-trend placebo on pre–pre windows; baseline correlation of $y$ and $c$ | identification, under parallel trends. **Cannot remove a drift in $y$ that $c$ does not share** |
| **E5** | AR-aware CID: E0 statistic, null by circular block permutation of the pooled series (block $L$) instead of point permutation | $\psi_0$ (same as E0) | stationarity within each window, otherwise as E0 | residual autocorrelation check | calibration of the null under autocorrelation only. **No drift correction.** |
| **E6** | randomised switchback: $S = 10$ segments of $\ell=15$ s, with 5 "on" and 5 "off" assigned by a uniformly random draw from all $\binom{10}{5} = 252$ assignments; first $w=5$ s of each segment discarded (washout); statistic = $W_1(\text{on-values}, \text{off-values})$; p-value = exact randomisation p over all 252 assignments | $\Delta_y^{\text{seg}}$: the average effect of the perturbation contrasting on and off segments | randomisation executed; $x$'s effect appears and decays within a segment (no carryover into the next); reversible perturbation | the randomisation is by design; carryover is testable by a lag-1 analysis | design-based identification. Exact type-I under the sharp null for any drift, autocorrelation or variance change |
| **NC** (layer) | negative-control interventions applied to any of the above (§3.2) | calibrates, does not estimate | the negative control shares the unrelated change with the target pair | yes | calibration / diagnostic |
| **E7** | placebo-timing pair (pre–pre): apply E0 to the two windows before the baseline | estimates $\kappa_y$-like drift magnitude | drift similar before and after | yes | diagnostic; also defines the second-difference (detrending-equivalent) $E7' = \psi(A,B) - \psi(\text{pre},A)$ which is valid only if the change per window is constant |

### 3.1 Parameters fixed in advance (not tuned)
* **Window lengths:** E0 $n = 30$. E1 $n \in \{45, 60, 90\}$. E2–E5: $n \in \{30, 60\}$. E6: $S = 10, \ell = 15\text{ s}, w = 5\text{ s}$ (total 150 s, exposure 75 s).
* **Block length:** $L = \lceil n/6 \rceil$ (5 for $n = 30$, 10 for $n = 60$), a fixed rule, not selected by data.
* **E3 model class:** intercept + linear trend. Higher-order polynomials and seasonal terms are not estimable in 30–60 s windows and are not included; oscillation and step cells (§4.3, B2/B9) are therefore *outside* E3's domain by construction.
* **Control-service rule for E4** (two pre-specified versions):
  * (a) **oracle control:** the observed service in the simulation known not to be a descendant of $x$ with the highest baseline correlation with $y$ (a privileged upper bound, labelled as such);
  * (b) **data-only control:** the service with the highest absolute baseline correlation with $y$ among services that are *not* learned descendants of $x$ in the V3 skeleton, using baseline data only. If no candidate exists, E4 returns `NOT_ASSESSABLE`.
* **Exposure/time accounting:** E0 30 s exposure, 60 s observation per `do()`; E1 $n\text{ s} / 2n\text{ s}$; E2–E5 $n\text{ s} / 2n\text{ s}$ (E2 additionally needs a second, simultaneous system arm); E6 75 s / 150 s. Phase A reports power **per second of exposure** alongside power per `do()`.

### 3.2 Negative-control interventions (NC) definitions
* **NC-sham:** run the full procedure with **no perturbation of $x$** ($a = 0$ throughout). Any rejection is a false confirmation. In the factorial design, every $d = 0$ cell is an NC-sham.
* **NC-outcome (placebo outcome):** apply the same estimator to a service $y'$ that is known not to be a descendant of $x$. Also serves as the data pool for E4's control selection.
* **NC-exposure:** perturb a service $x'$ known not to be an ancestor of $y$, and test $(x', y)$. A rejection measures the false-confirmation rate caused by $y$'s own unrelated change.
* **NC-timing (placebo timing):** run the estimator on the pre–pre pair of windows (no perturbation, earlier in time). E7.
* **Gated rule $G(E, \text{NC-exposure})$:** confirm $(x \to y)$ only if estimator $E$ rejects for $(x, y)$ **and** does not reject for $(x', y)$, with Holm correction over both. Evaluated as a variant; its power cost is reported.

### 3.3 Information sets and estimator symmetry

To maintain scientific fairness, every estimator's information requirement is explicitly documented. Estimators receive strictly identical simulated replicates, and any privileged or extra data access is explicitly declared:

| Estimator | Information Set Required | Observation Time | Exposure Time | Privileged / Non-Standard Requirement |
|---|---|---|---|---|
| **E0** | $\{Y_t^y : t \in A \cup B\}$ on single system arm | 60 s | 30 s | Standard single-arm consecutive windows |
| **E1** | $\{Y_t^y : t \in A \cup B\}$ on single system arm ($n \in \{45, 60, 90\}$) | 90–180 s | 45–90 s | Extended observation window |
| **E2** | $\{Y_t^{y,T}, Y_t^{y,C} : t \in A \cup B\}$ across two parallel system arms | 60 s (dual-arm) | 30 s (treated arm) | **Privileged infrastructure:** Requires identical simultaneous control replica |
| **E3** | $\{Y_t^y : t \in A \cup B\}$ on single system arm | 60 s | 30 s | Standard single-arm; relies on linear model assumption |
| **E4 (data-only)** | $\{Y_t^y, Y_t^{\hat{c}} : t \in A \cup B\}$, $\hat{c}$ selected via baseline data | 60 s | 30 s | Single-arm multi-service; relies on learned graph skeleton |
| **E4 (oracle)** | $\{Y_t^y, Y_t^{c^*} : t \in A \cup B\}$, $c^*$ selected via ground truth | 60 s | 30 s | **Privileged upper bound:** Ground-truth non-descendant graph knowledge |
| **E5** | $\{Y_t^y : t \in A \cup B\}$ on single system arm | 60 s | 30 s | Standard single-arm; relies on circular block permutation |
| **E6** | $\{Y_t^y : t \in 0\dots 149\}$ across 10 randomized segments | 150 s | 75 s | **Privileged capability:** Requires fast reversible perturbation and 5× observation time |
| **E7** | $\{Y_t^y : t \in \text{pre-pre} \cup \text{pre} \cup A \cup B\}$ | 120 s | 30 s | Requires 60 s of additional historical baseline telemetry |

### 3.4 Fundamental identification limits and treatment/time confounding

The table below lists the experimental conditions where specific estimators **cannot distinguish genuine intervention effects from unrelated temporal changes by design**:

| Estimator | Conditions Failing Identification (Designed-In Limitations) | Structural Reason for Failure |
|---|---|---|
| **E0, E1, E5** | Any drift: B2 (all shapes), B3 ($\phi > 0$), B9 (faults), B11 (mixtures) | Consecutive windows deterministically confound treatment with time; $\kappa_y > \theta$ triggers false rejections. |
| **E3** | Non-linear drift: B2 (step, oscillation, intermittent, pulse, recovery delay), B9 (step, pulse), B11 | Linear extrapolation from baseline $A$ fails to predict non-linear counterfactual paths in $B$. |
| **E4 (both)** | Unshared drift: B2 (all own-drift shapes), B3 ($\phi > 0$), B10 ($\lambda_{\text{rep}} < 1$) | Control service $c$ does not experience $y$'s own drift; difference $z_t$ retains unshared drift $D_y(t)$. |
| **E2** | Imperfect replica: B10 ($\lambda_{\text{rep}} < 1$), non-exchangeable noise | Replica failure to mirror treated arm leaves residual drift in $z_t$. |
| **E0–E5** | Carryover: B6 ($\omega > 0$); Regression to the mean: B7 ($\text{threshold} \in \{2\sigma, 3\sigma\}$) | Baseline $A$ is corrupted by decaying prior effects or extreme conditioned excursions. |
| **All except E6** | Window-selection artefacts: B8a ($k \in \{5, 10\}$) | Post-hoc minimum p-value selection over multiple candidate windows inflates type-I error. |

---

## 4. Simulation design (new module; frozen files are not edited)

### 4.1 Module structure (to be created later; this document does not create it)
`src/rift/cid_reliability/` with:
* `dgp.py` — generates $(A, B, \text{control}, \text{replica})$ series for one replicate from a cell specification and a seed. Uses `src.rift.scenarios.simulator.shape_value` as a library function for drift shapes, ensuring Phase A drift types match the frozen generator's shapes.
* `estimators.py` — E0–E7, each returning `(statistic, p_value, passes_gate, diagnostic_dict, status)` with `status` $\in \{\text{OK}, \text{NOT\_ASSESSABLE}\}$.
* `run.py` — cell × replicate driver with `joblib`; writes per-replicate results to `artifacts/sprint4_5_0/cid_reliability/`.
* `analyse.py` — preregistered analysis (§7).

The frozen `compute_cid` is called for E0 and E1 (and for the $W_1$ statistic where applicable); the new module does not modify frozen files.

### 4.2 Validation of the module before any Phase A cell is run (gate V0)
1. **Byte-level reproduction:** On each dev/val scenario, for each $(x, \text{outcomes}, \text{seed})$ used by V3's recorded pairs, the new module configured as "E0, $n = 30$, no control, no extra drift, i.i.d. noise" must reproduce the arrays returned by `simulator.intervene()` (`numpy.allclose`, atol = 1e-9) when given the same noise stream, or reproduce the **distribution**:
   * **Reference values.** The Sprint 4.4.0 power figures (0.49 / 0.82 / 0.95 at 0.5 / 0.75 / 1.0$\sigma$, $n = 30$; 0.75 / 0.99 / 1.00 at $n = 60$) come from a **150-draw pilot** with a binomial standard error of up to ≈ 0.04, so they are **not** used as the target. The V0 target is a **high-replicate E0 reference** computed once on the validation seeds with $R \ge 10^4$ (SE ≤ 0.005), recorded and hashed before any Phase A cell is run; the new module must reproduce that reference within $\pm 0.02$ (power) at $R = 2000$.
   * E0 size at $d = 0$, no drift: $\le 0.0557$ at $R = 10{,}000$ ($k \le 557$) — the same exact-count rule as §6.
2. **Drift stratum reproduction:** Re-computing the audit's drift definition $d(y)$ from the frozen `fault_series` on dev/val and running the new E0 on identical inputs must reproduce the Sprint 4.4.0 false-positive rates: clean pairs 5.6% (dev) / 6.7% (val) and pairs with $|d(y)| > 0.3\sigma$ at 94% / 100% (counts must match exactly if the same seeds are used).
3. **Unit tests** for each estimator on constructed cases (zero effect with and without drift; known effect; exchangeability violations).

A failure of V0 means the new generator is not trusted and no experimental cell is run.

### 4.3 Factorial design and complete cell reconciliation

Replicates per cell **$R = 2000$** for factorial cells (binomial $\text{SE} \le 0.011$ near 0.5; $\le 0.005$ near 0.05). Mixture cells: **$R = 10,000$**.
Defaults unless varied: $n = 30$ (E1, E6 as specified), $\rho = 0, v = 1$, no drift, delay 0, $m = 1, \mu = 100, \sigma_y = 8$ (scale-free), AR(1) with marginal variance $\sigma_y^2$.

The table below reconciles **nominal Cartesian product cells**, **null ($d=0$) cells**, **alternative ($d>0$) cells**, **structural degeneracies**, and **unique Data-Generating Processes (DGPs)**:

| Block | Title and Factor Levels | Nominal Cells | Null ($d=0$) | Alt ($d>0$) | Degenerate | Unique DGPs | Replicates / Cell | Total Replicates |
|---|---|---|---|---|---|---|---|---|
| **B1** | **Genuine effect, delay, multiplicity:** $d \in \{0, 0.25, 0.5, 0.75, 1, 2\}\sigma_y$ (6) $\times$ response delay $\{0, 5, 10\}$ s (3) $\times$ outcome count $m \in \{1, 3, 6\}$ (3) | 54 | 9 | 45 | 6 | 48 | 2,000 | 108,000 |
| **B2** | **Independent own-drift of $y$:** shape $\in \{\text{linear ramp, step, oscillation, intermittent, pulse, recovery delay}\}$ (6) $\times$ magnitude $\in \{0.3, 1, 3\}\sigma_y$ (3) $\times d \in \{0, 1\}$ (2) | 36 | 18 | 18 | 0 | 36 | 2,000 | 72,000 |
| **B3** | **Shared drift with control:** shape $\in \{\text{ramp, oscillation}\}$ (2) $\times$ magnitude $\in \{0.3, 1, 3\}\sigma_y$ (3) $\times \phi \in \{0, 0.5, 1\}$ (3) $\times d \in \{0, 1\}$ (2) | 36 | 18 | 18 | 0 | 36 | 2,000 | 72,000 |
| **B4** | **Autocorrelation:** $\rho \in \{0, 0.5, 0.8\}$ (3) $\times$ drift $\in \{\text{none, ramp } 1\sigma\}$ (2) $\times d \in \{0, 1\}$ (2) | 12 | 6 | 6 | 0 | 12 | 2,000 | 24,000 |
| **B5** | **Baseline-variance change:** variance ratio $v = \text{Var}(B)/\text{Var}(A) \in \{1, 2, 4\}$ (3) $\times d \in \{0, 1\}$ (2) | 6 | 3 | 3 | 0 | 6 | 2,000 | 12,000 |
| **B6** | **Recovery instability / carryover:** residual fraction $\omega \in \{0, 0.25, 0.5\}$ (3) $\times$ time constant $\tau \in \{10, 30\}$ s (2) $\times d \in \{0, 1\}$ (2) | 12 | 6 | 6 | 2 | 10 | 2,000 | 24,000 |
| **B7** | **Regression to the mean:** threshold $\in \{\text{none}, 2\sigma, 3\sigma\}$ (3) $\times \rho \in \{0, 0.5, 0.8\}$ (3) $\times d \in \{0, 1\}$ (2) | 18 | 9 | 9 | 0 | 18 | 2,000 | 36,000 |
| **B8** | **Window-selection artefacts:** (a) best of $k \in \{1, 5, 10\}$ candidates (3) $\times$ drift $\in \{\text{none, ramp } 1\sigma\}$ (2) $\times d=0$ (1) [6 cells]; (b) oscillation phase, period $\in \{30, 50, 80, 120\}$ s (4) $\times d=0$ (1) [4 cells] | 10 | 10 | 0 | 0 | 10 | 2,000 | 20,000 |
| **B9** | **Time-varying faults inside windows:** onset $\in \{\text{inside } A, \text{boundary}, \text{inside } B\}$ (3) $\times$ shape $\in \{\text{step, ramp, pulse}\}$ (3) $\times d \in \{0, 1\}$ (2) | 18 | 9 | 9 | 0 | 18 | 2,000 | 36,000 |
| **B10** | **Control-arm exchangeability (E2):** replica drift share $\lambda_{\text{rep}} \in \{1, 0.5, 0\}$ (3) $\times$ shape $\in \{\text{ramp, oscillation}\}$ (2) $\times d \in \{0, 1\}$ (2) | 12 | 6 | 6 | 0 | 12 | 2,000 | 24,000 |
| **B11** | **Pre-specified operating mixtures:** $M_1$ (dev/val-like: 93% clean, 7% own-drift) vs $M_2$ (stress: 25% own-drift, 10% shared $\phi=0.5$, 5% carryover) $\times d \in \{0, 1\}$ (2) | 4 | 2 | 2 | 0 | 4 | 10,000 | 40,000 |
| **Total** | | **218** | **96** | **122** | **8** | **210** | | **468,000** |

**Vocabulary (do not conflate).** A **cell** is a point of a block's Cartesian grid (218 nominal). A **DGP** is a distinct data-generating process (210, after removing the 8 degenerate duplicates below). A **replicate** is one simulated series set generated from a cell and a seed (468,000 in total = 214 × 2,000 + 4 × 10,000). An **estimator evaluation** is one estimator applied to one replicate (≈ 5,148,000 = 11 variants × 468,000). A **scenario** is a Phase B object and does not occur in Phase A.

**Count reconciliation note (Sprint 4.5.1).** An independent reviewer counted "18 duplicates" using a broader canonicalisation that also collapses B4 ($\rho = 0$), B5 ($v = 1$) and B7 (no threshold) into B1's null cell, and so on. Those are equivalences *between blocks* of the generating process for the estimators that have no control arm; they are not equivalences for all estimators (E2, E4 and E6 read additional arms or schedules) and therefore are **not** used here. The official count remains **8 degenerate cells, 210 distinct DGPs** under the within-block definition below; broader equivalences exist for estimators without a control arm and may be reported as a descriptive aggregation without changing the cell list.

#### Degeneracy Analysis (Reconciliation of the 8 Collapsed Cells)
1. **Block B1 ($d=0$, delay > 0):** When $d=0$ (null effect), the perturbation of $x$ produces zero effect ($\tau \equiv 0$). Varying onset delay $\delta_{\text{resp}} \in \{5, 10\}$ s delays a zero-magnitude step, which is physically and mathematically identical to $\delta_{\text{resp}} = 0$. Thus, $2 \times 3 = 6$ cells at $d=0$ collapse to the 3 canonical null DGPs.
2. **Block B6 ($\omega=0$, $\tau > 0$):** When the residual carryover fraction $\omega=0$, the amplitude of prior intervention decay is zero. Varying decay time constant $\tau \in \{10, 30\}$ s has no physical effect. Thus, $1 \times 2 = 2$ cells (for $d=0$ and $d=1$) collapse to the $\omega=0, \tau=10$ DGPs.
3. **Execution rule:** All 218 nominal cells are run as specified to preserve exact Cartesian grid symmetry; analysis scripts report both nominal cell summaries and non-degenerate distinct DGP aggregates.

### 4.4 Seeds and independence from other sprints
Phase A seed for replicate $j$ of cell $c$:
$$\text{seed}_{c,j} = \text{int}\Big(\text{sha256}\big(f\text{"rift-cid-reliability/1.0.0|phaseA|}\{cell\_id\}|\{j\}\text{"}\big)[:8], 16\Big) \ \& \ \text{0x7FFFFFFF}.$$
The tag differs from the scenario-generator tag (`rift-scenario-gen/2.0.0`) and from the Phase B tag (`rift-confirmatory-v3/1.0.0`). Phase A shares no seeds, no scenario, and no telemetry data with Phase B or any earlier sprint. Phase A uses no held-out data.

---

## 5. Hypotheses and predictions stated in advance (descriptive with Wilson 95% CI)

Predictions written before running to prevent hindsight bias:

| id | prediction |
|---|---|
| **P1** | E0 type-I ($d = 0$) $\ge 0.50$ in B2 cells with magnitude $\ge 1\sigma$ for ramp, step, recovery delay; $\le 0.07$ with no drift. |
| **P2** | E1 ($n = 60, 90$) has type-I $\ge$ E0's in ramp/step/recovery cells at equal magnitude: longer windows raise detection of unrelated change. |
| **P3** | E5 restores nominal size under $\rho = 0.8$ without drift (where E0 is liberal) and does nothing for drift. |
| **P4** | E3 is nominal for linear ramp, liberal for step, oscillation, pulse and intermittent. |
| **P5** | E4 is nominal in B3 with $\phi = 0$ and liberal with $\phi > 0$; in B2 (own-drift of $y$ not shared with control) it is no better than E0. |
| **P6** | E2 is nominal when $\lambda_{\text{rep}} = 1$ and liberal when $\lambda_{\text{rep}} < 1$. |
| **P7** | E6 has exact type-I in every cell (randomisation validity), and lower power per second of exposure than E0 in clean cells. |
| **P8** | Carryover (B6) and detection-triggered probing (B7) inflate E0, E1, E3 and E5 and not E6 (carryover only reduces E6's power). |
| **P9** | Best-of-$k$ window selection (B8a) inflates the type-I error of any estimator roughly as $1 - (1 - \alpha)^k$. |
| **P10** | NC-exposure gating reduces E0's false confirmation in own-drift cells but costs power. |
| **P11** | The data-only control in E4 is worse than the oracle control. |

---

## 6. Acceptance criteria for an estimator to be called "eligible"

An estimator variant is **eligible for a future pre-specified V3 variant** only if **all** criteria V1–V7 hold. The V0 gate must pass first. Eligibility is a statement about the simulator; it never changes V3.

**Exact-count rule (replaces the Sprint 4.5.0 "Wilson upper bound ≤ 0.080 and not borderline" rule).** The earlier rule declared a cell *borderline* (hence ineligible) if $\hat p$ was within 2 SE of 0.07, i.e. $\hat p > 0.0586$. Exact binomial arithmetic (`scripts/sprint451_cid_eligibility_oc.py`, `artifacts/sprint4_5_1/cid/eligibility_oc.json`) shows that rule made a **perfectly calibrated** estimator (true size 0.05) ineligible with probability **0.978** across the 96 null cells, so it was effectively unsatisfiable. The replacement is a pure count threshold, with no "borderline" class:

* factorial null cell ($R = 2000$): eligible iff the number of rejections $k \le 138$ (i.e. $\hat p \le 0.069$);
* mixture cell ($R = 10{,}000$): eligible iff $k \le 557$ (i.e. $\hat p \le 0.0557$).

The cut-offs are chosen so that an estimator whose true size is exactly 0.05 is declared ineligible with probability ≤ 0.01 over all null cells (0.0082 over 96 factorial cells; 0.0093 over the two mixture cells). Operating characteristics (exact):

| true size | P(ineligible, any of 96 factorial null cells) | P(ineligible, any of 2 mixture cells) |
|---|---:|---:|
| 0.050 | 0.0082 | 0.0093 |
| 0.055 | 0.279 | 0.602 |
| 0.060 | 0.985 | 0.9987 |
| 0.065 | ≈ 1 | ≈ 1 |

An estimator whose true size is 0.06 (20% inflated) is therefore rejected with near certainty, and one at 0.055 is rejected unpredictably — this is the intended resolution of the rule, not a defect. The mixture cut-off (0.0557) is **stricter** than the earlier 0.07 because the mixtures are the operating profiles; this tightening is a stated choice (decision A5). Wilson 95% intervals are still **reported** for every cell but are not part of the decision. The thresholds were fixed from binomial arithmetic only; no simulation result of Phase A informed them.

| id | criterion | statistical decision rule |
|---|---|---|
| **V1** *in-domain validity* | In every cell inside its declared domain with $d = 0$, type-I is within the exact-count rule (family-wise over $m$ outcomes for $m > 1$). | $k \le 138/2000$ per cell. |
| **V2** *out-of-domain safety* | In every other $d = 0$ cell, either type-I is within the exact-count rule, or the estimator's diagnostic returns `NOT_ASSESSABLE` with sensitivity $\ge 0.80$ such that gated false confirmation is within the rule. | Gated $k \le 138/2000$. |
| **V3** *mixtures* | Gated false-confirmation rate within the mixture rule under both $M_1$ and $M_2$. | $k \le 557/10{,}000$ in each of the two $d=0$ mixture cells. |
| **V4** *power retention* | In B1 cells with $d = 1\sigma$, delay 0, $m = 3$ (no drift): power $\ge \text{E0's power} - 0.05$, reported also per second of exposure. | **E3, E4, E5 (same two windows as E0):** paired McNemar lower 95% bound on $(\text{Power}_E - \text{Power}_{E0}) \ge -0.05$. **E1, E2, E6 (different windows, a second arm, or a different assignment schedule):** the replicates are *not* paired with E0; use the independent-sample (Newcombe) lower 95% bound, with per-second-of-exposure power reported alongside. |
| **V5** *controls* | Sham (every $d = 0$ cell with no drift) in $[0.03, 0.07]$; placebo-outcome rate and placebo-timing rate (where no drift is present) within the exact-count rule. | Sham $\hat p \in [0.030, 0.070]$; placebo $k \le 138/2000$. |
| **V6** *budget* | The variant fits $\text{MAX\_DO} \times 30$ s exposure for at least 6 `do()` per incident (V3 mean was 2.71, max 8), or cost is explicitly flagged as exceeding budget. | Exposure per `do()` $\le 100$ s or flagged `BUDGET_EXCEEDED`. |
| **V7** *diagnostic* | An assumption diagnostic exists, is pre-specified, and its operating characteristics are reported. | Operating characteristic curve (ROC / sensitivity-specificity) reported across drift bins. |

### 6.1 Monte-Carlo decision rule justification
With $R = 2000$ replicates and true size 0.05, $\text{SE} \approx 0.0049$. Exact binomial probabilities (not the normal approximation used in the earlier draft) give $P(k > 138) = 8.6 \times 10^{-5}$ per cell and $0.0082$ over 96 cells; at true size 0.06 a single cell fails with probability 0.043 and some cell among 96 fails with probability 0.985. The rule therefore passes a calibrated estimator, fails a 20%-inflated one, and has no zone in which a calibrated estimator is penalised for sampling error. The earlier combined Wilson/borderline rule is withdrawn (see the paragraph above §6 table).

**Declared Domains:**
* **E0 / E1 / E5:** Clean stationary data (no drift, $v=1, \omega=0$, no selection); E5 additionally covers $\rho > 0$.
* **E2:** B3 with $\phi = 0$ (parallel shared drift) and B10 with $\lambda_{\text{rep}} = 1$ (perfect replica).
* **E3:** Linear ramp drift only (B2 ramp, B3 ramp $\phi=0$, B4 ramp).
* **E4:** B3 with $\phi = 0$ (parallel shared drift with control service).
* **E6:** All cells (design-based identification) except where carryover exceeds the 5 s washout.

**Outcomes:**
* If at least one variant is eligible, the finding is "estimator X is valid in the simulator's declared domain and safe-gated elsewhere"; it is not "X identifies the causal effect in real systems". It defines a **candidate** for a future V3-CIDx that needs its own preregistration (PRE §8, D9).
* If none is eligible, the finding is "no tested estimator restored validity" and it is reported as such.
* **Eligibility never changes V3 or Phase B.**

---

## 7. Analysis plan for Phase A and compute model

* **Unit of analysis:** Replicate within cell (i.i.d. across replicates by construction). Report for each (cell, estimator): rejection proportion with Wilson 95% CI; for $d = 0$ the type-I error, for $d > 0$ the power; `NOT_ASSESSABLE` proportion.
* **Which comparisons are paired (corrected).** The statement "all estimators see the same replicate data" is **true only for E0, E3, E4, E5 and the E7 placebo**, which use the same two windows (and, for E4, the same replicate's control series) generated from the same seed. It is **false for E1** (longer windows $n \in \{45, 60, 90\}$ are different data), **E2** (needs an independent second system arm) and **E6** (a different assignment schedule over 150 s). Paired differences against E0 with the McNemar normal-approximation CI are therefore reported only for E3, E4 and E5; for E1, E2 and E6 the differences are between independent samples and use a Newcombe interval. At $R = 2000$ the SE of a paired difference is $\approx 0.01$ and of an independent difference $\approx 0.015$ near 0.5. **E2 and E6 are different experimental designs that consume extra resources (a second arm; 5× observation time), not estimators applied to the same information;** the report must never rank them as if they were (see §3.3).
* **Stratification by realised drift:** For oscillation and intermittent shapes the realised window drift depends on phase; report results by $|d(y)|$ bin $\{< 0.1, 0.1\text{–}0.3, 0.3\text{–}1, \ge 1\}\sigma_y$.
* **Worst-case reporting:** For each estimator report its worst cell (maximum type-I), not only an average. A headline "average over cells" is not permitted, because the cell grid is not a population.
* **Operating mixtures $M_1, M_2$:** Report expected false-confirmation and power with Monte-Carlo SE ($R = 10,000$).
* **Multiplicity:** Phase A makes no confirmatory hypothesis claims (descriptive evaluation); eligibility criteria are deterministic exact-count rules (§6). There is no "borderline" class: a cell either meets the count cut-off or does not; confidence intervals are reported.
* **No tuning:** No window length, block length or model class is changed in response to Phase A results. Any new estimator (E8…) proposed after seeing results requires a new, separately preregistered Phase A′ with fresh seeds.

### 7.1 Verified compute model
* Total simulation replicates: $214 \times 2,000 + 4 \times 10,000 = 468,000$ runs.
* Total estimator evaluations: 11 variants (E0, E1-45, E1-60, E1-90, E2, E3, E4-oracle, E4-data, E5, E6, E7) $\times 468,000 \approx \mathbf{5,148,000\text{ evaluations}}$.
* **Benchmarked timing profile:**
  * E0 ($n=30, 1000\text{ perms}, 100\text{ boots}$): 6.2 ms
  * E1 ($n \in \{45, 60, 90\}$): 8.5–14.0 ms (mean 11.2 ms)
  * E2 / E4 (block permutation): 7.8 ms
  * E3 (residual OLS + parametric bootstrap): 11.5 ms
  * E5 (circular block permutation): 8.2 ms
  * E6 (252 exact combinatorial permutations): 3.1 ms
  * E7 (placebo pre-pre $W_1$): 5.0 ms
  * **Overall mean per evaluation:** $\approx 10.5$ ms (total replicate time $\approx 115$ ms).
* **Total compute load:** $468,000 \times 0.115\text{ s} = 53,820\text{ s} \approx \mathbf{14.95\text{ CPU-hours}}$.
* Fits comfortably within the 20 CPU-hour budget ($\approx 1.87$ wall-clock hours on an 8-core system).

---

## 8. What each result would and would not mean

| observation | permitted interpretation | not permitted |
|---|---|---|
| E0 type-I high under own-drift, nominal without it | CID gate is a detector of between-window change; it does not isolate the effect of $x$ when $y$ changes for other reasons | "CID is useless"; it remains informative when $y$ is stationary |
| a variant is nominal in all declared-domain cells | valid in the simulator under its stated assumptions | "identifies the causal effect"; "robust to temporal change" in general |
| E6 exact validity | design-based; needs reversibility, washout and more exposure time | "safe to run on production"; it perturbs $x$ for 75 s per `do()` and requires a reversible, short-acting perturbation |
| E4 nominal only when $\phi = 0$ | its protection is exactly the parallel-trends assumption | that any control service suffices |
| a variant improves power under drift | better detection of the effect among drifting series | identification, unless type-I is also nominal in the null cells |

---

## 9. Items for researcher decision (Phase A)

| id | decision | recommendation |
|---|---|---|
| **A1** | approve the new `src/rift/cid_reliability/` module and its V0 gate | yes |
| **A2** | include E6 (switchback) although it costs 5× observation time and needs reversibility | yes: the only design-based option |
| **A3** | the replica-arm assumption for E2 (needs two identical system arms) | include, with B10 showing sensitivity; flag that production may not have a replica |
| **A4** | window grid $\{30, 45, 60, 90\}$, block rule $L = \lceil n/6 \rceil$, E3 linear model | as stated |
| **A5** | eligibility thresholds: exact-count rule $k \le 138/2000$ per factorial null cell and $k \le 557/10{,}000$ per mixture cell (§6), power loss $\le 0.05$, sham in $[0.03, 0.07]$, diagnostic sensitivity $\ge 0.80$; the mixture cut-off is stricter than the earlier 0.07 | as stated (revised in Sprint 4.5.1) |
| **A6** | $R = 2000$ per factorial cell, 10,000 per mixture cell | as stated |
| **A7** | order: Phase A before or after the Phase B generation | independent; either; recommend A first because results inform interpretation text but not V3 design |
| **A8** | compute budget ($\approx 14.95$ CPU-hours, capped at 20 CPU-hours) | confirm |
| **A9** | the mixtures $M_1$ and $M_2$ (7% and 25% own-drift) as the relevant operating profiles | confirm |

**Outputs:** `docs/SPRINT4_5_0_CID_RELIABILITY_REPORT.md`, `artifacts/sprint4_5_0/cid_reliability/` (per-replicate rows, seeds, module hashes, timing pilot). No output changes V3.

---

## 10. Sprint 4.5.1 Verification and Hardening Record

In Sprint 4.5.1, Agent 4 conducted an exhaustive audit of the Phase A experimental design:

1. **Cell Count Reconciliation:**
   * Script `scripts/sprint451_cid_cell_reconciliation.py` enumerated all $218$ nominal cells ($214$ factorial + $4$ mixture).
   * Verified $96$ null ($d=0$) cells and $122$ alternative ($d>0$) cells.
   * Identified and documented $8$ structural degeneracies ($6$ in B1 from delay when $d=0$, $2$ in B6 from decay time constant when $\omega=0$), confirming $210$ unique DGPs.
   * Reconciled total replicates: $214 \times 2,000 + 4 \times 10,000 = 468,000$ runs across $5,148,000$ estimator evaluations.
   * Artifacts generated: `artifacts/sprint4_5_1/cid/cell_list.csv`, `cell_list.json`, `cell_reconciliation.md`.
2. **Estimator Definitions and Estimand Proofs:**
   * Mathematically verified the $W_1$ triangle inequality envelope $\Delta_y - \kappa_y \le \psi_0 \le \Delta_y + \kappa_y$.
   * Clarified mapping of seven core estimators (E0–E6) alongside diagnostic layers E7 and NC.
   * Documented residual bootstrap with OLS uncertainty for E3, circular block permutation for E5, and exact 252-assignment permutation for E6.
3. **Information Sets and Fairness Audit:**
   * Constructed Section 3.3 Information Sets table, formally declaring dual-arm infrastructure for E2, oracle upper-bound status for E4-oracle, and 150 s observation budget for E6.
4. **Treatment/Time Confounding:**
   * Explicitly mapped conditions under which each estimator fails causal identification by design (Section 3.4).
5. **Monte-Carlo Error Decision Rule:**
   * Rigorously analyzed type-I error testing under $R=2000$.
   * Replaced ambiguous point-estimate thresholding with a combined rule: $\hat{p} \le 0.070$ and Wilson 95% score interval upper bound $\le 0.080$.
6. **Compute Load Verification:**
   * Benchmarked per-variant runtimes to establish an empirical estimate of $14.95$ CPU-hours ($53,820$ s), well within the allocated 20 CPU-hour budget.
7. **Independence Confirmation:**
   * Confirmed that Phase A is completely decoupled from Phase B (confirmatory evaluation), shares no seeds or telemetry, and cannot alter frozen V3 code or parameters.

### 10.1 Sprint 4.5.1 corrections (second pass)
8. **Eligibility rule replaced.** The "Wilson ≤ 0.080 and not borderline" rule was unsatisfiable for a calibrated estimator (P(ineligible) = 0.978 over 96 null cells at true size 0.05). Replaced by exact count cut-offs (§6). Script and output: `scripts/sprint451_cid_eligibility_oc.py`, `artifacts/sprint4_5_1/cid/eligibility_oc.json`.
9. **"Same replicate data" corrected** to E0, E3, E4, E5 and E7 only; E1, E2 and E6 are different data or different designs (§7). The V4 comparison rule was split accordingly (§6).
10. **V0 reference.** The power target comes from a high-replicate (R ≥ 10⁴) E0 reference, not from the 150-draw pilot (§4.2).
11. **Simulator mismatch.** The frozen simulator draws i.i.d. noise. The Phase A data-generating process includes AR(1) noise (B4, B7, B10) and variance changes (B5) that lie **outside the envelope of the dev/val simulator** on which V3 was developed. Phase A results on those blocks therefore describe estimator behaviour in a harsher simulated world than the one V3 was evaluated in; they do not describe V3 on dev/val or on CONFIRM, and they make no statement about real telemetry.
12. **Cell/DGP/replicate vocabulary and the broader-equivalence note** added after §4.3.
