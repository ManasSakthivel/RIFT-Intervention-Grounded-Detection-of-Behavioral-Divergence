import sys, warnings, io, contextlib
warnings.filterwarnings("ignore")
sys.path.insert(0, "."); sys.path.insert(0, "src")
import numpy as np, pandas as pd
from src.rift.fci.fci_runner import run_fci
rng=np.random.default_rng(1)
def edges(df):
    with contextlib.redirect_stdout(io.StringIO()):
        p=run_fci(df,alpha=0.05,seed=1)
    kinds={}
    for e in p.edges: kinds[e.edge_type.value]=kinds.get(e.edge_type.value,0)+1
    return len(p.edges),kinds
cols=[f"s{i}" for i in range(10)]
# A: independent stationary noise, n=27
tot=[]
for r in range(5):
    df=pd.DataFrame(rng.normal(0,1,(27,10)),columns=cols); tot.append(edges(df)[0])
print("A independent n=27, 10 vars: edges per run", tot)
# B: independent noise but 4 services share a regime step at t=15 (incident), n=27
tot=[]
for r in range(5):
    X=rng.normal(0,1,(27,10)); X[15:,:4]+=4.0
    df=pd.DataFrame(X,columns=cols); tot.append(edges(df))
print("B step-regime on s0..s3 only (no causal links among them):", tot)
# C: same but n=300
X=rng.normal(0,1,(300,10)); X[150:,:4]+=4.0
print("C n=300 same:", edges(pd.DataFrame(X,columns=cols)))
