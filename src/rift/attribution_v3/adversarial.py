"""Sprint 4.4.0 Phase 7 adversarial scenario generator (DEV-SIDE ONLY).

Produces 14 hand-designed counterexample families x K variants, in the frozen v2 scenario schema, written to
``datasets/rift_v3_dev/adversarial_dev.json`` (NEW file; the pinned dev.json / val.json / held-out are never touched).
Ground truth is computed by the unchanged ``generator_v2.compute_ground_truth`` from the noise-free simulator state, never from a
method. Scenario ids are ``ADV-<type>-<k>``; split is "adv_dev" so no loader treats them as dev/val/held-out.

Every family states the property it attacks (``ATTACKS``). Variants differ in seed, names, gains and sigmas; they are NOT
independent evidence of generalisation -- they are regression/stress tests for known failure modes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from src.rift.scenarios import GENERATOR_VERSION
from src.rift.scenarios.fingerprint import sha256_json
from src.rift.scenarios.generator_v2 import compute_ground_truth
from src.rift.scenarios.simulator import DELTA_T

REPO = Path(__file__).resolve().parents[3]
OUT_DIR = REPO / "datasets" / "rift_v3_dev"
OUT_FILE = OUT_DIR / "adversarial_dev.json"
K = 8
NAMES = ["alder", "birch", "cedar", "dune", "elm", "fjord", "grove", "heath", "iris", "juniper", "kelp", "larch", "moss",
         "nettle", "oak", "pine", "quill", "reed", "sage", "thorn", "umber", "vale", "willow", "yarrow"]

ATTACKS = {
    "A01_DOWNSTREAM_LARGEST": "downstream service has the largest anomaly score (gain>1); root must still be named, not the biggest",
    "A02_ROOT_SMALLER_ANOMALY": "true root has noisier/smaller z than its descendant",
    "A03_DELAYED_PROPAGATION": "propagation lags 4-5 windows; earliest-divergence ordering is clean but late effects tempt wrong sources",
    "A04_SIMULTANEOUS_ONSET": "root and child diverge in the same window; temporal precedence cannot decide",
    "A05_COMMON_CAUSE_CONFOUNDING": "observed root with a latent confounder shared with its child",
    "A06_MULTIPLE_POSSIBLE_ROOTS": "two independent faulted roots feeding one mediator",
    "A07_WEAK_INTERVENTION": "do() magnitude 0.15 sigma: positive control and effects are below detectability",
    "A08_MULTI_SERVICE_INTERVENTION": "do(x) also perturbs a co-target that feeds a non-descendant of x (spurious x->c effect)",
    "A09_INSUFFICIENT_SAMPLES": "short pre-incident window; abstention required",
    "A10_AMBIGUOUS_PAG": "latent common driver of every observed service flattens the PAG",
    "A11_ISOLATED_ROOT_HARD_FOR_FCI": "short transient fault on a root with noisy descendants; FCI may isolate the root (realised, not forced)",
    "A12_MISSING_TELEMETRY_ON_ROOT": "true root is unobserved; any named service is a descendant (abstention required)",
    "A13_NO_IDENTIFIABLE_ORIGIN": "mutual a<->b dependency; origin not identifiable (abstention required)",
    "A14_STRONG_ANOMALIES_ABSTAIN": "large simultaneous anomalies from a hidden common cause (abstention required)",
}


def _seed(tag: str, k: int) -> int:
    return int(hashlib.sha256(f"rift-v3-adversarial|{tag}|{k}".encode()).hexdigest()[:8], 16) & 0x7FFFFFFF


def _base_iv(**kw) -> Dict[str, Any]:
    iv = {"mode": "single_service", "magnitude_sigma": 2.0, "delivered": 1.0, "delay_s": 0.0, "multi_service": False,
          "co_target": None, "collateral": {}, "rollback_complete": True}
    iv.update(kw)
    return iv


def _fault(svc: str, onset_w: int, amp: float, shape: str = "step", **kw) -> Dict[str, Any]:
    f = {"service": svc, "onset_s": float(onset_w * DELTA_T), "amp_ms": round(amp, 3), "shape": shape, "shape_params": {}, "var_mult": 1.0}
    f.update(kw)
    return f


def build(tag: str, k: int) -> Dict[str, Any]:
    seed = _seed(tag, k)
    rng = np.random.default_rng(seed)
    nm = [NAMES[i] for i in rng.permutation(len(NAMES))]
    j = lambda lo, hi: round(float(rng.uniform(lo, hi)), 3)  # noqa: E731
    onset = int(rng.integers(14, 20))
    nwin = onset + 26
    dims = {"family": "synthetic_adversarial", "intervention": "single_service", "negative": None,
            "observability": "complete_telemetry", "structure": "linear_chain", "temporal": "abrupt_degradation",
            "workload": "moderate_load", "size_extra": 0}
    sigma = 8.0
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    faults: List[Dict[str, Any]]
    tel = {"n_windows": nwin, "missing_frac": 0.0, "delay_windows": {}, "unobserved": []}
    iv = _base_iv()
    roots: List[str]
    distractors: List[str] = []
    mutual: List[List[str]] = []
    E = lambda a, b, g, lag=1: {"src": a, "dst": b, "gain": g, "lag": lag}  # noqa: E731
    N = lambda i, s=sigma, **kw: {"id": i, "sigma": s, **kw}  # noqa: E731

    if tag == "A01_DOWNSTREAM_LARGEST":
        r, a, b = nm[0], nm[1], nm[2]
        nodes = [N(r), N(a), N(b)]
        edges = [E(r, a, j(1.5, 1.8)), E(a, b, j(1.4, 1.7))]
        faults = [_fault(r, onset, 52.0)]; roots = [r]
    elif tag == "A02_ROOT_SMALLER_ANOMALY":
        r, a, b = nm[0], nm[1], nm[2]
        nodes = [N(r, 12.0), N(a, 4.0), N(b, 4.0)]
        edges = [E(r, a, j(1.6, 1.9)), E(a, b, j(1.0, 1.3))]
        faults = [_fault(r, onset, 72.0)]; roots = [r]
    elif tag == "A03_DELAYED_PROPAGATION":
        r, a, b, c = nm[:4]
        nodes = [N(r), N(a), N(b), N(c)]
        edges = [E(r, a, j(0.9, 1.1), 4), E(a, b, j(0.9, 1.1), 4), E(r, c, j(0.9, 1.1), 5)]
        faults = [_fault(r, onset, 56.0)]; roots = [r]; dims["temporal"] = "delayed_downstream_effects"
    elif tag == "A04_SIMULTANEOUS_ONSET":
        r, a, b = nm[:3]
        nodes = [N(r), N(a), N(b)]
        edges = [E(r, a, j(1.0, 1.2), 0), E(a, b, j(1.0, 1.2), 0)]
        faults = [_fault(r, onset, 56.0)]; roots = [r]; dims["temporal"] = "immediate_propagation"
    elif tag == "A05_COMMON_CAUSE_CONFOUNDING":
        h, r, c, d = nm[:4]
        nodes = [N(r), N(c), N(d), N(h, sigma, hidden=True, latent=True)]
        edges = [E(h, r, j(0.7, 0.9), 0), E(h, c, j(0.7, 0.9), 0), E(r, c, j(0.9, 1.2)), E(c, d, j(0.9, 1.2))]
        faults = [_fault(r, onset, 52.0)]; roots = [r]; dims["structure"] = "confounding"
    elif tag == "A06_MULTIPLE_POSSIBLE_ROOTS":
        r1, r2, m, d = nm[:4]
        nodes = [N(r1), N(r2), N(m), N(d)]
        edges = [E(r1, m, j(0.9, 1.1)), E(r2, m, j(0.9, 1.1)), E(m, d, j(0.9, 1.1))]
        faults = [_fault(r1, onset, 52.0), _fault(r2, onset + 3, 52.0)]; roots = [r1, r2]
        dims["structure"] = "multiple_upstream"; dims["temporal"] = "overlapping_faults"
    elif tag == "A07_WEAK_INTERVENTION":
        r, a, b = nm[:3]
        nodes = [N(r), N(a), N(b)]
        edges = [E(r, a, j(0.9, 1.2)), E(a, b, j(0.9, 1.2))]
        faults = [_fault(r, onset, 52.0)]; roots = [r]
        iv = _base_iv(mode="no_meaningful_effect", magnitude_sigma=0.15); dims["intervention"] = "no_meaningful_effect"
    elif tag == "A08_MULTI_SERVICE_INTERVENTION":
        r, a, c, f = nm[:4]
        nodes = [N(r), N(a), N(c), N(f)]
        edges = [E(r, a, j(0.9, 1.2)), E(r, c, j(0.9, 1.2), 2), E(f, c, j(1.2, 1.6))]
        faults = [_fault(r, onset, 52.0)]; roots = [r]
        iv = _base_iv(mode="multi_service", multi_service=True, co_target=f); dims["intervention"] = "multi_service"
        dims["structure"] = "converging"
    elif tag == "A09_INSUFFICIENT_SAMPLES":
        r, a, b = nm[:3]
        nodes = [N(r), N(a), N(b)]
        edges = [E(r, a, j(0.9, 1.2)), E(a, b, j(0.9, 1.2))]
        onset, nwin = 6, 16
        faults = [_fault(r, onset, 52.0)]; roots = [r]; dims["observability"] = "insufficient_samples"
    elif tag == "A10_AMBIGUOUS_PAG":
        r, a, b, z = nm[:4]
        nodes = [N(r), N(a), N(b), N(z, sigma, hidden=True, latent=True)]
        edges = [E(r, a, j(0.9, 1.2)), E(a, b, j(0.9, 1.2))] + [E(z, n, j(0.75, 0.95), 0) for n in (r, a, b)]
        faults = [_fault(r, onset, 52.0)]; roots = [r]; dims["observability"] = "ambiguous_pag"
    elif tag == "A11_ISOLATED_ROOT_HARD_FOR_FCI":
        r, a, b, c = nm[:4]
        nodes = [N(r, 6.0), N(a, 14.0), N(b, 14.0), N(c, 14.0)]
        edges = [E(r, a, j(0.5, 0.7), 1), E(a, b, j(0.9, 1.1), 1), E(r, c, j(0.5, 0.7), 2)]
        faults = [_fault(r, onset, 64.0, "pulse", shape_params={"windows": 4})]; roots = [r]
        dims["family"] = "transient"; dims["structure"] = "branching"
    elif tag == "A12_MISSING_TELEMETRY_ON_ROOT":
        r, a, b = nm[:3]
        nodes = [N(r), N(a), N(b)]
        edges = [E(r, a, j(0.9, 1.2)), E(a, b, j(0.9, 1.2))]
        faults = [_fault(r, onset, 52.0)]; roots = [r]; tel["unobserved"] = [r]
        dims["observability"] = "partial_service_observability"
    elif tag == "A13_NO_IDENTIFIABLE_ORIGIN":
        a, b, t = nm[:3]
        nodes = [N(a), N(b), N(t)]
        edges = [E(a, b, 0.8, 0), E(b, a, 0.8, 0), E(b, t, j(0.9, 1.2))]
        mutual = [[a, b]]
        faults = [_fault(a, onset, 52.0)]; roots = [a]; dims["structure"] = "ambiguous"
    elif tag == "A14_STRONG_ANOMALIES_ABSTAIN":
        h, x, y, z = nm[:4]
        nodes = [N(x), N(y), N(z), N(h, sigma, hidden=True)]
        edges = [E(h, x, j(0.9, 1.1), 0), E(h, y, j(0.9, 1.1), 0), E(h, z, j(0.9, 1.1), 0)]
        faults = [_fault(h, onset, 80.0)]; roots = [h]; dims["structure"] = "hidden_common_cause"
    else:
        raise ValueError(tag)

    sc: Dict[str, Any] = {
        "scenario_id": f"ADV-{tag[:3]}-{k + 1:02d}", "split": "adv_dev", "seed": seed, "generator_version": GENERATOR_VERSION,
        "parent_scenario": None, "dimensions": dims, "template_id": f"adversarial|{tag}",
        "graph": {"nodes": nodes, "edges": edges, "mutual_pairs": mutual, "decoy_edges": []},
        "faults": faults, "telemetry": tel, "workload_params": {}, "intervention": iv,
        "design": {"onset_window": onset, "distractors": distractors, "true_roots": roots},
        "adversarial": {"type": tag, "attacks": ATTACKS[tag], "variant": k + 1},
    }
    sc["telemetry"]["n_windows"] = nwin
    sc["ground_truth"] = compute_ground_truth(sc)
    sc["content_hash"] = sha256_json({kk: v for kk, v in sc.items() if kk not in {"scenario_id", "seed", "split", "content_hash", "parent_scenario"}})
    return sc


def generate() -> List[Dict[str, Any]]:
    return [build(tag, k) for tag in ATTACKS for k in range(K)]


def write() -> Dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scs = generate()
    payload = {"purpose": "Sprint 4.4.0 adversarial regression/stress set (DEV-SIDE; not held-out, not part of dev.json/val.json)",
               "generator": "src/rift/attribution_v3/adversarial.py", "variants_per_type": K, "attacks": ATTACKS, "scenarios": scs}
    raw = json.dumps(payload, indent=1, sort_keys=True)
    OUT_FILE.write_text(raw)
    prov = {"sha256": hashlib.sha256(raw.encode()).hexdigest(), "n": len(scs), "types": len(ATTACKS), "variants_per_type": K,
            "ground_truth": "generator_v2.compute_ground_truth (noise-free simulator state); never derived from any method output",
            "independence": "disjoint from dev/val/held-out by construction (split='adv_dev', new seeds from a distinct hash tag)",
            "caveat": "hand-designed counterexamples; K variants per family are NOT independent samples"}
    (OUT_DIR / "provenance.json").write_text(json.dumps(prov, indent=1))
    return prov


def load() -> List[Dict[str, Any]]:
    return json.loads(OUT_FILE.read_text())["scenarios"]
