#!/usr/bin/env python3
"""Sprint 4.5.0 Confirmatory Analysis Script (WP4).

Reads the runner's JSONL records file and the labelled confirmatory dataset,
performs the preregistered analysis (SAP §1–§9), and writes a self-contained
report JSON.

Usage:
    python3 scripts/sprint450_analyze.py \\
        --records <records.jsonl> \\
        --labelled <confirm.json> \\
        --out <confirm_analysis.json> \\
        [--prereg <prereg.sha256>]

Hard rules:
  - This script NEVER opens the sealed held-out files.
  - It reads ground_truth ONLY from the LABELLED file, never from method records.
  - The interpretation function is a pure function (C7) imported from confirm_stats.py.
  - Primary inference: stratified group bootstrap-t (B=20000, seed 4505) within structure.
  - Family-block sensitivity: D19, seed 4506.
  - Decision rules: H1 alone at one-sided 0.025; Holm over {H2, H3, H4} conditional on H1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]
for _p in (str(REPO), str(REPO / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402

from src.rift.evaluation import benchmark_v2 as bm  # noqa: E402
from src.rift.statistics.confirmatory_inference import (  # noqa: E402
    ALPHA, DEFAULT_B, DELTA, SEED_FAMILY, SEED_TEMPLATE,
    FixedStrataDesign, check_utility_invariants, gatekeep,
    interpret, interpret_two_key, mcnemar_exact, holm_adjust, utility,
)

# Also use stats_v2 for supporting McNemar (SAP §4)
from src.rift.evaluation.stats_v2 import (  # noqa: E402
    clustered_bootstrap_diff, exact_mcnemar, holm, paired_indicator_table,
)

ALWAYS_ABSTAIN_ID = "ALWAYS-ABSTAIN"
V3_FOCAL = "V3-FULL"
V2_REFERENCE = "RIFT-FULL-V2"
MAX_DO = 20   # PRE 3.1 confirmed in rift_v2
LAMBDA_DEFAULT = 2.0
GAMMA_DEFAULT = 1.0
KAPPA_DEFAULT = 0.05   # intervention cost weight


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_records(records_path: Path) -> List[Dict[str, Any]]:
    recs = []
    for line in records_path.read_text().splitlines():
        line = line.strip()
        if line:
            recs.append(json.loads(line))
    return recs


def _load_labelled(labelled_path: Path) -> Dict[str, Dict[str, Any]]:
    data = json.loads(labelled_path.read_text())
    scenarios = data["scenarios"] if isinstance(data, dict) and "scenarios" in data else data
    return {sc["scenario_id"]: sc for sc in scenarios}


def _check_no_sealed_access(path: Path) -> None:
    for forbidden in ("heldout_candidate", "heldout_status", "results/held_out"):
        if forbidden in str(path).replace("\\", "/"):
            raise RuntimeError(
                f"C11 VIOLATION: refusing to read sealed held-out path: {path}"
            )


def _rate(k: int, n: int) -> Dict[str, Any]:
    lo, hi = bm._wilson(k, n)
    return {"k": int(k), "n": int(n), "value": (k / n if n else None), "wilson95": [lo, hi]}


# ---- utility vector ----------------------------------------------------------
def _utility_vec(scores: List[Dict[str, Any]], records: List[Dict[str, Any]],
                 lam: float = LAMBDA_DEFAULT, gamma: float = GAMMA_DEFAULT) -> np.ndarray:
    correct = np.array([int(s["p2"]) for s in scores], dtype=float)
    unsafe = np.array([int(s["unsafe"]) for s in scores], dtype=float)
    n_do = np.array([r.get("n_do_charged", r.get("n_do", 0)) for r in records], dtype=float)
    return utility(correct, unsafe, n_do, lam=lam, gamma=gamma, max_do=MAX_DO)


# ---- always-abstain ground truth utility (identically 0) ---------------------
def _aa_utility_vec(n: int) -> np.ndarray:
    return np.zeros(n, dtype=float)


# ---- score scenarios from labelled file + records ----------------------------
def _score_from_labels(labelled: Dict[str, Dict[str, Any]],
                       records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Score each record against ground_truth from the labelled file."""
    scores = []
    for rec in records:
        sid = rec["scenario_id"]
        sc = labelled.get(sid)
        if sc is None:
            scores.append({"scenario_id": sid, "expected": None, "answered": bool(not rec.get("abstained", True)),
                           "correct": False, "p2": False, "unsafe": False, "wrong_root": False,
                           "top1": None})
            continue
        scores.append(bm.score_one(sc, rec))
    return scores


# ---- structural covariates ---------------------------------------------------
def _get_covariates(labelled: Dict[str, Dict[str, Any]], sid: str) -> Dict[str, str]:
    sc = labelled.get(sid, {})
    dims = sc.get("dimensions", {})
    return {
        "structure": dims.get("structure", "unknown"),
        "family": dims.get("family", "unknown"),
        "template_id": sc.get("template_id", "unknown"),
    }


# ---- Newcombe paired Wilson CI for paired risk difference --------------------
def _newcombe_paired(n11: int, n10: int, n01: int, n00: int) -> Dict[str, float]:
    n = n11 + n10 + n01 + n00
    if n == 0:
        return {"lo": 0.0, "hi": 0.0}
    p1 = (n11 + n10) / n
    p2 = (n11 + n01) / n
    z = 1.959964
    # Wilson scores for each marginal
    def _ws(p):
        d = 1 + z * z / n
        c = (p + z * z / (2 * n)) / d
        h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
        return max(0.0, c - h), min(1.0, c + h)
    lo1, hi1 = _ws(p1)
    lo2, hi2 = _ws(p2)
    phi = (n11 * n00 - n10 * n01) / (n * n) if n else 0.0
    diff = p1 - p2
    margin = z * np.sqrt(p1 * (1 - p1) / n + p2 * (1 - p2) / n - 2 * phi * np.sqrt(p1 * (1 - p1) * p2 * (1 - p2)) / n)
    return {"diff": float(diff), "lo": float(diff - margin), "hi": float(diff + margin),
            "wilson_lo1": lo1, "wilson_hi1": hi1, "wilson_lo2": lo2, "wilson_hi2": hi2}


# ---- main analysis -----------------------------------------------------------
def analyze(records_path: Path, labelled_path: Path, prereg_path: Optional[Path],
            out_path: Path) -> Dict[str, Any]:
    _check_no_sealed_access(records_path)
    _check_no_sealed_access(labelled_path)

    records_sha = _sha256_file(records_path)
    labelled_sha = _sha256_file(labelled_path)

    if prereg_path and prereg_path.exists():
        prereg_sha = _sha256_file(prereg_path)
        # Verify dataset hash if recorded
        try:
            prereg = json.loads(prereg_path.read_text())
            recorded_dataset_sha = prereg.get("labelled_sha256")
            if recorded_dataset_sha and recorded_dataset_sha != labelled_sha:
                raise RuntimeError(
                    f"INTEGRITY STOP: labelled file SHA-256 {labelled_sha[:16]}... "
                    f"does not match prereg record {recorded_dataset_sha[:16]}..."
                )
        except (ValueError, OSError):
            prereg_sha = _sha256_file(prereg_path)
    else:
        prereg_sha = None

    print(f"[analyze] Loading records from {records_path} ...")
    all_recs = _load_records(records_path)
    print(f"[analyze] {len(all_recs)} records loaded")

    print(f"[analyze] Loading labelled scenarios from {labelled_path} ...")
    labelled = _load_labelled(labelled_path)
    print(f"[analyze] {len(labelled)} labelled scenarios")

    # Group records by method_id
    by_method: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in all_recs:
        by_method[r["method_id"]].append(r)

    scenario_ids = sorted(labelled.keys())
    N = len(scenario_ids)

    report: Dict[str, Any] = {
        "analysis_version": "sprint450_analyze/1.0.0",
        "records_sha256": records_sha,
        "labelled_sha256": labelled_sha,
        "prereg_sha256": prereg_sha,
        "n_scenarios": N,
        "methods_present": list(by_method.keys()),
    }

    # ---- Score all methods --------------------------------------------------
    scores_by_method: Dict[str, List[Dict[str, Any]]] = {}
    records_by_method: Dict[str, List[Dict[str, Any]]] = {}
    for mid, recs in by_method.items():
        # sort by scenario order in labelled file
        rec_map = {r["scenario_id"]: r for r in recs}
        ordered_recs = [rec_map[sid] for sid in scenario_ids if sid in rec_map]
        ordered_scores = _score_from_labels(labelled, ordered_recs)
        scores_by_method[mid] = ordered_scores
        records_by_method[mid] = ordered_recs

    # Always-abstain analytic baseline
    aa_scores = []
    for sid in scenario_ids:
        sc = labelled[sid]
        exp = sc["ground_truth"]["expected_outcome"]
        aa_scores.append({"scenario_id": sid, "expected": exp, "answered": False,
                          "correct": False, "p2": exp == "ABSTAIN_REQUIRED",
                          "unsafe": False, "wrong_root": False, "top1": None})
    scores_by_method[ALWAYS_ABSTAIN_ID] = aa_scores
    aa_recs = [{"scenario_id": sid, "n_do_charged": 0, "n_do": 0, "abstained": True,
                "error_flag": 0} for sid in scenario_ids]
    records_by_method[ALWAYS_ABSTAIN_ID] = aa_recs

    # ---- Record completeness (PRE §11) --------------------------------------
    completion = {}
    for mid, recs in records_by_method.items():
        completion[mid] = len(recs) / N if N else 0.0
    report["completion_by_method"] = completion

    if V3_FOCAL not in scores_by_method:
        report["ERROR"] = f"V3-FULL records not found in {records_path}; cannot compute H1."
        out_path.write_text(json.dumps(report, indent=2, default=float))
        return report

    # ---- Structural covariates for stratified inference ---------------------
    covariates = [_get_covariates(labelled, sid) for sid in scenario_ids]
    structures = [c["structure"] for c in covariates]
    families = [c["family"] for c in covariates]
    templates = [c["template_id"] for c in covariates]

    # ---- Utility vectors ----------------------------------------------------
    def _u_vec(mid):
        return _utility_vec(scores_by_method[mid], records_by_method[mid],
                            lam=LAMBDA_DEFAULT, gamma=GAMMA_DEFAULT)

    u_v3 = _u_vec(V3_FOCAL)
    u_aa = _aa_utility_vec(N)
    u_v2 = _u_vec(V2_REFERENCE) if V2_REFERENCE in scores_by_method else None

    # Invariant check (PRE 3.1)
    u_map = {V3_FOCAL: u_v3, ALWAYS_ABSTAIN_ID: u_aa}
    if u_v2 is not None:
        u_map[V2_REFERENCE] = u_v2
    violations = check_utility_invariants(u_map, lam=LAMBDA_DEFAULT, gamma=GAMMA_DEFAULT)
    report["utility_invariant_violations"] = violations
    if violations:
        print(f"[analyze] WARNING: utility invariant violations: {violations}", file=sys.stderr)

    # ---- Design object (stratified by structure, group = template) ----------
    try:
        design = FixedStrataDesign(structures, templates, families)
    except ValueError as exc:
        report["design_error"] = str(exc)
        out_path.write_text(json.dumps(report, indent=2, default=float))
        return report

    # ---- Primary: H1  d_i = U_V3,i (one-sided, H0: mu <= 0) ----------------
    rng_primary = np.random.default_rng(SEED_TEMPLATE)
    rng_family = np.random.default_rng(SEED_FAMILY)
    h1_d = u_v3  # d_i = U_V3,i − U_AA,i = U_V3,i (AA always 0)

    h1_tmpl = design.template_bootstrap_t(h1_d, B=DEFAULT_B, rng=rng_primary)
    h1_fam = design.family_block_bootstrap_t(h1_d, B=DEFAULT_B, rng=rng_family)

    # Operational utility (kappa = 0.05 cost sensitivity)
    kappa = KAPPA_DEFAULT
    n_do_v3 = np.array([r.get("n_do_charged", r.get("n_do", 0)) for r in records_by_method[V3_FOCAL]], dtype=float)
    correct_v3 = np.array([int(s["p2"]) for s in scores_by_method[V3_FOCAL]], dtype=float)
    unsafe_v3 = np.array([int(s["unsafe"]) for s in scores_by_method[V3_FOCAL]], dtype=float)
    u_op = utility(correct_v3, unsafe_v3, n_do_v3, lam=LAMBDA_DEFAULT, gamma=kappa, max_do=MAX_DO)

    rng_op_tmpl = np.random.default_rng(SEED_TEMPLATE)
    rng_op_fam = np.random.default_rng(SEED_FAMILY)
    h1_op_tmpl = design.template_bootstrap_t(u_op, B=DEFAULT_B, rng=rng_op_tmpl)
    h1_op_fam = design.family_block_bootstrap_t(u_op, B=DEFAULT_B, rng=rng_op_fam)

    h1_verdict = interpret_two_key(h1_tmpl, h1_fam, h1_op_tmpl, h1_op_fam, delta=DELTA)
    report["H1_V3_utility"] = {
        "description": "H1: mean utility of V3-FULL > 0 (always-abstain). Primary endpoint.",
        "template_bootstrap": h1_tmpl.as_dict(),
        "family_block_bootstrap": h1_fam.as_dict(),
        "operational_template_bootstrap": h1_op_tmpl.as_dict(),
        "operational_family_block_bootstrap": h1_op_fam.as_dict(),
        "verdict": h1_verdict,
        "gatekeeping_p": float(h1_tmpl.p),
        "alpha": ALPHA,
    }
    h1_rejected = bool(h1_tmpl.p < ALPHA)

    # ---- Secondary hypotheses H2–H4 (conditional on H1) --------------------
    secondary_p: Dict[str, float] = {}
    secondary_results: Dict[str, Any] = {}

    if u_v2 is not None:
        # H2: V3 – V2 utility difference
        h2_d = u_v3 - u_v2
        rng_h2 = np.random.default_rng(SEED_TEMPLATE)
        rng_h2f = np.random.default_rng(SEED_FAMILY)
        h2_t = design.template_bootstrap_t(h2_d, B=DEFAULT_B, rng=rng_h2)
        h2_f = design.family_block_bootstrap_t(h2_d, B=DEFAULT_B, rng=rng_h2f)

        # H3: unsafe rate V2 - V3 (positive = V3 safer)
        unsafe_v2_arr = np.array([int(s["unsafe"]) for s in scores_by_method[V2_REFERENCE]], dtype=float)
        h3_d = unsafe_v2_arr - unsafe_v3
        rng_h3 = np.random.default_rng(SEED_TEMPLATE)
        rng_h3f = np.random.default_rng(SEED_FAMILY)
        h3_t = design.template_bootstrap_t(h3_d, B=DEFAULT_B, rng=rng_h3)
        h3_f = design.family_block_bootstrap_t(h3_d, B=DEFAULT_B, rng=rng_h3f)

        # H4: coverage V3 - V2 on ATTRIBUTE scenarios only (S11-S14 drop out)
        attr_mask = np.array([labelled[sid]["ground_truth"]["expected_outcome"] == "ATTRIBUTE"
                               for sid in scenario_ids], dtype=bool)
        cov_v3 = np.array([int(s["answered"]) for s in scores_by_method[V3_FOCAL]], dtype=float)
        cov_v2 = np.array([int(s["answered"]) for s in scores_by_method[V2_REFERENCE]], dtype=float)
        h4_d = attr_mask.astype(float) * (cov_v3 - cov_v2)

        # Only include structures that can produce ATTRIBUTE (not S11–S14 analogue)
        hidden_root_like = {"S11_hidden_driver_chain", "S12_hidden_driver_diamond"}
        mutual_like = {"S13_mutual_pair_merge", "S14_mutual_pair_fanout"}
        h4_excl = hidden_root_like | mutual_like
        h4_mask = np.array([c["structure"] not in h4_excl for c in covariates], dtype=bool)
        if h4_mask.sum() > 1:
            h4_structs = [structures[i] for i in range(N) if h4_mask[i]]
            h4_templates = [templates[i] for i in range(N) if h4_mask[i]]
            h4_families = [families[i] for i in range(N) if h4_mask[i]]
            h4_d_filt = h4_d[h4_mask]
            try:
                d4 = FixedStrataDesign(h4_structs, h4_templates, h4_families)
                rng_h4 = np.random.default_rng(SEED_TEMPLATE)
                rng_h4f = np.random.default_rng(SEED_FAMILY)
                h4_t = d4.template_bootstrap_t(h4_d_filt, B=DEFAULT_B, rng=rng_h4)
                h4_f = d4.family_block_bootstrap_t(h4_d_filt, B=DEFAULT_B, rng=rng_h4f)
                secondary_p["H4_coverage"] = float(h4_t.p)
                secondary_results["H4_coverage_V3_minus_V2_ATTRIBUTE_only"] = {
                    "description": "H4: V3 coverage - V2 coverage on ATTRIBUTE scenarios (S11-S14 excluded)",
                    "template_bootstrap": h4_t.as_dict(),
                    "family_block_bootstrap": h4_f.as_dict(),
                    "status": "confirmatory" if h1_rejected else "descriptive, not confirmatory",
                }
            except ValueError as exc:
                secondary_results["H4_error"] = str(exc)

        secondary_p["H2_utility_diff"] = float(h2_t.p)
        secondary_p["H3_safety"] = float(h3_t.p)
        secondary_results["H2_utility_V3_minus_V2"] = {
            "description": "H2: mean utility V3-FULL minus RIFT-FULL-V2 > 0",
            "template_bootstrap": h2_t.as_dict(),
            "family_block_bootstrap": h2_f.as_dict(),
            "status": "confirmatory" if h1_rejected else "descriptive, not confirmatory",
        }
        secondary_results["H3_safety_V2_minus_V3"] = {
            "description": "H3: unsafe rate V2 minus V3 > 0 (V3 is safer)",
            "template_bootstrap": h3_t.as_dict(),
            "family_block_bootstrap": h3_f.as_dict(),
            "status": "confirmatory" if h1_rejected else "descriptive, not confirmatory",
        }

    # Holm adjustment over secondary
    holm_adj = holm_adjust(secondary_p) if secondary_p else {}
    gate = gatekeep(float(h1_tmpl.p), secondary_p, alpha=ALPHA)

    report["gatekeeping"] = gate
    report["holm_adjusted_secondary"] = holm_adj
    report["secondary_hypotheses"] = secondary_results

    # ---- Supporting: paired binary comparisons (SAP §4, McNemar) -----------
    mcnemar_results: Dict[str, Any] = {}
    if V2_REFERENCE in scores_by_method:
        for metric_name, fn_a, fn_b in [
            ("P2_outcome", lambda s: int(s["p2"]), lambda s: int(s["p2"])),
            ("P3_safety", lambda s: int(not s["unsafe"]), lambda s: int(not s["unsafe"])),
        ]:
            a_vec = [fn_a(s) for s in scores_by_method[V3_FOCAL]]
            b_vec = [fn_b(s) for s in scores_by_method[V2_REFERENCE]]
            tab = paired_indicator_table(a_vec, b_vec)
            mc = mcnemar_exact(tab["only_a"], tab["only_b"])
            nc = _newcombe_paired(tab["both"], tab["only_a"], tab["only_b"], tab["neither"])
            mcnemar_results[f"{V3_FOCAL}_vs_{V2_REFERENCE}_{metric_name}"] = {
                "paired_table": tab, "mcnemar": mc, "newcombe_paired": nc,
                "note": "Ignores clustering; supporting evidence only (SAP §4).",
            }
    report["supporting_binary_comparisons"] = mcnemar_results

    # ---- Descriptive breakdowns (SAP §8) ------------------------------------
    breakdowns: Dict[str, Any] = {}
    for mid in [V3_FOCAL, V2_REFERENCE, ALWAYS_ABSTAIN_ID]:
        if mid not in scores_by_method:
            continue
        S = scores_by_method[mid]
        R = records_by_method[mid]
        breakdowns[mid] = bm.aggregate(S, R)
    report["descriptive_aggregates"] = breakdowns

    # Stratum-level breakdowns by structure and family
    strat_struct: Dict[str, Any] = {}
    strat_fam: Dict[str, Any] = {}
    for mid in [V3_FOCAL, V2_REFERENCE, ALWAYS_ABSTAIN_ID]:
        if mid not in scores_by_method:
            continue
        by_s: Dict[str, List] = defaultdict(list)
        by_f: Dict[str, List] = defaultdict(list)
        for i, sid in enumerate(scenario_ids):
            c = covariates[i]
            s = scores_by_method[mid][i] if i < len(scores_by_method[mid]) else None
            if s:
                by_s[c["structure"]].append(s)
                by_f[c["family"]].append(s)
        strat_struct[mid] = {k: _rate(sum(s["p2"] for s in vs), len(vs)) for k, vs in sorted(by_s.items())}
        strat_fam[mid] = {k: _rate(sum(s["p2"] for s in vs), len(vs)) for k, vs in sorted(by_f.items())}
    report["stratum_breakdowns"] = {"by_structure": strat_struct, "by_family": strat_fam}

    # ---- Error accounting (SAP §7) ------------------------------------------
    error_counts: Dict[str, Any] = {}
    for mid, recs in records_by_method.items():
        cnt_s: Dict[str, int] = Counter()
        cnt_t: Dict[str, int] = Counter()
        for r in recs:
            if r.get("error_flag"):
                sid = r["scenario_id"]
                c = _get_covariates(labelled, sid)
                cnt_s[c["structure"]] += 1
                cnt_t[r.get("error_type", "unknown")] += 1
        error_counts[mid] = {
            "total_errors": sum(cnt_s.values()),
            "by_structure": dict(cnt_s),
            "by_error_type": dict(cnt_t),
            "completion_fraction": completion.get(mid, 0.0),
        }
    report["error_accounting"] = error_counts

    # ---- Sensitivity: (lambda, kappa) grid (SAP §9) -------------------------
    lambda_grid = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    kappa_grid = [0.0, 0.025, 0.05, 0.10]
    if V3_FOCAL in scores_by_method:
        grid: Dict[str, Any] = {}
        for lam in lambda_grid:
            for kap in kappa_grid:
                key = f"lam={lam}_kap={kap}"
                u = utility(correct_v3, unsafe_v3, n_do_v3, lam=lam, gamma=kap, max_do=MAX_DO)
                grid[key] = {"mean_utility": float(u.mean()), "positive_fraction": float((u > 0).mean())}
        report["lambda_kappa_sensitivity"] = grid

    # ---- C4 verification: check dev/val numbers (SAP §12.4) ----------------
    # We load dev/val data to verify that the analysis code reproduces known numbers
    dev_path = REPO / "datasets" / "rift_v2" / "dev.json"
    val_path = REPO / "datasets" / "rift_v2" / "val.json"
    if dev_path.exists() and val_path.exists():
        try:
            dev_scs = json.loads(dev_path.read_text())["scenarios"]
            val_scs = json.loads(val_path.read_text())["scenarios"]
            v4_art = REPO / "artifacts" / "sprint4_4_0" / "v3_dev.json"
            v4_val = REPO / "artifacts" / "sprint4_4_0" / "v3_val.json"
            if v4_art.exists() and v4_val.exists():
                dev_rows = json.loads(v4_art.read_text())
                val_rows = json.loads(v4_val.read_text())
                # Recompute V3-FULL utility on dev+val
                dv_scs = {sc["scenario_id"]: sc for sc in dev_scs + val_scs}
                cfg_key = "V3-FULL"
                dv_scores, dv_recs = [], []
                for rows, scs in ((dev_rows, dev_scs), (val_rows, val_scs)):
                    for row in rows:
                        sid = row["scenario_id"]
                        sc = dv_scs[sid]
                        rec = row["methods"].get(cfg_key, {}).get("record")
                        if rec:
                            dv_recs.append(rec)
                            dv_scores.append(bm.score_one(sc, rec))
                if dv_scores:
                    c_dv = np.array([int(s["p2"]) for s in dv_scores], dtype=float)
                    u_dv = np.array([int(s["unsafe"]) for s in dv_scores], dtype=float)
                    nd_dv = np.array([r.get("n_do", 0) for r in dv_recs], dtype=float)
                    u_dv_vec = utility(c_dv, u_dv, nd_dv, lam=LAMBDA_DEFAULT, gamma=GAMMA_DEFAULT, max_do=MAX_DO)
                    report["C4_devval_sanity"] = {
                        "n_devval": len(dv_scores),
                        "mean_utility_V3": float(u_dv_vec.mean()),
                        "reference_mean_utility_V3": -0.338,  # from utility_verification.json
                        "within_tolerance_0.01": abs(u_dv_vec.mean() - (-0.338)) < 0.01,
                        "note": "C4: verify that the analysis code reproduces known dev/val utility",
                    }
        except Exception as exc:  # noqa: BLE001
            report["C4_devval_sanity"] = {"error": str(exc)}

    # ---- Write output -------------------------------------------------------
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, default=float))
    print(f"[analyze] Analysis written to {out_path}")
    print(f"[analyze] H1 p={h1_tmpl.p:.4f}, CI=[{h1_tmpl.lo:.3f}, {h1_tmpl.hi:.3f}], "
          f"verdict={h1_verdict['label']}")
    return report


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Sprint 4.5.0 confirmatory analysis")
    ap.add_argument("--records", required=True,
                    help="Path to the records JSONL file from sprint450_run_confirm.py")
    ap.add_argument("--labelled", required=True,
                    help="Path to the labelled confirmatory JSON file (with ground_truth)")
    ap.add_argument("--out", required=True,
                    help="Output path for analysis JSON report")
    ap.add_argument("--prereg", default=None,
                    help="Path to prereg.sha256 for dataset hash verification")
    args = ap.parse_args(argv)

    analyze(
        records_path=Path(args.records).resolve(),
        labelled_path=Path(args.labelled).resolve(),
        prereg_path=Path(args.prereg).resolve() if args.prereg else None,
        out_path=Path(args.out).resolve(),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
