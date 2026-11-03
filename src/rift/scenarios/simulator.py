"""Synthetic telemetry + intervention simulator for v2 scenarios (Sprint 4.3.0).

Everything here is a *synthetic* environment. Methods never see the scenario record: they receive
only the output of :func:`observe` (series, call graph, reference stats) and, for interventional
methods, the callable :func:`intervene`. Ground truth lives in ``scenario["ground_truth"]`` and is
consumed only by scoring and by the label function in ``generator_v2``.

Model (linear, one sample per window of ``delta_t`` seconds):
    x_s(t) = mu_s + drift(t) + latent_s(t) + fault_s(t) + sigma_s * eps_s(t)
    fault_s(t) = sum_{faults f} sum_{simple paths p: root_f -> s} amp_f * gain_p * h_f(t - lag_p)
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import networkx as nx
import numpy as np
import pandas as pd

DELTA_T = 10.0
REF_WINDOWS = 10               # reference period = first 10 windows (Amendment 2 §1)
INCIDENT_START = REF_WINDOWS * DELTA_T
MU = 100.0


# ---------------------------------------------------------------------------------------- shapes
def shape_value(shape: str, t_rel: float, p: Mapping[str, Any]) -> float:
    """Fault envelope h(t_rel) with t_rel seconds since onset (t_rel<0 -> 0)."""
    if t_rel < 0:
        return 0.0
    if shape == "step":
        return 1.0
    if shape == "ramp":
        return min(1.0, t_rel / (p.get("windows", 8) * DELTA_T))
    if shape == "pulse":
        return 1.0 if t_rel < p.get("windows", 4) * DELTA_T else 0.0
    if shape == "intermittent":
        return 1.0 if (t_rel % 50.0) < 30.0 else 0.0
    if shape == "oscillation":
        return 0.6 + 0.4 * math.sin(2 * math.pi * t_rel / 80.0)
    if shape == "multi_onset":
        return 0.5 if t_rel < 70.0 else 1.0
    if shape == "recovery_delay":
        r = p.get("recover_after_s", 120.0)
        return 1.0 if t_rel < r else math.exp(-(t_rel - r) / 40.0)
    if shape == "partial_recovery":
        return 1.0 if t_rel < 100.0 else 0.4
    if shape == "rebound":
        return 1.0 if t_rel < 80.0 else (0.3 if t_rel < 170.0 else 1.0)
    raise ValueError(f"unknown shape {shape!r}")


# ------------------------------------------------------------------------------------- structure
def _graph(sc: Mapping[str, Any]) -> nx.DiGraph:
    g = nx.DiGraph()
    for n in sc["graph"]["nodes"]:
        g.add_node(n["id"], **{k: v for k, v in n.items() if k != "id"})
    for e in sc["graph"]["edges"]:
        g.add_edge(e["src"], e["dst"], gain=e["gain"], lag=e["lag"])
    return g


def path_responses(g: nx.DiGraph, src: str, dst: str, cap: int = 64) -> List[Tuple[float, float, int]]:
    """[(gain_product, lag_seconds, hops)] over simple paths src->dst (src==dst -> [(1,0,0)])."""
    if src == dst:
        return [(1.0, 0.0, 0)]
    out: List[Tuple[float, float, int]] = []
    if src not in g or dst not in g:
        return out
    for path in nx.all_simple_paths(g, src, dst, cutoff=12):
        gain, lag = 1.0, 0.0
        for a, b in zip(path[:-1], path[1:]):
            gain *= g[a][b]["gain"]
            lag += g[a][b]["lag"] * DELTA_T
        out.append((gain, lag, len(path) - 1))
        if len(out) >= cap:
            break
    return out


def fault_series(sc: Mapping[str, Any], g: nx.DiGraph, svc: str, times: Sequence[float]) -> np.ndarray:
    """Noise-free total fault contribution at ``svc`` over ``times`` (path enumeration done once per fault)."""
    out = np.zeros(len(times))
    for f in sc["faults"]:
        resp = path_responses(g, f["service"], svc)
        if not resp:
            continue
        sp = f.get("shape_params", {})
        for gain, lag, hops in resp:
            shp = f.get("downstream_shape", f["shape"]) if hops > 0 else f["shape"]
            out += f["amp_ms"] * gain * np.array(
                [shape_value(shp, float(t) - f["onset_s"] - lag, sp) for t in times])
    return out


def fault_signal(sc: Mapping[str, Any], g: nx.DiGraph, svc: str, t: float) -> float:
    return float(fault_series(sc, g, svc, [t])[0])


def sigma_of(sc: Mapping[str, Any], svc: str) -> float:
    for n in sc["graph"]["nodes"]:
        if n["id"] == svc:
            return float(n["sigma"])
    raise KeyError(svc)


def observed_services(sc: Mapping[str, Any]) -> List[str]:
    return [n["id"] for n in sc["graph"]["nodes"] if not n.get("hidden")
            and n["id"] not in sc["telemetry"].get("unobserved", [])]


# -------------------------------------------------------------------------------------- telemetry
def _noise(rng: np.random.Generator, n: int, wl: Mapping[str, Any]) -> np.ndarray:
    if wl.get("skew"):
        raw = rng.lognormal(0.0, 0.6, n)
        e = (raw - math.exp(0.18)) / (math.sqrt((math.exp(0.36) - 1) * math.exp(0.36)))
    else:
        e = rng.normal(0.0, 1.0, n)
    if wl.get("burst_p"):
        e = e + (rng.random(n) < wl["burst_p"]) * rng.uniform(3.0, 5.0, n)
    return e


def _latent(rng: np.random.Generator, n: int, phi: float = 0.7) -> np.ndarray:
    x = np.zeros(n)
    eps = rng.normal(0, 1, n) * math.sqrt(1 - phi * phi)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + eps[i]
    return x


def simulate_full(sc: Mapping[str, Any]) -> Dict[str, np.ndarray]:
    """Noise-included true series for ALL nodes (hidden too) on the window grid. Deterministic in seed."""
    rng = np.random.default_rng(int(sc["seed"]))
    tel = sc["telemetry"]
    n = int(tel["n_windows"])
    times = np.arange(n) * DELTA_T
    g = _graph(sc)
    wl = sc.get("workload_params", {})
    drift = wl.get("drift_sigma", 0.0) * np.linspace(0, 1, n)
    latents = {nd["id"]: nd["latent"] for nd in sc["graph"]["nodes"] if nd.get("latent")}
    lat_series = {h: _latent(rng, n) for h in latents}
    out: Dict[str, np.ndarray] = {}
    for nd in sc["graph"]["nodes"]:
        s = nd["id"]
        sig = float(nd["sigma"])
        fs = fault_series(sc, g, s, times)
        lat = np.zeros(n)
        for h, series in lat_series.items():
            if g.has_edge(h, s):
                lat += g[h][s]["gain"] * sig * 0.9 * series
        var_mult = np.ones(n)
        for f in sc["faults"]:
            vm = float(f.get("var_mult", 1.0))
            if vm != 1.0 and f["service"] in g and (s == f["service"] or nx.has_path(g, f["service"], s)):
                var_mult = np.where(times >= f["onset_s"], vm, var_mult)
        eps = _noise(rng, n, wl)
        out[s] = MU + drift * sig + lat + fs + sig * var_mult * eps
    return out


def observe(sc: Mapping[str, Any]) -> Dict[str, Any]:
    """What a method may see: series (absent rows = missing), call graph, reference stats, window."""
    tel = sc["telemetry"]
    n = int(tel["n_windows"])
    times = np.arange(n) * DELTA_T
    full = simulate_full(sc)
    rng = np.random.default_rng(int(sc["seed"]) + 7919)
    metrics: Dict[str, pd.DataFrame] = {}
    for s in observed_services(sc):
        v = full[s].copy()
        d = int(tel.get("delay_windows", {}).get(s, 0))
        if d > 0:
            v = np.concatenate([MU + sigma_of(sc, s) * rng.normal(0, 1, d), v[: n - d]])
        keep = rng.random(n) >= float(tel.get("missing_frac", 0.0))
        if tel.get("sparse_frac"):
            keep &= rng.random(n) >= float(tel["sparse_frac"])
        df = pd.DataFrame({"time": times[keep], "value": v[keep]})
        metrics[s] = df
    stats: Dict[str, Dict[str, float]] = {}
    for s, df in metrics.items():
        ref = df[df["time"] < INCIDENT_START]["value"]
        if len(ref) >= 5:
            stats[s] = {"mean": float(ref.mean()), "std": float(ref.std(ddof=1) + 1e-9)}
    obs = set(metrics)
    cg = nx.DiGraph()
    cg.add_nodes_from(sorted(obs))
    for e in sc["graph"]["edges"]:
        if e["src"] in obs and e["dst"] in obs:
            cg.add_edge(e["src"], e["dst"])
    for a, b in sc["graph"].get("decoy_edges", []):
        if a in obs and b in obs:
            cg.add_edge(a, b)
    return {"metrics": metrics, "baseline_stats": stats, "call_graph": cg,
            "incident_window": (INCIDENT_START, float((n - 1) * DELTA_T))}


# ------------------------------------------------------------------------------ intervention
def intervene(sc: Mapping[str, Any], x: str, outcomes: Sequence[str], seed: int
              ) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """Simulated do(x): 30 s unperturbed + 30 s perturbed window at 1 Hz, per outcome (Amendment 2 §5)."""
    iv = sc["intervention"]
    g = _graph(sc)
    n = int(sc["telemetry"]["n_windows"])
    t_end = (n - 1) * DELTA_T
    rng = np.random.default_rng(int(seed))
    t_base = t_end + np.arange(30.0)
    t_post = t_end + 30.0 + np.arange(30.0)
    delivered = float(iv["delivered"])
    msig = float(iv["magnitude_sigma"])
    perturbed: List[Tuple[str, float]] = [(x, msig * sigma_of(sc, x) * delivered)]
    if iv.get("multi_service") and iv.get("co_target"):
        perturbed.append((iv["co_target"], msig * sigma_of(sc, iv["co_target"]) * delivered))
    leak = iv.get("collateral", {})            # {svc: gain} direct leakage of do(x)
    res: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
    for y in outcomes:
        sig = sigma_of(sc, y)
        eff = np.zeros(60)
        for src, amp in perturbed:
            for gain, lag, _h in path_responses(g, src, y):
                arrive = 30.0 + float(iv.get("delay_s", 0.0)) + 2.0 * lag / DELTA_T
                eff += np.where(np.arange(60) >= arrive, amp * gain, 0.0)
        if y in leak:
            eff += np.where(np.arange(60) >= 30.0, msig * sigma_of(sc, x) * delivered * leak[y], 0.0)
        ts = np.concatenate([t_base, t_post])
        fs = fault_series(sc, g, y, ts)
        vals = MU + fs + eff + sig * _noise(rng, 60, sc.get("workload_params", {}))
        res[y] = (vals[:30], vals[30:])
    return res


# ----------------------------------------------------------------------------- analytic labels
def apparent_signal(sc: Mapping[str, Any], svc: str) -> np.ndarray:
    """Noise-free, delay-shifted fault signal in sigma units on the grid (what the label rule uses)."""
    g = _graph(sc)
    n = int(sc["telemetry"]["n_windows"])
    sig = sigma_of(sc, svc)
    d = int(sc["telemetry"].get("delay_windows", {}).get(svc, 0))
    sig_series = fault_series(sc, g, svc, [k * DELTA_T for k in range(n)]) / sig
    if d > 0:
        sig_series = np.concatenate([np.zeros(d), sig_series[: n - d]])
    return sig_series


def detectable_onset_window(z: np.ndarray, theta: float = 3.0) -> Optional[int]:
    for k in range(REF_WINDOWS, len(z) - 1):
        if abs(z[k]) >= theta and abs(z[k + 1]) >= theta:
            return k
    return None
