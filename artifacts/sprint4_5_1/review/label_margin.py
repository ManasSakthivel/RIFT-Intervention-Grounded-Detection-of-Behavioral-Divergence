#!/usr/bin/env python3
"""Agent 7: label-boundary sensitivity on dev/val only (saved V3 records + frozen simulator functions; no method run)."""
import json, sys
from pathlib import Path
import numpy as np
REPO = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(REPO))
from src.rift.scenarios import simulator as sim
rows = []
for split in ("dev", "val"):
    runs = {r["scenario_id"]: r for r in json.loads((REPO / f"artifacts/sprint4_4_0/v3_{split}.json").read_text())}
    ds = json.loads((REPO / f"datasets/rift_v2/{split}.json").read_text()); ds = ds if isinstance(ds, list) else ds["scenarios"]
    for sc in ds:
        gt = sc["ground_truth"]; m = runs[sc["scenario_id"]]["methods"]["V3-FULL"]; s = m["score"]
        if not gt["roots"] or gt.get("abstain_reason") in ("NO_FAULT", "ROOT_UNOBSERVED", "SYMMETRIC_MUTUAL_DEPENDENCY", "INSUFFICIENT_BASELINE"):
            continue
        snr = max(float(np.max(np.abs(sim.apparent_signal(sc, r)))) for r in gt["roots"])
        c, u = int(s["correct"]), int(s["unsafe"])
        rows.append(dict(exp=gt["expected_outcome"], reason=gt.get("abstain_reason"), snr=snr, ans=int(s["answered"]), c=c, u=u,
                         U=c - 2 * u - m["record"]["n_do"] / 20, lucky=int(s["answered"] and gt["expected_outcome"] != "ATTRIBUTE" and s["top1"] in gt["roots"])))
out = {"n": len(rows)}
bins = [(0, 3), (3, 4), (4, 5), (5, 6), (6, 8), (8, 1e9)]
out["by_root_snr_bin"] = {}
for lo, hi in bins:
    sub = [r for r in rows if lo <= r["snr"] < hi]
    if sub:
        out["by_root_snr_bin"][f"[{lo},{hi})"] = {"n": len(sub), "frac_ATTRIBUTE_label": float(np.mean([r["exp"] == "ATTRIBUTE" for r in sub])),
            "v3_answer_rate": float(np.mean([r["ans"] for r in sub])), "v3_meanU": float(np.mean([r["U"] for r in sub])),
            "lucky_correct_rate": float(np.mean([r["lucky"] for r in sub])), "unsafe_rate": float(np.mean([r["u"] for r in sub]))}
weak = [r for r in rows if r["reason"] == "WEAK_SIGNAL"]
out["WEAK_SIGNAL"] = {"n": len(weak), "snr_ge_3": int(sum(r["snr"] >= 3 for r in weak)), "snr_ge_3.5": int(sum(r["snr"] >= 3.5 for r in weak)),
                      "answered": int(sum(r["ans"] for r in weak)), "lucky": int(sum(r["lucky"] for r in weak)),
                      "lucky_with_snr_ge_3": int(sum(r["lucky"] for r in weak if r["snr"] >= 3))}
# counterfactual: relabel scenarios with 3<=snr<4 as ATTRIBUTE ('EBD detection threshold = 3') -> NOT a recommendation, a sensitivity illustration
Path(__file__).with_name("label_margin.json").write_text(json.dumps(out, indent=1, default=float))
print(json.dumps(out, indent=1, default=float))
