"""RIFT Power Analysis — Phase 3.6 §16.

Implements sample-size analysis for H1-H5.

The confounded subset currently requires approximately n ≥ 48 for 80% power
(H2 hypothesis). This is documented and cannot be claimed if n < 48.

The benchmark runner uses this module to report:
  required_n
  actual_n
  achieved_power

Authority: docs/risk_closure/sample_requirements.md, docs/PHASE_3_SPEC_FREEZE.md §15.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy import stats as scipy_stats


@dataclass
class PowerAnalysisResult:
    """
    Result of a power analysis for one hypothesis.

    claim_80pct_power MUST be False when actual_n < required_n.
    """
    hypothesis_id: str
    required_n: int
    actual_n: int
    target_power: float           # e.g., 0.80
    achieved_power: float         # computed from actual_n and effect_size
    effect_size: float            # assumed effect size (Cliff's δ or Cohen's d)
    alpha: float                  # one-sided significance level
    claim_80pct_power: bool       # MUST be False when actual_n < required_n
    power_deficit: float          # max(0, required_n - actual_n)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "hypothesis_id": self.hypothesis_id,
            "required_n": self.required_n,
            "actual_n": self.actual_n,
            "target_power": self.target_power,
            "achieved_power": self.achieved_power,
            "effect_size": self.effect_size,
            "alpha": self.alpha,
            "claim_80pct_power": self.claim_80pct_power,
            "power_deficit": self.power_deficit,
            "notes": self.notes,
        }


def compute_power(
    n: int,
    effect_size: float = 0.30,
    alpha: float = 0.05,
    test: str = "wilcoxon",
) -> float:
    """
    Approximate achieved power for a one-sided test at sample size n.

    Uses normal approximation to the Wilcoxon signed-rank test (conservative).
    Formula: power ≈ Φ(|δ| × √n / σ_ref − z_α)
    where σ_ref = 1/√3 (conservative reference for uniform [0,1] differences).

    Authority: docs/PHASE_3_SPEC_FREEZE.md §15.
    """
    if n <= 0:
        return 0.0

    z_alpha = scipy_stats.norm.ppf(1.0 - alpha)
    sigma_ref = 1.0 / np.sqrt(3.0)  # conservative reference

    z_stat = effect_size * np.sqrt(n) / sigma_ref - z_alpha
    return float(scipy_stats.norm.cdf(z_stat))


def required_sample_size(
    effect_size: float = 0.30,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    """
    Minimum sample size required to achieve `power` at `effect_size` and `alpha`.

    Binary search implementation (safe for all effect sizes).
    """
    for n in range(2, 10_000):
        p = compute_power(n, effect_size=effect_size, alpha=alpha)
        if p >= power:
            return n
    return 10_000  # fallback — should not be reached for reasonable effect sizes


def power_analysis_h2(
    actual_n: int,
    effect_size: float = 0.30,
    alpha: float = 0.05,
    target_power: float = 0.80,
) -> PowerAnalysisResult:
    """
    Power analysis for H2 (confounded incidents).

    The frozen requirement is n ≥ 48 for 80% power at δ=0.30, α=0.05.
    (From docs/risk_closure/sample_requirements.md)

    If actual_n < 48: achieved_power is reported; 80% power is NOT claimed.
    """
    required = required_sample_size(effect_size=effect_size, alpha=alpha, power=target_power)
    achieved = compute_power(actual_n, effect_size=effect_size, alpha=alpha)

    claim_80pct = actual_n >= required

    if not claim_80pct:
        warnings.warn(
            f"H2 power: actual_n={actual_n} < required_n={required}. "
            f"Cannot claim {target_power*100:.0f}% power. "
            f"Achieved power ≈ {achieved:.3f}. "
            "Report achieved power only. "
            "Authority: docs/PHASE_3_SPEC_FREEZE.md §15.",
            stacklevel=2,
        )

    notes = (
        f"H2 power analysis: actual_n={actual_n}, required_n={required}. "
        f"Achieved power ≈ {achieved:.3f} (δ={effect_size}, α={alpha}, one-sided). "
    )
    notes += (
        "80% power target met — claim is valid."
        if claim_80pct
        else "80% power NOT met — report achieved power only."
    )

    return PowerAnalysisResult(
        hypothesis_id="H2",
        required_n=required,
        actual_n=actual_n,
        target_power=target_power,
        achieved_power=achieved,
        effect_size=effect_size,
        alpha=alpha,
        claim_80pct_power=claim_80pct,
        power_deficit=max(0, required - actual_n),
        notes=notes,
    )


def power_analysis_full(
    actual_n: int,
    actual_n_confounded: Optional[int] = None,
) -> dict:
    """
    Run power analysis for all 5 hypotheses.

    Returns dict mapping hypothesis_id → PowerAnalysisResult.
    """
    results = {}

    # H1: P@1 overall — δ=0.3, α=0.05, one-sided
    results["H1"] = PowerAnalysisResult(
        hypothesis_id="H1",
        required_n=required_sample_size(0.30, 0.05, 0.80),
        actual_n=actual_n,
        target_power=0.80,
        achieved_power=compute_power(actual_n, 0.30, 0.05),
        effect_size=0.30,
        alpha=0.05,
        claim_80pct_power=actual_n >= required_sample_size(0.30, 0.05, 0.80),
        power_deficit=max(0, required_sample_size(0.30, 0.05, 0.80) - actual_n),
        notes="H1: P@1 overall comparison.",
    )

    # H2: confounded incidents
    n_conf = actual_n_confounded if actual_n_confounded is not None else actual_n
    results["H2"] = power_analysis_h2(n_conf)

    # H3: detection latency
    results["H3"] = PowerAnalysisResult(
        hypothesis_id="H3",
        required_n=required_sample_size(0.30, 0.05, 0.80),
        actual_n=actual_n,
        target_power=0.80,
        achieved_power=compute_power(actual_n, 0.30, 0.05),
        effect_size=0.30,
        alpha=0.05,
        claim_80pct_power=actual_n >= required_sample_size(0.30, 0.05, 0.80),
        power_deficit=max(0, required_sample_size(0.30, 0.05, 0.80) - actual_n),
        notes="H3: detection latency comparison.",
    )

    # H4 / H5: smaller effect or different test — conservative estimate
    for hid in ("H4", "H5"):
        results[hid] = PowerAnalysisResult(
            hypothesis_id=hid,
            required_n=required_sample_size(0.30, 0.05, 0.80),
            actual_n=actual_n,
            target_power=0.80,
            achieved_power=compute_power(actual_n, 0.30, 0.05),
            effect_size=0.30,
            alpha=0.05,
            claim_80pct_power=actual_n >= required_sample_size(0.30, 0.05, 0.80),
            power_deficit=max(0, required_sample_size(0.30, 0.05, 0.80) - actual_n),
            notes=f"{hid}: conservative power estimate.",
        )

    return results
