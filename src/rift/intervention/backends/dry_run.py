"""DryRun Network Intervention Backend — Phase 3.6 §27.

Implements NetworkInterventionBackend for macOS / CI environments.
All tc commands are logged but NOT executed.

Status: IMPLEMENTED
Label: DRY_RUN

DRY_RUN is useful for:
- Testing orchestration logic (lifecycle phases)
- CI pipeline validation
- Development on macOS where tc is unavailable

DRY_RUN is NOT evidence that real tc/netem works.
All dry-run records are explicitly tagged DRY_RUN in their artifacts.

Authority: Phase 3.6 §27, docs/PHASE_3_SPEC_FREEZE.md §11.
"""
from __future__ import annotations

import time
import uuid
from typing import List, Optional

from src.rift.intervention.network_intervention import (
    NetworkInterventionRecord,
    NetworkInterventionStatus,
)


class DryRunBackend:
    """
    Dry-run backend for development and CI.

    Logs all tc commands without executing them.
    Returns mock success for all operations.
    """

    name: str = "DRY_RUN"
    is_live: bool = False

    def __init__(self):
        self._log: List[str] = []
        self._applied: dict = {}

    def apply(self, record: NetworkInterventionRecord) -> NetworkInterventionRecord:
        """Log apply command. Return APPLIED status (not executed)."""
        cmds = self._build_apply_commands(record)
        for cmd in cmds:
            self._log.append(f"[DRY_RUN APPLY] {' '.join(cmd)}")

        record.t_applied = time.time()
        record.status = NetworkInterventionStatus.APPLIED
        record.notes = (
            "DRY_RUN: tc commands logged but not executed. "
            "NOT evidence that real tc/netem works. "
            "Label: DRY_RUN"
        )
        self._applied[record.record_id] = record
        return record

    def verify(
        self,
        record: NetworkInterventionRecord,
        measured_latency_ms: Optional[float] = None,
    ) -> NetworkInterventionRecord:
        """Dry-run verify: assume precision pass but log explicitly as DRY_RUN."""
        self._log.append(f"[DRY_RUN VERIFY] record_id={record.record_id} — NOT MEASURED")
        record.precision_achieved = None   # unknown — not measured
        record.precision_check_pass = None  # unknown
        record.status = NetworkInterventionStatus.VERIFIED
        record.notes = (
            (record.notes + " | " if record.notes else "") +
            "DRY_RUN: verification skipped — no independent measurement performed. "
            "NOT evidence of correct tc behavior."
        )
        return record

    def rollback(self, record: NetworkInterventionRecord) -> NetworkInterventionRecord:
        """Log rollback command. Return ROLLED_BACK status (not executed)."""
        cmds = self._build_rollback_commands(record)
        for cmd in cmds:
            self._log.append(f"[DRY_RUN ROLLBACK] {' '.join(cmd)}")

        record.t_rolled_back = time.time()
        record.status = NetworkInterventionStatus.ROLLED_BACK
        self._applied.pop(record.record_id, None)
        return record

    def rollback_all(self) -> List[NetworkInterventionRecord]:
        """Roll back all active records."""
        rolled = []
        for record_id in list(self._applied.keys()):
            record = self._applied[record_id]
            record = self.rollback(record)
            rolled.append(record)
        return rolled

    def get_log(self) -> List[str]:
        """Return all logged commands (for test verification)."""
        return list(self._log)

    # ── Command builders (same logic as live backend, for completeness) ──

    def _build_apply_commands(self, record: NetworkInterventionRecord) -> List[List[str]]:
        iface = record.interface
        handle = record.tc_handle.rstrip(":")
        dest_ip = record.destination_ip
        lat = record.latency_ms
        jitter = record.jitter_ms
        loss = record.packet_loss_pct
        return [
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

    def _build_rollback_commands(self, record: NetworkInterventionRecord) -> List[List[str]]:
        iface = record.interface
        handle = record.tc_handle.rstrip(":")
        dest_ip = record.destination_ip
        return [
            ["tc", "filter", "del", "dev", iface, "parent", "1:",
             "protocol", "ip", "u32",
             "match", "ip", "dst", f"{dest_ip}/32",
             "flowid", f"1:{handle}"],
            ["tc", "qdisc", "del", "dev", iface, "parent", f"1:{handle}",
             "handle", f"{handle}:"],
        ]
