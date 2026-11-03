"""Semantic fingerprints for scenario records (Sprint 4.3.0, Phase 1).

A scenario's identity for independence purposes is its CONTENT, never its id, name, seed or split.
Several layered fingerprints are produced because different notions of "the same" matter:

``raw_content``       every field except id/name/seed/split/bookkeeping flags.
``effective_dynamics`` exactly the fields the legacy metric generator
                       (``scripts/run_reproducible_evaluation.generate_scenario_metrics``) consumes:
                       root, ordered causal_path, injected_at_t. Two records with the same value
                       produce statistically identical observable series (differing only in noise
                       realisation), whatever their labels say.
``structure``         label-free structure: Weisfeiler-Lehman hash of the causal graph with the root
                       marked, plus confounded flag and size. Detects shared propagation structure
                       across renamed services.
``template``          structure + fault_type + coarse timing (parameter-only variations collapse).
``edge_set`` / ``affected_set`` raw sets for similarity scoring.

Functions are pure and deterministic.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping, Sequence, Tuple

import networkx as nx

# Fields that are labels/bookkeeping, not content.
NON_CONTENT_FIELDS = frozenset({
    "fault_id", "scenario_id", "name", "seed", "split", "ground_truth_locked",
    "parent_scenario", "generator_version", "content_hash", "provenance",
    "dataset_role", "template_id", "group_id",
})

# Fields consumed by the legacy generator (``generate_scenario_metrics``).
LEGACY_EFFECTIVE_FIELDS = ("root_cause_service", "causal_path", "injected_at_t")


def _canon(obj: Any) -> Any:
    """Canonicalise to JSON-stable form (tuples->lists, sets->sorted lists, floats rounded)."""
    if isinstance(obj, Mapping):
        return {str(k): _canon(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, (list, tuple)):
        return [_canon(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted(_canon(v) for v in obj)
    if isinstance(obj, float):
        return round(obj, 6)
    return obj


def sha256_json(obj: Any) -> str:
    return hashlib.sha256(json.dumps(_canon(obj), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _scenario_id(sc: Mapping[str, Any]) -> str:
    return str(sc.get("fault_id") or sc.get("scenario_id"))


def _edges(sc: Mapping[str, Any]) -> List[Tuple[str, str]]:
    return [tuple(e) for e in sc.get("causal_path", [])]


def _services(sc: Mapping[str, Any]) -> FrozenSet[str]:
    nodes = set()
    for a, b in _edges(sc):
        nodes.add(a)
        nodes.add(b)
    nodes.update(sc.get("affected_services", []))
    if sc.get("root_cause_service"):
        nodes.add(sc["root_cause_service"])
    return frozenset(nodes)


def structure_hash(sc: Mapping[str, Any]) -> str:
    """Label-free hash of the causal structure with the root marked (isomorphism class via WL)."""
    g = nx.DiGraph()
    root = sc.get("root_cause_service")
    for n in _services(sc):
        g.add_node(n, role="root" if n == root else "node")
    for a, b in _edges(sc):
        g.add_edge(a, b)
    wl = nx.weisfeiler_lehman_graph_hash(g, node_attr="role", iterations=3)
    return sha256_json({"wl": wl, "n": g.number_of_nodes(), "m": g.number_of_edges(),
                        "confounded": bool(sc.get("confounded", False)),
                        "n_affected": len(sc.get("affected_services", []))})


def _coarse_time(t: Any) -> float:
    try:
        return round(float(t) / 30.0) * 30.0
    except (TypeError, ValueError):
        return 0.0


@dataclass(frozen=True)
class ScenarioFingerprint:
    scenario_id: str
    raw_content: str
    effective_dynamics: str
    structure: str
    template: str
    edge_set: FrozenSet[Tuple[str, str]] = field(default_factory=frozenset)
    affected_set: FrozenSet[str] = field(default_factory=frozenset)
    root: str = ""
    fault_type: str = ""
    confounded: bool = False
    injected_at_t: float = 0.0
    recovery_t: float = 0.0


def fingerprint(sc: Mapping[str, Any]) -> ScenarioFingerprint:
    content = {k: v for k, v in sc.items() if k not in NON_CONTENT_FIELDS}
    eff = {k: sc.get(k) for k in LEGACY_EFFECTIVE_FIELDS}
    eff["causal_path"] = [list(e) for e in sc.get("causal_path", [])]
    tmpl = {"structure": structure_hash(sc), "fault_type": sc.get("fault_type"),
            "t": _coarse_time(sc.get("injected_at_t")),
            "rec": _coarse_time(sc.get("expected_recovery_t"))}
    return ScenarioFingerprint(
        scenario_id=_scenario_id(sc),
        raw_content=sha256_json(content),
        effective_dynamics=sha256_json(eff),
        structure=structure_hash(sc),
        template=sha256_json(tmpl),
        edge_set=frozenset(_edges(sc)),
        affected_set=frozenset(sc.get("affected_services", [])),
        root=str(sc.get("root_cause_service", "")),
        fault_type=str(sc.get("fault_type", "")),
        confounded=bool(sc.get("confounded", False)),
        injected_at_t=float(sc.get("injected_at_t", 0.0) or 0.0),
        recovery_t=float(sc.get("expected_recovery_t", 0.0) or 0.0),
    )


def _jaccard(a: FrozenSet, b: FrozenSet) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def similarity(a: ScenarioFingerprint, b: ScenarioFingerprint) -> float:
    """Weighted similarity in [0,1]: edges 0.4, affected 0.2, root 0.15, type 0.1, timing 0.1, conf 0.05."""
    timing = 1.0 if (abs(a.injected_at_t - b.injected_at_t) <= 1e-9
                     and abs(a.recovery_t - b.recovery_t) <= 1e-9) else 0.0
    return (0.40 * _jaccard(a.edge_set, b.edge_set)
            + 0.20 * _jaccard(a.affected_set, b.affected_set)
            + 0.15 * float(a.root == b.root)
            + 0.10 * float(a.fault_type == b.fault_type)
            + 0.10 * timing
            + 0.05 * float(a.confounded == b.confounded))


def fingerprint_all(scenarios: Iterable[Mapping[str, Any]]) -> List[ScenarioFingerprint]:
    return [fingerprint(s) for s in scenarios]
