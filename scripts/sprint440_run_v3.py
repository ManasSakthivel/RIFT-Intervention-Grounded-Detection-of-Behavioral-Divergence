#!/usr/bin/env python3
"""Sprint 4.4.0 Phase 5-6 runner: V3 variants (and V2 reference) on DEV or VAL ONLY.

    python3 scripts/sprint440_run_v3.py dev
    python3 scripts/sprint440_run_v3.py val

Refuses any other split name. Writes artifacts/sprint4_4_0/v3_{split}.json (scenario-level records + scores).
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO), str(REPO / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.rift.attribution_v3 import pag_semantics as ps  # noqa: E402
from src.rift.attribution_v3.rift_v3 import V3_CONFIGS, run_v3  # noqa: E402
from src.rift.evaluation import benchmark_v2 as bm  # noqa: E402
from src.rift.evaluation.dataset_registry_v2 import load_v2  # noqa: E402
from src.rift.evaluation.rift_v2 import SharedCache  # noqa: E402
from src.rift.scenarios import simulator as sim  # noqa: E402

OUT = REPO / "artifacts" / "sprint4_4_0"


def run_scenario(sc, keys):
    o = sim.observe(sc)
    fid, seed = sc["scenario_id"], int(sc["seed"])
    iv = lambda x, ys, s: sim.intervene(sc, x, ys, s)  # noqa: E731
    cache = SharedCache()
    res = {}
    for k in keys:
        t0 = time.perf_counter()
        out = run_v3(o, iv, fid, seed, V3_CONFIGS[k], cache=cache)
        rec = bm._out_to_rec(out, time.perf_counter() - t0, 0.0)
        rec["status"] = out.raw_output.get("status")
        rec["caveats"] = out.raw_output.get("caveats", [])
        rec["possible_roots"] = out.raw_output.get("possible_roots", [])
        res[k] = {"record": rec, "score": bm.score_one(sc, rec)}
    return res


def main(argv) -> int:
    split = argv[1] if len(argv) > 1 else "dev"
    if split not in ("dev", "val"):
        raise SystemExit("this runner is restricted to dev/val")
    keys = list(V3_CONFIGS)
    rows = []
    for sc in load_v2(split).scenarios:
        rows.append({"scenario_id": sc["scenario_id"], "template_id": sc["template_id"],
                     "dimensions": sc["dimensions"], "methods": run_scenario(sc, keys)})
    (OUT / f"v3_{split}.json").write_text(json.dumps(rows, indent=1, default=float))
    for k in keys:
        S = [r["methods"][k]["score"] for r in rows]
        att = [s for s in S if s["expected"] == "ATTRIBUTE"]
        print(f"{split} {k:28s} P1 {sum(s['correct'] for s in att)}/{len(att)} P2 {sum(s['p2'] for s in S)} "
              f"unsafe {sum(s['unsafe'] for s in S)} cov {sum(s['answered'] for s in S)} wrong {sum(s['wrong_root'] for s in S)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
