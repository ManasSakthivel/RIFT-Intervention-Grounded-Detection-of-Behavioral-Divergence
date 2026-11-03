#!/usr/bin/env python3
"""Agent 7: can DATASET_PROTOCOL §3.2 periphery (0-3 extra observed nodes, attached from a random non-root node,
optional 2nd edge) meet the §6/§8.5 gates (>=90% unique topology hash, no hash shared by >3, K>=250, max group<=25)?
Pure design-space simulation with the frozen independence.topology_hash. No scenario data, no methods. Seed 4513."""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np, networkx as nx
REPO = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(REPO))
from src.rift.scenarios.independence import topology_hash
from src.rift.scenarios.splitter import build_groups
sys.path.insert(0, str(Path(__file__).parent))
import importlib.util
spec = importlib.util.spec_from_file_location("t5", str(Path(__file__).with_name("t5_feasibility.py")))
src = Path(__file__).with_name("t5_feasibility.py").read_text().split("lib = []")[0]   # MOTIFS definitions only
ns = {"__file__": str(Path(__file__).with_name("t5_feasibility.py"))}; exec(src, ns); MOTIFS = ns["MOTIFS"]
rng = np.random.default_rng(4513)
FAM = 16

def sc_from(G, hid):
    nodes = [{"id": n, "hidden": bool(G.nodes[n]["h"])} for n in G]
    faults = [{"service": n} for n in G if G.nodes[n]["r"]]
    return {"graph": {"nodes": nodes, "edges": [{"src": a, "dst": b} for a, b in G.edges]}, "faults": faults}

def periphery(M, k_dist):
    G = M.copy(); k = int(rng.choice(len(k_dist), p=k_dist))
    for i in range(k):
        cand = [n for n in G if not G.nodes[n]["r"]] or list(G)
        s = cand[rng.integers(len(cand))]; new = f"p{i}"; G.add_node(new, h=0, r=0); G.add_edge(s, new)
        if rng.random() < 0.5:
            c2 = [n for n in G if n not in (s, new) and not nx.has_path(G, new, n)]
            if c2: G.add_edge(c2[rng.integers(len(c2))], new)
    return G

out = {}
for label, dist in {"uniform_0-3": [.25, .25, .25, .25], "heavy_periphery_(1-3)": [0, 1/3, 1/3, 1/3]}.items():
    items = {}; thash = Counter(); per_motif = {}
    sid = 0
    for k, M in MOTIFS.items():
        for fam in range(FAM):
            for j in range(8):          # ~7.8 scenarios per template (2000/256)
                G = periphery(M, dist); sid += 1
                s = sc_from(G, None); s.update(scenario_id=f"c{sid}", template_id=f"{k}|f{fam}")
                items[s["scenario_id"]] = s; h = topology_hash(s); s["_h"] = h; thash[h] += 1
    n = len(items)
    uniq = sum(1 for s in items.values() if thash[s["_h"]] == 1) / n
    shared_gt3 = sum(c for c in thash.values() if c > 3) / n
    grp = build_groups(items, [lambda s: ("t", s["template_id"]), lambda s: ("topo", topology_hash(s))])
    sizes = Counter(grp.values())
    out[label] = {"n_scenarios": n, "distinct_topology_hashes": len(thash), "share_with_unique_hash": uniq,
                  "share_in_hashes_used_by_more_than_3": shared_gt3, "max_scenarios_per_hash": max(thash.values()),
                  "K_groups": len(sizes), "max_group_size": max(sizes.values()), "median_group_size": float(np.median(list(sizes.values()))),
                  "gates": {"unique>=0.90": uniq >= 0.90, "no_hash_>3": max(thash.values()) <= 3, "K>=250": len(sizes) >= 250, "max_group<=25": max(sizes.values()) <= 25}}
Path(__file__).with_name("geometry_feasibility.json").write_text(json.dumps(out, indent=1, default=float))
print(json.dumps(out, indent=1, default=float))
