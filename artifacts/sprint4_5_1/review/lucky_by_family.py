#!/usr/bin/env python3
"""Agent 7: are V3 'lucky-correct' answers (named a true root on ABSTAIN_REQUIRED) concentrated in families whose fault has var_mult>1
(variance inflation, which the label's mean-shift-only SNR ignores)? dev/val saved records + scenario specs only."""
import json
from collections import Counter, defaultdict
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
tot = Counter(); lucky = Counter(); ans = Counter(); n_vm = Counter()
for split in ("dev", "val"):
    runs = {r["scenario_id"]: r for r in json.loads((REPO / f"artifacts/sprint4_4_0/v3_{split}.json").read_text())}
    ds = json.loads((REPO / f"datasets/rift_v2/{split}.json").read_text()); ds = ds if isinstance(ds, list) else ds["scenarios"]
    for sc in ds:
        gt = sc["ground_truth"]
        if gt["expected_outcome"] != "ABSTAIN_REQUIRED" or gt.get("abstain_reason") not in ("WEAK_SIGNAL", "NO_DISCRIMINATING_EVIDENCE"):
            continue
        s = runs[sc["scenario_id"]]["methods"]["V3-FULL"]["score"]
        vm = max([f.get("var_mult", 1.0) for f in sc["faults"]] or [1.0]) > 1.0
        k = "var_mult>1" if vm else "var_mult=1"
        tot[k] += 1; ans[k] += int(s["answered"]); lucky[k] += int(s["answered"] and s["top1"] in set(gt["roots"]))
out = {k: {"n": tot[k], "answered": ans[k], "lucky_correct": lucky[k]} for k in tot}
Path(__file__).with_name("lucky_by_family.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
