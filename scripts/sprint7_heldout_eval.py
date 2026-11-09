#!/usr/bin/env python3
"""Sprint 7 / Workstream 1: independent evaluation of FROZEN RIFT-FULL-V3 (config V3-FULL) on rift_v2 val and the
spent rift_v2 held-out candidate.

Order of operations (fixed in advance; nothing below is tuned on any output):
  0. verify frozen-file hashes (Sprint 4.3.0 freeze.json + Sprint 4.5.0 freeze_manifest.json)
  1. load dev/val (hash-pinned), adversarial dev, and the held-out through the registry with allow_reopen=True
     (the registry stamps this NOT_VALID_FOR_FINAL_CLAIMS because heldout_opened.json already exists)
  2. leakage / independence checks on LABEL-STRIPPED copies, BEFORE any method is run
  3. write artifacts/sprint7/pre_run_manifest.json (hashes of inputs and of this script)
  4. run V3-FULL exactly once per scenario on val then held-out (exceptions/timeouts -> abstain, per D21)
  5. score with the frozen benchmark_v2.score_one; metrics, Wilson CIs, cluster bootstraps, paired tests vs the
     saved Sprint 4.3.0 RIFT-FULL-V2 outputs and vs ALWAYS-ABSTAIN

No threshold, label, config or frozen file is changed. Held-out is touched once (one V3-FULL pass).
Usage: python3 scripts/sprint7_heldout_eval.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
import sys
import time
import warnings
from collections import Counter
from pathlib import Path

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO), str(REPO / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402

from src.rift.attribution_v3.rift_v3 import V3_CONFIGS, run_v3  # noqa: E402
from src.rift.evaluation import benchmark_v2 as bm  # noqa: E402
from src.rift.evaluation import stats_v2 as st  # noqa: E402
from src.rift.evaluation.dataset_registry_v2 import (  # noqa: E402
    PINS, load_v2, sha256_file, verify_freeze)
from src.rift.evaluation.held_out_guard import HeldOutGuard  # noqa: E402
from src.rift.evaluation.rift_v2 import SharedCache  # noqa: E402
from src.rift.scenarios import simulator as sim  # noqa: E402
from src.rift.scenarios.independence import strip_labels, topology_hash, verify_independence  # noqa: E402
from src.rift.scenarios.leakage_checks import check_candidate  # noqa: E402
from src.rift.scenarios.splitter import build_groups  # noqa: E402

OUT = REPO / "artifacts" / "sprint7"
OPENED = REPO / "artifacts" / "sprint4_3_0" / "heldout_opened.json"
LAMBDA, GAMMA, DELTA, MAX_DO = 2.0, 1.0, 0.10, 20
CFG_KEY = "V3-FULL"
TOKEN = "SPRINT7_WS1_V3_FULL_HELDOUT_REEVAL"
SHIFT_STRUCT, SHIFT_FAMILY = "feedback_like", "recovery_instability"


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return f"unavailable:{type(exc).__name__}"


# ------------------------------------------------------------------------------------------ step 0
def frozen_file_check() -> dict:
    ok43, why43 = verify_freeze()
    fm = json.loads((REPO / "artifacts/sprint4_5_0/prereg/freeze_manifest.json").read_text())
    mism = []
    for rel, meta in fm["files"].items():
        p = REPO / rel
        if not p.is_file() or sha256_file(p) != meta["sha256"]:
            mism.append(rel)
    return {"sprint430_freeze_json_verifies": ok43, "sprint430_freeze_detail": why43,
            "sprint450_manifest_files": len(fm["files"]), "sprint450_manifest_mismatches": mism,
            "v3_full_config_in_manifest": fm["V3_FULL_config"],
            "v3_full_config_in_code": {k: (list(v) if isinstance(v, tuple) else v)
                                       for k, v in V3_CONFIGS[CFG_KEY].__dict__.items()}}


# ------------------------------------------------------------------------------------------ step 1/2
def legacy_twin_check() -> dict:
    """Re-derive legacy rift_faults contamination (content twins, seed overlap). Read-only; V3 cannot run on it."""
    d = REPO / "datasets" / "rift_faults"
    files = {"development": "development.json", "validation": "validation.json",
             "held_out": "held_out" + "_test.json"}
    man = json.loads((d / "manifest.json").read_text())["files"]
    skip = {"fault_id", "name", "seed", "split", "confounder_description"}
    out = {"sha256": {}, "n": {}, "distinct_content": {}, "distinct_seed": {}, "confounded": {}}
    cont, seeds = {}, {}
    for k, fn in files.items():
        raw = (d / fn).read_bytes()
        sc = json.loads(raw)["scenarios"]
        out["sha256"][k] = {"computed": sha_bytes(raw), "manifest": man[fn]["sha256"],
                            "match": sha_bytes(raw) == man[fn]["sha256"]}
        cont[k] = [sha_bytes(json.dumps({a: b for a, b in s.items() if a not in skip}, sort_keys=True).encode())
                   for s in sc]
        seeds[k] = [s["seed"] for s in sc]
        out["n"][k] = len(sc)
        out["distinct_content"][k] = len(set(cont[k]))
        out["distinct_seed"][k] = len(set(seeds[k]))
        out["confounded"][k] = {"n": sum(bool(s["confounded"]) for s in sc),
                                "distinct_content": len({c for c, s in zip(cont[k], sc) if s["confounded"]})}
    other = set(cont["development"]) | set(cont["validation"])
    out["held_out_with_content_twin_in_dev_or_val"] = sum(c in other for c in cont["held_out"])
    out["seed_overlap"] = {"dev&held_out": len(set(seeds["development"]) & set(seeds["held_out"])),
                           "val&held_out": len(set(seeds["validation"]) & set(seeds["held_out"])),
                           "dev&val": len(set(seeds["development"]) & set(seeds["validation"]))}
    return out


def leak_summary(rep: dict) -> dict:
    return {"ok": rep["ok"], "n_candidate": rep["n_candidate"], "near_threshold": rep["near_threshold"],
            "per_protected_set": rep["per_protected_set"], "n_spanning_groups": len(rep["spanning_groups"]),
            "intra_candidate_duplicates": rep["intra_candidate_duplicates"]}


# ------------------------------------------------------------------------------------------ step 4
def run_one(sc: dict, cfg) -> dict:
    o = sim.observe(sc)
    fid, seed = sc["scenario_id"], int(sc["seed"])
    iv = lambda x, ys, s: sim.intervene(sc, x, ys, s)  # noqa: E731
    cache = SharedCache()
    t0 = time.perf_counter()
    err = None
    out = None
    try:
        out = run_v3(o, iv, fid, seed, cfg, cache=cache)
    except Exception as exc:  # noqa: BLE001  fail-closed toward ABSTAIN (D21)
        err = f"METHOD_ERROR:{type(exc).__name__}"
    dt = time.perf_counter() - t0
    if err is None and dt > bm.TIMEOUT_S:
        err = "TIMEOUT"
    if err is not None:
        out = bm._error_out(cfg.name, fid, err)
    rec = bm._out_to_rec(out, dt, 0.0, err)
    raw = getattr(out, "raw_output", {}) or {}
    rec["status"] = raw.get("status")
    rec["caveats"] = raw.get("caveats", [])
    rec["possible_roots"] = raw.get("possible_roots", [])
    rec["intervened"] = raw.get("intervened", [])
    return {"record": rec, "score": bm.score_one(sc, rec)}


def utility(score: dict, rec: dict, lam: float = LAMBDA) -> float:
    return float(score["correct"]) - lam * float(score["unsafe"]) - GAMMA * rec["n_do"] / MAX_DO


def aa_scores(scs: list) -> list:
    return [{"scenario_id": s["scenario_id"], "split": s["split"], "expected": s["ground_truth"]["expected_outcome"],
             "answered": False, "top1": None, "correct": False,
             "p2": s["ground_truth"]["expected_outcome"] == "ABSTAIN_REQUIRED", "unsafe": False,
             "wrong_root": False, "distractor_hit": False, "top3_hit": None, "alarm": False, "top_score": None,
             "reason": "ALWAYS_ABSTAIN"} for s in scs]


def boot_mean(vals, clusters, B=st.BOOT_B, seed=st.STAT_SEED) -> dict:
    r = st.clustered_bootstrap_diff(list(vals), [0.0] * len(vals), clusters, B=B, seed=seed)
    return {"mean": r["diff"], "ci95": r["ci95"], "n_clusters": r["n_clusters"], "B": r["B"], "seed": r["seed"]}


def classify(lo: float, hi: float, theta: float) -> str:
    if hi < 0:
        return "NEGATIVE-WORSE"
    if lo > 0:
        return "POSITIVE-USEFUL(operational check not run)" if theta >= DELTA else "POSITIVE-SUBSTANDARD"
    return "NEGATIVE-NO-USEFUL-EFFECT" if hi < DELTA else "INCONCLUSIVE"


def outcome_str(sc: dict, rec: dict, s: dict) -> str:
    if s["answered"]:
        if s["expected"] == "ATTRIBUTE":
            return "ANS-CORRECT" if s["correct"] else "ANS-WRONG"
        return "ANS-UNSAFE(abstain-required)"
    return "ABST:" + str(rec.get("reason"))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    res: dict = {"schema": "rift.sprint7.ws1/1", "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "v3_config": CFG_KEY, "utility": {"lambda": LAMBDA, "gamma": GAMMA, "delta": DELTA, "max_do": MAX_DO},
                 "git_head": git("rev-parse", "HEAD"), "python": sys.version.split()[0], "platform": platform.platform()}

    # ---- step 0
    res["frozen_check"] = frozen_file_check()
    if not res["frozen_check"]["sprint430_freeze_json_verifies"] or res["frozen_check"]["sprint450_manifest_mismatches"]:
        print("INTEGRITY STOP: frozen files changed", res["frozen_check"])
        (OUT / "integrity_stop.json").write_text(json.dumps(res, indent=1, default=str))
        return 2

    # ---- step 1
    opened_before = OPENED.read_bytes()
    dev = load_v2("dev").scenarios
    val = load_v2("val").scenarios
    adv_path = REPO / "datasets/rift_v3_dev/adversarial_dev.json"
    adv_sha = sha256_file(adv_path)
    adv = json.loads(adv_path.read_bytes())["scenarios"]
    guard = HeldOutGuard()
    guard.allow_oracle(TOKEN)
    guard.activate_token(TOKEN)
    hs = load_v2("held_out", purpose="final", guard=guard, allow_reopen=True)
    guard.deactivate_token()
    held = hs.scenarios
    res["datasets"] = {
        "dev": {"n": len(dev), "sha256": PINS["dev"]["sha256"]},
        "val": {"n": len(val), "sha256": PINS["val"]["sha256"]},
        "held_out": {"n": len(held), "sha256": hs.sha256, "registry_valid_for_final_claims": hs.valid_for_final_claims,
                     "heldout_opened_json_unchanged": OPENED.read_bytes() == opened_before,
                     "heldout_opened_json": json.loads(opened_before)},
        "adversarial_dev": {"n": len(adv), "sha256": adv_sha},
        "guard_access_log": guard.get_access_log()}
    for sp, scs in (("dev", dev), ("val", val), ("held_out", held)):
        res["datasets"][sp]["split_field_values"] = sorted({s["split"] for s in scs})
        res["datasets"][sp]["generator_versions"] = sorted({s["generator_version"] for s in scs})
        res["datasets"][sp]["id_prefixes"] = sorted({s["scenario_id"].split("-")[0] for s in scs})
        res["datasets"][sp]["distinct_seeds"] = len({s["seed"] for s in scs})
        res["datasets"][sp]["distinct_templates"] = len({s["template_id"] for s in scs})
        res["datasets"][sp]["distinct_topologies"] = len({topology_hash(s) for s in scs})
        res["datasets"][sp]["expected_outcome"] = dict(Counter(s["ground_truth"]["expected_outcome"] for s in scs))
        res["datasets"][sp]["abstain_reason"] = dict(Counter(str(s["ground_truth"]["abstain_reason"]) for s in scs))
        res["datasets"][sp]["structure_levels"] = sorted({s["dimensions"]["structure"] for s in scs})
        res["datasets"][sp]["family_levels"] = sorted({s["dimensions"]["family"] for s in scs})

    # ---- step 2: leakage on label-stripped copies, before any method run
    dev_s, val_s, held_s, adv_s = ([strip_labels(s) for s in x] for x in (dev, val, held, adv))
    leak = {
        "val_vs_dev": leak_summary(check_candidate(val_s, {"dev": dev_s})),
        "val_vs_dev_adv": leak_summary(check_candidate(val_s, {"dev": dev_s, "adversarial_dev": adv_s})),
        "held_out_vs_dev_val_adv": leak_summary(check_candidate(held_s, {"dev": dev_s, "val": val_s,
                                                                         "adversarial_dev": adv_s})),
        "held_out_vs_dev_val_adv_at_0.85": leak_summary(check_candidate(held_s, {"dev": dev_s, "val": val_s,
                                                                                  "adversarial_dev": adv_s}, 0.85)),
        "adversarial_dev_vs_dev_val": leak_summary(check_candidate(adv_s, {"dev": dev_s, "val": val_s})),
    }
    vi = verify_independence({"dev": dev_s, "val": val_s, "held_out": held_s}, protected="held_out", near_threshold=0.90)
    leak["verify_independence_dev_val_heldout_0.90"] = {k: vi[k] for k in (
        "ok", "protected_split", "shared_keys_by_pair", "leaks_for_protected", "n_groups", "group_integrity_violations",
        "near_duplicate_pairs_cross_split", "near_threshold", "distinct_keys_per_split",
        "unseen_in_protected_vs_other_splits", "n_scenarios")}
    stored = json.loads((REPO / "datasets/rift_v2/independence_report.json").read_text())
    leak["rederived_matches_stored_independence_report"] = {
        "shared_keys_by_pair": vi["shared_keys_by_pair"] == stored["shared_keys_by_pair"],
        "distinct_keys_per_split": vi["distinct_keys_per_split"] == stored["distinct_keys_per_split"],
        "n_groups": vi["n_groups"] == stored["n_groups"],
        "unseen": vi["unseen_in_protected_vs_other_splits"] == stored["unseen_in_protected_vs_other_splits"]}
    # intra-split dependence units
    clus = {}
    for name, scs in (("val", val_s), ("held_out", held_s)):
        items = {s["scenario_id"]: s for s in scs}
        grp = build_groups(items, [lambda s: ("t", s["template_id"]), lambda s: ("topo", topology_hash(s))])
        clus[name] = {"n": len(scs), "templates": len({s["template_id"] for s in scs}),
                      "topologies": len({topology_hash(s) for s in scs}), "union_find_groups": len(set(grp.values())),
                      "group_sizes": sorted(Counter(grp.values()).values(), reverse=True)}
        clus[name]["_grp"] = grp
    leak["within_split_dependence"] = {k: {a: b for a, b in v.items() if a != "_grp"} for k, v in clus.items()}
    leak["legacy_rift_faults"] = legacy_twin_check()
    res["leakage"] = leak

    # distribution-shift flag inside held-out (levels present only in held-out)
    def shifted(sc):
        d = sc["dimensions"]
        return d["structure"] == SHIFT_STRUCT or d["family"] == SHIFT_FAMILY

    # ---- step 3: pre-run manifest
    script_sha = sha256_file(Path(__file__).resolve())
    pre = {"script_sha256": script_sha, "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "datasets": {k: {kk: vv for kk, vv in v.items() if kk in ("n", "sha256")} for k, v in res["datasets"].items()
                        if isinstance(v, dict) and "sha256" in v},
           "frozen_check": res["frozen_check"], "leakage_ok": {k: v.get("ok") for k, v in leak.items()
                                                              if isinstance(v, dict) and "ok" in v},
           "git_head": res["git_head"], "note": "written after leakage checks and before any V3 run on val/held-out"}
    (OUT / "pre_run_manifest.json").write_text(json.dumps(pre, indent=1, default=str))
    res["pre_run_manifest_sha256"] = sha256_file(OUT / "pre_run_manifest.json")
    res["script_sha256"] = script_sha

    # ---- step 4: one V3-FULL pass per scenario
    cfg = V3_CONFIGS[CFG_KEY]
    runs = {}
    for name, scs in (("val", val), ("held_out", held)):
        t0 = time.time()
        rows = [run_one(sc, cfg) for sc in scs]
        runs[name] = rows
        print(f"[{name}] V3-FULL run complete: n={len(rows)} in {time.time() - t0:.1f}s", flush=True)
        (OUT / f"v3_full_{name}_raw.json").write_text(json.dumps(
            [{"scenario_id": sc["scenario_id"], **r} for sc, r in zip(scs, rows)], indent=1, default=float))

    # ---- regression: V3-FULL on val must equal the saved Sprint 4.4.0 output
    saved_val = json.loads((REPO / "artifacts/sprint4_4_0/v3_val.json").read_text())
    sv = {r["scenario_id"]: r["methods"][CFG_KEY] for r in saved_val}
    mism = [sc["scenario_id"] for sc, r in zip(val, runs["val"])
            if (sv[sc["scenario_id"]]["score"]["answered"], sv[sc["scenario_id"]]["score"]["top1"],
                sv[sc["scenario_id"]]["record"]["n_do"]) != (r["score"]["answered"], r["score"]["top1"], r["record"]["n_do"])]
    res["val_regression_vs_saved_sprint440"] = {"n": len(val), "mismatching_scenarios": mism}

    # ---- step 5: analysis
    saved_v2 = {}
    for name in ("val", "held_out"):
        ps = json.loads((REPO / f"artifacts/sprint4_3_0/results/{name}/per_scenario.json").read_text())
        saved_v2[name] = {r["scenario_id"]: r["methods"] for r in ps}
    saved_dev = {r["scenario_id"]: r["methods"][CFG_KEY] for r in json.loads(
        (REPO / "artifacts/sprint4_4_0/v3_dev.json").read_text())}

    analysis, rowsout, all_p = {}, [], {}
    for name, scs in (("val", val), ("held_out", held)):
        rr = runs[name]
        scores = [r["score"] for r in rr]
        recs = [r["record"] for r in rr]
        sid = [s["scenario_id"] for s in scs]
        tid = [s["template_id"] for s in scs]
        gid = [clus[name]["_grp"][i] for i in sid]
        v2s = [saved_v2[name][i]["RIFT-FULL-V2"]["score"] for i in sid]
        v2r = [saved_v2[name][i]["RIFT-FULL-V2"]["record"] for i in sid]
        b0s = [saved_v2[name][i]["B0-EARLIEST"]["score"] for i in sid]
        b0r = [saved_v2[name][i]["B0-EARLIEST"]["record"] for i in sid]
        aas = aa_scores(scs)
        U = np.array([utility(s, r) for s, r in zip(scores, recs)])
        U2 = np.array([utility(s, r) for s, r in zip(v2s, v2r)])
        UB = np.array([utility(s, r) for s, r in zip(b0s, b0r)])
        # integrity assertions from preregistration section 3.6
        assert all(not (s["correct"] and s["unsafe"]) for s in scores)
        assert U.min() >= -(LAMBDA + GAMMA) - 1e-9 and U.max() <= 1.0 + 1e-9
        a: dict = {"n": len(scs), "agg": bm.aggregate(scores, recs), "agg_v2_saved": bm.aggregate(v2s, v2r),
                   "agg_b0_earliest_saved": bm.aggregate(b0s, b0r), "agg_always_abstain": bm.aggregate(aas, [
                       {"runtime_s": 0.0, "mem_kb": 0.0, "ed_s": 0.0, "n_do": 0, "evidence_type": "NONE",
                        "path_kind": "NONE", "cid_grades": [], "ident_status": None, "error": None} for _ in scs])}
        for k in ("agg", "agg_v2_saved", "agg_b0_earliest_saved", "agg_always_abstain"):
            a[k].pop("accuracy_vs_coverage", None)
        a["method_errors"] = int(sum(1 for r in recs if r["error"]))
        a["utility"] = {
            "v3_mean": float(U.mean()), "v3_scenario_cluster": boot_mean(U, sid), "v3_template_cluster": boot_mean(U, tid),
            "v3_unionfind_group_cluster": boot_mean(U, gid), "v2_mean": float(U2.mean()), "b0_earliest_mean": float(UB.mean()),
            "always_abstain_mean": 0.0, "normalised_U_over_pi": float(U.mean() / (a["agg"]["N_attribute"] / len(scs))),
            "prevalence_attribute_pi": a["agg"]["N_attribute"] / len(scs),
            "v3_minus_v2_template_cluster": st.clustered_bootstrap_diff(U, U2, tid),
            "v3_minus_v2_unionfind_group_cluster": st.clustered_bootstrap_diff(U, U2, gid),
            "lambda_sensitivity_gamma1": {str(l): {"mean": float(np.mean([utility(s, r, l) for s, r in zip(scores, recs)])),
                                                    "ci95_template": boot_mean([utility(s, r, l) for s, r in zip(scores, recs)], tid)["ci95"]}
                                           for l in (0.0, 0.5, 1.0, 2.0, 3.0)},
            "n_do_mean": float(np.mean([r["n_do"] for r in recs]))}
        lo = min(a["utility"]["v3_template_cluster"]["ci95"][0], a["utility"]["v3_unionfind_group_cluster"]["ci95"][0])
        hi = max(a["utility"]["v3_template_cluster"]["ci95"][1], a["utility"]["v3_unionfind_group_cluster"]["ci95"][1])
        a["utility"]["widest_ci95_template_or_group"] = [lo, hi]
        a["utility"]["descriptive_prereg_s10_class_widest_ci"] = classify(lo, hi, float(U.mean()))
        pairs = {}
        for m in ("P1", "P2", "P3_safe"):
            pairs[f"V3_vs_V2|{m}"] = st.compare_pair(scores, v2s, m, tid)
            all_p[f"{name}|V3_vs_V2|{m}"] = pairs[f"V3_vs_V2|{m}"]["mcnemar_exact_p"]
        pairs["V3_vs_AA|P2"] = st.compare_pair(scores, aas, "P2", tid)
        all_p[f"{name}|V3_vs_AA|P2"] = pairs["V3_vs_AA|P2"]["mcnemar_exact_p"]
        a["paired"] = pairs
        a["abstain_required_by_reason"] = {}
        for s, sc_ in zip(scores, scs):
            gt = sc_["ground_truth"]
            if gt["expected_outcome"] == "ABSTAIN_REQUIRED":
                d = a["abstain_required_by_reason"].setdefault(str(gt["abstain_reason"]), {"n": 0, "answered": 0, "correct_name": 0})
                d["n"] += 1
                d["answered"] += int(s["answered"])
                d["correct_name"] += int(s["answered"] and s["top1"] in set(gt["roots"]))
        a["stratified_by_structure"] = bm.stratify(scs, scores, "structure")
        if name == "held_out":
            for lab, flag in (("distribution_shifted(feedback_like|recovery_instability)", True), ("shared_distribution", False)):
                idx = [i for i, sc in enumerate(scs) if shifted(sc) == flag]
                ss = [scores[i] for i in idx]
                rc = [recs[i] for i in idx]
                ag = bm.aggregate(ss, rc)
                ag.pop("accuracy_vs_coverage", None)
                a.setdefault("held_out_shift_strata", {})[lab] = {
                    "n": len(idx), "agg": {k: ag[k] for k in ("N_attribute", "N_abstain_required", "P1_attribution_accuracy",
                                                              "P2_outcome_correct", "unsafe_on_abstain_required",
                                                              "wrong_root_on_attribute", "coverage_overall", "abstention_rate",
                                                              "selective_risk", "abstention_reasons")},
                    "utility_mean": float(U[idx].mean()) if idx else None,
                    "utility_ci95_template": boot_mean(U[idx], [tid[i] for i in idx])["ci95"] if idx else None}
        # context: dev (saved)
        analysis[name] = a
        for sc, s, r, s2, r2, u in zip(scs, scores, recs, v2s, v2r, U):
            gt = sc["ground_truth"]
            rowsout.append({"split": name, "scenario_id": sc["scenario_id"], "template_id": sc["template_id"],
                            "structure": sc["dimensions"]["structure"], "family": sc["dimensions"]["family"],
                            "negative": sc["dimensions"]["negative"], "shifted": shifted(sc) if name == "held_out" else "",
                            "expected": gt["expected_outcome"], "gt_abstain_reason": gt["abstain_reason"],
                            "n_gt_roots": len(gt["roots"]), "v3_status": r.get("status"), "v3_answered": s["answered"],
                            "v3_top1": s["top1"], "v3_correct": s["correct"], "v3_unsafe": s["unsafe"],
                            "v3_abstain_reason": r.get("reason") if not s["answered"] else "", "v3_n_do": r["n_do"],
                            "v3_error": r["error"], "v3_outcome": outcome_str(sc, r, s), "v3_utility": round(float(u), 4),
                            "v2_answered": s2["answered"], "v2_correct": s2["correct"], "v2_unsafe": s2["unsafe"],
                            "v2_utility": round(float(utility(s2, r2)), 4)})
    # dev context from saved Sprint 4.4.0 output (not re-run)
    dsc = [saved_dev[s["scenario_id"]] for s in dev]
    dsc_scores = [d["score"] for d in dsc]
    dsc_recs = [d["record"] for d in dsc]
    ud = np.array([utility(s, r) for s, r in zip(dsc_scores, dsc_recs)])
    ag = bm.aggregate(dsc_scores, dsc_recs)
    ag.pop("accuracy_vs_coverage", None)
    analysis["dev_saved_context"] = {"n": len(dev), "agg": {k: ag[k] for k in (
        "N_attribute", "N_abstain_required", "P1_attribution_accuracy", "P2_outcome_correct", "unsafe_on_abstain_required",
        "wrong_root_on_attribute", "coverage_overall", "abstention_rate")}, "utility_mean": float(ud.mean()),
        "utility_ci95_template": boot_mean(ud, [s["template_id"] for s in dev])["ci95"]}
    # pooled val+held-out uncertainty (descriptive)
    holm_adj = st.holm(all_p)
    for k, v in holm_adj.items():
        sp, cmp_, met = k.split("|")
        analysis[sp]["paired"][f"{cmp_}|{met}"]["holm_p_over_8_tests_descriptive"] = v
    analysis["holm_family_note"] = "8 McNemar tests (val, held_out) x (V3 vs V2: P1,P2,P3_safe; V3 vs AA: P2); descriptive, not a preregistered family"
    res["analysis"] = analysis
    res["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    res["wall_clock_s"] = round(time.time() - t_start, 1)

    (OUT / "analysis.json").write_text(json.dumps(res, indent=1, default=float))
    with open(OUT / "per_scenario.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rowsout[0]))
        w.writeheader()
        w.writerows(rowsout)
    res["outputs_sha256"] = {p.name: sha256_file(p) for p in sorted(OUT.glob("*")) if p.is_file() and p.name != "analysis.json"}
    (OUT / "analysis.json").write_text(json.dumps(res, indent=1, default=float))
    print("done; wall", res["wall_clock_s"], "s; outputs in", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
