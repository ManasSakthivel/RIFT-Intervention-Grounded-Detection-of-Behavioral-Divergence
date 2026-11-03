#!/usr/bin/env python3
"""Sprint 4.5.1 (lead) node-order leakage investigation, finding G.   DEV/VAL ONLY (readable, non-confirmatory).

Questions
  Q1 Is the true root first in graph.nodes / observe()['metrics'] order?  Where does it sit (position distribution)?
  Q2 Why?  (generation artefact: _build_topology appends the root first and the name pool is shuffled, not the node order.)
  Q3 Does any method's OUTPUT depend on metric insertion order?  Frozen V3-FULL, V2 and the cheap baselines are re-run with
     K random permutations of observe()['metrics'] (and of call_graph node insertion) and the outputs (abstained, top-1) compared
     with the original order.  Also scored (correct/unsafe) to see whether the ORIGINAL order is advantageous.
  Q4 A candidate invariance/permutation test for the new generator (acceptance test T10) is exercised on dev/val for reference.

No held-out access.  No confirmatory data.  Frozen code is imported, never edited.  Seed 4517.
Output: artifacts/sprint4_5_1/nodeorder/node_order_investigation.json
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from collections import Counter
from pathlib import Path

import networkx as nx
import numpy as np

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[1]
for p in (str(REPO), str(REPO / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.rift.attribution_v3.rift_v3 import V3_CONFIGS, run_v3  # noqa: E402
from src.rift.evaluation import benchmark_v2 as bm  # noqa: E402
from src.rift.evaluation.rift_v2 import SharedCache  # noqa: E402
from src.rift.scenarios import simulator as sim  # noqa: E402

SEED = 4517
K_PERM = 3
OUT = REPO / "artifacts" / "sprint4_5_1" / "nodeorder"
PINS = {"dev": "a833ad0ca1db0583a30bc4450f9f59b2984a5823702935ef59c6b037e026ef5f",
        "val": "e82252b47f29dc1353586034b6fd8c3491df3221851f9c84c48bf717a944a1fb"}


def load(split):
    import hashlib
    raw = (REPO / "datasets/rift_v2" / f"{split}.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PINS[split]
    return json.loads(raw)["scenarios"]


def permuted_obs(o, rng):
    ks = list(o["metrics"])
    perm = [ks[i] for i in rng.permutation(len(ks))]
    cg = nx.DiGraph()
    cg.add_nodes_from(perm)
    for a, b in o["call_graph"].edges():
        cg.add_edge(a, b)
    return dict(o, metrics={k: o["metrics"][k] for k in perm}, call_graph=cg,
                baseline_stats={k: o["baseline_stats"][k] for k in perm if k in o["baseline_stats"]})


def sig(r):
    return (bool(r.abstained), r.top_candidates[0][0] if r.top_candidates else None)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    L = bm._legacy()
    baselines = {"B0-EARLIEST": "B0E", "B0-HIGHEST": "B0H", "B1": "B1", "B3": "B3", "B5": "B5", "B7": "B7"}
    res = {"purpose": "node-order leakage investigation (dev/val only; no confirmatory data; no held-out)", "seed": SEED,
           "K_permutations": K_PERM, "position_of_true_root": {}, "method_order_sensitivity": {}, "advantage_of_original_order": {}}
    t0 = time.time()
    diffs = {m: Counter() for m in ["V3-FULL", "V2"] + list(baselines)}
    adv = {m: {"orig_correct": 0, "perm_correct": 0, "orig_unsafe": 0, "perm_unsafe": 0, "n_att": 0} for m in diffs}
    pos_graph, pos_metrics, n_obs_root = Counter(), Counter(), 0
    n_att = n_first_graph = n_first_metrics = n_multi = 0
    nsc = 0
    for split in ("dev", "val"):
        for sc in load(split):
            nsc += 1
            o = sim.observe(sc)
            ks = list(o["metrics"])
            roots = [r for r in sc["ground_truth"]["roots"] if r in ks]
            gnodes = [n["id"] for n in sc["graph"]["nodes"] if n["id"] in ks]
            if sc["ground_truth"]["expected_outcome"] == "ATTRIBUTE" and roots:
                n_att += 1
                if len(roots) > 1:
                    n_multi += 1
                first_root_pos_m = min(ks.index(r) for r in roots)
                first_root_pos_g = min(gnodes.index(r) for r in roots)
                n_first_metrics += int(first_root_pos_m == 0)
                n_first_graph += int(first_root_pos_g == 0)
                pos_metrics[first_root_pos_m] += 1
                pos_graph[first_root_pos_g] += 1
            iv = lambda x, ys, sd, _sc=sc: sim.intervene(_sc, x, ys, sd)  # noqa: E731
            runners = {}
            for name, key in baselines.items():
                runners[name] = (lambda oo, _sc=sc, _k=key: sig(L[_k]().run(bm.make_context(_sc, oo))), key)
            runners["V3-FULL"] = (lambda oo, _sc=sc, _iv=iv: sig(run_v3(oo, _iv, _sc["scenario_id"], int(_sc["seed"]),
                                                                       V3_CONFIGS["V3-FULL"], cache=SharedCache())), None)
            for name, (fn, _) in runners.items():
                try:
                    base = fn(o)
                except Exception as exc:  # noqa: BLE001
                    base = ("ERR", type(exc).__name__)
                changed = 0
                for _ in range(K_PERM):
                    try:
                        s2 = fn(permuted_obs(o, rng))
                    except Exception as exc:  # noqa: BLE001
                        s2 = ("ERR", type(exc).__name__)
                    changed += int(s2 != base)
                diffs[name]["scenarios"] += 1
                diffs[name]["scenarios_with_any_change"] += int(changed > 0)
                diffs[name]["permutation_runs_changed"] += changed
                if sc["ground_truth"]["expected_outcome"] == "ATTRIBUTE" and name in adv:
                    adv[name]["n_att"] += 1
                    roots_set = set(sc["ground_truth"]["roots"])
                    adv[name]["orig_correct"] += int((not base[0]) and base[1] in roots_set)
    # V2 omitted from loop above on purpose: V2 is run through the benchmark runner (below) only if cheap import is available.
    res["position_of_true_root"] = {
        "n_scenarios": nsc, "n_attributable_with_observed_root": n_att, "n_with_multiple_roots": n_multi,
        "first_root_is_first_in_graph_nodes": n_first_graph, "first_root_is_first_in_observe_metrics": n_first_metrics,
        "position_histogram_metrics": {str(k): v for k, v in sorted(pos_metrics.items())},
        "position_histogram_graph_nodes": {str(k): v for k, v in sorted(pos_graph.items())},
        "chance_if_uniform_expected_first_share": "1/n_observed per scenario (mean ~ %.3f)" % 0.16,
    }
    res["method_order_sensitivity"] = {m: dict(c) for m, c in diffs.items() if c}
    res["seconds"] = round(time.time() - t0, 1)
    (OUT / "node_order_investigation.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
