"""Statistics for Sprint 4.3.0 (Protocol v2 §6-7). Unit of analysis = SCENARIO; overlapping windows are never samples.

* Wilson CI for single proportions (see benchmark_v2).
* Scenario-clustered (or template-clustered) percentile bootstrap for paired differences.
* Exact two-sided McNemar test (binomial on discordant pairs).
* Paired sign-flip permutation test on per-scenario differences.
* Cohen's h and paired risk difference.
* Holm step-down correction.
All randomness uses an explicit seed.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
from scipy import stats as _sps

BOOT_B = 2000
PERM_N = 10000
STAT_SEED = 430


def paired_indicator_table(a: Sequence[int], b: Sequence[int]) -> Dict[str, int]:
    """2x2 paired table. a, b are 0/1 indicators for the same scenarios (same order)."""
    if len(a) != len(b):
        raise ValueError("paired vectors must have equal length")
    a = np.asarray(a, dtype=int)
    b = np.asarray(b, dtype=int)
    return {"both": int(((a == 1) & (b == 1)).sum()), "only_a": int(((a == 1) & (b == 0)).sum()),
            "only_b": int(((a == 0) & (b == 1)).sum()), "neither": int(((a == 0) & (b == 0)).sum())}


def exact_mcnemar(only_a: int, only_b: int) -> float:
    """Two-sided exact McNemar p-value: binomial test of min(b,c) on n=b+c with p=0.5. n=0 -> 1.0."""
    n = int(only_a) + int(only_b)
    if n == 0:
        return 1.0
    return float(_sps.binomtest(int(min(only_a, only_b)), n, 0.5, alternative="two-sided").pvalue)


def sign_flip_permutation(diff: Sequence[float], n_perm: int = PERM_N, seed: int = STAT_SEED) -> float:
    """Two-sided paired sign-flip permutation p-value on the mean per-scenario difference."""
    d = np.asarray(diff, dtype=float)
    d = d[d != 0.0]                      # zero differences are invariant under sign flips
    if d.size == 0:
        return 1.0
    rng = np.random.default_rng(seed)
    obs = abs(d.mean())
    signs = rng.choice((-1.0, 1.0), size=(n_perm, d.size))
    perm = np.abs((signs * d).mean(axis=1))
    return float((1 + int((perm >= obs - 1e-12).sum())) / (n_perm + 1))


def cohens_h(p1: float, p2: float) -> float:
    return float(2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2)))


def clustered_bootstrap_diff(a: Sequence[float], b: Sequence[float], clusters: Sequence[Any],
                             B: int = BOOT_B, seed: int = STAT_SEED) -> Dict[str, Any]:
    """Percentile bootstrap of mean(a-b), resampling CLUSTERS (scenario id or template id) with replacement.

    Each cluster contributes all its scenarios together, so pairing and within-cluster correlation are preserved.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if len(a) != len(b) or len(a) != len(clusters):
        raise ValueError("a, b and clusters must have equal length")
    d = a - b
    keys = sorted({str(c) for c in clusters})
    idx = {k: [] for k in keys}
    for i, c in enumerate(clusters):
        idx[str(c)].append(i)
    sums = np.array([d[idx[k]].sum() for k in keys])
    cnts = np.array([len(idx[k]) for k in keys], dtype=float)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(keys), size=(B, len(keys)))
    est = sums[draws].sum(axis=1) / cnts[draws].sum(axis=1)
    lo, hi = np.percentile(est, [2.5, 97.5])
    return {"diff": float(d.mean()), "ci95": [float(lo), float(hi)], "n_units": int(len(a)),
            "n_clusters": len(keys), "B": B, "seed": seed}


def holm(pvals: Mapping[str, float]) -> Dict[str, float]:
    """Holm-Bonferroni adjusted p-values (monotone step-down)."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    adj: Dict[str, float] = {}
    running = 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adj[k] = running
    return adj


def metric_vectors(scores: Sequence[Mapping[str, Any]], metric: str) -> Tuple[List[int], List[int]]:
    """(indices into `scores`, 0/1 indicator) for P1 (ATTRIBUTE subset), P2 (all), P3_safe (all; 1 = not unsafe)."""
    if metric == "P1":
        idx = [i for i, s in enumerate(scores) if s["expected"] == "ATTRIBUTE"]
        return idx, [int(scores[i]["correct"]) for i in idx]
    if metric == "P2":
        return list(range(len(scores))), [int(s["p2"]) for s in scores]
    if metric == "P3_safe":
        return list(range(len(scores))), [int(not s["unsafe"]) for s in scores]
    raise ValueError(metric)


def compare_pair(scores_a: Sequence[Mapping[str, Any]], scores_b: Sequence[Mapping[str, Any]], metric: str,
                 template_ids: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """Paired comparison of method A vs B on identical scenarios. Positive diff = A better."""
    if [s["scenario_id"] for s in scores_a] != [s["scenario_id"] for s in scores_b]:
        raise ValueError("methods must be scored on identical scenarios in identical order")
    idx, va = metric_vectors(scores_a, metric)
    _, vb = metric_vectors(scores_b, metric)
    tab = paired_indicator_table(va, vb)
    n = len(va)
    pa = sum(va) / n if n else float("nan")
    pb = sum(vb) / n if n else float("nan")
    out: Dict[str, Any] = {"metric": metric, "n": n, "p_a": pa, "p_b": pb, "paired_table": tab,
                           "risk_difference": pa - pb,
                           "cohens_h": cohens_h(pa, pb) if n else None,
                           "mcnemar_exact_p": exact_mcnemar(tab["only_a"], tab["only_b"]),
                           "permutation_p": sign_flip_permutation(np.asarray(va) - np.asarray(vb)),
                           "discordant": tab["only_a"] + tab["only_b"]}
    sid = [scores_a[i]["scenario_id"] for i in idx]
    out["bootstrap_scenario"] = clustered_bootstrap_diff(va, vb, sid)
    if template_ids is not None:
        tid = [template_ids[i] for i in idx]
        out["bootstrap_template"] = clustered_bootstrap_diff(va, vb, tid)
        lo = min(out["bootstrap_scenario"]["ci95"][0], out["bootstrap_template"]["ci95"][0])
        hi = max(out["bootstrap_scenario"]["ci95"][1], out["bootstrap_template"]["ci95"][1])
        out["ci95_quoted_widest"] = [lo, hi]
    else:
        out["ci95_quoted_widest"] = out["bootstrap_scenario"]["ci95"]
    out["descriptive_only"] = bool(out["discordant"] < 10)
    return out


def confirmatory_family(scores: Mapping[str, Sequence[Mapping[str, Any]]], focal: str,
                        comparators: Sequence[str], template_ids: Optional[Sequence[str]] = None,
                        metrics: Sequence[str] = ("P1", "P2", "P3_safe")) -> Dict[str, Any]:
    """focal vs each comparator x metric; Holm over the whole family (McNemar p-values)."""
    rows: Dict[str, Dict[str, Any]] = {}
    for c in comparators:
        for m in metrics:
            rows[f"{focal}|{c}|{m}"] = compare_pair(scores[focal], scores[c], m, template_ids)
    adj = holm({k: v["mcnemar_exact_p"] for k, v in rows.items()})
    adj_perm = holm({k: v["permutation_p"] for k, v in rows.items()})
    for k, v in rows.items():
        v["holm_p_mcnemar"] = adj[k]
        v["holm_p_permutation"] = adj_perm[k]
        v["significant_holm_0.05"] = bool(adj[k] < 0.05 and v["ci95_quoted_widest"][0] > 0 and not v["descriptive_only"])
        v["interpretation_rule_15_1"] = ("A better (Holm p<0.05 and CI excludes 0)" if v["significant_holm_0.05"]
                                         else "not established")
    return {"family_size": len(rows), "alpha": 0.05, "correction": "Holm", "rows": rows}


# ----- detection (stage-1) metrics -------------------------------------------------------------------------------
def detection_metrics(det: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    tp = sum(1 for d in det if d["fault_present"] and d["detected"])
    fn = sum(1 for d in det if d["fault_present"] and not d["detected"])
    fp = sum(1 for d in det if not d["fault_present"] and d["detected"])
    tn = sum(1 for d in det if not d["fault_present"] and not d["detected"])
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * prec * rec / (prec + rec)) if (prec and rec) else None
    delays = [d["delay_s"] for d in det if d["delay_s"] is not None]
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n_fault": tp + fn, "n_no_fault": fp + tn,
            "precision": prec, "recall": rec, "f1": f1,
            "fpr": (fp / (fp + tn)) if (fp + tn) else None, "fnr": (fn / (tp + fn)) if (tp + fn) else None,
            "delay_s": {"n": len(delays), "median": float(np.median(delays)) if delays else None,
                        "q1": float(np.percentile(delays, 25)) if delays else None,
                        "q3": float(np.percentile(delays, 75)) if delays else None}}
