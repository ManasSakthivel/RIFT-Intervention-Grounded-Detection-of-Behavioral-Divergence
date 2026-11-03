#!/usr/bin/env python3
"""Sprint 4.4.2: record the execution environment of a reproduction run.

    python3 scripts/sprint442_capture_environment.py [output.json]

Records interpreter, platform, exact versions of the numerically relevant packages, thread/hash-seed settings,
the fixed seeds used by the V3 pipeline, git commit, and whether the protected materials are present locally.
Reads no scenario content. Never opens the sealed held-out split (existence + size only).
"""
from __future__ import annotations

import importlib.metadata as md
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

PACKAGES = ["numpy", "scipy", "scikit-learn", "networkx", "pandas", "causal-learn", "statsmodels", "joblib",
            "momentchi2", "pytest"]

# Seeds are fixed in code, not drawn at run time. Listed here so a report can state them without re-deriving them.
SEEDS = {
    "fci": "np.random.seed(scenario['seed']) inside run_fci (src/rift/fci/fci_runner.py)",
    "simulator.observe": "np.random.default_rng(scenario['seed'])",
    "simulator.intervene": "np.random.default_rng(seed_do), seed_do=(scenario_seed*7919+crc32(node)) & 0x7FFFFFFF",
    "cid": "seed=(scenario_seed*1000003+crc32('x->y')) & 0x7FFFFFFF",
    "adversarial_generator": "sha256('rift-v3-adversarial|<tag>|<k>')[:8] & 0x7FFFFFFF",
    "sprint440_analyze / sprint440_cid_audit Monte Carlo": 440,
    "sprint430 statistics": {"stat_seed": 430, "bootstrap_B": 2000, "permutations": 10000},
}

PROTECTED = [
    "datasets/rift_v2/heldout_candidate.json",
    "datasets/rift_v2/heldout_status.json",
    "artifacts/sprint4_3_0/heldout_opened.json",
    "artifacts/sprint4_3_0/results/held_out",
    "artifacts/stage4_intervention_results.json",
]


def _version(pkg: str) -> str:
    try:
        return md.version(pkg)
    except md.PackageNotFoundError:
        return "NOT INSTALLED"


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=REPO, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:  # noqa: BLE001
        return "unavailable"


def capture() -> dict:
    prot = {}
    for rel in PROTECTED:
        p = REPO / rel
        prot[rel] = {"present": p.exists()}  # existence only: contents are never read here
    return {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "packages": {p: _version(p) for p in PACKAGES},
        "env": {k: os.environ.get(k) for k in ("PYTHONHASHSEED", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                                                "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")},
        "seeds": SEEDS,
        "git": {"commit": _git("rev-parse", "HEAD"), "branch": _git("rev-parse", "--abbrev-ref", "HEAD")},
        "protected_materials_present": prot,
    }


def main(argv) -> int:
    info = capture()
    text = json.dumps(info, indent=1, sort_keys=True)
    if len(argv) > 1:
        Path(argv[1]).write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
