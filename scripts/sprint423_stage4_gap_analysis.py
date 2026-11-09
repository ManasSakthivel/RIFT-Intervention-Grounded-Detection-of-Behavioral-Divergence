#!/usr/bin/env python3
"""
Sprint 4.2.3 §5 — analysis of the "50 ms injected vs ~230 ms observed" gap using ONLY
saved artifacts (artifacts/stage4_intervention_results.json). No live access.

Outputs artifacts/sprint4_2_3/stage4_50_vs_230_analysis.json

What it can establish from saved data:
  1. Update granularity of the Prometheus series (plateau run-lengths).
  2. Effective number of independent observations per phase.
  3. What a p99 value inside the (100, 250] ms histogram bucket does and does not imply.
  4. Whether the checkoutservice ~245 ms level also appears outside the intervention.
What it cannot establish: per-hop latency, retries, queueing, Redis span boundaries
(no traces were saved).
"""
from __future__ import annotations

import json
from itertools import groupby
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "artifacts" / "stage4_intervention_results.json"
OUT = ROOT / "artifacts" / "sprint4_2_3" / "stage4_50_vs_230_analysis.json"

BUCKETS_MS = [2, 5, 10, 25, 50, 100, 250, 500, 1000]  # spanmetrics explicit buckets (deploy/otel-collector.yaml)
INJECTED_DELAY_MS = 50.0


def runs(vals):
    return [len(list(g)) for _, g in groupby(np.round(vals, 6))]


def main() -> None:
    d = json.loads(SRC.read_text())
    res = {"source": str(SRC.relative_to(ROOT)), "per_service": {}}
    all_runs = []
    for svc in d["pre_baseline"]:
        phases = {}
        for ph, key in (("pre", "pre_baseline"), ("active", "intervention"), ("post", "post_recovery")):
            v = np.array([x["val"] for x in d[key][svc]]) * 1000.0
            r = runs(v)
            all_runs += r
            phases[ph] = {"n_samples": int(len(v)), "n_plateaus": len(r), "plateau_lengths": r,
                          "distinct_values_ms": sorted({round(float(x), 2) for x in v})}
        res["per_service"][svc] = phases

    rl = np.array(all_runs)
    res["plateau_length_summary"] = {
        "median_samples": float(np.median(rl)), "mean_samples": round(float(rl.mean()), 2),
        "share_of_plateaus_ge_3_samples": round(float((rl >= 3).mean()), 3),
        "interpretation": ("Series are constant for several consecutive 10 s samples, i.e. the effective "
                           "update interval is longer than the 10 s query step (consistent with a 60 s "
                           "spanmetrics flush; flush interval not verified from the running stack)."),
    }

    cart = res["per_service"]["cartservice"]
    cart_act = cart["active"]["distinct_values_ms"]
    chk = res["per_service"]["checkoutservice"]
    res["bucket_argument"] = {
        "buckets_ms": BUCKETS_MS,
        "cartservice_active_p99_ms": cart_act,
        "statement": (
            "histogram_quantile(0.99) returns a value inside (100, 250] ms only if at least ~1% of the "
            "spans in the 2 m rate window were slower than 100 ms. Linear interpolation inside the bucket "
            "means the exact value (227.5 vs 244.8) reflects bucket mass, not a measured latency."),
        "single_hop_expectation_ms": (
            f"cartservice baseline p99 ~5-8 ms + one {INJECTED_DELAY_MS:.0f} ms egress delay would land in "
            "(50, 100] ms if the delay were applied once per request. Observing p99 > 100 ms therefore "
            "requires >=1% of spans to carry more than ~one delayed hop or additional queueing/retry/client-"
            "span effects. This is a lower-bound argument, not an identification of the mechanism."),
        "mean_latency_not_available": True,
    }
    res["checkoutservice_level_outside_intervention"] = {
        "pre_values_ms": chk["pre"]["distinct_values_ms"],
        "active_values_ms": chk["active"]["distinct_values_ms"],
        "post_values_ms": chk["post"]["distinct_values_ms"],
        "statement": (
            "The ~241-246 ms level appears in pre-baseline and post-recovery windows in which no "
            "intervention was active; an increase to that level during the active window is therefore "
            "not evidence of an intervention-caused shift for checkoutservice."),
    }
    res["measurement_definition_issues_from_code"] = [
        "Query regex span_name=~\"(?i).*<service>.*\" matches any span whose NAME contains the service "
        "string, with no span_kind filter; callers' client spans and callee server spans are merged.",
        "sum by (le) merges all matching operations into a single mixture histogram.",
        "tc filter 'u32 match ip protocol 6' delays ALL TCP egress from the cart container (gRPC replies, "
        "Redis requests, telemetry export), not only application replies.",
        "Active-phase analysis window (110 s) and rate(...[2m]) both extend beyond the 30 s intervention.",
    ]
    res["conclusion"] = (
        "Not resolvable from saved data. Compounded multi-hop egress delay is consistent with p99 > 100 ms "
        "but 2 x 50 ms = ~100 ms still leaves part of the 227-245 ms bucket-interpolated value "
        "unexplained; queueing, retries, mixed client/server span aggregation and bucket interpolation "
        "are not excluded. No per-request, per-hop or trace data were saved, so no mechanism is claimed.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2))
    print(json.dumps({k: res[k] for k in ("plateau_length_summary", "bucket_argument", "conclusion")}, indent=2))


if __name__ == "__main__":
    main()
