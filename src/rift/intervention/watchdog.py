"""Independent Rollback Watchdog for RIFT Network Interventions — Phase 4 Remediation.

Provides an independent, detached watchdog mechanism ensuring that any applied
tc netem qdisc is guaranteed to be deleted after a strict timeout (max 30.0s),
even if the initiating Python runtime crashes, is killed (OOM/SIGKILL), or the
SSH connection is severed.

Authority: SPRINT4_1_1_INDEPENDENT_PLAN_AUDIT.md Finding F-04.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class WatchdogStatus(str, Enum):
    ARMED = "ARMED"
    DISARMED = "DISARMED"
    TRIGGERED = "TRIGGERED"
    FAILED = "FAILED"


@dataclass
class WatchdogSpec:
    """
    Specification for arming an independent rollback watchdog.

    experiment_id : Unique identifier for the experiment run.
    target_pid    : Container PID whose NetNS will be cleaned.
    interface     : Container-internal network interface (e.g., 'eth0').
    tc_handle     : Child handle to remove (e.g., '1:').
    timeout_s     : Maximum perturbation duration before forced rollback (<= 30.0s).
    """
    experiment_id: str
    target_pid: int
    interface: str
    tc_handle: str = "1:"
    timeout_s: float = 30.0

    def __post_init__(self) -> None:
        if self.target_pid <= 1:
            raise ValueError(
                f"Invalid target_pid={self.target_pid}: Watchdog cannot target host PID."
            )
        if self.timeout_s <= 0.0 or self.timeout_s > 30.0:
            raise ValueError(
                f"timeout_s={self.timeout_s} exceeds maximum allowed safety threshold of 30.0s."
            )


@dataclass
class WatchdogRecord:
    spec: WatchdogSpec
    watchdog_pid: Optional[int] = None
    armed_at: float = field(default_factory=time.time)
    deadline: float = 0.0
    status: WatchdogStatus = WatchdogStatus.ARMED
    disarmed_at: Optional[float] = None
    notes: str = ""

    def __post_init__(self) -> None:
        if self.deadline == 0.0:
            self.deadline = self.armed_at + self.spec.timeout_s


class DetachedRollbackWatchdog:
    """
    Manages detached, asynchronous rollback timers.

    Before applying any network perturbation, the caller must call arm().
    If arm() fails, the intervention MUST be aborted immediately (fail-closed).
    Upon successful experiment completion and normal rollback, caller calls disarm().
    If the caller crashes, the detached subshell executes 'tc qdisc del' at the deadline.
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._records: dict[str, WatchdogRecord] = {}

    def generate_watchdog_command(self, spec: WatchdogSpec) -> List[str]:
        """
        Generate the detached shell script command.
        Uses nsenter inside the target container NetNS to cleanly remove qdisc.
        Revalidates target PID existence and confirms NetNS inode is not host NetNS.
        """
        handle_clean = spec.tc_handle.rstrip(":")
        clean_script = (
            f"sleep {spec.timeout_s:.1f} && "
            f"if [ -d /proc/{spec.target_pid}/ns ] && "
            f"[ \"$(stat -L -c '%i' /proc/{spec.target_pid}/ns/net 2>/dev/null)\" != "
            f"\"$(stat -L -c '%i' /proc/1/ns/net 2>/dev/null)\" ]; then "
            f"nsenter -t {spec.target_pid} -n tc filter del dev {spec.interface} parent 1: "
            f"protocol ip u32 2>/dev/null || true; "
            f"nsenter -t {spec.target_pid} -n tc qdisc del dev {spec.interface} parent 1:{handle_clean} "
            f"handle {handle_clean}: 2>/dev/null || true; "
            f"nsenter -t {spec.target_pid} -n tc qdisc del dev {spec.interface} root handle 1: 2>/dev/null || true; "
            f"fi"
        )
        return ["sh", "-c", clean_script]

    def arm(self, spec: WatchdogSpec) -> WatchdogRecord:
        """
        Arm the independent watchdog timer. Must succeed before any tc netem apply.
        """
        record = WatchdogRecord(spec=spec)
        if self.dry_run:
            record.watchdog_pid = 99999
            record.status = WatchdogStatus.ARMED
            self._records[spec.experiment_id] = record
            return record

        try:
            cmd = self.generate_watchdog_command(spec)
            # Spawn detached process with start_new_session=True so it survives parent death
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            record.watchdog_pid = proc.pid
            record.status = WatchdogStatus.ARMED
            self._records[spec.experiment_id] = record
            return record
        except Exception as e:
            record.status = WatchdogStatus.FAILED
            record.notes = f"Failed to arm watchdog: {e}"
            raise RuntimeError(f"Watchdog arming failed: {e}. Intervention aborted.") from e

    def disarm(self, experiment_id: str) -> bool:
        """
        Disarm the watchdog when normal experiment teardown has succeeded.
        """
        record = self._records.get(experiment_id)
        if not record:
            return False

        if record.watchdog_pid and not self.dry_run:
            try:
                # Terminate the sleeping watchdog process
                os.kill(record.watchdog_pid, 15)  # SIGTERM
            except ProcessLookupError:
                pass  # Already terminated

        record.status = WatchdogStatus.DISARMED
        record.disarmed_at = time.time()
        return True
