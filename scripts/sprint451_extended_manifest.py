#!/usr/bin/env python3
"""Sprint 4.5.1 - EXTENDED freeze manifest (Decision 2).  Hashes only; read-only with respect to every listed file.

The original 4.5.0 manifest (51 files) is NOT modified and remains the baseline for "V3 unchanged" checks.
This manifest = those 51 files + the files in the static import closure of the confirmatory comparators
(artifacts/sprint4_5_1/freeze/closure_analysis.json, produced by scripts/sprint451_freeze_closure.py), grouped by ROLE:

  v3_frozen_implementation | v2_frozen_implementation | shared_method_dependencies | comparator_implementation_dependencies |
  evaluation_framework | dataset_generation_dependencies | evaluation_scripts | environment_and_lock | development_data | test_suite | protocol

It never opens datasets/rift_v2/heldout_candidate.json, heldout_status.json or artifacts/sprint4_3_0/results/held_out/.
For each file: sha256 (working tree), sha256 of the git index blob and of HEAD (None if absent).
Output: artifacts/sprint4_5_1/freeze/extended_manifest.json
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ORIG = REPO / "artifacts" / "sprint4_5_0" / "prereg" / "freeze_manifest.json"
CLOS = REPO / "artifacts" / "sprint4_5_1" / "freeze" / "closure_analysis.json"
OUT = REPO / "artifacts" / "sprint4_5_1" / "freeze" / "extended_manifest.json"
FORBIDDEN = ("heldout_candidate", "heldout_status", "results/held_out")

ROLE_BY_ORIGINAL_GROUP = {
    "v3_source": "v3_frozen_implementation",
    "evaluation_scripts": "evaluation_scripts",
    "v3_dependencies_evaluation": "evaluation_framework",
    "baselines": "comparator_implementation_dependencies",
    "dataset_generation_code": "dataset_generation_dependencies",
    "test_suite": "test_suite",
    "development_datasets_and_registry": "development_data",
    "dependency_lock": "environment_and_lock",
    "protocol": "protocol",
}
SHARED = ["src/rift/ebd/ebd.py", "src/rift/fci/fci_runner.py", "src/rift/cid/cid.py", "src/rift/cid/evidence.py",
          "src/rift/identifiability/identifiability.py", "src/rift/optimizer/cost_model.py",
          "src/rift/graph/anomaly_subgraph.py", "src/rift/graph/time_slice.py", "src/rift/statistics/stats.py",
          "src/rift/statistics/__init__.py", "src/rift/cid/__init__.py", "src/rift/fci/__init__.py",
          "src/rift/identifiability/__init__.py", "src/rift/__init__.py"]
ROLE_OVERRIDE = {p: "shared_method_dependencies" for p in SHARED}
ROLE_OVERRIDE.update({
    "src/rift/evaluation/rift_v2.py": "v2_frozen_implementation",
    "src/rift/evaluation/__init__.py": "evaluation_framework",
    "src/rift/evaluation/attribution_metrics.py": "evaluation_framework",
    "src/rift/evaluation/complete_evaluator.py": "evaluation_framework",
    "src/rift/evaluation/dataset_registry.py": "comparator_implementation_dependencies",
    "src/rift/benchmark/__init__.py": "comparator_implementation_dependencies",
    "src/rift/benchmark/adversarial_generator.py": "comparator_implementation_dependencies",
    "src/rift/benchmark/synthetic_benchmark.py": "comparator_implementation_dependencies",
    "scripts/run_adversarial_benchmark.py": "comparator_implementation_dependencies",
    "scripts/run_reproducible_evaluation.py": "comparator_implementation_dependencies",
})
RATIONALE = {
    "src/rift/evaluation/dataset_registry.py": "Legacy (Sprint 4.2.4) split registry imported at module load by scripts/run_reproducible_evaluation.py "
        "(RIFT-FULL-LEGACY and ORACLE rows). Not imported by V3, V2 or benchmark_v2 at import time (verified by import trace). Sealed loading requires "
        "purpose=final plus an active HeldOutGuard; verify_all_files hashes bytes only. Pinned to datasets/rift_faults/*, not datasets/rift_v2/*.",
    "src/rift/benchmark/adversarial_generator.py": "Imported by scripts/run_adversarial_benchmark.py (B0-EARLIEST/B0-HIGHEST and legacy adversarial helpers). "
        "Imports only json/numpy/pandas/dataclasses; performs no dataset IO. Not imported by V3 or V2.",
    "src/rift/benchmark/synthetic_benchmark.py": "Imported by run_reproducible_evaluation.py; split-name constants only at import time.",
}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git_bytes(spec: str):
    r = subprocess.run(["git", "show", spec], cwd=REPO, capture_output=True)
    return r.stdout if r.returncode == 0 else None


def main() -> int:
    orig = json.loads(ORIG.read_text())
    clos = json.loads(CLOS.read_text())
    paths = {rel: {"membership": "original_4_5_0_manifest", "original_group": m["group"]} for rel, m in orig["files"].items()}
    for r in clos["rows"]:
        paths.setdefault(r["path"], {"membership": "added_4_5_1_comparator_closure", "original_group": None})
    files, problems = {}, []
    for rel in sorted(paths):
        assert not any(f in rel for f in FORBIDDEN), rel
        raw = (REPO / rel).read_bytes()
        idx, head = git_bytes(f":{rel}"), git_bytes(f"HEAD:{rel}")
        role = ROLE_OVERRIDE.get(rel) or ROLE_BY_ORIGINAL_GROUP.get(paths[rel]["original_group"], "unclassified")
        e = {"role": role, "membership": paths[rel]["membership"], "original_group": paths[rel]["original_group"],
             "sha256": sha(raw), "git_index_sha256": sha(idx) if idx is not None else None,
             "git_head_sha256": sha(head) if head is not None else None}
        if rel in RATIONALE:
            e["rationale"] = RATIONALE[rel]
        if paths[rel]["membership"].startswith("original") and (head is None or sha(head) != e["sha256"]):
            problems.append(f"original file differs from HEAD: {rel}")
        if idx is None:
            problems.append(f"not tracked in index: {rel}")
        elif sha(idx) != e["sha256"]:
            problems.append(f"working tree differs from index: {rel}")
        if role == "unclassified":
            problems.append(f"unclassified: {rel}")
        files[rel] = e
    by_role = {}
    for rel, e in files.items():
        by_role.setdefault(e["role"], []).append(rel)
    lock = REPO / "reproducibility/requirements-canonical-py39.lock.txt"
    out = {"purpose": "Sprint 4.5.1 extended freeze manifest (hashes only)",
           "base_commit": orig["git"]["commit"],
           "original_manifest_sha256": sha(ORIG.read_bytes()),
           "closure_analysis_sha256": sha(CLOS.read_bytes()),
           "dependency_lock_sha256": sha(lock.read_bytes()),
           "python": orig["python"], "packages": orig["packages"],
           "n_files": len(files),
           "n_original": sum(1 for e in files.values() if e["membership"].startswith("original")),
           "n_added": sum(1 for e in files.values() if e["membership"].startswith("added")),
           "files_by_role_counts": {k: len(v) for k, v in sorted(by_role.items())},
           "problems": problems, "files": files}
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True))
    print("files", len(files), "original", out["n_original"], "added", out["n_added"])
    print("roles", out["files_by_role_counts"])
    print("problems", problems, "| manifest sha256", sha(OUT.read_bytes()))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
