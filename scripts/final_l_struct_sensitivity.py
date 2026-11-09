#!/usr/bin/env python3
"""D23 L-struct descriptive sensitivity on committed dev/val ONLY (post-hoc, non-confirmatory, NOT relabelling).

Reads datasets/rift_v2/{dev,val}.json and the existing per-scenario method scores
(artifacts/sprint4_3_0/results/{dev,val}/per_scenario.json for RIFT-FULL-V2,
 artifacts/sprint4_4_0/v3_{dev,val}.json for V3-FULL). Never opens heldout_candidate.json or any held-out result.
Writes only a NEW file (default artifacts/final_closure/l_struct_sensitivity_devval.json); overwrites nothing historical.

Rescoring under L-struct (sensitivity definition, NOT the frozen scoring):
  L+ (structurally attributable): correct = answered with top1 in ground_truth.roots; wrong = answered with other root;
                                  abstain = neither correct nor unsafe (missed attribution).
  L- (structurally not)         : any answer is unsafe; abstain is correct.
"""
from __future__ import annotations
import argparse, json, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from rift.scenarios import l_struct as LS  # noqa: E402


def band(s):
    return "none" if s is None else "<3" if s < 3 else "[3,4)" if s < 4 else "[4,5)" if s < 5 else ">=5"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "artifacts/final_closure/l_struct_sensitivity_devval.json"))
    out_path = Path(ap.parse_args().out)
    sc = {}
    for sp in ("dev", "val"):
        for s in json.load(open(REPO / f"datasets/rift_v2/{sp}.json"))["scenarios"]:
            sc[s["scenario_id"]] = s
    scores = {"RIFT-FULL-V2": {}, "V3-FULL": {}}
    for sp in ("dev", "val"):
        for r in json.load(open(REPO / f"artifacts/sprint4_3_0/results/{sp}/per_scenario.json")):
            scores["RIFT-FULL-V2"][r["scenario_id"]] = r["methods"]["RIFT-FULL-V2"]["score"]
        for r in json.load(open(REPO / f"artifacts/sprint4_4_0/v3_{sp}.json")):
            scores["V3-FULL"][r["scenario_id"]] = r["methods"]["V3-FULL"]["score"]
    lab = {i: LS.l_struct(s) for i, s in sc.items()}
    cov = {i: LS.detectability_covariates(s) for i, s in sc.items()}
    n = len(sc)
    res = {"n": n, "scope": "dev+val only; post-hoc descriptive; not confirmatory; frozen labels unchanged",
           "l_struct_version": LS.L_STRUCT_VERSION,
           "l_plus": sum(l["label"] for l in lab.values()),
           "frozen_attribute": sum(s["ground_truth"]["expected_outcome"] == "ATTRIBUTE" for s in sc.values()),
           "methods": {}}
    res["always_abstain"] = {"outcome_accuracy_lstruct": (n - res["l_plus"]) / n,
                             "outcome_accuracy_frozen": 1 - res["frozen_attribute"] / n,
                             "unsafe": 0, "missed_attributions_lstruct": res["l_plus"]}
    for m, M in scores.items():
        corr = wrong = ans_neg = abst_neg = miss = 0
        strata = defaultdict(lambda: defaultdict(int))
        for i, s in sc.items():
            l, a = lab[i]["label"], M[i]
            roots = set(s["ground_truth"]["roots"])
            k = ("L+/" + band(cov[i]["root_snr_noisefree"])) if l else ("L-/" + lab[i]["reason"])
            strata[k]["n"] += 1
            if l:
                if not a["answered"]:
                    miss += 1; strata[k]["missed"] += 1
                elif a["top1"] in roots:
                    corr += 1; strata[k]["correct_root"] += 1
                else:
                    wrong += 1; strata[k]["wrong_root"] += 1
            else:
                if a["answered"]:
                    ans_neg += 1; strata[k]["unsafe_answer"] += 1
                else:
                    abst_neg += 1; strata[k]["correct_abstain"] += 1
        res["methods"][m] = {
            "correct_root_on_Lplus": corr, "wrong_root_on_Lplus": wrong, "missed_on_Lplus": miss,
            "answered_on_Lminus_unsafe": ans_neg, "abstained_on_Lminus_correct": abst_neg,
            "unsafe_lstruct": wrong + ans_neg, "unsafe_rate_lstruct": (wrong + ans_neg) / n,
            "outcome_accuracy_lstruct": (corr + abst_neg) / n,
            "correct_root_rate_on_Lplus": corr / res["l_plus"],
            "strata": {k: dict(v) for k, v in sorted(strata.items())}}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(res, indent=2, sort_keys=True))
    print(json.dumps({k: v for k, v in res.items() if k != "methods"}, indent=1))
    for m, v in res["methods"].items():
        print(m, {k: v[k] for k in v if k != "strata"})
    print("wrote", out_path)


if __name__ == "__main__":
    main()
