#!/usr/bin/env python3
"""Freeze the Sprint 4.3.0 evaluation (Protocol v2 §13-14).

Preconditions (all checked, fail-closed): independence report ok and bound to the current held-out hash; dev/val pinned
hashes match; the held-out has never been opened. On success writes artifacts/sprint4_3_0/freeze.json (SHA-256 of
protocol, every method / scenario / evaluation source file and dataset) and flips heldout_status.json to FINAL_FROZEN.
Any later edit of a frozen file makes dataset_registry_v2.load_v2('held_out') refuse.

    python3 scripts/sprint430_freeze.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.rift.evaluation import dataset_registry_v2 as reg  # noqa: E402

FROZEN_FILES = [
    "docs/EVALUATION_PROTOCOL_V2.md",
    "artifacts/sprint4_3_0/protocol_v2.sha256", "artifacts/sprint4_3_0/protocol_v2_amendments.sha256",
    "datasets/rift_v2/dev.json", "datasets/rift_v2/val.json", "datasets/rift_v2/" + reg.HELD_FILE,
    "datasets/rift_v2/independence_report.json", "datasets/rift_v2/manifest.json",
    "src/rift/evaluation/rift_v2.py", "src/rift/evaluation/benchmark_v2.py", "src/rift/evaluation/stats_v2.py",
    "src/rift/evaluation/dataset_registry_v2.py", "src/rift/evaluation/held_out_guard.py",
    "scripts/sprint430_run_evaluation.py", "scripts/run_reproducible_evaluation.py",
    "scripts/run_adversarial_benchmark.py",
    "src/rift/ebd/ebd.py", "src/rift/cid/cid.py", "src/rift/cid/evidence.py", "src/rift/fci/fci_runner.py",
    "src/rift/identifiability/identifiability.py", "src/rift/optimizer/cost_model.py",
    "src/rift/baselines/__init__.py", "src/rift/baselines/latency_correlation.py", "src/rift/baselines/oracle.py",
    "src/rift/baselines/rift_obs.py", "src/rift/baselines/rift_one_shot.py", "src/rift/baselines/rift_random.py",
    "src/rift/baselines/sieve_like.py",
    "src/rift/scenarios/__init__.py", "src/rift/scenarios/simulator.py", "src/rift/scenarios/generator_v2.py",
    "src/rift/scenarios/validators.py", "src/rift/scenarios/independence.py", "src/rift/scenarios/splitter.py",
    "src/rift/scenarios/fingerprint.py", "src/rift/scenarios/duplicates.py",
]


def main() -> int:
    ind_p = reg.INDEP_FILE
    ind = json.loads(ind_p.read_text()) if ind_p.is_file() else {}
    held = reg.V2_DIR / reg.HELD_FILE
    hd = reg.sha256_file(held)
    if not ind.get("ok") or ind.get("heldout_sha256") != hd:
        print("REFUSED: independence report missing/failed or not bound to the current held-out hash "
              "(run scripts/sprint430_verify_independence.py)")
        return 2
    for sp in reg.PINS:
        reg._load_pinned(sp, reg.V2_DIR)  # raises on mismatch
    if reg.OPENED_FILE.is_file():
        print("REFUSED: held-out already opened; a freeze after opening is meaningless")
        return 3
    status = {"heldout_status": "FINAL_FROZEN", "file": reg.HELD_FILE, "sha256": hd,
              "reason": "independence verified; freeze performed before any held-out method run"}
    reg.STATUS_FILE.write_text(json.dumps(status, indent=1, sort_keys=True) + "\n")
    files = {}
    for rel in FROZEN_FILES:
        p = reg.REPO_ROOT / rel
        if not p.is_file():
            print("REFUSED: missing frozen file", rel)
            return 4
        files[rel] = reg.sha256_file(p)
    fz = {"frozen_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "files": files,
          "heldout_sha256": hd, "note": "any change to a listed file invalidates the held-out run"}
    reg.FREEZE_FILE.write_text(json.dumps(fz, indent=1, sort_keys=True) + "\n")
    print(f"FROZEN: {len(files)} files; held-out sha256 {hd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
