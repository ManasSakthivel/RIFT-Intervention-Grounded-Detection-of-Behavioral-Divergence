"""RIFT-FULL-V2 and its ablations (Sprint 4.3.0) — implements Protocol v2 §5.1, §8 and Amendments 1-2.

This is a NEW method evaluated on SYNTHETIC scenarios. Interventions are executed by the scenario
simulator (``rift.scenarios.simulator.intervene``), never on a live system. The method receives only
``observe(sc)`` output and an ``intervene(x, outcomes, seed)`` callable: no ground-truth field.

Evidence typing: a candidate is attributed with ``evidence_type == "INTERVENTIONAL"`` only when R4
(strict ``validate_cid_for_r4`` + Bonferroni across tested outcomes) passes on a simulated do(X).
Observational ablations are typed ``OBSERVATIONAL`` and never claim interventional evidence.
Path kind (DIRECTED vs SEMI_DIRECTED) comes from the EBD result and is reported, never upgraded.
"""
from __future__ import annotations

import math
import random
import zlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import networkx as nx
import numpy as np
import pandas as pd

from src.rift.baselines import BaselineOutput
from src.rift.cid.cid import compute_cid
from src.rift.cid.evidence import validate_cid_for_r4
from src.rift.ebd.ebd import EBDResult, _pag_to_digraph, compute_ebd
from src.rift.fci.fci_runner import PAGEdge, PAGEdgeType, PAGResult, run_fci
from src.rift.identifiability.identifiability import IdentifiabilityStatus, identify_query
from src.rift.optimizer.cost_model import InterventionCandidate, compute_intervention_costs

INCIDENT_START = 100.0
DELTA_T = 10.0
ED_PER_DO_S = 30.0
MAX_DO = 20                       # 600 s budget / 30 s
CID_PERMUTATIONS = 1000
CID_BOOTSTRAP = 100
ALPHA = 0.05


@dataclass(frozen=True)
class V2Config:
    name: str = "RIFT-FULL-V2"
    graph: str = "fci"                # fci | callgraph | oracle
    use_ebd: bool = True
    use_identifiability: bool = True
    use_interventions: bool = True
    cid_mode: str = "cid"             # cid | ztest
    order: str = "msis"               # msis | alpha | random
    oracle: bool = False
    earlier_guard: bool = False       # Amendment 3: abstain if an earlier R1 divergence is unexplained


CONFIGS: Dict[str, V2Config] = {
    "A1-FULL": V2Config("RIFT-FULL-V2"),
    "A2-NO-FCI": V2Config("A2-NO-FCI", graph="callgraph"),
    "A3-NO-EBD": V2Config("A3-NO-EBD", use_ebd=False),
    "A4-NO-CID": V2Config("A4-NO-CID", cid_mode="ztest"),
    "A5-NO-IDENT": V2Config("A5-NO-IDENT", use_identifiability=False),
    "A6-NO-INTERVENTION": V2Config("A6-NO-INTERVENTION", use_interventions=False),
    "A7-NO-MSIS": V2Config("A7-NO-MSIS", order="alpha"),
    "A8-OBSERVATIONAL-ONLY": V2Config("A8-OBSERVATIONAL-ONLY", use_interventions=False,
                                      use_identifiability=False),
    "A9-ORACLE-GRAPH": V2Config("A9-ORACLE-GRAPH", graph="oracle", oracle=True),
    "A10-RANDOM-INTERVENTION": V2Config("A10-RANDOM-INTERVENTION", order="random"),
}
# Post-hoc exploratory variant (Protocol v2 Amendment 3): NOT part of the confirmatory family, NOT an ablation.
EXPLORATORY_CONFIGS: Dict[str, V2Config] = {
    "V2G-EARLIER-GUARD": V2Config("RIFT-FULL-V2G", earlier_guard=True),
}


class SharedCache:
    """Per-scenario cache of deterministic sub-results shared by V2 and its ablations (pure optimisation)."""

    def __init__(self) -> None:
        self.pag: Dict[str, Any] = {}
        self.cid: Dict[Tuple[str, str], Any] = {}
        self.do: Dict[str, Dict[str, Tuple[np.ndarray, np.ndarray]]] = {}


def _abstain(cfg: V2Config, fault_id: str, reason: str, **raw: Any) -> BaselineOutput:
    return BaselineOutput(baseline_id=cfg.name, fault_id=fault_id, top_candidates=[], abstained=True,
                          abstention_reason=reason, raw_output=dict(raw, reason=reason))


def _callgraph_pag(cg: nx.DiGraph) -> PAGResult:
    return PAGResult(variables=sorted(cg.nodes()),
                     edges=[PAGEdge(a, b, PAGEdgeType.DIRECTED) for a, b in cg.edges()], alpha=ALPHA,
                     notes="call-graph substitute (ablation A2): no conditional-independence testing")


def _wide_for_fci(metrics: Mapping[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
    cols = {}
    for s, df in metrics.items():
        sub = df[df["time"] >= INCIDENT_START]
        if len(sub):
            cols[s] = sub.set_index("time")["value"]
    if len(cols) < 2:
        return None
    wide = pd.concat(cols, axis=1).sort_index()
    wide = wide.interpolate(limit=3, limit_area="inside")
    cnt = wide.notna().sum()
    keep = [c for c in wide.columns if cnt[c] >= 0.6 * cnt.max()]
    wide = wide[keep].dropna()
    return wide if wide.shape[1] >= 2 and len(wide) >= 12 else None


def _observational_candidates(usable: Mapping[str, pd.DataFrame], stats: Mapping[str, Mapping[str, float]],
                              window: Tuple[float, float]) -> List[EBDResult]:
    """A3 (no EBD): any service with a single |z| >= 3 in the window; t* = first crossing; ranked by max|z|."""
    out: List[EBDResult] = []
    for s, df in usable.items():
        sub = df[(df["time"] >= window[0]) & (df["time"] <= window[1])]
        if sub.empty:
            continue
        z = ((sub["value"] - stats[s]["mean"]) / stats[s]["std"]).abs()
        hit = sub[z >= 3.0]
        if hit.empty:
            continue
        out.append(EBDResult(result_id=f"obs_{s}", service_id=s, variable_id=f"{s}.divergence",
                             t_star=float(hit["time"].iloc[0]), confidence="CANDIDATE", r1_pass=True,
                             r2_pass=True, r3_pass=True, anomaly_score=float(z.max())))
    out.sort(key=lambda e: -e.anomaly_score)
    return out


def _cid_for(cache: SharedCache, sc_seed: int, x: str, y: str, base: np.ndarray, post: np.ndarray,
             mode: str) -> Any:
    key = (x + "\u2192" + y, mode)
    if key in cache.cid:
        return cache.cid[key]
    if mode == "cid":
        seed = (sc_seed * 1_000_003 + zlib.crc32(f"{x}->{y}".encode())) & 0x7FFFFFFF
        res = compute_cid(base, post, x, y, t_intervention=0.0, alpha=ALPHA, n_bootstrap=CID_BOOTSTRAP,
                          n_permutations=CID_PERMUTATIONS, seed=seed)
    else:
        d = float(np.mean(post) - np.mean(base))
        se = math.sqrt(np.var(base, ddof=1) / len(base) + np.var(post, ddof=1) / len(post)) + 1e-12
        res = {"effect": d, "se": se, "ok": abs(d) > 2.0 * se}
    cache.cid[key] = res
    return res


def run_v2(obs: Mapping[str, Any], intervene_fn: Callable[[str, Sequence[str], int], Dict[str, Any]],
           fault_id: str, scenario_seed: int, cfg: V2Config, cache: Optional[SharedCache] = None,
           pag_override: Optional[PAGResult] = None) -> BaselineOutput:
    cache = cache or SharedCache()
    metrics: Dict[str, pd.DataFrame] = obs["metrics"]
    stats: Dict[str, Dict[str, float]] = obs["baseline_stats"]
    window: Tuple[float, float] = obs["incident_window"]
    raw: Dict[str, Any] = {"config": cfg.name, "evidence_type": "OBSERVATIONAL", "path_kind": "NONE",
                           "cid_grades": [], "n_do": 0, "intervened": [], "confirmed": {}}

    n_ref_ok = sum(1 for df in metrics.values() if int((df["time"] < INCIDENT_START).sum()) >= 8)
    if n_ref_ok < 2:
        return _abstain(cfg, fault_id, "INSUFFICIENT_BASELINE", **raw)
    usable = {s: df for s, df in metrics.items() if s in stats}

    # ---- graph
    if cfg.graph == "oracle":
        if pag_override is None:
            raise ValueError("oracle graph requires pag_override")
        pag = pag_override
    elif cfg.graph == "callgraph":
        pag = _callgraph_pag(obs["call_graph"])
    else:
        if "fci" not in cache.pag:
            wide = _wide_for_fci(metrics)
            if wide is None:
                cache.pag["fci"] = ("ERR", "INSUFFICIENT_SAMPLES")
            else:
                try:
                    cache.pag["fci"] = ("OK", run_fci(wide, alpha=ALPHA, max_variables=15, seed=scenario_seed))
                except Exception as exc:  # noqa: BLE001
                    cache.pag["fci"] = ("ERR", f"GRAPH_DISCOVERY_FAILURE:{type(exc).__name__}")
        tag, val = cache.pag["fci"]
        if tag == "ERR":
            return _abstain(cfg, fault_id, val, **raw)
        pag = val

    # ---- candidates
    if cfg.use_ebd:
        ebd = compute_ebd(metrics=usable, baselines=stats, pag_result=pag, incident_window=window,
                          delta_t=DELTA_T, theta_detect=3.0, theta_persist=2, max_gap_windows=1)
        diverging = {e.service_id: e for e in ebd}
        cands = [e for e in ebd if e.r1_pass and e.r3_pass]
        if not cfg.use_interventions:
            cands = [e for e in cands if e.r2_pass]
    else:
        ebd = _observational_candidates(usable, stats, window)
        diverging = {e.service_id: e for e in ebd}
        cands = list(ebd)
    cands = sorted(cands, key=lambda e: (e.t_star, -e.anomaly_score, e.service_id))
    raw["candidates"] = [e.service_id for e in cands]
    raw["diverging"] = sorted(diverging)
    if not cands:
        return _abstain(cfg, fault_id, "NO_CANDIDATES", **raw)

    # ---- identifiability (observed EBD output only)
    if cfg.use_identifiability:
        target = cands[0].service_id
        others = [e for e in diverging.values() if e.service_id != target]
        outcome = max(others, key=lambda e: e.t_star).service_id if others else target
        if outcome != target:
            idr = identify_query(pag_result=pag, source=target, target=outcome)
            raw["ident_status"] = idr.status.value if hasattr(idr.status, "value") else str(idr.status)
            if idr.status == IdentifiabilityStatus.NOT_IDENTIFIABLE:
                return _abstain(cfg, fault_id, "NOT_IDENTIFIABLE", **raw)

    detect_s = max(0.0, cands[0].t_star - window[0])

    # ---- observational path (A6 / A8)
    if not cfg.use_interventions:
        top = cands[0]
        raw["path_kind"] = top.causal_path_kind
        ranked = [(top.service_id, 0.95 if top.causal_path_kind == "DIRECTED" else 0.80)]
        ranked += [(e.service_id, 0.2) for e in cands[1:5]]
        return BaselineOutput(baseline_id=cfg.name, fault_id=fault_id, top_candidates=ranked, abstained=False,
                              detection_latency_s=detect_s, total_intervention_ed_s=0.0, raw_output=raw)

    # ---- interventional path
    dag = _pag_to_digraph(pag)
    names = [e.service_id for e in cands]
    t_min = min(e.t_star for e in cands)
    post = {e.service_id: math.exp(-(e.t_star - t_min) / 20.0) for e in cands}
    z = sum(post.values())
    post = {k: v / z for k, v in post.items()}
    costs = compute_intervention_costs(
        candidates=[InterventionCandidate(s, f"{s}.latency", "LATENCY", 200.0, 50.0) for s in names],
        causal_graph=obs["call_graph"], candidate_posterior=post, service_count=max(1, len(metrics)))
    util = {c.candidate.service_id: c.utility for c in costs if c.authorized}
    order = [s for s in names if s in util]
    if cfg.order == "msis":
        order.sort(key=lambda s: (-util[s], s))
    elif cfg.order == "alpha":
        order.sort()
    else:
        random.Random(scenario_seed ^ 0xA10).shuffle(order)

    div_names = set(diverging)
    confirmed: Dict[str, Dict[str, float]] = {}
    explained: Set[str] = set()
    intervened: List[str] = []
    ebd_by = {e.service_id: e for e in cands}
    for x in order:
        if len(intervened) >= MAX_DO:
            break
        remaining = [c for c in order if c not in intervened and c != x]
        if x in explained:
            continue
        outcomes = sorted(y for y in div_names if y != x and dag.has_node(x) and dag.has_node(y)
                          and nx.has_path(dag, x, y))
        if not outcomes:
            continue
        if cache.do.get(x) is None:
            seed_do = (scenario_seed * 7919 + zlib.crc32(x.encode())) & 0x7FFFFFFF
            cache.do[x] = intervene_fn(x, outcomes, seed_do)
        have = cache.do[x]
        missing = [y for y in outcomes if y not in have]
        if missing:
            seed_do = (scenario_seed * 7919 + zlib.crc32((x + "+").encode())) & 0x7FFFFFFF
            have.update(intervene_fn(x, missing, seed_do))
        intervened.append(x)
        m = len(outcomes)
        conf_y: Dict[str, float] = {}
        for y in outcomes:
            base, postv = have[y]
            res = _cid_for(cache, scenario_seed, x, y, base, postv, cfg.cid_mode)
            if cfg.cid_mode == "cid":
                ok, _why = validate_cid_for_r4(res, res.theta_cid)
                ok = ok and (res.permutation_pvalue is not None and res.permutation_pvalue < ALPHA / m)
                raw["cid_grades"].append(getattr(res.grade, "value", str(res.grade)))
                w1 = float(res.w1_estimate or 0.0)
            else:
                ok, w1 = bool(res["ok"]), abs(float(res["effect"]))
                raw["cid_grades"].append("ZTEST")
            if ok:
                conf_y[y] = w1
        if conf_y:
            confirmed[x] = conf_y
            explained |= set(conf_y)
        if all(c in explained for c in remaining):
            break

    raw.update(intervened=intervened, n_do=len(intervened),
               confirmed={k: sorted(v) for k, v in confirmed.items()}, evidence_type="INTERVENTIONAL" if confirmed else "OBSERVATIONAL")
    ed = ED_PER_DO_S * len(intervened)
    if not confirmed:
        return BaselineOutput(baseline_id=cfg.name, fault_id=fault_id, top_candidates=[], abstained=True,
                              abstention_reason="INTERVENTION_NOT_VERIFIED", detection_latency_s=detect_s,
                              total_intervention_ed_s=ed, raw_output=dict(raw, reason="INTERVENTION_NOT_VERIFIED"))
    attributed = [x for x in confirmed if x not in explained]
    if not attributed:
        return BaselineOutput(baseline_id=cfg.name, fault_id=fault_id, top_candidates=[], abstained=True,
                              abstention_reason="AMBIGUOUS_ATTRIBUTION", detection_latency_s=detect_s,
                              total_intervention_ed_s=ed, raw_output=dict(raw, reason="AMBIGUOUS_ATTRIBUTION"))
    attributed.sort(key=lambda s: (ebd_by[s].t_star, -max(confirmed[s].values())))
    if cfg.earlier_guard:
        t_top = ebd_by[attributed[0]].t_star
        unresolved = sorted(s for s, e in diverging.items()
                            if e.r1_pass and e.t_star < t_top and s not in explained and s != attributed[0])
        raw["unresolved_earlier"] = unresolved
        if unresolved:
            return BaselineOutput(baseline_id=cfg.name, fault_id=fault_id, top_candidates=[], abstained=True,
                                  abstention_reason="UNRESOLVED_EARLIER_DIVERGENCE", detection_latency_s=detect_s,
                                  total_intervention_ed_s=ed,
                                  raw_output=dict(raw, reason="UNRESOLVED_EARLIER_DIVERGENCE"))
    kinds = {s: ebd_by[s].causal_path_kind for s in attributed}
    raw["path_kind"] = kinds[attributed[0]]
    ranked = [(s, 0.95 if kinds[s] == "DIRECTED" else 0.80) for s in attributed]
    ranked += [(e.service_id, 0.2) for e in cands if e.service_id not in attributed][:5]
    return BaselineOutput(baseline_id=cfg.name, fault_id=fault_id, top_candidates=ranked, abstained=False,
                          detection_latency_s=detect_s, total_intervention_ed_s=ed, raw_output=raw)
