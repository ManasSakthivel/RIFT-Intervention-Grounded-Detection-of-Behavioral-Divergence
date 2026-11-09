import sys, json, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "."); sys.path.insert(0, "src")
import numpy as np, pandas as pd
from src.rift.cid.cid import compute_cid
from src.rift.pipeline.stage4_attribution import analyze_saved_record, build_evidence
saved=json.load(open("artifacts/stage4_intervention_results.json"))
p=analyze_saved_record(saved)["prediction"]
print("S4 ebd_candidate",p["ebd_candidate"],p["ebd_candidate_confidence"],"abstain",p["abstention_reason"])
print("S4 ident", p["identifiability"]["query"], p["identifiability"]["status"], p["identifiability"]["all_pairs"])
print("S4 edges", [e for e in p["pag_edges"]][:12])
# x-independence of CID in e2e: same (base, post) -> same CID irrespective of x
rng=np.random.default_rng(0); b=rng.normal(0,1,60); q=rng.normal(3,1,60)
a=compute_cid(b,q,"X1","Y",0.0,n_bootstrap=50,n_permutations=200); c=compute_cid(b,q,"X2","Y",0.0,n_bootstrap=50,n_permutations=200)
print("CID x-specific?", a.w1_estimate==c.w1_estimate, a.permutation_pvalue==c.permutation_pvalue)
# grade for e2e defaults
for n in (4,6,30):
    print("n=",n, compute_cid(rng.normal(0,1,100),rng.normal(0,1,n),"X","Y",0.0,n_bootstrap=10,n_permutations=10).grade.value)
# permutation floor with e2e n_permutations=1000: min p
print("min p with B=1000:", 1/1001, " B=200 bootstrap")
# autocorrelated null: AR(1) phi=0.8, n=30 vs 30 (no effect, no drift): permutation test false-positive rate
fp=0;N=400
for i in range(N):
    e=rng.normal(0,1,60); x=np.zeros(60)
    for t in range(1,60): x[t]=0.8*x[t-1]+e[t]
    r=compute_cid(x[:30],x[30:],"X","Y",0.0,n_bootstrap=5,n_permutations=200,seed=i)
    fp+= bool(r.permutation_significant and r.exceeds_threshold)
print("AR(1,0.8) null FP rate (adjacent windows):", fp/N)
