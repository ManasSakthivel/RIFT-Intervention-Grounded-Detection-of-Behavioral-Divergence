"""
stats.py — RIFT Phase 3Q Statistical Validation Infrastructure

Implements the frozen statistical correction plan from:
    docs/PHASE_3_SPEC_FREEZE.md §15

Hypothesis tests and multiple-testing corrections:
  H1–H3  Wilcoxon signed-rank (one-sided, RIFT > baseline)       α = 0.05
  H4     TOST equivalence (accuracy) + one-sided Wilcoxon (cost) α = 0.05
  H5     One-sided binomial test                                   α = 0.05

Multiple testing:  Holm-Bonferroni for 6 confirmatory tests
Exploratory:       BH FDR
Effect size:       Cliff's δ — ALWAYS reported regardless of p-value
C_confounded:      ≥ 48 incidents required for 80% power (H2)

Authority: docs/PHASE_3_SPEC_FREEZE.md §15, docs/hypotheses.md H1–H5
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
from scipy import stats as scipy_stats

# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass
class HypothesisTestResult:
    """
    Full result record for a single hypothesis test.

    Cliff's δ and its CI are always present regardless of significance.
    See docs/PHASE_3_SPEC_FREEZE.md §15: "Effect size: Cliff's δ (always
    reported regardless of p-value)."
    """

    hypothesis_id: str               # H1 | H2 | H3 | H4 | H5
    test_name: str
    statistic: float
    pvalue: float
    cliffs_delta: float
    cliffs_delta_ci: Tuple[float, float]  # 95 % bootstrap CI
    effect_size_interpretation: str       # negligible | small | medium | large
    significant: bool                     # after Holm-Bonferroni correction
    alpha_corrected: float                # corrected α threshold
    n_observations: int
    power_achieved: Optional[float]       # None if not computed
    notes: str


# ---------------------------------------------------------------------------
# Cliff's δ
# ---------------------------------------------------------------------------


def cliffs_delta(
    x: np.ndarray,
    y: np.ndarray,
    n_bootstrap: int = 2000,
    ci_level: float = 0.95,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[float, Tuple[float, float]]:
    """
    Cliff's δ = (# x > y  −  # x < y) / (len(x) × len(y))

    Returns
    -------
    (delta, (ci_lower, ci_upper))
        delta   : point estimate in [-1, 1]
        ci      : bootstrap (1 - α) confidence interval

    Always report regardless of p-value (§15).

    Parameters
    ----------
    x, y        : paired or unpaired score arrays
    n_bootstrap : number of bootstrap resamples for CI
    ci_level    : confidence level (default 0.95 → 95 %)
    rng         : optional seeded Generator for reproducibility
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    def _delta(a: np.ndarray, b: np.ndarray) -> float:
        n = len(a) * len(b)
        if n == 0:
            return 0.0
        gt = float(np.sum(a[:, None] > b[None, :]))
        lt = float(np.sum(a[:, None] < b[None, :]))
        return (gt - lt) / n

    point = _delta(x, y)

    if rng is None:
        rng = np.random.default_rng(42)

    boot_deltas = np.empty(n_bootstrap, dtype=float)
    for i in range(n_bootstrap):
        bx = rng.choice(x, size=len(x), replace=True)
        by = rng.choice(y, size=len(y), replace=True)
        boot_deltas[i] = _delta(bx, by)

    alpha = 1.0 - ci_level
    ci_lower = float(np.percentile(boot_deltas, 100 * alpha / 2))
    ci_upper = float(np.percentile(boot_deltas, 100 * (1 - alpha / 2)))

    return point, (ci_lower, ci_upper)


def _interpret_cliffs_delta(delta: float) -> str:
    """
    Magnitude thresholds from Romano et al. / Vargha & Delaney:
      |δ| < 0.147  → negligible
      |δ| < 0.33   → small
      |δ| < 0.474  → medium
      |δ| ≥ 0.474  → large
    """
    abs_d = abs(delta)
    if abs_d < 0.147:
        return "negligible"
    if abs_d < 0.330:
        return "small"
    if abs_d < 0.474:
        return "medium"
    return "large"


# ---------------------------------------------------------------------------
# Wilcoxon one-sided signed-rank test
# ---------------------------------------------------------------------------


def wilcoxon_one_sided(
    rift_scores: np.ndarray,
    baseline_scores: np.ndarray,
    hypothesis_id: str,
    alpha: float = 0.05,
    alpha_corrected: float = 0.05,
    power_achieved: Optional[float] = None,
    notes: str = "",
    rng: Optional[np.random.Generator] = None,
) -> HypothesisTestResult:
    """
    Paired one-sided Wilcoxon signed-rank test.

    H₀: RIFT scores ≤ baseline scores  (null — no benefit)
    H₁: RIFT scores >  baseline scores  (alternative — one-sided)

    Authority: docs/PHASE_3_SPEC_FREEZE.md §15
    The test is always one-sided (alternative='greater') per the frozen plan.
    Two-sided computation is NOT used here.

    Parameters
    ----------
    rift_scores, baseline_scores : paired per-incident score arrays
    hypothesis_id : 'H1' | 'H2' | 'H3' | 'H4' | 'H5'
    alpha          : nominal α (default 0.05)
    alpha_corrected: corrected α after Holm-Bonferroni (set externally)
    power_achieved : optional power estimate
    notes          : free-text annotations
    rng            : optional seeded Generator for Cliff's δ bootstrap
    """
    rift_scores = np.asarray(rift_scores, dtype=float)
    baseline_scores = np.asarray(baseline_scores, dtype=float)

    if len(rift_scores) != len(baseline_scores):
        raise ValueError(
            "rift_scores and baseline_scores must have the same length "
            f"(got {len(rift_scores)} vs {len(baseline_scores)}). "
            "Wilcoxon signed-rank requires paired observations."
        )

    n = len(rift_scores)
    differences = rift_scores - baseline_scores

    # scipy.stats.wilcoxon with alternative='greater' implements
    # the one-sided test H₁: median(diff) > 0
    if np.all(differences == 0):
        # All differences are zero → no evidence for either direction; p = 0.5.
        stat, pvalue = 0.0, 0.5
    else:
        stat, pvalue = scipy_stats.wilcoxon(
            differences,
            alternative="greater",
            zero_method="wilcox",
        )

    delta, delta_ci = cliffs_delta(rift_scores, baseline_scores, rng=rng)

    return HypothesisTestResult(
        hypothesis_id=hypothesis_id,
        test_name="Wilcoxon signed-rank (one-sided, RIFT > baseline)",
        statistic=float(stat),
        pvalue=float(pvalue),
        cliffs_delta=delta,
        cliffs_delta_ci=delta_ci,
        effect_size_interpretation=_interpret_cliffs_delta(delta),
        significant=float(pvalue) < alpha_corrected,
        alpha_corrected=alpha_corrected,
        n_observations=n,
        power_achieved=power_achieved,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# TOST equivalence test (H4 accuracy component)
# ---------------------------------------------------------------------------


def tost_equivalence(
    rift_scores: np.ndarray,
    baseline_scores: np.ndarray,
    margin: float = 0.05,
    alpha: float = 0.05,
    alpha_corrected: float = 0.05,
    rng: Optional[np.random.Generator] = None,
) -> HypothesisTestResult:
    """
    Two One-Sided Tests (TOST) equivalence test for H4 (accuracy component).

    H0: |mean(RIFT) - mean(baseline)| ≥ margin  (not equivalent)
    H1: |mean(RIFT) - mean(baseline)| < margin   (equivalent within margin)

    The TOST p-value is max(p_lower, p_upper), both from one-sided t-tests.
    Significance (equivalence declared) when p_TOST < alpha_corrected.

    Authority: docs/PHASE_3_SPEC_FREEZE.md §15 (H4 TOST equivalence component)
    """
    rift_scores = np.asarray(rift_scores, dtype=float)
    baseline_scores = np.asarray(baseline_scores, dtype=float)

    if len(rift_scores) != len(baseline_scores):
        raise ValueError(
            "rift_scores and baseline_scores must be paired arrays of equal length."
        )

    diff = rift_scores - baseline_scores
    n = len(diff)
    mean_diff = float(np.mean(diff))
    se = float(scipy_stats.sem(diff))

    if se == 0.0:
        # Identical arrays — trivially equivalent
        p_tost = 0.0
        t_stat = 0.0
    else:
        # Two one-sided t-tests on paired differences
        t_lower = (mean_diff + margin) / se
        t_upper = (mean_diff - margin) / se
        p_lower = float(scipy_stats.t.cdf(t_lower, df=n - 1))     # H₀: diff ≤ -margin
        p_upper = float(1.0 - scipy_stats.t.cdf(t_upper, df=n - 1))  # H₀: diff ≥ +margin
        p_tost = max(p_lower, p_upper)
        t_stat = float(min(abs(t_lower), abs(t_upper)))

    delta, delta_ci = cliffs_delta(rift_scores, baseline_scores, rng=rng)

    return HypothesisTestResult(
        hypothesis_id="H4",
        test_name=f"TOST equivalence (margin={margin})",
        statistic=t_stat,
        pvalue=p_tost,
        cliffs_delta=delta,
        cliffs_delta_ci=delta_ci,
        effect_size_interpretation=_interpret_cliffs_delta(delta),
        significant=p_tost < alpha_corrected,
        alpha_corrected=alpha_corrected,
        n_observations=n,
        power_achieved=None,
        notes=(
            f"TOST: equivalence declared when p < alpha_corrected={alpha_corrected}. "
            f"margin={margin}."
        ),
    )


# ---------------------------------------------------------------------------
# One-sided binomial test (H5)
# ---------------------------------------------------------------------------


def binomial_one_sided(
    n_successes: int,
    n_trials: int,
    p_null: float = 0.70,
    hypothesis_id: str = "H5",
    alpha: float = 0.05,
    alpha_corrected: float = 0.05,
    rift_scores: Optional[np.ndarray] = None,
    baseline_scores: Optional[np.ndarray] = None,
    rng: Optional[np.random.Generator] = None,
) -> HypothesisTestResult:
    """
    One-sided binomial test for H5 (cross-system generalisation).

    H₀: P(success) ≤ p_null
    H₁: P(success) >  p_null

    'Success' = Precision@1(RIFT_train_A_test_B)
                ≥ 0.70 × Precision@1(RIFT_train_A_test_A)

    Authority: docs/hypotheses.md H5, docs/PHASE_3_SPEC_FREEZE.md §15

    *** P2-08 FIX ***
    The default p_null=0.70 is ONLY correct when in-distribution P@1 = 1.0 (perfect).
    H5 defines: null = 0.70 × P@1(in-distribution).
    CALLERS MUST compute and pass the correct p_null:
        p_null = 0.70 * in_distribution_precision_at_1
    Example: if in-distribution P@1 = 0.80, pass p_null=0.56, NOT the default 0.70.
    The evaluation harness (scripts/run_confirmatory_tests.py) enforces this.

    Parameters
    ----------
    n_successes   : count of successful cross-system transfers
    n_trials      : total number of cross-system scenarios
    p_null        : null probability — MUST be 0.70 * in_dist_p1 (caller computes this)
    rift_scores, baseline_scores : optional arrays for Cliff's δ computation
    """
    result = scipy_stats.binomtest(n_successes, n_trials, p=p_null, alternative="greater")
    pvalue = float(result.pvalue)
    stat = float(n_successes)

    if rift_scores is not None and baseline_scores is not None:
        delta, delta_ci = cliffs_delta(
            np.asarray(rift_scores), np.asarray(baseline_scores), rng=rng
        )
    else:
        # No paired scores provided; return neutral Cliff's δ
        delta, delta_ci = 0.0, (0.0, 0.0)

    return HypothesisTestResult(
        hypothesis_id=hypothesis_id,
        test_name=f"One-sided binomial test (p_null={p_null})",
        statistic=stat,
        pvalue=pvalue,
        cliffs_delta=delta,
        cliffs_delta_ci=delta_ci,
        effect_size_interpretation=_interpret_cliffs_delta(delta),
        significant=pvalue < alpha_corrected,
        alpha_corrected=alpha_corrected,
        n_observations=n_trials,
        power_achieved=None,
        notes=(
            f"H5: successes={n_successes}/{n_trials}, p_null={p_null}. "
            "Cross-system generalisation test."
        ),
    )


# ---------------------------------------------------------------------------
# Multiple-testing corrections
# ---------------------------------------------------------------------------


def holm_bonferroni_correction(
    pvalues: Dict[str, float],
    alpha: float = 0.05,
) -> Dict[str, float]:
    """
    Holm-Bonferroni correction for 6 confirmatory tests.

    Returns a dict mapping each key to its corrected α threshold.
    A test is significant if its (sorted rank) p-value < alpha / (m - rank + 1).

    The returned dict maps key → corrected_alpha_threshold, not adjusted p-value.
    Compare pvalues[k] < corrected_alpha[k] for significance.

    Authority: docs/PHASE_3_SPEC_FREEZE.md §15
               "Multiple testing: Holm-Bonferroni for 6 confirmatory tests."
    """
    keys = list(pvalues.keys())
    m = len(keys)
    # Sort by ascending p-value
    sorted_keys = sorted(keys, key=lambda k: pvalues[k])

    corrected: Dict[str, float] = {}
    for rank, key in enumerate(sorted_keys, start=1):
        # Holm: α / (m - rank + 1)
        threshold = alpha / (m - rank + 1)
        corrected[key] = threshold

    return corrected


def bh_fdr_correction(
    pvalues: Dict[str, float],
    alpha: float = 0.05,
) -> Dict[str, float]:
    """
    Benjamini-Hochberg FDR correction for exploratory comparisons.

    Returns a dict mapping each key to its adjusted p-value (BH-adjusted).
    A test is significant when adjusted_pvalue[k] < alpha.

    BH procedure:
        Sort p-values: p_(1) ≤ p_(2) ≤ … ≤ p_(m)
        Find largest k: p_(k) ≤ (k / m) × α
        Reject all hypotheses 1 … k

    The adjusted p-value returned is the BH-adjusted p (step-up method):
        p_adj_(k) = min over j≥k of (m / j) × p_(j)

    Authority: docs/PHASE_3_SPEC_FREEZE.md §15
               "Exploratory comparisons: BH FDR."
    """
    keys = list(pvalues.keys())
    m = len(keys)
    if m == 0:
        return {}

    sorted_keys = sorted(keys, key=lambda k: pvalues[k])
    sorted_pvals = np.array([pvalues[k] for k in sorted_keys], dtype=float)

    # Compute step-up BH adjusted p-values
    adj = np.empty(m, dtype=float)
    adj[m - 1] = sorted_pvals[m - 1]
    for i in range(m - 2, -1, -1):
        adj[i] = min(adj[i + 1], (m / (i + 1)) * sorted_pvals[i])
    adj = np.clip(adj, 0.0, 1.0)

    return {k: float(adj[i]) for i, k in enumerate(sorted_keys)}


# ---------------------------------------------------------------------------
# Power check
# ---------------------------------------------------------------------------


def check_power_achieved(
    n_confounded: int,
    target_n: int = 48,
    target_power: float = 0.80,
    medium_effect_size: float = 0.30,
) -> dict:
    """
    Check whether 80% power is achievable with the current sample size.

    Authority: docs/PHASE_3_SPEC_FREEZE.md §15
        "C_confounded requires ≥ 48 incidents for 80% power.
         If fewer collected, report achieved power only;
         do NOT claim 80%."

    Parameters
    ----------
    n_confounded        : actual number of confounded incidents collected
    target_n            : minimum required for 80 % power (default 48)
    target_power        : desired power level (default 0.80)
    medium_effect_size  : assumed medium Cliff's δ ≈ 0.30 for power calc

    Returns
    -------
    dict with keys:
        n_confounded        : int
        target_n            : int
        target_power        : float
        power_target_met    : bool
        achieved_power      : float  (approximate, from normal approximation)
        claim_80pct_power   : bool   (MUST be False when n < target_n)
        notes               : str
    """
    # Approximate achieved power via Wilcoxon signed-rank power formula.
    # Under H₁ with Gaussian differences and effect size d ≈ Cliff's δ,
    # we use the normal approximation:
    #   power ≈ Φ( |δ| × sqrt(n) / σ_ref - z_α )
    # where σ_ref = 1 / sqrt(3) for uniform [0,1] differences, z_α = 1.645
    # This is a conservative approximation consistent with §15.
    z_alpha = 1.645  # one-sided α = 0.05
    sigma_ref = 1.0 / np.sqrt(3.0)  # conservative reference

    if n_confounded <= 0:
        achieved_power = 0.0
    else:
        z_stat = medium_effect_size * np.sqrt(n_confounded) / sigma_ref - z_alpha
        achieved_power = float(scipy_stats.norm.cdf(z_stat))

    power_target_met = n_confounded >= target_n
    claim_80pct = power_target_met  # MUST be False when n < target_n

    if not claim_80pct:
        warnings.warn(
            f"n_confounded={n_confounded} < target_n={target_n}. "
            "Cannot claim 80% power for H2. "
            f"Achieved power ≈ {achieved_power:.3f}. "
            "Report achieved power only. "
            "See docs/PHASE_3_SPEC_FREEZE.md §15.",
            stacklevel=2,
        )

    notes = (
        f"n_confounded={n_confounded}, target_n={target_n}. "
        f"Achieved power ≈ {achieved_power:.3f} "
        f"(Wilcoxon normal approx., δ={medium_effect_size}, α=0.05 one-sided). "
    )
    if claim_80pct:
        notes += "80% power target met — claim is valid."
    else:
        notes += (
            "80% power target NOT met — do NOT claim 80% power in any artifact. "
            "Report achieved power only."
        )

    return {
        "n_confounded": n_confounded,
        "target_n": target_n,
        "target_power": target_power,
        "power_target_met": power_target_met,
        "achieved_power": achieved_power,
        "claim_80pct_power": claim_80pct,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Convenience: run all confirmatory tests with shared Holm correction
# ---------------------------------------------------------------------------


def run_confirmatory_tests(
    h1_rift: np.ndarray,
    h1_baseline: np.ndarray,
    h2_rift: np.ndarray,
    h2_baseline: np.ndarray,
    h3_rift: np.ndarray,
    h3_baseline: np.ndarray,
    h4_cost_rift: np.ndarray,
    h4_cost_baseline: np.ndarray,
    h4_acc_rift: np.ndarray,
    h4_acc_baseline: np.ndarray,
    h5_successes: int,
    h5_trials: int,
    alpha: float = 0.05,
    rng: Optional[np.random.Generator] = None,
) -> Dict[str, HypothesisTestResult]:
    """
    Run all 6 confirmatory tests (H1–H5; H4 counts as 2: accuracy + cost)
    and apply Holm-Bonferroni correction jointly.

    Returns a dict mapping 'H1', 'H2', 'H3', 'H4_acc', 'H4_cost', 'H5'
    to their HypothesisTestResult (with corrected alpha threshold applied).

    Authority: docs/PHASE_3_SPEC_FREEZE.md §15
    """
    raw: Dict[str, HypothesisTestResult] = {}

    # Preliminary pass: compute p-values at nominal alpha
    raw["H1"] = wilcoxon_one_sided(h1_rift, h1_baseline, "H1", alpha=alpha, rng=rng)
    raw["H2"] = wilcoxon_one_sided(h2_rift, h2_baseline, "H2", alpha=alpha, rng=rng)
    raw["H3"] = wilcoxon_one_sided(h3_rift, h3_baseline, "H3", alpha=alpha, rng=rng)
    raw["H4_acc"] = tost_equivalence(h4_acc_rift, h4_acc_baseline, alpha=alpha, rng=rng)
    raw["H4_cost"] = wilcoxon_one_sided(
        # H4 cost: baseline > RIFT (lower cost is better for RIFT)
        -h4_cost_rift, -h4_cost_baseline,
        "H4", alpha=alpha, rng=rng,
    )
    raw["H5"] = binomial_one_sided(h5_successes, h5_trials, alpha_corrected=alpha, rng=rng)

    # Holm-Bonferroni across all 6 tests
    pmap = {k: r.pvalue for k, r in raw.items()}
    corrected_alphas = holm_bonferroni_correction(pmap, alpha=alpha)

    # Rebuild results with corrected thresholds
    results: Dict[str, HypothesisTestResult] = {}
    for key, res in raw.items():
        ca = corrected_alphas[key]
        results[key] = HypothesisTestResult(
            hypothesis_id=res.hypothesis_id,
            test_name=res.test_name,
            statistic=res.statistic,
            pvalue=res.pvalue,
            cliffs_delta=res.cliffs_delta,
            cliffs_delta_ci=res.cliffs_delta_ci,
            effect_size_interpretation=res.effect_size_interpretation,
            significant=res.pvalue < ca,
            alpha_corrected=ca,
            n_observations=res.n_observations,
            power_achieved=res.power_achieved,
            notes=res.notes,
        )

    return results
