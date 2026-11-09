"""Confirmatory scenario generator for RIFT Sprint 4.5.0 (WP1).

This module is a parameterised, faithful copy of the core ``generator_v2.build_scenario``
draw sequence, registered under the confirmatory tag family (``confirm`` | ``pilot``).
It imports the frozen ``simulator.py``, ``compute_ground_truth``, ``content_hash`` and the
level lists unchanged.

Hard rules (from CONFIRMATORY_INFRASTRUCTURE_PLAN §0):
  - No scenario file is written from this module; writing is the runner's responsibility.
  - ``generate("confirm", ...)`` is LOCKED unless prerequisites in ``artifacts/sprint4_5_0/prereg/prereg.sha256``
    and ``decisions.json`` are satisfied (G4 lock, §3.6).
  - ``generate("pilot", ...)`` is always permitted (for tests and feasibility checks).
  - No sealed held-out file is read by this module.
  - S13/S14 labels use the shallow-copy wrapper (§3.4); the stored structure name is preserved.

GEN_TAG mirrors DP §4 literal; seed formula: sha256(f"{GEN_TAG}|{tag_kind}|{i}")[:8] & 0x7FFFFFFF.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import networkx as nx
import numpy as np

# -- frozen imports -----------------------------------------------------------------
from src.rift.scenarios import generator_v2 as _gv2
from src.rift.scenarios.fingerprint import sha256_json
from src.rift.scenarios.generator_v2 import (
    AMP_K, DELTA_T, FAMILIES, FAMILY_SHAPE, INTERVENTIONS,
    LAG_ONLY_TEMPORAL, NEEDS_EDGE, NEG_STRUCT, NEGATIVES, OBSERVABILITY,
    REF_SIGMA, REF_WINDOWS, TEMPORAL, TEMPORAL_SHAPE, WORKLOADS,
    _cyc, _workload, compute_ground_truth, content_hash,
)
from src.rift.scenarios.simulator import (
    DELTA_T as _DELTA_T, apparent_signal, detectable_onset_window,
    observed_services, path_responses,
)

# --- version and tag ---------------------------------------------------------------
GEN_TAG = "rift-confirm-gen/1.0.0"   # DP §4 literal

REPO_ROOT = Path(__file__).resolve().parents[3]
PREREG_FILE = REPO_ROOT / "artifacts" / "sprint4_5_0" / "prereg" / "prereg.sha256"
DECISIONS_FILE = REPO_ROOT / "decisions.json"
PROVENANCE_LEDGER = REPO_ROOT / "artifacts" / "sprint4_5_0" / "prereg" / "ledger.jsonl"
MAX_ATTEMPTS = 3    # D15

# Confirmatory id prefix and split name
CONFIRM_SPLIT = "confirm"
PILOT_SPLIT = "pilot"
CONFIRM_PREFIX = "V3C"

# 16 new motifs (S01–S16) — topology blueprints
# Each entry: (ordered_node_labels, hidden_labels, latent_labels, edge_pairs, root_labels, mutual_pairs)
MOTIFS: Dict[str, Tuple] = {
    "S01_spine_with_leaves":     (["r", "a", "b", "c", "la", "lb"], [], [], [("r", "a"), ("a", "b"), ("b", "c"), ("a", "la"), ("b", "lb")], ["r"], []),
    "S02_two_level_fanout":      (["r", "a", "b", "c", "a2", "b2", "c2"], [], [], [("r", "a"), ("r", "b"), ("r", "c"), ("a", "a2"), ("b", "b2"), ("c", "c2")], ["r"], []),
    "S03_ladder":                (["r", "p", "a", "c", "b", "d"], [], [], [("r", "a"), ("a", "b"), ("p", "c"), ("c", "d"), ("a", "c"), ("b", "d")], ["r"], []),
    "S04_double_diamond":        (["r", "a", "b", "d", "e", "f", "g"], [], [], [("r", "a"), ("r", "b"), ("a", "d"), ("b", "d"), ("d", "e"), ("d", "f"), ("e", "g"), ("f", "g")], ["r"], []),
    "S05_late_merge":            (["r", "p", "a", "q", "m", "d"], [], [], [("r", "a"), ("a", "m"), ("p", "q"), ("q", "m"), ("m", "d")], ["r"], []),
    "S06_bypass_chain":          (["r", "a", "b", "c"], [], [], [("r", "a"), ("a", "b"), ("b", "c"), ("r", "c")], ["r"], []),
    "S07_two_stage_hub":         (["f1", "f2", "f3", "h1", "h2", "d"], [], [], [("f1", "h1"), ("f2", "h1"), ("h1", "h2"), ("f3", "h2"), ("h2", "d")], ["f1"], []),
    "S08_triangle_with_tail":    (["r", "a", "b", "c"], [], [], [("r", "a"), ("r", "b"), ("a", "b"), ("b", "c")], ["r"], []),
    "S09_staggered_roots":       (["r1", "r2", "a", "b", "c"], [], [], [("r1", "a"), ("a", "b"), ("r2", "b"), ("b", "c")], ["r1", "r2"], []),
    "S10_latent_confounded_diamond": (["r", "a", "b", "c"], ["h"], ["h"], [("h", "r"), ("h", "c"), ("r", "a"), ("r", "b"), ("a", "c"), ("b", "c")], ["r"], []),
    "S11_hidden_driver_chain":   (["x", "y", "z"], ["h"], [], [("h", "x"), ("x", "y"), ("h", "z")], ["h"], []),
    "S12_hidden_driver_diamond": (["a", "b", "c"], ["h"], [], [("h", "a"), ("h", "b"), ("a", "c"), ("b", "c")], ["h"], []),
    "S13_mutual_pair_merge":     (["a", "b", "p", "c", "d"], [], [], [("a", "b"), ("b", "a"), ("b", "c"), ("p", "c"), ("c", "d")], ["a"], [("a", "b")]),
    "S14_mutual_pair_fanout":    (["a", "b", "c", "d"], [], [], [("a", "b"), ("b", "a"), ("b", "c"), ("b", "d")], ["a"], [("a", "b")]),
    "S15_sink_with_two_chains":  (["r", "p", "a", "q", "s"], [], [], [("r", "a"), ("a", "s"), ("p", "q"), ("q", "s")], ["r"], []),
    "S16_pendant_cluster":       (["r", "a", "b", "c", "d"], [], [], [("r", "a"), ("a", "b"), ("a", "c"), ("b", "c"), ("c", "d")], ["r"], []),
}

STRUCTURES = list(MOTIFS.keys())
MUTUAL_STRUCTS = {"S13_mutual_pair_merge", "S14_mutual_pair_fanout"}
HIDDEN_ROOT_STRUCTS = {"S11_hidden_driver_chain", "S12_hidden_driver_diamond"}

# Size band for confirmatory scenarios (extra periphery nodes 0..3, one extra size tier vs dev/val)
_SIZE_BAND_CONFIRM = (0, 3)

# Name pool (same pool as generator_v2 for full compatibility)
_NAME_POOL = _gv2._NAME_POOL


# ------------------------------------------------------------------------------- seed formula
def derive_seed(tag_kind: str, i: int) -> int:
    """DP §4: sha256(f"{GEN_TAG}|{tag_kind}|{i}")[:8] & 0x7FFFFFFF."""
    raw = f"{GEN_TAG}|{tag_kind}|{i}"
    h = hashlib.sha256(raw.encode()).hexdigest()
    return int(h[:8], 16) & 0x7FFFFFFF


# ------------------------------------------------------------------------------- topology builder
def build_topology(kind: str, rng: np.random.Generator) -> Dict[str, Any]:
    """Build a topology from the MOTIFS table, applying a periphery of 0..3 extra nodes."""
    if kind not in MOTIFS:
        raise ValueError(f"Unknown structure kind: {kind!r}. Must be one of: {list(MOTIFS)}")
    order, hidden0, latent0, edges0, roots0, mutual0 = MOTIFS[kind]
    pool = [_NAME_POOL[i] for i in rng.permutation(len(_NAME_POOL))]
    it = iter(pool)
    nm: Dict[str, str] = {}
    for lab in order + hidden0:
        nm[lab] = next(it)

    nodes = [nm[x] for x in order]
    hidden = [nm[x] for x in hidden0]
    latent = [nm[x] for x in latent0]
    roots = [nm[x] for x in roots0]
    edges: List[Tuple[str, str]] = [(nm[a], nm[b]) for a, b in edges0]
    mutual = [(nm[a], nm[b]) for a, b in mutual0]

    rank = {nm[x]: float(i) for i, x in enumerate(order)}
    mutual_node_set = {nm[a] for a, _ in mutual0} | {nm[b] for _, b in mutual0}

    k = int(rng.integers(*_SIZE_BAND_CONFIRM))
    for _ in range(k):
        u = next(it)
        parents = [n for n in nodes if n not in roots and n not in mutual_node_set]
        if not parents:
            parents = [n for n in nodes if n not in roots] or nodes
        p = parents[int(rng.integers(0, len(parents)))]
        nodes.append(u)
        edges.append((p, u))
        rank[u] = rank[p] + 0.5
        if rng.random() < 0.5:
            later = [n for n in nodes if n not in roots and rank[n] > rank[u]
                     and n != u and (u, n) not in edges and n not in mutual_node_set]
            if later:
                edges.append((u, later[int(rng.integers(0, len(later)))]))

    return {"nodes": nodes, "edges": edges, "hidden": hidden, "latent": latent,
            "roots": roots, "mutual": mutual, "_pool_iter": it, "_pool": pool}


# ------------------------------------------------------------------------------- label wrapper (§3.4)
def label(sc: Dict[str, Any]) -> Dict[str, Any]:
    """Apply frozen compute_ground_truth with S13/S14 shallow-copy wrapper; stored structure preserved."""
    view = dict(sc)
    view["dimensions"] = dict(sc["dimensions"])
    if sc["dimensions"]["structure"] in MUTUAL_STRUCTS:
        view["dimensions"]["structure"] = "ambiguous"
    return compute_ground_truth(view)


# ------------------------------------------------------------------------------- quota (DP §5.2)
def quota_matrix() -> Dict[str, Dict[str, int]]:
    """Integer quota table (structure × label). Column totals: ATTRIBUTE 800, WEAK_SIGNAL 360,
    ROOT_UNOBSERVED 240, SYMMETRIC_MUTUAL_DEPENDENCY 180, INSUFFICIENT_BASELINE 180,
    NO_DISCRIMINATING_EVIDENCE 140, NO_FAULT 100. Grand total 2000."""
    A_STRUCTS = [s for s in STRUCTURES if s not in MUTUAL_STRUCTS and s not in HIDDEN_ROOT_STRUCTS]
    q: Dict[str, Dict[str, int]] = {}
    for i, s in enumerate(A_STRUCTS):
        q[s] = {
            "ATTRIBUTE": 67 if i < 8 else 66,
            "WEAK_SIGNAL": 30,
            "INSUFFICIENT_BASELINE": 15,
            "NO_DISCRIMINATING_EVIDENCE": 12 if i < 8 else 11,
            "NO_FAULT": 8 if i % 2 == 0 else 7,
        }
    for s in sorted(HIDDEN_ROOT_STRUCTS):
        q[s] = {"ROOT_UNOBSERVED": 120, "NO_FAULT": 5}
    for s in sorted(MUTUAL_STRUCTS):
        q[s] = {"SYMMETRIC_MUTUAL_DEPENDENCY": 90}
    return q

QUOTA = quota_matrix()


# ------------------------------------------------------------------------------- build_scenario
def build_scenario(tag_kind: str, i: int, structure: str, family: str, temporal: str,
                   workload: str, observability: str, intervention: str,
                   negative: Optional[str]) -> Dict[str, Any]:
    """Build one confirmatory/pilot scenario. tag_kind is 'pilot' or 'confirm'."""
    if tag_kind not in ("pilot", "confirm"):
        raise ValueError(f"tag_kind must be 'pilot' or 'confirm', got {tag_kind!r}")
    if structure not in MOTIFS:
        raise ValueError(f"structure {structure!r} not in new motif set")

    seed = derive_seed(tag_kind, i)
    rng = np.random.default_rng(seed)
    topo = build_topology(structure, rng)
    pool = topo.pop("_pool")
    pool_it = topo.pop("_pool_iter")
    n_used = len(topo["nodes"]) + len(topo["hidden"])

    # --- workload parameters
    if negative == "high_variance_no_fault":
        workload = "high_baseline_variance"
    sigma_base, wl_params, per_node = _workload(workload)
    if negative == "high_variance_no_fault":
        wl_params = {"burst_p": 0.08, "drift_sigma": 1.5}
    if observability == "noisy_telemetry":
        sigma_base *= 1.8

    nodes_list: List[Dict[str, Any]] = []
    for n in topo["nodes"] + topo["hidden"]:
        if n in topo["hidden"]:
            nd: Dict[str, Any] = {"id": n, "sigma": REF_SIGMA, "hidden": True}
        else:
            nd = {"id": n, "sigma": round(float(rng.uniform(4.0, 22.0)) if per_node else sigma_base, 3)}
        if n in topo["latent"]:
            nd["latent"] = True
        nodes_list.append(nd)

    # --- lags
    lag_tbl = {"immediate_propagation": (0, 0), "delayed_propagation": (2, 3),
               "delayed_downstream_effects": (4, 5)}
    lo, hi = lag_tbl.get(temporal, (1, 1))
    if family in ("network_degradation", "queue_buildup"):
        lo, hi = lo + 1, hi + 1
    if negative in ("indistinguishable_onsets", "weak_intervention_effects"):
        lo, hi = 0, 0
    if negative == "earliest_not_root":
        lo, hi = 1, 1
    gain_c = {"retry_amplification": 1.4, "cascading_failure": 0.92}.get(family, 0.8)
    if negative == "downstream_largest_increase":
        gain_c = 1.5

    mutual_set = {frozenset(p) for p in topo["mutual"]}
    edges: List[Dict[str, Any]] = []
    for a, b in topo["edges"]:
        if a in topo["hidden"]:
            edges.append({"src": a, "dst": b, "gain": round(float(rng.uniform(0.7, 0.9)), 3), "lag": 0})
        elif frozenset((a, b)) in mutual_set:
            edges.append({"src": a, "dst": b, "gain": 0.8, "lag": 0})
        else:
            edges.append({"src": a, "dst": b,
                          "gain": round(float(np.clip(gain_c + rng.uniform(-0.08, 0.08), 0.2, 2.0)), 3),
                          "lag": int(rng.integers(lo, hi + 1))})

    # --- timing
    onset_w = int(rng.integers(14, 22))
    n_windows = onset_w + 26
    if negative == "insufficient_telemetry" or observability == "insufficient_samples":
        n_windows, onset_w = 16, 6

    # --- fault shape/amplitude
    shape = FAMILY_SHAPE.get(family, TEMPORAL_SHAPE.get(temporal, "step"))
    if negative == "incomplete_recovery_after_normalisation":
        shape = "partial_recovery"
    amp = AMP_K[family] * REF_SIGMA * float(rng.uniform(0.9, 1.15))
    if negative == "incomplete_recovery_after_normalisation":
        amp = 6.0 * REF_SIGMA
    sp: Dict[str, Any] = {}
    if shape == "ramp":
        sp = {"windows": 8}
    elif shape == "pulse":
        sp = {"windows": 4}
    elif shape == "recovery_delay":
        sp = {"recover_after_s": float(rng.integers(100, 160))}
    var_mult = {"cpu_contention": 2.0, "resource_saturation": 1.5, "packet_loss": 2.5}.get(family, 1.0)

    # hidden_common_cause analogue: S11/S12 use hidden root
    if structure in HIDDEN_ROOT_STRUCTS:
        roots = list(topo["hidden"])
    else:
        roots = list(topo["roots"])
    if negative in ("high_variance_no_fault", "no_fault_plain"):
        roots = []

    faults: List[Dict[str, Any]] = []
    for k, r in enumerate(roots):
        f: Dict[str, Any] = {"service": r, "onset_s": float((onset_w + 3 * k) * DELTA_T),
                             "amp_ms": round(amp, 3), "shape": shape, "shape_params": dict(sp),
                             "var_mult": var_mult}
        if family == "queue_buildup":
            f["downstream_shape"] = "ramp"
            f["shape_params"] = {"windows": 6}
        faults.append(f)

    obs_nodes = [n["id"] for n in nodes_list if not n.get("hidden")]
    g0 = nx.DiGraph([(e["src"], e["dst"]) for e in edges])
    g0.add_nodes_from(n["id"] for n in nodes_list)

    distractors: List[str] = []
    if temporal == "overlapping_faults" and roots and not negative and structure not in HIDDEN_ROOT_STRUCTS:
        cands = [n for n in obs_nodes if n not in roots
                 and n not in nx.ancestors(g0, roots[0]) and n not in nx.descendants(g0, roots[0])]
        if cands:
            sec = cands[int(rng.integers(0, len(cands)))]
            faults.append({"service": sec, "onset_s": float((onset_w + 5) * DELTA_T),
                           "amp_ms": round(5.0 * REF_SIGMA, 3), "shape": "step", "shape_params": {},
                           "var_mult": 1.0})
            roots.append(sec)

    # use next names from pool for decoy/ambig nodes
    pool_extra = pool[n_used + 1:]
    extra_idx = 0
    if (negative == "coincidental_anomaly" and roots) or \
            (observability == "conflicting_observational_evidence" and roots and not negative):
        decoy_id = pool_extra[extra_idx]; extra_idx += 1
        nodes_list.append({"id": decoy_id, "sigma": sigma_base})
        faults.append({"service": decoy_id, "onset_s": float((onset_w - 4) * DELTA_T),
                       "amp_ms": round(6.0 * REF_SIGMA, 3), "shape": "pulse",
                       "shape_params": {"windows": 6}, "var_mult": 1.0})
        distractors.append(decoy_id)

    if observability == "ambiguous_pag":
        zid = pool_extra[extra_idx]; extra_idx += 1
        nodes_list.append({"id": zid, "sigma": REF_SIGMA, "hidden": True, "latent": True})
        for n in [x["id"] for x in nodes_list if not x.get("hidden")]:
            edges.append({"src": zid, "dst": n, "gain": round(float(rng.uniform(0.75, 0.95)), 3), "lag": 0})

    # --- telemetry
    tel: Dict[str, Any] = {"n_windows": n_windows, "missing_frac": 0.0, "delay_windows": {}, "unobserved": []}
    if observability == "missing_windows":
        tel["missing_frac"] = 0.2
    if negative == "insufficient_telemetry":
        tel["missing_frac"] = 0.3
    if workload == "sparse_telemetry":
        tel["sparse_frac"] = 0.3
    if observability == "partial_service_observability":
        obs_all = [n["id"] for n in nodes_list if not n.get("hidden")]
        leaves = [n for n in obs_all if n not in roots and g0.out_degree(n) == 0 and n not in distractors]
        tel["unobserved"] = sorted(leaves[:2])
    if observability == "delayed_telemetry":
        for n in obs_nodes:
            if rng.random() < 0.5:
                tel["delay_windows"][n] = int(rng.integers(1, 3))
    if negative == "earliest_not_root" and roots and g0.out_degree(roots[0]) > 0:
        tel["delay_windows"][roots[0]] = 3

    # --- intervention
    iv: Dict[str, Any] = {"mode": intervention, "magnitude_sigma": 2.0, "delivered": 1.0, "delay_s": 0.0,
                          "multi_service": False, "co_target": None, "collateral": {}, "rollback_complete": True}
    if intervention == "low_magnitude":
        iv["magnitude_sigma"] = 0.8
    elif intervention == "high_magnitude":
        iv["magnitude_sigma"] = 4.0
    elif intervention == "imperfect":
        iv["delivered"] = 0.5
    elif intervention == "delayed":
        iv["delay_s"] = 15.0
    elif intervention == "no_meaningful_effect":
        iv["magnitude_sigma"] = 0.15
    elif intervention == "multi_service":
        iv["multi_service"] = True
    if observability == "weak_interventional_evidence":
        iv["magnitude_sigma"], iv["delivered"] = 0.6, 0.5
    if negative == "weak_intervention_effects":
        iv["magnitude_sigma"] = 0.2

    # assign opaque id (F9: shuffled later in generate(); individual scenario gets V3C-<n>)
    sc: Dict[str, Any] = {
        "scenario_id": f"{CONFIRM_PREFIX}-{i:06d}",
        "split": tag_kind,
        "seed": seed,
        "generator_version": GEN_TAG,
        "parent_scenario": None,
        "dimensions": {"structure": structure, "family": family, "temporal": temporal,
                       "workload": workload, "observability": observability,
                       "intervention": intervention, "negative": negative},
        "template_id": f"{structure}|{family}",
        "graph": {"nodes": nodes_list, "edges": edges, "mutual_pairs": [list(p) for p in topo["mutual"]],
                  "decoy_edges": []},
        "faults": faults, "telemetry": tel, "workload_params": wl_params, "intervention": iv,
        "design": {"onset_window": onset_w, "distractors": distractors, "true_roots": roots},
    }
    # decoy edges (same as generator_v2 pattern)
    obs = observed_services(sc)
    cand_pairs = [(a, b) for a in obs for b in obs if a != b and not g0.has_edge(a, b)
                  and a not in distractors and b not in distractors]
    rng.shuffle(cand_pairs)
    sc["graph"]["decoy_edges"] = [list(p) for p in cand_pairs[:int(rng.integers(2, 4))]]

    # co-target / collateral
    gg = _gv2._graph(sc)
    rel: set = set()
    for r in roots:
        rel |= (nx.descendants(gg, r) if r in gg else set())
        rel |= (nx.ancestors(gg, r) if r in gg else set())
    free = [n for n in obs if n not in roots and n not in rel and n not in distractors]
    if iv["multi_service"]:
        iv["co_target"] = free[0] if free else None
        iv["multi_service"] = iv["co_target"] is not None
    if intervention == "collateral_effects" and free:
        iv["collateral"] = {free[0]: 0.5}

    sc["ground_truth"] = label(sc)
    sc["content_hash"] = content_hash(sc)
    return sc


# ------------------------------------------------------------------------------- G4 lock (§3.6)
def _check_g4_lock() -> None:
    """Raise RuntimeError if prereg.sha256 or decisions.json D7 sign-off are not present."""
    if not PREREG_FILE.exists():
        raise RuntimeError(
            f"G4 LOCK: {PREREG_FILE} does not exist. "
            "prereg.sha256 must be committed and signed before generating confirmatory data."
        )
    if not DECISIONS_FILE.exists():
        raise RuntimeError(
            f"G4 LOCK: {DECISIONS_FILE} does not exist. "
            "decisions.json must be present with D7 human reviewer sign-off."
        )
    try:
        decisions = json.loads(DECISIONS_FILE.read_text())
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"G4 LOCK: could not parse decisions.json: {exc}") from exc
    d7 = decisions.get("D7", {})
    if not d7.get("reviewer_name") or not d7.get("signed_off"):
        raise RuntimeError(
            "G4 LOCK: decisions.json D7 is missing a named human reviewer and/or signed_off == true. "
            "An actual independent human scientist must sign off before confirmatory generation."
        )
    # Attempt counter check
    if PROVENANCE_LEDGER.exists():
        attempts = [json.loads(line) for line in PROVENANCE_LEDGER.read_text().splitlines() if line.strip()]
        confirm_attempts = [a for a in attempts if a.get("event") == "GENERATE_CONFIRM"]
        if len(confirm_attempts) >= MAX_ATTEMPTS:
            raise RuntimeError(
                f"G4 LOCK: already {len(confirm_attempts)} confirmatory generation attempt(s) recorded "
                f"(D15 limit = {MAX_ATTEMPTS}). No further generation is permitted."
            )


# ------------------------------------------------------------------------------- generate
def generate(tag_kind: str, cells: Optional[Sequence[Tuple[str, str]]] = None,
             seed_override: Optional[int] = None) -> List[Dict[str, Any]]:
    """Generate scenarios for tag_kind='pilot' or tag_kind='confirm'.

    For 'confirm' the G4 lock is enforced (requires prereg.sha256 + decisions.json D7).
    For 'pilot' the lock is skipped (used in tests and feasibility checks).

    ``cells`` is a list of (structure, family) pairs drawn for this generation run; if None,
    a uniform schedule over all 256 cells is used to fill QUOTA.

    Returns: list of scenario dicts with 'ground_truth' and 'content_hash' populated.
    NOTE: scenario ids are opaque V3C-NNNNNN; the caller is responsible for shuffling
    the order and reassigning sequential ids (F9).
    """
    if tag_kind == "confirm":
        _check_g4_lock()
    elif tag_kind != "pilot":
        raise ValueError(f"tag_kind must be 'pilot' or 'confirm', got {tag_kind!r}")

    rng = np.random.default_rng(seed_override if seed_override is not None else
                                (derive_seed(tag_kind, 0)))
    if cells is None:
        all_cells = [(s, f) for s in STRUCTURES for f in FAMILIES]
        cells = [all_cells[i] for i in rng.permutation(len(all_cells))]

    workloads = _cyc(WORKLOADS, 10000, rng)
    observabilities = _cyc(OBSERVABILITY, 10000, rng)
    interventions_ = _cyc(INTERVENTIONS, 10000, rng)
    temporal_all = _cyc(TEMPORAL, 10000, rng)
    temporal_lag = _cyc(LAG_ONLY_TEMPORAL, 10000, rng)
    negatives = _cyc(NEGATIVES, 10000, rng)

    out: List[Dict[str, Any]] = []
    ni = 0
    cell_ptr = 0
    for j in range(10000):  # over-draw; stop when quota satisfied
        neg: Optional[str] = None
        if j % 4 == 3:
            neg = negatives[ni]; ni += 1
            need = NEG_STRUCT.get(neg)
            if need:
                opts = [c for c in cells if c[0] == need]
                if opts:
                    cell = opts[(j // 4) % len(opts)]
                else:
                    neg = "indistinguishable_onsets"
                    cell = cells[cell_ptr % len(cells)]; cell_ptr += 1
            else:
                cell = cells[cell_ptr % len(cells)]; cell_ptr += 1
        else:
            cell = cells[cell_ptr % len(cells)]; cell_ptr += 1
        structure, family = cell
        if neg in NEEDS_EDGE and structure in HIDDEN_ROOT_STRUCTS:
            neg = "coincidental_anomaly"
        temporal = temporal_lag[j] if family in FAMILY_SHAPE else temporal_all[j]
        sc = build_scenario(tag_kind, j + 1, structure, family, temporal,
                            workloads[j], observabilities[j], interventions_[j], neg)
        out.append(sc)
        # check if quota satisfied for pilot (for pilot, just return first 200 as a smoke test)
        if tag_kind == "pilot" and len(out) >= 200:
            break
    return out
