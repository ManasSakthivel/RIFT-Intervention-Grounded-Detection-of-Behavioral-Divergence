"""L-struct: threshold-free structural ground-truth label + continuous detectability covariates (D23).

STATUS: PROPOSAL / CO-REPORTED SENSITIVITY LABEL. It does NOT replace the frozen primary label
(``generator_v2.compute_ground_truth``) and is NOT wired into any frozen generator, dataset or result.
No historical scenario is relabelled by importing this module; ``annotate`` returns a copy.

Design rule (see docs/FINAL_GROUND_TRUTH_INDEPENDENCE_REPORT.md):

* ``l_struct`` answers only "is there anything in the simulated world that makes a unique root
  attributable in principle?" using facts the simulator fixes: a fault exists, a true root is observed,
  the structure is not a symmetric mutual dependency, and the baseline is long enough.
  It contains NO signal-size, persistence, detector, effect-size or timing threshold.
* ``detectability_covariates`` returns CONTINUOUS measurements (root SNR, best expected do() effect,
  effect-arrival latency, temporal separation). They are never folded into the binary label; analysts
  stratify on them. Choosing where "detectable" starts is deliberately left to the reader.

Imports are restricted on purpose (enforced by tests/unit/test_l_struct.py): only the simulator's
world-model helpers (graph, path responses, noise-free signal, observed set, grid constants) -- never
``detectable_onset_window``, ``generator_v2``, ``ebd``, ``attribution_v3``, ``evaluation``, ``baselines``
or ``pipeline``. The function reads no ground_truth and no method output.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Mapping, Optional

import networkx as nx
import numpy as np

from .simulator import DELTA_T, REF_WINDOWS, _graph, apparent_signal, observed_services, path_responses

L_STRUCT_VERSION = "l-struct/1.0.0-proposal"
# Minimum number of post-reference windows for a baseline to count as "adequate". This mirrors the
# frozen generator's step-4 rule so that L-struct == steps 1-4 of the frozen cascade (D23 spec). It is a
# simulator budget, not a detector threshold; it remains an authors' choice (disclosed in the report).
MIN_POST_REFERENCE_WINDOWS = 8

LABEL_ONLY_FIELDS = ("label_structural", "label_structural_reason", "root_snr_noisefree",
                     "expected_do_effect_sigma", "effect_arrival_latency_s", "temporal_separation_s",
                     "l_struct_version")


# --------------------------------------------------------------------------------------- label
def l_struct(sc: Mapping[str, Any]) -> Dict[str, Any]:
    """Binary structural label. Returns {"label": bool, "reason": str}. Reads no ground_truth."""
    dims = sc["dimensions"]
    obs = set(observed_services(sc))
    true_roots = list(sc["design"]["true_roots"])
    if not true_roots:
        return {"label": False, "reason": "NO_FAULT"}
    if not [r for r in true_roots if r in obs]:
        return {"label": False, "reason": "ROOT_UNOBSERVED"}
    if dims["structure"] == "ambiguous":
        return {"label": False, "reason": "SYMMETRIC_MUTUAL_DEPENDENCY"}
    if (int(sc["telemetry"]["n_windows"]) < REF_WINDOWS + MIN_POST_REFERENCE_WINDOWS
            or dims["observability"] == "insufficient_samples"
            or dims["negative"] == "insufficient_telemetry"):
        return {"label": False, "reason": "INSUFFICIENT_BASELINE"}
    return {"label": True, "reason": "STRUCTURALLY_ATTRIBUTABLE"}


# ------------------------------------------------------------------------------- covariates
def _first_appearance_s(sc: Mapping[str, Any], g: nx.DiGraph, svc: str) -> Optional[float]:
    """Earliest time any fault's *specified* onset can reach ``svc`` (onset + shortest path lag + telemetry
    delay). Uses only fault specification and graph lags; no amplitude / noise / detector."""
    best: Optional[float] = None
    for f in sc["faults"]:
        resp = path_responses(g, f["service"], svc)
        if not resp:
            continue
        t = float(f["onset_s"]) + min(p[1] for p in resp)
        best = t if best is None else min(best, t)
    if best is None:
        return None
    return best + int(sc["telemetry"].get("delay_windows", {}).get(svc, 0)) * DELTA_T


def detectability_covariates(sc: Mapping[str, Any]) -> Dict[str, Any]:
    """Continuous, label-free measurements from the noise-free simulator state. ``None`` = undefined.

    * root_snr_noisefree          : max over observed roots of max|noise-free fault signal| in sigma units.
    * expected_do_effect_sigma    : max over observed roots & reachable observed descendants of the expected
                                    do() effect in the descendant's sigma units (magnitude*sigma_r*delivered*
                                    summed path gain / sigma_d).
    * effect_arrival_latency_s    : latency (s after do() start) at which that best effect arrives
                                    (intervention delay + 2*path lag in grid steps). Lower = more room.
    * temporal_separation_s       : (earliest specified appearance among other fault-affected observed
                                    services) - (earliest appearance at the best root). Negative => another
                                    service shows the fault before the root does.
    """
    obs = observed_services(sc)
    g = _graph(sc)
    iv = sc["intervention"]
    sig = {n["id"]: float(n["sigma"]) for n in sc["graph"]["nodes"]}
    roots = [r for r in sc["design"]["true_roots"] if r in obs]
    out: Dict[str, Any] = {"root_snr_noisefree": None, "expected_do_effect_sigma": None,
                           "effect_arrival_latency_s": None, "temporal_separation_s": None,
                           "per_root": {}}
    if not roots:
        return out
    best_snr: Optional[float] = None
    best_eff: Optional[float] = None
    best_lat: Optional[float] = None
    first = {s: _first_appearance_s(sc, g, s) for s in obs}
    sep_best: Optional[float] = None
    for r in roots:
        z = apparent_signal(sc, r)
        snr = float(np.max(np.abs(z))) if len(z) else 0.0
        eff_r: Optional[float] = None
        lat_r: Optional[float] = None
        for d in obs:
            if d == r or not nx.has_path(g, r, d):
                continue
            pr = path_responses(g, r, d)
            tot = sum(p[0] for p in pr)
            lag_s = min(p[1] for p in pr)
            eff = float(iv["magnitude_sigma"]) * sig[r] * float(iv["delivered"]) * tot / sig[d]
            if eff_r is None or eff > eff_r:
                eff_r = eff
                lat_r = float(iv["delay_s"]) + 2.0 * lag_s / DELTA_T
        others = [first[s] for s in obs if s != r and first[s] is not None]
        sep_r = (min(others) - first[r]) if (others and first[r] is not None) else None
        out["per_root"][r] = {"root_snr_noisefree": snr, "expected_do_effect_sigma": eff_r,
                              "effect_arrival_latency_s": lat_r, "temporal_separation_s": sep_r}
        if best_snr is None or snr > best_snr:
            best_snr = snr
        if eff_r is not None and (best_eff is None or eff_r > best_eff):
            best_eff, best_lat = eff_r, lat_r
        if sep_r is not None and (sep_best is None or sep_r > sep_best):
            sep_best = sep_r
    out.update({"root_snr_noisefree": best_snr, "expected_do_effect_sigma": best_eff,
                "effect_arrival_latency_s": best_lat, "temporal_separation_s": sep_best})
    return out


# ---------------------------------------------------------------------------------- annotation
def annotate(sc: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a DEEP COPY of ``sc`` whose label-only ``design`` block carries the D23 fields.

    The input is never mutated, so historical frozen scenarios are untouched. Because ``design`` is a
    label field (``independence.LABEL_FIELDS``), these values are stripped with the rest of the label
    block before any method sees a record. NOTE: ``generator_v2.content_hash`` hashes ``design``; an
    annotated copy therefore has a different content hash than the frozen record -- annotate only
    scenarios produced by a NEW (separately preregistered) generator.
    """
    lab = l_struct(sc)
    cov = detectability_covariates(sc)
    new = copy.deepcopy(dict(sc))
    new["design"].update({
        "label_structural": lab["label"], "label_structural_reason": lab["reason"],
        "root_snr_noisefree": cov["root_snr_noisefree"],
        "expected_do_effect_sigma": cov["expected_do_effect_sigma"],
        "effect_arrival_latency_s": cov["effect_arrival_latency_s"],
        "temporal_separation_s": cov["temporal_separation_s"],
        "l_struct_version": L_STRUCT_VERSION})
    return new
