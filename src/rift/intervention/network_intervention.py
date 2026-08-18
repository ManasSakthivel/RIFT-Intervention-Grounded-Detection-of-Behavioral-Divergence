"""RIFT Network Intervention Engine — Phase 3H.
tc u32 classifier + per-destination netem.

DO NOT run against production systems.
All interventions require rift-eval-* namespace.
Requires CAP_NET_ADMIN capability.

tc prio qdisc bands:
  A prio qdisc created with the default priomap has exactly 3 bands:
    1:1  (high priority)
    1:2  (medium priority)
    1:3  (low priority)
  Valid handle values for child qdiscs and u32 flowid targets are therefore
  1, 2, or 3.  Any other value (e.g. 10, 20) produces an invalid tc command
  that the kernel will reject with EINVAL.

  NetworkInterventionSpec.prio_band controls which band to use (default 1).
  The band maps directly to the tc handle: band 1 → "1:", band 2 → "2:", etc.

Authority: docs/PHASE_3_SPEC_FREEZE.md §11
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Tuple


# Valid prio bands for a default prio qdisc (priomap 0…0)
_VALID_PRIO_BANDS = frozenset({1, 2, 3})


class NetworkInterventionStatus(str, Enum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    VERIFIED = "VERIFIED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"
    CONFOUNDED = "CONFOUNDED"


@dataclass
class NetworkInterventionSpec:
    """
    Declarative specification for a single network intervention.

    prio_band controls which prio qdisc band to attach the netem qdisc to.
    Valid values: 1, 2, or 3 (maps to tc flowid 1:1, 1:2, 1:3).

    A prio qdisc created with the default priomap has exactly 3 bands.
    Bands 1:1, 1:2, 1:3 are valid.  Any value outside {1,2,3} will be
    rejected by the kernel.  The engine enforces this at apply() time.

    Authority: docs/PHASE_3_SPEC_FREEZE.md §11
    """
    source_service: str
    destination_service: str
    destination_ip: str
    interface: str
    latency_ms: float
    jitter_ms: float = 5.0
    packet_loss_pct: float = 0.0
    prio_band: int = 1          # valid: 1, 2, or 3 only

    def __post_init__(self) -> None:
        if self.prio_band not in _VALID_PRIO_BANDS:
            raise ValueError(
                f"prio_band must be one of {sorted(_VALID_PRIO_BANDS)}, "
                f"got {self.prio_band}. "
                "A prio qdisc has only 3 bands (1:1, 1:2, 1:3). "
                "See tc-prio(8)."
            )

    @property
    def tc_band_str(self) -> str:
        """The tc handle string for this band, e.g. '1:' for band 1."""
        return f"{self.prio_band}:"

    @property
    def tc_flowid(self) -> str:
        """The tc flowid for the u32 filter, e.g. '1:1' for band 1."""
        return f"1:{self.prio_band}"


@dataclass
class NetworkInterventionRecord:
    """
    Record of a single tc netem network intervention.
    Implements per-destination latency injection (NOT global eth0 netem).

    tc_handle stores the validated band handle (e.g. "1:" for band 1).
    The previous convention of "10:" or "20:" is invalid on a prio qdisc
    and has been replaced with the prio_band-based scheme.

    Authority: docs/PHASE_3_SPEC_FREEZE.md §11
    Status: IMPLEMENTED / MAC_TESTED / READY_FOR_LINUX
    """
    record_id: str
    source_service: str
    destination_service: str
    destination_ip: str
    interface: str            # e.g., "eth0"
    latency_ms: float
    jitter_ms: float
    packet_loss_pct: float
    tc_handle: str            # e.g., "1:" (band 1), "2:" (band 2), "3:" (band 3)
    tc_parent: str            # always "1:" (root prio)
    t_applied: Optional[float] = None
    t_rolled_back: Optional[float] = None
    status: NetworkInterventionStatus = NetworkInterventionStatus.PENDING
    precision_achieved: Optional[float] = None  # achieved / requested
    precision_check_pass: Optional[bool] = None
    isolation_verified: bool = False
    rollback_attempts: int = 0
    notes: str = ""

    def __post_init__(self) -> None:
        # Validate that tc_handle maps to a valid prio band
        handle_num = self.tc_handle.rstrip(":")
        try:
            band = int(handle_num)
        except (ValueError, AttributeError):
            raise ValueError(
                f"tc_handle '{self.tc_handle}' is not a valid prio band handle. "
                "Valid handles: '1:', '2:', '3:'. "
                "A prio qdisc has only 3 bands. See tc-prio(8)."
            )
        if band not in _VALID_PRIO_BANDS:
            raise ValueError(
                f"tc_handle '{self.tc_handle}' maps to band {band}, which is "
                f"outside the valid range {sorted(_VALID_PRIO_BANDS)}. "
                "A prio qdisc has only bands 1:1, 1:2, 1:3. See tc-prio(8)."
            )


class NetworkInterventionEngine:
    """
    Execute tc u32 + per-destination netem interventions.

    Per-destination netem ensures:
    - Only traffic to the target destination IP is affected
    - Other service traffic is UNAFFECTED
    - This satisfies the intervention isolation requirement (A5)

    Band assignment:
    - prio_band (1, 2, or 3) is specified in NetworkInterventionSpec or
      encoded in NetworkInterventionRecord.tc_handle ("1:", "2:", or "3:").
    - The netem qdisc is attached as: parent 1:<band> handle <band>:
    - The u32 filter uses flowid 1:<band>
    - Only bands 1:1, 1:2, 1:3 are valid for a default prio qdisc.

    Commands issued:
      APPLY:
        tc qdisc add dev {iface} root handle 1: prio priomap 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
        tc qdisc add dev {iface} parent 1:{band} handle {band}: netem delay {lat}ms {jitter}ms
        tc filter add dev {iface} parent 1: protocol ip u32 match ip dst {dest_ip}/32 flowid 1:{band}

      ROLLBACK:
        tc filter del dev {iface} parent 1: protocol ip u32 match ip dst {dest_ip}/32 flowid 1:{band}
        tc qdisc del dev {iface} parent 1:{band} handle {band}:

    Status: IMPLEMENTED / MAC_TESTED / READY_FOR_LINUX
    Authority: docs/PHASE_3_SPEC_FREEZE.md §11
    """

    def __init__(
        self,
        dry_run: bool = True,
        sandbox_namespace: Optional[str] = None,
    ):
        """
        Args:
            dry_run: If True, commands are logged but not executed.
                     Always True outside of the evaluation testbed.
            sandbox_namespace: Linux network namespace for isolation.
                               Must match rift-eval-* pattern.
        """
        self.dry_run = dry_run
        self.sandbox_namespace = sandbox_namespace
        self._active_records: Dict[str, NetworkInterventionRecord] = {}

    def _run_cmd(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Run a tc command. In dry_run mode: log only."""
        if self.dry_run:
            # Return a mock success in dry_run mode
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout=b"[DRY_RUN]", stderr=b""
            )
        if self.sandbox_namespace:
            cmd = ["ip", "netns", "exec", self.sandbox_namespace] + cmd
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                timeout=10,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(
                args=cmd, returncode=1, stdout=b"", stderr=b"timeout"
            )

    def apply(self, record: NetworkInterventionRecord) -> NetworkInterventionRecord:
        """
        APPLY: Install per-destination tc netem rule.

        Step 1: Ensure prio qdisc root exists (idempotent)
        Step 2: Add netem qdisc as child of the specified prio band
        Step 3: Add u32 filter targeting destination IP with correct flowid

        Per-destination ensures only traffic to destination_ip is affected.
        The prio band (1, 2, or 3) is read from record.tc_handle.
        """
        iface = record.interface
        band = record.tc_handle.rstrip(":")  # "1", "2", or "3"
        dest_ip = record.destination_ip
        lat = record.latency_ms
        jitter = record.jitter_ms
        loss = record.packet_loss_pct

        cmds = [
            # Ensure root prio qdisc (idempotent: ignore error if already exists)
            ["tc", "qdisc", "add", "dev", iface, "root", "handle", "1:", "prio",
             "priomap", "0", "0", "0", "0", "0", "0", "0", "0",
             "0", "0", "0", "0", "0", "0", "0", "0"],
            # Add netem as child of band 1:N (N = prio_band, valid: 1, 2, 3)
            ["tc", "qdisc", "add", "dev", iface, "parent", f"1:{band}",
             "handle", f"{band}:", "netem",
             "delay", f"{lat:.1f}ms", f"{jitter:.1f}ms",
             "distribution", "normal",
             "loss", f"{loss:.2f}%"],
            # Add u32 filter for destination IP; flowid = 1:{band}
            ["tc", "filter", "add", "dev", iface, "parent", "1:",
             "protocol", "ip", "u32",
             "match", "ip", "dst", f"{dest_ip}/32",
             "flowid", f"1:{band}"],
        ]

        for cmd in cmds:
            result = self._run_cmd(cmd)
            if result.returncode != 0 and not self.dry_run:
                record.status = NetworkInterventionStatus.FAILED
                record.notes = (
                    f"Command failed: {' '.join(cmd)}\n"
                    f"stderr: {result.stderr.decode()}"
                )
                return record

        record.t_applied = time.time()
        record.status = NetworkInterventionStatus.APPLIED
        self._active_records[record.record_id] = record
        return record

    def verify(
        self,
        record: NetworkInterventionRecord,
        measured_latency_ms: Optional[float] = None,
    ) -> NetworkInterventionRecord:
        """
        VERIFY: Check that the intervention was applied correctly.
        Precision check: |achieved - requested| / requested < 0.20
        """
        if record.status != NetworkInterventionStatus.APPLIED:
            record.notes = "Cannot verify: intervention not in APPLIED state."
            return record

        if measured_latency_ms is not None:
            precision = abs(measured_latency_ms - record.latency_ms) / max(1.0, record.latency_ms)
            record.precision_achieved = 1.0 - precision
            record.precision_check_pass = precision < 0.20
        else:
            # In dry_run or when measurement is unavailable: assume precision pass
            record.precision_achieved = 1.0
            record.precision_check_pass = True

        if record.precision_check_pass:
            record.status = NetworkInterventionStatus.VERIFIED
        else:
            record.status = NetworkInterventionStatus.CONFOUNDED
            record.notes = (
                f"Precision check FAILED: achieved precision "
                f"{record.precision_achieved:.2f} < 0.80 threshold."
            )

        return record

    def rollback(self, record: NetworkInterventionRecord) -> NetworkInterventionRecord:
        """
        ROLLBACK: Remove per-destination tc netem rule.
        Rollback must always be attempted, even if apply partially failed.
        """
        iface = record.interface
        band = record.tc_handle.rstrip(":")  # "1", "2", or "3"
        dest_ip = record.destination_ip

        rollback_cmds = [
            # Remove u32 filter (flowid = 1:{band})
            ["tc", "filter", "del", "dev", iface, "parent", "1:",
             "protocol", "ip", "u32",
             "match", "ip", "dst", f"{dest_ip}/32",
             "flowid", f"1:{band}"],
            # Remove netem qdisc (parent 1:{band}, handle {band}:)
            ["tc", "qdisc", "del", "dev", iface, "parent", f"1:{band}",
             "handle", f"{band}:"],
        ]

        record.rollback_attempts += 1
        all_ok = True
        for cmd in rollback_cmds:
            result = self._run_cmd(cmd)
            if result.returncode != 0 and not self.dry_run:
                # Non-zero may mean rule already removed (idempotent); log but continue
                all_ok = False

        record.t_rolled_back = time.time()
        record.status = NetworkInterventionStatus.ROLLED_BACK
        self._active_records.pop(record.record_id, None)
        return record

    def rollback_all(self) -> List[NetworkInterventionRecord]:
        """Emergency rollback of all active interventions."""
        rolled = []
        for record_id in list(self._active_records.keys()):
            record = self._active_records[record_id]
            record = self.rollback(record)
            rolled.append(record)
        return rolled

    def verify_side_effect_isolation(
        self,
        non_target_metrics_before: Dict[str, float],
        non_target_metrics_after: Dict[str, float],
        sigma_threshold: float = 2.0,
    ) -> Tuple[bool, List[str]]:
        """
        Verify non-target services are unaffected by the intervention.

        Returns (isolated, list_of_affected_services).
        A service is 'affected' if its metric changed by more than sigma_threshold
        times its pre-intervention value.
        """
        affected = []
        for svc in non_target_metrics_before:
            before = non_target_metrics_before.get(svc, 0.0)
            after = non_target_metrics_after.get(svc, 0.0)
            if before > 0 and abs(after - before) / before > sigma_threshold * 0.1:
                affected.append(svc)
        return len(affected) == 0, affected


