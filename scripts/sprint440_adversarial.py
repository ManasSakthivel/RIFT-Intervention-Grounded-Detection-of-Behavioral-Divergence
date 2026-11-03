#!/usr/bin/env python3
"""Sprint 4.4.0 Phase 7: generate the adversarial dev-side set and compare V2 vs V3 (and always-abstain) on it.

    python3 scripts/sprint440_adversarial.py
"""
from __future__ import annotations

import json
import sys
import warnings
from collections import Counter, defaultdict
from pathlib import Path

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO), str(REPO / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.rift.attribution_v3 import adversarial as adv  # noqa: E402
from src.rift.attribution_v3.rift_v3 import V3_CONFIGS, run_v3  # noqa: E402
from src.rift.evaluation import benchmark_v2 as bm  # noqa: E402
from src.rift.evaluation import rift_v2 as r2  # noqa: E402
from src.rift.scenarios import simulator as sim  # noqa: E402

OUT = REPO / "artifacts" / "sprint4_4_0"


def run(sc):
    o = sim.observe(sc)
    fid, seed = sc["scenario_id"], int(sc["seed"])
    iv = lambda x, ys, s: sim.intervene(sc, x, ys, s)  # noqa: E731
    cache = r2.SharedCache()
    res = {}
    out = r2.run_v2(o, iv, fid, seed, r2.CONFIGS["A1-FULL"], cache=cache)
    rec = bm._out_to_rec(out, 0, 0); rec["status"] = None
    res["RIFT-FULL-V2"] = {"record": rec, "score": bm.score_one(sc, rec)}
    for k in ("V3-FULL", "V3-DEFINITIVE-ONLY", "V3-NO-SYMMETRY-CHECK"):
        out = run_v3(o, iv, fid, seed, V3_CONFIGS[k], cache=r2.SharedCache())
        rec = bm._out_to_rec(out, 0, 0); rec["status"] = out.raw_output.get("status"); rec["caveats"] = out.raw_output.get("caveats", [])
        res[k] = {"record": rec, "score": bm.score_one(sc, rec)}
    return res


def main() -> int:
    prov = adv.write()
    scs = adv.load()
    rows = [{"scenario_id": s["scenario_id"], "type": s["adversarial"]["type"], "expected": s["ground_truth"]["expected_outcome"],
             "abstain_reason": s["ground_truth"]["abstain_reason"], "methods": run(s)} for s in scs]
    (OUT / "adversarial_results.json").write_text(json.dumps(rows, indent=1, default=float))
    summ = {}
    for t in adv.ATTACKS:
        rs = [r for r in rows if r["type"] == t]
        d = {"n": len(rs), "expected": dict(Counter(r["expected"] for r in rs))}
        for m in ("RIFT-FULL-V2", "V3-FULL", "V3-DEFINITIVE-ONLY", "V3-NO-SYMMETRY-CHECK"):
            S = [r["methods"][m]["score"] for r in rs]
            d[m] = {"correct": sum(s["correct"] for s in S), "answered": sum(s["answered"] for s in S),
                    "unsafe": sum(s["unsafe"] for s in S), "wrong_root": sum(s["wrong_root"] for s in S)}
        d["always_abstain_unsafe"] = 0
        summ[t] = d
    tot = {m: {k: sum(summ[t][m][k] for t in summ) for k in ("correct", "answered", "unsafe", "wrong_root")}
           for m in ("RIFT-FULL-V2", "V3-FULL", "V3-DEFINITIVE-ONLY", "V3-NO-SYMMETRY-CHECK")}
    tot["n"] = len(rows)
    tot["n_attribute"] = sum(1 for r in rows if r["expected"] == "ATTRIBUTE")
    (OUT / "adversarial_summary.json").write_text(json.dumps({"provenance": prov, "per_type": summ, "total": tot}, indent=1))
    print(json.dumps(prov))
    for t, d in summ.items():
        print(f"{t:34s} exp={d['expected']} V2 c/a/u={d['RIFT-FULL-V2']['correct']}/{d['RIFT-FULL-V2']['answered']}/{d['RIFT-FULL-V2']['unsafe']} "
              f"V3 c/a/u={d['V3-FULL']['correct']}/{d['V3-FULL']['answered']}/{d['V3-FULL']['unsafe']} "
              f"V3def c/a/u={d['V3-DEFINITIVE-ONLY']['correct']}/{d['V3-DEFINITIVE-ONLY']['answered']}/{d['V3-DEFINITIVE-ONLY']['unsafe']}")
    print(tot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
