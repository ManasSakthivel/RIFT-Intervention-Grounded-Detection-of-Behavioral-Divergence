#!/usr/bin/env python3
"""Agent 2 — dataset independence report (read-only except for its own output file).

Hashes ONLY readable files. Sealed-file hashes are COPIED from existing committed manifests; no sealed file is
opened, hashed or parsed. Output: artifacts/final_closure/dataset_independence_report.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from src.rift.scenarios import duplicates as dup  # noqa: E402
from src.rift.scenarios import fingerprint as fp  # noqa: E402
from src.rift.scenarios import leakage_checks as LC  # noqa: E402
from src.rift.scenarios.independence import strip_labels  # noqa: E402

OUT = ROOT / "artifacts" / "final_closure" / "dataset_independence_report.json"
READABLE = ["datasets/rift_faults/development.json", "datasets/rift_faults/validation.json",
            "datasets/rift_faults/adversarial_stress_cohort.json", "datasets/rift_v2/dev.json",
            "datasets/rift_v2/val.json", "datasets/rift_v3_dev/adversarial_dev.json"]


def sha(p: str) -> str:
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def main() -> int:
    v2 = {"dev": [strip_labels(s) for s in LC.load_scenarios(ROOT / "datasets/rift_v2/dev.json")],
          "val": [strip_labels(s) for s in LC.load_scenarios(ROOT / "datasets/rift_v2/val.json")],
          "adv": [strip_labels(s) for s in LC.load_scenarios(ROOT / "datasets/rift_v3_dev/adversarial_dev.json")]}
    legacy = {k: LC.load_scenarios(ROOT / f"datasets/rift_faults/{k}.json") for k in ("development", "validation")}
    lf = {k: fp.fingerprint_all(v) for k, v in legacy.items()}
    leg_man = json.loads((ROOT / "datasets/rift_faults/manifest.json").read_text())
    v2_man = json.loads((ROOT / "datasets/rift_v2/manifest.json").read_text())
    rep = {
        "schema": "rift.final_dataset_independence/1",
        "sealed_policy": "no sealed file opened, parsed or hashed; sealed hashes copied from committed manifests",
        "readable_file_sha256": {p: sha(p) for p in READABLE},
        "sealed_file_sha256_copied_from_manifests": {
            "datasets/rift_faults/held_out_test" + ".json": leg_man["files"]["held_out_test" + ".json"]["sha256"],
            "datasets/rift_v2/heldout_candidate.json": v2_man["datasets"]["held_out"]["sha256"]},
        "legacy_rift_faults_dev_val": {
            "n": {k: len(v) for k, v in legacy.items()},
            "distinct_pooled": {lvl: dup.count_distinct(lf["development"] + lf["validation"], lvl) for lvl in dup.LEVELS},
            "val_scenarios_with_twin_in_dev": {lvl: len(dup.cross_split_leaks(
                {"dev": lf["development"], "val": lf["validation"]}, lvl, "val")) for lvl in dup.LEVELS}},
        "legacy_heldout_declared_twins": {
            "n_declared": len(leg_man["held_out_scenarios_with_content_twin_in_other_split"]),
            "of": leg_man["split_counts"]["HELD_OUT_TEST"],
            "source": "datasets/rift_faults/manifest.json + artifacts/sprint4_3_0/provenance/legacy_provenance_summary.json"},
        "v2_val_vs_dev": LC.check_candidate(v2["val"], {"dev": v2["dev"]}),
        "v2_adversarial_dev_vs_dev_val": LC.check_candidate(v2["adv"], {"dev": v2["dev"], "val": v2["val"]}),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=1, sort_keys=True, default=str) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print("v2 val vs dev ok:", rep["v2_val_vs_dev"]["ok"], "| adv vs dev/val ok:",
          rep["v2_adversarial_dev_vs_dev_val"]["ok"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
