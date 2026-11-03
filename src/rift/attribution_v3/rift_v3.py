"""RIFT-FULL-V3 (Sprint 4.4.0): direction-aware, intervention-grounded root-cause attribution.

NEW method; RIFT-FULL-V2 (src/rift/evaluation/rift_v2.py) is untouched and remains the frozen benchmark reference.
Evaluated on SYNTHETIC scenarios only; interventions are simulated, never live. Receives only ``observe(sc)`` output and an
``intervene(x, outcomes, seed)`` callable. No ground-truth field is read.

What differs from V2 (each item traces to a measured failure in docs/SPRINT4_4_0_ATTRIBUTION_FAILURE_ANALYSIS.md):

1. Candidate set = every service with persistent divergence (EBD R1), NOT only services with a PAG path to another divergent
   service. V2's R3 filter treats PAG skeleton connectivity as ancestry evidence; 83-89% of learned edges are o-o (orientation
   unknown) and a true root was isolated by FCI in 14/57 dev and 6/29 val ATTRIBUTE scenarios, so it was never intervened on.
2. The PAG is not used as causal evidence. Ancestry comes from simulated do(x) (outcomes = all other divergent services,
   Holm-corrected). The PAG is decoded with the corrected causal-learn mark convention and used only for a *contradiction*
   check (an arrowhead pointing at the claimed source on every semi-directed route) and for diagnostics.
3. A positive-control (manipulation check): do(x) is also observed on x itself. If the perturbation is not detectable on x,
   a non-effect on other services is uninterpretable, so x is "unresolved", never "cleared".
4. Source rule: a service is a root candidate only if it has a confirmed downstream effect AND no confirmed effect from any
   other intervened service. Mutual (symmetric) effects leave no source -> abstain. To make that test possible every
   candidate is intervened on (V2 skipped services already "explained" by an earlier do(), which hides mutual effects).
   This choice was made on DEV evidence (V3-NO-SYMMETRY-CHECK vs V3-FULL on dev: unsafe 54 -> 35, P2 104 -> 116).
5. An earlier divergence that could not be resolved (uninformative intervention, budget) blocks attribution.
6. Explicit decision status: DEFINITIVE_ROOT / QUALIFIED_ROOT / POSSIBLE_ROOT / INSUFFICIENT_EVIDENCE / NON_IDENTIFIABLE.
   Only the first two (configurable) are reported as attributions; POSSIBLE_ROOT is never counted as an attribution.

Confidence values are ORDINAL (rank only); they are not probabilities and are not calibrated.
No threshold is introduced: theta_detect=3.0, persist=2, alpha=0.05, CID gate, 30 s do() window are all inherited from V2/CID.
"""
from __future__ import annotations

import zlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

from src.rift.attribution_v3 import pag_semantics as ps
from src.rift.baselines import BaselineOutput
from src.rift.cid.cid import compute_cid
from src.rift.cid.evidence import validate_cid_for_r4
from src.rift.ebd.ebd import EBDResult, compute_ebd
from src.rift.evaluation.rift_v2 import (ALPHA, CID_BOOTSTRAP, CID_PERMUTATIONS, DELTA_T, ED_PER_DO_S, MAX_DO,
                                         SharedCache, _wide_for_fci)
from src.rift.fci.fci_runner import run_fci
from src.rift.identifiability.identifiability import IdentifiabilityStatus, identify_query

DEFINITIVE, QUALIFIED, POSSIBLE, INSUFFICIENT, NON_IDENT = (
    "DEFINITIVE_ROOT", "QUALIFIED_ROOT", "POSSIBLE_ROOT", "INSUFFICIENT_EVIDENCE", "NON_IDENTIFIABLE")


@dataclass(frozen=True)
class V3Config:
    name: str = "RIFT-FULL-V3"
    manipulation_check: bool = True
    earlier_guard: bool = True
    answer_statuses: Tuple[str, ...] = (DEFINITIVE, QUALIFIED)
    divergent_candidates: bool = True      # False => V2-style R3 filter (ablation)
    test_explained: bool = True            # also intervene on services already 'explained' by an earlier do() (symmetry check)


V3_CONFIGS: Dict[str, V3Config] = {
    "V3-FULL": V3Config("RIFT-FULL-V3"),
    "V3-DEFINITIVE-ONLY": V3Config("V3-DEFINITIVE-ONLY", answer_statuses=(DEFINITIVE,)),
    "V3-NO-MANIPULATION-CHECK": V3Config("V3-NO-MANIPULATION-CHECK", manipulation_check=False),
    "V3-NO-EARLIER-GUARD": V3Config("V3-NO-EARLIER-GUARD", earlier_guard=False),
    "V3-R3-CANDIDATES": V3Config("V3-R3-CANDIDATES", divergent_candidates=False),
    "V3-NO-SYMMETRY-CHECK": V3Config("V3-NO-SYMMETRY-CHECK", test_explained=False),
}


def holm_reject(pvals: Mapping[str, float], alpha: float = ALPHA) -> Set[str]:
    """Holm step-down: controls FWER at alpha, uniformly more powerful than Bonferroni, parameter-free."""
    order = sorted(pvals, key=lambda k: (pvals[k], k))
    m = len(order)
    rej: Set[str] = set()
    for i, k in enumerate(order):
        if pvals[k] < alpha / (m - i):
            rej.add(k)
        else:
            break
    return rej


def _abstain(cfg: V3Config, fid: str, reason: str, status: str, **raw: Any) -> BaselineOutput:
    raw = {**raw, "reason": reason, "status": status}
    return BaselineOutput(baseline_id=cfg.name, fault_id=fid, top_candidates=[], abstained=True,
                          abstention_reason=reason, raw_output=raw)


def _learn_pag(metrics: Mapping[str, pd.DataFrame], cache: SharedCache, seed: int):
    if "fci" not in cache.pag:
        wide = _wide_for_fci(metrics)
        if wide is None:
            cache.pag["fci"] = ("ERR", "INSUFFICIENT_SAMPLES")
        else:
            try:
                cache.pag["fci"] = ("OK", run_fci(wide, alpha=ALPHA, max_variables=15, seed=seed))
            except Exception as exc:  # noqa: BLE001
                cache.pag["fci"] = ("ERR", f"GRAPH_DISCOVERY_FAILURE:{type(exc).__name__}")
    return cache.pag["fci"]


def _cid(cache: SharedCache, seed: int, x: str, y: str, base: np.ndarray, post: np.ndarray):
    key = (x + "\u2192" + y, "cid")
    if key not in cache.cid:
        s = (seed * 1_000_003 + zlib.crc32(f"{x}->{y}".encode())) & 0x7FFFFFFF
        cache.cid[key] = compute_cid(base, post, x, y, t_intervention=0.0, alpha=ALPHA, n_bootstrap=CID_BOOTSTRAP,
                                     n_permutations=CID_PERMUTATIONS, seed=s)
    return cache.cid[key]


def _relation_to_path_kind(rel: str) -> str:
    return {ps.DIRECTED_ANCESTOR: "DIRECTED", ps.POSSIBLE_ANCESTOR: "SEMI_DIRECTED"}.get(rel, "NONE")


def run_v3(obs: Mapping[str, Any], intervene_fn: Callable[[str, Sequence[str], int], Dict[str, Any]], fault_id: str,
           scenario_seed: int, cfg: V3Config = V3_CONFIGS["V3-FULL"],
           cache: Optional[SharedCache] = None, pag_override=None) -> BaselineOutput:
    """``pag_override``: a ps.MarkedPAG (ORACLE ablation, labelled privileged by callers)."""
    cache = cache or SharedCache()
    metrics = obs["metrics"]
    stats = obs["baseline_stats"]
    window = obs["incident_window"]
    raw: Dict[str, Any] = {"config": cfg.name, "evidence_type": "OBSERVATIONAL", "path_kind": "NONE", "cid_grades": [],
                           "n_do": 0, "intervened": [], "confirmed": {}}

    if sum(1 for df in metrics.values() if int((df["time"] < 100.0).sum()) >= 8) < 2:
        return _abstain(cfg, fault_id, "INSUFFICIENT_BASELINE", INSUFFICIENT, **raw)
    usable = {s: df for s, df in metrics.items() if s in stats}

    # ---- graph (diagnostic + contradiction check only; inherited availability guard from V2)
    if pag_override is not None:
        mp, pagr = pag_override, None
    else:
        tag, val = _learn_pag(metrics, cache, scenario_seed)
        if tag == "ERR":
            return _abstain(cfg, fault_id, val, INSUFFICIENT, **raw)
        mp = ps.decode_marks(val.variables, val.adjacency_matrix)
        pagr = ps.to_pag_result(mp, val)
    raw["pag_edge_kinds"] = {k: sum(1 for a, b in mp.edges() if mp.kind(a, b) == k)
                             for k in sorted({mp.kind(a, b) for a, b in mp.edges()})}

    # ---- divergence (EBD R1/R2/R3 primitives, unchanged)
    ebd_graph = pagr if pagr is not None else ps.to_pag_result(mp, _FakeTemplate(mp))
    ebd = compute_ebd(metrics=usable, baselines=stats, pag_result=ebd_graph, incident_window=window, delta_t=DELTA_T,
                      theta_detect=3.0, theta_persist=2, max_gap_windows=1)
    diverging: Dict[str, EBDResult] = {e.service_id: e for e in ebd if e.r1_pass}
    if cfg.divergent_candidates:
        cands = list(diverging.values())
    else:
        cands = [e for e in diverging.values() if e.r3_pass]
    cands.sort(key=lambda e: (e.t_star, -e.anomaly_score, e.service_id))
    raw["diverging"] = sorted(diverging)
    raw["candidates"] = [e.service_id for e in cands]
    if not cands:
        return _abstain(cfg, fault_id, "NO_CANDIDATES", INSUFFICIENT, **raw)

    # ---- identifiability (inherited V2 query on the corrected PAG)
    if pagr is not None and len(diverging) > 1:
        target = cands[0].service_id
        outcome = max((e for e in diverging.values() if e.service_id != target), key=lambda e: e.t_star).service_id
        idr = identify_query(pag_result=pagr, source=target, target=outcome)
        raw["ident_status"] = getattr(idr.status, "value", str(idr.status))
        if idr.status == IdentifiabilityStatus.NOT_IDENTIFIABLE:
            return _abstain(cfg, fault_id, "NOT_IDENTIFIABLE", NON_IDENT, **raw)

    detect_s = max(0.0, cands[0].t_star - window[0])
    names = [e.service_id for e in cands]
    div_names = set(diverging)
    if len(div_names) < 2:
        raw["possible_roots"] = names
        return BaselineOutput(baseline_id=cfg.name, fault_id=fault_id, top_candidates=[], abstained=True,
                              abstention_reason="SOLE_DIVERGENCE_NO_CORROBORATION", detection_latency_s=detect_s,
                              total_intervention_ed_s=0.0, raw_output=dict(raw, reason="SOLE_DIVERGENCE_NO_CORROBORATION",
                                                                          status=POSSIBLE))

    # ---- interventions in temporal order; outcomes = all other divergent services (graph-agnostic) + positive control
    confirmed: Dict[str, Dict[str, float]] = {}
    manip_ok: Dict[str, bool] = {}
    explained: Set[str] = set()
    intervened: List[str] = []
    for x in names:
        if len(intervened) >= MAX_DO:
            break
        if x in explained and not cfg.test_explained:
            continue                                  # already shown to be an effect of an intervened service
        others = sorted(y for y in div_names if y != x)
        outs = others + [x]
        seed_do = (scenario_seed * 7919 + zlib.crc32((x + "|v3").encode())) & 0x7FFFFFFF
        if x not in cache.do:
            cache.do[x] = intervene_fn(x, outs, seed_do)
        have = cache.do[x]
        intervened.append(x)
        pv: Dict[str, float] = {}
        w1s: Dict[str, float] = {}
        gate: Dict[str, bool] = {}
        for y in outs:
            base, post = have[y]
            res = _cid(cache, scenario_seed, x, y, base, post)
            raw["cid_grades"].append(getattr(res.grade, "value", str(res.grade)))
            ok, _ = validate_cid_for_r4(res, res.theta_cid)
            gate[y] = bool(ok)
            pv[y] = float(res.permutation_pvalue) if res.permutation_pvalue is not None else 1.0
            w1s[y] = float(res.w1_estimate or 0.0)
        rej = holm_reject({y: pv[y] for y in others})
        conf = {y: w1s[y] for y in others if y in rej and gate[y]}
        manip_ok[x] = bool(gate[x] and pv[x] < ALPHA) if cfg.manipulation_check else True
        if conf:
            confirmed[x] = conf
            explained |= set(conf)
        if not cfg.test_explained and all(c in explained or c in intervened for c in names):
            break

    raw.update(intervened=intervened, n_do=len(intervened), manipulation_check=dict(manip_ok),
               confirmed={k: sorted(v) for k, v in confirmed.items()},
               evidence_type="INTERVENTIONAL" if confirmed else "OBSERVATIONAL")
    ed = ED_PER_DO_S * len(intervened)

    def out_abstain(reason: str, status: str, **extra: Any) -> BaselineOutput:
        return BaselineOutput(baseline_id=cfg.name, fault_id=fault_id, top_candidates=[], abstained=True,
                              abstention_reason=reason, detection_latency_s=detect_s, total_intervention_ed_s=ed,
                              raw_output=dict(raw, reason=reason, status=status, **extra))

    resolved = {x for x in intervened if manip_ok.get(x, False) or x in confirmed}
    unresolved = sorted(u for u in names if u not in explained and u not in resolved)
    raw["unresolved"] = unresolved
    if not confirmed:
        raw["possible_roots"] = names[:3]
        if intervened and not any(manip_ok.get(x, False) for x in intervened):
            return out_abstain("INTERVENTION_UNINFORMATIVE", POSSIBLE)
        return out_abstain("INTERVENTION_NOT_VERIFIED", POSSIBLE)
    sources = [x for x in confirmed if not any(x in confirmed[z] for z in confirmed if z != x)]
    if not sources:
        return out_abstain("AMBIGUOUS_ATTRIBUTION", INSUFFICIENT)
    byname = {e.service_id: e for e in cands}
    sources.sort(key=lambda s: (byname[s].t_star, -max(confirmed[s].values()), s))
    top = sources[0]
    raw["sources"] = sources
    if cfg.earlier_guard:
        blockers = [u for u in unresolved if diverging[u].t_star < diverging[top].t_star]
        raw["unresolved_earlier"] = blockers
        if blockers:
            return out_abstain("UNRESOLVED_EARLIER_DIVERGENCE", INSUFFICIENT)

    rel = {y: ps.classify_relation(mp, top, y) for y in confirmed[top]}
    contradicted = sorted(y for y, r in rel.items() if r in (ps.OBSERVATIONAL_ASSOCIATION, ps.SEMI_DIRECTED_CONNECTION))
    best_rel = (ps.DIRECTED_ANCESTOR if ps.DIRECTED_ANCESTOR in rel.values() else
                ps.POSSIBLE_ANCESTOR if ps.POSSIBLE_ANCESTOR in rel.values() else ps.NO_SUPPORTED_RELATIONSHIP)
    raw.update(pag_relations=rel, pag_contradicted=contradicted, path_kind=_relation_to_path_kind(best_rel))
    caveats = []
    if len(sources) > 1:
        caveats.append("MULTIPLE_INTERVENTIONAL_SOURCES")
    if unresolved:
        caveats.append("UNRESOLVED_DIVERGENCE")
    if contradicted:
        caveats.append("PAG_CONTRADICTS_INTERVENTION")
    raw["caveats"] = caveats
    status = DEFINITIVE if not caveats else QUALIFIED
    raw["status"] = status
    if status not in cfg.answer_statuses:
        raw["possible_roots"] = sources
        return out_abstain("NOT_ANSWERED_AT_THIS_OPERATING_POINT", status)
    score = 1.0 if status == DEFINITIVE else 0.5                      # ordinal, NOT a probability
    ranked = [(s, score if s == top else 0.25) for s in sources]
    ranked += [(e.service_id, 0.1) for e in cands if e.service_id not in sources][:5]
    return BaselineOutput(baseline_id=cfg.name, fault_id=fault_id, top_candidates=ranked, abstained=False,
                          detection_latency_s=detect_s, total_intervention_ed_s=ed, raw_output=raw)


class _FakeTemplate:
    """Template for ps.to_pag_result when only a MarkedPAG (oracle) is available."""
    def __init__(self, mp: ps.MarkedPAG):
        self.variables = list(mp.variables)
        self.adjacency_matrix = None
        self.alpha = ALPHA
        self.n_samples_used = 0
        self.n_variables = len(mp.variables)
