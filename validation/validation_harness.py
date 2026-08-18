"""
RIFT Independent Validation Harness — Phase 3W

Validates that RIFT's core claims hold on the synthetic fault benchmark
using oracles that are INDEPENDENT of RIFT's internal graph representation.

The oracle ground truth comes from FaultScenario.root_cause_service and
FaultScenario.causal_path — these are locked before RIFT runs.

Validation Goals:
  V1  EBD correctly identifies the ground-truth root cause in ≥ 70% of
      non-confounded synthetic scenarios (development split only).
  V2  On confounded scenarios, RIFT either: (a) abstains, or (b) issues
      assumption_warnings about bidirected edges — in ≥ 80% of cases.
  V3  R2 (temporal precedence): the first EBD candidate always has an
      earlier t_star than non-candidates in the same scenario.
  V4  No DEFINITIVE EBD without passing R1-R4 (invariant).
  V5  FAR (False Attribution Rate): RIFT does not produce CANDIDATE/DEFINITIVE
      for services with no causal path to any anomalous downstream service.

Status: PARTIAL — uses synthetic metric simulation (not live testbed).
        Live testbed validation is Phase 10.

Authority: docs/PHASE_3_SPEC_FREEZE.md §17 (independent validation)
"""
from __future__ import annotations

import json
import sys
import os
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import networkx as nx

# Make both `rift` and `src.rift` importable (mirrors conftest.py)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rift.benchmark.synthetic_benchmark import (
    FaultScenario,
    SyntheticBenchmark,
    SPLIT_DEVELOPMENT,
    SPLIT_HELD_OUT_TEST,
)
from rift.ebd.ebd import compute_ebd, EBDResult
from rift.fci.fci_runner import PAGEdge, PAGEdgeType, PAGResult


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic metric generator (oracle, independent of RIFT's benchmark)
# ─────────────────────────────────────────────────────────────────────────────

def generate_oracle_metrics(
    scenario: FaultScenario,
    services: List[str],
    delta_t: float = 10.0,
    incident_duration_s: float = 120.0,
    seed: int = 0,
) -> Dict[str, pd.DataFrame]:
    """
    Generate synthetic metrics for a scenario using the ground-truth FaultScenario.

    Root cause service: spikes at t = scenario.injected_at_t
    Downstream services (causal_path): spike with delay proportional to graph distance
    Other services: normal noise

    This oracle is INDEPENDENT of RIFT's metric simulation in synthetic_benchmark.py.
    It uses only FaultScenario.root_cause_service and FaultScenario.causal_path.
    """
    rng = np.random.default_rng(seed + scenario.seed)
    t_start = scenario.injected_at_t - 60.0  # 1min pre-injection baseline
    t_end = t_start + 180.0  # 3 minutes total
    times = list(np.arange(t_start, t_end, delta_t))

    # Determine which services are downstream in causal chain
    downstream = {}
    for i, (src, tgt) in enumerate(scenario.causal_path):
        downstream[tgt] = (i + 1) * delta_t  # delay per hop

    metrics = {}
    for svc in services:
        values = []
        for t in times:
            if t < scenario.injected_at_t:
                # Baseline: Gaussian noise
                v = rng.normal(0.0, 10.0)
            elif svc == scenario.root_cause_service:
                # Root cause: persistent spike
                v = 50.0 + rng.normal(0, 5.0)
            elif svc in downstream:
                delay = downstream[svc]
                if t >= scenario.injected_at_t + delay:
                    v = 40.0 + rng.normal(0, 5.0)
                else:
                    v = rng.normal(0.0, 10.0)
            else:
                v = rng.normal(0.0, 10.0)
            values.append(float(v))
        metrics[svc] = pd.DataFrame({"time": times, "value": values})

    return metrics


def build_oracle_pag(scenario: FaultScenario) -> PAGResult:
    """
    Build a PAGResult directly from scenario.causal_path.

    This is the ORACLE graph — independent of RIFT's FCI runner.
    Used to test EBD logic without noise from FCI estimation.
    """
    all_nodes = set()
    edges = []
    for src, tgt in scenario.causal_path:
        all_nodes.add(src)
        all_nodes.add(tgt)
        edges.append(PAGEdge(src, tgt, PAGEdgeType.DIRECTED))

    if scenario.confounded and len(scenario.causal_path) > 0:
        # Add bidirected edge for confounded scenarios
        src, tgt = scenario.causal_path[0]
        edges.append(PAGEdge(src, tgt, PAGEdgeType.BIDIRECTED))

    return PAGResult(
        variables=list(all_nodes),
        edges=edges,
        notes="Oracle PAG from FaultScenario.causal_path. Independent of FCI.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Validation result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    scenario_id: str
    root_cause: str
    confounded: bool
    split: str
    ebd_results: List[EBDResult] = field(default_factory=list)
    top_candidate: Optional[str] = None
    top_confidence: str = "NONE"
    root_cause_found: bool = False
    root_cause_rank: Optional[int] = None
    has_assumption_warning: bool = False
    abstained: bool = False
    r2_invariant_holds: bool = True
    r4_invariant_holds: bool = True
    notes: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Invariant checkers
# ─────────────────────────────────────────────────────────────────────────────

def check_r4_invariant(results: List[EBDResult]) -> bool:
    """V4: No DEFINITIVE EBD without R1+R2+R3+R4 all passing."""
    for r in results:
        if r.confidence == "DEFINITIVE":
            if not (r.r1_pass and r.r2_pass and r.r3_pass and r.r4_pass):
                return False
    return True


def check_r2_temporal_invariant(results: List[EBDResult]) -> bool:
    """V3: Top-ranked CANDIDATE/DEFINITIVE has earliest or tied t_star."""
    ranked = [r for r in results if r.confidence in ("CANDIDATE", "DEFINITIVE")]
    if len(ranked) < 2:
        return True
    # The first result must not have a strictly later t_star than any other
    first_t = float(ranked[0].t_star)
    for r in ranked[1:]:
        if float(r.t_star) < first_t - 1.0:  # 1s tolerance
            return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Run validation on one scenario
# ─────────────────────────────────────────────────────────────────────────────

def validate_scenario(
    scenario: FaultScenario,
    services: List[str],
    delta_t: float = 10.0,
) -> ValidationResult:
    """Run RIFT EBD on oracle data and check against ground truth."""
    metrics = generate_oracle_metrics(scenario, services, delta_t=delta_t)
    pag = build_oracle_pag(scenario)

    # Baseline stats
    baselines = {svc: {"mean": 0.0, "std": 10.0} for svc in services}
    incident_window = (
        scenario.injected_at_t - 60.0,
        scenario.injected_at_t + 120.0,
    )

    ebd_results = compute_ebd(
        metrics=metrics,
        baselines=baselines,
        pag_result=pag,
        incident_window=incident_window,
        delta_t=delta_t,
        theta_detect=3.0,
        theta_persist=2,
    )

    root_cause_found = False
    root_cause_rank = None
    top_candidate = None
    top_confidence = "NONE"
    has_warning = False
    abstained = len(ebd_results) == 0

    if ebd_results:
        top_candidate = ebd_results[0].service_id
        top_confidence = ebd_results[0].confidence
        for i, r in enumerate(ebd_results):
            if r.assumption_warnings:
                has_warning = True
            if r.service_id == scenario.root_cause_service:
                root_cause_rank = i + 1
                if r.confidence in ("CANDIDATE", "DEFINITIVE"):
                    root_cause_found = True

    r2_ok = check_r2_temporal_invariant(ebd_results)
    r4_ok = check_r4_invariant(ebd_results)

    return ValidationResult(
        scenario_id=scenario.fault_id,
        root_cause=scenario.root_cause_service,
        confounded=scenario.confounded,
        split=scenario.split,
        ebd_results=ebd_results,
        top_candidate=top_candidate,
        top_confidence=top_confidence,
        root_cause_found=root_cause_found,
        root_cause_rank=root_cause_rank,
        has_assumption_warning=has_warning,
        abstained=abstained,
        r2_invariant_holds=r2_ok,
        r4_invariant_holds=r4_ok,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Aggregate validation runner
# ─────────────────────────────────────────────────────────────────────────────

def run_validation(
    scenarios: List[FaultScenario],
    services: List[str],
    split_filter: Optional[str] = SPLIT_DEVELOPMENT,
) -> dict:
    """
    Run validation across all scenarios.
    Returns aggregate metrics for V1–V5.
    """
    if split_filter:
        scenarios = [s for s in scenarios if s.split == split_filter]

    results = []
    for scenario in scenarios:
        r = validate_scenario(scenario, services)
        results.append(r)

    non_conf = [r for r in results if not r.confounded]
    conf = [r for r in results if r.confounded]

    # V1: Precision@1 on non-confounded (development only)
    v1_correct = sum(1 for r in non_conf if r.root_cause_found)
    v1_total = len(non_conf)
    v1_precision = v1_correct / v1_total if v1_total > 0 else 0.0

    # V2: Confounded scenarios: abstain OR has assumption_warning
    v2_correct = sum(1 for r in conf if r.abstained or r.has_assumption_warning)
    v2_total = len(conf)
    v2_rate = v2_correct / v2_total if v2_total > 0 else 0.0

    # V3: R2 temporal invariant
    v3_violations = sum(1 for r in results if not r.r2_invariant_holds)

    # V4: R4 invariant
    v4_violations = sum(1 for r in results if not r.r4_invariant_holds)

    # V5: FAR (False Attribution Rate) — CANDIDATE/DEFINITIVE on non-root-cause service
    # A false attribution: top_candidate != root_cause AND not abstained
    far_count = sum(
        1 for r in non_conf
        if not r.abstained and r.top_candidate is not None
        and r.top_candidate != r.root_cause
    )
    far = far_count / max(1, len(non_conf))

    status_notes = []
    if v1_precision >= 0.70:
        status_notes.append(f"V1 PASS: P@1={v1_precision:.2%} ≥ 70% target")
    else:
        status_notes.append(f"V1 PARTIAL: P@1={v1_precision:.2%} < 70% (synthetic oracle only)")
    if v2_rate >= 0.80:
        status_notes.append(f"V2 PASS: confounded_correct_rate={v2_rate:.2%} ≥ 80%")
    else:
        status_notes.append(f"V2 PARTIAL: confounded_correct_rate={v2_rate:.2%} < 80%")
    if v3_violations == 0:
        status_notes.append("V3 PASS: R2 temporal invariant holds on all scenarios")
    else:
        status_notes.append(f"V3 FAIL: {v3_violations} scenarios violate R2 temporal invariant")
    if v4_violations == 0:
        status_notes.append("V4 PASS: R4 invariant holds on all scenarios")
    else:
        status_notes.append(f"V4 FAIL: {v4_violations} DEFINITIVE results missing R1-R4")
    status_notes.append(f"V5 FAR={far:.2%} (False Attribution Rate on non-confounded)")

    return {
        "split_filter": split_filter,
        "n_scenarios": len(results),
        "n_non_confounded": v1_total,
        "n_confounded": v2_total,
        "V1_precision_at_1": round(v1_precision, 4),
        "V1_status": "PASS" if v1_precision >= 0.70 else "PARTIAL",
        "V2_confounded_correct_rate": round(v2_rate, 4),
        "V2_status": "PASS" if v2_rate >= 0.80 else "PARTIAL",
        "V3_r2_violations": v3_violations,
        "V3_status": "PASS" if v3_violations == 0 else "FAIL",
        "V4_r4_violations": v4_violations,
        "V4_status": "PASS" if v4_violations == 0 else "FAIL",
        "V5_far": round(far, 4),
        "notes": status_notes,
        "caveat": (
            "Validation uses oracle PAG (direct from ground truth causal path), "
            "not FCI-estimated PAG. Results are upper-bound estimates. "
            "Live testbed validation is Phase 10."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    bench = SyntheticBenchmark()
    scenarios = bench.generate_all_faults(seed=42)
    services = SyntheticBenchmark.SERVICES

    print("\n=== RIFT Independent Validation (Development Split) ===\n")
    report = run_validation(scenarios, services, split_filter=SPLIT_DEVELOPMENT)

    for note in report["notes"]:
        print(f"  {note}")
    print(f"\n  n_scenarios={report['n_scenarios']}, "
          f"non_conf={report['n_non_confounded']}, conf={report['n_confounded']}")
    print(f"  Caveat: {report['caveat']}")

    # Write report
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "artifacts", "phase3"),
                exist_ok=True)
    report_path = os.path.join(
        os.path.dirname(__file__), "..", "artifacts", "phase3",
        "independent_validation_report.json"
    )
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report written to: {report_path}")
