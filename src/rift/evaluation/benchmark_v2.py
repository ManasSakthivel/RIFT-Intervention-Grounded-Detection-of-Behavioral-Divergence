"""Benchmark core for Sprint 4.3.0: method registry, per-scenario scoring, aggregation (Protocol v2 §3-5, §10-11).

Every method sees exactly the same inputs: ``observe(sc)`` output wrapped in an IncidentContext. Ground truth
(``sc['ground_truth']``) is read only by :func:`score_one` and by the explicitly labelled ORACLE methods.
Abstentions are never dropped; method exceptions become ``METHOD_ERROR:<type>`` abstentions that are counted.
"""
from __future__ import annotations

import importlib.util
import sys
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.rift.evaluation.rift_v2 import CONFIGS, EXPLORATORY_CONFIGS, SharedCache, run_v2  # noqa: E402
from src.rift.fci.fci_runner import PAGEdge, PAGEdgeType, PAGResult  # noqa: E402
from src.rift.scenarios import simulator as sim  # noqa: E402

TIMEOUT_S = 60.0
NO_ALARM_REASONS = ("NO_CANDIDATES", "INSUFFICIENT_BASELINE", "INSUFFICIENT_SAMPLES", "FCI_FAILED",
                    "GRAPH_DISCOVERY_FAILURE", "METHOD_ERROR", "TIMEOUT")


@dataclass(frozen=True)
class MethodSpec:
    method_id: str
    kind: str           # BASELINE | RIFT_VARIANT | ORACLE
    source: str
    oracle: bool = False
    confirmatory: bool = False   # member of the Holm family (non-oracle comparators of RIFT-FULL-V2)


_LEGACY: Dict[str, Any] = {}


def _import_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _legacy() -> Dict[str, Any]:
    if _LEGACY:
        return _LEGACY
    from rift.baselines import IncidentContext  # type: ignore
    from rift.baselines.latency_correlation import LatencyCorrelationBaseline  # type: ignore
    from rift.baselines.oracle import OracleGroundTruth, OracleUpperBound  # type: ignore
    from rift.baselines.rift_obs import RIFTObsBaseline  # type: ignore
    from rift.baselines.rift_one_shot import RIFTOneShotBaseline  # type: ignore
    from rift.baselines.rift_random import RIFTRandomBaseline  # type: ignore
    from rift.baselines.sieve_like import SieveLikeBaseline  # type: ignore
    adv = _import_path("sprint430_adv_baselines_src", REPO_ROOT / "scripts" / "run_adversarial_benchmark.py")
    rre = _import_path("sprint430_rre_src", REPO_ROOT / "scripts" / "run_reproducible_evaluation.py")
    _LEGACY.update(IncidentContext=IncidentContext, B1=LatencyCorrelationBaseline, B3=SieveLikeBaseline,
                   B5=RIFTObsBaseline, B6=RIFTRandomBaseline, B7=RIFTOneShotBaseline,
                   OracleGT=OracleGroundTruth, OracleUB=OracleUpperBound,
                   B0E=adv.EarliestAnomalyBaseline, B0H=adv.HighestAnomalyBaseline,
                   run_rift_full_scenario=rre.run_rift_full_scenario)
    return _LEGACY


REGISTRY: List[MethodSpec] = [
    MethodSpec("B0-EARLIEST", "BASELINE", "scripts/run_adversarial_benchmark.py (inline class)", confirmatory=True),
    MethodSpec("B0-HIGHEST", "BASELINE", "scripts/run_adversarial_benchmark.py (inline class)", confirmatory=True),
    MethodSpec("B1-LATENCY-CORR", "BASELINE", "src/rift/baselines/latency_correlation.py", confirmatory=True),
    MethodSpec("B3-SIEVE-LIKE", "BASELINE", "src/rift/baselines/sieve_like.py", confirmatory=True),
    MethodSpec("B5-RIFT-OBS", "RIFT_VARIANT", "src/rift/baselines/rift_obs.py", confirmatory=True),
    MethodSpec("B6-RIFT-RANDOM", "RIFT_VARIANT", "src/rift/baselines/rift_random.py", confirmatory=True),
    MethodSpec("B7-RIFT-ONE-SHOT", "RIFT_VARIANT", "src/rift/baselines/rift_one_shot.py", confirmatory=True),
    MethodSpec("RIFT-FULL-LEGACY", "RIFT_VARIANT",
               "scripts/run_reproducible_evaluation.py::run_rift_full_scenario (learned FCI)", confirmatory=True),
    MethodSpec("RIFT-FULL-V2", "RIFT_VARIANT", "src/rift/evaluation/rift_v2.py"),
    MethodSpec("RIFT-FULL-V2G", "RIFT_VARIANT",
               "src/rift/evaluation/rift_v2.py (earlier_guard; EXPLORATORY post-hoc, Amendment 3)"),
    MethodSpec("ORACLE:RIFT-FULL-LEGACY-ORACLE-PAG", "ORACLE", "legacy harness, oracle PAG", oracle=True),
    MethodSpec("ORACLE:RIFT-FULL-V2-ORACLE-GRAPH", "ORACLE", "rift_v2 A9", oracle=True),
    MethodSpec("ORACLE:UPPER-BOUND", "ORACLE", "src/rift/baselines/oracle.py", oracle=True),
]
EXCLUDED = [{"method_id": "B4-SAGE-CHAOS", "reason": "deferred stub that always abstains; not a method"}]
ID_NOTES = ("RIFT-ONE-SHOT: class id B7-RIFT-ONE-SHOT, adversarial-script dict key B4-RIFT-ONE-SHOT; "
            "reported under the class id B7. B4-SAGE-CHAOS is excluded (stub).")


def method_ids(include_oracle: bool = True) -> List[str]:
    return [m.method_id for m in REGISTRY if include_oracle or not m.oracle]


def _true_pag(sc: Mapping[str, Any]) -> PAGResult:
    """ORACLE graph over observed services: true edges between observed nodes (hidden ones removed)."""
    obs = set(sim.observed_services(sc))
    edges = [PAGEdge(e["src"], e["dst"], PAGEdgeType.DIRECTED) for e in sc["graph"]["edges"]
             if e["src"] in obs and e["dst"] in obs]
    return PAGResult(variables=sorted(obs), edges=edges, alpha=0.05)


def _desc_set(sc: Mapping[str, Any], r: str) -> set:
    import networkx as nx
    g = nx.DiGraph([(e["src"], e["dst"]) for e in sc["graph"]["edges"]])
    return nx.descendants(g, r) if r in g else set()


def _legacy_oracle_dict(sc: Mapping[str, Any]) -> Dict[str, Any]:
    obs = set(sim.observed_services(sc))
    roots = sc["ground_truth"]["roots"] or sorted(obs)[:1]
    root = roots[0]
    edges = [(e["src"], e["dst"]) for e in sc["graph"]["edges"] if e["src"] in obs and e["dst"] in obs]
    aff = [root] + sorted(n for n in obs if n != root and any(n in _desc_set(sc, r) for r in roots))
    return {"root_cause_service": root, "causal_path": [list(e) for e in edges], "affected_services": aff,
            "confounded": sc["dimensions"]["structure"] in ("confounding", "hidden_common_cause")}


def make_context(sc: Mapping[str, Any], o: Mapping[str, Any]):
    L = _legacy()
    return L["IncidentContext"](fault_id=sc["scenario_id"], incident_window=o["incident_window"],
                                metrics=o["metrics"], baseline_stats=o["baseline_stats"],
                                call_graph=o["call_graph"], scenario_seed=int(sc["seed"]))


def _out_to_rec(out: Any, runtime: float, mem_kb: float, error: Optional[str] = None) -> Dict[str, Any]:
    raw = getattr(out, "raw_output", {}) or {}
    ed = float(out.total_intervention_ed_s or 0.0)
    return {"abstained": bool(out.abstained), "reason": out.abstention_reason,
            "top": [(str(s), float(v)) for s, v in (out.top_candidates or [])][:5],
            "ed_s": ed, "n_do": int(raw.get("n_do", round(ed / 30.0))),
            "evidence_type": raw.get("evidence_type", "OBSERVATIONAL"), "path_kind": raw.get("path_kind", "NONE"),
            "cid_grades": list(raw.get("cid_grades", [])), "ident_status": raw.get("ident_status"),
            "detect_latency_s": out.detection_latency_s, "runtime_s": runtime, "mem_kb": mem_kb, "error": error}


def _timed(fn: Callable[[], Any], measure_mem: bool) -> Tuple[Any, float, float, Optional[str]]:
    if measure_mem:
        tracemalloc.start()
    t0 = time.perf_counter()
    err = None
    out = None
    try:
        out = fn()
    except Exception as exc:  # noqa: BLE001  (recorded and counted as an abstention)
        err = f"METHOD_ERROR:{type(exc).__name__}"
    dt = time.perf_counter() - t0
    peak = 0.0
    if measure_mem:
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    if err is None and dt > TIMEOUT_S:
        err = "TIMEOUT"
    return out, dt, peak / 1024.0, err


def _error_out(spec_id: str, fid: str, reason: str):
    from src.rift.baselines import BaselineOutput
    return BaselineOutput(baseline_id=spec_id, fault_id=fid, top_candidates=[], abstained=True,
                          abstention_reason=reason)


def run_methods(sc: Mapping[str, Any], methods: Optional[Sequence[str]] = None,
                ablations: bool = False, measure_mem: bool = False) -> Dict[str, Dict[str, Any]]:
    """Run every selected method on one scenario with identical inputs. Returns method_id -> record."""
    L = _legacy()
    o = sim.observe(sc)
    ctx = make_context(sc, o)
    seed = int(sc["seed"])
    fid = sc["scenario_id"]
    iv_fn = lambda x, ys, s: sim.intervene(sc, x, ys, s)  # noqa: E731
    want = set(methods) if methods else None
    recs: Dict[str, Dict[str, Any]] = {}

    def add(mid: str, fn: Callable[[], Any]) -> None:
        if want is not None and mid not in want:
            return
        out, dt, mem, err = _timed(fn, measure_mem)
        if out is None:
            out = _error_out(mid, fid, err or "METHOD_ERROR:NoOutput")
        recs[mid] = _out_to_rec(out, dt, mem, err)

    add("B0-EARLIEST", lambda: L["B0E"]().run(ctx))
    add("B0-HIGHEST", lambda: L["B0H"]().run(ctx))
    add("B1-LATENCY-CORR", lambda: L["B1"]().run(ctx))
    add("B3-SIEVE-LIKE", lambda: L["B3"]().run(ctx))
    add("B5-RIFT-OBS", lambda: L["B5"]().run(ctx))
    add("B6-RIFT-RANDOM", lambda: L["B6"](seed=42).run(ctx))
    add("B7-RIFT-ONE-SHOT", lambda: L["B7"]().run(ctx))
    add("RIFT-FULL-LEGACY", lambda: L["run_rift_full_scenario"]({}, ctx, use_oracle_pag=False))
    add("ORACLE:RIFT-FULL-LEGACY-ORACLE-PAG",
        lambda: L["run_rift_full_scenario"](_legacy_oracle_dict(sc), ctx, use_oracle_pag=True))

    gt = sc["ground_truth"]

    def oracle_ub():
        if gt["expected_outcome"] != "ATTRIBUTE":
            return _error_out("ORACLE-UPPER-BOUND", fid, "ORACLE_ABSTAIN_REQUIRED")
        o_gt = L["OracleGT"](ground_truth_service=gt["attributable_roots"][0], ground_truth_fault_type="SYN",
                             ground_truth_causal_path=[])
        return L["OracleUB"](o_gt).run(ctx)
    add("ORACLE:UPPER-BOUND", oracle_ub)

    cache = SharedCache()

    def v2(cfg_key: str, pag=None, shared=None):
        return run_v2(o, iv_fn, fid, seed, {**CONFIGS, **EXPLORATORY_CONFIGS}[cfg_key],
                      cache=shared if shared is not None else cache, pag_override=pag)
    add("RIFT-FULL-V2", lambda: v2("A1-FULL"))
    add("RIFT-FULL-V2G", lambda: v2("V2G-EARLIER-GUARD"))
    add("ORACLE:RIFT-FULL-V2-ORACLE-GRAPH", lambda: v2("A9-ORACLE-GRAPH", pag=_true_pag(sc), shared=SharedCache()))
    if ablations:
        for key in CONFIGS:
            if key == "A1-FULL":
                continue
            pag = _true_pag(sc) if key == "A9-ORACLE-GRAPH" else None
            shared = SharedCache() if key == "A9-ORACLE-GRAPH" else None
            add("ABL:" + key, (lambda k=key, p=pag, sh=shared: v2(k, pag=p, shared=sh)))
    return recs


def score_one(sc: Mapping[str, Any], rec: Mapping[str, Any]) -> Dict[str, Any]:
    gt = sc["ground_truth"]
    exp = gt["expected_outcome"]
    roots = set(gt["roots"])
    ans = not rec["abstained"]
    top1 = rec["top"][0][0] if (ans and rec["top"]) else None
    top3 = [s for s, _ in rec["top"][:3]] if ans else []
    correct = bool(ans and top1 in roots) if exp == "ATTRIBUTE" else False
    p2 = correct if exp == "ATTRIBUTE" else (not ans)
    unsafe = bool(ans and (exp == "ABSTAIN_REQUIRED" or top1 not in roots))
    reason = rec.get("reason")
    alarm = bool(ans or (reason is not None and not str(reason).startswith(NO_ALARM_REASONS)))
    return {"scenario_id": sc["scenario_id"], "split": sc["split"], "expected": exp, "answered": ans,
            "top1": top1, "correct": correct, "p2": bool(p2), "unsafe": unsafe,
            "wrong_root": bool(ans and exp == "ATTRIBUTE" and top1 not in roots),
            "distractor_hit": bool(ans and top1 in set(gt.get("distractors", []))),
            "top3_hit": (bool(ans and any(s in roots for s in top3)) if exp == "ATTRIBUTE" else None),
            "alarm": alarm, "top_score": rec["top"][0][1] if (ans and rec["top"]) else None, "reason": reason}


def stage1_detection(sc: Mapping[str, Any], o: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Method-independent stage-1 detector: EBD R1 persistence on the shared reference statistics."""
    from src.rift.ebd.ebd import _check_r1
    o = o or sim.observe(sc)
    t_first: Optional[float] = None
    for s, df in o["metrics"].items():
        if s not in o["baseline_stats"]:
            continue
        w = df[df["time"] >= o["incident_window"][0]]
        if w.empty:
            continue
        ok, t, _ = _check_r1(w, o["baseline_stats"][s]["mean"], o["baseline_stats"][s]["std"], 3.0, 2, 10.0,
                             o["incident_window"][0], "both", 1)
        if ok and (t_first is None or t < t_first):
            t_first = float(t)
    onset = min((f["onset_s"] for f in sc["faults"]), default=None)
    present = onset is not None
    return {"scenario_id": sc["scenario_id"], "fault_present": present, "detected": t_first is not None,
            "delay_s": (t_first - onset) if (present and t_first is not None) else None}


def _wilson(k: int, n: int, z: float = 1.959964) -> Tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (float(max(0.0, c - h)), float(min(1.0, c + h)))


def _rate(k: int, n: int) -> Dict[str, Any]:
    lo, hi = _wilson(k, n)
    return {"k": int(k), "n": int(n), "value": (k / n) if n else None, "wilson95": [lo, hi]}


def aggregate(scores: Sequence[Mapping[str, Any]], recs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Primary + secondary metrics with explicit numerators/denominators for one method over a scenario set."""
    N = len(scores)
    attr = [s for s in scores if s["expected"] == "ATTRIBUTE"]
    absr = [s for s in scores if s["expected"] == "ABSTAIN_REQUIRED"]
    answered = [s for s in scores if s["answered"]]
    ans_attr = [s for s in attr if s["answered"]]
    out: Dict[str, Any] = {"N": N, "N_attribute": len(attr), "N_abstain_required": len(absr)}
    out["P1_attribution_accuracy"] = _rate(sum(s["correct"] for s in attr), len(attr))
    out["conditional_accuracy_on_answered_attribute"] = _rate(sum(s["correct"] for s in ans_attr), len(ans_attr))
    out["P2_outcome_correct"] = _rate(sum(s["p2"] for s in scores), N)
    out["P3_unsafe_attribution_overall"] = _rate(sum(s["unsafe"] for s in scores), N)
    out["unsafe_on_abstain_required"] = _rate(sum(s["unsafe"] for s in absr), len(absr))
    out["wrong_root_on_attribute"] = _rate(sum(s["wrong_root"] for s in attr), len(attr))
    out["false_attribution_among_answered"] = _rate(sum(s["unsafe"] for s in answered), len(answered))
    out["coverage_overall"] = _rate(len(answered), N)
    out["coverage_on_attribute"] = _rate(len(ans_attr), len(attr))
    out["coverage_on_abstain_required"] = _rate(sum(s["answered"] for s in absr), len(absr))
    out["abstention_rate"] = _rate(N - len(answered), N)
    out["correct_abstention_rate_on_abstain_required"] = _rate(sum(not s["answered"] for s in absr), len(absr))
    out["lost_coverage_on_attribute"] = _rate(len(attr) - len(ans_attr), len(attr))
    out["selective_risk"] = _rate(sum(s["unsafe"] for s in answered), len(answered))
    withtop3 = [s for s in attr if s["top3_hit"] is not None]
    out["top3_on_attribute"] = _rate(sum(bool(s["top3_hit"]) for s in withtop3), len(withtop3))
    out["distractor_top1_among_answered"] = _rate(sum(s["distractor_hit"] for s in answered), len(answered))
    reasons: Dict[str, int] = {}
    for s in scores:
        if not s["answered"]:
            reasons[str(s["reason"])] = reasons.get(str(s["reason"]), 0) + 1
    out["abstention_reasons"] = dict(sorted(reasons.items()))
    ranked = sorted([s for s in answered if s["top_score"] is not None], key=lambda s: -s["top_score"])
    curve, good = [], 0
    for i, s in enumerate(ranked, 1):
        good += int(not s["unsafe"])
        if i == len(ranked) or ranked[i]["top_score"] != s["top_score"]:
            curve.append({"coverage": i / N, "selective_accuracy": good / i, "threshold": s["top_score"]})
    out["accuracy_vs_coverage"] = curve
    rt = [r["runtime_s"] for r in recs]
    out["runtime_s"] = {"mean": float(np.mean(rt)) if rt else None,
                        "p95": float(np.percentile(rt, 95)) if rt else None,
                        "total": float(np.sum(rt)) if rt else 0.0, "n": len(rt)}
    mem = [r["mem_kb"] for r in recs if r["mem_kb"]]
    out["peak_memory_kb"] = {"mean": float(np.mean(mem)) if mem else None,
                             "max": float(np.max(mem)) if mem else None, "n": len(mem)}
    out["intervention"] = {"mean_ed_s": float(np.mean([r["ed_s"] for r in recs])) if recs else 0.0,
                           "total_ed_s": float(np.sum([r["ed_s"] for r in recs])) if recs else 0.0,
                           "mean_perturbations": float(np.mean([r["n_do"] for r in recs])) if recs else 0.0,
                           "modelled_recovery_s_per_scenario":
                               float(np.mean([30.0 * r["n_do"] for r in recs])) if recs else 0.0,
                           "recovery_note": "30 s per rollback is a model constant, not a measurement"}
    ans_recs = [r for r, s in zip(recs, scores) if s["answered"]]
    ev: Dict[str, Any] = {
        "answered": len(ans_recs),
        "interventional": sum(r["evidence_type"] == "INTERVENTIONAL" for r in ans_recs),
        "observational": sum(r["evidence_type"] != "INTERVENTIONAL" for r in ans_recs),
        "path_kind_directed": sum(r["path_kind"] == "DIRECTED" for r in ans_recs),
        "path_kind_semi_directed": sum(r["path_kind"] == "SEMI_DIRECTED" for r in ans_recs),
        "path_kind_none": sum(r["path_kind"] == "NONE" for r in ans_recs)}
    grades: Dict[str, int] = {}
    for r in recs:
        for g in r["cid_grades"]:
            grades[g] = grades.get(g, 0) + 1
    ev["cid_grade_distribution"] = grades
    idq = [r for r in recs if r["ident_status"] is not None]
    ev["identifiability_rate"] = _rate(sum(r["ident_status"] != "NOT_IDENTIFIABLE" for r in idq), len(idq))
    ev["definitive_attribution_rate"] = _rate(ev["interventional"], len(ans_recs))
    out["evidence"] = ev
    out["method_errors"] = sum(1 for r in recs if r["error"])
    return out


def stratify(scs: Sequence[Mapping[str, Any]], scores: Sequence[Mapping[str, Any]], dim: str) -> Dict[str, Any]:
    by: Dict[str, List[Mapping[str, Any]]] = {}
    for sc, s in zip(scs, scores):
        key = sc["dimensions"].get(dim)
        by.setdefault(str(key if key is not None else "none"), []).append(s)
    res: Dict[str, Any] = {}
    for k, ss in sorted(by.items()):
        attr = [s for s in ss if s["expected"] == "ATTRIBUTE"]
        res[k] = {"n": len(ss), "n_attribute": len(attr),
                  "P1": _rate(sum(s["correct"] for s in attr), len(attr)),
                  "P2": _rate(sum(s["p2"] for s in ss), len(ss)),
                  "unsafe": _rate(sum(s["unsafe"] for s in ss), len(ss)),
                  "coverage": _rate(sum(s["answered"] for s in ss), len(ss))}
    return res
