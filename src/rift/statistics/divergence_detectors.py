"""
Sprint 4.2.3 — Candidate divergence detectors (comparison harness, NOT a production swap).

All detectors share one contract so they can be compared fairly:

    detect(baseline, test, params) -> DetectorOutput(flag, onset_idx)

    baseline : 1-D array of pre-incident samples (the same array for every detector)
    test     : 1-D array of incident-window samples at equal spacing
    onset_idx: index into ``test`` of the first window of the supporting run
               (None for aggregate detectors that cannot resolve onset)

All detectors are directional (increase) except ``ebd_r1`` which reproduces the
shipped EBD R1 two-sided rule for reference.

No detector reads ground-truth labels. Thresholds are supplied by the caller;
selection happens in ``scripts/sprint423_detector_comparison.py`` on development
data only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

import numpy as np

MAD_TO_SIGMA = 1.4826


@dataclass(frozen=True)
class DetectorOutput:
    flag: bool
    onset_idx: Optional[int] = None


def _first_run(mask: np.ndarray, k: int) -> Optional[int]:
    """Index of the first element of the first run of >= k consecutive True values."""
    run = 0
    for i, m in enumerate(mask):
        run = run + 1 if m else 0
        if run >= k:
            return i - k + 1
    return None


def _clean(a) -> np.ndarray:
    a = np.asarray(a, dtype=float)
    return a[~np.isnan(a)]


# ── 1. Existing Stage 4 rule: directional aggregate Z >= 3 AND delta_mu >= 15 ──

def existing_stage4_rule(baseline, test, z_thr: float = 3.0, delta_thr: float = 15.0,
                         std_floor: float = 1e-4) -> DetectorOutput:
    b, x = _clean(baseline), _clean(test)
    if len(b) < 2 or len(x) < 1:
        return DetectorOutput(False)
    mu_b = b.mean()
    sd_b = max(float(b.std(ddof=1)), std_floor)
    delta = x.mean() - mu_b
    return DetectorOutput(bool(delta / sd_b >= z_thr and delta >= delta_thr))


# ── 2. Shipped EBD R1: per-window |z| > theta for >= k consecutive windows ──

def ebd_r1(baseline, test, theta: float = 3.0, k: int = 2) -> DetectorOutput:
    b, x = _clean(baseline), np.asarray(test, dtype=float)
    if len(b) < 2:
        return DetectorOutput(False)
    sd = float(b.std(ddof=1))
    if sd <= 0:
        return DetectorOutput(False)
    z = np.abs((x - b.mean()) / sd)
    z = np.where(np.isnan(z), -np.inf, z)
    i = _first_run(z > theta, k)
    return DetectorOutput(i is not None, i)


# ── 3. Absolute latency threshold (median reference, persistent) ──

def absolute_threshold(baseline, test, delta_abs: float, k: int = 2) -> DetectorOutput:
    b, x = _clean(baseline), np.asarray(test, dtype=float)
    if len(b) < 1:
        return DetectorOutput(False)
    d = x - np.median(b)
    i = _first_run(np.where(np.isnan(d), False, d >= delta_abs), k)
    return DetectorOutput(i is not None, i)


# ── 4. Relative percentage increase over baseline median ──

def relative_increase(baseline, test, pct: float, k: int = 2,
                      level_floor: float = 1e-6) -> DetectorOutput:
    b, x = _clean(baseline), np.asarray(test, dtype=float)
    if len(b) < 1:
        return DetectorOutput(False)
    med = max(abs(float(np.median(b))), level_floor)
    r = (x - np.median(b)) / med
    i = _first_run(np.where(np.isnan(r), False, r >= pct), k)
    return DetectorOutput(i is not None, i)


# ── 5. Robust deviation (median / MAD with a relative scale floor) ──

def robust_scale(b: np.ndarray, floor_frac: float) -> float:
    med = float(np.median(b))
    mad = float(np.median(np.abs(b - med))) * MAD_TO_SIGMA
    return max(mad, floor_frac * abs(med), 1e-9)


def robust_z(baseline, test, z_thr: float, k: int = 2,
             floor_frac: float = 0.05) -> DetectorOutput:
    b, x = _clean(baseline), np.asarray(test, dtype=float)
    if len(b) < 3:
        return DetectorOutput(False)
    z = (x - np.median(b)) / robust_scale(b, floor_frac)
    i = _first_run(np.where(np.isnan(z), False, z >= z_thr), k)
    return DetectorOutput(i is not None, i)


# ── 6. Persistence: directional classical-z window rule with delta gate ──

def persistence_z(baseline, test, z_thr: float = 3.0, delta_thr: float = 15.0,
                  k: int = 3) -> DetectorOutput:
    b, x = _clean(baseline), np.asarray(test, dtype=float)
    if len(b) < 2:
        return DetectorOutput(False)
    sd = max(float(b.std(ddof=1)), 1e-4)
    d = x - b.mean()
    m = (d / sd >= z_thr) & (d >= delta_thr)
    i = _first_run(np.where(np.isnan(d), False, m), k)
    return DetectorOutput(i is not None, i)


# ── 7. Combined: robust-z AND absolute AND relative gate, persistent ──

def combined(baseline, test, z_thr: float, delta_abs: float, pct: float,
             k: int = 2, floor_frac: float = 0.05) -> DetectorOutput:
    b, x = _clean(baseline), np.asarray(test, dtype=float)
    if len(b) < 3:
        return DetectorOutput(False)
    med = float(np.median(b))
    z = (x - med) / robust_scale(b, floor_frac)
    d = x - med
    rel = d / max(abs(med), 1e-6)
    m = (z >= z_thr) & (d >= delta_abs) & (rel >= pct)
    i = _first_run(np.where(np.isnan(d), False, m), k)
    return DetectorOutput(i is not None, i)


# Registry: name -> (callable, parameter grid). Grids are fixed a priori.
GRIDS: Dict[str, Dict[str, list]] = {
    "absolute_threshold": {"delta_abs": [5, 10, 15, 20, 25, 30, 40, 50, 75, 100]},
    "relative_increase": {"pct": [0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 0.75, 1.00]},
    "robust_z": {"z_thr": [3, 4, 5, 6, 8, 10, 15]},
    "persistence_z": {"k": [2, 3, 4]},
    "combined": {
        "z_thr": [3, 4, 5, 6, 8],
        "delta_abs": [10, 15, 20, 30],
        "pct": [0.05, 0.10, 0.20],
    },
}

DETECTORS: Dict[str, Callable[..., DetectorOutput]] = {
    "existing_stage4_rule": existing_stage4_rule,
    "ebd_r1": ebd_r1,
    "absolute_threshold": absolute_threshold,
    "relative_increase": relative_increase,
    "robust_z": robust_z,
    "persistence_z": persistence_z,
    "combined": combined,
}
