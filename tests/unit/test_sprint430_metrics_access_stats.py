"""Sprint 4.3.0 — ground-truth leakage, held-out access control, metric denominators, abstention accounting,
statistical grouping."""
import copy
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pytest

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.rift.evaluation import benchmark_v2 as bm  # noqa: E402
from src.rift.evaluation import dataset_registry_v2 as reg  # noqa: E402
from src.rift.evaluation import stats_v2 as st  # noqa: E402
from src.rift.evaluation.held_out_guard import HeldOutGuard, HeldOutLeakageError  # noqa: E402
from src.rift.scenarios import simulator as sim  # noqa: E402


def _dev(n=None):
    sc = reg.load_v2("dev").scenarios
    return sc if n is None else sc[:n]


# =================================================================== ground-truth leakage
LABEL_KEYS = {"ground_truth", "design", "dimensions", "faults", "graph", "template_id", "parent_scenario"}


def test_observe_output_contains_no_label_or_design_fields():
    o = sim.observe(_dev(1)[0])
    assert set(o) == {"metrics", "baseline_stats", "call_graph", "incident_window"}
    assert not (set(o) & LABEL_KEYS)
    assert all(set(df.columns) == {"time", "value"} for df in o["metrics"].values())


def test_incident_window_is_a_fixed_convention_not_derived_from_the_fault_onset():
    scs = _dev(40)
    assert len({sim.observe(s)["incident_window"][0] for s in scs}) == 1
    assert len({min(f["onset_s"] for f in s["faults"]) for s in scs if s["faults"]}) > 1


def test_incident_context_given_to_baselines_carries_no_labels():
    sc = _dev(1)[0]
    ctx = bm.make_context(sc, sim.observe(sc))
    fields = set(vars(ctx))
    assert not any("ground" in f or "root" in f or "label" in f for f in fields), fields


def test_non_oracle_method_outputs_are_invariant_to_ground_truth_and_design_fields():
    non_oracle = [m.method_id for m in bm.REGISTRY if not m.oracle]
    for sc in _dev(6):
        mutated = copy.deepcopy(sc)
        mutated["ground_truth"] = {"expected_outcome": "ABSTAIN_REQUIRED", "roots": ["ZZZ"], "distractors": ["QQQ"],
                                   "attributable_roots": ["ZZZ"], "abstain_reason": "X", "identifiability": "X",
                                   "identifiable_by": [], "unobserved_roots": []}
        mutated["design"] = {"poison": True}
        a = bm.run_methods(sc, methods=non_oracle)
        b = bm.run_methods(mutated, methods=non_oracle)
        assert set(a) == set(non_oracle)
        for m in non_oracle:
            ka = (a[m]["abstained"], a[m]["reason"], a[m]["top"])
            kb = (b[m]["abstained"], b[m]["reason"], b[m]["top"])
            assert ka == kb, f"{m} output depends on label fields on {sc['scenario_id']}"


def test_oracle_methods_are_labelled_and_excluded_from_the_confirmatory_family():
    for m in bm.REGISTRY:
        if m.oracle:
            assert m.method_id.startswith("ORACLE:")
            assert not m.confirmatory
    assert not any(m.oracle for m in bm.REGISTRY if m.confirmatory)
    assert "RIFT-FULL-V2" not in [m.method_id for m in bm.REGISTRY if m.confirmatory]
    assert bm.EXCLUDED[0]["method_id"] == "B4-SAGE-CHAOS"


def test_oracle_upper_bound_does_use_labels_so_it_must_change_with_them():
    sc = next(s for s in _dev() if s["ground_truth"]["expected_outcome"] == "ATTRIBUTE")
    base = bm.run_methods(sc, methods=["ORACLE:UPPER-BOUND"])["ORACLE:UPPER-BOUND"]["top"][0][0]
    mutated = copy.deepcopy(sc)
    mutated["ground_truth"]["attributable_roots"] = ["OTHER"]
    assert bm.run_methods(mutated, methods=["ORACLE:UPPER-BOUND"])["ORACLE:UPPER-BOUND"]["top"][0][0] == "OTHER" != base


def test_rift_v2_signature_has_no_scenario_argument():
    import inspect
    from src.rift.evaluation import rift_v2
    params = set(inspect.signature(rift_v2.run_v2).parameters)
    assert params == {"obs", "intervene_fn", "fault_id", "scenario_seed", "cfg", "cache", "pag_override"}


def test_oracle_graph_variant_refuses_to_run_without_an_explicit_graph():
    from src.rift.evaluation import rift_v2
    sc = _dev(1)[0]
    with pytest.raises(ValueError):
        rift_v2.run_v2(sim.observe(sc), lambda x, y, s: {}, "x", 1, rift_v2.CONFIGS["A9-ORACLE-GRAPH"])


# =================================================================== held-out access control
def _fake_heldout(tmp_path, *, status="FINAL_FROZEN", freeze=True, independent=True, hash_ok=True):
    root, art = tmp_path / "ds", tmp_path / "art"
    root.mkdir()
    art.mkdir()
    payload = json.dumps({"scenarios": [{"scenario_id": "H1", "split": "held_out"}]}).encode()
    (root / reg.HELD_FILE).write_bytes(payload)
    digest = reg.hashlib.sha256(payload).hexdigest()
    (root / "heldout_status.json").write_text(json.dumps({"heldout_status": status,
                                                          "sha256": digest if hash_ok else "0" * 64}))
    (root / "independence_report.json").write_text(json.dumps({"ok": independent}))
    if freeze:
        (art / "freeze.json").write_text(json.dumps({"files": {}}))
    return root, art


def _guard(active=True):
    g = HeldOutGuard()
    if active:
        g.allow_oracle("T")
        g.activate_token("T")
    return g


def test_heldout_without_guard_or_token_is_refused(tmp_path):
    root, art = _fake_heldout(tmp_path)
    with pytest.raises(HeldOutLeakageError):
        reg.load_v2("held_out", purpose="final", guard=None, root=root, art_dir=art)
    with pytest.raises(HeldOutLeakageError):
        reg.load_v2("held_out", purpose="final", guard=_guard(active=False), root=root, art_dir=art)
    assert not (art / "heldout_opened.json").exists()


def test_heldout_requires_final_purpose(tmp_path):
    root, art = _fake_heldout(tmp_path)
    with pytest.raises(reg.V2IntegrityError):
        reg.load_v2("held_out", purpose="selection", guard=_guard(), root=root, art_dir=art)


@pytest.mark.parametrize("kw,msg", [({"status": "CANDIDATE"}, "FINAL_FROZEN"), ({"freeze": False}, "freeze"),
                                    ({"independent": False}, "independence"), ({"hash_ok": False}, "hash")])
def test_heldout_fails_closed_when_any_precondition_is_missing(tmp_path, kw, msg):
    root, art = _fake_heldout(tmp_path, **kw)
    with pytest.raises(reg.V2IntegrityError, match=msg):
        reg.load_v2("held_out", purpose="final", guard=_guard(), root=root, art_dir=art)
    assert not (art / "heldout_opened.json").exists()


def test_heldout_freeze_with_modified_source_is_refused(tmp_path):
    root, art = _fake_heldout(tmp_path)
    (art / "freeze.json").write_text(json.dumps({"files": {"src/rift/evaluation/rift_v2.py": "0" * 64}}))
    with pytest.raises(reg.V2IntegrityError, match="changed after freeze"):
        reg.load_v2("held_out", purpose="final", guard=_guard(), root=root, art_dir=art)


def test_heldout_is_one_time_and_reopen_is_stamped_invalid(tmp_path):
    root, art = _fake_heldout(tmp_path)
    first = reg.load_v2("held_out", purpose="final", guard=_guard(), root=root, art_dir=art)
    assert first.valid_for_final_claims is True and (art / "heldout_opened.json").exists()
    with pytest.raises(reg.V2IntegrityError, match="already been opened"):
        reg.load_v2("held_out", purpose="final", guard=_guard(), root=root, art_dir=art)
    again = reg.load_v2("held_out", purpose="final", guard=_guard(), root=root, art_dir=art, allow_reopen=True)
    assert again.valid_for_final_claims is False


def test_real_heldout_is_currently_not_loadable_before_freeze_or_it_was_opened_exactly_once():
    status = json.loads((reg.STATUS_FILE).read_text())["heldout_status"]
    if status == "CANDIDATE":
        with pytest.raises((reg.V2IntegrityError, HeldOutLeakageError)):
            reg.load_v2("held_out", purpose="final", guard=_guard())
        assert not reg.OPENED_FILE.exists()


def test_dev_and_val_are_pinned_and_tamper_is_detected(tmp_path):
    for s in ("dev", "val"):
        assert len(reg.load_v2(s).scenarios) == reg.PINS[s]["n"]
    (tmp_path / "dev.json").write_bytes((reg.V2_DIR / "dev.json").read_bytes() + b" ")
    with pytest.raises(reg.V2IntegrityError):
        reg.load_v2("dev", root=tmp_path)


def test_heldout_literal_not_hardcoded_in_v2_sources():
    needle = '"held_out_' + 'test.json"'
    for f in (ROOT / "src" / "rift" / "evaluation").glob("*.py"):
        assert needle not in f.read_text(), f.name


# =================================================================== metric denominators / abstention accounting
def _sc(sid, outcome, roots, distractors=()):
    return {"scenario_id": sid, "split": "dev", "ground_truth": {"expected_outcome": outcome, "roots": list(roots),
            "distractors": list(distractors)}, "dimensions": {"family": "f"}}


def _rec(abstained, top=(), reason=None):
    return {"abstained": abstained, "reason": reason, "top": list(top), "ed_s": 0.0, "n_do": 0,
            "evidence_type": "OBSERVATIONAL", "path_kind": "NONE", "cid_grades": [], "ident_status": None,
            "detect_latency_s": None, "runtime_s": 0.01, "mem_kb": 0.0, "error": None}


CASES = [  # (scenario, record)
    (_sc("a", "ATTRIBUTE", ["r"]), _rec(False, [("r", .9)])),                         # correct
    (_sc("b", "ATTRIBUTE", ["r"]), _rec(False, [("x", .9)])),                         # wrong root -> unsafe
    (_sc("c", "ATTRIBUTE", ["r"]), _rec(True, reason="NOT_IDENTIFIABLE")),            # lost coverage
    (_sc("d", "ABSTAIN_REQUIRED", []), _rec(True, reason="NO_CANDIDATES")),           # correct abstention
    (_sc("e", "ABSTAIN_REQUIRED", ["r"]), _rec(False, [("r", .5)])),                  # right name, but must abstain
    (_sc("f", "ABSTAIN_REQUIRED", []), _rec(False, [("q", .5)])),                     # unsafe
]


def _agg():
    scores = [bm.score_one(s, r) for s, r in CASES]
    return scores, bm.aggregate(scores, [r for _, r in CASES])


def test_score_one_semantics_for_every_case():
    scores, _ = _agg()
    s = {x["scenario_id"]: x for x in scores}
    assert (s["a"]["correct"], s["a"]["unsafe"], s["a"]["p2"]) == (True, False, True)
    assert (s["b"]["correct"], s["b"]["unsafe"], s["b"]["p2"], s["b"]["wrong_root"]) == (False, True, False, True)
    assert (s["c"]["answered"], s["c"]["unsafe"], s["c"]["p2"]) == (False, False, False)
    assert (s["d"]["unsafe"], s["d"]["p2"]) == (False, True)
    assert (s["e"]["correct"], s["e"]["unsafe"], s["e"]["p2"]) == (False, True, False)   # naming the root is still unsafe
    assert (s["f"]["unsafe"], s["f"]["p2"]) == (True, False)


def test_aggregate_denominators_are_explicit_and_correct():
    _, a = _agg()
    assert (a["N"], a["N_attribute"], a["N_abstain_required"]) == (6, 3, 3)
    assert (a["P1_attribution_accuracy"]["k"], a["P1_attribution_accuracy"]["n"]) == (1, 3)      # abstention = miss
    assert (a["P2_outcome_correct"]["k"], a["P2_outcome_correct"]["n"]) == (2, 6)
    assert (a["P3_unsafe_attribution_overall"]["k"], a["P3_unsafe_attribution_overall"]["n"]) == (3, 6)
    assert (a["unsafe_on_abstain_required"]["k"], a["unsafe_on_abstain_required"]["n"]) == (2, 3)
    assert (a["wrong_root_on_attribute"]["k"], a["wrong_root_on_attribute"]["n"]) == (1, 3)
    c = a["conditional_accuracy_on_answered_attribute"]
    assert (c["k"], c["n"]) == (1, 2)                    # conditional accuracy: denominator excludes the abstention
    assert (a["coverage_overall"]["k"], a["coverage_overall"]["n"]) == (4, 6)
    assert (a["coverage_on_attribute"]["k"], a["coverage_on_attribute"]["n"]) == (2, 3)
    assert (a["selective_risk"]["k"], a["selective_risk"]["n"]) == (3, 4)


def test_abstentions_are_counted_by_reason_and_never_dropped():
    scores, a = _agg()
    assert a["abstention_reasons"] == {"NOT_IDENTIFIABLE": 1, "NO_CANDIDATES": 1}
    assert a["abstention_rate"]["k"] == 2 and a["abstention_rate"]["n"] == 6
    assert a["lost_coverage_on_attribute"]["k"] == 1
    assert a["correct_abstention_rate_on_abstain_required"]["k"] == 1
    assert len(scores) == len(CASES)


def test_zero_unsafe_from_zero_coverage_is_visible_in_the_same_aggregate():
    cases = [(s, _rec(True, reason="NOT_IDENTIFIABLE")) for s, _ in CASES]
    scores = [bm.score_one(s, r) for s, r in cases]
    a = bm.aggregate(scores, [r for _, r in cases])
    assert a["P3_unsafe_attribution_overall"]["k"] == 0
    assert a["coverage_overall"]["k"] == 0 and a["P1_attribution_accuracy"]["k"] == 0
    assert a["selective_risk"]["value"] is None            # undefined, not 0 — never presented as an advantage
    assert a["conditional_accuracy_on_answered_attribute"]["value"] is None


def test_method_exception_becomes_a_counted_abstention(monkeypatch):
    sc = _dev(1)[0]
    L = bm._legacy()

    class Boom:
        def run(self, ctx):
            raise RuntimeError("x")
    monkeypatch.setitem(L, "B1", Boom)
    r = bm.run_methods(sc, methods=["B1-LATENCY-CORR"])["B1-LATENCY-CORR"]
    assert r["abstained"] and r["reason"] == "METHOD_ERROR:RuntimeError" and r["error"]
    s = bm.score_one(sc, r)
    assert s["answered"] is False
    assert bm.aggregate([s], [r])["method_errors"] == 1


def test_wilson_interval_properties():
    lo, hi = bm._wilson(0, 10)
    assert lo == 0.0 and 0.2 < hi < 0.4
    lo, hi = bm._wilson(5, 10)
    assert lo < 0.5 < hi
    assert all(np.isnan(x) for x in bm._wilson(0, 0))


def test_every_method_scores_identical_scenarios_in_identical_order():
    scs = _dev(3)
    recs = [bm.run_methods(s) for s in scs]
    for r in recs:
        assert set(r) == set(bm.method_ids())
    mids = list(recs[0])
    sc_by_m = {m: [bm.score_one(s, rr[m])["scenario_id"] for s, rr in zip(scs, recs)] for m in mids}
    assert len({tuple(v) for v in sc_by_m.values()}) == 1


# =================================================================== statistical grouping / tests
def test_mcnemar_exact_matches_binomial_and_handles_no_discordance():
    assert st.exact_mcnemar(0, 0) == 1.0
    assert st.exact_mcnemar(10, 0) == pytest.approx(2 * 0.5 ** 10)
    assert st.exact_mcnemar(3, 3) == pytest.approx(1.0)
    assert st.exact_mcnemar(8, 2) == pytest.approx(st.exact_mcnemar(2, 8))


def test_holm_is_monotone_and_bounded():
    adj = st.holm({"a": 0.001, "b": 0.01, "c": 0.04, "d": 0.5})
    assert adj["a"] == pytest.approx(0.004) and adj["b"] == pytest.approx(0.03)
    assert adj["c"] == pytest.approx(0.08) and adj["d"] == pytest.approx(0.5)
    assert all(0 <= v <= 1 for v in adj.values())


def test_clustered_bootstrap_resamples_clusters_not_rows():
    n_clusters, per = 6, 20
    a = np.array([1.0 if c % 2 == 0 else 0.0 for c in range(n_clusters) for _ in range(per)])
    b = np.zeros_like(a)
    clusters = [c for c in range(n_clusters) for _ in range(per)]
    by_cluster = st.clustered_bootstrap_diff(a, b, clusters, B=500)
    by_row = st.clustered_bootstrap_diff(a, b, list(range(len(a))), B=500)
    assert by_cluster["n_clusters"] == 6 and by_row["n_clusters"] == 120
    w_c = by_cluster["ci95"][1] - by_cluster["ci95"][0]
    w_r = by_row["ci95"][1] - by_row["ci95"][0]
    assert w_c > 2 * w_r, "treating correlated rows as independent must understate uncertainty"


def test_bootstrap_is_deterministic_given_seed():
    a, b = np.random.default_rng(1).integers(0, 2, 50), np.random.default_rng(2).integers(0, 2, 50)
    c = list(range(50))
    assert st.clustered_bootstrap_diff(a, b, c, B=300, seed=7) == st.clustered_bootstrap_diff(a, b, c, B=300, seed=7)


def test_permutation_test_detects_a_real_effect_and_not_a_null():
    assert st.sign_flip_permutation(np.ones(30)) < 0.001
    rng = np.random.default_rng(0)
    assert st.sign_flip_permutation(rng.choice([-1.0, 1.0], 200)) > 0.05
    assert st.sign_flip_permutation(np.zeros(10)) == 1.0


def test_compare_pair_requires_identical_scenarios_and_uses_attribute_subset_for_p1():
    scores, _ = _agg()
    swapped = list(reversed(scores))
    with pytest.raises(ValueError):
        st.compare_pair(scores, swapped, "P2")
    r = st.compare_pair(scores, scores, "P1")
    assert r["n"] == 3 and r["risk_difference"] == 0 and r["mcnemar_exact_p"] == 1.0
    assert st.compare_pair(scores, scores, "P2")["n"] == 6


def test_confirmatory_family_applies_holm_over_all_comparisons_and_requires_ci_excluding_zero():
    n = 60
    base = [{"scenario_id": f"s{i}", "expected": "ATTRIBUTE", "correct": i % 2 == 0, "p2": i % 2 == 0,
             "unsafe": i % 2 == 1} for i in range(n)]
    better = [dict(s, correct=True, p2=True, unsafe=False) for s in base]
    fam = st.confirmatory_family({"F": better, "B": base}, "F", ["B"])
    assert fam["family_size"] == 3
    for row in fam["rows"].values():
        assert row["holm_p_mcnemar"] >= row["mcnemar_exact_p"]
        assert row["significant_holm_0.05"] is True
    same = st.confirmatory_family({"F": base, "B": base}, "F", ["B"])
    assert not any(r["significant_holm_0.05"] for r in same["rows"].values())


def test_detection_metrics_denominators():
    det = [{"fault_present": True, "detected": True, "delay_s": 10.0}, {"fault_present": True, "detected": False,
           "delay_s": None}, {"fault_present": False, "detected": True, "delay_s": None},
           {"fault_present": False, "detected": False, "delay_s": None}]
    m = st.detection_metrics(det)
    assert (m["tp"], m["fn"], m["fp"], m["tn"]) == (1, 1, 1, 1)
    assert m["fpr"] == 0.5 and m["fnr"] == 0.5 and m["precision"] == 0.5 and m["delay_s"]["n"] == 1


def test_stage1_detector_uses_only_observed_data_and_reports_no_fault_scenarios():
    scs = [s for s in _dev() if not s["faults"]][:3]
    assert scs, "dataset must contain NO_FAULT scenarios"
    for s in scs:
        d = bm.stage1_detection(s)
        assert d["fault_present"] is False and d["delay_s"] is None
