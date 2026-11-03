"""Group-aware splitting (Sprint 4.3.0, Phase 2).

Related scenarios must stay in ONE split. "Related" means sharing any grouping key (template,
topology, root-cause family, propagation mechanism, workload pattern, intervention mechanism ...).
Items are linked with union-find over every key function, so transitive relations (A shares a
template with B, B shares a topology with C) put A, B, C in the same group. Whole groups are then
assigned to splits.

Nothing here looks at labels or method outputs.
"""
from __future__ import annotations

import random
from typing import Any, Callable, Dict, Hashable, List, Mapping, Optional, Sequence, Tuple


class UnionFind:
    def __init__(self) -> None:
        self.parent: Dict[Hashable, Hashable] = {}

    def find(self, x: Hashable) -> Hashable:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: Hashable, b: Hashable) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb, key=str)] = min(ra, rb, key=str)


def build_groups(items: Mapping[str, Any], key_fns: Sequence[Callable[[Any], Hashable]]) -> Dict[str, str]:
    """item_id -> group_id (connected components over shared keys of any key function)."""
    uf = UnionFind()
    for iid in items:
        uf.find(("item", iid))
    for fi, fn in enumerate(key_fns):
        for iid, it in items.items():
            uf.union(("item", iid), ("key", fi, fn(it)))
    comp: Dict[Hashable, str] = {}
    out: Dict[str, str] = {}
    for iid in sorted(items):
        root = uf.find(("item", iid))
        comp.setdefault(root, f"G{len(comp):03d}")
        out[iid] = comp[root]
    return out


def assign_groups(
    group_sizes: Mapping[str, int],
    fractions: Mapping[str, float],
    seed: int,
    forced: Optional[Mapping[str, str]] = None,
) -> Dict[str, str]:
    """
    Whole-group assignment. ``forced`` pins groups (e.g. unseen structures -> held_out).
    Remaining groups go, largest first, to the split with the largest remaining deficit
    (seeded tie-break). Deterministic in ``seed``.
    """
    rng = random.Random(seed)
    forced = dict(forced or {})
    assignment: Dict[str, str] = dict(forced)
    free = [g for g in group_sizes if g not in forced]
    total_free = sum(group_sizes[g] for g in free)
    target = {s: f * total_free for s, f in fractions.items()}
    filled = {s: 0.0 for s in fractions}
    order = sorted(free, key=lambda g: (-group_sizes[g], rng.random()))
    for g in order:
        deficits = {s: target[s] - filled[s] for s in fractions}
        best = max(deficits.values())
        cands = sorted(s for s, d in deficits.items() if d >= best - 1e-9)
        s = cands[rng.randrange(len(cands))]
        assignment[g] = s
        filled[s] += group_sizes[g]
    return assignment


def group_integrity_violations(item_split: Mapping[str, str], item_group: Mapping[str, str]) -> List[Tuple[str, List[str]]]:
    """Groups whose members are not all in one split (empty list == group-aware)."""
    seen: Dict[str, set] = {}
    for iid, g in item_group.items():
        seen.setdefault(g, set()).add(item_split[iid])
    return [(g, sorted(s)) for g, s in sorted(seen.items()) if len(s) > 1]
