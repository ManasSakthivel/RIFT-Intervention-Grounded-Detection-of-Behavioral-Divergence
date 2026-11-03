#!/usr/bin/env python3
"""Agent 7: does metric-dict / node ORDER (root is always first in the frozen generator) help order-dependent comparators?
Runs ONLY the cheap B0-EARLIEST baseline (scripts/run_adversarial_benchmark.py) on dev/val with original vs shuffled
metric order. No V3, no V2, no held-out. Seed 4512."""
import json, sys, warnings
from pathlib import Path
import numpy as np
warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO), str(REPO / "src")]
from src.rift.evaluation import benchmark_v2 as bm
from src.rift.scenarios import simulator as sim
L = bm._legacy()
rng = np.random.default_rng(4512)
out = {}
for split in ("dev", "val"):
    ds = json.loads((REPO / f"datasets/rift_v2/{split}.json").read_text())
    ds = ds if isinstance(ds, list) else ds.get("scenarios", ds)
    corr_o = corr_s = n_att = unsafe_o = unsafe_s = 0
    for sc in ds:
        o = sim.observe(sc)
        gt = sc["ground_truth"]
        def run(o_):
            ctx = bm.make_context(sc, o_)
            res = L["B0E"]().run(ctx)
            rec = bm._out_to_rec(res, 0.0, 0.0)
            return bm.score_one(sc, rec)
        s0 = run(o)
        keys = list(o["metrics"]); rng.shuffle(keys)
        o2 = dict(o); o2["metrics"] = {k: o["metrics"][k] for k in keys}
        s1 = run(o2)
        if s0["expected"] == "ATTRIBUTE": n_att += 1
        corr_o += s0["correct"]; corr_s += s1["correct"]; unsafe_o += s0["unsafe"]; unsafe_s += s1["unsafe"]
    out[split] = {"n_attribute": n_att, "B0E_correct_original_order": int(corr_o), "B0E_correct_shuffled_order": int(corr_s),
                  "B0E_unsafe_original": int(unsafe_o), "B0E_unsafe_shuffled": int(unsafe_s)}
Path(__file__).with_name("node_order_leak.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
