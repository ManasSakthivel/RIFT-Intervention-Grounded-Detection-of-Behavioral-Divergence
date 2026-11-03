#!/usr/bin/env python3
"""Agent 7 scratch checks #2 (dev/val only; no method run; compute_cid timed on synthetic arrays). Seed 4511."""
import json, math, time, sys
from pathlib import Path
import numpy as np, networkx as nx
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from src.rift.scenarios import simulator as sim
from src.rift.cid.cid import compute_cid
from scipy import stats
LAM, GAM = 2.0, 1.0
rows = []
for split in ("dev", "val"):
    runs = {r["scenario_id"]: r for r in json.loads((REPO / f"artifacts/sprint4_4_0/v3_{split}.json").read_text())}
    ds = json.loads((REPO / f"datasets/rift_v2/{split}.json").read_text())
    ds = ds if isinstance(ds, list) else ds.get("scenarios", ds)
    for sc in ds:
        m = runs[sc["scenario_id"]]["methods"]["V3-FULL"]; s, rec = m["score"], m["record"]
        g = sim._graph(sc); obs = sim.observed_services(sc)
        n = int(sc["telemetry"]["n_windows"]); t_end = (n - 1) * 10.0
        ts = np.concatenate([t_end + np.arange(30.0), t_end + 30.0 + np.arange(30.0)])
        best = 0.0; has = False
        for y in obs:
            if not any((x != y and not nx.has_path(g, x, y)) for x in obs): continue
            fs = sim.fault_series(sc, g, y, ts)
            d = abs(float((fs[30:].mean() - fs[:30].mean()) / sim.sigma_of(sc, y)))
            best = max(best, d); has = True
        stratum = "none" if best < 0.1 else ("mild" if best < 0.3 else "substantial")
        c, u = int(s["correct"]), int(s["unsafe"])
        rows.append(dict(split=split, exp=s["expected"], stratum=stratum, drift=best, c=c, u=u, nd=rec["n_do"], ans=int(s["answered"]),
                         U=c - LAM * u - GAM * rec["n_do"] / 20, struct=sc["dimensions"]["structure"],
                         abst_with_do=int((not s["answered"]) and rec["n_do"] > 0)))
out = {}
N = len(rows)
out["N"] = N
out["stratum_counts"] = {k: sum(r["stratum"] == k for r in rows) for k in ("none", "mild", "substantial")}
out["stratum_counts_by_split"] = {sp: {k: sum(r["stratum"] == k and r["split"] == sp for r in rows) for k in ("none", "mild", "substantial")} for sp in ("dev", "val")}
for k in ("none", "mild", "substantial"):
    sub = [r for r in rows if r["stratum"] == k]
    out[f"stratum_{k}"] = {"n": len(sub), "meanU": float(np.mean([r["U"] for r in sub])) if sub else None,
                           "unsafe_rate": float(np.mean([r["u"] for r in sub])) if sub else None,
                           "answer_rate": float(np.mean([r["ans"] for r in sub])) if sub else None,
                           "frac_attribute": float(np.mean([r["exp"] == "ATTRIBUTE" for r in sub])) if sub else None}
# gross-value decomposition of V3 at lambda=2,gamma=1
C = np.mean([r["c"] for r in rows]); S = np.mean([r["u"] for r in rows]); cost = np.mean([r["nd"] / 20 for r in rows])
out["decomp"] = {"mean_correct": C, "mean_unsafe": S, "mean_cost_c": cost, "lam*unsafe": LAM * S, "gamma*cost": GAM * cost,
                 "U": C - LAM * S - GAM * cost, "U_if_zero_unsafe_same_correct_same_cost": C - GAM * cost,
                 "U_if_zero_unsafe_zero_cost": C,
                 "cost_from_abstained_after_probing": float(np.mean([r["abst_with_do"] * r["nd"] / 20 for r in rows])),
                 "frac_scenarios_abstained_after_probing": float(np.mean([r["abst_with_do"] for r in rows]))}
# power in the substantial stratum
sd = 0.969
for n_s, deff in [(500, 2.0), (500, 3.0), (300, 2.0)]:
    se = sd * math.sqrt(deff / n_s)
    out[f"stratum_power_n{n_s}_deff{deff}_mu0.10"] = float(stats.norm.cdf(0.10 / se - 1.96))
    out[f"stratum_MDE80_n{n_s}_deff{deff}"] = float((1.96 + 0.8416) * se)
# compute_cid timing, n=30, 1000 perms, 100 boot (synthetic arrays only)
rng = np.random.default_rng(4511)
t0 = time.perf_counter()
R = 40
for i in range(R):
    compute_cid(100 + 8 * rng.normal(size=30), 100 + 8 * rng.normal(size=30), "x", "y", 0.0, alpha=0.05, n_bootstrap=100, n_permutations=1000, seed=i)
out["compute_cid_ms_per_call_n30_perm1000_boot100"] = (time.perf_counter() - t0) / R * 1000
# unequal-info check: SE of DEFF mis-specification when groups ~ templates but true correlation is at structure level (fixed vs random effect)
out["note"] = "stratum membership uses protocol definition (max over y with >=1 observed non-ancestor x) on frozen fault_series"
Path(__file__).with_name("adversarial_checks2.json").write_text(json.dumps(out, indent=1, default=float))
print(json.dumps(out, indent=1, default=float))
