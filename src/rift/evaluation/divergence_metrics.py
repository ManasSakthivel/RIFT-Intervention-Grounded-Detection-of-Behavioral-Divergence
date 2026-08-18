"""RIFT Divergence Metrics — Phase 3.6 §14.

Reusable evaluators for:
  - Wasserstein W1 distance
  - Permutation p-values
  - CID (Causal Intervention Divergence)
  - Confidence intervals
  - Bootstrap CI on W1

Authority: docs/PHASE_3_SPEC_FREEZE.md §6-8, Phase 3.6 §14.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
from scipy.stats import wasserstein_distance


# ---------------------------------------------------------------------------
# W1 (Wasserstein) computation
# ---------------------------------------------------------------------------

def wasserstein_w1(a: np.ndarray, b: np.ndarray) -> float:
    """
    First Wasserstein distance W1(P, Q).

    Equal-size arrays: sorted-difference formula (exact).
    Unequal sizes: scipy wasserstein_distance (linear programming).

    Authority: SPEC_FREEZE §6.
    """
    a = np.asarray(a, dtype=float).ravel()
    b = np.asarray(b, dtype=float).ravel()
    if len(a) == 0 or len(b) == 0:
        return 0.0
    if len(a) == len(b):
        return float(np.mean(np.abs(np.sort(a) - np.sort(b))))
    return float(wasserstein_distance(a, b))


def bootstrap_w1_ci(
    baseline: np.ndarray,
    post: np.ndarray,
    n_bootstrap: int = 1000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """
    Percentile bootstrap CI on W1 point estimate.

    Returns: (w1_point, ci_lower, ci_upper)

    Authority: SPEC_FREEZE §8 — bootstrap CI is for effect-size uncertainty only,
    NOT for significance testing.
    """
    rng = np.random.default_rng(seed)
    baseline = np.asarray(baseline, dtype=float).ravel()
    post = np.asarray(post, dtype=float).ravel()

    w1_point = wasserstein_w1(baseline, post)

    boot_w1 = np.empty(n_bootstrap, dtype=float)
    na, nb = len(baseline), len(post)
    for i in range(n_bootstrap):
        a_boot = rng.choice(baseline, size=na, replace=True)
        b_boot = rng.choice(post, size=nb, replace=True)
        boot_w1[i] = wasserstein_w1(a_boot, b_boot)

    alpha = (1.0 - ci_level) / 2.0
    ci_lo = float(np.percentile(boot_w1, alpha * 100))
    ci_hi = float(np.percentile(boot_w1, (1.0 - alpha) * 100))
    return w1_point, ci_lo, ci_hi


def permutation_pvalue(
    baseline: np.ndarray,
    post: np.ndarray,
    n_permutations: int = 10_000,
    seed: int = 42,
) -> float:
    """
    Label-permutation test for W1.

    p-value = (# perms where W1_perm >= W1_observed + 1) / (n_permutations + 1)

    The +1/(B+1) Phipson-Smyth correction prevents exactly-zero p-values.
    Primary significance test per SPEC_FREEZE §8.

    Authority: SPEC_FREEZE §8.
    """
    rng = np.random.default_rng(seed)
    baseline = np.asarray(baseline, dtype=float).ravel()
    post = np.asarray(post, dtype=float).ravel()
    observed = wasserstein_w1(baseline, post)

    combined = np.concatenate([baseline, post])
    na = len(baseline)
    count = 0
    for _ in range(n_permutations):
        perm = rng.permutation(combined)
        w1_perm = wasserstein_w1(perm[:na], perm[na:])
        if w1_perm >= observed:
            count += 1

    return (count + 1) / (n_permutations + 1)


# ---------------------------------------------------------------------------
# CID evaluator result
# ---------------------------------------------------------------------------

@dataclass
class DivergenceEvalResult:
    """
    Full divergence evaluation result for one (baseline, post) pair.

    Primary: W1 (Wasserstein)
    Secondary diagnostic: TV (Total Variation) — never used for attribution.
    Significance: permutation p-value (primary).
    CI: bootstrap CI on W1 (effect size only).
    """
    source_variable: str
    target_variable: str
    w1: float
    w1_ci_lower: float
    w1_ci_upper: float
    w1_ci_width: float
    tv_diagnostic: float            # secondary only; never for attribution
    permutation_pvalue: float
    permutation_significant: bool
    n_baseline: int
    n_post: int
    theta_cid: float
    exceeds_threshold: bool
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "source_variable": self.source_variable,
            "target_variable": self.target_variable,
            "w1": self.w1,
            "w1_ci_lower": self.w1_ci_lower,
            "w1_ci_upper": self.w1_ci_upper,
            "w1_ci_width": self.w1_ci_width,
            "tv_diagnostic": self.tv_diagnostic,
            "permutation_pvalue": self.permutation_pvalue,
            "permutation_significant": self.permutation_significant,
            "n_baseline": self.n_baseline,
            "n_post": self.n_post,
            "theta_cid": self.theta_cid,
            "exceeds_threshold": self.exceeds_threshold,
            "notes": self.notes,
        }


def _tv_distance(a: np.ndarray, b: np.ndarray, n_bins: int = 100) -> float:
    """TV distance via histogram. Secondary diagnostic only — never for attribution."""
    combined = np.concatenate([a, b])
    lo, hi = float(combined.min()), float(combined.max())
    if lo == hi:
        return 0.0
    edges = np.linspace(lo, hi, n_bins + 1)
    pa, _ = np.histogram(a, bins=edges, density=False)
    pb, _ = np.histogram(b, bins=edges, density=False)
    pa = pa / pa.sum()
    pb = pb / pb.sum()
    return float(0.5 * np.sum(np.abs(pa - pb)))


def evaluate_divergence(
    baseline_samples: np.ndarray,
    post_intervention_samples: np.ndarray,
    source_variable: str,
    target_variable: str,
    alpha: float = 0.05,
    n_bootstrap: int = 1000,
    n_permutations: int = 10_000,
    seed: int = 42,
) -> DivergenceEvalResult:
    """
    Compute the full divergence evaluation suite.

    Returns None if either sample is empty.

    Authority: SPEC_FREEZE §6-8.
    """
    baseline = np.asarray(baseline_samples, dtype=float).ravel()
    post = np.asarray(post_intervention_samples, dtype=float).ravel()

    n_base = len(baseline)
    n_post = len(post)

    if n_base == 0 or n_post == 0:
        return DivergenceEvalResult(
            source_variable=source_variable,
            target_variable=target_variable,
            w1=0.0, w1_ci_lower=0.0, w1_ci_upper=0.0, w1_ci_width=0.0,
            tv_diagnostic=0.0,
            permutation_pvalue=1.0, permutation_significant=False,
            n_baseline=n_base, n_post=n_post,
            theta_cid=0.0, exceeds_threshold=False,
            notes="Empty sample — divergence not computed.",
        )

    w1_point, ci_lo, ci_hi = bootstrap_w1_ci(
        baseline, post, n_bootstrap=n_bootstrap, ci_level=0.95, seed=seed
    )
    tv = _tv_distance(baseline, post)

    pvalue = permutation_pvalue(baseline, post, n_permutations=n_permutations, seed=seed)
    significant = pvalue < alpha

    iqr = float(np.percentile(baseline, 75) - np.percentile(baseline, 25))
    theta_cid = 0.1 * iqr
    exceeds = (w1_point > theta_cid) if theta_cid > 0 else (w1_point > 0)

    return DivergenceEvalResult(
        source_variable=source_variable,
        target_variable=target_variable,
        w1=w1_point,
        w1_ci_lower=ci_lo,
        w1_ci_upper=ci_hi,
        w1_ci_width=ci_hi - ci_lo,
        tv_diagnostic=tv,
        permutation_pvalue=pvalue,
        permutation_significant=significant,
        n_baseline=n_base,
        n_post=n_post,
        theta_cid=theta_cid,
        exceeds_threshold=exceeds,
        notes=(
            f"W1={w1_point:.4f} (p={pvalue:.4f}, θ_CID={theta_cid:.4f}). "
            "TV is secondary diagnostic only — not used for attribution."
        ),
    )
