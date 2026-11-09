#!/usr/bin/env python3
"""Final execution (Agent 5): regenerate the Sprint 4.4.0 V3 dev/val records in the CURRENT interpreter and compare them
with the committed `artifacts/sprint4_4_0/v3_{dev,val}.json`.

    python3 scripts/final_repro_check.py <scratch_out_dir> [--report report.json]

* Dev and val only (the sealed held-out split is never loaded; `load_v2` is called with 'dev' / 'val').
* Writes ONLY into <scratch_out_dir>, which must not be inside `artifacts/`. Committed artifacts are never overwritten.
* Comparison reuses `scripts/sprint442_compare_artifacts.compare_file` (structural; only `runtime_s`/`mem_kb` ignored).
* Additionally reports `ident_status` / `abstained` / top-candidate / score agreement separately, so that a
  label-only drift (the causal-learn 0.1.3.8 failure mode seen in Sprint 4.4.2) is visible by name.
* Exit 0 iff both files are structurally identical to the committed ones.
"""
from __future__ import annotations

import importlib.metadata as md
import json
import platform
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO), str(REPO / "src"), str(REPO / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import sprint442_compare_artifacts as cmp  # noqa: E402
from src.rift.attribution_v3.rift_v3 import V3_CONFIGS  # noqa: E402
from src.rift.evaluation.dataset_registry_v2 import load_v2  # noqa: E402
import sprint440_run_v3 as run_v3_mod  # noqa: E402

COMMITTED = REPO / "artifacts" / "sprint4_4_0"
PKGS = ["numpy", "scipy", "scikit-learn", "networkx", "pandas", "causal-learn", "momentchi2", "joblib", "statsmodels"]


def regenerate(split: str, out_dir: Path) -> Path:
    keys = list(V3_CONFIGS)
    rows = []
    for sc in load_v2(split).scenarios:
        rows.append({"scenario_id": sc["scenario_id"], "template_id": sc["template_id"],
                     "dimensions": sc["dimensions"], "methods": run_v3_mod.run_scenario(sc, keys)})
    p = out_dir / f"v3_{split}.json"
    p.write_text(json.dumps(rows, indent=1, default=float))
    return p


def field_drift(split: str, out_dir: Path) -> dict:
    a = json.loads((COMMITTED / f"v3_{split}.json").read_text())
    b = json.loads((out_dir / f"v3_{split}.json").read_text())
    drift = {"ident_status": [], "abstained": [], "top": [], "score": []}
    for ra, rb in zip(a, b):
        assert ra["scenario_id"] == rb["scenario_id"]
        for k, ma in ra["methods"].items():
            mb = rb["methods"][k]
            for f in ("ident_status", "abstained"):
                if ma["record"].get(f) != mb["record"].get(f):
                    drift[f].append(f"{ra['scenario_id']}:{k}")
            if ma["record"].get("top") != mb["record"].get("top"):
                drift["top"].append(f"{ra['scenario_id']}:{k}")
            if ma["score"] != mb["score"]:
                drift["score"].append(f"{ra['scenario_id']}:{k}")
    return {k: v for k, v in drift.items()}


def main(argv) -> int:
    args = list(argv[1:])
    report = None
    if "--report" in args:
        i = args.index("--report")
        report = args[i + 1]
        del args[i:i + 2]
    if not args:
        print(__doc__)
        return 2
    out = Path(args[0]).resolve()
    if (REPO / "artifacts") in out.parents or out == REPO / "artifacts":
        raise SystemExit("refusing to write inside artifacts/ (historical evidence must not be overwritten)")
    out.mkdir(parents=True, exist_ok=True)
    env = {"python": platform.python_version(), "platform": platform.platform()}
    for p in PKGS:
        try:
            env[p] = md.version(p)
        except md.PackageNotFoundError:
            env[p] = "NOT INSTALLED"
    result = {"environment": env, "files": {}, "field_drift": {}}
    ok = True
    for split in ("dev", "val"):
        regenerate(split, out)
        r = cmp.compare_file(f"v3_{split}.json", COMMITTED, out)
        result["files"][r["file"]] = {"status": r["status"], "n_differences": len(r["differences"]),
                                      "first_differences": r["differences"][:5]}
        result["field_drift"][split] = {k: len(v) for k, v in field_drift(split, out).items()}
        ok &= r["status"] == "IDENTICAL"
    result["verdict"] = "REPRODUCES_COMMITTED_RECORDS" if ok else "DIFFERS_FROM_COMMITTED_RECORDS"
    print(json.dumps(result, indent=1))
    if report:
        Path(report).write_text(json.dumps(result, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
