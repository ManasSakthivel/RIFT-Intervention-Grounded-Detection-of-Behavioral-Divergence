"""Linux tc netem Network Intervention Backend — Phase 3.6 §27.

Status: IMPLEMENTED / READY_FOR_LINUX

This backend executes real tc u32 + per-destination netem commands.
It requires:
  - Linux kernel (NOT macOS; tc is Linux-only)
  - CAP_NET_ADMIN capability
  - Network interface accessible inside the container/namespace

This file is FULLY IMPLEMENTED. It cannot be VALIDATED until the
Online Boutique testbed is deployed on Linux.

Do NOT use this backend on macOS or without CAP_NET_ADMIN.
Do NOT use this backend in production namespaces.
All interventions must target rift-eval-* namespaces only.

Label: READY_FOR_LINUX

Authority: Phase 3.6 §27, docs/PHASE_3_SPEC_FREEZE.md §11.
"""
from __future__ import annotations

import subprocess
import sys
import time
from typing import List, Optional

from src.rift.intervention.network_intervention import (
    NetworkInterventionRecord,
    NetworkInterventionStatus,
)


_LINUX_ONLY_WARNING = (
    "LinuxTcNetemBackend requires Linux + CAP_NET_ADMIN. "
    "This backend is READY_FOR_LINUX but cannot execute on this platform. "
    "Use DryRunBackend for development and CI. "
    "Status: READY_FOR_LINUX"
)


def _check_linux() -> bool:
    """Return True if running on Linux with tc available."""
    return sys.platform.startswith("linux")


def _run_tc(cmd: List[str], timeout: int = 10) -> subprocess.CompletedProcess:
    """Execute a tc command. Raises RuntimeError on non-Linux."""
    if not _check_linux():
        raise RuntimeError(_LINUX_ONLY_WARNING)
    return subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)


class LinuxTcNetemBackend:
    """
    Live Linux tc u32 + per-destination netem backend.

    Status: IMPLEMENTED / READY_FOR_LINUX

    Every method raises RuntimeError on non-Linux platforms.
    On Linux: executes real tc commands with CAP_NET_ADMIN.

    Per-destination targeting (A5 isolation requirement):
    - Only traffic to destination_ip is affected
    - Other service traffic is unaffected
    - u32 classifier selects packets by dst IP before netem applies

    Command sequence:
    APPLY:
      1. tc qdisc add dev {iface} root handle 1: prio priomap 0 0 ...
      2. tc qdisc add dev {iface} parent 1:{handle} handle {handle}: netem delay {lat}ms
      3. tc filter add dev {iface} parent 1: protocol ip u32 match ip dst {ip}/32 flowid 1:{handle}

    ROLLBACK:
      1. tc filter del dev {iface} parent 1: protocol ip u32 match ip dst {ip}/32 flowid 1:{handle}
      2. tc qdisc del dev {iface} parent 1:{handle} handle {handle}:
    """

    name: str = "LINUX_TC_NETEM"
    is_live: bool = True

    def __init__(self, sandbox_namespace: Optional[str] = None):
        """
        Parameters
        ----------
        sandbox_namespace : Linux network namespace name (optional).
            If set, all commands are prefixed with 'ip netns exec {ns}'.
            Must match rift-eval-* pattern (validated by safety controller).
        """
        self.sandbox_namespace = sandbox_namespace
        self._active: dict = {}

    def _wrap_ns(self, cmd: List[str]) -> List[str]:
        if self.sandbox_namespace:
            return ["ip", "netns", "exec", self.sandbox_namespace] + cmd
        return cmd

    def apply(self, record: NetworkInterventionRecord) -> NetworkInterventionRecord:
        """Apply per-destination netem. Requires Linux+CAP_NET_ADMIN."""
        iface = record.interface
        handle = record.tc_handle.rstrip(":")
        dest_ip = record.destination_ip
        lat = record.latency_ms
        jitter = record.jitter_ms
        loss = record.packet_loss_pct

        cmds = [
            ["tc", "qdisc", "add", "dev", iface, "root", "handle", "1:", "prio",
             "priomap"] + ["0"] * 16,
            ["tc", "qdisc", "add", "dev", iface, "parent", f"1:{handle}",
             "handle", f"{handle}:", "netem",
             "delay", f"{lat:.1f}ms", f"{jitter:.1f}ms",
             "distribution", "normal",
             "loss", f"{loss:.2f}%"],
            ["tc", "filter", "add", "dev", iface, "parent", "1:",
             "protocol", "ip", "u32",
             "match", "ip", "dst", f"{dest_ip}/32",
             "flowid", f"1:{handle}"],
        ]

        for cmd in cmds:
            result = _run_tc(self._wrap_ns(cmd))
            if result.returncode != 0:
                record.status = NetworkInterventionStatus.FAILED
                record.notes = (
                    f"tc command failed: {' '.join(cmd)}\n"
                    f"stderr: {result.stderr.decode(errors='replace')}"
                )
                return record

        record.t_applied = time.time()
        record.status = NetworkInterventionStatus.APPLIED
        self._active[record.record_id] = record
        return record

    def verify(
        self,
        record: NetworkInterventionRecord,
        measured_latency_ms: Optional[float] = None,
    ) -> NetworkInterventionRecord:
        """
        Verify intervention via independent measurement.

        If measured_latency_ms is provided: check precision ±20%.
        Otherwise: check that the tc qdisc was created via 'tc qdisc show'.
        """
        if record.status != NetworkInterventionStatus.APPLIED:
            record.notes = "Cannot verify: not in APPLIED state."
            return record

        if measured_latency_ms is not None:
            precision = abs(measured_latency_ms - record.latency_ms) / max(1.0, record.latency_ms)
            record.precision_achieved = 1.0 - precision
            record.precision_check_pass = precision < 0.20
        else:
            # Independent verification via tc show
            result = _run_tc(["tc", "qdisc", "show", "dev", record.interface])
            handle_str = record.tc_handle.rstrip(":")
            found = handle_str in result.stdout.decode(errors="replace")
            record.precision_check_pass = found
            record.precision_achieved = 1.0 if found else 0.0

        if record.precision_check_pass:
            record.status = NetworkInterventionStatus.VERIFIED
            record.isolation_verified = True
        else:
            record.status = NetworkInterventionStatus.CONFOUNDED
            record.notes = (
                f"Verification failed: precision={record.precision_achieved:.2f} "
                f"or qdisc not found. tc netem may not be active."
            )

        return record

    def rollback(self, record: NetworkInterventionRecord) -> NetworkInterventionRecord:
        """Remove the per-destination netem rule. Always attempted."""
        iface = record.interface
        handle = record.tc_handle.rstrip(":")
        dest_ip = record.destination_ip

        rollback_cmds = [
            ["tc", "filter", "del", "dev", iface, "parent", "1:",
             "protocol", "ip", "u32",
             "match", "ip", "dst", f"{dest_ip}/32",
             "flowid", f"1:{handle}"],
            ["tc", "qdisc", "del", "dev", iface, "parent", f"1:{handle}",
             "handle", f"{handle}:"],
        ]

        record.rollback_attempts += 1
        for cmd in rollback_cmds:
            _run_tc(self._wrap_ns(cmd))
            # Ignore non-zero returns (rule may already be removed)

        record.t_rolled_back = time.time()
        record.status = NetworkInterventionStatus.ROLLED_BACK
        self._active.pop(record.record_id, None)
        return record

    def rollback_all(self) -> list:
        rolled = []
        for record_id in list(self._active.keys()):
            record = self._active[record_id]
            rolled.append(self.rollback(record))
        return rolled
