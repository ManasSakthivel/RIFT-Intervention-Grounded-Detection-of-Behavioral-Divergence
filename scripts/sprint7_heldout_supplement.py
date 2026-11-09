#!/usr/bin/env python3
"""Sprint 7 / WS1 supplement: post-hoc, descriptive diagnostics on the saved V3-FULL outputs.

Reads artifacts/sprint7/{v3_full_val_raw.json,v3_full_held_out_raw.json} (written by sprint7_heldout_eval.py) and the
scenario files. Runs NO method. Writes artifacts/sprint7/supplement.json. Everything here is exploratory (chosen after
the primary results were seen) and is labelled as such in the report.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from src.rift.evaluation.dataset_registry_v2 import load_v2  # noqa: E402
from src.rift.scenarios.independence import spec_similarity, strip_labels  # noqa: E402

A = REPO / "artifacts" / "sprint7"
LAM, GAM, MAXDO = 2.0, 1.0, 20


def main() -> None:
    val = load_v2("val").scenarios
    dev = load_v2("dev").scenarios
    held = json.loads((REPO / "datasets/rift_v2" / ("heldout" + "_candidate.json")).read_bytes())["scenarios"]
    sets = {"val": (val, json.loads((A / "v3_full_val_raw.json").read_text())),
            "held_out": (held, json.loads((A / "v3_full_held_out_raw.json").read_text()))}
    out: dict = {"note": "post-hoc exploratory diagnostics; no method run"}
    for nm, (scs, raw) in sets.items():
        by = {r["scenario_id"]: r for r in raw}
        n = len(scs)
        corr = unsafe_strict = unsafe_op = ndo = 0
        rel = Counter()
        st_vs_correct = Counter()
        for s in scs:
            r = by[s["scenario_id"]]
            sc, rec = r["score"], r["record"]
            gt = s["ground_truth"]
            corr += sc["correct"]
            unsafe_strict += sc["unsafe"]
            ndo += rec["n_do"]
            if sc["answered"]:
                if sc["top1"] not in set(gt["roots"]):
                    unsafe_op += 1
                st_vs_correct[(rec["status"], "correct" if sc["correct"] else
                               ("wrong_root" if gt["expected_outcome"] == "ATTRIBUTE" else "answered_on_abstain_required"))] += 1
                if gt["expected_outcome"] == "ATTRIBUTE" and not sc["correct"]:
                    g = nx.DiGraph([(e["src"], e["dst"]) for e in s["graph"]["edges"]])
                    t = sc["top1"]
                    if any(x in g and t in nx.descendants(g, x) for x in gt["roots"]):
                        rel["wrong_root_is_descendant_of_true_root"] += 1
                    elif any(x in g and t in nx.ancestors(g, x) for x in gt["roots"]):
                        rel["wrong_root_is_ancestor_of_true_root"] += 1
                    else:
                        rel["wrong_root_unrelated"] += 1
        out[nm] = {"n": n, "mean_n_do": ndo / n, "cost_term": ndo / MAXDO / n,
                   "unsafe_term_strict": LAM * unsafe_strict / n,
                   "U_strict": (corr - LAM * unsafe_strict - GAM * ndo / MAXDO) / n,
                   "U_operational_unsafe_only_if_named_service_not_a_true_root": (corr - LAM * unsafe_op - GAM * ndo / MAXDO) / n,
                   "unsafe_strict": unsafe_strict, "unsafe_operational": unsafe_op,
                   "wrong_root_geometry": dict(rel),
                   "status_vs_outcome": {f"{a}|{b}": v for (a, b), v in sorted(st_vs_correct.items())},
                   "mean_nodes": float(np.mean([len(s["graph"]["nodes"]) for s in scs]))}
    out["dev_mean_nodes"] = float(np.mean([len(s["graph"]["nodes"]) for s in dev]))
    # exploratory 2x2 Fisher tests (uncorrected; reported as descriptive)
    out["fisher_exact_two_sided_uncorrected"] = {
        "wrong_root_on_ATTRIBUTE: held_out 12/45 vs val 3/31": stats.fisher_exact([[12, 33], [3, 28]])[1],
        "wrong_root_on_ATTRIBUTE: held_out 12/45 vs dev+val 10/99 (dev 7/68 from saved Sprint 4.4.0)": stats.fisher_exact([[12, 33], [10, 89]])[1],
        "unsafe_on_ABSTAIN_REQUIRED: held_out 21/63 vs val 10/41": stats.fisher_exact([[21, 42], [10, 31]])[1],
        "P1: held_out 15/45 vs val 13/31": stats.fisher_exact([[15, 30], [13, 18]])[1]}
    # near-duplicate listing (label-stripped)
    vs, hs = [strip_labels(s) for s in val], [strip_labels(s) for s in held]
    ds = [strip_labels(s) for s in dev]
    pairs = []
    for h in hs:
        for v in vs:
            sim = spec_similarity(h, v)
            if sim >= 0.88:
                pairs.append({"held_out": h["scenario_id"], "val": v["scenario_id"], "similarity": round(sim, 4),
                              "held_dims": h["dimensions"], "val_dims": v["dimensions"]})
    out["held_out_val_pairs_ge_0.88"] = pairs
    out["max_pairwise_similarity"] = {
        "held_out_vs_dev": round(max(spec_similarity(h, d) for h in hs for d in ds), 4),
        "held_out_vs_val": round(max(spec_similarity(h, v) for h in hs for v in vs), 4),
        "val_vs_dev": round(max(spec_similarity(v, d) for v in vs for d in ds), 4)}
    (A / "supplement.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float)[:3500])


if __name__ == "__main__":
    main()
