# Sprint 4.5.1 - Power Analysis and Verification

## 1. Summary of Methodology

### A. Normal Approximation Power Calculation
Power was reconstructed using the cluster-inflated normal approximation for a one-sided paired t-test:
$$N = \text{DEFF} \cdot \left( \frac{(z_{1-\alpha} + z_{1-\beta}) \cdot \text{SD}}{\delta} \right)^2$$
Where:
- $\alpha = 0.025$ (one-sided)
- $z_{1-\alpha} = 1.959964$
- $SD = 0.96916$ (empirical V3 utility standard deviation from dev/val)
- $\delta$ is the target effect size ($0.10$).

### B. McNemar Power (H3 and H4)
Reconstructed using the normal approximation on discordant counts:
$$z = 2.394 \quad (\text{for } \alpha = 0.00833 \text{ step-1 Holm})$$
$$\text{Power} = 1 - \Phi\left( \frac{z - (2p_+ - 1)\sqrt{n_d}}{2\sqrt{p_+(1-p_+)}} \right)$$
Where:
- $n_d = N \cdot p_{disc}$ is the expected number of discordant pairs.
- $p_{disc}$ is the proportion of discordant pairs in dev/val ($29/99$ for H4, $61/252$ for H3).
- $p_+$ is the proportion of discordant pairs favoring V3 ($0.655$ for H4, $0.754$ for H3).
- To model clustering for H4, we adjust $n_d$ by a design effect of $2.0$ ($n_d \leftarrow n_d / 2.0$), representing an effective sample size halving.

### C. Monte Carlo Simulation with Gaussian Copula
To evaluate test size and power beyond the normal approximation under a skewed discrete bounded utility, we developed a simulation using a Gaussian Copula:
1. **Group Size Structure:** Evaluated standard unequal group sizes ($K \approx 250$, mean size 8, max 25) and worse-case larger groups ($K \approx 100$, mean size 20, max 50).
2. **Latent Correlation Calibration:** Pre-calibrated the latent normal correlation $r$ such that the actual simulated group-level Pearson ICC and resulting design effect match target DEFF values ($1.5$, $2.0$, $3.0$) exactly.
3. **Quota Prevalence:** Programmatically enforced exactly $40\%$ expected prevalence of `ATTRIBUTE` scenarios using a weighted empirical CDF of dev/val scenarios.
4. **Missing Outcomes:** Simulated $2\%$ and $5\%$ missing completely at random (MCAR, mapped to abstention, utility $= 0$) and worst-case missingness (mapped to unsafe, utility $= -2.0$).
5. **Replication and Bootstrap:** For each condition, simulated $R = 1000$ independent confirmatory datasets and calculated one-sided p-values using a fully vectorized implementation of the cluster bootstrap-t test with $B = 199$ resamples.

---

## 2. Key Findings and Verification

1. **H1 Power Verification:** Re-calculated normal approximation power at $N=2000$, $\delta=0.10$ and $SD=0.96916$:
   - $\text{DEFF} = 1.5 \implies \text{Power} = 0.9647$ (table quotes $0.97$).
   - $\text{DEFF} = 2.0 \implies \text{Power} = 0.9037$ (table quotes $0.90$).
   - $\text{DEFF} = 3.0 \implies \text{Power} = 0.7593$ (table quotes $0.76$).
   - At $N=800$ and $\text{DEFF}=2.0$, power is indeed $0.5413$ ($54\%$, making N=800 highly underpowered).
   
2. **H4 Power Verification:** The power of $0.85$ (shrink=1.0) and $0.24$ (shrink=0.5) corresponds to an effective sample size of $N_{\text{attr, eff}} = 400$, which is exactly $N_{\text{attr}} = 800$ with a design effect of $2.0$.
   
3. **Monte Carlo Robustness:**
   - At $\text{shift} = 0.0$ (null hypothesis), the rejection rate is controlled at or below the nominal $0.025$ level (test size is robust to negative skewness and clustering).
   - MC power for $\text{shift} = 0.10$ under standard group sizes and $\text{DEFF}=2.0$ is approximately $0.89$, closely matching the normal approximation of $0.90$.
   - **Missingness Impact:** $2\%$ and $5\%$ MCAR missingness (mapped to abstention) slightly shrinks the SD and shifts the utility towards 0, resulting in a minor power loss ($0.88$ for $2\%$ and $0.85$ for $5\%$, at shift=0.10, DEFF=2.0).
   - **Worst-case Missingness Impact:** $2\%$ and $5\%$ worst-case missingness (mapped to unsafe, utility $=-2.0$) substantially inflates the SD and pulls the mean downward, severely reducing power ($0.84$ for $2\%$ and $0.75$ for $5\%$ at shift=0.10, DEFF=2.0).
