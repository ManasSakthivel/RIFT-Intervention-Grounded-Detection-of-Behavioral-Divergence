#!/usr/bin/env python3
"""Final pre-publication closure: READ-ONLY label-dependence audit on committed dev/val ONLY.

Reads datasets/rift_v2/{dev,val}.json (committed, not sealed). Never opens heldout_candidate.json or any confirmatory
material. Re-computes nothing that changes a label: it only tabulates the frozen label function's own inputs
(noise-free root SNR in sigma units, detectable onset) against the label it assigned. No relabelling is performed.
"""
from __future__ import annotations
import json, sys
from collections import Counter
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
import numpy as np
from rift.scenarios.simulator import apparent_signal, detectable_onset_window, observed_services

def band(x):
    return "<3" if x < 3 else "[3,4)" if x < 4 else "[4,5)" if x < 5 else ">=5"

rows = []
for split in ("dev", "val"):                      # held_out deliberately excluded
    for sc in json.load(open(REPO / f"datasets/rift_v2/{split}.json"))["scenarios"]:
        gt = sc["ground_truth"]
        obs = observed_services(sc)
        roots = [r for r in sc["design"]["true_roots"] if r in obs]
        snr = max((float(np.max(np.abs(apparent_signal(sc, r)))) for r in roots), default=None)
        on = [detectable_onset_window(apparent_signal(sc, r)) for r in roots]
        rows.append({"split": split, "id": sc["scenario_id"], "outcome": gt["expected_outcome"],
                     "reason": gt.get("abstain_reason"), "snr": snr, "n_obs_roots": len(roots),
                     "any_detectable": any(o is not None for o in on)})
out = {"n": len(rows), "by_label": dict(Counter(f"{r['outcome']}|{r['reason']}" for r in rows).most_common())}
att = [r for r in rows if r["outcome"] == "ATTRIBUTE"]
ws = [r for r in rows if r["reason"] == "WEAK_SIGNAL"]
nde = [r for r in rows if r["reason"] == "NO_DISCRIMINATING_EVIDENCE"]
out["ATTRIBUTE_root_snr_band"] = dict(Counter(band(r["snr"]) for r in att))
out["WEAK_SIGNAL_root_snr_band"] = dict(Counter(band(r["snr"]) for r in ws))
out["WEAK_SIGNAL_snr_lt_3_never_crosses_detector_threshold"] = sum(r["snr"] < 3 for r in ws)
out["WEAK_SIGNAL_snr_3_to_4_label_only_threshold_gap"] = sum(3 <= r["snr"] < 4 for r in ws)
out["NO_DISCRIMINATING_EVIDENCE_snr_band"] = dict(Counter(band(r["snr"]) for r in nde))
out["min_snr_of_any_ATTRIBUTE"] = min(r["snr"] for r in att)
out["definition"] = {"WEAK_SIGNAL": "all observed true roots have noise-free max|z| < 4.0 (compute_ground_truth)",
                     "detector_theta": 3.0, "label_theta": 4.0}
Path(REPO / "artifacts/final_closure").mkdir(parents=True, exist_ok=True)
(REPO / "artifacts/final_closure/label_circularity_audit.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps(out, indent=1, default=str))

# ---------------------------------------------------------------- part 2: label-rule dependence (diagnostic only)
# Re-derives, per scenario, the three ingredients of compute_ground_truth for the label families that reach the SNR gate,
# then counts how many stored labels would differ under a different SNR gate. NOTHING is written back to any dataset
# and these counts are NOT used to relabel or to score; they quantify how much of the labelling rests on the gate.
import networkx as nx
from rift.scenarios.simulator import _graph, path_responses, sigma_of, DELTA_T

def ingredients(sc):
    obs = observed_services(sc)
    roots = [r for r in sc["design"]["true_roots"] if r in obs]
    z = {s: apparent_signal(sc, s) for s in obs}
    onset = {s: detectable_onset_window(z[s]) for s in obs}
    g = _graph(sc); iv = sc["intervention"]
    sig = {n["id"]: float(n["sigma"]) for n in sc["graph"]["nodes"]}
    res = []
    for r in roots:
        snr = float(np.max(np.abs(z[r]))) if len(z[r]) else 0.0
        temporal = onset[r] is not None and all(onset[s] > onset[r] for s in obs if s != r and onset[s] is not None)
        interv = False
        for d in obs:
            if d == r or not nx.has_path(g, r, d):
                continue
            pr = path_responses(g, r, d)
            if 30.0 + iv["delay_s"] + 2.0 * min(p[1] for p in pr) / DELTA_T > 45.0:
                continue
            if iv["magnitude_sigma"] * sig[r] * iv["delivered"] * sum(p[0] for p in pr) / sig[d] >= 1.0:
                interv = True; break
        res.append((snr, onset[r] is not None, temporal, interv))
    return res

REACH = {"WEAK_SIGNAL", "NO_DISCRIMINATING_EVIDENCE", None}   # ATTRIBUTE has reason None
tot = {"scenarios_reaching_snr_gate": 0, "gate_reproduces_stored_label": 0}
flip = {g: {"ABSTAIN_to_ATTRIBUTE": 0, "ATTRIBUTE_to_ABSTAIN": 0} for g in (3.0, 3.5, 4.5, 5.0)}
by_kind = Counter(); temporal_only_rule3 = 0
for split in ("dev", "val"):
    for sc in json.load(open(REPO / f"datasets/rift_v2/{split}.json"))["scenarios"]:
        gt = sc["ground_truth"]
        if gt.get("abstain_reason") not in REACH:
            continue
        ing = ingredients(sc)
        tot["scenarios_reaching_snr_gate"] += 1
        def lab(g): return any(s >= g and (t or i) for s, _, t, i in ing)
        stored = gt["expected_outcome"] == "ATTRIBUTE"
        tot["gate_reproduces_stored_label"] += int(lab(4.0) == stored)
        for g in flip:
            new = lab(g)
            if new and not stored: flip[g]["ABSTAIN_to_ATTRIBUTE"] += 1
            if stored and not new: flip[g]["ATTRIBUTE_to_ABSTAIN"] += 1
        if stored:
            by_kind["+".join(gt["identifiable_by"])] += 1
            # ATTRIBUTE labels whose ONLY evidence is the TEMPORAL rule that is identical to RIFT's R1 (theta 3, persist 2)
            if gt["identifiable_by"] == ["TEMPORAL"]:
                temporal_only_rule3 += 1
out2 = {"label_rederivation": tot, "stored_ATTRIBUTE_by_evidence_kind": dict(by_kind),
        "ATTRIBUTE_labels_resting_only_on_TEMPORAL_rule_identical_to_RIFT_R1": temporal_only_rule3,
        "sensitivity_of_stored_labels_to_SNR_gate_(diagnostic_only,_not_relabelling)": flip}
out["part2"] = out2
(REPO / "artifacts/final_closure/label_circularity_audit.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps(out2, indent=1))
