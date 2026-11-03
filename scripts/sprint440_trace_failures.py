#!/usr/bin/env python3
"""Sprint 4.4.0 Phase 0-2: trace every dev/val scenario through unchanged RIFT-FULL-V2 and write diagnostics.

    python3 scripts/sprint440_trace_failures.py

DEV/VAL ONLY. Never touches the held-out split. Writes artifacts/sprint4_4_0/{failure_traces_*.json,graph_quality_*.json}
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO), str(REPO / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.rift.attribution_v3.diagnostics import trace_scenario  # noqa: E402
from src.rift.evaluation.dataset_registry_v2 import PINS, load_v2, verify_freeze  # noqa: E402

OUT = REPO / "artifacts" / "sprint4_4_0"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ok, why = verify_freeze()
    meta = {"verify_freeze": [ok, why], "pins": {k: v["sha256"] for k, v in PINS.items()}}
    for split in ("dev", "val"):
        ls = load_v2(split)
        rows = [trace_scenario(sc) for sc in ls.scenarios]
        (OUT / f"failure_traces_{split}.json").write_text(json.dumps(rows, indent=1, default=float))
        meta[split] = {"n": len(rows), "sha256": ls.sha256}
        print(split, len(rows))
    (OUT / "trace_meta.json").write_text(json.dumps(meta, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
