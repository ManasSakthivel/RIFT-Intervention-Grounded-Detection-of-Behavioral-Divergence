#!/usr/bin/env python3
"""Sprint 4.5.0 - write the V3 freeze manifest (hashes only; read-only with respect to every frozen file).

Hashes the files listed in FROZEN_FILES, records git commit/branch, Python + package versions, the lock-file hash,
constants and seed-derivation rules.  It NEVER opens datasets/rift_v2/heldout_candidate.json; the held-out sha256 is
copied as a string from datasets/rift_v2/independence_report.json.

Output: artifacts/sprint4_5_0/prereg/freeze_manifest.json   (does not modify any frozen file)
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "artifacts" / "sprint4_5_0" / "prereg" / "freeze_manifest.json"

GROUPS = {
    "v3_source": [
        "src/rift/attribution_v3/__init__.py", "src/rift/attribution_v3/rift_v3.py",
        "src/rift/attribution_v3/pag_semantics.py", "src/rift/attribution_v3/diagnostics.py",
        "src/rift/attribution_v3/adversarial.py"],
    "evaluation_scripts": [
        "scripts/sprint440_run_v3.py", "scripts/sprint440_analyze.py", "scripts/sprint440_cid_audit.py",
        "scripts/sprint440_adversarial.py", "scripts/sprint440_trace_failures.py",
        "scripts/sprint430_run_evaluation.py"],
    "v3_dependencies_evaluation": [
        "src/rift/evaluation/rift_v2.py", "src/rift/evaluation/benchmark_v2.py", "src/rift/evaluation/stats_v2.py",
        "src/rift/evaluation/dataset_registry_v2.py", "src/rift/evaluation/held_out_guard.py",
        "src/rift/ebd/ebd.py", "src/rift/fci/fci_runner.py", "src/rift/cid/cid.py", "src/rift/cid/evidence.py",
        "src/rift/identifiability/identifiability.py"],
    "baselines": [
        "src/rift/baselines/__init__.py", "src/rift/baselines/latency_correlation.py", "src/rift/baselines/oracle.py",
        "src/rift/baselines/rift_obs.py", "src/rift/baselines/rift_one_shot.py", "src/rift/baselines/rift_random.py",
        "src/rift/baselines/sieve_like.py", "src/rift/baselines/sage_chaos.py"],
    "dataset_generation_code": [
        "src/rift/scenarios/__init__.py", "src/rift/scenarios/simulator.py", "src/rift/scenarios/generator_v2.py",
        "src/rift/scenarios/fingerprint.py", "src/rift/scenarios/independence.py", "src/rift/scenarios/duplicates.py",
        "src/rift/scenarios/splitter.py", "src/rift/scenarios/validators.py"],
    "test_suite": ["tests/unit/test_sprint440_attribution_v3.py", "scripts/sprint442_run_tests.py",
                   "scripts/sprint442_compare_artifacts.py", "scripts/sprint442_capture_environment.py",
                   "reproducibility/protected_materials.py"],
    "development_datasets_and_registry": [
        "datasets/rift_v2/dev.json", "datasets/rift_v2/val.json", "datasets/rift_v2/manifest.json",
        "datasets/rift_v2/independence_report.json", "datasets/rift_v3_dev/adversarial_dev.json",
        "datasets/rift_v3_dev/provenance.json", "artifacts/sprint4_3_0/freeze.json"],
    "dependency_lock": ["reproducibility/requirements-canonical-py39.lock.txt"],
    "protocol": ["docs/EVALUATION_PROTOCOL_V2.md"],
}
PACKAGES = ["numpy", "scipy", "scikit-learn", "networkx", "pandas", "causal-learn", "statsmodels", "joblib",
            "pytest", "requests", "momentchi2"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def main() -> int:
    forbidden = "heldout_candidate"
    files, mismatches = {}, []
    for grp, lst in GROUPS.items():
        for rel in lst:
            assert forbidden not in rel
            p = REPO / rel
            h = sha(p)
            tracked = git("ls-files", "--error-unmatch", rel)
            head_blob = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=REPO, capture_output=True).stdout
            head_h = hashlib.sha256(head_blob).hexdigest()
            if head_h != h:
                mismatches.append(rel)
            files[rel] = {"group": grp, "sha256": h, "git_head_blob_sha256": head_h, "tracked": bool(tracked)}
    ho = json.loads((REPO / 'datasets/rift_v2/independence_report.json').read_text())['heldout_sha256']
    lock = REPO / "reproducibility/requirements-canonical-py39.lock.txt"
    out = {
        "purpose": "Sprint 4.5.0 V3 freeze manifest (hashes only)",
        "git": {"branch": git("rev-parse", "--abbrev-ref", "HEAD"), "commit": git("rev-parse", "HEAD")},
        "working_tree_matches_HEAD_for_all_listed_files": not mismatches, "mismatching_files": mismatches,
        "python": platform.python_version(),
        "packages": {p: metadata.version(p) for p in PACKAGES},
        "dependency_lock": {"path": "reproducibility/requirements-canonical-py39.lock.txt", "sha256": sha(lock),
                            "lines": len(lock.read_text().splitlines())},
        "heldout_sha256_string_copied_from_independence_report_NOT_RECOMPUTED": ho,
        "constants": {"DELTA_T": 10, "ED_PER_DO_S": 30, "MAX_DO": 20, "CID_PERMUTATIONS": 1000, "CID_BOOTSTRAP": 100,
                      "ALPHA": 0.05, "theta_detect": 3.0, "persist": 2, "fci_max_variables": 15,
                      "cid_theta_rule": "0.1 x IQR_baseline", "cid_grade_rule": "CANDIDATE if n<50; RELIABLE needs n>=50"},
        "V3_FULL_config": {"name": "RIFT-FULL-V3", "manipulation_check": True, "earlier_guard": True,
                           "answer_statuses": ["DEFINITIVE_ROOT", "QUALIFIED_ROOT"], "divergent_candidates": True,
                           "test_explained": True},
        "seed_rules": {"do_seed": "(seed*7919 + crc32(x+'|v3')) & 0x7FFFFFFF",
                       "cid_seed": "(seed*1000003 + crc32('x->y')) & 0x7FFFFFFF",
                       "generator_seed": "int(sha256(f'{GENERATOR_VERSION}|{split}|{idx}')[:8],16) & 0x7FFFFFFF",
                       "GENERATOR_VERSION": "rift-scenario-gen/2.0.0", "stats_seed": 430,
                       "stats_B": 2000, "stats_permutations": 10000, "audit_seeds": [450, 4502]},
        "test_suite": {"clean_export_reproducible_passes": 663, "clean_export_protected_unavailable": 2,
                       "clean_export_failures": 0, "full_tree_report_4_4_2": "886 reproducible + 2 protected = 888",
                       "note": "protected-material checks need the owner's tree and --require-protected"},
        "files": files,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True))
    print("files", len(files), "mismatches", mismatches, "manifest sha256", sha(OUT))
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
