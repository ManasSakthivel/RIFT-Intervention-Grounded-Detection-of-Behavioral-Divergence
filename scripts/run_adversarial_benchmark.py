#!/usr/bin/env python3
"""scripts/run_adversarial_benchmark.py — RIFT Sprint 3 Adversarial Benchmark Harness

Executes all baselines across the 6 adversarial failure families:
  Family A: Inverted Onset
  Family B: Retry Amplification
  Family C: Shared-Infrastructure Confounding
  Family D: Multiple Simultaneous Faults
  Family E: Noisy Telemetry & Dropouts
  Family F: Deep Cascade

Authority: docs/SPRINT3_BENCHMARK_SPECIFICATION.md
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import networkx as nx
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from rift.baselines import BaselineOutput, IncidentContext
from rift.baselines.latency_correlation import LatencyCorrelationBaseline
from rift.baselines.oracle import OracleGroundTruth, OracleUpperBound
from rift.baselines.rift_obs import RIFTObsBaseline
from rift.baselines.rift_one_shot import RIFTOneShotBaseline
from rift.baselines.rift_random import RIFTRandomBaseline
from rift.baselines.sieve_like import SieveLikeBaseline
from rift.benchmark.adversarial_generator import (
    SERVICES,
    AdversarialScenario,
    generate_adversarial_cohort,
    generate_adversarial_metrics,
)
from rift.benchmark.synthetic_benchmark import SyntheticBenchmark
from rift.cid.cid import CIDGrade, compute_cid
from rift.ebd.ebd import compute_ebd
from rift.fci.fci_runner import PAGEdge, PAGEdgeType, PAGResult, run_fci
from rift.identifiability.identifiability import IdentifiabilityStatus, identify_query


class HighestAnomalyBaseline:
    """Ranks candidates strictly by maximum z-score amplitude."""
    @property
    def baseline_id(self) -> str:
        return "B0-HIGHEST-ANOMALY"

    def run(self, context: IncidentContext) -> BaselineOutput:
        t_start, t_end = context.incident_window
        scores = {}
        for svc, df in context.metrics.items():
            sub = df[(df["time"] >= t_start) & (df["time"] <= t_end)]
            if sub.empty:
                continue
            b = context.baseline_stats.get(svc, {})
            mean = b.get("mean", 0.0)
            std = b.get("std", 10.0) + 1e-9
            z = float((sub["value"] - mean).abs().max() / std)
            scores[svc] = z
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return BaselineOutput(
            baseline_id=self.baseline_id,
            fault_id=context.fault_id,
            top_candidates=ranked[:3],
            abstained=False,
        )


class EarliestAnomalyBaseline:
    """Ranks candidates strictly by earliest threshold crossing."""
    @property
    def baseline_id(self) -> str:
        return "B0-EARLIEST-ANOMALY"

    def run(self, context: IncidentContext) -> BaselineOutput:
        t_start, t_end = context.incident_window
        triggers = {}
        for svc, df in context.metrics.items():
            sub = df[(df["time"] >= t_start) & (df["time"] <= t_end)]
            if sub.empty:
                continue
            b = context.baseline_stats.get(svc, {})
            mean = b.get("mean", 0.0)
            std = b.get("std", 10.0) + 1e-9
            z = (sub["value"] - mean).abs() / std
            anoms = sub[z >= 3.0]
            if not anoms.empty:
                triggers[svc] = float(anoms["time"].iloc[0])
            else:
                triggers[svc] = t_end + 100.0
        ranked = sorted(triggers.items(), key=lambda x: x[1])
        top = [(svc, 1.0 / (1.0 + (t - t_start))) for svc, t in ranked if t <= t_end]
        if not top:
            return BaselineOutput(baseline_id=self.baseline_id, fault_id=context.fault_id, top_candidates=[], abstained=True)
        return BaselineOutput(
            baseline_id=self.baseline_id,
            fault_id=context.fault_id,
            top_candidates=top[:3],
            abstained=False,
        )


def run_rift_full_adversarial(
    scenario: AdversarialScenario,
    context: IncidentContext,
    use_oracle_pag: bool = False,
) -> BaselineOutput:
    """Execute RIFT-FULL with Sprint 2 semi-directed graph handling."""
    t_start, t_end = context.incident_window

    if use_oracle_pag:
        all_nodes = set([scenario.root_cause_service] + scenario.affected_services)
        edges = []
        for src, tgt in scenario.causal_path:
            all_nodes.add(src)
            all_nodes.add(tgt)
            edges.append(PAGEdge(src, tgt, PAGEdgeType.DIRECTED))
        if scenario.confounded:
            if len(scenario.affected_services) >= 2:
                edges.append(PAGEdge(scenario.affected_services[0], scenario.affected_services[1], PAGEdgeType.BIDIRECTED))
        pag = PAGResult(variables=list(all_nodes), edges=edges, alpha=0.05)
    else:
        rows = []
        for svc, df in context.metrics.items():
            sub = df[(df["time"] >= t_start) & (df["time"] <= t_end)].copy()
            sub = sub.rename(columns={"value": svc}).set_index("time")
            rows.append(sub)
        try:
            wide_df = pd.concat(rows, axis=1).dropna()
            pag = run_fci(wide_df, alpha=0.05, max_variables=15, seed=scenario.seed)
        except Exception:
            pag = PAGResult(variables=list(context.metrics.keys()), edges=[])

    ebd_list = compute_ebd(
        metrics=context.metrics,
        baselines=context.baseline_stats,
        pag_result=pag,
        incident_window=context.incident_window,
        delta_t=10.0,
        theta_detect=3.0,
        theta_persist=2,
    )

    passing_ebd = [e for e in ebd_list if e.r1_pass and e.r3_pass]
    if not passing_ebd:
        return BaselineOutput(
            baseline_id="RIFT-FULL-ORACLE" if use_oracle_pag else "RIFT-FULL",
            fault_id=context.fault_id,
            top_candidates=[],
            abstained=True,
            abstention_reason="NO_CANDIDATES",
        )

    target_node = passing_ebd[0].service_id
    affected = scenario.affected_services if scenario.affected_services else [target_node]
    outcome_node = affected[-1] if affected else target_node
    id_res = identify_query(pag_result=pag, source=target_node, target=outcome_node)

    if id_res.status == IdentifiabilityStatus.NOT_IDENTIFIABLE:
        return BaselineOutput(
            baseline_id="RIFT-FULL-ORACLE" if use_oracle_pag else "RIFT-FULL",
            fault_id=context.fault_id,
            top_candidates=[],
            abstained=True,
            abstention_reason="NOT_IDENTIFIABLE",
        )

    ranked = [(cand.service_id, 0.95 if cand.confidence == "DEFINITIVE" else 0.80) for cand in passing_ebd]
    return BaselineOutput(
        baseline_id="RIFT-FULL-ORACLE" if use_oracle_pag else "RIFT-FULL",
        fault_id=context.fault_id,
        top_candidates=ranked,
        abstained=False,
        total_intervention_ed_s=30.0,
    )


def main():
    print("=" * 75)
    print("RIFT SPRINT 3 — ADVERSARIAL BENCHMARK EVALUATION HARNESS")
    print("=" * 75)

    cohort = generate_adversarial_cohort(cohort_size_per_family=5, seed=1000)
    cohort_path = REPO_ROOT / "datasets" / "rift_faults" / "adversarial_stress_cohort.json"
    with open(cohort_path, "w") as f:
        json.dump({"scenarios": [s.to_dict() for s in cohort]}, f, indent=2)
    print(f"Generated and saved {len(cohort)} adversarial scenarios to {cohort_path}")

    call_graph = nx.DiGraph()
    for caller, callees in SyntheticBenchmark.CALL_GRAPH.items():
        call_graph.add_node(caller)
        for callee in callees:
            call_graph.add_edge(caller, callee)

    baseline_stats = {svc: {"mean": 0.0, "std": 10.0} for svc in SERVICES}

    baselines = {
        "B0-EARLIEST": EarliestAnomalyBaseline(),
        "B0-HIGHEST": HighestAnomalyBaseline(),
        "B1-LATENCY-CORR": LatencyCorrelationBaseline(),
        "B3-SIEVE-LIKE": SieveLikeBaseline(),
        "B6-RIFT-RANDOM": RIFTRandomBaseline(seed=42),
        "B4-RIFT-ONE-SHOT": RIFTOneShotBaseline(),
        "RIFT-OBS": RIFTObsBaseline(),
        "RIFT-FULL": None,
        "RIFT-FULL-ORACLE": None,
    }

    results: Dict[str, Dict[str, Any]] = {m: {"total": 0, "correct": 0, "abstained": 0, "false_attribution": 0, "by_family": {}} for m in baselines}
    scenario_records: List[Dict[str, Any]] = []
    family_list = ["A_INVERTED", "B_RETRY", "C_CONFOUNDED", "D_MULTI", "E_NOISE", "F_DEEP"]
    for m in baselines:
        for fam in family_list:
            results[m]["by_family"][fam] = {"total": 0, "correct": 0, "abstained": 0, "false_attribution": 0}

    for sc in cohort:
        metrics = generate_adversarial_metrics(sc, SERVICES, delta_t=10.0, seed=sc.seed)
        incident_window = (max(0.0, sc.injected_at_t - 60.0), sc.injected_at_t + 120.0)
        ctx = IncidentContext(
            fault_id=sc.scenario_id,
            incident_window=incident_window,
            metrics=metrics,
            baseline_stats=baseline_stats,
            call_graph=call_graph,
            scenario_seed=sc.seed,
        )

        gt = sc.root_cause_service
        sec_gt = sc.secondary_root_cause

        for m_id, m_obj in baselines.items():
            if m_id == "RIFT-FULL":
                out = run_rift_full_adversarial(sc, ctx, use_oracle_pag=False)
            elif m_id == "RIFT-FULL-ORACLE":
                out = run_rift_full_adversarial(sc, ctx, use_oracle_pag=True)
            else:
                out = m_obj.run(ctx)

            top_svc = out.top_candidates[0][0] if out.top_candidates else None
            is_correct = (not out.abstained and (top_svc == gt or (sec_gt is not None and top_svc == sec_gt)))
            is_abstained = out.abstained
            is_fa = (not out.abstained and not is_correct)

            results[m_id]["total"] += 1
            if is_correct:
                results[m_id]["correct"] += 1
            if is_abstained:
                results[m_id]["abstained"] += 1
            if is_fa:
                results[m_id]["false_attribution"] += 1

            fam_dict = results[m_id]["by_family"][sc.family]
            fam_dict["total"] += 1
            if is_correct:
                fam_dict["correct"] += 1
            if is_abstained:
                fam_dict["abstained"] += 1
            if is_fa:
                fam_dict["false_attribution"] += 1

            scenario_records.append({
                "scenario_id": sc.scenario_id,
                "family": sc.family,
                "method_id": m_id,
                "ground_truth": gt,
                "secondary_ground_truth": sec_gt,
                "top_candidate": top_svc,
                "abstained": is_abstained,
                "abstain_reason": out.abstention_reason,
                "correct": is_correct,
                "false_attribution": is_fa,
                "seed": sc.seed,
            })

    out_artifact = REPO_ROOT / "artifacts" / "evaluation" / "adversarial_benchmark_results.json"
    out_artifact.parent.mkdir(parents=True, exist_ok=True)
    with open(out_artifact, "w") as f:
        json.dump(results, f, indent=2)

    sc_artifact = REPO_ROOT / "artifacts" / "evaluation" / "adversarial_scenario_predictions.json"
    with open(sc_artifact, "w") as f:
        json.dump(scenario_records, f, indent=2)

    print("\n" + "=" * 80)
    print("OVERALL ADVERSARIAL BENCHMARK RESULTS (n=30 Scenarios Across 6 Families)")
    print("=" * 80)
    print(f"{'Method':<20} | {'Raw P@1':<10} | {'Cond P@1':<10} | {'Abstain %':<10} | {'Coverage':<10} | {'FAR':<10}")
    print("-" * 80)
    for m, r in results.items():
        tot = r["total"]
        cor = r["correct"]
        abs_cnt = r["abstained"]
        fa_cnt = r["false_attribution"]
        pred_cnt = tot - abs_cnt

        raw_p1 = (cor / tot) if tot else 0.0
        cond_p1 = (cor / pred_cnt) if pred_cnt else 0.0
        abstain_pct = (abs_cnt / tot) if tot else 0.0
        cov = (pred_cnt / tot) if tot else 0.0
        far = (fa_cnt / tot) if tot else 0.0

        print(f"{m:<20} | {raw_p1:<10.1%} | {cond_p1:<10.1%} | {abstain_pct:<10.1%} | {cov:<10.1%} | {far:<10.1%}")
    print("=" * 80)

    print("\nBREAKDOWN BY ADVERSARIAL FAILURE FAMILY (Raw Precision@1):")
    print(f"{'Method':<18} | {'A:Invert':<8} | {'B:Retry':<8} | {'C:Conf':<8} | {'D:Multi':<8} | {'E:Noise':<8} | {'F:Deep':<8}")
    print("-" * 80)
    for m, r in results.items():
        row_str = f"{m:<18} | "
        for fam in family_list:
            f_res = r["by_family"][fam]
            p1 = (f_res["correct"] / f_res["total"]) if f_res["total"] else 0.0
            row_str += f"{p1:<8.0%} | "
        print(row_str)
    print("=" * 80)


if __name__ == "__main__":
    main()
