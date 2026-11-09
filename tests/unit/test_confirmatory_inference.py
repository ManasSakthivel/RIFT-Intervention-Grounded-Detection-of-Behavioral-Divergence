"""Tests for src/rift/statistics/confirmatory_inference.py (SAP 3-5, 7).  Synthetic data plus read-only dev/val;
nothing here touches the Sprint 4.3.0 held-out split or any confirmatory data."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.rift.statistics import confirmatory_inference as CI  # noqa: E402
from src.rift.statistics.confirmatory_inference import (  # noqa: E402
    FixedStrataDesign, check_utility_invariants, gatekeep, holm_adjust, interpret, interpret_two_key, mcnemar_exact,
    normal_power, utility)


def _layout(S=16, F=16, per_cell=(5, 9), seed=0):
    rng = np.random.default_rng(seed)
    st, gr, fa = [], [], []
    for s in range(S):
        for f in range(F):
            m = int(rng.integers(per_cell[0], per_cell[1] + 1))
            st += [s] * m
            gr += [f] * m          # group id unique only within stratum: exercises the combined key
            fa += [f] * m
    return np.array(st), np.array(gr), np.array(fa)


# ------------------------------------------------------------------------------------------------ module hygiene
def test_module_has_no_data_access():
    src = (ROOT / "src/rift/statistics/confirmatory_inference.py").read_text()
    for needle in ("open(", "read_text", "read_bytes", "json", "datasets", "dev.json", "val.json", "held_out", "heldout",
                   "pandas", "glob", "os.path"):
        assert needle not in src, needle


def test_reserved_seeds_are_sap_seeds():
    assert (CI.SEED_TEMPLATE, CI.SEED_FAMILY, CI.DEFAULT_B, CI.ALPHA, CI.DELTA) == (4505, 4506, 20000, 0.025, 0.10)


# ------------------------------------------------------------------------------------------------ estimator
def test_point_estimate_equals_pooled_mean_and_hand_calc():
    st, gr, fa = _layout()
    rng = np.random.default_rng(1)
    d = rng.normal(0.2, 1.0, size=len(st))
    des = FixedStrataDesign(st, gr, fa)
    t = des.template_bootstrap_t(d, B=199)
    f = des.family_block_bootstrap_t(d, B=199)
    assert t.theta == pytest.approx(d.mean(), abs=1e-12)     # W_s = n_s/N makes the stratified mean the pooled mean
    assert f.theta == pytest.approx(d.mean(), abs=1e-12)
    # hand-computed CR1 SE (SAP 3)
    var = 0.0
    N = len(d)
    for s in range(16):
        m = st == s
        ns = m.sum()
        ths = d[m].mean()
        gs = np.unique(gr[m])
        K = len(gs)
        r = np.array([d[m & (gr == g)].sum() - ths * (m & (gr == g)).sum() for g in gs])
        var += (ns / N) ** 2 * K / (K - 1) * np.sum(r ** 2) / ns ** 2
    assert t.se == pytest.approx(np.sqrt(var), rel=1e-10)


def test_reproducible_and_seeded():
    st, gr, fa = _layout()
    d = np.random.default_rng(2).normal(0, 1, len(st))
    des = FixedStrataDesign(st, gr, fa)
    a = des.template_bootstrap_t(d, B=300)
    b = des.template_bootstrap_t(d, B=300)
    assert a.as_dict() == b.as_dict()
    assert des.family_block_bootstrap_t(d, B=300).as_dict() == des.family_block_bootstrap_t(d, B=300).as_dict()


def test_degenerate_constant_input_does_not_reject_or_crash():
    st, gr, fa = _layout(S=4, F=4)
    des = FixedStrataDesign(st, gr, fa)
    for r in (des.template_bootstrap_t(np.ones(len(st)), B=99), des.family_block_bootstrap_t(np.ones(len(st)), B=99)):
        assert r.p == 1.0 and r.lo == r.hi == 1.0           # zero SE: no inference claimed


def test_input_validation():
    st, gr, fa = _layout(S=3, F=3)
    with pytest.raises(ValueError):
        FixedStrataDesign(st[:-1], gr)
    with pytest.raises(ValueError):
        FixedStrataDesign(np.array([0, 0, 1]), np.array([0, 1, 0]))        # stratum 1 has one group
    des = FixedStrataDesign(st, gr, fa)
    with pytest.raises(ValueError):
        des.template_bootstrap_t(np.zeros(3))
    with pytest.raises(ValueError):
        FixedStrataDesign(st, gr).family_block_bootstrap_t(np.zeros(len(st)))


def test_clear_effect_rejected_and_clear_negative_detected():
    st, gr, fa = _layout()
    des = FixedStrataDesign(st, gr, fa)
    rng = np.random.default_rng(3)
    pos = rng.normal(0.4, 0.5, len(st))
    neg = rng.normal(-0.4, 0.5, len(st))
    for fn in (des.template_bootstrap_t, des.family_block_bootstrap_t):
        assert fn(pos, B=999).lo > 0 and fn(pos, B=999).p < CI.ALPHA
        r = fn(neg, B=999)
        assert r.hi < 0 and r.p > 0.9


def test_weights_are_not_resampled_each_stratum_present_in_every_replicate():
    """Unequal stratum sizes; family-block replicate with an absent cell must still use fixed weights (valid flag)."""
    st, gr, fa = _layout(S=4, F=4, per_cell=(1, 3), seed=5)
    des = FixedStrataDesign(st, gr, fa)
    r = des.family_block_bootstrap_t(np.random.default_rng(4).normal(0, 1, len(st)), B=500)
    assert 0 < r.B_valid <= 500


# ------------------------------------------------------------------------------------------------ operating characteristics
def _gen(st, gr, fa, rg, rf, rng, S=16, F=16):
    G = {(s, f): rng.normal() for s in range(S) for f in range(F)}
    Fz = rng.normal(size=F)
    z = np.empty(len(st))
    for i in range(len(st)):
        z[i] = np.sqrt(rg) * G[(st[i], gr[i])] + np.sqrt(rf) * Fz[fa[i]] + np.sqrt(1 - rg - rf) * rng.normal()
    return z


def test_size_controlled_without_family_effect_and_family_block_robust_with_it():
    st, gr, fa = _layout(seed=7)
    des = FixedStrataDesign(st, gr, fa)
    rng = np.random.default_rng(11)
    R = 120
    rej = {("T", 0.0): 0, ("F", 0.0): 0, ("T", 0.08): 0, ("F", 0.08): 0}
    for _ in range(R):
        for rf in (0.0, 0.08):
            z = _gen(st, gr, fa, 0.05, rf, rng)
            rej[("T", rf)] += des.template_bootstrap_t(z, B=149, rng=rng).lo > 0
            rej[("F", rf)] += des.family_block_bootstrap_t(z, B=149, rng=rng).lo > 0
    # no family effect: both close to nominal 0.025 (MC SE 0.014 at R=120)
    assert rej[("T", 0.0)] / R <= 0.08 and rej[("F", 0.0)] / R <= 0.08
    # with a crossed family effect the template rule must be visibly anti-conservative, the family-block rule not
    assert rej[("T", 0.08)] / R > rej[("F", 0.08)] / R
    assert rej[("F", 0.08)] / R <= 0.08


# ------------------------------------------------------------------------------------------------ decisions
def test_interpret_matches_prereg_label_function_exhaustively():
    sys.path.insert(0, str(ROOT / "scripts"))
    from scripts.sprint451_doc_consistency_check import label_of
    vals = [-0.5, -0.1, -0.0001, 0.0, 0.0001, 0.05, 0.0999, 0.10, 0.1001, 0.3, 0.8]
    n = 0
    for lo in vals:
        for hi in vals:
            if hi < lo:
                continue
            for th in vals:
                if not lo <= th <= hi:
                    continue
                for op in vals:
                    hits = label_of(lo, hi, th, op)
                    assert hits == [interpret(lo, hi, th, op)], (lo, hi, th, op, hits)
                    n += 1
    assert n > 1000


def test_hull_rule_needs_both_intervals():
    mk = lambda lo, hi, th: CI.InferenceResult("x", th, 0.1, 0.0, lo, hi, lo, hi, 1, 1, 1, 1)  # noqa: E731
    r = interpret_two_key(mk(0.02, 0.2, 0.11), mk(-0.01, 0.23, 0.11), mk(0.02, 0.2, 0.11), mk(-0.01, 0.23, 0.11))
    assert r["label_template_only"] == "POSITIVE-USEFUL" and r["label_family_only"] == "INCONCLUSIVE"
    assert r["label"] == "INCONCLUSIVE" and r["robust_to_family_dependence"] is False


def test_holm_and_gatekeeping():
    adj = holm_adjust({"H2": 0.001, "H3": 0.02, "H4": 0.03})
    assert adj["H2"] == pytest.approx(0.003) and adj["H3"] == pytest.approx(0.04) and adj["H4"] == pytest.approx(0.04)
    assert gatekeep(0.01, {"H2": 0.001, "H3": 0.02, "H4": 0.03})["secondary_rejected"] == ["H2"]
    g = gatekeep(0.2, {"H2": 1e-9})
    assert not g["H1_rejected"] and g["secondary_rejected"] == [] and "descriptive" in g["secondary_status"]


def test_mcnemar_exact():
    r = mcnemar_exact(46, 15)       # H3 dev/val discordance
    assert r["p_two_sided"] < 0.001 and r["p_mid"] <= r["p_two_sided"]
    assert mcnemar_exact(0, 0)["p_two_sided"] == 1.0
    assert mcnemar_exact(5, 5)["p_two_sided"] == 1.0


def test_normal_power_matches_sap_table():
    assert normal_power(2000, 0.10, 0.96916, 2.0) == pytest.approx(0.9037, abs=2e-3)
    assert normal_power(2000, 0.10, 0.96916, 3.0) == pytest.approx(0.7593, abs=2e-3)
    assert normal_power(800, 0.10, 0.96916, 2.0) == pytest.approx(0.5413, abs=2e-3)


def test_utility_and_invariants():
    u = utility([1, 0, 0, 0], [0, 1, 0, 0], [4, 20, 0, 0])
    assert u.tolist() == pytest.approx([0.8, -3.0, 0.0, 0.0])
    assert check_utility_invariants({"ALWAYS-ABSTAIN": np.zeros(4), "V3": u}) == []
    assert check_utility_invariants({"ALWAYS-ABSTAIN": np.array([0, 0.1])})
    assert check_utility_invariants({"V3": np.array([-3.5])})
    assert check_utility_invariants({"V3": np.array([1.2])})


# ------------------------------------------------------------------------------------------------ dev/val reproduction (permitted data)
def test_reproduces_devval_numbers_from_sap():
    from scripts import sprint451_utility_sensitivity as U
    rows = U.load_rows()
    st = [r["structure"] for r in rows]
    gr = [r["template"] for r in rows]
    v3 = U.util(rows, "V3-FULL", 2.0, 0.05)
    v2 = U.util(rows, "RIFT-FULL-V2", 2.0, 0.05)
    des = FixedStrataDesign(st, gr)
    t = des.template_bootstrap_t(v3, B=4000, seed=1)
    assert t.theta == pytest.approx(-0.338, abs=5e-4)
    assert t.hi < 0                                           # NEGATIVE-WORSE on dev/val, as documented
    assert t.lo == pytest.approx(-0.465, abs=0.07) and t.hi == pytest.approx(-0.219, abs=0.07)
    assert des.template_bootstrap_t(v3 - v2, B=4000, seed=1).theta == pytest.approx(0.224, abs=5e-4)
    assert interpret(t.lo, t.hi, t.theta, t.lo) == "NEGATIVE-WORSE"
