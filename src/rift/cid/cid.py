"""
RIFT CID — Causal Intervention Divergence (Phase 3 Implementation)

CID(X → Y, t) = W₁( P(Y | baseline), P(Y | do(X := x_nominal)) )

Authority:
  Section 6  — CID definition, W₁ as primary, TV as secondary diagnostic
  Section 7  — Sample tiers (SPEC-AMEND-003): n<20 INSUFFICIENT, 20≤n<50 CANDIDATE, n≥50 RELIABLE
  Section 8  — Significance test: permutation test (primary, B=10000, α=0.05)
               Bootstrap CI: effect-size CI on W₁ only, NOT for significance

CRITICAL:  A CID score > θ_cid does NOT by itself constitute causal attribution.
           CID is one component of EBD R4. R1–R3 are also required.

CAUSAL CLAIM LANGUAGE (Section 18):
  - "intervention-consistent" — not "causally accurate"
  - RIFT abstains when n < 20 (INSUFFICIENT grade)
  - Validated on synthetic ground-truth scenarios
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np
from scipy.stats import wasserstein_distance


# ---------------------------------------------------------------------------
# Grade / tier definitions
# Authority: Section 7, SPEC-AMEND-003
# ---------------------------------------------------------------------------

class CIDGrade(Enum):
    """
    Sample-size tier for CID reliability.

    INSUFFICIENT : n < 20  — hard floor; no CID output of any kind
    CANDIDATE    : 20 ≤ n < 50 — directional claim valid, wide CI
    RELIABLE     : n ≥ 50  — definitive effect-size estimation
    """
    INSUFFICIENT = "INSUFFICIENT"
    CANDIDATE    = "CANDIDATE"
    RELIABLE     = "RELIABLE"


def _grade(n: int) -> CIDGrade:
    """Map sample count to CIDGrade tier (Section 7, SPEC-AMEND-003)."""
    if n < 20:
        return CIDGrade.INSUFFICIENT
    if n < 50:
        return CIDGrade.CANDIDATE
    return CIDGrade.RELIABLE


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class CIDResult:
    """
    Full output of a single CID computation.

    Primary metric  : w1_estimate — first Wasserstein distance (Section 6)
    Secondary diag  : tv_diagnostic — Total Variation; never used for attribution
    Significance    : permutation p-value (Section 8, permutation test primary)
    CI              : bootstrap 95 % CI on W₁ point estimate only (Section 8)
    """

    source_variable: str
    target_variable: str
    t_intervention: float

    # --- Primary metric (None when INSUFFICIENT) ---
    w1_estimate:  Optional[float] = None
    w1_ci_lower:  Optional[float] = None
    w1_ci_upper:  Optional[float] = None
    w1_ci_width:  Optional[float] = None

    # --- Secondary diagnostic (TV); never used for attribution ---
    tv_diagnostic: Optional[float] = None

    # --- Permutation significance test (Section 8) ---
    permutation_pvalue:      Optional[float] = None
    permutation_b:           int             = 0
    permutation_significant: Optional[bool]  = None
    alpha:                   float           = 0.05

    # --- Sample information ---
    n_baseline: int      = 0
    n_post:     int      = 0
    grade:      CIDGrade = CIDGrade.INSUFFICIENT

    # --- Attribution threshold ---
    theta_cid:        float          = 0.0   # IQR-normalised threshold (0.1 × IQR_baseline)
    exceeds_threshold: Optional[bool] = None

    # --- Provenance ---
    intervention_record_id: Optional[str] = None
    notes: str = ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _w1_equal(a: np.ndarray, b: np.ndarray) -> float:
    """
    W₁ from sorted arrays (Section 6, equal-size formula).
    W₁(P, Q) = (1/n) Σᵢ |sort(P)[i] − sort(Q)[i]|
    """
    n = len(a)
    return float(np.mean(np.abs(np.sort(a) - np.sort(b))))


def _w1(a: np.ndarray, b: np.ndarray) -> float:
    """
    W₁ dispatcher: equal-size uses sorted-array formula; unequal uses scipy.
    Authority: Section 6.
    """
    if len(a) == len(b):
        return _w1_equal(a, b)
    return float(wasserstein_distance(a, b))


def _tv(a: np.ndarray, b: np.ndarray, n_bins: int = 100) -> float:
    """
    Total Variation distance via histogram (secondary diagnostic only).
    TV = 0.5 × Σ |P(bin) − Q(bin)|.  Never used for attribution.
    Authority: Section 6 — TV is CID_TV_diagnostic, secondary only.
    """
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


def _permutation_pvalue(
    a: np.ndarray,
    b: np.ndarray,
    observed_w1: float,
    n_permutations: int,
    rng: np.random.Generator,
) -> float:
    """
    Label-permutation test for W₁.
    Authority: Section 8 — permutation test is primary significance test;
               B = 10 000 permutations, α = 0.05.

    p-value = (# permutations where W₁_perm ≥ observed_W₁ + 1) / (B + 1)
    The +1 / (B+1) is the standard Phipson-Smyth correction ensuring p ≤ 1
    and preventing exactly-zero p-values.
    """
    combined = np.concatenate([a, b])
    na = len(a)
    count = 0
    for _ in range(n_permutations):
        perm = rng.permutation(combined)
        w1_perm = _w1(perm[:na], perm[na:])
        if w1_perm >= observed_w1:
            count += 1
    return (count + 1) / (n_permutations + 1)


def _bootstrap_ci(
    a: np.ndarray,
    b: np.ndarray,
    n_bootstrap: int,
    rng: np.random.Generator,
    ci_level: float = 0.95,
) -> tuple[float, float]:
    """
    Percentile bootstrap CI on W₁ point estimate.
    Authority: Section 8 — bootstrap CI is for effect-size uncertainty only,
               NOT for significance testing.
    """
    w1_boot = np.empty(n_bootstrap)
    na, nb = len(a), len(b)
    for i in range(n_bootstrap):
        a_boot = rng.choice(a, size=na, replace=True)
        b_boot = rng.choice(b, size=nb, replace=True)
        w1_boot[i] = _w1(a_boot, b_boot)
    lo_pct = (1.0 - ci_level) / 2.0 * 100.0
    hi_pct = (1.0 + ci_level) / 2.0 * 100.0
    return float(np.percentile(w1_boot, lo_pct)), float(np.percentile(w1_boot, hi_pct))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_cid(
    baseline_samples: np.ndarray,
    post_intervention_samples: np.ndarray,
    source_variable: str,
    target_variable: str,
    t_intervention: float,
    intervention_record_id: Optional[str] = None,
    alpha: float = 0.05,
    n_bootstrap: int = 1000,
    n_permutations: int = 10_000,
    seed: int = 42,
) -> CIDResult:
    """
    Compute CID(X → Y, t) = W₁(P(Y|baseline), P(Y|do(X:=x_nominal))).

    Returns CIDResult.  All metric fields are None when grade == INSUFFICIENT.

    Primary significance test : permutation test (B = n_permutations, default 10 000).
    Bootstrap CI               : effect-size CI on W₁ only — NOT significance.
    Threshold                  : θ_cid = 0.1 × IQR(baseline_samples).

    IMPORTANT: CID score > θ_cid does NOT by itself constitute causal attribution.
    CID is one component of EBD R4, which also requires R1–R3.
    Authority: docs/PHASE_3_SPEC_FREEZE.md Sections 6, 7, 8.
    """
    baseline = np.asarray(baseline_samples, dtype=float).ravel()
    post     = np.asarray(post_intervention_samples, dtype=float).ravel()

    n_base = len(baseline)
    n_post = len(post)
    n_min  = min(n_base, n_post)

    grade = _grade(n_min)

    # IQR-normalised threshold (Section 6); computed from baseline regardless of grade
    iqr_baseline = float(np.percentile(baseline, 75) - np.percentile(baseline, 25))
    theta_cid    = 0.1 * iqr_baseline

    # ----- INSUFFICIENT: abstain entirely (Section 7 hard floor) -----
    if grade == CIDGrade.INSUFFICIENT:
        note = (
            f"INSUFFICIENT: n_min={n_min} < 20. "
            "RIFT abstains when sample count is below the hard floor. "
            "No CID output produced."
        )
        return CIDResult(
            source_variable=source_variable,
            target_variable=target_variable,
            t_intervention=t_intervention,
            n_baseline=n_base,
            n_post=n_post,
            grade=grade,
            theta_cid=theta_cid,
            alpha=alpha,
            permutation_b=0,
            intervention_record_id=intervention_record_id,
            notes=note,
        )

    # ----- Compute W₁ (primary) and TV (secondary diagnostic) -----
    rng = np.random.default_rng(seed)

    w1_obs = _w1(baseline, post)
    tv_obs = _tv(baseline, post)

    # ----- Bootstrap CI on W₁ point estimate (Section 8: effect-size CI only) -----
    ci_lo, ci_hi = _bootstrap_ci(baseline, post, n_bootstrap=n_bootstrap, rng=rng)
    ci_width = ci_hi - ci_lo

    # ----- Permutation significance test (Section 8: primary) -----
    pvalue = _permutation_pvalue(baseline, post, w1_obs, n_permutations, rng)
    significant = pvalue < alpha

    # ----- Threshold check (Section 6) -----
    exceeds = (w1_obs > theta_cid) if theta_cid > 0.0 else (w1_obs > 0.0)

    # ----- Grade-specific notes -----
    notes_parts: list[str] = []
    if grade == CIDGrade.CANDIDATE:
        if n_min < 30:
            notes_parts.append(
                f"CANDIDATE (marginal): n_min={n_min} in [20,30). Wide CI. "
                "Directional claim only; do not claim definitive effect size."
            )
        else:
            notes_parts.append(
                f"CANDIDATE: n_min={n_min} in [30,50). Directional claim valid. "
                "Wide CI; effect-size estimate imprecise."
            )

    return CIDResult(
        source_variable=source_variable,
        target_variable=target_variable,
        t_intervention=t_intervention,
        w1_estimate=w1_obs,
        w1_ci_lower=ci_lo,
        w1_ci_upper=ci_hi,
        w1_ci_width=ci_width,
        tv_diagnostic=tv_obs,
        permutation_pvalue=pvalue,
        permutation_b=n_permutations,
        permutation_significant=significant,
        alpha=alpha,
        n_baseline=n_base,
        n_post=n_post,
        grade=grade,
        theta_cid=theta_cid,
        exceeds_threshold=exceeds,
        intervention_record_id=intervention_record_id,
        notes=" ".join(notes_parts),
    )
