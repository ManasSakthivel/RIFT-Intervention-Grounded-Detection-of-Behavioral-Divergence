"""
synthetic_benchmark.py — RIFT Phase 3P Synthetic Fault Benchmark

Provides ground-truth fault scenarios for the RIFT evaluation benchmark.
Ground truth is locked before any evaluation; RIFT is evaluated on the
HELD_OUT_TEST split only for final results.

Authority: docs/PHASE_3_SPEC_FREEZE.md §15, §17
           docs/hypotheses.md H1–H5
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Fault type constants
# ---------------------------------------------------------------------------

NETWORK_LATENCY = "NETWORK_LATENCY"
PACKET_LOSS = "PACKET_LOSS"
SERVICE_DEGRADATION = "SERVICE_DEGRADATION"
RESOURCE_CONTENTION = "RESOURCE_CONTENTION"
QUEUEING = "QUEUEING"
DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
MULTI_CAUSE = "MULTI_CAUSE"
CONFOUNDED = "CONFOUNDED"

FAULT_TYPES = [
    NETWORK_LATENCY,
    PACKET_LOSS,
    SERVICE_DEGRADATION,
    RESOURCE_CONTENTION,
    QUEUEING,
    DEPENDENCY_FAILURE,
    MULTI_CAUSE,
    CONFOUNDED,
]

SPLIT_DEVELOPMENT = "DEVELOPMENT"
SPLIT_VALIDATION = "VALIDATION"
SPLIT_HELD_OUT_TEST = "HELD_OUT_TEST"

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FaultScenario:
    """
    Single ground-truth fault scenario.

    All fields are immutable after creation (frozen=True).
    ground_truth_locked=True is required on all production scenarios;
    set to False only in unit tests.
    """

    fault_id: str
    name: str
    root_cause_service: str
    fault_type: str  # one of FAULT_TYPES
    injected_at_t: float  # seconds since epoch-relative window start
    expected_recovery_t: float
    causal_path: List[Tuple[str, str]]  # directed edges root→effect
    confounded: bool          # True if scenario has an unobserved common cause
    confounder_description: Optional[str]
    affected_services: List[str]
    observable_by_rift: bool  # True if root-cause service is instrumented
    split: str                # DEVELOPMENT | VALIDATION | HELD_OUT_TEST
    ground_truth_locked: bool = True   # immutable after creation
    seed: int = 42

    def __post_init__(self) -> None:
        if self.fault_type not in FAULT_TYPES:
            raise ValueError(
                f"Unknown fault_type '{self.fault_type}'. Must be one of {FAULT_TYPES}"
            )
        if self.split not in (SPLIT_DEVELOPMENT, SPLIT_VALIDATION, SPLIT_HELD_OUT_TEST):
            raise ValueError(f"Unknown split '{self.split}'.")
        if not self.ground_truth_locked:
            import warnings
            warnings.warn(
                f"FaultScenario {self.fault_id} has ground_truth_locked=False. "
                "This is only acceptable in unit tests.",
                stacklevel=2,
            )


# ---------------------------------------------------------------------------
# Baseline statistics helper
# ---------------------------------------------------------------------------

def _default_baseline_stats() -> Dict[str, Dict[str, float]]:
    """Return nominal baseline metric statistics for all 11 Online-Boutique services."""
    baseline: Dict[str, Dict[str, float]] = {}
    for svc in SyntheticBenchmark.SERVICES:
        baseline[svc] = {
            "lat_p99_mean": 50.0,   # ms
            "lat_p99_std": 8.0,
            "err_rate_mean": 0.001,
            "err_rate_std": 0.0005,
            "rps_mean": 100.0,
            "rps_std": 15.0,
            "cpu_pct_mean": 30.0,
            "cpu_pct_std": 5.0,
            "mem_pct_mean": 45.0,
            "mem_pct_std": 6.0,
        }
    # Tune a few services to reflect realistic topology load
    baseline["frontend"]["rps_mean"] = 300.0
    baseline["frontend"]["rps_std"] = 40.0
    baseline["redis_cart"]["lat_p99_mean"] = 2.0
    baseline["redis_cart"]["lat_p99_std"] = 0.5
    baseline["redis_cart"]["cpu_pct_mean"] = 10.0
    baseline["payment"]["lat_p99_mean"] = 120.0
    baseline["payment"]["lat_p99_std"] = 20.0
    return baseline


# ---------------------------------------------------------------------------
# Main benchmark class
# ---------------------------------------------------------------------------


class SyntheticBenchmark:
    """
    Reproducible fault benchmark for RIFT evaluation.

    Uses Online Boutique topology (11 services: frontend, cart, checkout,
    payment, product_catalog, recommendation, shipping, email, currency,
    ad, redis_cart).

    Ground truth is locked before any evaluation.
    RIFT is evaluated on the HELD_OUT_TEST split only for final results.

    Authority: docs/PHASE_3_SPEC_FREEZE.md §15
    """

    SERVICES: List[str] = [
        "frontend",
        "cart",
        "checkout",
        "payment",
        "product_catalog",
        "recommendation",
        "shipping",
        "email",
        "currency",
        "ad",
        "redis_cart",
    ]

    # Directed call graph: caller → list of callees
    CALL_GRAPH: Dict[str, List[str]] = {
        "frontend": [
            "cart",
            "product_catalog",
            "recommendation",
            "shipping",
            "currency",
            "ad",
            "checkout",
        ],
        "checkout": ["payment", "shipping", "email", "cart", "currency"],
        "cart": ["redis_cart"],
        "recommendation": ["product_catalog"],
        "payment": [],
        "product_catalog": [],
        "shipping": [],
        "email": [],
        "currency": [],
        "ad": [],
        "redis_cart": [],
    }

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    def _causal_path_from_root(
        self, root: str, targets: List[str]
    ) -> List[Tuple[str, str]]:
        """
        Return the shortest causal edges connecting ``root`` to each target
        by BFS over CALL_GRAPH.  Edges are (parent, child).
        """
        visited: Dict[str, Optional[str]] = {root: None}
        queue = [root]
        while queue:
            node = queue.pop(0)
            for child in self.CALL_GRAPH.get(node, []):
                if child not in visited:
                    visited[child] = node
                    queue.append(child)

        edges: List[Tuple[str, str]] = []
        for target in targets:
            if target not in visited:
                continue
            cur = target
            while visited[cur] is not None:
                parent = visited[cur]
                assert parent is not None
                edge = (parent, cur)
                if edge not in edges:
                    edges.append(edge)
                cur = parent
        return edges

    def _split_assignment(
        self, idx: int, total: int, rng: random.Random
    ) -> str:
        """
        Assign split deterministically by index position.
        Roughly 50 % DEVELOPMENT / 25 % VALIDATION / 25 % HELD_OUT_TEST.
        """
        if idx < total // 2:
            return SPLIT_DEVELOPMENT
        if idx < (3 * total) // 4:
            return SPLIT_VALIDATION
        return SPLIT_HELD_OUT_TEST

    # ---------------------------------------------------------------------------
    # Per-type fault factory methods
    # ---------------------------------------------------------------------------

    def _make_network_latency(
        self, trial: int, split: str, seed: int
    ) -> FaultScenario:
        root = "frontend"
        affected = ["frontend", "checkout", "cart"]
        return FaultScenario(
            fault_id=f"NL_{trial:02d}",
            name=f"Network latency on frontend (trial {trial})",
            root_cause_service=root,
            fault_type=NETWORK_LATENCY,
            injected_at_t=60.0,
            expected_recovery_t=360.0,
            causal_path=self._causal_path_from_root(root, ["checkout", "cart"]),
            confounded=False,
            confounder_description=None,
            affected_services=affected,
            observable_by_rift=True,
            split=split,
            seed=seed + trial,
        )

    def _make_packet_loss(
        self, trial: int, split: str, seed: int
    ) -> FaultScenario:
        root = "cart"
        affected = ["cart", "redis_cart", "frontend"]
        return FaultScenario(
            fault_id=f"PL_{trial:02d}",
            name=f"Packet loss on cart↔redis_cart link (trial {trial})",
            root_cause_service=root,
            fault_type=PACKET_LOSS,
            injected_at_t=60.0,
            expected_recovery_t=420.0,
            causal_path=self._causal_path_from_root("cart", ["redis_cart"]),
            confounded=False,
            confounder_description=None,
            affected_services=affected,
            observable_by_rift=True,
            split=split,
            seed=seed + trial,
        )

    def _make_service_degradation(
        self, trial: int, split: str, seed: int
    ) -> FaultScenario:
        root = "payment"
        affected = ["payment", "checkout", "frontend"]
        return FaultScenario(
            fault_id=f"SD_{trial:02d}",
            name=f"Payment service CPU spike (trial {trial})",
            root_cause_service=root,
            fault_type=SERVICE_DEGRADATION,
            injected_at_t=60.0,
            expected_recovery_t=480.0,
            causal_path=self._causal_path_from_root("checkout", ["payment"])
            + self._causal_path_from_root("frontend", ["checkout"]),
            confounded=False,
            confounder_description=None,
            affected_services=affected,
            observable_by_rift=True,
            split=split,
            seed=seed + trial,
        )

    def _make_resource_contention(
        self, trial: int, split: str, seed: int
    ) -> FaultScenario:
        root = "redis_cart"
        affected = ["redis_cart", "cart", "checkout", "frontend"]
        return FaultScenario(
            fault_id=f"RC_{trial:02d}",
            name=f"Redis memory contention (trial {trial})",
            root_cause_service=root,
            fault_type=RESOURCE_CONTENTION,
            injected_at_t=60.0,
            expected_recovery_t=600.0,
            causal_path=self._causal_path_from_root(root, ["cart"]),
            confounded=False,
            confounder_description=None,
            affected_services=affected,
            observable_by_rift=True,
            split=split,
            seed=seed + trial,
        )

    def _make_queueing(
        self, trial: int, split: str, seed: int
    ) -> FaultScenario:
        root = "checkout"
        affected = ["checkout", "payment", "shipping", "email", "frontend"]
        return FaultScenario(
            fault_id=f"QU_{trial:02d}",
            name=f"Checkout request queue saturation (trial {trial})",
            root_cause_service=root,
            fault_type=QUEUEING,
            injected_at_t=60.0,
            expected_recovery_t=540.0,
            causal_path=self._causal_path_from_root(root, ["payment", "shipping"]),
            confounded=False,
            confounder_description=None,
            affected_services=affected,
            observable_by_rift=True,
            split=split,
            seed=seed + trial,
        )

    def _make_dependency_failure(
        self, trial: int, split: str, seed: int
    ) -> FaultScenario:
        root = "product_catalog"
        affected = ["product_catalog", "recommendation", "frontend"]
        return FaultScenario(
            fault_id=f"DF_{trial:02d}",
            name=f"Product-catalog OOM crash (trial {trial})",
            root_cause_service=root,
            fault_type=DEPENDENCY_FAILURE,
            injected_at_t=60.0,
            expected_recovery_t=300.0,
            causal_path=self._causal_path_from_root("recommendation", ["product_catalog"])
            + self._causal_path_from_root("frontend", ["recommendation"]),
            confounded=False,
            confounder_description=None,
            affected_services=affected,
            observable_by_rift=True,
            split=split,
            seed=seed + trial,
        )

    def _make_multi_cause(
        self, trial: int, split: str, seed: int
    ) -> FaultScenario:
        # Two simultaneous faults: payment CPU spike + shipping network latency
        affected = ["payment", "shipping", "checkout", "frontend"]
        path = (
            self._causal_path_from_root("checkout", ["payment"])
            + self._causal_path_from_root("checkout", ["shipping"])
            + self._causal_path_from_root("frontend", ["checkout"])
        )
        return FaultScenario(
            fault_id=f"MC_{trial:02d}",
            name=f"Multi-cause: payment CPU spike + shipping latency (trial {trial})",
            root_cause_service="payment",  # primary; shipping is co-root
            fault_type=MULTI_CAUSE,
            injected_at_t=60.0,
            expected_recovery_t=600.0,
            causal_path=path,
            confounded=False,
            confounder_description=None,
            affected_services=affected,
            observable_by_rift=True,
            split=split,
            seed=seed + trial,
        )

    def _make_confounded_simple(
        self, idx: int, split: str, seed: int
    ) -> FaultScenario:
        """
        Shared-host pressure causes correlated anomalies on two services.
        The confounder (host CPU saturation) is NOT an instrumented RIFT node.
        FCI should emit a bidirected edge between the co-affected services.
        """
        # co-located pair varies across trials
        pairs = [
            ("cart", "redis_cart"),
            ("payment", "email"),
            ("recommendation", "product_catalog"),
            ("shipping", "currency"),
        ]
        svc_a, svc_b = pairs[idx % len(pairs)]
        affected = [svc_a, svc_b, "checkout", "frontend"]
        return FaultScenario(
            fault_id=f"CF_{idx:02d}",
            name=f"Shared-host confounder: {svc_a} ↔ {svc_b} (idx {idx})",
            root_cause_service=svc_a,
            fault_type=CONFOUNDED,
            injected_at_t=60.0,
            expected_recovery_t=480.0,
            causal_path=[(svc_a, svc_b)],  # spurious correlation, not causal
            confounded=True,
            confounder_description=(
                f"Shared physical host CPU saturation affects both {svc_a} and "
                f"{svc_b} simultaneously. The correlation between them is due to "
                f"the latent host-level confounder (U_host), NOT a direct causal "
                f"link. FCI should produce {svc_a} ↔ {svc_b} (bidirected). "
                "RIFT abstains when CID score is below threshold (L1)."
            ),
            affected_services=affected,
            observable_by_rift=False,  # host CPU is not in V for this scenario
            split=split,
            seed=seed + idx,
        )

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    def generate_all_faults(self, seed: int = 42) -> List[FaultScenario]:
        """
        Generate the primary benchmark: minimum 4 fault types × 3 trials ×
        2 systems = 24+ scenarios.

        Covers all 8 fault types across 3 trials each, producing 24 scenarios
        before confounded scenarios are added.

        Fixed seed ensures reproducibility. Splits are assigned deterministically
        (50 % DEV / 25 % VAL / 25 % HELD_OUT_TEST) — see §15.

        Do NOT tune RIFT against HELD_OUT_TEST scenarios.
        """
        rng = random.Random(seed)
        scenarios: List[FaultScenario] = []

        factories = [
            self._make_network_latency,
            self._make_packet_loss,
            self._make_service_degradation,
            self._make_resource_contention,
            self._make_queueing,
            self._make_dependency_failure,
            self._make_multi_cause,
        ]

        # 7 fault types × 3 trials = 21 non-confounded scenarios
        # Add 3 more via an additional network-latency trial set (checkout root)
        # to hit ≥ 24 total
        for trial in range(1, 4):
            split = self._split_assignment(len(scenarios), 24, rng)
            for factory in factories:
                split = self._split_assignment(len(scenarios), 24, rng)
                scenarios.append(factory(trial, split, seed))

        # Add confounded scenarios (§15: ≥ 48 for 80 % power on H2)
        scenarios.extend(self.generate_confounded_scenarios(n=48, seed=seed))
        return scenarios

    def generate_confounded_scenarios(
        self, n: int = 48, seed: int = 42
    ) -> List[FaultScenario]:
        """
        Generate confounded scenarios where shared-resource pressure causes
        correlated anomalies across services that share a host or database.
        These are ESSENTIAL for testing H2 (intervention vs. observational).

        Authority: docs/hypotheses.md H2, docs/PHASE_3_SPEC_FREEZE.md §15

        Target: ≥ 48 confounded incidents for 80% power on H2.
        If fewer generated: document as sample-size limitation (L1).

        The confounder is a latent variable (U_host) NOT in V. FCI should emit
        a bidirected edge; RIFT abstains under L1 when CID is inconclusive.
        """
        rng = random.Random(seed)
        scenarios: List[FaultScenario] = []
        for i in range(n):
            split = self._split_assignment(i, n, rng)
            scenarios.append(self._make_confounded_simple(i, split, seed))

        actual = len(scenarios)
        if actual < 48:
            import warnings
            warnings.warn(
                f"Only {actual} confounded scenarios generated (target ≥ 48). "
                "80% power for H2 cannot be claimed. Report achieved power only. "
                "See docs/PHASE_3_SPEC_FREEZE.md §15.",
                stacklevel=2,
            )
        return scenarios

    def simulate_metrics(
        self,
        fault: FaultScenario,
        baseline_stats: Optional[Dict[str, Dict[str, float]]] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Simulate metric time series for a fault scenario.

        Returns dict of service → DataFrame with columns:
            [time, lat_p99, err_rate, rps, cpu_pct, mem_pct]

        Causal propagation model:
        - Root-cause service shows immediate degradation at injected_at_t.
        - Downstream services degrade with delay proportional to BFS depth
          in CALL_GRAPH from root (1 hop = 10 s propagation lag).
        - Confounded services show correlated (NOT causally linked) degradation
          driven by the shared latent variable U_host, simulated as additive
          Gaussian noise with the same covariance as the root-cause signal.

        This simulation provides INDEPENDENT ground truth.  It is NOT used
        as the oracle for RIFT's own causal graph.

        Authority: docs/PHASE_3_SPEC_FREEZE.md §1 (M/M/1 queueing), §17 L1
        """
        if baseline_stats is None:
            baseline_stats = _default_baseline_stats()

        rng_seed = seed if seed is not None else fault.seed
        rng = np.random.default_rng(rng_seed)

        duration = fault.expected_recovery_t + 120.0
        dt = 10.0  # seconds per window (§2: Δt = 10 s)
        times = np.arange(0.0, duration, dt)
        n_steps = len(times)

        # BFS depth from root cause to each service
        depth: Dict[str, int] = {fault.root_cause_service: 0}
        queue = [fault.root_cause_service]
        while queue:
            node = queue.pop(0)
            for child in self.CALL_GRAPH.get(node, []):
                if child not in depth:
                    depth[child] = depth[node] + 1
                    queue.append(child)

        result: Dict[str, pd.DataFrame] = {}

        for svc in self.SERVICES:
            bs = baseline_stats.get(svc, baseline_stats["frontend"])

            lat = rng.normal(bs["lat_p99_mean"], bs["lat_p99_std"], n_steps)
            err = rng.normal(bs["err_rate_mean"], bs["err_rate_std"], n_steps).clip(0)
            rps = rng.normal(bs["rps_mean"], bs["rps_std"], n_steps).clip(0)
            cpu = rng.normal(bs["cpu_pct_mean"], bs["cpu_pct_std"], n_steps).clip(0, 100)
            mem = rng.normal(bs["mem_pct_mean"], bs["mem_pct_std"], n_steps).clip(0, 100)

            # Fault onset index
            onset_idx = int(fault.injected_at_t / dt)
            recovery_idx = int(fault.expected_recovery_t / dt)

            if svc == fault.root_cause_service:
                # Immediate degradation at root cause
                lat[onset_idx:recovery_idx] *= _fault_multiplier(fault.fault_type)
                err[onset_idx:recovery_idx] = np.clip(
                    err[onset_idx:recovery_idx] + _err_delta(fault.fault_type), 0, 1
                )
                cpu[onset_idx:recovery_idx] = np.clip(
                    cpu[onset_idx:recovery_idx] + _cpu_delta(fault.fault_type), 0, 100
                )

            elif svc in fault.affected_services and not fault.confounded:
                # Causal downstream: delay = depth × 10 s (1 hop = 1 window)
                svc_depth = depth.get(svc, 99)
                if svc_depth == 99:
                    # service is affected but not reachable via CALL_GRAPH —
                    # use a conservative 3-hop delay
                    svc_depth = 3
                propagation_lag = int(svc_depth)  # number of windows
                delayed_onset = min(onset_idx + propagation_lag, n_steps)
                if delayed_onset < recovery_idx:
                    multiplier = max(1.0, _fault_multiplier(fault.fault_type) * (0.9 ** svc_depth))
                    lat[delayed_onset:recovery_idx] *= multiplier
                    err[delayed_onset:recovery_idx] = np.clip(
                        err[delayed_onset:recovery_idx]
                        + _err_delta(fault.fault_type) * (0.8 ** svc_depth),
                        0, 1,
                    )

            elif fault.confounded and svc in fault.affected_services:
                # Confounded service: correlated noise from shared U_host
                # NOT a causal link — same magnitude, independent noise draw
                conf_noise = rng.normal(0, bs["lat_p99_std"] * 3, recovery_idx - onset_idx)
                lat[onset_idx:recovery_idx] += conf_noise.clip(0)
                cpu[onset_idx:recovery_idx] = np.clip(
                    cpu[onset_idx:recovery_idx]
                    + rng.normal(20, 5, recovery_idx - onset_idx),
                    0, 100,
                )

            result[svc] = pd.DataFrame(
                {
                    "time": times,
                    "lat_p99": lat.clip(0),
                    "err_rate": err,
                    "rps": rps,
                    "cpu_pct": cpu,
                    "mem_pct": mem,
                }
            )

        return result


# ---------------------------------------------------------------------------
# Private helpers for fault-signal injection
# ---------------------------------------------------------------------------


def _fault_multiplier(fault_type: str) -> float:
    """Latency multiplier applied to root-cause service during fault window."""
    return {
        NETWORK_LATENCY: 8.0,
        PACKET_LOSS: 5.0,
        SERVICE_DEGRADATION: 4.0,
        RESOURCE_CONTENTION: 6.0,
        QUEUEING: 10.0,
        DEPENDENCY_FAILURE: 3.0,
        MULTI_CAUSE: 6.0,
        CONFOUNDED: 4.0,
    }.get(fault_type, 3.0)


def _err_delta(fault_type: str) -> float:
    """Additive error-rate delta (fraction) applied during fault window."""
    return {
        NETWORK_LATENCY: 0.05,
        PACKET_LOSS: 0.20,
        SERVICE_DEGRADATION: 0.10,
        RESOURCE_CONTENTION: 0.05,
        QUEUEING: 0.15,
        DEPENDENCY_FAILURE: 0.50,
        MULTI_CAUSE: 0.20,
        CONFOUNDED: 0.08,
    }.get(fault_type, 0.05)


def _cpu_delta(fault_type: str) -> float:
    """Additive CPU-% delta applied to root-cause service during fault window."""
    return {
        NETWORK_LATENCY: 5.0,
        PACKET_LOSS: 5.0,
        SERVICE_DEGRADATION: 45.0,
        RESOURCE_CONTENTION: 60.0,
        QUEUEING: 30.0,
        DEPENDENCY_FAILURE: 20.0,
        MULTI_CAUSE: 35.0,
        CONFOUNDED: 15.0,
    }.get(fault_type, 10.0)
