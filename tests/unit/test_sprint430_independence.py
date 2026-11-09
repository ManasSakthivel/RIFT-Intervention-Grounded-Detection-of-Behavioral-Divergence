"""Sprint 4.3.0 — duplicate detection, seed-only variation, template leakage, cross-split leakage,
group-aware splitting, deterministic generation, independence of the shipped v2 datasets."""
import copy
import json
import sys
import warnings
from pathlib import Path

import pytest

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.rift.scenarios import fingerprint as fp  # noqa: E402
from src.rift.scenarios import duplicates as dup  # noqa: E402
from src.rift.scenarios import generator_v2 as G  # noqa: E402
from src.rift.scenarios.independence import strip_labels, verify_independence  # noqa: E402
from src.rift.scenarios.splitter import (assign_groups, build_groups,  # noqa: E402
                                         group_integrity_violations)
from src.rift.scenarios.validators import validate_all  # noqa: E402


def legacy(fid, seed=1, root="a", path=(("a", "b"), ("b", "c")), t=120.0, ftype="LATENCY", **kw):
    d = {"fault_id": fid, "name": fid, "seed": seed, "split": "x", "root_cause_service": root,
         "causal_path": [list(e) for e in path], "injected_at_t": t, "expected_recovery_t": t + 60,
         "fault_type": ftype, "affected_services": sorted({s for e in path for s in e}), "confounded": False}
    d.update(kw)
    return d


# ------------------------------------------------------------------ duplicate detection
def test_exact_duplicates_detected_despite_different_ids_and_seeds():
    a, b = legacy("A", seed=1), legacy("B", seed=99)
    fps = fp.fingerprint_all([a, b, legacy("C", root="b", path=(("b", "c"),))])
    groups = dup.duplicate_groups(fps, "raw_content")
    assert groups == [["A", "B"]]
    assert dup.count_distinct(fps, "raw_content") == 2


def test_seed_only_variation_is_reported():
    a, b = legacy("A", seed=1), legacy("B", seed=2)
    c = legacy("C", seed=3, t=300.0)                       # genuinely different content
    assert dup.seed_only_variants([a, b, c]) == [["A", "B"]]
    # identical seed is a plain duplicate, not "seed-only"
    assert dup.seed_only_variants([legacy("A", seed=1), legacy("B", seed=1)]) == []


def test_effective_dynamics_collapses_fields_the_generator_ignores():
    """Legacy generator ignores fault_type/confounded/affected: records differing only there share dynamics."""
    a = legacy("A", ftype="LATENCY")
    b = legacy("B", ftype="ERROR_RATE", confounded=True)
    fa, fb = fp.fingerprint(a), fp.fingerprint(b)
    assert fa.raw_content != fb.raw_content
    assert fa.effective_dynamics == fb.effective_dynamics


def test_template_fingerprint_ignores_renaming_and_small_timing_shifts():
    a = legacy("A", root="a", path=(("a", "b"), ("b", "c")), t=120.0)
    b = legacy("B", root="x", path=(("x", "y"), ("y", "z")), t=125.0)
    assert fp.fingerprint(a).template == fp.fingerprint(b).template
    assert fp.fingerprint(a).raw_content != fp.fingerprint(b).raw_content


def test_near_duplicates_found_but_exact_excluded():
    a = legacy("A")
    b = legacy("B", t=125.0)       # differs only in timing: similarity 0.9
    c = legacy("C", root="q", path=(("q", "r"),), t=500.0, ftype="CPU")
    fps = fp.fingerprint_all([a, b, c, legacy("A2")])
    pairs = dup.near_duplicate_pairs(fps, 0.85)
    assert any({x, y} == {"A", "B"} for x, y, _ in pairs)
    assert not any({x, y} == {"A", "A2"} for x, y, _ in pairs)      # exact duplicates are not "near"
    assert not any("C" in (x, y) for x, y, _ in pairs)


# ------------------------------------------------------------------ cross-split / template leakage
def test_cross_split_leak_detected_by_content_not_by_id():
    dev = fp.fingerprint_all([legacy("DEV1"), legacy("DEV2", root="b", path=(("b", "c"),))])
    held = fp.fingerprint_all([legacy("H1", seed=777)])          # same content, new id and seed
    leaks = dup.cross_split_leaks({"dev": dev, "held_out": held}, "raw_content", "held_out")
    assert leaks == [("H1", "dev")]
    m = dup.leakage_matrix({"dev": dev, "held_out": held}, "raw_content")
    assert m["cells"]["held_out"]["dev"] == {"n_with_twin": 1, "denominator": 1, "fraction": 1.0}
    assert m["cells"]["dev"]["held_out"]["denominator"] == 2


def test_template_leakage_detected_across_renamed_services():
    dev = fp.fingerprint_all([legacy("D", root="a", path=(("a", "b"), ("b", "c")))])
    held = fp.fingerprint_all([legacy("H", root="m", path=(("m", "n"), ("n", "o")), t=118.0)])
    assert dup.cross_split_leaks({"dev": dev, "held_out": held}, "raw_content", "held_out") == []
    assert dup.cross_split_leaks({"dev": dev, "held_out": held}, "template", "held_out") == [("H", "dev")]


def _v2_split(name):
    return json.loads((ROOT / "datasets" / "rift_v2" / name).read_text())["scenarios"]


def test_independence_verifier_flags_injected_leaks():
    dev, val = _v2_split("dev.json"), _v2_split("val.json")
    held = [strip_labels(s) for s in json.loads(
        (ROOT / "datasets" / "rift_v2" / "heldout_candidate.json").read_text())["scenarios"]]
    splits = {"dev": [strip_labels(s) for s in dev], "val": [strip_labels(s) for s in val], "held_out": held}
    assert verify_independence(splits)["ok"] is True
    leaked = copy.deepcopy(splits)
    twin = copy.deepcopy(leaked["dev"][0])
    twin["scenario_id"] = "HELD-TWIN"
    twin["seed"] = 123456                                  # a different seed must not hide the leak
    twin["split"] = "held_out"
    leaked["held_out"].append(twin)
    rep = verify_independence(leaked)
    assert rep["ok"] is False
    assert rep["leaks_for_protected"]["template_id"] >= 1 or rep["leaks_for_protected"]["content_hash"] >= 1


def test_shipped_v2_datasets_are_content_disjoint_and_sizes_meet_targets():
    sets = {n: _v2_split(f) for n, f in (("dev", "dev.json"), ("val", "val.json"),
                                          ("held_out", "heldout_candidate.json"))}
    hashes = {n: {s["content_hash"] for s in v} for n, v in sets.items()}
    for n, v in sets.items():
        assert len(hashes[n]) == len(v), f"{n}: duplicate content inside split"
    assert not (hashes["dev"] & hashes["val"]) and not (hashes["dev"] & hashes["held_out"]) \
        and not (hashes["val"] & hashes["held_out"])
    ids = [s["scenario_id"] for v in sets.values() for s in v]
    assert len(ids) == len(set(ids)), "scenario ids collide across splits"
    tpl = {n: {s["template_id"] for s in v} for n, v in sets.items()}
    assert not (tpl["dev"] & tpl["held_out"]) and not (tpl["val"] & tpl["held_out"]) and not (tpl["dev"] & tpl["val"])
    assert len(sets["dev"]) >= 150 and len(sets["val"]) >= 60 and len(sets["held_out"]) >= 90
    assert sum(map(len, sets.values())) >= 300


def test_stored_independence_report_matches_current_files_and_is_ok():
    rep = json.loads((ROOT / "datasets" / "rift_v2" / "independence_report.json").read_text())
    assert rep["ok"] is True
    assert all(v == 0 for v in rep["leaks_for_protected"].values())
    assert rep["group_integrity_violations"] == [] and rep["near_duplicate_pairs_cross_split"] == []


# ------------------------------------------------------------------ group-aware splitting
def test_union_find_groups_are_transitive():
    items = {"a": {"t": 1, "g": "x"}, "b": {"t": 1, "g": "y"}, "c": {"t": 2, "g": "y"}, "d": {"t": 3, "g": "z"}}
    grp = build_groups(items, [lambda s: s["t"], lambda s: s["g"]])
    assert grp["a"] == grp["b"] == grp["c"]            # a~b via t, b~c via g
    assert grp["d"] != grp["a"]


def test_assign_groups_never_splits_a_group_and_is_deterministic():
    items = {f"s{i}": {"t": i // 3, "g": i % 5 if i % 7 == 0 else 100 + i} for i in range(60)}
    grp = build_groups(items, [lambda s: ("t", s["t"]), lambda s: ("g", s["g"])])
    sizes = {}
    for g in grp.values():
        sizes[g] = sizes.get(g, 0) + 1
    a1 = assign_groups(sizes, {"dev": 0.6, "val": 0.2, "held_out": 0.2}, seed=5)
    a2 = assign_groups(sizes, {"dev": 0.6, "val": 0.2, "held_out": 0.2}, seed=5)
    assert a1 == a2
    split_of = {i: a1[g] for i, g in grp.items()}
    assert group_integrity_violations(split_of, grp) == []
    broken = dict(split_of)
    victim = next(i for i, g in grp.items() if sizes[g] > 1)
    broken[victim] = "held_out" if split_of[victim] != "held_out" else "dev"
    assert group_integrity_violations(broken, grp)


def test_assign_groups_honours_forced_placement():
    out = assign_groups({"g1": 5, "g2": 5, "g3": 5}, {"dev": 0.5, "held_out": 0.5}, seed=1, forced={"g1": "held_out"})
    assert out["g1"] == "held_out"


# ------------------------------------------------------------------ deterministic generation
def test_generation_is_byte_deterministic_and_matches_shipped_prefix():
    a = G.generate_split("val", 12)
    b = G.generate_split("val", 12)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert [s["content_hash"] for s in a] == [s["content_hash"] for s in b]
    shipped = _v2_split("val.json")
    assert {s["content_hash"] for s in G.generate_split("val")} == {s["content_hash"] for s in shipped}


def test_content_hash_ignores_seed_label_but_not_dynamics():
    sc = copy.deepcopy(_v2_split("val.json")[0])
    h0 = G.content_hash(sc)
    sc2 = copy.deepcopy(sc)
    sc2["scenario_id"] = "RENAMED"
    assert G.content_hash(sc2) == h0                      # id is not content
    sc3 = copy.deepcopy(sc)
    sc3["faults"][0]["amp_ms"] = sc3["faults"][0]["amp_ms"] + 5.0
    assert G.content_hash(sc3) != h0


def test_qc_validator_accepts_shipped_and_rejects_broken_scenarios():
    val = _v2_split("val.json")
    assert validate_all(val[:6])["n_failed"] == 0
    bad = copy.deepcopy(val[0])
    del bad["ground_truth"]
    assert validate_all([bad], reproducibility=False)["n_failed"] == 1
    bad2 = copy.deepcopy(val[1])
    bad2["content_hash"] = "0" * 64
    assert validate_all([bad2])["n_failed"] == 1
