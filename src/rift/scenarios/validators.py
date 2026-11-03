"""Scenario QC (Sprint 4.3.0, Phase 4). Label-independent: nothing here runs a method.

Every check returns a list of problem strings (empty == pass). ``validate_scenario`` aggregates them.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

import networkx as nx

from . import GENERATOR_VERSION
from .generator_v2 import (FAMILIES, INTERVENTIONS, NEGATIVES, OBSERVABILITY, STRUCTURES, TEMPORAL,
                           WORKLOADS, build_scenario, compute_ground_truth, content_hash)
from .simulator import DELTA_T, REF_WINDOWS, observed_services

REQUIRED_KEYS = ("scenario_id", "split", "seed", "generator_version", "dimensions", "template_id", "graph",
                 "faults", "telemetry", "workload_params", "intervention", "design", "ground_truth",
                 "content_hash")
REQUIRED_GT = ("expected_outcome", "identifiability", "roots", "abstain_reason")
OUTCOMES = {"ATTRIBUTE", "ABSTAIN_REQUIRED"}
DIM_DOMAIN = {"structure": STRUCTURES, "family": FAMILIES, "temporal": TEMPORAL, "workload": WORKLOADS,
              "observability": OBSERVABILITY, "intervention": INTERVENTIONS}


def check_schema(sc: Mapping[str, Any]) -> List[str]:
    p = [f"missing key {k}" for k in REQUIRED_KEYS if k not in sc]
    if p:
        return p
    p += [f"missing ground_truth.{k}" for k in REQUIRED_GT if k not in sc["ground_truth"]]
    for k, dom in DIM_DOMAIN.items():
        if sc["dimensions"].get(k) not in dom:
            p.append(f"dimension {k}={sc['dimensions'].get(k)!r} outside domain")
    neg = sc["dimensions"].get("negative")
    if neg is not None and neg not in NEGATIVES:
        p.append(f"negative {neg!r} outside domain")
    if sc["ground_truth"].get("expected_outcome") not in OUTCOMES:
        p.append("expected_outcome invalid")
    if sc["generator_version"] != GENERATOR_VERSION:
        p.append(f"generator_version {sc['generator_version']} != {GENERATOR_VERSION}")
    if not isinstance(sc["seed"], int):
        p.append("seed must be int")
    return p


def check_graph(sc: Mapping[str, Any]) -> List[str]:
    p: List[str] = []
    ids = [n["id"] for n in sc["graph"]["nodes"]]
    if len(set(ids)) != len(ids):
        p.append("duplicate node ids")
    idset = set(ids)
    for e in sc["graph"]["edges"]:
        if e["src"] not in idset or e["dst"] not in idset:
            p.append(f"edge {e['src']}->{e['dst']} references unknown node")
        if e["src"] == e["dst"]:
            p.append("self loop")
        if not (0.0 < e["gain"] <= 2.5):
            p.append(f"gain {e['gain']} out of range")
        if e["lag"] < 0:
            p.append("negative lag")
    g = nx.DiGraph([(e["src"], e["dst"]) for e in sc["graph"]["edges"]])
    s = sc["dimensions"]["structure"]
    cyclic = not nx.is_directed_acyclic_graph(g)
    if s in ("ambiguous", "feedback_like"):
        if not cyclic:
            p.append(f"structure {s} must contain a directed cycle")
    elif cyclic:
        p.append(f"unexpected directed cycle in structure {s}")
    for n in sc["graph"]["nodes"]:
        if n["sigma"] <= 0:
            p.append(f"non-positive sigma at {n['id']}")
    obs = {n["id"] for n in sc["graph"]["nodes"] if not n.get("hidden")}
    for a, b in sc["graph"].get("decoy_edges", []):
        if a not in obs or b not in obs:
            p.append("decoy edge references non-observed node")
        if g.has_edge(a, b):
            p.append("decoy edge duplicates a true edge")
    return p


def check_temporal(sc: Mapping[str, Any]) -> List[str]:
    p: List[str] = []
    n = sc["telemetry"]["n_windows"]
    end = (n - 1) * DELTA_T
    for f in sc["faults"]:
        if f["onset_s"] < 0 or f["onset_s"] > end:
            p.append(f"fault onset {f['onset_s']} outside series")
        if f["amp_ms"] <= 0:
            p.append("non-positive amplitude")
    onset_w = sc["design"]["onset_window"]
    if sc["faults"]:
        ro = sorted({f["onset_s"] for f in sc["faults"] if f["service"] in sc["design"]["true_roots"]})
        if ro and ro[0] < REF_WINDOWS * DELTA_T and sc["dimensions"]["observability"] != "insufficient_samples" \
                and sc["dimensions"]["negative"] != "insufficient_telemetry":
            p.append("root onset inside the reference period")
    if onset_w >= n:
        p.append("onset window beyond series")
    tel = sc["telemetry"]
    if not (0.0 <= tel["missing_frac"] < 0.6):
        p.append("missing_frac out of range")
    return p


def check_intervention(sc: Mapping[str, Any]) -> List[str]:
    iv = sc["intervention"]
    p: List[str] = []
    if iv["magnitude_sigma"] <= 0:
        p.append("non-positive intervention magnitude")
    if not (0.0 < iv["delivered"] <= 1.0):
        p.append("delivered fraction out of (0,1]")
    obs = set(observed_services(sc))
    if iv.get("co_target") and iv["co_target"] not in obs:
        p.append("co_target not observed")
    for s in iv.get("collateral", {}):
        if s not in obs:
            p.append("collateral service not observed")
    if not iv.get("rollback_complete", True):
        p.append("rollback_complete false is not supported by the simulator")
    return p


def check_ground_truth(sc: Mapping[str, Any]) -> List[str]:
    p: List[str] = []
    gt = sc["ground_truth"]
    true_roots = set(sc["design"]["true_roots"])
    obs = set(observed_services(sc))
    if set(gt["roots"]) - obs:
        p.append("ground_truth.roots contains unobserved service")
    if set(gt["roots"]) - true_roots:
        p.append("ground_truth.roots not subset of design.true_roots")
    if gt["expected_outcome"] == "ATTRIBUTE":
        if not gt.get("attributable_roots"):
            p.append("ATTRIBUTE without attributable_roots")
        if not gt["identifiability"].startswith("IDENTIFIABLE"):
            p.append("ATTRIBUTE with non-identifiable label")
    else:
        if gt.get("abstain_reason") is None:
            p.append("ABSTAIN_REQUIRED without reason")
    if compute_ground_truth(sc) != gt:
        p.append("ground truth is not reproducible from the scenario state")
    if sc["content_hash"] != content_hash(sc):
        p.append("content_hash mismatch")
    if sc["template_id"] != f"{sc['dimensions']['structure']}|{sc['dimensions']['family']}":
        p.append("template_id inconsistent with dimensions")
    return p


def check_reproducible(sc: Mapping[str, Any]) -> List[str]:
    """Rebuild from the recorded dimensions and compare hashes."""
    d = sc["dimensions"]
    idx = int(sc["scenario_id"].rsplit("-", 1)[1])
    again = build_scenario(sc["split"], idx, d["structure"], d["family"], d["temporal"], d["workload"],
                           d["observability"], d["intervention"], d["negative"])
    return [] if again["content_hash"] == sc["content_hash"] and again["seed"] == sc["seed"] \
        else ["regeneration from recorded dimensions produced a different scenario"]


def validate_scenario(sc: Mapping[str, Any], reproducibility: bool = True) -> Dict[str, List[str]]:
    res = {"schema": check_schema(sc)}
    if res["schema"]:
        return res
    res["graph"] = check_graph(sc)
    res["temporal"] = check_temporal(sc)
    res["intervention"] = check_intervention(sc)
    res["ground_truth"] = check_ground_truth(sc)
    if reproducibility:
        res["reproducible"] = check_reproducible(sc)
    return res


def validate_all(scenarios: Sequence[Mapping[str, Any]], reproducibility: bool = True) -> Dict[str, Any]:
    failures: Dict[str, Dict[str, List[str]]] = {}
    for sc in scenarios:
        r = validate_scenario(sc, reproducibility)
        bad = {k: v for k, v in r.items() if v}
        if bad:
            failures[sc.get("scenario_id", "?")] = bad
    ids = [s.get("scenario_id") for s in scenarios]
    dup_ids = sorted({i for i in ids if ids.count(i) > 1})
    return {"n": len(scenarios), "n_failed": len(failures), "failures": failures, "duplicate_ids": dup_ids}
