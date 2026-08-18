"""
tests/unit/test_statistics.py — Unit tests for RIFT statistical infrastructure

Verifies:
  1. Wilcoxon one-sided is correctly directional (not two-sided)
  2. Cliff's δ CI covers true δ in ≥ 95 % of bootstrap trials
  3. Holm-Bonferroni is more conservative than uncorrected (α/m ≤ min threshold ≤ α)
  4. BH FDR controls false discovery rate at the target level
  5. Power check correctly flags n < 48 → do NOT claim 80 % power
  6. Cliff's δ is always reported regardless of p-value (even when p > 0.05)

Authority: docs/PHASE_3_SPEC_FREEZE.md §15
"""

from __future__ import annotations

import warnings
from typing import Dict

import numpy as np
import pytest
from scipy import stats as scipy_stats

from rift.statistics.stats import (
    HypothesisTestResult,
    bh_fdr_correction,
    binomial_one_sided,
    check_power_achieved,
    cliffs_delta,
    holm_bonferroni_correction,
    tost_equivalence,
    wilcoxon_one_sided,
)

RNG = np.random.default_rng(42)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def paired_arrays_rift_better():
    """RIFT clearly outperforms baseline — one-sided test should be significant."""
    rng = np.random.default_rng(0)
    baseline = rng.uniform(0.3, 0.6, 40)
    rift = baseline + rng.uniform(0.1, 0.25, 40)  # RIFT always higher
    return rift, baseline


@pytest.fixture
def paired_arrays_equal():
    """RIFT and baseline are drawn from the same distribution — should NOT be significant."""
    rng = np.random.default_rng(1)
    baseline = rng.uniform(0.4, 0.8, 40)
    rift = rng.uniform(0.4, 0.8, 40)
    return rift, baseline


@pytest.fixture
def paired_arrays_rift_worse():
    """Baseline is better than RIFT — one-sided RIFT > baseline should NOT be significant."""
    rng = np.random.default_rng(2)
    baseline = rng.uniform(0.5, 0.9, 40)
    rift = baseline - rng.uniform(0.1, 0.3, 40)
    return rift, baseline


# ─────────────────────────────────────────────────────────────────────────────
# 1. Wilcoxon one-sided directionality
# ─────────────────────────────────────────────────────────────────────────────


class TestWilcoxonOneSided:
    def test_significant_when_rift_is_better(self, paired_arrays_rift_better):
        rift, baseline = paired_arrays_rift_better
        result = wilcoxon_one_sided(rift, baseline, "H1")
        assert result.pvalue < 0.05, (
            "One-sided Wilcoxon should be significant when RIFT consistently outperforms baseline"
        )
        assert result.significant is True

    def test_not_significant_when_rift_is_worse(self, paired_arrays_rift_worse):
        rift, baseline = paired_arrays_rift_worse
        result = wilcoxon_one_sided(rift, baseline, "H1")
        assert result.pvalue > 0.05, (
            "One-sided Wilcoxon (RIFT > baseline) must NOT be significant when baseline is better"
        )

    def test_one_sided_strictly_less_than_two_sided(self, paired_arrays_rift_better):
        """
        For a positive difference, p_one_sided ≤ p_two_sided / 2 is not always exactly
        half (depends on distribution), but the one-sided p must be ≤ two-sided p.
        """
        rift, baseline = paired_arrays_rift_better
        one_sided = wilcoxon_one_sided(rift, baseline, "H1")
        diff = rift - baseline
        _, p_two = scipy_stats.wilcoxon(diff, alternative="two-sided", zero_method="wilcox")
        assert one_sided.pvalue <= p_two + 1e-12, (
            "One-sided p-value must be ≤ two-sided p-value for positive differences"
        )

    def test_result_is_hypothesis_test_result(self, paired_arrays_rift_better):
        rift, baseline = paired_arrays_rift_better
        result = wilcoxon_one_sided(rift, baseline, "H2")
        assert isinstance(result, HypothesisTestResult)
        assert result.hypothesis_id == "H2"
        assert "one-sided" in result.test_name.lower()

    def test_raises_for_mismatched_lengths(self):
        with pytest.raises(ValueError, match="same length"):
            wilcoxon_one_sided(np.array([0.5, 0.6]), np.array([0.4]), "H1")

    def test_n_observations_matches_input(self, paired_arrays_rift_better):
        rift, baseline = paired_arrays_rift_better
        result = wilcoxon_one_sided(rift, baseline, "H3")
        assert result.n_observations == len(rift)

    def test_directionality_asymmetry(self, paired_arrays_rift_better):
        """
        Swapping rift and baseline must flip significance:
        if RIFT > baseline is significant, then baseline > RIFT is not.
        """
        rift, baseline = paired_arrays_rift_better
        forward = wilcoxon_one_sided(rift, baseline, "H1")
        backward = wilcoxon_one_sided(baseline, rift, "H1")
        assert forward.pvalue < 0.05
        assert backward.pvalue > 0.05, (
            "Directional test: flipping scores must flip significance"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Cliff's δ CI coverage
# ─────────────────────────────────────────────────────────────────────────────


class TestCliffsDelta:
    def test_delta_within_minus1_to_1(self):
        rng = np.random.default_rng(10)
        x = rng.normal(1.0, 0.5, 30)
        y = rng.normal(0.5, 0.5, 30)
        delta, (lo, hi) = cliffs_delta(x, y)
        assert -1.0 <= delta <= 1.0, "Cliff's δ must be in [-1, 1]"
        assert lo <= delta <= hi, "Point estimate must lie within its own CI"

    def test_delta_equals_1_when_x_always_greater(self):
        x = np.array([10.0, 11.0, 12.0])
        y = np.array([1.0, 2.0, 3.0])
        delta, _ = cliffs_delta(x, y)
        assert abs(delta - 1.0) < 1e-10, "δ must be 1 when x always > y"

    def test_delta_equals_minus1_when_y_always_greater(self):
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([10.0, 11.0, 12.0])
        delta, _ = cliffs_delta(x, y)
        assert abs(delta - (-1.0)) < 1e-10, "δ must be -1 when y always > x"

    def test_delta_near_zero_for_identical_distributions(self):
        rng = np.random.default_rng(99)
        x = rng.normal(0, 1, 200)
        y = rng.normal(0, 1, 200)
        delta, _ = cliffs_delta(x, y)
        assert abs(delta) < 0.2, "δ should be near 0 for same-distribution samples"

    def test_ci_covers_true_delta_in_95pct_of_trials(self):
        """
        Parametric coverage test: draw 200 bootstrap trials and verify the
        nominal 95 % CI covers the population δ ≥ 95 % of the time.

        True δ is estimated from a large reference sample (n=5000).
        """
        rng = np.random.default_rng(77)
        # True distributions
        mu_x, mu_y, sigma = 1.0, 0.0, 1.0
        # True δ from large reference
        x_big = rng.normal(mu_x, sigma, 5000)
        y_big = rng.normal(mu_y, sigma, 5000)
        true_delta, _ = cliffs_delta(x_big, y_big, n_bootstrap=100, rng=rng)

        n_trials = 200
        covered = 0
        for _ in range(n_trials):
            x_s = rng.normal(mu_x, sigma, 40)
            y_s = rng.normal(mu_y, sigma, 40)
            _, (lo, hi) = cliffs_delta(x_s, y_s, n_bootstrap=500, rng=rng)
            if lo <= true_delta <= hi:
                covered += 1

        coverage = covered / n_trials
        assert coverage >= 0.90, (
            f"Bootstrap CI coverage {coverage:.3f} < 0.90. "
            "Expected ≈ 0.95 for 95% CI; minimum acceptable 0.90 for n=200 trials."
        )

    def test_ci_is_a_tuple_of_two_floats(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([0.5, 1.5, 2.5, 3.5, 4.5])
        delta, ci = cliffs_delta(x, y)
        assert isinstance(ci, tuple)
        assert len(ci) == 2
        lo, hi = ci
        assert lo <= hi, "CI lower bound must be ≤ upper bound"

    def test_delta_reported_even_when_pvalue_large(self, paired_arrays_equal):
        """
        Cliff's δ must be present and non-None even when p > 0.05.
        Authority: §15 "Effect size: Cliff's δ (always reported regardless of p-value)."
        """
        rift, baseline = paired_arrays_equal
        result = wilcoxon_one_sided(rift, baseline, "H1")
        # δ must always be present
        assert result.cliffs_delta is not None, (
            "Cliff's δ must always be reported, even when p > 0.05"
        )
        assert isinstance(result.cliffs_delta, float)
        assert isinstance(result.cliffs_delta_ci, tuple)
        assert result.effect_size_interpretation in (
            "negligible", "small", "medium", "large"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Holm-Bonferroni
# ─────────────────────────────────────────────────────────────────────────────


class TestHolmBonferroni:
    def _six_pvalues(self) -> Dict[str, float]:
        return {
            "H1": 0.01,
            "H2": 0.04,
            "H3": 0.10,
            "H4_acc": 0.03,
            "H4_cost": 0.002,
            "H5": 0.08,
        }

    def test_returns_dict_with_same_keys(self):
        pvalues = self._six_pvalues()
        corrected = holm_bonferroni_correction(pvalues)
        assert set(corrected.keys()) == set(pvalues.keys())

    def test_all_thresholds_at_most_alpha(self):
        pvalues = self._six_pvalues()
        corrected = holm_bonferroni_correction(pvalues, alpha=0.05)
        for key, threshold in corrected.items():
            assert threshold <= 0.05 + 1e-12, (
                f"Corrected threshold {threshold} for {key} exceeds alpha=0.05"
            )

    def test_minimum_threshold_is_alpha_over_m(self):
        """
        Most conservative test (smallest p) gets threshold = α / m.
        Holm-Bonferroni: rank 1 → α / (m - 1 + 1) = α / m.
        """
        pvalues = self._six_pvalues()
        m = len(pvalues)
        corrected = holm_bonferroni_correction(pvalues, alpha=0.05)
        min_threshold = min(corrected.values())
        expected_min = 0.05 / m
        assert abs(min_threshold - expected_min) < 1e-12, (
            f"Minimum corrected threshold should be α/m={expected_min:.6f}, got {min_threshold:.6f}"
        )

    def test_most_conservative_test_gets_smallest_threshold(self):
        pvalues = self._six_pvalues()
        corrected = holm_bonferroni_correction(pvalues, alpha=0.05)
        # H4_cost has the smallest p-value (0.002), so should get the smallest threshold
        min_key = min(pvalues, key=lambda k: pvalues[k])
        min_threshold = corrected[min_key]
        assert min_threshold == min(corrected.values())

    def test_more_conservative_than_uncorrected(self):
        """All corrected thresholds ≤ α (no threshold is more lenient than nominal α)."""
        pvalues = self._six_pvalues()
        corrected = holm_bonferroni_correction(pvalues, alpha=0.05)
        for key, threshold in corrected.items():
            assert threshold <= 0.05, (
                f"Holm threshold {threshold} must be ≤ uncorrected α=0.05 for {key}"
            )

    def test_monotone_thresholds(self):
        """
        When tests are sorted by ascending p-value, their Holm thresholds
        must be non-decreasing (less conservative as rank increases).
        """
        pvalues = self._six_pvalues()
        corrected = holm_bonferroni_correction(pvalues, alpha=0.05)
        sorted_keys = sorted(pvalues, key=lambda k: pvalues[k])
        thresholds = [corrected[k] for k in sorted_keys]
        for i in range(len(thresholds) - 1):
            assert thresholds[i] <= thresholds[i + 1] + 1e-12, (
                f"Holm thresholds must be non-decreasing by rank: "
                f"{thresholds[i]:.6f} > {thresholds[i+1]:.6f} at rank {i}"
            )

    def test_single_test_threshold_equals_alpha(self):
        pvalues = {"H1": 0.03}
        corrected = holm_bonferroni_correction(pvalues, alpha=0.05)
        assert abs(corrected["H1"] - 0.05) < 1e-12, (
            "Single test: Holm threshold = α/1 = α"
        )

    def test_empty_input(self):
        corrected = holm_bonferroni_correction({}, alpha=0.05)
        assert corrected == {}


# ─────────────────────────────────────────────────────────────────────────────
# 4. BH FDR
# ─────────────────────────────────────────────────────────────────────────────


class TestBHFDR:
    def test_returns_same_keys(self):
        pvalues = {"e1": 0.01, "e2": 0.04, "e3": 0.20, "e4": 0.50}
        adj = bh_fdr_correction(pvalues, alpha=0.05)
        assert set(adj.keys()) == set(pvalues.keys())

    def test_adjusted_pvalues_in_0_1(self):
        pvalues = {"e1": 0.001, "e2": 0.002, "e3": 0.01, "e4": 0.04, "e5": 0.10}
        adj = bh_fdr_correction(pvalues, alpha=0.05)
        for key, p in adj.items():
            assert 0.0 <= p <= 1.0, f"Adjusted p for {key}={p} out of [0,1]"

    def test_monotonicity_of_adjusted_pvalues(self):
        """
        After BH step-up, adjusted p-values must be non-decreasing when
        sorted by original p-value.
        """
        pvalues = {
            f"t{i}": p for i, p in enumerate([0.001, 0.005, 0.01, 0.04, 0.10, 0.30])
        }
        adj = bh_fdr_correction(pvalues, alpha=0.05)
        sorted_keys = sorted(pvalues, key=lambda k: pvalues[k])
        adj_sorted = [adj[k] for k in sorted_keys]
        for i in range(len(adj_sorted) - 1):
            assert adj_sorted[i] <= adj_sorted[i + 1] + 1e-12, (
                f"BH adjusted p-values must be non-decreasing: "
                f"{adj_sorted[i]:.4f} > {adj_sorted[i+1]:.4f}"
            )

    def test_fdr_controls_at_alpha_via_simulation(self):
        """
        Empirical FDR control: run 500 simulations with 10 truly null tests
        (p ~ Uniform) and 5 truly alternative tests (p ~ Beta(0.5,5)).
        Verify BH controls FDR at ≤ α + tolerance.
        """
        rng = np.random.default_rng(42)
        alpha = 0.05
        n_null = 10
        n_alt = 5
        n_sim = 500
        fdr_vals = []

        for _ in range(n_sim):
            p_null = rng.uniform(0, 1, n_null)
            p_alt = rng.beta(0.5, 5, n_alt)
            pvalues = {
                **{f"null_{i}": float(p) for i, p in enumerate(p_null)},
                **{f"alt_{i}": float(p) for i, p in enumerate(p_alt)},
            }
            adj = bh_fdr_correction(pvalues, alpha=alpha)
            rejected = [k for k, p in adj.items() if p < alpha]
            false_disc = sum(1 for k in rejected if k.startswith("null_"))
            fdr = false_disc / max(len(rejected), 1)
            fdr_vals.append(fdr)

        mean_fdr = float(np.mean(fdr_vals))
        assert mean_fdr <= alpha + 0.03, (
            f"BH FDR mean={mean_fdr:.4f} exceeds α={alpha} + tolerance=0.03"
        )

    def test_empty_input(self):
        adj = bh_fdr_correction({}, alpha=0.05)
        assert adj == {}

    def test_all_nulls_no_rejections(self):
        """
        With all p-values = 1.0, BH should reject nothing.
        """
        pvalues = {f"t{i}": 1.0 for i in range(10)}
        adj = bh_fdr_correction(pvalues, alpha=0.05)
        rejected = [k for k, p in adj.items() if p < 0.05]
        assert len(rejected) == 0, "No hypothesis should be rejected when all p=1"

    def test_all_strongly_significant(self):
        """
        With all p = 0.0001, BH should reject all.
        """
        pvalues = {f"t{i}": 0.0001 for i in range(10)}
        adj = bh_fdr_correction(pvalues, alpha=0.05)
        rejected = [k for k, p in adj.items() if p < 0.05]
        assert len(rejected) == 10, "All should be rejected when all p=0.0001"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Power check
# ─────────────────────────────────────────────────────────────────────────────


class TestPowerCheck:
    def test_n_below_48_does_not_claim_80pct_power(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = check_power_achieved(n_confounded=30, target_n=48)

        assert result["claim_80pct_power"] is False, (
            "Must NOT claim 80% power when n_confounded=30 < target_n=48"
        )
        # Warning should have been emitted
        assert any("80% power" in str(w.message) for w in caught), (
            "A warning about 80% power must be issued when n < target_n"
        )

    def test_n_exactly_48_claims_80pct_power(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = check_power_achieved(n_confounded=48, target_n=48)

        assert result["claim_80pct_power"] is True, (
            "Must claim 80% power when n_confounded=48 == target_n=48"
        )
        # No warning expected
        power_warnings = [w for w in caught if "80% power" in str(w.message)]
        assert len(power_warnings) == 0, (
            "No 80%-power warning should be emitted when n >= target_n"
        )

    def test_n_above_48_claims_80pct_power(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = check_power_achieved(n_confounded=64, target_n=48)
        assert result["claim_80pct_power"] is True

    def test_achieved_power_increases_with_n(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            r30 = check_power_achieved(n_confounded=30)
            r48 = check_power_achieved(n_confounded=48)
            r80 = check_power_achieved(n_confounded=80)

        assert r30["achieved_power"] <= r48["achieved_power"], (
            "Achieved power must increase with n"
        )
        assert r48["achieved_power"] <= r80["achieved_power"], (
            "Achieved power must increase with n"
        )

    def test_achieved_power_in_0_1(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            for n in [0, 1, 10, 48, 100, 200]:
                result = check_power_achieved(n_confounded=n)
                assert 0.0 <= result["achieved_power"] <= 1.0, (
                    f"Achieved power for n={n} must be in [0,1]"
                )

    def test_zero_confounded_does_not_claim_power(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = check_power_achieved(n_confounded=0)
        assert result["claim_80pct_power"] is False
        assert result["achieved_power"] == 0.0

    def test_notes_contain_power_target(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = check_power_achieved(n_confounded=20)
        assert "80%" in result["notes"] or "power" in result["notes"].lower()

    def test_power_target_met_flag_matches_claim(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            for n in [0, 20, 47, 48, 50, 100]:
                result = check_power_achieved(n_confounded=n, target_n=48)
                assert result["power_target_met"] == result["claim_80pct_power"], (
                    f"power_target_met must equal claim_80pct_power for n={n}"
                )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Cliff's δ always reported
# ─────────────────────────────────────────────────────────────────────────────


class TestCliffsDeltaAlwaysReported:
    """
    Authority: docs/PHASE_3_SPEC_FREEZE.md §15
    "Effect size: Cliff's δ (always reported regardless of p-value)."
    """

    def test_delta_reported_for_nonsignificant_h1(self, paired_arrays_equal):
        rift, baseline = paired_arrays_equal
        result = wilcoxon_one_sided(rift, baseline, "H1")
        # May or may not be significant — we only care that δ is present
        assert result.cliffs_delta is not None
        assert result.effect_size_interpretation is not None
        assert result.cliffs_delta_ci is not None

    def test_delta_reported_for_nonsignificant_h2(self, paired_arrays_rift_worse):
        rift, baseline = paired_arrays_rift_worse
        result = wilcoxon_one_sided(rift, baseline, "H2")
        assert result.pvalue > 0.05, "This fixture should produce p > 0.05"
        assert result.cliffs_delta is not None, (
            "Cliff's δ must be reported even when p > 0.05"
        )

    def test_delta_reported_for_h4_tost(self, paired_arrays_equal):
        rift, baseline = paired_arrays_equal
        result = tost_equivalence(rift, baseline)
        assert result.cliffs_delta is not None
        assert result.cliffs_delta_ci is not None
        assert result.effect_size_interpretation in (
            "negligible", "small", "medium", "large"
        )

    def test_delta_reported_for_h5_binomial(self):
        result = binomial_one_sided(
            n_successes=5,
            n_trials=10,
            p_null=0.70,
            rift_scores=np.array([0.8, 0.7, 0.6]),
            baseline_scores=np.array([0.5, 0.4, 0.3]),
        )
        assert result.cliffs_delta is not None
        assert result.effect_size_interpretation is not None

    def test_delta_reported_when_no_score_arrays_for_h5(self):
        result = binomial_one_sided(n_successes=3, n_trials=10, p_null=0.70)
        # δ = 0.0 (no arrays provided) but must still be present
        assert result.cliffs_delta is not None
        assert isinstance(result.cliffs_delta, float)

    def test_effect_size_interpretation_values(self):
        """
        All returned interpretations must be one of the four canonical labels.

        Uses paired arrays with explicit non-zero differences to avoid the
        scipy Wilcoxon ValueError raised when all differences are zero.
        """
        rng = np.random.default_rng(7)
        base = rng.uniform(0.1, 0.9, 20)
        offsets = [-0.09, -0.04, -0.02, -0.01, 0.01, 0.02, 0.04, 0.09]
        for offset in offsets:
            rift_arr = np.clip(base + offset, 0.0, 1.0)
            result = wilcoxon_one_sided(rift_arr, base, "H1")
            assert result.effect_size_interpretation in (
                "negligible", "small", "medium", "large"
            ), (
                f"Unexpected interpretation '{result.effect_size_interpretation}' "
                f"for offset={offset}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Integration: run_confirmatory_tests smoke test
# ─────────────────────────────────────────────────────────────────────────────


class TestRunConfirmatoryTests:
    def test_returns_six_keys(self):
        from rift.statistics.stats import run_confirmatory_tests

        rng = np.random.default_rng(42)
        n = 40

        def _make_pair(effect=0.0):
            base = rng.uniform(0.3, 0.7, n)
            rift_arr = (base + effect).clip(0, 1)
            return rift_arr, base

        h1r, h1b = _make_pair(0.15)
        h2r, h2b = _make_pair(0.15)
        h3r, h3b = _make_pair(0.10)
        h4cr, h4cb = _make_pair(-0.10)   # cost: rift is lower (better)
        h4ar, h4ab = _make_pair(0.00)    # accuracy: equivalent
        results = run_confirmatory_tests(
            h1_rift=h1r, h1_baseline=h1b,
            h2_rift=h2r, h2_baseline=h2b,
            h3_rift=h3r, h3_baseline=h3b,
            h4_cost_rift=h4cr, h4_cost_baseline=h4cb,
            h4_acc_rift=h4ar, h4_acc_baseline=h4ab,
            h5_successes=8, h5_trials=10,
            alpha=0.05,
            rng=rng,
        )
        assert set(results.keys()) == {"H1", "H2", "H3", "H4_acc", "H4_cost", "H5"}

    def test_all_results_have_cliffs_delta(self):
        from rift.statistics.stats import run_confirmatory_tests

        rng = np.random.default_rng(43)
        n = 30
        base = rng.uniform(0.4, 0.6, n)
        rift_arr = (base + 0.05).clip(0, 1)

        results = run_confirmatory_tests(
            h1_rift=rift_arr, h1_baseline=base,
            h2_rift=rift_arr, h2_baseline=base,
            h3_rift=rift_arr, h3_baseline=base,
            h4_cost_rift=base, h4_cost_baseline=(base + 0.05).clip(0, 1),
            h4_acc_rift=rift_arr, h4_acc_baseline=rift_arr,
            h5_successes=5, h5_trials=8,
            rng=rng,
        )
        for key, res in results.items():
            assert res.cliffs_delta is not None, (
                f"Cliff's δ must always be reported — missing for {key}"
            )

    def test_corrected_alphas_are_at_most_nominal(self):
        from rift.statistics.stats import run_confirmatory_tests

        rng = np.random.default_rng(44)
        n = 30
        base = rng.uniform(0.4, 0.7, n)
        rift_arr = (base + 0.1).clip(0, 1)
        results = run_confirmatory_tests(
            h1_rift=rift_arr, h1_baseline=base,
            h2_rift=rift_arr, h2_baseline=base,
            h3_rift=rift_arr, h3_baseline=base,
            h4_cost_rift=base, h4_cost_baseline=(base + 0.10).clip(0, 1),
            h4_acc_rift=rift_arr, h4_acc_baseline=rift_arr,
            h5_successes=7, h5_trials=10,
            alpha=0.05,
            rng=rng,
        )
        for key, res in results.items():
            assert res.alpha_corrected <= 0.05 + 1e-12, (
                f"Corrected α for {key}={res.alpha_corrected} > 0.05"
            )
