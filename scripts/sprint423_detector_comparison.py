#!/usr/bin/env python3
"""
Sprint 4.2.3 — Divergence-detector comparison (dev-selected thresholds, held-out once).

Stages
------
  select : choose each detector's threshold on DEVELOPMENT data only and write
           artifacts/sprint4_2_3/thresholds_frozen.json (+ sha256 of that file).
  final  : load the frozen file, evaluate ONCE on held-out data (held-out JSON via
           HeldOutGuard), apply to the saved Stage 4 telemetry, write
           artifacts/sprint4_2_3/detector_comparison.json.
  all    : select then final (default).

Datasets
--------
  DEV   : datasets/rift_faults/development.json + validation.json
          + adversarial cohort scenarios with index 1-3 within each family
          + "stress" regime generator seeds 0..299
  FINAL : held-out split (via HeldOutGuard)
          + adversarial cohort scenarios with index 4-5 within each family
          + "stress" regime generator seeds 1000..1299

Unit of analysis: one (scenario, service) series. Baseline = samples before
injected_at_t; test = samples from injected_at_t onward. Label = whether the
GENERATOR injected a shift into that service (derived from the same rules the
generators use; never fed to a detector).

Synthetic values are zero-mean noise. Relative (%) detectors require a positive
latency level, so all existing-dataset series are shifted by a documented constant
LEVEL_OFFSET_MS = 100 (a modelling assumption).

Selection rule (fixed a priori): among grid points with DEV false-positive rate
<= 5 %, minimise DEV false-negative rate; ties -> lowest FPR, then the LARGEST
(most conservative) threshold values.

Usage: python3 scripts/sprint423_detector_comparison.py [select|final|all]
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
for p in (REPO_ROOT / "scripts", REPO_ROOT / "src", REPO_ROOT):
    sys.path.insert(0, str(p))

from rift.benchmark.adversarial_generator import (  # noqa: E402
    AdversarialScenario,
    generate_adversarial_metrics,
)
from rift.evaluation.held_out_guard import HeldOutGuard  # noqa: E402
from src.rift.evaluation.dataset_registry import (  # noqa: E402
    PURPOSE_FINAL, PURPOSE_SELECTION, SPLIT_DEVELOPMENT, SPLIT_HELD_OUT_TEST,
    SPLIT_VALIDATION, load_split,
)
from rift.statistics.divergence_detectors import DETECTORS, GRIDS  # noqa: E402
from run_reproducible_evaluation import generate_scenario_metrics  # noqa: E402

OUT_DIR = REPO_ROOT / "artifacts" / "sprint4_2_3"
FROZEN = OUT_DIR / "thresholds_frozen.json"
STAGE4_JSON = REPO_ROOT / "artifacts" / "stage4_intervention_results.json"

LEVEL_OFFSET_MS = 100.0
FPR_CAP = 0.05
FIXED = ("existing_stage4_rule", "ebd_r1")  # shipped parameters; never tuned
SERVICES = [
    "frontend", "cart", "checkout", "payment", "product_catalog",
    "recommendation", "shipping", "email", "currency", "ad", "redis_cart",
]
# Dataset files are loaded ONLY through src.rift.evaluation.dataset_registry (repo-root-relative,
# SHA-256/identity verified, held-out sealed behind purpose="final" + HeldOutGuard).

Series = Tuple[np.ndarray, np.ndarray, bool, str]  # baseline, test, label, group


# ─────────────────────────────── series construction ───────────────────────────────

def _split(df, injected_at: float):
    d = df.sort_values("time")
    base = d[d["time"] < injected_at]["value"].to_numpy(float)
    test = d[d["time"] >= injected_at]["value"].to_numpy(float)
    return base + LEVEL_OFFSET_MS, test + LEVEL_OFFSET_MS


def _existing_series(scenarios: List[dict], group: str) -> List[Series]:
    out: List[Series] = []
    for sc in scenarios:
        metrics = generate_scenario_metrics(sc, SERVICES, 10.0, seed=sc.get("seed", 42))
        pos = {sc["root_cause_service"]} | {t for _, t in sc.get("causal_path", [])}
        for svc, df in metrics.items():
            b, t = _split(df, sc.get("injected_at_t", 60.0))
            out.append((b, t, svc in pos, group))
    return out


def _adv_positive(sc: AdversarialScenario) -> set:
    f, p = sc.family, sc.parameters
    pos = {sc.root_cause_service}
    if f == "A_INVERTED":
        pos.add(p.get("victim_service", "frontend"))
    elif f == "B_RETRY":
        pos.add(p.get("child_service", "checkout"))
        pos |= set(sc.affected_services)
    elif f == "C_CONFOUNDED":
        pos |= set(sc.affected_services)
    elif f == "D_MULTI":
        if sc.secondary_root_cause:
            pos.add(sc.secondary_root_cause)
        pos |= set(sc.affected_services)
    elif f == "E_NOISE":
        pos |= set(sc.affected_services)
    elif f == "F_DEEP":
        pos |= {t for _, t in sc.causal_path}
    return pos


def _adv_series(final: bool) -> List[Series]:
    raw = load_split("ADVERSARIAL", purpose=PURPOSE_SELECTION)
    out: List[Series] = []
    for d in raw:
        idx = int(d["scenario_id"].rsplit("_", 1)[1])
        if (idx >= 4) != final:
            continue
        sc = AdversarialScenario(**{**d, "causal_path": [tuple(x) for x in d["causal_path"]]})
        metrics = generate_adversarial_metrics(sc)
        pos = _adv_positive(sc)
        for svc, df in metrics.items():
            b, t = _split(df, sc.injected_at_t)
            out.append((b, t, svc in pos, "ADV_" + sc.family))
    return out


def _stress_series(seeds: range) -> List[Series]:
    """
    Regime generator targeting the checkoutservice failure mode: large absolute
    shifts under high / bimodal / block-constant baselines. 6 pre, 12 test samples.
    Negatives: pure noise, level drift <= 5 ms, a downward shift, and a spontaneous
    mode switch (bimodal service flipping with no injected fault).
    """
    out: List[Series] = []
    for s in seeds:
        rng = np.random.default_rng(90_000 + s)
        level = float(rng.choice([5.0, 50.0, 100.0, 250.0]))
        cv = float(rng.choice([0.02, 0.10, 0.30]))
        sd = level * cv
        blocked = bool(rng.integers(0, 2))      # 30 s plateau structure
        n_pre, n_test = 6, 12

        def noise(n):
            if blocked:
                k = int(math.ceil(n / 3))
                return np.repeat(rng.normal(0, sd, k), 3)[:n]
            return rng.normal(0, sd, n)

        kind = str(rng.choice(["pos", "pos", "neg_null", "neg_drift", "neg_down", "neg_switch"]))
        base = level + noise(n_pre)
        test = level + noise(n_test)
        label = False
        if kind == "pos":
            shift = float(rng.choice([20.0, 40.0, 80.0, 160.0]))
            on = int(rng.integers(0, 4))
            test[on:] += shift
            label = True
        elif kind == "neg_drift":
            test += float(rng.uniform(-5, 5))
        elif kind == "neg_down":
            test -= min(level * 0.5, float(rng.choice([20.0, 40.0, 80.0])))
        elif kind == "neg_switch":
            hi = level + float(rng.choice([60.0, 150.0]))
            base[: n_pre // 2] = hi + noise(n_pre // 2)
            test[:] = np.where(np.arange(n_test) % 6 < 3, hi, level) + noise(n_test)
        out.append((np.maximum(base, 0.1), np.maximum(test, 0.1), label,
                    "STRESS_pos" if label else f"STRESS_{kind}"))
    return out


def build_dev() -> List[Series]:
    s = _existing_series(load_split(SPLIT_DEVELOPMENT, purpose=PURPOSE_SELECTION), "DEV_development")
    s += _existing_series(load_split(SPLIT_VALIDATION, purpose=PURPOSE_SELECTION), "DEV_validation")
    s += _adv_series(final=False)
    s += _stress_series(range(0, 300))
    return s


def build_final() -> List[Series]:
    guard = HeldOutGuard()
    token = "SPRINT_4_2_3_DETECTOR_FINAL_EVAL"
    guard.allow_oracle(token)
    guard.activate_token(token)
    try:
        held = load_split(SPLIT_HELD_OUT_TEST, purpose=PURPOSE_FINAL, guard=guard)
    finally:
        guard.deactivate_token()
    s = _existing_series(held, "FINAL_held_out")
    s += _adv_series(final=True)
    s += _stress_series(range(1000, 1300))
    return s


# ─────────────────────────────────── scoring ───────────────────────────────────

def wilson(k: int, n: int, z: float = 1.96) -> List[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def score(name: str, params: Dict[str, Any], series: List[Series]) -> Dict[str, Any]:
    fn = DETECTORS[name]
    tp = fp = fnn = tn = 0
    by_group: Dict[str, List[int]] = {}
    for b, t, y, g in series:
        flag = bool(fn(b, t, **params).flag)
        tp += flag and y
        fp += flag and not y
        fnn += (not flag) and y
        tn += (not flag) and not y
        c = by_group.setdefault(g, [0, 0, 0, 0])
        c[0 if (flag and y) else 1 if flag else 2 if y else 3] += 1
    npos, nneg = tp + fnn, fp + tn
    return {
        "params": params, "tp": int(tp), "fp": int(fp), "fn": int(fnn), "tn": int(tn),
        "n_pos": int(npos), "n_neg": int(nneg),
        "fpr": round(fp / nneg, 4) if nneg else None, "fpr_ci95": wilson(int(fp), int(nneg)),
        "fnr": round(fnn / npos, 4) if npos else None, "fnr_ci95": wilson(int(fnn), int(npos)),
        "by_group": {g: {"tp": c[0], "fp": c[1], "fn": c[2], "tn": c[3]}
                     for g, c in sorted(by_group.items())},
    }


def _grid_points(name: str) -> List[Dict[str, Any]]:
    grid = GRIDS[name]
    keys = list(grid)
    return [dict(zip(keys, vals)) for vals in itertools.product(*(grid[k] for k in keys))]


# ─────────────────────────────────── stages ───────────────────────────────────

def stage_select() -> Dict[str, Any]:
    dev = build_dev()
    frozen: Dict[str, Any] = {
        "selection_data": "development+validation+adv(1-3)+stress(0-299)",
        "level_offset_ms": LEVEL_OFFSET_MS, "fpr_cap": FPR_CAP,
        "n_series": len(dev), "detectors": {}, "dev_scores": {},
    }
    for name in DETECTORS:
        if name in FIXED:
            frozen["detectors"][name] = {}
            frozen["dev_scores"][name] = score(name, {}, dev)
            continue
        scored = [(p, score(name, p, dev)) for p in _grid_points(name)]
        ok = [(p, s) for p, s in scored if s["fpr"] <= FPR_CAP]
        pool = ok if ok else scored
        best = min(pool, key=lambda ps: (ps[1]["fnr"], ps[1]["fpr"],
                                          tuple(-v for v in ps[0].values())))
        frozen["detectors"][name] = best[0]
        frozen["dev_scores"][name] = {**best[1], "feasible_under_fpr_cap": bool(ok)}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FROZEN.write_text(json.dumps(frozen, indent=2))
    digest = hashlib.sha256(FROZEN.read_bytes()).hexdigest()
    (OUT_DIR / "thresholds_frozen.sha256").write_text(digest + "\n")
    print("Frozen thresholds:", json.dumps(frozen["detectors"]))
    return frozen


def _stage4_check(frozen: Dict[str, Any]) -> Dict[str, Any]:
    d = json.loads(STAGE4_JSON.read_text())
    out: Dict[str, Any] = {}
    for svc in d["pre_baseline"]:
        pre = np.array([x["val"] for x in d["pre_baseline"][svc]]) * 1000.0
        act = np.array([x["val"] for x in d["intervention"][svc]]) * 1000.0
        post = np.array([x["val"] for x in d["post_recovery"][svc]]) * 1000.0
        row: Dict[str, Any] = {
            "pre_mean_ms": round(float(pre.mean()), 2),
            "pre_median_ms": round(float(np.median(pre)), 2),
            "act_mean_ms": round(float(act.mean()), 2),
            "post_median_ms": round(float(np.median(post)), 2),
        }
        for name, params in frozen["detectors"].items():
            fn = DETECTORS[name]
            row[name] = {"active": bool(fn(pre, act, **params).flag),
                         "post_recovery": bool(fn(pre, post, **params).flag)}
        out[svc] = row
    return out


def stage_final() -> Dict[str, Any]:
    frozen = json.loads(FROZEN.read_text())
    expect = (OUT_DIR / "thresholds_frozen.sha256").read_text().strip()
    if hashlib.sha256(FROZEN.read_bytes()).hexdigest() != expect:
        raise SystemExit("thresholds_frozen.json changed after selection; refusing to evaluate.")
    final = build_final()
    res: Dict[str, Any] = {
        "frozen_thresholds_sha256": expect, "level_offset_ms": LEVEL_OFFSET_MS,
        "final_n_series": len(final),
        "frozen_thresholds": frozen["detectors"],
        "final_scores": {n: score(n, p, final) for n, p in frozen["detectors"].items()},
        "dev_scores": frozen["dev_scores"],
        "stage4_saved_telemetry_NOT_USED_FOR_SELECTION": _stage4_check(frozen),
        "caveats": [
            "Synthetic data only; labels come from the generators' own injection rules.",
            "Existing-dataset series use a documented +100 ms level offset (relative detectors depend on it).",
            "Held-out json has 15 scenarios (12 confounded); series are autocorrelated within scenario.",
            "Stage 4 telemetry is n=1 trial, 60 s plateau-structured; not used for selection.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "detector_comparison.json").write_text(json.dumps(res, indent=2))
    return res


def _print(res: Dict[str, Any]) -> None:
    print(f"\n{'detector':<22}{'params':<44}{'FPR dev':>9}{'FNR dev':>9}{'FPR fin':>9}{'FNR fin':>9}")
    for n, s in res["final_scores"].items():
        d = res["dev_scores"][n]
        print(f"{n:<22}{json.dumps(s['params']):<44}{d['fpr']:>9}{d['fnr']:>9}{s['fpr']:>9}{s['fnr']:>9}")
    print("\nStage 4 saved telemetry (active/post flags):")
    for svc, r in res["stage4_saved_telemetry_NOT_USED_FOR_SELECTION"].items():
        print(f"  {svc:<24}" + " ".join(f"{n[:8]}={int(r[n]['active'])}/{int(r[n]['post_recovery'])}"
                                         for n in DETECTORS))


def main() -> None:
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("select", "all"):
        stage_select()
    if stage in ("final", "all"):
        _print(stage_final())


if __name__ == "__main__":
    main()
