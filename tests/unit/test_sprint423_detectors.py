"""Sprint 4.2.3 — unit tests for candidate divergence detectors and the comparison protocol."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from rift.statistics.divergence_detectors import (
    DETECTORS,
    GRIDS,
    absolute_threshold,
    combined,
    existing_stage4_rule,
    persistence_z,
    relative_increase,
    robust_z,
)

ROOT = Path(__file__).resolve().parents[2]

# Reproduces the saved Stage 4 checkoutservice shape: 3 leading plateau samples at 245 ms
# then ~99 ms; active window ~245 ms.
CHK_PRE = np.array([245.0] * 3 + [99.2] * 6 + [99.0] * 6)
CHK_ACT = np.array([245.5] * 6 + [246.2] * 6)


def test_existing_rule_misses_bimodal_baseline_checkout_shape():
    assert existing_stage4_rule(CHK_PRE, CHK_ACT).flag is False


def test_robust_detectors_flag_checkout_shape_but_so_would_post_recovery_plateau():
    assert robust_z(CHK_PRE, CHK_ACT, z_thr=3).flag is True
    # Same 245 ms level re-appears with no intervention in the saved post window
    assert robust_z(CHK_PRE, np.array([241.0] * 6 + [98.0] * 6 + [242.0] * 6), z_thr=3).flag is True


def test_gaussian_noise_not_flagged_by_robust_or_persistence():
    rng = np.random.default_rng(0)
    fp = 0
    for s in range(200):
        r = np.random.default_rng(s)
        b, t = 100 + r.normal(0, 5, 12), 100 + r.normal(0, 5, 12)
        fp += robust_z(b, t, z_thr=6).flag or persistence_z(b, t, k=3).flag
    assert fp / 200 < 0.10


def test_isolated_spike_not_flagged_by_persistence_detectors():
    b = np.full(8, 100.0) + np.linspace(-1, 1, 8)
    t = np.array([100, 100, 400, 100, 100, 100.0])
    assert persistence_z(b, t, k=2).flag is False
    assert robust_z(b, t, z_thr=3, k=2).flag is False
    assert absolute_threshold(b, t, delta_abs=20, k=2).flag is False


def test_sustained_shift_flagged_with_onset_index():
    b = np.full(8, 100.0) + np.linspace(-1, 1, 8)
    t = np.array([100, 100, 160, 160, 160, 160.0])
    out = persistence_z(b, t, k=2)
    assert out.flag and out.onset_idx == 2
    assert combined(b, t, z_thr=3, delta_abs=15, pct=0.1).onset_idx == 2


def test_directional_detectors_ignore_decreases():
    b = np.full(8, 100.0) + np.linspace(-1, 1, 8)
    t = np.full(6, 40.0)
    for fn, kw in [(absolute_threshold, {"delta_abs": 20}), (relative_increase, {"pct": 0.2}),
                   (robust_z, {"z_thr": 3}), (persistence_z, {}), (combined, {"z_thr": 3, "delta_abs": 15, "pct": 0.1})]:
        assert fn(b, t, **kw).flag is False


def test_nan_and_short_inputs_do_not_crash_or_flag():
    for name, fn in DETECTORS.items():
        kw = {k: v[0] for k, v in GRIDS.get(name, {}).items()}
        assert fn(np.array([]), np.array([1.0, 2.0]), **kw).flag is False
        assert fn(np.array([1.0, np.nan, 1.1, 0.9]), np.array([np.nan, np.nan]), **kw).flag is False


def test_relative_detector_requires_positive_level_floor():
    assert relative_increase(np.zeros(5), np.array([1.0, 1.0]), pct=0.5).flag is True  # floor => huge ratio
    # documented: relative detectors are only meaningful for strictly positive latency baselines


def test_frozen_thresholds_artifact_is_hash_pinned_if_present():
    d = ROOT / "artifacts" / "sprint4_2_3"
    if not (d / "thresholds_frozen.json").exists():
        pytest.skip("run scripts/sprint423_detector_comparison.py select first")
    expect = (d / "thresholds_frozen.sha256").read_text().strip()
    assert hashlib.sha256((d / "thresholds_frozen.json").read_bytes()).hexdigest() == expect


def test_comparison_script_selection_never_loads_held_out():
    """Static check: the DEV builders reference no held-out token; the held-out read is
    confined to build_final() and goes through HeldOutGuard."""
    src = (ROOT / "scripts" / "sprint423_detector_comparison.py").read_text()
    dev_fn = src[src.index("def build_dev"):src.index("def build_final")]
    assert "held" not in dev_fn.lower() and "SPLIT_HELD_OUT_TEST" not in dev_fn
    final_fn = src[src.index("def build_final"):src.index("# ───", src.index("def build_final"))]
    assert "HeldOutGuard" in final_fn and "load_split" in final_fn and "PURPOSE_FINAL" in final_fn
    stage_sel = src[src.index("def stage_select"):src.index("def _stage4_check")]
    assert "build_final" not in stage_sel and "STAGE4" not in stage_sel
