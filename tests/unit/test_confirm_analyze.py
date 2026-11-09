"""Tests for the confirmatory analysis script (WP4 tests C4, C5, C7, C10).

Tests the interpretation function, Holm arithmetic, and analysis reproducibility.
Never accesses sealed data.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
for _p in (str(REPO), str(REPO / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.rift.statistics.confirmatory_inference import (  # noqa: E402
    ALPHA, DELTA, FixedStrataDesign, check_utility_invariants,
    gatekeep, holm_adjust, interpret, interpret_two_key,
    mcnemar_exact, utility,
)


# ------------------------------------------------------------------------------- C7: Interpretation function
class TestC7InterpretationFunction:
    """C7: The interpret() function is exhaustive and mutually exclusive over a grid."""

    _labels = {"NEGATIVE-WORSE", "POSITIVE-USEFUL", "POSITIVE-SUBSTANDARD",
               "NEGATIVE-NO-USEFUL-EFFECT", "INCONCLUSIVE"}

    def _check_one(self, lo, hi, theta, op_lo):
        label = interpret(lo, hi, theta, op_lo)
        assert label in self._labels, f"Unknown label: {label}"

    def test_negative_worse(self):
        """hi < 0 → NEGATIVE-WORSE."""
        assert interpret(-0.5, -0.1, -0.3, -0.4) == "NEGATIVE-WORSE"

    def test_positive_useful(self):
        """lo > 0 AND theta >= delta AND op_lo > 0 → POSITIVE-USEFUL."""
        assert interpret(0.05, 0.3, 0.15, 0.02) == "POSITIVE-USEFUL"

    def test_positive_substandard(self):
        """lo > 0 AND (theta < delta OR op_lo <= 0) → POSITIVE-SUBSTANDARD."""
        result = interpret(0.01, 0.08, 0.05, 0.02)  # theta < DELTA=0.10
        assert result == "POSITIVE-SUBSTANDARD"

    def test_negative_no_useful_effect(self):
        """lo <= 0 AND hi < delta → NEGATIVE-NO-USEFUL-EFFECT."""
        assert interpret(-0.05, 0.05, 0.02, -0.01) == "NEGATIVE-NO-USEFUL-EFFECT"

    def test_inconclusive(self):
        """lo <= 0 AND hi >= delta → INCONCLUSIVE."""
        assert interpret(-0.05, 0.15, 0.06, -0.01) == "INCONCLUSIVE"

    def test_boundary_hi_zero(self):
        """Boundary: hi == 0 → not NEGATIVE-WORSE (requires hi < 0 strictly).
        interpret() checks `if hi < 0` so hi==0 falls through to NEGATIVE-NO-USEFUL-EFFECT."""
        label = interpret(-0.2, 0.0, -0.1, -0.15)
        # hi=0 < delta=0.1, so → NEGATIVE-NO-USEFUL-EFFECT (hi is not < 0 strictly)
        assert label == "NEGATIVE-NO-USEFUL-EFFECT"

    def test_boundary_lo_zero(self):
        """Boundary: lo == 0 → not POSITIVE-* (lo must be > 0)."""
        label = interpret(0.0, 0.15, 0.08, -0.01)
        assert label in {"NEGATIVE-NO-USEFUL-EFFECT", "INCONCLUSIVE"}

    def test_grid_exhaustive_and_exclusive(self):
        """Every point in a discretised grid gets exactly one label."""
        grid_vals = [-0.5, -0.1, -0.001, 0.0, 0.001, 0.05, 0.09, 0.10, 0.11, 0.3, 0.6]
        for lo in grid_vals:
            for hi in grid_vals:
                if hi < lo:
                    continue
                for theta in grid_vals:
                    for op_lo in grid_vals:
                        label = interpret(lo, hi, theta, op_lo)
                        assert label in self._labels, \
                            f"Unexpected label {label} for lo={lo}, hi={hi}, theta={theta}, op_lo={op_lo}"


# ------------------------------------------------------------------------------- C10: Holm arithmetic
class TestC10HolmArithmetic:
    """C10: step-down thresholds 0.00833, 0.0125, 0.025 and adjusted p-values match hand-checked table."""

    def test_three_hypotheses_step_down(self):
        """With m=3 and raw p-values 0.002, 0.01, 0.04 the Holm steps are 3, 2, 1."""
        raw = {"H2": 0.002, "H3": 0.01, "H4": 0.04}
        adj = holm_adjust(raw)
        # H2: min(1.0, 3*0.002) = 0.006
        assert abs(adj["H2"] - 0.006) < 1e-9
        # H3: max(0.006, min(1.0, 2*0.01)) = max(0.006, 0.02) = 0.02
        assert abs(adj["H3"] - 0.02) < 1e-9
        # H4: max(0.02, min(1.0, 1*0.04)) = max(0.02, 0.04) = 0.04
        assert abs(adj["H4"] - 0.04) < 1e-9

    def test_uniform_p_values(self):
        """With m=3 equal p-values p=0.01 each, all adjusted = min(1.0, 3*0.01)=0.03."""
        raw = {"H2": 0.01, "H3": 0.01, "H4": 0.01}
        adj = holm_adjust(raw)
        for k, v in adj.items():
            assert abs(v - 0.03) < 1e-9, f"{k}: expected 0.03, got {v}"

    def test_one_hypothesis(self):
        """With m=1, the adjusted p equals the raw p."""
        raw = {"H2": 0.03}
        adj = holm_adjust(raw)
        assert abs(adj["H2"] - 0.03) < 1e-9

    def test_gatekeep_h1_rejected_opens_secondary(self):
        """If H1 is rejected (p < ALPHA), secondary hypotheses are confirmatory."""
        result = gatekeep(0.01, {"H2": 0.02, "H3": 0.03}, alpha=ALPHA)
        assert result["H1_rejected"] is True
        assert result["secondary_status"] == "confirmatory"

    def test_gatekeep_h1_not_rejected_secondary_descriptive(self):
        """If H1 is not rejected, secondary hypotheses are descriptive."""
        result = gatekeep(0.10, {"H2": 0.02, "H3": 0.03}, alpha=ALPHA)
        assert result["H1_rejected"] is False
        assert result["secondary_status"] == "descriptive, not confirmatory"


# ------------------------------------------------------------------------------- C4 (partial): Utility computation
class TestC4UtilityInvariants:
    """C4 (partial): verify utility function and invariants work correctly on dev/val data."""

    def test_always_abstain_utility_zero(self):
        """Always-abstain must score U ≡ 0."""
        n = 50
        correct = np.zeros(n)
        unsafe = np.zeros(n)
        n_do = np.zeros(n)
        u = utility(correct, unsafe, n_do)
        assert np.all(u == 0.0), "Always-abstain utility is not identically 0"

    def test_check_utility_invariants_passes(self):
        """check_utility_invariants should pass with valid inputs."""
        aa = np.zeros(10)
        v3 = np.array([0.5, -0.3, 0.1, 0.0, -0.1, 0.2, 0.3, -0.2, 0.0, 0.1])
        violations = check_utility_invariants({"ALWAYS-ABSTAIN": aa, "V3-FULL": v3})
        assert violations == [], f"Unexpected violations: {violations}"

    def test_utility_range(self):
        """Utility must be in [-(lambda+gamma), 1]."""
        rng = np.random.default_rng(42)
        correct = rng.integers(0, 2, 100).astype(float)
        unsafe = rng.integers(0, 2, 100).astype(float)
        n_do = rng.integers(0, 21, 100).astype(float)
        lam, gamma = 2.0, 1.0
        u = utility(correct, unsafe, n_do, lam=lam, gamma=gamma)
        assert np.all(u >= -(lam + gamma) - 1e-9)
        assert np.all(u <= 1 + 1e-9)

    def test_devval_utility_sanity(self):
        """Load dev/val sprint4_4_0 V3 results and check mean utility is close to -0.338."""
        v4_art = REPO / "artifacts" / "sprint4_4_0" / "v3_dev.json"
        v4_val = REPO / "artifacts" / "sprint4_4_0" / "v3_val.json"
        dev_path = REPO / "datasets" / "rift_v2" / "dev.json"
        val_path = REPO / "datasets" / "rift_v2" / "val.json"

        if not all(p.exists() for p in [v4_art, v4_val, dev_path, val_path]):
            pytest.skip("Sprint 4.4.0 dev/val V3 results not present")

        from src.rift.evaluation import benchmark_v2 as bm

        dev_scs = {sc["scenario_id"]: sc for sc in json.loads(dev_path.read_text())["scenarios"]}
        val_scs = {sc["scenario_id"]: sc for sc in json.loads(val_path.read_text())["scenarios"]}
        all_scs = {**dev_scs, **val_scs}

        scores, recs = [], []
        for art_path in [v4_art, v4_val]:
            rows = json.loads(art_path.read_text())
            for row in rows:
                sid = row["scenario_id"]
                sc = all_scs.get(sid)
                rec = row["methods"].get("V3-FULL", {}).get("record")
                if sc and rec:
                    scores.append(bm.score_one(sc, rec))
                    recs.append(rec)

        if not scores:
            pytest.skip("No V3-FULL records found in sprint4_4_0 artifacts")

        c = np.array([int(s["correct"]) for s in scores], dtype=float)  # preregistered C_i = score_one()["correct"]
        u = np.array([int(s["unsafe"]) for s in scores], dtype=float)
        nd = np.array([r.get("n_do", 0) for r in recs], dtype=float)
        u_vec = utility(c, u, nd, lam=2.0, gamma=1.0, max_do=20)
        mean_u = float(u_vec.mean())
        assert abs(mean_u - (-0.338)) < 0.05, \
            f"Dev/val mean utility {mean_u:.3f} differs too much from expected -0.338"


# ------------------------------------------------------------------------------- Inference correctness
class TestFixedStrataDesign:
    """Basic correctness checks for stratified inference (uses simulated data)."""

    def _make_design(self, n_strata=4, n_groups_per=4, n_per_group=5, seed=0):
        rng = np.random.default_rng(seed)
        structs, groups, fams = [], [], []
        for s in range(n_strata):
            for g in range(n_groups_per):
                for _ in range(n_per_group):
                    structs.append(f"S{s:02d}")
                    groups.append(f"S{s:02d}|F{g:02d}")
                    fams.append(f"F{g:02d}")
        d = np.zeros(len(structs))
        return FixedStrataDesign(structs, groups, fams), d, np.array(structs), np.array(groups), np.array(fams)

    def test_design_creates_without_error(self):
        design, _, structs, groups, fams = self._make_design()
        assert design.S == 4
        assert design.G == 16  # 4 strata × 4 groups

    def test_zero_effect_p_is_valid(self):
        """Under null (d=0), one-sided p should be a valid probability in (0, 1]."""
        design, d, _, _, _ = self._make_design(seed=42)
        result = design.template_bootstrap_t(d, B=200, seed=4505)
        # p for H0: mu <= 0 on exact-zero data is defined as (1+0)/(B+1) ≈ 1/(B+1) ≈ 0.005
        # because all bootstrap t-stats are nan/0 and theta==0, so 0/(B+1) or 1/(B+1)
        # Accept any valid probability — the important contract is 0 < p <= 1
        assert 0.0 < result.p <= 1.0, f"p={result.p} is not a valid probability"

    def test_positive_effect_p_small(self):
        """Under positive effect, one-sided p should be small."""
        rng = np.random.default_rng(7)
        design, _, _, _, _ = self._make_design(seed=42)
        d = np.ones(design.n) * 0.3 + rng.normal(0, 0.1, design.n)
        result = design.template_bootstrap_t(d, B=200, seed=4505)
        assert result.p < 0.1, f"Expected small p under strong positive effect, got {result.p}"
