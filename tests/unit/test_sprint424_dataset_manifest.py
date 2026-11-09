"""
Sprint 4.2.4 / Issue 4 — dataset manifest reconciliation (69 generator output vs 83 deployed).

The manifest is checked against the actual files, the generator is re-run, and the historical
manifest is checked against its recorded hash.
"""
import collections
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from src.rift.evaluation import dataset_registry as dr  # noqa: E402
import sprint424_build_dataset_manifest as bm  # noqa: E402

D = dr.data_dir()
HELD_FILE = dr.REGISTRY[dr.SPLIT_HELD_OUT_TEST].filename   # no literal sealed path in source
HELD_STEM = dr.REGISTRY[dr.SPLIT_HELD_OUT_TEST].stem
MANIFEST = json.loads((D / "manifest.json").read_text())
HISTORICAL = json.loads((D / dr.HISTORICAL_MANIFEST_V1).read_text())


def _count(path):
    return len(json.loads(path.read_text())["scenarios"])


def test_canonical_manifest_is_current_with_builder():
    assert bm.build() == MANIFEST


def test_manifest_counts_match_files():
    assert MANIFEST["schema"] == "rift.dataset_manifest/2"
    for name, spec in MANIFEST["files"].items():
        assert _count(D / name) == spec["scenario_count"], name
    assert MANIFEST["split_counts"] == {"DEVELOPMENT": 50, "VALIDATION": 18, "HELD_OUT_TEST": 15}
    assert MANIFEST["total_scenarios"] == sum(MANIFEST["split_counts"].values()) == 83


def test_manifest_hashes_match_files_and_registry():
    for name, spec in MANIFEST["files"].items():
        assert hashlib.sha256((D / name).read_bytes()).hexdigest() == spec["sha256"], name
    for r in dr.REGISTRY.values():
        assert MANIFEST["files"][r.filename]["sha256"] == r.sha256


def test_unique_id_counts_are_honest():
    deployed = []
    for sp in ("development", "validation", HELD_STEM):
        deployed += [s["fault_id"] for s in json.loads((D / f"{sp}.json").read_text())["scenarios"]]
    assert len(deployed) == 83
    assert MANIFEST["unique_fault_ids"] == len(set(deployed)) == 81
    for name, spec in MANIFEST["files"].items():
        assert spec["unique_scenario_ids"] == spec["scenario_count"], name


def test_historical_manifest_preserved_and_documents_69():
    raw = (D / dr.HISTORICAL_MANIFEST_V1).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == dr.HISTORICAL_MANIFEST_V1_SHA256
    assert HISTORICAL["total_scenarios"] == 69
    assert HISTORICAL["split_counts"] == {"DEVELOPMENT": 36, "VALIDATION": 18, "HELD_OUT_TEST": 15}
    assert MANIFEST["generator_output"]["historical_manifest_sha256"] == dr.HISTORICAL_MANIFEST_V1_SHA256


def test_69_is_reproduced_by_regenerating_with_the_generator():
    from src.rift.benchmark.synthetic_benchmark import SyntheticBenchmark
    gen = SyntheticBenchmark().generate_all_faults(42)
    assert len(gen) == 69
    c = collections.Counter(g.split for g in gen)
    assert (c["DEVELOPMENT"], c["VALIDATION"], c["HELD_OUT_TEST"]) == (36, 18, 15)
    assert MANIFEST["generator_output"]["total_scenarios"] == 69


def test_difference_is_exactly_the_14_hand_added_dev_scenarios():
    assert MANIFEST["reconciliation"]["difference"] == 14
    ids = MANIFEST["files"]["development.json"]["hand_added_ids"]
    assert ids == [f"MC_{i:02d}" for i in range(2, 13)] + ["AA_01", "AA_02", "AA_03"]
    assert MANIFEST["files"]["validation.json"]["hand_added"] == 0
    assert MANIFEST["files"][HELD_FILE]["hand_added"] == 0


def test_generator_scenarios_are_field_identical_in_deployed_files():
    from src.rift.benchmark.synthetic_benchmark import SyntheticBenchmark
    import dataclasses
    gen = {(g.split, g.fault_id): json.loads(json.dumps(dataclasses.asdict(g), default=list))
           for g in SyntheticBenchmark().generate_all_faults(42)}
    deployed = {}
    for sp, f in (("DEVELOPMENT", "development"), ("VALIDATION", "validation"),
                  ("HELD_OUT_TEST", HELD_STEM)):
        for s in json.loads((D / f"{f}.json").read_text())["scenarios"]:
            deployed[(sp, s["fault_id"])] = s
    assert set(gen) <= set(deployed)
    assert all(deployed[k] == v for k, v in gen.items())
    assert len(set(deployed) - set(gen)) == 14


def test_fault_id_collisions_are_documented():
    assert set(MANIFEST["fault_id_collisions_across_files"]) == {"MC_02", "MC_03"}
    for entries in MANIFEST["fault_id_collisions_across_files"].values():
        assert len({e["split"] for e in entries}) == 2


def test_held_out_content_overlap_is_disclosed_not_hidden():
    twins = MANIFEST["held_out_scenarios_with_content_twin_in_other_split"]
    assert len(twins) > 0 and "CF_36" in twins
    assert "content_duplication_note" in MANIFEST


def test_adversarial_cohort_listed_separately_and_not_in_total():
    adv = MANIFEST["files"]["adversarial_stress_cohort.json"]
    assert adv["scenario_count"] == 30 and adv["split"] is None
    assert MANIFEST["total_scenarios"] == 83


def test_selection_flags():
    f = MANIFEST["files"]
    assert f["development.json"]["used_for_threshold_selection"] is True
    assert f["validation.json"]["used_for_threshold_selection"] is True
    assert f[HELD_FILE]["used_for_threshold_selection"] is False
    assert f[HELD_FILE]["sealed"] is True


def test_fault_injector_import_check_accepts_canonical_manifest():
    import importlib
    import src.rift.fault_injection.fault_injector as fi
    importlib.reload(fi)
    assert fi.MANIFEST_SPLIT_DEVELOPMENT == 50
    fi._verify_manifest_split()


def test_fault_injector_rejects_the_stale_generator_manifest(monkeypatch):
    import src.rift.fault_injection.fault_injector as fi
    monkeypatch.setattr(fi, "_MANIFEST_PATH", D / dr.HISTORICAL_MANIFEST_V1)
    with pytest.raises(RuntimeError, match="DEVELOPMENT count 36"):
        fi._verify_manifest_split()


def test_builder_check_cli_passes():
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "sprint424_build_dataset_manifest.py"),
                        "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
