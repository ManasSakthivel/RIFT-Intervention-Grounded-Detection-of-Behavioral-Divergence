#!/usr/bin/env python3
"""Sprint 4.3.0 evaluation runner (Protocol v2).

    python3 scripts/sprint430_run_evaluation.py --split dev   [--ablations]
    python3 scripts/sprint430_run_evaluation.py --split val   [--ablations]
    python3 scripts/sprint430_run_evaluation.py --split held_out --ablations --final   # only after sprint430_freeze.py

Every method sees identical inputs (benchmark_v2.run_methods). Results go to artifacts/sprint4_3_0/results/<split>/:
  per_scenario.json / per_scenario.csv, aggregate.json / aggregate.csv, breakdowns.json, detection.json,
  statistics.json / statistics.csv, failures.json, run_metadata.json
No live system is contacted. Held-out is loaded only through dataset_registry_v2.load_v2 (fail-closed).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")
REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.rift.evaluation import benchmark_v2 as bm  # noqa: E402
from src.rift.evaluation import stats_v2 as st  # noqa: E402
from src.rift.evaluation.dataset_registry_v2 import ART_DIR, load_v2  # noqa: E402

DIMS = ["family", "structure", "workload", "observability", "intervention", "negative", "temporal"]
CORE_REPORT = ["B0-EARLIEST", "B0-HIGHEST", "B1-LATENCY-CORR", "B3-SIEVE-LIKE", "B5-RIFT-OBS", "B6-RIFT-RANDOM",
               "B7-RIFT-ONE-SHOT", "RIFT-FULL-LEGACY", "RIFT-FULL-V2"]
FOCAL = "RIFT-FULL-V2"
CONFIRMATORY = [m.method_id for m in bm.REGISTRY if m.confirmatory]


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=REPO_ROOT, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:  # noqa: BLE001
        return "unavailable"


def _versions() -> dict:
    out = {"python": platform.python_version(), "platform": platform.platform()}
    for mod in ("numpy", "scipy", "pandas", "networkx", "causallearn"):
        try:
            m = __import__(mod)
            out[mod] = getattr(m, "__version__", "unknown")
        except Exception:  # noqa: BLE001
            try:
                from importlib.metadata import version
                out[mod] = version("causal-learn" if mod == "causallearn" else mod)
            except Exception:  # noqa: BLE001
                out[mod] = "unavailable"
    return out


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"


def _fmt(r: dict) -> str:
    return "n/a" if r["value"] is None else f"{r['k']}/{r['n']}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["dev", "val", "held_out"])
    ap.add_argument("--ablations", action="store_true")
    ap.add_argument("--final", action="store_true", help="held_out only: purpose=final")
    ap.add_argument("--allow-reopen", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--limit", type=int, default=None, help="debug only; marks the run NOT_VALID")
    a = ap.parse_args()

    status = "VALID"
    if a.split == "held_out":
        if not a.final:
            print("REFUSED: held_out requires --final")
            return 2
        from src.rift.evaluation.held_out_guard import HeldOutGuard
        guard = HeldOutGuard()
        token = "SPRINT430_FINAL_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        guard.allow_oracle(token)
        guard.activate_token(token)
        ls = load_v2("held_out", purpose="final", guard=guard, allow_reopen=a.allow_reopen)
        if not ls.valid_for_final_claims:
            status = "NOT_VALID_FOR_FINAL_CLAIMS"
    else:
        ls = load_v2(a.split, purpose="selection")
    scs = ls.scenarios
    if a.limit:
        scs = scs[: a.limit]
        status = "NOT_VALID_DEBUG_SUBSET"
    out_dir = Path(a.out) if a.out else ART_DIR / "results" / a.split
    out_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    t0 = time.perf_counter()

    recs = {}
    det = []
    for sc in scs:
        recs[sc["scenario_id"]] = bm.run_methods(sc, ablations=a.ablations, measure_mem=False)
        det.append(bm.stage1_detection(sc))
    elapsed = time.perf_counter() - t0
    mids = list(next(iter(recs.values())).keys())
    sids = [s["scenario_id"] for s in scs]
    tmpl = [s["template_id"] for s in scs]

    scores = {m: [bm.score_one(sc, recs[sc["scenario_id"]][m]) for sc in scs] for m in mids}
    aggregate = {m: bm.aggregate(scores[m], [recs[s][m] for s in sids]) for m in mids}
    breakdowns = {m: {d: bm.stratify(scs, scores[m], d) for d in DIMS} for m in mids if not m.startswith("ABL:")}
    detection = st.detection_metrics(det)

    # ---- statistics (confirmatory family only meaningful on held_out; on dev/val they are descriptive)
    statistics = {"role": "CONFIRMATORY" if (a.split == "held_out" and status == "VALID") else "DESCRIPTIVE_DEV_VAL",
                  "unit": "scenario", "n_scenarios": len(scs), "n_templates": len(set(tmpl))}
    comps = [c for c in CONFIRMATORY if c in scores]
    statistics["confirmatory_family"] = st.confirmatory_family(scores, FOCAL, comps, tmpl)
    exp_rows = {}
    if "RIFT-FULL-V2G" in scores:
        for m in ("P1", "P2", "P3_safe"):
            exp_rows[f"RIFT-FULL-V2G|{FOCAL}|{m}"] = st.compare_pair(scores["RIFT-FULL-V2G"], scores[FOCAL], m, tmpl)
    for m in mids:
        if m.startswith("ABL:"):
            for met in ("P1", "P2", "P3_safe"):
                exp_rows[f"{FOCAL}|{m}|{met}"] = st.compare_pair(scores[FOCAL], scores[m], met, tmpl)
    for m in mids:
        if m.startswith("ORACLE:"):
            for met in ("P1", "P2", "P3_safe"):
                exp_rows[f"{FOCAL}|{m}|{met}"] = st.compare_pair(scores[FOCAL], scores[m], met, tmpl)
    statistics["exploratory"] = exp_rows

    # ---- failures (reproducible scenario ids)
    failures = {}
    for m in mids:
        fl = {"unsafe_on_abstain_required": [], "wrong_root_on_attribute": [], "lost_coverage_on_attribute": [],
              "method_errors": []}
        for sc, s in zip(scs, scores[m]):
            sid = sc["scenario_id"]
            if s["unsafe"] and s["expected"] == "ABSTAIN_REQUIRED":
                fl["unsafe_on_abstain_required"].append(sid)
            if s["wrong_root"]:
                fl["wrong_root_on_attribute"].append(sid)
            if s["expected"] == "ATTRIBUTE" and not s["answered"]:
                fl["lost_coverage_on_attribute"].append(sid)
            if recs[sid][m]["error"]:
                fl["method_errors"].append({"scenario_id": sid, "error": recs[sid][m]["error"]})
        failures[m] = fl

    # ---- write
    per = [{"scenario_id": sc["scenario_id"], "template_id": sc["template_id"],
            "dimensions": sc["dimensions"],
            "methods": {m: {"record": recs[sc["scenario_id"]][m], "score": s}
                        for m, s in ((m, scores[m][i]) for m in mids)}}
           for i, sc in enumerate(scs)]
    (out_dir / "per_scenario.json").write_text(json.dumps(per, indent=1, default=float))
    with open(out_dir / "per_scenario.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario_id", "template_id", "method", "expected", "answered", "top1", "correct", "p2", "unsafe",
                    "reason", "ed_s", "n_do", "evidence_type", "path_kind", "runtime_s"])
        for i, sc in enumerate(scs):
            for m in mids:
                s, r = scores[m][i], recs[sc["scenario_id"]][m]
                w.writerow([sc["scenario_id"], sc["template_id"], m, s["expected"], int(s["answered"]), s["top1"],
                            int(s["correct"]), int(s["p2"]), int(s["unsafe"]), s["reason"], r["ed_s"], r["n_do"],
                            r["evidence_type"], r["path_kind"], f"{r['runtime_s']:.4f}"])
    (out_dir / "aggregate.json").write_text(json.dumps(aggregate, indent=1, default=float))
    with open(out_dir / "aggregate.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        keys = ["P1_attribution_accuracy", "conditional_accuracy_on_answered_attribute", "P2_outcome_correct",
                "P3_unsafe_attribution_overall", "unsafe_on_abstain_required", "wrong_root_on_attribute",
                "coverage_overall", "coverage_on_attribute", "coverage_on_abstain_required", "selective_risk",
                "correct_abstention_rate_on_abstain_required", "top3_on_attribute"]
        w.writerow(["method", "N", "N_attribute", "N_abstain_required"] +
                   [f"{k}{sfx}" for k in keys for sfx in ("_k", "_n", "_value", "_wilson_lo", "_wilson_hi")] +
                   ["mean_ed_s", "mean_runtime_s", "method_errors"])
        for m in mids:
            ag = aggregate[m]
            row = [m, ag["N"], ag["N_attribute"], ag["N_abstain_required"]]
            for k in keys:
                r = ag[k]
                row += [r["k"], r["n"], "" if r["value"] is None else f"{r['value']:.4f}",
                        f"{r['wilson95'][0]:.4f}", f"{r['wilson95'][1]:.4f}"]
            row += [f"{ag['intervention']['mean_ed_s']:.1f}", f"{ag['runtime_s']['mean']:.4f}", ag["method_errors"]]
            w.writerow(row)
    (out_dir / "breakdowns.json").write_text(json.dumps(breakdowns, indent=1, default=float))
    (out_dir / "detection.json").write_text(json.dumps({"stage1_detector": "EBD R1 persistence (theta=3, 2 windows)",
                                                         "metrics": detection, "per_scenario": det}, indent=1))
    (out_dir / "statistics.json").write_text(json.dumps(statistics, indent=1, default=float))
    with open(out_dir / "statistics.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["family", "comparison", "n", "p_focal", "p_other", "risk_diff", "ci_lo", "ci_hi", "cohens_h",
                    "only_focal", "only_other", "mcnemar_p", "perm_p", "holm_p_mcnemar", "significant_holm"])
        for fam, rows in (("confirmatory", statistics["confirmatory_family"]["rows"]), ("exploratory", exp_rows)):
            for k, v in rows.items():
                w.writerow([fam, k, v["n"], f"{v['p_a']:.4f}", f"{v['p_b']:.4f}", f"{v['risk_difference']:.4f}",
                            f"{v['ci95_quoted_widest'][0]:.4f}", f"{v['ci95_quoted_widest'][1]:.4f}",
                            f"{v['cohens_h']:.4f}", v["paired_table"]["only_a"], v["paired_table"]["only_b"],
                            f"{v['mcnemar_exact_p']:.5f}", f"{v['permutation_p']:.5f}",
                            f"{v.get('holm_p_mcnemar', float('nan')):.5f}", v.get("significant_holm_0.05", "")])
    (out_dir / "failures.json").write_text(json.dumps(failures, indent=1))

    cfg_hash = hashlib.sha256(json.dumps(
        {"methods": mids, "ablations": a.ablations, "boot": st.BOOT_B, "perm": st.PERM_N, "seed": st.STAT_SEED},
        sort_keys=True).encode()).hexdigest()
    meta = {"split": a.split, "status": status, "n_scenarios": len(scs), "dataset_sha256": ls.sha256,
            "n_templates": len(set(tmpl)), "methods": mids, "excluded": bm.EXCLUDED, "id_notes": bm.ID_NOTES,
            "ablations": a.ablations, "config_hash": cfg_hash, "stat_seed": st.STAT_SEED,
            "bootstrap_B": st.BOOT_B, "permutations": st.PERM_N,
            "git_commit": _git("rev-parse", "HEAD"), "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "protocol_sha256": _sha(REPO_ROOT / "docs" / "EVALUATION_PROTOCOL_V2.md"),
            "source_hashes": {p: _sha(REPO_ROOT / p) for p in (
                "src/rift/evaluation/rift_v2.py", "src/rift/evaluation/benchmark_v2.py",
                "src/rift/evaluation/stats_v2.py", "scripts/sprint430_run_evaluation.py")},
            "versions": _versions(), "started_utc": started.isoformat(),
            "finished_utc": datetime.now(timezone.utc).isoformat(), "wall_clock_s": round(elapsed, 2),
            "live_system_contacted": False,
            "metric_definitions": "docs/EVALUATION_PROTOCOL_V2.md sections 3-4"}
    (out_dir / "run_metadata.json").write_text(json.dumps(meta, indent=1))

    print(f"split={a.split} status={status} N={len(scs)} templates={len(set(tmpl))} elapsed={elapsed:.1f}s -> {out_dir}")
    hdr = f"{'method':38s} {'P1':>9s} {'P2':>9s} {'unsafe':>9s} {'cov':>9s} {'condacc':>9s}"
    print(hdr)
    for m in mids:
        ag = aggregate[m]
        print(f"{m:38s} {_fmt(ag['P1_attribution_accuracy']):>9s} {_fmt(ag['P2_outcome_correct']):>9s} "
              f"{_fmt(ag['P3_unsafe_attribution_overall']):>9s} {_fmt(ag['coverage_overall']):>9s} "
              f"{_fmt(ag['conditional_accuracy_on_answered_attribute']):>9s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
