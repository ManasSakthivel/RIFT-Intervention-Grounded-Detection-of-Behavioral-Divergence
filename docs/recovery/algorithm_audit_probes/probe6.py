import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "."); sys.path.insert(0, "src")
import numpy as np, pandas as pd, networkx as nx
from src.rift.pipeline.e2e_runner import RIFTEndToEndRunner, MockTelemetry
from src.rift.cid.cid import _w1

# (1) baseline_metrics DataFrame passed as 'baselines' -> silently ignored
class T(MockTelemetry):
    def collect(self, services, window_s=300.0, **kw):
        out = super().collect(services, window_s=window_s, inject_anomaly="B", anomaly_magnitude=8.0); return out
g = nx.DiGraph([("A","B")])
r = RIFTEndToEndRunner(T(1), ["A","B"], g, dry_run=True)
t = [float(i*10) for i in range(30)]
bm = {s: pd.DataFrame({"time": t, "value": np.random.default_rng(0).normal(50, 5, 30)}) for s in ("A","B")}
m = r.telemetry_source.collect(["A","B"])
base_df = bm
# emulate L645-648
baselines = base_df or {}
sc = r._compute_anomaly_scores(m, baselines)
sc_default = r._compute_anomaly_scores(m, r._default_baselines(m))
print("PROBE15 scores with DataFrame baseline_metrics:", {k: round(v,2) for k,v in sc.items()},
      " scores with proper dict baselines:", {k: round(v,2) for k,v in sc_default.items()})

# (2) null W1 vs 0.1*IQR threshold
rng = np.random.default_rng(0); ratios=[]; exc=0; N=2000
for _ in range(N):
    a = rng.normal(0,1,30); b = rng.normal(0,1,30)
    w = _w1(a,b); iqr = np.percentile(a,75)-np.percentile(a,25)
    exc += w > 0.1*iqr
print("PROBE16 P(W1 > 0.1*IQR) under TRUE NULL n=30/30:", exc/N)
