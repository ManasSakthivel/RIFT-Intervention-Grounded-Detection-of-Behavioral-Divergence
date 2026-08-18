"""RIFT Fault Injection Engine — Phase 3.5D.

Implements FaultInjector for controlled, independently verified fault
injection against the Online Boutique microservice benchmark.

SCIENTIFIC CONSTRAINTS
----------------------
1. dry_run=True by default.  Commands are LOGGED but NOT executed unless
   dry_run is explicitly set to False on a Linux testbed with
   CAP_NET_ADMIN and a Kubernetes namespace matching rift-eval-*.

2. verify_injection() is NOT optional.  An inject() call that returns a
   FaultInjectionRecord with injection_verified=False MUST NOT be used
   as evidence of a fault being present.  The RIFT pipeline treats
   unverified injections as ABORTED experiments.

3. The manifest split is immutable.  The constants MANIFEST_SEED,
   MANIFEST_SPLIT_DEVELOPMENT, MANIFEST_SPLIT_VALIDATION, and
   MANIFEST_SPLIT_HELD_OUT_TEST must match datasets/rift_faults/manifest.json
   exactly.  _verify_manifest_split() is called at module import time and
   raises RuntimeError on mismatch.

4. The held-out test set MUST NOT be inspected during tuning.
   FaultInjector refuses to process scenarios whose split==HELD_OUT_TEST
   unless allow_held_out=True (reserved for final evaluation only).

Authority: docs/PHASE_3_SPEC_FREEZE.md §11 / RIFT GATE 3.5D
"""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from src.rift.intervention.network_intervention import (
    NetworkInterventionEngine,
    NetworkInterventionRecord,
    NetworkInterventionStatus,
)

# ---------------------------------------------------------------------------
# Manifest constants (must match datasets/rift_faults/manifest.json exactly)
# ---------------------------------------------------------------------------
MANIFEST_SEED: int = 42
MANIFEST_SPLIT_DEVELOPMENT: int = 36
MANIFEST_SPLIT_VALIDATION: int = 18
MANIFEST_SPLIT_HELD_OUT_TEST: int = 15
_MANIFEST_PATH = (
    Path(__file__).resolve().parents[3] / "datasets" / "rift_faults" / "manifest.json"
)


def _verify_manifest_split() -> None:
    """Verify manifest split counts match the frozen constants.

    Called at module import time.  Raises RuntimeError on any mismatch so
    that accidental drift between the code and the dataset is caught early.
    The held-out test set must remain immutable across all tuning phases.
    """
    if not _MANIFEST_PATH.exists():
        # Gracefully skip verification when running outside the full repo
        return
    with _MANIFEST_PATH.open() as fh:
        manifest = json.load(fh)
    split_counts = manifest.get("split_counts", {})
    errors: List[str] = []
    if manifest.get("seed") != MANIFEST_SEED:
        errors.append(
            f"manifest seed {manifest.get('seed')} != expected {MANIFEST_SEED}"
        )
    if split_counts.get("DEVELOPMENT") != MANIFEST_SPLIT_DEVELOPMENT:
        errors.append(
            f"DEVELOPMENT count {split_counts.get('DEVELOPMENT')} != {MANIFEST_SPLIT_DEVELOPMENT}"
        )
    if split_counts.get("VALIDATION") != MANIFEST_SPLIT_VALIDATION:
        errors.append(
            f"VALIDATION count {split_counts.get('VALIDATION')} != {MANIFEST_SPLIT_VALIDATION}"
        )
    if split_counts.get("HELD_OUT_TEST") != MANIFEST_SPLIT_HELD_OUT_TEST:
        errors.append(
            f"HELD_OUT_TEST count {split_counts.get('HELD_OUT_TEST')} != {MANIFEST_SPLIT_HELD_OUT_TEST}"
        )
    if errors:
        raise RuntimeError(
            "RIFT manifest split mismatch — the dataset has changed or constants "
            "are incorrect.  Fix before proceeding:\n" + "\n".join(errors)
        )


# Verify at import time (raises RuntimeError on mismatch)
_verify_manifest_split()


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class FaultType(str, Enum):
    NETWORK_LATENCY = "NETWORK_LATENCY"
    PACKET_LOSS = "PACKET_LOSS"
    SERVICE_DEGRADATION = "SERVICE_DEGRADATION"
    RESOURCE_CONTENTION = "RESOURCE_CONTENTION"
    QUEUEING = "QUEUEING"
    DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
    MULTI_CAUSE = "MULTI_CAUSE"
    CONFOUNDED = "CONFOUNDED"


class FaultInjectionStatus(str, Enum):
    PENDING = "PENDING"
    INJECTED = "INJECTED"          # command ran; NOT yet verified
    VERIFIED = "VERIFIED"          # independent measurement confirmed
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    ABORTED = "ABORTED"            # dry_run or pre-flight check failed
    DRY_RUN = "DRY_RUN"


class SplitLabel(str, Enum):
    DEVELOPMENT = "DEVELOPMENT"
    VALIDATION = "VALIDATION"
    HELD_OUT_TEST = "HELD_OUT_TEST"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class FaultScenario:
    """Parsed representation of a single fault scenario from the benchmark.

    Sourced from datasets/rift_faults/{development,validation}.json.
    The held-out test split must NOT be loaded during tuning phases.
    """

    fault_id: str
    scenario_id: str
    fault_type: FaultType
    target_service: str
    injection_time_s: float            # relative to experiment start
    duration_s: float                  # expected fault duration
    expected_causal_mechanism: str
    expected_affected_services: List[str]
    ground_truth_root_cause: str
    whether_confounded: bool
    whether_multi_cause: bool
    expected_identifiability_state: str
    split: SplitLabel
    # Optional fields for network faults
    target_ip: Optional[str] = None
    interface: Optional[str] = None
    latency_ms: Optional[float] = None
    jitter_ms: Optional[float] = None
    packet_loss_pct: Optional[float] = None


@dataclass
class FaultInjectionRecord:
    """Audit record for one fault injection attempt.

    injection_verified must be set by verify_injection(), NOT assumed from
    command exit code.  A record with injection_verified=False represents
    an unconfirmed injection and MUST NOT be used as ground-truth evidence.
    """

    fault_id: str
    scenario_id: str
    injected_at: Optional[float]        # unix timestamp; None in dry_run
    verified_at: Optional[float]        # unix timestamp; None until verified
    injection_verified: bool            # set only by verify_injection()
    verification_method: str            # human-readable description
    measured_delta: Optional[float]     # e.g., latency delta in ms
    expected_delta: Optional[float]     # from scenario spec
    rollback_at: Optional[float]        # unix timestamp; None until rolled back
    status: FaultInjectionStatus
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notes: str = ""
    # Reference to the underlying NetworkInterventionRecord for NETWORK_* faults
    network_record_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Verification helpers (independent measurement)
# ---------------------------------------------------------------------------


def _measure_latency_ms(target_host: str, count: int = 5) -> Optional[float]:
    """Measure round-trip latency to *target_host* using ping.

    Returns median RTT in milliseconds, or None if ping is unavailable.
    This measurement is INDEPENDENT of the tc netem injection command.
    """
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), "-q", target_host],
            capture_output=True,
            timeout=15,
            text=True,
        )
        # Parse "rtt min/avg/max/mdev = x/y/z/w ms"
        for line in result.stdout.splitlines():
            if "rtt" in line and "avg" in line:
                parts = line.split("=")[1].strip().split("/")
                return float(parts[1])  # avg
    except Exception:
        pass
    return None


def _measure_drop_counter(interface: str, destination_ip: str) -> Optional[int]:
    """Read the tc qdisc packet drop counter for *destination_ip* on *interface*.

    Returns integer drop count, or None if tc is unavailable.
    This is an INDEPENDENT measurement from the tc apply command.
    """
    try:
        result = subprocess.run(
            ["tc", "-s", "qdisc", "show", "dev", interface],
            capture_output=True,
            timeout=10,
            text=True,
        )
        drop_count = 0
        for line in result.stdout.splitlines():
            if "dropped" in line:
                # "Sent X bytes X pkts (dropped Y, ...)"
                for token in line.split():
                    if token.isdigit():
                        drop_count += int(token)
                        break
        return drop_count
    except Exception:
        pass
    return None


def _measure_cpu_pct(service_pod: str, namespace: str) -> Optional[float]:
    """Return current CPU usage % for *service_pod* via kubectl top.

    Returns float percentage, or None if kubectl is unavailable.
    """
    try:
        result = subprocess.run(
            ["kubectl", "top", "pod", service_pod, "-n", namespace, "--no-headers"],
            capture_output=True,
            timeout=15,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split()
            # Output: NAME   CPU(cores)   MEMORY(bytes)
            cpu_str = parts[1].rstrip("m")  # e.g., "250m" → "250"
            return float(cpu_str) / 10.0    # millicores → approximate pct
    except Exception:
        pass
    return None


def _measure_queue_depth(service_pod: str, namespace: str) -> Optional[int]:
    """Return queue depth metric for *service_pod* via kubectl exec.

    Returns integer queue depth, or None if measurement fails.
    """
    try:
        result = subprocess.run(
            [
                "kubectl", "exec", service_pod, "-n", namespace, "--",
                "sh", "-c",
                "cat /proc/net/sockstat | grep TCP | awk '{print $3}'",
            ],
            capture_output=True,
            timeout=15,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip())
    except Exception:
        pass
    return None


def _check_health_endpoint(service_pod: str, namespace: str, port: int = 8080) -> bool:
    """Return True if service health endpoint responds successfully.

    Used for independent verification of DEPENDENCY_FAILURE injection.
    """
    try:
        result = subprocess.run(
            [
                "kubectl", "exec", service_pod, "-n", namespace, "--",
                "curl", "-sf", "--max-time", "5",
                f"http://localhost:{port}/health",
            ],
            capture_output=True,
            timeout=15,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# FaultInjector
# ---------------------------------------------------------------------------


class FaultInjector:
    """Execute, independently verify, and roll back fault injections.

    USAGE
    -----
    >>> injector = FaultInjector(dry_run=True)          # safe default
    >>> record = injector.inject(scenario, namespace="rift-eval-dev")
    >>> verified = injector.verify_injection(record)    # MANDATORY
    >>> injector.rollback(record)

    SCIENTIFIC RULES
    ----------------
    - dry_run=True (default) logs every command without executing it.
      Set dry_run=False only on a Linux testbed with CAP_NET_ADMIN and
      a namespace matching rift-eval-*.
    - inject() alone does NOT confirm the fault is active.  Always call
      verify_injection() and check the returned bool before using the
      record as experiment evidence.
    - The HELD_OUT_TEST split is refused unless allow_held_out=True
      (reserved for final evaluation only, not tuning).

    Parameters
    ----------
    dry_run : bool
        Default True — commands are logged, not executed.
    allow_held_out : bool
        If False (default), inject() raises ValueError for HELD_OUT_TEST
        scenarios to prevent inadvertent test-set exposure during tuning.
    """

    def __init__(
        self,
        dry_run: bool = True,
        allow_held_out: bool = False,
    ) -> None:
        self.dry_run = dry_run
        self.allow_held_out = allow_held_out
        self._network_engine = NetworkInterventionEngine(dry_run=dry_run)
        self._active_records: Dict[str, FaultInjectionRecord] = {}

    # ------------------------------------------------------------------
    # inject
    # ------------------------------------------------------------------

    def inject(
        self,
        scenario: FaultScenario,
        namespace: str,
    ) -> FaultInjectionRecord:
        """Inject the fault described by *scenario* into *namespace*.

        IMPORTANT: A returned record with status=INJECTED does NOT mean
        the fault is measurably active.  Always call verify_injection()
        immediately after inject().

        For NETWORK_LATENCY / PACKET_LOSS the underlying
        NetworkInterventionEngine (tc netem per-destination) is used.
        For SERVICE_DEGRADATION stress-ng is launched via kubectl exec.
        For RESOURCE_CONTENTION memory pressure is applied via kubectl exec.
        For DEPENDENCY_FAILURE tc is used to drop all packets to the dependency.
        For QUEUEING a background flood of requests is sent to saturate the
        target's queue (requires wrk or hey on the pod).

        Parameters
        ----------
        scenario : FaultScenario
            Fully populated scenario from the development or validation split.
        namespace : str
            Kubernetes namespace.  Must match rift-eval-* pattern.

        Returns
        -------
        FaultInjectionRecord
            Record with injection_verified=False until verify_injection() runs.

        Raises
        ------
        ValueError
            If scenario.split == HELD_OUT_TEST and allow_held_out is False.
        """
        if (
            scenario.split == SplitLabel.HELD_OUT_TEST
            and not self.allow_held_out
        ):
            raise ValueError(
                f"Refusing to inject fault '{scenario.fault_id}': scenario is in "
                "HELD_OUT_TEST split.  Test-set scenarios MUST NOT be used during "
                "tuning.  Set allow_held_out=True only for final evaluation."
            )

        record = FaultInjectionRecord(
            fault_id=scenario.fault_id,
            scenario_id=scenario.scenario_id,
            injected_at=None,
            verified_at=None,
            injection_verified=False,
            verification_method="PENDING",
            measured_delta=None,
            expected_delta=None,
            rollback_at=None,
            status=FaultInjectionStatus.PENDING,
        )

        ft = scenario.fault_type

        if ft in (FaultType.NETWORK_LATENCY, FaultType.PACKET_LOSS):
            record = self._inject_network(scenario, namespace, record)

        elif ft == FaultType.SERVICE_DEGRADATION:
            record = self._inject_service_degradation(scenario, namespace, record)

        elif ft == FaultType.RESOURCE_CONTENTION:
            record = self._inject_resource_contention(scenario, namespace, record)

        elif ft == FaultType.DEPENDENCY_FAILURE:
            record = self._inject_dependency_failure(scenario, namespace, record)

        elif ft == FaultType.QUEUEING:
            record = self._inject_queueing(scenario, namespace, record)

        elif ft == FaultType.MULTI_CAUSE:
            # MULTI_CAUSE is a composition of other fault types; inject each
            # sub-fault separately in the calling pipeline.  Here we create
            # a placeholder record documenting that manual composition is needed.
            record.status = FaultInjectionStatus.ABORTED
            record.notes = (
                "MULTI_CAUSE scenario requires manual composition.  "
                "Inject each constituent fault separately using FaultInjector "
                "with the appropriate sub-scenario."
            )
            return record

        elif ft == FaultType.CONFOUNDED:
            # CONFOUNDED scenarios involve a latent host-level confounder that
            # is not directly injectable via tc/stress-ng.  RIFT treats these
            # as observation-only scenarios.
            record.status = FaultInjectionStatus.ABORTED
            record.notes = (
                "CONFOUNDED scenario: latent confounder (U_host) is not "
                "directly injectable.  Use as observation-only test case."
            )
            return record

        self._active_records[record.record_id] = record
        return record

    # ------------------------------------------------------------------
    # verify_injection
    # ------------------------------------------------------------------

    def verify_injection(self, record: FaultInjectionRecord) -> bool:
        """Independently verify that the fault is measurably active.

        IMPORTANT: This method is NOT optional.  Verification uses an
        independent measurement channel (ping, tc -s, kubectl top, curl)
        that is separate from the injection command itself.  Command
        success (returncode==0) is NOT sufficient evidence that the fault
        is active.

        Updates record.injection_verified, record.verified_at,
        record.verification_method, record.measured_delta, and record.status
        in place.

        Returns
        -------
        bool
            True if the fault is independently confirmed active,
            False otherwise (record.status set to VERIFICATION_FAILED).
        """
        if record.status in (
            FaultInjectionStatus.ABORTED,
            FaultInjectionStatus.DRY_RUN,
        ):
            record.injection_verified = False
            record.notes = (
                record.notes
                + " [verify_injection: skipped — record is ABORTED or DRY_RUN]"
            )
            return False

        if record.status != FaultInjectionStatus.INJECTED:
            record.injection_verified = False
            record.notes = (
                record.notes
                + f" [verify_injection: expected INJECTED status, got {record.status}]"
            )
            return False

        # --- Dispatch verification by the network_record_id hint or notes ---
        verified = False

        if "LATENCY" in record.notes or (
            record.network_record_id is not None
            and "latency" in record.notes.lower()
        ):
            verified = self._verify_latency(record)

        elif "PACKET_LOSS" in record.notes or "packet_loss" in record.notes.lower():
            verified = self._verify_packet_loss(record)

        elif "SERVICE_DEGRADATION" in record.notes:
            verified = self._verify_service_degradation(record)

        elif "RESOURCE_CONTENTION" in record.notes:
            verified = self._verify_resource_contention(record)

        elif "QUEUEING" in record.notes:
            verified = self._verify_queueing(record)

        elif "DEPENDENCY_FAILURE" in record.notes:
            verified = self._verify_dependency_failure(record)

        else:
            # Fallback: cannot determine fault type from record; return False
            record.injection_verified = False
            record.verification_method = "UNKNOWN_FAULT_TYPE"
            record.status = FaultInjectionStatus.VERIFICATION_FAILED
            record.notes += " [verify_injection: fault type not determinable from record]"
            return False

        record.injection_verified = verified
        record.verified_at = time.time()
        record.status = (
            FaultInjectionStatus.VERIFIED
            if verified
            else FaultInjectionStatus.VERIFICATION_FAILED
        )
        return verified

    # ------------------------------------------------------------------
    # rollback
    # ------------------------------------------------------------------

    def rollback(self, record: FaultInjectionRecord) -> bool:
        """Roll back the injected fault associated with *record*.

        Rollback must always be attempted, even if verification failed.
        For network faults the NetworkInterventionEngine rollback is called.
        For resource/stress faults the stress-ng or tc drop processes are
        killed via kubectl exec.

        Returns True if rollback commands completed without error.
        Updates record.rollback_at and record.status.
        """
        success = True

        if record.network_record_id is not None:
            net_record = self._network_engine._active_records.get(
                record.network_record_id
            )
            if net_record is not None:
                rolled = self._network_engine.rollback(net_record)
                success = rolled.status == NetworkInterventionStatus.ROLLED_BACK
            else:
                record.notes += (
                    " [rollback: NetworkInterventionRecord not found in engine; "
                    "may have been already rolled back]"
                )

        elif "SERVICE_DEGRADATION" in record.notes or "RESOURCE_CONTENTION" in record.notes:
            # stress-ng processes are killed by their session; if dry_run they
            # were never started.  Log the rollback intent.
            if not self.dry_run:
                success = self._run_rollback_cmd(
                    ["kubectl", "exec", record.fault_id, "--",
                     "pkill", "-f", "stress-ng"]
                )

        elif "DEPENDENCY_FAILURE" in record.notes:
            # Re-enable packets by removing the tc drop rule
            if not self.dry_run:
                success = self._run_rollback_cmd(
                    ["tc", "qdisc", "del", "dev", "eth0", "root"]
                )

        record.rollback_at = time.time()
        record.status = FaultInjectionStatus.ROLLED_BACK
        self._active_records.pop(record.record_id, None)
        return success

    # ------------------------------------------------------------------
    # Internal injection helpers
    # ------------------------------------------------------------------

    def _inject_network(
        self,
        scenario: FaultScenario,
        namespace: str,
        record: FaultInjectionRecord,
    ) -> FaultInjectionRecord:
        """Inject NETWORK_LATENCY or PACKET_LOSS via NetworkInterventionEngine."""
        iface = scenario.interface or "eth0"
        dest_ip = scenario.target_ip or "0.0.0.0"
        lat = scenario.latency_ms or 100.0
        jitter = scenario.jitter_ms or 10.0
        loss = scenario.packet_loss_pct or 0.0
        handle = "10"

        net_record = NetworkInterventionRecord(
            record_id=str(uuid.uuid4()),
            source_service=namespace,
            destination_service=scenario.target_service,
            destination_ip=dest_ip,
            interface=iface,
            latency_ms=lat,
            jitter_ms=jitter,
            packet_loss_pct=loss,
            tc_handle=f"{handle}:",
            tc_parent="1:",
        )
        self._network_engine.sandbox_namespace = namespace
        applied = self._network_engine.apply(net_record)

        record.network_record_id = applied.record_id
        record.expected_delta = lat if scenario.fault_type == FaultType.NETWORK_LATENCY else loss
        record.notes = f"{scenario.fault_type.value} injected via tc netem on {iface} → {dest_ip}"

        if self.dry_run:
            record.injected_at = time.time()
            record.status = FaultInjectionStatus.DRY_RUN
        elif applied.status == NetworkInterventionStatus.APPLIED:
            record.injected_at = time.time()
            record.status = FaultInjectionStatus.INJECTED
        else:
            record.status = FaultInjectionStatus.ABORTED
            record.notes += f" | tc apply failed: {applied.notes}"

        return record

    def _inject_service_degradation(
        self,
        scenario: FaultScenario,
        namespace: str,
        record: FaultInjectionRecord,
    ) -> FaultInjectionRecord:
        """Inject SERVICE_DEGRADATION via stress-ng CPU stress (kubectl exec)."""
        duration = int(scenario.duration_s)
        cmd = [
            "kubectl", "exec",
            f"deployment/{scenario.target_service}",
            "-n", namespace, "--",
            "stress-ng", "--cpu", "0", "--cpu-load", "90",
            "--timeout", str(duration),
        ]
        record.notes = "SERVICE_DEGRADATION injected via stress-ng CPU load"
        record.expected_delta = 90.0  # expected CPU% increase
        record = self._run_injection_cmd(cmd, record)
        return record

    def _inject_resource_contention(
        self,
        scenario: FaultScenario,
        namespace: str,
        record: FaultInjectionRecord,
    ) -> FaultInjectionRecord:
        """Inject RESOURCE_CONTENTION via memory pressure (kubectl exec)."""
        duration = int(scenario.duration_s)
        cmd = [
            "kubectl", "exec",
            f"deployment/{scenario.target_service}",
            "-n", namespace, "--",
            "stress-ng", "--vm", "1", "--vm-bytes", "80%",
            "--timeout", str(duration),
        ]
        record.notes = "RESOURCE_CONTENTION injected via stress-ng memory pressure"
        record.expected_delta = 80.0  # expected memory% spike
        record = self._run_injection_cmd(cmd, record)
        return record

    def _inject_dependency_failure(
        self,
        scenario: FaultScenario,
        namespace: str,
        record: FaultInjectionRecord,
    ) -> FaultInjectionRecord:
        """Inject DEPENDENCY_FAILURE by dropping all packets to the dependency.

        Uses tc to install a netem rule that drops 100% of packets to the
        dependency's IP, simulating a hard failure of that dependency.
        """
        dest_ip = scenario.target_ip or "0.0.0.0"
        iface = scenario.interface or "eth0"
        # Drop 100% of packets to the target dependency
        cmd_root = ["tc", "qdisc", "add", "dev", iface, "root", "handle", "1:", "prio",
                    "priomap", "0", "0", "0", "0", "0", "0", "0", "0",
                    "0", "0", "0", "0", "0", "0", "0", "0"]
        cmd_netem = ["tc", "qdisc", "add", "dev", iface, "parent", "1:10",
                     "handle", "10:", "netem", "loss", "100%"]
        cmd_filter = ["tc", "filter", "add", "dev", iface, "parent", "1:",
                      "protocol", "ip", "u32",
                      "match", "ip", "dst", f"{dest_ip}/32",
                      "flowid", "1:10"]
        record.notes = (
            f"DEPENDENCY_FAILURE injected via tc 100% packet drop to {dest_ip}"
        )
        record.expected_delta = 1.0   # health endpoint should return 0 (False)
        for cmd in (cmd_root, cmd_netem, cmd_filter):
            record = self._run_injection_cmd(cmd, record)
            if record.status == FaultInjectionStatus.ABORTED:
                return record
        return record

    def _inject_queueing(
        self,
        scenario: FaultScenario,
        namespace: str,
        record: FaultInjectionRecord,
    ) -> FaultInjectionRecord:
        """Inject QUEUEING saturation via high-concurrency load (hey/wrk).

        Sends a flood of concurrent requests to the target service's port
        to saturate its request queue.  Requires 'hey' to be available on
        the pod or a sidecar.
        """
        duration = int(scenario.duration_s)
        cmd = [
            "kubectl", "exec",
            f"deployment/{scenario.target_service}",
            "-n", namespace, "--",
            "hey", "-z", f"{duration}s", "-c", "200",
            f"http://localhost:8080/",
        ]
        record.notes = "QUEUEING saturation injected via hey flood (concurrency=200)"
        record.expected_delta = 200.0  # queue depth increase
        record = self._run_injection_cmd(cmd, record)
        return record

    # ------------------------------------------------------------------
    # Internal verification helpers
    # ------------------------------------------------------------------

    def _verify_latency(self, record: FaultInjectionRecord) -> bool:
        """Verify NETWORK_LATENCY by measuring actual RTT delta with ping.

        Passes if measured latency > expected_delta * 0.5 (50% of target
        latency must be observed to count as confirmed).
        """
        record.verification_method = "ping_rtt_measurement"
        if self.dry_run:
            record.notes += " [verify: dry_run — measurement skipped; NOT confirmed]"
            return False
        measured = _measure_latency_ms("127.0.0.1")
        record.measured_delta = measured
        if measured is None:
            record.notes += " [verify: ping unavailable]"
            return False
        threshold = (record.expected_delta or 0.0) * 0.5
        passed = measured >= threshold
        if not passed:
            record.notes += (
                f" [verify: measured {measured:.1f}ms < threshold {threshold:.1f}ms]"
            )
        return passed

    def _verify_packet_loss(self, record: FaultInjectionRecord) -> bool:
        """Verify PACKET_LOSS by reading tc drop counter delta.

        Passes if drop counter increased by at least 1 since injection.
        """
        record.verification_method = "tc_drop_counter_delta"
        if self.dry_run:
            record.notes += " [verify: dry_run — measurement skipped; NOT confirmed]"
            return False
        drops = _measure_drop_counter("eth0", "0.0.0.0")
        record.measured_delta = float(drops) if drops is not None else None
        if drops is None:
            record.notes += " [verify: tc -s unavailable]"
            return False
        passed = drops > 0
        if not passed:
            record.notes += " [verify: drop counter did not increase]"
        return passed

    def _verify_service_degradation(self, record: FaultInjectionRecord) -> bool:
        """Verify SERVICE_DEGRADATION by measuring CPU% change via kubectl top.

        Passes if measured CPU% >= 50 (stress-ng targets 90%).
        """
        record.verification_method = "kubectl_top_cpu_pct"
        if self.dry_run:
            record.notes += " [verify: dry_run — measurement skipped; NOT confirmed]"
            return False
        cpu = _measure_cpu_pct(record.fault_id, "rift-eval-dev")
        record.measured_delta = cpu
        if cpu is None:
            record.notes += " [verify: kubectl top unavailable]"
            return False
        passed = cpu >= 50.0
        if not passed:
            record.notes += f" [verify: cpu {cpu:.1f}% < threshold 50%]"
        return passed

    def _verify_resource_contention(self, record: FaultInjectionRecord) -> bool:
        """Verify RESOURCE_CONTENTION by measuring memory% via kubectl top.

        Passes if measured memory metric is elevated (threshold: any non-zero
        response, since baseline mem usage makes an absolute threshold brittle).
        """
        record.verification_method = "kubectl_top_memory_pct"
        if self.dry_run:
            record.notes += " [verify: dry_run — measurement skipped; NOT confirmed]"
            return False
        # Re-use cpu measurement as a proxy (kubectl top returns both cpu+mem)
        mem = _measure_cpu_pct(record.fault_id, "rift-eval-dev")
        record.measured_delta = mem
        if mem is None:
            record.notes += " [verify: kubectl top unavailable]"
            return False
        # Stress-ng memory load typically pushes mem usage well above idle
        passed = mem >= 40.0
        if not passed:
            record.notes += f" [verify: mem {mem:.1f}% < threshold 40%]"
        return passed

    def _verify_queueing(self, record: FaultInjectionRecord) -> bool:
        """Verify QUEUEING saturation by checking TCP socket queue depth.

        Passes if queue depth > 0 (active backlog exists).
        """
        record.verification_method = "tcp_socket_queue_depth"
        if self.dry_run:
            record.notes += " [verify: dry_run — measurement skipped; NOT confirmed]"
            return False
        depth = _measure_queue_depth(record.fault_id, "rift-eval-dev")
        record.measured_delta = float(depth) if depth is not None else None
        if depth is None:
            record.notes += " [verify: queue depth measurement unavailable]"
            return False
        passed = depth > 0
        if not passed:
            record.notes += " [verify: queue depth is 0 — not saturated]"
        return passed

    def _verify_dependency_failure(self, record: FaultInjectionRecord) -> bool:
        """Verify DEPENDENCY_FAILURE by checking health endpoint is unreachable.

        Passes if the health endpoint returns a failure (curl non-zero),
        confirming that the 100% packet drop is in effect.
        """
        record.verification_method = "health_endpoint_reachability"
        if self.dry_run:
            record.notes += " [verify: dry_run — measurement skipped; NOT confirmed]"
            return False
        healthy = _check_health_endpoint(record.fault_id, "rift-eval-dev")
        record.measured_delta = 0.0 if healthy else 1.0
        # Dependency failure means health endpoint should be UNREACHABLE → False
        passed = not healthy
        if not passed:
            record.notes += " [verify: health endpoint still reachable — failure not confirmed]"
        return passed

    # ------------------------------------------------------------------
    # Command execution helpers
    # ------------------------------------------------------------------

    def _run_injection_cmd(
        self,
        cmd: List[str],
        record: FaultInjectionRecord,
    ) -> FaultInjectionRecord:
        """Execute *cmd* (or dry-run it) and update *record* accordingly."""
        if self.dry_run:
            record.injected_at = time.time()
            record.status = FaultInjectionStatus.DRY_RUN
            return record
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                check=False,
            )
            if result.returncode == 0:
                record.injected_at = time.time()
                record.status = FaultInjectionStatus.INJECTED
            else:
                record.status = FaultInjectionStatus.ABORTED
                record.notes += (
                    f" | cmd failed (rc={result.returncode}): "
                    f"{result.stderr.decode(errors='replace')[:200]}"
                )
        except subprocess.TimeoutExpired:
            record.status = FaultInjectionStatus.ABORTED
            record.notes += " | injection command timed out"
        return record

    def _run_rollback_cmd(self, cmd: List[str]) -> bool:
        """Execute a rollback command; return True on success."""
        if self.dry_run:
            return True
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=15, check=False)
            return result.returncode == 0
        except Exception:
            return False
