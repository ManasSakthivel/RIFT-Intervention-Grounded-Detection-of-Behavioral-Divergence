# Sprint 4.5.1 — CID Reliability Experiment Factorial Cell Reconciliation

## 1. Executive Summary

- **Nominal Factorial Cells:** 214
- **Nominal Mixture Cells:** 4
- **Total Nominal Cells:** 218 (matches claimed 218 = 214 factorial + 4 mixture exactly)
- **Null ($d=0$) Cells:** 96 (nominal) / 88 (distinct DGPs)
- **Alternative ($d>0$) Cells:** 122
- **Degenerate Factorial Cells:** 8 (structural redundancies in full Cartesian product)
- **Unique Data-Generating Processes (DGPs):** 210
- **Total Sim Replicates:** 468,000 (214 × 2,000 + 4 × 10,000)

## 2. Block-by-Block Reconciliation Table

| Block | Title | Nominal Cells | Null ($d=0$) | Alt ($d>0$) | Degenerate | Unique DGPs | Replicates/Cell | Total Replicates |
|---|---|---|---|---|---|---|---|---|
| **B1** | Genuine effect, delay, multiplicity | 54 | 9 | 45 | 6 | 48 | 2,000 | 108,000 |
| **B2** | Independent own-drift of y | 36 | 18 | 18 | 0 | 36 | 2,000 | 72,000 |
| **B3** | Shared drift with control | 36 | 18 | 18 | 0 | 36 | 2,000 | 72,000 |
| **B4** | Autocorrelation | 12 | 6 | 6 | 0 | 12 | 2,000 | 24,000 |
| **B5** | Baseline-variance change | 6 | 3 | 3 | 0 | 6 | 2,000 | 12,000 |
| **B6** | Recovery instability / carryover | 12 | 6 | 6 | 2 | 10 | 2,000 | 24,000 |
| **B7** | Regression to the mean | 18 | 9 | 9 | 0 | 18 | 2,000 | 36,000 |
| **B8** | Window-selection artefacts (a: best-of-k) | 10 | 10 | 0 | 0 | 10 | 2,000 | 20,000 |
| **B9** | Time-varying faults inside windows | 18 | 9 | 9 | 0 | 18 | 2,000 | 36,000 |
| **B10** | Control-arm exchangeability (E2) | 12 | 6 | 6 | 0 | 12 | 2,000 | 24,000 |
| **B11** | Pre-specified operating mixtures | 4 | 2 | 2 | 0 | 4 | 10,000 | 40,000 |
| **Total** | | **218** | **96** | **122** | **8** | **210** | | **468,000** |

## 3. Detailed Degeneracy Analysis

In a full factorial design crossing parameter grids, certain parameter combinations yield mathematically identical DGPs:

1. **Block B1 (Delay at $d=0$):** Crossing $d \in \{0, 0.25, 0.5, 0.75, 1, 2\}$ with response delay $\in \{0, 5, 10\}$ s and $m \in \{1, 3, 6\}$ yields $6 \times 3 \times 3 = 54$ nominal cells. For $d=0$, perturbing $x$ produces zero intervention effect $\tau(t - t_0) \equiv 0$. The onset delay $\delta_{resp} \in \{5, 10\}$ s delays a zero-magnitude step, which is physically identical to $\delta_{resp}=0$. Thus, 6 cells ($2 \text{ delays} \times 3 \text{ multiplicity levels}$ at $d=0$) are duplicate representations of the 3 canonical null DGPs. Unique DGPs in B1 = 48.

2. **Block B6 (Decay Time Constant at $\omega=0$):** Crossing residual carryover fraction $\omega \in \{0, 0.25, 0.5\}$ with decay time constant $\tau \in \{10, 30\}$ s and $d \in \{0, 1\}$ yields $3 \times 2 \times 2 = 12$ nominal cells. When $\omega = 0$ (no residual carryover), the decay time constant $\tau$ is multiplied by zero residual amplitude, making $\tau=10$ and $\tau=30$ identical DGPs. Thus, 2 cells (at $\omega=0, \tau=30$ for $d=0, 1$) are duplicate representations of the $\omega=0, \tau=10$ DGPs. Unique DGPs in B6 = 10.

3. **Non-Degenerate Blocks (B2, B3, B4, B5, B7, B8, B9, B10, B11):** All parameter combinations in these blocks represent distinct physical DGPs:
   - B2: All 6 shapes have distinct temporal trajectories; magnitude $\in \{0.3, 1, 3\}$ alters SNR.
   - B3: $\phi \in \{0, 0.5, 1\}$ spans parallel, partially differential, and fully differential shared drift.
   - B4: $\rho \in \{0, 0.5, 0.8\}$ alters serial covariance even with no drift.
   - B5: Variance ratio $v \in \{1, 2, 4\}$ alters post-window dispersion.
   - B7: Threshold triggering selects conditional excursion baselines across $\rho$.
   - B8: Best-of-$k$ selects extreme order statistics ($k \in \{1, 5, 10\}$); oscillation period spans $30$ to $120$ s.
   - B9: Fault onset location ({inside A, at boundary, inside B}) interacts with window boundary.
   - B10: Replica drift share $\lambda_{rep} \in \{1, 0.5, 0\}$ evaluates exchangeability degradation.
   - B11: Empirical dev/val mixture vs severe stress mixture.

## 4. Replicate and Compute Verification

- **Factorial cells (B1–B10):** 214 cells × 2,000 replicates = 428,000 simulation runs.
- **Mixture cells (B11):** 4 cells × 10,000 replicates = 40,000 simulation runs.
- **Total Simulation Replicates:** 468,000 runs.
- **Estimator Evaluations:** ~11 evaluations per replicate (E0, E1-45, E1-60, E1-90, E2, E3, E4-oracle, E4-data, E5, E6, E7) = **5,148,000 total estimator evaluations**.
- **Compute Budget Model:**
  - E0 (n=30, 1000 perms, 100 boots): 6.2 ms
  - E1 (n=45/60/90): 8.5–14.0 ms
  - E2 / E4 (block perm): 7.8 ms
  - E3 (residual OLS + parametric bootstrap): 11.5 ms
  - E5 (circular block perm): 8.2 ms
  - E6 (252 exact combinatorial perms): 3.1 ms
  - E7 (placebo pre-pre W1): 5.0 ms
  - **Weighted mean execution time per replicate:** ~115 ms across all 11 estimators (or ~10.5 ms per estimator evaluation).
  - **Total CPU time:** 468,000 × 0.115 s = 53,820 s = **14.95 CPU-hours** (well within 20 CPU-hour budget; ~1.87 wall-clock hours on 8 cores).
