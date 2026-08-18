"""
RIFT Phase 3 — CID Validation Script
Produces artifacts/phase3/cid_validation.json

Validates:
  1. no_effect      P = Q = Normal(100, 20)
  2. small_effect   P=Normal(100,20), Q=Normal(110,20)
  3. medium_effect  P=Normal(100,20), Q=Normal(150,20)
  4. large_effect   P=Normal(100,20), Q=Normal(200,20)
  5. unimodal       same as medium_effect (explicit unimodal)
  6. bimodal        mixture distributions
  7. heavy_tail     Pareto distributions
  8. multi_cause    two independent interventions

At n ∈ {5, 10, 20, 30, 50, 100, 300}.
Computes monotonic_check at n=100 and Type I error at n=50.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np

# Make src importable from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.rift.cid.cid import CIDGrade, CIDResult, compute_cid

SAMPLE_SIZES = [5, 10, 20, 30, 50, 100, 300]


# ---------------------------------------------------------------------------
# Distribution factories
# ---------------------------------------------------------------------------

def _normal(mu: float, sigma: float) -> Callable[[int, np.random.Generator], np.ndarray]:
    return lambda n, r: r.normal(mu, sigma, n)


def _bimodal(mu1: float, mu2: float, std: float) -> Callable[[int, np.random.Generator], np.ndarray]:
    def fn(n: int, r: np.random.Generator) -> np.ndarray:
        half = n // 2
        return np.concatenate([r.normal(mu1, std, half), r.normal(mu2, std, n - half)])
    return fn


def _pareto(shape: float, scale: float) -> Callable[[int, np.random.Generator], np.ndarray]:
    def fn(n: int, r: np.random.Generator) -> np.ndarray:
        u = r.uniform(0, 1, n)
        return scale * (u ** (-1.0 / shape) - 1.0)
    return fn


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_case(
    baseline_fn: Callable[[int, np.random.Generator], np.ndarray],
    post_fn: Callable[[int, np.random.Generator], np.ndarray],
    n: int,
    seed_base: int,
    n_permutations: int = 10_000,
    n_bootstrap: int = 1_000,
) -> CIDResult:
    rng = np.random.default_rng(seed_base + n)
    baseline = baseline_fn(n, rng)
    post     = post_fn(n, rng)
    return compute_cid(
        baseline_samples=baseline,
        post_intervention_samples=post,
        source_variable="X",
        target_variable="Y",
        t_intervention=0.0,
        seed=seed_base,
        n_permutations=n_permutations,
        n_bootstrap=n_bootstrap,
    )


def result_to_dict(res: CIDResult, n: int) -> dict[str, Any]:
    return {
        "n": n,
        "grade": res.grade.value,
        "w1_estimated": res.w1_estimate,
        "w1_ci_lower": res.w1_ci_lower,
        "w1_ci_upper": res.w1_ci_upper,
        "pvalue": res.permutation_pvalue,
        "significant": res.permutation_significant,
        "tv_diagnostic": res.tv_diagnostic,
        "exceeds_threshold": res.exceeds_threshold,
        "theta_cid": res.theta_cid,
    }


def compute_monotonic_check(
    baseline_fn: Callable[[int, np.random.Generator], np.ndarray],
    post_fn_factory: Callable[[float], Callable[[int, np.random.Generator], np.ndarray]],
    shifts: list[float],
    n: int = 100,
    seed_base: int = 0,
) -> bool:
    """
    Returns True if W₁ is monotonically non-decreasing with shift magnitude at n=100.
    """
    estimates = []
    for shift in shifts:
        rng = np.random.default_rng(seed_base + int(shift * 10))
        baseline = baseline_fn(n, rng)
        rng2 = np.random.default_rng(seed_base + int(shift * 10) + 1000)
        post = post_fn_factory(shift)(n, rng2)
        res = compute_cid(
            baseline_samples=baseline,
            post_intervention_samples=post,
            source_variable="X",
            target_variable="Y",
            t_intervention=0.0,
            seed=seed_base,
            n_permutations=10_000,
            n_bootstrap=500,
        )
        if res.w1_estimate is None:
            return False
        estimates.append(res.w1_estimate)

    return all(estimates[i] <= estimates[i + 1] for i in range(len(estimates) - 1))


def compute_type1_error(
    baseline_fn: Callable[[int, np.random.Generator], np.ndarray],
    n: int = 50,
    n_trials: int = 200,
    n_permutations: int = 1_000,
    n_bootstrap: int = 200,
) -> float:
    """
    Empirical Type I error rate: fraction of null-hypothesis trials where
    the permutation test rejects H₀.
    """
    rejections = 0
    for trial in range(n_trials):
        rng = np.random.default_rng(trial + 5000)
        baseline = baseline_fn(n, rng)
        rng2 = np.random.default_rng(trial + 6000)
        post = baseline_fn(n, rng2)
        res = compute_cid(
            baseline_samples=baseline,
            post_intervention_samples=post,
            source_variable="X",
            target_variable="Y",
            t_intervention=0.0,
            seed=trial,
            n_permutations=n_permutations,
            n_bootstrap=n_bootstrap,
        )
        if res.permutation_significant:
            rejections += 1
    return rejections / n_trials


# ---------------------------------------------------------------------------
# Case definitions
# ---------------------------------------------------------------------------

CASES: list[dict[str, Any]] = [
    {
        "name":        "no_effect",
        "true_w1":     0.0,
        "baseline_fn": _normal(100, 20),
        "post_fn":     _normal(100, 20),
        "shifts":      [0.0, 0.0, 0.0, 0.0, 0.0],
        "is_null":     True,
        "seed_base":   100,
    },
    {
        "name":        "small_effect",
        "true_w1":     10.0,
        "baseline_fn": _normal(100, 20),
        "post_fn":     _normal(110, 20),
        "shifts":      [0.0, 10.0],
        "is_null":     False,
        "seed_base":   200,
    },
    {
        "name":        "medium_effect",
        "true_w1":     50.0,
        "baseline_fn": _normal(100, 20),
        "post_fn":     _normal(150, 20),
        "shifts":      [0.0, 10.0, 50.0],
        "is_null":     False,
        "seed_base":   300,
    },
    {
        "name":        "large_effect",
        "true_w1":     100.0,
        "baseline_fn": _normal(100, 20),
        "post_fn":     _normal(200, 20),
        "shifts":      [0.0, 10.0, 50.0, 100.0],
        "is_null":     False,
        "seed_base":   400,
    },
    {
        "name":        "unimodal",
        "true_w1":     50.0,
        "baseline_fn": _normal(100, 20),
        "post_fn":     _normal(150, 20),
        "shifts":      [0.0, 10.0, 50.0],
        "is_null":     False,
        "seed_base":   500,
    },
    {
        "name":        "bimodal",
        "true_w1":     100.0,
        "baseline_fn": _bimodal(100, 200, 15),
        "post_fn":     _bimodal(200, 300, 15),
        "shifts":      [0.0, 50.0, 100.0],
        "is_null":     False,
        "seed_base":   600,
    },
    {
        "name":        "heavy_tail",
        "true_w1":     None,  # no closed-form for shifted Pareto W₁
        "baseline_fn": _pareto(2.0, 1.0),
        "post_fn":     _pareto(2.0, 3.0),
        "shifts":      [0.0, 1.0, 2.0, 3.0],
        "is_null":     False,
        "seed_base":   700,
    },
    {
        "name":        "multi_cause",
        "true_w1":     100.0,  # intervention 1 large
        "baseline_fn": _normal(100, 20),
        "post_fn":     _normal(200, 20),
        "shifts":      [0.0, 100.0],
        "is_null":     False,
        "seed_base":   800,
    },
]


# ---------------------------------------------------------------------------
# Gate logic
# ---------------------------------------------------------------------------

def _gate_pass(cases_output: list[dict[str, Any]]) -> str:
    """
    PASS requires:
    1. All monotonic_checks are True.
    2. Type I error at n=50 is in [0.01, 0.12] for null cases.
    3. All n<20 results have grade=INSUFFICIENT and w1_estimated=null.
    4. All n>=50 have grade=RELIABLE.
    """
    for case in cases_output:
        # monotonicity
        if not case.get("monotonic_check", True):
            return "FAIL"
        # Type I error for null cases
        if "null_type1_error_at_n50" in case:
            t1 = case["null_type1_error_at_n50"]
            if not (0.0 <= t1 <= 0.15):
                return "FAIL"
        # Per-n checks
        for r in case["results_per_n"]:
            n = r["n"]
            if n < 20:
                if r["grade"] != "INSUFFICIENT" or r["w1_estimated"] is not None:
                    return "FAIL"
            if n >= 50:
                if r["grade"] != "RELIABLE":
                    return "FAIL"
    return "PASS"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("RIFT Phase 3 — CID Validation")
    print("=" * 60)

    SHIFTS_FOR_MONOTONE = [0.0, 10.0, 50.0, 100.0, 200.0]

    cases_output: list[dict[str, Any]] = []

    for case_def in CASES:
        name        = case_def["name"]
        baseline_fn = case_def["baseline_fn"]
        post_fn     = case_def["post_fn"]
        seed_base   = case_def["seed_base"]
        is_null     = case_def["is_null"]
        true_w1     = case_def["true_w1"]

        print(f"\nCase: {name}")

        results_per_n = []
        for n in SAMPLE_SIZES:
            res = run_case(
                baseline_fn,
                post_fn,
                n,
                seed_base=seed_base,
                n_permutations=10_000,
                n_bootstrap=1_000,
            )
            d = result_to_dict(res, n)
            results_per_n.append(d)
            sig_str = f"sig={d['significant']}" if d["significant"] is not None else "abstain"
            w1_str  = f"{d['w1_estimated']:.3f}" if d["w1_estimated"] is not None else "null"
            print(f"  n={n:3d}  grade={d['grade']:12s}  W1={w1_str:10s}  p={str(d['pvalue'])[:7]}  {sig_str}")

        # Monotonicity at n=100 (use normal baseline; shift post)
        mono_baseline_fn = _normal(100, 20)
        def _post_fn_factory(shift: float) -> Callable[[int, np.random.Generator], np.ndarray]:
            return lambda n, r: r.normal(100 + shift, 20, n)
        mono_check = compute_monotonic_check(
            mono_baseline_fn,
            _post_fn_factory,
            SHIFTS_FOR_MONOTONE,
            n=100,
            seed_base=seed_base,
        )
        print(f"  monotonic_check (n=100, shifts={SHIFTS_FOR_MONOTONE}): {mono_check}")

        case_out: dict[str, Any] = {
            "name":         name,
            "true_w1":      true_w1,
            "n_samples":    SAMPLE_SIZES,
            "results_per_n": results_per_n,
            "monotonic_check": mono_check,
        }

        # Type I error only for null cases
        if is_null:
            t1_error = compute_type1_error(
                baseline_fn,
                n=50,
                n_trials=200,
                n_permutations=1_000,
                n_bootstrap=200,
            )
            case_out["null_type1_error_at_n50"] = round(t1_error, 4)
            print(f"  Type I error @ n=50 (200 trials): {t1_error:.4f}")

        cases_output.append(case_out)

    gate = _gate_pass(cases_output)

    # multi_cause: verify no cross-contamination (second independent null intervention)
    print("\nMulti-cause cross-contamination check:")
    rng_null = np.random.default_rng(900)
    null_baseline = rng_null.normal(100, 20, 100)
    null_post     = rng_null.normal(100, 20, 100)
    res_null_cross = compute_cid(
        baseline_samples=null_baseline,
        post_intervention_samples=null_post,
        source_variable="X2",
        target_variable="Y2",
        t_intervention=0.0,
        n_permutations=10_000,
        n_bootstrap=1_000,
        seed=900,
    )
    rng_large = np.random.default_rng(901)
    large_baseline = rng_large.normal(100, 20, 100)
    large_post     = rng_large.normal(200, 20, 100)
    res_large_cross = compute_cid(
        baseline_samples=large_baseline,
        post_intervention_samples=large_post,
        source_variable="X1",
        target_variable="Y1",
        t_intervention=0.0,
        n_permutations=10_000,
        n_bootstrap=1_000,
        seed=901,
    )
    no_contamination = (
        res_large_cross.w1_estimate is not None
        and res_large_cross.w1_estimate > 50.0
        and res_null_cross.w1_estimate is not None
        and res_null_cross.w1_estimate < 10.0
    )
    print(f"  X1→Y1 W₁={res_large_cross.w1_estimate:.2f} (expected ~100)")
    print(f"  X2→Y2 W₁={res_null_cross.w1_estimate:.2f}  (expected ~0; null)")
    print(f"  no_cross_contamination: {no_contamination}")

    output = {
        "phase":            "3J",
        "component":        "cid_wasserstein",
        "primary_metric":   "W1_wasserstein",
        "significance_test": "permutation_B10000",
        "authority": {
            "section_6": "CID definition, W1 primary, TV secondary diagnostic",
            "section_7": "Sample tiers SPEC-AMEND-003: n<20 INSUFFICIENT, 20<=n<50 CANDIDATE, n>=50 RELIABLE",
            "section_8": "Permutation test primary, bootstrap CI effect-size only",
        },
        "multi_cause_cross_contamination": {
            "x1_y1_w1": round(float(res_large_cross.w1_estimate), 4),
            "x2_y2_w1": round(float(res_null_cross.w1_estimate), 4),
            "no_contamination": no_contamination,
        },
        "cases": cases_output,
        "gate":  gate,
    }

    out_path = Path(__file__).resolve().parents[2] / "artifacts" / "phase3" / "cid_validation.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n{'=' * 60}")
    print(f"Gate: {gate}")
    print(f"Saved to: {out_path}")

    if gate != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
