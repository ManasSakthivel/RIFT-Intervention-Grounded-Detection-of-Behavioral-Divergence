"""
adversarial_generator.py — RIFT Sprint 3 Adversarial Failure Benchmark Generator

Generates complex failure scenarios that challenge simple heuristic baselines:
  Family A: Inverted Onset (downstream spikes before root cause due to asynchronous queue buffering)
  Family B: Retry Amplification (child exhibits higher latency spike than failing parent due to retry storm)
  Family C: Shared-Infrastructure Confounding (unmeasured shared CPU / DB locks affecting multiple services)
  Family D: Multiple Simultaneous Faults (overlapping dual root causes)
  Family E: Noisy & Incomplete Telemetry (15% random dropouts, timestamp jitter, high variance noise)
  Family F: Deep Cascade Topology (multi-hop degradation paths)

Authority: docs/SPRINT3_BENCHMARK_SPECIFICATION.md
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd


SERVICES = [
    "frontend",
    "cart",
    "product_catalog",
    "currency",
    "payment",
    "shipping",
    "email",
    "checkout",
    "recommendation",
    "ad",
    "redis_cart",
]


@dataclass
class AdversarialScenario:
    scenario_id: str
    family: str  # A_INVERTED, B_RETRY, C_CONFOUNDED, D_MULTI, E_NOISE, F_DEEP
    name: str
    root_cause_service: str
    secondary_root_cause: Optional[str] = None
    injected_at_t: float = 60.0
    expected_recovery_t: float = 180.0
    causal_path: List[Tuple[str, str]] = field(default_factory=list)
    confounded: bool = False
    confounder_description: Optional[str] = None
    affected_services: List[str] = field(default_factory=list)
    seed: int = 42
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def generate_adversarial_metrics(
    scenario: AdversarialScenario,
    services: List[str] = SERVICES,
    delta_t: float = 10.0,
    seed: int = 42,
) -> Dict[str, pd.DataFrame]:
    """
    Generate time series metrics matching the specific adversarial failure family.
    """
    rng = np.random.default_rng(seed + scenario.seed)
    t_start = max(0.0, scenario.injected_at_t - 60.0)
    t_end = t_start + 180.0
    times = list(np.arange(t_start, t_end, delta_t))

    root = scenario.root_cause_service
    family = scenario.family
    params = scenario.parameters

    metrics: Dict[str, pd.DataFrame] = {}

    for svc in services:
        values = []
        for t in times:
            # Baseline normal noise
            base_noise = rng.normal(0.0, 10.0)

            if t < scenario.injected_at_t:
                val = base_noise
            else:
                if family == "A_INVERTED":
                    # Downstream victim spikes immediately; root cause is masked by buffer and spikes later
                    buffer_delay = params.get("buffer_delay_s", 20.0)
                    victim = params.get("victim_service", "frontend")
                    if svc == victim:
                        val = 45.0 + rng.normal(0.0, 5.0)  # Downstream spikes FIRST
                    elif svc == root:
                        if t >= scenario.injected_at_t + buffer_delay:
                            val = 55.0 + rng.normal(0.0, 5.0)  # Root cause spikes LATER
                        else:
                            val = base_noise
                    else:
                        val = base_noise

                elif family == "B_RETRY":
                    # Child exhibits LARGER spike (e.g. z=8) due to client retry storm; root cause has moderate spike (z=3.5)
                    child = params.get("child_service", "checkout")
                    if svc == root:
                        val = 35.0 + rng.normal(0.0, 4.0)  # Moderate spike at root
                    elif svc == child:
                        val = 80.0 + rng.normal(0.0, 8.0)  # Amplified spike at child
                    elif svc in scenario.affected_services:
                        val = 30.0 + rng.normal(0.0, 5.0)
                    else:
                        val = base_noise

                elif family == "C_CONFOUNDED":
                    # Latent resource contention affects both root and affected services simultaneously
                    if svc == root or svc in scenario.affected_services:
                        val = 50.0 + rng.normal(0.0, 6.0)
                    else:
                        val = base_noise

                elif family == "D_MULTI":
                    # Two concurrent root causes
                    sec_root = scenario.secondary_root_cause
                    if svc == root:
                        val = 50.0 + rng.normal(0.0, 5.0)
                    elif svc == sec_root:
                        val = 48.0 + rng.normal(0.0, 5.0)
                    elif svc in scenario.affected_services:
                        val = 35.0 + rng.normal(0.0, 5.0)
                    else:
                        val = base_noise

                elif family == "E_NOISE":
                    # High variance noise and random dropouts
                    if svc == root:
                        val = 45.0 + rng.normal(0.0, 15.0)
                    elif svc in scenario.affected_services:
                        val = 35.0 + rng.normal(0.0, 15.0)
                    else:
                        val = rng.normal(0.0, 15.0)

                elif family == "F_DEEP":
                    # Multi-hop cascade: root -> hop1 -> hop2 -> hop3
                    path = scenario.causal_path
                    hop_delay = 0.0
                    for i, (src, tgt) in enumerate(path):
                        if svc == tgt:
                            hop_delay = (i + 1) * delta_t
                    if svc == root:
                        val = 50.0 + rng.normal(0.0, 5.0)
                    elif hop_delay > 0 and t >= scenario.injected_at_t + hop_delay:
                        val = 40.0 + rng.normal(0.0, 5.0)
                    else:
                        val = base_noise
                else:
                    val = base_noise

            values.append(float(val))

        df = pd.DataFrame({"time": times, "value": values})
        # Simulate 15% random dropouts in Family E
        if family == "E_NOISE":
            keep_mask = rng.uniform(0.0, 1.0, size=len(df)) > 0.15
            df = df[keep_mask].reset_index(drop=True)

        metrics[svc] = df

    return metrics


def generate_adversarial_cohort(cohort_size_per_family: int = 5, seed: int = 1000) -> List[AdversarialScenario]:
    """Generate a balanced cohort of adversarial stress-test scenarios."""
    scenarios: List[AdversarialScenario] = []
    sc_idx = 1

    # Family A: Inverted Onset
    for i in range(cohort_size_per_family):
        sc = AdversarialScenario(
            scenario_id=f"ADV_A_{i+1:02d}",
            family="A_INVERTED",
            name=f"Inverted Onset Async Queue {i+1}",
            root_cause_service="cart",
            injected_at_t=60.0,
            causal_path=[("cart", "checkout"), ("checkout", "frontend")],
            confounded=False,
            affected_services=["frontend", "checkout"],
            seed=seed + sc_idx,
            parameters={"buffer_delay_s": 20.0, "victim_service": "frontend"},
        )
        scenarios.append(sc)
        sc_idx += 1

    # Family B: Retry Amplification
    for i in range(cohort_size_per_family):
        sc = AdversarialScenario(
            scenario_id=f"ADV_B_{i+1:02d}",
            family="B_RETRY",
            name=f"Client Retry Amplification {i+1}",
            root_cause_service="payment",
            injected_at_t=60.0,
            causal_path=[("payment", "checkout"), ("checkout", "frontend")],
            confounded=False,
            affected_services=["checkout", "frontend"],
            seed=seed + sc_idx,
            parameters={"child_service": "checkout"},
        )
        scenarios.append(sc)
        sc_idx += 1

    # Family C: Shared Infrastructure Confounding
    for i in range(cohort_size_per_family):
        sc = AdversarialScenario(
            scenario_id=f"ADV_C_{i+1:02d}",
            family="C_CONFOUNDED",
            name=f"Shared Host CPU Throttle {i+1}",
            root_cause_service="recommendation",
            injected_at_t=60.0,
            causal_path=[],
            confounded=True,
            confounder_description="Shared hypervisor core contention",
            affected_services=["recommendation", "product_catalog"],
            seed=seed + sc_idx,
        )
        scenarios.append(sc)
        sc_idx += 1

    # Family D: Multiple Simultaneous Faults
    for i in range(cohort_size_per_family):
        sc = AdversarialScenario(
            scenario_id=f"ADV_D_{i+1:02d}",
            family="D_MULTI",
            name=f"Dual Root Cause Concurrent Degradation {i+1}",
            root_cause_service="shipping",
            secondary_root_cause="email",
            injected_at_t=60.0,
            causal_path=[("shipping", "checkout"), ("email", "checkout")],
            confounded=False,
            affected_services=["checkout"],
            seed=seed + sc_idx,
        )
        scenarios.append(sc)
        sc_idx += 1

    # Family E: Noisy Telemetry & Dropouts
    for i in range(cohort_size_per_family):
        sc = AdversarialScenario(
            scenario_id=f"ADV_E_{i+1:02d}",
            family="E_NOISE",
            name=f"Noisy Telemetry with Dropouts {i+1}",
            root_cause_service="product_catalog",
            injected_at_t=60.0,
            causal_path=[("product_catalog", "frontend")],
            confounded=False,
            affected_services=["frontend"],
            seed=seed + sc_idx,
        )
        scenarios.append(sc)
        sc_idx += 1

    # Family F: Deep Cascade
    for i in range(cohort_size_per_family):
        sc = AdversarialScenario(
            scenario_id=f"ADV_F_{i+1:02d}",
            family="F_DEEP",
            name=f"Deep Multi-Hop Degradation Cascade {i+1}",
            root_cause_service="redis_cart",
            injected_at_t=60.0,
            causal_path=[("redis_cart", "cart"), ("cart", "checkout"), ("checkout", "frontend")],
            confounded=False,
            affected_services=["cart", "checkout", "frontend"],
            seed=seed + sc_idx,
        )
        scenarios.append(sc)
        sc_idx += 1

    return scenarios
