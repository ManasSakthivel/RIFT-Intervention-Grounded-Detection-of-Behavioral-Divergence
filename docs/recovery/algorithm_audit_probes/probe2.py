import sys, json, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "."); sys.path.insert(0, "src")
import numpy as np, pandas as pd, networkx as nx
from src.rift.pipeline.e2e_runner import RIFTEndToEndRunner

# Probe 8: dry_run + "live" telemetry + ongoing fault, NO intervention ever executed
class LiveFake:
    is_live = True
    endpoint = "http://fake"
    def __init__(s): s.calls = 0; s.rng = np.random.default_rng(3)
    def collect(s, services, window_s=300.0):
        s.calls += 1
        n = int(window_s // 10); out = {}
        for svc in services:
            t = [float(i*10) for i in range(n)]
            v = s.rng.normal(50, 5, n)
            if s.calls == 1:              # observation: fault starts in 2nd half; A first, B one window later
                half = n // 2
                if svc == "A": v[half:] += 60
                if svc == "B": v[half+1:] += 60
            else:                         # "post-intervention": fault still ongoing, nothing was injected
                if svc in ("A", "B"): v += 60
            out[svc] = pd.DataFrame({"time": t, "value": v})
        return out
g = nx.DiGraph([("A", "B"), ("A", "C"), ("C", "D")])
r = RIFTEndToEndRunner(LiveFake(), ["A", "B", "C", "D"], g, dry_run=True,
                       observe_window_s=600.0, post_window_s=300.0).run()
print("PROBE8", r.final_state, r.attribution, r.attribution_confidence,
      "valid_for_gate=", r.is_valid_for_gate, "dry_run=", r.intervention_records[0]["dry_run"] if r.intervention_records else None)
for e in r.ebd_results[:3]:
    print("   ", e["service_id"], e["confidence"], "r4=", e["r4_pass"], e["evidence_type"], e["causal_path_kind"])

# Probe 9: stage4 artifact end-to-end
from src.rift.pipeline.stage4_attribution import analyze_saved_record
saved = json.load(open("artifacts/stage4_intervention_results.json"))
res = analyze_saved_record(saved)
p = res["prediction"]
print("PROBE9", p["predicted_root"], p["abstained"], p["abstention_reason"], p["confidence_label"], p["ebd_candidate_confidence"],
      "tied=", p["ebd_tied_at_t_star"], "cid_grade=", p["cid_grade"], "ident=", p["identifiability"].get("status"))
print("   diverging:", p["diverging_services"], "n_edges:", len(p["pag_edges"]))
# remove ground truth/target leakage: change target_service to a different service and re-run
for tgt in ("rift-frontend", "rift-adservice"):
    s2 = dict(saved); s2["target_service"] = tgt
    q = analyze_saved_record(s2)["prediction"]
    print("PROBE9 target=", tgt, "->", q["predicted_root"], q["abstained"], q["abstention_reason"], q["ebd_candidate_confidence"], q["evidence_type"])
