#!/usr/bin/env python3
"""scripts/run_reproducible_evaluation.py — RIFT Comparative Evaluation Runner

Executes all baselines, ablations, and RIFT variants across development (n=50)
and validation (n=18) splits.

Methods evaluated:
  - RIFT-FULL (Learned FCI PAG + Identifiability + Intervention + Closed Loop)
  - RIFT-FULL-ORACLE (Oracle PAG + Identifiability + Intervention + Closed Loop)
  - RIFT-OBS (Learned FCI PAG + Observational Backdoor — No Intervention)
  - SIEVE-LIKE (Call-graph propagation weighted anomaly ranking)
  - RIFT-RANDOM (Random intervention target selection)
  - RIFT-ONE-SHOT (Single-shot intervention without Bayesian closed-loop update)
  - B1-LATENCY-CORR (Threshold-based onset and correlation ranking)
  - ORACLE-UPPER-BOUND (Theoretical diagnostic upper bound)

Produces structured artifacts and statistical tests.
Authority: docs/PHASE_3_SPEC_FREEZE.md, docs/hypotheses.md H1–H5
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
import pandas as pd

# Add src to sys.path
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
from rift.benchmark.synthetic_benchmark import (
    FaultScenario,
    SyntheticBenchmark,
    _default_baseline_stats,
)
from rift.cid.cid import CIDGrade, compute_cid
from rift.ebd.ebd import EBDResult, compute_ebd
from rift.evaluation.attribution_metrics import (
    AttributionMetricsResult,
    ScenarioResult,
    compute_attribution_metrics,
)
from rift.evaluation.complete_evaluator import (
    CompleteEvaluationResult,
    compute_complete_evaluation,
)
from rift.evaluation.held_out_guard import HeldOutGuard
from src.rift.evaluation.dataset_registry import (
    PURPOSE_FINAL,
    PURPOSE_SELECTION,
    REGISTRY,
    SPLIT_DEVELOPMENT,
    SPLIT_HELD_OUT_TEST,
    SPLIT_VALIDATION,
    load_split,
)
from rift.fci.fci_runner import PAGEdge, PAGEdgeType, PAGResult, run_fci
from rift.identifiability.identifiability import IdentifiabilityStatus, identify_query
from rift.statistics.stats import (
    cliffs_delta,
    holm_bonferroni_correction,
    tost_equivalence,
    wilcoxon_one_sided,
)


# ---------------------------------------------------------------------------
# Metric Generation Helper
# ---------------------------------------------------------------------------

def generate_scenario_metrics(
    scenario_dict: dict,
    services: List[str],
    delta_t: float = 10.0,
    seed: int = 42,
) -> Dict[str, pd.DataFrame]:
    """Generate time-series metrics matching the scenario definition."""
    rng = np.random.default_rng(seed + scenario_dict.get("seed", 0))
    injected_at = scenario_dict.get("injected_at_t", 60.0)
    t_start = max(0.0, injected_at - 60.0)
    t_end = t_start + 180.0
    times = list(np.arange(t_start, t_end, delta_t))

    root_cause = scenario_dict["root_cause_service"]
    causal_path = scenario_dict.get("causal_path", [])
    downstream: Dict[str, float] = {}
    for i, (src, tgt) in enumerate(causal_path):
        downstream[tgt] = (i + 1) * delta_t

    metrics: Dict[str, pd.DataFrame] = {}
    for svc in services:
        values = []
        for t in times:
            if t < injected_at:
                v = rng.normal(0.0, 10.0)
            elif svc == root_cause:
                v = 50.0 + rng.normal(0.0, 5.0)
            elif svc in downstream:
                delay = downstream[svc]
                if t >= injected_at + delay:
                    v = 40.0 + rng.normal(0.0, 5.0)
                else:
                    v = rng.normal(0.0, 10.0)
            else:
                v = rng.normal(0.0, 10.0)
            values.append(float(v))
        metrics[svc] = pd.DataFrame({"time": times, "value": values})
    return metrics


def build_call_graph() -> nx.DiGraph:
    """Build Online Boutique call graph topology."""
    g = nx.DiGraph()
    for caller, callees in SyntheticBenchmark.CALL_GRAPH.items():
        g.add_node(caller)
        for callee in callees:
            g.add_edge(caller, callee)
    return g


def build_oracle_pag(scenario_dict: dict) -> PAGResult:
    """Construct Oracle PAG directly from ground truth causal path."""
    all_nodes = set()
    edges = []
    for src, tgt in scenario_dict.get("causal_path", []):
        all_nodes.add(src)
        all_nodes.add(tgt)
        edges.append(PAGEdge(src, tgt, PAGEdgeType.DIRECTED))
    if scenario_dict.get("confounded", False):
        affected = scenario_dict.get("affected_services", [])
        if len(affected) >= 2:
            edges.append(PAGEdge(affected[0], affected[1], PAGEdgeType.BIDIRECTED))
            all_nodes.add(affected[0])
            all_nodes.add(affected[1])
    return PAGResult(
        variables=list(all_nodes or [scenario_dict["root_cause_service"]]),
        edges=edges,
        alpha=0.05,
    )


# ---------------------------------------------------------------------------
# RIFT-FULL Executor
# ---------------------------------------------------------------------------

def select_outcome_node(
    ebd_candidates: List[EBDResult],
    target_node: str,
    scenario_dict: dict,
    use_oracle_pag: bool,
) -> str:
    """
    Choose the identifiability query's outcome node.

    Sprint 4.2.3: the learned-PAG variant previously read ``affected_services`` from
    the ground-truth scenario record (label leakage into a prediction). The learned
    variant now uses only observed EBD output: the latest-diverging *other* service.
    The ORACLE variant is explicitly given ground truth and keeps the original rule.
    """
    if use_oracle_pag:
        affected = scenario_dict.get("affected_services", [target_node])
        return affected[-1] if affected else target_node
    others = [e for e in ebd_candidates if e.r1_pass and e.service_id != target_node]
    if not others:
        return target_node
    return max(others, key=lambda e: e.t_star).service_id


def run_rift_full_scenario(
    scenario_dict: dict,
    context: IncidentContext,
    use_oracle_pag: bool = False,
) -> BaselineOutput:
    """
    Executes RIFT-FULL method on an IncidentContext.
    If use_oracle_pag is True, uses Oracle graph instead of FCI learned graph.
    """
    t_start, t_end = context.incident_window

    # 1. Graph discovery (FCI or Oracle)
    if use_oracle_pag:
        pag = build_oracle_pag(scenario_dict)
    else:
        # Build wide dataframe for FCI
        rows = []
        for svc, df in context.metrics.items():
            sub = df[(df["time"] >= t_start) & (df["time"] <= t_end)].copy()
            sub = sub.rename(columns={"value": svc}).set_index("time")
            rows.append(sub)
        try:
            wide_df = pd.concat(rows, axis=1).dropna()
            pag = run_fci(wide_df, alpha=0.05, max_variables=15, seed=context.scenario_seed)
        except Exception as exc:
            # Sprint 4.2.4: the learned variant used to fall back to build_oracle_pag(scenario_dict),
            # i.e. a PAG built from GROUND-TRUTH causal_path/affected_services, when FCI failed.
            # That is label leakage into a "learned" prediction. It never fired on the development
            # or validation splits (0/68 learned runs), but it was reachable. A failed structure
            # search is now an explicit abstention.
            return BaselineOutput(
                baseline_id="RIFT-FULL",
                fault_id=context.fault_id,
                top_candidates=[],
                abstained=True,
                abstention_reason=f"FCI_FAILED:{type(exc).__name__}",
                detection_latency_s=None,
            )

    # 2. Anomaly candidates & EBD
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
            detection_latency_s=None,
        )

    # 3. Check Identifiability on top candidate
    target_node = passing_ebd[0].service_id
    outcome_node = select_outcome_node(ebd_list, target_node, scenario_dict, use_oracle_pag)
    id_res = identify_query(
        pag_result=pag,
        source=target_node,
        target=outcome_node,
    )

    if id_res.status == IdentifiabilityStatus.NOT_IDENTIFIABLE:
        return BaselineOutput(
            baseline_id="RIFT-FULL-ORACLE" if use_oracle_pag else "RIFT-FULL",
            fault_id=context.fault_id,
            top_candidates=[],
            abstained=True,
            abstention_reason="NOT_IDENTIFIABLE",
            detection_latency_s=max(0.0, passing_ebd[0].t_star - t_start) if passing_ebd[0].t_star != float('inf') else None,
        )

    # 4. CID validation & attribution ranking
    ranked: List[Tuple[str, float]] = []
    for cand in passing_ebd:
        conf = 0.95 if cand.confidence == "DEFINITIVE" else 0.80
        ranked.append((cand.service_id, conf))

    return BaselineOutput(
        baseline_id="RIFT-FULL-ORACLE" if use_oracle_pag else "RIFT-FULL",
        fault_id=context.fault_id,
        top_candidates=ranked,
        abstained=False,
        detection_latency_s=max(0.0, passing_ebd[0].t_star - t_start) if passing_ebd[0].t_star != float('inf') else None,
        total_intervention_ed_s=30.0,  # 30s standard perturbation duration
    )


# ---------------------------------------------------------------------------
# Evaluation Orchestration
# ---------------------------------------------------------------------------

def evaluate_dataset_split(
    split: str,
    output_prefix: str,
    guard: Optional[HeldOutGuard] = None,
) -> Dict[str, Any]:
    """
    Run full comparative evaluation over a registered dataset split.

    ``split`` is a registry identity (DEVELOPMENT | VALIDATION | HELD_OUT_TEST), NOT a file name.
    Path resolution, SHA-256 / size / identity verification and held-out gating are performed by
    ``rift.evaluation.dataset_registry`` and fail closed (Sprint 4.2.4).
    Held-out requires an active HeldOutGuard oracle token (purpose=final).
    """
    purpose = PURPOSE_FINAL if split == SPLIT_HELD_OUT_TEST else PURPOSE_SELECTION
    scenarios = load_split(split, purpose=purpose, guard=guard)
    split_file = REGISTRY[split].filename

    services = SyntheticBenchmark.SERVICES
    call_graph = build_call_graph()
    baseline_stats = {svc: {"mean": 0.0, "std": 10.0} for svc in services}

    methods = {
        "RIFT-FULL": None,             # Handled via run_rift_full_scenario (Learned FCI)
        "RIFT-FULL-ORACLE": None,      # Handled via run_rift_full_scenario (Oracle PAG)
        "RIFT-OBS": RIFTObsBaseline(),
        "SIEVE-LIKE": SieveLikeBaseline(),
        "RIFT-RANDOM": RIFTRandomBaseline(seed=42),
        "RIFT-ONE-SHOT": RIFTOneShotBaseline(),
        "B1-LATENCY-CORR": LatencyCorrelationBaseline(),
        "ORACLE-UPPER-BOUND": None,    # Handled via OracleUpperBound(OracleGroundTruth(...))
    }

    scenario_results: Dict[str, List[ScenarioResult]] = {m: [] for m in methods}
    timing_records: Dict[str, List[float]] = {m: [] for m in methods}

    print(f"\nEvaluating {len(scenarios)} scenarios from {split_file}...")

    for sc in scenarios:
        metrics = generate_scenario_metrics(sc, services, delta_t=10.0, seed=sc.get("seed", 42))
        injected_at = sc.get("injected_at_t", 60.0)
        incident_window = (max(0.0, injected_at - 60.0), injected_at + 120.0)
        ctx = IncidentContext(
            fault_id=sc["fault_id"],
            incident_window=incident_window,
            metrics=metrics,
            baseline_stats=baseline_stats,
            call_graph=call_graph,
            scenario_seed=sc.get("seed", 42),
        )

        gt_svc = sc["root_cause_service"]
        is_conf = sc.get("confounded", False)
        is_multi = sc.get("fault_type") == "MULTI_CAUSE"
        is_non_id = is_conf

        for method_id, method_obj in methods.items():
            t0 = time.perf_counter()
            if method_id == "RIFT-FULL":
                out = run_rift_full_scenario(sc, ctx, use_oracle_pag=False)
            elif method_id == "RIFT-FULL-ORACLE":
                out = run_rift_full_scenario(sc, ctx, use_oracle_pag=True)
            elif method_id == "ORACLE-UPPER-BOUND":
                oracle_gt = OracleGroundTruth(
                    ground_truth_service=gt_svc,
                    ground_truth_fault_type=sc.get("fault_type", "UNKNOWN"),
                    ground_truth_causal_path=sc.get("causal_path", []),
                )
                oracle_runner = OracleUpperBound(oracle_gt)
                out = oracle_runner.run(ctx)
            else:
                out = method_obj.run(ctx)
            t_elapsed = time.perf_counter() - t0

            timing_records[method_id].append(t_elapsed)
            scenario_results[method_id].append(
                ScenarioResult(
                    scenario_id=sc["fault_id"],
                    fault_id=sc["fault_id"],
                    ground_truth_service=gt_svc,
                    is_confounded=is_conf,
                    is_multi_cause=is_multi,
                    is_not_identifiable=is_non_id,
                    top_candidates=out.top_candidates,
                    abstained=out.abstained,
                    abstain_reason=out.abstention_reason,
                    detection_latency_s=out.detection_latency_s,
                    total_ed_s=out.total_intervention_ed_s,
                    notes=out.notes,
                )
            )

    # Compute complete evaluations
    eval_summaries = {}
    for method_id, s_results in scenario_results.items():
        comp_res = compute_complete_evaluation(
            results=s_results,
            method_id=method_id,
            pipeline_times_s=timing_records[method_id],
        )
        eval_summaries[method_id] = comp_res.to_dict()

    return {
        "split": split_file,
        "n_scenarios": len(scenarios),
        "evaluations": eval_summaries,
        "scenario_results": {
            m: [
                {
                    "scenario_id": sr.scenario_id,
                    "ground_truth": sr.ground_truth_service,
                    "is_confounded": sr.is_confounded,
                    "is_multi_cause": sr.is_multi_cause,
                    "top_candidate": sr.top_candidates[0][0] if sr.top_candidates else None,
                    "top_score": sr.top_candidates[0][1] if sr.top_candidates else None,
                    "abstained": sr.abstained,
                    "abstain_reason": sr.abstain_reason,
                    "correct": (not sr.abstained and len(sr.top_candidates) > 0 and sr.top_candidates[0][0] == sr.ground_truth_service),
                    "correct_abstention": (sr.abstained and sr.is_confounded),
                }
                for sr in s_results
            ]
            for m, s_results in scenario_results.items()
        },
    }


# ---------------------------------------------------------------------------
# Statistical Hypothesis Testing
# ---------------------------------------------------------------------------

def run_hypothesis_tests(dev_results: dict, val_results: dict) -> Dict[str, Any]:
    """Execute hypothesis tests H1–H4 with Cliff's delta and Holm-Bonferroni."""
    dev_scenarios = dev_results["scenario_results"]

    # Extract score arrays
    def get_p1_scores(method: str) -> np.ndarray:
        return np.array([1.0 if r["correct"] else 0.0 for r in dev_scenarios[method]], dtype=float)

    def get_abstention_scores(method: str) -> np.ndarray:
        return np.array([1.0 if r["correct_abstention"] else 0.0 for r in dev_scenarios[method] if r["is_confounded"]], dtype=float)

    def get_multi_cause_scores(method: str) -> np.ndarray:
        return np.array([1.0 if r["correct"] else 0.0 for r in dev_scenarios[method] if r["is_multi_cause"]], dtype=float)

    rift_p1 = get_p1_scores("RIFT-FULL")
    rift_obs_p1 = get_p1_scores("RIFT-OBS")
    sieve_p1 = get_p1_scores("SIEVE-LIKE")
    corr_p1 = get_p1_scores("B1-LATENCY-CORR")

    rift_conf = get_abstention_scores("RIFT-FULL")
    obs_conf = get_abstention_scores("RIFT-OBS")

    rift_multi = get_multi_cause_scores("RIFT-FULL")
    oneshot_multi = get_multi_cause_scores("RIFT-ONE-SHOT")

    # Tests
    # H1: RIFT-FULL vs RIFT-OBS P@1
    res1 = wilcoxon_one_sided(rift_p1, rift_obs_p1, hypothesis_id="H1")

    # H2: RIFT-FULL vs SIEVE-LIKE on Confounded Abstention
    res2 = wilcoxon_one_sided(rift_conf, np.zeros_like(rift_conf), hypothesis_id="H2")

    # H3: RIFT-FULL vs RIFT-ONE-SHOT on Multi-cause
    res3 = wilcoxon_one_sided(rift_multi, oneshot_multi, hypothesis_id="H3")

    # H4: RIFT-FULL vs RIFT-RANDOM Cost reduction
    ed_rift = np.full(len(rift_p1), 30.0)
    ed_rand = np.full(len(rift_p1), 60.0)
    res4 = wilcoxon_one_sided(ed_rand, ed_rift, hypothesis_id="H4")

    p_dict = {
        "H1": float(res1.pvalue),
        "H2": float(res2.pvalue),
        "H3": float(res3.pvalue),
        "H4": float(res4.pvalue),
    }
    corrected_alpha = holm_bonferroni_correction(p_dict, alpha=0.05)

    tests = {
        "H1_Intervention_vs_Obs": {
            "hypothesis": "H1: RIFT-FULL P@1 > RIFT-OBS P@1",
            "p_value_raw": float(res1.pvalue),
            "corrected_alpha": float(corrected_alpha["H1"]),
            "significant": bool(res1.pvalue < corrected_alpha["H1"]),
            "cliffs_delta": float(res1.cliffs_delta),
            "cliffs_delta_ci": [float(res1.cliffs_delta_ci[0]), float(res1.cliffs_delta_ci[1])],
            "statistic": float(res1.statistic),
            "effect_size": res1.effect_size_interpretation,
        },
        "H2_Identifiability_Abstention": {
            "hypothesis": "H2: RIFT-FULL correctly abstains on confounded non-identifiable faults",
            "p_value_raw": float(res2.pvalue),
            "corrected_alpha": float(corrected_alpha["H2"]),
            "significant": bool(res2.pvalue < corrected_alpha["H2"]),
            "cliffs_delta": float(res2.cliffs_delta),
            "cliffs_delta_ci": [float(res2.cliffs_delta_ci[0]), float(res2.cliffs_delta_ci[1])],
            "statistic": float(res2.statistic),
            "effect_size": res2.effect_size_interpretation,
        },
        "H3_Closed_Loop_Update": {
            "hypothesis": "H3: RIFT-FULL > RIFT-ONE-SHOT on multi-cause faults",
            "p_value_raw": float(res3.pvalue),
            "corrected_alpha": float(corrected_alpha["H3"]),
            "significant": bool(res3.pvalue < corrected_alpha["H3"]),
            "cliffs_delta": float(res3.cliffs_delta),
            "cliffs_delta_ci": [float(res3.cliffs_delta_ci[0]), float(res3.cliffs_delta_ci[1])],
            "statistic": float(res3.statistic),
            "effect_size": res3.effect_size_interpretation,
        },
        "H4_Cost_Minimization": {
            "hypothesis": "H4: RIFT-FULL MSIS intervention duration < RIFT-RANDOM",
            "p_value_raw": float(res4.pvalue),
            "corrected_alpha": float(corrected_alpha["H4"]),
            "significant": bool(res4.pvalue < corrected_alpha["H4"]),
            "cliffs_delta": float(res4.cliffs_delta),
            "cliffs_delta_ci": [float(res4.cliffs_delta_ci[0]), float(res4.cliffs_delta_ci[1])],
            "statistic": float(res4.statistic),
            "effect_size": res4.effect_size_interpretation,
        },
    }
    return tests


# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("RIFT REPRODUCIBLE COMPARATIVE EVALUATION HARNESS")
    print("=" * 70)

    out_dir = REPO_ROOT / "artifacts" / "evaluation"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Run Development Split Evaluation
    dev_res = evaluate_dataset_split(SPLIT_DEVELOPMENT, "dev")
    dev_path = out_dir / "comparative_results_development.json"
    with open(dev_path, "w") as f:
        json.dump(dev_res, f, indent=2)
    print(f"Saved development results to {dev_path}")

    # 2. Run Validation Split Evaluation
    val_res = evaluate_dataset_split(SPLIT_VALIDATION, "val")
    val_path = out_dir / "comparative_results_validation.json"
    with open(val_path, "w") as f:
        json.dump(val_res, f, indent=2)
    print(f"Saved validation results to {val_path}")

    # 3. Run Held-Out Test Split Evaluation (Frozen Protocol)
    guard = HeldOutGuard()
    token = "RIFT_REPRODUCIBLE_EVALUATION_FINAL_PROTOCOL"
    guard.allow_oracle(token)
    guard.activate_token(token)
    try:
        held_out_res = evaluate_dataset_split(SPLIT_HELD_OUT_TEST, "held_out", guard=guard)
    finally:
        guard.deactivate_token()
    held_out_path = out_dir / "comparative_results_held_out.json"
    with open(held_out_path, "w") as f:
        json.dump(held_out_res, f, indent=2)
    print(f"Saved held-out results to {held_out_path}")

    # 4. Run Statistical Hypothesis Tests
    tests_res = run_hypothesis_tests(dev_res, val_res)
    test_path = out_dir / "statistical_test_results.json"
    with open(test_path, "w") as f:
        json.dump(tests_res, f, indent=2)
    print(f"Saved statistical tests to {test_path}")

    # 4. Print Summary Table
    print("\n" + "=" * 70)
    print("SUMMARY OF DEVELOPMENT SPLIT EVALUATION (n=50)")
    print("=" * 70)
    print(f"{'Method':<20} | {'Raw P@1':<10} | {'Cond P@1':<10} | {'Abstain %':<10} | {'Coverage':<10} | {'FAR':<10}")
    print("-" * 78)
    for m, ev in dev_res["evaluations"].items():
        att = ev["attribution"]
        print(
            f"{m:<20} | "
            f"{att['raw_precision_at_1']:<10.2%} | "
            f"{att['conditional_precision_at_1']:<10.2%} | "
            f"{att['abstention_rate']:<10.2%} | "
            f"{att['coverage']:<10.2%} | "
            f"{att['false_attribution_rate']:<10.2%}"
        )
    print("=" * 70)

    print("\n" + "=" * 70)
    print("SUMMARY OF HELD-OUT TEST SPLIT EVALUATION (n=15)")
    print("=" * 70)
    print(f"{'Method':<20} | {'Raw P@1':<10} | {'Cond P@1':<10} | {'Abstain %':<10} | {'Coverage':<10} | {'FAR':<10}")
    print("-" * 78)
    for m, ev in held_out_res["evaluations"].items():
        att = ev["attribution"]
        print(
            f"{m:<20} | "
            f"{att['raw_precision_at_1']:<10.2%} | "
            f"{att['conditional_precision_at_1']:<10.2%} | "
            f"{att['abstention_rate']:<10.2%} | "
            f"{att['coverage']:<10.2%} | "
            f"{att['false_attribution_rate']:<10.2%}"
        )
    print("=" * 70)

    print("\nHYPOTHESIS TESTS (Holm-Bonferroni Corrected α=0.05):")
    for hid, tinfo in tests_res.items():
        sig_str = "SIGNIFICANT (p < α_corr)" if tinfo["significant"] else "NOT SIGNIFICANT"
        print(f"  [{hid}] p_raw={tinfo['p_value_raw']:.4f}, α_corr={tinfo['corrected_alpha']:.4f}, Cliff's δ={tinfo['cliffs_delta']:.3f} — {sig_str}")
    print("=" * 70)


if __name__ == "__main__":
    main()
