#!/usr/bin/env python3
"""Sprint 4.4.0 CID evidence audit (DEV/VAL ONLY; offline synthetic; no live intervention).

    python3 scripts/sprint440_cid_audit.py

Question: what exactly is the "~94% spurious-effect rate" reported by scripts/sprint440_analyze.py::cid_analysis?

Independent re-derivation (does not import analyze.py):
  * pair (x, y): x = intervened service, y = observed outcome service, y != x
  * x is an ANCESTOR of y  <=>  nx.has_path(full true graph incl. hidden nodes, x, y)
  * "significant"          <=>  CID permutation p-value < 0.05, UNCORRECTED (the quantity analyze.py used)
  * window drift d(y)      =   [mean fault_series(post window) - mean fault_series(baseline window)] / sigma_y
                              (noise-free fault contribution to y that changes between the two 30 s do() windows,
                               i.e. a change in y that exists whether or not x is perturbed)
  * non-ancestral pairs are partitioned into (A) clean, (B) |d|>0.3 sigma, (C) other real channel
    (co-target or collateral leakage reaches y). Categories are mutually exclusive in the order C, B, A.
Two pair sets are audited: the V2-trace pair set (the one analyze.py used) and the larger V3 pair set.
Everything is computed twice from scratch and compared (reproducibility).
Ground truth is used only for post-hoc labelling of pairs; no method sees it.
"""
from __future__ import annotations

import json
import sys
import warnings
from collections import Counter, defaultdict
from pathlib import Path

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO), str(REPO / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402

from src.rift.attribution_v3.rift_v3 import V3_CONFIGS, run_v3  # noqa: E402
from src.rift.evaluation import benchmark_v2 as bm  # noqa: E402
from src.rift.evaluation import rift_v2 as r2  # noqa: E402
from src.rift.evaluation.dataset_registry_v2 import load_v2  # noqa: E402
from src.rift.scenarios import simulator as sim  # noqa: E402

OUT = REPO / "artifacts" / "sprint4_4_0"
DRIFT_CUT = 0.3          # analysis stratum used by analyze.py (a descriptive cut, NOT a method threshold)
BINS = [(0.0, 0.1), (0.1, 0.3), (0.3, 0.6), (0.6, 1.0), (1.0, 1e9)]
rng = np.random.default_rng(440)


def wilson(k, n, z=1.959964):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [float(max(0, c - h)), float(min(1, c + h))]


def cluster_boot(rows, B=2000):
    """Scenario-clustered bootstrap CI for the rate of `sig` among rows (pairs are nested in scenarios)."""
    if not rows:
        return [None, None]
    by = defaultdict(list)
    for r in rows:
        by[r["sid"]].append(r["sig"])
    keys = sorted(by)
    vals = []
    for _ in range(B):
        pick = rng.choice(len(keys), len(keys), replace=True)
        s = n = 0
        for i in pick:
            s += sum(by[keys[i]]); n += len(by[keys[i]])
        vals.append(s / n if n else np.nan)
    return [float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5))]


def rate(rows):
    k = sum(r["sig"] for r in rows)
    n = len(rows)
    return {"k": int(k), "n": int(n), "rate": (k / n) if n else None, "wilson95": wilson(k, n),
            "scenario_cluster_boot95": cluster_boot(rows), "n_scenarios": len({r["sid"] for r in rows})}


def pair_rows(sc, cache):
    g = sim._graph(sc)
    iv = sc["intervention"]
    n = int(sc["telemetry"]["n_windows"])
    t_end = (n - 1) * 10.0
    ts = np.concatenate([t_end + np.arange(30.0), t_end + 30.0 + np.arange(30.0)])
    out = []
    co = iv.get("co_target") if iv.get("multi_service") else None
    for (key, mode), res in cache.cid.items():
        x, y = key.split("\u2192")
        if x == y:
            continue
        anc = nx.has_path(g, x, y)
        sy = sim.sigma_of(sc, y)
        fs = sim.fault_series(sc, g, y, ts)
        d = float((fs[30:].mean() - fs[:30].mean()) / sy)
        other = bool((co and (co == y or nx.has_path(g, co, y))) or (y in iv.get("collateral", {})))
        shapes = sorted({f["shape"] for f in sc["faults"] if f["service"] == y or nx.has_path(g, f["service"], y)})
        out.append({"sid": sc["scenario_id"], "x": x, "y": y, "anc": bool(anc), "drift": d, "other_channel": other,
                    "sig": bool(res.permutation_pvalue is not None and res.permutation_pvalue < 0.05),
                    "p": res.permutation_pvalue, "w1": res.w1_estimate, "theta": res.theta_cid,
                    "shapes": shapes, "mode": iv["mode"], "temporal": sc["dimensions"]["temporal"]})
    return out


def collect(split):
    scs = load_v2(split).scenarios
    v2pairs, v3pairs, dec = [], [], []
    for sc in scs:
        o = sim.observe(sc)
        iv = lambda x, ys, s, sc=sc: sim.intervene(sc, x, ys, s)  # noqa: E731
        c2 = r2.SharedCache()
        out2 = r2.run_v2(o, iv, sc["scenario_id"], int(sc["seed"]), r2.CONFIGS["A1-FULL"], cache=c2)
        v2pairs += pair_rows(sc, c2)
        c3 = r2.SharedCache()
        out3 = run_v3(o, iv, sc["scenario_id"], int(sc["seed"]), V3_CONFIGS["V3-FULL"], cache=c3)
        v3pairs += pair_rows(sc, c3)
        g = sim._graph(sc)
        for tag, out in (("V2", out2), ("V3", out3)):
            s = bm.score_one(sc, bm._out_to_rec(out, 0, 0))
            if not s["answered"]:
                continue
            top = s["top1"]
            conf = out.raw_output.get("confirmed", {}).get(top, [])
            bad = [y for y in conf if not nx.has_path(g, top, y)]
            iv_ = sc["intervention"]
            co = iv_.get("co_target") if iv_.get("multi_service") else None
            def why(y):
                d = [r for r in (v2pairs if tag == "V2" else v3pairs) if r["sid"] == sc["scenario_id"] and r["x"] == top and r["y"] == y]
                if not d:
                    return "unknown"
                r = d[0]
                return "other_channel" if r["other_channel"] else ("drift" if abs(r["drift"]) > DRIFT_CUT else "clean_false_positive")
            dec.append({"split": split, "method": tag, "sid": sc["scenario_id"], "top": top, "unsafe": s["unsafe"],
                        "correct": s["correct"], "n_confirmed_from_top": len(conf), "n_nonancestral_confirmed": len(bad),
                        "nonancestral_causes": [why(y) for y in bad]})
    return v2pairs, v3pairs, dec


def summarise(pairs):
    out = {"n_pairs": len(pairs)}
    anc = [r for r in pairs if r["anc"]]
    non = [r for r in pairs if not r["anc"]]
    C = [r for r in non if r["other_channel"]]
    B = [r for r in non if not r["other_channel"] and abs(r["drift"]) > DRIFT_CUT]
    A = [r for r in non if not r["other_channel"] and abs(r["drift"]) <= DRIFT_CUT]
    out["ancestral_pairs"] = {"n": len(anc), "sig": rate(anc)}
    out["nonancestral"] = {"n": len(non), "A_clean_no_drift_no_other_channel": rate(A),
                           "B_drift_gt_0.3_sigma": rate(B), "C_other_real_channel_cotarget_or_collateral": rate(C),
                           "all_nonancestral_sig": rate(non),
                           "share_of_nonancestral_pairs_in_B": len(B) / len(non) if non else None,
                           "scenarios_with_any_B_pair": len({r["sid"] for r in B}),
                           "scenarios_total_with_nonancestral_pairs": len({r["sid"] for r in non})}
    bins = {}
    for lo, hi in BINS:
        sel = [r for r in non if not r["other_channel"] and lo <= abs(r["drift"]) < hi]
        bins[f"{lo}-{hi if hi < 1e8 else 'inf'}"] = rate(sel)
    out["nonancestral_by_abs_drift_sigma"] = bins
    sh = defaultdict(list)
    for r in B:
        sh["+".join(r["shapes"])].append(r)
    out["B_pairs_by_upstream_fault_shapes"] = {k: {"n": len(v), "sig": sum(x["sig"] for x in v), "scenarios": len({x['sid'] for x in v})}
                                               for k, v in sorted(sh.items())}
    tm = Counter(r["temporal"] for r in B)
    out["B_pairs_by_temporal_dimension"] = dict(tm)
    # sign: does drift go the same direction as a DETECTED (significant) shift?  report mean signed drift of sig B pairs
    out["B_sig_signed_drift_sigma"] = {"min": float(min((r["drift"] for r in B if r["sig"]), default=0)),
                                       "median": float(np.median([r["drift"] for r in B if r["sig"]])) if any(r["sig"] for r in B) else None,
                                       "max": float(max((r["drift"] for r in B if r["sig"]), default=0))}
    # ancestral pairs also contaminated?
    ancB = [r for r in anc if abs(r["drift"]) > DRIFT_CUT]
    out["ancestral_pairs_with_abs_drift_gt_0.3"] = {"n": len(ancB), "of": len(anc)}
    return out


def main() -> int:
    res = {}
    for split in ("dev", "val"):
        v2p, v3p, dec = collect(split)
        res[split] = {"V2_pair_set": summarise(v2p), "V3_pair_set": summarise(v3p), "decisions": dec}
    # reproducibility: recompute dev/val from scratch and compare headline numbers; compare with analyze.py's stored figures
    again = {}
    for split in ("dev", "val"):
        v2p, v3p, _ = collect(split)
        again[split] = {"V2": summarise(v2p)["nonancestral"]["B_drift_gt_0.3_sigma"], "V3": summarise(v3p)["nonancestral"]["B_drift_gt_0.3_sigma"]}
    ana = json.loads((OUT / "analysis.json").read_text())
    rep = {}
    for split in ("dev", "val"):
        stored = ana[split]["cid"]["false_positive_rate_nonancestral"]["fault_drift_gt_0.3sigma"]
        mine = res[split]["V2_pair_set"]["nonancestral"]["B_drift_gt_0.3_sigma"]
        rep[split] = {"analyze_py_k_n": [stored["k"], stored["n"]], "audit_V2_pair_set_k_n": [mine["k"], mine["n"]],
                      "audit_rerun_identical": again[split]["V2"]["k"] == mine["k"] and again[split]["V2"]["n"] == mine["n"]
                      and again[split]["V3"]["k"] == res[split]["V3_pair_set"]["nonancestral"]["B_drift_gt_0.3_sigma"]["k"],
                      "note": "audit B category excludes pairs reached by a co-target/collateral channel; analyze.py did not"}
    res["reproducibility"] = rep
    # decision-level contamination
    dsum = {}
    for split in ("dev", "val"):
        for tag in ("V2", "V3"):
            d = [r for r in res[split]["decisions"] if r["method"] == tag]
            bad = [r for r in d if r["n_nonancestral_confirmed"] > 0]
            dsum[f"{split}/{tag}"] = {"answered": len(d), "with_nonancestral_confirmation_from_named_service": len(bad),
                                      "of_which_unsafe": sum(r["unsafe"] for r in bad),
                                      "causes": dict(Counter(c for r in bad for c in r["nonancestral_causes"])),
                                      "unsafe_total": sum(r["unsafe"] for r in d)}
    res["decision_level"] = dsum
    (OUT / "cid_audit.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({"reproducibility": rep, "decision_level": dsum}, indent=1))
    for split in ("dev", "val"):
        for ps in ("V2_pair_set", "V3_pair_set"):
            s = res[split][ps]
            print(split, ps, "pairs", s["n_pairs"], "anc", s["ancestral_pairs"]["n"], "non", s["nonancestral"]["n"])
            for k in ("A_clean_no_drift_no_other_channel", "B_drift_gt_0.3_sigma", "C_other_real_channel_cotarget_or_collateral"):
                v = s["nonancestral"][k]
                print("   ", k, v["k"], "/", v["n"], v["rate"], "wilson", v["wilson95"], "clusterboot", v["scenario_cluster_boot95"], "nsc", v["n_scenarios"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
