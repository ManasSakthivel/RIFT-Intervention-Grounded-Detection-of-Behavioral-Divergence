#!/usr/bin/env python3
"""Failure-taxonomy evidence for Sprint 4.3.0 (POST-HOC, descriptive; nothing here feeds back into any method).

    python3 scripts/sprint430_failure_analysis.py

* held_out : uses ONLY saved results (per_scenario.json) + the already-opened scenario file. NO method is executed.
* dev, val : additionally re-runs RIFT-FULL-V2 (A1, unchanged) to expose EBD internals (R1/R3 status of the true root,
             PAG adjacency of the true root) for the wrong-root answers. These splits are legitimate development data.
Writes artifacts/sprint4_3_0/failure_taxonomy_evidence.json
"""
from __future__ import annotations

import json
import sys
import warnings
from collections import Counter
from pathlib import Path

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO), str(REPO / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import networkx as nx  # noqa: E402

from src.rift.evaluation import benchmark_v2 as bm  # noqa: E402
from src.rift.evaluation import rift_v2 as r2  # noqa: E402
from src.rift.evaluation.dataset_registry_v2 import ART_DIR, HELD_FILE, V2_DIR, load_v2  # noqa: E402
from src.rift.ebd.ebd import compute_ebd  # noqa: E402
from src.rift.scenarios import simulator as sim  # noqa: E402

FOCAL = "RIFT-FULL-V2"
D = lambda sc, k: sc["dimensions"].get(k)  # noqa: E731

CATEGORIES = {
    "C01_downstream_misattribution": None,   # handled separately (defined on outputs, not on scenario attributes)
    "C02_earliest_divergence_ambiguity": lambda s: D(s, "negative") in ("earliest_not_root", "indistinguishable_onsets",
                                                                       "coincidental_anomaly"),
    "C05_non_identifiable": lambda s: s["ground_truth"]["abstain_reason"] in ("SYMMETRIC_MUTUAL_DEPENDENCY",
                                                                             "NO_DISCRIMINATING_EVIDENCE")
    or D(s, "negative") == "root_not_identifiable",
    "C06_confounding": lambda s: D(s, "structure") in ("confounding", "hidden_common_cause")
    or D(s, "negative") == "common_cause_several_services",
    "C07_multiple_simultaneous_causes": lambda s: len(s["faults"]) >= 2 or D(s, "structure") == "multiple_upstream"
    or D(s, "temporal") == "overlapping_faults",
    "C08_high_variance_service": lambda s: D(s, "workload") == "high_baseline_variance"
    or D(s, "negative") == "high_variance_no_fault",
    "C09_weak_intervention_effect": lambda s: D(s, "intervention") in ("no_meaningful_effect", "low_magnitude", "imperfect")
    or D(s, "observability") == "weak_interventional_evidence" or D(s, "negative") == "weak_intervention_effects",
    "C10_insufficient_telemetry": lambda s: D(s, "observability") in ("insufficient_samples", "missing_windows",
                                                                     "partial_service_observability")
    or D(s, "negative") == "insufficient_telemetry",
    "C11_recovery_anomaly": lambda s: D(s, "family") == "recovery_instability"
    or D(s, "temporal") in ("partial_recovery", "recovery_delay")
    or D(s, "negative") == "incomplete_recovery_after_normalisation",
    "C12_feedback_like_structure_unseen": lambda s: D(s, "structure") == "feedback_like",
}


def rate(k, n):
    lo, hi = bm._wilson(k, n)
    return {"k": k, "n": n, "value": (k / n) if n else None, "wilson95": [lo, hi]}


def subset(rows):
    attr = [r for r in rows if r["expected"] == "ATTRIBUTE"]
    ans = [r for r in rows if r["answered"]]
    return {"n": len(rows), "n_attribute": len(attr), "n_abstain_required": len(rows) - len(attr),
            "P1": rate(sum(r["correct"] for r in attr), len(attr)), "P2": rate(sum(r["p2"] for r in rows), len(rows)),
            "unsafe": rate(sum(r["unsafe"] for r in rows), len(rows)), "coverage": rate(len(ans), len(rows)),
            "wrong_root": sum(r["wrong_root"] for r in rows),
            "unsafe_on_abstain_required": sum(r["unsafe"] for r in rows if r["expected"] == "ABSTAIN_REQUIRED"),
            "lost_coverage_on_attribute": sum(1 for r in attr if not r["answered"])}


def load_split(split):
    per = json.loads((ART_DIR / "results" / split / "per_scenario.json").read_text())
    if split == "held_out":
        assert (ART_DIR / "heldout_opened.json").is_file()
        scs = {s["scenario_id"]: s for s in json.loads((V2_DIR / HELD_FILE).read_bytes())["scenarios"]}
    else:
        scs = {s["scenario_id"]: s for s in load_v2(split).scenarios}
    return per, scs


def downstream_relation(sc, top):
    g = nx.DiGraph([(e["src"], e["dst"]) for e in sc["graph"]["edges"]])
    roots = sc["ground_truth"]["roots"]
    if any(r in g and top in nx.descendants(g, r) for r in roots):
        return "downstream_of_true_root"
    if any(f["service"] == top for f in sc["faults"]):
        return "other_faulted_service"
    return "unrelated"


def mechanisms(sc):
    """Re-run RIFT-FULL-V2 (A1, unchanged) on a DEV/VAL scenario to expose why a wrong root was named."""
    o = sim.observe(sc)
    cache = r2.SharedCache()
    out = r2.run_v2(o, lambda x, ys, s: sim.intervene(sc, x, ys, s), sc["scenario_id"], int(sc["seed"]),
                    r2.CONFIGS["A1-FULL"], cache=cache)
    tag, pag = cache.pag["fci"]
    usable = {s: df for s, df in o["metrics"].items() if s in o["baseline_stats"]}
    ebd = {e.service_id: e for e in compute_ebd(metrics=usable, baselines=o["baseline_stats"], pag_result=pag,
                                                incident_window=o["incident_window"], delta_t=10.0, theta_detect=3.0,
                                                theta_persist=2, max_gap_windows=1)}
    top = out.top_candidates[0][0]
    roots = sc["ground_truth"]["roots"]
    r = next((x for x in roots if x in ebd), None)
    adj = bool(r) and any(r in (e.source, e.target) for e in pag.edges)
    if r is None:
        cls = "M1_true_root_not_diverging_or_not_observed"
    elif not ebd[r].r1_pass:
        cls = "M1_true_root_not_diverging_or_not_observed"
    elif not ebd[r].r3_pass:
        cls = "M2_true_root_diverges_but_fails_R3_no_PAG_path_to_a_diverging_service" + \
              ("" if adj else "_and_isolated_in_PAG")
    elif r in out.raw_output.get("intervened", []):
        cls = "M3_true_root_intervened_but_effect_not_confirmed"
    else:
        cls = "M4_true_root_candidate_never_intervened_or_explained_away"
    earlier = [s for s, e in ebd.items() if e.r1_pass and e.t_star < ebd[top].t_star and s != top]
    return {"scenario_id": sc["scenario_id"], "named": top, "true_roots": roots, "mechanism": cls,
            "true_root_t_star": (ebd[r].t_star if r else None), "named_t_star": ebd[top].t_star,
            "true_root_earlier_than_named": bool(r and ebd[r].r1_pass and ebd[r].t_star < ebd[top].t_star),
            "n_unexplained_earlier_R1_divergences": len([s for s in earlier if s not in out.raw_output["confirmed"]]),
            "path_kind": out.raw_output["path_kind"], "relation": downstream_relation(sc, top)}


def main() -> int:
    res = {"note": "POST-HOC descriptive evidence for docs/SPRINT4_3_0_FAILURE_TAXONOMY.md; held-out section uses saved "
                   "results only (no method execution)."}
    for split in ("dev", "val", "held_out"):
        per, scs = load_split(split)
        order = [p["scenario_id"] for p in per]
        S = [p["methods"][FOCAL]["score"] for p in per]
        Sg = [p["methods"]["RIFT-FULL-V2G"]["score"] for p in per]
        R = [p["methods"][FOCAL]["record"] for p in per]
        sp = {"n": len(order)}
        wrong = [(sid, s, r) for sid, s, r in zip(order, S, R) if s["wrong_root"]]
        ans_attr = [s for sid, s in zip(order, S) if s["expected"] == "ATTRIBUTE" and s["answered"]]
        att = [s for s in S if s["expected"] == "ATTRIBUTE"]
        sp["attribute_scenarios"] = len(att)
        sp["attribute_answered"] = len(ans_attr)
        sp["attribute_answered_correct"] = sum(s["correct"] for s in ans_attr)
        sp["attribute_answered_wrong"] = len(wrong)
        sp["attribute_abstained"] = len(att) - len(ans_attr)
        sp["wrong_root_relation"] = dict(Counter(downstream_relation(scs[sid], s["top1"]) for sid, s, _ in wrong))
        sp["wrong_root_ids"] = [sid for sid, _, _ in wrong]
        sp["wrong_root_path_kind"] = dict(Counter(r["path_kind"] for _, _, r in wrong))
        sp["answered_path_kind_correctness"] = {
            k: {"answered": sum(1 for s, r in zip(S, R) if s["answered"] and r["path_kind"] == k),
                "correct": sum(1 for s, r in zip(S, R) if s["answered"] and r["path_kind"] == k and s["correct"])}
            for k in ("DIRECTED", "SEMI_DIRECTED")}
        sp["abstention_reasons_on_attribute"] = dict(Counter(
            str(s["reason"]) for s in S if s["expected"] == "ATTRIBUTE" and not s["answered"]))
        sp["unsafe_on_abstain_required_by_label_reason"] = dict(Counter(
            str(scs[sid]["ground_truth"]["abstain_reason"]) for sid, s in zip(order, S)
            if s["unsafe"] and s["expected"] == "ABSTAIN_REQUIRED"))
        sp["answered_top_is_true_root_on_abstain_required"] = sum(
            1 for sid, s in zip(order, S) if s["unsafe"] and s["expected"] == "ABSTAIN_REQUIRED"
            and s["top1"] in scs[sid]["ground_truth"]["roots"])
        cats = {}
        for name, pred in CATEGORIES.items():
            if pred is None:
                continue
            idx = [i for i, sid in enumerate(order) if pred(scs[order[i]])]
            fail = [order[i] for i in idx if S[i]["unsafe"] or (S[i]["expected"] == "ATTRIBUTE" and not S[i]["answered"])]
            cats[name] = {"V2": subset([S[i] for i in idx]), "V2G_unsafe": rate(sum(Sg[i]["unsafe"] for i in idx), len(idx)),
                          "n_failing_scenarios": len(fail), "failing_ids": fail[:6], "all_ids_n": len(idx)}
        sp["categories"] = cats
        if split != "held_out":
            sp["wrong_root_mechanisms"] = [mechanisms(scs[sid]) for sid, _, _ in wrong]
            sp["wrong_root_mechanism_counts"] = dict(Counter(m["mechanism"].split("_")[0] for m in sp["wrong_root_mechanisms"]))
            sp["wrong_root_true_root_earlier"] = sum(m["true_root_earlier_than_named"] for m in sp["wrong_root_mechanisms"])
        res[split] = sp
    (ART_DIR / "failure_taxonomy_evidence.json").write_text(json.dumps(res, indent=1, default=float))
    for sp in ("dev", "val", "held_out"):
        r = res[sp]
        print(sp, {k: r[k] for k in ("attribute_scenarios", "attribute_answered", "attribute_answered_correct",
                                     "attribute_answered_wrong", "attribute_abstained", "wrong_root_relation",
                                     "wrong_root_path_kind")})
        if "wrong_root_mechanism_counts" in r:
            print("   mechanisms", r["wrong_root_mechanism_counts"], "true_root_earlier", r["wrong_root_true_root_earlier"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
