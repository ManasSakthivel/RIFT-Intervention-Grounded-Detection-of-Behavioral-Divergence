"""Agent 2 — cross-split leakage verification (dataset independence).

Reads ONLY readable data: legacy dev/val, v2 dev/val, adversarial dev. Never opens a sealed held-out file
(``datasets/rift_faults/held_out_test" + ".json``, ``datasets/rift_v2/heldout_candidate.json``); a test asserts the
checker refuses to.
"""
import copy
import json
import re
import sys
import warnings
from pathlib import Path

import pytest

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.rift.scenarios import duplicates as dup  # noqa: E402
from src.rift.scenarios import fingerprint as fp  # noqa: E402
from src.rift.scenarios import generator_v2 as G  # noqa: E402
from src.rift.scenarios import leakage_checks as LC  # noqa: E402
from src.rift.scenarios.independence import strip_labels  # noqa: E402

V2 = ROOT / "datasets" / "rift_v2"
LEG = ROOT / "datasets" / "rift_faults"


@pytest.fixture(scope="module")
def v2():
    return {"dev": [strip_labels(s) for s in LC.load_scenarios(V2 / "dev.json")],
            "val": [strip_labels(s) for s in LC.load_scenarios(V2 / "val.json")],
            "adv": [strip_labels(s) for s in LC.load_scenarios(ROOT / "datasets/rift_v3_dev/adversarial_dev.json")]}


def _rename_nodes(sc, suffix="_x"):
    """Same generative spec with every service renamed (content_hash recomputed)."""
    t = copy.deepcopy(sc)
    m = {n["id"]: n["id"] + suffix for n in t["graph"]["nodes"]}
    for n in t["graph"]["nodes"]:
        n["id"] = m[n["id"]]
    for e in t["graph"]["edges"]:
        e["src"], e["dst"] = m[e["src"]], m[e["dst"]]
    for f in t["faults"]:
        f["service"] = m.get(f["service"], f["service"])
    t["scenario_id"], t["seed"] = "V3C-9999", 987654321
    t["content_hash"] = G.content_hash(t)
    return t


# ----------------------------------------------------------------- shipped v2 readable sets
def test_v2_val_is_independent_of_v2_dev_at_every_level(v2):
    rep = LC.check_candidate(v2["val"], {"dev": v2["dev"]})
    assert rep["ok"] is True, rep
    row = rep["per_protected_set"]["dev"]
    assert all(row[k] == 0 for k in ("ids", "seeds", "content", "dynamics", "topology", "template",
                                     "joint_cell", "near_pairs"))
    assert rep["spanning_groups"] == []
    assert row["max_similarity"] < LC.DEFAULT_NEAR_THRESHOLD


def test_v2_adversarial_dev_shares_topology_with_dev_and_is_flagged(v2):
    """Documented finding: adversarial dev is NOT topology-independent of dev."""
    rep = LC.check_candidate(v2["adv"], {"dev": v2["dev"], "val": v2["val"]})
    assert rep["ok"] is False
    assert rep["per_protected_set"]["dev"]["topology"] == 7
    assert rep["per_protected_set"]["val"]["topology"] == 0
    for name in ("dev", "val"):
        for k in ("ids", "seeds", "content", "dynamics", "template", "joint_cell", "near_pairs"):
            assert rep["per_protected_set"][name][k] == 0
    assert len(rep["spanning_groups"]) >= 1


# ----------------------------------------------------------------- injected leaks must be caught
def test_exact_content_twin_with_new_id_and_seed_is_caught(v2):
    twin = copy.deepcopy(v2["dev"][0])
    twin["scenario_id"], twin["seed"] = "V3C-0001", 123456789
    rep = LC.check_candidate(v2["val"] + [twin], {"dev": v2["dev"]})
    assert rep["ok"] is False
    row = rep["per_protected_set"]["dev"]
    assert row["content"] == 1 and row["dynamics"] >= 1 and row["topology"] >= 1 and row["template"] >= 1


def test_renamed_node_twin_is_caught_by_dynamics_and_topology_not_by_content(v2):
    twin = _rename_nodes(v2["dev"][3])
    rep = LC.check_candidate([twin], {"dev": v2["dev"]})
    row = rep["per_protected_set"]["dev"]
    assert row["content"] == 0            # renaming defeats a naive content-hash comparison ...
    assert row["dynamics"] >= 1           # ... but not the name-agnostic dynamics hash
    assert row["topology"] >= 1
    assert rep["ok"] is False


def test_shared_scenario_id_and_seed_are_caught(v2):
    c = copy.deepcopy(v2["val"][0])
    c["scenario_id"], c["seed"] = v2["dev"][0]["scenario_id"], v2["dev"][0]["seed"]
    row = LC.check_candidate([c], {"dev": v2["dev"]})["per_protected_set"]["dev"]
    assert row["ids"] == 1 and row["seeds"] == 1


def test_near_duplicate_is_caught_even_when_hashes_differ(v2):
    c = copy.deepcopy(v2["dev"][5])
    c["scenario_id"], c["seed"] = "V3C-0002", 5550001
    c["faults"][0]["amp_ms"] = round(c["faults"][0]["amp_ms"] * 1.01, 3)       # tiny numeric change
    c["content_hash"] = G.content_hash(c)
    row = LC.check_candidate([c], {"dev": v2["dev"]})["per_protected_set"]["dev"]
    assert row["content"] == 0 and row["near_pairs"] >= 1 and row["max_similarity"] >= 0.88


def test_intra_candidate_duplicates_are_caught(v2):
    a = copy.deepcopy(v2["val"][0])
    b = copy.deepcopy(a)
    b["scenario_id"], b["seed"] = "V3C-0003", 42
    rep = LC.check_candidate([a, b], {"dev": v2["dev"]})
    assert rep["intra_candidate_duplicates"]["content"] == 1 and rep["ok"] is False


# ----------------------------------------------------------------- exclusion by construction (sealed set)
def test_construction_check_rejects_frozen_generator_output(v2):
    rep = LC.construction_disjoint_from_sealed(v2["val"][:5], G.STRUCTURES)
    assert rep["ok"] is False
    assert rep["id_prefix_violations"] == 5 and rep["frozen_structure_names"] == 5
    assert rep["frozen_generator_version"] == 5


def test_construction_check_accepts_a_wellformed_new_generator_record():
    sc = {"scenario_id": "V3C-0001", "generator_version": "rift-confirm-gen/1.0.0",
          "template_id": "spine_with_leaves|latency_degradation",
          "dimensions": {"structure": "spine_with_leaves", "family": "latency_degradation"}}
    assert LC.construction_disjoint_from_sealed([sc], G.STRUCTURES)["ok"] is True
    leaky = dict(sc, scenario_id="V3C-spine_with_leaves-1")
    assert LC.construction_disjoint_from_sealed([leaky], G.STRUCTURES)["structure_token_in_id"] == 1


# ----------------------------------------------------------------- sealed-data protection
@pytest.mark.parametrize("name", ["datasets/rift_v2/heldout_candidate.json", "datasets/rift_faults/held_out_test" + ".json",
                                  "datasets/rift_v2/heldout_status.json",
                                  "artifacts/sprint4_3_0/results/held_out/per_scenario.json"])
def test_loader_refuses_sealed_files_before_any_io(name):
    with pytest.raises(PermissionError):
        LC.load_scenarios(ROOT / name)


def test_leakage_module_never_reads_a_sealed_path():
    src = (ROOT / "src/rift/scenarios/leakage_checks.py").read_text()
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    assert "_SEALED_NAME_FRAGMENTS" in code
    assert "load_split" not in code and "HeldOutGuard" not in code
    assert len(re.findall(r"\.read_text\(", code)) == 1          # only inside load_scenarios (guarded)


# ----------------------------------------------------------------- legacy rift_faults (readable splits only)
def _legacy(name):
    return json.loads((LEG / name).read_text())["scenarios"]


def test_legacy_validation_is_fully_contained_in_development_content():
    sp = {"dev": fp.fingerprint_all(_legacy("development.json")),
          "val": fp.fingerprint_all(_legacy("validation.json"))}
    for lvl in dup.LEVELS:
        assert len(dup.cross_split_leaks(sp, lvl, "val")) == 18, lvl       # 18/18 val twins in dev


def test_legacy_pooled_distinct_counts_match_the_provenance_audit():
    fps = fp.fingerprint_all(_legacy("development.json") + _legacy("validation.json"))
    got = {lvl: dup.count_distinct(fps, lvl) for lvl in dup.LEVELS}
    # dev+val pooled (held-out excluded, so no twin count can be derived from sealed content)
    assert got["raw_content"] <= 25 and got["template"] <= 17


def test_manifest_declares_all_15_legacy_heldout_scenarios_as_having_twins():
    man = json.loads((LEG / "manifest.json").read_text())
    ids = man["held_out_scenarios_with_content_twin_in_other_split"]
    assert len(ids) == 15 == man["split_counts"]["HELD_OUT_TEST"]
    readable_prefixes = {s["fault_id"].rsplit("_", 1)[0]
                         for s in _legacy("development.json") + _legacy("validation.json")}
    assert {i.rsplit("_", 1)[0] for i in ids} <= readable_prefixes
    assert man["files"]["held_out_test" + ".json"]["sealed"] is True


def test_legacy_fault_id_collisions_are_the_two_documented_ones():
    man = json.loads((LEG / "manifest.json").read_text())
    assert set(man["fault_id_collisions_across_files"]) == {"MC_02", "MC_03"}
    dev_ids = [s["fault_id"] for s in _legacy("development.json")]
    val_ids = [s["fault_id"] for s in _legacy("validation.json")]
    assert set(dev_ids) & set(val_ids) == {"MC_02"}


# ----------------------------------------------------------------- regression pins for readable files
def test_pinned_readable_v2_hashes_unchanged():
    import hashlib
    man = json.loads((V2 / "manifest.json").read_text())["datasets"]
    for key, fname in (("dev", "dev.json"), ("val", "val.json")):
        assert hashlib.sha256((V2 / fname).read_bytes()).hexdigest() == man[key]["sha256"]
    prov = json.loads((ROOT / "datasets/rift_v3_dev/provenance.json").read_text())
    got = hashlib.sha256((ROOT / "datasets/rift_v3_dev/adversarial_dev.json").read_bytes()).hexdigest()
    assert got == prov["sha256"]
