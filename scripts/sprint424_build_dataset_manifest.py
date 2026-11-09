#!/usr/bin/env python3
"""
Sprint 4.2.4 / Issue 4 — build the canonical dataset manifest (schema rift.dataset_manifest/2).

Deterministic and read-only with respect to the scenario files: it
  1. verifies every registered file against src.rift.evaluation.dataset_registry pins,
  2. re-runs SyntheticBenchmark().generate_all_faults(42) to obtain the generator output (69),
  3. classifies each deployed scenario as generator-produced (field-identical) or hand-added,
  4. records id collisions and content duplication across splits,
  5. verifies the preserved historical manifest copy hash.

It reads the sealed file only as a hashed byte string via the registry's file-level verification
(no labels are used for any selection). Usage:

    python3 scripts/sprint424_build_dataset_manifest.py            # print manifest JSON
    python3 scripts/sprint424_build_dataset_manifest.py --write    # overwrite datasets/rift_faults/manifest.json
    python3 scripts/sprint424_build_dataset_manifest.py --check    # exit 1 if manifest.json is stale
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.rift.benchmark.synthetic_benchmark import SyntheticBenchmark  # noqa: E402
from src.rift.evaluation import dataset_registry as dr  # noqa: E402

SCHEMA = "rift.dataset_manifest/2"
MANIFEST = dr.data_dir() / "manifest.json"
CONTENT_EXCLUDE = ("fault_id", "name", "seed", "split", "_file")


def _norm(obj: Any) -> Any:
    """JSON round-trip so tuples == lists."""
    return json.loads(json.dumps(obj, default=list))


def _content_key(sc: dict) -> str:
    return json.dumps({k: v for k, v in sc.items() if k not in CONTENT_EXCLUDE}, sort_keys=True)


def _load_raw_unsealed(split: str) -> List[dict]:
    """Read + verify a split file at the byte level (registry pin), for MANIFEST generation only."""
    spec = dr.REGISTRY[split]
    raw = dr.resolve_path(split).read_bytes()
    return dr.verify_bytes(split, raw, spec)["scenarios"]


def build() -> Dict[str, Any]:
    problems = dr.verify_all_files()
    if problems:
        raise SystemExit("dataset integrity failure: " + "; ".join(problems))

    generated = [_norm(dataclasses.asdict(g)) for g in SyntheticBenchmark().generate_all_faults(42)]
    gen_by_key = {(g["split"], g["fault_id"]): g for g in generated}
    gen_counts = collections.Counter(g["split"] for g in generated)

    files: Dict[str, Any] = {}
    deployed: List[dict] = []
    hand_added: Dict[str, List[str]] = {}
    for split in (dr.SPLIT_DEVELOPMENT, dr.SPLIT_VALIDATION, dr.SPLIT_HELD_OUT_TEST):
        spec = dr.REGISTRY[split]
        scs = _load_raw_unsealed(split)
        extra = [s["fault_id"] for s in scs if gen_by_key.get((split, s["fault_id"])) != _norm(s)]
        hand_added[split] = extra
        deployed += [{**s, "_file": spec.filename} for s in scs]
        files[spec.filename] = {
            "split": split,
            "scenario_count": len(scs),
            "unique_scenario_ids": len({s["fault_id"] for s in scs}),
            "sha256": spec.sha256,
            "size_bytes": spec.size_bytes,
            "generator_produced": len(scs) - len(extra),
            "hand_added": len(extra),
            "hand_added_ids": extra,
            "used_for_threshold_selection": split != dr.SPLIT_HELD_OUT_TEST,
            "sealed": spec.sealed,
        }
    adv = dr.REGISTRY["ADVERSARIAL"]
    adv_sc = json.loads(dr.resolve_path("ADVERSARIAL").read_bytes())["scenarios"]
    files[adv.filename] = {
        "split": None,
        "scenario_count": len(adv_sc),
        "unique_scenario_ids": len({s["scenario_id"] for s in adv_sc}),
        "sha256": adv.sha256,
        "size_bytes": adv.size_bytes,
        "generator_produced": None,
        "hand_added": None,
        "role": "adversarial stress cohort (separate generator; NOT part of the 83-scenario corpus); "
                "per family (6 families x 5): indices 01-03 (18 scenarios) used for threshold selection, "
                "indices 04-05 (12 scenarios) reserved for the frozen final evaluation",
        "used_for_threshold_selection": "partial (18 of 30: per-family indices 01-03)",
        "sealed": False,
    }

    ids = collections.Counter(s["fault_id"] for s in deployed)
    collisions = {
        i: [{"file": s["_file"], "split": s["split"], "root_cause_service": s["root_cause_service"],
             "seed": s["seed"]} for s in deployed if s["fault_id"] == i]
        for i, n in sorted(ids.items()) if n > 1
    }
    groups: Dict[str, List[dict]] = collections.defaultdict(list)
    for s in deployed:
        groups[_content_key(s)].append(s)
    held_with_twin = sorted(
        s["fault_id"] for g in groups.values() for s in g
        if s["split"] == dr.SPLIT_HELD_OUT_TEST and any(o["split"] != s["split"] for o in g))

    split_counts = {sp: files[dr.REGISTRY[sp].filename]["scenario_count"]
                    for sp in (dr.SPLIT_DEVELOPMENT, dr.SPLIT_VALIDATION, dr.SPLIT_HELD_OUT_TEST)}
    by_type = collections.Counter(s["fault_type"] for s in deployed)
    confounded = sum(bool(s.get("confounded")) for s in deployed)
    v1_gen_conf = sum(bool(g["confounded"]) for g in generated)
    return {
        "schema": SCHEMA,
        "generator": "SyntheticBenchmark",
        "seed": 42,
        "total_scenarios": len(deployed),
        "unique_fault_ids": len(ids),
        "non_confounded": len(deployed) - confounded,
        "confounded": confounded,
        "by_fault_type": dict(sorted(by_type.items())),
        "split_counts": split_counts,
        "generator_output": {
            "total_scenarios": len(generated),
            "split_counts": {k: gen_counts[k] for k in
                             (dr.SPLIT_DEVELOPMENT, dr.SPLIT_VALIDATION, dr.SPLIT_HELD_OUT_TEST)},
            "confounded": v1_gen_conf,
            "historical_manifest": dr.HISTORICAL_MANIFEST_V1,
            "historical_manifest_sha256": dr.HISTORICAL_MANIFEST_V1_SHA256,
            "note": "The historical manifest (69 scenarios) described the generator output only. "
                    "It was not regenerated when the development split was expanded by hand "
                    "(P0-02: +14 scenarios).",
        },
        "files": files,
        "reconciliation": {
            "deployed_total": len(deployed),
            "generator_total": len(generated),
            "difference": len(deployed) - len(generated),
            "difference_explained_by": "hand-added development scenarios " + ", ".join(
                hand_added[dr.SPLIT_DEVELOPMENT]),
            "hand_added_total": sum(len(v) for v in hand_added.values()),
        },
        "fault_id_collisions_across_files": collisions,
        "held_out_scenarios_with_content_twin_in_other_split": held_with_twin,
        "content_duplication_note": (
            "Scenarios are templated; scenarios in different splits can be identical apart from "
            "fault_id/name/seed/split. Held-out is therefore NOT content-independent of "
            "development/validation. See docs/RIFT_DATASET_PROVENANCE.md."),
        "h2_power_note": "48 confounded scenarios; unchanged by the development expansion "
                         "(hand-added scenarios are MULTI_CAUSE / AMBIGUOUS_ATTRIBUTION, not CONFOUNDED)",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    text = json.dumps(build(), indent=2, sort_keys=False) + "\n"
    if a.write:
        MANIFEST.write_text(text)
        print(f"wrote {MANIFEST} sha256={hashlib.sha256(text.encode()).hexdigest()}")
        return 0
    if a.check:
        if not MANIFEST.exists() or MANIFEST.read_text() != text:
            print("manifest.json is stale or missing", file=sys.stderr)
            return 1
        print("manifest.json is current")
        return 0
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
