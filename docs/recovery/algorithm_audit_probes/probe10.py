import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "."); sys.path.insert(0, "src")
import networkx as nx
from src.rift.pipeline.e2e_runner import RIFTEndToEndRunner, MockTelemetry
try:
    RIFTEndToEndRunner(MockTelemetry(1), ["A","B"], nx.DiGraph([("A","B")]), dry_run=False)
except Exception as e: print("PROBE17 e2e dry_run=False ->", type(e).__name__, str(e)[:90])
from src.rift.intervention.network_intervention import NetworkInterventionRecord
try:
    NetworkInterventionRecord("r","s","s","1.1.1.1","eth0",100,5,0,"10:","1:")
except Exception as e: print("PROBE18 lifecycle tc_handle='10:' ->", type(e).__name__)
# cmd emitted for band 1
from src.rift.intervention.network_intervention import NetworkInterventionEngine
import subprocess
class Rec(NetworkInterventionEngine):
    def _run_cmd(s,cmd): s.l.append(" ".join(cmd)); return subprocess.CompletedProcess(cmd,0,b"",b"")
e=Rec(dry_run=True); e.l=[]
e.apply(NetworkInterventionRecord("r","s","s","10.0.0.1","eth0",100,5,0,"1:","1:"))
print("PROBE19 band-1 cmds:"); [print("   ",c) for c in e.l[:2]]
