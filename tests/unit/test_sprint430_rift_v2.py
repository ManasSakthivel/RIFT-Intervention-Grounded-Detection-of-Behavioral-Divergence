"""Sprint 4.3.0 — adversarial regression tests for RIFT-FULL-V2 (EBD / attribution / abstention).

All scenarios come from the pinned DEV split (never held-out). Expected behaviours are properties of the method
specification (Protocol v2 §5.1, Amendment 3), not tuned numbers.
"""
import dataclasses
import sys
import warnings
from pathlib import Path

import pytest

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.rift.evaluation import benchmark_v2 as bm  # noqa: E402
from src.rift.evaluation import rift_v2 as r2  # noqa: E402
from src.rift.evaluation.dataset_registry_v2 import load_v2  # noqa: E402
from src.rift.scenarios import simulator as sim  # noqa: E402

DEV = {s["scenario_id"]: s for s in load_v2("dev").scenarios}


def run(sid, cfg_key="A1-FULL", cfg=None):
    sc = DEV[sid]
    o = sim.observe(sc)
    cfg = cfg or {**r2.CONFIGS, **r2.EXPLORATORY_CONFIGS}[cfg_key]
    return sc, r2.run_v2(o, lambda x, ys, s: sim.intervene(sc, x, ys, s), sid, int(sc["seed"]), cfg)


def test_registered_configs_are_the_ten_preregistered_ablations_plus_one_labelled_exploratory_variant():
    assert list(r2.CONFIGS) == ["A1-FULL", "A2-NO-FCI", "A3-NO-EBD", "A4-NO-CID", "A5-NO-IDENT",
                                "A6-NO-INTERVENTION", "A7-NO-MSIS", "A8-OBSERVATIONAL-ONLY", "A9-ORACLE-GRAPH",
                                "A10-RANDOM-INTERVENTION"]
    assert list(r2.EXPLORATORY_CONFIGS) == ["V2G-EARLIER-GUARD"]
    assert r2.CONFIGS["A1-FULL"].earlier_guard is False       # confirmatory method is NOT modified by Amendment 3
    spec = {m.method_id: m for m in bm.REGISTRY}
    assert not spec["RIFT-FULL-V2G"].confirmatory and "EXPLORATORY" in spec["RIFT-FULL-V2G"].source


def test_confirmatory_method_unchanged_by_the_guard_addition():
    cfg = r2.CONFIGS["A1-FULL"]
    assert (cfg.graph, cfg.use_ebd, cfg.use_identifiability, cfg.use_interventions, cfg.cid_mode, cfg.order) == \
        ("fci", True, True, True, "cid", "msis")


def test_observational_variants_never_claim_interventional_evidence():
    for sid in list(DEV)[:25]:
        for key in ("A6-NO-INTERVENTION", "A8-OBSERVATIONAL-ONLY"):
            _, out = run(sid, key)
            assert out.raw_output["evidence_type"] == "OBSERVATIONAL"
            assert out.total_intervention_ed_s == 0.0 and out.raw_output["n_do"] == 0


def test_interventional_evidence_is_claimed_only_when_a_perturbation_confirmed_the_effect():
    seen_int = 0
    for sid in list(DEV)[:40]:
        _, out = run(sid)
        raw = out.raw_output
        if raw["evidence_type"] == "INTERVENTIONAL":
            seen_int += 1
            assert raw["confirmed"] and raw["n_do"] >= 1 and not out.abstained
        if not out.abstained:
            assert raw["evidence_type"] == "INTERVENTIONAL"
            assert raw["n_do"] >= 1 and out.total_intervention_ed_s == 30.0 * raw["n_do"]
        if out.abstained and out.abstention_reason == "INTERVENTION_NOT_VERIFIED":
            assert raw["confirmed"] == {}
    assert seen_int > 0


def test_semi_directed_reachability_is_reported_with_lower_confidence_never_upgraded_to_directed():
    n_semi = 0
    for sid in list(DEV):
        _, out = run(sid)
        if out.abstained:
            continue
        top_conf = out.top_candidates[0][1]
        kind = out.raw_output["path_kind"]
        assert kind in ("DIRECTED", "SEMI_DIRECTED", "NONE")
        if kind == "SEMI_DIRECTED":
            n_semi += 1
            assert top_conf == 0.80
        elif kind == "DIRECTED":
            assert top_conf == 0.95
        assert top_conf < 1.0                  # never certainty
    assert n_semi > 0, "dev contains semi-directed attributions; the distinction must be exercised"


def test_call_graph_substitute_is_not_labelled_as_fci_output():
    sc = DEV["V2D-0044"]
    pag = r2._callgraph_pag(sim.observe(sc)["call_graph"])
    assert "ablation A2" in pag.notes and "no conditional-independence" in pag.notes


# ---- Amendment 3 (EXPLORATORY): earlier unexplained divergence => abstain
GUARD_CASES = ["V2D-0015", "V2D-0021", "V2D-0044"]     # dev ATTRIBUTE scenarios where V2 names a descendant


@pytest.mark.parametrize("sid", GUARD_CASES)
def test_v2_names_a_late_descendant_while_the_guard_variant_abstains_instead(sid):
    sc, base = run(sid, "A1-FULL")
    assert not base.abstained and base.top_candidates[0][0] not in sc["ground_truth"]["roots"]
    _, g = run(sid, "V2G-EARLIER-GUARD")
    assert g.abstained and g.abstention_reason == "UNRESOLVED_EARLIER_DIVERGENCE"
    assert g.raw_output["unresolved_earlier"], "the unexplained earlier services must be listed"
    assert g.top_candidates == []


def test_guard_never_turns_an_abstention_into_an_answer_and_never_changes_a_kept_answer():
    changed = 0
    for sid in list(DEV)[:60]:
        _, base = run(sid, "A1-FULL")
        _, g = run(sid, "V2G-EARLIER-GUARD")
        if base.abstained:
            assert g.abstained and g.abstention_reason == base.abstention_reason
        elif not g.abstained:
            assert g.top_candidates == base.top_candidates
        else:
            changed += 1
    assert changed > 0


def test_guard_trades_coverage_for_safety_on_dev_and_does_not_improve_attribution_accuracy():
    """Recorded honestly: the guard reduces unsafe attributions and coverage; P1 does not rise."""
    scs = list(DEV.values())
    res = {}
    for key in ("A1-FULL", "V2G-EARLIER-GUARD"):
        recs = []
        for sc in scs:
            _, out = run(sc["scenario_id"], key)
            recs.append(bm.score_one(sc, bm._out_to_rec(out, 0.0, 0.0)))
        res[key] = (sum(r["unsafe"] for r in recs), sum(r["answered"] for r in recs),
                    sum(r["correct"] for r in recs))
    assert res["V2G-EARLIER-GUARD"][0] < res["A1-FULL"][0]          # fewer unsafe attributions
    assert res["V2G-EARLIER-GUARD"][1] < res["A1-FULL"][1]          # at the price of coverage
    assert res["V2G-EARLIER-GUARD"][2] <= res["A1-FULL"][2]         # no accuracy gain


# ---- abstention behaviour under missing telemetry / no fault
def test_insufficient_reference_data_abstains_instead_of_guessing():
    for sid, sc in DEV.items():
        o = sim.observe(sc)
        n_ok = sum(1 for df in o["metrics"].values() if int((df["time"] < 100).sum()) >= 8)
        if n_ok < 2:
            _, out = run(sid)
            assert out.abstained and out.abstention_reason == "INSUFFICIENT_BASELINE"
            assert out.top_candidates == []


def test_no_fault_scenarios_never_yield_interventional_attribution_without_confirmed_effect():
    for sc in DEV.values():
        if sc["faults"]:
            continue
        _, out = run(sc["scenario_id"])
        if not out.abstained:
            assert out.raw_output["confirmed"], "an answer without a confirmed intervention effect is a defect"
