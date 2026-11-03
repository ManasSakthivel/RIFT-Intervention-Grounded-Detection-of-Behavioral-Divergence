#!/usr/bin/env python3
"""Agent 7: exact upper bound on distinct topology hashes reachable under DATASET_PROTOCOL §3.1-3.2 (design space only)."""
import json, sys
from pathlib import Path
import networkx as nx
REPO = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(REPO))
from src.rift.scenarios.independence import topology_hash
src = Path(__file__).with_name("t5_feasibility.py").read_text()
head = src.split("lib = []")[0]
tail = "def peripheries" + src.split("def peripheries")[1].split("tot = {}")[0]
ns = {"__file__": str(Path(__file__).with_name("t5_feasibility.py"))}
exec(head, ns); exec("import networkx as nx\n" + tail, ns)
MOTIFS, peripheries = ns["MOTIFS"], ns["peripheries"]
def sc_from(G):
    return {"graph": {"nodes": [{"id": n, "hidden": bool(G.nodes[n]["h"])} for n in G],
                      "edges": [{"src": a, "dst": b} for a, b in G.edges]},
            "faults": [{"service": n} for n in G if G.nodes[n]["r"]]}
allh = set(); per = {}
for k, M in MOTIFS.items():
    hs = set()
    for G in peripheries(M):
        if G.number_of_nodes() <= 12:
            hs.add(topology_hash(sc_from(G)))
    per[k] = len(hs); allh |= hs
out = {"distinct_topology_hashes_per_motif": per, "distinct_total_all_16_motifs": len(allh),
       "scenarios_planned": 2000, "min_distinct_needed_for_90pct_unique_and_none_shared_by_more_than_3": 1800}
Path(__file__).with_name("geometry_bound.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
