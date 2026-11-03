#!/usr/bin/env python3
"""Agent 7: is DATASET_PROTOCOL T5 ('zero isomorphic pairs' between new motifs+periphery and the frozen skeleton library) satisfiable?
Design-space only: uses the frozen _build_topology as a function; reads no scenario data; touches no held-out content."""
import itertools, json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
import networkx as nx
from src.rift.scenarios import generator_v2 as g2

def frozen_graph(kind, extra):
    names = [f"n{i}" for i in range(40)]
    t = g2._build_topology(kind, extra, names)
    G = nx.DiGraph()
    roots = set(t["hidden"]) if kind == "hidden_common_cause" else set(t["roots"])   # faults sit on the hidden node (generator_v2 line ~273)
    for n in t["nodes"]: G.add_node(n, h=0, r=int(n in roots))
    for n in t["hidden"]: G.add_node(n, h=1, r=int(n in roots))
    for a, b in t["edges"]: G.add_edge(a, b)
    return G

def mk(nodes, hidden, edges, roots):
    G = nx.DiGraph()
    for n in nodes: G.add_node(n, h=int(n in hidden), r=int(n in roots))
    G.add_edges_from(edges); return G

MOTIFS = {  # protocol §3.1 table
 "S01": mk("r a b c l1 l2".split(), [], [("r","a"),("a","b"),("b","c"),("a","l1"),("b","l2")], {"r"}),
 "S02": mk("r a b c ga gb gc".split(), [], [("r","a"),("r","b"),("r","c"),("a","ga"),("b","gb"),("c","gc")], {"r"}),
 "S03": mk("r a b p c d".split(), [], [("r","a"),("a","b"),("p","c"),("c","d"),("a","c"),("b","d")], {"r"}),
 "S04": mk("r a b d e f g".split(), [], [("r","a"),("r","b"),("a","d"),("b","d"),("d","e"),("d","f"),("e","g"),("f","g")], {"r"}),
 "S05": mk("r a m p q d".split(), [], [("r","a"),("a","m"),("p","q"),("q","m"),("m","d")], {"r"}),
 "S06": mk("r a b c".split(), [], [("r","a"),("a","b"),("b","c"),("r","c")], {"r"}),
 "S07": mk("f1 f2 f3 h d".split(), [], [("f1","h"),("f2","h"),("f3","h"),("h","d")], {"f1"}),
 "S08": mk("r a b c".split(), [], [("r","a"),("r","b"),("a","b"),("b","c")], {"r"}),
 "S09": mk("r1 a b r2 c".split(), [], [("r1","a"),("a","b"),("r2","b"),("b","c")], {"r1","r2"}),
 "S10": mk("h r a b c".split(), ["h"], [("h","r"),("h","c"),("r","a"),("r","b"),("a","c"),("b","c")], {"r"}),
 "S11": mk("h x y z".split(), ["h"], [("h","x"),("x","y"),("h","z")], {"h"}),
 "S12": mk("h a b c".split(), ["h"], [("h","a"),("h","b"),("a","c"),("b","c")], {"h"}),
 "S13": mk("a b c d".split(), [], [("a","b"),("b","a"),("b","c"),("c","d")], {"a"}),
 "S14": mk("a b c d".split(), [], [("a","b"),("b","a"),("b","c"),("b","d")], {"a"}),
 "S15": mk("r a s p q".split(), [], [("r","a"),("a","s"),("p","q"),("q","s")], {"r"}),
 "S16": mk("r a b c d".split(), [], [("r","a"),("a","b"),("a","c"),("b","c"),("c","d")], {"r"}),
}
lib = []
for kind in g2.STRUCTURES:
    for extra in range(0, 5):
        lib.append((kind, extra, frozen_graph(kind, extra)))
nm = lambda a, b: a["h"] == b["h"] and a["r"] == b["r"]
def iso(G, H):
    return G.number_of_nodes()==H.number_of_nodes() and G.number_of_edges()==H.number_of_edges() and nx.is_isomorphic(G, H, node_match=nm)

out = {"library_size": len(lib), "motif_periphery0_hits": {}, "with_periphery": {}}
for k, M in MOTIFS.items():
    hits = [(kind, e) for kind, e, F in lib if iso(M, F)]
    out["motif_periphery0_hits"][k] = hits

# periphery enumeration: add p in 0..3 observed nodes, each attached by an edge from a non-root existing node,
# optionally a second edge to a LATER node (acyclic wrt insertion order); node total <= 12
def peripheries(M):
    base = list(M.nodes)
    yield M
    def rec(G, k, left):
        if left == 0: return
        cand_src = [n for n in G.nodes if not G.nodes[n]["r"]]
        for s in cand_src:
            G2 = G.copy(); new = f"p{k}"; G2.add_node(new, h=0, r=0); G2.add_edge(s, new)
            yield G2
            yield from rec(G2, k+1, left-1)
            # second edge: new -> some existing later node is unavailable (new is last); use s2 -> new
            for s2 in cand_src:
                if s2 != s and not nx.has_path(G2, new, s2):
                    G3 = G2.copy(); G3.add_edge(s2, new)
                    yield G3
    yield from rec(M, 0, 3)
tot = {}
for k, M in MOTIFS.items():
    seen = set(); n = 0; hit = 0; hit_kinds = set()
    for G in peripheries(M):
        if G.number_of_nodes() > 12: continue
        key = nx.weisfeiler_lehman_graph_hash(G, node_attr=None, iterations=4) + str(sorted((G.nodes[x]["h"], G.nodes[x]["r"]) for x in G))
        n += 1
        for kind, e, F in lib:
            if iso(G, F):
                hit += 1; hit_kinds.add(f"{kind}/extra{e}"); break
    tot[k] = {"variants_enumerated": n, "isomorphic_to_frozen_skeleton": hit, "which": sorted(hit_kinds)[:6]}
out["with_periphery"] = tot
Path(__file__).with_name("t5_feasibility.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps(out["motif_periphery0_hits"], indent=0)); print(json.dumps(tot, indent=0))
