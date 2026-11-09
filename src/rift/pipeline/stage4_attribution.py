"""
Stage 4 offline attribution -- Sprint 4.2.4 (Issue 1).

Converts SAVED Stage 4 telemetry (``artifacts/stage4_intervention_results.json`` format) into the
representation consumed by the RIFT-FULL / EBD pipeline, runs the real learned-graph inference
(FCI -> compute_ebd -> identifiability -> abstention) and returns a prediction.

Replaces the previous hard-coded ``attributed = "cartservice"`` / ``attribution_accuracy_top1 = 1.0``
in ``scripts/stage4_intervention_analysis.py``.

Separation of concerns
----------------------
* :func:`build_evidence` reads ONLY the three telemetry series (``pre_baseline``, ``intervention``,
  ``post_recovery`` is NOT used for inference) and the experiment's intervention record
  (``target_service``). It never reads ``ground_truth``, ``attributed_root_cause``,
  ``attribution_accuracy_top1``, ``verdict`` or ``summary_table`` -- those keys are results/labels.
* :func:`infer` takes the evidence only. It has no label parameter.
* :func:`evaluate_prediction` is the ONLY place a ground-truth label is compared with a prediction,
  and it runs after inference on an already-built prediction object.

Interpretation limits (see docs/SPRINT4_2_4_CRITICAL_REPAIR_REPORT.md)
-----------------------------------------------------------------------
* The Stage 4 experiment is a single trial, so it is a mechanics/consistency check, not a benchmark.
* The intervention target is chosen by the experimenter. R4 evidence for that service is therefore
  intervention-consistent by construction; it is accepted only if the CID evidence itself is
  sufficient (>= 20 samples per side, permutation-significant, above theta_cid).
* Series are plateau-constant (~60 s blocks) with 15 baseline and 12 active samples, so effective
  sample sizes are small and FCI independence tests are weakly powered.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd

from src.rift.cid.cid import compute_cid
from src.rift.cid.evidence import CIDEvidenceStore, grade_name
from src.rift.ebd.ebd import EBDResult, compute_ebd
from src.rift.fci.fci_runner import run_fci
from src.rift.identifiability.identifiability import IdentifiabilityStatus, identify_query

SCHEMA = "rift.stage4_attribution/1"
# The only keys of the saved record that inference may read.
EVIDENCE_KEYS = ("pre_baseline", "intervention", "target_service")
# Keys that are results/labels and must never influence inference.
LABEL_KEYS = ("ground_truth", "attributed_root_cause", "attribution_accuracy_top1", "verdict",
              "summary_table")
S_TO_MS = 1000.0
MIN_BASELINE_SAMPLES = 3
MIN_ACTIVE_SAMPLES = 2
# Same constants run_rift_full_scenario uses for its ranking score (NOT calibrated probabilities).
_CONF_SCORE = {"DEFINITIVE": 0.95, "CANDIDATE": 0.80}


# ───────────────────────────── evidence ─────────────────────────────

@dataclass(frozen=True)
class InterventionRecord:
    """The intervention that was physically applied (an experimental input, not a label)."""
    service_id: str
    applied_at: float          # first sample of the active phase (apply time is not in the series)
    source: str = "target_service"


@dataclass
class Stage4Evidence:
    metrics: Dict[str, pd.DataFrame]                 # pre + active, milliseconds, columns time,value
    baseline_samples: Dict[str, np.ndarray]          # pre phase only (ms)
    active_samples: Dict[str, np.ndarray]            # active phase only (ms)
    baselines: Dict[str, Dict[str, float]]           # mean/std from the pre phase only
    incident_window: Tuple[float, float]             # (first active t, last active t)
    intervention: Optional[InterventionRecord]
    n_pre: int
    n_active: int
    notes: List[str] = field(default_factory=list)


def _series(rows: Any) -> Optional[pd.DataFrame]:
    if not isinstance(rows, list) or not rows:
        return None
    try:
        t = [float(r["t"]) for r in rows]
        v = [float(r["val"]) * S_TO_MS for r in rows]
    except (KeyError, TypeError, ValueError):
        return None
    df = pd.DataFrame({"time": t, "value": v})
    df = df[np.isfinite(df["value"])].sort_values("time").reset_index(drop=True)
    return df if not df.empty else None


def build_evidence(saved: Mapping[str, Any]) -> Stage4Evidence:
    """Convert a saved Stage 4 record into pipeline evidence. Reads EVIDENCE_KEYS only."""
    pre_raw = saved.get("pre_baseline") or {}
    act_raw = saved.get("intervention") or {}
    notes: List[str] = []
    metrics: Dict[str, pd.DataFrame] = {}
    base_s: Dict[str, np.ndarray] = {}
    act_s: Dict[str, np.ndarray] = {}
    baselines: Dict[str, Dict[str, float]] = {}
    t_first_active: List[float] = []
    t_last_active: List[float] = []
    for svc in sorted(set(pre_raw) & set(act_raw)):
        pre, act = _series(pre_raw[svc]), _series(act_raw[svc])
        if pre is None or act is None:
            notes.append(f"{svc}: missing telemetry in pre or active phase; excluded")
            continue
        if len(pre) < MIN_BASELINE_SAMPLES or len(act) < MIN_ACTIVE_SAMPLES:
            notes.append(f"{svc}: too few samples (pre={len(pre)}, active={len(act)}); excluded")
            continue
        metrics[svc] = pd.concat([pre, act], ignore_index=True)
        base_s[svc] = pre["value"].to_numpy(float)
        act_s[svc] = act["value"].to_numpy(float)
        baselines[svc] = {"mean": float(base_s[svc].mean()), "std": float(base_s[svc].std(ddof=1))}
        t_first_active.append(float(act["time"].iloc[0]))
        t_last_active.append(float(act["time"].iloc[-1]))
    window = (min(t_first_active), max(t_last_active)) if t_first_active else (0.0, 0.0)

    intervention: Optional[InterventionRecord] = None
    target = saved.get("target_service")
    if isinstance(target, str) and metrics:
        name = target[len("rift-"):] if target.startswith("rift-") else target
        if name in metrics:
            intervention = InterventionRecord(name, window[0])
        else:
            notes.append(f"intervention target {target!r} has no usable telemetry; no CID evidence")
    return Stage4Evidence(
        metrics=metrics, baseline_samples=base_s, active_samples=act_s, baselines=baselines,
        incident_window=window, intervention=intervention,
        n_pre=min((len(v) for v in base_s.values()), default=0),
        n_active=min((len(v) for v in act_s.values()), default=0), notes=notes,
    )


def build_cid_store(ev: Stage4Evidence) -> CIDEvidenceStore:
    """Real compute_cid(X -> Y) for the applied intervention X over every other observed outcome Y.
    Baseline = Y's pre phase, post = Y's active phase. Grade INSUFFICIENT if n < 20 on either side."""
    store = CIDEvidenceStore()
    if ev.intervention is None:
        return store
    x = ev.intervention.service_id
    for y in sorted(ev.metrics):
        if y == x:
            continue
        store.add(compute_cid(
            baseline_samples=ev.baseline_samples[y], post_intervention_samples=ev.active_samples[y],
            source_variable=x, target_variable=y, t_intervention=ev.intervention.applied_at,
            intervention_record_id=f"stage4:{x}",
        ))
    return store


# ───────────────────────────── inference ─────────────────────────────

@dataclass
class Stage4Prediction:
    predicted_root: Optional[str]
    confidence: float
    confidence_label: str
    abstained: bool
    abstention_reason: Optional[str]
    ebd_candidate: Optional[str]
    ebd_candidate_confidence: str
    ebd_tied_at_t_star: List[str]
    causal_path_kind: str
    evidence_type: str
    cid_grade: str
    cid_evidence: Dict[str, Any]
    detection_timestamp: Optional[float]
    prediction_timestamp: float
    identifiability: Dict[str, Any]
    pag_edges: List[List[str]]
    diverging_services: List[str]
    warnings: List[str]
    parameters: Dict[str, Any]


_GRADE_RANK = {"INSUFFICIENT": 0, "CANDIDATE": 1, "RELIABLE": 2}


def _outcome_node(ebd: List[EBDResult], target: str) -> str:
    """Same rule as scripts/run_reproducible_evaluation.select_outcome_node (learned variant):
    the latest-diverging OTHER service, derived from observed EBD output only."""
    others = [e for e in ebd if e.r1_pass and e.service_id != target]
    return max(others, key=lambda e: e.t_star).service_id if others else target


def _abstain(reason: str, ev: Stage4Evidence, params: Dict[str, Any], *, ebd_candidate=None,
             ebd_conf="NONE", tied=None, kind="NONE", cid_grade="NOT_AVAILABLE", cid_ev=None,
             detection=None, ident=None, edges=None, diverging=None, warnings=None) -> Stage4Prediction:
    return Stage4Prediction(
        predicted_root=None, confidence=0.0, confidence_label="NONE", abstained=True,
        abstention_reason=reason, ebd_candidate=ebd_candidate, ebd_candidate_confidence=ebd_conf,
        ebd_tied_at_t_star=tied or [], causal_path_kind=kind, evidence_type="OBSERVATIONAL",
        cid_grade=cid_grade, cid_evidence=cid_ev or {}, detection_timestamp=detection,
        prediction_timestamp=ev.incident_window[1], identifiability=ident or {},
        pag_edges=edges or [], diverging_services=diverging or [], warnings=(warnings or []) + ev.notes,
        parameters=params,
    )


def infer(
    ev: Stage4Evidence, *, alpha: float = 0.05, seed: int = 42, delta_t: float = 10.0,
    theta_detect: float = 3.0, theta_persist: int = 2, direction: str = "both",
) -> Stage4Prediction:
    """Learned-graph RIFT-FULL inference on Stage 4 evidence. No labels are accepted."""
    params = dict(alpha=alpha, seed=seed, delta_t=delta_t, theta_detect=theta_detect,
                  theta_persist=theta_persist, direction=direction, n_pre=ev.n_pre,
                  n_active=ev.n_active, services=sorted(ev.metrics))
    if len(ev.metrics) < 2 or ev.n_pre < MIN_BASELINE_SAMPLES or ev.n_active < MIN_ACTIVE_SAMPLES:
        return _abstain("INSUFFICIENT_EVIDENCE", ev, params)

    # 1. Learned graph (no oracle fallback: a failed structure search is an abstention)
    wide = pd.concat(
        [m.set_index("time")[["value"]].rename(columns={"value": s}) for s, m in ev.metrics.items()],
        axis=1,
    ).dropna()
    try:
        pag = run_fci(wide, alpha=alpha, max_variables=15, seed=seed)
    except Exception as exc:  # FCI unavailable / singular covariance / too many variables
        return _abstain(f"GRAPH_DISCOVERY_FAILURE:{type(exc).__name__}", ev, params)
    edges = [[e.source, e.target, e.edge_type.value] for e in pag.edges]

    # 2. Interventional evidence (real compute_cid) + EBD
    store = build_cid_store(ev)
    ebd = compute_ebd(
        metrics=ev.metrics, baselines=ev.baselines, pag_result=pag, incident_window=ev.incident_window,
        cid_results=store if len(store) else None, delta_t=delta_t, theta_detect=theta_detect,
        theta_persist=theta_persist, direction=direction,
    )
    diverging = [e.service_id for e in ebd if e.r1_pass]
    passing = [e for e in ebd if e.r1_pass and e.r3_pass]
    if not passing:
        return _abstain("NO_CANDIDATES", ev, params, edges=edges, diverging=diverging)
    top = passing[0]
    tied = [e.service_id for e in passing[1:] if abs(e.t_star - top.t_star) <= delta_t * 0.5]

    # CID evidence quality for the candidate's OWN intervention (if it was the intervened service)
    cid_ev: Dict[str, Any] = {}
    cid_grade = "NOT_AVAILABLE"
    if ev.intervention is not None:
        for y, c in store.for_intervened(top.service_id).items():
            g = grade_name(c) or "INSUFFICIENT"
            cid_ev[f"{top.service_id}\u2192{y}"] = {
                "grade": g, "n_baseline": c.n_baseline, "n_post": c.n_post,
                "w1": c.w1_estimate, "theta_cid": c.theta_cid,
                "permutation_significant": c.permutation_significant,
                "exceeds_threshold": c.exceeds_threshold,
            }
            if cid_grade == "NOT_AVAILABLE" or _GRADE_RANK.get(g, 0) > _GRADE_RANK.get(cid_grade, 0):
                cid_grade = g

    detection = float(top.t_star) if np.isfinite(top.t_star) else None
    common = dict(ebd_candidate=top.service_id, ebd_conf=top.confidence, tied=tied,
                  kind=top.causal_path_kind, cid_grade=cid_grade, cid_ev=cid_ev, detection=detection,
                  edges=edges, diverging=diverging, warnings=list(top.assumption_warnings))

    # 3. Identifiability of the pipeline's query pair; diagnostics for every other diverging service
    outcome = _outcome_node(ebd, top.service_id)
    idr = identify_query(pag_result=pag, source=top.service_id, target=outcome)
    ident = {
        "query": [top.service_id, outcome], "status": idr.status.value, "method": idr.method.value,
        "blocking_reason": idr.blocking_reason,
        "all_pairs": {o: identify_query(pag, top.service_id, o).status.value
                      for o in diverging if o != top.service_id},
    }
    if idr.status == IdentifiabilityStatus.NOT_IDENTIFIABLE:
        return _abstain("NOT_IDENTIFIABLE", ev, params, ident=ident, **common)

    label = top.confidence if top.confidence in _CONF_SCORE else "NONE"
    return Stage4Prediction(
        predicted_root=top.service_id, confidence=_CONF_SCORE.get(label, 0.0), confidence_label=label,
        abstained=False, abstention_reason=None, ebd_candidate=top.service_id,
        ebd_candidate_confidence=top.confidence, ebd_tied_at_t_star=tied,
        causal_path_kind=top.causal_path_kind, evidence_type=top.evidence_type, cid_grade=cid_grade,
        cid_evidence=cid_ev, detection_timestamp=detection, prediction_timestamp=ev.incident_window[1],
        identifiability=ident, pag_edges=edges, diverging_services=diverging,
        warnings=list(top.assumption_warnings) + ev.notes, parameters=params,
    )


# ───────────────────────────── evaluation (post-inference only) ─────────────────────────────

def evaluate_prediction(prediction: Stage4Prediction, ground_truth_root: str) -> Dict[str, Any]:
    """Compare an ALREADY-COMPUTED prediction with a label. Never feeds back into inference."""
    if prediction.abstained:
        outcome, top1 = "ABSTAINED", None
    else:
        top1 = prediction.predicted_root == ground_truth_root
        outcome = "CORRECT" if top1 else "INCORRECT"
    return {
        "ground_truth_root": ground_truth_root,
        "outcome": outcome,
        "top1_correct": top1,
        "coverage": 0.0 if prediction.abstained else 1.0,
        "ebd_candidate_matches_ground_truth": prediction.ebd_candidate == ground_truth_root,
        "n_trials": 1,
        "note": ("Single trial; not a statistical estimate. ABSTAINED is neither correct nor incorrect."),
    }


def ground_truth_from_saved(saved: Mapping[str, Any]) -> Optional[str]:
    """Evaluation-only label read; never passed to build_evidence()/infer()."""
    gt = saved.get("ground_truth")
    return gt if isinstance(gt, str) else None


def analyze_saved_record(
    saved: Mapping[str, Any], *, ground_truth_root: Optional[str] = None, **infer_kwargs: Any,
) -> Dict[str, Any]:
    """Evidence -> inference -> (afterwards) evaluation. Returns the full machine-readable result.

    ``ground_truth_root`` is an evaluation-only argument; when omitted, the label stored in the
    historical record is used. It is consulted only after ``infer`` has returned.
    """
    ev = build_evidence(saved)
    pred = infer(ev, **infer_kwargs)
    gt = ground_truth_root or ground_truth_from_saved(saved)   # read only AFTER pred exists
    evaluation = evaluate_prediction(pred, gt) if gt else {
        "ground_truth_root": None, "outcome": "NO_GROUND_TRUTH", "top1_correct": None}
    p = asdict(pred)
    return {
        "schema": SCHEMA,
        "prediction": p,
        "evaluation": evaluation,                  # evaluation-only; produced after inference
        "summary": {                               # post-hoc join for convenience / machine reading
            "predicted_root": p["predicted_root"],
            "ground_truth_root": evaluation.get("ground_truth_root"),
            "confidence": p["confidence"],
            "abstained": p["abstained"],
            "ebd_candidate": p["ebd_candidate"],
            "causal_path_kind": p["causal_path_kind"],
            "evidence_type": p["evidence_type"],
            "cid_grade": p["cid_grade"],
            "detection_timestamp": p["detection_timestamp"],
            "prediction_timestamp": p["prediction_timestamp"],
        },
        "inputs": {
            "evidence_keys_read": list(EVIDENCE_KEYS),
            "label_keys_ignored_by_inference": list(LABEL_KEYS),
            "evidence_sha256": hashlib.sha256(json.dumps(
                {k: saved.get(k) for k in EVIDENCE_KEYS}, sort_keys=True, default=str).encode()).hexdigest(),
            "n_services": len(ev.metrics), "n_pre": ev.n_pre, "n_active": ev.n_active,
            "incident_window": list(ev.incident_window),
            "intervention": asdict(ev.intervention) if ev.intervention else None,
        },
        "computed_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }
