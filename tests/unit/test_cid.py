"""
RIFT CID — Comprehensive unit tests with synthetic ground-truth validation.

Test cases cover:
  1. no_effect      P = Q = Normal(100, 20)                   true W₁ ≈ 0
  2. small_effect   P = Normal(100,20), Q = Normal(110,20)    small shift
  3. medium_effect  P = Normal(100,20), Q = Normal(150,20)    2.5-sigma shift
  4. large_effect   P = Normal(100,20), Q = Normal(200,20)    5-sigma shift
  5. unimodal       same as medium_effect, explicitly unimodal
  6. bimodal        mixture distributions; W₁ handles correctly, TV would be problematic
  7. heavy_tail     Pareto / shifted Pareto
  8. multi_cause    two independent interventions; no cross-contamination

Grade checks at n ∈ {5, 10, 20, 30, 50, 100, 300}.
Permutation Type I error check at n=50 (repeated trials).
Monotonicity of W₁ with shift magnitude at n=100.
INSUFFICIENT abstention at n < 20.

Authority: docs/PHASE_3_SPEC_FREEZE.md Sections 6, 7, 8
"""

from __future__ import annotations

import math
from typing import Callable

import numpy as np
import pytest

from src.rift.cid.cid import CIDGrade, CIDResult, compute_cid

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RNG = np.random.default_rng(0)


def _normal(mean: float, std: float, n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.normal(mean, std, n)


def _bimodal(
    mu1: float, mu2: float, std: float, n: int, rng: np.random.Generator
) -> np.ndarray:
    """Equal-weight mixture of two Gaussians."""
    half = n // 2
    a = rng.normal(mu1, std, half)
    b = rng.normal(mu2, std, n - half)
    return np.concatenate([a, b])


def _pareto(shape: float, scale: float, n: int, rng: np.random.Generator) -> np.ndarray:
    """Pareto samples: scale * (U^(-1/shape) - 1) where U~Uniform."""
    u = rng.uniform(0, 1, n)
    return scale * (u ** (-1.0 / shape) - 1.0)


SAMPLE_SIZES = [5, 10, 20, 30, 50, 100, 300]
GRADE_MAP = {
    5: CIDGrade.INSUFFICIENT,
    10: CIDGrade.INSUFFICIENT,
    20: CIDGrade.CANDIDATE,
    30: CIDGrade.CANDIDATE,
    50: CIDGrade.RELIABLE,
    100: CIDGrade.RELIABLE,
    300: CIDGrade.RELIABLE,
}


def _run(
    baseline_fn: Callable[[int, np.random.Generator], np.ndarray],
    post_fn: Callable[[int, np.random.Generator], np.ndarray],
    n: int,
    rng: np.random.Generator,
    seed: int = 42,
    n_permutations: int = 10_000,
    n_bootstrap: int = 500,
) -> CIDResult:
    baseline = baseline_fn(n, rng)
    post     = post_fn(n, rng)
    return compute_cid(
        baseline_samples=baseline,
        post_intervention_samples=post,
        source_variable="X",
        target_variable="Y",
        t_intervention=0.0,
        seed=seed,
        n_permutations=n_permutations,
        n_bootstrap=n_bootstrap,
    )


# ---------------------------------------------------------------------------
# 1. Grade assignment — all cases
# ---------------------------------------------------------------------------

class TestGradeAssignment:
    """Grade must follow SPEC-AMEND-003 tiers exactly."""

    @pytest.mark.parametrize("n,expected_grade", list(GRADE_MAP.items()))
    def test_grade_from_n(self, n: int, expected_grade: CIDGrade) -> None:
        rng = np.random.default_rng(7)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(100, 20, n),
            n,
            rng,
        )
        assert result.grade == expected_grade, (
            f"n={n}: expected {expected_grade}, got {result.grade}"
        )

    @pytest.mark.parametrize("n", [5, 10, 19])
    def test_insufficient_abstention_all_fields_none(self, n: int) -> None:
        """INSUFFICIENT must produce None for every metric field (Section 7 hard floor)."""
        rng = np.random.default_rng(9)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(200, 20, n),
            n,
            rng,
        )
        assert result.grade == CIDGrade.INSUFFICIENT
        assert result.w1_estimate is None
        assert result.w1_ci_lower is None
        assert result.w1_ci_upper is None
        assert result.permutation_pvalue is None
        assert result.permutation_significant is None
        assert result.exceeds_threshold is None
        assert result.tv_diagnostic is None


# ---------------------------------------------------------------------------
# 2. INSUFFICIENT abstention — no output at n < 20
# ---------------------------------------------------------------------------

class TestInsufficientAbstention:
    """Section 7: no CID output of any kind below n_min=20."""

    def test_large_effect_still_abstains_at_n5(self) -> None:
        rng = np.random.default_rng(11)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(300, 20, n),
            5,
            rng,
        )
        assert result.grade == CIDGrade.INSUFFICIENT
        assert result.w1_estimate is None

    def test_abstention_boundary_n19(self) -> None:
        rng = np.random.default_rng(13)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(300, 20, n),
            19,
            rng,
        )
        assert result.grade == CIDGrade.INSUFFICIENT

    def test_no_abstention_at_n20(self) -> None:
        rng = np.random.default_rng(15)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(300, 20, n),
            20,
            rng,
        )
        assert result.grade != CIDGrade.INSUFFICIENT
        assert result.w1_estimate is not None


# ---------------------------------------------------------------------------
# 3. no_effect case  (P = Q = Normal(100, 20))
# ---------------------------------------------------------------------------

class TestNoEffect:
    """True W₁ = 0. Should not exceed threshold at adequate n."""

    def test_w1_near_zero_at_n300(self) -> None:
        rng = np.random.default_rng(17)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(100, 20, n),
            300,
            rng,
        )
        assert result.grade == CIDGrade.RELIABLE
        assert result.w1_estimate is not None
        # With equal distributions and n=300 the empirical W₁ is small
        assert result.w1_estimate < 5.0, (
            f"W₁={result.w1_estimate:.4f} too large for null case"
        )

    def test_does_not_exceed_threshold_at_n300(self) -> None:
        rng = np.random.default_rng(19)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(100, 20, n),
            300,
            rng,
        )
        # θ_cid = 0.1 × IQR ≈ 0.1 × 27 ≈ 2.7; empirical W₁ should be below that
        assert result.exceeds_threshold is False

    def test_not_significant_at_n50(self) -> None:
        """Permutation test should not reject H₀ for null case (most of the time)."""
        rng = np.random.default_rng(21)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(100, 20, n),
            50,
            rng,
        )
        assert result.permutation_pvalue is not None
        # p-value should not be tiny for a null effect
        assert result.permutation_pvalue > 0.01, (
            f"pvalue={result.permutation_pvalue:.4f} unexpectedly small for null"
        )


# ---------------------------------------------------------------------------
# 4. small_effect  (shift = 10, σ = 20 → Cohen's d = 0.5)
# ---------------------------------------------------------------------------

class TestSmallEffect:
    def test_grade_reliable_at_n100(self) -> None:
        rng = np.random.default_rng(23)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(110, 20, n),
            100,
            rng,
        )
        assert result.grade == CIDGrade.RELIABLE

    def test_w1_positive_at_n100(self) -> None:
        rng = np.random.default_rng(25)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(110, 20, n),
            100,
            rng,
        )
        assert result.w1_estimate is not None
        assert result.w1_estimate > 0.0

    def test_ci_brackets_estimate(self) -> None:
        rng = np.random.default_rng(27)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(110, 20, n),
            100,
            rng,
        )
        assert result.w1_ci_lower is not None
        assert result.w1_ci_upper is not None
        assert result.w1_ci_lower <= result.w1_estimate  # type: ignore[operator]
        assert result.w1_ci_upper >= result.w1_estimate  # type: ignore[operator]


# ---------------------------------------------------------------------------
# 5. medium_effect  (shift = 50, σ = 20 → Cohen's d = 2.5)
# ---------------------------------------------------------------------------

class TestMediumEffect:
    def test_significant_at_n50(self) -> None:
        rng = np.random.default_rng(29)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(150, 20, n),
            50,
            rng,
        )
        assert result.permutation_significant is True, (
            f"medium effect not significant at n=50; pvalue={result.permutation_pvalue}"
        )

    def test_exceeds_threshold_at_n100(self) -> None:
        rng = np.random.default_rng(31)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(150, 20, n),
            100,
            rng,
        )
        assert result.exceeds_threshold is True

    def test_w1_near_true_value_at_n300(self) -> None:
        """True W₁ for Normal(100,20) vs Normal(150,20) = |150-100| = 50."""
        rng = np.random.default_rng(33)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(150, 20, n),
            300,
            rng,
        )
        assert result.w1_estimate is not None
        assert abs(result.w1_estimate - 50.0) < 5.0, (
            f"W₁={result.w1_estimate:.2f} far from true value 50"
        )


# ---------------------------------------------------------------------------
# 6. large_effect  (shift = 100, σ = 20 → Cohen's d = 5)
# ---------------------------------------------------------------------------

class TestLargeEffect:
    def test_significant_at_n20(self) -> None:
        rng = np.random.default_rng(35)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(200, 20, n),
            20,
            rng,
        )
        assert result.grade == CIDGrade.CANDIDATE
        assert result.permutation_significant is True

    def test_w1_near_100_at_n300(self) -> None:
        """True W₁ = 100 for this shift."""
        rng = np.random.default_rng(37)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(200, 20, n),
            300,
            rng,
        )
        assert result.w1_estimate is not None
        assert abs(result.w1_estimate - 100.0) < 8.0, (
            f"W₁={result.w1_estimate:.2f} far from true value 100"
        )


# ---------------------------------------------------------------------------
# 7. unimodal (explicitly single-mode, same as medium_effect)
# ---------------------------------------------------------------------------

class TestUnimodal:
    """Explicit sanity check that unimodal results are stable."""

    def test_reliable_grade_at_n50(self) -> None:
        rng = np.random.default_rng(39)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(150, 20, n),
            50,
            rng,
        )
        assert result.grade == CIDGrade.RELIABLE

    def test_ci_width_narrower_at_n300_than_n50(self) -> None:
        rng = np.random.default_rng(41)
        r50 = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(150, 20, n),
            50,
            rng,
        )
        rng2 = np.random.default_rng(43)
        r300 = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(150, 20, n),
            300,
            rng2,
        )
        assert r300.w1_ci_width is not None
        assert r50.w1_ci_width is not None
        assert r300.w1_ci_width < r50.w1_ci_width, (
            f"CI should narrow with more samples: n50={r50.w1_ci_width:.2f}, "
            f"n300={r300.w1_ci_width:.2f}"
        )


# ---------------------------------------------------------------------------
# 8. bimodal  (mixture distributions)
# ---------------------------------------------------------------------------

class TestBimodal:
    """
    W₁ handles bimodal distributions correctly.
    TV distance would be problematic here (Section 6, Phase 2.5 adversarial finding).
    We verify W₁ detects a meaningful shift and TV is only a secondary diagnostic.
    """

    def test_w1_detects_bimodal_shift_at_n100(self) -> None:
        rng = np.random.default_rng(45)
        # baseline: mixture(Normal(100,15), Normal(200,15))
        # post:     mixture(Normal(130,15), Normal(230,15))  — shifted by 30
        result = _run(
            lambda n, r: _bimodal(100, 200, 15, n, r),
            lambda n, r: _bimodal(130, 230, 15, n, r),
            100,
            rng,
        )
        assert result.w1_estimate is not None
        assert result.w1_estimate > 10.0, (
            f"W₁={result.w1_estimate:.2f} too small to detect bimodal shift"
        )

    def test_tv_is_secondary_diagnostic_only(self) -> None:
        """TV should be present but must not be None when grade is not INSUFFICIENT."""
        rng = np.random.default_rng(47)
        result = _run(
            lambda n, r: _bimodal(100, 200, 15, n, r),
            lambda n, r: _bimodal(130, 230, 15, n, r),
            100,
            rng,
        )
        assert result.tv_diagnostic is not None
        assert 0.0 <= result.tv_diagnostic <= 1.0

    def test_bimodal_no_effect_w1_near_zero_at_n300(self) -> None:
        rng = np.random.default_rng(49)
        result = _run(
            lambda n, r: _bimodal(100, 200, 15, n, r),
            lambda n, r: _bimodal(100, 200, 15, n, r),
            300,
            rng,
        )
        assert result.w1_estimate is not None
        assert result.w1_estimate < 10.0, (
            f"W₁={result.w1_estimate:.2f} too large for bimodal null case"
        )

    def test_bimodal_significant_shift_at_n50(self) -> None:
        rng = np.random.default_rng(51)
        result = _run(
            lambda n, r: _bimodal(100, 200, 15, n, r),
            lambda n, r: _bimodal(200, 300, 15, n, r),
            50,
            rng,
        )
        assert result.permutation_significant is True, (
            f"bimodal large shift not significant; pvalue={result.permutation_pvalue}"
        )


# ---------------------------------------------------------------------------
# 9. heavy_tail  (Pareto distributions)
# ---------------------------------------------------------------------------

class TestHeavyTail:
    """W₁ works on heavy-tailed (Pareto) distributions."""

    def test_heavy_tail_null_w1_near_zero(self) -> None:
        rng = np.random.default_rng(53)
        result = _run(
            lambda n, r: _pareto(2.0, 1.0, n, r),
            lambda n, r: _pareto(2.0, 1.0, n, r),
            300,
            rng,
        )
        assert result.w1_estimate is not None
        assert result.w1_estimate < 1.0, (
            f"W₁={result.w1_estimate:.4f} unexpectedly large for identical Pareto"
        )

    def test_heavy_tail_shifted_detects_effect(self) -> None:
        rng = np.random.default_rng(55)
        # shift scale from 1.0 to 3.0; W₁ proportional to scale shift
        result = _run(
            lambda n, r: _pareto(2.0, 1.0, n, r),
            lambda n, r: _pareto(2.0, 3.0, n, r),
            100,
            rng,
        )
        assert result.w1_estimate is not None
        assert result.w1_estimate > 0.5, (
            f"W₁={result.w1_estimate:.4f} too small for shifted Pareto"
        )
        assert result.grade == CIDGrade.RELIABLE

    def test_heavy_tail_significant_at_n100(self) -> None:
        rng = np.random.default_rng(57)
        result = _run(
            lambda n, r: _pareto(2.0, 1.0, n, r),
            lambda n, r: _pareto(2.0, 3.0, n, r),
            100,
            rng,
        )
        assert result.permutation_significant is True, (
            f"heavy-tail shift not significant; pvalue={result.permutation_pvalue}"
        )


# ---------------------------------------------------------------------------
# 10. multi_cause — no cross-contamination
# ---------------------------------------------------------------------------

class TestMultiCause:
    """
    Two independent interventions on different (X→Y) pairs should not
    cross-contaminate each other's W₁ estimates.
    """

    def test_independent_interventions_no_cross_contamination(self) -> None:
        rng1 = np.random.default_rng(59)
        rng2 = np.random.default_rng(61)

        # Intervention 1: X1 → Y1 (large shift)
        res1 = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(200, 20, n),
            100,
            rng1,
        )
        # Intervention 2: X2 → Y2 (null effect)
        res2 = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(100, 20, n),
            100,
            rng2,
        )

        assert res1.w1_estimate is not None
        assert res2.w1_estimate is not None

        # Large effect should have much higher W₁ than null
        assert res1.w1_estimate > 50.0, f"res1 W₁={res1.w1_estimate:.2f}"
        assert res2.w1_estimate < 10.0, f"res2 W₁={res2.w1_estimate:.2f}"

        # They are computed independently → no contamination by construction
        assert res1.w1_estimate != res2.w1_estimate

    def test_source_and_target_variables_recorded(self) -> None:
        rng = np.random.default_rng(63)
        baseline = rng.normal(100, 20, 100)
        post     = rng.normal(150, 20, 100)
        result = compute_cid(
            baseline_samples=baseline,
            post_intervention_samples=post,
            source_variable="ServiceA_latency",
            target_variable="ServiceB_errors",
            t_intervention=1234.5,
            n_permutations=1000,
            n_bootstrap=200,
        )
        assert result.source_variable == "ServiceA_latency"
        assert result.target_variable == "ServiceB_errors"
        assert result.t_intervention == 1234.5


# ---------------------------------------------------------------------------
# 11. Monotonicity of W₁ with shift magnitude at n=100
# ---------------------------------------------------------------------------

class TestMonotonicity:
    """
    W₁ must be monotonically increasing with shift magnitude.
    Tested at n=100 with shifts [0, 10, 50, 100, 200].
    """

    SHIFTS = [0.0, 10.0, 50.0, 100.0, 200.0]

    def test_w1_monotone_with_shift(self) -> None:
        estimates = []
        for shift in self.SHIFTS:
            rng = np.random.default_rng(65)
            result = _run(
                lambda n, r: r.normal(100, 20, n),
                lambda n, r, s=shift: r.normal(100 + s, 20, n),
                100,
                rng,
            )
            assert result.w1_estimate is not None
            estimates.append(result.w1_estimate)

        for i in range(len(estimates) - 1):
            assert estimates[i] <= estimates[i + 1], (
                f"W₁ not monotone: shift[{i}]={self.SHIFTS[i]} → "
                f"W₁={estimates[i]:.2f}, "
                f"shift[{i+1}]={self.SHIFTS[i+1]} → W₁={estimates[i+1]:.2f}"
            )


# ---------------------------------------------------------------------------
# 12. Permutation test Type I error rate at n=50
# ---------------------------------------------------------------------------

class TestPermutationTypeIError:
    """
    Under H₀ (P=Q), the permutation test Type I error rate should be ≈ α=0.05.
    We run 200 trials and check the empirical rejection rate is close to 5%.
    A loose tolerance [0.01, 0.12] avoids false failures from Monte Carlo variance.
    """

    N_TRIALS = 200
    ALPHA = 0.05
    TOLERANCE_LO = 0.01
    TOLERANCE_HI = 0.12

    def test_type1_error_at_n50(self) -> None:
        rejections = 0
        for trial in range(self.N_TRIALS):
            rng = np.random.default_rng(trial + 1000)
            result = _run(
                lambda n, r: r.normal(100, 20, n),
                lambda n, r: r.normal(100, 20, n),
                50,
                rng,
                seed=trial,
                n_permutations=1_000,   # reduced for speed; still valid Type I check
                n_bootstrap=100,
            )
            if result.permutation_significant:
                rejections += 1

        empirical_rate = rejections / self.N_TRIALS
        assert self.TOLERANCE_LO <= empirical_rate <= self.TOLERANCE_HI, (
            f"Type I error rate {empirical_rate:.3f} outside [{self.TOLERANCE_LO}, "
            f"{self.TOLERANCE_HI}]. Expected ≈ {self.ALPHA}."
        )


# ---------------------------------------------------------------------------
# 13. Dataclass fields — schema completeness
# ---------------------------------------------------------------------------

class TestResultSchema:
    """Verify CIDResult fields match the frozen schema in the spec."""

    def test_reliable_result_has_all_fields_populated(self) -> None:
        rng = np.random.default_rng(91)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(150, 20, n),
            100,
            rng,
        )
        assert result.grade == CIDGrade.RELIABLE
        assert result.w1_estimate is not None
        assert result.w1_ci_lower is not None
        assert result.w1_ci_upper is not None
        assert result.w1_ci_width is not None
        assert result.tv_diagnostic is not None
        assert result.permutation_pvalue is not None
        assert result.permutation_b == 10_000
        assert result.permutation_significant is not None
        assert result.n_baseline == 100
        assert result.n_post == 100
        assert result.theta_cid >= 0.0
        assert result.exceeds_threshold is not None

    def test_permutation_b_matches_requested(self) -> None:
        rng = np.random.default_rng(93)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(150, 20, n),
            100,
            rng,
            n_permutations=500,
        )
        assert result.permutation_b == 500

    def test_ci_lower_le_estimate_le_upper(self) -> None:
        rng = np.random.default_rng(95)
        result = _run(
            lambda n, r: r.normal(100, 20, n),
            lambda n, r: r.normal(150, 20, n),
            100,
            rng,
        )
        assert result.w1_ci_lower <= result.w1_estimate   # type: ignore[operator]
        assert result.w1_estimate  <= result.w1_ci_upper  # type: ignore[operator]

    def test_intervention_record_id_propagated(self) -> None:
        rng = np.random.default_rng(97)
        baseline = rng.normal(100, 20, 100)
        post     = rng.normal(150, 20, 100)
        result = compute_cid(
            baseline_samples=baseline,
            post_intervention_samples=post,
            source_variable="X",
            target_variable="Y",
            t_intervention=0.0,
            intervention_record_id="INT-001",
            n_permutations=1000,
            n_bootstrap=200,
        )
        assert result.intervention_record_id == "INT-001"

    def test_alpha_stored_in_result(self) -> None:
        rng = np.random.default_rng(99)
        baseline = rng.normal(100, 20, 100)
        post     = rng.normal(150, 20, 100)
        result = compute_cid(
            baseline_samples=baseline,
            post_intervention_samples=post,
            source_variable="X",
            target_variable="Y",
            t_intervention=0.0,
            alpha=0.01,
            n_permutations=1000,
            n_bootstrap=200,
        )
        assert result.alpha == 0.01

    def test_tv_in_unit_interval(self) -> None:
        for seed in range(5):
            rng = np.random.default_rng(seed + 200)
            result = _run(
                lambda n, r: r.normal(100, 20, n),
                lambda n, r: r.normal(150, 20, n),
                100,
                rng,
                seed=seed,
            )
            assert result.tv_diagnostic is not None
            assert 0.0 <= result.tv_diagnostic <= 1.0, (
                f"TV={result.tv_diagnostic} outside [0,1]"
            )


# ---------------------------------------------------------------------------
# 14. theta_cid threshold calibration
# ---------------------------------------------------------------------------

class TestThresholdCalibration:
    """θ_cid = 0.1 × IQR_baseline (Section 6)."""

    def test_theta_cid_equals_01_times_iqr(self) -> None:
        rng = np.random.default_rng(101)
        baseline = rng.normal(100, 20, 300)
        post     = rng.normal(150, 20, 300)
        result = compute_cid(
            baseline_samples=baseline,
            post_intervention_samples=post,
            source_variable="X",
            target_variable="Y",
            t_intervention=0.0,
            n_permutations=1000,
            n_bootstrap=200,
        )
        iqr = float(np.percentile(baseline, 75) - np.percentile(baseline, 25))
        expected_theta = 0.1 * iqr
        assert math.isclose(result.theta_cid, expected_theta, rel_tol=1e-9)

    def test_theta_cid_available_for_insufficient(self) -> None:
        """theta_cid is computed from baseline even when grade is INSUFFICIENT."""
        rng = np.random.default_rng(103)
        baseline = rng.normal(100, 20, 5)
        post     = rng.normal(200, 20, 5)
        result = compute_cid(
            baseline_samples=baseline,
            post_intervention_samples=post,
            source_variable="X",
            target_variable="Y",
            t_intervention=0.0,
            n_permutations=1000,
            n_bootstrap=200,
        )
        assert result.grade == CIDGrade.INSUFFICIENT
        assert result.theta_cid >= 0.0  # computed but metric fields are None


# ---------------------------------------------------------------------------
# 15. Reproducibility
# ---------------------------------------------------------------------------

class TestReproducibility:
    """Same seed must produce identical results."""

    def test_same_seed_same_result(self) -> None:
        def _compute() -> CIDResult:
            rng = np.random.default_rng(777)
            baseline = rng.normal(100, 20, 100)
            post     = rng.normal(150, 20, 100)
            return compute_cid(
                baseline_samples=baseline,
                post_intervention_samples=post,
                source_variable="X",
                target_variable="Y",
                t_intervention=0.0,
                seed=42,
                n_permutations=1000,
                n_bootstrap=200,
            )

        r1 = _compute()
        r2 = _compute()
        assert r1.w1_estimate == r2.w1_estimate
        assert r1.permutation_pvalue == r2.permutation_pvalue
        assert r1.w1_ci_lower == r2.w1_ci_lower
        assert r1.w1_ci_upper == r2.w1_ci_upper
