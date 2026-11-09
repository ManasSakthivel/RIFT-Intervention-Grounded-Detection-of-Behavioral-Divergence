#!/usr/bin/env python3
"""Sprint 4.3.0 Phase 1 — dataset provenance audit of the legacy scenario splits.

Read-only with respect to every dataset. Writes only under artifacts/sprint4_3_0/provenance/.

Legacy held-out (v1) labels are read ONLY to compute content fingerprints, through the registry
and an explicit HeldOutGuard token whose name records that this is a provenance audit. No metric,
threshold or method output is computed from them. The legacy held-out set was already consumed by
earlier sprints and is treated as contaminated legacy data regardless.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from src.rift.evaluation.dataset_registry import (  # noqa: E402
    PURPOSE_FINAL, PURPOSE_SELECTION, SPLIT_DEVELOPMENT, SPLIT_HELD_OUT_TEST,
    SPLIT_VALIDATION, load_split,
)
from src.rift.evaluation.held_out_guard import HeldOutGuard  # noqa: E402
from src.rift.scenarios.duplicates import (  # noqa: E402
    count_distinct, duplicate_groups, group_by_level, leakage_matrix, near_duplicate_pairs,
    seed_only_variants,
)
from src.rift.scenarios.fingerprint import fingerprint_all  # noqa: E402

OUT = REPO_ROOT / "artifacts" / "sprint4_3_0" / "provenance"
LEVELS = ("raw_content", "effective_dynamics", "structure", "template")


def _family(fid: str) -> str:
    return fid.rsplit("_", 1)[0]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    guard = HeldOutGuard()
    token = "SPRINT430_PROVENANCE_AUDIT_FINGERPRINT_ONLY"
    guard.allow_oracle(token)
    guard.activate_token(token)
    try:
        ho = load_split(SPLIT_HELD_OUT_TEST, purpose=PURPOSE_FINAL, guard=guard)
    finally:
        guard.deactivate_token()
    splits = {
        "dev": load_split(SPLIT_DEVELOPMENT, purpose=PURPOSE_SELECTION),
        "val": load_split(SPLIT_VALIDATION, purpose=PURPOSE_SELECTION),
        "held_out_v1": ho,
        "adversarial": load_split("ADVERSARIAL", purpose=PURPOSE_SELECTION),
    }
    fps = {k: fingerprint_all(v) for k, v in splits.items()}
    core = {k: fps[k] for k in ("dev", "val", "held_out_v1")}

    records = []
    for split, scs in splits.items():
        for sc, fp in zip(scs, fps[split]):
            sid = fp.scenario_id
            records.append({
                "id": sid, "split": split, "template_prefix": _family(sid),
                "fault_type": sc.get("fault_type", sc.get("family")),
                "root_cause": sc.get("root_cause_service"),
                "n_affected": len(sc.get("affected_services", [])),
                "n_edges": len(sc.get("causal_path", [])),
                "injected_at_t": sc.get("injected_at_t"),
                "expected_recovery_t": sc.get("expected_recovery_t"),
                "confounded": bool(sc.get("confounded", False)),
                "seed": sc.get("seed"),
                "intervention_type": None, "intervention_magnitude": None,
                "propagation_pattern": "fixed hop*10s +40ms (legacy generator)",
                "workload": "fixed N(0,10) baseline (legacy generator)",
                "generator_version": "legacy (unversioned) / generate_scenario_metrics",
                "parent_scenario": None,
                "raw_content": fp.raw_content[:16], "effective_dynamics": fp.effective_dynamics[:16],
                "structure": fp.structure[:16], "template": fp.template[:16],
            })
    (OUT / "legacy_lineage.json").write_text(json.dumps(records, indent=1, sort_keys=True))
    with open(OUT / "legacy_lineage.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)

    report = {"n_records": {k: len(v) for k, v in splits.items()}}
    report["distinct"] = {lvl: {k: count_distinct(v, lvl) for k, v in fps.items()} for lvl in LEVELS}
    all_core = [fp for k in core for fp in core[k]]
    report["distinct_core_pooled"] = {lvl: count_distinct(all_core, lvl) for lvl in LEVELS}
    report["distinct_all_pooled"] = {lvl: count_distinct([fp for v in fps.values() for fp in v], lvl)
                                     for lvl in LEVELS}
    report["leakage"] = {lvl: leakage_matrix(core, lvl) for lvl in LEVELS}
    report["heldout_twin_counts"] = {}
    for lvl in LEVELS:
        other = {getattr(fp, lvl) for k in ("dev", "val") for fp in fps[k]}
        twins = [fp.scenario_id for fp in fps["held_out_v1"] if getattr(fp, lvl) in other]
        report["heldout_twin_counts"][lvl] = {"n_heldout": len(fps["held_out_v1"]),
                                              "n_with_twin_in_dev_or_val": len(twins), "ids": twins}
    ids = {}
    for k in core:
        for fp in core[k]:
            ids.setdefault(fp.scenario_id, []).append(k)
    report["id_collisions_across_splits"] = {i: s for i, s in ids.items() if len(s) > 1}
    report["seed_only_variant_groups"] = {k: seed_only_variants(v) for k, v in splits.items()}
    report["seed_only_groups_pooled_core"] = seed_only_variants([s for k in core for s in splits[k]])
    report["exact_duplicate_groups_pooled_core"] = duplicate_groups(all_core, "raw_content")
    report["near_duplicate_pairs_ge_0.85_excluding_exact"] = len(near_duplicate_pairs(all_core, 0.85))
    report["near_duplicate_pairs_ge_0.70_excluding_exact"] = len(near_duplicate_pairs(all_core, 0.70))
    report["template_prefix_by_split"] = {}
    for k in splits:
        c = {}
        for fp in fps[k]:
            c[_family(fp.scenario_id)] = c.get(_family(fp.scenario_id), 0) + 1
        report["template_prefix_by_split"][k] = dict(sorted(c.items()))
    report["legacy_generator_consumed_fields"] = ["root_cause_service", "causal_path", "injected_at_t", "seed"]
    report["labels_not_reflected_in_observable_series"] = [
        "fault_type", "confounded", "affected_services", "expected_recovery_t", "workload", "observability"]
    report["groups_effective_dynamics_core"] = {
        h[:12]: g for h, g in group_by_level(all_core, "effective_dynamics").items() if len(g) > 1}
    (OUT / "legacy_provenance_summary.json").write_text(
        json.dumps(report, indent=1, sort_keys=True, default=str))

    print("n_records", report["n_records"])
    print("distinct", json.dumps(report["distinct"]))
    print("pooled core", report["distinct_core_pooled"], "pooled all", report["distinct_all_pooled"])
    for lvl in LEVELS:
        h = report["heldout_twin_counts"][lvl]
        print("heldout twins", lvl, h["n_with_twin_in_dev_or_val"], "/", h["n_heldout"])
    print("id collisions:", report["id_collisions_across_splits"])
    print("near>=0.85:", report["near_duplicate_pairs_ge_0.85_excluding_exact"],
          "near>=0.70:", report["near_duplicate_pairs_ge_0.70_excluding_exact"])
    print("seed-only groups (pooled core):", len(report["seed_only_groups_pooled_core"]))
    for lvl in LEVELS:
        print(lvl, {a: {b: c["n_with_twin"] for b, c in row.items()}
                    for a, row in report["leakage"][lvl]["cells"].items()})
    print("template prefixes", json.dumps(report["template_prefix_by_split"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
