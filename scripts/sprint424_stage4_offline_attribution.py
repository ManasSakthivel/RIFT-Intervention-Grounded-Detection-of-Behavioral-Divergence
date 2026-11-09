#!/usr/bin/env python3
"""
Sprint 4.2.4 / Issue 1 -- offline Stage 4 attribution from SAVED telemetry.

Reads ``artifacts/stage4_intervention_results.json`` (never modified), runs the real learned-graph
RIFT-FULL / EBD pipeline via ``src.rift.pipeline.stage4_attribution`` and writes the result to
``artifacts/sprint4_2_4/stage4_attribution_result.json``. No live system is contacted.

    python3 scripts/sprint424_stage4_offline_attribution.py [--input PATH] [--output PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import warnings
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
warnings.filterwarnings("ignore")

from src.rift.pipeline.stage4_attribution import analyze_saved_record  # noqa: E402

DEFAULT_INPUT = REPO_ROOT / "artifacts" / "stage4_intervention_results.json"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "sprint4_2_4" / "stage4_attribution_result.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    a = ap.parse_args()
    if a.output.resolve() == a.input.resolve():
        raise SystemExit("refusing to overwrite the historical input artifact")
    raw = a.input.read_bytes()
    saved = json.loads(raw)
    result = analyze_saved_record(saved)
    try:
        result["inputs"]["source_artifact"] = str(a.input.resolve().relative_to(REPO_ROOT))
    except ValueError:
        result["inputs"]["source_artifact"] = str(a.input)
    result["inputs"]["source_artifact_sha256"] = hashlib.sha256(raw).hexdigest()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, default=str) + "\n")
    print(json.dumps(result["summary"], indent=2))
    print("evaluation:", json.dumps(result["evaluation"]))
    print("abstention_reason:", result["prediction"]["abstention_reason"])
    print("wrote", a.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
