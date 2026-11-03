"""Sprint 4.4.0 regression tests: PAG mark semantics, direction-aware attribution (RIFT-FULL-V3), leakage, held-out isolation,
V2 backward compatibility, adversarial counterexamples. All on SYNTHETIC scenarios; nothing here touches the held-out split."""
import copy
import json
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.rift.attribution_v3 import adversarial as adv  # noqa: E402
from src.rift.attribution_v3 import pag_semantics as ps  # noqa: E402
from src.rift.attribution_v3 import rift_v3  # noqa: E402
from src.rift.attribution_v3.rift_v3 import (DEFINITIVE, V3_CONFIGS, holm_reject, run_v3)  # noqa: E402
from src.rift.cid.cid import CIDGrade, compute_cid  # noqa: E402
from src.rift.evaluation import benchmark_v2 as bm  # noqa: E402
from src.rift.evaluation import rift_v2 as r2  # noqa: E402
from src.rift.evaluation.dataset_registry_v2 import PINS, load_v2, verify_freeze  # noqa: E402
from src.rift.fci.fci_runner import PAGEdgeType, _decode_pag_edges  # noqa: E402
from src.rift.scenarios import simulator as sim  # noqa: E402

TARGET_FILES = [ROOT / "src/rift/attribution_v3" / f for f in ("pag_semantics.py", "rift_v3.py", "diagnostics.py", "adversarial.py")]
TARGET_FILES += [ROOT / "scripts" / f for f in ("sprint440_trace_failures.py", "sprint440_run_v3.py", "sprint440_analyze.py",
                                                  "sprint440_adversarial.py")]


def run_on(sc, cfg="V3-FULL"):
    o = sim.observe(sc)
    return run_v3(o, lambda x, ys, s: sim.intervene(sc, x, ys, s), sc["scenario_id"], int(sc["seed"]), V3_CONFIGS[cfg],
                  cache=r2.SharedCache())


@pytest.fixture(scope="module")
def adv_by_type():
    out = {}
    for t in adv.ATTACKS:
        out[t] = [adv.build(t, k) for k in range(3)]
    return out


# ------------------------------------------------------------------------------------ PAG semantics
def M(vars_, entries):
    n = len(vars_)
    m = np.zeros((n, n), dtype=int)
    for (a, b), (ma, mb) in entries.items():
        i, j = vars_.index(a), vars_.index(b)
        m[i][j], m[j][i] = ma, mb
    return m


def test_mark_convention_matches_causal_learn_on_a_collider():
    """X -> Z <- Y: causal-learn returns M[X][Z]=2 (circle at X), M[Z][X]=1 (arrowhead at Z), i.e. X o-> Z.
    The frozen decoder (Sprint 4.3.0) reports this as UNDIRECTED; the corrected decoder reports o->. DEFECT D1."""
    from src.rift.fci.fci_runner import run_fci
    rng = np.random.default_rng(1)
    n = 800
    X, Y = rng.normal(size=n), rng.normal(size=n)
    Z = X + Y + 0.5 * rng.normal(size=n)
    pag = run_fci(pd.DataFrame({"X": X, "Y": Y, "Z": Z}), seed=1)
    vs = pag.variables
    assert pag.adjacency_matrix[vs.index("X")][vs.index("Z")] == 2 and pag.adjacency_matrix[vs.index("Z")][vs.index("X")] == 1
    assert all(e.edge_type == PAGEdgeType.UNDIRECTED for e in pag.edges)          # frozen decoder: information lost
    mp = ps.decode_marks(vs, pag.adjacency_matrix)
    assert mp.kind("X", "Z") == "xo->y" and mp.kind("Y", "Z") == "xo->y"
    # Z cannot be an ancestor of X or Y (arrowhead at X/Y end?? no: arrowhead is at Z) -> X,Y are possible ancestors of Z only
    assert ps.classify_relation(mp, "X", "Z") == ps.POSSIBLE_ANCESTOR
    assert ps.classify_relation(mp, "Z", "X") == ps.SEMI_DIRECTED_CONNECTION or ps.classify_relation(mp, "Z", "X") == ps.OBSERVATIONAL_ASSOCIATION
    # and the frozen reachability graph (bidirectional for UNDIRECTED) would have wrongly allowed Z -> X
    from src.rift.ebd.ebd import _pag_to_digraph
    assert _pag_to_digraph(pag).has_edge("Z", "X")


def test_hierarchy_directed_possible_semidirected_none():
    vs = ["a", "b", "c", "d", "e"]
    mp = ps.decode_marks(vs, M(vs, {("a", "b"): (-1, 1), ("b", "c"): (2, 1), ("d", "e"): (1, 1)}))
    assert ps.classify_relation(mp, "a", "b") == ps.DIRECTED_ANCESTOR
    assert ps.classify_relation(mp, "a", "c") == ps.POSSIBLE_ANCESTOR            # a -> b o-> c : possible, NOT established
    assert ps.classify_relation(mp, "b", "a") != ps.POSSIBLE_ANCESTOR            # tail->arrow cannot be traversed backwards
    assert ps.classify_relation(mp, "a", "e") == ps.NO_SUPPORTED_RELATIONSHIP
    assert ps.classify_relation(mp, "d", "e") == ps.SEMI_DIRECTED_CONNECTION     # bidirected: association only, never ancestry
    assert ps.classify_relation(mp, "e", "d") == ps.SEMI_DIRECTED_CONNECTION


def test_circle_edges_are_possible_not_directed_ancestry():
    vs = ["a", "b"]
    mp = ps.decode_marks(vs, M(vs, {("a", "b"): (2, 2)}))
    assert ps.classify_relation(mp, "a", "b") == ps.POSSIBLE_ANCESTOR
    assert ps.classify_relation(mp, "b", "a") == ps.POSSIBLE_ANCESTOR           # symmetric -> carries no direction information
    assert ps.directed_descendants(mp, "a") == set()


def test_wrong_orientation_is_visible_in_marks():
    vs = ["root", "child"]
    wrong = ps.from_true_dag(vs, [("child", "root")])                            # reversed orientation
    assert ps.classify_relation(wrong, "root", "child") != ps.DIRECTED_ANCESTOR
    assert ps.classify_relation(wrong, "child", "root") == ps.DIRECTED_ANCESTOR  # a confidently WRONG graph is still labelled so
    # => V3 never lets the graph alone select a root (see test_graph_not_used_as_causal_evidence)


def test_to_pag_result_roundtrip_types():
    vs = ["a", "b", "c", "d"]
    mp = ps.decode_marks(vs, M(vs, {("a", "b"): (-1, 1), ("b", "c"): (2, 1), ("c", "d"): (2, 2)}))
    pr = ps.to_pag_result(mp, type("T", (), dict(variables=vs, adjacency_matrix=None, alpha=0.05, n_samples_used=0, n_variables=4))())
    kinds = {(e.source, e.target): e.edge_type for e in pr.edges}
    assert kinds[("a", "b")] == PAGEdgeType.DIRECTED and kinds[("b", "c")] == PAGEdgeType.PARTIALLY_DIRECTED
    assert kinds[("c", "d")] == PAGEdgeType.UNDIRECTED


# ------------------------------------------------------------------------------- adversarial V3 behaviour
def test_downstream_with_largest_anomaly_is_not_named(adv_by_type):
    for sc in adv_by_type["A01_DOWNSTREAM_LARGEST"] + adv_by_type["A02_ROOT_SMALLER_ANOMALY"]:
        out = run_on(sc)
        assert not out.abstained and out.top_candidates[0][0] in sc["ground_truth"]["roots"]


def test_delayed_propagation_not_misattributed(adv_by_type):
    for sc in adv_by_type["A03_DELAYED_PROPAGATION"]:
        out = run_on(sc)
        assert out.abstained or out.top_candidates[0][0] in sc["ground_truth"]["roots"]


def test_mutual_dependency_abstains(adv_by_type):
    for sc in adv_by_type["A13_NO_IDENTIFIABLE_ORIGIN"]:
        assert sc["ground_truth"]["expected_outcome"] == "ABSTAIN_REQUIRED"
        out = run_on(sc)
        assert out.abstained
    # ablation shows why: without the symmetry check V3 can still answer on some mutual-dependency scenarios (documented limitation)


def test_strong_anomaly_from_hidden_common_cause_abstains(adv_by_type):
    for sc in adv_by_type["A14_STRONG_ANOMALIES_ABSTAIN"]:
        assert run_on(sc).abstained


def test_insufficient_samples_abstains(adv_by_type):
    for sc in adv_by_type["A09_INSUFFICIENT_SAMPLES"]:
        out = run_on(sc)
        assert out.abstained


def test_weak_intervention_abstains_not_guesses(adv_by_type):
    for sc in adv_by_type["A07_WEAK_INTERVENTION"]:
        out = run_on(sc)
        assert out.abstained and out.abstention_reason in ("INTERVENTION_UNINFORMATIVE", "INTERVENTION_NOT_VERIFIED",
                                                           "AMBIGUOUS_ATTRIBUTION", "UNRESOLVED_EARLIER_DIVERGENCE")


def test_multi_service_intervention_collateral_never_wrong_root(adv_by_type):
    for sc in adv_by_type["A08_MULTI_SERVICE_INTERVENTION"] + adv_by_type["A05_COMMON_CAUSE_CONFOUNDING"]:
        out = run_on(sc)
        assert out.abstained or out.top_candidates[0][0] in sc["ground_truth"]["roots"]


def test_isolated_root_in_learned_graph_still_a_candidate(adv_by_type):
    """V2's R3 filter cannot even consider a root that FCI isolated; V3 intervenes on every divergent service."""
    for sc in adv_by_type["A11_ISOLATED_ROOT_HARD_FOR_FCI"]:
        o = sim.observe(sc)
        cache = r2.SharedCache()
        out = run_v3(o, lambda x, ys, s: sim.intervene(sc, x, ys, s), sc["scenario_id"], int(sc["seed"]), cache=cache)
        tag, pag = cache.pag["fci"]
        if tag == "OK":
            r = sc["ground_truth"]["roots"][0]
            if not any(r in (e.source, e.target) for e in pag.edges):
                assert r in out.raw_output["candidates"]
        assert out.abstained or out.top_candidates[0][0] in sc["ground_truth"]["roots"]


def test_unobserved_root_cannot_be_distinguished_is_documented_limitation(adv_by_type):
    """A12: the root is not in the telemetry. A descendant that is an interventional source among OBSERVED services is
    indistinguishable from a root. This test pins the CURRENT behaviour so a future change cannot silently claim otherwise."""
    unsafe = sum(not run_on(sc).abstained for sc in adv_by_type["A12_MISSING_TELEMETRY_ON_ROOT"])
    assert unsafe >= 1


def test_v3_not_worse_than_v2_on_adversarial_unsafe(adv_by_type):
    u2 = u3 = 0
    for t, scs in adv_by_type.items():
        for sc in scs:
            o = sim.observe(sc)
            iv = lambda x, ys, s, sc=sc: sim.intervene(sc, x, ys, s)  # noqa: E731
            a = r2.run_v2(o, iv, sc["scenario_id"], int(sc["seed"]), r2.CONFIGS["A1-FULL"], cache=r2.SharedCache())
            b = run_v3(o, iv, sc["scenario_id"], int(sc["seed"]), cache=r2.SharedCache())
            u2 += bm.score_one(sc, bm._out_to_rec(a, 0, 0))["unsafe"]
            u3 += bm.score_one(sc, bm._out_to_rec(b, 0, 0))["unsafe"]
    assert u3 <= u2


# ------------------------------------------------------------------------------------ evidence handling
def test_graph_not_used_as_causal_evidence():
    """Replacing the PAG with a confidently reversed oracle must not change which service V3 names (graph = diagnostics only)."""
    sc = adv.build("A01_DOWNSTREAM_LARGEST", 0)
    o = sim.observe(sc)
    iv = lambda x, ys, s: sim.intervene(sc, x, ys, s)  # noqa: E731
    vs = sorted(sim.observed_services(sc))
    rev = ps.from_true_dag(vs, [(e["dst"], e["src"]) for e in sc["graph"]["edges"] if e["src"] in vs and e["dst"] in vs])
    base = run_v3(o, iv, sc["scenario_id"], int(sc["seed"]), cache=r2.SharedCache())
    flip = run_v3(o, iv, sc["scenario_id"], int(sc["seed"]), cache=r2.SharedCache(), pag_override=rev)
    assert base.top_candidates[0][0] == flip.top_candidates[0][0] == sc["ground_truth"]["roots"][0]
    assert "PAG_CONTRADICTS_INTERVENTION" in flip.raw_output["caveats"]            # contradiction surfaced, status downgraded
    assert flip.raw_output["status"] != DEFINITIVE and base.raw_output["status"] in (DEFINITIVE, rift_v3.QUALIFIED)


def test_path_kind_is_never_directed_from_circle_edges():
    sc = adv.build("A01_DOWNSTREAM_LARGEST", 1)
    vs = sorted(sim.observed_services(sc))
    circle = ps.decode_marks(vs, M(vs, {(a, b): (2, 2) for i, a in enumerate(vs) for b in vs[i + 1:]}))
    o = sim.observe(sc)
    r = run_v3(o, lambda x, ys, s: sim.intervene(sc, x, ys, s), sc["scenario_id"], int(sc["seed"]), cache=r2.SharedCache(),
               pag_override=circle)
    assert r.raw_output["path_kind"] == "SEMI_DIRECTED"


def test_cid_grade_tops_out_at_candidate_for_30_sample_window():
    rng = np.random.default_rng(0)
    c = compute_cid(rng.normal(0, 1, 30), rng.normal(3, 1, 30), "x", "y", 0.0, n_bootstrap=5, n_permutations=200, seed=1)
    assert c.grade == CIDGrade.CANDIDATE and c.permutation_significant


def test_holm_is_at_least_as_powerful_as_bonferroni_and_controls_fwer_shape():
    p = {"a": 0.01, "b": 0.02, "c": 0.04}
    assert holm_reject(p, 0.05) >= {k for k, v in p.items() if v < 0.05 / 3}
    assert holm_reject({"a": 0.2, "b": 0.3}, 0.05) == set()


def test_manipulation_check_blocks_uninformative_interventions(adv_by_type):
    """Positive control failure => intervention is 'unresolved', never evidence of absence."""
    sc = adv_by_type["A07_WEAK_INTERVENTION"][0]
    out = run_on(sc)
    assert out.abstained
    assert not any(out.raw_output.get("manipulation_check", {}).values()) or out.abstention_reason != "AMBIGUOUS_ATTRIBUTION"


# ------------------------------------------------------------------------------------- ground-truth leakage
def test_v3_output_independent_of_ground_truth_and_labels():
    sc = adv.build("A01_DOWNSTREAM_LARGEST", 2)
    a = run_on(sc)
    sc2 = copy.deepcopy(sc)
    sc2["ground_truth"] = {"roots": ["WRONG"], "expected_outcome": "ABSTAIN_REQUIRED", "abstain_reason": "X", "unobserved_roots": [],
                           "distractors": [], "identifiability": "X", "identifiable_by": []}
    sc2["design"] = {"onset_window": 0, "distractors": ["WRONG"], "true_roots": ["WRONG"]}
    sc2["dimensions"] = {k: "LEAK" for k in sc2["dimensions"]}
    b = run_on(sc2)
    assert (a.abstained, a.top_candidates, a.abstention_reason) == (b.abstained, b.top_candidates, b.abstention_reason)


def test_v3_source_does_not_reference_ground_truth():
    src = (ROOT / "src/rift/attribution_v3/rift_v3.py").read_text()
    code = re.sub(r'""".*?"""', "", src, flags=re.S)
    for tok in ("ground_truth", "true_roots", "design", "expected_outcome", "heldout", "held_out"):
        assert tok not in code, tok


def test_run_v3_signature_has_no_scenario_argument():
    import inspect
    params = set(inspect.signature(run_v3).parameters)
    assert params == {"obs", "intervene_fn", "fault_id", "scenario_seed", "cfg", "cache", "pag_override"}


# ---------------------------------------------------------------------------------------- held-out isolation
def test_new_sprint440_code_never_references_heldout_data():
    heldname = "heldout" + "_" + "candidate"
    for f in TARGET_FILES:
        txt = f.read_text()
        assert heldname not in txt, f
        assert not re.search(r"load_v2\(\s*['\"]held_out", txt), f
        assert "purpose=\"final\"" not in txt and "purpose='final'" not in txt


def test_runner_refuses_non_dev_val_splits():
    txt = (ROOT / "scripts/sprint440_run_v3.py").read_text()
    assert 'split not in ("dev", "val")' in txt


def test_dev_val_pins_and_freeze_intact():
    for k in ("dev", "val"):
        assert load_v2(k).sha256 == PINS[k]["sha256"]
    assert verify_freeze()[0] is True


def test_adversarial_set_is_separate_and_labelled():
    scs = [adv.build(t, 0) for t in adv.ATTACKS]
    assert len(scs) == 14 and all(s["split"] == "adv_dev" for s in scs)
    assert len({s["scenario_id"] for s in scs}) == 14
    dev_ids = {s["scenario_id"] for s in load_v2("dev").scenarios}
    assert not dev_ids & {s["scenario_id"] for s in scs}


def test_adversarial_labels_come_from_simulator_not_methods():
    s = adv.build("A13_NO_IDENTIFIABLE_ORIGIN", 0)
    assert s["ground_truth"]["expected_outcome"] == "ABSTAIN_REQUIRED" and s["ground_truth"]["abstain_reason"] == "SYMMETRIC_MUTUAL_DEPENDENCY"
    s = adv.build("A12_MISSING_TELEMETRY_ON_ROOT", 0)
    assert s["ground_truth"]["abstain_reason"] == "ROOT_UNOBSERVED"
    s = adv.build("A01_DOWNSTREAM_LARGEST", 0)
    assert s["ground_truth"]["expected_outcome"] == "ATTRIBUTE"


# ---------------------------------------------------------------------------------- V2 backward compatibility
def test_v2_configs_and_registry_unchanged():
    assert list(r2.CONFIGS) == ["A1-FULL", "A2-NO-FCI", "A3-NO-EBD", "A4-NO-CID", "A5-NO-IDENT", "A6-NO-INTERVENTION",
                                "A7-NO-MSIS", "A8-OBSERVATIONAL-ONLY", "A9-ORACLE-GRAPH", "A10-RANDOM-INTERVENTION"]
    assert r2.CONFIGS["A1-FULL"].name == "RIFT-FULL-V2" and r2.CONFIGS["A1-FULL"].graph == "fci"
    assert "RIFT-FULL-V3" not in bm.method_ids()


@pytest.mark.parametrize("split,sid", [("dev", "V2D-0001"), ("dev", "V2D-0015"), ("val", "V2V-0001")])
def test_v2_reproduces_saved_sprint430_outputs(split, sid):
    saved = {p["scenario_id"]: p for p in json.loads((ROOT / "artifacts/sprint4_3_0/results" / split / "per_scenario.json").read_text())}
    sc = next(s for s in load_v2(split).scenarios if s["scenario_id"] == sid)
    o = sim.observe(sc)
    out = r2.run_v2(o, lambda x, ys, s: sim.intervene(sc, x, ys, s), sid, int(sc["seed"]), r2.CONFIGS["A1-FULL"], cache=r2.SharedCache())
    rec = bm._out_to_rec(out, 0, 0)
    ref = saved[sid]["methods"]["RIFT-FULL-V2"]["record"]
    assert (rec["abstained"], rec["reason"], rec["top"]) == (ref["abstained"], ref["reason"], [tuple(t) for t in ref["top"]])


def test_v3_deterministic():
    sc = adv.build("A06_MULTIPLE_POSSIBLE_ROOTS", 0)
    a, b = run_on(sc), run_on(sc)
    assert a.top_candidates == b.top_candidates and a.abstention_reason == b.abstention_reason


def test_historical_stage4_artifact_untouched():
    import hashlib
    h = hashlib.sha256((ROOT / "artifacts/stage4_intervention_results.json").read_bytes()).hexdigest()
    assert h == "e4cf1391c83bcb33070e8bc4ae3f8b792df2e0d1970df14524fc6c8d5d1dcffe"
