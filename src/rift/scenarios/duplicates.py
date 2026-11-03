"""Duplicate / near-duplicate detection and cross-split leakage matrices (Sprint 4.3.0).

The unit of analysis is the scenario. A "twin" is any other scenario sharing a fingerprint level.
Fingerprint levels, from strictest to loosest:

  raw_content        identical content (modulo id/name/seed/split)
  effective_dynamics identical inputs to the legacy metric generator
  structure          isomorphic causal structure (+ root role, confounded flag, size)
  template           structure + fault type + coarse timing
  near               pairwise similarity >= threshold (not an equivalence relation)
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .fingerprint import ScenarioFingerprint, fingerprint, similarity

LEVELS = ("raw_content", "effective_dynamics", "structure", "template")


def group_by_level(fps: Sequence[ScenarioFingerprint], level: str) -> Dict[str, List[str]]:
    groups: Dict[str, List[str]] = defaultdict(list)
    for fp in fps:
        groups[getattr(fp, level)].append(fp.scenario_id)
    return dict(groups)


def count_distinct(fps: Sequence[ScenarioFingerprint], level: str) -> int:
    return len({getattr(fp, level) for fp in fps})


def duplicate_groups(fps: Sequence[ScenarioFingerprint], level: str = "raw_content") -> List[List[str]]:
    """Groups of >=2 scenarios sharing the fingerprint at ``level``."""
    return [sorted(ids) for ids in group_by_level(fps, level).values() if len(ids) > 1]


def seed_only_variants(scenarios: Sequence[Mapping[str, Any]]) -> List[List[str]]:
    """Groups with identical raw content but different seeds (seed-only variation)."""
    by: Dict[str, List[Tuple[str, Any]]] = defaultdict(list)
    for sc in scenarios:
        fp = fingerprint(sc)
        by[fp.raw_content].append((fp.scenario_id, sc.get("seed")))
    out = []
    for members in by.values():
        if len(members) > 1 and len({s for _, s in members}) > 1:
            out.append(sorted(i for i, _ in members))
    return out


def near_duplicate_pairs(fps: Sequence[ScenarioFingerprint], threshold: float = 0.85,
                         exclude_exact: bool = True) -> List[Tuple[str, str, float]]:
    pairs = []
    for a, b in combinations(fps, 2):
        if exclude_exact and a.raw_content == b.raw_content:
            continue
        s = similarity(a, b)
        if s >= threshold:
            pairs.append((a.scenario_id, b.scenario_id, round(s, 4)))
    return pairs


def leakage_matrix(split_fps: Mapping[str, Sequence[ScenarioFingerprint]], level: str) -> Dict[str, Any]:
    """
    For each ordered pair (A, B): number and fraction of scenarios in A that have >=1 content twin
    at ``level`` in B. Diagonal = within-split duplicates (scenarios whose key repeats inside A).
    Denominator is always |A| (stated explicitly).
    """
    keys = {s: [getattr(fp, level) for fp in fps] for s, fps in split_fps.items()}
    keysets = {s: set(k) for s, k in keys.items()}
    names = list(split_fps)
    cells: Dict[str, Dict[str, Any]] = {}
    for a in names:
        cells[a] = {}
        for b in names:
            if a == b:
                counts: Dict[str, int] = defaultdict(int)
                for k in keys[a]:
                    counts[k] += 1
                n = sum(1 for k in keys[a] if counts[k] > 1)
            else:
                n = sum(1 for k in keys[a] if k in keysets[b])
            d = len(keys[a])
            cells[a][b] = {"n_with_twin": n, "denominator": d, "fraction": (n / d) if d else 0.0}
    shared = {f"{a}&{b}": len(keysets[a] & keysets[b]) for a, b in combinations(names, 2)}
    return {"level": level, "cells": cells, "shared_distinct_keys": shared,
            "distinct_keys": {s: len(v) for s, v in keysets.items()}}


def cross_split_leaks(split_fps: Mapping[str, Sequence[ScenarioFingerprint]], level: str,
                      protected: str) -> List[Tuple[str, str]]:
    """(protected_scenario_id, other_split) for every scenario in ``protected`` with a twin elsewhere."""
    out = []
    others = {s: {getattr(fp, level) for fp in fps} for s, fps in split_fps.items() if s != protected}
    for fp in split_fps[protected]:
        for s, ks in others.items():
            if getattr(fp, level) in ks:
                out.append((fp.scenario_id, s))
    return out
