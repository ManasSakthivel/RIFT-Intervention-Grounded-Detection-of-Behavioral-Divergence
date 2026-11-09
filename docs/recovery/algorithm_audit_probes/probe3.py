import sys, json, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "."); sys.path.insert(0, "src")
import numpy as np, pandas as pd, networkx as nx
from src.rift.ebd.ebd import _check_r1, compute_ebd
from src.rift.fci.fci_runner import PAGResult, PAGEdge, PAGEdgeType
from src.rift.identifiability.identifiability import identify_query

# (a) 15 s Prometheus step vs delta_t=10 in R1 persistence
df = pd.DataFrame({"time":[float(i*15) for i in range(20)], "value":[0.0]*10+[50.0]*10})
print("PROBE10 step=15s,delta_t=10:", _check_r1(df,0.0,10.0,3.0,2,10.0,0.0))
df = pd.DataFrame({"time":[float(i*10) for i in range(20)], "value":[0.0]*10+[50.0]*10})
print("PROBE10 step=10s,delta_t=10:", _check_r1(df,0.0,10.0,3.0,2,10.0,0.0))
# zero-variance baseline
print("PROBE11 std=0:", _check_r1(df,0.0,0.0,3.0,2,10.0,0.0))

# (b) null false-alarm rate of e2e Stage-2 rule (std from first half, max |z| over all windows)
rng=np.random.default_rng(0); fp=0; N=2000
for _ in range(N):
    v=rng.normal(50,5,30)
    half=v[:15]; z=np.abs(v-half.mean()).max()/(half.std(ddof=1)+1e-9)
    fp+= z>3.0
print("PROBE12 per-service null alarm rate (n=30, baseline=first 15):", fp/N)
fp=0
for _ in range(N):
    v=rng.normal(50,5,30)
    fp+= any(np.abs(v-v[:15].mean()).max()/(v[:15].std(ddof=1)+1e-9)>3.0 for _ in range(1))
# 10 services: P(at least one alarm)
print("PROBE12 P(>=1 of 10 services alarms)=", 1-(1-0.1)**10 if False else None)

# (c) identify_query optimism
p=PAGResult(variables=["A","B","C"],edges=[PAGEdge("A","B",PAGEdgeType.UNDIRECTED)])
r=identify_query(p,"A","B"); print("PROBE13 A o-o B:", r.status.value, r.method.value, r.adjustment_set)
p=PAGResult(variables=["A","B","C"],edges=[PAGEdge("C","A",PAGEdgeType.BIDIRECTED),PAGEdge("A","B",PAGEdgeType.DIRECTED)])
print("PROBE13 A<->C, A->B:", identify_query(p,"A","B").status.value)
p=PAGResult(variables=["A","B","C"],edges=[PAGEdge("C","B",PAGEdgeType.BIDIRECTED),PAGEdge("C","A",PAGEdgeType.DIRECTED),PAGEdge("A","B",PAGEdgeType.DIRECTED)])
r=identify_query(p,"A","B"); print("PROBE13 C->A, C<->B (confounder on target side), A->B:", r.status.value, r.method.value, r.adjustment_set)
p=PAGResult(variables=["A","B"],edges=[])
print("PROBE13 no edge A,B:", identify_query(p,"A","B").status.value, identify_query(p,"A","B").method.value)

# (d) stage4 artifact top EBD
from src.rift.pipeline.stage4_attribution import build_evidence
from src.rift.fci.fci_runner import run_fci
saved=json.load(open("artifacts/stage4_intervention_results.json"))
ev=build_evidence(saved)
print("PROBE14 incident_window", ev.incident_window, "n_pre", ev.n_pre, "n_act", ev.n_active)
print("PROBE14 baseline std (ms):", {k:round(v['std'],3) for k,v in ev.baselines.items()})
from src.rift.pipeline.stage4_attribution import infer
import src.rift.pipeline.stage4_attribution as s4
wide=pd.concat([m.set_index("time")[["value"]].rename(columns={"value":s}) for s,m in ev.metrics.items()],axis=1).dropna()
print("PROBE14 wide shape", wide.shape, "(rows are pre+active concatenated; time index duplicates?)", wide.index.is_unique)
