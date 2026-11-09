import sys, json, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "."); sys.path.insert(0, "src")
import numpy as np, pandas as pd
from src.rift.fci.fci_runner import PAGResult, PAGEdge, PAGEdgeType
from src.rift.ebd.ebd import compute_ebd

# ---- Probe 1: R2-failing candidate is still "passing" in harness filters (r1 & r3 only)
times=[float(t) for t in range(0,200,10)]
def series(onset, amp=50.0):
    return pd.DataFrame({"time":times,"value":[0.0 if t<onset else amp for t in times]})
m={"A":series(60),"B":series(80),"C":series(100)}   # A true root, isolated in PAG
base={k:{"mean":0.0,"std":10.0} for k in m}
pag=PAGResult(variables=["A","B","C"],edges=[PAGEdge("B","C",PAGEdgeType.DIRECTED)])
res=compute_ebd(m,base,pag,(0.0,190.0))
print("PROBE1 ebd:",[(r.service_id,r.confidence,r.r1_pass,r.r2_pass,r.r3_pass) for r in res])
passing=[e for e in res if e.r1_pass and e.r3_pass]
print("PROBE1 harness passing_ebd[0]:",passing[0].service_id if passing else None, "conf=",passing[0].confidence if passing else None)

# ---- Probe 2: R3 near-vacuous with o-o edges; BIDIRECTED adds no reachability
pag2=PAGResult(variables=["A","B","C"],edges=[PAGEdge("A","B",PAGEdgeType.UNDIRECTED),PAGEdge("B","C",PAGEdge and PAGEdgeType.UNDIRECTED)])
res2=compute_ebd(m,base,pag2,(0.0,190.0))
print("PROBE2 o-o chain:",[(r.service_id,r.confidence,r.r2_pass,r.r3_pass) for r in res2])
# reversed: C earliest
m3={"A":series(100),"B":series(80),"C":series(60)}
res3=compute_ebd(m3,base,pag2,(0.0,190.0))
print("PROBE2b o-o chain, C earliest:",[(r.service_id,r.confidence,r.r2_pass,r.r3_pass) for r in res3])
pag3=PAGResult(variables=["A","B","C"],edges=[PAGEdge("A","B",PAGEdgeType.DIRECTED),PAGEdge("A","C",PAGEdgeType.BIDIRECTED)])
res4=compute_ebd(m3,base,pag3,(0.0,190.0))
print("PROBE2c:",[(r.service_id,r.confidence,r.identifiability_state,r.r3_pass) for r in res4])

# ---- Probe 3: CID sample size in e2e defaults
from src.rift.pipeline.e2e_runner import RIFTEndToEndRunner, MockTelemetry
import networkx as nx
svcs=["frontend","cart","checkout","payment"]
g=nx.DiGraph([("frontend","cart"),("frontend","checkout"),("checkout","payment")])
class M2(MockTelemetry):
    def collect(self, services, window_s=300.0, **kw):
        out=super().collect(services, window_s=window_s, inject_anomaly=("payment" if window_s>100 else None), anomaly_magnitude=8.0)
        return out
r=RIFTEndToEndRunner(M2(1),svcs,g,dry_run=True).run()
print("PROBE3 final:",r.final_state,r.attribution,r.attribution_confidence)
for st in r.pipeline_stages:
    if st.stage in("CID","EBD","IDENTIFIABILITY","COST_SELECTION"): print("  ",st.stage,json.dumps(st.output_summary,default=str)[:400])

# ---- Probe 4: safety soft checks not enforced
from src.rift.safety.safety import SafetyController
from src.rift.optimizer.cost_model import InterventionCandidate, InterventionCost
c=InterventionCandidate("x","lat","LATENCY",100,10)
cost=InterventionCost(c,blast_radius=0.9,sla_impact=0.5,execution_duration_s=30,rollback_cost=0.1,eig=0.1,eig_normalized=0.1,safety_compliance=0.0,cost_composite=0.5,utility=0.1,authorized=True,authorization_level="SUPERVISED")
sc=SafetyController(approved_namespaces=["rift-eval-a"])
a=sc.assess_pre_intervention(c,cost,"rift-eval-a",0.0)
print("PROBE4 br=0.9 sla=0.5 ->",a.decision.value,a.checks_failed)
a=sc.assess_pre_intervention(c,cost,"rift-eval-a",0.0,human_override=True)
print("PROBE4 override ->",a.decision.value)
sc2=SafetyController(approved_namespaces=["rift-eval-a\n"])
print("PROBE4 newline ns production?",sc2.is_production_namespace("rift-eval-a\n"))
print("PROBE4 default approved_targets empty ->", SafetyController(approved_namespaces=["rift-eval-a"]).assess_pre_intervention(c,cost,"rift-eval-a",0.0).decision.value)

# ---- Probe 5: engine multi-intervention live apply (simulated tc: 'File exists' on 2nd root add)
import subprocess
from src.rift.intervention.network_intervention import NetworkInterventionEngine, NetworkInterventionRecord
class FakeLive(NetworkInterventionEngine):
    def __init__(s): 
        s.dry_run=False; s.sandbox_namespace="rift-eval-a"; s._active_records={}; s.root=False; s.log=[]
    def _run_cmd(s,cmd):
        s.log.append(" ".join(cmd[:6]))
        if cmd[:4]==["tc","qdisc","add","dev"] and "root" in cmd:
            if s.root: return subprocess.CompletedProcess(cmd,2,b"",b"RTNETLINK answers: File exists")
            s.root=True
        return subprocess.CompletedProcess(cmd,0,b"",b"")
e=FakeLive()
for i in (1,2):
    rec=NetworkInterventionRecord(f"r{i}","s","s","10.0.0.1","eth0",100,5,0,f"{i}:","1:")
    rec=e.apply(rec); print("PROBE5 apply",i,rec.status.value)
print("PROBE5 active records after failure:",list(e._active_records))
rec=NetworkInterventionRecord("r9","s","s","10.0.0.1","eth0",100,5,0,"1:","1:")
class FailRollback(FakeLive):
    def _run_cmd(s,cmd): return subprocess.CompletedProcess(cmd,1,b"",b"boom")
f=FailRollback(); out=f.rollback(rec); print("PROBE5 rollback with all-cmd failure ->",out.status.value)

# ---- Probe 6: closed-loop unit saturation
from src.rift.loop.closed_loop import ClosedLoop, ClosedLoopState, RIFTState
cl=ClosedLoop()
for w in (0.3, 2.0, 40.0):
    st=ClosedLoopState(RIFTState.UPDATE,nx.DiGraph(),{},{"a":0.5,"b":0.5})
    st=cl.update_candidate_posterior(st,"a",w); print("PROBE6 w1=",w,"posterior a=",round(st.candidate_posterior["a"],4))

# ---- Probe 7: harness confounded vs non-confounded data identical
sys.path.insert(0,"scripts")
import importlib.util
spec=importlib.util.spec_from_file_location("rre","scripts/run_reproducible_evaluation.py"); rre=importlib.util.module_from_spec(spec); spec.loader.exec_module(rre)
dev=json.load(open("datasets/rift_faults/development.json"))["scenarios"]
cf=[s for s in dev if s["confounded"]][0]
cf2=dict(cf); cf2["confounded"]=False
svc=rre.SyntheticBenchmark.SERVICES
m1=rre.generate_scenario_metrics(cf,svc); m2=rre.generate_scenario_metrics(cf2,svc)
print("PROBE7 confounded flag changes generated metrics?", any(not m1[s].equals(m2[s]) for s in svc))
orc=rre.build_oracle_pag(cf)
print("PROBE7 oracle PAG edges for confounded:",[(e.source,e.target,e.edge_type.value) for e in orc.edges])
