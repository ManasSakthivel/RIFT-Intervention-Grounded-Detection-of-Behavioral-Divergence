#!/usr/bin/env python3
"""Post-run analysis for Sprint 4.3.0 (reads saved per-scenario results only; runs NO method, reads NO dataset labels
except via the already-written per_scenario.json and the split's own scenario file passed through load_v2).

    python3 scripts/sprint430_analyze.py --split held_out

Writes artifacts/sprint4_3_0/results/<split>/analysis.json containing:
  * trivial reference policies (POST-HOC sanity references, not methods): always-abstain, always-answer-top-1 of B0-HIGHEST
  * V2 / V2G / legacy / best-baseline breakdowns with n (family, structure, workload, observability, intervention, negative)
  * distribution-shift strata (structure/family absent from dev+val)
  * failure taxonomy for RIFT-FULL-V2 with reproducible scenario ids
  * ablation deltas (descriptive)
For the held-out split the scenario file is read only if the held-out was already opened (heldout_opened.json exists).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.rift.evaluation import benchmark_v2 as bm  # noqa: E402
from src.rift.evaluation import stats_v2 as st  # noqa: E402
from src.rift.evaluation.dataset_registry_v2 import ART_DIR, HELD_FILE, V2_DIR, load_v2  # noqa: E402

FOCAL = "RIFT-FULL-V2"
UNSEEN = {"structure": ["feedback_like"], "family": ["recovery_instability"]}


def load_scenarios(split: str):
    if split == "held_out":
        if not (ART_DIR / "heldout_opened.json").is_file():
            raise SystemExit("REFUSED: held-out was not opened through the guard yet")
        return json.loads((V2_DIR / HELD_FILE).read_bytes())["scenarios"]
    return load_v2(split).scenarios


def rate(k, n):
    lo, hi = bm._wilson(k, n)
    return {"k": k, "n": n, "value": (k / n) if n else None, "wilson95": [lo, hi]}


def subset_metrics(rows):
    attr = [r for r in rows if r["expected"] == "ATTRIBUTE"]
    ans = [r for r in rows if r["answered"]]
    return {"n": len(rows), "n_attribute": len(attr),
            "P1": rate(sum(r["correct"] for r in attr), len(attr)),
            "P2": rate(sum(r["p2"] for r in rows), len(rows)),
            "unsafe": rate(sum(r["unsafe"] for r in rows), len(rows)),
            "coverage": rate(len(ans), len(rows)),
            "selective_risk": rate(sum(r["unsafe"] for r in ans), len(ans))}


def taxonomy(sc, rec, score):
    gt = sc["ground_truth"]
    if score["unsafe"] and gt["expected_outcome"] == "ABSTAIN_REQUIRED":
        return f"UNSAFE_ON_ABSTAIN_REQUIRED/{gt['abstain_reason']}"
    if score["wrong_root"]:
        top = score["top1"]
        import networkx as nx
        g = nx.DiGraph([(e["src"], e["dst"]) for e in sc["graph"]["edges"]])
        roots = gt["roots"]
        if top in {n for r in roots if r in g for n in nx.descendants(g, r)}:
            return "WRONG_ROOT/named_downstream_of_true_root"
        if any(f["service"] == top for f in sc["faults"]):
            return "WRONG_ROOT/named_other_faulted_service"
        return "WRONG_ROOT/named_unrelated_service"
    if gt["expected_outcome"] == "ATTRIBUTE" and not score["answered"]:
        return f"LOST_COVERAGE/{score['reason']}"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["dev", "val", "held_out"])
    a = ap.parse_args()
    rdir = ART_DIR / "results" / a.split
    per = json.loads((rdir / "per_scenario.json").read_text())
    scs = {s["scenario_id"]: s for s in load_scenarios(a.split)}
    mids = list(per[0]["methods"])
    order = [p["scenario_id"] for p in per]
    S = {m: [p["methods"][m]["score"] for p in per] for m in mids}
    R = {m: [p["methods"][m]["record"] for p in per] for m in mids}
    out = {"split": a.split, "n": len(per)}

    # --- trivial references (post-hoc)
    n = len(per)
    n_abs = sum(1 for sid in order if scs[sid]["ground_truth"]["expected_outcome"] == "ABSTAIN_REQUIRED")
    n_attr = n - n_abs
    out["trivial_references_POST_HOC"] = {
        "note": "Sanity references added after seeing results; not methods, not in any test family.",
        "always_abstain": {"P1": rate(0, n_attr), "P2": rate(n_abs, n), "unsafe": rate(0, n),
                           "coverage": rate(0, n),
                           "reading": "P2 equals the share of ABSTAIN_REQUIRED scenarios; a method must beat THIS, "
                                      "not only the never-abstaining baselines, to show it adds value."},
        "label_mix": {"ATTRIBUTE": n_attr, "ABSTAIN_REQUIRED": n_abs},
    }

    # --- breakdowns
    dims = ["family", "structure", "workload", "observability", "intervention", "negative", "temporal"]
    sel = [FOCAL, "RIFT-FULL-V2G", "RIFT-FULL-LEGACY", "B6-RIFT-RANDOM", "B3-SIEVE-LIKE", "B1-LATENCY-CORR"]
    bk = {}
    for m in sel:
        bk[m] = {}
        for d in dims:
            by = defaultdict(list)
            for sid, s in zip(order, S[m]):
                v = scs[sid]["dimensions"].get(d)
                by[str(v if v is not None else "none")].append(s)
            bk[m][d] = {k: subset_metrics(v) for k, v in sorted(by.items())}
    out["breakdowns"] = bk

    # --- distribution shift
    shift = {}
    for dim, vals in UNSEEN.items():
        for v in vals:
            idx = [i for i, sid in enumerate(order) if scs[sid]["dimensions"][dim] == v]
            shift[f"{dim}={v}"] = {m: subset_metrics([S[m][i] for i in idx]) for m in sel}
            shift[f"{dim}={v}"]["scenario_ids"] = [order[i] for i in idx]
    seen_idx = [i for i, sid in enumerate(order)
                if all(scs[sid]["dimensions"][d] != v for d, vs in UNSEEN.items() for v in vs)]
    shift["seen_structure_and_family"] = {m: subset_metrics([S[m][i] for i in seen_idx]) for m in sel}
    out["distribution_shift"] = shift

    # --- observability strata (RQ3)
    obs = defaultdict(list)
    for i, sid in enumerate(order):
        o = scs[sid]["dimensions"]["observability"]
        grp = "complete_or_ambiguous_pag" if o in ("complete_telemetry", "ambiguous_pag") else "degraded:" + o
        obs[grp].append(i)
    out["observability_strata"] = {g: {m: subset_metrics([S[m][i] for i in idx]) for m in sel}
                                   for g, idx in sorted(obs.items())}
    deg = [i for g, idx in obs.items() if g.startswith("degraded") for i in idx]
    out["observability_degraded_pooled"] = {m: subset_metrics([S[m][i] for i in deg]) for m in sel}

    # --- failure taxonomy
    for m in (FOCAL, "RIFT-FULL-V2G", "RIFT-FULL-LEGACY"):
        cnt, ids = Counter(), defaultdict(list)
        for sid, rec, s in zip(order, R[m], S[m]):
            t = taxonomy(scs[sid], rec, s)
            if t:
                cnt[t] += 1
                ids[t].append(sid)
        out.setdefault("failure_taxonomy", {})[m] = {k: {"count": cnt[k], "scenario_ids": sorted(ids[k])}
                                                     for k in sorted(cnt)}

    # --- evidence composition of V2 answers
    ev = Counter()
    for sid, rec, s in zip(order, R[FOCAL], S[FOCAL]):
        if s["answered"]:
            ev[(rec["evidence_type"], rec["path_kind"], "correct" if s["correct"] else "not_correct")] += 1
    out["v2_answered_evidence"] = {"|".join(k): v for k, v in sorted(ev.items())}

    # --- abstention informativeness: selective risk answered-vs-all and accuracy-coverage
    info = {}
    for m in sel:
        ans = [s for s in S[m] if s["answered"]]
        info[m] = {"coverage": rate(len(ans), n),
                   "selective_risk_answered": rate(sum(s["unsafe"] for s in ans), len(ans)),
                   "unsafe_rate_if_always_answered_same_method": None}
    out["abstention_informativeness"] = info

    # --- ablation deltas
    base = bm.aggregate(S[FOCAL], R[FOCAL])
    abl = {}
    for m in mids:
        if m.startswith("ABL:") or m.startswith("ORACLE:RIFT-FULL-V2"):
            ag = bm.aggregate(S[m], R[m])
            abl[m] = {k: ag[k]["value"] for k in ("P1_attribution_accuracy", "P2_outcome_correct",
                                                   "P3_unsafe_attribution_overall", "coverage_overall",
                                                   "conditional_accuracy_on_answered_attribute")}
            abl[m]["mean_ed_s"] = ag["intervention"]["mean_ed_s"]
            abl[m]["mean_runtime_s"] = ag["runtime_s"]["mean"]
            abl[m]["delta_vs_V2"] = {k: (None if ag[k]["value"] is None or base[k]["value"] is None
                                         else ag[k]["value"] - base[k]["value"])
                                     for k in ("P1_attribution_accuracy", "P2_outcome_correct",
                                               "P3_unsafe_attribution_overall", "coverage_overall")}
    abl[FOCAL] = {"P1_attribution_accuracy": base["P1_attribution_accuracy"]["value"],
                  "P2_outcome_correct": base["P2_outcome_correct"]["value"],
                  "P3_unsafe_attribution_overall": base["P3_unsafe_attribution_overall"]["value"],
                  "coverage_overall": base["coverage_overall"]["value"],
                  "conditional_accuracy_on_answered_attribute": base["conditional_accuracy_on_answered_attribute"]["value"],
                  "mean_ed_s": base["intervention"]["mean_ed_s"], "mean_runtime_s": base["runtime_s"]["mean"]}
    out["ablations"] = abl

    # --- POST-HOC: paired comparison against the trivial always-abstain policy (P2 / unsafe / P1)
    aa = []
    for sid in order:
        e = scs[sid]["ground_truth"]["expected_outcome"]
        aa.append({"scenario_id": sid, "expected": e, "answered": False, "correct": False, "p2": e == "ABSTAIN_REQUIRED",
                   "unsafe": False})
    tmpl = [scs[sid]["template_id"] for sid in order]
    out["POST_HOC_vs_always_abstain"] = {
        "note": "Not pre-registered. Always-abstain is a trivial policy; a method that cannot beat it on P2 adds no "
                "outcome-level value on this label mix.",
        **{f"{m}|{met}": st.compare_pair(S[m], aa, met, tmpl) for m in (FOCAL, "RIFT-FULL-V2G", "RIFT-FULL-LEGACY",
                                                                       "B5-RIFT-OBS") for met in ("P2",)}}

    # --- H4 (pre-registered): removing interventional evidence raises unsafe attributions on counterexample strata
    cx = ("earliest_not_root", "coincidental_anomaly", "indistinguishable_onsets")
    idx = [i for i, sid in enumerate(order) if scs[sid]["dimensions"].get("negative") in cx]
    h4 = {"strata": list(cx), "n_scenarios": len(idx), "scenario_ids": [order[i] for i in idx]}
    for m in (FOCAL, "ABL:A6-NO-INTERVENTION", "ABL:A8-OBSERVATIONAL-ONLY"):
        if m in S:
            h4[m] = {"unsafe": rate(sum(S[m][i]["unsafe"] for i in idx), len(idx)),
                     "coverage": rate(sum(S[m][i]["answered"] for i in idx), len(idx))}
    if "ABL:A6-NO-INTERVENTION" in S:
        h4["verdict"] = ("SUPPORTED" if h4["ABL:A6-NO-INTERVENTION"]["unsafe"]["k"] > h4[FOCAL]["unsafe"]["k"]
                         else "NOT SUPPORTED (no higher unsafe count without interventions)")
    out["H4_counterexample_strata"] = h4

    # --- H5 (pre-registered): greedy MSIS lowers cumulative intervention duration vs random order, same accuracy
    h5 = {}
    for m in ("ABL:A10-RANDOM-INTERVENTION", "ABL:A7-NO-MSIS"):
        if m in R:
            diff = [rb["ed_s"] - rf["ed_s"] for rf, rb in zip(R[FOCAL], R[m])]
            h5[m] = {"mean_ed_V2": sum(r["ed_s"] for r in R[FOCAL]) / n, "mean_ed_other": sum(r["ed_s"] for r in R[m]) / n,
                     "mean_diff_other_minus_V2_s": sum(diff) / n, "n_scenarios_differing": sum(1 for d in diff if d != 0),
                     "permutation_p": st.sign_flip_permutation(diff),
                     "bootstrap": st.clustered_bootstrap_diff([rb["ed_s"] for rb in R[m]],
                                                              [rf["ed_s"] for rf in R[FOCAL]], tmpl)}
    out["H5_msis_vs_alternatives"] = h5

    (rdir / "analysis.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"wrote {rdir/'analysis.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
