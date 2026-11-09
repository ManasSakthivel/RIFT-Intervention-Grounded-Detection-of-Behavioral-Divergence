"""Cross-split leakage checks for a candidate confirmatory set (Agent 2 / dataset independence).

Compares a CANDIDATE set (e.g. the future CONFIRM set, label-stripped) against READABLE protected sets
(dev, val, adversarial dev). It never opens a sealed file: the sealed held-out set is handled only by
``construction_disjoint_from_sealed`` which inspects the candidate's own identifiers, never sealed content.

Checks (all on the candidate's pairs with each protected set only):
  ids          shared scenario_id
  seeds        shared seed value
  content      shared content_hash
  dynamics     shared dynamics_hash (name-agnostic generative spec)
  topology     shared topology_hash (name-agnostic WL hash, root roles read from ``faults``, not labels)
  template     shared template_id
  joint_cell   shared (structure, family, temporal, workload, observability, intervention)
  near         spec_similarity >= threshold (default 0.88, dataset protocol §8.3)
  groups       union-find component (template OR topology) spanning candidate and a protected set
  intra        duplicate content/dynamics/topology inside the candidate (R-DUP / R-CAP1)

Pure functions; no I/O except the optional ``load_scenarios`` helper, which refuses sealed file names.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import numpy as np

from .independence import dynamics_hash, joint_cell, spec_vector, topology_hash
from .splitter import build_groups

DEFAULT_NEAR_THRESHOLD = 0.88
# Id prefixes already used by the readable/protected generators.
RESERVED_ID_PREFIXES = ("V2D-", "V2V-", "V2H-", "ADV-")
CONFIRM_ID_PREFIX = "V3C-"
FROZEN_GENERATOR_VERSION = "rift-scenario-gen/2.0.0"
_SEALED_NAME_FRAGMENTS = ("heldout_candidate", "held_out_test", "heldout_status", "results/held_out")
_CAT_KEYS = ("structure", "family", "temporal", "workload", "observability", "intervention", "negative")


def load_scenarios(path: Path) -> List[Dict[str, Any]]:
    """Load a readable scenario file. Refuses any path that names a sealed held-out file."""
    p = str(path).replace("\\", "/")
    if any(frag in p for frag in _SEALED_NAME_FRAGMENTS):
        raise PermissionError(f"refusing to open protected/sealed file: {path}")
    data = json.loads(Path(path).read_text())
    return list(data["scenarios"] if isinstance(data, dict) else data)


def _keys(sc: Mapping[str, Any]) -> Dict[str, Any]:
    return {"ids": sc["scenario_id"], "seeds": sc["seed"], "content": sc["content_hash"],
            "dynamics": dynamics_hash(sc), "topology": topology_hash(sc),
            "template": sc["template_id"], "joint_cell": joint_cell(sc)}


def _sim_matrix(a: Sequence[Mapping[str, Any]], b: Sequence[Mapping[str, Any]]) -> np.ndarray:
    """Vectorised ``independence.spec_similarity`` for all pairs (identical formula)."""
    va = np.array([spec_vector(s) for s in a])
    vb = np.array([spec_vector(s) for s in b])
    ca = np.array([[s["dimensions"][k] for k in _CAT_KEYS] for s in a], dtype=object)
    cb = np.array([[s["dimensions"][k] for k in _CAT_KEYS] for s in b], dtype=object)
    cat = np.zeros((len(a), len(b)))
    for j in range(len(_CAT_KEYS)):
        cat += (ca[:, j][:, None] == cb[:, j][None, :])
    num = 1.0 - np.abs(va[:, None, :] - vb[None, :, :]).mean(axis=2)
    return 0.6 * cat / 7.0 + 0.4 * num


def check_candidate(candidate: Sequence[Mapping[str, Any]],
                    protected: Mapping[str, Sequence[Mapping[str, Any]]],
                    near_threshold: float = DEFAULT_NEAR_THRESHOLD) -> Dict[str, Any]:
    """Leakage report for ``candidate`` against each readable protected set. ``ok`` iff every count is 0."""
    ckeys = [_keys(s) for s in candidate]
    per_set: Dict[str, Dict[str, Any]] = {}
    for name, scs in protected.items():
        pkeys = [_keys(s) for s in scs]
        row: Dict[str, Any] = {}
        for k in ("ids", "seeds", "content", "dynamics", "topology", "template", "joint_cell"):
            row[k] = len({c[k] for c in ckeys} & {p[k] for p in pkeys})
        if len(candidate) and len(scs):
            sims = _sim_matrix(list(candidate), list(scs))
            row["near_pairs"] = int((sims >= near_threshold).sum())
            row["max_similarity"] = round(float(sims.max()), 4)
        else:
            row["near_pairs"], row["max_similarity"] = 0, 0.0
        per_set[name] = row

    items = {("C", s["scenario_id"]): s for s in candidate}
    for name, scs in protected.items():
        items.update({(name, s["scenario_id"]): s for s in scs})
    grp = build_groups(items, [lambda s: ("t", s["template_id"]), lambda s: ("topo", topology_hash(s))])
    members: Dict[str, set] = {}
    for (origin, _), g in grp.items():
        members.setdefault(g, set()).add(origin)
    spanning = sorted(g for g, o in members.items() if "C" in o and len(o) > 1)

    intra = {"content": _dup_count(ck["content"] for ck in ckeys),
             "dynamics": _dup_count(ck["dynamics"] for ck in ckeys),
             "topology": _dup_count(ck["topology"] for ck in ckeys),
             "ids": _dup_count(ck["ids"] for ck in ckeys)}
    flat = [v for row in per_set.values() for k, v in row.items() if k != "max_similarity"]
    ok = all(v == 0 for v in flat) and not spanning and intra["content"] == 0 and intra["dynamics"] == 0 \
        and intra["ids"] == 0
    return {"ok": bool(ok), "n_candidate": len(candidate), "near_threshold": near_threshold,
            "per_protected_set": per_set, "spanning_groups": spanning, "intra_candidate_duplicates": intra}


def _dup_count(it) -> int:
    c = Counter(it)
    return sum(n - 1 for n in c.values() if n > 1)


def construction_disjoint_from_sealed(candidate: Sequence[Mapping[str, Any]],
                                      frozen_structures: Sequence[str]) -> Dict[str, Any]:
    """Exclusion-by-construction facts about the candidate itself (dataset protocol §8.2).

    Uses only the candidate's identifiers and the PUBLIC frozen structure list. No sealed content is read.
    """
    bad_prefix = [s["scenario_id"] for s in candidate if not str(s["scenario_id"]).startswith(CONFIRM_ID_PREFIX)]
    reserved = [s["scenario_id"] for s in candidate if str(s["scenario_id"]).startswith(RESERVED_ID_PREFIXES)]
    frozen = set(frozen_structures)
    old_struct = [s["scenario_id"] for s in candidate if s["dimensions"]["structure"] in frozen]
    old_tpl = [s["scenario_id"] for s in candidate if s["template_id"].split("|")[0] in frozen]
    same_gen = [s["scenario_id"] for s in candidate if s.get("generator_version") == FROZEN_GENERATOR_VERSION]
    token_in_id = [s["scenario_id"] for s in candidate
                   if str(s["dimensions"]["structure"]).lower() in str(s["scenario_id"]).lower()]
    res = {"id_prefix_violations": len(bad_prefix), "reserved_prefix_ids": len(reserved),
           "frozen_structure_names": len(old_struct), "frozen_template_structures": len(old_tpl),
           "frozen_generator_version": len(same_gen), "structure_token_in_id": len(token_in_id)}
    res["ok"] = all(v == 0 for v in res.values())
    return res
